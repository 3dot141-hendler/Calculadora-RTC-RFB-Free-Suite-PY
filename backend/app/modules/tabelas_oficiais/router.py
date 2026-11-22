"""Rotas FastAPI para consulta às tabelas oficiais vigentes (/tabelas)."""

from datetime import date
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from .repository import (
    buscar_localidades_ibge,
    listar_atividades_simples,
    listar_cst_classificacao,
    listar_ufs_referencia,
    obter_fator_compra_gov_simples,
)

router = APIRouter(prefix="/tabelas", tags=["Tabelas Oficiais (RFB)"])


@router.get("/cst", summary="Consultar CST e cClassTrib vigentes")
def endpoint_listar_cst(
    data_fato_gerador: date = Query(default=date(2026, 1, 1)),
    cst: str | None = Query(default=None, min_length=3, max_length=3),
    q: str | None = Query(default=None, min_length=1, max_length=80),
) -> list[dict[str, Any]]:
    """Lista classificações tributárias CST/cClassTrib vigentes na data informada."""
    return listar_cst_classificacao(data_fato_gerador=data_fato_gerador, cst=cst, q=q)


@router.get("/atividades-simples", summary="Consultar atividades cAtivSN vigentes")
def endpoint_listar_atividades_simples(
    data_fato_gerador: date = Query(default=date(2026, 1, 1)),
) -> list[dict[str, Any]]:
    """Lista atividades do Simples Nacional vigentes na data do fato gerador."""
    return listar_atividades_simples(data_fato_gerador=data_fato_gerador)


@router.get("/compra-gov-simples", summary="Consultar fator de transição compra gov (Simples)")
def endpoint_fator_compra_gov(
    data_fato_gerador: date = Query(default=date(2026, 1, 1)),
) -> dict[str, Any]:
    """Retorna o fator de deslocamento CBS→IBS vigente para tpEnteGov ∈ {2,3,4}."""
    registro = obter_fator_compra_gov_simples(data_fato_gerador=data_fato_gerador)
    if not registro:
        raise HTTPException(
            status_code=404,
            detail=f"Nenhum fator de transição vigente encontrado para {data_fato_gerador.isoformat()}.",
        )
    return registro


@router.get("/ufs", summary="Consultar alíquotas de referência por UF")
def endpoint_listar_ufs(
    data_fato_gerador: date = Query(default=date(2026, 1, 1)),
) -> list[dict[str, Any]]:
    """Lista alíquotas de referência de IBS Estadual e CBS por UF."""
    return listar_ufs_referencia(data_fato_gerador=data_fato_gerador)


@router.get("/localidades", summary="Consultar municípios IBGE (catálogo DANFSE)")
def endpoint_buscar_localidades(
    uf: str | None = Query(default=None, min_length=2, max_length=2),
    nome: str | None = Query(default=None, min_length=2),
    codigo: int | None = Query(default=None, ge=1000000),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[dict[str, Any]]:
    """Consulta municípios IBGE por UF, nome ou código de 7 dígitos."""
    return buscar_localidades_ibge(uf=uf, nome=nome, codigo=codigo, limit=limit)
