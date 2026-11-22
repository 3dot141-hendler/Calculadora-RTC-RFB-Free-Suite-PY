/**
 * ComparadorPresumidoRealModule - Comparador Lucro Presumido vs. Lucro Real (+ IBS/CBS).
 */
(function (window, document) {
  "use strict";

  const PRESETS = {
    "servicos-alta-margem": {
      receita_bruta_mensal: "500000.00",
      despesas_dedutiveis_mensais: "275000.00",
      atividade: "SERVICOS_GERAIS",
      uf: "RS",
      c_class_trib: "000001",
      creditos_ibs_cbs: "14000.00",
      aliquota_ibs_mun: "0.00",
      aliquota_is: "0.00",
    },
    "comercio-atacado": {
      receita_bruta_mensal: "600000.00",
      despesas_dedutiveis_mensais: "576000.00",
      atividade: "COMERCIO_INDUSTRIA",
      uf: "RS",
      c_class_trib: "000001",
      creditos_ibs_cbs: "80000.00",
      aliquota_ibs_mun: "0.00",
      aliquota_is: "0.00",
    },
    "hospitalar-red60": {
      receita_bruta_mensal: "900000.00",
      despesas_dedutiveis_mensais: "765000.00",
      atividade: "SERVICOS_HOSPITALARES",
      uf: "RS",
      c_class_trib: "200028",
      creditos_ibs_cbs: "18000.00",
      aliquota_ibs_mun: "0.00",
      aliquota_is: "0.00",
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

  function readNum(form, name, fallback = "0.00") {
    const el = form.elements.namedItem(name);
    if (!el) return fallback;
    if (window.BrNumber) {
      return window.BrNumber.parseToApiDecimal(el.value, fallback);
    }
    const raw = String(el.value ?? "").trim().replace(",", ".");
    return raw === "" ? fallback : raw;
  }

  function readVal(form, name, fallback = "") {
    const el = form.elements.namedItem(name);
    const val = el ? String(el.value ?? "").trim() : "";
    return val || fallback;
  }

  function applyPreset(form, key) {
    const preset = PRESETS[key];
    if (!preset) return;
    Object.entries(preset).forEach(([field, val]) => {
      const el = form.elements.namedItem(field);
      if (!el) return;
      if (el.hasAttribute("data-br-money") && window.BrNumber) {
        el.value = window.BrNumber.formatBrDecimal(val, 2);
      } else {
        el.value = val;
      }
    });
    const dateEl = form.elements.namedItem("data_fato_gerador");
    if (dateEl && !dateEl.value) {
      dateEl.value = getTodayIso();
    }
  }

  function setPrintButtonState(enabled) {
    const printBtn = document.getElementById("presumidoRealPrintBtn");
    if (printBtn) printBtn.disabled = !enabled;
  }

  function renderResultado(container, data) {
    const nowLabel = new Date().toLocaleTimeString("pt-BR");
    const maxAliq = Math.max(
      ...data.cenarios.map((c) => Number(c.aliquota_efetiva_percentual) || 0),
      1
    );

    const cardsHtml = data.cenarios
      .map((c) => {
        const isMelhor = c.id === data.melhor_regime;
        const borderClass = !c.elegivel
          ? "border-danger border-2"
          : isMelhor
            ? "border-success border-2"
            : "border";
        const barWidth = Math.min(
          Math.round((Number(c.aliquota_efetiva_percentual) / maxAliq) * 100),
          100
        );
        const barColor = c.id === "lucro_presumido" ? "bg-info" : "bg-primary";

        const badge = !c.elegivel
          ? '<span class="badge text-bg-danger"><i class="bi bi-slash-circle me-1"></i>Inelegível (&gt; R$ 78 mi/ano)</span>'
          : isMelhor
            ? '<span class="badge text-bg-success"><i class="bi bi-trophy me-1"></i>Regime Mais Econômico</span>'
            : '<span class="badge text-bg-light border text-dark">Cenário Comparado</span>';

        return `
          <div class="col-lg-6">
            <article class="card h-100 shadow-sm ${borderClass}">
              <div class="card-body d-flex flex-column">
                <div class="mb-2">${badge}</div>
                <h3 class="h6 fw-bold mb-1">${c.nome}</h3>
                <p class="text-muted small mb-3">${c.subtitulo}</p>

                <div class="p-3 rounded bg-light mb-3">
                  <div class="small text-muted">Carga Tributária Mensal Total (IRPJ + CSLL + IBS/CBS)</div>
                  <div class="fs-4 fw-bold text-dark">${formatBRL(c.carga_tributaria_total)}</div>
                  <div class="d-flex justify-content-between small mt-1">
                    <span>Alíquota Efetiva Total</span>
                    <strong>${formatPct(c.aliquota_efetiva_percentual)}</strong>
                  </div>
                  <div class="progress mt-1" style="height: 6px;">
                    <div class="progress-bar ${barColor}" style="width: ${barWidth}%;"></div>
                  </div>
                </div>

                <ul class="list-group list-group-flush small mb-3 flex-grow-1">
                  <li class="list-group-item px-0 d-flex justify-content-between">
                    <span class="text-muted">Base de Cálculo IRPJ / CSLL</span>
                    <strong>${formatBRL(c.base_calculo_irpj)} / ${formatBRL(c.base_calculo_csll)}</strong>
                  </li>
                  <li class="list-group-item px-0 d-flex justify-content-between">
                    <span class="text-muted">IRPJ Básico (15%)</span>
                    <strong>${formatBRL(c.irpj_basico)}</strong>
                  </li>
                  <li class="list-group-item px-0 d-flex justify-content-between">
                    <span class="text-muted">Adicional IRPJ (10% &gt; R$ 20k/mês)</span>
                    <strong>${formatBRL(c.adicional_irpj)}</strong>
                  </li>
                  <li class="list-group-item px-0 d-flex justify-content-between">
                    <span class="text-muted">CSLL (9%)</span>
                    <strong>${formatBRL(c.csll)}</strong>
                  </li>
                  <li class="list-group-item px-0 d-flex justify-content-between">
                    <span class="text-muted">Subtotal Lucro (IRPJ + CSLL)</span>
                    <strong class="text-primary">${formatBRL(c.total_irpj_csll)}</strong>
                  </li>
                  <li class="list-group-item px-0 d-flex justify-content-between">
                    <span class="text-muted">IBS + CBS + IS Líquido (Regime Regular)</span>
                    <strong>${formatBRL(c.ibs_cbs_is_liquido)}</strong>
                  </li>
                </ul>

                <p class="text-muted mb-0" style="font-size: 0.78rem;">
                  <i class="bi bi-info-circle me-1"></i>${c.observacoes}
                </p>
              </div>
            </article>
          </div>
        `;
      })
      .join("");

    const tableRowsHtml = data.cenarios
      .map((c) => {
        const irpjTotal = Number(c.irpj_basico) + Number(c.adicional_irpj);
        const statusTag = c.elegivel
          ? ""
          : ' <span class="badge text-bg-danger ms-1">Inelegível</span>';
        return `
          <tr>
            <td class="fw-semibold">${c.nome}${statusTag}</td>
            <td class="text-end">${formatBRL(c.base_calculo_irpj)} / ${formatBRL(c.base_calculo_csll)}</td>
            <td class="text-end">${formatBRL(irpjTotal)}</td>
            <td class="text-end">${formatBRL(c.csll)}</td>
            <td class="text-end text-primary fw-semibold">${formatBRL(c.total_irpj_csll)}</td>
            <td class="text-end">${formatBRL(c.ibs_cbs_is_liquido)}</td>
            <td class="text-end fw-bold">${formatBRL(c.carga_tributaria_total)} (${formatPct(c.aliquota_efetiva_percentual)})</td>
          </tr>
        `;
      })
      .join("");

    const alertClass = data.excede_limite_presumido ? "alert-warning" : "alert-primary";

    container.innerHTML = `
      <div class="alert ${alertClass} border-0 shadow-sm mb-4">
        <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-1">
          <strong><i class="bi bi-lightbulb-fill me-2"></i>Diagnóstico: Lucro Presumido vs. Lucro Real</strong>
          <div class="d-flex flex-wrap gap-1">
            <span class="badge text-bg-light border text-dark">
              Receita Anualizada ${formatBRL(data.receita_anualizada_estimada)}
            </span>
            <span class="badge text-bg-light border text-dark">
              Lucro Real ${formatBRL(data.lucro_contabil_mensal)} (${formatPct(data.margem_lucro_real_percentual)})
            </span>
            <span class="badge text-bg-light border text-dark">
              Economia: ${formatBRL(data.economia_mensal_reais)}/mês • ${formatBRL(data.economia_anual_estimada_reais)}/ano
            </span>
            <span class="badge text-bg-success">
              <i class="bi bi-check2-circle me-1"></i>Atualizado ${nowLabel}
            </span>
          </div>
        </div>
        <p class="mb-0 small">${data.resumo_executivo}</p>
      </div>

      <div class="row g-3 mb-4">${cardsHtml}</div>

      <div class="card shadow-sm border-0">
        <div class="card-header bg-white py-2 d-flex flex-wrap justify-content-between align-items-center gap-2">
          <h3 class="h6 mb-0 fw-bold"><i class="bi bi-table me-2 text-primary"></i>Quadro Comparativo Sintético Mensal</h3>
          <button type="button" class="btn btn-outline-dark btn-sm" data-comparador-print="presumido_real">
            <i class="bi bi-printer me-1"></i>Imprimir / Salvar Relatório PDF
          </button>
        </div>
        <div class="table-responsive">
          <table class="table table-sm table-hover align-middle mb-0 small">
            <thead class="table-light">
              <tr>
                <th>Regime</th>
                <th class="text-end">Base IRPJ / CSLL</th>
                <th class="text-end">IRPJ + Adic.</th>
                <th class="text-end">CSLL (9%)</th>
                <th class="text-end">Subtotal Lucro</th>
                <th class="text-end">IBS/CBS/IS Líq.</th>
                <th class="text-end">Carga Total</th>
              </tr>
            </thead>
            <tbody>${tableRowsHtml}</tbody>
          </table>
        </div>
      </div>
    `;

    const inlinePrintBtn = container.querySelector('[data-comparador-print="presumido_real"]');
    if (inlinePrintBtn) {
      inlinePrintBtn.addEventListener("click", () => {
        window.ComparadorReport?.printReport("presumido_real");
      });
    }
  }

  async function runComparison(form, container, scrollToResult = false) {
    const submitBtn = document.getElementById("presumidoRealSubmitBtn");
    const statusText = document.getElementById("presumidoRealStatusText");

    const receita = Number(readNum(form, "receita_bruta_mensal", "0"));
    const despesas = Number(readNum(form, "despesas_dedutiveis_mensais", "-1"));

    if (Number.isNaN(receita) || receita <= 0) {
      window.ComparadorReport?.setLastResult("presumido_real", null, null);
      setPrintButtonState(false);
      container.innerHTML =
        '<div class="alert alert-warning mb-0">Informe uma <strong>Receita Bruta Mensal</strong> maior que zero.</div>';
      return;
    }
    if (Number.isNaN(despesas) || despesas < 0) {
      window.ComparadorReport?.setLastResult("presumido_real", null, null);
      setPrintButtonState(false);
      container.innerHTML =
        '<div class="alert alert-warning mb-0">As <strong>Despesas Dedutíveis</strong> não podem ser negativas.</div>';
      return;
    }

    const payload = {
      receita_bruta_mensal: readNum(form, "receita_bruta_mensal", "0.00"),
      despesas_dedutiveis_mensais: readNum(form, "despesas_dedutiveis_mensais", "0.00"),
      atividade: readVal(form, "atividade", "COMERCIO_INDUSTRIA"),
      data_fato_gerador: readVal(form, "data_fato_gerador", getTodayIso()),
      uf: readVal(form, "uf", "RS"),
      c_class_trib: readVal(form, "c_class_trib", "000001"),
      aliquota_ibs_mun: readNum(form, "aliquota_ibs_mun", "0.00"),
      aliquota_is: readNum(form, "aliquota_is", "0.00"),
      creditos_ibs_cbs: readNum(form, "creditos_ibs_cbs", "0.00"),
    };

    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Calculando...';
    }
    if (statusText) statusText.textContent = "Recalculando Presumido vs. Real...";

    try {
      const res = await fetch("/api/v1/comparador/presumido-vs-real", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        cache: "no-store",
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) {
        window.ComparadorReport?.setLastResult("presumido_real", null, null);
        setPrintButtonState(false);
        container.innerHTML = `<div class="alert alert-danger mb-0">${JSON.stringify(data.detail)}</div>`;
        if (statusText) statusText.textContent = "Erro de validação.";
        return;
      }
      window.ComparadorReport?.setLastResult("presumido_real", payload, data);
      setPrintButtonState(true);
      renderResultado(container, data);
      if (statusText) {
        statusText.innerHTML = `<i class="bi bi-check-circle-fill text-success me-1"></i>Simulação atualizada às ${new Date().toLocaleTimeString("pt-BR")}`;
      }
      if (scrollToResult) container.scrollIntoView({ behavior: "smooth", block: "nearest" });
    } catch (err) {
      window.ComparadorReport?.setLastResult("presumido_real", null, null);
      setPrintButtonState(false);
      container.innerHTML = `<div class="alert alert-danger mb-0">Erro ao consultar API: ${err.message}</div>`;
    } finally {
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="bi bi-calculator me-1"></i>Comparar Presumido vs. Real';
      }
    }
  }

  document.addEventListener("partial:loaded", (event) => {
    if (event.detail.route !== "comparador") return;

    const form = document.getElementById("presumidoRealForm");
    const container = document.getElementById("presumidoRealResultadoArea");
    const printBtn = document.getElementById("presumidoRealPrintBtn");
    if (!form || !container) return;

    window.BrNumber?.applyDefaultTodayDates(form);
    window.BrNumber?.attachMoneyInputs(form);

    if (printBtn) {
      printBtn.addEventListener("click", () => {
        window.ComparadorReport?.printReport("presumido_real");
      });
    }

    document.querySelectorAll("[data-pr-preset]").forEach((btn) => {
      btn.addEventListener("click", () => {
        applyPreset(form, btn.dataset.prPreset);
        runComparison(form, container, true);
      });
    });

    form.addEventListener("submit", (e) => {
      e.preventDefault();
      runComparison(form, container, true);
    });

    // Pré-carrega o resultado da segunda aba ao abrir o comparador
    runComparison(form, container, false);
  });
})(window, document);
