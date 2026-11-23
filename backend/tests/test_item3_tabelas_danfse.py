"""Testes do Item 3: Tabelas Oficiais (NCM IS, NBS, Tratamento Tributário) e XML DANFSE (interm/subst)."""

from fastapi.testclient import TestClient

XML_NFSE_INTERM_SUBST = """<?xml version="1.0" encoding="UTF-8"?>
<NFSe xmlns="http://www.sped.fazenda.gov.br/nfse">
  <infNFSe Id="NFS43149022211222333000181000000000000999">
    <nNFSe>999</nNFSe>
    <cStat>100</cStat>
    <xLocEmi>Porto Alegre</xLocEmi>
    <emit>
      <CNPJ>11222333000181</CNPJ>
      <xNome>PRESTADOR EXEMPLO LTDA</xNome>
      <enderNac>
        <xLgr>Av Borges de Medeiros</xLgr>
        <nro>1500</nro>
        <xBairro>Centro</xBairro>
        <CEP>90020020</CEP>
      </enderNac>
    </emit>
    <DPS>
      <infDPS>
        <tpAmb>1</tpAmb>
        <dCompet>2027-03-01</dCompet>
        <cLocEmi>4314902</cLocEmi>
        <subst>
          <chSubstda>NFS43149022211222333000181000000000000111</chSubstda>
          <cMotivo>01</cMotivo>
          <xMotivo>Correção de valor e alíquota IBS/CBS</xMotivo>
        </subst>
        <toma>
          <CNPJ>99888777000166</CNPJ>
          <xNome>TOMADOR CORPORATIVO SA</xNome>
        </toma>
        <interm>
          <CNPJ>55444333000122</CNPJ>
          <xNome>INTERMEDIADORA DIGITAL LTDA</xNome>
          <end>
            <xLgr>Rua dos Andradas</xLgr>
            <nro>777</nro>
            <xBairro>Centro Histórico</xBairro>
            <CEP>90020005</CEP>
            <endNac><cMun>4314902</cMun></endNac>
          </end>
        </interm>
        <serv>
          <cServ>
            <cTribNac>01.07</cTribNac>
            <cNBS>115021000</cNBS>
            <xDescServ>Intermediação de plataforma e suporte técnico</xDescServ>
          </cServ>
        </serv>
        <valores>
          <vServPrest><vServ>2500.00</vServ></vServPrest>
        </valores>
      </infDPS>
    </DPS>
    <IBSCBS>
      <CST>000</CST>
      <cClassTrib>000001</cClassTrib>
      <totCIBS>
        <gIBS><vIBSTot>250.00</vIBSTot></gIBS>
        <gCBS><vCBS>220.00</vCBS></gCBS>
      </totCIBS>
    </IBSCBS>
  </infNFSe>
</NFSe>
"""


def test_tabelas_ncm_imposto_seletivo_ad_valorem_e_ad_rem(client: TestClient) -> None:
    """Valida consulta à tabela oficial de NCMs do Imposto Seletivo (Ad Valorem e Ad Rem)."""
    resp_all = client.get("/api/v1/tabelas/ncm-is", params={"data_fato_gerador": "2027-06-01", "limit": 100})
    assert resp_all.status_code == 200
    itens = resp_all.json()
    assert len(itens) >= 2

    resp_auto = client.get("/api/v1/tabelas/ncm-is", params={"data_fato_gerador": "2027-06-01", "ncm": "87032100"})
    assert resp_auto.status_code == 200
    auto = resp_auto.json()
    assert len(auto) >= 1
    assert auto[0]["ncm"] == "87032100"
    assert auto[0]["aliquota_ad_valorem"] is not None

    resp_rem = client.get("/api/v1/tabelas/ncm-is", params={"data_fato_gerador": "2027-06-01", "ncm": "24021000"})
    assert resp_rem.status_code == 200
    rem = resp_rem.json()
    assert len(rem) >= 1
    assert any(r["aliquota_ad_rem"] == "21.30" for r in rem)


def test_tabelas_nbs_e_tratamentos_tributarios_adr001(client: TestClient) -> None:
    """Valida consulta de NBS aplicáveis e da matriz oficial TRATAMENTO_TRIBUTARIO."""
    resp_nbs = client.get("/api/v1/tabelas/nbs", params={"data_fato_gerador": "2026-06-01", "limit": 50})
    assert resp_nbs.status_code == 200
    nbs_rows = resp_nbs.json()
    assert len(nbs_rows) >= 1
    assert "nbs" in nbs_rows[0] and "c_class_trib" in nbs_rows[0]

    resp_trat = client.get(
        "/api/v1/tabelas/tratamentos-tributarios",
        params={"data_fato_gerador": "2026-06-01", "limit": 50},
    )
    assert resp_trat.status_code == 200
    trats = resp_trat.json()
    assert len(trats) >= 1
    assert any(t["expressao_tributo_calculado"] for t in trats)


def test_danfse_xml_parser_extrai_interm_e_subst_e_gera_pdf(client: TestClient) -> None:
    """Valida extração de `<interm>` e `<subst>` no parser XML e renderização no PDF binário."""
    resp_parse = client.post("/api/v1/danfse/parse-xml", json={"xml_content": XML_NFSE_INTERM_SUBST})
    assert resp_parse.status_code == 200
    parsed = resp_parse.json()
    assert parsed["intermediario_nome"] == "INTERMEDIADORA DIGITAL LTDA"
    assert parsed["intermediario_documento"] == "55.444.333/0001-22"
    assert "Rua dos Andradas" in parsed["intermediario_endereco"]
    assert "Porto Alegre" in parsed["intermediario_municipio"]
    assert parsed["chave_nfse_substituida"] == "NFS43149022211222333000181000000000000111"
    assert "01" in parsed["motivo_substituicao"]

    resp_pdf = client.post("/api/v1/danfse/pdf-from-xml", json={"xml_content": XML_NFSE_INTERM_SUBST})
    assert resp_pdf.status_code == 200
    assert resp_pdf.headers["content-type"] == "application/pdf"
    assert resp_pdf.content.startswith(b"%PDF-")
    assert len(resp_pdf.content) > 2000
