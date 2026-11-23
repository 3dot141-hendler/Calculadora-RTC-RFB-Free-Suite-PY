/**
 * ComparadorFatorR - Controle de UI e renderização gerencial do Fator R (LC 123/2006).
 * Mantém comparador.js abaixo de 400 linhas respeitando SRP.
 */
(function (window) {
  "use strict";

  function formatBRL(value) {
    const num = Number(value);
    if (Number.isNaN(num)) return "R$ 0,00";
    return num.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
  }

  function formatPct(value) {
    const num = Number(value);
    if (Number.isNaN(num)) return "0,00%";
    return `${num.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%`;
  }

  function parseDecimal(el, fallback = "0.00") {
    if (!el) return fallback;
    if (window.BrNumber) return window.BrNumber.parseToApiDecimal(el.value, fallback);
    const raw = String(el.value ?? "").trim().replace(",", ".");
    return raw === "" ? fallback : raw;
  }

  function syncUiState(form) {
    const toggle = form.elements.namedItem("aplicar_fator_r");
    const folhaInput = form.elements.namedItem("folha_salarios_12m");
    const anexoSelect = form.elements.namedItem("anexo");
    const badge = form.querySelector("#compFatorRBadge");
    if (!toggle || !folhaInput) return;

    const ativo = Boolean(toggle.checked);
    folhaInput.disabled = !ativo;
    if (anexoSelect) anexoSelect.disabled = ativo;

    if (!badge) return;
    if (!ativo) {
      badge.className = "badge text-bg-light border text-muted";
      badge.textContent = "Desativado (usa Anexo selecionado)";
      return;
    }

    const rbt12 = Number(parseDecimal(form.elements.namedItem("receita_bruta_12m"), "0"));
    const folha = Number(parseDecimal(folhaInput, "0"));
    const pct = rbt12 > 0 ? (folha / rbt12) * 100 : folha > 0 ? 100 : 0;
    const atingiu = pct >= 28;
    badge.className = atingiu ? "badge text-bg-success" : "badge text-bg-warning text-dark";
    badge.textContent = `Fator R: ${formatPct(pct)} → Anexo ${atingiu ? "III" : "V"}`;
  }

  function bindControls(form) {
    const toggle = form.elements.namedItem("aplicar_fator_r");
    const folhaInput = form.elements.namedItem("folha_salarios_12m");
    const rbtInput = form.elements.namedItem("receita_bruta_12m");
    if (!toggle) return;

    const handler = () => syncUiState(form);
    toggle.addEventListener("change", handler);
    if (folhaInput) {
      folhaInput.addEventListener("input", handler);
      folhaInput.addEventListener("blur", handler);
    }
    if (rbtInput) {
      rbtInput.addEventListener("input", handler);
      rbtInput.addEventListener("blur", handler);
    }
    syncUiState(form);
  }

  function readPayloadFields(form) {
    const toggle = form.elements.namedItem("aplicar_fator_r");
    const ativo = Boolean(toggle && toggle.checked);
    if (!ativo) return { aplicar_fator_r: false };
    return {
      aplicar_fator_r: true,
      folha_salarios_12m: parseDecimal(form.elements.namedItem("folha_salarios_12m"), "0.00"),
    };
  }

  function renderBannerHtml(fatorR) {
    if (!fatorR || !fatorR.aplicado) return "";
    const ok = Boolean(fatorR.atingiu_minimo_28_pct);
    const tone = ok ? "border-success bg-success-subtle" : "border-warning bg-warning-subtle";
    const pill = ok
      ? `<span class="badge text-bg-success">Fator R ${formatPct(fatorR.percentual_fator_r)} ≥ 28% • Anexo III</span>`
      : `<span class="badge text-bg-warning text-dark">Fator R ${formatPct(fatorR.percentual_fator_r)} &lt; 28% • Anexo V</span>`;
    const metaFaltante = ok
      ? `Folha 12m: <strong>${formatBRL(fatorR.folha_salarios_12m)}</strong> (mínimo 28%: ${formatBRL(fatorR.folha_minima_anexo_iii)})`
      : `Folha faltante p/ Anexo III: <strong>${formatBRL(fatorR.folha_faltante_anexo_iii)}/12m</strong> (~${formatBRL(fatorR.folha_faltante_mensal)}/mês)`;

    return `
      <div class="card ${tone} border shadow-sm mb-4">
        <div class="card-body py-3">
          <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-2">
            <div class="fw-bold small">
              <i class="bi bi-people-fill me-1"></i>Diagnóstico do Fator R (LC 123/2006 — Anexo III vs. Anexo V)
            </div>
            ${pill}
          </div>
          <p class="small mb-2">${fatorR.recomendacao}</p>
          <div class="d-flex flex-wrap gap-3 small">
            <span>DAS Anexo III: <strong class="text-success">${formatBRL(fatorR.das_anexo_iii)}</strong></span>
            <span>DAS Anexo V: <strong class="text-danger">${formatBRL(fatorR.das_anexo_v)}</strong></span>
            <span>Economia no DAS: <strong class="text-primary">${formatBRL(fatorR.economia_das_fator_r)}</strong></span>
            <span>${metaFaltante}</span>
          </div>
        </div>
      </div>
    `;
  }

  window.ComparadorFatorR = {
    bindControls,
    syncUiState,
    readPayloadFields,
    renderBannerHtml,
  };
})(window);
