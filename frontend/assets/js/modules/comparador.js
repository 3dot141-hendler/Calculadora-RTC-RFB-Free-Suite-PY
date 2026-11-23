/**
 * ComparadorModule - Simulador lado a lado (Simples DAS vs. Simples Híbrido vs. Regime Regular).
 */
(function (window, document) {
  "use strict";

  const PRESETS = {
    "comercio-b2b": {
      receita_bruta_12m: "720000.00",
      valor_operacao: "50000.00",
      anexo: "I",
      aplicar_fator_r: false,
      uf: "RS",
      c_class_trib: "000001",
      creditos_anteriores: "4500.00",
      aliquota_ibs_mun: "0.00",
      aliquota_is: "0.00",
      percentual_vendas_b2b: "100.00",
    },
    "servicos-ti": {
      receita_bruta_12m: "1200000.00",
      valor_operacao: "30000.00",
      anexo: "V",
      aplicar_fator_r: true,
      folha_salarios_12m: "360000.00",
      uf: "RS",
      c_class_trib: "000001",
      creditos_anteriores: "600.00",
      aliquota_ibs_mun: "0.00",
      aliquota_is: "0.00",
      percentual_vendas_b2b: "100.00",
    },
    "saude-red60": {
      receita_bruta_12m: "1800000.00",
      valor_operacao: "40000.00",
      anexo: "V",
      aplicar_fator_r: true,
      folha_salarios_12m: "396000.00",
      uf: "RS",
      c_class_trib: "200028",
      creditos_anteriores: "1200.00",
      aliquota_ibs_mun: "0.00",
      aliquota_is: "0.00",
      percentual_vendas_b2b: "50.00",
    },
  };

  function getTodayIso() {
    return window.BrNumber ? window.BrNumber.getTodayIso() : new Date().toISOString().slice(0, 10);
  }

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

  function readNumberField(form, name, fallback = "0.00") {
    const el = form.elements.namedItem(name);
    if (!el) return fallback;
    if (window.BrNumber) return window.BrNumber.parseToApiDecimal(el.value, fallback);
    const raw = String(el.value ?? "").trim().replace(",", ".");
    return raw === "" ? fallback : raw;
  }

  function readField(form, name, fallback = "") {
    const el = form.elements.namedItem(name);
    const val = el ? String(el.value ?? "").trim() : "";
    return val || fallback;
  }

  function applyPreset(form, presetKey) {
    const preset = PRESETS[presetKey];
    if (!preset) return;
    Object.entries(preset).forEach(([field, val]) => {
      const el = form.elements.namedItem(field);
      if (!el) return;
      if (el.type === "checkbox") {
        el.checked = Boolean(val);
      } else if (el.hasAttribute("data-br-money") && window.BrNumber) {
        el.value = window.BrNumber.formatBrDecimal(val, 2);
      } else {
        el.value = val;
      }
    });
    const dateEl = form.elements.namedItem("data_fato_gerador");
    if (dateEl && !dateEl.value) dateEl.value = getTodayIso();
    window.ComparadorFatorR?.syncUiState(form);
  }

  function formatValidationError(detail) {
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((err) => {
          const campo = Array.isArray(err.loc) ? err.loc[err.loc.length - 1] : "campo";
          return `<strong>${campo}</strong>: ${err.msg}`;
        })
        .join("<br/>");
    }
    return JSON.stringify(detail);
  }

  function setPrintButtonState(enabled) {
    const printBtn = document.getElementById("comparadorPrintBtn");
    if (printBtn) printBtn.disabled = !enabled;
  }

  function renderResultado(container, data) {
    const nowLabel = new Date().toLocaleTimeString("pt-BR");
    const maxAliq = Math.max(
      ...data.cenarios.map((c) => Number(c.aliquota_efetiva_percentual) || 0),
      1
    );
    const fatorRHtml = window.ComparadorFatorR?.renderBannerHtml(data.fator_r) || "";

    const cardsHtml = data.cenarios
      .map((cenario) => {
        const isMelhorCarga = cenario.id === data.melhor_cenario_carga_propria;
        const isMelhorB2b =
          cenario.id === data.melhor_cenario_competitividade_b2b &&
          Number(data.percentual_vendas_b2b) > 0;
        const borderClass = isMelhorCarga ? "border-success border-2" : "border";
        const barWidth = Math.min(
          Math.round((Number(cenario.aliquota_efetiva_percentual) / maxAliq) * 100),
          100
        );
        const barColor =
          cenario.id === "simples_das"
            ? "bg-success"
            : cenario.id === "simples_hibrido"
              ? "bg-info"
              : "bg-primary";
        const badges = [
          isMelhorCarga
            ? '<span class="badge text-bg-success"><i class="bi bi-trophy me-1"></i>Menor Carga Própria</span>'
            : "",
          isMelhorB2b
            ? '<span class="badge text-bg-primary"><i class="bi bi-building-check me-1"></i>Melhor Crédito B2B</span>'
            : "",
        ]
          .filter(Boolean)
          .join(" ");

        return `
          <div class="col-lg-4">
            <article class="card h-100 shadow-sm ${borderClass}">
              <div class="card-body d-flex flex-column">
                <div class="d-flex flex-wrap gap-1 mb-2">${badges || '<span class="badge text-bg-light border text-dark">Cenário Simulado</span>'}</div>
                <h3 class="h6 fw-bold mb-1">${cenario.nome}</h3>
                <p class="text-muted small mb-3">${cenario.subtitulo}</p>
                <div class="p-3 rounded bg-light mb-3">
                  <div class="small text-muted">Carga Tributária Própria</div>
                  <div class="fs-4 fw-bold text-dark">${formatBRL(cenario.carga_tributaria_total)}</div>
                  <div class="d-flex justify-content-between small mt-1">
                    <span>Alíquota Efetiva</span>
                    <strong>${formatPct(cenario.aliquota_efetiva_percentual)}</strong>
                  </div>
                  <div class="progress mt-1" style="height: 6px;">
                    <div class="progress-bar ${barColor}" style="width: ${barWidth}%;"></div>
                  </div>
                </div>
                <ul class="list-group list-group-flush small mb-3 flex-grow-1">
                  <li class="list-group-item px-0 d-flex justify-content-between">
                    <span class="text-muted">DAS (LC 123)</span>
                    <strong>${formatBRL(cenario.valor_das)}</strong>
                  </li>
                  <li class="list-group-item px-0 d-flex justify-content-between">
                    <span class="text-muted">IBS + CBS Líquido</span>
                    <strong>${formatBRL(cenario.valor_ibs_cbs_liquido)}</strong>
                  </li>
                  <li class="list-group-item px-0 d-flex justify-content-between">
                    <span class="text-muted">Créditos Aproveitados</span>
                    <strong class="text-success">${formatBRL(cenario.creditos_aproveitados)}</strong>
                  </li>
                  <li class="list-group-item px-0 d-flex justify-content-between">
                    <span class="text-muted">Crédito Gerado p/ Cliente B2B</span>
                    <strong class="text-primary">${formatBRL(cenario.credito_gerado_cliente_b2b)}</strong>
                  </li>
                  <li class="list-group-item px-0 d-flex justify-content-between">
                    <span class="text-muted">Custo Efetivo p/ Comprador B2B</span>
                    <strong>${formatBRL(cenario.custo_efetivo_cliente_b2b)}</strong>
                  </li>
                </ul>
                <p class="text-muted mb-0" style="font-size: 0.78rem;">
                  <i class="bi bi-info-circle me-1"></i>${cenario.observacoes}
                </p>
              </div>
            </article>
          </div>
        `;
      })
      .join("");

    const tableRowsHtml = data.cenarios
      .map(
        (c) => `
          <tr>
            <td class="fw-semibold">${c.nome}</td>
            <td class="text-end">${formatBRL(c.valor_das)}</td>
            <td class="text-end">${formatBRL(c.valor_ibs_cbs_bruto)}</td>
            <td class="text-end text-success">${formatBRL(c.creditos_aproveitados)}</td>
            <td class="text-end fw-bold">${formatBRL(c.carga_tributaria_total)} (${formatPct(c.aliquota_efetiva_percentual)})</td>
            <td class="text-end text-primary fw-semibold">${formatBRL(c.credito_gerado_cliente_b2b)}</td>
            <td class="text-end">${formatBRL(c.custo_efetivo_cliente_b2b)}</td>
          </tr>
        `
      )
      .join("");

    container.innerHTML = `
      <div class="alert alert-primary border-0 shadow-sm mb-4">
        <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-1">
          <strong><i class="bi bi-lightbulb-fill me-2"></i>Resumo Executivo para Decisão Tributária</strong>
          <div class="d-flex flex-wrap gap-1">
            <span class="badge text-bg-light border text-dark">
              RBT12 ${formatBRL(data.receita_bruta_12m)} • Operação ${formatBRL(data.valor_operacao)} • Anexo ${data.anexo}
            </span>
            <span class="badge text-bg-light border text-dark">
              UF ${data.uf || "-"} • IBS ${formatPct(data.aliquota_ibs_uf_aplicada)} • CBS ${formatPct(data.aliquota_cbs_aplicada)} • Red. ${formatPct(data.reducao_ibs_percentual)}
            </span>
            <span class="badge text-bg-success">
              <i class="bi bi-check2-circle me-1"></i>Atualizado ${nowLabel}
            </span>
          </div>
        </div>
        <p class="mb-0 small">${data.resumo_executivo}</p>
      </div>
      ${fatorRHtml}
      <div class="row g-3 mb-4">${cardsHtml}</div>
      <div class="card shadow-sm border-0">
        <div class="card-header bg-white py-2 d-flex flex-wrap justify-content-between align-items-center gap-2">
          <h3 class="h6 mb-0 fw-bold"><i class="bi bi-table me-2 text-primary"></i>Quadro Comparativo Sintético</h3>
          <button type="button" class="btn btn-outline-dark btn-sm" data-comparador-print="simples_regular">
            <i class="bi bi-printer me-1"></i>Imprimir / Salvar Relatório PDF
          </button>
        </div>
        <div class="table-responsive">
          <table class="table table-sm table-hover align-middle mb-0 small">
            <thead class="table-light">
              <tr>
                <th>Cenário</th>
                <th class="text-end">DAS</th>
                <th class="text-end">IBS/CBS Bruto</th>
                <th class="text-end">Créditos Insumos</th>
                <th class="text-end">Carga Própria</th>
                <th class="text-end">Crédito p/ B2B</th>
                <th class="text-end">Custo Efetivo B2B</th>
              </tr>
            </thead>
            <tbody>${tableRowsHtml}</tbody>
          </table>
        </div>
      </div>
    `;

    const inlinePrintBtn = container.querySelector('[data-comparador-print="simples_regular"]');
    if (inlinePrintBtn) {
      inlinePrintBtn.addEventListener("click", () => {
        window.ComparadorReport?.printReport("simples_regular");
      });
    }
  }

  async function runComparison(form, container, scrollToResult = false) {
    const submitBtn = document.getElementById("comparadorSubmitBtn");
    const statusText = document.getElementById("comparadorStatusText");

    const rbt12 = Number(readNumberField(form, "receita_bruta_12m", "-1"));
    const valorOp = Number(readNumberField(form, "valor_operacao", "0"));

    if (Number.isNaN(rbt12) || rbt12 < 0 || rbt12 > 4800000) {
      window.ComparadorReport?.setLastResult("simples_regular", null, null);
      setPrintButtonState(false);
      container.innerHTML =
        '<div class="alert alert-warning mb-0"><i class="bi bi-exclamation-triangle me-2"></i>O campo <strong>RBT12</strong> deve estar entre <strong>R$ 0,00</strong> e <strong>R$ 4.800.000,00</strong> (limite legal do Simples Nacional).</div>';
      return;
    }

    if (Number.isNaN(valorOp) || valorOp <= 0) {
      window.ComparadorReport?.setLastResult("simples_regular", null, null);
      setPrintButtonState(false);
      container.innerHTML =
        '<div class="alert alert-warning mb-0"><i class="bi bi-exclamation-triangle me-2"></i>Informe um <strong>Valor da Operação</strong> maior que zero.</div>';
      return;
    }

    const fatorRFields = window.ComparadorFatorR?.readPayloadFields(form) || { aplicar_fator_r: false };
    const payload = {
      receita_bruta_12m: readNumberField(form, "receita_bruta_12m", "0.00"),
      valor_operacao: readNumberField(form, "valor_operacao", "0.00"),
      anexo: readField(form, "anexo", "I"),
      data_fato_gerador: readField(form, "data_fato_gerador", getTodayIso()),
      uf: readField(form, "uf", "RS"),
      c_class_trib: readField(form, "c_class_trib", "000001"),
      aliquota_ibs_mun: readNumberField(form, "aliquota_ibs_mun", "0.00"),
      aliquota_is: readNumberField(form, "aliquota_is", "0.00"),
      creditos_anteriores: readNumberField(form, "creditos_anteriores", "0.00"),
      percentual_vendas_b2b: readNumberField(form, "percentual_vendas_b2b", "0.00"),
      ...fatorRFields,
    };

    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Calculando...';
    }
    if (statusText) statusText.textContent = "Recalculando cenários na API...";

    try {
      const res = await fetch("/api/v1/comparador/simular", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        cache: "no-store",
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) {
        window.ComparadorReport?.setLastResult("simples_regular", null, null);
        setPrintButtonState(false);
        container.innerHTML = `<div class="alert alert-danger mb-0">${formatValidationError(data.detail)}</div>`;
        if (statusText) statusText.textContent = "Erro de validação nos parâmetros.";
        return;
      }
      window.ComparadorReport?.setLastResult("simples_regular", payload, data);
      setPrintButtonState(true);
      renderResultado(container, data);
      if (statusText) {
        statusText.innerHTML = `<i class="bi bi-check-circle-fill text-success me-1"></i>Simulação atualizada às ${new Date().toLocaleTimeString("pt-BR")}`;
      }
      if (scrollToResult) container.scrollIntoView({ behavior: "smooth", block: "nearest" });
    } catch (err) {
      window.ComparadorReport?.setLastResult("simples_regular", null, null);
      setPrintButtonState(false);
      container.innerHTML = `<div class="alert alert-danger mb-0">Erro ao consultar API: ${err.message}</div>`;
      if (statusText) statusText.textContent = "Falha de comunicação com a API.";
    } finally {
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="bi bi-calculator me-1"></i>Comparar Cenários Lado a Lado';
      }
    }
  }

  document.addEventListener("partial:loaded", (event) => {
    if (event.detail.route !== "comparador") return;

    const form = document.getElementById("comparadorForm");
    const container = document.getElementById("comparadorResultadoArea");
    const printBtn = document.getElementById("comparadorPrintBtn");
    if (!form || !container) return;

    window.BrNumber?.applyDefaultTodayDates(form);
    window.BrNumber?.attachMoneyInputs(form);
    window.ComparadorFatorR?.bindControls(form);

    if (printBtn) {
      printBtn.addEventListener("click", () => {
        window.ComparadorReport?.printReport("simples_regular");
      });
    }

    document.querySelectorAll("[data-preset]").forEach((btn) => {
      btn.addEventListener("click", () => {
        applyPreset(form, btn.dataset.preset);
        runComparison(form, container, true);
      });
    });

    form.addEventListener("submit", (e) => {
      e.preventDefault();
      runComparison(form, container, true);
    });

    runComparison(form, container, false);
  });
})(window, document);
