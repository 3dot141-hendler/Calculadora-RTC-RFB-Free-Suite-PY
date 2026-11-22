/**
 * TabelasModule - Submódulo JS dedicado para consulta às Tabelas Oficiais (RFB).
 */
(function (window, document) {
  "use strict";

  const API_BASE = "/api/v1/tabelas";

  function createCell(text, className = "") {
    const td = document.createElement("td");
    if (className) td.className = className;
    td.textContent = text ?? "-";
    return td;
  }

  function setBadgeCount(id, count) {
    const el = document.getElementById(id);
    if (el) el.textContent = String(count);
  }

  function formatPctLabel(value) {
    const num = Number(value);
    if (Number.isNaN(num)) return `${value ?? "0,00"}%`;
    return `${num.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%`;
  }

  async function carregarCsts(dataIso, cstCode = "", queryText = "") {
    const params = new URLSearchParams({ data_fato_gerador: dataIso });
    if (cstCode && cstCode.trim().length === 3) params.set("cst", cstCode.trim());
    if (queryText && queryText.trim().length >= 1) params.set("q", queryText.trim());

    const res = await fetch(`${API_BASE}/cst?${params.toString()}`);
    const cstBody = document.getElementById("tabelasCstBody");
    if (!cstBody || !res.ok) return;

    const csts = await res.json();
    setBadgeCount("tabelasCstCount", csts.length);
    cstBody.replaceChildren();

    if (!csts.length) {
      const tr = document.createElement("tr");
      const td = createCell("Nenhuma classificação encontrada para o filtro informado.", "text-muted small text-center py-3");
      td.colSpan = 4;
      tr.appendChild(td);
      cstBody.appendChild(tr);
      return;
    }

    csts.forEach((item) => {
      const tr = document.createElement("tr");
      tr.append(
        createCell(item.cst, "fw-semibold"),
        createCell(item.c_class_trib, "text-nowrap"),
        createCell(item.descricao, "small"),
        createCell(
          `${formatPctLabel(item.aliquota_reducao_ibs)} / ${formatPctLabel(item.aliquota_reducao_cbs)}`,
          "text-end small text-nowrap"
        )
      );
      cstBody.appendChild(tr);
    });
  }

  async function carregarTabelas(dataIso) {
    const query = `?data_fato_gerador=${encodeURIComponent(dataIso)}`;
    const cstCode = document.getElementById("cstCodeFilter")?.value || "";
    const cstQuery = document.getElementById("cstQueryFilter")?.value || "";

    const [, ativRes, ufsRes, govRes] = await Promise.all([
      carregarCsts(dataIso, cstCode, cstQuery),
      fetch(`${API_BASE}/atividades-simples${query}`),
      fetch(`${API_BASE}/ufs${query}`),
      fetch(`${API_BASE}/compra-gov-simples${query}`),
    ]);

    const ativBody = document.getElementById("tabelasAtivBody");
    if (ativBody && ativRes.ok) {
      const atividades = await ativRes.json();
      setBadgeCount("tabelasAtivCount", atividades.length);
      ativBody.replaceChildren();
      atividades.forEach((item) => {
        const tr = document.createElement("tr");
        tr.append(
          createCell(item.codigo, "fw-semibold"),
          createCell(item.descricao, "small"),
          createCell(item.anexo_sem_fator_r || "Sem anexo", "text-nowrap"),
          createCell(item.anexo_com_fator_r || "-", "text-nowrap")
        );
        ativBody.appendChild(tr);
      });
    }

    const ufsBody = document.getElementById("tabelasUfsBody");
    if (ufsBody && ufsRes.ok) {
      const ufs = await ufsRes.json();
      setBadgeCount("tabelasUfsCount", ufs.length);
      ufsBody.replaceChildren();
      ufs.forEach((item) => {
        const tr = document.createElement("tr");
        tr.append(
          createCell(item.uf, "fw-semibold"),
          createCell(item.nome, "small"),
          createCell(formatPctLabel(item.aliquota_ibs_uf), "text-end small text-nowrap"),
          createCell(formatPctLabel(item.aliquota_cbs), "text-end small text-nowrap")
        );
        ufsBody.appendChild(tr);
      });
    }

    const govBanner = document.getElementById("tabelasCompraGovBanner");
    if (govBanner) {
      if (govRes.ok) {
        const gov = await govRes.json();
        govBanner.className = "alert alert-info border-0 shadow-sm mb-0 py-2 small";
        govBanner.textContent = `Fator de transição Compra Governamental (Simples) vigente em ${dataIso}: ${gov.fator} (de ${gov.inicio_vigencia} até ${gov.fim_vigencia || "indeterminado"}).`;
      } else {
        govBanner.className = "alert alert-warning border-0 shadow-sm mb-0 py-2 small";
        govBanner.textContent = `Nenhum fator de transição Compra Governamental vigente para ${dataIso}.`;
      }
    }
  }

  async function buscarLocalidades(uf, nome) {
    const params = new URLSearchParams({ limit: "25" });
    if (uf && uf.trim().length === 2) params.set("uf", uf.trim().toUpperCase());
    if (nome && nome.trim().length >= 2) params.set("nome", nome.trim());

    const res = await fetch(`${API_BASE}/localidades?${params.toString()}`);
    const body = document.getElementById("tabelasLocalidadesBody");
    if (!body || !res.ok) return;

    const itens = await res.json();
    body.replaceChildren();
    itens.forEach((loc) => {
      const tr = document.createElement("tr");
      tr.append(
        createCell(String(loc.codigo_ibge), "fw-semibold"),
        createCell(loc.nome),
        createCell(loc.uf_sigla),
        createCell(String(loc.uf_codigo), "text-muted")
      );
      body.appendChild(tr);
    });
  }

  document.addEventListener("partial:loaded", (event) => {
    if (event.detail.route !== "tabelas") return;

    const form = document.getElementById("tabelasFilterForm");
    const dateInput = document.getElementById("tabelasDataVigencia");
    if (form && dateInput) {
      form.addEventListener("submit", (e) => {
        e.preventDefault();
        carregarTabelas(dateInput.value);
      });
      carregarTabelas(dateInput.value);
    }

    const cstForm = document.getElementById("cstSearchForm");
    const cstCode = document.getElementById("cstCodeFilter");
    const cstQuery = document.getElementById("cstQueryFilter");
    if (cstForm && cstCode && cstQuery && dateInput) {
      cstForm.addEventListener("submit", (e) => {
        e.preventDefault();
        carregarCsts(dateInput.value, cstCode.value, cstQuery.value);
      });
    }

    const locForm = document.getElementById("localidadesSearchForm");
    const locUf = document.getElementById("locUfInput");
    const locNome = document.getElementById("locNomeInput");
    if (locForm && locUf && locNome) {
      locForm.addEventListener("submit", (e) => {
        e.preventDefault();
        buscarLocalidades(locUf.value, locNome.value);
      });
      buscarLocalidades("", "");
    }
  });
})(window, document);
