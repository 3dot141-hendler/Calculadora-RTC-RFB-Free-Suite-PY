/**
 * PartialRouter - Carregamento assíncrono de visões HTML parciais
 * com cache local em memória, cache-busting dinâmico e preservação de rota ativa.
 */
(function (window, document) {
  "use strict";

  const STORAGE_KEY_ROUTE = "rtc_suite_active_route";
  const partialCache = new Map();

  const ROUTE_TITLES = {
    dashboard: "Visão Geral",
    simples: "Simples Nacional (RTC)",
    "regime-regular": "Regime Regular (IBS / CBS / IS)",
    danfse: "Gerador DANFSE",
  };

  function updateActiveNav(route) {
    document.querySelectorAll("#appSidebar [data-route]").forEach((link) => {
      const isMatch = link.dataset.route === route;
      link.classList.toggle("active", isMatch);
      if (link.classList.contains("text-white-50") && isMatch) {
        link.classList.remove("text-white-50");
        link.classList.add("text-white");
      }
    });

    const titleEl = document.getElementById("pageTitle");
    if (titleEl) {
      titleEl.textContent = ROUTE_TITLES[route] || "Calculadora RTC";
    }
  }

  async function fetchPartialHtml(route, forceRefresh = false) {
    if (!forceRefresh && partialCache.has(route)) {
      return partialCache.get(route);
    }

    const rawPath = `partials/${route}.html`;
    const url = window.CacheBuster ? await window.CacheBuster.bustUrl(rawPath) : rawPath;

    const response = await fetch(url, { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`Falha ao carregar módulo '${route}' (HTTP ${response.status}).`);
    }

    const html = await response.text();
    partialCache.set(route, html);
    return html;
  }

  async function navigate(route, forceRefresh = false) {
    const validRoute = ROUTE_TITLES[route] ? route : "dashboard";
    const container = document.getElementById("partial-container");
    if (!container) return;

    updateActiveNav(validRoute);
    localStorage.setItem(STORAGE_KEY_ROUTE, validRoute);
    if (window.location.hash !== `#${validRoute}`) {
      window.history.replaceState(null, "", `#${validRoute}`);
    }

    // Fecha menu mobile após clique
    document.body.classList.remove("sidebar-mobile-open");

    try {
      const html = await fetchPartialHtml(validRoute, forceRefresh);
      container.replaceChildren();
      const range = document.createRange();
      range.selectNodeContents(container);
      container.appendChild(range.createContextualFragment(html));

      document.dispatchEvent(
        new CustomEvent("partial:loaded", { detail: { route: validRoute } })
      );
    } catch (error) {
      container.innerHTML = `
        <div class="alert alert-danger d-flex align-items-center gap-2" role="alert">
          <i class="bi bi-exclamation-triangle-fill"></i>
          <div>${error.message}</div>
        </div>
      `;
    }
  }

  function initRouter() {
    document.querySelectorAll("#appSidebar [data-route]").forEach((el) => {
      el.addEventListener("click", (event) => {
        event.preventDefault();
        navigate(el.dataset.route);
      });
    });

    const hashRoute = window.location.hash.replace("#", "").trim();
    const savedRoute = localStorage.getItem(STORAGE_KEY_ROUTE);
    navigate(hashRoute || savedRoute || "dashboard");
  }

  window.PartialRouter = {
    navigate,
    initRouter,
    clearCache: () => partialCache.clear(),
  };
})(window, document);

