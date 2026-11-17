/**
 * SidebarManager - Controle de submenus expansíveis, modo mini-sidebar,
 * tooltips inteligentes (ativos apenas no modo mini) e persistência em localStorage.
 */
(function (window, document) {
  "use strict";

  const STORAGE_KEY_MINI = "rtc_suite_sidebar_mini";
  const STORAGE_KEY_SUBMENUS = "rtc_suite_sidebar_submenus";

  let tooltipInstances = [];

  function syncTooltips() {
    // Destrói tooltips anteriores antes de recalcular o estado
    tooltipInstances.forEach((instance) => instance.dispose());
    tooltipInstances = [];

    const isMini = document.body.classList.contains("sidebar-mini");
    if (!isMini || typeof window.bootstrap === "undefined") {
      return;
    }

    const triggers = document.querySelectorAll('#appSidebar [data-bs-toggle="tooltip"]');
    triggers.forEach((el) => {
      tooltipInstances.push(
        new window.bootstrap.Tooltip(el, {
          trigger: "hover focus",
          boundary: "window",
        })
      );
    });
  }

  function loadSubmenuState() {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY_SUBMENUS) || "{}");
    } catch {
      return {};
    }
  }

  function saveSubmenuState(state) {
    localStorage.setItem(STORAGE_KEY_SUBMENUS, JSON.stringify(state));
  }

  function initSubmenus() {
    const savedState = loadSubmenuState();
    const toggles = document.querySelectorAll(".submenu-toggle");

    toggles.forEach((toggle) => {
      const key = toggle.dataset.submenu;
      const content = document.querySelector(`[data-submenu-content="${key}"]`);
      if (!content) return;

      const isExpanded = savedState[key] !== undefined ? savedState[key] : true;
      toggle.setAttribute("aria-expanded", String(isExpanded));
      content.classList.toggle("collapsed", !isExpanded);

      toggle.addEventListener("click", () => {
        if (document.body.classList.contains("sidebar-mini")) {
          // Em modo mini, expande a sidebar ao clicar em um grupo
          setMiniMode(false);
        }
        const currentlyExpanded = toggle.getAttribute("aria-expanded") === "true";
        const nextState = !currentlyExpanded;
        toggle.setAttribute("aria-expanded", String(nextState));
        content.classList.toggle("collapsed", !nextState);

        const state = loadSubmenuState();
        state[key] = nextState;
        saveSubmenuState(state);
      });
    });
  }

  function setMiniMode(enabled) {
    document.body.classList.toggle("sidebar-mini", enabled);
    localStorage.setItem(STORAGE_KEY_MINI, String(enabled));
    syncTooltips();
  }

  function initSidebar() {
    const savedMini = localStorage.getItem(STORAGE_KEY_MINI) === "true";
    setMiniMode(savedMini);
    initSubmenus();

    const toggleBtn = document.getElementById("toggleSidebarBtn");
    if (toggleBtn) {
      toggleBtn.addEventListener("click", () => {
        const isMini = document.body.classList.contains("sidebar-mini");
        setMiniMode(!isMini);
      });
    }

    const mobileBtn = document.getElementById("mobileMenuBtn");
    if (mobileBtn) {
      mobileBtn.addEventListener("click", () => {
        document.body.classList.toggle("sidebar-mobile-open");
      });
    }
  }

  window.SidebarManager = {
    initSidebar,
    setMiniMode,
    syncTooltips,
  };
})(window, document);

