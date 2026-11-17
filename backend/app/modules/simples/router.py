"""Rotas FastAPI para o módulo Simples Nacional (/simples)."""

from fastapi import APIRouter

from .schemas import SimplesCalculoRequest, SimplesCalculoResponse
from .service import calcular_simples

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

