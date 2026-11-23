"""Sincroniza tabelas oficiais da RFB de `originals` para SQLite.

Lê diretamente as migrações oficiais Flyway da RFB na branch `originals` via `git show`,
sem copiar a pasta `references/` para a branch de trabalho.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sqlite3
import subprocess

ROOT_DIR = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT_DIR / "backend" / "app" / "modules" / "tabelas_oficiais" / "schema.sql"
DB_PATH = ROOT_DIR / "database" / "rtc_referencias.db"

_DEFAULT_IBS_UF = "10.00"
_DEFAULT_CBS = "8.80"
_LOWERCASE_PREPOSITIONS = {"DA", "DAS", "DE", "DO", "DOS", "E"}

_SQL_CST_IBSCBS = """
SELECT
    st.SITR_CD AS cst,
    ct.CLTR_CD AS c_class_trib,
    ct.CLTR_DESCRICAO AS descricao,
    MAX(CASE WHEN pr.PERE_TBTO_ID = 3 THEN pr.PERE_VALOR END) AS red_ibs,
    MAX(CASE WHEN pr.PERE_TBTO_ID = 2 THEN pr.PERE_VALOR END) AS red_cbs,
    ct.CLTR_INICIO_VIGENCIA AS inicio_vigencia,
    ct.CLTR_FIM_VIGENCIA AS fim_vigencia,
    st.SITR_IND_GIBSCBS AS ind_gibscbs
FROM CLASSIFICACAO_TRIBUTARIA ct
JOIN SITUACAO_TRIBUTARIA st ON st.SITR_ID = ct.CLTR_SITR_ID
JOIN TRIBUTO_SITUACAO_TRIBUTARIA tst
    ON tst.TRST_SITR_ID = st.SITR_ID AND tst.TRST_TBTO_ID IN (2, 3, 4)
LEFT JOIN PERCENTUAL_REDUCAO pr ON pr.PERE_CLTR_ID = ct.CLTR_ID
GROUP BY ct.CLTR_ID
ORDER BY st.SITR_CD, ct.CLTR_CD, ct.CLTR_INICIO_VIGENCIA
"""

_SQL_ATIVIDADES_SIMPLES = """
SELECT
    ATSN_CATIVSN, ATSN_DESCRICAO, ATSN_ANEXO_SEM_FATOR_R,
    ATSN_ANEXO_COM_FATOR_R, ATSN_FIM_VIGENCIA
FROM ATIVIDADE_SIMPLES_NACIONAL
WHERE ATSN_CATIVSN IS NOT NULL
ORDER BY ATSN_ORDEM
"""

_SQL_REDUTOR_COMPRA_GOV = """
SELECT RCGO_ID, RCGO_VALOR, RCGO_INICIO_VIGENCIA, RCGO_FIM_VIGENCIA
FROM REDUTOR_COMPRA_GOVERNAMENTAL ORDER BY RCGO_ID
"""

_SQL_TRANSFERENCIA_CBS = """
SELECT TCEG_ID, TCEG_VALOR, TCEG_INICIO_VIGENCIA, TCEG_FIM_VIGENCIA
FROM TRANSFERENCIA_CBS_ENTE_GOV ORDER BY TCEG_ID
"""

_SQL_NCM_IS_AD_VALOREM = """
SELECT
    p.AAVP_NCM_CD, COALESCE(n.NCM_DESCRICAO, 'NCM sujeito ao Imposto Seletivo'),
    a.AADV_VALOR, NULL, p.AAVP_INICIO_VIGENCIA, p.AAVP_FIM_VIGENCIA
FROM ALIQUOTA_AD_VALOREM_PRODUTO p
JOIN ALIQUOTA_AD_VALOREM a ON a.AADV_ID = p.AAVP_AADV_ID
LEFT JOIN NCM n ON n.NCM_CD = p.AAVP_NCM_CD
WHERE a.AADV_TBTO_ID = 1
ORDER BY p.AAVP_NCM_CD
"""

_SQL_NCM_IS_AD_REM = """
SELECT
    p.AARP_NCM_CD, COALESCE(n.NCM_DESCRICAO, 'NCM sujeito ao Imposto Seletivo (Ad Rem)'),
    NULL, a.AARE_VALOR, p.AARP_INICIO_VIGENCIA, p.AARP_FIM_VIGENCIA
FROM ALIQUOTA_AD_REM_PRODUTO p
JOIN ALIQUOTA_AD_REM a ON a.AARE_ID = p.AARP_AARE_ID
LEFT JOIN NCM n ON n.NCM_CD = p.AARP_NCM_CD
WHERE a.AARE_TBTO_ID = 1
ORDER BY p.AARP_NCM_CD
"""

_SQL_NBS_APLICAVEL = """
SELECT
    na.NBSA_NBS_CD, COALESCE(n.NBS_DESCRICAO, 'Serviço NBS aplicável'),
    n.NBS_LC_116, ct.CLTR_CD, na.NBSA_INICIO_VIGENCIA, na.NBSA_FIM_VIGENCIA
FROM NBS_APLICAVEL na
LEFT JOIN NBS n ON n.NBS_CD = na.NBSA_NBS_CD
LEFT JOIN CLASSIFICACAO_TRIBUTARIA ct ON ct.CLTR_ID = na.NBSA_CLTR_ID
ORDER BY na.NBSA_NBS_CD
"""

_SQL_TRATAMENTO_TRIBUTARIO = """
SELECT
    TRTR_ID, TRTR_DESCRICAO, TRTR_EXPRESSAO_ALIQUOTA, TRTR_EXPRESSAO_ALIQUOTA_EFETIVA,
    TRTR_EXPRESSAO_BASE_CALCULO, TRTR_EXPRESSAO_TRIBUTO_CALCULADO, TRTR_EXPRESSAO_TRIBUTO_DEVIDO,
    COALESCE(TRTR_IN_POSSUI_PERCENTUAL_REDUCAO, 0), COALESCE(TRTR_IN_POSSUI_MONOFASIA, 0),
    TRTR_INICIO_VIGENCIA, TRTR_FIM_VIGENCIA
FROM TRATAMENTO_TRIBUTARIO
ORDER BY TRTR_ID
"""


def _format_uf_name(raw_name: str) -> str:
    words = raw_name.strip().split()
    return " ".join(
        w.lower() if idx > 0 and w.upper() in _LOWERCASE_PREPOSITIONS else w.capitalize()
        for idx, w in enumerate(words)
    )


def _format_pct(value: float | None, cst: str, ind_gibscbs: int) -> str:
    if cst in {"400", "410"} and ind_gibscbs == 0:
        return "100.00"
    return f"{float(value):.2f}" if value is not None else "0.00"


def _migration_sort_key(path: str) -> tuple[int, int]:
    name = path.rsplit("/", 1)[-1]
    prefix = 0 if name.startswith("B") else 1
    match = re.search(r"[BV](\d+)", name)
    return (prefix, int(match.group(1)) if match else 0)


def _load_rfb_memory_db(branch: str = "originals") -> sqlite3.Connection:
    """Executa todas as migrações Flyway da RFB (B0001..V0053) em SQLite em memória."""
    raw_files = subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", branch, "references/regime-regular/flyway/sql/"],
        cwd=ROOT_DIR,
    ).decode("utf-8")

    sql_files = [
        line.strip()
        for line in raw_files.splitlines()
        if line.strip().endswith(".sql") and ("/criacao/B" in line or "/manutencao/V" in line)
    ]
    sql_files.sort(key=_migration_sort_key)
    if not sql_files:
        raise RuntimeError(f"Nenhuma migração Flyway encontrada em '{branch}:references/regime-regular/flyway/sql/'.")

    mem = sqlite3.connect(":memory:")
    for rel_path in sql_files:
        sql_bytes = subprocess.check_output(["git", "show", f"{branch}:{rel_path}"], cwd=ROOT_DIR)
        mem.execute("PRAGMA foreign_keys = OFF;")
        mem.executescript(sql_bytes.decode("utf-8"))
    return mem


def _replace_table(conn: sqlite3.Connection, table: str, insert_sql: str, rows: list[tuple]) -> int:
    conn.execute(f"DELETE FROM {table}")
    conn.executemany(insert_sql, rows)
    return len(rows)


def sync_rfb_tables(db_path: Path = DB_PATH, branch: str = "originals") -> dict[str, int]:
    """Sincroniza todas as tabelas oficiais da RFB no SQLite de referência."""
    mem = _load_rfb_memory_db(branch=branch)
    try:
        ufs_records = [
            (s.upper(), _format_uf_name(n), _DEFAULT_IBS_UF, _DEFAULT_CBS, "2026-01-01", None)
            for s, n in mem.execute("SELECT UF_SIGLA, UF_NOME FROM UF WHERE UF_SIGLA != 'EX' ORDER BY UF_SIGLA")
        ]
        cst_records = [
            (cst, c_class, desc.strip(), _format_pct(r_ibs, cst, ind), _format_pct(r_cbs, cst, ind), ini, fim)
            for cst, c_class, desc, r_ibs, r_cbs, ini, fim, ind in mem.execute(_SQL_CST_IBSCBS)
        ]
        ativ_records = [
            (cod.strip(), desc.strip(), sem_r, com_r, "2026-01-01", fim)
            for cod, desc, sem_r, com_r, fim in mem.execute(_SQL_ATIVIDADES_SIMPLES)
        ]
        redutor_records = [
            (int(rid), f"{float(val):.2f}", ini, fim)
            for rid, val, ini, fim in mem.execute(_SQL_REDUTOR_COMPRA_GOV)
        ]
        transf_records = [
            (int(tid), f"{float(val):.2f}", ini, fim)
            for tid, val, ini, fim in mem.execute(_SQL_TRANSFERENCIA_CBS)
        ]
        ncm_map: dict[tuple[str, str, str | None], list] = {}
        for ncm, desc, ad_val, ad_rem, ini, fim in (
            mem.execute(_SQL_NCM_IS_AD_VALOREM).fetchall()
            + mem.execute(_SQL_NCM_IS_AD_REM).fetchall()
        ):
            key = (ncm.strip(), ini, fim)
            entry = ncm_map.setdefault(key, [ncm.strip(), desc.strip(), None, None, ini, fim])
            if ad_val is not None:
                entry[2] = f"{float(ad_val):.2f}"
            if ad_rem is not None:
                entry[3] = f"{float(ad_rem):.2f}"
        ncm_is_records = [tuple(v) for v in sorted(ncm_map.values(), key=lambda r: (r[0], r[4]))]
        nbs_records = [
            (nbs.strip(), desc.strip(), lc116, c_class, ini, fim)
            for nbs, desc, lc116, c_class, ini, fim in mem.execute(_SQL_NBS_APLICAVEL)
        ]
        trat_records = [
            (int(tid), desc.strip(), e_al, e_ef, e_bc, e_tc, e_td, int(p_red), int(p_mono), ini, fim)
            for tid, desc, e_al, e_ef, e_bc, e_tc, e_td, p_red, p_mono, ini, fim in mem.execute(_SQL_TRATAMENTO_TRIBUTARIO)
        ]
    finally:
        mem.close()

    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    try:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        counts = {
            "ufs": _replace_table(
                conn, "uf_aliquota_referencia",
                "INSERT INTO uf_aliquota_referencia (uf, nome, aliquota_ibs_uf, aliquota_cbs, inicio_vigencia, fim_vigencia) VALUES (?, ?, ?, ?, ?, ?)",
                ufs_records,
            ),
            "cst_classificacao": _replace_table(
                conn, "cst_classificacao",
                "INSERT INTO cst_classificacao (cst, c_class_trib, descricao, aliquota_reducao_ibs, aliquota_reducao_cbs, inicio_vigencia, fim_vigencia) VALUES (?, ?, ?, ?, ?, ?, ?)",
                cst_records,
            ),
            "atividade_simples": _replace_table(
                conn, "atividade_simples",
                "INSERT INTO atividade_simples (codigo, descricao, anexo_sem_fator_r, anexo_com_fator_r, inicio_vigencia, fim_vigencia) VALUES (?, ?, ?, ?, ?, ?)",
                ativ_records,
            ),
            "redutor_compra_governamental": _replace_table(
                conn, "redutor_compra_governamental",
                "INSERT INTO redutor_compra_governamental (id, percentual_redutor, inicio_vigencia, fim_vigencia) VALUES (?, ?, ?, ?)",
                redutor_records,
            ),
            "transferencia_cbs_ente_gov": _replace_table(
                conn, "transferencia_cbs_ente_gov",
                "INSERT INTO transferencia_cbs_ente_gov (id, percentual_transferencia, inicio_vigencia, fim_vigencia) VALUES (?, ?, ?, ?)",
                transf_records,
            ),
            "ncm_imposto_seletivo": _replace_table(
                conn, "ncm_imposto_seletivo",
                "INSERT INTO ncm_imposto_seletivo (ncm, descricao, aliquota_ad_valorem, aliquota_ad_rem, inicio_vigencia, fim_vigencia) VALUES (?, ?, ?, ?, ?, ?)",
                ncm_is_records,
            ),
            "nbs_aplicavel": _replace_table(
                conn, "nbs_aplicavel",
                "INSERT INTO nbs_aplicavel (nbs, descricao, item_lc116, c_class_trib, inicio_vigencia, fim_vigencia) VALUES (?, ?, ?, ?, ?, ?)",
                nbs_records,
            ),
            "tratamento_tributario": _replace_table(
                conn, "tratamento_tributario",
                "INSERT INTO tratamento_tributario (id, descricao, expressao_aliquota, expressao_aliquota_efetiva, expressao_base_calculo, expressao_tributo_calculado, expressao_tributo_devido, possui_reducao, possui_monofasia, inicio_vigencia, fim_vigencia) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                trat_records,
            ),
        }
        conn.commit()
    finally:
        conn.close()
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Sincroniza tabelas oficiais da RFB para o SQLite local.")
    parser.add_argument("--branch", default="originals", help="Branch Git de origem das migrações RFB.")
    args = parser.parse_args()

    c = sync_rfb_tables(branch=args.branch)
    print(
        f"Sincronizado em {DB_PATH}: "
        f"{c['ufs']} UFs | {c['cst_classificacao']} CST | {c['atividade_simples']} cAtivSN | "
        f"{c['ncm_imposto_seletivo']} NCM IS | {c['nbs_aplicavel']} NBS | "
        f"{c['tratamento_tributario']} Tratamentos | {c['redutor_compra_governamental']} Redutor | "
        f"{c['transferencia_cbs_ente_gov']} Transf. CBS"
    )


if __name__ == "__main__":
    main()
