"""Testes de integração da Etapa 4: ICMS UF + ISS municipal + transição EC 132 nos motores."""

from decimal import Decimal
from fastapi.testclient import TestClient


def test_comparador_2027_iss_porto_alegre_blinda_simples_das(client: TestClient) -> None:
    """Em 2027 (Porto Alegre, 01.01 -> ISS 2%): DAS=0 de ISS municipal; Híbrido/Regular=100% ISS + CBS cheia + IBS 0,1%."""
    resp = client.post(
        "/api/v1/comparador/simular",
        json={
            "receita_bruta_12m": "600000.00",
            "valor_operacao": "10000.00",
            "anexo": "III",
            "uf": "RS",
            "data_fato_gerador": "2027-06-01",
            "aplicar_transicao_ano": True,
            "tipo_tributo_local": "iss",
            "codigo_ibge": 4314902,
            "codigo_servico_iss": "01.01",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    trans = data["transicao_tributo_local"]
    assert trans["ano"] == 2027
    assert trans["origem_aliquota_local"] == "portal_nfse"
    assert Decimal(trans["aliquota_local_cheia"]) == Decimal("2.00")
    assert Decimal(trans["aliquota_local_efetiva"]) == Decimal("2.0000")
    assert Decimal(data["aliquota_ibs_uf_aplicada"]) == Decimal("0.1000")
    assert Decimal(data["aliquota_cbs_aplicada"]) == Decimal("8.8000")

    cenarios = {c["id"]: c for c in data["cenarios"]}
    # Regra de ouro: Simples DAS JAMAIS aplica ISS municipal!
    assert Decimal(cenarios["simples_das"]["valor_tributo_local"]) == Decimal("0.00")
    # Simples Híbrido e Regime Regular aplicam 2% de R$ 10.000 = R$ 200,00
    assert Decimal(cenarios["simples_hibrido"]["valor_tributo_local"]) == Decimal("200.00")
    assert Decimal(cenarios["regime_regular"]["valor_tributo_local"]) == Decimal("200.00")
    # Regime Regular: R$ 10,00 (IBS 0,1%) + R$ 880,00 (CBS 8,8%) + R$ 200,00 (ISS 2%) = R$ 1.090,00
    assert Decimal(cenarios["regime_regular"]["carga_tributaria_total"]) == Decimal("1090.00")


def test_comparador_2029_e_2033_escada_gradual_iss(client: TestClient) -> None:
    """Em 2029 ISS reduz para 90% (1,80% sobre 2,00%); em 2033 ISS é 0,00% (extinto)."""
    base_payload = {
        "receita_bruta_12m": "600000.00",
        "valor_operacao": "10000.00",
        "anexo": "III",
        "uf": "RS",
        "aplicar_transicao_ano": True,
        "tipo_tributo_local": "iss",
        "codigo_ibge": 4314902,
        "codigo_servico_iss": "01.01",
    }
    r2029 = client.post("/api/v1/comparador/simular", json={**base_payload, "data_fato_gerador": "2029-05-01"}).json()
    assert Decimal(r2029["transicao_tributo_local"]["aliquota_local_efetiva"]) == Decimal("1.8000")
    cen_2029 = {c["id"]: c for c in r2029["cenarios"]}
    assert Decimal(cen_2029["regime_regular"]["valor_tributo_local"]) == Decimal("180.00")

    r2033 = client.post("/api/v1/comparador/simular", json={**base_payload, "data_fato_gerador": "2033-05-01"}).json()
    assert Decimal(r2033["transicao_tributo_local"]["aliquota_local_efetiva"]) == Decimal("0.0000")
    cen_2033 = {c["id"]: c for c in r2033["cenarios"]}
    assert Decimal(cen_2033["regime_regular"]["valor_tributo_local"]) == Decimal("0.00")


def test_comparador_municipio_nao_parametrizado_e_override_manual(client: TestClient) -> None:
    """Campinas (3509502) sem manual retorna origem='nao_parametrizado'; com manual=3.50 calcula normalmente."""
    r_sem = client.post(
        "/api/v1/comparador/simular",
        json={
            "receita_bruta_12m": "500000.00",
            "valor_operacao": "10000.00",
            "uf": "SP",
            "data_fato_gerador": "2027-06-01",
            "aplicar_transicao_ano": True,
            "tipo_tributo_local": "iss",
            "codigo_ibge": 3509502,
            "codigo_servico_iss": "01.07",
        },
    ).json()
    assert r_sem["transicao_tributo_local"]["origem_aliquota_local"] == "nao_parametrizado"
    assert Decimal(r_sem["transicao_tributo_local"]["aliquota_local_efetiva"]) == Decimal("0.0000")

    r_manual = client.post(
        "/api/v1/comparador/simular",
        json={
            "receita_bruta_12m": "500000.00",
            "valor_operacao": "10000.00",
            "uf": "SP",
            "data_fato_gerador": "2027-06-01",
            "aplicar_transicao_ano": True,
            "tipo_tributo_local": "iss",
            "codigo_ibge": 3509502,
            "codigo_servico_iss": "01.07",
            "aliquota_iss_manual": "3.50",
        },
    ).json()
    assert r_manual["transicao_tributo_local"]["origem_aliquota_local"] == "manual"
    cen = {c["id"]: c for c in r_manual["cenarios"]}
    assert Decimal(cen["regime_regular"]["valor_tributo_local"]) == Decimal("350.00")


def test_presumido_vs_real_2027_com_icms_uf_automatico(client: TestClient) -> None:
    """Em 2027 com tipo='icms' e UF='RS', resolve ICMS modal 17% (R$ 17.000 sobre R$ 100.000) em ambos os regimes."""
    resp = client.post(
        "/api/v1/comparador/presumido-vs-real",
        json={
            "receita_bruta_mensal": "100000.00",
            "despesas_dedutiveis_mensais": "85000.00",
            "atividade": "COMERCIO_INDUSTRIA",
            "uf": "RS",
            "data_fato_gerador": "2027-06-01",
            "aplicar_transicao_ano": True,
            "tipo_tributo_local": "icms",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["transicao_tributo_local"]["origem_aliquota_local"] == "tabela_icms_uf"
    assert Decimal(data["transicao_tributo_local"]["aliquota_local_efetiva"]) == Decimal("17.0000")
    for cen in data["cenarios"]:
        assert Decimal(cen["valor_tributo_local"]) == Decimal("17000.00")


def test_regime_regular_operacao_com_icms_rs_transicao_2027_e_2033(client: TestClient) -> None:
    """Operação Regime Regular com ICMS RS (17%): R$ 170,00 em 2027 e R$ 0,00 (extinto) em 2033."""
    payload_base = {
        "uf": "RS",
        "aplicar_transicao_ano": True,
        "tipo_tributo_local": "icms",
        "itens": [{"codigo_item": "PROD-01", "valor_base": "1000.00", "aliquota_ibs_mun": "7.00"}],
    }
    r2027 = client.post(
        "/api/v1/regime-regular/calcular-operacao",
        json={**payload_base, "data_fato_gerador": "2027-06-01"},
    )
    assert r2027.status_code == 200
    d27 = r2027.json()
    assert d27["total_tributo_local"] == "170.00"
    assert d27["total_ibs"] == "1.00"    # 0,10% de R$ 1.000
    assert d27["total_cbs"] == "88.00"   # 8,80% de R$ 1.000
    assert d27["total_geral_operacao"] == "259.00"

    r2033 = client.post(
        "/api/v1/regime-regular/calcular-operacao",
        json={**payload_base, "data_fato_gerador": "2033-06-01"},
    )
    assert r2033.status_code == 200
    d33 = r2033.json()
    assert d33["total_tributo_local"] == "0.00"
    assert d33["total_ibs"] == "170.00"  # 10% UF + 7% Mun
    assert d33["total_cbs"] == "88.00"
    assert d33["total_geral_operacao"] == "258.00"
