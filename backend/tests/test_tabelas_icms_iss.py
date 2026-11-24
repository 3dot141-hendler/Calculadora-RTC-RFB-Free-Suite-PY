"""Testes HTTP dos endpoints de ICMS UF, ISS municipal (5 shards regionais) e regra de transição."""

from fastapi.testclient import TestClient
import pytest


def test_endpoint_icms_ufs_retorna_27_ufs_e_filtro_rs_rj(client: TestClient) -> None:
    """Valida retorno das 27 UFs e filtro individual para RS (17%) e RJ (20% + 2% FECP)."""
    resp = client.get("/api/v1/tabelas/icms-ufs", params={"data_fato_gerador": "2026-11-23"})
    assert resp.status_code == 200
    ufs = resp.json()
    assert len(ufs) == 27

    resp_rs = client.get("/api/v1/tabelas/icms-ufs", params={"uf": "rs", "data_fato_gerador": "2026-11-23"})
    assert resp_rs.status_code == 200
    rs = resp_rs.json()
    assert len(rs) == 1
    assert rs[0]["aliquota_interna"] == "17.00"
    assert rs[0]["aliquota_total"] == "17.00"

    resp_rj = client.get("/api/v1/tabelas/icms-ufs", params={"uf": "RJ", "data_fato_gerador": "2026-11-23"})
    assert resp_rj.status_code == 200
    rj = resp_rj.json()[0]
    assert rj["aliquota_interna"] == "20.00"
    assert rj["aliquota_fcp"] == "2.00"
    assert rj["aliquota_total"] == "22.00"


def test_endpoint_iss_servicos_catalogo(client: TestClient) -> None:
    """Valida consulta ao catálogo de serviços cTribNac / LC 116."""
    resp = client.get("/api/v1/tabelas/iss-servicos", params={"q": "01.01"})
    assert resp.status_code == 200
    itens = resp.json()
    assert len(itens) >= 1
    assert itens[0]["subitem_lc116"] == "01.01"
    assert "sistemas" in itens[0]["descricao"].lower()


@pytest.mark.parametrize(
    ("codigo_ibge", "regiao_esperada"),
    [
        (1721000, "Norte"),         # Palmas (TO)
        (2927408, "Nordeste"),      # Salvador (BA)
        (3205309, "Sudeste"),       # Vitória (ES)
        (4314902, "Sul"),           # Porto Alegre (RS)
        (5208707, "Centro-Oeste"),  # Goiânia (GO)
    ],
)
def test_endpoint_iss_municipal_roteia_5_shards_regionais(
    client: TestClient, codigo_ibge: int, regiao_esperada: str
) -> None:
    """Valida lookup real em todas as 5 regiões IBGE via subitem LC 116 (01.01)."""
    resp = client.get(
        "/api/v1/tabelas/iss-municipal",
        params={
            "codigo_ibge": codigo_ibge,
            "codigo_servico": "01.01",
            "data_fato_gerador": "2027-06-01",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["regiao"] == regiao_esperada
    assert data["encontrado"] is True
    assert data["municipio_parametrizado"] is True
    assert data["origem"] == "portal_nfse"
    assert data["aliquota_iss"] is not None
    assert data["regra_transicao"]["ano"] == 2027
    assert data["regra_transicao"]["percentual_icms_iss"] == "100.00"


@pytest.mark.parametrize(
    "codigo_ibge",
    [
        3509502,  # Campinas (SP)
        2611606,  # Recife (PE)
        3548500,  # Santos (SP)
        3518800,  # Guarulhos (SP)
        3303302,  # Niterói (RJ)
        3550308,  # São Paulo (SP)
        5300108,  # Brasília (DF)
    ],
)
def test_endpoint_iss_municipal_retorna_nao_parametrizado_para_cidades_ausentes(
    client: TestClient, codigo_ibge: int
) -> None:
    """Cidades ausentes no Portal Nacional devem retornar origem='nao_parametrizado' e aliquota=None."""
    resp = client.get(
        "/api/v1/tabelas/iss-municipal",
        params={
            "codigo_ibge": codigo_ibge,
            "codigo_servico": "01.07",
            "data_fato_gerador": "2027-06-01",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["encontrado"] is False
    assert data["municipio_parametrizado"] is False
    assert data["origem"] == "nao_parametrizado"
    assert data["aliquota_iss"] is None
    assert "não parametrizado" in data["mensagem"].lower()


def test_endpoint_transicao_dinamica_por_data(client: TestClient) -> None:
    """Valida endpoint GET /api/v1/tabelas/transicao para 2026, 2027, 2029 e 2033."""
    r2027 = client.get("/api/v1/tabelas/transicao", params={"data_fato_gerador": "2027-03-01"}).json()
    assert r2027["percentual_icms_iss"] == "100.00"
    assert r2027["percentual_cbs"] == "100.00"
    assert r2027["aliquota_ibs_fixa"] == "0.10"

    r2029 = client.get("/api/v1/tabelas/transicao", params={"data_fato_gerador": "2029-03-01"}).json()
    assert r2029["percentual_icms_iss"] == "90.00"
    assert r2029["percentual_ibs"] == "10.00"

    r2033 = client.get("/api/v1/tabelas/transicao", params={"data_fato_gerador": "2033-01-01"}).json()
    assert r2033["percentual_icms_iss"] == "0.00"
    assert r2033["percentual_ibs"] == "100.00"
