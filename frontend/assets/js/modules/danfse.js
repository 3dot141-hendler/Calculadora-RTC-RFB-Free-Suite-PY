/**
 * DanfseModule - Submódulo JS dedicado ao Parser XML da NFS-e Nacional,
 * prévia imprimível e download do PDF binário DANFSe v2.0 com QR Code.
 */
(function (window, document) {
  "use strict";

  const activeObjectUrls = [];

  function getTodayIso() {
    return window.BrNumber ? window.BrNumber.getTodayIso() : new Date().toISOString().slice(0, 10);
  }

  function buildSampleNfseXml() {
    const today = getTodayIso();
    return `<?xml version="1.0" encoding="UTF-8"?>
<NFSe versao="1.00" xmlns="http://www.sped.fazenda.gov.br/nfse">
  <infNFSe Id="NFS431490222123456780001950000000001042">
    <nNFSe>1042</nNFSe>
    <cStat>100</cStat>
    <dhProc>${today}T14:30:00-03:00</dhProc>
    <emit>
      <CNPJ>12345678000195</CNPJ>
      <xNome>Tech Tributária Soluções Ltda</xNome>
      <enderNac>
        <xLgr>Av. Borges de Medeiros</xLgr>
        <nro>1501</nro>
        <xBairro>Praia de Belas</xBairro>
        <CEP>90119900</CEP>
      </enderNac>
    </emit>
    <IBSCBS>
      <CST>000</CST>
      <cClassTrib>000001</cClassTrib>
      <totCIBS>
        <gIBS><vIBSTot>350.00</vIBSTot></gIBS>
        <gCBS><vCBS>308.00</vCBS></gCBS>
      </totCIBS>
    </IBSCBS>
    <DPS>
      <infDPS>
        <tpAmb>2</tpAmb>
        <dCompet>${today}</dCompet>
        <cLocEmi>4314902</cLocEmi>
        <toma>
          <CPF>12345678909</CPF>
          <xNome>João da Silva</xNome>
          <end>
            <endNac><cMun>4314902</cMun></endNac>
            <xLgr>Rua dos Andradas</xLgr>
            <nro>1234</nro>
            <xBairro>Centro Histórico</xBairro>
          </end>
        </toma>
        <serv>
          <cServ>
            <cTribNac>010101</cTribNac>
            <cNBS>115011000</cNBS>
            <xDescServ>Desenvolvimento de API Fiscal Reforma Tributária (RTC — IBS/CBS)</xDescServ>
          </cServ>
          <infoCompl>
            <xInfComp>Serviço prestado em Porto Alegre/RS conforme LC 214/2025.</xInfComp>
          </infoCompl>
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
  }

  function formatBRL(value) {
    const num = Number(value);
    if (Number.isNaN(num)) return "R$ 0,00";
    return num.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
  }

  function toApiNum(raw, fallback = "0.00") {
    if (window.BrNumber) return window.BrNumber.parseToApiDecimal(raw, fallback);
    const cleaned = String(raw ?? "").trim().replace(",", ".");
    return cleaned === "" ? fallback : cleaned;
  }

  function extractFilename(contentDisposition, fallback) {
    if (!contentDisposition) return fallback;
    const match = /filename="?([^";]+)"?/i.exec(contentDisposition);
    return match ? match[1] : fallback;
  }

  function showStatusBanner(container, html, isReplace = false) {
    if (!container) return;
    const prev = container.querySelector(".danfse-pdf-banner");
    if (prev) prev.remove();
    const wrapper = document.createElement("div");
    wrapper.className = "danfse-pdf-banner mb-3";
    wrapper.innerHTML = html;
    if (isReplace) {
      container.replaceChildren(wrapper);
    } else {
      container.prepend(wrapper);
    }
  }

  async function downloadPdf(endpoint, payload, fallbackFilename, buttonEl, statusContainer) {
    const prevHtml = buttonEl ? buttonEl.innerHTML : "";
    if (buttonEl) {
      buttonEl.disabled = true;
      buttonEl.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Gerando PDF...';
    }

    try {
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        cache: "no-store",
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        let msg = `Erro HTTP ${res.status}`;
        if (res.status === 404) {
          msg = `Endpoint ${endpoint} não encontrado (HTTP 404). Reinicie o servidor backend (uvicorn) para carregar as novas rotas de PDF.`;
        } else {
          try {
            const errData = await res.json();
            msg = typeof errData.detail === "string" ? errData.detail : JSON.stringify(errData.detail);
          } catch {
            // Mantém mensagem HTTP
          }
        }
        showStatusBanner(
          statusContainer,
          `<div class="alert alert-danger mb-0"><i class="bi bi-exclamation-triangle-fill me-1"></i>${msg}</div>`
        );
        return;
      }

      const contentType = res.headers.get("Content-Type") || "";
      if (!contentType.includes("application/pdf")) {
        showStatusBanner(
          statusContainer,
          `<div class="alert alert-warning mb-0">Resposta inesperada do servidor (<code>${contentType || "sem Content-Type"}</code>). Verifique se o backend FastAPI está ativo em <code>http://127.0.0.1:8000</code>.</div>`
        );
        return;
      }

      const blob = await res.blob();
      const filename = extractFilename(res.headers.get("Content-Disposition"), fallbackFilename);
      const url = URL.createObjectURL(blob);
      activeObjectUrls.push(url);
      if (activeObjectUrls.length > 5) {
        URL.revokeObjectURL(activeObjectUrls.shift());
      }

      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();

      const sizeKb = (blob.size / 1024).toFixed(1).replace(".", ",");
      showStatusBanner(
        statusContainer,
        `<div class="alert alert-success d-flex flex-wrap justify-content-between align-items-center gap-2 mb-0">
          <span><i class="bi bi-check-circle-fill me-1"></i>PDF oficial gerado: <strong>${filename}</strong> (${sizeKb} KB)</span>
          <span class="d-flex gap-2">
            <a href="${url}" download="${filename}" class="btn btn-sm btn-success"><i class="bi bi-download me-1"></i>Baixar novamente</a>
            <a href="${url}" target="_blank" rel="noopener noreferrer" class="btn btn-sm btn-outline-success"><i class="bi bi-box-arrow-up-right me-1"></i>Abrir PDF</a>
          </span>
        </div>`
      );
    } catch (err) {
      showStatusBanner(
        statusContainer,
        `<div class="alert alert-danger mb-0"><i class="bi bi-wifi-off me-1"></i>Falha ao conectar com a API (${err.message}). Verifique se o servidor FastAPI está em execução.</div>`
      );
    } finally {
      if (buttonEl) {
        buttonEl.disabled = false;
        buttonEl.innerHTML = prevHtml;
      }
    }
  }

  function readPreviewPayload(form) {
    return {
      numero_nfse: form.elements.numero_nfse.value,
      prestador_cnpj: form.elements.prestador_cnpj.value.replace(/\D/g, ""),
      tomador_documento: form.elements.tomador_documento.value.replace(/\D/g, ""),
      discriminacao_servico: form.elements.discriminacao_servico.value,
      valor_servicos: toApiNum(form.elements.valor_servicos.value),
      valor_ibs: toApiNum(form.elements.valor_ibs.value),
      valor_cbs: toApiNum(form.elements.valor_cbs.value),
      situacao_stc: Number(form.elements.situacao_stc.value),
    };
  }

  function renderDanfseSheet(container, data, rawXml) {
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
      <strong class="d-block">DANFSe v2.0 — Documento Auxiliar da NFS-e</strong>
      <small class="text-muted">Número: <strong>${data.numero_nfse}</strong> | Situação: <strong>${data.cstat} - ${data.cstat_descricao}</strong></small>
    `;

    const body = document.createElement("div");
    body.className = "row g-2 small";
    const fields = [
      ["Prestador", `${data.prestador_nome} (${data.prestador_documento})`],
      ["Tomador", `${data.tomador_nome} (${data.tomador_documento})`],
      ["Município Emissão", data.municipio_emissao || "-"],
      ["Discriminação", data.discriminacao_servico],
      ["Valor dos Serviços", formatBRL(data.valor_servicos)],
      ["IBS / CBS Apurado", `IBS ${formatBRL(data.valor_ibs)} • CBS ${formatBRL(data.valor_cbs)} (CST/cClass: ${data.cst_cclasstrib || "-"})`],
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
    actions.className = "mt-3 d-flex flex-wrap gap-2 d-print-none";

    const pdfBtn = document.createElement("button");
    pdfBtn.type = "button";
    pdfBtn.className = "btn btn-sm btn-dark";
    pdfBtn.innerHTML = '<i class="bi bi-file-earmark-pdf-fill me-1"></i>Baixar PDF Oficial (QR Code)';
    pdfBtn.addEventListener("click", () => {
      downloadPdf(
        "/api/v1/danfse/pdf-from-xml",
        { xml_content: rawXml },
        `DANFSE_${data.numero_nfse || "xml"}.pdf`,
        pdfBtn,
        container
      );
    });

    const printBtn = document.createElement("button");
    printBtn.type = "button";
    printBtn.className = "btn btn-sm btn-outline-dark";
    printBtn.innerHTML = '<i class="bi bi-printer me-1"></i>Imprimir Prévia HTML';
    printBtn.addEventListener("click", () => window.print());

    actions.append(pdfBtn, printBtn);
    sheet.append(header, body, actions);
    container.appendChild(sheet);
  }

  // Delegação global blindada contra re-renders ou ordem de carregamento dos partials
  document.addEventListener("click", (event) => {
    const target = event.target instanceof Element ? event.target : null;
    if (!target) return;

    const previewPdfBtn = target.closest("#danfseDownloadPdfBtn");
    if (previewPdfBtn) {
      const form = document.getElementById("danfseForm");
      const resultEl = document.getElementById("danfseResult");
      if (!form) return;
      const payload = readPreviewPayload(form);
      downloadPdf(
        "/api/v1/danfse/pdf",
        payload,
        `DANFSE_${payload.numero_nfse || "preview"}.pdf`,
        previewPdfBtn,
        resultEl
      );
      return;
    }

    const sampleBtn = target.closest("#loadSampleXmlBtn");
    if (sampleBtn) {
      const xmlInput = document.getElementById("danfseXmlInput");
      if (xmlInput) xmlInput.value = buildSampleNfseXml();
      return;
    }

    const xmlPdfBtn = target.closest("#danfseXmlPdfBtn");
    if (xmlPdfBtn) {
      const xmlInput = document.getElementById("danfseXmlInput");
      const resultEl = document.getElementById("danfseXmlResult");
      if (!xmlInput) return;
      if (!xmlInput.value.trim()) {
        xmlInput.value = buildSampleNfseXml();
      }
      downloadPdf(
        "/api/v1/danfse/pdf-from-xml",
        { xml_content: xmlInput.value },
        "DANFSE_xml.pdf",
        xmlPdfBtn,
        resultEl
      );
    }
  });

  document.addEventListener("submit", async (event) => {
    const form = event.target instanceof HTMLFormElement ? event.target : null;
    if (!form || form.id !== "danfseXmlForm") return;

    event.preventDefault();
    const xmlInput = document.getElementById("danfseXmlInput");
    const resultEl = document.getElementById("danfseXmlResult");
    if (!xmlInput || !resultEl) return;

    try {
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
      renderDanfseSheet(resultEl, data, xmlInput.value);
    } catch (err) {
      resultEl.innerHTML = `<div class="alert alert-danger mb-0">Falha ao conectar com a API: ${err.message}</div>`;
    }
  });
})(window, document);
