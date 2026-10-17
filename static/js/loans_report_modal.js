// static/js/loans_report_modal.js
console.log("✅ loans_report_modal.js загружен");

(function() {
    'use strict';

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

    function injectStylesOnce() {
        if (document.getElementById("jmLoansReportStyles")) return;

        const st = document.createElement("style");
        st.id = "jmLoansReportStyles";
        st.textContent = `
            .jm-loans-backdrop {
                position: fixed;
                inset: 0;
                background: rgba(17, 24, 39, 0.45);
                z-index: 20000;
                display: none;
                align-items: center;
                justify-content: center;
                padding: 24px;
            }

            .jm-loans-backdrop.is-open {
                display: flex;
            }

            .jm-loans-modal {
                width: 100%;
                max-width: 460px;
                background: #ffffff;
                border: 1px solid #d1d5db;
                box-shadow: 0 20px 50px rgba(17, 24, 39, 0.18);
                padding: 20px;
            }

            .jm-loans-title {
                margin: 0 0 8px 0;
                font-size: 18px;
                font-weight: 700;
                color: #111827;
            }

            .jm-loans-subtitle {
                margin: 0 0 16px 0;
                font-size: 13px;
                color: #6b7280;
                line-height: 1.45;
            }

            .jm-loans-label {
                display: block;
                margin-bottom: 8px;
                font-size: 13px;
                font-weight: 600;
                color: #111827;
            }

            .jm-loans-input {
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

            .jm-loans-input:focus {
                border-color: #059669;
            }

            .jm-loans-quick {
                display: flex;
                gap: 8px;
                margin-top: 12px;
                margin-bottom: 18px;
                flex-wrap: wrap;
            }

            .jm-loans-quick-btn {
                border: 1px solid #d1d5db;
                background: #ffffff;
                color: #111827;
                height: 34px;
                padding: 0 12px;
                cursor: pointer;
                font-size: 13px;
            }

            .jm-loans-quick-btn:hover {
                background: #f9fafb;
            }

            .jm-loans-actions {
                display: flex;
                justify-content: flex-end;
                gap: 10px;
            }

            .jm-loans-btn {
                min-width: 110px;
                height: 38px;
                padding: 0 14px;
                border: 1px solid #d1d5db;
                background: #fff;
                cursor: pointer;
                font-size: 14px;
                font-weight: 600;
            }

            .jm-loans-btn:hover {
                background: #f9fafb;
            }

            .jm-loans-btn--primary {
                background: #059669;
                color: #ffffff;
                border-color: #059669;
            }

            .jm-loans-btn--primary:hover {
                background: #047857;
            }

            .jm-loans-error {
                margin-top: 10px;
                font-size: 12px;
                color: #b91c1c;
                display: none;
            }

            .jm-loans-error.is-visible {
                display: block;
            }
        `;
        document.head.appendChild(st);
    }

    function ensureModal() {
        injectStylesOnce();

        let backdrop = document.getElementById("jmLoansBackdrop");
        if (backdrop) return backdrop;

        backdrop = document.createElement("div");
        backdrop.className = "jm-loans-backdrop";
        backdrop.id = "jmLoansBackdrop";

        backdrop.innerHTML = `
            <div class="jm-loans-modal" role="dialog" aria-modal="true" aria-labelledby="jmLoansTitle">
                <h3 class="jm-loans-title" id="jmLoansTitle">📊 Отчёт по займам и кредитам</h3>
                <div class="jm-loans-subtitle">
                    Выберите дату для формирования отчёта
                </div>

                <label class="jm-loans-label" for="jmLoansDate">Дата отчёта</label>
                <input type="date" id="jmLoansDate" class="jm-loans-input" />

                <div class="jm-loans-quick">
                    <button type="button" class="jm-loans-quick-btn" id="jmLoansToday">
                        📅 Сегодня
                    </button>
                    <button type="button" class="jm-loans-quick-btn" id="jmLoansPrevMonthEnd">
                        📆 Конец прошлого месяца
                    </button>
                </div>

                <div class="jm-loans-error" id="jmLoansError">
                    Пожалуйста, выберите дату.
                </div>

                <div class="jm-loans-actions">
                    <button type="button" class="jm-loans-btn" id="jmLoansCancel">Отмена</button>
                    <button type="button" class="jm-loans-btn jm-loans-btn--primary" id="jmLoansDownload">Скачать</button>
                </div>
            </div>
        `;

        document.body.appendChild(backdrop);

        const dateInput = backdrop.querySelector("#jmLoansDate");
        const btnToday = backdrop.querySelector("#jmLoansToday");
        const btnPrevMonthEnd = backdrop.querySelector("#jmLoansPrevMonthEnd");
        const btnCancel = backdrop.querySelector("#jmLoansCancel");
        const btnDownload = backdrop.querySelector("#jmLoansDownload");
        const errorBox = backdrop.querySelector("#jmLoansError");

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

        // ПРОСТОЙ РЕДИРЕКТ - как в manpack!
        btnDownload.addEventListener("click", function () {
            const reportDate = dateInput.value;

            if (!reportDate) {
                errorBox.classList.add("is-visible");
                return;
            }

            errorBox.classList.remove("is-visible");

            const baseUrl = "/contracts/export/loans-report/";
            const url = `${baseUrl}?report_date=${encodeURIComponent(reportDate)}`;

            close();
            window.location.href = url;  // ПРОСТО РЕДИРЕКТ!
        });

        backdrop._openLoansModal = open;
        backdrop._closeLoansModal = close;

        return backdrop;
    }

    function bindTriggers() {
        const backdrop = ensureModal();
        const triggers = document.querySelectorAll("#loans-report-btn");

        triggers.forEach((el) => {
            if (el.dataset.loansBound === "1") return;
            el.dataset.loansBound = "1";

            el.addEventListener("click", function (e) {
                e.preventDefault();
                backdrop._openLoansModal();
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