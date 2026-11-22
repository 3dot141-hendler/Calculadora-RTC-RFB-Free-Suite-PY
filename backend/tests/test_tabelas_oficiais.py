"""Testes para o módulo de tabelas oficiais (SQLite somente-leitura ADR004)."""

from datetime import date
from pathlib import Path
import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.core.database import readonly_session
from app.modules.tabelas_oficiais.repository import obter_fator_compra_gov_simples
from app.modules.tabelas_oficiais.seed import ensure_reference_db

_UFS_ESPERADAS = {
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO",
    "MA", "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR",
    "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO",
}


def test_banco_somente_leitura_impede_escrita(tmp_path: Path) -> None:
    db_file = ensure_reference_db(tmp_path / "test_rtc.db")
    with readonly_session(db_file) as conn:
        with pytest.raises(sqlite3.OperationalError):
            conn.execute("DELETE FROM uf_aliquota_referencia")


def test_vigencia_fator_compra_gov_por_ano(tmp_path: Path) -> None:
    db_file = ensure_reference_db(tmp_path / "test_vigencia.db")
    assert obter_fator_compra_gov_simples(date(2026, 6, 1), db_file)["fator"] == "0.10"
    assert obter_fator_compra_gov_simples(date(2027, 6, 1), db_file)["fator"] == "0.20"
    assert obter_fator_compra_gov_simples(date(2028, 6, 1), db_file)["fator"] == "0.50"
    assert obter_fator_compra_gov_simples(date(2025, 12, 31), db_file) is None


def test_endpoints_tabelas_oficiais(client: TestClient) -> None:
    res_cst_all = client.get("/api/v1/tabelas/cst")
    assert res_cst_all.status_code == 200
    all_csts = res_cst_all.json()
    assert len(all_csts) >= 150

    res_cst = client.get("/api/v1/tabelas/cst?cst=200")
    assert res_cst.status_code == 200
    cst_200 = res_cst.json()
    assert len(cst_200) >= 50
    by_code = {item["c_class_trib"]: item for item in cst_200}
    assert by_code["200003"]["aliquota_reducao_ibs"] == "100.00"
    assert by_code["200028"]["aliquota_reducao_ibs"] == "60.00"

    res_cst_q = client.get("/api/v1/tabelas/cst?q=200028")
    assert res_cst_q.status_code == 200
    assert any(item["c_class_trib"] == "200028" for item in res_cst_q.json())

    res_cst_410 = client.get("/api/v1/tabelas/cst?cst=410")
    assert res_cst_410.status_code == 200
    assert any(
        item["c_class_trib"] == "410001" and item["aliquota_reducao_ibs"] == "100.00"
        for item in res_cst_410.json()
    )

    res_ativ = client.get("/api/v1/tabelas/atividades-simples")
    assert res_ativ.status_code == 200
    atividades = res_ativ.json()
    assert len(atividades) == 15
    ativ_by_code = {item["codigo"]: item for item in atividades}
    assert "04" in ativ_by_code
    assert ativ_by_code["09"]["anexo_sem_fator_r"] == "III"
    assert ativ_by_code["09"]["anexo_com_fator_r"] == "V"
    assert ativ_by_code["90"]["anexo_sem_fator_r"] is None

    res_gov = client.get("/api/v1/tabelas/compra-gov-simples?data_fato_gerador=2027-05-01")
    assert res_gov.status_code == 200
    assert res_gov.json()["fator"] == "0.20"

    res_gov_404 = client.get("/api/v1/tabelas/compra-gov-simples?data_fato_gerador=2025-01-01")
    assert res_gov_404.status_code == 404

    res_ufs = client.get("/api/v1/tabelas/ufs")
    assert res_ufs.status_code == 200
    ufs = res_ufs.json()
    assert len(ufs) == 27
    assert {item["uf"] for item in ufs} == _UFS_ESPERADAS

    res_loc = client.get("/api/v1/tabelas/localidades?uf=RS&nome=Porto")
    assert res_loc.status_code == 200
    assert any(item["codigo_ibge"] == 4314902 for item in res_loc.json())


def test_cobertura_nacional_uf_e_cclasstrib_no_comparador_e_regime_regular(
    client: TestClient,
) -> None:
    # UF CE (antes ausente) + cClassTrib 011002 (Planos de assistência à saúde, redução 60%)
    res_rr = client.post(
        "/api/v1/regime-regular/calcular",
        json={
            "data_fato_gerador": "2026-06-01",
            "uf": "CE",
            "c_class_trib": "011002",
            "valor_operacao": "1000.00",
            "aliquota_ibs_mun": "0.00",
        },
    )
    assert res_rr.status_code == 200
    assert res_rr.json()["valor_ibs_uf"] == "40.00"
    assert res_rr.json()["valor_cbs"] == "35.20"

    res_comp = client.post(
        "/api/v1/comparador/simular",
        json={
            "receita_bruta_12m": "360000.00",
            "valor_operacao": "10000.00",
            "anexo": "III",
            "data_fato_gerador": "2026-06-01",
            "uf": "PE",
            "c_class_trib": "011002",
            "percentual_vendas_b2b": "100.00",
        },
    )
    assert res_comp.status_code == 200
    assert res_comp.json()["uf"] == "PE"
    assert res_comp.json()["reducao_ibs_percentual"] == "60.00"


def test_assets_catalogo_comparador_e_limite_de_linhas(client: TestClient) -> None:
    res_js = client.get("/assets/js/modules/comparador-catalog.js")
    assert res_js.status_code == 200
    assert "no-cache" in res_js.headers.get("cache-control", "")

    res_tip = client.get("/assets/js/overflow-tooltip.js")
    assert res_tip.status_code == 200
    assert "no-cache" in res_tip.headers.get("cache-control", "")

    res_index = client.get("/")
    assert res_index.status_code == 200
    assert "overflow-tooltip.js" in res_index.text

    root = Path(__file__).resolve().parents[2]
    checked = [
        root / "scripts" / "sync_rfb_sqlite.py",
        root / "backend" / "app" / "modules" / "tabelas_oficiais" / "repository.py",
        root / "backend" / "app" / "modules" / "tabelas_oficiais" / "router.py",
        root / "backend" / "app" / "modules" / "tabelas_oficiais" / "seed.py",
        root / "frontend" / "partials" / "tabelas.html",
        root / "frontend" / "assets" / "js" / "modules" / "tabelas.js",
        root / "frontend" / "assets" / "js" / "modules" / "comparador-catalog.js",
        root / "frontend" / "assets" / "js" / "overflow-tooltip.js",
        root / "frontend" / "assets" / "css" / "style.css",
        root / "frontend" / "partials" / "comparador.html",
        root / "frontend" / "partials" / "regime-regular.html",
    ]
    for path in checked:
        line_count = len(path.read_text(encoding="utf-8").splitlines())
        assert line_count <= 400, f"{path.name} excedeu 400 linhas ({line_count})"
