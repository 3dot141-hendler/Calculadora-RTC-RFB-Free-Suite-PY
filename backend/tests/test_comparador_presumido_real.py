"""Testes do Comparador Lucro Presumido vs. Lucro Real (+ IBS/CBS no Regime Regular)."""

from decimal import Decimal

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_presumido_vence_servicos_alta_margem_com_adicional_irpj() -> None:
    """Serviços com margem real de 45% (> presunção de 32%) favorecem Lucro Presumido."""
    response = client.post(
        "/api/v1/comparador/presumido-vs-real",
        json={
            "receita_bruta_mensal": "500000.00",
            "despesas_dedutiveis_mensais": "275000.00",
            "atividade": "SERVICOS_GERAIS",
            "data_fato_gerador": "2026-06-01",
            "uf": "SP",
            "c_class_trib": "000001",
            "creditos_ibs_cbs": "14000.00",
        },
    )
    assert response.status_code == 200
    body = response.json()

    assert body["melhor_regime"] == "lucro_presumido"
    assert body["excede_limite_presumido"] is False
    assert Decimal(body["margem_lucro_real_percentual"]) == Decimal("45.00")
    assert Decimal(body["presuncao_irpj_percentual"]) == Decimal("32.00")

    cenarios = {c["id"]: c for c in body["cenarios"]}
    # Presumido: base 32% de 500k = 160k -> IRPJ 24k + Adic (140k*10%=14k) + CSLL (160k*9%=14.4k) = 52.4k
    assert Decimal(cenarios["lucro_presumido"]["base_calculo_irpj"]) == Decimal("160000.00")
    assert Decimal(cenarios["lucro_presumido"]["irpj_basico"]) == Decimal("24000.00")
    assert Decimal(cenarios["lucro_presumido"]["adicional_irpj"]) == Decimal("14000.00")
    assert Decimal(cenarios["lucro_presumido"]["csll"]) == Decimal("14400.00")
    assert Decimal(cenarios["lucro_presumido"]["total_irpj_csll"]) == Decimal("52400.00")

    # Real: lucro 225k -> IRPJ 33.75k + Adic (205k*10%=20.5k) + CSLL (225k*9%=20.25k) = 74.5k
    assert Decimal(cenarios["lucro_real"]["total_irpj_csll"]) == Decimal("74500.00")
    assert Decimal(body["economia_mensal_reais"]) == Decimal("22100.00")
    assert Decimal(body["economia_anual_estimada_reais"]) == Decimal("265200.00")


def test_lucro_real_vence_comercio_margem_apertada() -> None:
    """Comércio com margem real de 4% (< presunção 8%/12%) economiza no Lucro Real."""
    response = client.post(
        "/api/v1/comparador/presumido-vs-real",
        json={
            "receita_bruta_mensal": "600000.00",
            "despesas_dedutiveis_mensais": "576000.00",
            "atividade": "COMERCIO_INDUSTRIA",
            "uf": "SP",
            "c_class_trib": "000001",
            "creditos_ibs_cbs": "80000.00",
        },
    )
    assert response.status_code == 200
    body = response.json()

    assert body["melhor_regime"] == "lucro_real"
    assert Decimal(body["lucro_contabil_mensal"]) == Decimal("24000.00")
    assert Decimal(body["margem_lucro_real_percentual"]) == Decimal("4.00")
    assert Decimal(body["economia_mensal_reais"]) > Decimal("0.00")


def test_prejuizo_fiscal_zera_irpj_csll_no_lucro_real() -> None:
    """Com despesas maiores que receita, IRPJ e CSLL zeram no Lucro Real."""
    response = client.post(
        "/api/v1/comparador/presumido-vs-real",
        json={
            "receita_bruta_mensal": "400000.00",
            "despesas_dedutiveis_mensais": "430000.00",
            "atividade": "COMERCIO_INDUSTRIA",
            "uf": "SP",
            "c_class_trib": "200028",
            "creditos_ibs_cbs": "10000.00",
        },
    )
    assert response.status_code == 200
    body = response.json()
    cenarios = {c["id"]: c for c in body["cenarios"]}

    assert Decimal(body["reducao_ibs_percentual"]) == Decimal("60.00")
    assert Decimal(cenarios["lucro_real"]["total_irpj_csll"]) == Decimal("0.00")
    assert Decimal(cenarios["lucro_presumido"]["total_irpj_csll"]) > Decimal("0.00")
    assert body["melhor_regime"] == "lucro_real"


def test_receita_acima_78_milhoes_obriga_lucro_real() -> None:
    """Receita mensal acima de R$ 6,5 milhões (> R$ 78 mi/ano) bloqueia elegibilidade do Presumido."""
    response = client.post(
        "/api/v1/comparador/presumido-vs-real",
        json={
            "receita_bruta_mensal": "7000000.00",
            "despesas_dedutiveis_mensais": "3000000.00",
            "atividade": "SERVICOS_GERAIS",
            "uf": "SP",
            "c_class_trib": "000001",
            "creditos_ibs_cbs": "200000.00",
        },
    )
    assert response.status_code == 200
    body = response.json()
    cenarios = {c["id"]: c for c in body["cenarios"]}

    assert body["excede_limite_presumido"] is True
    assert cenarios["lucro_presumido"]["elegivel"] is False
    assert cenarios["lucro_real"]["elegivel"] is True
    assert body["melhor_regime"] == "lucro_real"
