"""Simulador puro de Fator R (Anexo III vs. Anexo V) para o Comparador Tributário."""

from decimal import Decimal, ROUND_HALF_EVEN

from app.core.rounding import multiplicar
from app.modules.simples.anexos import avaliar_fator_r
from app.modules.simples.schemas import AnexoSimples
from app.modules.simples.tabelas_lc123 import calcular_aliquota_efetiva_lc123
from .schemas import AnaliseFatorR


def _round_money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)


def simular_analise_fator_r(
    receita_bruta_12m: Decimal,
    valor_operacao: Decimal,
    folha_salarios_12m: Decimal,
) -> AnaliseFatorR:
    """Calcula enquadramento Fator R (>= 28% → Anexo III) e compara DAS III vs. V."""
    avaliacao = avaliar_fator_r(folha_salarios_12m, receita_bruta_12m)
    anexo_definido = (
        AnexoSimples.ANEXO_III if avaliacao.anexo_definido == "III" else AnexoSimples.ANEXO_V
    )

    base = _round_money(valor_operacao)
    aliq_iii = calcular_aliquota_efetiva_lc123(AnexoSimples.ANEXO_III, receita_bruta_12m)
    aliq_v = calcular_aliquota_efetiva_lc123(AnexoSimples.ANEXO_V, receita_bruta_12m)

    das_iii = _round_money(multiplicar(base, aliq_iii))
    das_v = _round_money(multiplicar(base, aliq_v))
    economia = _round_money(max(Decimal("0.00"), das_v - das_iii))
    faltante_mensal = _round_money(avaliacao.folha_faltante_anexo_iii / Decimal("12"))

    if avaliacao.atingiu_minimo_28_pct:
        recomendacao = (
            f"Fator R de {avaliacao.percentual_fator_r:.2f}% atingiu o mínimo de 28% "
            f"(enquadramento no Anexo III), gerando economia de R$ {economia:.2f} no DAS "
            f"desta operação frente ao Anexo V (R$ {das_iii:.2f} vs. R$ {das_v:.2f})."
        )
    else:
        recomendacao = (
            f"Fator R de {avaliacao.percentual_fator_r:.2f}% ficou abaixo de 28% "
            f"(enquadramento no Anexo V). Faltam R$ {avaliacao.folha_faltante_anexo_iii:.2f} "
            f"em folha/pró-labore nos 12 meses (~R$ {faltante_mensal:.2f}/mês) para migrar ao "
            f"Anexo III e reduzir o DAS desta operação em R$ {economia:.2f}."
        )

    return AnaliseFatorR(
        aplicado=True,
        folha_salarios_12m=avaliacao.folha_salarios_12m,
        percentual_fator_r=avaliacao.percentual_fator_r,
        atingiu_minimo_28_pct=avaliacao.atingiu_minimo_28_pct,
        anexo_definido=anexo_definido,
        folha_minima_anexo_iii=avaliacao.folha_minima_anexo_iii,
        folha_faltante_anexo_iii=avaliacao.folha_faltante_anexo_iii,
        folha_faltante_mensal=faltante_mensal,
        das_anexo_iii=das_iii,
        das_anexo_v=das_v,
        economia_das_fator_r=economia,
        recomendacao=recomendacao,
    )
