/**
 * SimplesOperacaoModule - Operação em lote multi-itens e observabilidade VSN-* (NT 2026.005).
 */
(function (window, document) {
  "use strict";

  function escapeHtml(val) {
    return String(val ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function formatBRL(val) {
    if (val === undefined || val === null || val === "") return "—";
    const num = Number(val);
    if (Number.isNaN(num)) return escapeHtml(val);
    return num.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
  }

  function parseDecimal(val, fallback = "0.00") {
    if (window.BrNumber) return window.BrNumber.parseToApiDecimal(val, fallback);
    const raw = String(val ?? "").trim().replace(",", ".");
    return raw === "" ? fallback : raw;
  }

  function estadoBadge(estado) {
    if (estado === "CALCULADO") return '<span class="badge text-bg-success">CALCULADO</span>';
    if (estado === "NAO_CALCULADO") return '<span class="badge text-bg-secondary">NAO_CALCULADO</span>';
    if (estado === "NAO_IMPLEMENTADO") return '<span class="badge text-bg-info text-dark">NAO_IMPLEMENTADO</span>';
    return `<span class="badge text-bg-danger">${escapeHtml(estado)}</span>`;
  }

  function addItemRow(tbody, item = {}) {
    const idx = tbody.querySelectorAll("tr").length + 1;
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><input type="number" min="1" class="form-control form-control-sm" data-field="numero" value="${item.numero ?? idx}" /></td>
      <td><input type="text" class="form-control form-control-sm" data-field="cAtivSN" value="${escapeHtml(item.cAtivSN ?? "01")}" placeholder="01..14, 90" /></td>
      <td><input type="text" class="form-control form-control-sm" data-field="cClassTrib" value="${escapeHtml(item.cClassTrib ?? "000001")}" placeholder="000001" /></td>
      <td><input type="text" inputmode="decimal" data-br-money class="form-control form-control-sm" data-field="baseCalculo" value="${escapeHtml(item.baseCalculo ?? "1.000,00")}" /></td>
      <td><input type="text" inputmode="decimal" data-br-money class="form-control form-control-sm" data-field="valorImpostoSeletivo" value="${escapeHtml(item.valorImpostoSeletivo ?? "0,00")}" /></td>
      <td><input type="text" inputmode="decimal" data-br-money class="form-control form-control-sm" data-field="pIBSSN" value="${escapeHtml(item.pIBSSN ?? "1,25")}" /></td>
      <td><input type="text" inputmode="decimal" data-br-money class="form-control form-control-sm" data-field="pCBSSN" value="${escapeHtml(item.pCBSSN ?? "2,75")}" /></td>
      <td class="text-center">
        <button type="button" class="btn btn-sm btn-outline-danger border-0" data-remove-row title="Remover item">
          <i class="bi bi-trash"></i>
        </button>
      </td>
    `;
    tbody.appendChild(tr);
    window.BrNumber?.attachMoneyInputs(tr);
    tr.querySelector("[data-remove-row]").addEventListener("click", () => tr.remove());
  }

  function loadDefaultItems(tbody) {
    tbody.innerHTML = "";
    addItemRow(tbody, { numero: 1, cAtivSN: "01", cClassTrib: "000001", baseCalculo: "1.000,00", valorImpostoSeletivo: "0,00", pIBSSN: "1,25", pCBSSN: "2,75" });
    addItemRow(tbody, { numero: 2, cAtivSN: "04", cClassTrib: "000001", baseCalculo: "500,00", valorImpostoSeletivo: "20,00", pIBSSN: "1,00", pCBSSN: "2,00" });
  }

  function loadMixedErrorDemo(tbody) {
    tbody.innerHTML = "";
    addItemRow(tbody, { numero: 1, cAtivSN: "01", cClassTrib: "000001", baseCalculo: "1.000,00", valorImpostoSeletivo: "0,00", pIBSSN: "1,25", pCBSSN: "2,75" });
    addItemRow(tbody, { numero: 2, cAtivSN: "90", cClassTrib: "000001", baseCalculo: "400,00", valorImpostoSeletivo: "0,00", pIBSSN: "1,00", pCBSSN: "" });
    addItemRow(tbody, { numero: 3, cAtivSN: "99", cClassTrib: "000001", baseCalculo: "300,00", valorImpostoSeletivo: "0,00", pIBSSN: "", pCBSSN: "" });
  }

  function collectItems(tbody) {
    return Array.from(tbody.querySelectorAll("tr")).map((tr) => {
      const read = (field) => String(tr.querySelector(`[data-field="${field}"]`)?.value ?? "").trim();
      const numRaw = read("numero");
      const pIbsRaw = read("pIBSSN");
      const pCbsRaw = read("pCBSSN");
      return {
        numero: numRaw ? Number(numRaw) : null,
        cAtivSN: read("cAtivSN") || null,
        cClassTrib: read("cClassTrib") || null,
        baseCalculo: read("baseCalculo") ? parseDecimal(read("baseCalculo"), "0.00") : null,
        valorImpostoSeletivo: read("valorImpostoSeletivo") ? parseDecimal(read("valorImpostoSeletivo"), "0.00") : "0.00",
        pIBSSN: pIbsRaw ? parseDecimal(pIbsRaw, "") : null,
        pCBSSN: pCbsRaw ? parseDecimal(pCbsRaw, "") : null,
      };
    });
  }

  function renderErrosList(erros) {
    if (!Array.isArray(erros) || !erros.length) return "";
    return erros
      .map(
        (e) =>
          `<div class="small text-danger"><span class="badge text-bg-danger me-1">${escapeHtml(e.codigo)}</span><code>${escapeHtml(e.pointer)}</code> — ${escapeHtml(e.detail)}</div>`
      )
      .join("");
  }

  function renderObservabilidadeResult(container, data) {
    const tot = data.total;
    const totalsHtml = tot
      ? `
        <div class="row g-2 mb-3">
          <div class="col-md-3"><div class="p-2 rounded bg-light border small"><div class="text-muted">Receita Bruta (vRBSNtot)</div><strong>${formatBRL(tot.vRBSNtot)}</strong></div></div>
          <div class="col-md-3"><div class="p-2 rounded bg-light border small"><div class="text-muted">IBS Devido / Pend.</div><strong>${formatBRL(tot.vIBSSNtot)}</strong> <span class="text-muted">/ ${formatBRL(tot.vIBSSNtotPendSusp)}</span></div></div>
          <div class="col-md-3"><div class="p-2 rounded bg-light border small"><div class="text-muted">CBS Devida / Pend.</div><strong>${formatBRL(tot.vCBSSNtot)}</strong> <span class="text-muted">/ ${formatBRL(tot.vCBSSNtotPendSusp)}</span></div></div>
          <div class="col-md-3"><div class="p-2 rounded bg-success-subtle border border-success small"><div class="text-muted">Total Tributos Devidos</div><strong class="text-success">${formatBRL(tot.totalTributos)}</strong></div></div>
        </div>
      `
      : '<div class="alert alert-warning small py-2">Nenhum item produziu totais calculados (todos os itens falharam na validação).</div>';

    const rows = (data.objetos || [])
      .map((obj) => {
        const tc = obj.tribCalc;
        const detalhes = tc
          ? `vRBSN: ${formatBRL(tc.vRBSNitem)} | tpRBSN ${tc.tpRBSN} | vIBS: ${formatBRL(tc.vIBSSN)} | vCBS: ${formatBRL(tc.vCBSSN)} | Total: <strong>${formatBRL(tc.totalItem)}</strong>`
          : renderErrosList(obj.erros);
        return `
          <tr>
            <td class="fw-bold">#${obj.nObj}</td>
            <td>${estadoBadge(obj.estadoItem)}</td>
            <td class="small">${detalhes}</td>
          </tr>
        `;
      })
      .join("");

    container.innerHTML = `
      ${totalsHtml}
      <div class="table-responsive border rounded">
        <table class="table table-sm align-middle mb-0 small">
          <thead class="table-light">
            <tr><th style="width: 60px;">Item</th><th style="width: 180px;">Estado</th><th>Detalhamento / Diagnóstico VSN-*</th></tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    `;
  }

  async function toggleCatalog(catalogArea) {
    if (!catalogArea.classList.contains("d-none")) {
      catalogArea.classList.add("d-none");
      return;
    }
    catalogArea.classList.remove("d-none");
    catalogArea.innerHTML = '<div class="small text-muted">Carregando catálogo VSN-*...</div>';
    try {
      const res = await fetch("/api/v1/simples/observabilidade/erros", { cache: "no-store" });
      const lista = await res.json();
      const rows = lista
        .map(
          (e) =>
            `<tr><td><span class="badge text-bg-dark">${escapeHtml(e.codigo)}</span></td><td class="fw-semibold">${escapeHtml(e.titulo)}</td><td>${escapeHtml(e.descricao)}</td></tr>`
        )
        .join("");
      catalogArea.innerHTML = `
        <div class="card border">
          <div class="card-header bg-light py-2 small fw-bold d-flex justify-content-between">
            <span>Catálogo Oficial de Códigos VSN-* (${lista.length} códigos ativos)</span>
            <button type="button" class="btn-close btn-close-sm" aria-label="Fechar"></button>
          </div>
          <div class="table-responsive" style="max-height: 260px;">
            <table class="table table-sm mb-0 small">
              <thead class="table-light"><tr><th>Código</th><th>Título</th><th>Descrição</th></tr></thead>
              <tbody>${rows}</tbody>
            </table>
          </div>
        </div>
      `;
      catalogArea.querySelector(".btn-close")?.addEventListener("click", () => catalogArea.classList.add("d-none"));
    } catch (err) {
      catalogArea.innerHTML = `<div class="alert alert-danger small mb-0">Erro ao carregar catálogo: ${escapeHtml(err.message)}</div>`;
    }
  }

  document.addEventListener("partial:loaded", (event) => {
    if (event.detail.route !== "simples") return;

    const form = document.getElementById("simplesOperForm");
    const tbody = document.getElementById("simplesOperItensBody");
    const resultDiv = document.getElementById("simplesOperResult");
    const catalogArea = document.getElementById("simplesOperCatalogArea");
    if (!form || !tbody || !resultDiv) return;

    window.BrNumber?.applyDefaultTodayDates(form);
    loadDefaultItems(tbody);

    document.getElementById("simplesOperAddItemBtn")?.addEventListener("click", () => addItemRow(tbody));
    document.getElementById("simplesOperDemoErroBtn")?.addEventListener("click", () => loadMixedErrorDemo(tbody));
    document.getElementById("simplesOperCatalogBtn")?.addEventListener("click", () => toggleCatalog(catalogArea));

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = new FormData(form);
      const payload = {
        id: `op-ui-${Date.now()}`,
        versao: "2.0.0",
        data: String(fd.get("data") || ""),
        tpDoc: String(fd.get("tpDoc") || ""),
        CRT: String(fd.get("CRT") || ""),
        tpRegimeIBSCBS: String(fd.get("tpRegimeIBSCBS") || "") || null,
        tpEnteGov: String(fd.get("tpEnteGov") || "") || null,
        itens: collectItems(tbody),
      };

      resultDiv.innerHTML = '<div class="small text-muted">Processando lote na API...</div>';
      try {
        const res = await fetch("/api/v1/simples/observabilidade/calcular", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          cache: "no-store",
          body: JSON.stringify(payload),
        });
        const data = await res.json();
        if (!res.ok) {
          const errosHtml = renderErrosList(data.erros) || escapeHtml(JSON.stringify(data.detail || data));
          resultDiv.innerHTML = `
            <div class="alert alert-danger mb-0">
              <div class="fw-bold small mb-1"><i class="bi bi-shield-exclamation me-1"></i>Operação rejeitada na validação global (HTTP ${res.status})</div>
              ${errosHtml}
            </div>
          `;
          return;
        }
        renderObservabilidadeResult(resultDiv, data);
      } catch (err) {
        resultDiv.innerHTML = `<div class="alert alert-danger small mb-0">Falha de comunicação: ${escapeHtml(err.message)}</div>`;
      }
    });
  });
})(window, document);
