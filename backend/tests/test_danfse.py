"""Testes do módulo Gerador DANFSE (/api/v1/danfse)."""

from fastapi.testclient import TestClient


def test_danfse_preview_valido(client: TestClient) -> None:
    payload = {
        "numero_nfse": "20260001",
        "prestador_cnpj": "12345678000195",
        "tomador_documento": "12345678909",
        "discriminacao_servico": "Consultoria em engenharia de software tributário",
        "valor_servicos": "5000.00",
        "valor_ibs": "150.00",
        "valor_cbs": "100.00",
    }
    response = client.post("/api/v1/danfse/preview", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status_validacao"] == "VALIDO_PARA_PREVIA"
    assert data["valor_total_tributos_rtc"] == "250.00"
    assert data["prestador_cnpj_formatado"] == "12.345.678/0001-95"
    assert data["tomador_documento_formatado"] == "123.456.789-09"
    assert data["situacao"] == "valida"
    assert data["marca_dagua"] == ""
    assert len(data["chave_acesso_simulada"]) == 44


def test_danfse_marca_dagua_cancelada(client: TestClient) -> None:
    payload = {
        "numero_nfse": "20260002",
        "prestador_cnpj": "12345678000195",
        "tomador_documento": "12345678909",
        "discriminacao_servico": "Serviço cancelado",
        "valor_servicos": "1000.00",
        "situacao_stc": 2,
    }
    response = client.post("/api/v1/danfse/preview", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["situacao"] == "cancelada"
    assert data["marca_dagua"] == "CANCELADA"


def test_danfse_rejeita_cnpj_invalido(client: TestClient) -> None:
    payload = {
        "numero_nfse": "20260001",
        "prestador_cnpj": "123",
        "tomador_documento": "12345678909",
        "discriminacao_servico": "Serviço",
        "valor_servicos": "100.00",
    }
    response = client.post("/api/v1/danfse/preview", json=payload)
    assert response.status_code == 422


def test_danfse_parse_xml_nacional_valido(client: TestClient) -> None:
    xml_sample = """<?xml version="1.0" encoding="UTF-8"?>
    <NFSe versao="1.00" xmlns="http://www.sped.fazenda.gov.br/nfse">
      <infNFSe Id="NFS431490222123456780001950000000000001">
        <nNFSe>1042</nNFSe>
        <cStat>100</cStat>
        <emit>
          <CNPJ>12345678000195</CNPJ>
          <xNome>Tech Tributária Ltda</xNome>
        </emit>
        <DPS>
          <infDPS>
            <cLocEmi>4314902</cLocEmi>
            <toma>
              <CPF>12345678909</CPF>
              <xNome>João da Silva</xNome>
            </toma>
            <serv>
              <cServ>
                <xDescServ>Desenvolvimento de API Fiscal</xDescServ>
              </cServ>
            </serv>
            <valores>
              <vServPrest>
                <vServ>3500.00</vServ>
              </vServPrest>
            </valores>
          </infDPS>
        </DPS>
      </infNFSe>
    </NFSe>
    """
    response = client.post("/api/v1/danfse/parse-xml", json={"xml_content": xml_sample})
    assert response.status_code == 200
    data = response.json()
    assert data["numero_nfse"] == "1042"
    assert data["cstat_descricao"] == "NFS-e Regular"
    assert data["prestador_documento"] == "12.345.678/0001-95"
    assert data["tomador_documento"] == "123.456.789-09"
    assert data["valor_servicos"] == "3500.00"
    assert data["municipio_emissao"] == "Porto Alegre - RS"


def test_danfse_parse_xml_rejeita_doctype_xxe(client: TestClient) -> None:
    malicious_xml = '<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><NFSe/>'
    response = client.post("/api/v1/danfse/parse-xml", json={"xml_content": malicious_xml})
    assert response.status_code == 422
    assert "DOCTYPE" in response.json()["detail"]

