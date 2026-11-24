/**
 * TabelasIcmsIssModule - Aba "ICMS (27 UFs) & ISS Municipal" na tela #tabelas.
 */
(function (window, document) {
  "use strict";

  function escHtml(text) {
    return String(text ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function fmtPct(val) {
    const num = Number(val);
    if (Number.isNaN(num)) return "0,00%";
    return `${num.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%`;
  }

  function asList(data) {
    return Array.isArray(data) ? data : data?.itens || [];
  }

  async function fetchJson(url) {
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  }

  async function carregarIcmsUfs(dataIso) {
    const tbody = document.getElementById("tabelasIcmsBody");
    const badge = document.getElementById("tabelasIcmsCount");
    if (!tbody) return;
    try {
      const data = await fetchJson(`/api/v1/tabelas/icms-ufs?data_fato_gerador=${encodeURIComponent(dataIso)}`);
      const itens = asList(data);
      if (badge) badge.textContent = String(itens.length);
      tbody.innerHTML = itens
        .map(
          (u) => `
          <tr>
            <td class="fw-bold">${escHtml(u.uf)}</td>
            <td class="text-end">${fmtPct(u.aliquota_interna)}</td>
            <td class="text-end">${fmtPct(u.aliquota_fcp)}</td>
            <td class="text-end fw-semibold text-primary">${fmtPct(u.aliquota_total)}</td>
            <td class="small text-muted">${escHtml(u.fundamentacao || "-")}</td>
          </tr>`
        )
        .join("");
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="5" class="text-danger small">${escHtml(err.message)}</td></tr>`;
    }
  }

  function bindIssLookup() {
    const ufSel = document.getElementById("tabIssUf");
    const munInput = document.getElementById("tabIssMun");
    const munList = document.getElementById("tabIssMunList");
    const servInput = document.getElementById("tabIssServ");
    const servList = document.getElementById("tabIssServList");
    const manualInput = document.getElementById("tabIssManual");
    const resultEl = document.getElementById("tabIssResult");
    const form = document.getElementById("tabIssLookupForm");
    const dataInput = document.getElementById("tabelasDataVigencia");
    if (!form || !ufSel || !munInput || !servInput || !resultEl) return;

    const munMap = new Map();

    async function loadServicos() {
      try {
        const data = await fetchJson("/api/v1/tabelas/iss-servicos?limit=350");
        const vistos = new Set();
        const opts = [];
        asList(data).forEach((s) => {
          if (!vistos.has(s.subitem_lc116)) {
            vistos.add(s.subitem_lc116);
            opts.push(`<option value="${escHtml(s.subitem_lc116)}">${escHtml(s.descricao)}</option>`);
          }
          opts.push(`<option value="${escHtml(s.codigo_ctribnac)}">${escHtml(s.descricao)}</option>`);
        });
        servList.innerHTML = opts.join("");
      } catch {
        /* silencioso */
      }
    }

    async function loadMunicipios(nome = "") {
      try {
        const p = new URLSearchParams({ uf: ufSel.value || "RS", limit: "60" });
        if (nome.trim()) p.set("nome", nome.trim());
        const data = await fetchJson(`/api/v1/tabelas/localidades?${p.toString()}`);
        munMap.clear();
        munList.innerHTML = asList(data)
          .map((m) => {
            const label = `${m.nome} - ${m.uf_sigla} (${m.codigo_ibge})`;
            munMap.set(label, Number(m.codigo_ibge));
            munMap.set(m.nome.toLowerCase(), Number(m.codigo_ibge));
            return `<option value="${escHtml(label)}"></option>`;
          })
          .join("");
      } catch {
        /* silencioso */
      }
    }

    function resolveIbge() {
      const raw = munInput.value.trim();
      if (munMap.has(raw)) return munMap.get(raw);
      const match = raw.match(/\((\d{7})\)/);
      if (match) return Number(match[1]);
      if (/^\d{7}$/.test(raw)) return Number(raw);
      return munMap.get(raw.toLowerCase()) || null;
    }

    ufSel.addEventListener("change", () => {
      munInput.value = "";
      loadMunicipios();
    });
    let timer = null;
    munInput.addEventListener("input", () => {
      clearTimeout(timer);
      timer = setTimeout(() => {
        if (!resolveIbge() && munInput.value.trim().length >= 2) loadMunicipios(munInput.value.trim());
      }, 220);
    });

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const ibge = resolveIbge();
      const serv = servInput.value.trim();
      const dataIso = dataInput?.value || new Date().toISOString().slice(0, 10);
      if (!ibge || !serv) {
        resultEl.innerHTML = '<div class="alert alert-warning py-2 small mb-0">Selecione o município IBGE e o código de serviço LC 116.</div>';
        return;
      }
      try {
        const r = await fetchJson(
          `/api/v1/tabelas/iss-municipal?codigo_ibge=${ibge}&codigo_servico=${encodeURIComponent(serv)}&data_fato_gerador=${encodeURIComponent(dataIso)}`
        );
        if (r.encontrado && r.aliquota_iss !== null) {
          if (manualInput) {
            manualInput.value = Number(r.aliquota_iss).toLocaleString("pt-BR", { minimumFractionDigits: 2 });
            manualInput.classList.remove("border-warning");
          }
          resultEl.innerHTML = `
            <div class="alert alert-success py-2 small mb-0">
              <strong>${escHtml(r.municipio_nome)}/${escHtml(r.uf)}</strong> (${escHtml(r.regiao)}) •
              Serviço <code>${escHtml(r.codigo_ctribnac)}</code> (${escHtml(r.descricao_servico)}):
              <strong class="fs-6 ms-1">${fmtPct(r.aliquota_iss)}</strong>
              <span class="ms-2 badge text-bg-light border text-dark">Transição ${r.regra_transicao.ano}: ${r.regra_transicao.percentual_icms_iss}% vigente</span>
            </div>`;
        } else {
          if (manualInput) {
            manualInput.value = "";
            manualInput.placeholder = "Insira a alíquota ISS (2% a 5%)";
            manualInput.classList.add("border-warning");
          }
          resultEl.innerHTML = `
            <div class="alert alert-warning py-2 small mb-0">
              <i class="bi bi-exclamation-triangle-fill me-1"></i><strong>${escHtml(r.origem)}</strong> — ${escHtml(r.mensagem)}
            </div>`;
        }
      } catch (err) {
        resultEl.innerHTML = `<div class="alert alert-danger py-2 small mb-0">${escHtml(err.message)}</div>`;
      }
    });

    loadServicos();
    loadMunicipios();
  }

  document.addEventListener("partial:loaded", (event) => {
    if (event.detail.route !== "tabelas") return;
    const dataInput = document.getElementById("tabelasDataVigencia");
    const filterForm = document.getElementById("tabelasFilterForm");
    const getDataIso = () => dataInput?.value || (window.BrNumber ? window.BrNumber.getTodayIso() : new Date().toISOString().slice(0, 10));

    carregarIcmsUfs(getDataIso());
    bindIssLookup();
    filterForm?.addEventListener("submit", () => carregarIcmsUfs(getDataIso()));
  });
})(window, document);
