"""Rotas FastAPI para o módulo Regime Regular (/regime-regular)."""

from fastapi import APIRouter, HTTPException

from .base_calculo import (
    BaseCalculoCibsRequest,
    BaseCalculoISMercadoriasRequest,
    BaseCalculoResponse,
    CampoInvalidoError,
    calcular_base_cibs,
    calcular_base_is_mercadorias,
)
from .operacao import (
    OperacaoRegimeRegularRequest,
    OperacaoRegimeRegularResponse,
    calcular_operacao_regime_regular,
)
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


@router.post(
    "/base-calculo/cbs-ibs",
    response_model=BaseCalculoResponse,
    summary="Apurar Base de Cálculo CBS/IBS (Regime Regular RFB)",
)
def endpoint_base_calculo_cibs(payload: BaseCalculoCibsRequest) -> BaseCalculoResponse:
    """Calcula a base de cálculo de CBS/IBS validando vigência de tributos legados."""
    try:
        return calcular_base_cibs(payload)
    except CampoInvalidoError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post(
    "/base-calculo/is-mercadorias",
    response_model=BaseCalculoResponse,
    summary="Apurar Base de Cálculo IS Mercadorias (Regime Regular RFB)",
)
def endpoint_base_calculo_is(payload: BaseCalculoISMercadoriasRequest) -> BaseCalculoResponse:
    """Calcula a base de cálculo do Imposto Seletivo sobre mercadorias."""
    try:
        return calcular_base_is_mercadorias(payload)
    except CampoInvalidoError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post(
    "/calcular-operacao",
    response_model=OperacaoRegimeRegularResponse,
    summary="Calcular operação com múltiplos itens, redução CST e diferimento",
)
def endpoint_calcular_operacao_regime_regular(
    payload: OperacaoRegimeRegularRequest,
) -> OperacaoRegimeRegularResponse:
    """Calcula múltiplos itens no Regime Regular com totalização sem arredondamento intermediário."""
    return calcular_operacao_regime_regular(payload)

