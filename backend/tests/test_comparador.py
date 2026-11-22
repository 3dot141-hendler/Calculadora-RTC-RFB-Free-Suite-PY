"""Testes unitários e de API para o Comparador Tributário (Simples vs. Híbrido vs. Regular)."""

from decimal import Decimal

from fastapi.testclient import TestClient


def test_comparador_comercio_b2b_resolve_sqlite_e_compara_tres_cenarios(client: TestClient) -> None:
    payload = {
        "receita_bruta_12m": "180000.00",
        "valor_operacao": "10000.00",
        "anexo": "I",
        "data_fato_gerador": "2026-06-01",
        "uf": "SP",
        "c_class_trib": "000001",
        "aliquota_ibs_mun": "0.00",
        "creditos_anteriores": "500.00",
        "percentual_vendas_b2b": "100.00",
    }
    response = client.post("/api/v1/comparador/simular", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["uf"] == "SP"
    assert Decimal(data["aliquota_ibs_uf_aplicada"]) == Decimal("10.00")
    assert Decimal(data["aliquota_cbs_aplicada"]) == Decimal("8.80")
    assert len(data["cenarios"]) == 3

    cenarios = {c["id"]: c for c in data["cenarios"]}

    # Anexo I até 180k = 4,00% -> DAS = 400.00; parcela IBS/CBS estimada (20%) = 80.00
    das = cenarios["simples_das"]
    assert Decimal(das["carga_tributaria_total"]) == Decimal("400.00")
    assert Decimal(das["credito_gerado_cliente_b2b"]) == Decimal("80.00")

    # IBS/CBS bruto SP = 1000.00 + 880.00 = 1880.00; créditos = 500.00 -> líquido = 1380.00
    # Híbrido = DAS residual (320.00) + 1380.00 = 1700.00; crédito B2B = 1880.00
    hibrido = cenarios["simples_hibrido"]
    assert Decimal(hibrido["valor_das"]) == Decimal("320.00")
    assert Decimal(hibrido["valor_ibs_cbs_liquido"]) == Decimal("1380.00")
    assert Decimal(hibrido["carga_tributaria_total"]) == Decimal("1700.00")
    assert Decimal(hibrido["credito_gerado_cliente_b2b"]) == Decimal("1880.00")

    # Regime Regular = 1880.00 - 500.00 = 1380.00; crédito B2B = 1880.00
    regular = cenarios["regime_regular"]
    assert Decimal(regular["carga_tributaria_total"]) == Decimal("1380.00")
    assert Decimal(regular["credito_gerado_cliente_b2b"]) == Decimal("1880.00")

    assert data["melhor_cenario_carga_propria"] == "simples_das"
    assert Decimal(data["economia_maxima_reais"]) == Decimal("1300.00")
    assert data["melhor_cenario_competitividade_b2b"] == "regime_regular"
    assert "crédito aproveitável" in data["resumo_executivo"]


def test_comparador_com_reducao_cclasstrib_60_porcento_e_creditos_altos(client: TestClient) -> None:
    payload = {
        "receita_bruta_12m": "1800000.00",
        "valor_operacao": "10000.00",
        "anexo": "V",
        "data_fato_gerador": "2026-06-01",
        "uf": "SP",
        "c_class_trib": "200028",
        "creditos_anteriores": "600.00",
        "percentual_vendas_b2b": "100.00",
    }
    response = client.post("/api/v1/comparador/simular", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert Decimal(data["reducao_ibs_percentual"]) == Decimal("60.00")
    assert Decimal(data["reducao_cbs_percentual"]) == Decimal("60.00")

    cenarios = {c["id"]: c for c in data["cenarios"]}
    # Com redução de 60%: IBS_UF = 400.00, CBS = 352.00 -> bruto = 752.00; créditos 600.00 -> líquido 152.00
    assert Decimal(cenarios["regime_regular"]["valor_ibs_cbs_bruto"]) == Decimal("752.00")
    assert Decimal(cenarios["regime_regular"]["carga_tributaria_total"]) == Decimal("152.00")
    assert data["melhor_cenario_carga_propria"] == "regime_regular"


def test_comparador_b2c_puro_zera_credito_b2b(client: TestClient) -> None:
    payload = {
        "receita_bruta_12m": "360000.00",
        "valor_operacao": "5000.00",
        "anexo": "III",
        "uf": "SP",
        "c_class_trib": "000001",
        "percentual_vendas_b2b": "0.00",
    }
    response = client.post("/api/v1/comparador/simular", json=payload)
    assert response.status_code == 200
    data = response.json()

    for cenario in data["cenarios"]:
        assert Decimal(cenario["credito_gerado_cliente_b2b"]) == Decimal("0.00")
        assert Decimal(cenario["custo_efetivo_cliente_b2b"]) == Decimal("5000.00")
    assert "não há vendas B2B" in data["resumo_executivo"]


def test_comparador_rejeita_rbt12_acima_do_limite_simples(client: TestClient) -> None:
    payload = {
        "receita_bruta_12m": "5000000.00",
        "valor_operacao": "1000.00",
        "anexo": "I",
    }
    response = client.post("/api/v1/comparador/simular", json=payload)
    assert response.status_code == 422
