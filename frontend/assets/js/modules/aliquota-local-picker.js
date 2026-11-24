/**
 * AliquotaLocalPicker - Componente reutilizável para Transição EC 132/LC 214 + ICMS UF / ISS Municipal.
 * Separa explicitamente UF Destino (IBS/ICMS) da UF/Município de Emissão/Incidência do ISS (LC 116, art. 3º).
 */
(function (window, document) {
  "use strict";

  const UFS_BR = "AC,AL,AM,AP,BA,CE,DF,ES,GO,MA,MG,MS,MT,PA,PB,PE,PI,PR,RJ,RN,RO,RR,RS,SC,SE,SP,TO".split(",");
  const _cacheIcms = new Map();
  let _cacheServicos = null;

  function escHtml(text) {
    return String(text ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function parseApiNum(raw) {
    const clean = String(raw ?? "").trim().replace(/\./g, "").replace(",", ".");
    return clean === "" || Number.isNaN(Number(clean)) ? null : clean;
  }

  function fmtBrPct(val) {
    const num = Number(val);
    return Number.isNaN(num) ? "" : num.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function asList(data) {
    return Array.isArray(data) ? data : data?.itens || [];
  }

  async function fetchJson(url) {
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  }

  async function loadServicosCatalog() {
    if (_cacheServicos) return _cacheServicos;
    _cacheServicos = asList(await fetchJson("/api/v1/tabelas/iss-servicos?limit=350"));
    return _cacheServicos;
  }

  async function loadIcmsMap(dataIso) {
    const key = dataIso || "today";
    if (_cacheIcms.has(key)) return _cacheIcms.get(key);
    const data = await fetchJson(`/api/v1/tabelas/icms-ufs?data_fato_gerador=${encodeURIComponent(dataIso)}`);
    const map = new Map(asList(data).map((r) => [r.uf, r]));
    _cacheIcms.set(key, map);
    return map;
  }

  function buildUfOptions(selectedUf) {
    return UFS_BR.map((uf) => `<option value="${uf}"${uf === selectedUf ? " selected" : ""}>${uf}</option>`).join("");
  }

  function buildMarkup(uid, showSimplesNote, initialUf) {
    const simplesNote = showSimplesNote
      ? '<span class="badge text-bg-light border text-muted"><i class="bi bi-shield-check me-1 text-success"></i>Simples DAS usa apenas LC 123</span>'
      : "";
    return `
      <div class="p-2 px-3 rounded border bg-light-subtle" data-picker-root="${uid}">
        <div class="d-flex flex-wrap align-items-center justify-content-between gap-2 mb-2">
          <div class="form-check form-switch mb-0">
            <input class="form-check-input" type="checkbox" role="switch" id="${uid}_enable" checked />
            <label class="form-check-label small fw-semibold" for="${uid}_enable">
              Aplicar Transição EC 132 + ICMS/ISS do Ano
            </label>
          </div>
          <div class="d-flex flex-wrap align-items-center gap-2">
            <span id="${uid}_faseBadge" class="badge text-bg-info text-dark">Carregando regra do ano...</span>
            ${simplesNote}
          </div>
        </div>

        <div id="${uid}_body" class="row g-2 align-items-end">
          <div class="col-md-3">
            <label for="${uid}_tipo" class="form-label small fw-semibold mb-1">Tributo Local Substituído</label>
            <select id="${uid}_tipo" class="form-select form-select-sm">
              <option value="icms">ICMS Estadual (Comércio/Indústria)</option>
              <option value="iss">ISS Municipal (Serviços LC 116)</option>
            </select>
          </div>

          <div class="col-md-3" id="${uid}_icmsWrap">
            <label for="${uid}_icmsInput" class="form-label small fw-semibold mb-1">Alíquota ICMS Modal (%)</label>
            <input id="${uid}_icmsInput" type="text" inputmode="decimal" class="form-control form-control-sm" placeholder="Auto UF (ex: 17,00)" />
          </div>

          <div class="col-md-6" id="${uid}_icmsHintWrap">
            <div class="small text-muted border rounded px-2 py-1 bg-white d-flex flex-wrap align-items-center justify-content-between gap-2" style="font-size: 0.78rem;">
              <span><i class="bi bi-geo-alt me-1 text-secondary"></i>ICMS é estadual (usa a UF). Para selecionar <strong>município</strong>, use <strong>ISS Municipal</strong>.</span>
              <button type="button" id="${uid}_switchIssBtn" class="btn btn-link btn-sm p-0 text-decoration-none fw-semibold" style="font-size: 0.78rem;">Trocar para ISS →</button>
            </div>
          </div>

          <div class="col-md-2 d-none" id="${uid}_ufIssWrap">
            <label for="${uid}_ufIss" class="form-label small fw-semibold mb-1" title="LC 116/2003 art. 3º: regra geral no estabelecimento prestador (emissão da NFS-e), independente da UF Destino do IBS.">UF Emissão/ISS</label>
            <select id="${uid}_ufIss" class="form-select form-select-sm">${buildUfOptions(initialUf)}</select>
          </div>

          <div class="col-md-3 d-none" id="${uid}_munWrap">
            <label for="${uid}_munInput" class="form-label small fw-semibold mb-1">Município Emissão/ISS (Prestador)</label>
            <input id="${uid}_munInput" list="${uid}_munList" type="text" class="form-control form-control-sm" placeholder="Cidade de emissão da NFS-e..." autocomplete="off" />
            <datalist id="${uid}_munList"></datalist>
          </div>

          <div class="col-md-2 d-none" id="${uid}_servWrap">
            <label for="${uid}_servInput" class="form-label small fw-semibold mb-1">Serviço LC 116</label>
            <input id="${uid}_servInput" list="${uid}_servList" type="text" class="form-control form-control-sm" value="01.01" placeholder="Ex: 01.01" autocomplete="off" />
            <datalist id="${uid}_servList"></datalist>
          </div>

          <div class="col-md-2 d-none" id="${uid}_issWrap">
            <label for="${uid}_issInput" class="form-label small fw-semibold mb-1">Alíquota ISS (%)</label>
            <input id="${uid}_issInput" type="text" inputmode="decimal" class="form-control form-control-sm" placeholder="Insira a alíquota ISS (2% a 5%)" />
          </div>

          <div class="col-12">
            <small id="${uid}_originMsg" class="text-muted d-block" style="font-size: 0.76rem;"></small>
          </div>
        </div>
      </div>
    `;
  }

  function mount(containerId, opts) {
    const container = document.getElementById(containerId);
    if (!container) return null;

    const uid = `lp_${containerId}`;
    const byId = (s) => document.getElementById(`${uid}_${s}`);
    const ufEl = opts.form.querySelector(opts.ufSelector);
    const dateEl = opts.form.querySelector(opts.dateSelector);
    const initialUf = (ufEl?.value || "RS").toUpperCase();
    container.innerHTML = buildMarkup(uid, Boolean(opts.showSimplesNote), initialUf);

    const els = {
      enable: byId("enable"), body: byId("body"), fase: byId("faseBadge"), tipo: byId("tipo"),
      icmsWrap: byId("icmsWrap"), icmsInput: byId("icmsInput"), icmsHintWrap: byId("icmsHintWrap"),
      switchIssBtn: byId("switchIssBtn"), ufIssWrap: byId("ufIssWrap"), ufIss: byId("ufIss"),
      munWrap: byId("munWrap"), munInput: byId("munInput"), munList: byId("munList"),
      servWrap: byId("servWrap"), servInput: byId("servInput"), servList: byId("servList"),
      issWrap: byId("issWrap"), issInput: byId("issInput"), msg: byId("originMsg"),
    };
    const state = {
      munMap: new Map(), selectedIbge: null, autoIcms: null, autoIss: null,
      issOrigem: "nao_informado", icmsUserEdited: false, issUserEdited: false, ufIssUserEdited: false,
    };

    if (opts.defaultTipo === "iss") els.tipo.value = "iss";

    const currentDateIso = () =>
      dateEl?.value || (window.BrNumber ? window.BrNumber.getTodayIso() : new Date().toISOString().slice(0, 10));
    const currentUfDestino = () => (ufEl?.value || "RS").toUpperCase();
    const currentUfIss = () => (els.ufIss?.value || currentUfDestino()).toUpperCase();

    function toggleVisibility() {
      els.body.classList.toggle("opacity-50", !els.enable.checked);
      const isIss = els.tipo.value === "iss";
      els.icmsWrap.classList.toggle("d-none", isIss);
      els.icmsHintWrap.classList.toggle("d-none", isIss);
      [els.ufIssWrap, els.munWrap, els.servWrap, els.issWrap].forEach((w) => w.classList.toggle("d-none", !isIss));
    }

    async function refreshFase() {
      try {
        const data = await fetchJson(`/api/v1/tabelas/transicao?data_fato_gerador=${encodeURIComponent(currentDateIso())}`);
        const pctLocal = Number(data.percentual_icms_iss ?? 0).toFixed(0);
        els.fase.textContent = data.titulo_curto || `${data.ano}: ICMS/ISS ${pctLocal}%`;
        els.fase.title = data.descricao || "";
      } catch {
        els.fase.textContent = "Regra de transição indisponível";
      }
    }

    async function refreshIcms() {
      try {
        const reg = (await loadIcmsMap(currentDateIso())).get(currentUfDestino());
        if (!reg) return;
        state.autoIcms = reg.aliquota_total;
        if (!state.icmsUserEdited) els.icmsInput.value = fmtBrPct(reg.aliquota_total);
        els.msg.innerHTML = `<i class="bi bi-check-circle-fill text-success me-1"></i>ICMS modal <strong>${escHtml(reg.uf)}</strong>: ${fmtBrPct(reg.aliquota_interna)}% + FCP ${fmtBrPct(reg.aliquota_fcp)}% = <strong>${fmtBrPct(reg.aliquota_total)}%</strong> (${escHtml(reg.fundamentacao)}).`;
      } catch {
        els.msg.textContent = "Não foi possível consultar a tabela de ICMS UF.";
      }
    }

    async function refreshMunicipios(queryNome = "") {
      try {
        const params = new URLSearchParams({ uf: currentUfIss(), limit: "60" });
        if (queryNome.trim()) params.set("nome", queryNome.trim());
        const data = await fetchJson(`/api/v1/tabelas/localidades?${params.toString()}`);
        state.munMap.clear();
        els.munList.innerHTML = asList(data)
          .map((m) => {
            const label = `${m.nome} - ${m.uf_sigla} (${m.codigo_ibge})`;
            state.munMap.set(label, Number(m.codigo_ibge));
            state.munMap.set(m.nome.toLowerCase(), Number(m.codigo_ibge));
            return `<option value="${escHtml(label)}"></option>`;
          })
          .join("");
      } catch { /* silencioso */ }
    }

    async function refreshServicosDatalist() {
      try {
        if (els.servList.children.length > 0) return;
        const itens = await loadServicosCatalog();
        const vistos = new Set();
        const optsHtml = [];
        itens.forEach((s) => {
          if (!vistos.has(s.subitem_lc116)) {
            vistos.add(s.subitem_lc116);
            optsHtml.push(`<option value="${escHtml(s.subitem_lc116)}">${escHtml(s.descricao)}</option>`);
          }
          optsHtml.push(`<option value="${escHtml(s.codigo_ctribnac)}">${escHtml(s.descricao)}</option>`);
        });
        els.servList.innerHTML = optsHtml.join("");
      } catch { /* silencioso */ }
    }

    function resolveIbgeFromInput() {
      const raw = els.munInput.value.trim();
      if (state.munMap.has(raw)) return state.munMap.get(raw);
      const match = raw.match(/\((\d{7})\)/);
      if (match) return Number(match[1]);
      if (/^\d{7}$/.test(raw)) return Number(raw);
      return state.munMap.get(raw.toLowerCase()) || null;
    }

    async function refreshIssLookup() {
      const ibge = resolveIbgeFromInput();
      state.selectedIbge = ibge;
      const serv = els.servInput.value.trim();
      const ufDest = currentUfDestino();
      if (!ibge || !serv) {
        state.autoIss = null;
        state.issOrigem = "nao_informado";
        els.issInput.placeholder = "Insira a alíquota ISS (2% a 5%)";
        els.msg.innerHTML = `<i class="bi bi-info-circle me-1"></i><strong>LC 116 (art. 3º):</strong> ISS incide no município de emissão/prestador (exceto obras, limpeza e eventos no local da prestação); IBS continua na UF Destino (<strong>${escHtml(ufDest)}</strong>).`;
        return;
      }
      try {
        const url = `/api/v1/tabelas/iss-municipal?codigo_ibge=${ibge}&codigo_servico=${encodeURIComponent(serv)}&data_fato_gerador=${encodeURIComponent(currentDateIso())}`;
        const res = await fetchJson(url);
        state.issOrigem = res.origem;
        const splitInfo = res.uf && res.uf !== ufDest ? ` • IBS no Destino: <strong>${escHtml(ufDest)}</strong>` : "";
        if (res.encontrado && res.aliquota_iss !== null) {
          state.autoIss = res.aliquota_iss;
          state.issUserEdited = false;
          els.issInput.value = fmtBrPct(res.aliquota_iss);
          els.issInput.classList.remove("border-warning");
          els.msg.innerHTML = `<i class="bi bi-check-circle-fill text-success me-1"></i>ISS em <strong>${escHtml(res.municipio_nome)}/${escHtml(res.uf)}</strong> (${escHtml(res.regiao)}) • Serviço <code>${escHtml(res.codigo_ctribnac)}</code>: <strong>${fmtBrPct(res.aliquota_iss)}%</strong> (Portal Nacional NFS-e)${splitInfo}.`;
        } else {
          state.autoIss = null;
          state.issUserEdited = false;
          els.issInput.value = "";
          els.issInput.placeholder = "Insira a alíquota ISS (2% a 5%)";
          els.issInput.classList.add("border-warning");
          els.msg.innerHTML = `<span class="text-warning-emphasis"><i class="bi bi-exclamation-triangle-fill me-1"></i><strong>Município não parametrizado</strong> — ${escHtml(res.mensagem)}${splitInfo}</span>`;
        }
      } catch {
        els.msg.textContent = "Falha ao consultar alíquota municipal de ISS.";
      }
    }

    async function refreshAll() {
      toggleVisibility();
      await refreshFase();
      if (els.tipo.value === "icms") {
        await refreshIcms();
      } else {
        await refreshServicosDatalist();
        await refreshMunicipios();
        await refreshIssLookup();
      }
    }

    els.enable.addEventListener("change", () => toggleVisibility());
    els.tipo.addEventListener("change", () => {
      state.icmsUserEdited = false;
      state.issUserEdited = false;
      refreshAll();
    });
    els.switchIssBtn.addEventListener("click", () => {
      els.tipo.value = "iss";
      state.issUserEdited = false;
      refreshAll().then(() => els.munInput.focus());
    });
    els.icmsInput.addEventListener("input", () => { state.icmsUserEdited = true; });
    els.issInput.addEventListener("input", () => {
      state.issUserEdited = true;
      els.issInput.classList.remove("border-warning");
    });
    els.ufIss.addEventListener("change", () => {
      state.ufIssUserEdited = true;
      els.munInput.value = "";
      state.selectedIbge = null;
      state.issUserEdited = false;
      refreshMunicipios().then(() => refreshIssLookup());
    });

    let munTimer = null;
    els.munInput.addEventListener("input", () => {
      clearTimeout(munTimer);
      munTimer = setTimeout(async () => {
        const ibge = resolveIbgeFromInput();
        if (ibge) await refreshIssLookup();
        else if (els.munInput.value.trim().length >= 2) await refreshMunicipios(els.munInput.value.trim());
      }, 220);
    });
    els.munInput.addEventListener("change", () => refreshIssLookup());
    els.servInput.addEventListener("change", () => refreshIssLookup());

    ufEl?.addEventListener("change", () => {
      state.icmsUserEdited = false;
      if (!state.ufIssUserEdited && els.ufIss) {
        els.ufIss.value = currentUfDestino();
        els.munInput.value = "";
        state.selectedIbge = null;
      }
      refreshAll();
    });
    dateEl?.addEventListener("change", () => refreshAll());

    refreshAll();

    return {
      refresh: refreshAll,
      setTipo(tipo) {
        if (tipo === "icms" || tipo === "iss") {
          els.tipo.value = tipo;
          refreshAll();
        }
      },
      getPayloadFields() {
        if (!els.enable.checked) return { aplicar_transicao_ano: false };
        const tipo = els.tipo.value;
        const out = { aplicar_transicao_ano: true, tipo_tributo_local: tipo };
        if (tipo === "icms") {
          const manual = parseApiNum(els.icmsInput.value);
          if (state.icmsUserEdited && manual !== null) out.aliquota_icms_manual = manual;
        } else {
          if (state.selectedIbge) out.codigo_ibge = state.selectedIbge;
          const serv = els.servInput.value.trim();
          if (serv) out.codigo_servico_iss = serv;
          const manual = parseApiNum(els.issInput.value);
          if (manual !== null && (state.issUserEdited || state.autoIss === null)) out.aliquota_iss_manual = manual;
        }
        return out;
      },
    };
  }

  function renderResumoBanner(trans) {
    if (!trans) return "";
    const tipoLabel = trans.tipo_tributo_local ? trans.tipo_tributo_local.toUpperCase() : "N/A";
    const alertStyle = trans.origem_aliquota_local === "nao_parametrizado" ? "alert-warning" : "alert-info";
    const extraMsg = trans.mensagem_aliquota_local ? `<div class="mt-1">${escHtml(trans.mensagem_aliquota_local)}</div>` : "";
    return `
      <div class="alert ${alertStyle} border-0 shadow-sm mb-3 py-2 small">
        <div class="d-flex flex-wrap justify-content-between align-items-center gap-2">
          <strong>
            <i class="bi bi-calendar2-week me-1"></i>Transição ${trans.ano} (${escHtml(trans.titulo_fase)}):
            ${tipoLabel} efetivo ${fmtBrPct(trans.aliquota_local_efetiva)}% (${fmtBrPct(trans.percentual_icms_iss_vigente)}% da alíquota cheia ${fmtBrPct(trans.aliquota_local_cheia)}%)
          </strong>
          <span class="badge text-bg-light border text-dark">
            IBS Efet. ${fmtBrPct(trans.aliquota_ibs_uf_efetiva)}% • CBS Efet. ${fmtBrPct(trans.aliquota_cbs_efetiva)}%
          </span>
        </div>
        ${extraMsg}
      </div>
    `;
  }

  window.AliquotaLocalPicker = { mount, renderResumoBanner };
})(window, document);
