"""Rotas FastAPI para o módulo Simples Nacional (/simples)."""

from fastapi import APIRouter

from .schemas import (
    SimplesCalculoRequest,
    SimplesCalculoResponse,
    SimplesItemCalculoRequest,
    SimplesItemCalculoResponse,
)
from .service import calcular_item_simples_api, calcular_simples

router = APIRouter(prefix="/simples", tags=["Simples Nacional"])


@router.get("/info", summary="Metadados do módulo Simples Nacional")
def info_simples() -> dict[str, str]:
    """Retorna informações de status e referência do módulo Simples Nacional."""
    return {
        "modulo": "simples",
        "status": "ready",
        "referencia_rfb": "https://github.com/ReceitaFederal/calculadora-rtc-simples-nacional",
    }


@router.post(
    "/calcular",
    response_model=SimplesCalculoResponse,
    summary="Calcular tributos no Simples Nacional (RTC)",
)
def endpoint_calcular_simples(payload: SimplesCalculoRequest) -> SimplesCalculoResponse:
    """Calcula DAS e parcela estimada de IBS/CBS no Simples Nacional."""
    return calcular_simples(payload)


@router.post(
    "/calcular-item",
    response_model=SimplesItemCalculoResponse,
    summary="Calcular item no Simples Nacional (NT 2026.005 v1.00)",
)
def endpoint_calcular_item_simples(
    payload: SimplesItemCalculoRequest,
) -> SimplesItemCalculoResponse:
    """Executa o motor oficial de cálculo por item (CRT, tpRBSN, compra governamental)."""
    return calcular_item_simples_api(payload)

