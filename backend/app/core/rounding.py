"""Utilitário centralizado de arredondamento para a Calculadora RTC.

Port fiel de `ArredondamentoUtils.java` (Ref.: art. 349, § 14, da LC 214/2025):
- Precisão interna de 8 casas decimais em todos os cálculos intermediários.
- Modo de arredondamento HALF_EVEN (arredondamento bancário).
- Formatação final exclusivamente na camada de apresentação/serialização.
"""

from decimal import Decimal, ROUND_HALF_EVEN
from typing import Iterable

PRECISAO_INTERNA = Decimal("0.00000001")
ESCALA_MOEDA = Decimal("0.01")
ESCALA_ALIQUOTA_MAX = Decimal("0.0001")
ESCALA_QUANTIDADE = Decimal("0.0001")
CEM = Decimal("100")


def arredondar_interno(valor: Decimal) -> Decimal:
    """Aplica arredondamento interno (8 casas decimais, HALF_EVEN)."""
    return valor.quantize(PRECISAO_INTERNA, rounding=ROUND_HALF_EVEN)


def dividir_por_cem(valor: Decimal) -> Decimal:
    """Divide o valor por 100 com precisão interna (8 casas, HALF_EVEN)."""
    return (valor / CEM).quantize(PRECISAO_INTERNA, rounding=ROUND_HALF_EVEN)


def dividir(dividendo: Decimal, divisor: Decimal) -> Decimal:
    """Divisão com precisão interna (8 casas, HALF_EVEN)."""
    return (dividendo / divisor).quantize(PRECISAO_INTERNA, rounding=ROUND_HALF_EVEN)


def multiplicar(v1: Decimal, v2: Decimal) -> Decimal:
    """Multiplicação com precisão interna (8 casas, HALF_EVEN)."""
    return (v1 * v2).quantize(PRECISAO_INTERNA, rounding=ROUND_HALF_EVEN)


def subtrair(v1: Decimal, v2: Decimal) -> Decimal:
    """Subtração com precisão interna (8 casas, HALF_EVEN)."""
    return (v1 - v2).quantize(PRECISAO_INTERNA, rounding=ROUND_HALF_EVEN)


def multiplicar_por_cem(valor: Decimal) -> Decimal:
    """Multiplica o valor por 100 (operação exata, sem arredondamento)."""
    return valor * CEM


def totalizar(valores: Iterable[Decimal]) -> Decimal:
    """Soma valores sem arredondamento intermediário."""
    return sum(valores, Decimal("0"))


def formatar_moeda(valor: Decimal) -> str:
    """Formata valor monetário com exatamente 2 casas decimais (HALF_EVEN)."""
    return f"{valor.quantize(ESCALA_MOEDA, rounding=ROUND_HALF_EVEN):f}"


def formatar_aliquota(valor: Decimal) -> str:
    """Formata alíquota com 2 a 4 casas decimais (HALF_EVEN), removendo zeros extras."""
    scaled = valor.quantize(ESCALA_ALIQUOTA_MAX, rounding=ROUND_HALF_EVEN)
    text = f"{scaled:f}".rstrip("0")
    if "." in text:
        decimals = len(text.split(".")[1])
        if decimals < 2:
            text += "0" * (2 - decimals)
    else:
        text += ".00"
    return text


def formatar_quantidade(valor: Decimal) -> str:
    """Formata quantidade como inteiro se exata, senão 4 casas decimais (HALF_EVEN)."""
    normalized = valor.normalize()
    if normalized == normalized.to_integral_value():
        return str(int(normalized))
    return f"{valor.quantize(ESCALA_QUANTIDADE, rounding=ROUND_HALF_EVEN):f}"
