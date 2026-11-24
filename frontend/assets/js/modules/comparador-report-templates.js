/**
 * ComparadorReportTemplates - Templates HTML puros (A4, 1 página)
 * para as duas abas do Comparador Tributário (incluindo ICMS/ISS transição EC 132).
 */
(function (window) {
  "use strict";

  const ANEXO_LABELS = {
    I: "Anexo I (Comércio)",
    II: "Anexo II (Indústria)",
    III: "Anexo III (Serviços)",
    IV: "Anexo IV (Serviços)",
    V: "Anexo V (Serviços)",
  };

  const ATIVIDADE_LABELS = {
    COMERCIO_INDUSTRIA: "Comércio / Indústria",
    SERVICOS_GERAIS: "Serviços Gerais",
    SERVICOS_HOSPITALARES: "Serviços Hospitalares",
    TRANSPORTE_CARGA: "Transporte de Cargas",
    TRANSPORTE_PASSAGEIROS: "Transporte de Passageiros",
  };

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function formatBRL(value) {
    const num = Number(value);
    return Number.isNaN(num)
      ? "R$ 0,00"
      : num.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
  }

  function formatPct(value) {
    const num = Number(value);
    if (Number.isNaN(num)) return "0,00%";
    return `${num.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%`;
  }

  function formatDateBR(isoDate) {
    if (!isoDate || typeof isoDate !== "string") return "-";
    const parts = isoDate.split("-");
    return parts.length === 3 ? `${parts[2]}/${parts[1]}/${parts[0]}` : escapeHtml(isoDate);
  }

  function buildHeaderHtml(title, subtitle, legalRef, clientName) {
    const now = new Date();
    const emittedAt = `${now.toLocaleDateString("pt-BR")} às ${now.toLocaleTimeString("pt-BR", {
      hour: "2-digit",
      minute: "2-digit",
    })}`;
    const clientBlock = clientName
      ? `<div class="rp-client-line">Cliente / Empresa: ${escapeHtml(clientName)}</div>`
      : "";

    return `
      <header class="rp-header">
        <div>
          <div class="rp-kicker">Relatório Executivo • Reforma Tributária (RTC)</div>
          <h1 class="rp-title">${escapeHtml(title)}</h1>
          <p class="rp-subtitle">${escapeHtml(subtitle)}</p>
          ${clientBlock}
        </div>
        <div class="rp-meta">
          <strong>Emitido em ${escapeHtml(emittedAt)}</strong>
          <div>Base: ${escapeHtml(legalRef)}</div>
          <div>Calculadora RTC RFB Free Suite PY</div>
        </div>
      </header>
    `;
  }

  function buildParamsGridHtml(items) {
    const cells = items
      .map(
        ([label, value]) => `
          <div class="rp-param-item">
            <span class="rp-param-label">${escapeHtml(label)}</span>
            <span class="rp-param-value">${escapeHtml(value)}</span>
          </div>`
      )
      .join("");
    return `<h2 class="rp-section-title">Parâmetros da Simulação</h2><div class="rp-params">${cells}</div>`;
  }

  function buildFooterHtml(legalNote) {
    return `
      <footer class="rp-footer">
        <div class="rp-footer-note">
          <strong>Nota técnica:</strong> ${escapeHtml(legalNote)} Os valores têm caráter simulatório e
          apoiam o planejamento tributário, devendo ser validados conforme enquadramento fiscal vigente.
        </div>
        <div class="rp-footer-brand">Calculadora RTC RFB Free Suite PY<br />Documento Executivo — 1 página</div>
      </footer>
    `;
  }

  function formatTransicaoParam(trans) {
    if (!trans) return "";
    const tipo = (trans.tipo_tributo_local || "ICMS/ISS").toUpperCase();
    return `${trans.ano} • ${tipo} ${formatPct(trans.aliquota_local_efetiva)} (${formatPct(trans.percentual_icms_iss_vigente)} vigente)`;
  }

  function buildSimplesRegularHtml(payload, data, clientName) {
    const maxAliq = Math.max(...data.cenarios.map((c) => Number(c.aliquota_efetiva_percentual) || 0), 1);
    const trans = data.transicao_tributo_local;
    const localLabel = (trans?.tipo_tributo_local || "ICMS/ISS").toUpperCase();
    const extras = [];
    if (Number(data.aliquota_ibs_mun_aplicada) > 0) extras.push(`Mun ${formatPct(data.aliquota_ibs_mun_aplicada)}`);
    if (Number(payload.aliquota_is) > 0) extras.push(`IS ${formatPct(payload.aliquota_is)}`);
    if (trans) extras.push(formatTransicaoParam(trans));
    const aliqResumo = `IBS ${formatPct(data.aliquota_ibs_uf_aplicada)} • CBS ${formatPct(data.aliquota_cbs_aplicada)}${extras.length ? ` • ${extras.join(" • ")}` : ""}`;
    const fr = data.fator_r;
    const anexoTexto = fr && fr.aplicado
      ? `${ANEXO_LABELS[data.anexo] || `Anexo ${data.anexo}`} • Fator R ${formatPct(fr.percentual_fator_r)} (Folha ${formatBRL(fr.folha_salarios_12m)})`
      : ANEXO_LABELS[data.anexo] || `Anexo ${data.anexo}`;

    const paramsHtml = buildParamsGridHtml([
      ["RBT12 (12 meses)", formatBRL(data.receita_bruta_12m)],
      ["Valor da Operação", formatBRL(data.valor_operacao)],
      ["Anexo LC 123", anexoTexto],
      ["Fato Gerador / UF", `${formatDateBR(payload.data_fato_gerador)} • ${data.uf || "-"}`],
      ["cClassTrib / Redução", `${data.c_class_trib || "-"} (Red. ${formatPct(data.reducao_ibs_percentual)})`],
      ["Alíquotas Aplicadas", aliqResumo],
      ["Créditos de Insumos", formatBRL(payload.creditos_anteriores)],
      ["Vendas B2B / PJ", formatPct(data.percentual_vendas_b2b)],
    ]);

    const cardsHtml = data.cenarios
      .map((c) => {
        const isMelhorCarga = c.id === data.melhor_cenario_carga_propria;
        const isMelhorB2b =
          c.id === data.melhor_cenario_competitividade_b2b && Number(data.percentual_vendas_b2b) > 0;
        const barWidth = Math.min(Math.round((Number(c.aliquota_efetiva_percentual) / maxAliq) * 100), 100);
        const barClass =
          c.id === "simples_das" ? "rp-bar-green" : c.id === "simples_hibrido" ? "rp-bar-cyan" : "";
        const badges = [
          isMelhorCarga ? '<span class="rp-badge rp-badge-success">Menor Carga Própria</span>' : "",
          isMelhorB2b ? '<span class="rp-badge rp-badge-primary">Melhor Crédito B2B</span>' : "",
        ].filter(Boolean).join("");

        return `
          <article class="rp-card ${isMelhorCarga ? "rp-card-winner" : ""}">
            <div class="rp-badges">${badges || '<span class="rp-badge">Cenário Simulado</span>'}</div>
            <h3 class="rp-card-name">${escapeHtml(c.nome)}</h3>
            <p class="rp-card-sub">${escapeHtml(c.subtitulo)}</p>
            <div class="rp-kpi">
              <div class="rp-kpi-label">Carga Tributária Própria</div>
              <div class="rp-kpi-value">${formatBRL(c.carga_tributaria_total)}</div>
              <div class="rp-kpi-row"><span>Alíquota Efetiva</span><strong>${formatPct(c.aliquota_efetiva_percentual)}</strong></div>
              <div class="rp-bar-track"><div class="rp-bar-fill ${barClass}" style="width: ${barWidth}%;"></div></div>
            </div>
            <ul class="rp-metrics">
              <li><span>DAS (LC 123)</span><strong>${formatBRL(c.valor_das)}</strong></li>
              <li><span>IBS + CBS Líquido</span><strong>${formatBRL(c.valor_ibs_cbs_liquido)}</strong></li>
              <li><span>${localLabel} (Transição)</span><strong>${formatBRL(c.valor_tributo_local || 0)}</strong></li>
              <li><span>Créditos Aproveitados</span><strong>${formatBRL(c.creditos_aproveitados)}</strong></li>
              <li><span>Crédito p/ Cliente B2B</span><strong>${formatBRL(c.credito_gerado_cliente_b2b)}</strong></li>
              <li><span>Custo Efetivo B2B</span><strong>${formatBRL(c.custo_efetivo_cliente_b2b)}</strong></li>
            </ul>
            <p class="rp-card-note">${escapeHtml(c.observacoes)}</p>
          </article>`;
      })
      .join("");

    const rowsHtml = data.cenarios
      .map((c) => `
        <tr class="${c.id === data.melhor_cenario_carga_propria ? "rp-row-winner" : ""}">
          <td>${escapeHtml(c.nome)}</td>
          <td class="rp-num">${formatBRL(c.valor_das)}</td>
          <td class="rp-num">${formatBRL(c.valor_ibs_cbs_bruto)}</td>
          <td class="rp-num">${formatBRL(c.valor_tributo_local || 0)}</td>
          <td class="rp-num">${formatBRL(c.creditos_aproveitados)}</td>
          <td class="rp-num">${formatBRL(c.carga_tributaria_total)} (${formatPct(c.aliquota_efetiva_percentual)})</td>
          <td class="rp-num">${formatBRL(c.credito_gerado_cliente_b2b)}</td>
          <td class="rp-num">${formatBRL(c.custo_efetivo_cliente_b2b)}</td>
        </tr>`)
      .join("");

    return `
      ${buildHeaderHtml(
        "Simples (DAS) vs. Simples Híbrido vs. Regime Regular",
        "Análise comparativa para ME/EPP (até R$ 4,8 mi/ano) considerando carga própria, transição ICMS/ISS e competitividade B2B.",
        "LC 214/2025 • EC 132 • LC 123/2006",
        clientName
      )}
      ${paramsHtml}
      <section class="rp-diagnosis">
        <div class="rp-diagnosis-head">
          <span class="rp-diagnosis-title">Diagnóstico Executivo &amp; Recomendação</span>
          <span class="rp-diagnosis-pill">Diferença máxima: ${formatBRL(data.economia_maxima_reais)} na operação</span>
        </div>
        <p class="rp-diagnosis-text">${escapeHtml(data.resumo_executivo)}</p>
      </section>
      <h2 class="rp-section-title">Comparativo Detalhado por Cenário</h2>
      <div class="rp-cards rp-cols-3">${cardsHtml}</div>
      <div class="rp-table-wrap">
        <h2 class="rp-section-title">Quadro Comparativo Sintético</h2>
        <table class="rp-table">
          <thead>
            <tr>
              <th>Cenário</th><th class="rp-num">DAS</th><th class="rp-num">IBS/CBS Bruto</th>
              <th class="rp-num">${localLabel}</th><th class="rp-num">Créditos Insumos</th><th class="rp-num">Carga Própria</th>
              <th class="rp-num">Crédito p/ B2B</th><th class="rp-num">Custo Efetivo B2B</th>
            </tr>
          </thead>
          <tbody>${rowsHtml}</tbody>
        </table>
      </div>
      ${buildFooterHtml("Cálculos baseados nas faixas progressivas da LC 123/2006 (incluindo Fator R quando ativo) e escada de transição EC 132/LC 214/2025.")}
    `;
  }

  function buildPresumidoRealHtml(payload, data, clientName) {
    const maxAliq = Math.max(...data.cenarios.map((c) => Number(c.aliquota_efetiva_percentual) || 0), 1);
    const trans = data.transicao_tributo_local;
    const localLabel = (trans?.tipo_tributo_local || "ICMS/ISS").toUpperCase();
    const ativLabel = ATIVIDADE_LABELS[data.atividade] || data.atividade;
    const presuncaoTxt = `${formatPct(data.presuncao_irpj_percentual)} IR | ${formatPct(data.presuncao_csll_percentual)} CSLL`;
    const aliqTxt = `${data.c_class_trib || "-"} • IBS ${formatPct(data.aliquota_ibs_uf_aplicada)} / CBS ${formatPct(data.aliquota_cbs_aplicada)}${trans ? ` • ${formatTransicaoParam(trans)}` : ""}`;

    const paramsHtml = buildParamsGridHtml([
      ["Receita Bruta Mensal", formatBRL(data.receita_bruta_mensal)],
      ["Receita Anualizada Est.", formatBRL(data.receita_anualizada_estimada)],
      ["Despesas Dedutíveis", formatBRL(data.despesas_dedutiveis_mensais)],
      ["Lucro Contábil / Margem", `${formatBRL(data.lucro_contabil_mensal)} (${formatPct(data.margem_lucro_real_percentual)})`],
      ["Atividade / Presunção", `${ativLabel} (${presuncaoTxt})`],
      ["Fato Gerador / UF", `${formatDateBR(payload.data_fato_gerador)} • ${data.uf || "-"}`],
      ["cClassTrib / Alíquotas", aliqTxt],
      ["Créditos IBS/CBS Mensais", formatBRL(data.creditos_ibs_cbs_aproveitados)],
    ]);

    const cardsHtml = data.cenarios
      .map((c) => {
        const isMelhor = c.id === data.melhor_regime;
        const cardClass = !c.elegivel ? "rp-card-danger" : isMelhor ? "rp-card-winner" : "";
        const barWidth = Math.min(Math.round((Number(c.aliquota_efetiva_percentual) / maxAliq) * 100), 100);
        const barClass = c.id === "lucro_presumido" ? "rp-bar-cyan" : "";
        const badgeHtml = !c.elegivel
          ? '<span class="rp-badge rp-badge-danger">Inelegível (&gt; R$ 78 mi/ano)</span>'
          : isMelhor
            ? '<span class="rp-badge rp-badge-success">Regime Mais Econômico</span>'
            : '<span class="rp-badge">Cenário Comparado</span>';

        return `
          <article class="rp-card ${cardClass}">
            <div class="rp-badges">${badgeHtml}</div>
            <h3 class="rp-card-name">${escapeHtml(c.nome)}</h3>
            <p class="rp-card-sub">${escapeHtml(c.subtitulo)}</p>
            <div class="rp-kpi">
              <div class="rp-kpi-label">Carga Tributária Mensal Total (IRPJ + CSLL + IBS/CBS + ${localLabel})</div>
              <div class="rp-kpi-value">${formatBRL(c.carga_tributaria_total)}</div>
              <div class="rp-kpi-row"><span>Alíquota Efetiva Total</span><strong>${formatPct(c.aliquota_efetiva_percentual)}</strong></div>
              <div class="rp-bar-track"><div class="rp-bar-fill ${barClass}" style="width: ${barWidth}%;"></div></div>
            </div>
            <ul class="rp-metrics">
              <li><span>Base IRPJ / CSLL</span><strong>${formatBRL(c.base_calculo_irpj)} / ${formatBRL(c.base_calculo_csll)}</strong></li>
              <li><span>IRPJ (15%) + Adic. (10%)</span><strong>${formatBRL(c.irpj_basico)} + ${formatBRL(c.adicional_irpj)}</strong></li>
              <li><span>CSLL (9%)</span><strong>${formatBRL(c.csll)}</strong></li>
              <li><span>Subtotal Lucro (IRPJ + CSLL)</span><strong>${formatBRL(c.total_irpj_csll)}</strong></li>
              <li><span>IBS + CBS + IS Líquido</span><strong>${formatBRL(c.ibs_cbs_is_liquido)}</strong></li>
              <li><span>${localLabel} (Transição)</span><strong>${formatBRL(c.valor_tributo_local || 0)}</strong></li>
            </ul>
            <p class="rp-card-note">${escapeHtml(c.observacoes)}</p>
          </article>`;
      })
      .join("");

    const rowsHtml = data.cenarios
      .map((c) => {
        const rowClass = !c.elegivel ? "rp-row-danger" : c.id === data.melhor_regime ? "rp-row-winner" : "";
        const irpjTotal = Number(c.irpj_basico) + Number(c.adicional_irpj);
        return `
          <tr class="${rowClass}">
            <td>${escapeHtml(c.nome)}${c.elegivel ? "" : " (Inelegível)"}</td>
            <td class="rp-num">${formatBRL(c.base_calculo_irpj)} / ${formatBRL(c.base_calculo_csll)}</td>
            <td class="rp-num">${formatBRL(irpjTotal)}</td>
            <td class="rp-num">${formatBRL(c.csll)}</td>
            <td class="rp-num">${formatBRL(c.total_irpj_csll)}</td>
            <td class="rp-num">${formatBRL(c.ibs_cbs_is_liquido)}</td>
            <td class="rp-num">${formatBRL(c.valor_tributo_local || 0)}</td>
            <td class="rp-num">${formatBRL(c.carga_tributaria_total)} (${formatPct(c.aliquota_efetiva_percentual)})</td>
          </tr>`;
      })
      .join("");

    const diagClass = data.excede_limite_presumido ? "rp-diagnosis rp-diagnosis-warning" : "rp-diagnosis";
    const economiaPill = `Economia: ${formatBRL(data.economia_mensal_reais)}/mês • ${formatBRL(data.economia_anual_estimada_reais)}/ano`;

    return `
      ${buildHeaderHtml(
        "Lucro Presumido vs. Lucro Real (+ IBS/CBS + ICMS/ISS)",
        "Comparativo mensal de IRPJ (15% + Adicional 10%), CSLL (9%), IBS/CBS e tributo local na transição EC 132.",
        "LC 214/2025 • EC 132 • Lei 9.249/1995",
        clientName
      )}
      ${paramsHtml}
      <section class="${diagClass}">
        <div class="rp-diagnosis-head">
          <span class="rp-diagnosis-title">Diagnóstico Executivo &amp; Recomendação</span>
          <span class="rp-diagnosis-pill">${escapeHtml(economiaPill)}</span>
        </div>
        <p class="rp-diagnosis-text">${escapeHtml(data.resumo_executivo)}</p>
      </section>
      <h2 class="rp-section-title">Comparativo Detalhado por Regime</h2>
      <div class="rp-cards rp-cols-2">${cardsHtml}</div>
      <div class="rp-table-wrap">
        <h2 class="rp-section-title">Quadro Comparativo Sintético Mensal</h2>
        <table class="rp-table">
          <thead>
            <tr>
              <th>Regime</th><th class="rp-num">Base IRPJ / CSLL</th><th class="rp-num">IRPJ + Adic.</th>
              <th class="rp-num">CSLL (9%)</th><th class="rp-num">Subtotal Lucro</th>
              <th class="rp-num">IBS/CBS/IS Líq.</th><th class="rp-num">${localLabel}</th><th class="rp-num">Carga Total</th>
            </tr>
          </thead>
          <tbody>${rowsHtml}</tbody>
        </table>
      </div>
      ${buildFooterHtml("Apuração estimativa considerando Lei 9.249/1995 (presunção e adicional IRPJ > R$ 20 mil/mês, teto R$ 78 mi/ano) e transição EC 132/LC 214/2025.")}
    `;
  }

  window.ComparadorReportTemplates = {
    buildSimplesRegularHtml,
    buildPresumidoRealHtml,
  };
})(window);
