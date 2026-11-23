"""Rotas FastAPI para o módulo Simples Nacional (/simples)."""

from typing import Optional, Union

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from .codigos_erro import buscar_erro_simples_por_codigo, listar_catalogo_erros_simples
from .observabilidade import (
    OperacaoSimplesInvalidaError,
    calcular_operacao_simples_observabilidade,
)
from .schemas import (
    SimplesCalculoRequest,
    SimplesCalculoResponse,
    SimplesItemCalculoRequest,
    SimplesItemCalculoResponse,
)
from .schemas_operacao import (
    ErroDescricaoSimples,
    ObservabilidadeSimplesDomain,
    OperacaoSimplesInput,
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
    try:
        return calcular_item_simples_api(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post(
    "/observabilidade/calcular",
    response_model=ObservabilidadeSimplesDomain,
    response_model_exclude_none=True,
    summary="Calcular operação multi-itens com observabilidade VSN-* (NT 2026.005)",
)
def endpoint_calcular_operacao_simples(
    payload: OperacaoSimplesInput,
    request: Request,
) -> Union[ObservabilidadeSimplesDomain, JSONResponse]:
    """Processa operação em lote do Simples Nacional com validação cruzada e totais."""
    base_url = str(request.base_url).rstrip("/")
    try:
        return calcular_operacao_simples_observabilidade(payload, base_url=base_url)
    except OperacaoSimplesInvalidaError as exc:
        return JSONResponse(
            status_code=422,
            content={
                "status": 422,
                "title": "Erro de validação na operação do Simples Nacional",
                "erros": [err.model_dump() for err in exc.erros],
            },
        )


@router.get(
    "/observabilidade/erros",
    response_model=Union[ErroDescricaoSimples, list[ErroDescricaoSimples]],
    summary="Catálogo oficial de códigos de erro VSN-* do Simples Nacional",
)
def endpoint_catalogo_erros_simples(
    codigo: Optional[str] = Query(
        default=None,
        description="Código específico (ex.: VSN-018). Quando omitido, retorna todo o catálogo.",
    ),
) -> Union[ErroDescricaoSimples, list[ErroDescricaoSimples]]:
    """Consulta a documentação oficial de erros VSN-* da NT 2026.005."""
    if codigo:
        encontrado = buscar_erro_simples_por_codigo(codigo)
        if encontrado is None:
            raise HTTPException(status_code=404, detail=f"Código '{codigo}' não encontrado no catálogo VSN-*.")
        return ErroDescricaoSimples(**encontrado)
    return [ErroDescricaoSimples(**item) for item in listar_catalogo_erros_simples()]
