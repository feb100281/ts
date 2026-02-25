console.log("✅ conditions_inline_collapse.js loaded");

(function () {
  function onClick(event) {
    const header = event.target.closest(".valuation-inline__header");
    if (!header) return;

    // блокируем ТОЛЬКО клик по зоне "Удалить"
    if (event.target.closest(".inline-deletelink")) return;

    const box = header.closest(".valuation-inline");
    if (!box) return;

    box.classList.toggle("is-collapsed");
    box.classList.toggle("is-open");
  }

  // чтобы не навешивалось 2 раза
  function bindOnce() {
    if (window.__condInlineBound) return;
    window.__condInlineBound = true;
    document.addEventListener("click", onClick);
  }

  document.addEventListener("DOMContentLoaded", bindOnce);
  document.addEventListener("pjax:end", bindOnce); // Jazzmin
})();