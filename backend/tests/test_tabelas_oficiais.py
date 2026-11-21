"""Testes para o módulo de tabelas oficiais (SQLite somente-leitura ADR004)."""

from datetime import date
from pathlib import Path
import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.core.database import readonly_session
from app.modules.tabelas_oficiais.repository import obter_fator_compra_gov_simples
from app.modules.tabelas_oficiais.seed import ensure_reference_db


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
    res_cst = client.get("/api/v1/tabelas/cst?cst=200")
    assert res_cst.status_code == 200
    assert len(res_cst.json()) == 2

    res_ativ = client.get("/api/v1/tabelas/atividades-simples")
    assert res_ativ.status_code == 200
    assert any(item["codigo"] == "04" for item in res_ativ.json())

    res_gov = client.get("/api/v1/tabelas/compra-gov-simples?data_fato_gerador=2027-05-01")
    assert res_gov.status_code == 200
    assert res_gov.json()["fator"] == "0.20"

    res_gov_404 = client.get("/api/v1/tabelas/compra-gov-simples?data_fato_gerador=2025-01-01")
    assert res_gov_404.status_code == 404

    res_ufs = client.get("/api/v1/tabelas/ufs")
    assert res_ufs.status_code == 200
    assert len(res_ufs.json()) >= 5

    res_loc = client.get("/api/v1/tabelas/localidades?uf=RS&nome=Porto")
    assert res_loc.status_code == 200
    assert any(item["codigo_ibge"] == 4314902 for item in res_loc.json())

