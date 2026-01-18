// document.addEventListener("click", function (event) {
//     // ищем клик по шапке карточки оценки или по кнопке-стрелочке
//     const header = event.target.closest(".valuation-inline__header");
//     if (!header) {
//         return;
//     }

//     const box = header.closest(".valuation-inline");
//     if (!box) {
//         return;
//     }

//     // переключаем состояние
//     if (box.classList.contains("is-collapsed")) {
//         box.classList.remove("is-collapsed");
//         box.classList.add("is-open");
//     } else {
//         box.classList.add("is-collapsed");
//         box.classList.remove("is-open");
//     }
// });



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
  // value: "2025-12-21" | ISO string | timestamp
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
    "Объекты Недвижимости": "fa-solid fa-building",
    "Корзина Помещений": "fa-solid fa-basket-shopping",
  };

  function enhanceTopMenu() {
    const links = document.querySelectorAll(".main-header .navbar-nav .nav-link");

    links.forEach((a) => {
      const rawText = (a.textContent || "").replace(/\s+/g, " ").trim();
      if (!rawText) return;

      // уже обработан — не трогаем
      if (a.classList.contains("jm-toplink")) return;

      const iconClass = ICONS[rawText];
      if (!iconClass) return;

      a.classList.add("jm-toplink");

      // убираем текст
      a.textContent = "";

      // вставляем иконку
      const ico = document.createElement("span");
      ico.className = "jm-ico";
      ico.innerHTML = `<i class="${iconClass}" aria-hidden="true"></i>`;
      a.appendChild(ico);

      // нативный tooltip (без Popper)
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
// 3) Navbar "Сегодня": dropdown без Bootstrap/Popper
//    + список контрагентов без отметки ФНС
//    + договоры: сегодня / 1–7 / 8–30
//    + улучшенный профессиональный визуал (секции/разделители/бейджи/анимация)
// -------------------------------------------------
(function () {
  function getNavbarUl() {
    return document.querySelector(".main-header .navbar-nav");
  }

  function injectTodayStylesOnce() {
    if (document.getElementById("jmTodayStyles")) return;

    const st = document.createElement("style");
    st.id = "jmTodayStyles";
    st.textContent = `
/* -----------------------------
   Today dropdown (business / monochrome)
----------------------------- */

:root{
  --jm-fg: #111827;        /* slate-900 */
  --jm-muted: #6b7280;     /* gray-500 */
  --jm-border: #e5e7eb;    /* gray-200 */
  --jm-bg: #ffffff;        /* white */
  --jm-bg2: #f9fafb;       /* gray-50 */
  --jm-shadow: 0 18px 42px rgba(17,24,39,.12);
}

.jm-today-wrap{ position: relative; }

/* button */
.jm-today-btn{
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  transition: background .12s ease, transform .08s ease;
}
.jm-today-btn:hover{
  background: rgba(17,24,39,.04);
  transform: translateY(-1px);
}

.jm-today-badge{
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
  background: #ef4444;   /* red-500 */
  color: #fff;
  box-shadow: 0 10px 20px rgba(17,24,39,.18);
}

/* menu container */
.jm-today-menu{
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 8px;
  width: 360px;
  z-index: 9999;

  background: var(--jm-bg);
  border: 1px solid var(--jm-border);
  border-radius: 12px;
  box-shadow: var(--jm-shadow);

  /* compact, not full height */
  max-height: min(520px, 70vh);
  overflow: auto;

  transform-origin: top right;
  transform: translateY(6px);
  opacity: 0;
  pointer-events: none;
  transition: opacity .12s ease, transform .12s ease;
}
.jm-today-menu.is-open{
  transform: translateY(0);
  opacity: 1;
  pointer-events: auto;
}

/* header */
.jm-today-menu__head{
  padding: 12px 12px 10px 12px;
  border-bottom: 1px solid var(--jm-border);
  background: var(--jm-bg);
  position: sticky;
  top: 0;
  z-index: 2;
}
.jm-today-menu__title{
  font-size: 14px;
  font-weight: 900;
  color: var(--jm-fg);
  line-height: 1.1;
}
.jm-today-menu__date{
  margin-top: 3px;
  font-size: 12px;
  color: var(--jm-muted);
}

/* sections */
.jm-today-section{
  padding: 10px 12px 6px 12px;
}
.jm-today-section__title{
  font-size: 11px;
  font-weight: 900;
  letter-spacing: .08em;
  text-transform: uppercase;
  color: var(--jm-muted);
}
.jm-today-section__hint{
  margin-top: 2px;
  font-size: 11px;
  color: var(--jm-muted);
}

/* divider */
.jm-today-divider{
  height: 1px;
  margin: 6px 12px;
  background: var(--jm-border);
}

/* items = strict rows */
.jm-today-item{
  display:flex;
  align-items:center;
  gap: 10px;
  margin: 2px 8px;
  padding: 9px 10px;
  border-radius: 10px;
  text-decoration:none;

  color: var(--jm-fg);
  background: var(--jm-bg);
  border: 1px solid transparent;

  transition: background .12s ease, border-color .12s ease, transform .08s ease;
}
.jm-today-item:hover{
  background: var(--jm-bg2);
  border-color: var(--jm-border);
  transform: translateY(-1px);
}

/* dot: neutral (no kids colors) */
.jm-dot{
  width: 8px;
  height: 8px;
  border-radius: 6px;
  flex: 0 0 auto;
  background: #9ca3af;           /* gray-400 */
  box-shadow: 0 0 0 3px rgba(17,24,39,.05);
}
.jm-dot-purple{ background: #6b7280; } /* unify */
.jm-dot-amber{ background: #6b7280; }
.jm-dot-blue{ background: #6b7280; }

/* label + sub */
.jm-today-item__label{
  flex: 1 1 auto;
  min-width: 0;
  display:flex;
  flex-direction:column;
  gap: 2px;
  font-size: 13px;
  font-weight: 800;
  line-height: 1.15;
}
.jm-today-item__sub{
  font-size: 11px;
  font-weight: 650;
  color: var(--jm-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* count badge: business */
.jm-today-item__count{
  flex: 0 0 auto;
  display:inline-flex;
  align-items:center;
  justify-content:center;
  min-width: 28px;
  height: 22px;
  padding: 0 8px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 900;
  border: 1px solid var(--jm-border);
  background: #fff;
  color: var(--jm-fg);
}

/* tones only for contract counts (subtle, not childish) */
.jm-today-item[data-tone="danger"] .jm-today-item__count{
  border-color: rgba(185,28,28,.25);
  background: rgba(185,28,28,.06);
  color: #991b1b;
}
.jm-today-item[data-tone="warn"] .jm-today-item__count{
  border-color: rgba(180,83,9,.25);
  background: rgba(180,83,9,.06);
  color: #b45309;
}
.jm-today-item[data-tone="info"] .jm-today-item__count{
  border-color: rgba(29,78,216,.20);
  background: rgba(29,78,216,.05);
  color: #1d4ed8;
}

/* focus-visible */
.jm-today-btn:focus-visible,
.jm-today-item:focus-visible,
.jm-checko-row:focus-visible{
  outline: 2px solid rgba(17,24,39,.25);
  outline-offset: 2px;
}

/* ---- checko list inside (strict rows) ---- */
.jm-checko-wrap{ padding: 4px 0 6px 0; }

.jm-checko-row{
  display:flex;
  align-items:center;
  gap:10px;
  padding: 9px 10px;
  border-radius: 10px;
  text-decoration:none;
  margin: 2px 8px;

  background: #fff;
  border: 1px solid transparent;

  transition: background .12s ease, border-color .12s ease, transform .08s ease;
}
.jm-checko-row:hover{
  background: var(--jm-bg2);
  border-color: var(--jm-border);
  transform: translateY(-1px);
}

.jm-checko-inn{
  flex: 0 0 auto;
  font-size: 11px;
  padding: 3px 8px;
  border-radius: 6px;
  border: 1px solid var(--jm-border);
  background: #fff;
  color: var(--jm-fg);
  font-weight: 900;
  white-space: nowrap;
}
.jm-checko-name{
  flex: 1 1 auto;
  font-size: 13px;
  color: var(--jm-fg);
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-weight: 850;
}
.jm-checko-go{
  opacity: .5;
  color: var(--jm-muted);
}

/* footer */
.jm-checko-foot{
  margin: 8px 12px 10px 12px;
  padding-top: 8px;
  border-top: 1px solid var(--jm-border);
  display:flex;
  align-items:flex-start;
  justify-content: space-between;
  gap: 10px;
}
.jm-checko-hint{
  font-size: 11px;
  color: var(--jm-muted);
  line-height: 1.2;
}
.jm-checko-all{
  font-size: 11px;
  text-decoration:none;
  font-weight: 900;
  white-space: nowrap;
  color: var(--jm-fg);
}
.jm-checko-all:hover{ text-decoration: underline; }

/* optional: if low height - hide subtext */
@media (max-height: 760px){
  .jm-today-item__sub{ display:none; }
}

`;
    document.head.appendChild(st);
  }

  function ensureTodayUI() {
    const nav = getNavbarUl();
    if (!nav) return;

    if (document.getElementById("jmTodayBtn")) return;

    injectTodayStylesOnce();

    const li = document.createElement("li");
    li.className = "nav-item jm-today-wrap";

    li.innerHTML = `
      <a href="#" class="nav-link jm-today-btn" id="jmTodayBtn" title="Сегодня">
        <span class="jm-ico"><i class="fa-solid fa-bell" aria-hidden="true"></i></span>
        <span class="jm-today-badge" style="display:none;">0</span>
      </a>

      <div class="jm-today-menu" id="jmTodayMenu" aria-hidden="true">
        <div class="jm-today-menu__head">
          <div class="jm-today-menu__title">Сегодня</div>
          <div class="jm-today-menu__date" id="jmTodayDate"></div>
        </div>

        <div class="jm-today-section">
          <div class="jm-today-section__title">Контрагенты</div>
        </div>

        <a class="jm-today-item" id="jmTodayChecko" href="#">
          <span class="jm-dot jm-dot-purple"></span>
          <span class="jm-today-item__label">
            Контрагенты без отметки ФНС
            <span class="jm-today-item__sub">Нужно открыть карточку и заполнить по ИНН</span>
          </span>
          <span class="jm-today-item__count" data-key="stale_checko">0</span>
        </a>

        <div class="jm-today-sublist" id="jmTodayCheckoList" style="display:none;"></div>

        <div class="jm-today-divider"></div>

        <div class="jm-today-section">
          <div class="jm-today-section__title">Календарь</div>
        </div>

        <a class="jm-today-item" id="jmTodayCalendar" href="#">
          <span class="jm-dot jm-dot-amber"></span>
          <span class="jm-today-item__label">
            Исключение в календаре
            <span class="jm-today-item__sub">Проверить исключение на текущую дату</span>
          </span>
          <span class="jm-today-item__count" data-key="calendar_today">0</span>
        </a>

        <div class="jm-today-divider"></div>

        <div class="jm-today-section">
          <div class="jm-today-section__title">Договоры</div>
          <div class="jm-today-section__hint">Истекают в ближайшее время</div>
        </div>

        <a class="jm-today-item" data-tone="danger" id="jmLeaseToday" href="#">
          <span class="jm-dot jm-dot-blue"></span>
          <span class="jm-today-item__label">
            Договоры: сегодня
            <span class="jm-today-item__sub">Критично — подготовить продление / оффер</span>
          </span>
          <span class="jm-today-item__count" data-key="leases_today">0</span>
        </a>

        <a class="jm-today-item" data-tone="warn" id="jmLease1_7" href="#">
          <span class="jm-dot jm-dot-blue"></span>
          <span class="jm-today-item__label">
            Договоры: 1–7 дней
            <span class="jm-today-item__sub">Высокий приоритет — связаться с арендатором</span>
          </span>
          <span class="jm-today-item__count" data-key="leases_1_7">0</span>
        </a>

        <a class="jm-today-item" data-tone="info" id="jmLease8_30" href="#">
          <span class="jm-dot jm-dot-blue"></span>
          <span class="jm-today-item__label">
            Договоры: 8–30 дней
            <span class="jm-today-item__sub">Планово — подготовить коммерческое предложение</span>
          </span>
          <span class="jm-today-item__count" data-key="leases_8_30">0</span>
        </a>
      </div>
    `;

    nav.appendChild(li);

    // статические ссылки
    li.querySelector("#jmTodayChecko").href =
      "/admin/counterparties/counterparty/?checko_updated_at__isnull=1";

    // calendar today (по браузеру)
    const d = new Date();
    const yyyy = d.getFullYear();
    const mm = String(d.getMonth() + 1).padStart(2, "0");
    const dd = String(d.getDate()).padStart(2, "0");
    const iso = `${yyyy}-${mm}-${dd}`;
    li.querySelector("#jmTodayCalendar").href =
      `/admin/macro/calendarexceptions/?date__exact=${iso}`;

    // договора — будут подставлены из API
    li.querySelector("#jmLeaseToday").href = "#";
    li.querySelector("#jmLease1_7").href = "#";
    li.querySelector("#jmLease8_30").href = "#";

    // открыть/закрыть меню
    const btn = li.querySelector("#jmTodayBtn");
    const menu = li.querySelector("#jmTodayMenu");

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

  // ---------- render: counterparties without FNS mark ----------
  function renderCheckoList(list, totalCount) {
    const box = document.getElementById("jmTodayCheckoList");
    if (!box) return;

    const items = Array.isArray(list) ? list : [];
    if (items.length === 0) {
      box.style.display = "none";
      box.innerHTML = "";
      return;
    }

    const maxShow = 6;
    const showItems = items.slice(0, maxShow);

    const rowsHtml = showItems
      .map((x) => {
        const name = escapeHtml(x?.name || "—");
        const inn = escapeHtml(shortInn(x?.tax_id));
        const url = x?.admin_url || "#";

        return `
          <a class="jm-checko-row" href="${url}" title="Открыть карточку">
            <span class="jm-checko-inn">${inn}</span>
            <span class="jm-checko-name">${name}</span>
            <span class="jm-checko-go">↗</span>
          </a>
        `;
      })
      .join("");

    const allUrl =
      "/admin/counterparties/counterparty/?checko_updated_at__isnull=1";
    const moreCount = Math.max(0, num(totalCount) - showItems.length);

    const footerHtml = `
      <div class="jm-checko-foot">
        <span class="jm-checko-hint">Нажми строку → откроется карточка → «Заполнить по ИНН»</span>
        <a class="jm-checko-all" href="${allUrl}">
          Показать всех (${num(totalCount)})${moreCount > 0 ? ` • ещё ${moreCount}` : ""}
        </a>
      </div>
    `;

    box.innerHTML = `
      <div class="jm-checko-wrap">
        ${rowsHtml}
        ${footerHtml}
      </div>
    `;

    box.style.display = "block";
  }

  // ---------- refresh ----------
  async function refreshToday() {
    ensureTodayUI();

    const btn = document.getElementById("jmTodayBtn");
    const menu = document.getElementById("jmTodayMenu");
    if (!btn || !menu) return;

    const badge = btn.querySelector(".jm-today-badge");
    const dateEl = document.getElementById("jmTodayDate");
    const counts = menu.querySelectorAll(".jm-today-item__count");

    try {
      const resp = await fetch("/admin/today/", { credentials: "same-origin" });
      if (!resp.ok) return;

      const data = await resp.json();

      const total = num(data.total);
      const items = data.items || {};

      if (dateEl && data.date) dateEl.textContent = formatRuDate(data.date);

      // обновляем цифры по data-key
      counts.forEach((el) => {
        const key = el.getAttribute("data-key");
        el.textContent = String(num(items[key]));
      });

      // список контрагентов без отметки ФНС
      const staleList = data.lists?.stale_checko || [];
      renderCheckoList(staleList, items["stale_checko"]);

      // подставляем ссылки на договоры из API
      const leases = data.lists?.leases || {};
      const aToday = document.getElementById("jmLeaseToday");
      const a1_7 = document.getElementById("jmLease1_7");
      const a8_30 = document.getElementById("jmLease8_30");

      if (aToday && leases.today?.url) aToday.href = leases.today.url;
      if (a1_7 && leases.d1_7?.url) a1_7.href = leases.d1_7.url;
      if (a8_30 && leases.d8_30?.url) a8_30.href = leases.d8_30.url;

      // badge
      if (!badge) return;

      if (total > 0) {
        badge.textContent = String(total);
        badge.style.display = "inline-flex";
        btn.classList.add("jm-today-has");
        btn.setAttribute("title", `Сегодня: ${total}`);
      } else {
        badge.style.display = "none";
        btn.classList.remove("jm-today-has");
        btn.setAttribute("title", "Сегодня: ничего срочного");
      }
    } catch (e) {
      console.warn("today metrics error", e);
    }
  }

  function boot() {
    refreshToday();
    setInterval(refreshToday, 60 * 1000);
  }

  document.addEventListener("DOMContentLoaded", boot);
  document.addEventListener("pjax:end", boot);
})();

