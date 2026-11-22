/**
 * BrNumber - Formatação e conversão de números/moedas no padrão PT-BR (1.234.567,89)
 * para strings decimais padrão ISO/API ("1234567.89") compatíveis com Decimal no Python,
 * além de helpers de data local atual (produção).
 */
(function (window, document) {
  "use strict";

  /**
   * Retorna a data local atual do usuário em formato ISO ("YYYY-MM-DD").
   */
  function getTodayIso() {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, "0");
    const day = String(now.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  }

  /**
   * Preenche inputs [data-default-today] com a data atual e [data-default-year] com o ano atual.
   */
  function applyDefaultTodayDates(root = document) {
    const today = getTodayIso();
    const currentYear = String(new Date().getFullYear());

    root.querySelectorAll("input[type='date'][data-default-today]").forEach((input) => {
      if (input.dataset.todayApplied === "true") return;
      input.dataset.todayApplied = "true";
      input.value = today;
    });

    root.querySelectorAll("input[data-default-year]").forEach((input) => {
      if (input.dataset.yearApplied === "true") return;
      input.dataset.yearApplied = "true";
      input.value = currentYear;
    });
  }

  /**
   * Converte entrada PT-BR ("720.000,00", "600.000", "50,5") ou ISO ("720000.00")
   * em string numérica limpa para envio à API Python ("720000.00").
   */
  function parseToApiDecimal(raw, fallback = "0.00") {
    if (raw === null || raw === undefined) return fallback;
    let cleaned = String(raw)
      .trim()
      .replace(/R\$/gi, "")
      .replace(/\s+/g, "");

    if (!cleaned) return fallback;

    const negative = cleaned.startsWith("-");
    cleaned = cleaned.replace(/^[+-]/, "");

    if (cleaned.includes(",")) {
      // Padrão PT-BR com vírgula decimal: remove pontos de milhar e troca vírgula por ponto
      const parts = cleaned.split(",");
      const intPart = parts[0].replace(/\./g, "");
      const decPart = parts.slice(1).join("").replace(/\./g, "");
      cleaned = decPart ? `${intPart}.${decPart}` : intPart;
    } else {
      const dotMatches = cleaned.match(/\./g);
      const dotCount = dotMatches ? dotMatches.length : 0;
      if (dotCount > 1) {
        // Múltiplos pontos (ex.: "1.200.000") são separadores de milhar
        cleaned = cleaned.replace(/\./g, "");
      } else if (dotCount === 1) {
        // Único ponto seguido de exatamente 3 dígitos (ex.: "600.000") -> milhar PT-BR
        const [, afterDot] = cleaned.split(".");
        if (afterDot && afterDot.length === 3) {
          cleaned = cleaned.replace(".", "");
        }
      }
    }

    const result = `${negative ? "-" : ""}${cleaned}`;
    if (!/^-?\d+(\.\d+)?$/.test(result)) {
      return fallback;
    }
    return result;
  }

  /**
   * Formata valor numérico/string API ("720000.00") para exibição PT-BR ("720.000,00").
   */
  function formatBrDecimal(value, decimals = 2) {
    const apiStr = parseToApiDecimal(value, "");
    if (!apiStr) return "";
    const num = Number(apiStr);
    if (Number.isNaN(num)) return "";
    return num.toLocaleString("pt-BR", {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    });
  }

  /**
   * Ativa formatação PT-BR automática em todos os inputs com atributo [data-br-money].
   */
  function attachMoneyInputs(root = document) {
    const inputs = root.querySelectorAll("input[data-br-money]");
    inputs.forEach((input) => {
      if (input.dataset.brBound === "true") return;
      input.dataset.brBound = "true";

      const decimals = Number(input.dataset.brDecimals ?? 2);
      if (input.value) {
        input.value = formatBrDecimal(input.value, decimals);
      }

      input.addEventListener("blur", () => {
        if (input.value.trim() !== "") {
          const formatted = formatBrDecimal(input.value, decimals);
          if (formatted) input.value = formatted;
        }
      });

      input.addEventListener("focus", () => {
        input.select();
      });
    });
  }

  // Registrado antes dos módulos para garantir data atual pronta no carregamento de cada partial
  document.addEventListener("partial:loaded", () => {
    applyDefaultTodayDates(document);
  });

  window.BrNumber = {
    getTodayIso,
    applyDefaultTodayDates,
    parseToApiDecimal,
    formatBrDecimal,
    attachMoneyInputs,
  };
})(window, document);
