/**
 * RegimeRegularUnificadaModule - Submódulo JS para Base de Cálculo Unificada
 * NF-e/NFC-e (/base-calculo/unificada) e NFS-e / Locação 99.03 (/base-calculo/unificada-nfse).
 */
(function (window, document) {
  "use strict";

  function formatBRL(value) {
    if (value === null || value === undefined) return "N/A";
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

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;");
  }

  function bindBaseUnificadaNfe() {
    const form = document.getElementById("baseUnificadaNfeForm");
    const resultEl = document.getElementById("baseUnificadaNfeResult");
    if (!form || !resultEl) return;

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const payload = {
        ano_fato_gerador: Number(form.unif_ano.value),
        natureza: form.unif_natureza.value,
        tipo_documento: Number(form.unif_tp_doc.value),
        componentes: {
          vProd: toApiNum(form.unif_vprod.value),
          vFrete: toApiNum(form.unif_vfrete.value),
          vII: toApiNum(form.unif_vii.value),
          vIS: toApiNum(form.unif_vis.value),
          vDesc: toApiNum(form.unif_vdesc.value),
          vPIS: toApiNum(form.unif_vpis.value),
          vCOFINS: toApiNum(form.unif_vcofins.value),
          vICMS: toApiNum(form.unif_vicms.value),
          vISSQN: toApiNum(form.unif_vissqn.value),
        },
      };

      const res = await fetch("/api/v1/regime-regular/base-calculo/unificada", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) {
        resultEl.innerHTML = `<div class="alert alert-danger mb-0">${escapeHtml(data.detail)}</div>`;
        return;
      }

      const avisosHtml = data.avisos?.length
        ? `<ul class="small text-warning-emphasis mb-0 mt-2">${data.avisos.map((a) => `<li>${escapeHtml(a)}</li>`).join("")}</ul>`
        : `<small class="text-success d-block mt-2">Nenhum aviso de vigência, natureza ou modelo.</small>`;

      resultEl.innerHTML = `
        <div class="result-box p-3">
          <div class="row g-2 small">
            <div class="col-md-4">Base RG (IBS/CBS): <strong class="text-primary">${formatBRL(data.baseRG)}</strong></div>
            <div class="col-md-4">Base IS: <strong>${formatBRL(data.baseIS)}</strong></div>
            <div class="col-md-4">Base SN: <strong>${formatBRL(data.baseSN)}</strong></div>
          </div>
          ${avisosHtml}
        </div>
      `;
    });
  }

  function bindBaseUnificadaNfse() {
    const form = document.getElementById("baseUnificadaNfseForm");
    const resultEl = document.getElementById("baseUnificadaNfseResult");
    const locBox = document.getElementById("nfseLocacaoFields");
    const regApWrap = document.getElementById("nfseRegApWrap");
    if (!form || !resultEl) return;

    function syncVisibility() {
      const isLoc = form.nfse_situacao.value === "locacao9903";
      const op = Number(form.nfse_op_sn.value);
      if (locBox) locBox.classList.toggle("d-none", !isLoc);
      if (regApWrap) regApWrap.classList.toggle("d-none", op !== 3 && op !== 4);
    }
    form.nfse_situacao.addEventListener("change", syncVisibility);
    form.nfse_op_sn.addEventListener("change", syncVisibility);
    syncVisibility();

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const opSn = Number(form.nfse_op_sn.value);
      const situacao = form.nfse_situacao.value;
      const ajusteVal = Number(toApiNum(form.nfse_vajuste.value, "0.00"));

      const payload = {
        ano_fato_gerador: Number(form.nfse_ano.value),
        opSimpNac: opSn,
        situacao,
        vServ: toApiNum(form.nfse_vserv.value),
        vDescIncond: toApiNum(form.nfse_vdesc.value),
        vISSQN: toApiNum(form.nfse_vissqn.value),
        vPIS: toApiNum(form.nfse_vpis.value),
        vCOFINS: toApiNum(form.nfse_vcofins.value),
        documentos: ajusteVal > 0
          ? [{
              tpAjusteBC: form.nfse_tp_ajuste.value,
              xTpAjusteBC: form.nfse_xtp_ajuste.value.trim() || null,
              vAjusteAplic: toApiNum(form.nfse_vajuste.value),
            }]
          : [],
      };
      if (opSn === 3 || opSn === 4) {
        payload.regApIBSCBSSN = Number(form.nfse_reg_ap.value);
      }
      if (situacao === "locacao9903") {
        payload.locacao = {
          pCopropriedade: toApiNum(form.nfse_pcoprop.value, "100.00"),
          vTotOper: toApiNum(form.nfse_vtot_oper.value),
          vDescIncondTot: toApiNum(form.nfse_vdesc_loc.value),
          somaAjustesLocImoveis: toApiNum(form.nfse_vajuste_loc.value),
        };
      }

      const res = await fetch("/api/v1/regime-regular/base-calculo/unificada-nfse", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) {
        resultEl.innerHTML = `<div class="alert alert-danger mb-0">${escapeHtml(data.detail)}</div>`;
        return;
      }

      const errosHtml = data.erros?.length
        ? `<div class="alert alert-danger py-2 px-3 mt-2 mb-0 small">${data.erros.map((er) => `<div><strong>${escapeHtml(er.codigo)}:</strong> ${escapeHtml(er.mensagem)}</div>`).join("")}</div>`
        : "";
      const avisosHtml = data.avisos?.length
        ? `<ul class="small text-warning-emphasis mb-0 mt-2">${data.avisos.map((a) => `<li>${escapeHtml(a)}</li>`).join("")}</ul>`
        : "";

      resultEl.innerHTML = `
        <div class="result-box p-3">
          <div class="row g-2 small">
            <div class="col-md-4">Base RG (IBS/CBS): <strong class="text-primary">${formatBRL(data.baseRG)}</strong></div>
            <div class="col-md-4">Base SN: <strong>${formatBRL(data.baseSN)}</strong></div>
            <div class="col-md-4">Ajustes IBS/CBS: <strong>${formatBRL(data.vCalcAjusteBCIBSCBS)}</strong></div>
          </div>
          ${avisosHtml}
          ${errosHtml}
        </div>
      `;
    });
  }

  document.addEventListener("partial:loaded", (event) => {
    if (event.detail.route !== "regime-regular") return;
    bindBaseUnificadaNfe();
    bindBaseUnificadaNfse();
  });
})(window, document);
