/**
 * OverflowTooltip - Exibe um balão flutuante com a frase completa sempre que
 * o texto de um elemento (célula, rótulo, input ou select) não couber na linha.
 */
(function (window, document) {
  "use strict";

  const TEXT_SELECTOR =
    "td, th, .text-ellipsis-cell, .text-truncate, .form-select, .form-label, .form-text, .nav-link, .card-header span, .badge, small, p";
  const MEASURE_CANVAS = document.createElement("canvas");
  const MEASURE_CTX = MEASURE_CANVAS.getContext("2d");

  let tooltipEl = null;
  let activeTarget = null;

  function ensureTooltipEl() {
    if (tooltipEl) return tooltipEl;
    tooltipEl = document.createElement("div");
    tooltipEl.className = "rtc-floating-tooltip";
    tooltipEl.setAttribute("role", "tooltip");
    tooltipEl.setAttribute("aria-hidden", "true");
    document.body.appendChild(tooltipEl);
    return tooltipEl;
  }

  function measureTextWidth(text, el) {
    if (!MEASURE_CTX) return text.length * 7;
    const style = window.getComputedStyle(el);
    MEASURE_CTX.font = `${style.fontWeight} ${style.fontSize} ${style.fontFamily}`;
    return MEASURE_CTX.measureText(text).width;
  }

  function getOverflowFullText(el) {
    if (!el || el.nodeType !== 1) return null;
    if (el.closest(".rtc-floating-tooltip")) return null;

    if (el.tagName === "SELECT") {
      const opt = el.options[el.selectedIndex];
      if (!opt) return null;
      const visibleText = (opt.textContent || "").trim();
      const fullText = (opt.dataset.fullText || visibleText).trim();
      if (!fullText) return null;

      const style = window.getComputedStyle(el);
      const padLeft = parseFloat(style.paddingLeft) || 0;
      const padRight = parseFloat(style.paddingRight) || 28;
      const available = el.clientWidth - padLeft - padRight - 4;
      const isTruncatedOption = Boolean(opt.dataset.fullText && opt.dataset.fullText !== visibleText);

      if (isTruncatedOption || measureTextWidth(fullText, el) > available) {
        return fullText;
      }
      return null;
    }

    const explicit = (el.dataset.tooltipFull || "").trim();
    const isOverflowing =
      el.scrollWidth > el.clientWidth + 1 || el.scrollHeight > el.clientHeight + 1;

    if (!isOverflowing) return null;
    const text = explicit || (el.textContent || "").replace(/\s+/g, " ").trim();
    return text.length > 0 ? text : null;
  }

  function positionTooltip(target) {
    const tip = ensureTooltipEl();
    const rect = target.getBoundingClientRect();
    const margin = 10;

    tip.style.left = "0px";
    tip.style.top = "0px";
    const tipRect = tip.getBoundingClientRect();

    let left = rect.left + rect.width / 2 - tipRect.width / 2;
    left = Math.max(margin, Math.min(left, window.innerWidth - tipRect.width - margin));

    let top = rect.top - tipRect.height - 8;
    if (top < margin) {
      top = rect.bottom + 8;
    }
    if (top + tipRect.height > window.innerHeight - margin) {
      top = Math.max(margin, window.innerHeight - tipRect.height - margin);
    }

    tip.style.left = `${Math.round(left)}px`;
    tip.style.top = `${Math.round(top)}px`;
  }

  function showTooltip(target, text) {
    const tip = ensureTooltipEl();
    activeTarget = target;
    tip.textContent = text;
    tip.setAttribute("aria-hidden", "false");
    tip.classList.add("is-visible");
    positionTooltip(target);
  }

  function hideTooltip() {
    if (!tooltipEl) return;
    activeTarget = null;
    tooltipEl.classList.remove("is-visible");
    tooltipEl.setAttribute("aria-hidden", "true");
  }

  function resolveCandidate(node) {
    if (!node || node.nodeType !== 1) return null;
    let current = node.closest(TEXT_SELECTOR);
    while (current) {
      const fullText = getOverflowFullText(current);
      if (fullText) return { el: current, text: fullText };
      current = current.parentElement ? current.parentElement.closest(TEXT_SELECTOR) : null;
    }
    return null;
  }

  document.addEventListener("mouseover", (event) => {
    const match = resolveCandidate(event.target);
    if (!match) {
      if (activeTarget && !activeTarget.contains(event.target)) {
        hideTooltip();
      }
      return;
    }
    if (activeTarget !== match.el || (tooltipEl && tooltipEl.textContent !== match.text)) {
      showTooltip(match.el, match.text);
    }
  });

  document.addEventListener("mouseout", (event) => {
    if (!activeTarget) return;
    if (event.relatedTarget && activeTarget.contains(event.relatedTarget)) return;
    hideTooltip();
  });

  document.addEventListener("mousedown", hideTooltip);
  document.addEventListener("scroll", hideTooltip, true);
  window.addEventListener("resize", hideTooltip);
})(window, document);
