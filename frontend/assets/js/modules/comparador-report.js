/**
 * ComparadorReport - Fachada/Orquestrador leve de impressão do Relatório Executivo
 * do Comparador Tributário (A4, 1 página) com suporte a Ctrl+P e zero regressão no DANFSE.
 */
(function (window, document) {
  "use strict";

  const lastResults = {
    simples_regular: null,
    presumido_real: null,
  };

  let originalTitle = "";
  let isPrintingReport = false;

  function getClientName() {
    const input = document.getElementById("comparadorClienteNome");
    return input ? input.value.trim() : "";
  }

  function ensurePrintSheet() {
    let sheet = document.getElementById("comparadorPrintSheet");
    if (!sheet) {
      sheet = document.createElement("section");
      sheet.id = "comparadorPrintSheet";
      sheet.className = "comparador-print-sheet";
      sheet.setAttribute("aria-hidden", "true");
      document.body.appendChild(sheet);
    }
    return sheet;
  }

  function detectActiveTabKey() {
    const panePr = document.getElementById("panePresumidoReal");
    if (panePr && panePr.classList.contains("active")) {
      return "presumido_real";
    }
    return "simples_regular";
  }

  function prepareSheet(tabKey) {
    const entry = lastResults[tabKey];
    const templates = window.ComparadorReportTemplates;
    if (!entry || !entry.data || !templates) return false;

    const clientName = getClientName();
    const sheet = ensurePrintSheet();
    sheet.innerHTML =
      tabKey === "presumido_real"
        ? templates.buildPresumidoRealHtml(entry.payload, entry.data, clientName)
        : templates.buildSimplesRegularHtml(entry.payload, entry.data, clientName);

    const today = new Date().toISOString().slice(0, 10);
    const slug =
      tabKey === "presumido_real"
        ? "Relatorio_Comparador_Presumido_vs_Real"
        : "Relatorio_Comparador_Simples_vs_Regular";

    originalTitle = document.title;
    document.title = `${slug}_${today}`;
    document.body.classList.add("printing-comparador-report");
    isPrintingReport = true;
    return true;
  }

  function cleanupAfterPrint() {
    if (!isPrintingReport) return;
    isPrintingReport = false;
    document.body.classList.remove("printing-comparador-report");
    if (originalTitle) {
      document.title = originalTitle;
      originalTitle = "";
    }
    const sheet = document.getElementById("comparadorPrintSheet");
    if (sheet) sheet.innerHTML = "";
  }

  function setLastResult(tabKey, payload, data) {
    if (!(tabKey in lastResults)) return;
    lastResults[tabKey] = payload && data ? { payload, data } : null;
  }

  function printReport(tabKey) {
    const targetKey = tabKey || detectActiveTabKey();
    if (!prepareSheet(targetKey)) {
      window.alert("Execute uma simulação válida antes de imprimir ou salvar o relatório PDF.");
      return;
    }
    window.print();
  }

  window.addEventListener("beforeprint", () => {
    if (isPrintingReport) return;
    if (!document.getElementById("comparadorTabs")) return;
    const activeKey = detectActiveTabKey();
    if (lastResults[activeKey]) {
      prepareSheet(activeKey);
    }
  });

  window.addEventListener("afterprint", cleanupAfterPrint);

  window.ComparadorReport = {
    setLastResult,
    printReport,
  };
})(window, document);
