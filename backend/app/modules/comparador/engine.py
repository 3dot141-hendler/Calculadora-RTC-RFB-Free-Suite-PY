"""Motor puro de simulação comparativa: Simples DAS vs. Simples Híbrido vs. Regime Regular."""

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
from app.modules.simples.schemas import AnexoSimples
from app.modules.simples.tabelas_lc123 import calcular_aliquota_efetiva_lc123
from .schemas import CenarioComparativo

_FRACAO_IBS_CBS_NO_DAS = Decimal("0.20")
_FRACAO_DAS_RESIDUAL_HIBRIDO = Decimal("0.80")


def _round_money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)


def _round_rate(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)


@dataclass(frozen=True, slots=True)
class InsumoComparador:
    """Parâmetros já resolvidos para cálculo puro dos 3 cenários tributários."""

    receita_bruta_12m: Decimal
    valor_operacao: Decimal
    anexo: AnexoSimples
    aliquota_ibs_uf: Decimal
    aliquota_ibs_mun: Decimal
    aliquota_cbs: Decimal
    aliquota_is: Decimal
    reducao_ibs: Decimal
    reducao_cbs: Decimal
    creditos_anteriores: Decimal
    percentual_vendas_b2b: Decimal


@dataclass(frozen=True, slots=True)
class ResultadoComparadorMotor:
    """Resultado consolidado do motor puro de comparação tributária."""

    cenarios: list[CenarioComparativo]
    melhor_cenario_carga_propria: str
    economia_maxima_reais: Decimal
    melhor_cenario_competitividade_b2b: str
    resumo_executivo: str


def _calcular_aliquota_efetiva_operacao(carga_total: Decimal, valor_operacao: Decimal) -> Decimal:
    return _round_rate(multiplicar_por_cem(dividir(carga_total, valor_operacao)))


def executar_comparacao_regimes(insumo: InsumoComparador) -> ResultadoComparadorMotor:
    """Compara Simples Unificado (DAS), Simples Híbrido (por fora) e Regime Regular."""
    base = _round_money(insumo.valor_operacao)
    fator_b2b = dividir_por_cem(insumo.percentual_vendas_b2b)

    # 1. Alíquota efetiva oficial do Simples Nacional (LC 123/2006)
    aliq_das_decimal = calcular_aliquota_efetiva_lc123(insumo.anexo, insumo.receita_bruta_12m)
    valor_das_cheio = _round_money(multiplicar(base, aliq_das_decimal))
    parcela_ibs_cbs_das = _round_money(multiplicar(valor_das_cheio, _FRACAO_IBS_CBS_NO_DAS))
    das_residual_hibrido = _round_money(multiplicar(valor_das_cheio, _FRACAO_DAS_RESIDUAL_HIBRIDO))

    # 2. Tributos do Regime Regular (IBS UF + IBS Mun + CBS + IS) com reduções oficiais
    fator_red_ibs = subtrair(Decimal("1"), dividir_por_cem(insumo.reducao_ibs))
    fator_red_cbs = subtrair(Decimal("1"), dividir_por_cem(insumo.reducao_cbs))

    valor_ibs_uf = _round_money(
        multiplicar(multiplicar(base, dividir_por_cem(insumo.aliquota_ibs_uf)), fator_red_ibs)
    )
    valor_ibs_mun = _round_money(
        multiplicar(multiplicar(base, dividir_por_cem(insumo.aliquota_ibs_mun)), fator_red_ibs)
    )
    valor_cbs = _round_money(
        multiplicar(multiplicar(base, dividir_por_cem(insumo.aliquota_cbs)), fator_red_cbs)
    )
    valor_is = _round_money(multiplicar(base, dividir_por_cem(insumo.aliquota_is)))

    ibs_cbs_bruto = _round_money(totalizar((valor_ibs_uf, valor_ibs_mun, valor_cbs)))
    creditos_ibs_cbs = _round_money(min(insumo.creditos_anteriores, ibs_cbs_bruto))
    ibs_cbs_liquido = _round_money(ibs_cbs_bruto - creditos_ibs_cbs)

    # --- Cenário A: Simples Nacional Unificado (DAS) ---
    cred_b2b_das = _round_money(multiplicar(parcela_ibs_cbs_das, fator_b2b))
    custo_b2b_das = _round_money(base - cred_b2b_das)
    cenario_das = CenarioComparativo(
        id="simples_das",
        nome="Simples Nacional (DAS Unificado)",
        subtitulo=f"Anexo {insumo.anexo.value} • Recolhimento único via DAS",
        carga_tributaria_total=valor_das_cheio,
        aliquota_efetiva_percentual=_calcular_aliquota_efetiva_operacao(valor_das_cheio, base),
        valor_das=valor_das_cheio,
        valor_ibs_cbs_bruto=parcela_ibs_cbs_das,
        valor_ibs_cbs_liquido=parcela_ibs_cbs_das,
        valor_is=Decimal("0.00"),
        creditos_aproveitados=Decimal("0.00"),
        credito_gerado_cliente_b2b=cred_b2b_das,
        custo_efetivo_cliente_b2b=custo_b2b_das,
        observacoes=(
            "Recolhimento simplificado no DAS (LC 123/2006). Não aproveita créditos de insumos "
            "e transfere ao comprador PJ apenas o IBS/CBS efetivamente pago no DAS."
        ),
    )

    # --- Cenário B: Simples Nacional Híbrido (IBS/CBS por fora) ---
    carga_hibrido = _round_money(totalizar((das_residual_hibrido, ibs_cbs_liquido, valor_is)))
    cred_b2b_hibrido = _round_money(multiplicar(ibs_cbs_bruto, fator_b2b))
    custo_b2b_hibrido = _round_money(base - cred_b2b_hibrido)
    cenario_hibrido = CenarioComparativo(
        id="simples_hibrido",
        nome="Simples Híbrido (IBS/CBS por Fora)",
        subtitulo=f"Anexo {insumo.anexo.value} residual + IBS/CBS no Regime Regular",
        carga_tributaria_total=carga_hibrido,
        aliquota_efetiva_percentual=_calcular_aliquota_efetiva_operacao(carga_hibrido, base),
        valor_das=das_residual_hibrido,
        valor_ibs_cbs_bruto=ibs_cbs_bruto,
        valor_ibs_cbs_liquido=ibs_cbs_liquido,
        valor_is=valor_is,
        creditos_aproveitados=creditos_ibs_cbs,
        credito_gerado_cliente_b2b=cred_b2b_hibrido,
        custo_efetivo_cliente_b2b=custo_b2b_hibrido,
        observacoes=(
            "Opção prevista na LC 214/2025: mantém IRPJ/CSLL/CPP no DAS reduzido, aproveita "
            "créditos de IBS/CBS sobre insumos e transfere crédito integral de IBS/CBS ao cliente B2B."
        ),
    )

    # --- Cenário C: Regime Regular (IBS + CBS + IS) ---
    total_bruto_regular = _round_money(totalizar((ibs_cbs_bruto, valor_is)))
    creditos_regular = _round_money(min(insumo.creditos_anteriores, total_bruto_regular))
    carga_regular = _round_money(total_bruto_regular - creditos_regular)
    cred_b2b_regular = _round_money(multiplicar(ibs_cbs_bruto, fator_b2b))
    custo_b2b_regular = _round_money(base - cred_b2b_regular)
    cenario_regular = CenarioComparativo(
        id="regime_regular",
        nome="Regime Regular (IBS / CBS / IS)",
        subtitulo="Não cumulatividade plena sobre o consumo",
        carga_tributaria_total=carga_regular,
        aliquota_efetiva_percentual=_calcular_aliquota_efetiva_operacao(carga_regular, base),
        valor_das=Decimal("0.00"),
        valor_ibs_cbs_bruto=ibs_cbs_bruto,
        valor_ibs_cbs_liquido=ibs_cbs_liquido,
        valor_is=valor_is,
        creditos_aproveitados=creditos_regular,
        credito_gerado_cliente_b2b=cred_b2b_regular,
        custo_efetivo_cliente_b2b=custo_b2b_regular,
        observacoes=(
            "Apuração integral de IBS/CBS/IS com crédito financeiro pleno. "
            "Atenção: não inclui IRPJ, CSLL e CPP (Lucro Presumido/Real), que incidem à parte."
        ),
    )

    cenarios = [cenario_das, cenario_hibrido, cenario_regular]

    # Análise comparativa de carga própria
    menor_carga = min(cenarios, key=lambda c: c.carga_tributaria_total)
    maior_carga = max(cenarios, key=lambda c: c.carga_tributaria_total)
    economia_maxima = _round_money(maior_carga.carga_tributaria_total - menor_carga.carga_tributaria_total)

    # Competitividade B2B: prioriza menor custo efetivo para o cliente PJ, desempatando por menor carga própria
    melhor_b2b = min(
        cenarios,
        key=lambda c: (c.custo_efetivo_cliente_b2b, c.carga_tributaria_total),
    )

    diferenca_credito_b2b = _round_money(
        cenario_hibrido.credito_gerado_cliente_b2b - cenario_das.credito_gerado_cliente_b2b
    )
    if insumo.percentual_vendas_b2b > Decimal("0") and diferenca_credito_b2b > Decimal("0"):
        nota_b2b = (
            f" Para clientes PJ ({insumo.percentual_vendas_b2b:.0f}% B2B), optar pelo IBS/CBS por fora "
            f"gera R$ {diferenca_credito_b2b:.2f} a mais de crédito aproveitável na cadeia."
        )
    else:
        nota_b2b = " Como não há vendas B2B com aproveitamento de crédito, prevalece a menor carga direta."

    resumo = (
        f"Menor carga própria estimada: {menor_carga.nome} "
        f"(R$ {menor_carga.carga_tributaria_total:.2f} | {menor_carga.aliquota_efetiva_percentual:.2f}%), "
        f"com economia de até R$ {economia_maxima:.2f} frente ao cenário mais oneroso."
        f"{nota_b2b}"
    )

    return ResultadoComparadorMotor(
        cenarios=cenarios,
        melhor_cenario_carga_propria=menor_carga.id,
        economia_maxima_reais=economia_maxima,
        melhor_cenario_competitividade_b2b=melhor_b2b.id,
        resumo_executivo=resumo,
    )
