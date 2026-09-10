# gear/app/daily_sales/daily_brief/presentation/stock_style.py

STOCK_BALANCE_CSS = r"""

/* ==================================================================
   STOCK BALANCE PAGE
   ================================================================== */

.stock-balance-page {
    padding-top: 8mm;
}

.stock-balance-page .masthead {
    margin-bottom: 6px;
}

.stock-balance-page .masthead h1 {
    font-size: 26px;
}


/* ==================================================================
   KPI
   ================================================================== */

.sb2-kpi-grid {
    display: grid;

    grid-template-columns:
        repeat(4, minmax(0, 1fr));

    gap: 5px;

    margin-bottom: 6px;
}

.sb2-kpi {
    min-width: 0;
    min-height: 60px;

    padding: 6px 7px;

    border: 1px solid #D7DCE2;
    border-top: 3px solid #14213D;

    background: #FFFDF7;

    overflow: hidden;
}

.sb2-kpi-green {
    border-top-color: #93C99D;
    background: #F8FBF5;
}

.sb2-kpi-yellow {
    border-top-color: #E6CF87;
    background: #FFFBEF;
}

.sb2-kpi-rose {
    border-top-color: #E85D75;
    background: #FFF6F8;
}

.sb2-kpi-lilac {
    border-top-color: #B7A2D8;
    background: #FAF8FC;
}

.sb2-kpi-top {
    display: flex;

    justify-content: space-between;
    align-items: flex-start;

    gap: 5px;
}

.sb2-kpi-label {
    padding-top: 1px;

    color: #667085;

    font-size: 5.7px;
    line-height: 1.1;
    font-weight: 800;

    letter-spacing: .45px;

    text-transform: uppercase;
}

.sb2-kpi-icon {
    flex: 0 0 25px;

    width: 25px;
    height: 25px;
}

.sb2-kpi-icon .svg-icon {
    width: 25px !important;
    height: 25px !important;
}

.sb2-kpi-value {
    margin-top: 2px;

    color: #14213D;

    font-family:
        Georgia,
        "Times New Roman",
        serif;

    font-size: 14px;
    line-height: 1;
    font-weight: 800;

    white-space: nowrap;
}

.sb2-kpi-note {
    margin-top: 3px;

    color: #7A8494;

    font-size: 5.7px;
    line-height: 1.15;
}


/* ==================================================================
   LEAD
   ================================================================== */

.sb2-lead {
    display: grid;

    grid-template-columns:
        34px
        minmax(0, 1fr);

    gap: 7px;

    margin-bottom: 6px;

    padding: 6px 8px;

    border-left: 5px solid #FFD84D;

    background: #F4F0E6;
}

.sb2-lead-icon {
    display: flex;

    align-items: center;
    justify-content: center;
}

.sb2-lead-kicker {
    color: #E85D75;

    font-size: 5.6px;
    line-height: 1;
    font-weight: 900;

    letter-spacing: .9px;
}

.sb2-lead-text {
    margin-top: 2px;

    color: #354052;

    font-family:
        Georgia,
        "Times New Roman",
        serif;

    font-size: 7.4px;
    line-height: 1.38;

    text-align: justify;
}


/* ==================================================================
   SECTION
   ================================================================== */

.sb2-section {
    margin-top: 6px;

    padding-top: 5px;

    border-top: 3px solid #14213D;

    break-inside: avoid;
    page-break-inside: avoid;
}

.sb2-section-head {
    display: flex;

    justify-content: space-between;
    align-items: flex-end;

    gap: 8px;

    margin-bottom: 5px;
}

.sb2-kicker {
    color: #E85D75;

    font-size: 5.6px;
    line-height: 1;
    font-weight: 900;

    letter-spacing: .9px;

    text-transform: uppercase;
}

.sb2-kicker.rose {
    color: #E85D75;
}

.sb2-kicker.lilac {
    color: #8067AB;
}

.sb2-title {
    margin-top: 2px;

    color: #14213D;

    font-family:
        Georgia,
        "Times New Roman",
        serif;

    font-size: 12px;
    line-height: 1;
    font-weight: 800;
}

.sb2-head-note {
    padding-bottom: 1px;

    color: #7A8494;

    font-size: 5.4px;
    line-height: 1.1;

    text-align: right;
}


/* ==================================================================
   STOCK CONTOUR
   ================================================================== */

.sb2-contour {
    display: flex;

    width: 100%;
    height: 13px;

    overflow: hidden;

    border: 1px solid #D9DDE3;

    background: #EDF0F3;
}


/*
ВАЖНО:
НИКАКОГО ТЁМНОГО СИНЕГО В ЗАЛИВКАХ.
*/

.sb2-contour-wb {
    background: #93C99D;
}

.sb2-contour-fbs {
    background: #E89AA9;
}

.sb2-contour-transit {
    background: #B7A2D8;
}

.sb2-contour-part {
    height: 100%;
}

.sb2-contour-legend {
    display: grid;

    grid-template-columns:
        repeat(3, minmax(0, 1fr));

    gap: 5px;

    margin-top: 4px;
}

.sb2-contour-item {
    display: grid;

    grid-template-columns:
        8px
        minmax(0, 1fr);

    gap: 5px;

    align-items: center;

    min-width: 0;

    padding: 4px 6px;

    border: 1px solid #E1E3E7;

    background: #FFFDF7;
}

.sb2-contour-dot {
    width: 7px;
    height: 7px;
}

.sb2-dot-wb {
    background: #93C99D;
}

.sb2-dot-fbs {
    background: #E89AA9;
}

.sb2-dot-transit {
    background: #B7A2D8;
}

.sb2-contour-label {
    color: #667085;

    font-size: 5.2px;
    line-height: 1;
    font-weight: 800;

    text-transform: uppercase;
}

.sb2-contour-number {
    margin-top: 2px;

    color: #14213D;

    font-family:
        Georgia,
        "Times New Roman",
        serif;

    font-size: 8px;
    line-height: 1;
    font-weight: 800;
}

.sb2-contour-number span {
    margin-left: 4px;

    color: #7A8494;

    font-family: Arial, sans-serif;

    font-size: 5.4px;
    font-weight: 400;
}


/* ==================================================================
   FBS
   ================================================================== */

.sb2-fbs-grid {
    display: grid;

    grid-template-columns:
        .9fr
        1.1fr;

    gap: 6px;

    align-items: stretch;
}

.sb2-fbs-feature {
    padding: 6px 7px;

    border: 1px solid #E5CCD2;
    border-top: 3px solid #E85D75;

    background: #FFF7F8;
}

.sb2-feature-head {
    display: flex;

    justify-content: space-between;
    align-items: flex-start;

    gap: 5px;
}

.sb2-fbs-hero {
    display: flex;

    align-items: flex-end;

    gap: 8px;

    margin-top: 5px;
    margin-bottom: 5px;
}

.sb2-fbs-number {
    color: #C74E66;

    font-family:
        Georgia,
        "Times New Roman",
        serif;

    font-size: 17px;
    line-height: .95;
    font-weight: 800;

    white-space: nowrap;
}

.sb2-fbs-caption {
    padding-bottom: 1px;

    color: #7A8494;

    font-size: 5.4px;
    line-height: 1.15;
}

.sb2-fbs-stats {
    display: grid;

    grid-template-columns:
        repeat(3, minmax(0, 1fr));

    gap: 3px;
}

.sb2-fbs-stat {
    padding: 4px 5px;

    border: 1px solid #E6DADD;

    background: #FFFDF7;
}

.sb2-fbs-stat-label {
    color: #7A8494;

    font-size: 4.8px;
    line-height: 1;
    font-weight: 800;

    text-transform: uppercase;
}

.sb2-fbs-stat-value {
    margin-top: 3px;

    color: #14213D;

    font-family:
        Georgia,
        "Times New Roman",
        serif;

    font-size: 9px;
    line-height: 1;
    font-weight: 800;
}

.sb2-fbs-copy {
    margin-top: 5px;

    color: #4A5567;

    font-family:
        Georgia,
        "Times New Roman",
        serif;

    font-size: 6.1px;
    line-height: 1.38;

    text-align: justify;
}


/* ==================================================================
   FBS — УВЕЛИЧЕННЫЙ БЛОК
   ================================================================== */

.sb2-fbs-grid {
    display: grid;

    grid-template-columns:
        .9fr
        1.1fr;

    gap: 7px;

    align-items: stretch;
}


/* ------------------------------------------------------------------
   ЛЕВАЯ КАРТОЧКА — FBS ПОД ЛУПОЙ
   ------------------------------------------------------------------ */

.sb2-fbs-feature {
    padding: 9px 10px;

    min-height: 154px;

    border: 1px solid #E5CCD2;
    border-top: 4px solid #E85D75;

    background: #FFF7F8;
}

.sb2-feature-head {
    display: flex;

    justify-content: space-between;
    align-items: flex-start;

    gap: 7px;
}

.sb2-fbs-feature .sb2-kicker {
    font-size: 6.3px;
    letter-spacing: 1px;
}

.sb2-fbs-feature .sb2-title {
    margin-top: 3px;

    font-size: 15px;
    line-height: 1.05;
}


/* ------------------------------------------------------------------
   ГЛАВНАЯ ЦИФРА
   ------------------------------------------------------------------ */

.sb2-fbs-hero {
    display: flex;

    align-items: flex-end;

    gap: 10px;

    margin-top: 12px;
    margin-bottom: 8px;
}

.sb2-fbs-number {
    color: #C74E66;

    font-family:
        Georgia,
        "Times New Roman",
        serif;

    font-size: 24px;
    line-height: .95;
    font-weight: 800;

    white-space: nowrap;
}

.sb2-fbs-caption {
    padding-bottom: 2px;

    color: #7A8494;

    font-size: 6.2px;
    line-height: 1.2;
}


/* ------------------------------------------------------------------
   ТРИ ПОКАЗАТЕЛЯ
   ------------------------------------------------------------------ */

.sb2-fbs-stats {
    display: grid;

    grid-template-columns:
        repeat(3, minmax(0, 1fr));

    gap: 5px;
}

.sb2-fbs-stat {
    min-height: 38px;

    padding: 6px 7px;

    border: 1px solid #E6DADD;

    background: #FFFDF7;
}

.sb2-fbs-stat-label {
    color: #7A8494;

    font-size: 5.4px;
    line-height: 1;
    font-weight: 800;

    text-transform: uppercase;
}

.sb2-fbs-stat-value {
    margin-top: 5px;

    color: #14213D;

    font-family:
        Georgia,
        "Times New Roman",
        serif;

    font-size: 11px;
    line-height: 1;
    font-weight: 800;
}


/* ------------------------------------------------------------------
   ПОЯСНЯЮЩИЙ ТЕКСТ
   ------------------------------------------------------------------ */

.sb2-fbs-copy {
    margin-top: 8px;

    color: #4A5567;

    font-family:
        Georgia,
        "Times New Roman",
        serif;

    font-size: 7px;
    line-height: 1.42;

    text-align: justify;
}


/* ==================================================================
   ПРАВАЯ ЧАСТЬ — БРЕНДЫ + КАТЕГОРИИ
   ================================================================== */

.sb2-fbs-assortment {
    display: grid;

    grid-template-columns:
        1fr
        1px
        1fr;

    gap: 9px;

    min-height: 154px;

    padding: 9px 10px;

    border: 1px solid #D7DCE2;
    border-top: 4px solid #B7A2D8;

    background: #FFFDF7;
}

.sb2-assortment-divider {
    background: #D9DDE3;
}

.sb2-assortment-head {
    display: flex;

    justify-content: space-between;
    align-items: flex-start;

    gap: 5px;

    margin-bottom: 9px;
}

.sb2-assortment-head .sb2-kicker {
    font-size: 6.2px;
}

.sb2-mini-title {
    margin-top: 3px;

    color: #14213D;

    font-family:
        Georgia,
        "Times New Roman",
        serif;

    font-size: 9px;
    line-height: 1.12;
    font-weight: 800;
}


/* ==================================================================
   РЕЙТИНГИ БРЕНДОВ / КАТЕГОРИЙ
   ================================================================== */

.sb2-rank-row {
    display: grid;

    grid-template-columns:
        82px
        minmax(0, 1fr)
        48px;

    gap: 6px;

    align-items: center;

    margin-bottom: 8px;
}

.sb2-rank-row:last-child {
    margin-bottom: 0;
}

.sb2-rank-name {
    overflow: hidden;

    color: #354052;

    font-size: 6.3px;
    line-height: 1.1;
    font-weight: 700;

    white-space: nowrap;
    text-overflow: ellipsis;
}

.sb2-rank-track {
    height: 9px;

    overflow: hidden;

    background: #E9EDF1;
}

.sb2-rank-fill {
    height: 100%;
}

.sb2-rank-lilac {
    background: #B7A2D8;
}

.sb2-rank-rose {
    background: #E89AA9;
}

.sb2-rank-value {
    color: #14213D;

    font-size: 6.5px;
    line-height: 1;
    font-weight: 800;

    text-align: right;
}

.sb2-rank-value span {
    display: block;

    margin-top: 2px;

    color: #8A929F;

    font-size: 5px;
    font-weight: 400;
}

.sb2-empty-mini {
    padding: 12px 0;

    color: #8A929F;

    font-size: 6.5px;
}

/* ==================================================================
   БОЛЬШОЙ ГРАФИК БРЕНДОВ
   ================================================================== */

.sb2-brand-section {
    border-top-color: #B7A2D8;
}


/*
Сам график специально очень светлый.

WB    -> pastel green
FBS   -> pastel rose
Путь  -> pastel lilac
*/

.sb2-brand-chart {
    padding: 6px 8px;

    border: 1px solid #D7DCE2;

    background: #FFFDF7;
}

.sb2-brand-row {
    display: grid;

    grid-template-columns:
        95px
        minmax(0, 1fr)
        48px;

    gap: 6px;

    align-items: center;

    margin-bottom: 5px;
}

.sb2-brand-row:last-child {
    margin-bottom: 0;
}

.sb2-brand-name {
    min-width: 0;

    overflow: hidden;

    color: #14213D;

    font-size: 6.2px;
    line-height: 1;
    font-weight: 800;

    white-space: nowrap;
    text-overflow: ellipsis;
}

.sb2-brand-track {
    width: 100%;
    height: 12px;

    overflow: hidden;

    background: #EDF0F3;
}

.sb2-brand-total {
    display: flex;

    height: 100%;

    min-width: 1px;

    overflow: hidden;
}


/*
ГЛАВНЫЕ ЦВЕТА ГРАФИКА
*/

.sb2-brand-wb {
    height: 100%;

    background: #93C99D;
}

.sb2-brand-fbs {
    height: 100%;

    background: #E89AA9;
}

.sb2-brand-transit {
    height: 100%;

    background: #B7A2D8;
}

.sb2-brand-value {
    color: #14213D;

    font-family:
        Georgia,
        "Times New Roman",
        serif;

    font-size: 7.2px;
    line-height: 1;
    font-weight: 800;

    text-align: right;

    white-space: nowrap;
}

.sb2-brand-legend {
    display: flex;

    justify-content: center;

    gap: 18px;

    margin-top: 4px;

    color: #667085;

    font-size: 5.2px;
    line-height: 1;
}

.sb2-brand-legend > div {
    display: flex;

    align-items: center;

    gap: 4px;
}

.sb2-brand-legend-dot {
    width: 7px;
    height: 7px;
}

.sb2-brand-legend-dot.wb {
    background: #93C99D;
}

.sb2-brand-legend-dot.fbs {
    background: #E89AA9;
}

.sb2-brand-legend-dot.transit {
    background: #B7A2D8;
}


/* ==================================================================
   COST
   ================================================================== */

.sb2-cost-section {
    border-top-color: #8067AB;
}

.sb2-cost-grid {
    display: grid;

    grid-template-columns:
        repeat(3, minmax(0, 1fr));

    gap: 4px;
}

.sb2-cost-card {
    display: grid;

    grid-template-columns:
        29px
        minmax(0, 1fr);

    gap: 6px;

    min-height: 49px;

    padding: 5px 6px;

    border: 1px solid #D7DCE2;

    background: #FFFDF7;
}

.sb2-cost-card.accounting {
    border-top: 2px solid #93C99D;

    background: #F8FBF5;
}

.sb2-cost-card.management {
    border-top: 2px solid #B7A2D8;

    background: #FAF8FC;
}

.sb2-cost-card.difference {
    border-top: 2px solid #E89AA9;

    background: #FFF7F8;
}

.sb2-cost-icon {
    display: flex;

    justify-content: center;

    padding-top: 1px;
}

.sb2-cost-label {
    color: #667085;

    font-size: 5px;
    line-height: 1;
    font-weight: 800;

    text-transform: uppercase;
}

.sb2-cost-value {
    margin-top: 3px;

    color: #14213D;

    font-family:
        Georgia,
        "Times New Roman",
        serif;

    font-size: 10.5px;
    line-height: 1;
    font-weight: 800;

    white-space: nowrap;
}

.sb2-cost-value.negative {
    color: #C45169;
}

.sb2-cost-value.positive {
    color: #5B9568;
}

.sb2-cost-note {
    margin-top: 3px;

    color: #7A8494;

    font-size: 4.9px;
    line-height: 1.1;
}

.sb2-cost-note.negative {
    color: #C45169;
}

.sb2-cost-note.positive {
    color: #5B9568;
}


/* ==================================================================
   HEALTH
   ================================================================== */

.stock-balance-page
.stocks-health {
    margin-top: 6px;

    padding-top: 5px;

    border-top-width: 3px;
}

.stock-balance-page
.stocks-health-kicker {
    color: #8067AB;
}

.stock-balance-page
.stocks-health-title {
    font-size: 11.5px;
}

.stock-balance-page
.stocks-health-bar {
    height: 10px;
}

.stock-balance-page
.stocks-health-buckets {
    margin-top: 3px;
}

.stock-balance-page
.stocks-health-metrics {
    margin-top: 4px;
}


/* ==================================================================
   METHOD
   ================================================================== */

.sb2-method {
    display: flex;

    justify-content: space-between;

    gap: 12px;

    margin-top: 5px;

    padding-top: 4px;

    border-top: 1px solid #D7DCE2;

    color: #8A929F;

    font-size: 4.9px;
    line-height: 1.25;
}

.sb2-method span:last-child {
    flex: 1;

    text-align: right;
}


/* ==================================================================
   EMPTY
   ================================================================== */

.sb2-empty {
    display: flex;

    flex-direction: column;

    align-items: center;
    justify-content: center;

    min-height: 160mm;

    text-align: center;
}

.sb2-empty-title {
    margin-top: 8px;

    color: #14213D;

    font-family:
        Georgia,
        "Times New Roman",
        serif;

    font-size: 18px;
    font-weight: 800;
}

.sb2-empty-text {
    margin-top: 4px;

    color: #667085;

    font-size: 7px;
}


/* ==================================================================
   PDF
   ================================================================== */

.sb2-kpi-grid,
.sb2-lead,
.sb2-section,
.sb2-contour-legend,
.sb2-fbs-grid,
.sb2-brand-chart,
.sb2-cost-grid {
    break-inside: avoid;
    page-break-inside: avoid;
}

"""