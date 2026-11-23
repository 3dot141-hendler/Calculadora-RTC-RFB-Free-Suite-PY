"""Testes de integridade dos assets e contrato do Relatório Executivo do Comparador."""

from pathlib import Path

from fastapi.testclient import TestClient

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"


def test_comparador_report_assets_servidos_com_no_cache(client: TestClient) -> None:
    assets = [
        "/index.html",
        "/partials/comparador.html",
        "/assets/css/comparador-print.css",
        "/assets/js/modules/comparador-report-templates.js",
        "/assets/js/modules/comparador-report.js",
        "/assets/js/modules/comparador.js",
        "/assets/js/modules/comparador-presumido-real.js",
    ]
    for path in assets:
        response = client.get(path)
        assert response.status_code == 200, f"Asset indisponível: {path}"
        assert "no-cache" in response.headers.get("cache-control", "")


def test_comparador_partial_e_index_expoem_relatorio_executivo(client: TestClient) -> None:
    index_html = client.get("/index.html").text
    assert "assets/css/comparador-print.css" in index_html
    assert "assets/js/modules/comparador-report-templates.js" in index_html
    assert "assets/js/modules/comparador-report.js" in index_html

    comparador_html = client.get("/partials/comparador.html").text
    assert 'id="comparadorPrintBtn"' in comparador_html
    assert 'id="presumidoRealPrintBtn"' in comparador_html
    assert 'id="comparadorClienteNome"' in comparador_html

    print_css = client.get("/assets/css/comparador-print.css").text
    assert "@page" in print_css
    assert "body.printing-comparador-report" in print_css

    templates_js = client.get("/assets/js/modules/comparador-report-templates.js").text
    assert "window.ComparadorReportTemplates" in templates_js
    assert "buildSimplesRegularHtml" in templates_js
    assert "buildPresumidoRealHtml" in templates_js

    report_js = client.get("/assets/js/modules/comparador-report.js").text
    assert "window.ComparadorReport" in report_js


def test_arquivos_relatorio_respeitam_limite_modularizacao() -> None:
    arquivos = [
        FRONTEND_DIR / "partials" / "comparador.html",
        FRONTEND_DIR / "assets" / "css" / "comparador-print.css",
        FRONTEND_DIR / "assets" / "js" / "modules" / "comparador-report-templates.js",
        FRONTEND_DIR / "assets" / "js" / "modules" / "comparador-report.js",
        FRONTEND_DIR / "assets" / "js" / "modules" / "comparador.js",
        FRONTEND_DIR / "assets" / "js" / "modules" / "comparador-presumido-real.js",
    ]
    for arquivo in arquivos:
        linhas = len(arquivo.read_text(encoding="utf-8").splitlines())
        assert linhas <= 400, f"{arquivo.name} excedeu o teto de 400 linhas ({linhas} linhas)"
