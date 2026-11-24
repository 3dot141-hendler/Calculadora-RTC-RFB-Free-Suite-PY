/**
 * AliquotaLocalPicker - Componente reutilizável para Transição EC 132/LC 214 + ICMS UF / ISS Municipal.
 * Usado no Comparador (Simples/Híbrido/Regular e Presumido/Real) e no Regime Regular Multi-Itens.
 */
(function (window, document) {
  "use strict";

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
    if (Number.isNaN(num)) return "";
    return num.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
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
    const data = await fetchJson("/api/v1/tabelas/iss-servicos?limit=350");
    _cacheServicos = asList(data);
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

  function buildMarkup(uid, showSimplesNote) {
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

          <div class="col-md-3 d-none" id="${uid}_munWrap">
            <label for="${uid}_munInput" class="form-label small fw-semibold mb-1">Município IBGE (da UF)</label>
            <input id="${uid}_munInput" list="${uid}_munList" type="text" class="form-control form-control-sm" placeholder="Digite a cidade..." autocomplete="off" />
            <datalist id="${uid}_munList"></datalist>
          </div>

          <div class="col-md-3 d-none" id="${uid}_servWrap">
            <label for="${uid}_servInput" class="form-label small fw-semibold mb-1">Serviço LC 116 / cTribNac</label>
            <input id="${uid}_servInput" list="${uid}_servList" type="text" class="form-control form-control-sm" value="01.01" placeholder="Ex: 01.01 ou 14.01" autocomplete="off" />
            <datalist id="${uid}_servList"></datalist>
          </div>

          <div class="col-md-3 d-none" id="${uid}_issWrap">
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
    const form = opts.form;
    const ufEl = form.querySelector(opts.ufSelector);
    const dateEl = form.querySelector(opts.dateSelector);
    container.innerHTML = buildMarkup(uid, Boolean(opts.showSimplesNote));

    const elEnable = document.getElementById(`${uid}_enable`);
    const elBody = document.getElementById(`${uid}_body`);
    const elFase = document.getElementById(`${uid}_faseBadge`);
    const elTipo = document.getElementById(`${uid}_tipo`);
    const elIcmsWrap = document.getElementById(`${uid}_icmsWrap`);
    const elIcmsInput = document.getElementById(`${uid}_icmsInput`);
    const elMunWrap = document.getElementById(`${uid}_munWrap`);
    const elMunInput = document.getElementById(`${uid}_munInput`);
    const elMunList = document.getElementById(`${uid}_munList`);
    const elServWrap = document.getElementById(`${uid}_servWrap`);
    const elServInput = document.getElementById(`${uid}_servInput`);
    const elServList = document.getElementById(`${uid}_servList`);
    const elIssWrap = document.getElementById(`${uid}_issWrap`);
    const elIssInput = document.getElementById(`${uid}_issInput`);
    const elMsg = document.getElementById(`${uid}_originMsg`);

    const state = {
      munMap: new Map(),
      selectedIbge: null,
      autoIcms: null,
      autoIss: null,
      issOrigem: "nao_informado",
      icmsUserEdited: false,
      issUserEdited: false,
    };

    if (opts.defaultTipo === "iss") elTipo.value = "iss";

    function currentDateIso() {
      return dateEl?.value || (window.BrNumber ? window.BrNumber.getTodayIso() : new Date().toISOString().slice(0, 10));
    }
    function currentUf() {
      return (ufEl?.value || "RS").toUpperCase();
    }

    function toggleVisibility() {
      const enabled = elEnable.checked;
      elBody.classList.toggle("opacity-50", !enabled);
      const isIss = elTipo.value === "iss";
      elIcmsWrap.classList.toggle("d-none", isIss);
      elMunWrap.classList.toggle("d-none", !isIss);
      elServWrap.classList.toggle("d-none", !isIss);
      elIssWrap.classList.toggle("d-none", !isIss);
    }

    async function refreshFase() {
      try {
        const data = await fetchJson(`/api/v1/tabelas/transicao?data_fato_gerador=${encodeURIComponent(currentDateIso())}`);
        const pctLocal = Number(data.percentual_icms_iss ?? 0).toFixed(0);
        elFase.textContent = data.titulo_curto || `${data.ano}: ICMS/ISS ${pctLocal}%`;
        elFase.title = data.descricao || "";
      } catch {
        elFase.textContent = "Regra de transição indisponível";
      }
    }

    async function refreshIcms() {
      try {
        const map = await loadIcmsMap(currentDateIso());
        const reg = map.get(currentUf());
        if (reg) {
          state.autoIcms = reg.aliquota_total;
          if (!state.icmsUserEdited) elIcmsInput.value = fmtBrPct(reg.aliquota_total);
          elMsg.innerHTML = `<i class="bi bi-check-circle-fill text-success me-1"></i>ICMS modal <strong>${escHtml(reg.uf)}</strong>: ${fmtBrPct(reg.aliquota_interna)}% + FCP ${fmtBrPct(reg.aliquota_fcp)}% = <strong>${fmtBrPct(reg.aliquota_total)}%</strong> (${escHtml(reg.fundamentacao)}).`;
        }
      } catch {
        elMsg.textContent = "Não foi possível consultar a tabela de ICMS UF.";
      }
    }

    async function refreshMunicipios(queryNome = "") {
      try {
        const params = new URLSearchParams({ uf: currentUf(), limit: "60" });
        if (queryNome.trim()) params.set("nome", queryNome.trim());
        const data = await fetchJson(`/api/v1/tabelas/localidades?${params.toString()}`);
        state.munMap.clear();
        elMunList.innerHTML = asList(data)
          .map((m) => {
            const label = `${m.nome} - ${m.uf_sigla} (${m.codigo_ibge})`;
            state.munMap.set(label, Number(m.codigo_ibge));
            state.munMap.set(m.nome.toLowerCase(), Number(m.codigo_ibge));
            return `<option value="${escHtml(label)}"></option>`;
          })
          .join("");
      } catch {
        /* silencioso */
      }
    }

    async function refreshServicosDatalist() {
      try {
        const itens = await loadServicosCatalog();
        if (elServList.children.length > 0) return;
        const vistos = new Set();
        const optsHtml = [];
        itens.forEach((s) => {
          if (!vistos.has(s.subitem_lc116)) {
            vistos.add(s.subitem_lc116);
            optsHtml.push(`<option value="${escHtml(s.subitem_lc116)}">${escHtml(s.descricao)}</option>`);
          }
          optsHtml.push(`<option value="${escHtml(s.codigo_ctribnac)}">${escHtml(s.descricao)}</option>`);
        });
        elServList.innerHTML = optsHtml.join("");
      } catch {
        /* silencioso */
      }
    }

    function resolveIbgeFromInput() {
      const raw = elMunInput.value.trim();
      if (state.munMap.has(raw)) return state.munMap.get(raw);
      const match = raw.match(/\((\d{7})\)/);
      if (match) return Number(match[1]);
      if (/^\d{7}$/.test(raw)) return Number(raw);
      return state.munMap.get(raw.toLowerCase()) || null;
    }

    async function refreshIssLookup() {
      const ibge = resolveIbgeFromInput();
      state.selectedIbge = ibge;
      const serv = elServInput.value.trim();
      if (!ibge || !serv) {
        state.autoIss = null;
        state.issOrigem = "nao_informado";
        elIssInput.placeholder = "Insira a alíquota ISS (2% a 5%)";
        elMsg.innerHTML = '<i class="bi bi-info-circle me-1"></i>Selecione um município IBGE e o subitem LC 116 para buscar a alíquota oficial, ou digite manualmente.';
        return;
      }
      try {
        const url = `/api/v1/tabelas/iss-municipal?codigo_ibge=${ibge}&codigo_servico=${encodeURIComponent(serv)}&data_fato_gerador=${encodeURIComponent(currentDateIso())}`;
        const res = await fetchJson(url);
        state.issOrigem = res.origem;
        if (res.encontrado && res.aliquota_iss !== null) {
          state.autoIss = res.aliquota_iss;
          state.issUserEdited = false;
          elIssInput.value = fmtBrPct(res.aliquota_iss);
          elIssInput.classList.remove("border-warning");
          elMsg.innerHTML = `<i class="bi bi-check-circle-fill text-success me-1"></i><strong>${escHtml(res.municipio_nome)}/${escHtml(res.uf)}</strong> (${escHtml(res.regiao)}) • Serviço <code>${escHtml(res.codigo_ctribnac)}</code>: <strong>${fmtBrPct(res.aliquota_iss)}%</strong> (Portal Nacional NFS-e).`;
        } else {
          state.autoIss = null;
          state.issUserEdited = false;
          elIssInput.value = "";
          elIssInput.placeholder = "Insira a alíquota ISS (2% a 5%)";
          elIssInput.classList.add("border-warning");
          elMsg.innerHTML = `<span class="text-warning-emphasis"><i class="bi bi-exclamation-triangle-fill me-1"></i><strong>Município não parametrizado</strong> — ${escHtml(res.mensagem)}</span>`;
        }
      } catch {
        elMsg.textContent = "Falha ao consultar alíquota municipal de ISS.";
      }
    }

    async function refreshAll() {
      toggleVisibility();
      await refreshFase();
      if (elTipo.value === "icms") {
        await refreshIcms();
      } else {
        await refreshServicosDatalist();
        await refreshMunicipios();
        await refreshIssLookup();
      }
    }

    elEnable.addEventListener("change", () => toggleVisibility());
    elTipo.addEventListener("change", () => {
      state.icmsUserEdited = false;
      state.issUserEdited = false;
      refreshAll();
    });
    elIcmsInput.addEventListener("input", () => { state.icmsUserEdited = true; });
    elIssInput.addEventListener("input", () => {
      state.issUserEdited = true;
      elIssInput.classList.remove("border-warning");
    });

    let munTimer = null;
    elMunInput.addEventListener("input", () => {
      clearTimeout(munTimer);
      munTimer = setTimeout(async () => {
        const ibge = resolveIbgeFromInput();
        if (ibge) {
          await refreshIssLookup();
        } else if (elMunInput.value.trim().length >= 2) {
          await refreshMunicipios(elMunInput.value.trim());
        }
      }, 220);
    });
    elMunInput.addEventListener("change", () => refreshIssLookup());
    elServInput.addEventListener("change", () => refreshIssLookup());

    ufEl?.addEventListener("change", () => {
      state.icmsUserEdited = false;
      elMunInput.value = "";
      state.selectedIbge = null;
      refreshAll();
    });
    dateEl?.addEventListener("change", () => refreshAll());

    refreshAll();

    return {
      refresh: refreshAll,
      setTipo(tipo) {
        if (tipo === "icms" || tipo === "iss") {
          elTipo.value = tipo;
          refreshAll();
        }
      },
      getPayloadFields() {
        if (!elEnable.checked) return { aplicar_transicao_ano: false };
        const tipo = elTipo.value;
        const out = { aplicar_transicao_ano: true, tipo_tributo_local: tipo };
        if (tipo === "icms") {
          const manual = parseApiNum(elIcmsInput.value);
          if (state.icmsUserEdited && manual !== null) out.aliquota_icms_manual = manual;
        } else {
          if (state.selectedIbge) out.codigo_ibge = state.selectedIbge;
          const serv = elServInput.value.trim();
          if (serv) out.codigo_servico_iss = serv;
          const manual = parseApiNum(elIssInput.value);
          if (manual !== null && (state.issUserEdited || state.autoIss === null)) {
            out.aliquota_iss_manual = manual;
          }
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
