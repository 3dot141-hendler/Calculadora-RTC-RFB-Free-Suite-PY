"""Rotas HTTP do módulo Regime Regular (IBS/CBS/IS)."""

from fastapi import APIRouter, HTTPException

from .base_calculo import (
    BaseCalculoCibsRequest,
    BaseCalculoISMercadoriasRequest,
    BaseCalculoResponse,
    calcular_base_cibs,
    calcular_base_is_mercadorias,
)
from .base_unificada import (
    BaseCalculoUnificadaRequest,
    BaseCalculoUnificadaResponse,
    calcular_base_unificada,
)
from .base_unificada_nfse import (
    BaseCalculoUnificadaNfseRequest,
    BaseCalculoUnificadaNfseResponse,
    calcular_base_unificada_nfse,
)
from .expressao_engine import (
    FORMULAS_OFICIAIS_REFERENCIA,
    ExpressaoAvaliacaoRequest,
    ExpressaoAvaliacaoResponse,
    ExpressaoInvalidaError,
    executar_avaliacao_expressao,
)
from .operacao import (
    OperacaoRegimeRegularRequest,
    OperacaoRegimeRegularResponse,
    calcular_operacao_regime_regular,
)
from .schemas import RegimeRegularCalculoRequest, RegimeRegularCalculoResponse
from .service import calcular_regime_regular

router = APIRouter(prefix="/regime-regular", tags=["Regime Regular (IBS / CBS / IS)"])


@router.get("/info", summary="Informações do motor Regime Regular")
def info_regime_regular() -> dict[str, object]:
    """Descreve as capacidades do motor de cálculo do Regime Regular."""
    return {
        "modulo": "regime_regular",
        "descricao": (
            "Cálculo do Regime Regular (IBS/CBS/IS), Base Unificada NF-e/NFC-e e NFS-e/Locação, "
            "crédito presumido, redução de base, compra governamental e avaliador ADR001."
        ),
        "referencia": "LC 214/2025 + RFB RTC (V0019 / ADR001 / BaseCalculoUnificada)",
        "endpoints": [
            "/api/v1/regime-regular/calcular",
            "/api/v1/regime-regular/calcular-operacao",
            "/api/v1/regime-regular/base-calculo/cbs-ibs",
            "/api/v1/regime-regular/base-calculo/is-mercadorias",
            "/api/v1/regime-regular/base-calculo/unificada",
            "/api/v1/regime-regular/base-calculo/unificada-nfse",
            "/api/v1/regime-regular/expressao/avaliar",
            "/api/v1/regime-regular/expressao/formulas",
        ],
    }


@router.post("/calcular", response_model=RegimeRegularCalculoResponse, summary="Calcula IBS, CBS e IS")
def post_calcular_regime_regular(payload: RegimeRegularCalculoRequest) -> RegimeRegularCalculoResponse:
    """Executa o cálculo tributário do Regime Regular com arredondamento ROUND_HALF_EVEN."""
    return calcular_regime_regular(payload)


@router.post(
    "/base-calculo/cbs-ibs",
    response_model=BaseCalculoResponse,
    summary="Calcula Base de Cálculo CBS/IBS (legado RFB)",
)
def post_base_calculo_cibs(payload: BaseCalculoCibsRequest) -> BaseCalculoResponse:
    """Apura a base de cálculo CBS/IBS validando a extinção de tributos legados."""
    try:
        return calcular_base_cibs(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post(
    "/base-calculo/is-mercadorias",
    response_model=BaseCalculoResponse,
    summary="Calcula Base de Cálculo do Imposto Seletivo (Mercadorias)",
)
def post_base_calculo_is(payload: BaseCalculoISMercadoriasRequest) -> BaseCalculoResponse:
    """Apura a base de cálculo do IS validando a vigência dos tributos excluídos."""
    try:
        return calcular_base_is_mercadorias(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post(
    "/base-calculo/unificada",
    response_model=BaseCalculoUnificadaResponse,
    summary="Calcula Base de Cálculo Unificada (RG/IBS-CBS, IS e SN) para NF-e/NFC-e",
)
def post_base_calculo_unificada(
    payload: BaseCalculoUnificadaRequest,
) -> BaseCalculoUnificadaResponse:
    """Executa o cálculo unificado das três bases (RG, IS, SN) conforme catálogo RFB."""
    try:
        return calcular_base_unificada(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post(
    "/base-calculo/unificada-nfse",
    response_model=BaseCalculoUnificadaNfseResponse,
    summary="Calcula Base de Cálculo Unificada NFS-e / Salão Parceiro / Locação 99.03",
)
def post_base_calculo_unificada_nfse(
    payload: BaseCalculoUnificadaNfseRequest,
) -> BaseCalculoUnificadaNfseResponse:
    """Executa o cálculo unificado de bases NFS-e (IBS/CBS + Simples Nacional + Locação 99.03)."""
    try:
        return calcular_base_unificada_nfse(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post(
    "/calcular-operacao",
    response_model=OperacaoRegimeRegularResponse,
    summary="Calcula operação multi-itens com redução, crédito presumido, compra gov e diferimento",
)
def post_calcular_operacao(payload: OperacaoRegimeRegularRequest) -> OperacaoRegimeRegularResponse:
    """Calcula múltiplos itens com consulta SQLite de vigência e totalização exata."""
    return calcular_operacao_regime_regular(payload)


@router.post(
    "/expressao/avaliar",
    response_model=ExpressaoAvaliacaoResponse,
    summary="Avalia expressão aritmética tributária em sandbox AST segura (ADR001)",
)
def post_avaliar_expressao(payload: ExpressaoAvaliacaoRequest) -> ExpressaoAvaliacaoResponse:
    """Avalia uma fórmula tributária com variáveis Decimal sem uso de eval()."""
    try:
        return executar_avaliacao_expressao(payload)
    except ExpressaoInvalidaError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get(
    "/expressao/formulas",
    summary="Lista fórmulas tributárias oficiais de referência (ADR001 / TRATAMENTO_TRIBUTARIO)",
)
def get_formulas_referencia() -> dict[str, dict[str, str]]:
    """Retorna o catálogo de fórmulas de referência avaliáveis pelo motor ADR001."""
    return FORMULAS_OFICIAIS_REFERENCIA
