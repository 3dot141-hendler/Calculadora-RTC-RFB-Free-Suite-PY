/**
 * DanfseModule - Submódulo JS dedicado ao Parser XML da NFS-e Nacional
 * e prévia imprimível do DANFSE (padrão RFB).
 */
(function (window, document) {
  "use strict";

  const SAMPLE_NFSE_XML = `<?xml version="1.0" encoding="UTF-8"?>
<NFSe versao="1.00" xmlns="http://www.sped.fazenda.gov.br/nfse">
  <infNFSe Id="NFS431490222123456780001950000000001042">
    <nNFSe>1042</nNFSe>
    <cStat>100</cStat>
    <emit>
      <CNPJ>12345678000195</CNPJ>
      <xNome>Tech Tributária Soluções Ltda</xNome>
    </emit>
    <DPS>
      <infDPS>
        <toma>
          <CPF>12345678909</CPF>
          <xNome>João da Silva</xNome>
        </toma>
        <serv>
          <cServ>
            <xDescServ>Desenvolvimento de API Fiscal Reforma Tributária (RTC)</xDescServ>
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
</NFSe>`;

  function formatBRL(value) {
    const num = Number(value);
    if (Number.isNaN(num)) return "R$ 0,00";
    return num.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
  }

  function renderDanfseSheet(container, data) {
    container.replaceChildren();
    const sheet = document.createElement("div");
    sheet.className = "border rounded p-3 bg-white position-relative danfse-print-sheet";

    if (data.marca_dagua) {
      const wm = document.createElement("span");
      wm.className = "badge text-bg-danger position-absolute top-0 end-0 m-3 fs-6";
      wm.textContent = data.marca_dagua;
      sheet.appendChild(wm);
    }

    const header = document.createElement("div");
    header.className = "border-bottom pb-2 mb-3";
    header.innerHTML = `
      <strong class="d-block">DANFSE — Documento Auxiliar da NFS-e</strong>
      <small class="text-muted">Número: <strong>${data.numero_nfse}</strong> | Situação: <strong>${data.cstat} - ${data.cstat_descricao}</strong></small>
    `;

    const body = document.createElement("div");
    body.className = "row g-2 small";
    const fields = [
      ["Prestador", `${data.prestador_nome} (${data.prestador_documento})`],
      ["Tomador", `${data.tomador_nome} (${data.tomador_documento})`],
      ["Discriminação", data.discriminacao_servico],
      ["Valor dos Serviços", formatBRL(data.valor_servicos)],
      ["Chave / Id", data.chave_id || "-"],
    ];
    fields.forEach(([label, val]) => {
      const col = document.createElement("div");
      col.className = "col-12";
      const strong = document.createElement("strong");
      strong.textContent = `${label}: `;
      const span = document.createElement("span");
      span.textContent = val;
      col.append(strong, span);
      body.appendChild(col);
    });

    const actions = document.createElement("div");
    actions.className = "mt-3 d-print-none";
    const printBtn = document.createElement("button");
    printBtn.type = "button";
    printBtn.className = "btn btn-sm btn-outline-dark";
    printBtn.innerHTML = '<i class="bi bi-printer me-1"></i>Imprimir / Salvar PDF';
    printBtn.addEventListener("click", () => window.print());
    actions.appendChild(printBtn);

    sheet.append(header, body, actions);
    container.appendChild(sheet);
  }

  document.addEventListener("partial:loaded", (event) => {
    if (event.detail.route !== "danfse") return;

    const xmlForm = document.getElementById("danfseXmlForm");
    const xmlInput = document.getElementById("danfseXmlInput");
    const sampleBtn = document.getElementById("loadSampleXmlBtn");
    const resultEl = document.getElementById("danfseXmlResult");

    if (sampleBtn && xmlInput) {
      sampleBtn.addEventListener("click", () => {
        xmlInput.value = SAMPLE_NFSE_XML;
      });
    }

    if (xmlForm && xmlInput && resultEl) {
      xmlForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const res = await fetch("/api/v1/danfse/parse-xml", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ xml_content: xmlInput.value }),
        });
        const data = await res.json();
        if (!res.ok) {
          resultEl.innerHTML = `<div class="alert alert-danger mb-0">${data.detail}</div>`;
          return;
        }
        renderDanfseSheet(resultEl, data);
      });
    }
  });
})(window, document);
