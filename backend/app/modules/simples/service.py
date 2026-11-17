"""Serviço de regras de negócio do Simples Nacional (esqueleto para port da RFB)."""

from decimal import Decimal, ROUND_HALF_UP

from .schemas import AnexoSimples, SimplesCalculoRequest, SimplesCalculoResponse

# Tabela simplificada de alíquota nominal base por anexo (referência inicial para TDD)
_ALIQUOTA_BASE_ANEXO: dict[AnexoSimples, Decimal] = {
    AnexoSimples.ANEXO_I: Decimal("0.0400"),
    AnexoSimples.ANEXO_II: Decimal("0.0450"),
    AnexoSimples.ANEXO_III: Decimal("0.0600"),
    AnexoSimples.ANEXO_IV: Decimal("0.0450"),
    AnexoSimples.ANEXO_V: Decimal("0.1550"),
}

_ALIQUOTA_TRANSICAO_IBS_CBS = Decimal("0.0100")  # 1,0% referência inicial de transição


def _round_money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calcular_simples(payload: SimplesCalculoRequest) -> SimplesCalculoResponse:
    """Executa o cálculo estimado do Simples Nacional com parametrização RTC.

    As faixas progressivas completas e deduções por partilha de tributos serão
    portadas a partir do código de referência em `originals:references/simples`.
    """
    aliquota_base = _ALIQUOTA_BASE_ANEXO[payload.anexo]
    fator_faixa = (payload.receita_bruta_12m / Decimal("4800000.00")) * Decimal("0.05")
    aliquota_efetiva = (aliquota_base + fator_faixa).quantize(
        Decimal("0.0001"), rounding=ROUND_HALF_UP
    )

    valor_das = _round_money(payload.valor_operacao * aliquota_efetiva)

    if payload.recolher_ibs_cbs_por_fora:
        valor_ibs_cbs = _round_money(payload.valor_operacao * _ALIQUOTA_TRANSICAO_IBS_CBS)
        obs = "Cálculo com IBS/CBS destacado por fora do DAS (opção regime regular)."
    else:
        valor_ibs_cbs = _round_money(valor_das * Decimal("0.20"))
        obs = "Cálculo unificado via DAS com parcela estimada de IBS/CBS."

    valor_total = (
        valor_das + valor_ibs_cbs if payload.recolher_ibs_cbs_por_fora else valor_das
    )

    return SimplesCalculoResponse(
        anexo=payload.anexo,
        aliquota_efetiva_das=(aliquota_efetiva * Decimal("100")).quantize(Decimal("0.01")),
        valor_das=valor_das,
        valor_ibs_cbs_estimado=valor_ibs_cbs,
        valor_total_tributos=_round_money(valor_total),
        observacoes=obs,
    )

