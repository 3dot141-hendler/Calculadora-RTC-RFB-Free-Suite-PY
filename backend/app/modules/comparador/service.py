"""Serviço fachada do Comparador Tributário integrado às tabelas oficiais SQLite."""

from datetime import date
from decimal import Decimal
from typing import Optional

from app.modules.tabelas_oficiais.repository import (
    listar_cst_classificacao,
    listar_ufs_referencia,
)
from app.modules.tabelas_oficiais.tributo_local_resolver import resolver_contexto_transicao_local
from .engine import InsumoComparador, executar_comparacao_regimes
from .engine_presumido_real import (
    InsumoPresumidoReal,
    executar_comparacao_presumido_real,
)
from .fator_r import simular_analise_fator_r
from .schemas import AnaliseFatorR, ComparadorRequest, ComparadorResponse
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
    """Resolve alíquotas vigentes (UF, cClassTrib, ICMS/ISS e transição) e executa o comparador."""
    uf_norm, aliq_ibs_uf, aliq_cbs, reducao_ibs, reducao_cbs = _resolver_aliquotas_referencia(
        data_fato_gerador=payload.data_fato_gerador,
        uf=payload.uf,
        c_class_trib=payload.c_class_trib,
        override_ibs_uf=payload.aliquota_ibs_uf,
        override_cbs=payload.aliquota_cbs,
    )

    ctx_trans = resolver_contexto_transicao_local(
        data_fato_gerador=payload.data_fato_gerador,
        uf=uf_norm,
        aliq_ibs_uf_cheia=aliq_ibs_uf,
        aliq_ibs_mun_cheia=payload.aliquota_ibs_mun,
        aliq_cbs_cheia=aliq_cbs,
        aplicar_transicao_ano=payload.aplicar_transicao_ano,
        tipo_tributo_local=payload.tipo_tributo_local,
        codigo_ibge=payload.codigo_ibge,
        codigo_servico_iss=payload.codigo_servico_iss,
        aliquota_icms_manual=payload.aliquota_icms_manual,
        aliquota_iss_manual=payload.aliquota_iss_manual,
    )
    ibs_uf_efet = ctx_trans.aliquota_ibs_uf_efetiva if ctx_trans else aliq_ibs_uf
    ibs_mun_efet = ctx_trans.aliquota_ibs_mun_efetiva if ctx_trans else payload.aliquota_ibs_mun
    cbs_efet = ctx_trans.aliquota_cbs_efetiva if ctx_trans else aliq_cbs
    local_efet = ctx_trans.aliquota_local_efetiva if ctx_trans else Decimal("0.00")

    analise_fator_r: Optional[AnaliseFatorR] = None
    anexo_efetivo = payload.anexo
    if payload.aplicar_fator_r:
        folha = payload.folha_salarios_12m if payload.folha_salarios_12m is not None else Decimal("0.00")
        analise_fator_r = simular_analise_fator_r(
            receita_bruta_12m=payload.receita_bruta_12m,
            valor_operacao=payload.valor_operacao,
            folha_salarios_12m=folha,
        )
        anexo_efetivo = analise_fator_r.anexo_definido

    resultado = executar_comparacao_regimes(
        InsumoComparador(
            receita_bruta_12m=payload.receita_bruta_12m,
            valor_operacao=payload.valor_operacao,
            anexo=anexo_efetivo,
            aliquota_ibs_uf=ibs_uf_efet,
            aliquota_ibs_mun=ibs_mun_efet,
            aliquota_cbs=cbs_efet,
            aliquota_is=payload.aliquota_is,
            reducao_ibs=reducao_ibs,
            reducao_cbs=reducao_cbs,
            creditos_anteriores=payload.creditos_anteriores,
            percentual_vendas_b2b=payload.percentual_vendas_b2b,
            aliquota_local_efetiva=local_efet,
        )
    )

    resumo = resultado.resumo_executivo
    if analise_fator_r is not None:
        resumo = f"{resumo} {analise_fator_r.recomendacao}"

    return ComparadorResponse(
        valor_operacao=payload.valor_operacao,
        receita_bruta_12m=payload.receita_bruta_12m,
        anexo=anexo_efetivo,
        fator_r=analise_fator_r,
        transicao_tributo_local=ctx_trans.resumo if ctx_trans else None,
        uf=uf_norm,
        c_class_trib=payload.c_class_trib,
        aliquota_ibs_uf_aplicada=ibs_uf_efet,
        aliquota_ibs_mun_aplicada=ibs_mun_efet,
        aliquota_cbs_aplicada=cbs_efet,
        reducao_ibs_percentual=reducao_ibs,
        reducao_cbs_percentual=reducao_cbs,
        percentual_vendas_b2b=payload.percentual_vendas_b2b,
        cenarios=resultado.cenarios,
        melhor_cenario_carga_propria=resultado.melhor_cenario_carga_propria,
        economia_maxima_reais=resultado.economia_maxima_reais,
        melhor_cenario_competitividade_b2b=resultado.melhor_cenario_competitividade_b2b,
        resumo_executivo=resumo,
    )


def simular_presumido_vs_real(
    payload: ComparadorPresumidoRealRequest,
) -> ComparadorPresumidoRealResponse:
    """Resolve alíquotas vigentes (UF, cClassTrib, ICMS/ISS e transição) e compara Presumido vs. Real."""
    uf_norm, aliq_ibs_uf, aliq_cbs, reducao_ibs, reducao_cbs = _resolver_aliquotas_referencia(
        data_fato_gerador=payload.data_fato_gerador,
        uf=payload.uf,
        c_class_trib=payload.c_class_trib,
        override_ibs_uf=payload.aliquota_ibs_uf,
        override_cbs=payload.aliquota_cbs,
    )

    ctx_trans = resolver_contexto_transicao_local(
        data_fato_gerador=payload.data_fato_gerador,
        uf=uf_norm,
        aliq_ibs_uf_cheia=aliq_ibs_uf,
        aliq_ibs_mun_cheia=payload.aliquota_ibs_mun,
        aliq_cbs_cheia=aliq_cbs,
        aplicar_transicao_ano=payload.aplicar_transicao_ano,
        tipo_tributo_local=payload.tipo_tributo_local,
        codigo_ibge=payload.codigo_ibge,
        codigo_servico_iss=payload.codigo_servico_iss,
        aliquota_icms_manual=payload.aliquota_icms_manual,
        aliquota_iss_manual=payload.aliquota_iss_manual,
    )
    ibs_uf_efet = ctx_trans.aliquota_ibs_uf_efetiva if ctx_trans else aliq_ibs_uf
    ibs_mun_efet = ctx_trans.aliquota_ibs_mun_efetiva if ctx_trans else payload.aliquota_ibs_mun
    cbs_efet = ctx_trans.aliquota_cbs_efetiva if ctx_trans else aliq_cbs
    local_efet = ctx_trans.aliquota_local_efetiva if ctx_trans else Decimal("0.00")

    resultado = executar_comparacao_presumido_real(
        InsumoPresumidoReal(
            receita_bruta_mensal=payload.receita_bruta_mensal,
            despesas_dedutiveis_mensais=payload.despesas_dedutiveis_mensais,
            atividade=payload.atividade,
            aliquota_ibs_uf=ibs_uf_efet,
            aliquota_ibs_mun=ibs_mun_efet,
            aliquota_cbs=cbs_efet,
            aliquota_is=payload.aliquota_is,
            reducao_ibs=reducao_ibs,
            reducao_cbs=reducao_cbs,
            creditos_ibs_cbs=payload.creditos_ibs_cbs,
            aliquota_local_efetiva=local_efet,
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
        transicao_tributo_local=ctx_trans.resumo if ctx_trans else None,
        uf=uf_norm,
        c_class_trib=payload.c_class_trib,
        aliquota_ibs_uf_aplicada=ibs_uf_efet,
        aliquota_cbs_aplicada=cbs_efet,
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
