"""Testes do orquestrador multi-itens e observabilidade VSN-* do Simples Nacional."""

from fastapi.testclient import TestClient


def _operacao_base(**overrides):
    payload = {
        "id": "op-sn-001",
        "versao": "2.0.0",
        "data": "2027-03-15",
        "tpDoc": "55",
        "CRT": "1",
        "itens": [
            {
                "numero": 1,
                "cAtivSN": "01",
                "cClassTrib": "000001",
                "baseCalculo": "1000.00",
                "valorImpostoSeletivo": "0.00",
                "pIBSSN": "1.25",
                "pCBSSN": "2.75",
            }
        ],
    }
    payload.update(overrides)
    return payload


def test_observabilidade_lote_multi_itens_crt1_e_nao_calculado(client: TestClient) -> None:
    payload = _operacao_base(
        itens=[
            {
                "numero": 2,
                "cAtivSN": "01",
                "cClassTrib": "000001",
                "baseCalculo": "500.00",
                "valorImpostoSeletivo": "20.00",
                "pIBSSN": "1.00",
                "pCBSSN": "2.00",
            },
            {
                "numero": 1,
                "cAtivSN": "04",
                "cClassTrib": "000001",
                "baseCalculo": "1000.00",
                "valorImpostoSeletivo": "0.00",
                "pIBSSN": "1.25",
                "pCBSSN": "2.75",
            },
            {
                # cAtivSN desconhecido -> NAO_CALCULADO (sem erro, contribui só para vRBSNtot)
                "numero": 3,
                "cAtivSN": "99",
                "cClassTrib": "000001",
                "baseCalculo": "300.00",
                "valorImpostoSeletivo": "0.00",
            },
        ]
    )
    res = client.post("/api/v1/simples/observabilidade/calcular", json=payload)
    assert res.status_code == 200
    data = res.json()

    # Ordenação garantida por nObj
    assert [o["nObj"] for o in data["objetos"]] == [1, 2, 3]
    assert data["objetos"][0]["estadoItem"] == "CALCULADO"
    assert data["objetos"][1]["estadoItem"] == "CALCULADO"
    assert data["objetos"][2]["estadoItem"] == "NAO_CALCULADO"
    assert "erros" not in data["objetos"][2]

    # Totais: vRBSNtot = 1000 + 500 + 300 = 1800; vBC = 1000 + 500 = 1500
    # vIBSSNtot = 12.50 + 5.00 = 17.50; vCBSSNtot = 27.50 + 10.00 = 37.50; totalIs = 20.00
    # totalTributos = 17.50 + 37.50 + 20.00 = 75.00
    tot = data["total"]
    assert tot["vRBSNtot"] == "1800.00"
    assert tot["vBC"] == "1500.00"
    assert tot["vIBSSNtot"] == "17.50"
    assert tot["vCBSSNtot"] == "37.50"
    assert tot["totalIs"] == "20.00"
    assert tot["totalTributos"] == "75.00"


def test_observabilidade_crt2_suprime_ibs_e_nao_exige_pibssn(client: TestClient) -> None:
    payload = _operacao_base(
        CRT="2",
        itens=[
            {
                "numero": 1,
                "cAtivSN": "01",
                "cClassTrib": "000001",
                "baseCalculo": "1000.00",
                "valorImpostoSeletivo": "0.00",
                "pCBSSN": "2.75",
            }
        ],
    )
    res = client.post("/api/v1/simples/observabilidade/calcular", json=payload)
    assert res.status_code == 200
    data = res.json()

    tc = data["objetos"][0]["tribCalc"]
    assert "vIBSSN" not in tc
    assert "pIBSSN" not in tc
    assert tc["vCBSSN"] == "27.50"
    assert "vIBSSNtot" not in data["total"]
    assert data["total"]["vCBSSNtot"] == "27.50"
    assert data["total"]["totalTributos"] == "27.50"


def test_observabilidade_crt3_tpregime2_direciona_para_pendente_suspenso(client: TestClient) -> None:
    payload = _operacao_base(CRT="3", tpRegimeIBSCBS="2")
    res = client.post("/api/v1/simples/observabilidade/calcular", json=payload)
    assert res.status_code == 200
    data = res.json()

    tc = data["objetos"][0]["tribCalc"]
    assert tc["vIBSSN"] == "0.00"
    assert tc["vIBSPendSusp"] == "12.50"
    assert tc["vCBSSN"] == "0.00"
    assert tc["vCBSPendSusp"] == "27.50"
    assert data["total"]["vIBSSNtotPendSusp"] == "12.50"
    assert data["total"]["vCBSSNtotPendSusp"] == "27.50"
    assert data["total"]["totalTributos"] == "0.00"


def test_observabilidade_compra_gov_lote_e_sem_vigencia_vsn025(client: TestClient) -> None:
    # Em 2027, fator = 0.20 (SQLite) -> pIBS = 1.00 + 2.00*0.20 = 1.40; pCBS = 2.00*(1-0.20) = 1.60
    payload = _operacao_base(
        data="2027-06-01",
        tpEnteGov="3",
        itens=[
            {
                "numero": 1,
                "cAtivSN": "04",
                "cClassTrib": "000001",
                "baseCalculo": "1000.00",
                "valorImpostoSeletivo": "0.00",
                "pIBSSN": "1.00",
                "pCBSSN": "2.00",
            }
        ],
    )
    res = client.post("/api/v1/simples/observabilidade/calcular", json=payload)
    assert res.status_code == 200
    tc = res.json()["objetos"][0]["tribCalc"]
    assert tc["pIBSSN"] == "1.40"
    assert tc["pCBSSN"] == "1.60"

    # Em 2025 não há vigência de compra governamental -> VSN-025 (HTTP 422)
    payload_2025 = _operacao_base(data="2025-01-15", tpEnteGov="2")
    res_2025 = client.post("/api/v1/simples/observabilidade/calcular", json=payload_2025)
    assert res_2025.status_code == 422
    codigos = [e["codigo"] for e in res_2025.json()["erros"]]
    assert "VSN-025" in codigos


def test_observabilidade_regras_escopo_crt_tpregime_tpdoc(client: TestClient) -> None:
    # CRT=1 + tpRegimeIBSCBS=2 -> VSN-018
    r1 = client.post(
        "/api/v1/simples/observabilidade/calcular",
        json=_operacao_base(CRT="1", tpRegimeIBSCBS="2"),
    )
    assert r1.status_code == 422
    assert "VSN-018" in [e["codigo"] for e in r1.json()["erros"]]

    # CRT=4 (MEI) -> VSN-019
    r2 = client.post(
        "/api/v1/simples/observabilidade/calcular",
        json=_operacao_base(CRT="4"),
    )
    assert r2.status_code == 422
    assert "VSN-019" in [e["codigo"] for e in r2.json()["erros"]]

    # CRT=3 sem tpRegimeIBSCBS -> VSN-019
    r3 = client.post(
        "/api/v1/simples/observabilidade/calcular",
        json=_operacao_base(CRT="3"),
    )
    assert r3.status_code == 422
    assert "VSN-019" in [e["codigo"] for e in r3.json()["erros"]]

    # tpDoc=77 (sem tratamento) + tpEnteGov=9 + itens vazio
    r4 = client.post(
        "/api/v1/simples/observabilidade/calcular",
        json=_operacao_base(tpDoc="77", tpEnteGov="9", itens=[]),
    )
    assert r4.status_code == 422
    cods = {e["codigo"] for e in r4.json()["erros"]}
    assert {"VSN-015", "VSN-024", "VSN-011"}.issubset(cods)


def test_observabilidade_erros_por_item_isolados_no_lote(client: TestClient) -> None:
    payload = _operacao_base(
        itens=[
            {
                "numero": 1,
                "cAtivSN": "01",
                "cClassTrib": "000001",
                "baseCalculo": "1000.00",
                "valorImpostoSeletivo": "0.00",
                "pIBSSN": "1.25",
                "pCBSSN": "2.75",
            },
            {
                # cAtivSN='90' incompatível com tpRBSN=1 (VSN-023) e pCBSSN ausente (VSN-004)
                "numero": 2,
                "cAtivSN": "90",
                "cClassTrib": "000001",
                "baseCalculo": "500.00",
                "valorImpostoSeletivo": "0.00",
                "pIBSSN": "1.00",
            },
            {
                # cClassTrib inexistente (VSN-021) e base negativa (VSN-002)
                "numero": 3,
                "cAtivSN": "01",
                "cClassTrib": "999999",
                "baseCalculo": "-50.00",
                "valorImpostoSeletivo": "0.00",
            },
        ]
    )
    res = client.post("/api/v1/simples/observabilidade/calcular", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["objetos"][0]["estadoItem"] == "CALCULADO"
    assert data["objetos"][1]["estadoItem"] == "INCONSISTENCIA_ENTRADA"
    erros_item_2 = {e["codigo"]: e["pointer"] for e in data["objetos"][1]["erros"]}
    assert erros_item_2["VSN-023"] == "#/itens/1/cAtivSN"
    assert erros_item_2["VSN-004"] == "#/itens/1/pCBSSN"

    assert data["objetos"][2]["estadoItem"] == "INCONSISTENCIA_ENTRADA"
    erros_item_3 = {e["codigo"] for e in data["objetos"][2]["erros"]}
    assert {"VSN-021", "VSN-002"}.issubset(erros_item_3)

    # Totais contabilizam apenas o item 1 válido
    assert data["total"]["vRBSNtot"] == "1000.00"
    assert data["total"]["totalTributos"] == "40.00"


def test_catalogo_erros_vsn_endpoint(client: TestClient) -> None:
    res_all = client.get("/api/v1/simples/observabilidade/erros")
    assert res_all.status_code == 200
    lista = res_all.json()
    codigos = {item["codigo"] for item in lista}
    assert {"VSN-001", "VSN-018", "VSN-023", "VSN-027", "VSN-999"}.issubset(codigos)
    # Códigos aposentados nunca podem aparecer
    assert "VSN-008" not in codigos
    assert "VSN-009" not in codigos

    res_one = client.get("/api/v1/simples/observabilidade/erros", params={"codigo": "VSN-018"})
    assert res_one.status_code == 200
    assert res_one.json()["codigo"] == "VSN-018"

    res_retired = client.get("/api/v1/simples/observabilidade/erros", params={"codigo": "VSN-008"})
    assert res_retired.status_code == 404
