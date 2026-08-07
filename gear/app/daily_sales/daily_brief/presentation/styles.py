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


/* ==================================================================
   ПЛАНОВЫЙ ГАЗЕТНЫЙ РАЗВОРОТ
   ================================================================== */

.plans-page {
    display: block;
}

.plans-newspaper-grid {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    gap: 9px;
    align-items: start;
}

.plans-newspaper-left,
.plans-newspaper-right {
    min-width: 0;
}

.plans-column {
    min-width: 0;
    padding-top: 5px;
}

.plans-month-column {
    border-top: 3px solid #14213D;
}

.plans-half-year-column {
    border-top: 3px solid #E85D75;
    background: #F8F5ED;
    padding: 5px 7px 7px;
}

.plans-column-head {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 7px;
    margin-bottom: 6px;
}

.plans-column-kicker,
.plans-small-kicker {
    color: #E85D75;
    font-size: 6.5px;
    line-height: 1;
    font-weight: 800;
    letter-spacing: 1px;
    text-transform: uppercase;
}

.plans-column-head h2,
.plans-prophet-head h2 {
    margin: 2px 0 0;
    color: #14213D;
    font-family: Georgia, "Times New Roman", serif;
    font-size: 17px;
    line-height: 1;
}

.plans-column-subtitle {
    margin-top: 3px;
    color: #667085;
    font-size: 6.7px;
}

.plans-column-icon {
    width: 29px;
    height: 29px;
    flex: 0 0 29px;
}


/* KPI */

.plans-metric-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 4px;
    margin-bottom: 6px;
}

.plans-metric {
    min-width: 0;
    min-height: 55px;
    padding: 5px 6px;
    border: 1px solid #D7DCE2;
    background: #FFFDF7;
}

.plans-metric.accent {
    border-color: #F1B9C4;
    background: #FFF5F7;
}

.plans-metric.positive {
    border-top: 2px solid #12654F;
}

.plans-metric.negative {
    border-top: 2px solid #E85D75;
}

.plans-metric-head {
    display: flex;
    justify-content: space-between;
    gap: 4px;
    color: #667085;
    font-size: 5.7px;
    font-weight: 800;
    text-transform: uppercase;
}

.plans-metric-icon {
    width: 19px;
    height: 19px;
    flex: 0 0 19px;
}

.plans-metric-value {
    margin-top: 4px;
    overflow: hidden;
    color: #14213D;
    font-family: Georgia, "Times New Roman", serif;
    font-size: 13.2px;
    line-height: 1;
    font-weight: 800;
    white-space: nowrap;
    text-overflow: ellipsis;
}

.plans-metric-note {
    margin-top: 3px;
    overflow: hidden;
    color: #667085;
    font-size: 5.7px;
    white-space: nowrap;
    text-overflow: ellipsis;
}


/* Графики */

.plans-chart-card {
    margin-bottom: 6px;
    padding: 5px;
    border: 1px solid #D7DCE2;
    background: #FFFDF7;
    break-inside: avoid;
}

.plans-chart-title {
    margin-bottom: 3px;
    color: #667085;
    font-size: 6px;
    font-weight: 800;
    text-transform: uppercase;
}

.plans-chart-image {
    display: block;
    width: 100%;
    height: auto;
}

.plans-chart-image.month-chart {
    max-height: 145px;
    object-fit: contain;
}

.plans-chart-image.monthly-chart {
    max-height: 145px;
    object-fit: contain;
}

.plans-chart-image.prophet-chart {
    max-height: 150px;
    object-fit: contain;
}

.plans-chart-empty {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 80px;
    padding: 8px;
    border: 1px dashed #D7DCE2;
    background: #F8F5ED;
    color: #667085;
    font-size: 6.5px;
    text-align: center;
}


/* Последние семь дней */

.plans-seven-days {
    margin-bottom: 6px;
    border-top: 2px solid #14213D;
    padding-top: 5px;
}

.plans-small-head {
    display: flex;
    justify-content: space-between;
    gap: 6px;
    align-items: flex-end;
    margin-bottom: 4px;
}

.plans-small-title {
    margin-top: 2px;
    color: #14213D;
    font-family: Georgia, "Times New Roman", serif;
    font-size: 10.5px;
    font-weight: 800;
}

.plans-seven-average {
    text-align: right;
}

.plans-seven-average span {
    display: block;
    color: #667085;
    font-size: 5.5px;
    text-transform: uppercase;
}

.plans-seven-average b {
    display: block;
    margin-top: 1px;
    color: #14213D;
    font-family: Georgia, serif;
    font-size: 9px;
}

.plans-seven-table,
.plans-prophet-table {
    width: 100%;
    border-collapse: collapse;
    table-layout: fixed;
}



.plans-seven-table th:first-child,
.plans-prophet-table th:first-child {
    text-align: left;
}


/* ================================================================
   ТАБЛИЦА — ПОСЛЕДНИЕ 7 ДНЕЙ
   ================================================================ */

.plans-seven-table th {
    padding: 4px 4px;
    background: #14213D;
    color: #FFFFFF;

    font-size: 6.2px;
    line-height: 1.15;

    text-align: right;
}

.plans-seven-table td {
    padding: 4px 4px;

    border-bottom: 1px solid #E1E4E8;

    color: #354052;
    font-size: 6.3px;
    line-height: 1.18;
}


/* ================================================================
   ТАБЛИЦА — PROPHET
   ================================================================ */

.plans-prophet-table th {
    padding: 5px 6px;
    background: #14213D;
    color: #FFFFFF;

    font-size: 6.4px;
    line-height: 1.15;

    text-align: right;
}

.plans-prophet-table td {
    padding: 5px 6px;

    border-bottom: 1px solid #E1E4E8;

    color: #354052;
    font-size: 6.6px;
    line-height: 1.2;
}


.plans-seven-table tbody tr:nth-child(even),
.plans-prophet-table tbody tr:nth-child(even) {
    background: #F8F5ED;
}

.plans-seven-table tfoot td {
    background: #FFF5F7;
    border-top: 2px solid #E85D75;
    color: #14213D;
    font-weight: 800;
}

.plans-seven-table .numeric,
.plans-prophet-table .numeric {
    text-align: right;
    white-space: nowrap;
}

.plans-seven-table .muted {
    color: #667085;
}

.plans-seven-table .positive,
.plans-prophet-table .positive {
    color: #12654F;
    font-weight: 800;
}

.plans-seven-table .negative,
.plans-prophet-table .negative {
    color: #B53C56;
    font-weight: 800;
}

.plans-prophet-table .forecast {
    color: #0F766E;
    font-weight: 700;
}


/* Редакционный текст */

.plans-editorial-copy {
    color: #354052;
    font-family: Georgia, "Times New Roman", serif;
    font-size: 7.1px;
    line-height: 1.47;
    text-align: justify;
    hyphens: auto;
}

.plans-editorial-copy.dropcap::first-letter {
    color: #E85D75;
    font-size: 17px;
    line-height: .8;
    font-weight: 800;
}

.half-copy {
    margin-top: 6px;
}


/* Полугодие */

.plans-half-top {
    display: grid;
    grid-template-columns: minmax(0, 1.2fr) minmax(0, .8fr);
    gap: 4px;
    align-items: center;
}

.plans-gauge-image {
    display: block;
    width: 100%;
    max-height: 119px;
    object-fit: contain;
}

.plans-half-stats > div {
    padding: 3px 0;
    border-bottom: 1px solid #D7DCE2;
}

.plans-half-stats > div:last-child {
    border-bottom: 0;
}

.plans-half-stats span {
    display: block;
    color: #667085;
    font-size: 5.2px;
    font-weight: 800;
    text-transform: uppercase;
}

.plans-half-stats b {
    display: block;
    margin-top: 1px;
    overflow: hidden;
    color: #14213D;
    font-family: Georgia, serif;
    font-size: 8.8px;
    white-space: nowrap;
    text-overflow: ellipsis;
}

.plans-progress-card {
    margin: 4px 0 6px;
    padding: 5px 6px;
    border: 1px solid #D7DCE2;
    background: transparent;
}

.plans-progress-item + .plans-progress-item {
    margin-top: 4px;
}

.plans-progress-item > div:first-child {
    display: flex;
    justify-content: space-between;
    margin-bottom: 2px;
    color: #667085;
    font-size: 5.6px;
}

.plans-progress-item b {
    color: #14213D;
}

.plans-progress-track {
    height: 6px;
    overflow: hidden;
    background: #EDF0F3;
}

.plans-progress-track span {
    display: block;
    height: 100%;
}

.plans-progress-track .execution {
    background: #9BFF57;
}

.plans-progress-track .calendar {
    background: #E85D75;
}

.plans-progress-result {
    margin-top: 4px;
    padding-top: 4px;
    border-top: 1px solid #E1E4E8;
    font-size: 5.6px;
    font-weight: 800;
}

.plans-progress-result.positive {
    color: #12654F;
}

.plans-progress-result.negative {
    color: #B53C56;
}

.plans-divider-title {
    display: flex;
    align-items: center;
    gap: 5px;
    margin: 7px 0 4px;
    color: #E85D75;
    font-size: 6px;
    font-weight: 800;
    letter-spacing: .85px;
}

.plans-divider-title::after {
    content: "";
    height: 1px;
    flex: 1;
    background: #E85D75;
    opacity: .45;
}


/* Prophet — нижняя газетная полоса */

.plans-prophet-section {
    margin-top: 8px;
    padding-top: 6px;
    border-top: 4px solid #14213D;
    break-inside: avoid;
}

.plans-prophet-head {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 8px;
    margin-bottom: 5px;
}

.plans-prophet-badge {
    padding: 3px 6px;
    background: #E3F2ED;
    border: 1px solid #A9CEC2;
    color: #0F766E;
    font-size: 6px;
    font-weight: 800;
    letter-spacing: .8px;
}

.plans-prophet-lead {
    display: grid;
    grid-template-columns: 27px 1fr;
    gap: 7px;
    margin-bottom: 5px;
    padding: 6px 7px;
    background: #F4F0E6;
    border-left: 4px solid #FFD84D;
    color: #354052;
    font-family: Georgia, serif;
    font-size: 7px;
    line-height: 1.42;
    text-align: justify;
}

.plans-prophet-symbol {
    color: #E85D75;
    font-family: Georgia, serif;
    font-size: 23px;
    line-height: 1;
    font-weight: 800;
}

.plans-prophet-kpis {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 4px;
    margin-bottom: 5px;
}

.plans-prophet-kpis > div {
    padding: 5px;
    border: 1px solid #D7DCE2;
    background: #FFFDF7;
}

.plans-prophet-kpis span {
    display: block;
    color: #667085;
    font-size: 5.2px;
    font-weight: 800;
    text-transform: uppercase;
}

.plans-prophet-kpis b {
    display: block;
    margin-top: 3px;
    overflow: hidden;
    color: #14213D;
    font-family: Georgia, serif;
    font-size: 9.3px;
    white-space: nowrap;
    text-overflow: ellipsis;
}

.plans-prophet-kpis .positive b {
    color: #12654F;
}

.plans-prophet-kpis .negative b {
    color: #B53C56;
}

.plans-prophet-conclusion {
    margin-bottom: 5px;
    padding: 5px 7px;
    font-family: Georgia, serif;
    font-size: 7.2px;
    line-height: 1.35;
}

.plans-prophet-conclusion.positive {
    border-left: 4px solid #12654F;
    background: #E8F3EE;
    color: #12654F;
}

.plans-prophet-conclusion.negative {
    border-left: 4px solid #E85D75;
    background: #FFF1F4;
    color: #B53C56;
}

.prophet-chart-card {
    margin-bottom: 5px;
}

.plans-method-note {
    margin-top: 6px;
    color: #667085;
    font-size: 6.2px;
    line-height: 1.4;
}

.plans-footer {
    margin-top: 5px;
}



.plans-chart-image {
    display: block;
    width: 100%;
    height: auto;
}

.plans-chart-image.month-chart {
    max-height: 145px;
    object-fit: contain;
}

.plans-chart-image.monthly-chart {
    max-height: 145px;
    object-fit: contain;
}

.plans-chart-image.prophet-chart {
    max-height: 150px;
    object-fit: contain;
}

.plans-gauge-image {
    display: block;
    width: 100%;
    max-height: 119px;
    object-fit: contain;
}



/* ================================================================
   ПОЛУГОДИЕ — ДОПОЛНИТЕЛЬНАЯ ТРАЕКТОРИЯ
   ================================================================ */

.plans-half-trajectory-card {
    margin-top: 5px;
    padding: 4px 6px 2px;

    border: 1px solid #D7DCE2;
    background: #FFFDF7;

    break-inside: avoid;
}

.half-trajectory-chart {
    width: 100%;
    height: 108px;
}

.half-trajectory-chart svg {
    display: block;
    width: 100%;
    height: 100%;
}


/* ================================================================
   PROPHET — БОЛЬШОЙ ГРАФИК
   ================================================================ */

.prophet-chart-card {
    margin-top: 6px;
    margin-bottom: 6px;

    padding: 6px 7px 4px;

    border: 1px solid #D7DCE2;
    background: #FFFDF7;
}

.prophet-chart {
    width: 100%;
    height: 205px;
}

.prophet-chart svg {
    display: block;
    width: 100%;
    height: 100%;
}

.plans-chart-title {
    margin-bottom: 2px;

    color: #667085;

    font-size: 6.4px;
    line-height: 1.1;
    font-weight: 800;

    letter-spacing: .35px;
    text-transform: uppercase;
}


/* ================================================================
   НЕМНОГО УПЛОТНЯЕМ ПРАВУЮ КОЛОНКУ
   ================================================================ */

.plans-half-year-column .plans-progress-card {
    margin-bottom: 5px;
}

.plans-half-year-column .half-copy {
    margin-top: 5px;
}



/* SVG внутри полугодового блока должен сливаться с фоном блока */

.plans-gauge-wrap,
.gauge-chart,
.gauge-chart svg {
    background: transparent;
}

.plans-half-trajectory-card {
    margin-top: 5px;
    padding: 4px 5px 2px;

    border: 1px solid #D7DCE2;
    background: transparent;

    break-inside: avoid;
}

.half-trajectory-chart,
.half-trajectory-chart svg {
    display: block;
    width: 100%;
    background: transparent;
}





/* ==================================================================
   ТОВАРНЫЙ РАЗВОРОТ — STOCKS PAGE
   ================================================================== */

.stocks-page {
    padding-top: 8mm;
}


/* ==================================================================
   ШАПКА СТРАНИЦЫ
   ================================================================== */

.stocks-page .masthead {
    margin-bottom: 6px;
}

.stocks-page .masthead h1 {
    font-size: 26px;
}


/* ==================================================================
   KPI — ВЕРХНЯЯ ПОЛОСА
   ================================================================== */

.stocks-kpi-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 5px;

    margin-bottom: 6px;
}

.stocks-kpi-grid .metric {
    position: relative;

    min-width: 0;
    min-height: 57px;

    padding: 6px 7px;

    border: 1px solid #DADDE3;
    border-top: 3px solid #14213D;

    background: #FFFDF7;
}

.stocks-kpi-grid .metric:nth-child(2) {
    border-top-color: #E85D75;
}

.stocks-kpi-grid .metric:nth-child(3) {
    border-top-color: #B7A2D8;
}

.stocks-kpi-grid .metric:nth-child(4) {
    border-top-color: #8067AB;
    background: #F8F5FB;
}

.stocks-kpi-grid .metric-top {
    color: #667085;

    font-size: 5.8px;
    line-height: 1.1;
    font-weight: 800;

    letter-spacing: .45px;
}

.stocks-kpi-grid .metric-top .svg-icon {
    width: 20px;
    height: 20px;
}

.stocks-kpi-grid .metric-value {
    margin-top: 4px;

    overflow: hidden;

    color: #14213D;

    font-family: Georgia, "Times New Roman", serif;
    font-size: 14px;
    line-height: 1;
    font-weight: 800;

    white-space: nowrap;
    text-overflow: ellipsis;
}

.stocks-kpi-grid .metric-note {
    margin-top: 3px;

    overflow: hidden;

    color: #667085;

    font-size: 6.1px;
    line-height: 1.15;

    white-space: nowrap;
    text-overflow: ellipsis;
}


/* ==================================================================
   АВТОМАТИЧЕСКИЙ АНАЛИТИЧЕСКИЙ ВЫВОД
   ================================================================== */

.stocks-analysis {
    position: relative;

    display: grid;
    grid-template-columns: 86px minmax(0, 1fr);
    gap: 10px;

    margin-bottom: 6px;
    padding: 7px 9px;

    border-top: 1px solid #DED8CC;
    border-bottom: 1px solid #DED8CC;
    border-left: 4px solid #E85D75;

    background: #F7F3EA;
}

.stocks-analysis-label {
    padding-top: 1px;

    color: #E85D75;

    font-size: 6.2px;
    line-height: 1.3;
    font-weight: 900;

    letter-spacing: 1px;
}

.stocks-analysis-text {
    color: #354052;

    font-family: Georgia, "Times New Roman", serif;
    font-size: 7.3px;
    line-height: 1.46;

    text-align: justify;
    hyphens: auto;
}

.stocks-analysis-text b {
    color: #14213D;
    font-weight: 800;
}


/* ==================================================================
   ОБЩИЕ ЗАГОЛОВКИ БЛОКОВ STOCKS
   ================================================================== */

.stocks-block-kicker {
    color: #E85D75;

    font-size: 5.8px;
    line-height: 1;
    font-weight: 900;

    letter-spacing: .9px;
}

.stocks-block-kicker.lilac {
    color: #8067AB;
}

.stocks-block-kicker.rose {
    color: #CC687D;
}

.stocks-block-title {
    margin-top: 2px;

    color: #14213D;

    font-family: Georgia, "Times New Roman", serif;
    font-size: 11px;
    line-height: 1.05;
    font-weight: 800;
}


/* ==================================================================
   КАРТА
   ================================================================== */

.stocks-map-wrap {
    margin-bottom: 6px;
    padding-top: 5px;

    border-top: 3px solid #14213D;
}

.stocks-map-head {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 8px;

    margin-bottom: 2px;
}

.stocks-map-caption {
    color: #7A8494;

    font-size: 5.7px;
    line-height: 1;

    text-align: right;
}

.stocks-map-block {
    width: 100%;
    height: 285px;

    overflow: hidden;

    background: #FFFDF7;
}

.stocks-map-image {
    display: block;

    width: 100%;
    height: 285px;

    object-fit: contain;
    object-position: center center;
}


/* ==================================================================
   РЕЙТИНГИ — ОБЩАЯ СЕТКА
   ================================================================== */

.stocks-ranking-grid {
    display: grid;
    grid-template-columns:
        minmax(0, 1fr)
        minmax(0, 1fr);

    gap: 9px;

    margin-bottom: 6px;

    align-items: start;
}

.stocks-ranking-grid-secondary {
    margin-top: 2px;
    padding-top: 6px;

    border-top: 1px solid #D7DCE2;
}

.stocks-ranking-card {
    min-width: 0;

    padding-top: 5px;

    border-top: 3px solid #14213D;
}

.stocks-ranking-card:nth-child(2) {
    border-top-color: #B7A2D8;
}

.stocks-ranking-grid-secondary
.stocks-ranking-card:first-child {
    border-top-color: #EAA1B0;
}

.stocks-ranking-grid-secondary
.stocks-ranking-card:nth-child(2) {
    border-top-color: #A993CB;
}

.stocks-ranking-head {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;

    gap: 5px;

    margin-bottom: 4px;
}

.stocks-ranking-unit {
    flex: 0 0 auto;

    padding-bottom: 1px;

    color: #98A2B3;

    font-size: 5.2px;
    line-height: 1;

    white-space: nowrap;
}


/* ==================================================================
   BAR CHART — ТОЛЬКО НА СТРАНИЦЕ ОСТАТКОВ
   ================================================================== */

.stocks-page .bar-row {
    display: grid;

    grid-template-columns:
        minmax(0, 102px)
        minmax(0, 1fr)
        85px;

    gap: 5px;

    align-items: center;

    min-width: 0;

    margin: 3px 0;
}

.stocks-page .bar-label {
    min-width: 0;

    overflow: hidden;

    color: #26344D;

    font-size: 6.7px;
    line-height: 1.05;
    font-weight: 700;

    white-space: nowrap;
    text-overflow: ellipsis;
}

.stocks-page .bar-track {
    position: relative;

    width: 100%;
    height: 9px;

    overflow: hidden;

    background: #E9EDF1;
}

.stocks-page .bar-fill {
    display: block;

    height: 9px;

    background: #E47B90;

    opacity: 1;
}


/* Регионы — коралл */

.stocks-page .bar-tone-coral .bar-fill {
    background: #E47B90;
}


/* Склады — нежно-сиреневый */

.stocks-page .bar-tone-lilac .bar-fill {
    background: #B8A2D8;
}


/* Категории — нежно-розовый */

.stocks-page .bar-tone-rose .bar-fill {
    background: #E9A6B3;
}


/* Значение справа */

.stocks-page .bar-number {
    display: flex;
    align-items: baseline;
    justify-content: flex-end;

    gap: 4px;

    min-width: 0;

    color: #14213D;

    font-size: 6.2px;
    line-height: 1;
    font-weight: 800;

    text-align: right;

    white-space: nowrap;
}


/* Процент */

.stocks-page .bar-share {
    color: #87909E;

    font-size: 5.6px;
    line-height: 1;

    font-weight: 700;
}


/* ==================================================================
   ВТОРОЙ РЯД — КАТЕГОРИИ / БРЕНДЫ
   ================================================================== */

.stocks-ranking-grid-secondary
.bar-row {
    grid-template-columns:
        minmax(0, 112px)
        minmax(0, 1fr)
        80px;
}

.stocks-ranking-grid-secondary
.bar-label {
    font-size: 6.4px;
}

.stocks-ranking-grid-secondary
.bar-track,
.stocks-ranking-grid-secondary
.bar-fill {
    height: 8px;
}


/* ==================================================================
   СТОИМОСТНАЯ ОЦЕНКА
   ================================================================== */

.stocks-cost-section {
    margin-top: 5px;
    padding-top: 5px;

    border-top: 3px solid #14213D;
}

.stocks-cost-head {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;

    gap: 8px;

    margin-bottom: 4px;
}

.stocks-cost-head-note {
    padding-bottom: 1px;

    color: #7A8494;

    font-size: 5.5px;
    line-height: 1;
}

.stocks-cost-strip {
    display: grid;

    grid-template-columns:
        minmax(0, 1fr)
        minmax(0, 1fr)
        minmax(0, .85fr);

    gap: 5px;
}

.stocks-cost-card {
    position: relative;

    min-width: 0;
    min-height: 51px;

    padding: 6px 7px;

    border: 1px solid #D9DDE3;

    background: #FFFDF7;
}

.stocks-cost-card.accounting {
    border-top: 3px solid #14213D;
}

.stocks-cost-card.management {
    border-top: 3px solid #A993CB;

    background: #FBF9FD;
}

.stocks-cost-card.difference {
    border-top: 3px solid #8067AB;

    background: #F4F0F8;
}

.stocks-cost-label {
    color: #667085;

    font-size: 5.6px;
    line-height: 1.15;
    font-weight: 800;

    text-transform: uppercase;
    letter-spacing: .35px;
}

.stocks-cost-value {
    margin-top: 4px;

    overflow: hidden;

    color: #14213D;

    font-family: Georgia, "Times New Roman", serif;
    font-size: 13px;
    line-height: 1;
    font-weight: 800;

    white-space: nowrap;
    text-overflow: ellipsis;
}

.stocks-cost-note {
    margin-top: 3px;

    color: #7A8494;

    font-size: 5.7px;
    line-height: 1.15;
}

.stocks-cost-value.positive,
.stocks-cost-note.positive {
    color: #12654F;
}

.stocks-cost-value.negative,
.stocks-cost-note.negative {
    color: #B53C56;
}

.stocks-cost-value.neutral,
.stocks-cost-note.neutral {
    color: #667085;
}


/* ==================================================================
   МЕТОДОЛОГИЯ
   ================================================================== */

.stocks-method-note {
    display: flex;
    justify-content: space-between;

    gap: 14px;

    margin-top: 5px;
    padding-top: 4px;

    border-top: 1px solid #D7DCE2;

    color: #7A8494;

    font-size: 5.3px;
    line-height: 1.25;
}

.stocks-method-note span:first-child {
    flex: 0 0 auto;

    color: #667085;

    font-weight: 700;
}

.stocks-method-note span:last-child {
    flex: 1;

    text-align: right;
}


/* ==================================================================
   ПУСТОЕ СОСТОЯНИЕ
   ================================================================== */

.stocks-empty {
    display: flex;
    flex-direction: column;

    align-items: center;
    justify-content: center;

    min-height: 170mm;

    text-align: center;
}

.stocks-empty-title {
    color: #14213D;

    font-family: Georgia, "Times New Roman", serif;
    font-size: 19px;
    font-weight: 800;
}

.stocks-empty-text {
    max-width: 360px;

    margin-top: 5px;

    color: #667085;

    font-size: 8px;
    line-height: 1.45;
}


/* ==================================================================
   ЗАЩИТА ОТ ПЕРЕНОСА БЛОКОВ В PDF
   ================================================================== */

.stocks-kpi-grid,
.stocks-analysis,
.stocks-ranking-grid,
.stocks-cost-section,
.stocks-cost-strip {
    break-inside: avoid;
    page-break-inside: avoid;
}




/* ==================================================================
   ЗДОРОВЬЕ ТОВАРНОГО ЗАПАСА
   ================================================================== */

.stocks-health {
    margin-top: 7px;
    padding-top: 6px;

    border-top: 4px solid #14213D;

    break-inside: avoid;
    page-break-inside: avoid;
}


/* ------------------------------------------------------------------
   Заголовок
   ------------------------------------------------------------------ */

.stocks-health-head {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;

    gap: 10px;

    margin-bottom: 5px;
}

.stocks-health-kicker {
    color: #8067AB;

    font-size: 5.8px;
    line-height: 1;
    font-weight: 900;

    letter-spacing: 1px;
}

.stocks-health-title {
    margin-top: 2px;

    color: #14213D;

    font-family: Georgia, "Times New Roman", serif;
    font-size: 12px;
    line-height: 1;
    font-weight: 800;
}

.stocks-health-period {
    padding-bottom: 1px;

    color: #7A8494;

    font-size: 5.4px;
    line-height: 1;

    text-align: right;
}


/* ------------------------------------------------------------------
   Segmented bar
   ------------------------------------------------------------------ */

.stocks-health-bar {
    display: flex;

    width: 100%;
    height: 12px;

    overflow: hidden;

    background: #EDF0F3;

    border: 1px solid #D9DDE3;
}

.stocks-health-segment {
    height: 100%;
}


/* до 30 */

.stocks-health-segment-0_30,
.stocks-health-bucket-0_30 .stocks-health-dot {
    background: #93C99D;
}


/* 30–60 */

.stocks-health-segment-30_60,
.stocks-health-bucket-30_60 .stocks-health-dot {
    background: #C7D99A;
}


/* 60–90 */

.stocks-health-segment-60_90,
.stocks-health-bucket-60_90 .stocks-health-dot {
    background: #E6CF87;
}


/* 90+ */

.stocks-health-segment-90_plus,
.stocks-health-bucket-90_plus .stocks-health-dot {
    background: #E89AA9;
}


/* нет продаж */

.stocks-health-segment-no_sales,
.stocks-health-bucket-no_sales .stocks-health-dot {
    background: #B94A62;
}


/* ------------------------------------------------------------------
   Подписи корзин
   ------------------------------------------------------------------ */

.stocks-health-buckets {
    display: grid;

    grid-template-columns:
        repeat(5, minmax(0, 1fr));

    gap: 4px;

    margin-top: 4px;
}

.stocks-health-bucket {
    min-width: 0;

    padding: 4px 5px;

    border-left: 1px solid #D9DDE3;
}

.stocks-health-bucket:first-child {
    border-left: 0;
}

.stocks-health-bucket-top {
    display: flex;
    align-items: center;

    gap: 4px;

    min-width: 0;
}

.stocks-health-dot {
    flex: 0 0 6px;

    width: 6px;
    height: 6px;
}

.stocks-health-bucket-label {
    overflow: hidden;

    color: #667085;

    font-size: 5.4px;
    line-height: 1;
    font-weight: 800;

    text-transform: uppercase;

    white-space: nowrap;
    text-overflow: ellipsis;
}

.stocks-health-bucket-share {
    margin-top: 3px;

    color: #14213D;

    font-family: Georgia, "Times New Roman", serif;
    font-size: 10px;
    line-height: 1;
    font-weight: 800;
}

.stocks-health-bucket-90_plus
.stocks-health-bucket-share {
    color: #C45169;
}

.stocks-health-bucket-no_sales
.stocks-health-bucket-share {
    color: #A6364E;
}

.stocks-health-bucket-qty {
    margin-top: 2px;

    color: #7A8494;

    font-size: 5.6px;
    line-height: 1;
}


/* ------------------------------------------------------------------
   Основные KPI
   ------------------------------------------------------------------ */

.stocks-health-metrics {
    display: grid;

    grid-template-columns:
        .95fr
        .95fr
        1fr
        1fr
        1.15fr;

    gap: 4px;

    margin-top: 6px;
}

.stocks-health-metric {
    min-width: 0;

    min-height: 46px;

    padding: 5px 6px;

    border: 1px solid #D9DDE3;
    border-top: 2px solid #14213D;

    background: #FFFDF7;
}

.stocks-health-metric-accent {
    border-top-color: #8067AB;

    background: #F8F5FB;
}

.stocks-health-metric-active {
    border-top-color: #93C99D;

    background: #F7FAF6;
}

.stocks-health-metric-risk {
    border-top-color: #B94A62;

    background: #FFF5F7;
}

.stocks-health-metric-label {
    color: #667085;

    font-size: 5.2px;
    line-height: 1;
    font-weight: 800;

    text-transform: uppercase;
}

.stocks-health-metric-value {
    margin-top: 4px;

    overflow: hidden;

    color: #14213D;

    font-family: Georgia, "Times New Roman", serif;
    font-size: 10.5px;
    line-height: 1;
    font-weight: 800;

    white-space: nowrap;
    text-overflow: ellipsis;
}

.stocks-health-metric-risk
.stocks-health-metric-value {
    color: #B53C56;
}

.stocks-health-metric-note {
    margin-top: 3px;

    color: #7A8494;

    font-size: 5.2px;
    line-height: 1.15;
}

.stocks-health-risk-line {
    display: flex;
    align-items: baseline;
    justify-content: space-between;

    gap: 5px;
}

.stocks-health-risk-qty {
    color: #B53C56;

    font-size: 5.6px;
    font-weight: 800;

    white-space: nowrap;
}


/* ------------------------------------------------------------------
   Разбивка зоны риска
   ------------------------------------------------------------------ */

.stocks-health-risk-details {
    display: grid;

    grid-template-columns:
        1fr
        1px
        1fr;

    gap: 8px;

    align-items: center;

    margin-top: 5px;
    padding: 5px 7px;

    background: #F8F5ED;

    border-left: 3px solid #E85D75;
}

.stocks-health-risk-divider {
    width: 1px;
    height: 28px;

    background: #D7DCE2;
}

.stocks-health-risk-item {
    min-width: 0;
}

.stocks-health-risk-item-label {
    color: #667085;

    font-size: 5px;
    line-height: 1;
    font-weight: 800;

    text-transform: uppercase;
}

.stocks-health-risk-item-main {
    margin-top: 3px;

    color: #14213D;

    font-family: Georgia, "Times New Roman", serif;
    font-size: 8.8px;
    line-height: 1;
    font-weight: 800;
}

.stocks-health-risk-item-main span {
    margin-left: 4px;

    color: #B53C56;

    font-family: Arial, sans-serif;
    font-size: 5.7px;
}

.stocks-health-risk-item-note {
    margin-top: 2px;

    color: #7A8494;

    font-size: 5.2px;
}


/* ------------------------------------------------------------------
   Методология
   ------------------------------------------------------------------ */

.stocks-health-method {
    margin-top: 4px;

    color: #8A939F;

    font-size: 4.8px;
    line-height: 1.28;
}


/* ==================================================================
   ОТДЕЛЬНАЯ СТРАНИЦА ПРОИСШЕСТВИЙ
   ================================================================== */

.incidents-page {
    padding-top: 8mm;
}

.incidents-page .masthead {
    margin-bottom: 7px;
}

.incidents-page .brandline {
    color: #C23D58;
}


/* ==================================================================
   СВОДКА
   ================================================================== */

.incidents-summary {
    display: grid;

    grid-template-columns:
        .72fr
        .72fr
        1fr
        1.15fr
        1.15fr;

    gap: 5px;

    margin-bottom: 7px;
}

.incidents-summary-card {
    min-width: 0;

    padding: 6px 7px;

    border: 1px solid #D9DDE3;
    border-top: 3px solid #14213D;

    background: #FFFDF7;
}

.incidents-summary-card.danger {
    border-top-color: #C23D58;
    background: #FFF5F7;
}

.incidents-summary-card.accounting {
    border-top-color: #14213D;
}

.incidents-summary-card.management {
    border-top-color: #A993CB;
    background: #FAF8FC;
}

.incidents-summary-label {
    color: #667085;

    font-size: 5.3px;
    line-height: 1.1;
    font-weight: 800;

    text-transform: uppercase;
    letter-spacing: .35px;
}

.incidents-summary-value {
    margin-top: 4px;

    color: #14213D;

    font-family: Georgia, "Times New Roman", serif;
    font-size: 12px;
    line-height: 1;
    font-weight: 800;

    white-space: nowrap;
}

.incidents-summary-card.danger
.incidents-summary-value {
    color: #B53C56;
}

.incidents-summary-note {
    margin-top: 3px;

    color: #7A8494;

    font-size: 5.3px;
    line-height: 1.15;
}


/* ==================================================================
   МЕТОДОЛОГИЯ
   ================================================================== */

.incidents-method {
    display: grid;
    grid-template-columns: 19px 1fr;
    gap: 7px;

    align-items: start;

    margin-bottom: 8px;
    padding: 7px 9px;

    background: #F6F3EB;

    border-top: 1px solid #D7D1C6;
    border-bottom: 1px solid #D7D1C6;

    color: #4B5563;

    font-size: 7px;
    line-height: 1.42;
}

.incidents-method-icon {
    display: flex;
    align-items: center;
    justify-content: center;

    width: 16px;
    height: 16px;

    border: 1.5px solid #667085;
    border-radius: 50%;

    color: #667085;

    font-family: Georgia, serif;
    font-size: 9px;
    font-weight: 800;
}


/* ==================================================================
   СПИСОК
   ================================================================== */

.incidents-page-list {
    display: flex;
    flex-direction: column;
    gap: 7px;
}


/* ==================================================================
   СОБЫТИЕ
   ================================================================== */

.incident-page-event {
    position: relative;

    border: 1px solid #D6DAE0;
    border-left: 4px solid #C23D58;

    background: #FFFDF7;

    break-inside: avoid;
    page-break-inside: avoid;

    overflow: hidden;
}

.incident-page-event-number {
    position: absolute;

    top: 6px;
    right: 9px;

    color: #E6E8EC;

    font-family: Georgia, serif;
    font-size: 28px;
    line-height: 1;
    font-weight: 800;

    z-index: 0;
}

.incident-page-event-head {
    position: relative;
    z-index: 1;

    display: flex;
    justify-content: space-between;
    align-items: center;

    gap: 10px;

    padding: 7px 9px;

    border-bottom: 1px solid #DADDE3;

    background: #FFFAF7;
}

.incident-page-event-main {
    display: flex;
    align-items: center;

    gap: 8px;

    min-width: 0;
}

.incident-page-fire {
    flex: 0 0 31px;

    width: 31px;
    height: 31px;
}

.incident-page-warehouse {
    color: #14213D;

    font-family: Georgia, serif;
    font-size: 13px;
    line-height: 1;
    font-weight: 800;
}

.incident-page-event-title {
    margin-top: 3px;

    color: #667085;

    font-size: 6.5px;
    line-height: 1.15;
}

.incident-page-status {
    flex: 0 0 auto;

    padding: 3px 7px;

    border: 1px solid #E77B90;
    border-radius: 10px;

    background: #FFF1F4;

    color: #B83D56;

    font-size: 6px;
    line-height: 1;
    font-weight: 800;

    text-transform: uppercase;
}


/* ==================================================================
   ДАТЫ + ОПИСАНИЕ
   ================================================================== */

.incident-page-event-body {
    display: grid;

    grid-template-columns:
        150px
        minmax(0, 1fr);

    gap: 9px;

    padding: 7px 9px;
}

.incident-page-dates {
    padding-right: 9px;

    border-right: 1px solid #DADDE3;
}

.incident-page-date + .incident-page-date {
    margin-top: 7px;
}

.incident-page-date-label,
.incident-page-description-label {
    color: #98A2B3;

    font-size: 5.3px;
    line-height: 1;
    font-weight: 800;

    text-transform: uppercase;
    letter-spacing: .4px;
}

.incident-page-date-value {
    margin-top: 3px;

    color: #14213D;

    font-family: Georgia, serif;
    font-size: 8px;
    line-height: 1.15;
    font-weight: 700;
}

.incident-page-description-text {
    margin-top: 4px;

    color: #354052;

    font-family: Georgia, serif;
    font-size: 7px;
    line-height: 1.45;

    text-align: justify;
}


/* ==================================================================
   KPI СОБЫТИЯ
   ================================================================== */

.incident-page-metrics {
    display: grid;

    grid-template-columns:
        1fr
        1fr
        1fr;

    gap: 5px;

    padding: 0 9px 7px;
}

.incident-page-metric {
    min-width: 0;

    padding: 5px 7px;

    border: 1px solid #DADDE3;
    border-top: 2px solid #14213D;

    background: #FFFDF7;
}

.incident-page-metric.stock {
    border-top-color: #E85D75;
}

.incident-page-metric.management {
    border-top-color: #A993CB;

    background: #FAF8FC;
}

.incident-page-metric-label {
    color: #667085;

    font-size: 5.2px;
    line-height: 1;
    font-weight: 800;

    text-transform: uppercase;
}

.incident-page-metric-value {
    margin-top: 4px;

    color: #14213D;

    font-family: Georgia, serif;
    font-size: 10px;
    line-height: 1;
    font-weight: 800;
}

.incident-page-metric-note {
    margin-top: 3px;

    color: #7A8494;

    font-size: 5.2px;
}


/* ==================================================================
   ПРЕДУПРЕЖДЕНИЯ
   ================================================================== */

.incident-page-info,
.incident-page-warning {
    display: grid;

    grid-template-columns: 17px 1fr;

    gap: 6px;

    align-items: start;

    margin: 0 9px 7px;
    padding: 5px 7px;

    font-size: 6px;
    line-height: 1.35;
}

.incident-page-info {
    background: #F4F6F8;

    color: #4B5563;
}

.incident-page-warning {
    background: #FFF1F4;

    border-left: 3px solid #C23D58;

    color: #7A3444;
}

.incident-page-info-symbol,
.incident-page-warning-symbol {
    display: flex;
    align-items: center;
    justify-content: center;

    width: 15px;
    height: 15px;

    border-radius: 50%;

    font-size: 8px;
    line-height: 1;
    font-weight: 900;
}

.incident-page-info-symbol {
    border: 1px solid #667085;

    color: #667085;
}

.incident-page-warning-symbol {
    background: #C23D58;

    color: white;
}

.incident-page-no-stock {
    margin: 0 9px 7px;
    padding: 7px;

    background: #F4F6F8;

    color: #667085;

    font-size: 6.5px;
}


/* ==================================================================
   НИЖНЯЯ СТРОКА
   ================================================================== */

.incidents-page-footer {
    display: flex;
    justify-content: space-between;

    gap: 15px;

    margin-top: 7px;
    padding-top: 5px;

    border-top: 1px solid #D7DCE2;

    color: #8A939F;

    font-size: 5.3px;
}



/* ==================================================================
   FINANCIAL PAGE
   ================================================================== */

.financial-page {
    padding-top: 7.5mm;
}

.financial-page .masthead {
    margin-bottom: 5px;
}

.financial-page .masthead h1 {
    font-size: 25px;
}


/* ==================================================================
   KPI
   ================================================================== */

.finance-kpi-grid {
    display: grid;

    grid-template-columns:
        repeat(4, minmax(0, 1fr));

    gap: 5px;

    margin-bottom: 6px;
}

.finance-kpi {
    min-width: 0;
    min-height: 58px;

    padding: 6px 7px;

    border: 1px solid #D7DCE2;
    border-top: 3px solid #14213D;

    background: #FFFDF7;
}

.finance-kpi.positive {
    border-top-color: #16805E;
}

.finance-kpi.negative {
    border-top-color: #C23D58;

    background: #FFF7F8;
}

.finance-kpi.cost {
    border-top-color: #8067AB;
}

.finance-kpi.returns {
    border-top-color: #E85D75;
}

.finance-kpi-top {
    display: flex;

    align-items: center;
    justify-content: space-between;

    gap: 4px;

    color: #667085;

    font-size: 5.5px;
    line-height: 1.05;
    font-weight: 800;

    letter-spacing: .42px;
    text-transform: uppercase;
}

.finance-kpi-icon {
    width: 18px;
    height: 18px;

    flex: 0 0 18px;
}

.finance-kpi-value {
    margin-top: 4px;

    overflow: hidden;

    color: #14213D;

    font-family:
        Georgia,
        "Times New Roman",
        serif;

    font-size: 14px;
    line-height: 1;
    font-weight: 800;

    white-space: nowrap;
    text-overflow: ellipsis;
}

.finance-kpi.negative
.finance-kpi-value {
    color: #C23D58;
}

.finance-kpi-note {
    margin-top: 3px;

    overflow: hidden;

    color: #667085;

    font-size: 5.6px;
    line-height: 1.1;

    white-space: nowrap;
    text-overflow: ellipsis;
}


/* ==================================================================
   HEADINGS
   ================================================================== */

.finance-kicker {
    color: #E85D75;

    font-size: 5.8px;
    line-height: 1;
    font-weight: 800;

    letter-spacing: .72px;

    text-transform: uppercase;
}

.finance-block-title,
.finance-side-title {
    margin-top: 2px;

    color: #14213D;

    font-family:
        Georgia,
        "Times New Roman",
        serif;

    font-size: 12.7px;
    line-height: 1.06;
    font-weight: 700;
}

.finance-block-title.small {
    font-size: 11.4px;
}

.finance-block-note,
.finance-side-subtitle {
    color: #667085;

    font-size: 5.8px;
    line-height: 1.15;
}

.finance-block-head {
    display: flex;

    align-items: flex-start;
    justify-content: space-between;

    gap: 8px;
}


/* ==================================================================
   MAIN GRID
   ================================================================== */

.finance-main-grid {
    display: grid;

    grid-template-columns:
        minmax(0, 2.05fr)
        minmax(0, .95fr);

    gap: 6px;

    margin-bottom: 5px;
}

.finance-main-card,
.finance-side-card {
    min-width: 0;

    border: 1px solid #D7DCE2;

    background: #FFFDF7;

    break-inside: avoid;
}

.finance-main-card {
    padding:
        6px
        7px
        3px;

    border-top:
        3px solid #14213D;
}

.finance-side-card {
    padding: 6px 7px 4px;

    border-top:
        3px solid #8067AB;

    background: #F9F7FC;
}

.finance-bridge-chart {
    width: 100%;
    height: 158px;

    margin-top: 2px;
}

.finance-bridge-chart svg,
.finance-economics-chart svg,
.finance-trend-chart svg,
.finance-weeks-strip svg {
    display: block;

    width: 100%;
    height: 100%;

    background: transparent;
}

.finance-economics-chart {
    width: 100%;
    height: 153px;

    margin-top: 4px;
}


/* ==================================================================
   DAY COMMENT
   ================================================================== */

.finance-insight {
    margin-bottom: 5px;

    padding:
        6px
        9px
        6px
        11px;

    border: 1px solid #D7DCE2;
    border-left: 4px solid #16805E;

    background: #F4F0E6;
}

.finance-insight-label {
    margin-bottom: 3px;

    color: #667085;

    font-size: 5.5px;
    line-height: 1;

    font-weight: 800;

    letter-spacing: .55px;

    text-transform: uppercase;
}

.finance-insight-text {
    color: #354052;

    font-family:
        Georgia,
        "Times New Roman",
        serif;

    font-size: 7.7px;
    line-height: 1.38;
}

.finance-insight-text b {
    color: #14213D;
}


/* ==================================================================
   MID GRID
   ================================================================== */

.finance-mid-grid {
    display: grid;

    grid-template-columns:
        minmax(0, 1.9fr)
        minmax(0, .90fr);

    gap: 6px;

    margin-bottom: 5px;
}

.finance-trend-card,
.finance-week-card {
    min-width: 0;

    border: 1px solid #D7DCE2;

    background: #FFFDF7;

    break-inside: avoid;
}

.finance-trend-card {
    padding:
        6px
        7px
        2px;

    border-top:
        3px solid #14213D;
}

.finance-trend-chart {
    width: 100%;
    height: 132px;

    margin-top: 2px;
}


/* ==================================================================
   LEGEND
   ================================================================== */

.finance-legend {
    display: flex;

    align-items: center;

    gap: 4px;

    color: #667085;

    font-size: 5.5px;
}

.finance-dot {
    display: inline-block;

    width: 5px;
    height: 5px;

    margin-left: 5px;

    border-radius: 50%;
}

.finance-dot:first-child {
    margin-left: 0;
}

.finance-dot.positive {
    background: #16805E;
}

.finance-dot.negative {
    background: #C23D58;
}


/* ==================================================================
   CURRENT WEEK
   ================================================================== */

.finance-week-card {
    padding: 6px 8px;

    border-top:
        3px solid #E85D75;

    background: #FAF8F2;
}

.finance-week-period {
    margin-top: 3px;

    color: #667085;

    font-size: 6.3px;
}

.finance-week-status {
    display: inline-block;

    margin-top: 5px;

    padding:
        2px
        4px;

    background: #F1EDE3;

    color: #667085;

    font-size: 5.4px;
    font-weight: 800;

    letter-spacing: .4px;
}

.finance-week-result {
    margin-top: 5px;

    color: #14213D;

    font-family:
        Georgia,
        "Times New Roman",
        serif;

    font-size: 20px;
    line-height: 1;

    font-weight: 800;
}

.finance-week-result.positive {
    color: #16805E;
}

.finance-week-result.negative {
    color: #C23D58;
}

.finance-week-result-caption {
    margin-top: 2px;

    color: #667085;

    font-size: 6px;
}

.finance-week-metrics {
    margin-top: 6px;

    border-top:
        1px solid #D7DCE2;

    border-bottom:
        1px solid #D7DCE2;
}

.finance-week-metric {
    display: flex;

    align-items: center;
    justify-content: space-between;

    padding: 3px 0;

    color: #667085;

    font-size: 6.2px;
}

.finance-week-metric b {
    color: #14213D;

    font-size: 6.8px;
}

.finance-week-comparison {
    margin-top: 5px;
}

.finance-week-comparison-label {
    color: #667085;

    font-size: 5.4px;

    text-transform: uppercase;

    letter-spacing: .4px;
}

.finance-week-comparison-main {
    margin-top: 2px;

    color: #14213D;

    font-family:
        Georgia,
        serif;

    font-size: 13px;
    font-weight: 700;
}

.finance-week-comparison-base {
    margin-top: 1px;

    color: #667085;

    font-size: 5.6px;
}

.finance-week-warning {
    margin-top: 5px;

    padding-top: 4px;

    border-top:
        1px dashed #D7DCE2;

    color: #806F42;

    font-size: 5.4px;
    line-height: 1.25;
}


/* ==================================================================
   WEEK STRIP
   ================================================================== */

.finance-weeks-strip-card {
    margin-bottom: 5px;

    padding:
        6px
        7px
        3px;

    border: 1px solid #D7DCE2;

    border-top:
        3px solid #16805E;

    background: #FFFDF7;

    break-inside: avoid;
}

.finance-weeks-strip {
    width: 100%;
    height: 78px;

    margin-top: 3px;
}


/* ==================================================================
   LOWER GRID
   ================================================================== */

.finance-lower-grid {
    display: grid;

    grid-template-columns:
        minmax(0, .95fr)
        minmax(0, 2.05fr);

    gap: 6px;
}


/* ==================================================================
   EDITORIAL
   ================================================================== */

.finance-editorial {
    padding: 7px;

    border: 1px solid #D7DCE2;
    border-top: 3px solid #14213D;

    background: #FFFDF7;

    break-inside: avoid;
}

.finance-editorial.positive {
    border-top-color: #16805E;
}

.finance-editorial.warning {
    border-top-color: #E9B949;
}

.finance-editorial.negative {
    border-top-color: #C23D58;
}

.finance-editorial-title {
    margin-top: 3px;

    color: #14213D;

    font-family:
        Georgia,
        "Times New Roman",
        serif;

    font-size: 10.5px;
    line-height: 1.12;

    font-weight: 700;
}

.finance-editorial-text {
    margin-top: 4px;

    color: #354052;

    font-family:
        Georgia,
        serif;

    font-size: 6.8px;
    line-height: 1.35;
}

.finance-editorial-deltas {
    display: grid;

    grid-template-columns:
        repeat(3, 1fr);

    gap: 3px;

    margin-top: 6px;
}

.finance-editorial-deltas > div {
    padding:
        4px
        3px;

    border: 1px solid #E0E3E7;

    background: #FAF9F5;

    text-align: center;
}

.finance-editorial-deltas span {
    display: block;

    color: #667085;

    font-size: 4.9px;
}

.finance-editorial-deltas b {
    display: block;

    margin-top: 2px;

    color: #14213D;

    font-size: 6.8px;
}


/* ==================================================================
   METHODOLOGY
   ================================================================== */

.finance-methodology {
    padding: 7px;

    border: 1px solid #D7DCE2;
    border-top: 3px solid #8067AB;

    background: #F8F5FB;

    break-inside: avoid;
}

.finance-methodology-title {
    color: #667085;

    font-size: 5.5px;
    font-weight: 800;

    letter-spacing: .55px;

    text-transform: uppercase;
}

.finance-methodology-grid {
    display: grid;

    grid-template-columns:
        repeat(3, minmax(0, 1fr));

    gap: 7px;

    margin-top: 5px;
}

.finance-methodology-grid > div {
    color: #4A5568;

    font-family:
        Georgia,
        serif;

    font-size: 6.3px;
    line-height: 1.34;
}

.finance-methodology-grid > div + div {
    padding-left: 7px;

    border-left:
        1px solid #D7DCE2;
}

.finance-methodology-grid b {
    display: block;

    margin-bottom: 2px;

    color: #14213D;

    font-family:
        Arial,
        sans-serif;

    font-size: 5.9px;
}


/* ==================================================================
   EMPTY
   ================================================================== */

.finance-empty {
    min-height: 80px;

    display: flex;

    align-items: center;
    justify-content: center;

    padding: 10px;

    border:
        1px dashed #D7DCE2;

    color: #7A8492;

    font-size: 6px;
}


/* ==================================================================
   FOOTER
   ================================================================== */

.finance-footer-note {
    display: flex;

    justify-content: space-between;

    gap: 15px;

    margin-top: 4px;
    padding-top: 3px;

    border-top:
        1px solid #D7DCE2;

    color: #7A8492;

    font-size: 5.2px;
}


/* ======================================================================
   FINANCIAL PAGE — КОНТРОЛЬ СЕБЕСТОИМОСТИ
   ====================================================================== */

.finance-cost-control {
    display: grid;
    grid-template-columns: 1.35fr 2fr;

    margin-top: 6px;

    border: 1px solid #D7DCE2;
    border-left: 4px solid #16805E;

    background: #F7FAF8;

    break-inside: avoid;
    page-break-inside: avoid;
}


/* ======================================================================
   СОСТОЯНИЕ — ЕСТЬ ПРОБЛЕМНЫЕ ПРОДАЖИ
   ====================================================================== */

.finance-cost-control.warning {
    border-left-color: #E9B949;
    background: #FFFBF0;
}


/* ======================================================================
   ЛЕВАЯ ЧАСТЬ — ТЕКУЩИЙ ДЕНЬ
   ====================================================================== */

.finance-cost-day {
    min-width: 0;

    padding: 7px 10px;

    border-right: 1px solid #D7DCE2;
}


/* ----------------------------------------------------------------------
   Заголовок
   ---------------------------------------------------------------------- */

.finance-cost-control .finance-kicker {
    margin: 0 0 3px 0;

    color: #EF5A70;

    font-family: Arial, sans-serif;
    font-size: 5.8px;
    line-height: 1;
    font-weight: 800;

    letter-spacing: 0.08em;
    text-transform: uppercase;
}


.finance-cost-control-title {
    margin: 0;

    color: #14213D;

    font-family: Georgia, "Times New Roman", serif;
    font-size: 9px;
    line-height: 1.1;
    font-weight: 700;
}


/* ======================================================================
   ГЛАВНЫЙ ПОКАЗАТЕЛЬ ДНЯ
   ====================================================================== */

.finance-cost-day-main {
    display: flex;
    align-items: center;

    gap: 9px;

    margin-top: 5px;
}


.finance-cost-day-percent {
    flex: 0 0 auto;

    color: #16805E;

    font-family: Georgia, "Times New Roman", serif;
    font-size: 20px;
    line-height: 0.95;
    font-weight: 800;

    white-space: nowrap;
}


.finance-cost-control.warning .finance-cost-day-percent {
    color: #B7791F;
}


.finance-cost-day-caption {
    color: #667085;

    font-family: Arial, sans-serif;
    font-size: 5.5px;
    line-height: 1.25;
}


.finance-cost-day-caption b {
    display: block;

    margin-top: 2px;

    color: #14213D;

    font-family: Georgia, "Times New Roman", serif;
    font-size: 7px;
    line-height: 1;
    font-weight: 700;
}


/* ======================================================================
   ПРИЧИНЫ ОТСУТСТВИЯ СЕБЕСТОИМОСТИ
   ====================================================================== */

.finance-cost-day-details {
    display: flex;

    gap: 12px;

    margin-top: 6px;
    padding-top: 5px;

    border-top: 1px solid #E2E6EA;
}


.finance-cost-day-details span {
    display: block;

    color: #667085;

    font-family: Arial, sans-serif;
    font-size: 5px;
    line-height: 1.15;
}


.finance-cost-day-details b {
    display: block;

    margin-top: 2px;

    color: #14213D;

    font-family: Georgia, "Times New Roman", serif;
    font-size: 7px;
    line-height: 1;
    font-weight: 700;
}


/* ======================================================================
   ПРАВАЯ ЧАСТЬ — НЕДЕЛЯ / КВАРТАЛ / YTD
   ====================================================================== */

.finance-cost-history {
    display: grid;

    grid-template-columns:
        repeat(3, minmax(0, 1fr));

    min-width: 0;
}


/* ======================================================================
   ОДИН ПЕРИОД
   ====================================================================== */

.finance-cost-period {
    display: flex;
    flex-direction: column;
    justify-content: center;

    min-width: 0;

    padding: 7px 10px;

    border-right: 1px solid #D7DCE2;
}


.finance-cost-period:last-child {
    border-right: 0;
}


/* ----------------------------------------------------------------------
   Название периода
   ---------------------------------------------------------------------- */

.finance-cost-period-label {
    color: #667085;

    font-family: Arial, sans-serif;
    font-size: 5.2px;
    line-height: 1;
    font-weight: 700;

    letter-spacing: 0.04em;
    text-transform: uppercase;
}


/* ----------------------------------------------------------------------
   Процент продаж без себестоимости
   ---------------------------------------------------------------------- */

.finance-cost-period-pct {
    display: block;

    margin-top: 5px;

    color: #14213D;

    font-family: Georgia, "Times New Roman", serif;
    font-size: 15px;
    line-height: 0.95;
    font-weight: 800;

    white-space: nowrap;
}


/* ----------------------------------------------------------------------
   Количество единиц
   ---------------------------------------------------------------------- */

.finance-cost-period-count {
    display: block;

    margin-top: 4px;

    color: #667085;

    font-family: Arial, sans-serif;
    font-size: 5.2px;
    line-height: 1.15;

    white-space: nowrap;
}


/* ======================================================================
   ВИЗУАЛЬНАЯ ИЕРАРХИЯ ПЕРИОДОВ
   ====================================================================== */

.finance-cost-period:first-child {
    background: rgba(239, 90, 112, 0.025);
}


.finance-cost-period:last-child {
    background: rgba(22, 128, 94, 0.035);
}


.finance-cost-period:last-child .finance-cost-period-pct {
    color: #16805E;
}


/* ======================================================================
   WARNING
   ====================================================================== */

.finance-cost-control.warning .finance-cost-day {
    background: rgba(233, 185, 73, 0.035);
}


/* ======================================================================
   OK
   ====================================================================== */

.finance-cost-control.ok {
    border-left-color: #16805E;
}


.finance-cost-control.ok .finance-cost-day {
    background: rgba(22, 128, 94, 0.025);
}


/* ======================================================================
   PDF SAFETY
   ====================================================================== */

.finance-cost-control,
.finance-cost-day,
.finance-cost-history,
.finance-cost-period {
    box-sizing: border-box;
}


.finance-cost-control * {
    box-sizing: border-box;
}




/* ======================================================================
   DEMAND PAGE
   ====================================================================== */

.demand-page {
    padding-top: 7.5mm;
}


.demand-page .masthead {
    margin-bottom: 5px;
}


.demand-page .masthead h1 {
    font-size: 25px;
}


/* ======================================================================
   KPI
   ====================================================================== */

.demand-kpi-grid {
    display: grid;

    grid-template-columns:
        repeat(4, minmax(0, 1fr));

    gap: 5px;

    margin-bottom: 5px;
}


.demand-kpi {
    min-width: 0;

    padding: 6px 7px;

    border: 1px solid #D7DCE2;
    border-top: 3px solid #14213D;

    background: #FFFDF7;
}


.demand-kpi.demand {
    border-top-color: #16805E;
}


.demand-kpi.price {
    border-top-color: #E85D75;
}


.demand-kpi.revenue {
    border-top-color: #8067AB;
}


.demand-kpi.today {
    border-top-color: #E9B949;
}


.demand-kpi-label {
    color: #667085;

    font-family: Arial, sans-serif;
    font-size: 5.4px;
    line-height: 1;

    font-weight: 800;

    letter-spacing: .05em;

    text-transform: uppercase;
}


.demand-kpi-value {
    margin-top: 4px;

    color: #14213D;

    font-family:
        Georgia,
        "Times New Roman",
        serif;

    font-size: 13.5px;
    line-height: 1;

    font-weight: 800;

    white-space: nowrap;
}


.demand-kpi-bottom {
    display: flex;

    align-items: flex-end;
    justify-content: space-between;

    gap: 4px;

    margin-top: 4px;

    color: #667085;

    font-size: 5.2px;
    line-height: 1.1;
}


.demand-kpi-change {
    flex: 0 0 auto;

    font-size: 5.7px;
    font-weight: 800;
}


.demand-kpi-change.up {
    color: #16805E;
}


.demand-kpi-change.down {
    color: #C23D58;
}


.demand-kpi-change.neutral {
    color: #667085;
}


/* ======================================================================
   COMMON
   ====================================================================== */

.demand-kicker {
    color: #E85D75;

    font-family: Arial, sans-serif;

    font-size: 5.7px;
    line-height: 1;

    font-weight: 800;

    letter-spacing: .08em;
    text-transform: uppercase;
}


.demand-block-title {
    margin-top: 2px;

    color: #14213D;

    font-family:
        Georgia,
        "Times New Roman",
        serif;

    font-size: 12px;
    line-height: 1.05;

    font-weight: 700;
}


.demand-block-title.small {
    font-size: 10px;
}


.demand-block-subtitle,
.demand-chart-caption {
    color: #667085;

    font-size: 5.5px;
    line-height: 1.15;
}


.demand-block-subtitle {
    margin-top: 2px;
}


.demand-block-head {
    display: flex;

    align-items: flex-start;
    justify-content: space-between;

    gap: 8px;
}


/* ======================================================================
   TOP GRID
   ====================================================================== */

.demand-top-grid {
    display: grid;

    grid-template-columns:
        minmax(0, .85fr)
        minmax(0, 2.15fr);

    gap: 6px;

    margin-bottom: 5px;
}


/* ======================================================================
   EDITORIAL
   ====================================================================== */

.demand-editorial {
    padding: 7px 8px;

    border: 1px solid #D7DCE2;
    border-top: 3px solid #14213D;

    background: #F7F4EC;
}


.demand-editorial.positive {
    border-top-color: #16805E;
}


.demand-editorial.warning {
    border-top-color: #E9B949;
}


.demand-editorial.negative {
    border-top-color: #C23D58;
}


.demand-editorial-label {
    color: #E85D75;

    font-size: 5.5px;
    font-weight: 800;

    letter-spacing: .08em;
}


.demand-editorial-title {
    margin-top: 3px;

    color: #14213D;

    font-family:
        Georgia,
        "Times New Roman",
        serif;

    font-size: 12.2px;
    line-height: 1.06;

    font-weight: 700;
}


.demand-editorial-copy {
    margin-top: 5px;

    color: #39465A;

    font-family:
        Georgia,
        "Times New Roman",
        serif;

    font-size: 6.7px;
    line-height: 1.4;
}


.demand-corr-strip {
    display: grid;

    grid-template-columns:
        1fr 1fr;

    gap: 4px;

    margin-top: 7px;
    padding-top: 5px;

    border-top: 1px solid #D7DCE2;
}


.demand-corr-strip > div {
    min-width: 0;
}


.demand-corr-strip > div + div {
    padding-left: 5px;

    border-left: 1px solid #D7DCE2;
}


.demand-corr-strip span {
    display: block;

    color: #667085;

    font-size: 5px;

    text-transform: uppercase;
}


.demand-corr-strip b {
    display: block;

    margin-top: 2px;

    color: #14213D;

    font-family: Georgia, serif;

    font-size: 10px;
}


.demand-corr-strip small {
    display: block;

    margin-top: 1px;

    color: #667085;

    font-size: 4.8px;
    line-height: 1.2;
}


/* ======================================================================
   MONTHLY
   ====================================================================== */

.demand-monthly-card {
    min-width: 0;

    padding: 6px 7px 3px;

    border: 1px solid #D7DCE2;
    border-top: 3px solid #8067AB;

    background: #FFFDF7;
}


.demand-monthly-chart {
    width: 100%;
    height: 146px;

    margin-top: 3px;
}


.demand-monthly-chart svg {
    display: block;

    width: 100%;
    height: 100%;
}


/* ======================================================================
   90 DAY REGIME
   ====================================================================== */

.demand-regime-card {
    padding: 6px 7px 4px;

    margin-bottom: 5px;

    border: 1px solid #D7DCE2;
    border-top: 3px solid #14213D;

    background: #FFFDF7;
}


.demand-regime-chart {
    width: 100%;
    height: 145px;

    margin-top: 2px;
}


.demand-regime-chart svg {
    display: block;

    width: 100%;
    height: 100%;
}


.demand-chart-note {
    margin-top: 2px;
    padding-top: 3px;

    border-top: 1px solid #E7E9EC;

    color: #667085;

    font-family:
        Georgia,
        serif;

    font-size: 5.4px;
    line-height: 1.3;
}


/* ======================================================================
   RANKINGS
   ====================================================================== */

.demand-ranking-grid {
    display: grid;

    grid-template-columns:
        1fr 1fr;

    gap: 6px;

    margin-bottom: 5px;
}


.demand-ranking-card {
    min-width: 0;

    padding: 6px 7px 3px;

    border: 1px solid #D7DCE2;
    border-top: 3px solid #E85D75;

    background: #FFFDF7;
}


.demand-ranking-card:last-child {
    border-top-color: #16805E;
}


.demand-ranking-chart {
    width: 100%;
    height: 105px;

    margin-top: 3px;
}


.demand-ranking-chart svg {
    display: block;

    width: 100%;
    height: 100%;
}


/* ======================================================================
   METHODOLOGY
   ====================================================================== */

.demand-methodology {
    padding: 6px 7px;

    border: 1px solid #D7DCE2;
    border-top: 3px solid #E9B949;

    background: #F8F5ED;
}


.demand-methodology-grid {
    display: grid;

    grid-template-columns:
        repeat(3, minmax(0, 1fr));

    gap: 7px;

    margin-top: 4px;
}


.demand-methodology-grid > div {
    color: #4B5565;

    font-family:
        Georgia,
        serif;

    font-size: 5.8px;
    line-height: 1.32;
}


.demand-methodology-grid > div + div {
    padding-left: 7px;

    border-left: 1px solid #D7DCE2;
}


.demand-methodology-grid b {
    display: block;

    margin-bottom: 2px;

    color: #14213D;

    font-family:
        Arial,
        sans-serif;

    font-size: 5.4px;
}


/* ======================================================================
   EMPTY
   ====================================================================== */

.demand-empty {
    display: flex;

    align-items: center;
    justify-content: center;

    min-height: 100px;

    border: 1px dashed #D7DCE2;

    color: #667085;

    font-size: 6px;
}


.demand-empty.compact {
    min-height: 70px;
}


/* ======================================================================
   FOOTER
   ====================================================================== */

.demand-footer-note {
    display: flex;

    justify-content: space-between;

    gap: 10px;

    margin-top: 4px;
    padding-top: 3px;

    border-top: 1px solid #D7DCE2;

    color: #7A8492;

    font-size: 5.1px;
}


/* ======================================================================
   PDF SAFETY
   ====================================================================== */

.demand-page *,
.demand-kpi,
.demand-editorial,
.demand-monthly-card,
.demand-regime-card,
.demand-ranking-card,
.demand-methodology {
    box-sizing: border-box;
}




/* ======================================================================
   ЦЕНОВОЙ ПОТЕНЦИАЛ БРЕНДОВ
   ====================================================================== */

.demand-price-potential {
    margin-bottom: 5px;

    padding: 6px 7px 4px;

    border: 1px solid #D7DCE2;
    border-top: 3px solid #16805E;

    background: #FFFDF7;

    break-inside: avoid;
}


.demand-price-potential-head {
    display: flex;

    align-items: flex-start;
    justify-content: space-between;

    gap: 12px;

    margin-bottom: 4px;
}


.demand-price-rule {
    max-width: 285px;

    padding-left: 8px;

    border-left: 2px solid #E9B949;

    color: #667085;

    font-family:
        Georgia,
        "Times New Roman",
        serif;

    font-size: 5.3px;
    line-height: 1.28;
}


.demand-price-rule b {
    display: block;

    margin-bottom: 1px;

    color: #14213D;

    font-family:
        Arial,
        sans-serif;

    font-size: 5.4px;
}


.demand-price-potential-grid {
    display: grid;

    grid-template-columns:
        minmax(0, 1.8fr)
        minmax(0, 1fr);

    gap: 7px;
}


.demand-price-matrix {
    min-width: 0;

    height: 185px;

    border-right: 1px solid #E2E5E9;

    padding-right: 6px;
}


.demand-price-matrix svg {
    display: block;

    width: 100%;
    height: 100%;
}


/* ======================================================================
   ВОЗМОЖНОСТИ
   ====================================================================== */

.demand-price-opportunities {
    min-width: 0;
}


.demand-price-opportunities-title {
    margin-bottom: 3px;

    color: #667085;

    font-size: 5.2px;
    line-height: 1;

    font-weight: 800;

    letter-spacing: .06em;

    text-transform: uppercase;
}


.demand-price-opportunity {
    padding: 4px 0;

    border-bottom: 1px solid #E4E7EB;
}


.demand-price-opportunity:last-child {
    border-bottom: 0;
}


.demand-price-opportunity-brand {
    color: #14213D;

    font-family:
        Georgia,
        "Times New Roman",
        serif;

    font-size: 7px;
    line-height: 1;

    font-weight: 700;
}


.demand-price-opportunity-action {
    margin-top: 2px;

    color: #667085;

    font-size: 5px;
}


.demand-price-opportunity-action b {
    margin-left: 3px;

    color: #E85D75;

    font-size: 6.3px;
}


.demand-price-opportunity-grid {
    display: grid;

    grid-template-columns:
        repeat(3, minmax(0, 1fr));

    gap: 3px;

    margin-top: 3px;
}


.demand-price-opportunity-grid > div {
    padding: 3px;

    background: #F7F7F3;
}


.demand-price-opportunity-grid span {
    display: block;

    color: #667085;

    font-size: 4.5px;
}


.demand-price-opportunity-grid b {
    display: block;

    margin-top: 1px;

    color: #14213D;

    font-size: 5.8px;
}


.demand-price-opportunity-grid b.positive {
    color: #16805E;
}


.demand-price-opportunity-meta {
    margin-top: 2px;

    color: #7A8492;

    font-size: 4.7px;
}


.demand-price-opportunity-meta b {
    color: #14213D;
}


.demand-opportunity-empty {
    padding: 9px;

    border: 1px dashed #D7DCE2;

    color: #667085;

    font-family:
        Georgia,
        serif;

    font-size: 5.8px;
    line-height: 1.35;
}


.demand-opportunity-empty b {
    display: block;

    margin-top: 4px;

    color: #14213D;
}


/* ======================================================================
   DISCLAIMER
   ====================================================================== */

.demand-price-disclaimer {
    margin-top: 4px;
    padding-top: 3px;

    border-top: 1px solid #E7E9EC;

    color: #7A8492;

    font-size: 4.8px;
    line-height: 1.25;
}


/* ======================================================================
   АНОМАЛИИ
   ====================================================================== */

.demand-anomalies {
    margin-bottom: 4px;

    padding: 4px 6px;

    border: 1px solid #D7DCE2;
    border-top: 3px solid #E9B949;

    background: #FAF8F2;

    break-inside: avoid;
}


.demand-anomalies-head {
    display: flex;

    justify-content: space-between;
    align-items: flex-start;

    gap: 8px;

    margin-bottom: 4px;
}


.demand-anomalies-grid {
    display: grid;

    grid-template-columns:
        repeat(4, minmax(0, 1fr));

    gap: 4px;
}


.demand-anomaly {
    min-width: 0;

    padding: 5px;

    border: 1px solid #E1E4E8;
    border-left: 3px solid #667085;

    background: #FFFDF7;
}


.demand-anomaly.warning {
    border-left-color: #E9B949;
}


.demand-anomaly.negative {
    border-left-color: #C23D58;
}


.demand-anomaly.positive {
    border-left-color: #16805E;
}


.demand-anomaly-brand {
    color: #14213D;

    font-size: 5.3px;
    font-weight: 800;

    text-transform: uppercase;
}


.demand-anomaly-title {
    margin-top: 2px;

    min-height: 22px;

    color: #354052;

    font-family:
        Georgia,
        "Times New Roman",
        serif;

    font-size: 5.8px;
    line-height: 1.25;

    font-weight: 700;
}


.demand-anomaly-numbers {
    margin-top: 4px;
}


.demand-anomaly-numbers span {
    display: flex;

    justify-content: space-between;

    gap: 3px;

    padding-top: 2px;

    color: #667085;

    font-size: 4.7px;
}


.demand-anomaly-numbers b {
    color: #14213D;
}


.demand-anomalies-clear {
    margin-top: 4px;

    padding: 8px;

    color: #667085;

    font-family:
        Georgia,
        serif;

    font-size: 6px;

    border: 1px dashed #D7DCE2;
}




/* ======================================================================
   DEMAND — ЦЕНОВОЙ БАЛАНС
   ====================================================================== */

.demand-balance-focus {
    display: grid;

    grid-template-columns:
        minmax(0, 1.75fr)
        minmax(0, .95fr);

    gap: 6px;

    margin-top: 4px;
}


/* ======================================================================
   ГРАФИК
   ====================================================================== */

.demand-balance-chart {
    min-width: 0;

    padding-right: 7px;

    border-right: 1px solid #D7DCE2;
}


.demand-balance-brand {
    color: #14213D;

    font-family:
        Georgia,
        "Times New Roman",
        serif;

    font-size: 10.5px;
    line-height: 1;

    font-weight: 700;
}


.demand-balance-chart-subtitle {
    margin-top: 2px;

    color: #667085;

    font-size: 5.2px;
}


.demand-balance-chart svg {
    display: block;

    width: 100%;
    height: 145px;

    margin-top: 2px;
}


/* ======================================================================
   SUMMARY
   ====================================================================== */

.demand-balance-summary {
    min-width: 0;

    padding: 4px 2px 2px 2px;
}


.demand-balance-summary-title {
    margin-top: 3px;

    color: #14213D;

    font-family:
        Georgia,
        "Times New Roman",
        serif;

    font-size: 9px;
    line-height: 1.08;

    font-weight: 700;
}


.demand-balance-summary-title.positive {
    color: #16805E;
}


.demand-balance-summary-title.warning {
    color: #B7791F;
}


.demand-balance-summary-copy {
    margin-top: 3px;

    color: #4B5565;

    font-family:
        Georgia,
        "Times New Roman",
        serif;

    font-size: 5px;
    line-height: 1.22;
}


/* ======================================================================
   PRICE
   ====================================================================== */

.demand-balance-price {
    display: grid;

    grid-template-columns:
        1fr auto 1fr;

    align-items: center;

    gap: 5px;

    margin-top: 6px;
    padding: 5px;

    border: 1px solid #E0E4E8;

    background: #F7F7F3;
}


.demand-balance-price span {
    display: block;

    color: #667085;

    font-size: 4.8px;
    text-transform: uppercase;
}


.demand-balance-price b {
    display: block;

    margin-top: 2px;

    color: #14213D;

    font-family:
        Georgia,
        "Times New Roman",
        serif;

    font-size: 8px;
}


.demand-balance-price b.accent {
    color: #16805E;
}


.demand-balance-price .arrow {
    color: #667085;

    font-size: 10px;
}


.demand-balance-delta {
    margin-top: 3px;

    color: #E85D75;

    font-size: 6px;
    font-weight: 800;
}


/* ======================================================================
   RESULT METRICS
   ====================================================================== */

.demand-balance-metrics {
    display: grid;

    grid-template-columns:
        1fr 1fr;

    gap: 3px;

   margin-top: 4px;
}


.demand-balance-metrics > div {
     padding: 3px 4px;

    border: 1px solid #E4E7EB;

    background: #FFFDF7;
}


.demand-balance-metrics span {
    display: block;

    color: #667085;

    font-size: 4.7px;
}


.demand-balance-metrics b {
    display: block;

    margin-top: 1px;

    color: #14213D;

    font-size: 6.5px;
}


.demand-balance-metrics b.positive {
    color: #16805E;
}


/* ======================================================================
   MAX MARGIN
   ====================================================================== */

.demand-balance-max {
    margin-top: 5px;
    padding-top: 4px;

    border-top: 1px solid #D7DCE2;
}


.demand-balance-max span {
    color: #667085;

    font-size: 4.8px;
}


.demand-balance-max > b {
    margin-left: 4px;

    color: #E85D75;

    font-size: 6px;
}


.demand-balance-max small {
    display: block;

    margin-top: 2px;

    color: #667085;

    font-size: 4.7px;
}


.demand-balance-model {
    margin-top: 5px;

    color: #7A8492;

    font-size: 4.6px;
    line-height: 1.3;
}


.demand-balance-model b {
    color: #14213D;
}


/* ======================================================================
   BRAND TABLE
   ====================================================================== */

.demand-balance-table {
    margin-top: 6px;

    border-top: 1px solid #D7DCE2;
}


.demand-balance-table-title {
    padding: 5px 0 3px;

    color: #667085;

    font-size: 5px;
    font-weight: 800;

    letter-spacing: .06em;

    text-transform: uppercase;
}


.demand-balance-table-row {
    display: grid;

    grid-template-columns:
        1.35fr
        .8fr
        .8fr
        .65fr
        .65fr
        .7fr
        .7fr
        .9fr;

    align-items: center;

    min-width: 0;

    border-top: 1px solid #ECEEF0;
}


.demand-balance-table-row > div {
    min-width: 0;

    padding: 3px 4px;

    color: #4B5565;

    font-size: 5px;

    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}


.demand-balance-table-row.header {
    background: #F5F3ED;
}


.demand-balance-table-row.header > div {
    color: #667085;

    font-size: 4.6px;
    font-weight: 800;

    text-transform: uppercase;
}


.demand-balance-table-row .brand {
    color: #14213D;

    font-weight: 800;
}


.demand-balance-table-row .positive {
    color: #16805E;

    font-weight: 700;
}


.demand-balance-table-row .negative {
    color: #C23D58;

    font-weight: 700;
}


.demand-balance-table-row .neutral {
    color: #667085;

    font-weight: 700;
}


/* ======================================================================
   DEMAND — ФОКУСНЫЙ ЦЕНОВОЙ КЕЙС
   ====================================================================== */

.demand-balance-focus-label {
    margin-bottom: 2px;

    color: #E85D75;

    font-size: 4.8px;
    line-height: 1;

    font-weight: 800;

    letter-spacing: .08em;
    text-transform: uppercase;
}


.demand-balance-focus-reason {
    margin-top: 3px;

    color: #667085;

    font-size: 5px;
    line-height: 1.2;
}


.demand-balance-focus-reason b {
    color: #14213D;
}


/* ======================================================================
   КРУПНЫЙ ВЕРДИКТ ПО ЦЕНЕ
   ====================================================================== */

.demand-balance-verdict {
    display: flex;

    align-items: center;
    justify-content: space-between;

    gap: 7px;

    margin-top: 5px;
    padding: 5px 6px;

    border-left: 3px solid #E85D75;

    background: #F7F3F4;
}


.demand-balance-verdict span {
    color: #667085;

    font-size: 4.7px;
    line-height: 1;

    font-weight: 800;

    letter-spacing: .05em;
}


.demand-balance-verdict b {
    color: #E85D75;

    font-family:
        Georgia,
        "Times New Roman",
        serif;

    font-size: 12px;
    line-height: 1;

    white-space: nowrap;
}


/* ======================================================================
   MAX MARGIN EXPLANATION
   ====================================================================== */

.demand-balance-max-explain {
    margin-top: 2px;

    color: #7A8492;

    font-family:
        Georgia,
        "Times New Roman",
        serif;

    font-size: 4.6px;
    line-height: 1.25;
}



demand-balance-metrics b.positive,
.demand-balance-table-row .positive { color: #16805E; font-weight: 700; }

.demand-balance-metrics b.negative,
.demand-balance-table-row .negative { color: #C23D58; font-weight: 700; }

.demand-balance-metrics b.neutral,
.demand-balance-table-row .neutral { color: #667085; font-weight: 700; }

.demand-balance-max {
    margin-top: 3px;
    padding: 3px 4px;
    border-left: 3px solid #8067AB;
    background: #F5F2F8;
}

.demand-balance-max-label {
    color: #8067AB;
    font-size: 3.7px;
    line-height: 1;
    font-weight: 800;
    letter-spacing: .05em;
    text-transform: uppercase;
}

.demand-balance-max-main {
    display: flex;
    align-items: baseline;
    gap: 4px;
    margin-top: 1px;
}

.demand-balance-max-main b {
    color: #14213D;
    font-family: Georgia, "Times New Roman", serif;
    font-size: 6px;
    line-height: 1;
}

.demand-balance-max-main span,
.demand-balance-max-note,
.demand-balance-max-explain {
    color: #667085;
    font-size: 3.8px;
    line-height: 1.08;
}

.demand-balance-max-note { margin-top: 1px; color: #14213D; font-weight: 700; }
.demand-balance-max-explain { margin-top: 1px; font-family: Georgia, "Times New Roman", serif; }

.demand-balance-model {
    margin-top: 3px;
    color: #7A8492;
    font-size: 3.8px;
    line-height: 1.12;
}

.demand-balance-model b { color: #14213D; }

.demand-balance-action {
    display: inline-block;
    margin-top: 3px;
    padding: 2px 5px;
    border: 1px solid #16805E;
    color: #16805E;
    background: #EDF7F2;
    font-size: 3.8px;
    line-height: 1;
    font-weight: 800;
    letter-spacing: .06em;
    text-transform: uppercase;
}




'''
