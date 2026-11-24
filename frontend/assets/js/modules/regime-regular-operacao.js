/**
 * RegimeRegularOperacaoModule - Submódulo JS para cálculo multi-itens
 * com redução (cClassTrib e base), crédito presumido, compra governamental,
 * diferimento e transição EC 132 (ICMS UF / ISS Municipal).
 */
(function (window, document) {
  "use strict";

  function formatBRL(value) {
    const num = Number(value);
    if (Number.isNaN(num)) return "R$ 0,00";
    return num.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
  }

  function toApiNum(raw, fallback = "0.00") {
    if (window.BrNumber) {
      return window.BrNumber.parseToApiDecimal(raw, fallback);
    }
    const cleaned = String(raw ?? "").trim().replace(",", ".");
    return cleaned === "" ? fallback : cleaned;
  }

  function createItemRow(
    codigo = "ITEM-01",
    valor = "1.000,00",
    cClass = "000001",
    redBase = "0,00",
    dif = "0,00",
    credIbs = "0,00"
  ) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><input type="text" class="form-control form-control-sm op-codigo" value="${codigo}" required /></td>
      <td><input type="text" inputmode="decimal" data-br-money class="form-control form-control-sm op-valor" value="${valor}" required /></td>
      <td>
        <select class="form-select form-select-sm op-cclasstrib">
          <option value="000001" ${cClass === "000001" ? "selected" : ""}>000001 (Integral)</option>
          <option value="200028" ${cClass === "200028" ? "selected" : ""}>200028 (Red. 60%)</option>
          <option value="200003" ${cClass === "200003" ? "selected" : ""}>200003 (Zero)</option>
        </select>
      </td>
      <td><input type="text" inputmode="decimal" data-br-money class="form-control form-control-sm op-red-base" value="${redBase}" /></td>
      <td><input type="text" inputmode="decimal" data-br-money class="form-control form-control-sm op-dif" value="${dif}" /></td>
      <td><input type="text" inputmode="decimal" data-br-money class="form-control form-control-sm op-cred-ibs" value="${credIbs}" /></td>
      <td class="text-end">
        <button type="button" class="btn btn-sm btn-outline-danger op-remove" title="Remover item">
          <i class="bi bi-trash"></i>
        </button>
      </td>
    `;
    window.BrNumber?.attachMoneyInputs(tr);
    tr.querySelector(".op-remove").addEventListener("click", () => {
      if (tr.parentElement && tr.parentElement.children.length > 1) {
        tr.remove();
      }
    });
    return tr;
  }

  document.addEventListener("partial:loaded", (event) => {
    if (event.detail.route !== "regime-regular") return;

    const tbody = document.getElementById("opItensBody");
    const addBtn = document.getElementById("opAddItemBtn");
    const form = document.getElementById("operacaoRegimeRegularForm");
    const resultEl = document.getElementById("operacaoRegimeRegularResult");
    if (!tbody || !addBtn || !form || !resultEl) return;

    window.BrNumber?.applyDefaultTodayDates(form);
    const localPicker = window.AliquotaLocalPicker?.mount("opLocalPicker", {
      form,
      ufSelector: "#op_uf",
      dateSelector: "#op_data",
      defaultTipo: "icms",
      showSimplesNote: false,
    });

    tbody.replaceChildren(
      createItemRow("ITEM-01", "1.000,00", "000001", "0,00", "0,00", "0,00"),
      createItemRow("ITEM-02", "1.000,00", "200028", "10,00", "50,00", "5,00")
    );

    addBtn.addEventListener("click", () => {
      const idx = tbody.children.length + 1;
      tbody.appendChild(createItemRow(`ITEM-0${idx}`, "500,00", "000001", "0,00", "0,00", "0,00"));
    });

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const itens = Array.from(tbody.querySelectorAll("tr")).map((row) => {
        const credIbs = Number(toApiNum(row.querySelector(".op-cred-ibs").value, "0.00"));
        const item = {
          codigo_item: row.querySelector(".op-codigo").value,
          valor_base: toApiNum(row.querySelector(".op-valor").value),
          c_class_trib: row.querySelector(".op-cclasstrib").value,
          aliquota_ibs_mun: "0.00",
          percentual_reducao_base: toApiNum(row.querySelector(".op-red-base").value, "0.00"),
          percentual_diferimento: toApiNum(row.querySelector(".op-dif").value, "0.00"),
        };
        if (credIbs > 0) {
          item.credito_presumido = {
            percentual_ibs: toApiNum(row.querySelector(".op-cred-ibs").value, "0.00"),
            percentual_cbs: "0.00",
            condicao_suspensiva: false,
          };
        }
        return item;
      });

      const localFields = localPicker?.getPayloadFields() || {};
      const payload = {
        data_fato_gerador: form.op_data.value,
        uf: form.op_uf.value,
        itens,
        ...localFields,
      };
      const tpEnteGov = form.op_tp_ente_gov?.value;
      if (tpEnteGov) {
        payload.tp_ente_gov = Number(tpEnteGov);
        const redGovRaw = form.op_redutor_gov?.value?.trim();
        if (redGovRaw) {
          payload.percentual_redutor_compra_gov = toApiNum(redGovRaw, "0.00");
        }
      }

      const res = await fetch("/api/v1/regime-regular/calcular-operacao", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) {
        resultEl.innerHTML = `<div class="alert alert-danger mb-0">${JSON.stringify(data.detail)}</div>`;
        return;
      }

      const transBannerHtml = window.AliquotaLocalPicker?.renderResumoBanner(data.transicao_tributo_local) || "";
      const localLabel = (data.transicao_tributo_local?.tipo_tributo_local || "ICMS/ISS").toUpperCase();

      resultEl.innerHTML = `
        ${transBannerHtml}
        <div class="result-box p-3">
          <div class="d-flex justify-content-between align-items-center mb-2">
            <strong>Consolidação (${data.quantidade_itens} itens - UF ${data.uf})</strong>
            <span class="badge text-bg-primary">Total: ${formatBRL(data.total_geral_operacao)}</span>
          </div>
          <div class="row g-2 small">
            <div class="col-4">Base Efetiva: <strong>${formatBRL(data.total_base_calculo)}</strong></div>
            <div class="col-4">Redução Base: <strong>${formatBRL(data.total_reducao_base)}</strong></div>
            <div class="col-4">Total Diferido: <strong>${formatBRL(data.total_diferido)}</strong></div>
            <div class="col-4">Total IBS: <strong>${formatBRL(data.total_ibs)}</strong></div>
            <div class="col-4">Total CBS: <strong>${formatBRL(data.total_cbs)}</strong></div>
            <div class="col-4">${localLabel} (Transição): <strong>${formatBRL(data.total_tributo_local || 0)}</strong></div>
            <div class="col-4">Créd. Pres. IBS: <strong>${formatBRL(data.total_credito_presumido_ibs)}</strong></div>
            <div class="col-4">Redutor Gov: <strong>${data.percentual_redutor_compra_gov_aplicado}%</strong></div>
            <div class="col-4">Total Devido: <strong class="text-primary">${formatBRL(data.total_geral_operacao)}</strong></div>
          </div>
        </div>
      `;
    });
  });
})(window, document);
