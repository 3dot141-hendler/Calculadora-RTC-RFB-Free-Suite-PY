"""Testes do módulo Regime Regular (/api/v1/regime-regular)."""

from fastapi.testclient import TestClient


def test_regime_regular_calcular_com_creditos(client: TestClient) -> None:
    payload = {
        "valor_operacao": "1000.00",
        "aliquota_ibs_uf": "10.00",
        "aliquota_ibs_mun": "7.00",
        "aliquota_cbs": "8.80",
        "aliquota_is": "0.00",
        "percentual_reducao": "0.00",
        "creditos_anteriores": "58.00",
    }
    response = client.post("/api/v1/regime-regular/calcular", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["total_bruto_tributos"] == "258.00"
    assert data["creditos_aproveitados"] == "58.00"
    assert data["valor_liquido_a_recolher"] == "200.00"


def test_base_calculo_cibs_valida_composicao_e_vigencia(client: TestClient) -> None:
    payload = {
        "ano_fato_gerador": 2026,
        "valor_bem": "1000.00",
        "frete": "100.00",
        "imposto_seletivo": "50.00",
        "icms": "180.00",
        "pis": "16.50",
        "desconto_incondicional": "20.00",
    }
    response = client.post("/api/v1/regime-regular/base-calculo/cbs-ibs", json=payload)
    assert response.status_code == 200
    assert response.json()["base_calculo"] == "933.50"


def test_base_calculo_cibs_rejeita_pis_em_2027(client: TestClient) -> None:
    payload = {
        "ano_fato_gerador": 2027,
        "valor_bem": "1000.00",
        "pis": "10.00",
    }
    response = client.post("/api/v1/regime-regular/base-calculo/cbs-ibs", json=payload)
    assert response.status_code == 422
    assert "2027" in response.json()["detail"]


def test_base_calculo_is_rejeita_ano_anterior_a_2027(client: TestClient) -> None:
    payload = {
        "ano_fato_gerador": 2026,
        "valor_bem": "1000.00",
    }
    response = client.post("/api/v1/regime-regular/base-calculo/is-mercadorias", json=payload)
    assert response.status_code == 422
    assert "2027" in response.json()["detail"]


def test_base_calculo_rejeita_valor_negativo(client: TestClient) -> None:
    payload = {
        "ano_fato_gerador": 2026,
        "valor_bem": "100.00",
        "desconto_incondicional": "150.00",
    }
    response = client.post("/api/v1/regime-regular/base-calculo/cbs-ibs", json=payload)
    assert response.status_code == 422

