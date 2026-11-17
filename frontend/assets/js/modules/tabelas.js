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

  async function carregarTabelas(dataIso) {
    const query = `?data_fato_gerador=${encodeURIComponent(dataIso)}`;
    const [cstRes, ativRes, govRes] = await Promise.all([
      fetch(`${API_BASE}/cst${query}`),
      fetch(`${API_BASE}/atividades-simples${query}`),
      fetch(`${API_BASE}/compra-gov-simples${query}`),
    ]);

    const cstBody = document.getElementById("tabelasCstBody");
    if (cstBody && cstRes.ok) {
      const csts = await cstRes.json();
      cstBody.replaceChildren();
      csts.forEach((item) => {
        const tr = document.createElement("tr");
        tr.append(
          createCell(item.cst, "fw-semibold"),
          createCell(item.c_class_trib),
          createCell(item.descricao, "small"),
          createCell(`${item.aliquota_reducao_ibs}% / ${item.aliquota_reducao_cbs}%`, "text-end small")
        );
        cstBody.appendChild(tr);
      });
    }

    const ativBody = document.getElementById("tabelasAtivBody");
    if (ativBody && ativRes.ok) {
      const atividades = await ativRes.json();
      ativBody.replaceChildren();
      atividades.forEach((item) => {
        const tr = document.createElement("tr");
        tr.append(
          createCell(item.codigo, "fw-semibold"),
          createCell(item.descricao, "small"),
          createCell(item.anexo_sem_fator_r || "Sem anexo"),
          createCell(item.anexo_com_fator_r || "-")
        );
        ativBody.appendChild(tr);
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
  });
})(window, document);
