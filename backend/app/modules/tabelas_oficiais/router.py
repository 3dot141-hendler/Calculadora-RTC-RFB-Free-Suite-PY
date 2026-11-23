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
from .repository_avancado import (
    listar_nbs_aplicavel,
    listar_ncm_imposto_seletivo,
    listar_tratamentos_tributarios,
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


@router.get("/ncm-is", summary="Consultar NCMs sujeitos ao Imposto Seletivo (Ad Valorem / Ad Rem)")
def endpoint_listar_ncm_is(
    data_fato_gerador: date = Query(default=date(2027, 1, 1)),
    ncm: str | None = Query(default=None, min_length=2, max_length=8),
    q: str | None = Query(default=None, min_length=1, max_length=80),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[dict[str, Any]]:
    """Lista NCMs oficiais do Imposto Seletivo vigentes na data informada (início 2027)."""
    return listar_ncm_imposto_seletivo(
        data_fato_gerador=data_fato_gerador, ncm=ncm, q=q, limit=limit
    )


@router.get("/nbs", summary="Consultar códigos NBS aplicáveis (serviços LC 214/2025)")
def endpoint_listar_nbs(
    data_fato_gerador: date = Query(default=date(2026, 1, 1)),
    nbs: str | None = Query(default=None, min_length=2, max_length=12),
    q: str | None = Query(default=None, min_length=1, max_length=80),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[dict[str, Any]]:
    """Lista códigos NBS aplicáveis vinculados a classificações cClassTrib vigentes."""
    return listar_nbs_aplicavel(data_fato_gerador=data_fato_gerador, nbs=nbs, q=q, limit=limit)


@router.get("/tratamentos-tributarios", summary="Consultar matriz TRATAMENTO_TRIBUTARIO (ADR001)")
def endpoint_listar_tratamentos(
    data_fato_gerador: date = Query(default=date(2026, 1, 1)),
    q: str | None = Query(default=None, min_length=1, max_length=80),
    limit: int = Query(default=50, ge=1, le=100),
) -> list[dict[str, Any]]:
    """Lista as expressões tributárias oficiais da tabela TRATAMENTO_TRIBUTARIO da RFB."""
    return listar_tratamentos_tributarios(data_fato_gerador=data_fato_gerador, q=q, limit=limit)
