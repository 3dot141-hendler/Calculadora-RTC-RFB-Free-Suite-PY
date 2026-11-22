"""Serviço fachada do Comparador Tributário integrado às tabelas oficiais SQLite."""

from decimal import Decimal

from app.modules.tabelas_oficiais.repository import (
    listar_cst_classificacao,
    listar_ufs_referencia,
)
from .engine import InsumoComparador, executar_comparacao_regimes
from .schemas import ComparadorRequest, ComparadorResponse

_DEFAULT_ALIQ_IBS_UF = Decimal("10.00")
_DEFAULT_ALIQ_CBS = Decimal("8.80")


def simular_comparativo_regimes(payload: ComparadorRequest) -> ComparadorResponse:
    """Resolve alíquotas vigentes (UF e cClassTrib) no SQLite e executa o motor comparativo."""
    aliq_ibs_uf = payload.aliquota_ibs_uf if payload.aliquota_ibs_uf is not None else _DEFAULT_ALIQ_IBS_UF
    aliq_cbs = payload.aliquota_cbs if payload.aliquota_cbs is not None else _DEFAULT_ALIQ_CBS
    reducao_ibs = Decimal("0.00")
    reducao_cbs = Decimal("0.00")

    uf_normalizada = payload.uf.upper() if payload.uf else None
    if uf_normalizada:
        ufs = listar_ufs_referencia(payload.data_fato_gerador)
        uf_match = next((u for u in ufs if u["uf"] == uf_normalizada), None)
        if uf_match:
            if payload.aliquota_ibs_uf is None:
                aliq_ibs_uf = Decimal(uf_match["aliquota_ibs_uf"])
            if payload.aliquota_cbs is None:
                aliq_cbs = Decimal(uf_match["aliquota_cbs"])

    if payload.c_class_trib:
        csts = listar_cst_classificacao(payload.data_fato_gerador)
        cst_match = next((c for c in csts if c["c_class_trib"] == payload.c_class_trib), None)
        if cst_match:
            reducao_ibs = Decimal(cst_match["aliquota_reducao_ibs"])
            reducao_cbs = Decimal(cst_match["aliquota_reducao_cbs"])

    resultado = executar_comparacao_regimes(
        InsumoComparador(
            receita_bruta_12m=payload.receita_bruta_12m,
            valor_operacao=payload.valor_operacao,
            anexo=payload.anexo,
            aliquota_ibs_uf=aliq_ibs_uf,
            aliquota_ibs_mun=payload.aliquota_ibs_mun,
            aliquota_cbs=aliq_cbs,
            aliquota_is=payload.aliquota_is,
            reducao_ibs=reducao_ibs,
            reducao_cbs=reducao_cbs,
            creditos_anteriores=payload.creditos_anteriores,
            percentual_vendas_b2b=payload.percentual_vendas_b2b,
        )
    )

    return ComparadorResponse(
        valor_operacao=payload.valor_operacao,
        receita_bruta_12m=payload.receita_bruta_12m,
        anexo=payload.anexo,
        uf=uf_normalizada,
        c_class_trib=payload.c_class_trib,
        aliquota_ibs_uf_aplicada=aliq_ibs_uf,
        aliquota_ibs_mun_aplicada=payload.aliquota_ibs_mun,
        aliquota_cbs_aplicada=aliq_cbs,
        reducao_ibs_percentual=reducao_ibs,
        reducao_cbs_percentual=reducao_cbs,
        percentual_vendas_b2b=payload.percentual_vendas_b2b,
        cenarios=resultado.cenarios,
        melhor_cenario_carga_propria=resultado.melhor_cenario_carga_propria,
        economia_maxima_reais=resultado.economia_maxima_reais,
        melhor_cenario_competitividade_b2b=resultado.melhor_cenario_competitividade_b2b,
        resumo_executivo=resultado.resumo_executivo,
    )
