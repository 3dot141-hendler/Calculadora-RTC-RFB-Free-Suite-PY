"""Serviço de cálculo do Regime Regular (IBS, CBS e Imposto Seletivo)."""

from decimal import Decimal, ROUND_HALF_UP

from .schemas import RegimeRegularCalculoRequest, RegimeRegularCalculoResponse


def _round_money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calcular_regime_regular(payload: RegimeRegularCalculoRequest) -> RegimeRegularCalculoResponse:
    """Calcula IBS (UF + Municipal), CBS e Imposto Seletivo com redução e créditos.

    A matriz completa de CST/cClassTrib e regras de incidência por fora serão
    sincronizadas com `originals:references/regime-regular`.
    """
    fator_reducao = Decimal("1.00") - (payload.percentual_reducao / Decimal("100.00"))
    base_calculo = _round_money(payload.valor_operacao)

    valor_ibs_uf = _round_money(base_calculo * (payload.aliquota_ibs_uf / Decimal("100.00")) * fator_reducao)
    valor_ibs_mun = _round_money(base_calculo * (payload.aliquota_ibs_mun / Decimal("100.00")) * fator_reducao)
    valor_cbs = _round_money(base_calculo * (payload.aliquota_cbs / Decimal("100.00")) * fator_reducao)
    valor_is = _round_money(base_calculo * (payload.aliquota_is / Decimal("100.00")))

    total_bruto = _round_money(valor_ibs_uf + valor_ibs_mun + valor_cbs + valor_is)
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

