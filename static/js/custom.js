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
    'Запустить GL ETL': "fa-solid fa-gears",
    'Скачать GL CSV': "fa-solid fa-file-csv",
    'Скачать дебиторы/кредиторы CSV': "fa-solid fa-money-bill-transfer",
    'Скачать проверку договоров GL/PL/BS CSV': "fa-solid fa-scale-balanced",
    'Скачать ManPack': "fa-solid fa-file-excel",
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
// 2.1) Topmenu dropdown: Экспорт
// -------------------------------------------------
(function () {
  function injectExportMenuStylesOnce() {
    if (document.getElementById("jmExportMenuStyles")) return;

    const st = document.createElement("style");
    st.id = "jmExportMenuStyles";
    st.textContent = `
  .jm-export-wrap {
    position: relative;
  }

  .jm-export-btn {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-weight: 600;
  }

  .jm-export-btn .jm-export-label {
    white-space: nowrap;
  }

  .jm-export-menu {
    position: absolute;
    top: calc(100% + 8px);
    left: 0;
    min-width: 340px;
    z-index: 9999;

    background: #ffffff;
    border: 1px solid #cfcfcf;
    border-radius: 0;
    box-shadow: none;
    padding: 0;

    opacity: 0;
    transform: translateY(4px);
    pointer-events: none;
    transition: opacity .12s ease, transform .12s ease;
  }

  .jm-export-menu.is-open {
    opacity: 1;
    transform: translateY(0);
    pointer-events: auto;
  }

  .jm-export-item {
    display: flex;
    align-items: center;
    gap: 14px;
    min-height: 35px;
    padding: 0 18px;
    text-decoration: none;
    color: #2f2f2f;
    font-size: 12px;
    font-weight: 300;
    line-height: 1.2;
    background: #ffffff;
    border-bottom: 1px solid #d9d9d9;
  }

  .jm-export-item:last-child {
    border-bottom: none;
  }

  .jm-export-item:hover {
    background: #f7f7f7;
    color: #2f2f2f;
    text-decoration: none;
  }

  .jm-export-item:focus-visible {
    outline: none;
    background: #f3f3f3;
  }

  .jm-export-item i {
    width: 20px;
    text-align: center;
    color: #4b5563;
    font-size: 14px;
    flex: 0 0 20px;
  }

  .jm-export-item span {
    display: block;
    color: #2f2f2f;
    font-size: 14px;
    font-weight: 400;
    letter-spacing: 0;
  }
`;
    document.head.appendChild(st);
  }

  function getLinkLabel(a) {
    return (
      (a.getAttribute("title") || "").trim() ||
      (a.textContent || "").replace(/\s+/g, " ").trim()
    );
  }

  function buildExportDropdown() {
    const nav = document.querySelector(".main-header .navbar-nav");
    if (!nav) return;
    if (document.getElementById("jmExportWrap")) return;

    const links = Array.from(document.querySelectorAll(".main-header .navbar-nav .nav-link"));

    const glLink = links.find((a) => getLinkLabel(a) === "Скачать GL CSV");

    const arapLink = links.find((a) => getLinkLabel(a) === "Скачать дебиторы/кредиторы CSV");

    const contractsCheckLink = links.find(
      (a) => getLinkLabel(a) === "Скачать проверку договоров GL/PL/BS CSV"
    );

    const manpackLink = links.find(
      (a) => getLinkLabel(a) === "Скачать ManPack"
    );

    if (!glLink && !arapLink && !contractsCheckLink && !manpackLink) return;

    injectExportMenuStylesOnce();

    const glLi = glLink ? glLink.closest(".nav-item") : null;
    const arapLi = arapLink ? arapLink.closest(".nav-item") : null;
    const contractsCheckLi = contractsCheckLink ? contractsCheckLink.closest(".nav-item") : null;
    const manpackLi = manpackLink ? manpackLink.closest(".nav-item") : null;

    const insertBeforeNode = glLi || arapLi || contractsCheckLi || manpackLi;

    [glLi, arapLi, contractsCheckLi, manpackLi].forEach((li) => {
      if (li) li.remove();
    });

    const li = document.createElement("li");
    li.className = "nav-item jm-export-wrap";
    li.id = "jmExportWrap";

    li.innerHTML = `
      <a href="#" class="nav-link jm-export-btn" id="jmExportBtn" title="Экспорт">
        <span class="jm-ico">
          <i class="fa-solid fa-download" aria-hidden="true"></i>
        </span>
        <span class="jm-export-label">Экспорт</span>
      </a>
      <div class="jm-export-menu" id="jmExportMenu" aria-hidden="true"></div>
    `;

    if (insertBeforeNode && insertBeforeNode.parentNode) {
      insertBeforeNode.parentNode.insertBefore(li, insertBeforeNode);
    } else {
      nav.appendChild(li);
    }

    const menu = li.querySelector("#jmExportMenu");

   const items = [
      glLink
        ? {
            href: glLink.getAttribute("href") || "#",
            label: "Главная книга (GL)",
            icon: "fa-solid fa-file-csv",
          }
        : null,
      arapLink
        ? {
            href: arapLink.getAttribute("href") || "#",
            label: "Дебиторы / кредиторы (ARAP)",
            icon: "fa-solid fa-file-csv",
          }
        : null,
      contractsCheckLink
        ? {
            href: contractsCheckLink.getAttribute("href") || "#",
            label: "Проверка договоров на списание в PL",
            icon: "fa-solid fa-scale-balanced",
          }
        : null,
      manpackLink
        ? {
            href: manpackLink.getAttribute("href") || "#",
            label: "Management Pack",
            icon: "fa-solid fa-file-excel",
            className: "jm-manpack-trigger",
          }
        : null,
    ].filter(Boolean);

    items.forEach((item) => {
        const a = document.createElement("a");
        a.className = `jm-export-item ${item.className || ""}`.trim();
        a.href = item.href;
        a.innerHTML = `
          <i class="${item.icon}" aria-hidden="true"></i>
          <span>${item.label}</span>
        `;
        menu.appendChild(a);
      });

    const btn = li.querySelector("#jmExportBtn");

    function closeMenu() {
      menu.classList.remove("is-open");
      menu.setAttribute("aria-hidden", "true");
    }

    function toggleMenu() {
      const isOpen = menu.classList.contains("is-open");
      if (isOpen) closeMenu();
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

  function boot() {
    buildExportDropdown();
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
  border-radius: 4px;
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
  border-radius: 2px;
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



        // 3) Договоры
try {
  const resp = await fetch("/admin/contracts-issues-status/", { credentials: "same-origin" });
  if (resp.ok) {
    const data = await resp.json();


    const noAccrual = data.no_accrual_fn || {};
    const missingDistribution = data.missing_distribution || {};
    const missingBs = data.missing_bs || {};
    const missingPl = data.missing_pl || {};
    const missingSubcontoPl = data.missing_subconto_pl || {};

    const totalNoAccrual = num(noAccrual.total);
    const totalMissingDistribution = num(missingDistribution.total);
    const totalMissingBs = num(missingBs.total);
    const totalMissingPl = num(missingPl.total);
    const totalMissingSubcontoPl = num(missingSubcontoPl.total);

    const items = [];

    if (totalNoAccrual === 0) {
      items.push({
        status: "ok",
        title: "Договоры без функции начисления",
        sub: "Пусто",
        badge: "OK",
        href: noAccrual.admin_url || "/admin/contracts/contracts/?has_accrual_fn=no",
      });
    } else {
      problems += 1;
      items.push({
        status: "danger",
        title: "Договоры без функции начисления",
        sub: "Нужно добавить условия начисления",
        badge: String(totalNoAccrual),
        href: noAccrual.admin_url || "/admin/contracts/contracts/?has_accrual_fn=no",
      });
    }



    if (totalMissingBs === 0) {
      items.push({
        status: "ok",
        title: "Не заполнен Счет ST",
        sub: "Пусто",
        badge: "OK",
        href: missingBs.admin_url || "/admin/contracts/contracts/?missing_distribution=bs",
      });
    } else {
      problems += 1;
      items.push({
        status: "danger",
        title: "Не заполнен Счет ST",
        sub: "Нужно заполнить поле Счет ST",
        badge: String(totalMissingBs),
        href: missingBs.admin_url || "/admin/contracts/contracts/?missing_distribution=bs",
      });
    }

    if (totalMissingPl === 0) {
      items.push({
        status: "ok",
        title: "Не заполнен Счет PL",
        sub: "Пусто",
        badge: "OK",
        href: missingPl.admin_url || "/admin/contracts/contracts/?missing_distribution=pl",
      });
    } else {
      problems += 1;
      items.push({
        status: "danger",
        title: "Не заполнен Счет PL",
        sub: "Нужно заполнить поле Счет PL",
        badge: String(totalMissingPl),
        href: missingPl.admin_url || "/admin/contracts/contracts/?missing_distribution=pl",
      });
    }

    if (totalMissingSubcontoPl === 0) {
      items.push({
        status: "ok",
        title: "Не заполнено Субконто PL",
        sub: "Пусто",
        badge: "OK",
        href: missingSubcontoPl.admin_url || "/admin/contracts/contracts/?missing_distribution=subconto_pl",
      });
    } else {
      problems += 1;
      items.push({
        status: "danger",
        title: "Не заполнено Субконто PL",
        sub: "Нужно заполнить поле Субконто PL",
        badge: String(totalMissingSubcontoPl),
        href: missingSubcontoPl.admin_url || "/admin/contracts/contracts/?missing_distribution=subconto_pl",
      });
    }

    sections.push({ title: "Договоры", items });
  }
} catch (e) {
  console.warn("contracts issues status error", e);
}



    // 4) Казначейство (3 отдельные строки)
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














console.log("✅ manpack_export.js loaded");

(function () {
  function injectStylesOnce() {
    if (document.getElementById("jmManpackStyles")) return;

    const st = document.createElement("style");
    st.id = "jmManpackStyles";
    st.textContent = `
      .jm-manpack-backdrop {
        position: fixed;
        inset: 0;
        background: rgba(17, 24, 39, 0.45);
        z-index: 20000;
        display: none;
        align-items: center;
        justify-content: center;
        padding: 24px;
      }

      .jm-manpack-backdrop.is-open {
        display: flex;
      }

      .jm-manpack-modal {
        width: 100%;
        max-width: 460px;
        background: #ffffff;
        border: 1px solid #d1d5db;
        box-shadow: 0 20px 50px rgba(17, 24, 39, 0.18);
        padding: 20px;
      }

      .jm-manpack-title {
        margin: 0 0 8px 0;
        font-size: 18px;
        font-weight: 700;
        color: #111827;
      }

      .jm-manpack-subtitle {
        margin: 0 0 16px 0;
        font-size: 13px;
        color: #6b7280;
        line-height: 1.45;
      }

      .jm-manpack-label {
        display: block;
        margin-bottom: 8px;
        font-size: 13px;
        font-weight: 600;
        color: #111827;
      }

      .jm-manpack-input {
        width: 100%;
        height: 40px;
        border: 1px solid #d1d5db;
        padding: 0 12px;
        font-size: 14px;
        color: #111827;
        outline: none;
        box-sizing: border-box;
        background: #fff;
      }

      .jm-manpack-input:focus {
        border-color: #111827;
      }

      .jm-manpack-quick {
        display: flex;
        gap: 8px;
        margin-top: 12px;
        margin-bottom: 18px;
        flex-wrap: wrap;
      }

      .jm-manpack-quick-btn {
        border: 1px solid #d1d5db;
        background: #ffffff;
        color: #111827;
        height: 34px;
        padding: 0 12px;
        cursor: pointer;
        font-size: 13px;
      }

      .jm-manpack-quick-btn:hover {
        background: #f9fafb;
      }

      .jm-manpack-actions {
        display: flex;
        justify-content: flex-end;
        gap: 10px;
      }

      .jm-manpack-btn {
        min-width: 110px;
        height: 38px;
        padding: 0 14px;
        border: 1px solid #d1d5db;
        background: #fff;
        cursor: pointer;
        font-size: 14px;
        font-weight: 600;
      }

      .jm-manpack-btn:hover {
        background: #f9fafb;
      }

      .jm-manpack-btn--primary {
        background: #111827;
        color: #ffffff;
        border-color: #111827;
      }

      .jm-manpack-btn--primary:hover {
        background: #0b1220;
      }

      .jm-manpack-error {
        margin-top: 10px;
        font-size: 12px;
        color: #b91c1c;
        display: none;
      }

      .jm-manpack-error.is-visible {
        display: block;
      }
    `;
    document.head.appendChild(st);
  }

  function formatDateToYmd(dateObj) {
    const y = dateObj.getFullYear();
    const m = String(dateObj.getMonth() + 1).padStart(2, "0");
    const d = String(dateObj.getDate()).padStart(2, "0");
    return `${y}-${m}-${d}`;
  }

  function getTodayYmd() {
    return formatDateToYmd(new Date());
  }

  function getEndOfPrevMonthYmd() {
    const d = new Date();
    d.setDate(1);
    d.setHours(0, 0, 0, 0);
    d.setDate(0);
    return formatDateToYmd(d);
  }

  function ensureModal() {
    injectStylesOnce();

    let backdrop = document.getElementById("jmManpackBackdrop");
    if (backdrop) return backdrop;

    backdrop = document.createElement("div");
    backdrop.className = "jm-manpack-backdrop";
    backdrop.id = "jmManpackBackdrop";

    backdrop.innerHTML = `
      <div class="jm-manpack-modal" role="dialog" aria-modal="true" aria-labelledby="jmManpackTitle">
        <h3 class="jm-manpack-title" id="jmManpackTitle">Скачать ManPack</h3>
        <div class="jm-manpack-subtitle">
          Выберите дату отчетности. Можно указать любую дату вручную.
        </div>

        <label class="jm-manpack-label" for="jmManpackDate">Дата отчетности</label>
        <input type="date" id="jmManpackDate" class="jm-manpack-input" />

        <div class="jm-manpack-quick">
          <button type="button" class="jm-manpack-quick-btn" id="jmManpackToday">
            Сегодня
          </button>
          <button type="button" class="jm-manpack-quick-btn" id="jmManpackPrevMonthEnd">
            Конец прошлого месяца
          </button>
        </div>

        <div class="jm-manpack-error" id="jmManpackError">
          Пожалуйста, выберите дату.
        </div>

        <div class="jm-manpack-actions">
          <button type="button" class="jm-manpack-btn" id="jmManpackCancel">Отмена</button>
          <button type="button" class="jm-manpack-btn jm-manpack-btn--primary" id="jmManpackDownload">Скачать</button>
        </div>
      </div>
    `;

    document.body.appendChild(backdrop);

    const dateInput = backdrop.querySelector("#jmManpackDate");
    const btnToday = backdrop.querySelector("#jmManpackToday");
    const btnPrevMonthEnd = backdrop.querySelector("#jmManpackPrevMonthEnd");
    const btnCancel = backdrop.querySelector("#jmManpackCancel");
    const btnDownload = backdrop.querySelector("#jmManpackDownload");
    const errorBox = backdrop.querySelector("#jmManpackError");

    function open() {
      errorBox.classList.remove("is-visible");
      if (!dateInput.value) {
        dateInput.value = getTodayYmd();
      }
      backdrop.classList.add("is-open");
    }

    function close() {
      backdrop.classList.remove("is-open");
      errorBox.classList.remove("is-visible");
    }

    btnToday.addEventListener("click", function () {
      dateInput.value = getTodayYmd();
      errorBox.classList.remove("is-visible");
    });

    btnPrevMonthEnd.addEventListener("click", function () {
      dateInput.value = getEndOfPrevMonthYmd();
      errorBox.classList.remove("is-visible");
    });

    btnCancel.addEventListener("click", close);

    backdrop.addEventListener("click", function (e) {
      if (e.target === backdrop) close();
    });

    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && backdrop.classList.contains("is-open")) {
        close();
      }
    });

    btnDownload.addEventListener("click", function () {
      const reportDate = dateInput.value;

      if (!reportDate) {
        errorBox.classList.add("is-visible");
        return;
      }

      errorBox.classList.remove("is-visible");

      const baseUrl = "/admin/export/manpack/";
      const url = `${baseUrl}?report_date=${encodeURIComponent(reportDate)}`;

      close();
      window.location.href = url;
    });

    backdrop._openManpackModal = open;
    backdrop._closeManpackModal = close;

    return backdrop;
  }

  function bindTriggers() {
    const backdrop = ensureModal();
    const triggers = document.querySelectorAll(".jm-manpack-trigger");

    triggers.forEach((el) => {
      if (el.dataset.manpackBound === "1") return;
      el.dataset.manpackBound = "1";

      el.addEventListener("click", function (e) {
        e.preventDefault();
        backdrop._openManpackModal();
      });
    });
  }

  function boot() {
    ensureModal();
    bindTriggers();
  }

  document.addEventListener("DOMContentLoaded", boot);
  document.addEventListener("pjax:end", boot);
})();




