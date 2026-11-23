/**
 * ApiExemplosModule - Gerador de snippets (cURL, Python, JS/Node, PHP) e teste ao vivo da API.
 */
(function (window, document) {
  "use strict";

  function getTodayIso() {
    return window.BrNumber ? window.BrNumber.getTodayIso() : new Date().toISOString().slice(0, 10);
  }

  function buildEndpoints() {
    const today = getTodayIso();
    return {
      comparador: {
        method: "POST",
        path: "/api/v1/comparador/simular",
        payload: {
          receita_bruta_12m: "720000.00",
          valor_operacao: "50000.00",
          anexo: "I",
          data_fato_gerador: today,
          uf: "RS",
          c_class_trib: "000001",
          creditos_anteriores: "4500.00",
          percentual_vendas_b2b: "100.00",
        },
      },
      "presumido-real": {
        method: "POST",
        path: "/api/v1/comparador/presumido-vs-real",
        payload: {
          receita_bruta_mensal: "600000.00",
          despesas_dedutiveis_mensais: "552000.00",
          atividade: "COMERCIO_INDUSTRIA",
          data_fato_gerador: today,
          uf: "RS",
          c_class_trib: "000001",
          creditos_ibs_cbs: "75000.00",
        },
      },
      "simples-das": {
        method: "POST",
        path: "/api/v1/simples/calcular",
        payload: {
          receita_bruta_12m: "360000.00",
          valor_operacao: "15000.00",
          anexo: "III",
          recolher_ibs_cbs_por_fora: false,
        },
      },
      "simples-item": {
        method: "POST",
        path: "/api/v1/simples/calcular-item",
        payload: {
          regime: "CRT_1",
          data_fato_gerador: today,
          tp_rbsn: 1,
          c_ativ_sn_valido: true,
          base_calculo: "1000.00",
          p_ibs_sn: "1.50",
          p_cbs_sn: "0.90",
        },
      },
      "regime-operacao": {
        method: "POST",
        path: "/api/v1/regime-regular/calcular-operacao",
        payload: {
          data_fato_gerador: today,
          uf: "RS",
          itens: [
            {
              codigo_item: "PROD-01",
              valor_base: "1000.00",
              c_class_trib: "000001",
              aliquota_ibs_mun: "0.00",
            },
            {
              codigo_item: "SERV-EDUC",
              valor_base: "1000.00",
              c_class_trib: "200028",
              aliquota_ibs_mun: "0.00",
              percentual_diferimento: "50.00",
            },
          ],
        },
      },
      "danfse-preview": {
        method: "POST",
        path: "/api/v1/danfse/preview",
        payload: {
          numero_nfse: "2026000142",
          prestador_cnpj: "11222333000181",
          tomador_documento: "98765432000199",
          discriminacao_servico: "Consultoria em adequação fiscal RTC (IBS/CBS)",
          valor_servicos: "5000.00",
          valor_ibs: "500.00",
          valor_cbs: "440.00",
          situacao_stc: 0,
        },
      },
      "danfse-pdf": {
        method: "POST",
        path: "/api/v1/danfse/pdf",
        binaryPdf: true,
        payload: {
          numero_nfse: "2026000142",
          prestador_cnpj: "11222333000181",
          tomador_documento: "98765432000199",
          discriminacao_servico: "Consultoria em adequação fiscal RTC (IBS/CBS)",
          valor_servicos: "5000.00",
          valor_ibs: "500.00",
          valor_cbs: "440.00",
          situacao_stc: 0,
        },
      },
      "tabelas-ibge": {
        method: "GET",
        path: "/api/v1/tabelas/localidades?uf=RS&nome=Porto&limit=5",
        payload: null,
      },
    };
  }

  function buildCurl(baseUrl, ep) {
    const url = `${baseUrl}${ep.path}`;
    if (ep.method === "GET") {
      return `curl -X GET "${url}" \\\n  -H "Accept: application/json"`;
    }
    const body = JSON.stringify(ep.payload, null, 2);
    const outFlag = ep.binaryPdf ? " \\\n  --output DANFSE_2026000142.pdf" : "";
    return `curl -X POST "${url}" \\\n  -H "Content-Type: application/json" \\\n  -d '${body}'${outFlag}`;
  }

  function buildPython(baseUrl, ep) {
    const url = `${baseUrl}${ep.path}`;
    if (ep.method === "GET") {
      return [
        "import requests",
        "",
        `url = "${url}"`,
        "response = requests.get(url, timeout=10)",
        "response.raise_for_status()",
        "print(response.json())",
      ].join("\n");
    }
    const pyPayload = JSON.stringify(ep.payload, null, 4)
      .replace(/\btrue\b/g, "True")
      .replace(/\bfalse\b/g, "False")
      .replace(/\bnull\b/g, "None");
    const outputLines = ep.binaryPdf
      ? [
          'with open("DANFSE_2026000142.pdf", "wb") as f:',
          "    f.write(response.content)",
          'print("PDF salvo com sucesso:", len(response.content), "bytes")',
        ]
      : ["print(response.json())"];
    return [
      "import requests",
      "",
      `url = "${url}"`,
      `payload = ${pyPayload}`,
      "",
      "response = requests.post(url, json=payload, timeout=10)",
      "response.raise_for_status()",
      ...outputLines,
    ].join("\n");
  }

  function buildJavaScript(baseUrl, ep) {
    const url = `${baseUrl}${ep.path}`;
    if (ep.method === "GET") {
      return [
        `const response = await fetch("${url}");`,
        "if (!response.ok) throw new Error(`HTTP ${response.status}`);",
        "const data = await response.json();",
        "console.log(data);",
      ].join("\n");
    }
    const jsPayload = JSON.stringify(ep.payload, null, 2);
    const parseLines = ep.binaryPdf
      ? [
          "const pdfBlob = await response.blob();",
          'console.log("PDF recebido:", pdfBlob.size, "bytes");',
        ]
      : ["const data = await response.json();", "console.log(data);"];
    return [
      `const payload = ${jsPayload};`,
      "",
      `const response = await fetch("${url}", {`,
      '  method: "POST",',
      '  headers: { "Content-Type": "application/json" },',
      "  body: JSON.stringify(payload),",
      "});",
      "",
      "if (!response.ok) throw new Error(`HTTP ${response.status}`);",
      ...parseLines,
    ].join("\n");
  }

  function buildPhp(baseUrl, ep) {
    const url = `${baseUrl}${ep.path}`;
    if (ep.method === "GET") {
      return [
        "<?php",
        `$ch = curl_init("${url}");`,
        "curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);",
        '$response = curl_exec($ch);',
        "curl_close($ch);",
        "print_r(json_decode($response, true));",
      ].join("\n");
    }
    const jsonEscaped = JSON.stringify(ep.payload, null, 2);
    const outLine = ep.binaryPdf
      ? 'file_put_contents("DANFSE_2026000142.pdf", $response);'
      : "print_r(json_decode($response, true));";
    return [
      "<?php",
      "$payload = <<<'JSON'",
      jsonEscaped,
      "JSON;",
      "",
      `$ch = curl_init("${url}");`,
      "curl_setopt_array($ch, [",
      "    CURLOPT_RETURNTRANSFER => true,",
      "    CURLOPT_POST => true,",
      '    CURLOPT_HTTPHEADER => ["Content-Type: application/json"],',
      "    CURLOPT_POSTFIELDS => $payload,",
      "]);",
      "",
      "$response = curl_exec($ch);",
      "curl_close($ch);",
      outLine,
    ].join("\n");
  }

  function generateSnippet(lang, baseUrl, endpointKey, endpoints) {
    const ep = endpoints[endpointKey] || endpoints.comparador;
    const normalizedBase = (baseUrl || window.location.origin).replace(/\/+$/, "");
    if (lang === "python") return buildPython(normalizedBase, ep);
    if (lang === "javascript") return buildJavaScript(normalizedBase, ep);
    if (lang === "php") return buildPhp(normalizedBase, ep);
    return buildCurl(normalizedBase, ep);
  }

  document.addEventListener("partial:loaded", (event) => {
    if (event.detail.route !== "api-exemplos") return;

    const endpointSelect = document.getElementById("apiEndpointSelect");
    const baseUrlInput = document.getElementById("apiBaseUrlInput");
    const snippetCode = document.getElementById("apiSnippetCode");
    const copyBtn = document.getElementById("apiCopySnippetBtn");
    const testBtn = document.getElementById("apiTestLiveBtn");
    const liveResponse = document.getElementById("apiLiveResponse");
    const liveMeta = document.getElementById("apiLiveMeta");
    const langTabs = document.querySelectorAll("#apiLangTabs [data-lang]");

    if (!endpointSelect || !baseUrlInput || !snippetCode) return;

    const endpoints = buildEndpoints();
    let currentLang = "curl";
    baseUrlInput.value = window.location.origin;

    function refreshSnippet() {
      snippetCode.textContent = generateSnippet(
        currentLang,
        baseUrlInput.value,
        endpointSelect.value,
        endpoints
      );
    }

    langTabs.forEach((tab) => {
      tab.addEventListener("click", () => {
        langTabs.forEach((t) => t.classList.remove("active"));
        tab.classList.add("active");
        currentLang = tab.dataset.lang;
        refreshSnippet();
      });
    });

    endpointSelect.addEventListener("change", refreshSnippet);
    baseUrlInput.addEventListener("input", refreshSnippet);

    copyBtn?.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(snippetCode.textContent || "");
        const prev = copyBtn.innerHTML;
        copyBtn.innerHTML = '<i class="bi bi-check2 me-1"></i>Copiado!';
        copyBtn.classList.replace("btn-outline-dark", "btn-success");
        setTimeout(() => {
          copyBtn.innerHTML = prev;
          copyBtn.classList.replace("btn-success", "btn-outline-dark");
        }, 1800);
      } catch {
        // Fallback silencioso se clipboard API não estiver disponível
      }
    });

    testBtn?.addEventListener("click", async () => {
      const ep = endpoints[endpointSelect.value] || endpoints.comparador;
      const t0 = performance.now();
      liveMeta.className = "badge text-bg-secondary";
      liveMeta.textContent = "Executando...";

      try {
        const options =
          ep.method === "GET"
            ? { method: "GET" }
            : {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(ep.payload),
              };
        const res = await fetch(ep.path, options);
        const elapsed = Math.round(performance.now() - t0);
        const contentType = res.headers.get("Content-Type") || "";

        liveMeta.className = res.ok ? "badge text-bg-success" : "badge text-bg-danger";
        liveMeta.textContent = `HTTP ${res.status} • ${elapsed} ms`;

        if (res.ok && contentType.includes("application/pdf")) {
          const blob = await res.blob();
          const url = URL.createObjectURL(blob);
          const link = document.createElement("a");
          link.href = url;
          link.download = "DANFSE_2026000142.pdf";
          document.body.appendChild(link);
          link.click();
          link.remove();
          setTimeout(() => URL.revokeObjectURL(url), 1500);
          liveResponse.textContent = [
            `Content-Type: ${contentType}`,
            `Content-Disposition: ${res.headers.get("Content-Disposition") || "-"}`,
            `Tamanho do PDF binário: ${blob.size} bytes`,
            "Download automático iniciado: DANFSE_2026000142.pdf",
          ].join("\n");
          return;
        }

        const data = await res.json();
        liveResponse.textContent = JSON.stringify(data, null, 2);
      } catch (err) {
        liveMeta.className = "badge text-bg-danger";
        liveMeta.textContent = "Erro de conexão";
        liveResponse.textContent = err.message;
      }
    });

    refreshSnippet();
  });
})(window, document);
