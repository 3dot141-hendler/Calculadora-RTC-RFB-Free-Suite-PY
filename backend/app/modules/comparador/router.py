"""Rotas FastAPI para o Comparador Tributário (Simples/Híbrido/Regular e Presumido vs. Real)."""

from fastapi import APIRouter

from .schemas import ComparadorRequest, ComparadorResponse
from .schemas_presumido_real import (
    ComparadorPresumidoRealRequest,
    ComparadorPresumidoRealResponse,
)
from .service import simular_comparativo_regimes, simular_presumido_vs_real

router = APIRouter(prefix="/comparador", tags=["Comparador Tributário"])


@router.post(
    "/simular",
    response_model=ComparadorResponse,
    summary="Comparar Simples Nacional (DAS), Simples Híbrido e Regime Regular lado a lado",
)
def simular_comparativo(payload: ComparadorRequest) -> ComparadorResponse:
    """Executa simulação comparativa para empresas até R$ 4,8 mi/ano (carga própria e crédito B2B)."""
    return simular_comparativo_regimes(payload)


@router.post(
    "/presumido-vs-real",
    response_model=ComparadorPresumidoRealResponse,
    summary="Comparar Lucro Presumido vs. Lucro Real (+ IBS/CBS no Regime Regular)",
)
def simular_comparativo_presumido_real(
    payload: ComparadorPresumidoRealRequest,
) -> ComparadorPresumidoRealResponse:
    """Compara IRPJ, Adicional 10%, CSLL e IBS/CBS para empresas acima de R$ 4,8 mi/ano ou em geral."""
    return simular_presumido_vs_real(payload)
