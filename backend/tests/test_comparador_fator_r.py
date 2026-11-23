"""Testes do Fator R (Anexo III vs. Anexo V — regra dos 28%) no Comparador Tributário."""

from decimal import Decimal

from fastapi.testclient import TestClient

from app.modules.simples.anexos import avaliar_fator_r


def test_avaliar_fator_r_limiar_exato_28_porcento() -> None:
    # Exatamente 28% -> enquadra Anexo III, folha faltante 0.00
    res_exato = avaliar_fator_r(Decimal("280000.00"), Decimal("1000000.00"))
    assert res_exato.atingiu_minimo_28_pct is True
    assert res_exato.anexo_definido == "III"
    assert res_exato.percentual_fator_r == Decimal("28.00")
    assert res_exato.folha_minima_anexo_iii == Decimal("280000.00")
    assert res_exato.folha_faltante_anexo_iii == Decimal("0.00")

    # 27,999% (1 centavo abaixo de 28%) -> cai para Anexo V
    res_abaixo = avaliar_fator_r(Decimal("279999.99"), Decimal("1000000.00"))
    assert res_abaixo.atingiu_minimo_28_pct is False
    assert res_abaixo.anexo_definido == "V"
    assert res_abaixo.folha_faltante_anexo_iii == Decimal("0.01")


def test_comparador_fator_r_atingiu_28_enquadra_anexo_iii(client: TestClient) -> None:
    # RBT12 = 180.000, Folha 12m = 54.000 (30%) -> Anexo III (6% = R$ 600 vs. Anexo V 15,5% = R$ 1.550)
    payload = {
        "receita_bruta_12m": "180000.00",
        "valor_operacao": "10000.00",
        "anexo": "V",
        "aplicar_fator_r": True,
        "folha_salarios_12m": "54000.00",
        "uf": "SP",
        "c_class_trib": "000001",
    }
    res = client.post("/api/v1/comparador/simular", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["anexo"] == "III"
    fr = data["fator_r"]
    assert fr is not None
    assert fr["atingiu_minimo_28_pct"] is True
    assert Decimal(fr["percentual_fator_r"]) == Decimal("30.00")
    assert Decimal(fr["das_anexo_iii"]) == Decimal("600.00")
    assert Decimal(fr["das_anexo_v"]) == Decimal("1550.00")
    assert Decimal(fr["economia_das_fator_r"]) == Decimal("950.00")
    assert Decimal(fr["folha_faltante_anexo_iii"]) == Decimal("0.00")

    # Cenário Simples DAS deve refletir Anexo III (R$ 600.00)
    das = next(c for c in data["cenarios"] if c["id"] == "simples_das")
    assert Decimal(das["valor_das"]) == Decimal("600.00")


def test_comparador_fator_r_abaixo_28_enquadra_anexo_v_e_calcula_folha_faltante(
    client: TestClient,
) -> None:
    # RBT12 = 180.000, mínimo 28% = 50.400; Folha = 36.000 (20%) -> falta 14.400 (1.200/mês)
    payload = {
        "receita_bruta_12m": "180000.00",
        "valor_operacao": "10000.00",
        "anexo": "III",
        "aplicar_fator_r": True,
        "folha_salarios_12m": "36000.00",
        "uf": "SP",
        "c_class_trib": "000001",
    }
    res = client.post("/api/v1/comparador/simular", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["anexo"] == "V"
    fr = data["fator_r"]
    assert fr["atingiu_minimo_28_pct"] is False
    assert Decimal(fr["percentual_fator_r"]) == Decimal("20.00")
    assert Decimal(fr["folha_minima_anexo_iii"]) == Decimal("50400.00")
    assert Decimal(fr["folha_faltante_anexo_iii"]) == Decimal("14400.00")
    assert Decimal(fr["folha_faltante_mensal"]) == Decimal("1200.00")
    assert Decimal(fr["economia_das_fator_r"]) == Decimal("950.00")

    das = next(c for c in data["cenarios"] if c["id"] == "simples_das")
    assert Decimal(das["valor_das"]) == Decimal("1550.00")


def test_comparador_sem_fator_r_mantem_compatibilidade_retroativa(client: TestClient) -> None:
    payload = {
        "receita_bruta_12m": "180000.00",
        "valor_operacao": "10000.00",
        "anexo": "I",
    }
    res = client.post("/api/v1/comparador/simular", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["fator_r"] is None
    assert data["anexo"] == "I"
