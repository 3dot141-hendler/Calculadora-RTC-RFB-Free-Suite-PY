"""Sincroniza 27 UFs, CST/cClassTrib (LC 214/2025) e cAtivSN (NT 2026.005) de `originals` para SQLite.

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
    ATSN_CATIVSN AS codigo,
    ATSN_DESCRICAO AS descricao,
    ATSN_ANEXO_SEM_FATOR_R AS anexo_sem_fator_r,
    ATSN_ANEXO_COM_FATOR_R AS anexo_com_fator_r,
    ATSN_FIM_VIGENCIA AS fim_vigencia
FROM ATIVIDADE_SIMPLES_NACIONAL
WHERE ATSN_CATIVSN IS NOT NULL
ORDER BY ATSN_ORDEM
"""


def _format_uf_name(raw_name: str) -> str:
    """Converte nome da UF em MAIÚSCULAS para Title Case PT-BR (ex.: Rio Grande do Sul)."""
    words = raw_name.strip().split()
    formatted: list[str] = []
    for idx, word in enumerate(words):
        if idx > 0 and word.upper() in _LOWERCASE_PREPOSITIONS:
            formatted.append(word.lower())
        else:
            formatted.append(word.capitalize())
    return " ".join(formatted)


def _format_pct(value: float | None, cst: str, ind_gibscbs: int) -> str:
    """Formata percentual de redução com 2 casas; isenção/imunidade (CST 400/410) = 100.00."""
    if cst in {"400", "410"} and ind_gibscbs == 0:
        return "100.00"
    if value is not None:
        return f"{float(value):.2f}"
    return "0.00"


def _migration_sort_key(path: str) -> tuple[int, int]:
    name = path.rsplit("/", 1)[-1]
    if name.startswith("B"):
        match = re.search(r"B(\d+)", name)
        return (0, int(match.group(1)) if match else 0)
    match = re.search(r"V(\d+)", name)
    return (1, int(match.group(1)) if match else 0)


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


def sync_rfb_tables(db_path: Path = DB_PATH, branch: str = "originals") -> dict[str, int]:
    """Sincroniza 27 UFs, CST/cClassTrib e cAtivSN no banco SQLite de referência."""
    mem = _load_rfb_memory_db(branch=branch)
    try:
        uf_rows = mem.execute(
            "SELECT UF_SIGLA, UF_NOME FROM UF WHERE UF_SIGLA != 'EX' ORDER BY UF_SIGLA"
        ).fetchall()
        ufs_records = [
            (sigla.upper(), _format_uf_name(nome), _DEFAULT_IBS_UF, _DEFAULT_CBS, "2026-01-01", None)
            for sigla, nome in uf_rows
        ]

        cst_rows = mem.execute(_SQL_CST_IBSCBS).fetchall()
        cst_records = [
            (
                cst,
                c_class_trib,
                descricao.strip(),
                _format_pct(red_ibs, cst, ind_gibscbs),
                _format_pct(red_cbs, cst, ind_gibscbs),
                inicio_vigencia,
                fim_vigencia,
            )
            for cst, c_class_trib, descricao, red_ibs, red_cbs, inicio_vigencia, fim_vigencia, ind_gibscbs in cst_rows
        ]

        ativ_rows = mem.execute(_SQL_ATIVIDADES_SIMPLES).fetchall()
        ativ_records = [
            (
                codigo.strip(),
                descricao.strip(),
                anexo_sem_fator_r,
                anexo_com_fator_r,
                "2026-01-01",
                fim_vigencia,
            )
            for codigo, descricao, anexo_sem_fator_r, anexo_com_fator_r, fim_vigencia in ativ_rows
        ]
    finally:
        mem.close()

    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    try:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        conn.execute("DELETE FROM uf_aliquota_referencia")
        conn.executemany(
            """
            INSERT INTO uf_aliquota_referencia
                (uf, nome, aliquota_ibs_uf, aliquota_cbs, inicio_vigencia, fim_vigencia)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ufs_records,
        )

        conn.execute("DELETE FROM cst_classificacao")
        conn.executemany(
            """
            INSERT INTO cst_classificacao
                (cst, c_class_trib, descricao, aliquota_reducao_ibs, aliquota_reducao_cbs, inicio_vigencia, fim_vigencia)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            cst_records,
        )

        conn.execute("DELETE FROM atividade_simples")
        conn.executemany(
            """
            INSERT INTO atividade_simples
                (codigo, descricao, anexo_sem_fator_r, anexo_com_fator_r, inicio_vigencia, fim_vigencia)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ativ_records,
        )

        conn.commit()
    finally:
        conn.close()

    return {
        "ufs": len(ufs_records),
        "cst_classificacao": len(cst_records),
        "atividade_simples": len(ativ_records),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Sincroniza tabelas oficiais da RFB para o SQLite local.")
    parser.add_argument("--branch", default="originals", help="Branch Git de origem das migrações RFB.")
    args = parser.parse_args()

    counts = sync_rfb_tables(branch=args.branch)
    print(
        f"Sincronizado em {DB_PATH}: "
        f"{counts['ufs']} UFs | "
        f"{counts['cst_classificacao']} CST/cClassTrib | "
        f"{counts['atividade_simples']} atividades cAtivSN"
    )


if __name__ == "__main__":
    main()
