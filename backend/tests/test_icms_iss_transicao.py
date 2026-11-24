"""Testes de integração ponta a ponta (Etapa 6):
5 Shards Regionais ISS, 27 UFs ICMS, Escada EC 132 (2026-2033),
Retrocompatibilidade de APIs e Integridade dos Assets Frontend.
"""

from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parents[2]
FRONTEND_DIR = ROOT_DIR / "frontend"
DATABASE_DIR = ROOT_DIR / "database"


def test_cinco_shards_regionais_existem_e_respondem_via_api(client: TestClient) -> None:
    """Valida que os 5 shards SQLite regionais estão presentes e respondem via API read-only."""
    shards = [
        "iss_norte.db",
        "iss_nordeste.db",
        "iss_sudeste.db",
        "iss_sul.db",
        "iss_centro_oeste.db",
    ]
    for nome in shards:
        assert (DATABASE_DIR / nome).exists(), f"Shard ausente: {nome}"

    amostras_regioes = [
        (1100015, "Norte"),         # Alta Floresta D'Oeste/RO
        (2100055, "Nordeste"),      # Açailândia/MA
        (3100104, "Sudeste"),       # Abadia dos Dourados/MG
        (4100103, "Sul"),           # Abatiá/PR
        (5208707, "Centro-Oeste"),  # Goiânia/GO
    ]
    for ibge, regiao_esperada in amostras_regioes:
        resp = client.get(
            "/api/v1/tabelas/iss-municipal",
            params={"codigo_ibge": ibge, "codigo_servico": "01.01", "data_fato_gerador": "2026-06-15"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["regiao"] == regiao_esperada
        assert body["municipio_parametrizado"] is True
        assert body["encontrado"] is True
        assert body["origem"] == "portal_nfse"
        assert Decimal("2.00") <= Decimal(body["aliquota_iss"]) <= Decimal("5.00")


@pytest.mark.parametrize("ibge", [3509502, 3550308, 2611606, 5300108])
def test_cidades_nao_parametrizadas_retornam_status_claro_sem_inventar_aliquota(
    client: TestClient, ibge: int
) -> None:
    """Campinas, São Paulo, Recife e Brasília retornam nao_parametrizado e aliquota_iss=None."""
    resp = client.get(
        "/api/v1/tabelas/iss-municipal",
        params={"codigo_ibge": ibge, "codigo_servico": "01.01", "data_fato_gerador": "2027-03-10"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["encontrado"] is False
    assert body["municipio_parametrizado"] is False
    assert body["origem"] == "nao_parametrizado"
    assert body["aliquota_iss"] is None


def test_todas_27_ufs_icms_modal_somam_interna_mais_fcp(client: TestClient) -> None:
    """Valida cobertura das 27 UFs na tabela de ICMS modal e consistência interna + FCP = total."""
    resp = client.get("/api/v1/tabelas/icms-ufs", params={"data_fato_gerador": "2026-06-15"})
    assert resp.status_code == 200
    itens = resp.json()
    assert isinstance(itens, list)
    assert len(itens) == 27
    for item in itens:
        soma = Decimal(item["aliquota_interna"]) + Decimal(item["aliquota_fcp"])
        assert soma == Decimal(item["aliquota_total"])


def test_catalogo_servicos_iss_responde_com_limit_350(client: TestClient) -> None:
    """Valida o contrato exato usado pelo frontend (/iss-servicos?limit=350)."""
    resp = client.get("/api/v1/tabelas/iss-servicos", params={"limit": 350})
    assert resp.status_code == 200
    itens = resp.json()
    assert isinstance(itens, list)
    assert len(itens) == 333


def test_iss_origem_prestador_independente_da_uf_destino_ibs(client: TestClient) -> None:
    """LC 116 art. 3º: ISS do prestador (Goiânia/GO) resolve independente da UF Destino do IBS (SP)."""
    resp = client.post(
        "/api/v1/comparador/presumido-vs-real",
        json={
            "receita_bruta_mensal": "100000.00",
            "despesas_dedutiveis_mensais": "40000.00",
            "atividade": "SERVICOS_GERAIS",
            "data_fato_gerador": "2026-06-15",
            "uf": "SP",
            "aplicar_transicao_ano": True,
            "tipo_tributo_local": "iss",
            "codigo_ibge": 5208707,
            "codigo_servico_iss": "01.01",
        },
    )
    assert resp.status_code == 200
    trans = resp.json()["transicao_tributo_local"]
    assert trans["tipo_tributo_local"] == "iss"
    assert trans["origem_aliquota_local"] == "portal_nfse"
    assert "Goiânia" in (trans["municipio_nome"] or "")
    assert Decimal(trans["aliquota_local_cheia"]) >= Decimal("2.00")


@pytest.mark.parametrize(
    ("ano", "pct_esperado"),
    [
        (2026, "100.00"),
        (2027, "100.00"),
        (2028, "100.00"),
        (2029, "90.00"),
        (2030, "80.00"),
        (2031, "70.00"),
        (2032, "60.00"),
        (2033, "0.00"),
    ],
)
def test_escada_constitucional_completa_2026_a_2033(
    client: TestClient, ano: int, pct_esperado: str
) -> None:
    """Verifica toda a escada constitucional da EC 132/LC 214 no endpoint e no Comparador."""
    resp_regra = client.get("/api/v1/tabelas/transicao", params={"data_fato_gerador": f"{ano}-07-01"})
    assert resp_regra.status_code == 200
    assert resp_regra.json()["percentual_icms_iss"] == pct_esperado

    resp_sim = client.post(
        "/api/v1/comparador/simular",
        json={
            "receita_bruta_12m": "600000.00",
            "valor_operacao": "10000.00",
            "anexo": "III",
            "data_fato_gerador": f"{ano}-07-01",
            "uf": "RS",
            "aplicar_transicao_ano": True,
            "tipo_tributo_local": "iss",
            "aliquota_iss_manual": "5.00",
        },
    )
    assert resp_sim.status_code == 200
    sim = resp_sim.json()
    esperado_val = (Decimal("10000.00") * Decimal("5.00") * Decimal(pct_esperado) / Decimal("10000")).quantize(
        Decimal("0.01")
    )
    cenarios = {c["id"]: c for c in sim["cenarios"]}
    # Regra de Ouro Simples Nacional: DAS nunca soma ISS municipal externo
    assert cenarios["simples_das"]["valor_tributo_local"] == "0.00"
    assert Decimal(cenarios["regime_regular"]["valor_tributo_local"]) == esperado_val


def test_retrocompatibilidade_payloads_legados_sem_transicao(client: TestClient) -> None:
    """Payloads antigos (sem campos de transição/ICMS/ISS) continuam retornando 200 sem quebra."""
    r1 = client.post(
        "/api/v1/comparador/simular",
        json={"receita_bruta_12m": "500000.00", "valor_operacao": "10000.00", "anexo": "I", "uf": "RS"},
    )
    assert r1.status_code == 200
    b1 = r1.json()
    assert b1["transicao_tributo_local"] is None
    assert all(c["valor_tributo_local"] == "0.00" for c in b1["cenarios"])

    r2 = client.post(
        "/api/v1/comparador/presumido-vs-real",
        json={
            "receita_bruta_mensal": "500000.00",
            "despesas_dedutiveis_mensais": "400000.00",
            "atividade": "COMERCIO_INDUSTRIA",
            "uf": "RS",
        },
    )
    assert r2.status_code == 200
    b2 = r2.json()
    assert b2["transicao_tributo_local"] is None
    assert all(c["valor_tributo_local"] == "0.00" for c in b2["cenarios"])

    r3 = client.post(
        "/api/v1/regime-regular/calcular-operacao",
        json={
            "data_fato_gerador": "2026-06-15",
            "uf": "RS",
            "itens": [{"codigo_item": "LEG-1", "valor_base": "1000.00", "c_class_trib": "000001"}],
        },
    )
    assert r3.status_code == 200
    b3 = r3.json()
    assert b3["transicao_tributo_local"] is None
    assert b3["total_tributo_local"] == "0.00"


def test_assets_frontend_icms_iss_servidos_e_modulares(client: TestClient) -> None:
    """Valida entrega HTTP 200 no-cache, placeholder cinza-claro, contratos API e limite <= 400 linhas."""
    paths = [
        "/index.html",
        "/assets/css/style.css",
        "/partials/comparador.html",
        "/partials/regime-regular.html",
        "/partials/tabelas.html",
        "/assets/js/modules/aliquota-local-picker.js",
        "/assets/js/modules/tabelas-icms-iss.js",
        "/assets/js/modules/regime-regular-operacao.js",
    ]
    for p in paths:
        r = client.get(p)
        assert r.status_code == 200, f"Asset indisponível: {p}"
        assert "no-cache" in r.headers.get("cache-control", "")

    picker_js = client.get("/assets/js/modules/aliquota-local-picker.js").text
    assert "window.AliquotaLocalPicker" in picker_js
    assert "Insira a alíquota ISS (2% a 5%)" in picker_js
    assert "Município não parametrizado" in picker_js
    assert "UF Emissão/ISS" in picker_js
    assert "Município Emissão/ISS (Prestador)" in picker_js
    assert "iss-servicos?limit=350" in picker_js
    assert "percentual_icms_iss" in picker_js

    tab_js = client.get("/assets/js/modules/tabelas-icms-iss.js").text
    assert "iss-servicos?limit=350" in tab_js
    assert "percentual_icms_iss" in tab_js

    tabelas_html = client.get("/partials/tabelas.html").text
    assert 'id="tabIcmsIss"' in tabelas_html
    assert 'placeholder="Insira a alíquota ISS (2% a 5%)"' in tabelas_html

    comparador_html = client.get("/partials/comparador.html").text
    assert 'id="compLocalPicker"' in comparador_html
    assert 'id="prLocalPicker"' in comparador_html

    rr_html = client.get("/partials/regime-regular.html").text
    assert 'id="opLocalPicker"' in rr_html

    arquivos_modulares = [
        FRONTEND_DIR / "index.html",
        FRONTEND_DIR / "assets" / "css" / "style.css",
        FRONTEND_DIR / "partials" / "comparador.html",
        FRONTEND_DIR / "partials" / "regime-regular.html",
        FRONTEND_DIR / "partials" / "tabelas.html",
        FRONTEND_DIR / "assets" / "js" / "modules" / "aliquota-local-picker.js",
        FRONTEND_DIR / "assets" / "js" / "modules" / "tabelas-icms-iss.js",
        FRONTEND_DIR / "assets" / "js" / "modules" / "comparador.js",
        FRONTEND_DIR / "assets" / "js" / "modules" / "comparador-presumido-real.js",
        FRONTEND_DIR / "assets" / "js" / "modules" / "comparador-report-templates.js",
        FRONTEND_DIR / "assets" / "js" / "modules" / "regime-regular-operacao.js",
    ]
    for arq in arquivos_modulares:
        linhas = len(arq.read_text(encoding="utf-8").splitlines())
        assert linhas <= 400, f"{arq.name} excedeu 400 linhas ({linhas})"
