"""Tabelas progressivas oficiais da LC 123/2006 (Anexos I a V) para cálculo do DAS.

Fórmula oficial:
    AliquotaEfetiva = ((RBT12 * AliquotaNominal) - ParcelaADeduzir) / RBT12
"""

from dataclasses import dataclass
from decimal import Decimal

from app.core.rounding import dividir, multiplicar, subtrair
from .schemas import AnexoSimples


@dataclass(frozen=True)
class FaixaSimples:
    """Faixa de faturamento (RBT12) do Simples Nacional."""

    limite_superior: Decimal
    aliquota_nominal: Decimal  # fração decimal (ex.: 0.0400 = 4,00%)
    parcela_deduzir: Decimal


_TABELAS_LC123: dict[AnexoSimples, tuple[FaixaSimples, ...]] = {
    AnexoSimples.ANEXO_I: (
        FaixaSimples(Decimal("180000.00"), Decimal("0.0400"), Decimal("0.00")),
        FaixaSimples(Decimal("360000.00"), Decimal("0.0730"), Decimal("5940.00")),
        FaixaSimples(Decimal("720000.00"), Decimal("0.0950"), Decimal("13860.00")),
        FaixaSimples(Decimal("1800000.00"), Decimal("0.1070"), Decimal("22500.00")),
        FaixaSimples(Decimal("3600000.00"), Decimal("0.1430"), Decimal("87300.00")),
        FaixaSimples(Decimal("4800000.00"), Decimal("0.1900"), Decimal("378000.00")),
    ),
    AnexoSimples.ANEXO_II: (
        FaixaSimples(Decimal("180000.00"), Decimal("0.0450"), Decimal("0.00")),
        FaixaSimples(Decimal("360000.00"), Decimal("0.0780"), Decimal("5940.00")),
        FaixaSimples(Decimal("720000.00"), Decimal("0.1000"), Decimal("13860.00")),
        FaixaSimples(Decimal("1800000.00"), Decimal("0.1120"), Decimal("22500.00")),
        FaixaSimples(Decimal("3600000.00"), Decimal("0.1470"), Decimal("85500.00")),
        FaixaSimples(Decimal("4800000.00"), Decimal("0.3000"), Decimal("720000.00")),
    ),
    AnexoSimples.ANEXO_III: (
        FaixaSimples(Decimal("180000.00"), Decimal("0.0600"), Decimal("0.00")),
        FaixaSimples(Decimal("360000.00"), Decimal("0.1120"), Decimal("9360.00")),
        FaixaSimples(Decimal("720000.00"), Decimal("0.1350"), Decimal("17640.00")),
        FaixaSimples(Decimal("1800000.00"), Decimal("0.1600"), Decimal("35640.00")),
        FaixaSimples(Decimal("3600000.00"), Decimal("0.2100"), Decimal("125640.00")),
        FaixaSimples(Decimal("4800000.00"), Decimal("0.3300"), Decimal("648000.00")),
    ),
    AnexoSimples.ANEXO_IV: (
        FaixaSimples(Decimal("180000.00"), Decimal("0.0450"), Decimal("0.00")),
        FaixaSimples(Decimal("360000.00"), Decimal("0.0900"), Decimal("8100.00")),
        FaixaSimples(Decimal("720000.00"), Decimal("0.1020"), Decimal("12420.00")),
        FaixaSimples(Decimal("1800000.00"), Decimal("0.1400"), Decimal("39780.00")),
        FaixaSimples(Decimal("3600000.00"), Decimal("0.2200"), Decimal("183780.00")),
        FaixaSimples(Decimal("4800000.00"), Decimal("0.3300"), Decimal("828000.00")),
    ),
    AnexoSimples.ANEXO_V: (
        FaixaSimples(Decimal("180000.00"), Decimal("0.1550"), Decimal("0.00")),
        FaixaSimples(Decimal("360000.00"), Decimal("0.1800"), Decimal("4500.00")),
        FaixaSimples(Decimal("720000.00"), Decimal("0.1950"), Decimal("9900.00")),
        FaixaSimples(Decimal("1800000.00"), Decimal("0.2050"), Decimal("17100.00")),
        FaixaSimples(Decimal("3600000.00"), Decimal("0.2300"), Decimal("62100.00")),
        FaixaSimples(Decimal("4800000.00"), Decimal("0.3050"), Decimal("540000.00")),
    ),
}


def calcular_aliquota_efetiva_lc123(anexo: AnexoSimples, rbt12: Decimal) -> Decimal:
    """Calcula a alíquota efetiva (fração decimal) pela faixa progressiva da LC 123/2006."""
    faixas = _TABELAS_LC123[anexo]
    faixa_selecionada = next((f for f in faixas if rbt12 <= f.limite_superior), faixas[-1])

    if rbt12 <= Decimal("0.00"):
        return faixa_selecionada.aliquota_nominal

    bruto = multiplicar(rbt12, faixa_selecionada.aliquota_nominal)
    liquido = subtrair(bruto, faixa_selecionada.parcela_deduzir)
    return dividir(liquido, rbt12)
