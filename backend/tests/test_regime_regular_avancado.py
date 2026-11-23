"""Testes das regras avançadas do Regime Regular: redução de base, crédito presumido, compra gov e ADR001."""

from fastapi.testclient import TestClient


def test_operacao_reducao_base_e_credito_presumido(client: TestClient) -> None:
    """Valida redução de base de cálculo + crédito presumido normal e em condição suspensiva."""
    payload = {
        "data_fato_gerador": "2027-06-15",
        "uf": "RS",
        "itens": [
            {
                "codigo_item": "ITEM-CRED",
                "valor_base": "1000.00",
                "c_class_trib": "000001",
                "aliquota_ibs_uf": "10.00",
                "aliquota_ibs_mun": "0.00",
                "aliquota_cbs": "8.80",
                "percentual_reducao_base": "20.00",
                "credito_presumido": {
                    "codigo_credito_presumido": 1,
                    "percentual_ibs": "5.00",
                    "percentual_cbs": "3.00",
                    "condicao_suspensiva": False,
                },
            },
            {
                "codigo_item": "ITEM-SUSP",
                "valor_base": "500.00",
                "c_class_trib": "000001",
                "aliquota_ibs_uf": "10.00",
                "aliquota_ibs_mun": "0.00",
                "aliquota_cbs": "8.80",
                "credito_presumido": {
                    "codigo_credito_presumido": 2,
                    "percentual_ibs": "4.00",
                    "percentual_cbs": "2.00",
                    "condicao_suspensiva": True,
                },
            },
        ],
    }

    resp = client.post("/api/v1/regime-regular/calcular-operacao", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    item1, item2 = data["itens"]
    assert item1["valor_base_original"] == "1000.00"
    assert item1["valor_reducao_base"] == "200.00"
    assert item1["valor_base"] == "800.00"
    assert item1["valor_ibs_uf"] == "80.00"
    assert item1["valor_cbs"] == "70.40"
    assert item1["credito_presumido"]["vBCCredPres"] == "800.00"
    assert item1["credito_presumido"]["vCredPresIBS"] == "40.00"
    assert item1["credito_presumido"]["vCredPresCBS"] == "24.00"
    assert item1["credito_presumido"]["vCredPresCondSusIBS"] == "0.00"

    assert item2["credito_presumido"]["vCredPresIBS"] == "0.00"
    assert item2["credito_presumido"]["vCredPresCondSusIBS"] == "20.00"
    assert item2["credito_presumido"]["vCredPresCondSusCBS"] == "10.00"

    assert data["total_base_calculo"] == "1300.00"
    assert data["total_reducao_base"] == "200.00"
    assert data["total_credito_presumido_ibs"] == "40.00"
    assert data["total_credito_presumido_cbs"] == "24.00"


def test_operacao_compra_governamental_sqlite_v0019_estado_vs_uniao(client: TestClient) -> None:
    """Valida consulta SQLite de transferência CBS em 2029 (10%) e simulação com redutor 50%."""
    base_payload = {
        "data_fato_gerador": "2029-05-10",
        "uf": "SP",
        "itens": [
            {
                "codigo_item": "GOV-01",
                "valor_base": "1000.00",
                "c_class_trib": "000001",
                "aliquota_ibs_uf": "10.00",
                "aliquota_ibs_mun": "0.00",
                "aliquota_cbs": "8.80",
            }
        ],
    }

    # 1) Consulta direta do SQLite em 2029: transferência CBS = 10% para Estado (tp_ente_gov=2)
    resp_sqlite = client.post(
        "/api/v1/regime-regular/calcular-operacao",
        json={**base_payload, "tp_ente_gov": 2},
    )
    assert resp_sqlite.status_code == 200
    sq = resp_sqlite.json()
    assert sq["percentual_transferencia_cbs_aplicado"] == "10.00"
    assert sq["total_cbs"] == "88.00"
    assert sq["total_cbs_transferida_ente_gov"] == "8.80"

    # 2) Simulação com redutor governamental de 50% para Estado (tp_ente_gov=2)
    resp_est = client.post(
        "/api/v1/regime-regular/calcular-operacao",
        json={**base_payload, "tp_ente_gov": 2, "percentual_redutor_compra_gov": "50.00"},
    )
    assert resp_est.status_code == 200
    est = resp_est.json()
    assert est["percentual_redutor_compra_gov_aplicado"] == "50.00"
    assert est["percentual_transferencia_cbs_aplicado"] == "10.00"
    assert est["total_ibs"] == "50.00"
    assert est["total_cbs"] == "44.00"
    assert est["total_cbs_transferida_ente_gov"] == "4.40"
    cg = est["itens"][0]["compra_governamental"]
    assert cg["ente_governamental"] == "Estado"
    assert cg["pAliqIBSUF"] == "5.00"
    assert cg["pAliqCBS"] == "4.40"
    assert cg["vCBSTransferidaEnte"] == "4.40"

    # 3) União (tp_ente_gov=1): mesmo redutor 50%, mas sem transferência CBS para outro ente
    resp_uniao = client.post(
        "/api/v1/regime-regular/calcular-operacao",
        json={**base_payload, "tp_ente_gov": 1, "percentual_redutor_compra_gov": "50.00"},
    )
    assert resp_uniao.status_code == 200
    uniao = resp_uniao.json()
    assert uniao["percentual_redutor_compra_gov_aplicado"] == "50.00"
    assert uniao["percentual_transferencia_cbs_aplicado"] == "0.00"
    assert uniao["total_cbs_transferida_ente_gov"] == "0.00"


def test_avaliador_expressao_adr001_sucesso_e_formulas(client: TestClient) -> None:
    """Valida cálculo aritmético Decimal e listagem do catálogo oficial ADR001."""
    formulas = client.get("/api/v1/regime-regular/expressao/formulas")
    assert formulas.status_code == 200
    assert "aliquota_efetiva_compra_gov" in formulas.json()

    resp = client.post(
        "/api/v1/regime-regular/expressao/avaliar",
        json={
            "expressao": "baseCalculo * aliquota * (1 - percentualReducao) * (1 - percentualReducaoCompraGov)",
            "variaveis": {
                "baseCalculo": "1000.00",
                "aliquota": "0.088",
                "percentualReducao": "0.60",
                "percentualReducaoCompraGov": "0.50",
            },
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["resultado_monetario"] == "17.60"
    assert "aliquota" in data["variaveis_utilizadas"]


def test_avaliador_expressao_adr001_bloqueia_sandbox_insegura(client: TestClient) -> None:
    """Garante que a sandbox AST bloqueia chamadas de função, imports, atributos e divisão por zero."""
    payloads_bloqueados = [
        {"expressao": "__import__('os').system('echo pwn')", "variaveis": {}},
        {"expressao": "abs(-10)", "variaveis": {}},
        {"expressao": "aliquota.__class__", "variaveis": {"aliquota": "0.10"}},
        {"expressao": "100 / 0", "variaveis": {}},
        {"expressao": "variavelInexistente * 2", "variaveis": {}},
    ]
    for payload in payloads_bloqueados:
        resp = client.post("/api/v1/regime-regular/expressao/avaliar", json=payload)
        assert resp.status_code == 422
