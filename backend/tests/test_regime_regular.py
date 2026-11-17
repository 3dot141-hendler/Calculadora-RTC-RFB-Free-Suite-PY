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

