// =============================
// Conditions accordion (UNBREAKABLE)
// window capture + direct handlers + PJAX
// =============================

(function () {
  function init(root = document) {
    const groups = [
      root.getElementById?.("conditions-group") || document.getElementById("conditions-group"),
      root.getElementById?.("conditions_set-group") || document.getElementById("conditions_set-group"),
    ].filter(Boolean);

    if (!groups.length) return;

    groups.forEach((group) => {
      const inlines = Array.from(group.querySelectorAll(".inline-related"))
        .filter(el => !el.classList.contains("empty-form"));

      inlines.forEach((inline, idx) => {
        const h3 = inline.querySelector("h3");
        if (!h3) return;

        // headerTop = прямой ребёнок inline (учёт Jazzmin обёрток)
        let headerTop = h3;
        while (headerTop.parentElement && headerTop.parentElement !== inline) {
          headerTop = headerTop.parentElement;
        }

        // body
        let body = inline.querySelector(":scope > .cond-body");
        if (!body) {
          body = document.createElement("div");
          body.className = "cond-body";
          headerTop.insertAdjacentElement("afterend", body);

          // переносим всё после headerTop в body, пока не упремся в .delete
          while (body.nextSibling) {
            const next = body.nextSibling;
            if (next.classList && next.classList.contains("delete")) break;
            body.appendChild(next);
          }
        }

        // кнопка
        let btn = h3.querySelector(".cond-toggle");
        if (!btn) {
          btn = document.createElement("button");
          btn.type = "button";
          btn.className = "cond-toggle";
          btn.setAttribute("aria-label", "Свернуть/развернуть");
          btn.innerHTML = "▾";
          h3.appendChild(btn);
        }

        // дефолт: свернуть все кроме первого
        const collapsed = idx > 0;
        inline.classList.toggle("is-collapsed", collapsed);
        body.style.display = collapsed ? "none" : "";

        // прямой обработчик на кнопку (на случай если кто-то глушит события)
        if (btn.dataset.bound !== "1") {
          btn.dataset.bound = "1";
          btn.addEventListener("click", (e) => {
            e.preventDefault();
            e.stopPropagation();

            const isCollapsed = inline.classList.contains("is-collapsed");
            inline.classList.toggle("is-collapsed", !isCollapsed);
            body.style.display = isCollapsed ? "" : "none";
          }, true); // capture
        }
      });
    });
  }

  function toggleFromEvent(e) {
    const btn = e.target && e.target.closest ? e.target.closest(".cond-toggle") : null;
    if (!btn) return;

    const inline = btn.closest(".inline-related");
    if (!inline) return;

    const body = inline.querySelector(":scope > .cond-body") || inline.querySelector(".cond-body");
    if (!body) return;

    e.preventDefault();
    e.stopPropagation();

    const isCollapsed = inline.classList.contains("is-collapsed");
    inline.classList.toggle("is-collapsed", !isCollapsed);
    body.style.display = isCollapsed ? "" : "none";
  }

  document.addEventListener("DOMContentLoaded", () => init(document));
  document.addEventListener("pjax:end", () => init(document));

  // самый ранний перехват клика
  window.addEventListener("click", toggleFromEvent, true);
})();