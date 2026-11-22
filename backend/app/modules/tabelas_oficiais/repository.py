"""Repositório somente-leitura para consulta às tabelas oficiais por vigência."""

from datetime import date
from pathlib import Path
from typing import Any

from app.core.database import readonly_session
from .seed import ensure_reference_db


def _vigencia_clause() -> str:
    return "inicio_vigencia <= ? AND (fim_vigencia IS NULL OR fim_vigencia >= ?)"


def listar_cst_classificacao(
    data_fato_gerador: date,
    cst: str | None = None,
    q: str | None = None,
    db_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Lista classificações CST/cClassTrib vigentes na data do fato gerador."""
    target = ensure_reference_db(db_path)
    data_iso = data_fato_gerador.isoformat()
    query = f"""
        SELECT cst, c_class_trib, descricao, aliquota_reducao_ibs, aliquota_reducao_cbs,
               inicio_vigencia, fim_vigencia
        FROM cst_classificacao
        WHERE {_vigencia_clause()}
    """
    params: list[Any] = [data_iso, data_iso]
    if cst:
        query += " AND cst = ?"
        params.append(cst)
    if q and q.strip():
        termo = f"%{q.strip()}%"
        query += " AND (c_class_trib LIKE ? OR descricao LIKE ?)"
        params.extend([termo, termo])
    query += " ORDER BY cst, c_class_trib"

    with readonly_session(target) as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def listar_atividades_simples(
    data_fato_gerador: date,
    db_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Lista atividades cAtivSN vigentes na data do fato gerador."""
    target = ensure_reference_db(db_path)
    data_iso = data_fato_gerador.isoformat()
    query = f"""
        SELECT codigo, descricao, anexo_sem_fator_r, anexo_com_fator_r,
               inicio_vigencia, fim_vigencia
        FROM atividade_simples
        WHERE {_vigencia_clause()}
        ORDER BY codigo
    """
    with readonly_session(target) as conn:
        rows = conn.execute(query, [data_iso, data_iso]).fetchall()
    return [dict(row) for row in rows]


def obter_fator_compra_gov_simples(
    data_fato_gerador: date,
    db_path: Path | None = None,
) -> dict[str, Any] | None:
    """Obtém o fator de transição CBS→IBS vigente para compras governamentais no Simples."""
    target = ensure_reference_db(db_path)
    data_iso = data_fato_gerador.isoformat()
    query = f"""
        SELECT id, fator, inicio_vigencia, fim_vigencia
        FROM transicao_compra_gov_simples
        WHERE {_vigencia_clause()}
        LIMIT 1
    """
    with readonly_session(target) as conn:
        row = conn.execute(query, [data_iso, data_iso]).fetchone()
    return dict(row) if row else None


def listar_ufs_referencia(
    data_fato_gerador: date,
    db_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Lista alíquotas de referência por UF vigentes na data do fato gerador."""
    target = ensure_reference_db(db_path)
    data_iso = data_fato_gerador.isoformat()
    query = f"""
        SELECT uf, nome, aliquota_ibs_uf, aliquota_cbs, inicio_vigencia, fim_vigencia
        FROM uf_aliquota_referencia
        WHERE {_vigencia_clause()}
        ORDER BY uf
    """
    with readonly_session(target) as conn:
        rows = conn.execute(query, [data_iso, data_iso]).fetchall()
    return [dict(row) for row in rows]


def buscar_localidades_ibge(
    uf: str | None = None,
    nome: str | None = None,
    codigo: int | None = None,
    limit: int = 50,
    db_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Consulta municípios IBGE no catálogo oficial somente-leitura."""
    target = ensure_reference_db(db_path)
    query = "SELECT codigo_ibge, nome, uf_codigo, uf_sigla FROM localidades_ibge WHERE 1=1"
    params: list[Any] = []
    if codigo is not None:
        query += " AND codigo_ibge = ?"
        params.append(codigo)
    if uf:
        query += " AND uf_sigla = ?"
        params.append(uf.upper())
    if nome:
        query += " AND nome LIKE ?"
        params.append(f"%{nome}%")
    query += " ORDER BY uf_sigla, nome LIMIT ?"
    params.append(limit)

    with readonly_session(target) as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]
