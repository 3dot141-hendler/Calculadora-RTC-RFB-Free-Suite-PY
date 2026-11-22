"""Serviço fachada do Comparador Tributário integrado às tabelas oficiais SQLite."""

from datetime import date
from decimal import Decimal
from typing import Optional

from app.modules.tabelas_oficiais.repository import (
    listar_cst_classificacao,
    listar_ufs_referencia,
)
from .engine import InsumoComparador, executar_comparacao_regimes
from .engine_presumido_real import (
    InsumoPresumidoReal,
    executar_comparacao_presumido_real,
)
from .schemas import ComparadorRequest, ComparadorResponse
from .schemas_presumido_real import (
    ComparadorPresumidoRealRequest,
    ComparadorPresumidoRealResponse,
)

_DEFAULT_ALIQ_IBS_UF = Decimal("10.00")
_DEFAULT_ALIQ_CBS = Decimal("8.80")


def _resolver_aliquotas_referencia(
    data_fato_gerador: date,
    uf: Optional[str],
    c_class_trib: Optional[str],
    override_ibs_uf: Optional[Decimal],
    override_cbs: Optional[Decimal],
) -> tuple[Optional[str], Decimal, Decimal, Decimal, Decimal]:
    """Resolve UF, IBS Estadual, CBS e percentuais de redução via SQLite oficial."""
    aliq_ibs_uf = override_ibs_uf if override_ibs_uf is not None else _DEFAULT_ALIQ_IBS_UF
    aliq_cbs = override_cbs if override_cbs is not None else _DEFAULT_ALIQ_CBS
    reducao_ibs = Decimal("0.00")
    reducao_cbs = Decimal("0.00")

    uf_normalizada = uf.upper() if uf else None
    if uf_normalizada:
        ufs = listar_ufs_referencia(data_fato_gerador)
        uf_match = next((u for u in ufs if u["uf"] == uf_normalizada), None)
        if uf_match:
            if override_ibs_uf is None:
                aliq_ibs_uf = Decimal(uf_match["aliquota_ibs_uf"])
            if override_cbs is None:
                aliq_cbs = Decimal(uf_match["aliquota_cbs"])

    if c_class_trib:
        csts = listar_cst_classificacao(data_fato_gerador)
        cst_match = next((c for c in csts if c["c_class_trib"] == c_class_trib), None)
        if cst_match:
            reducao_ibs = Decimal(cst_match["aliquota_reducao_ibs"])
            reducao_cbs = Decimal(cst_match["aliquota_reducao_cbs"])

    return uf_normalizada, aliq_ibs_uf, aliq_cbs, reducao_ibs, reducao_cbs


def simular_comparativo_regimes(payload: ComparadorRequest) -> ComparadorResponse:
    """Resolve alíquotas vigentes (UF e cClassTrib) no SQLite e executa o comparador Simples/Regular."""
    uf_norm, aliq_ibs_uf, aliq_cbs, reducao_ibs, reducao_cbs = _resolver_aliquotas_referencia(
        data_fato_gerador=payload.data_fato_gerador,
        uf=payload.uf,
        c_class_trib=payload.c_class_trib,
        override_ibs_uf=payload.aliquota_ibs_uf,
        override_cbs=payload.aliquota_cbs,
    )

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
        uf=uf_norm,
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


def simular_presumido_vs_real(
    payload: ComparadorPresumidoRealRequest,
) -> ComparadorPresumidoRealResponse:
    """Resolve alíquotas vigentes (UF e cClassTrib) no SQLite e compara Lucro Presumido vs. Real."""
    uf_norm, aliq_ibs_uf, aliq_cbs, reducao_ibs, reducao_cbs = _resolver_aliquotas_referencia(
        data_fato_gerador=payload.data_fato_gerador,
        uf=payload.uf,
        c_class_trib=payload.c_class_trib,
        override_ibs_uf=payload.aliquota_ibs_uf,
        override_cbs=payload.aliquota_cbs,
    )

    resultado = executar_comparacao_presumido_real(
        InsumoPresumidoReal(
            receita_bruta_mensal=payload.receita_bruta_mensal,
            despesas_dedutiveis_mensais=payload.despesas_dedutiveis_mensais,
            atividade=payload.atividade,
            aliquota_ibs_uf=aliq_ibs_uf,
            aliquota_ibs_mun=payload.aliquota_ibs_mun,
            aliquota_cbs=aliq_cbs,
            aliquota_is=payload.aliquota_is,
            reducao_ibs=reducao_ibs,
            reducao_cbs=reducao_cbs,
            creditos_ibs_cbs=payload.creditos_ibs_cbs,
        )
    )

    return ComparadorPresumidoRealResponse(
        receita_bruta_mensal=payload.receita_bruta_mensal,
        receita_anualizada_estimada=resultado.receita_anualizada_estimada,
        despesas_dedutiveis_mensais=payload.despesas_dedutiveis_mensais,
        lucro_contabil_mensal=resultado.lucro_contabil_mensal,
        margem_lucro_real_percentual=resultado.margem_lucro_real_percentual,
        atividade=payload.atividade,
        presuncao_irpj_percentual=resultado.presuncao_irpj_percentual,
        presuncao_csll_percentual=resultado.presuncao_csll_percentual,
        uf=uf_norm,
        c_class_trib=payload.c_class_trib,
        aliquota_ibs_uf_aplicada=aliq_ibs_uf,
        aliquota_cbs_aplicada=aliq_cbs,
        reducao_ibs_percentual=reducao_ibs,
        ibs_cbs_bruto=resultado.ibs_cbs_bruto,
        creditos_ibs_cbs_aproveitados=resultado.creditos_ibs_cbs_aproveitados,
        excede_limite_presumido=resultado.excede_limite_presumido,
        cenarios=resultado.cenarios,
        melhor_regime=resultado.melhor_regime,
        economia_mensal_reais=resultado.economia_mensal_reais,
        economia_anual_estimada_reais=resultado.economia_anual_estimada_reais,
        resumo_executivo=resultado.resumo_executivo,
    )
