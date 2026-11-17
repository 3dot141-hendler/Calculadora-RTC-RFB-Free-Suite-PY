"""Testes unitários para o utilitário de arredondamento (port de ArredondamentoUtils)."""

from decimal import Decimal

from app.core.rounding import (
    arredondar_interno,
    dividir_por_cem,
    formatar_aliquota,
    formatar_moeda,
    formatar_quantidade,
    multiplicar,
    totalizar,
)


def test_arredondamento_bancario_half_even() -> None:
    # 2.505 -> 2.50 (par), 2.515 -> 2.52 (par)
    assert formatar_moeda(Decimal("2.505")) == "2.50"
    assert formatar_moeda(Decimal("2.515")) == "2.52"


def test_precisao_interna_8_casas() -> None:
    assert arredondar_interno(Decimal("1.123456789")) == Decimal("1.12345679")
    assert dividir_por_cem(Decimal("30")) == Decimal("0.30000000")
    assert multiplicar(Decimal("100.00"), Decimal("0.123456789")) == Decimal("12.34567890")


def test_formatar_aliquota_2_a_4_casas() -> None:
    assert formatar_aliquota(Decimal("0.2080")) == "0.208"
    assert formatar_aliquota(Decimal("0.2000")) == "0.20"
    assert formatar_aliquota(Decimal("60.0000")) == "60.00"
    assert formatar_aliquota(Decimal("8.87555")) == "8.8756"


def test_formatar_quantidade() -> None:
    assert formatar_quantidade(Decimal("1000.0000")) == "1000"
    assert formatar_quantidade(Decimal("55.55")) == "55.5500"


def test_totalizar_sem_arredondamento_intermediario() -> None:
    valores = [Decimal("10.004"), Decimal("10.004")]
    assert totalizar(valores) == Decimal("20.008")
    assert formatar_moeda(totalizar(valores)) == "20.01"
