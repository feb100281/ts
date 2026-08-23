// static/js/custom.js
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
    'Скачать остатки': "fa-solid fa-boxes", 
    'Контроль выручки': "fa-solid fa-chart-pie",
    
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

    const stocksLink = links.find((a) => getLinkLabel(a) === "Скачать остатки");
    const budgetAnalysisLink = links.find((a) => getLinkLabel(a) === "Контроль выручки");
    const budgetAnalysisLi = budgetAnalysisLink ? budgetAnalysisLink.closest(".nav-item") : null;
  



    if (!glLink && !arapLink && !contractsCheckLink && !manpackLink && !stocksLink && !budgetAnalysisLink) return;

    injectExportMenuStylesOnce();

    const glLi = glLink ? glLink.closest(".nav-item") : null;
    const arapLi = arapLink ? arapLink.closest(".nav-item") : null;
    const contractsCheckLi = contractsCheckLink ? contractsCheckLink.closest(".nav-item") : null;
    const manpackLi = manpackLink ? manpackLink.closest(".nav-item") : null;
    const stocksLi = stocksLink ? stocksLink.closest(".nav-item") : null;


    const insertBeforeNode = glLi || arapLi || contractsCheckLi || manpackLi || stocksLi || budgetAnalysisLi;

    [glLi, arapLi, contractsCheckLi, manpackLi, stocksLi, budgetAnalysisLi ].forEach((li) => {
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
      stocksLink
        ? {
            href: stocksLink.getAttribute("href") || "#",
            label: "Остатки на складах",
            icon: "fa-solid fa-boxes",
            className: "jm-stocks-trigger",
          }
        : null,
        
      budgetAnalysisLink ? {
        href: budgetAnalysisLink.getAttribute("href") || "#",
        label: "Контроль выручки",
        icon: "fa-solid fa-chart-pie",
        className: "jm-budget-analysis-trigger",
    } : null,

   

    
        
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
// 3) УВЕДОМЛЕНИЯ: ТОЛЬКО КУРСЫ ВАЛЮТ
// -------------------------------------------------
(function () {
  function getNavbarUl() {
    return document.querySelector(
      ".main-header .navbar-nav"
    );
  }

  // -------------------------------------------------
  // СТИЛИ КОЛОКОЛЬЧИКА
  // -------------------------------------------------

  function injectBellStylesOnce() {
    if (
      document.getElementById(
        "jmBellStyles"
      )
    ) {
      return;
    }

    const style = document.createElement(
      "style"
    );

    style.id = "jmBellStyles";

    style.textContent = `
      :root {
        --jm-fg: #111827;
        --jm-muted: #6b7280;
        --jm-border: #e5e7eb;
        --jm-bg: #ffffff;
        --jm-bg-hover: #f9fafb;
        --jm-shadow:
          0 18px 42px rgba(17, 24, 39, 0.12);
      }

      .jm-bell-wrap {
        position: relative;
      }

      .jm-bell-btn {
        position: relative;
      }

      .jm-bell-badge {
        position: absolute;
        top: 5px;
        right: 5px;

        display: inline-flex;
        align-items: center;
        justify-content: center;

        min-width: 18px;
        height: 18px;
        padding: 0 6px;

        border-radius: 6px;

        background: #ef4444;
        color: #ffffff;

        font-size: 11px;
        font-weight: 800;

        box-shadow:
          0 10px 20px rgba(17, 24, 39, 0.18);

        z-index: 5;
      }

      .jm-bell-menu {
        position: absolute;
        top: 100%;
        right: 0;

        width: 390px;
        margin-top: 8px;

        background: var(--jm-bg);
        border: 1px solid var(--jm-border);
        border-radius: 4px;

        box-shadow: var(--jm-shadow);

        opacity: 0;
        pointer-events: none;
        transform: translateY(6px);

        transition:
          opacity 0.12s ease,
          transform 0.12s ease;

        z-index: 9999;
      }

      .jm-bell-menu.is-open {
        opacity: 1;
        pointer-events: auto;
        transform: translateY(0);
      }

      .jm-bell-menu__head {
        padding: 13px 14px 11px;

        background: var(--jm-bg);
        border-bottom: 1px solid var(--jm-border);
      }

      .jm-bell-menu__title {
        color: var(--jm-fg);
        font-size: 14px;
        font-weight: 800;
        line-height: 1.2;
      }

      .jm-bell-menu__sub {
        margin-top: 4px;

        color: var(--jm-muted);
        font-size: 12px;
        line-height: 1.35;
      }

      .jm-bell-section {
        padding: 10px;
      }

      .jm-bell-section__title {
        padding: 3px 4px 8px;

        color: var(--jm-muted);
        font-size: 11px;
        font-weight: 800;
        letter-spacing: 0.06em;
        text-transform: uppercase;
      }

      .jm-bell-item {
        display: flex;
        align-items: center;
        gap: 11px;

        min-height: 58px;
        padding: 11px 12px;

        background: var(--jm-bg);
        border: 1px solid var(--jm-border);
        border-radius: 2px;

        color: var(--jm-fg);
        text-decoration: none;

        transition:
          background 0.12s ease,
          border-color 0.12s ease;
      }

      .jm-bell-item:hover {
        background: var(--jm-bg-hover);
        color: var(--jm-fg);
        text-decoration: none;
      }

      .jm-bell-item:focus-visible,
      .jm-bell-btn:focus-visible {
        outline: 2px solid rgba(17, 24, 39, 0.25);
        outline-offset: 2px;
      }

      .jm-bell-dot {
        width: 9px;
        height: 9px;

        border-radius: 50%;

        flex: 0 0 9px;
      }

      .jm-bell-dot--ok {
        background: #10b981;

        box-shadow:
          0 0 0 4px rgba(16, 185, 129, 0.10);
      }

      .jm-bell-dot--danger {
        background: #ef4444;

        box-shadow:
          0 0 0 4px rgba(239, 68, 68, 0.10);
      }

      .jm-bell-item__content {
        display: flex;
        flex: 1 1 auto;
        flex-direction: column;
        gap: 3px;

        min-width: 0;
      }

      .jm-bell-item__title {
        color: var(--jm-fg);
        font-size: 13px;
        font-weight: 750;
        line-height: 1.25;
      }

      .jm-bell-item__description {
        overflow: hidden;

        color: var(--jm-muted);
        font-size: 11px;
        font-weight: 500;
        line-height: 1.35;

        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .jm-bell-item__status {
        display: inline-flex;
        align-items: center;
        justify-content: center;

        min-width: 34px;
        height: 23px;
        padding: 0 8px;

        border: 1px solid var(--jm-border);
        border-radius: 6px;

        flex: 0 0 auto;

        font-size: 11px;
        font-weight: 800;
      }

      .jm-bell-item__status--ok {
        background: rgba(16, 185, 129, 0.08);
        border-color: rgba(16, 185, 129, 0.25);
        color: #047857;
      }

      .jm-bell-item__status--danger {
        background: rgba(185, 28, 28, 0.06);
        border-color: rgba(185, 28, 28, 0.25);
        color: #991b1b;
      }

      .jm-bell-empty {
        padding: 18px 14px;

        color: var(--jm-muted);
        font-size: 12px;
        text-align: center;
      }
    `;

    document.head.appendChild(
      style
    );
  }

  // -------------------------------------------------
  // СОЗДАЁМ КОЛОКОЛЬЧИК
  // -------------------------------------------------

  function ensureBellUI() {
    const nav = getNavbarUl();

    if (!nav) {
      return;
    }

    if (
      document.getElementById(
        "jmBellBtn"
      )
    ) {
      return;
    }

    injectBellStylesOnce();

    const li = document.createElement(
      "li"
    );

    li.className = (
      "nav-item jm-bell-wrap"
    );

    li.innerHTML = `
      <a
        href="#"
        class="nav-link jm-toplink jm-bell-btn"
        id="jmBellBtn"
        title="Курсы валют"
        aria-label="Курсы валют"
      >
        <span class="jm-ico">
          <i
            class="fa-solid fa-bell"
            aria-hidden="true"
          ></i>
        </span>

        <span
          class="jm-bell-badge"
          id="jmBellBadge"
          style="display: none;"
        >
          1
        </span>
      </a>

      <div
        class="jm-bell-menu"
        id="jmBellMenu"
        aria-hidden="true"
      >
        <div class="jm-bell-menu__head">
          <div class="jm-bell-menu__title">
            Курсы валют
          </div>

          <div
            class="jm-bell-menu__sub"
            id="jmBellSub"
          >
            Проверяем наличие курса на сегодня
          </div>
        </div>

        <div id="jmBellBody"></div>
      </div>
    `;

    nav.appendChild(li);

    const button = li.querySelector(
      "#jmBellBtn"
    );

    const menu = li.querySelector(
      "#jmBellMenu"
    );

    function closeMenu() {
      menu.classList.remove(
        "is-open"
      );

      menu.setAttribute(
        "aria-hidden",
        "true"
      );
    }

    function toggleMenu() {
      const isOpen = (
        menu.classList.contains(
          "is-open"
        )
      );

      if (isOpen) {
        closeMenu();
        return;
      }

      menu.classList.add(
        "is-open"
      );

      menu.setAttribute(
        "aria-hidden",
        "false"
      );
    }

    button.addEventListener(
      "click",
      function (event) {
        event.preventDefault();
        event.stopPropagation();

        toggleMenu();
      }
    );

    document.addEventListener(
      "click",
      function (event) {
        if (
          !li.contains(
            event.target
          )
        ) {
          closeMenu();
        }
      }
    );

    document.addEventListener(
      "keydown",
      function (event) {
        if (
          event.key === "Escape"
        ) {
          closeMenu();
        }
      }
    );
  }

  // -------------------------------------------------
  // СОЗДАЁМ СТРОКУ КУРСОВ ВАЛЮТ
  // -------------------------------------------------

  function createFxItem({
    href,
    status,
    title,
    description,
    badge,
  }) {
    const link = document.createElement(
      "a"
    );

    link.className = "jm-bell-item";
    link.href = href || "#";

    const isDanger = (
      status === "danger"
    );

    const dotClass = isDanger
      ? "jm-bell-dot jm-bell-dot--danger"
      : "jm-bell-dot jm-bell-dot--ok";

    const badgeClass = isDanger
      ? (
          "jm-bell-item__status "
          + "jm-bell-item__status--danger"
        )
      : (
          "jm-bell-item__status "
          + "jm-bell-item__status--ok"
        );

    link.innerHTML = `
      <span class="${dotClass}"></span>

      <span class="jm-bell-item__content">
        <span class="jm-bell-item__title">
          ${escapeHtml(title)}
        </span>

        <span class="jm-bell-item__description">
          ${escapeHtml(description)}
        </span>
      </span>

      <span class="${badgeClass}">
        ${escapeHtml(badge)}
      </span>
    `;

    return link;
  }

  // -------------------------------------------------
  // ПРОВЕРКА КУРСОВ ВАЛЮТ
  // -------------------------------------------------

  async function refreshBell() {
    ensureBellUI();

    const bellBadge = (
      document.getElementById(
        "jmBellBadge"
      )
    );

    const bellSub = (
      document.getElementById(
        "jmBellSub"
      )
    );

    const bellBody = (
      document.getElementById(
        "jmBellBody"
      )
    );

    if (!bellBody) {
      return;
    }

    bellBody.innerHTML = `
      <div class="jm-bell-empty">
        Проверяем курсы валют…
      </div>
    `;

    try {
      const response = await fetch(
        "/admin/fx-status/",
        {
          credentials: "same-origin",
        }
      );

      if (!response.ok) {
        throw new Error(
          `HTTP ${response.status}`
        );
      }

      const data = await response.json();

      const todayText = data.date
        ? formatRuDate(data.date)
        : "сегодня";

      const href = (
        data.admin_url
        || "/admin/macro/currencyrate/"
      );

      bellBody.innerHTML = "";

      const section = (
        document.createElement("div")
      );

      section.className = (
        "jm-bell-section"
      );

      const sectionTitle = (
        document.createElement("div")
      );

      sectionTitle.className = (
        "jm-bell-section__title"
      );

      sectionTitle.textContent = (
        "Макроэкономика"
      );

      section.appendChild(
        sectionTitle
      );

      if (data.has_fx_today) {
        section.appendChild(
          createFxItem({
            href: href,
            status: "ok",
            title: (
              "Курсы валют загружены"
            ),
            description: (
              `Дата: ${todayText}`
            ),
            badge: "OK",
          })
        );

        if (bellSub) {
          bellSub.textContent = (
            "Курс на сегодня загружен"
          );
        }

        if (bellBadge) {
          bellBadge.style.display = (
            "none"
          );
        }

      } else {
        section.appendChild(
          createFxItem({
            href: href,
            status: "danger",
            title: (
              "Нет курса валют на сегодня"
            ),
            description: (
              `Дата: ${todayText}. `
              + "Нужно обновить курс в базе"
            ),
            badge: "!",
          })
        );

        if (bellSub) {
          bellSub.textContent = (
            "Требуется обновление"
          );
        }

        if (bellBadge) {
          bellBadge.textContent = "1";
          bellBadge.style.display = (
            "inline-flex"
          );
        }
      }

      bellBody.appendChild(
        section
      );

    } catch (error) {
      console.warn(
        "fx status error",
        error
      );

      bellBody.innerHTML = "";

      const section = (
        document.createElement("div")
      );

      section.className = (
        "jm-bell-section"
      );

      section.appendChild(
        createFxItem({
          href: (
            "/admin/macro/currencyrate/"
          ),
          status: "danger",
          title: (
            "Не удалось проверить курсы"
          ),
          description: (
            "Сервис проверки временно недоступен"
          ),
          badge: "!",
        })
      );

      bellBody.appendChild(
        section
      );

      if (bellSub) {
        bellSub.textContent = (
          "Ошибка проверки"
        );
      }

      if (bellBadge) {
        bellBadge.textContent = "1";
        bellBadge.style.display = (
          "inline-flex"
        );
      }
    }
  }

  // -------------------------------------------------
  // ЗАПУСК
  // -------------------------------------------------

  function boot() {
    refreshBell();
  }

  document.addEventListener(
    "DOMContentLoaded",
    boot
  );

  document.addEventListener(
    "pjax:end",
    boot
  );

  // Обновляем статус один раз в минуту.
  setInterval(
    refreshBell,
    60 * 1000
  );
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






console.log("✅ stocks_export.js loaded");

(function () {
  function injectStocksStylesOnce() {
    if (document.getElementById("jmStocksStyles")) return;

    const st = document.createElement("style");
    st.id = "jmStocksStyles";
    st.textContent = `
      .jm-stocks-backdrop {
        position: fixed;
        inset: 0;
        background: rgba(17, 24, 39, 0.45);
        z-index: 20000;
        display: none;
        align-items: center;
        justify-content: center;
        padding: 24px;
      }

      .jm-stocks-backdrop.is-open {
        display: flex;
      }

      .jm-stocks-modal {
        width: 100%;
        max-width: 500px;
        background: #ffffff;
        border: 1px solid #d1d5db;
        box-shadow: 0 20px 50px rgba(17, 24, 39, 0.18);
        padding: 20px;
      }

      .jm-stocks-title {
        margin: 0 0 8px 0;
        font-size: 18px;
        font-weight: 700;
        color: #111827;
      }

      .jm-stocks-subtitle {
        margin: 0 0 16px 0;
        font-size: 13px;
        color: #6b7280;
        line-height: 1.45;
      }

      .jm-stocks-label {
        display: block;
        margin-bottom: 8px;
        font-size: 13px;
        font-weight: 600;
        color: #111827;
      }

      .jm-stocks-input {
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

      .jm-stocks-input:focus {
        border-color: #111827;
      }

      .jm-stocks-quick {
        display: flex;
        gap: 8px;
        margin-top: 12px;
        margin-bottom: 18px;
        flex-wrap: wrap;
      }

      .jm-stocks-quick-btn {
        border: 1px solid #d1d5db;
        background: #ffffff;
        color: #111827;
        height: 34px;
        padding: 0 12px;
        cursor: pointer;
        font-size: 13px;
      }

      .jm-stocks-quick-btn:hover {
        background: #f9fafb;
      }

      /* Три кнопки в один ряд */
      .jm-stocks-actions-row {
        display: flex;
        gap: 10px;
        margin-top: 20px;
      }

      .jm-stocks-btn {
        flex: 1;
        height: 38px;
        padding: 0 14px;
        border: 1px solid #d1d5db;
        background: #fff;
        cursor: pointer;
        font-size: 14px;
        font-weight: 600;
        white-space: nowrap;
      }

      .jm-stocks-btn:hover {
        background: #f9fafb;
      }

      .jm-stocks-btn--primary {
        background: #111827;
        color: #ffffff;
        border-color: #111827;
      }

      .jm-stocks-btn--primary:hover {
        background: #0b1220;
      }

      .jm-stocks-btn--map {
        background: #059669;
        color: #ffffff;
        border-color: #059669;
      }

      .jm-stocks-btn--map:hover {
        background: #047857;
      }

      .jm-stocks-error {
        margin-top: 10px;
        font-size: 12px;
        color: #b91c1c;
        display: none;
      }

      .jm-stocks-error.is-visible {
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

  function ensureStocksModal() {
    injectStocksStylesOnce();

    let backdrop = document.getElementById("jmStocksBackdrop");
    if (backdrop) return backdrop;

    backdrop = document.createElement("div");
    backdrop.className = "jm-stocks-backdrop";
    backdrop.id = "jmStocksBackdrop";

    backdrop.innerHTML = `
      <div class="jm-stocks-modal" role="dialog" aria-modal="true" aria-labelledby="jmStocksTitle">
        <h3 class="jm-stocks-title" id="jmStocksTitle">📊 Скачать остатки</h3>
        <div class="jm-stocks-subtitle">
          Выберите дату, на которую нужны остатки.
        </div>

        <label class="jm-stocks-label" for="jmStocksDate">Дата отчетности</label>
        <input type="date" id="jmStocksDate" class="jm-stocks-input" />

        <div class="jm-stocks-quick">
          <button type="button" class="jm-stocks-quick-btn" id="jmStocksToday">
            📅 Сегодня
          </button>
          <button type="button" class="jm-stocks-quick-btn" id="jmStocksPrevMonthEnd">
            📆 Конец прошлого месяца
          </button>
        </div>

        <div class="jm-stocks-error" id="jmStocksError">
          Пожалуйста, выберите дату.
        </div>

        <div class="jm-stocks-actions-row">
          <button type="button" class="jm-stocks-btn" id="jmStocksCancel">Отмена</button>
          <button type="button" class="jm-stocks-btn jm-stocks-btn--primary" id="jmStocksDownloadExcel">
            📎 Скачать Excel
          </button>
          <button type="button" class="jm-stocks-btn jm-stocks-btn--map" id="jmStocksDownloadMap">
            🗺️ Карта остатков
          </button>
        </div>
      </div>
    `;

    document.body.appendChild(backdrop);

    const dateInput = backdrop.querySelector("#jmStocksDate");
    const btnToday = backdrop.querySelector("#jmStocksToday");
    const btnPrevMonthEnd = backdrop.querySelector("#jmStocksPrevMonthEnd");
    const btnCancel = backdrop.querySelector("#jmStocksCancel");
    const btnDownloadExcel = backdrop.querySelector("#jmStocksDownloadExcel");
    const btnDownloadMap = backdrop.querySelector("#jmStocksDownloadMap");
    const errorBox = backdrop.querySelector("#jmStocksError");

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

    function getSelectedDate() {
      return dateInput.value;
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

    btnDownloadExcel.addEventListener("click", function () {
      const reportDate = getSelectedDate();

      if (!reportDate) {
        errorBox.classList.add("is-visible");
        return;
      }

      errorBox.classList.remove("is-visible");

      const baseUrl = "/admin/export/stocks/";
      const url = `${baseUrl}?report_date=${encodeURIComponent(reportDate)}`;

      close();
      window.location.href = url;
    });

    btnDownloadMap.addEventListener("click", function () {
      const reportDate = getSelectedDate();

      if (!reportDate) {
        errorBox.classList.add("is-visible");
        return;
      }

      errorBox.classList.remove("is-visible");

      const baseUrl = "/admin/export/stocks-map/";
      const url = `${baseUrl}?report_date=${encodeURIComponent(reportDate)}&format=png`;

      close();
      window.location.href = url;
    });

    backdrop._openStocksModal = open;
    backdrop._closeStocksModal = close;

    return backdrop;
  }

  function bindStocksTriggers() {
    const backdrop = ensureStocksModal();
    const triggers = document.querySelectorAll(".jm-stocks-trigger");

    triggers.forEach((el) => {
      if (el.dataset.stocksBound === "1") return;
      el.dataset.stocksBound = "1";

      el.addEventListener("click", function (e) {
        e.preventDefault();
        backdrop._openStocksModal();
      });
    });
  }

  function boot() {
    ensureStocksModal();
    bindStocksTriggers();
  }

  document.addEventListener("DOMContentLoaded", boot);
  document.addEventListener("pjax:end", boot);
})();








// =============================
// budget_analysis_export.js
// Контроль выручки (PDF отчет)
// =============================

(function () {
  function injectBudgetAnalysisStylesOnce() {
    if (document.getElementById("jmBudgetAnalysisStyles")) return;

    const st = document.createElement("style");
    st.id = "jmBudgetAnalysisStyles";
    st.textContent = `
      .jm-budget-analysis-backdrop {
        position: fixed;
        inset: 0;
        background: rgba(17, 24, 39, 0.45);
        z-index: 20000;
        display: none;
        align-items: center;
        justify-content: center;
        padding: 24px;
      }

      .jm-budget-analysis-backdrop.is-open {
        display: flex;
      }

      .jm-budget-analysis-modal {
        width: 100%;
        max-width: 520px;
        background: #ffffff;
        border: 1px solid #d1d5db;
        box-shadow: 0 20px 50px rgba(17, 24, 39, 0.18);
        padding: 24px;
      }

      .jm-budget-analysis-title {
        margin: 0 0 8px 0;
        font-size: 18px;
        font-weight: 700;
        color: #111827;
      }

      .jm-budget-analysis-subtitle {
        margin: 0 0 20px 0;
        font-size: 13px;
        color: #6b7280;
        line-height: 1.45;
      }

      .jm-budget-analysis-field {
        margin-bottom: 18px;
      }

      .jm-budget-analysis-label {
        display: block;
        margin-bottom: 8px;
        font-size: 13px;
        font-weight: 600;
        color: #111827;
      }

      .jm-budget-analysis-select,
      .jm-budget-analysis-input {
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

      .jm-budget-analysis-select:focus,
      .jm-budget-analysis-input:focus {
        border-color: #111827;
      }

      .jm-budget-analysis-quick {
        display: flex;
        gap: 8px;
        margin-top: 12px;
        flex-wrap: wrap;
      }

      .jm-budget-analysis-quick-btn {
        border: 1px solid #d1d5db;
        background: #ffffff;
        color: #111827;
        height: 34px;
        padding: 0 12px;
        cursor: pointer;
        font-size: 13px;
      }

      .jm-budget-analysis-quick-btn:hover {
        background: #f9fafb;
      }

      .jm-budget-analysis-actions {
        display: flex;
        justify-content: flex-end;
        gap: 10px;
        margin-top: 24px;
      }

      .jm-budget-analysis-btn {
        min-width: 110px;
        height: 38px;
        padding: 0 14px;
        border: 1px solid #d1d5db;
        background: #fff;
        cursor: pointer;
        font-size: 14px;
        font-weight: 600;
      }

      .jm-budget-analysis-btn:hover {
        background: #f9fafb;
      }

      .jm-budget-analysis-btn--primary {
        background: #111827;
        color: #ffffff;
        border-color: #111827;
      }

      .jm-budget-analysis-btn--primary:hover {
        background: #0b1220;
      }

      .jm-budget-analysis-error {
        margin-top: 10px;
        font-size: 12px;
        color: #b91c1c;
        display: none;
      }

      .jm-budget-analysis-error.is-visible {
        display: block;
      }

      .jm-budget-analysis-loading {
        margin-top: 10px;
        font-size: 12px;
        color: #6b7280;
        display: none;
        align-items: center;
        gap: 8px;
      }

      .jm-budget-analysis-loading.is-visible {
        display: flex;
      }

      .jm-budget-analysis-spinner {
        width: 16px;
        height: 16px;
        border: 2px solid #e5e7eb;
        border-top-color: #111827;
        border-radius: 50%;
        animation: jm-spin 0.6s linear infinite;
      }

      @keyframes jm-spin {
        to { transform: rotate(360deg); }
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

  function getCurrentYear() {
    return new Date().getFullYear();
  }

  // Загрузка списка бюджетов с сервера
  async function loadBudgets() {
    try {
      const response = await fetch("/admin/api/budgets/", {
        credentials: "same-origin",
        headers: {
          "X-Requested-With": "XMLHttpRequest"
        }
      });
      
      if (response.ok) {
        return await response.json();
      }
      return [];
    } catch (e) {
      console.warn("Failed to load budgets:", e);
      return [];
    }
  }

  // Найти бюджет по году и сценарию base
  function findDefaultBudget(budgets, targetYear) {
    return budgets.find(b => {
      if (!b.date_from) return false;
      const budgetYear = new Date(b.date_from).getFullYear();
      const isBaseScenario = b.revenue_param?.scenario === "base";
      return budgetYear === targetYear && isBaseScenario;
    });
  }

  function ensureModal() {
    injectBudgetAnalysisStylesOnce();

    let backdrop = document.getElementById("jmBudgetAnalysisBackdrop");
    if (backdrop) return backdrop;

    backdrop = document.createElement("div");
    backdrop.className = "jm-budget-analysis-backdrop";
    backdrop.id = "jmBudgetAnalysisBackdrop";

    backdrop.innerHTML = `
      <div class="jm-budget-analysis-modal" role="dialog" aria-modal="true" aria-labelledby="jmBudgetAnalysisTitle">
        <h3 class="jm-budget-analysis-title" id="jmBudgetAnalysisTitle">📊 Контроль выручки</h3>
        <div class="jm-budget-analysis-subtitle">
          Выберите версию бюджета и дату для анализа
        </div>

        <div class="jm-budget-analysis-field">
          <label class="jm-budget-analysis-label" for="jmBudgetSelect">
            Версия бюджета
          </label>
          <select id="jmBudgetSelect" class="jm-budget-analysis-select">
            <option value="">Загрузка...</option>
          </select>
        </div>

        <div class="jm-budget-analysis-field">
          <label class="jm-budget-analysis-label" for="jmAnalysisDate">
            Дата анализа
          </label>
          <input type="date" id="jmAnalysisDate" class="jm-budget-analysis-input" />
          <div class="jm-budget-analysis-quick">
            <button type="button" class="jm-budget-analysis-quick-btn" id="jmBudgetToday">
              📅 Сегодня
            </button>
            <button type="button" class="jm-budget-analysis-quick-btn" id="jmBudgetMonthStart">
              📆 Начало месяца
            </button>
            <button type="button" class="jm-budget-analysis-quick-btn" id="jmBudgetYearStart">
              🗓️ Начало года
            </button>
          </div>
        </div>

        <div class="jm-budget-analysis-loading" id="jmBudgetAnalysisLoading">
          <div class="jm-budget-analysis-spinner"></div>
          <span>Генерация отчета...</span>
        </div>

        <div class="jm-budget-analysis-error" id="jmBudgetAnalysisError">
          Пожалуйста, выберите версию бюджета и дату.
        </div>

        <div class="jm-budget-analysis-actions">
          <button type="button" class="jm-budget-analysis-btn" id="jmBudgetAnalysisCancel">Отмена</button>
          <button type="button"class="jm-budget-analysis-btn jm-budget-analysis-btn--primary" id="jmBudgetAnalysisDownload">
            📄 Скачать PDF
          </button>
        </div>
      </div>
    `;

    document.body.appendChild(backdrop);

    const budgetSelect = backdrop.querySelector("#jmBudgetSelect");
    const dateInput = backdrop.querySelector("#jmAnalysisDate");
    const btnToday = backdrop.querySelector("#jmBudgetToday");
    const btnMonthStart = backdrop.querySelector("#jmBudgetMonthStart");
    const btnYearStart = backdrop.querySelector("#jmBudgetYearStart");
    const btnCancel = backdrop.querySelector("#jmBudgetAnalysisCancel");
    const btnDownload = backdrop.querySelector("#jmBudgetAnalysisDownload");
    const errorBox = backdrop.querySelector("#jmBudgetAnalysisError");
    const loadingBox = backdrop.querySelector("#jmBudgetAnalysisLoading");

    let budgetsList = [];

    // Функции дат
    function getMonthStartYmd() {
      const d = new Date();
      d.setDate(1);
      return formatDateToYmd(d);
    }

    function getYearStartYmd() {
      const d = new Date();
      d.setMonth(0, 1);
      return formatDateToYmd(d);
    }

    // Заполнение селекта бюджетов
    async function populateBudgets() {
      budgetSelect.innerHTML = '<option value="">Загрузка...</option>';
      budgetsList = await loadBudgets();
      
      if (!budgetsList.length) {
        budgetSelect.innerHTML = '<option value="">Нет доступных бюджетов</option>';
        return;
      }

      const options = budgetsList.map(b => {
        const year = b.date_from ? new Date(b.date_from).getFullYear() : '—';
        const scenario = b.revenue_param?.scenario || '—';
        const label = `${b.number} (${year}) — ${scenario}`;
        return `<option value="${b.id}">${escapeHtml(label)}</option>`;
      }).join('');

      budgetSelect.innerHTML = options;

      // Установка бюджета по умолчанию
      const currentYear = getCurrentYear();
      const defaultBudget = findDefaultBudget(budgetsList, currentYear);
      
      if (defaultBudget) {
        budgetSelect.value = defaultBudget.id;
      }
    }

    function getSelectedBudget() {
      const budgetId = budgetSelect.value;
      return budgetsList.find(b => b.id == budgetId);
    }

    function getSelectedDate() {
      return dateInput.value;
    }

    async function open() {
      errorBox.classList.remove("is-visible");
      loadingBox.classList.remove("is-visible");
      
      if (!dateInput.value) {
        dateInput.value = getTodayYmd();
      }
      
      // Загружаем бюджеты если еще не загружены
      if (!budgetsList.length) {
        await populateBudgets();
      }
      
      backdrop.classList.add("is-open");
    }

    function close() {
      backdrop.classList.remove("is-open");
      errorBox.classList.remove("is-visible");
      loadingBox.classList.remove("is-visible");
    }

    async function downloadReport() {
      const budget = getSelectedBudget();
      const reportDate = getSelectedDate();

      if (!budget || !reportDate) {
        errorBox.classList.add("is-visible");
        return;
      }

      errorBox.classList.remove("is-visible");
      loadingBox.classList.add("is-visible");

      const url = `/admin/export/budget-analysis/?budget_id=${budget.id}&report_date=${encodeURIComponent(reportDate)}`;

      try {
        // Пока что просто редирект (позже будет PDF)
        window.location.href = url;
        close();
      } catch (err) {
        console.error("Download error:", err);
        errorBox.textContent = "Ошибка при генерации отчета";
        errorBox.classList.add("is-visible");
        loadingBox.classList.remove("is-visible");
      }
    }

    // Event listeners
    btnToday.addEventListener("click", () => {
      dateInput.value = getTodayYmd();
      errorBox.classList.remove("is-visible");
    });

    btnMonthStart.addEventListener("click", () => {
      dateInput.value = getMonthStartYmd();
      errorBox.classList.remove("is-visible");
    });

    btnYearStart.addEventListener("click", () => {
      dateInput.value = getYearStartYmd();
      errorBox.classList.remove("is-visible");
    });

    btnCancel.addEventListener("click", close);
    btnDownload.addEventListener("click", downloadReport);

    backdrop.addEventListener("click", (e) => {
      if (e.target === backdrop) close();
    });

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && backdrop.classList.contains("is-open")) {
        close();
      }
    });

    // Загружаем бюджеты при создании
    populateBudgets();

    backdrop._openBudgetAnalysisModal = open;
    backdrop._closeBudgetAnalysisModal = close;

    return backdrop;
  }

    function bindTriggers() {
    const backdrop = ensureModal();
    
    // Ищем только триггеры в выпадающем меню "Экспорт"
    const triggers = document.querySelectorAll(".jm-budget-analysis-trigger");
    
    triggers.forEach((el) => {
      if (el.dataset.budgetAnalysisBound === "1") return;
      el.dataset.budgetAnalysisBound = "1";
      
      el.addEventListener("click", function (e) {
        e.preventDefault();
        backdrop._openBudgetAnalysisModal();
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