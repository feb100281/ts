# gear/app/daily_sales/daily_brief/presentation/styles.py
CSS = r'''
@page {
    size: A4 portrait;
   margin: 0 0 9mm 0;

    @bottom-center {
        content: "ТРЕНДСЕТТЕР · Коммерческий обзор · " counter(page);
        font-size: 7px;
        color: #6B7280;
        margin-bottom: 4mm;
    }
}

* {
    box-sizing: border-box;
}

html,
body {
    margin: 0;
    padding: 0;

    color: #14213D;
    background: #FFFDF7;

    font-family: Arial, sans-serif;
    font-size: 9px;
    line-height: 1.38;
}

.page {
    position: relative;

    width: 210mm;
   min-height: 288mm;

    padding: 9mm 9mm 11mm;

    background: #FFFDF7;

    page-break-after: always;
}

.page:last-child {
    page-break-after: auto;
}
.masthead{border-top:6px solid #14213D;border-bottom:2px solid #14213D;padding:8px 0 7px;margin-bottom:8px;display:flex;justify-content:space-between;align-items:flex-end}.brandline{color:#E85D75;font-weight:800;letter-spacing:1.5px;font-size:7px;text-transform:uppercase}h1{font-family:Georgia,serif;font-size:30px;line-height:.92;margin:3px 0 1px;letter-spacing:-1px}.mast-subtitle{margin-top: 5px; font-size:7px;letter-spacing:1.1px;text-transform:uppercase;color:#667085}.issue-meta{text-align:right;color:#667085;font-size:8px}
.lead{display:grid;grid-template-columns:42px 1fr;gap:9px;padding:9px 11px;background:#F4F0E6;border-left:5px solid #FFD84D;margin-bottom:8px;font-family:Georgia,serif;font-size:11px;line-height:1.5}.svg-icon,.svg-icon svg{display:inline-block;width:100%;height:100%}.columns{display:grid;grid-template-columns:1fr 1fr;gap:8px;align-items:start}.columns.compact{gap:10px}.full{grid-column:1/-1}.section{border-top:3px solid #14213D;padding-top:5px;margin-bottom:8px;break-inside:avoid}.section.soft{background:#F8F5ED;padding:7px;border-top-color:#E85D75}.section.feature{break-inside:auto}.section-head{display:flex;justify-content:space-between;gap:8px;align-items:flex-start;margin-bottom:5px}.kicker{color:#E85D75;font-size:7px;font-weight:800;letter-spacing:1.15px;text-transform:uppercase}h2{font-family:Georgia,serif;font-size:17px;line-height:1.05;margin:2px 0}.section-subtitle{color:#667085;font-size:7.5px}
.lead-text {
    text-align: justify;
    hyphens: auto;
    line-height: 1.45;
}

.lead-text::first-letter {
    font-size: 22px;
    font-weight: bold;
    color: #E85D75;
}


.metric-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:5px;  margin-bottom: 8px;}.metric-grid.four{grid-template-columns:repeat(4,1fr)}.metric{border:1px solid #D7DCE2;background: #FFFDF7;padding:6px;min-height:68px}.metric.accent{background:#FFF5F7;border-color:#F3B7C3}.metric-top{display:flex;justify-content:space-between;align-items:center;gap:4px;color:#667085;font-size:7px;font-weight:700;text-transform:uppercase}.metric-value{font-family:Georgia,serif;font-size:16px;font-weight:700;margin:3px 0 1px;white-space:nowrap}.metric-note{color:#667085;font-size:7.5px}

.prose{margin-top:6px;white-space:normal;color:#354052;font-family:Georgia,serif;font-size:9.5px;line-height:1.55;text-align:justify;hyphens:auto}.prose.dropcap:first-letter{font-size:18px;color:#E85D75;font-weight:bold}.mini-title{margin:7px 0 3px;color:#667085;font-size:7px;font-weight:800;letter-spacing:.8px;text-transform:uppercase}
.bar-row{display:grid;grid-template-columns:92px 1fr 63px;gap:5px;align-items:center;margin:5px 0}.bar-label{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.bar-track{height:11px;background:#E9EDF1}.bar-fill{height:11px;background:#E85D75;opacity:.78}.bar-number{text-align:right;font-weight:700;font-size:7.5px}
/* ================================================================
   КАЛЕНДАРЬ ВЫРУЧКИ
   ================================================================ */

.heat-calendar {
    width: 100%;
    min-width: 0;
}


/* Заголовки колонок */

.heat-calendar-head,
.heat-calendar-grid {
    display: grid;

    grid-template-columns:
        repeat(7, minmax(0, 1fr))
        minmax(82px, 1.15fr);

    gap: 3px;
}

.heat-calendar-head {
    margin-bottom: 3px;

    color: #667085;
    font-size: 7px;
    line-height: 1;
    text-align: center;
}

.heat-calendar-head span {
    min-width: 0;
}

.heat-week-head {
    color: #14213D;
    font-weight: 800;
}


/* ================================================================
   ДНЕВНАЯ ЯЧЕЙКА
   ================================================================ */

.heat-cell {
    height: 39px;
    min-width: 0;
    overflow: hidden;

    padding: 4px 5px;

    border: 1px solid rgba(20, 33, 61, 0.10);

    display: flex;
    flex-direction: column;
    justify-content: space-between;

    color: #14213D;
}

.heat-date {
    display: block;

    font-size: 7.8px;
    line-height: 1;
    font-weight: 800;
    white-space: nowrap;
}

.heat-value {
    display: block;

    overflow: hidden;

    font-size: 5.7px;
    line-height: 1;
    font-weight: 500;
    white-space: nowrap;
    text-overflow: ellipsis;
}


/* ================================================================
   ЦВЕТОВАЯ ШКАЛА
   ================================================================ */

/* Минимальная выручка */

.heat-cell.heat-0 {
    background: #F0F7DD;
    border-color: #D9E8B9;
}

/* Низкая */

.heat-cell.heat-1 {
    background: #DDF1AE;
    border-color: #C9E392;
}

/* Ниже средней */

.heat-cell.heat-2 {
    background: #BEE77D;
    border-color: #A9D969;
}

/* Выше средней */

.heat-cell.heat-3 {
    background: #91D45E;
    border-color: #7DC64D;
}

/* Высокая */

.heat-cell.heat-4 {
    background: #63BC51;
    border-color: #51AB43;
}

/* Максимальная */

.heat-cell.heat-5 {
    background: #33995A;
    border-color: #27864B;

    color: #FFFFFF;
}

.heat-cell.heat-5 .heat-date,
.heat-cell.heat-5 .heat-value {
    color: #FFFFFF;
}


/* Пустая дата */

.heat-cell-empty {
    background: #F7F5EF;
    border-color: #E6E3DA;
}


/* ================================================================
   ИТОГ НЕДЕЛИ
   ================================================================ */

.heat-week-total {
    position: relative;

    height: 39px;
    min-width: 0;
    overflow: hidden;

    padding-left: 16px;

    background: #F1EEE6;
    border: 1px solid #E4E0D6;
    border-left: 0;

    display: flex;
    flex-direction: column;
    justify-content: center;
}

.heat-week-total::before {
    content: "";

    position: absolute;
    top: 0;
    bottom: 0;
    left: 0;

    width: 2px;

    background: #14213D;
}

.heat-week-total-label {
    color: #667085;

    font-size: 5.5px;
    line-height: 1;
    font-weight: 800;
    letter-spacing: 0.35px;
    text-transform: uppercase;
}

.heat-week-total-value {
    margin-top: 2px;

    overflow: hidden;

    color: #14213D;
    font-family: Georgia, "Times New Roman", serif;
    font-size: 8.4px;
    line-height: 1;
    font-weight: 700;
    white-space: nowrap;
    text-overflow: ellipsis;
}

.heat-week-change {
    margin-top: 3px;

    font-size: 5.4px;
    line-height: 1;
    font-weight: 800;
    white-space: nowrap;
}

.heat-week-change.up {
    color: #12654F;
}

.heat-week-change.down {
    color: #C23D58;
}

.heat-week-change.neutral {
    color: #667085;
}


/* ================================================================
   ЛЕГЕНДА
   ================================================================ */

.heat-legend {
    margin-top: 4px;

    color: #7A8492;
    font-size: 6.3px;
    line-height: 1;
    text-align: right;
}
.spark{width:100%;height:95px;background:#FAFAF8;border:1px solid #E3E6EA}.spark polyline{fill:none;stroke-width:3;vector-effect:non-scaling-stroke}.spark-fact{stroke:#E85D75}.spark-plan{stroke:#14213D;stroke-dasharray:6 4}.spark-legend{display:flex;gap:12px;justify-content:flex-end;margin-top:3px;color:#667085;font-size:7px}.spark-legend i{display:inline-block;width:9px;height:3px;margin-right:3px;vertical-align:middle}.fact-dot{background:#E85D75}.plan-dot{background:#14213D}
.chart-image{display:block;width:100%;margin:7px 0 3px}.chart-image.wide{max-height:245px;object-fit:contain}.analysis-notes{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:7px}.analysis-notes>div{background:#F4F0E6;border-top:3px solid #FFD84D;padding:7px}.analysis-notes b{font-family:Georgia,serif;font-size:10px}.analysis-notes p{margin:3px 0 0;color:#4B5563;line-height:1.45;text-align:justify}.map-image{display:block;width:100%;max-height:410px;object-fit:contain;margin:4px 0 7px}.map-fallback{padding:18px;border:1px dashed #D7DCE2;color:#7A8492;text-align:center;margin:6px 0}
.progress-caption{display:flex;justify-content:space-between;margin-top:7px;font-size:7.5px}.progress{height:14px;background:#E9EDF1;position:relative;margin:4px 0}.progress>span{display:block;height:14px;background:#9BFF57}.progress-marker{position:absolute;width:2px;top:-4px;height:22px;background:#E85D75}.progress-key{display:flex;justify-content:space-between;color:#667085;font-size:6.8px}.progress-key i{display:inline-block;margin-right:4px;vertical-align:middle}.key-fill{width:10px;height:5px;background:#9BFF57}.key-line{width:2px;height:10px;background:#E85D75}
.recommendation{padding:6px 7px;border-left:4px solid #9BFF57;background:#F4FAEC;margin-bottom:5px}.recommendation.warning{border-color:#FFD84D;background:#FFF8DF}.recommendation.danger{border-color:#E85D75;background:#FFF1F4}.recommendation.info{border-color:#4E8BFF;background:#EFF5FF}.recommendation b{font-family:Georgia,serif;font-size:10px}.recommendation div{color:#667085;margin-top:2px}
.big-quote {
    padding: 9px 11px;
    border-left: 5px solid #E85D75;
    background: #FFF5F7;

    color: #14213D;
    font-family: Georgia, "Times New Roman", serif;
    font-size: 13px;
    line-height: 1.5;
}

.big-quote p {
    margin: 0;
    text-align: justify;
    hyphens: auto;
}

.big-quote p::first-letter {
    color: #E85D75;
    font-size: 22px;
    line-height: 1;
    font-weight: 700;
}

.story-section{background:#FFFCF5;padding:7px 8px 8px;border-top-color:#E85D75}
.story-divider{height:1px;background:#D7DCE2;margin:7px 0}
.page-columns>.section,.page-columns>div>.section{break-inside:avoid}
.analysis-top{margin-bottom:8px}
.editorial-aside{border-top:3px solid #FFD84D;background:#F4F0E6;padding:9px 10px;font-family:Georgia,serif;font-size:10px;line-height:1.58;text-align:justify;hyphens:auto}
.aside-label{font-family:Arial,sans-serif;color:#E85D75;font-size:7px;font-weight:800;letter-spacing:1.1px;margin-bottom:5px}


/* ==================================================================
   СОПОСТАВИМАЯ ДИНАМИКА
   ================================================================== */

.comparison-layout {
    margin-top: 6px;
}

.comparison-row {
    display: grid;
    width: 100%;
}

.comparison-row-daily {
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 7px;
}

.comparison-row-periods {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 7px;
    margin-top: 7px;
}

/* ==================================================================
   ОБЩАЯ КАРТОЧКА
   ================================================================== */

.comparison-card {
    min-width: 0;
    padding: 9px 10px 8px;

    border: 1px solid #D7DCE2;
    background: #FFFDF7;

    break-inside: avoid;
}

.comparison-day {
    border-top: 3px solid #14213D;
}

.comparison-period {
    border-top: 3px solid #E85D75;
    background: #FFF9FA;
}

.comparison-card-label {
    color: #667085;
    font-size: 7.2px;
    line-height: 1.22;
    font-weight: 800;
    text-transform: uppercase;
}

/* ==================================================================
   ПЕРВЫЙ РЯД — ДНЕВНЫЕ СРАВНЕНИЯ
   ================================================================== */

.comparison-day .comparison-card-label {
    min-height: 30px;
}

.comparison-day-main {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;

    margin-top: 9px;

    font-family: Georgia, "Times New Roman", serif;
    font-size: 27px;
    line-height: 1;
    font-weight: 700;
    white-space: nowrap;
}

.comparison-day-main.up {
    color: #12654F;
}

.comparison-day-main.down {
    color: #BD3D59;
}

.comparison-day-main.neutral {
    color: #667085;
}

.comparison-day-arrow {
    font-family: Arial, sans-serif;
    font-size: 13px;
    line-height: 1;
}

.comparison-day-percent {
    letter-spacing: -0.8px;
}

.comparison-day-delta {
    margin-top: 5px;
    padding-bottom: 8px;

    border-bottom: 1px solid #DFE3E8;

    font-size: 7.5px;
    line-height: 1.2;
    font-weight: 800;
    text-align: center;
}

.comparison-day-delta.up {
    color: #12654F;
}

.comparison-day-delta.down {
    color: #BD3D59;
}

.comparison-day-delta.neutral {
    color: #667085;
}

/* ==================================================================
   ВТОРОЙ РЯД — MTD / YTD
   ================================================================== */

.comparison-period .comparison-card-label {
    min-height: 17px;
}

.comparison-period-current {
    margin-top: 13px;

    color: #14213D;
    font-family: Georgia, "Times New Roman", serif;
    font-size: 20px;
    line-height: 1;
    font-weight: 800;
    letter-spacing: -0.3px;
    white-space: nowrap;
}

.comparison-period-dynamics {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;

    margin-top: 10px;
    padding-bottom: 8px;

    border-bottom: 1px solid #DFE3E8;
}

.comparison-period-change {
    display: inline-flex;
    align-items: center;
    gap: 5px;

    padding: 4px 8px;

    font-size: 9px;
    line-height: 1;
    font-weight: 800;
    white-space: nowrap;
}

.comparison-period-change.up {
    background: #E3F2ED;
    color: #12654F;
}

.comparison-period-change.down {
    background: #FBE7EC;
    color: #B53C56;
}

.comparison-period-change.neutral {
    background: #EEF0F3;
    color: #667085;
}

.comparison-period-arrow {
    font-size: 8px;
}

.comparison-period-delta {
    font-size: 8px;
    line-height: 1.2;
    font-weight: 800;
    text-align: right;
}

.comparison-period-delta.up {
    color: #12654F;
}

.comparison-period-delta.down {
    color: #B53C56;
}

.comparison-period-delta.neutral {
    color: #667085;
}

/* ==================================================================
   БАЗА СРАВНЕНИЯ
   ================================================================== */

.comparison-base {
    position: relative;
    margin-top: 7px;
    padding-right: 34px;
}

.comparison-base-caption {
    position: absolute;
    right: 0;
    top: 4px;

    color: #E85D75;
    font-size: 7px;
    line-height: 1;
    font-weight: 800;
    text-transform: uppercase;
}

.comparison-base-value {
    color: #14213D;
    font-family: Georgia, "Times New Roman", serif;
    font-size: 11.5px;
    line-height: 1;
    font-weight: 700;
    white-space: nowrap;
}

.comparison-base-period {
    margin-top: 2px;

    color: #7A8494;
    font-size: 6.7px;
    line-height: 1.1;
}

.comparison-period-base .comparison-base-value {
    font-size: 12px;
}

/* ==================================================================
   ПРОИСШЕСТВИЯ НА СКЛАДАХ
   ================================================================== */

.incidents-section {
    margin-top: 8px;
    margin-bottom: 10px;
    border-top: 3px solid #14213D;
    padding-top: 5px;
    break-inside: auto;
}

.incident-section-head {
    margin-bottom: 7px;
}

.incident-header-icon {
    width: 36px;
    height: 36px;
    flex: 0 0 36px;
}

.incident-method-note {
    display: grid;
    grid-template-columns: 20px 1fr;
    gap: 7px;
    align-items: start;

    padding: 7px 9px;
    margin-bottom: 7px;

    background: #F7F8F7;
    border-top: 1px solid #D7DCE2;
    border-bottom: 1px solid #D7DCE2;

    color: #4B5563;
    font-size: 8px;
    line-height: 1.45;
}

.incident-note-symbol {
    display: flex;
    align-items: center;
    justify-content: center;

    width: 16px;
    height: 16px;

    border: 1.5px solid #667085;
    border-radius: 50%;

    color: #667085;
    font-family: Georgia, serif;
    font-size: 10px;
    font-weight: 700;
    line-height: 1;
}

/* ------------------------------------------------------------------
   ОДНО СОБЫТИЕ
   ------------------------------------------------------------------ */

.incident-event {
    border: 1px solid #D7DCE2;
    background: #FFFDF7;
    break-inside: avoid;
    margin-bottom: 7px;
}

.incident-event-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;

    padding: 7px 9px;
    border-bottom: 1px solid #D7DCE2;
    background: #FFFCF8;
}

.incident-event-main {
    display: flex;
    align-items: center;
    gap: 8px;
    min-width: 0;
}

.incident-fire-icon {
    width: 31px;
    height: 31px;
    flex: 0 0 31px;
}

.incident-warehouse-name {
    font-family: Georgia, serif;
    color: #14213D;
    font-size: 13px;
    line-height: 1.05;
    font-weight: 700;
}

.incident-event-meta {
    margin-top: 2px;
    color: #667085;
    font-size: 8px;
}

.incident-event-meta span {
    padding: 0 3px;
    color: #AEB5BF;
}

.incident-status {
    flex: 0 0 auto;

    padding: 3px 7px;

    border: 1px solid #E85D75;
    border-radius: 10px;

    background: #FFF5F7;
    color: #C23D58;

    font-size: 7px;
    line-height: 1;
    font-weight: 800;
}

/* ------------------------------------------------------------------
   ДАТЫ И ОПИСАНИЕ
   ------------------------------------------------------------------ */

.incident-event-details {
    display: grid;
    grid-template-columns: 28% 72%;
    border-bottom: 1px solid #D7DCE2;
}

.incident-dates {
    padding: 7px 9px;
    border-right: 1px solid #D7DCE2;
    background: #FCFCFA;
}

.incident-date-row {
    display: grid;
    grid-template-columns: 23px 1fr;
    gap: 6px;
    align-items: center;
}

.incident-date-row + .incident-date-row {
    margin-top: 8px;
}

.incident-date-icon {
    width: 21px;
    height: 21px;
}

.incident-date-label {
    color: #14213D;
    font-size: 7.5px;
    font-weight: 800;
}

.incident-date-value {
    margin-top: 1px;
    color: #667085;
    font-size: 7.5px;
}

.incident-event-description {
    padding: 7px 10px;
    color: #354052;
    font-family: Georgia, serif;
    font-size: 8.5px;
    line-height: 1.45;
}

.incident-event-description p {
    margin: 0 0 3px;
}

.incident-event-description p:last-child {
    margin-bottom: 0;
}

/* ------------------------------------------------------------------
   ТРИ КОМПАКТНЫЕ МЕТРИКИ
   ------------------------------------------------------------------ */

.incident-kpi-row {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    padding: 7px 8px;
    border-bottom: 1px solid #D7DCE2;
}

.incident-kpi {
    display: grid;
    grid-template-columns: 34px 1fr;
    gap: 7px;
    align-items: center;

    min-width: 0;
    padding: 2px 9px;
}

.incident-kpi + .incident-kpi {
    border-left: 1px dashed #C8CED6;
}

.incident-kpi-icon {
    display: flex;
    align-items: center;
    justify-content: center;

    width: 31px;
    height: 31px;

    border-radius: 50%;
    background: #F4F0E6;
}

.incident-kpi.stock-tone .incident-kpi-icon {
    background: #EAF6E4;
}

.incident-kpi.accounting-tone .incident-kpi-icon {
    background: #FFF4D7;
}

.incident-kpi.management-tone .incident-kpi-icon {
    background: #FFF0F4;
}

.incident-kpi-label {
    color: #667085;
    font-size: 6.8px;
    line-height: 1.15;
    font-weight: 800;
    text-transform: uppercase;
}

.incident-kpi-value {
    margin-top: 2px;

    color: #14213D;
    font-family: Georgia, serif;
    font-size: 13px;
    line-height: 1;
    font-weight: 700;
    white-space: nowrap;
}

.incident-kpi-note {
    margin-top: 2px;
    color: #667085;
    font-size: 7px;
}

/* ------------------------------------------------------------------
   ПРИМЕЧАНИЯ
   ------------------------------------------------------------------ */

.incident-info-note {
    display: grid;
    grid-template-columns: 20px 1fr;
    gap: 7px;
    align-items: start;

    padding: 7px 9px;
    border-bottom: 1px solid #E2E5E9;

    background: #FAFAF8;
    color: #4B5563;

    font-size: 7.8px;
    line-height: 1.4;
}

.incident-risk-note {
    display: grid;
    grid-template-columns: 20px 1fr;
    gap: 7px;
    align-items: start;

    padding: 7px 9px;

    background: #FFFCF4;
    color: #5F5541;

    font-size: 7.8px;
    line-height: 1.4;
}

.incident-risk-symbol {
    display: flex;
    align-items: center;
    justify-content: center;

    width: 17px;
    height: 17px;

    border: 1.5px solid #C28A19;
    border-radius: 50%;

    background: #FFD84D;
    color: #14213D;

    font-size: 10px;
    font-weight: 900;
    line-height: 1;
}

.incident-no-stock {
    padding: 8px 10px;

    border-bottom: 1px solid #D7DCE2;
    background: #FAFAF8;

    color: #667085;
    font-size: 8px;
    line-height: 1.45;
}




/* ==================================================================
   ПЕРВАЯ СТРАНИЦА
   ================================================================== */

.first-page-analysis {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    gap: 7px;
    align-items: start;
    margin-top: 6px;
}

.first-page-analysis-left,
.first-page-analysis-right {
    min-width: 0;
}

.first-page-analysis-right {
    display: flex;
    flex-direction: column;
    gap: 5px;
}

.first-page-analysis-left > .section,
.first-page-analysis-right > .section {
    margin-bottom: 0;
}


/* ------------------------------------------------------------------
   Сравнения на первой странице
   ------------------------------------------------------------------ */

.first-page .comparison-layout {
    margin-top: 4px;
}

.first-page .comparison-row-daily {
    gap: 5px;
}

.first-page .comparison-row-periods {
    gap: 5px;
    margin-top: 5px;
}

.first-page .comparison-card {
    padding: 6px 7px 5px;
}

.first-page .comparison-day .comparison-card-label {
    min-height: 24px;
    font-size: 6.5px;
}

.first-page .comparison-day-main {
    margin-top: 6px;
    font-size: 23px;
}

.first-page .comparison-day-delta {
    margin-top: 3px;
    padding-bottom: 5px;
}

.first-page .comparison-period-current {
    margin-top: 8px;
    font-size: 17px;
}

.first-page .comparison-period-dynamics {
    margin-top: 7px;
    padding-bottom: 5px;
}

.first-page .comparison-base {
    margin-top: 5px;
}

.first-page .prose {
    margin-top: 4px;
    font-size: 8.2px;
    line-height: 1.38;
}


/* ------------------------------------------------------------------
   Тепловая карта
   ------------------------------------------------------------------ */

.first-page-heatmap-section {
    margin-bottom: 0;
}

.first-page .heat-weekdays,
.first-page .heat-grid {
    gap: 2px;
}

.first-page .heat-weekdays {
    margin-bottom: 2px;
}

.first-page .heat-cell {
    height: 31px;
    padding: 2px 3px;
}

.first-page .heat-cell b {
    font-size: 7px;
}

.first-page .heat-cell span {
    font-size: 5.2px;
}

.first-page .heat-legend {
    margin-top: 2px;
    font-size: 6px;
}


/* ------------------------------------------------------------------
   Компактный YTD-график
   ------------------------------------------------------------------ */

.ytd-compact-section {
    margin: 0;
    padding-top: 4px;
    break-inside: avoid;
    page-break-inside: avoid;
}

.ytd-compact-section .section-head {
    margin-bottom: 1px;
}

.ytd-compact-section h2 {
    font-size: 14px;
}

.ytd-compact-section .section-subtitle {
    font-size: 6.5px;
}

.ytd-bloomberg-chart {
    display: block;
    width: 100%;
    height: 112px;
    max-height: 112px;
    object-fit: contain;
    margin: 0;
}

.ytd-empty {
    min-height: 90px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #98A2B3;
    font-size: 7px;
}


/* ------------------------------------------------------------------
   Бренды и категории внизу первой страницы
   ------------------------------------------------------------------ */

.first-page-leaders {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    gap: 7px;
    align-items: stretch;
    margin-top: 6px;

    break-inside: avoid;
    page-break-inside: avoid;
}

.first-page-leader-column {
    min-width: 0;
}

.first-page-leader-section {
    height: 100%;
    margin-bottom: 0;
    padding-top: 4px;
}

.first-page-leader-section .section-head {
    margin-bottom: 3px;
}

.first-page-leader-section h2 {
    font-size: 15px;
}

.first-page-leader-section .section-subtitle {
    font-size: 6.5px;
}

.first-page-leader-section .bar-row {
    grid-template-columns: 82px 1fr 58px;
    gap: 4px;
    margin: 3px 0;
}

.first-page-leader-section .bar-track,
.first-page-leader-section .bar-fill {
    height: 9px;
}

.first-page-leader-section .bar-label,
.first-page-leader-section .bar-number {
    font-size: 6.8px;
}


/* ------------------------------------------------------------------
   Компактный подвал первой страницы
   ------------------------------------------------------------------ */

.first-page .footer-note {
    margin-top: 5px;
    padding-top: 4px;
}

/* ==================================================================
   ДЕТАЛЬНЫЙ РЕЙТИНГ БРЕНДОВ И КАТЕГОРИЙ
   ================================================================== */

.leader-chart {
    width: 100%;
}

.leader-row {
    min-width: 0;
    padding: 4px 0 5px;
    border-bottom: 1px solid #E2E6EA;
}

.leader-row:last-child {
    border-bottom: 0;
}

.leader-row-name {
    overflow: hidden;
    color: #14213D;
    font-size: 7.4px;
    line-height: 1.15;
    font-weight: 800;
    white-space: nowrap;
    text-overflow: ellipsis;
}

.leader-row-main {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 67px;
    gap: 5px;
    align-items: center;
    margin-top: 3px;
}

.leader-row-track {
    height: 9px;
    overflow: hidden;
    background: #E6EBF0;
}

.leader-row-fill {
    height: 100%;
    background: #E85D75;
    opacity: 0.78;
}

.leader-row-revenue {
    color: #14213D;
    font-size: 7px;
    line-height: 1;
    font-weight: 800;
    text-align: right;
    white-space: nowrap;
}

.leader-row-meta {
    display: flex;
    align-items: center;
    gap: 4px;
    margin-top: 3px;
    color: #667085;
    font-size: 6.4px;
    line-height: 1.15;
}

.leader-row-meta b {
    margin-left: 2px;
    color: #14213D;
    font-weight: 800;
}

.leader-row-meta-divider {
    color: #C0C6CE;
}

.first-page-leader-section .section-head {
    margin-bottom: 2px;
}

.first-page-leader-section h2 {
    font-size: 15px;
}

.first-page-leader-section .section-subtitle {
    font-size: 6.3px;
}



.first-page .heat-calendar-head,
.first-page .heat-calendar-grid {
    grid-template-columns:
        repeat(7, minmax(0, 1fr))
        72px;
    gap: 2px;
}

.first-page .heat-calendar-head {
    margin-bottom: 2px;
}

.first-page .heat-cell,
.first-page .heat-week-total {
    height: 31px;
}

.first-page .heat-cell {
    padding: 2px 3px;
}

.first-page .heat-cell b {
    font-size: 7px;
}

.first-page .heat-cell span {
    font-size: 5.2px;
}

.first-page .heat-week-total {
    padding: 2px 4px;
}

.first-page .heat-week-total > b {
    font-size: 7px;
}

.first-page .heat-week-label,
.first-page .heat-week-change {
    font-size: 5px;
}

'''
