"""Rotas FastAPI para o Comparador Tributário (Simples vs. Híbrido vs. Regime Regular)."""

from fastapi import APIRouter

from .schemas import ComparadorRequest, ComparadorResponse
from .service import simular_comparativo_regimes

router = APIRouter(prefix="/comparador", tags=["Comparador Tributário"])


@router.post(
    "/simular",
    response_model=ComparadorResponse,
    summary="Comparar Simples Nacional (DAS), Simples Híbrido e Regime Regular lado a lado",
)
def simular_comparativo(payload: ComparadorRequest) -> ComparadorResponse:
    """Executa simulação comparativa de carga tributária e geração de crédito B2B."""
    return simular_comparativo_regimes(payload)
