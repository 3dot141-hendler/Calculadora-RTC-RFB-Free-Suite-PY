"""Consultas somente-leitura para NCM (Imposto Seletivo), NBS e Tratamento Tributário."""

from datetime import date
from pathlib import Path
from typing import Any

from app.core.database import readonly_session
from .seed import ensure_reference_db


def _vigencia_clause() -> str:
    return "inicio_vigencia <= ? AND (fim_vigencia IS NULL OR fim_vigencia >= ?)"


def listar_ncm_imposto_seletivo(
    data_fato_gerador: date,
    ncm: str | None = None,
    q: str | None = None,
    limit: int = 50,
    db_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Lista NCMs sujeitos ao Imposto Seletivo (Ad Valorem / Ad Rem) vigentes na data."""
    target = ensure_reference_db(db_path)
    data_iso = data_fato_gerador.isoformat()
    query = f"""
        SELECT ncm, descricao, aliquota_ad_valorem, aliquota_ad_rem,
               inicio_vigencia, fim_vigencia
        FROM ncm_imposto_seletivo
        WHERE {_vigencia_clause()}
    """
    params: list[Any] = [data_iso, data_iso]
    if ncm and ncm.strip():
        query += " AND ncm LIKE ?"
        params.append(f"{ncm.strip()}%")
    if q and q.strip():
        termo = f"%{q.strip()}%"
        query += " AND (ncm LIKE ? OR descricao LIKE ?)"
        params.extend([termo, termo])
    query += " ORDER BY ncm LIMIT ?"
    params.append(limit)

    with readonly_session(target) as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def listar_nbs_aplicavel(
    data_fato_gerador: date,
    nbs: str | None = None,
    q: str | None = None,
    limit: int = 50,
    db_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Lista códigos NBS aplicáveis vinculados a cClassTrib vigentes na data."""
    target = ensure_reference_db(db_path)
    data_iso = data_fato_gerador.isoformat()
    query = f"""
        SELECT nbs, descricao, item_lc116, c_class_trib,
               inicio_vigencia, fim_vigencia
        FROM nbs_aplicavel
        WHERE {_vigencia_clause()}
    """
    params: list[Any] = [data_iso, data_iso]
    if nbs and nbs.strip():
        query += " AND nbs LIKE ?"
        params.append(f"{nbs.strip()}%")
    if q and q.strip():
        termo = f"%{q.strip()}%"
        query += " AND (nbs LIKE ? OR descricao LIKE ? OR c_class_trib LIKE ?)"
        params.extend([termo, termo, termo])
    query += " ORDER BY nbs LIMIT ?"
    params.append(limit)

    with readonly_session(target) as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def listar_tratamentos_tributarios(
    data_fato_gerador: date,
    q: str | None = None,
    limit: int = 50,
    db_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Lista a matriz oficial TRATAMENTO_TRIBUTARIO (expressões ADR001) vigente na data."""
    target = ensure_reference_db(db_path)
    data_iso = data_fato_gerador.isoformat()
    query = f"""
        SELECT id, descricao, expressao_aliquota, expressao_aliquota_efetiva,
               expressao_base_calculo, expressao_tributo_calculado, expressao_tributo_devido,
               possui_reducao, possui_monofasia, inicio_vigencia, fim_vigencia
        FROM tratamento_tributario
        WHERE {_vigencia_clause()}
    """
    params: list[Any] = [data_iso, data_iso]
    if q and q.strip():
        termo = f"%{q.strip()}%"
        query += " AND (descricao LIKE ? OR expressao_tributo_calculado LIKE ?)"
        params.extend([termo, termo])
    query += " ORDER BY id LIMIT ?"
    params.append(limit)

    with readonly_session(target) as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]
