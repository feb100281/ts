(function () {
  function codeToChar(code) {
    if (!code) return "";
    let s = String(code).trim();
    if (s.startsWith("\\u")) s = s.slice(2);
    if (s.toLowerCase().startsWith("u")) s = s.slice(1);
    const n = parseInt(s, 16);
    if (Number.isNaN(n)) return "";
    return String.fromCharCode(n);
  }

  function extractCode(text) {
    const m = String(text || "").match(/u[0-9a-fA-F]{4}/);
    return m ? m[0] : "";
  }

  function renderOption(state) {
    if (!state || !state.id) {
      return state && state.text ? state.text : "";
    }

    const code = extractCode(state.text); // "uE007"
    const ch = code ? codeToChar(code) : "";

    // HTML для строки: [иконка]  uE007 — Название
    const wrap = document.createElement("span");
    wrap.className = "glyph2-wrap";

    const icon = document.createElement("span");
    icon.className = "glyph2-icon";
    icon.textContent = ch;

    const label = document.createElement("span");
    label.className = "glyph2-label";
    label.textContent = state.text;

    wrap.appendChild(icon);
    wrap.appendChild(label);
    return wrap;
  }

  function init() {
    const el = document.getElementById("id_logo_glyph");
    if (!el) return;

    // Django admin обычно уже поднимает jQuery
    if (!window.jQuery || !jQuery.fn.select2) return;

    const $el = jQuery(el);

    // если select2 уже был — уничтожим и пересоздадим
    try { $el.select2("destroy"); } catch (e) {}

    $el.select2({
      width: "style",
      templateResult: renderOption,
      templateSelection: renderOption,
      dropdownAutoWidth: true,
    });
  }

  document.addEventListener("DOMContentLoaded", init);
})();
