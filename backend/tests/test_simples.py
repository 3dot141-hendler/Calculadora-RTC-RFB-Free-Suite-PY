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

