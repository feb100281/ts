// =============================
// custom.js (Jazzmin / AdminLTE)
// =============================

console.log("✅ custom.js loaded");

// -------------------------------------------------
// 0) Helpers
// -------------------------------------------------
function num(x) {
  const n = Number(x);
  return Number.isFinite(n) ? n : 0;
}

function escapeHtml(s) {
  return String(s ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function shortInn(inn) {
  const x = String(inn ?? "").replace(/\D/g, "");
  return x ? x : "—";
}

function formatRuDate(value) {
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return String(value || "");
  return new Intl.DateTimeFormat("ru-RU", {
    day: "2-digit",
    month: "long",
    year: "numeric",
    weekday: "long",
  }).format(d);
}

// -------------------------------------------------
// 1) Твоя логика раскрытия/сворачивания карточки
// -------------------------------------------------
document.addEventListener("click", function (event) {
  const header = event.target.closest(".valuation-inline__header");
  if (!header) return;

  const box = header.closest(".valuation-inline");
  if (!box) return;

  if (box.classList.contains("is-collapsed")) {
    box.classList.remove("is-collapsed");
    box.classList.add("is-open");
  } else {
    box.classList.add("is-collapsed");
    box.classList.remove("is-open");
  }
});

// -------------------------------------------------
// 2) Jazzmin topmenu: ИКОНКИ БЕЗ ТЕКСТА
// -------------------------------------------------
(function () {
  const ICONS = {
    Home: "fa-solid fa-house",
    Пользователи: "fa-solid fa-users",
    Помощь: "fa-solid fa-circle-question",
    "Курсы Валют": "fa-solid fa-chart-line",
    Календарь: "fa-solid fa-calendar-days",
    Контрагенты: "fa-solid fa-handshake",
    Договоры: "fa-solid fa-file-signature",
    Выписки: "fa-solid fa-receipt",
  };

  function enhanceTopMenu() {
    const links = document.querySelectorAll(".main-header .navbar-nav .nav-link");

    links.forEach((a) => {
      const rawText = (a.textContent || "").replace(/\s+/g, " ").trim();
      if (!rawText) return;

      if (a.classList.contains("jm-toplink")) return;

      const iconClass = ICONS[rawText];
      if (!iconClass) return;

      a.classList.add("jm-toplink");
      a.textContent = "";

      const ico = document.createElement("span");
      ico.className = "jm-ico";
      ico.innerHTML = `<i class="${iconClass}" aria-hidden="true"></i>`;
      a.appendChild(ico);

      a.setAttribute("title", rawText);
    });
  }

  function boot() {
    enhanceTopMenu();
  }

  document.addEventListener("DOMContentLoaded", boot);
  document.addEventListener("pjax:end", boot);
})();

// -------------------------------------------------
// 3) Bell: секции + строки уведомлений (масштабируемо)
// -------------------------------------------------
(function () {
  function getNavbarUl() {
    return document.querySelector(".main-header .navbar-nav");
  }

  function injectBellStylesOnce() {
    if (document.getElementById("jmBellStyles")) return;

    const st = document.createElement("style");
    st.id = "jmBellStyles";
    st.textContent = `
:root{
  --jm-fg: #111827;
  --jm-muted: #6b7280;
  --jm-border: #e5e7eb;
  --jm-bg: #ffffff;
  --jm-bg2: #f9fafb;
  --jm-shadow: 0 18px 42px rgba(17,24,39,.12);
}

.jm-bell-wrap{ position: relative; }

.jm-bell-badge{
  position:absolute;
  top: 5px;
  right: 5px;
  display:inline-flex;
  align-items:center;
  justify-content:center;
  min-width: 18px;
  height: 18px;
  padding: 0 6px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 800;
  background: #ef4444;
  color: #fff;
  box-shadow: 0 10px 20px rgba(17,24,39,.18);
}

.jm-bell-menu{
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 8px;
  width: 420px;
  z-index: 9999;

  background: var(--jm-bg);
  border: 1px solid var(--jm-border);
  border-radius: 12px;
  box-shadow: var(--jm-shadow);

  max-height: min(520px, 70vh);
  overflow: auto;

  transform-origin: top right;
  transform: translateY(6px);
  opacity: 0;
  pointer-events: none;
  transition: opacity .12s ease, transform .12s ease;
}
.jm-bell-menu.is-open{
  transform: translateY(0);
  opacity: 1;
  pointer-events: auto;
}

.jm-bell-menu__head{
  padding: 12px 12px 10px 12px;
  border-bottom: 1px solid var(--jm-border);
  background: var(--jm-bg);
  position: sticky;
  top: 0;
  z-index: 2;
}
.jm-bell-menu__title{
  font-size: 14px;
  font-weight: 900;
  color: var(--jm-fg);
  line-height: 1.1;
}
.jm-bell-menu__sub{
  margin-top: 3px;
  font-size: 12px;
  color: var(--jm-muted);
}

/* Секция */
.jm-bell-section{
  padding: 10px 10px 0 10px;
}
.jm-bell-section__title{
  font-size: 11px;
  font-weight: 900;
  letter-spacing: .04em;
  text-transform: uppercase;
  color: var(--jm-muted);
  padding: 6px 4px 6px 4px;
}

/* Строка-уведомление */
.jm-bell-item{
  display:flex;
  align-items:center;
  gap: 10px;
  margin: 8px 0 10px 0;
  padding: 11px 12px;
  border-radius: 12px;
  text-decoration:none;

  color: var(--jm-fg);
  background: var(--jm-bg);
  border: 1px solid var(--jm-border);

  transition: background .12s ease, transform .08s ease;
}
.jm-bell-item:hover{
  background: var(--jm-bg2);
  transform: translateY(-1px);
}

.jm-dot{
  width: 8px;
  height: 8px;
  border-radius: 6px;
  flex: 0 0 auto;
  background: #9ca3af;
  box-shadow: 0 0 0 3px rgba(17,24,39,.05);
}
.jm-dot-danger{ background: #ef4444; }
.jm-dot-ok{ background: #10b981; }

.jm-bell-item__label{
  flex: 1 1 auto;
  min-width: 0;
  display:flex;
  flex-direction:column;
  gap: 2px;
  font-size: 13px;
  font-weight: 850;
  line-height: 1.15;
}
.jm-bell-item__sub{
  font-size: 11px;
  font-weight: 650;
  color: var(--jm-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.jm-bell-item__badge{
  flex: 0 0 auto;
  display:inline-flex;
  align-items:center;
  justify-content:center;
  min-width: 34px;
  height: 22px;
  padding: 0 8px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 900;
  border: 1px solid var(--jm-border);
  background: #fff;
  color: var(--jm-fg);
}
.jm-bell-item__badge.ok{
  border-color: rgba(16,185,129,.25);
  background: rgba(16,185,129,.08);
  color: #047857;
}
.jm-bell-item__badge.danger{
  border-color: rgba(185,28,28,.25);
  background: rgba(185,28,28,.06);
  color: #991b1b;
}

/* badge позиционируем относительно jm-toplink */
.jm-bell-btn { position: relative; }
#jmBellBadge { z-index: 5; }

.jm-bell-btn:focus-visible,
.jm-bell-item:focus-visible{
  outline: 2px solid rgba(17,24,39,.25);
  outline-offset: 2px;
}
`;
    document.head.appendChild(st);
  }

  function ensureBellUI() {
    const nav = getNavbarUl();
    if (!nav) return;
    if (document.getElementById("jmBellBtn")) return;

    injectBellStylesOnce();

    const li = document.createElement("li");
    li.className = "nav-item jm-bell-wrap";

    li.innerHTML = `
      <a href="#" class="nav-link jm-toplink jm-bell-btn" id="jmBellBtn" title="Уведомления">
        <span class="jm-ico">
          <i class="fa-solid fa-bell" aria-hidden="true"></i>
        </span>
        <span class="jm-bell-badge" id="jmBellBadge" style="display:none;">0</span>
      </a>

      <div class="jm-bell-menu" id="jmBellMenu" aria-hidden="true">
        <div class="jm-bell-menu__head">
          <div class="jm-bell-menu__title">Уведомления</div>
          <div class="jm-bell-menu__sub" id="jmBellSub">—</div>
        </div>

        <!-- сюда рендерим секции -->
        <div id="jmBellBody"></div>
      </div>
    `;

    nav.appendChild(li);

    const btn = li.querySelector("#jmBellBtn");
    const menu = li.querySelector("#jmBellMenu");

    function closeMenu() {
      menu.classList.remove("is-open");
      menu.setAttribute("aria-hidden", "true");
    }

    function toggleMenu() {
      const open = menu.classList.contains("is-open");
      if (open) closeMenu();
      else {
        menu.classList.add("is-open");
        menu.setAttribute("aria-hidden", "false");
      }
    }

    btn.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      toggleMenu();
    });

    document.addEventListener("click", function (e) {
      if (!li.contains(e.target)) closeMenu();
    });

    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") closeMenu();
    });
  }

  // ---- UI builders (секции и строки) ----

  function makeItem({ href = "#", status = "ok", title = "—", sub = "—", badge = "—" }) {
    const dotClass = status === "danger" ? "jm-dot jm-dot-danger" : "jm-dot jm-dot-ok";
    const badgeClass = status === "danger" ? "jm-bell-item__badge danger" : "jm-bell-item__badge ok";

    const a = document.createElement("a");
    a.className = "jm-bell-item";
    a.href = href;

    a.innerHTML = `
      <span class="${dotClass}"></span>
      <span class="jm-bell-item__label">
        <span>${escapeHtml(title)}</span>
        <span class="jm-bell-item__sub">${escapeHtml(sub)}</span>
      </span>
      <span class="${badgeClass}">${escapeHtml(badge)}</span>
    `;
    return a;
  }

  function makeSection(title, items) {
    const wrap = document.createElement("div");
    wrap.className = "jm-bell-section";

    const head = document.createElement("div");
    head.className = "jm-bell-section__title";
    head.textContent = title;

    wrap.appendChild(head);
    items.forEach((it) => wrap.appendChild(makeItem(it)));

    return wrap;
  }

  // -------------------------------------------------
  // refreshBell: собираем все уведомления как список секций
  // -------------------------------------------------
  async function refreshBell() {
    ensureBellUI();

    const bellBadge = document.getElementById("jmBellBadge");
    const bellSub = document.getElementById("jmBellSub");
    const bellBody = document.getElementById("jmBellBody");
    if (!bellBody) return;

    const sections = [];
    let problems = 0;

    // 1) FX (1 строка в секции "Курсы валют")
    try {
      const resp = await fetch("/admin/fx-status/", { credentials: "same-origin" });
      if (resp.ok) {
        const data = await resp.json();
        const todayStr = data.date ? formatRuDate(data.date) : "сегодня";
        const href = data.admin_url || "/admin/macro/currencyrate/";

        if (data.has_fx_today) {
          sections.push({
            title: "Макро показатели",
            items: [
              { status: "ok", title: "Курсы валют загружены", sub: `Дата: ${todayStr}`, badge: "OK", href },
            ],
          });
        } else {
          problems += 1;
          sections.push({
            title: "Курсы валют",
            items: [
              { status: "danger", title: "Нет курса валют на сегодня", sub: `Дата: ${todayStr}. Нужно обновить курс в базе`, badge: "!", href },
            ],
          });
        }
      }
    } catch (e) {
      console.warn("fx status error", e);
    }

    // 2) Контрагенты (2 отдельные строки)
    try {
      const resp = await fetch("/admin/cp-issues-status/", { credentials: "same-origin" });
      if (resp.ok) {
        const data = await resp.json();

        const nc = data.no_contracts || {};
        const ng = data.no_glyph || {};

        const totalNoContracts = num(nc.total);
        const totalNoGlyph = num(ng.total);

        const items = [];

        if (totalNoContracts === 0) {
          items.push({
            status: "ok",
            title: "Контрагенты без договоров",
            sub: "Пусто",
            badge: "OK",
            href: nc.admin_url || "/admin/counterparties/counterparty/?has_contract=0",
          });
        } else {
          problems += 1;
          items.push({
            status: "danger",
            title: "Контрагенты без договоров",
            sub: "Нужно проверить и привязать договоры",
            badge: String(totalNoContracts),
            href: nc.admin_url || "/admin/counterparties/counterparty/?has_contract=0",
          });
        }

        if (totalNoGlyph === 0) {
          items.push({
            status: "ok",
            title: "Контрагенты без глифа",
            sub: "Пусто",
            badge: "OK",
            href: ng.admin_url || "/admin/counterparties/counterparty/?logo__isnull=1",
          });
        } else {
          problems += 1;
          items.push({
            status: "danger",
            title: "Контрагенты без глифа",
            sub: "Нужно добавить логотип/глиф",
            badge: String(totalNoGlyph),
            href: ng.admin_url || "/admin/counterparties/counterparty/?logo__isnull=1",
          });
        }

        sections.push({ title: "Контрагенты", items });
      }
    } catch (e) {
      console.warn("cp issues status error", e);
    }

    // 3) Казначейство (3 отдельные строки)
    try {
      const resp = await fetch("/admin/treasury-status/", { credentials: "same-origin" });
      if (resp.ok) {
        const data = await resp.json();

        const noContract = data.no_contract || {};
        const noCfItem = data.no_cfitem || {};
        const noCpFinal = data.no_cp_final || {};

        const c1 = num(noContract.total);
        const c2 = num(noCfItem.total);
        const c3 = num(noCpFinal.total);

        const items = [];

        // CF без договоров
        if (c1 === 0) {
          items.push({
            status: "ok",
            title: "CF документы без договоров",
            sub: "Пусто",
            badge: "OK",
            href: noContract.admin_url || "#",
          });
        } else {
          problems += 1;
          items.push({
            status: "danger",
            title: "CF документы без договоров",
            sub: "Нужно привязать договор",
            badge: String(c1),
            href: noContract.admin_url || "#",
          });
        }

        // CF без статьи CF
        if (c2 === 0) {
          items.push({
            status: "ok",
            title: "CF документы без статьи CF",
            sub: "Пусто",
            badge: "OK",
            href: noCfItem.admin_url || "#",
          });
        } else {
          problems += 1;
          items.push({
            status: "danger",
            title: "CF документы без статьи CF",
            sub: "Нужно назначить статью CF",
            badge: String(c2),
            href: noCfItem.admin_url || "#",
          });
        }

        // CF без финального контрагента
        if (c3 === 0) {
          items.push({
            status: "ok",
            title: "CF документы без финального контрагента",
            sub: "Пусто",
            badge: "OK",
            href: noCpFinal.admin_url || "#",
          });
        } else {
          problems += 1;
          items.push({
            status: "danger",
            title: "CF документы без финального контрагента",
            sub: "Нужно указать финального контрагента",
            badge: String(c3),
            href: noCpFinal.admin_url || "#",
          });
        }

        sections.push({ title: "Казначейство", items });
      }
    } catch (e) {
      console.warn("treasury status error", e);
    }

    // ---- Рендер ----
    bellBody.innerHTML = "";
    if (!sections.length) {
      bellBody.innerHTML = `<div style="padding:12px;color:#6b7280;">Нет данных для уведомлений</div>`;
    } else {
      sections.forEach((s) => bellBody.appendChild(makeSection(s.title, s.items)));
    }

    // Header summary
    if (bellSub) {
      bellSub.textContent = problems ? `Есть замечания: ${problems}` : "Всё в порядке";
    }

    // Badge на колокольчике: количество проблемных строк
    if (bellBadge) {
      if (problems) {
        bellBadge.textContent = String(problems);
        bellBadge.style.display = "inline-flex";
      } else {
        bellBadge.style.display = "none";
      }
    }
  }

  function boot() {
    refreshBell();
    setInterval(refreshBell, 60 * 1000);
  }

  document.addEventListener("DOMContentLoaded", boot);
  document.addEventListener("pjax:end", boot);
})();




