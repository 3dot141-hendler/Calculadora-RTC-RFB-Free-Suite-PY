/**
 * CacheBuster - Injeção dinâmica de timestamps (?v={mtime}) em runtime
 * Garante atualização instantânea de CSS, JS e partials sem cache residual.
 */
(function (window, document) {
  "use strict";

  const SESSION_FALLBACK_VERSION = Date.now().toString();
  const mtimeCache = new Map();

  /**
   * Obtém o timestamp de modificação (mtime) via cabeçalho HTTP Last-Modified
   * com fallback seguro para o timestamp da sessão atual.
   */
  async function resolveMtime(url) {
    const cleanUrl = url.split("?")[0];
    if (mtimeCache.has(cleanUrl)) {
      return mtimeCache.get(cleanUrl);
    }

    let version = SESSION_FALLBACK_VERSION;
    try {
      const response = await fetch(cleanUrl, { method: "HEAD", cache: "no-store" });
      const lastModified = response.headers.get("Last-Modified");
      if (lastModified) {
        const parsed = Date.parse(lastModified);
        if (!Number.isNaN(parsed)) {
          version = String(Math.floor(parsed / 1000));
        }
      }
    } catch {
      // Mantém fallback da sessão se HEAD falhar
    }

    mtimeCache.set(cleanUrl, version);
    return version;
  }

  /**
   * Adiciona ?v={mtime} a uma URL para evitar cache residual.
   */
  async function bustUrl(url) {
    const version = await resolveMtime(url);
    const cleanUrl = url.split("?")[0];
    return `${cleanUrl}?v=${encodeURIComponent(version)}`;
  }

  /**
   * Atualiza elementos <link data-cache-bust> e <script data-cache-bust> no DOM.
   */
  async function applyDynamicCacheBusting() {
    const links = document.querySelectorAll("link[data-cache-bust]");
    for (const link of links) {
      const href = link.getAttribute("href");
      if (href) {
        link.setAttribute("href", await bustUrl(href));
      }
    }

    const scripts = document.querySelectorAll("script[data-cache-bust]");
    for (const script of scripts) {
      const src = script.getAttribute("src");
      if (src && !src.includes("?v=")) {
        const busted = await bustUrl(src);
        script.dataset.bustedSrc = busted;
      }
    }
  }

  window.CacheBuster = {
    bustUrl,
    resolveMtime,
    applyDynamicCacheBusting,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", applyDynamicCacheBusting);
  } else {
    applyDynamicCacheBusting();
  }
})(window, document);
