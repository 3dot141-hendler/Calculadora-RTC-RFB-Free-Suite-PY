"""Rotas FastAPI para o módulo Regime Regular (/regime-regular)."""

from fastapi import APIRouter

from .schemas import RegimeRegularCalculoRequest, RegimeRegularCalculoResponse
from .service import calcular_regime_regular

router = APIRouter(prefix="/regime-regular", tags=["Regime Regular"])


@router.get("/info", summary="Metadados do módulo Regime Regular")
def info_regime_regular() -> dict[str, str]:
    """Retorna informações de status e referência do módulo Regime Regular."""
    return {
        "modulo": "regime-regular",
        "status": "ready",
        "referencia_rfb": "https://github.com/ReceitaFederal/calculadora-rtc-regime-regular",
    }


@router.post(
    "/calcular",
    response_model=RegimeRegularCalculoResponse,
    summary="Calcular IBS, CBS e IS no Regime Regular",
)
def endpoint_calcular_regime_regular(
    payload: RegimeRegularCalculoRequest,
) -> RegimeRegularCalculoResponse:
    """Executa simulação de cálculo no Regime Regular da Reforma Tributária."""
    return calcular_regime_regular(payload)

