"""Serviço de cálculo do Regime Regular (IBS, CBS e Imposto Seletivo)."""

from decimal import Decimal, ROUND_HALF_EVEN

from app.core.rounding import dividir_por_cem, multiplicar, subtrair, totalizar
from app.modules.tabelas_oficiais.repository import (
    listar_cst_classificacao,
    listar_ufs_referencia,
)
from .schemas import RegimeRegularCalculoRequest, RegimeRegularCalculoResponse


def _round_money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)


def calcular_regime_regular(payload: RegimeRegularCalculoRequest) -> RegimeRegularCalculoResponse:
    """Calcula IBS (UF + Municipal), CBS e Imposto Seletivo com vigência e créditos."""
    aliq_ibs_uf = payload.aliquota_ibs_uf
    aliq_cbs = payload.aliquota_cbs
    red_ibs = payload.percentual_reducao
    red_cbs = payload.percentual_reducao

    if payload.uf:
        ufs = listar_ufs_referencia(payload.data_fato_gerador)
        uf_match = next((u for u in ufs if u["uf"] == payload.uf.upper()), None)
        if uf_match:
            aliq_ibs_uf = Decimal(uf_match["aliquota_ibs_uf"])
            aliq_cbs = Decimal(uf_match["aliquota_cbs"])

    if payload.c_class_trib:
        csts = listar_cst_classificacao(payload.data_fato_gerador)
        cst_match = next((c for c in csts if c["c_class_trib"] == payload.c_class_trib), None)
        if cst_match:
            red_ibs = Decimal(cst_match["aliquota_reducao_ibs"])
            red_cbs = Decimal(cst_match["aliquota_reducao_cbs"])

    fator_red_ibs = subtrair(Decimal("1"), dividir_por_cem(red_ibs))
    fator_red_cbs = subtrair(Decimal("1"), dividir_por_cem(red_cbs))
    base_calculo = _round_money(payload.valor_operacao)

    valor_ibs_uf = _round_money(
        multiplicar(multiplicar(base_calculo, dividir_por_cem(aliq_ibs_uf)), fator_red_ibs)
    )
    valor_ibs_mun = _round_money(
        multiplicar(multiplicar(base_calculo, dividir_por_cem(payload.aliquota_ibs_mun)), fator_red_ibs)
    )
    valor_cbs = _round_money(
        multiplicar(multiplicar(base_calculo, dividir_por_cem(aliq_cbs)), fator_red_cbs)
    )
    valor_is = _round_money(multiplicar(base_calculo, dividir_por_cem(payload.aliquota_is)))

    total_bruto = _round_money(totalizar((valor_ibs_uf, valor_ibs_mun, valor_cbs, valor_is)))
    creditos_aproveitados = min(payload.creditos_anteriores, total_bruto)
    valor_liquido = _round_money(total_bruto - creditos_aproveitados)

    return RegimeRegularCalculoResponse(
        base_calculo=base_calculo,
        valor_ibs_uf=valor_ibs_uf,
        valor_ibs_mun=valor_ibs_mun,
        valor_cbs=valor_cbs,
        valor_is=valor_is,
        total_bruto_tributos=total_bruto,
        creditos_aproveitados=_round_money(creditos_aproveitados),
        valor_liquido_a_recolher=valor_liquido,
    )

