/**
 * ComparadorCatalog - Carrega o catálogo oficial CST/cClassTrib (LC 214/2025)
 * nos selects das duas abas do Comparador preservando o valor selecionado.
 */
(function (window, document) {
  "use strict";

  const FEATURED_CODES = ["000001", "200028", "200003", "410001"];

  function getTodayIso() {
    return window.BrNumber ? window.BrNumber.getTodayIso() : new Date().toISOString().slice(0, 10);
  }

  function truncate(text, maxLen = 62) {
    const clean = String(text ?? "").trim();
    return clean.length > maxLen ? `${clean.slice(0, maxLen - 1)}…` : clean;
  }

  function formatOptionLabel(item) {
    const redIbs = Number(item.aliquota_reducao_ibs) || 0;
    const redTag = redIbs > 0 ? ` [Red. ${redIbs.toFixed(0)}%]` : "";
    return `${item.c_class_trib} — ${truncate(item.descricao)}${redTag}`;
  }

  function formatFullLabel(item) {
    const redIbs = Number(item.aliquota_reducao_ibs) || 0;
    const redCbs = Number(item.aliquota_reducao_cbs) || 0;
    const redTag =
      redIbs > 0 || redCbs > 0
        ? ` [Red. IBS ${redIbs.toFixed(0)}% / CBS ${redCbs.toFixed(0)}%]`
        : " [Tributação integral]";
    return `CST ${item.cst} | ${item.c_class_trib} — ${String(item.descricao ?? "").trim()}${redTag}`;
  }

  function buildOption(item) {
    const opt = document.createElement("option");
    const full = formatFullLabel(item);
    opt.value = item.c_class_trib;
    opt.textContent = formatOptionLabel(item);
    opt.dataset.fullText = full;
    opt.title = full;
    return opt;
  }

  function populateSelect(selectEl, items) {
    if (!selectEl || !items.length) return;
    const currentValue = selectEl.value || "000001";
    const byCode = new Map(items.map((item) => [item.c_class_trib, item]));

    selectEl.replaceChildren();

    const featuredGroup = document.createElement("optgroup");
    featuredGroup.label = "Principais Classificações (Atalhos)";
    FEATURED_CODES.forEach((code) => {
      const item = byCode.get(code);
      if (item) featuredGroup.appendChild(buildOption(item));
    });
    if (featuredGroup.children.length) {
      selectEl.appendChild(featuredGroup);
    }

    const groupedByCst = new Map();
    items.forEach((item) => {
      if (FEATURED_CODES.includes(item.c_class_trib)) return;
      if (!groupedByCst.has(item.cst)) groupedByCst.set(item.cst, []);
      groupedByCst.get(item.cst).push(item);
    });

    Array.from(groupedByCst.keys())
      .sort()
      .forEach((cst) => {
        const group = document.createElement("optgroup");
        group.label = `CST ${cst} (LC 214/2025)`;
        groupedByCst.get(cst).forEach((item) => group.appendChild(buildOption(item)));
        selectEl.appendChild(group);
      });

    if (byCode.has(currentValue)) {
      selectEl.value = currentValue;
    }
  }

  async function hydrateComparadorCClassSelects() {
    const compSelect = document.getElementById("compCClass");
    const prSelect = document.getElementById("prCClass");
    if (!compSelect && !prSelect) return;

    try {
      const today = encodeURIComponent(getTodayIso());
      const res = await fetch(`/api/v1/tabelas/cst?data_fato_gerador=${today}`);
      if (!res.ok) return;
      const items = await res.json();
      if (!Array.isArray(items) || !items.length) return;
      populateSelect(compSelect, items);
      populateSelect(prSelect, items);
    } catch {
      // Mantém opções fallback do HTML em caso de indisponibilidade
    }
  }

  document.addEventListener("partial:loaded", (event) => {
    if (event.detail.route !== "comparador") return;
    hydrateComparadorCClassSelects();
  });
})(window, document);
