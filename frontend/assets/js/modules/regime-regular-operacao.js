/**
 * RegimeRegularOperacaoModule - Submódulo JS para cálculo multi-itens
 * com redução via cClassTrib e diferimento no Regime Regular.
 */
(function (window, document) {
  "use strict";

  function formatBRL(value) {
    const num = Number(value);
    if (Number.isNaN(num)) return "R$ 0,00";
    return num.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
  }

  function createItemRow(codigo = "ITEM-01", valor = "1000.00", cClass = "000001", dif = "0.00") {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><input type="text" class="form-control form-control-sm op-codigo" value="${codigo}" required /></td>
      <td><input type="number" step="0.01" min="0.01" class="form-control form-control-sm op-valor" value="${valor}" required /></td>
      <td>
        <select class="form-select form-select-sm op-cclasstrib">
          <option value="000001" ${cClass === "000001" ? "selected" : ""}>000001 (Integral)</option>
          <option value="200028" ${cClass === "200028" ? "selected" : ""}>200028 (Red. 60%)</option>
          <option value="200003" ${cClass === "200003" ? "selected" : ""}>200003 (Zero)</option>
        </select>
      </td>
      <td><input type="number" step="0.01" min="0" max="100" class="form-control form-control-sm op-dif" value="${dif}" /></td>
      <td class="text-end">
        <button type="button" class="btn btn-sm btn-outline-danger op-remove" title="Remover item">
          <i class="bi bi-trash"></i>
        </button>
      </td>
    `;
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

    tbody.replaceChildren(
      createItemRow("ITEM-01", "1000.00", "000001", "0.00"),
      createItemRow("ITEM-02", "1000.00", "200028", "50.00")
    );

    addBtn.addEventListener("click", () => {
      const idx = tbody.children.length + 1;
      tbody.appendChild(createItemRow(`ITEM-0${idx}`, "500.00", "000001", "0.00"));
    });

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const itens = Array.from(tbody.querySelectorAll("tr")).map((row) => ({
        codigo_item: row.querySelector(".op-codigo").value,
        valor_base: row.querySelector(".op-valor").value,
        c_class_trib: row.querySelector(".op-cclasstrib").value,
        aliquota_ibs_mun: "0.00",
        percentual_diferimento: row.querySelector(".op-dif").value || "0.00",
      }));

      const payload = {
        data_fato_gerador: form.op_data.value,
        uf: form.op_uf.value,
        itens,
      };

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

      resultEl.innerHTML = `
        <div class="result-box p-3">
          <div class="d-flex justify-content-between align-items-center mb-2">
            <strong>Consolidação (${data.quantidade_itens} itens - UF ${data.uf})</strong>
            <span class="badge text-bg-primary">Total: ${formatBRL(data.total_geral_operacao)}</span>
          </div>
          <div class="row g-2 small">
            <div class="col-4">Base Total: <strong>${formatBRL(data.total_base_calculo)}</strong></div>
            <div class="col-4">Total IBS: <strong>${formatBRL(data.total_ibs)}</strong></div>
            <div class="col-4">Total CBS: <strong>${formatBRL(data.total_cbs)}</strong></div>
            <div class="col-6">Total Diferido: <strong>${formatBRL(data.total_diferido)}</strong></div>
            <div class="col-6">Total Devido: <strong class="text-primary">${formatBRL(data.total_geral_operacao)}</strong></div>
          </div>
        </div>
      `;
    });
  });
})(window, document);
