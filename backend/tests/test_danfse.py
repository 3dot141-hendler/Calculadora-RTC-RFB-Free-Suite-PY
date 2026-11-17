"""Testes do módulo Gerador DANFSE (/api/v1/danfse)."""

from fastapi.testclient import TestClient


def test_danfse_preview_valido(client: TestClient) -> None:
    payload = {
        "numero_nfse": "20260001",
        "prestador_cnpj": "12345678000195",
        "tomador_documento": "12345678909",
        "discriminacao_servico": "Consultoria em engenharia de software tributário",
        "valor_servicos": "5000.00",
        "valor_ibs": "150.00",
        "valor_cbs": "100.00",
    }
    response = client.post("/api/v1/danfse/preview", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status_validacao"] == "VALIDO_PARA_PREVIA"
    assert data["valor_total_tributos_rtc"] == "250.00"
    assert len(data["chave_acesso_simulada"]) == 44


def test_danfse_rejeita_cnpj_invalido(client: TestClient) -> None:
    payload = {
        "numero_nfse": "20260001",
        "prestador_cnpj": "123",
        "tomador_documento": "12345678909",
        "discriminacao_servico": "Serviço",
        "valor_servicos": "100.00",
    }
    response = client.post("/api/v1/danfse/preview", json=payload)
    assert response.status_code == 422

