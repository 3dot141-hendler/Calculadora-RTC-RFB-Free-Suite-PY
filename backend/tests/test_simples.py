"""Testes do módulo Simples Nacional (/api/v1/simples)."""

from fastapi.testclient import TestClient


def test_simples_info(client: TestClient) -> None:
    response = client.get("/api/v1/simples/info")
    assert response.status_code == 200
    assert response.json()["modulo"] == "simples"


def test_simples_calcular_unificado(client: TestClient) -> None:
    payload = {
        "receita_bruta_12m": "1200000.00",
        "valor_operacao": "10000.00",
        "anexo": "I",
        "recolher_ibs_cbs_por_fora": False,
    }
    response = client.post("/api/v1/simples/calcular", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["anexo"] == "I"
    assert float(data["valor_das"]) > 0
    assert data["valor_total_tributos"] == data["valor_das"]


def test_simples_rejeita_rbt12_acima_limite(client: TestClient) -> None:
    payload = {
        "receita_bruta_12m": "5000000.00",
        "valor_operacao": "1000.00",
        "anexo": "I",
    }
    response = client.post("/api/v1/simples/calcular", json=payload)
    assert response.status_code == 422


def test_simples_calcular_item_crt1(client: TestClient) -> None:
    payload = {
        "regime": "CRT_1",
        "tp_rbsn": 1,
        "c_ativ_sn_valido": True,
        "base_calculo": "1000.00",
        "valor_imposto_seletivo": "0.00",
        "p_ibs_sn": "1.50",
        "p_cbs_sn": "2.00",
    }
    response = client.post("/api/v1/simples/calcular-item", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["estado_item"] == "CALCULADO"
    assert data["trib_calc"]["v_ibs_sn"] == "15.00"
    assert data["trib_calc"]["v_cbs_sn"] == "20.00"
    assert data["trib_calc"]["total_item"] == "35.00"


def test_simples_calcular_item_rejeita_compra_gov_sem_fator(client: TestClient) -> None:
    payload = {
        "regime": "CRT_1",
        "tp_rbsn": 1,
        "c_ativ_sn_valido": True,
        "base_calculo": "1000.00",
        "p_ibs_sn": "1.50",
        "p_cbs_sn": "2.00",
        "tp_ente_gov": 3,
    }
    response = client.post("/api/v1/simples/calcular-item", json=payload)
    assert response.status_code == 422

