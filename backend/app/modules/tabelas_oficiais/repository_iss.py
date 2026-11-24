"""Consultas somente-leitura para ICMS modal (27 UFs) e ISS municipal (5 shards SQLite regionais)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
import sqlite3
from typing import Any

from app.core.database import readonly_session
from app.core.rounding import formatar_moeda
from app.core.transicao_rtc import obter_regra_transicao
from .seed import ensure_reference_db

_REGION_SHARDS: dict[str, tuple[str, str]] = {
    "1": ("Norte", "iss_norte.db"),
    "2": ("Nordeste", "iss_nordeste.db"),
    "3": ("Sudeste", "iss_sudeste.db"),
    "4": ("Sul", "iss_sul.db"),
    "5": ("Centro-Oeste", "iss_centro_oeste.db"),
}


def _open_iss_shard_readonly(codigo_ibge: int, db_path: Path | None = None) -> tuple[str | None, sqlite3.Connection | None]:
    """Abre em mode=ro o shard regional correspondente ao 1º dígito do código IBGE."""
    reg_key = str(codigo_ibge)[0] if codigo_ibge >= 1_000_000 else ""
    shard_info = _REGION_SHARDS.get(reg_key)
    if not shard_info:
        return None, None
    reg_nome, filename = shard_info
    db_dir: Path = ensure_reference_db(db_path).parent
    shard_path = db_dir / filename
    if not shard_path.exists():
        return reg_nome, None
    conn = sqlite3.connect(f"file:{shard_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return reg_nome, conn


def _normalizar_subitem_lc116(codigo: str) -> str:
    """Normaliza '1.07' ou '01.07' ou '01.07.01.000' para subitem '01.07'."""
    limpo = codigo.strip()
    partes = limpo.split(".")
    if len(partes) >= 2 and partes[0].isdigit() and partes[1].isdigit():
        return f"{int(partes[0]):02d}.{partes[1].zfill(2)}"
    return limpo


def listar_icms_ufs(
    data_fato_gerador: date | None = None,
    uf: str | None = None,
    db_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Lista alíquotas modais internas de ICMS por UF vigentes na data informada."""
    target = ensure_reference_db(db_path)
    ref = (data_fato_gerador or date.today()).isoformat()
    clauses = ["inicio_vigencia <= ?", "(fim_vigencia IS NULL OR fim_vigencia >= ?)"]
    params: list[Any] = [ref, ref]
    if uf:
        clauses.append("uf = ?")
        params.append(uf.upper().strip())

    sql = f"""
        SELECT uf, aliquota_interna, aliquota_fcp, inicio_vigencia, fim_vigencia, fundamentacao
        FROM icms_aliquota_uf
        WHERE {' AND '.join(clauses)}
        ORDER BY uf
    """
    with readonly_session(target) as conn:
        rows = conn.execute(sql, params).fetchall()
    result: list[dict[str, Any]] = []
    for r in rows:
        item = dict(r)
        total = Decimal(item["aliquota_interna"]) + Decimal(item["aliquota_fcp"])
        item["aliquota_total"] = formatar_moeda(total)
        result.append(item)
    return result


def obter_icms_uf(
    uf: str,
    data_fato_gerador: date | None = None,
    db_path: Path | None = None,
) -> dict[str, Any] | None:
    """Retorna a alíquota modal interna de ICMS vigente de uma UF específica."""
    itens = listar_icms_ufs(data_fato_gerador=data_fato_gerador, uf=uf, db_path=db_path)
    return itens[0] if itens else None


def listar_iss_servicos(
    q: str | None = None,
    limit: int = 100,
    db_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Lista códigos cTribNac / subitens LC 116 do catálogo oficial de serviços ISS."""
    target = ensure_reference_db(db_path)
    clauses: list[str] = []
    params: list[Any] = []
    if q:
        termo = q.strip()
        sub = _normalizar_subitem_lc116(termo)
        clauses.append("(codigo_ctribnac LIKE ? OR subitem_lc116 LIKE ? OR LOWER(descricao) LIKE LOWER(?))")
        params.extend([f"{termo}%", f"{sub}%", f"%{termo}%"])
    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f"""
        SELECT id, codigo_ctribnac, subitem_lc116, descricao
        FROM iss_servicos_catalogo
        {where_sql}
        ORDER BY codigo_ctribnac
        LIMIT ?
    """
    params.append(limit)
    with readonly_session(target) as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def _resolver_servicos_alvo(codigo_servico: str, target: Path) -> list[dict[str, Any]]:
    """Resolve código cTribNac completo (01.01.01.000) ou subitem LC 116 (01.01 / 1.01)."""
    limpo = codigo_servico.strip()
    sub = _normalizar_subitem_lc116(limpo)
    with readonly_session(target) as conn:
        exato = conn.execute(
            "SELECT id, codigo_ctribnac, subitem_lc116, descricao FROM iss_servicos_catalogo WHERE codigo_ctribnac = ?",
            (limpo,),
        ).fetchall()
        if exato:
            return [dict(r) for r in exato]
        por_sub = conn.execute(
            """
            SELECT id, codigo_ctribnac, subitem_lc116, descricao
            FROM iss_servicos_catalogo
            WHERE subitem_lc116 = ?
            ORDER BY codigo_ctribnac
            """,
            (sub,),
        ).fetchall()
        return [dict(r) for r in por_sub]


def _obter_info_municipio(codigo_ibge: int, target: Path) -> dict[str, Any] | None:
    with readonly_session(target) as conn:
        row = conn.execute(
            "SELECT codigo_ibge, nome, uf_sigla FROM localidades_ibge WHERE codigo_ibge = ?",
            (codigo_ibge,),
        ).fetchone()
    return dict(row) if row else None


def obter_iss_municipal(
    codigo_ibge: int,
    codigo_servico: str,
    data_fato_gerador: date | None = None,
    db_path: Path | None = None,
) -> dict[str, Any]:
    """Consulta a alíquota municipal de ISS no shard SQLite da região correspondente ao IBGE."""
    target = ensure_reference_db(db_path)
    ref_date = data_fato_gerador or date.today()
    ref_iso = ref_date.isoformat()
    regra = obter_regra_transicao(ref_date)
    mun_info = _obter_info_municipio(codigo_ibge, target)
    reg_nome, shard_conn = _open_iss_shard_readonly(codigo_ibge, target)

    base_resp: dict[str, Any] = {
        "codigo_ibge": codigo_ibge,
        "municipio_nome": mun_info["nome"] if mun_info else None,
        "uf": mun_info["uf_sigla"] if mun_info else None,
        "regiao": reg_nome,
        "codigo_servico_consultado": codigo_servico.strip(),
        "data_fato_gerador": ref_iso,
        "encontrado": False,
        "municipio_parametrizado": False,
        "origem": "nao_parametrizado",
        "aliquota_iss": None,
        "codigo_ctribnac": None,
        "subitem_lc116": None,
        "descricao_servico": None,
        "inicio_vigencia": None,
        "fim_vigencia": None,
        "mensagem": "Município não parametrizado no Portal Nacional da NFS-e. Informe a alíquota manualmente (2% a 5%).",
        "regra_transicao": regra.to_dict(),
    }

    if shard_conn is None:
        base_resp["mensagem"] = "Base regional de ISS indisponível para o código IBGE informado. Insira a alíquota manualmente."
        return base_resp

    try:
        cobertura = shard_conn.execute(
            "SELECT total_regras FROM iss_municipios_cobertura WHERE codigo_ibge = ?",
            (codigo_ibge,),
        ).fetchone()
        if not cobertura:
            return base_resp

        base_resp["municipio_parametrizado"] = True
        servicos = _resolver_servicos_alvo(codigo_servico, target)
        if not servicos:
            base_resp["origem"] = "servico_nao_encontrado"
            base_resp["mensagem"] = f"Código de serviço '{codigo_servico}' não encontrado no catálogo LC 116 / cTribNac."
            return base_resp

        serv_map = {s["id"]: s for s in servicos}
        placeholders = ",".join("?" for _ in serv_map)
        row = shard_conn.execute(
            f"""
            SELECT servico_id, aliquota_bps, inicio_vigencia, fim_vigencia
            FROM iss_aliquotas
            WHERE codigo_ibge = ?
              AND servico_id IN ({placeholders})
              AND inicio_vigencia <= ?
              AND (fim_vigencia IS NULL OR fim_vigencia >= ?)
            ORDER BY inicio_vigencia DESC, servico_id ASC
            LIMIT 1
            """,
            [codigo_ibge, *serv_map.keys(), ref_iso, ref_iso],
        ).fetchone()

        if not row:
            base_resp["origem"] = "servico_sem_regra_vigente"
            base_resp["codigo_ctribnac"] = servicos[0]["codigo_ctribnac"]
            base_resp["subitem_lc116"] = servicos[0]["subitem_lc116"]
            base_resp["descricao_servico"] = servicos[0]["descricao"]
            base_resp["mensagem"] = (
                f"Município parametrizado, mas sem regra vigente para o serviço '{codigo_servico}' em {ref_iso}. "
                "Informe a alíquota manualmente (2% a 5%)."
            )
            return base_resp

        serv = serv_map[int(row["servico_id"])]
        aliq_dec = Decimal(int(row["aliquota_bps"])) / Decimal("100")
        base_resp.update(
            {
                "encontrado": True,
                "origem": "portal_nfse",
                "aliquota_iss": formatar_moeda(aliq_dec),
                "codigo_ctribnac": serv["codigo_ctribnac"],
                "subitem_lc116": serv["subitem_lc116"],
                "descricao_servico": serv["descricao"],
                "inicio_vigencia": row["inicio_vigencia"],
                "fim_vigencia": row["fim_vigencia"],
                "mensagem": "Alíquota oficial obtida do Portal Nacional da NFS-e.",
            }
        )
        return base_resp
    finally:
        shard_conn.close()
