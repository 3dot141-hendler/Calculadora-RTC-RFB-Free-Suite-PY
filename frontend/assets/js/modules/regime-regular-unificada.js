/**
 * RegimeRegularUnificadaModule - Submódulo JS para Base de Cálculo Unificada
 * NF-e/NFC-e (/base-calculo/unificada) e NFS-e / Locação 99.03 (/base-calculo/unificada-nfse).
 */
(function (window, document) {
  "use strict";

  const UFS_BR = "AC,AL,AM,AP,BA,CE,DF,ES,GO,MA,MG,MS,MT,PA,PB,PE,PI,PR,RJ,RN,RO,RR,RS,SC,SE,SP,TO".split(",");

  function formatBRL(value) {
    if (value === null || value === undefined) return "N/A";
    const num = Number(value);
    if (Number.isNaN(num)) return "R$ 0,00";
    return num.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
  }

  function formatBrNum(value) {
    const num = Number(value);
    return Number.isNaN(num) ? "0,00" : num.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function toApiNum(raw, fallback = "0.00") {
    if (window.BrNumber) {
      return window.BrNumber.parseToApiDecimal(raw, fallback);
    }
    const cleaned = String(raw ?? "").trim().replace(/\./g, "").replace(",", ".");
    return cleaned === "" ? fallback : cleaned;
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;");
  }

  function asList(data) {
    return Array.isArray(data) ? data : data?.itens || [];
  }

  async function fetchJson(url) {
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  }

  function bindNfseIssHelper(form) {
    const box = document.getElementById("nfseIssHelperBox");
    if (!box) return;

    const ufOpts = UFS_BR.map((u) => `<option value="${u}"${u === "RS" ? " selected" : ""}>${u}</option>`).join("");
    box.innerHTML = `
      <div class="p-2 px-3 rounded border bg-light-subtle my-1" data-picker-root="nfseIssHelper">
        <div class="d-flex flex-wrap align-items-center justify-content-between gap-2">
          <div class="form-check form-switch mb-0">
            <input class="form-check-input" type="checkbox" role="switch" id="nfseIssAutoToggle" />
            <label class="form-check-label small fw-semibold" for="nfseIssAutoToggle">
              Calcular <code>vISSQN</code> automaticamente pelo município de emissão (opcional)
            </label>
          </div>
          <span id="nfseIssFaseBadge" class="badge text-bg-light border text-muted d-none">Transição ISS</span>
        </div>
        <div id="nfseIssHelperBody" class="row g-2 align-items-end mt-1 d-none">
          <div class="col-md-2">
            <label for="nfseIssUf" class="form-label small fw-semibold mb-1">UF Emissão/ISS</label>
            <select id="nfseIssUf" class="form-select form-select-sm">${ufOpts}</select>
          </div>
          <div class="col-md-4">
            <label for="nfseIssMun" class="form-label small fw-semibold mb-1">Município Emissão/ISS (Prestador)</label>
            <input id="nfseIssMun" list="nfseIssMunList" type="text" class="form-control form-control-sm" placeholder="Cidade de emissão da NFS-e..." autocomplete="off" />
            <datalist id="nfseIssMunList"></datalist>
          </div>
          <div class="col-md-3">
            <label for="nfseIssServ" class="form-label small fw-semibold mb-1">Serviço LC 116</label>
            <input id="nfseIssServ" list="nfseIssServList" type="text" class="form-control form-control-sm" value="01.01" placeholder="Ex: 01.01" autocomplete="off" />
            <datalist id="nfseIssServList"></datalist>
          </div>
          <div class="col-md-3">
            <label for="nfseIssAliq" class="form-label small fw-semibold mb-1">Alíquota ISS (%)</label>
            <input id="nfseIssAliq" type="text" inputmode="decimal" class="form-control form-control-sm" placeholder="Insira a alíquota ISS (2% a 5%)" />
          </div>
          <div class="col-12">
            <small id="nfseIssMsg" class="text-muted d-block" style="font-size: 0.76rem;"></small>
          </div>
        </div>
      </div>
    `;

    const elToggle = document.getElementById("nfseIssAutoToggle");
    const elBody = document.getElementById("nfseIssHelperBody");
    const elBadge = document.getElementById("nfseIssFaseBadge");
    const elUf = document.getElementById("nfseIssUf");
    const elMun = document.getElementById("nfseIssMun");
    const elMunList = document.getElementById("nfseIssMunList");
    const elServ = document.getElementById("nfseIssServ");
    const elServList = document.getElementById("nfseIssServList");
    const elAliq = document.getElementById("nfseIssAliq");
    const elMsg = document.getElementById("nfseIssMsg");

    const state = { munMap: new Map(), pctVigente: 100, anoAtual: 2026, infoFonte: "" };
    const getDataIso = () => `${Number(form.nfse_ano.value) || new Date().getFullYear()}-06-15`;

    function resolveIbge() {
      const raw = elMun.value.trim();
      if (state.munMap.has(raw)) return state.munMap.get(raw);
      const m = raw.match(/\((\d{7})\)/);
      if (m) return Number(m[1]);
      if (/^\d{7}$/.test(raw)) return Number(raw);
      return state.munMap.get(raw.toLowerCase()) || null;
    }

    function applyCalculatedVissqn() {
      if (!elToggle.checked) return;
      const aliqNum = Number(toApiNum(elAliq.value, ""));
      if (elAliq.value.trim() === "" || Number.isNaN(aliqNum) || aliqNum < 0) return;
      const vServ = Number(toApiNum(form.nfse_vserv.value, "0")) || 0;
      const vDesc = Number(toApiNum(form.nfse_vdesc.value, "0")) || 0;
      const base = Math.max(0, vServ - vDesc);
      const efetiva = aliqNum * (state.pctVigente / 100);
      const vissqn = Math.round(base * efetiva) / 100;
      form.nfse_vissqn.value = formatBrNum(vissqn);
      if (state.infoFonte) {
        elMsg.innerHTML = `${state.infoFonte} → <strong>vISSQN = ${formatBRL(vissqn)}</strong> (${formatBrNum(aliqNum)}% × ${state.pctVigente.toFixed(0)}% em ${state.anoAtual} sobre ${formatBRL(base)}).`;
      }
    }

    async function refreshTransicao() {
      try {
        const t = await fetchJson(`/api/v1/tabelas/transicao?data_fato_gerador=${encodeURIComponent(getDataIso())}`);
        state.pctVigente = Number(t.percentual_icms_iss ?? 100);
        state.anoAtual = Number(t.ano || form.nfse_ano.value || 2026);
        elBadge.textContent = `ISS ${state.pctVigente.toFixed(0)}% em ${state.anoAtual}`;
      } catch {
        state.pctVigente = 100;
      }
    }

    async function refreshMunicipios(nome = "") {
      try {
        const params = new URLSearchParams({ uf: elUf.value, limit: "60" });
        if (nome.trim()) params.set("nome", nome.trim());
        const itens = asList(await fetchJson(`/api/v1/tabelas/localidades?${params.toString()}`));
        state.munMap.clear();
        elMunList.innerHTML = itens
          .map((m) => {
            const label = `${m.nome} - ${m.uf_sigla} (${m.codigo_ibge})`;
            state.munMap.set(label, Number(m.codigo_ibge));
            state.munMap.set(m.nome.toLowerCase(), Number(m.codigo_ibge));
            return `<option value="${escapeHtml(label)}"></option>`;
          })
          .join("");
      } catch { /* silencioso */ }
    }

    async function loadServicos() {
      if (elServList.children.length > 0) return;
      try {
        const itens = asList(await fetchJson("/api/v1/tabelas/iss-servicos?limit=350"));
        const vistos = new Set();
        const opts = [];
        itens.forEach((s) => {
          if (!vistos.has(s.subitem_lc116)) {
            vistos.add(s.subitem_lc116);
            opts.push(`<option value="${escapeHtml(s.subitem_lc116)}">${escapeHtml(s.descricao)}</option>`);
          }
          opts.push(`<option value="${escapeHtml(s.codigo_ctribnac)}">${escapeHtml(s.descricao)}</option>`);
        });
        elServList.innerHTML = opts.join("");
      } catch { /* silencioso */ }
    }

    async function lookupIss() {
      await refreshTransicao();
      const ibge = resolveIbge();
      const serv = elServ.value.trim();
      if (!ibge || !serv) {
        state.infoFonte = "";
        elMsg.innerHTML = '<i class="bi bi-info-circle me-1"></i>LC 116 (art. 3º): selecione UF/município do prestador (emissão) e serviço para preencher <code>vISSQN</code> automaticamente.';
        return;
      }
      try {
        const url = `/api/v1/tabelas/iss-municipal?codigo_ibge=${ibge}&codigo_servico=${encodeURIComponent(serv)}&data_fato_gerador=${encodeURIComponent(getDataIso())}`;
        const res = await fetchJson(url);
        if (res.encontrado && res.aliquota_iss !== null) {
          elAliq.value = formatBrNum(res.aliquota_iss);
          elAliq.classList.remove("border-warning");
          state.infoFonte = `<i class="bi bi-check-circle-fill text-success me-1"></i><strong>${escapeHtml(res.municipio_nome)}/${escapeHtml(res.uf)}</strong> (${escapeHtml(res.codigo_ctribnac)})`;
          applyCalculatedVissqn();
        } else {
          elAliq.value = "";
          elAliq.placeholder = "Insira a alíquota ISS (2% a 5%)";
          elAliq.classList.add("border-warning");
          state.infoFonte = `<i class="bi bi-pencil-square text-primary me-1"></i>Alíquota ISS manual (${escapeHtml(res.municipio_nome || "Município")})`;
          elMsg.innerHTML = `<span class="text-warning-emphasis"><i class="bi bi-exclamation-triangle-fill me-1"></i><strong>Município não parametrizado</strong> — ${escapeHtml(res.mensagem)}</span>`;
        }
      } catch {
        elMsg.textContent = "Falha ao consultar alíquota municipal de ISS.";
      }
    }

    elToggle.addEventListener("change", async () => {
      const on = elToggle.checked;
      elBody.classList.toggle("d-none", !on);
      elBadge.classList.toggle("d-none", !on);
      if (on) {
        await Promise.all([loadServicos(), refreshMunicipios(), refreshTransicao()]);
        await lookupIss();
      }
    });
    elUf.addEventListener("change", () => { elMun.value = ""; refreshMunicipios().then(lookupIss); });
    let munTimer = null;
    elMun.addEventListener("input", () => {
      clearTimeout(munTimer);
      munTimer = setTimeout(async () => {
        if (resolveIbge()) await lookupIss();
        else if (elMun.value.trim().length >= 2) await refreshMunicipios(elMun.value.trim());
      }, 220);
    });
    elMun.addEventListener("change", lookupIss);
    elServ.addEventListener("change", lookupIss);
    elAliq.addEventListener("input", () => {
      elAliq.classList.remove("border-warning");
      if (!state.infoFonte) state.infoFonte = '<i class="bi bi-pencil-square text-primary me-1"></i>Alíquota ISS manual';
      applyCalculatedVissqn();
    });
    form.nfse_vserv.addEventListener("input", applyCalculatedVissqn);
    form.nfse_vdesc.addEventListener("input", applyCalculatedVissqn);
    form.nfse_ano.addEventListener("change", () => { if (elToggle.checked) lookupIss(); });
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

    bindNfseIssHelper(form);

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
