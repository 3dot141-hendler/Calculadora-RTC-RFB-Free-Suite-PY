"""Testes unitários do motor puro de transição constitucional (EC 132 / LC 214/2025)."""

from datetime import date
from decimal import Decimal

import pytest

from app.core.transicao_rtc import aplicar_transicao_aliquotas, obter_regra_transicao


def test_regra_default_usa_data_atual() -> None:
    """Quando data_fato_gerador é omitida, usa dinamicamente date.today()."""
    regra = obter_regra_transicao()
    assert regra.data_referencia == date.today()
    assert regra.ano == date.today().year


def test_transicao_2026_ano_teste_icms_iss_integrais() -> None:
    """Em 2026: 100% ISS/ICMS + alíquotas-teste CBS 0,90% e IBS 0,10% compensáveis."""
    res = aplicar_transicao_aliquotas(
        date(2026, 11, 23),
        aliquota_local_cheia=Decimal("5.00"),
        aliquota_ibs_cheia=Decimal("17.70"),
        aliquota_cbs_cheia=Decimal("8.80"),
    )
    assert res.regra.fase == "ano_teste_2026"
    assert res.regra.pis_cofins_vigente is True
    assert res.regra.ibs_cbs_compensaveis_teste is True
    assert res.aliquota_local_efetiva == Decimal("5.0000")
    assert res.aliquota_ibs_efetiva == Decimal("0.1000")
    assert res.aliquota_cbs_efetiva == Decimal("0.9000")
    assert res.aliquota_total_efetiva == Decimal("6.0000")


@pytest.mark.parametrize("ano", [2027, 2028])
def test_transicao_2027_2028_iss_100_porcento_cbs_cheia_ibs_01(ano: int) -> None:
    """Em 2027 e 2028: 100% ISS/ICMS + CBS cheia (8,80%) + IBS transição (0,10%)."""
    res = aplicar_transicao_aliquotas(
        date(ano, 6, 15),
        aliquota_local_cheia=Decimal("5.00"),
        aliquota_ibs_cheia=Decimal("17.70"),
        aliquota_cbs_cheia=Decimal("8.80"),
    )
    assert res.regra.fase == "transicao_cbs_cheia"
    assert res.regra.pis_cofins_vigente is False
    assert res.aliquota_local_efetiva == Decimal("5.0000")
    assert res.aliquota_cbs_efetiva == Decimal("8.8000")
    assert res.aliquota_ibs_efetiva == Decimal("0.1000")
    assert res.aliquota_total_efetiva == Decimal("13.9000")


@pytest.mark.parametrize(
    ("ano", "iss_esperado", "ibs_esperado"),
    [
        (2029, Decimal("4.5000"), Decimal("1.7700")),
        (2030, Decimal("4.0000"), Decimal("3.5400")),
        (2031, Decimal("3.5000"), Decimal("5.3100")),
        (2032, Decimal("3.0000"), Decimal("7.0800")),
    ],
)
def test_transicao_gradual_2029_a_2032(ano: int, iss_esperado: Decimal, ibs_esperado: Decimal) -> None:
    """De 2029 a 2032: redução 9/10 -> 6/10 no ISS/ICMS e subida 1/10 -> 4/10 no IBS + CBS cheia."""
    res = aplicar_transicao_aliquotas(
        date(ano, 3, 1),
        aliquota_local_cheia=Decimal("5.00"),
        aliquota_ibs_cheia=Decimal("17.70"),
        aliquota_cbs_cheia=Decimal("8.80"),
    )
    assert res.regra.fase == "transicao_gradual_ibs"
    assert res.aliquota_local_efetiva == iss_esperado
    assert res.aliquota_ibs_efetiva == ibs_esperado
    assert res.aliquota_cbs_efetiva == Decimal("8.8000")


def test_reforma_plena_2033_extingue_icms_e_iss() -> None:
    """A partir de 2033: ICMS/ISS extintos (0%), IBS 100% e CBS 100%."""
    res = aplicar_transicao_aliquotas(
        date(2033, 1, 1),
        aliquota_local_cheia=Decimal("17.00"),
        aliquota_ibs_cheia=Decimal("17.70"),
        aliquota_cbs_cheia=Decimal("8.80"),
    )
    assert res.regra.fase == "reforma_plena"
    assert res.aliquota_local_efetiva == Decimal("0.0000")
    assert res.aliquota_ibs_efetiva == Decimal("17.7000")
    assert res.aliquota_cbs_efetiva == Decimal("8.8000")
    assert res.aliquota_total_efetiva == Decimal("26.5000")


def test_simples_nacional_tradicional_ignora_tabela_municipal_e_icms() -> None:
    """Regra de ouro: Simples Nacional no DAS (LC 123) nunca aplica tabela municipal de ISS ou ICMS."""
    res = aplicar_transicao_aliquotas(
        date(2027, 6, 1),
        aliquota_local_cheia=Decimal("5.00"),
        aliquota_ibs_cheia=Decimal("17.70"),
        aliquota_cbs_cheia=Decimal("8.80"),
        simples_tradicional=True,
    )
    assert res.ignorou_tabela_local_simples_das is True
    assert res.aliquota_local_efetiva == Decimal("0.00")
    assert res.aliquota_ibs_efetiva == Decimal("0.00")
    assert res.aliquota_cbs_efetiva == Decimal("0.00")
    assert res.aliquota_total_efetiva == Decimal("0.00")
