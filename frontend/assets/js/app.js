/**
 * AppBootstrap - Orquestração principal do frontend e integração com a API FastAPI.
 */
(function (window, document) {
  "use strict";

  const API_BASE = "/api/v1";

  function formatBRL(value) {
    const num = Number(value);
    if (Number.isNaN(num)) return "R$ 0,00";
    return num.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
  }

  async function checkApiHealth() {
    const badge = document.getElementById("apiStatusBadge");
    if (!badge) return;

    try {
      const response = await fetch(`${API_BASE}/health`, { cache: "no-store" });
      if (!response.ok) throw new Error("API indisponível");
      const data = await response.json();
      badge.className = "badge rounded-pill text-bg-success";
      badge.innerHTML = `<i class="bi bi-circle-fill me-1 small"></i>API Online (v${data.version})`;
    } catch {
      badge.className = "badge rounded-pill text-bg-danger";
      badge.innerHTML = '<i class="bi bi-circle-fill me-1 small"></i>API Offline';
    }
  }

  function bindSimplesForm() {
    const form = document.getElementById("simplesForm");
    if (!form) return;

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const resultEl = document.getElementById("simplesResult");
      const payload = {
        receita_bruta_12m: form.receita_bruta_12m.value,
        valor_operacao: form.valor_operacao.value,
        anexo: form.anexo.value,
        recolher_ibs_cbs_por_fora: form.recolher_ibs_cbs_por_fora.checked,
      };

      const res = await fetch(`${API_BASE}/simples/calcular`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) {
        resultEl.innerHTML = `<div class="alert alert-danger mb-0">${JSON.stringify(data.detail)}</div>`;
        return;
      }

      resultEl.innerHTML = `
        <div class="result-box p-3">
          <div class="d-flex justify-content-between align-items-center mb-2">
            <strong>Resultado Simples Nacional (Anexo ${data.anexo})</strong>
            <span class="badge text-bg-success">${data.aliquota_efetiva_das}% Efetiva</span>
          </div>
          <p class="mb-1">DAS Estimado: <strong>${formatBRL(data.valor_das)}</strong></p>
          <p class="mb-1">IBS + CBS Estimado: <strong>${formatBRL(data.valor_ibs_cbs_estimado)}</strong></p>
          <p class="mb-2">Total Tributos: <strong>${formatBRL(data.valor_total_tributos)}</strong></p>
          <small class="text-muted">${data.observacoes}</small>
        </div>
      `;
    });
  }

  function bindRegimeRegularForm() {
    const form = document.getElementById("regimeRegularForm");
    if (!form) return;

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const resultEl = document.getElementById("regimeRegularResult");
      const payload = {
        valor_operacao: form.valor_operacao.value,
        aliquota_ibs_uf: form.aliquota_ibs_uf.value,
        aliquota_ibs_mun: form.aliquota_ibs_mun.value,
        aliquota_cbs: form.aliquota_cbs.value,
        aliquota_is: form.aliquota_is.value,
        percentual_reducao: form.percentual_reducao.value,
        creditos_anteriores: form.creditos_anteriores.value,
      };

      const res = await fetch(`${API_BASE}/regime-regular/calcular`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) {
        resultEl.innerHTML = `<div class="alert alert-danger mb-0">${JSON.stringify(data.detail)}</div>`;
        return;
      }

      resultEl.innerHTML = `
        <div class="result-box p-3">
          <strong class="d-block mb-2">Apuração Regime Regular (IBS + CBS + IS)</strong>
          <div class="row g-2 small">
            <div class="col-6">IBS Estadual: <strong>${formatBRL(data.valor_ibs_uf)}</strong></div>
            <div class="col-6">IBS Municipal: <strong>${formatBRL(data.valor_ibs_mun)}</strong></div>
            <div class="col-6">CBS Federal: <strong>${formatBRL(data.valor_cbs)}</strong></div>
            <div class="col-6">Imposto Seletivo: <strong>${formatBRL(data.valor_is)}</strong></div>
            <div class="col-6">Créditos Aproveitados: <strong>${formatBRL(data.creditos_aproveitados)}</strong></div>
            <div class="col-6">Líquido a Recolher: <strong class="text-primary">${formatBRL(data.valor_liquido_a_recolher)}</strong></div>
          </div>
        </div>
      `;
    });
  }

  function bindDanfseForm() {
    const form = document.getElementById("danfseForm");
    if (!form) return;

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const resultEl = document.getElementById("danfseResult");
      const payload = {
        numero_nfse: form.numero_nfse.value,
        prestador_cnpj: form.prestador_cnpj.value.replace(/\D/g, ""),
        tomador_documento: form.tomador_documento.value.replace(/\D/g, ""),
        discriminacao_servico: form.discriminacao_servico.value,
        valor_servicos: form.valor_servicos.value,
        valor_ibs: form.valor_ibs.value,
        valor_cbs: form.valor_cbs.value,
      };

      const res = await fetch(`${API_BASE}/danfse/preview`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) {
        resultEl.innerHTML = `<div class="alert alert-danger mb-0">${JSON.stringify(data.detail)}</div>`;
        return;
      }

      resultEl.innerHTML = `
        <div class="result-box p-3">
          <div class="d-flex justify-content-between align-items-center mb-2">
            <strong>Prévia DANFSE #${data.numero_nfse}</strong>
            <span class="badge text-bg-warning text-dark">${data.status_validacao}</span>
          </div>
          <p class="mb-1 small">Chave Simulada: <code>${data.chave_acesso_simulada}</code></p>
          <p class="mb-1">Valor dos Serviços: <strong>${formatBRL(data.valor_servicos)}</strong></p>
          <p class="mb-0">Total IBS/CBS Destacado: <strong>${formatBRL(data.valor_total_tributos_rtc)}</strong></p>
        </div>
      `;
    });
  }

  function bindDashboardCards() {
    document.querySelectorAll("[data-navigate-route]").forEach((btn) => {
      btn.addEventListener("click", () => {
        window.PartialRouter.navigate(btn.dataset.navigateRoute);
      });
    });
  }

  document.addEventListener("partial:loaded", (event) => {
    const { route } = event.detail;
    if (route === "dashboard") bindDashboardCards();
    if (route === "simples") bindSimplesForm();
    if (route === "regime-regular") bindRegimeRegularForm();
    if (route === "danfse") bindDanfseForm();
  });

  document.addEventListener("DOMContentLoaded", () => {
    window.SidebarManager.initSidebar();
    window.PartialRouter.initRouter();
    checkApiHealth();
  });
})(window, document);

