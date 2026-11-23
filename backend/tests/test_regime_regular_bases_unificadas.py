"""Testes de Base de Cálculo Unificada (NF-e/NFC-e) e Base Unificada NFS-e / Locação 99.03."""

from fastapi.testclient import TestClient


def test_base_unificada_nfe_2026_ignora_is_com_aviso(client: TestClient) -> None:
    """Em 2026 (NF-e 55 bem), vPIS/vCOFINS/vICMS deduzem RG e IS; vIS é ignorado com aviso."""
    payload = {
        "ano_fato_gerador": 2026,
        "natureza": "bem",
        "tipo_documento": 55,
        "componentes": {
            "vProd": "1000.00",
            "vFrete": "100.00",
            "vII": "50.00",
            "vIS": "80.00",
            "vDesc": "20.00",
            "vPIS": "16.50",
            "vCOFINS": "76.00",
            "vICMS": "180.00",
        },
    }
    resp = client.post("/api/v1/regime-regular/base-calculo/unificada", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    # RG: 1000 + 100 + 50 - 20 - 16.50 - 76 - 180 = 857.50
    assert data["baseRG"] == "857.50"
    assert data["baseIS"] == "857.50"
    # SN: 1000 + 100 - 20 = 1080.00 (vII e tributos legados não entram na baseSN)
    assert data["baseSN"] == "1080.00"
    assert any("vIS" in aviso and "2026" in aviso for aviso in data["avisos"])


def test_base_unificada_nfce_2027_regras_modelo_e_vigencia(client: TestClient) -> None:
    """Em 2027 (NFC-e 65 bem), vIS entra em RG e SN; vPIS e vII são ignorados com avisos."""
    payload = {
        "ano_fato_gerador": 2027,
        "natureza": "bem",
        "tipo_documento": 65,
        "componentes": {
            "vProd": "1000.00",
            "vII": "40.00",
            "vIS": "100.00",
            "vPIS": "16.50",
            "vICMS": "120.00",
        },
    }
    resp = client.post("/api/v1/regime-regular/base-calculo/unificada", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    # RG: 1000 + 100 - 120 = 980.00
    assert data["baseRG"] == "980.00"
    # IS: 1000 - 120 = 880.00 (vIS não compõe baseIS)
    assert data["baseIS"] == "880.00"
    # SN: 1000 + 100 = 1100.00
    assert data["baseSN"] == "1100.00"
    assert any("vII" in aviso and "65" in aviso for aviso in data["avisos"])
    assert any("vPIS" in aviso and "2027" in aviso for aviso in data["avisos"])


def test_base_unificada_nfse_comum_ajustes_e_leiaute_xtp(client: TestClient) -> None:
    """NFS-e comum (Não Optante) soma ajuste 101, rejeita 199 sem descrição e ignora desconhecido."""
    payload = {
        "ano_fato_gerador": 2026,
        "opSimpNac": 1,
        "situacao": "comum",
        "vServ": "1000.00",
        "vDescIncond": "50.00",
        "vISSQN": "50.00",
        "vPIS": "6.50",
        "vCOFINS": "30.00",
        "documentos": [
            {"tpAjusteBC": "101", "vAjusteAplic": "100.00"},
            {"tpAjusteBC": "199", "vAjusteAplic": "40.00"},
            {"tpAjusteBC": "999", "vAjusteAplic": "25.00"},
        ],
    }
    resp = client.post("/api/v1/regime-regular/base-calculo/unificada-nfse", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    # 1000 - 50 (desc) - 100 (ajuste 101) - 50 (ISS) - 6.50 (PIS) - 30 (COFINS) = 763.50
    assert data["baseRG"] == "763.50"
    assert data["baseSN"] is None
    assert data["vCalcAjusteBCIBSCBS"] == "100.00"
    assert any(e["codigo"] == "LEIAUTE-XTP" for e in data["erros"])
    assert any("999" in aviso for aviso in data["avisos"])


def test_base_unificada_nfse_salao_parceiro_simples(client: TestClient) -> None:
    """No Salão Parceiro optante ME/EPP (regAp=1), tipo 9 deduz apenas da baseSN."""
    payload = {
        "ano_fato_gerador": 2027,
        "opSimpNac": 3,
        "regApIBSCBSSN": 1,
        "situacao": "salaoParceiro",
        "vServ": "1000.00",
        "vDescIncond": "0.00",
        "vISSQN": "50.00",
        "documentos": [
            {"tpAjusteBC": "9", "vAjusteAplic": "300.00"},
        ],
    }
    resp = client.post("/api/v1/regime-regular/base-calculo/unificada-nfse", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    # baseRG = 1000 - 50 (ISSQN) = 950.00 (tipo 9 não deduz baseRG)
    assert data["baseRG"] == "950.00"
    # baseSN = 1000 - 300 (profissional parceiro) = 700.00
    assert data["baseSN"] == "700.00"
    assert data["erros"] == []


def test_base_unificada_nfse_locacao_9903_copropriedade_e_mei(client: TestClient) -> None:
    """Valida locação 99.03 com copropriedade 50% e retorno antecipado de MEI (E1302/E0436)."""
    loc_payload = {
        "ano_fato_gerador": 2026,
        "opSimpNac": 1,
        "situacao": "locacao9903",
        "vISSQN": "100.00",
        "vPIS": "10.00",
        "vCOFINS": "30.00",
        "locacao": {
            "pCopropriedade": "50.00",
            "vTotOper": "2000.00",
            "vDescIncondTot": "200.00",
            "somaAjustesLocImoveis": "100.00",
        },
    }
    resp_loc = client.post("/api/v1/regime-regular/base-calculo/unificada-nfse", json=loc_payload)
    assert resp_loc.status_code == 200
    loc = resp_loc.json()
    # 50%*(2000 - 200 - 100) = 850 - 10 (PIS) - 30 (COFINS) = 810.00 (ISSQN não deduz em locação!)
    assert loc["baseRG"] == "810.00"
    assert loc["baseSN"] is None
    assert loc["erros"] == []

    # MEI com documento de ajuste -> E1302 (aviso) + E0436 (erro), bases nulas
    mei_payload = {
        "ano_fato_gerador": 2026,
        "opSimpNac": 2,
        "situacao": "comum",
        "vServ": "500.00",
        "documentos": [{"tpAjusteBC": "101", "vAjusteAplic": "50.00"}],
    }
    resp_mei = client.post("/api/v1/regime-regular/base-calculo/unificada-nfse", json=mei_payload)
    assert resp_mei.status_code == 200
    mei = resp_mei.json()
    assert mei["baseRG"] is None
    assert mei["baseSN"] is None
    assert any("E1302" in a for a in mei["avisos"])
    assert any(e["codigo"] == "E0436" for e in mei["erros"])
