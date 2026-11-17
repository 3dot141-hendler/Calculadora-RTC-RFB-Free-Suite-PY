"""Testes unitários e de API para cálculo por operação no Regime Regular."""

from fastapi.testclient import TestClient


def test_calcular_operacao_multiplos_itens_com_reducao_e_diferimento(client: TestClient) -> None:
    payload = {
        "data_fato_gerador": "2026-06-01",
        "uf": "SP",
        "itens": [
            {
                "codigo_item": "ITEM-INTEGRAL",
                "valor_base": "1000.00",
                "c_class_trib": "000001",
                "aliquota_ibs_mun": "0.00",
            },
            {
                "codigo_item": "ITEM-EDUCACAO-DIFERIDO",
                "valor_base": "1000.00",
                "c_class_trib": "200028",
                "aliquota_ibs_mun": "0.00",
                "percentual_diferimento": "50.00",
            },
        ],
    }
    response = client.post("/api/v1/regime-regular/calcular-operacao", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["quantidade_itens"] == 2
    assert data["total_base_calculo"] == "2000.00"
    # Item 1: IBS_UF=100.00, CBS=88.00
    # Item 2: redução 60% -> bruto IBS_UF=40.00, CBS=35.20; diferimento 50% -> devido 20.00 + 17.60
    assert data["total_ibs"] == "120.00"
    assert data["total_cbs"] == "105.60"
    assert data["total_diferido"] == "37.60"
    assert data["total_geral_operacao"] == "225.60"
