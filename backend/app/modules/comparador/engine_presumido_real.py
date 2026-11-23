"""Motor puro de comparação: Lucro Presumido vs. Lucro Real no Regime Regular (IBS/CBS/IS)."""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_EVEN

from app.core.rounding import (
    dividir,
    dividir_por_cem,
    multiplicar,
    multiplicar_por_cem,
    subtrair,
    totalizar,
)
from .schemas_presumido_real import AtividadePresumido, CenarioLucroComparativo

_ALIQ_IRPJ = Decimal("0.15")
_ALIQ_ADICIONAL_IRPJ = Decimal("0.10")
_LIMITE_MENSAL_ADICIONAL_IRPJ = Decimal("20000.00")
_ALIQ_CSLL = Decimal("0.09")
_TETO_ANUAL_LUCRO_PRESUMIDO = Decimal("78000000.00")

# Percentuais oficiais de presunção (Lei nº 9.249/1995): (IRPJ %, CSLL %)
_PRESUNCAO_POR_ATIVIDADE: dict[AtividadePresumido, tuple[Decimal, Decimal]] = {
    AtividadePresumido.COMERCIO_INDUSTRIA: (Decimal("8.00"), Decimal("12.00")),
    AtividadePresumido.SERVICOS_GERAIS: (Decimal("32.00"), Decimal("32.00")),
    AtividadePresumido.SERVICOS_HOSPITALARES: (Decimal("8.00"), Decimal("12.00")),
    AtividadePresumido.TRANSPORTE_CARGA: (Decimal("8.00"), Decimal("12.00")),
    AtividadePresumido.TRANSPORTE_PASSAGEIROS: (Decimal("16.00"), Decimal("12.00")),
}


def _round_money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)


def _round_rate(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)


@dataclass(frozen=True, slots=True)
class InsumoPresumidoReal:
    """Parâmetros resolvidos para cálculo puro de Lucro Presumido vs. Lucro Real."""

    receita_bruta_mensal: Decimal
    despesas_dedutiveis_mensais: Decimal
    atividade: AtividadePresumido
    aliquota_ibs_uf: Decimal
    aliquota_ibs_mun: Decimal
    aliquota_cbs: Decimal
    aliquota_is: Decimal
    reducao_ibs: Decimal
    reducao_cbs: Decimal
    creditos_ibs_cbs: Decimal


@dataclass(frozen=True, slots=True)
class ResultadoPresumidoRealMotor:
    """Resultado consolidado do motor puro Lucro Presumido vs. Lucro Real."""

    receita_anualizada_estimada: Decimal
    lucro_contabil_mensal: Decimal
    margem_lucro_real_percentual: Decimal
    presuncao_irpj_percentual: Decimal
    presuncao_csll_percentual: Decimal
    ibs_cbs_bruto: Decimal
    creditos_ibs_cbs_aproveitados: Decimal
    excede_limite_presumido: bool
    cenarios: list[CenarioLucroComparativo]
    melhor_regime: str
    economia_mensal_reais: Decimal
    economia_anual_estimada_reais: Decimal
    resumo_executivo: str


def _calcular_irpj_csll(base_irpj: Decimal, base_csll: Decimal) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    irpj_basico = _round_money(multiplicar(base_irpj, _ALIQ_IRPJ))
    excedente = max(Decimal("0.00"), base_irpj - _LIMITE_MENSAL_ADICIONAL_IRPJ)
    adicional = _round_money(multiplicar(excedente, _ALIQ_ADICIONAL_IRPJ))
    csll = _round_money(multiplicar(base_csll, _ALIQ_CSLL))
    total = _round_money(totalizar((irpj_basico, adicional, csll)))
    return irpj_basico, adicional, csll, total


def executar_comparacao_presumido_real(insumo: InsumoPresumidoReal) -> ResultadoPresumidoRealMotor:
    """Compara Lucro Presumido e Lucro Real somando IRPJ/CSLL com IBS/CBS/IS no Regime Regular."""
    receita = _round_money(insumo.receita_bruta_mensal)
    despesas = _round_money(insumo.despesas_dedutiveis_mensais)
    receita_anualizada = _round_money(multiplicar(receita, Decimal("12")))
    excede_limite = receita_anualizada > _TETO_ANUAL_LUCRO_PRESUMIDO

    lucro_contabil = _round_money(receita - despesas)
    lucro_tributavel_real = max(Decimal("0.00"), lucro_contabil)
    margem_real_pct = _round_rate(multiplicar_por_cem(dividir(lucro_contabil, receita)))

    presuncao_irpj_pct, presuncao_csll_pct = _PRESUNCAO_POR_ATIVIDADE[insumo.atividade]

    # 1. IBS + CBS + IS no Regime Regular (não cumulatividade plena nos dois regimes)
    fator_red_ibs = subtrair(Decimal("1"), dividir_por_cem(insumo.reducao_ibs))
    fator_red_cbs = subtrair(Decimal("1"), dividir_por_cem(insumo.reducao_cbs))

    valor_ibs_uf = _round_money(
        multiplicar(multiplicar(receita, dividir_por_cem(insumo.aliquota_ibs_uf)), fator_red_ibs)
    )
    valor_ibs_mun = _round_money(
        multiplicar(multiplicar(receita, dividir_por_cem(insumo.aliquota_ibs_mun)), fator_red_ibs)
    )
    valor_cbs = _round_money(
        multiplicar(multiplicar(receita, dividir_por_cem(insumo.aliquota_cbs)), fator_red_cbs)
    )
    valor_is = _round_money(multiplicar(receita, dividir_por_cem(insumo.aliquota_is)))

    ibs_cbs_bruto = _round_money(totalizar((valor_ibs_uf, valor_ibs_mun, valor_cbs)))
    total_consumo_bruto = _round_money(totalizar((ibs_cbs_bruto, valor_is)))
    creditos_aproveitados = _round_money(min(insumo.creditos_ibs_cbs, total_consumo_bruto))
    ibs_cbs_is_liquido = _round_money(total_consumo_bruto - creditos_aproveitados)

    # 2. Cenário A — Lucro Presumido
    base_irpj_pres = _round_money(multiplicar(receita, dividir_por_cem(presuncao_irpj_pct)))
    base_csll_pres = _round_money(multiplicar(receita, dividir_por_cem(presuncao_csll_pct)))
    irpj_pres, adic_pres, csll_pres, total_lucro_pres = _calcular_irpj_csll(
        base_irpj_pres, base_csll_pres
    )
    carga_pres = _round_money(totalizar((total_lucro_pres, ibs_cbs_is_liquido)))
    aliq_efetiva_pres = _round_rate(multiplicar_por_cem(dividir(carga_pres, receita)))

    obs_pres = (
        "ATENÇÃO: faturamento anualizado ultrapassa R$ 78 milhões/ano — empresa obrigada ao Lucro Real."
        if excede_limite
        else (
            f"Presunção legal de {presuncao_irpj_pct:.0f}% (IRPJ) e {presuncao_csll_pct:.0f}% (CSLL) "
            "independentemente do lucro efetivo. IBS/CBS apurados pelo Regime Regular."
        )
    )

    cenario_presumido = CenarioLucroComparativo(
        id="lucro_presumido",
        nome="Lucro Presumido + IBS/CBS",
        subtitulo=f"Presunção {presuncao_irpj_pct:.0f}% IRPJ / {presuncao_csll_pct:.0f}% CSLL",
        elegivel=not excede_limite,
        base_calculo_irpj=base_irpj_pres,
        base_calculo_csll=base_csll_pres,
        irpj_basico=irpj_pres,
        adicional_irpj=adic_pres,
        csll=csll_pres,
        total_irpj_csll=total_lucro_pres,
        ibs_cbs_is_liquido=ibs_cbs_is_liquido,
        carga_tributaria_total=carga_pres,
        aliquota_efetiva_percentual=aliq_efetiva_pres,
        observacoes=obs_pres,
    )

    # 3. Cenário B — Lucro Real
    irpj_real, adic_real, csll_real, total_lucro_real = _calcular_irpj_csll(
        lucro_tributavel_real, lucro_tributavel_real
    )
    carga_real = _round_money(totalizar((total_lucro_real, ibs_cbs_is_liquido)))
    aliq_efetiva_real = _round_rate(multiplicar_por_cem(dividir(carga_real, receita)))

    obs_real = (
        "Prejuízo fiscal no período: IRPJ e CSLL zerados (com possibilidade de compensação futura em até 30%)."
        if lucro_contabil <= Decimal("0.00")
        else (
            f"Tributação sobre lucro líquido efetivo de {margem_real_pct:.2f}% "
            "(15% IRPJ + 10% adicional acima de R$ 20 mil/mês + 9% CSLL) + IBS/CBS no Regime Regular."
        )
    )

    cenario_real = CenarioLucroComparativo(
        id="lucro_real",
        nome="Lucro Real + IBS/CBS",
        subtitulo=f"Margem real apurada: {margem_real_pct:.2f}%",
        elegivel=True,
        base_calculo_irpj=lucro_tributavel_real,
        base_calculo_csll=lucro_tributavel_real,
        irpj_basico=irpj_real,
        adicional_irpj=adic_real,
        csll=csll_real,
        total_irpj_csll=total_lucro_real,
        ibs_cbs_is_liquido=ibs_cbs_is_liquido,
        carga_tributaria_total=carga_real,
        aliquota_efetiva_percentual=aliq_efetiva_real,
        observacoes=obs_real,
    )

    # 4. Análise e recomendação
    diferenca_mensal = _round_money(abs(carga_pres - carga_real))
    diferenca_anual = _round_money(multiplicar(diferenca_mensal, Decimal("12")))

    if excede_limite:
        melhor_regime = "lucro_real"
        resumo = (
            f"Faturamento anualizado estimado (R$ {receita_anualizada:.2f}) excede o teto legal de "
            "R$ 78.000.000,00/ano do Lucro Presumido: enquadramento obrigatório no Lucro Real "
            f"(carga mensal estimada de R$ {carga_real:.2f} | {aliq_efetiva_real:.2f}%)."
        )
    elif carga_real < carga_pres:
        melhor_regime = "lucro_real"
        resumo = (
            f"Lucro Real é mais econômico: margem real ({margem_real_pct:.2f}%) abaixo da presunção legal "
            f"({presuncao_irpj_pct:.0f}%/{presuncao_csll_pct:.0f}%), gerando economia estimada de "
            f"R$ {diferenca_mensal:.2f}/mês (R$ {diferenca_anual:.2f}/ano) em IRPJ/CSLL."
        )
    elif carga_pres < carga_real:
        melhor_regime = "lucro_presumido"
        resumo = (
            f"Lucro Presumido é mais econômico: margem real ({margem_real_pct:.2f}%) superior à presunção legal "
            f"({presuncao_irpj_pct:.0f}%/{presuncao_csll_pct:.0f}%), gerando economia estimada de "
            f"R$ {diferenca_mensal:.2f}/mês (R$ {diferenca_anual:.2f}/ano) em IRPJ/CSLL."
        )
    else:
        melhor_regime = "lucro_presumido"
        resumo = (
            f"Empate técnico entre Lucro Presumido e Lucro Real (carga mensal de R$ {carga_pres:.2f}). "
            "Nesse cenário, o Lucro Presumido costuma oferecer menor custo de compliance contábil."
        )

    return ResultadoPresumidoRealMotor(
        receita_anualizada_estimada=receita_anualizada,
        lucro_contabil_mensal=lucro_contabil,
        margem_lucro_real_percentual=margem_real_pct,
        presuncao_irpj_percentual=presuncao_irpj_pct,
        presuncao_csll_percentual=presuncao_csll_pct,
        ibs_cbs_bruto=ibs_cbs_bruto,
        creditos_ibs_cbs_aproveitados=creditos_aproveitados,
        excede_limite_presumido=excede_limite,
        cenarios=[cenario_presumido, cenario_real],
        melhor_regime=melhor_regime,
        economia_mensal_reais=diferenca_mensal,
        economia_anual_estimada_reais=diferenca_anual,
        resumo_executivo=resumo,
    )
