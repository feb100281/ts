
<style>
body {
    font-family: Arial, Helvetica, sans-serif;
    font-size: 12px;
    line-height: 1.45;
    color: #1f2937;
    margin: 22px;
}

h1, h2, h3 {
    color: #111827;
    margin-top: 18px;
    margin-bottom: 8px;
}

h1 {
    font-size: 22px;
    border-bottom: 2px solid #d1d5db;
    padding-bottom: 6px;
}

h2 {
    font-size: 16px;
    border-left: 4px solid #374151;
    padding-left: 8px;
}

h3 {
    font-size: 13px;
}

p, li {
    margin: 5px 0;
}

.small-note {
    color: #6b7280;
    font-size: 10px;
}

table.report-table {
    width: 100%;
    border-collapse: collapse;
    margin: 12px 0 18px 0;
    font-size: 10.5px;
    table-layout: fixed;
}

table.report-table th,
table.report-table td {
    border: 1px solid #d1d5db;
    padding: 6px 7px;
    vertical-align: middle;
    word-wrap: break-word;
}

table.report-table th {
    background: #f3f4f6;
    text-align: center;
    font-weight: 700;
}

table.report-table td.num {
    text-align: right;
    white-space: nowrap;
}

table.report-table td.center {
    text-align: center;
}

table.report-table tr:nth-child(even) {
    background: #fafafa;
}

.kpi-grid {
    width: 100%;
    margin: 14px 0 18px 0;
    border-collapse: separate;
    border-spacing: 10px;
}

.kpi-card {
    border: 1px solid #d1d5db;
    background: #f9fafb;
    padding: 10px 12px;
    border-radius: 8px;
}

.kpi-title {
    font-size: 10px;
    color: #6b7280;
    text-transform: uppercase;
    margin-bottom: 4px;
}

.kpi-value {
    font-size: 16px;
    font-weight: 700;
    color: #111827;
}

.page-break {
    page-break-before: always;
}

.chart-caption {
    font-size: 10px;
    color: #6b7280;
    margin-top: -4px;
    margin-bottom: 8px;
}
</style>


# Прогноз выручки

**Дата последнего факта:** 2026-03-25

## 1. Executive summary

- Выручка **2025** года составила **1 257 633 931 руб.**
- Изменение к предыдущему году: **190 509 295 руб.** (**17,9%**).
- Факт **2026 YTD**: **305 727 187 руб.**
- Прогноз на остаток **2026**: **1 316 732 601 руб.**
- Ожидаемый итог **2026**: **1 622 459 788 руб.**
- Доля прогнозной части в ожидаемом результате года: **81,2%**.
- Ожидаемое изменение к предыдущему году: **364 825 857 руб.** (**29,0%**).
- По текущему месяцу **2026-03**: факт MTD — **103 613 926 руб.**, прогноз до конца месяца — **21 556 964 руб.**, ожидаемый итог месяца — **125 170 890 руб.**
- За последние 12 месяцев выручка составила **1 622 459 788 руб.**, среднемесячный уровень — **135 204 982 руб.**
- Максимальный месяц: **2026-09** (**194 981 697 руб.**), минимальный месяц: **2026-01** (**88 331 967 руб.**).
- Совокупная будущая доходная часть по месяцам с прогнозом составляет **1 420 346 528 руб.**, средний прогнозный месяц — **142 034 653 руб.**.
- Наиболее сильные прогнозные месяцы: **2026-09 — 194 981 697 руб.; 2026-10 — 173 103 933 руб.; 2026-12 — 159 238 363 руб.**.

## 2. Подход к отражению данных

- Для завершенных лет в отчете отражается только фактическая выручка.
- Для текущего года отражается факт с начала года плюс прогноз на остаток периода.
- Для текущего месяца используется комбинированный подход: факт MTD + прогноз до конца месяца.
- Для будущих месяцев и лет отражается прогнозная выручка.

## 3. Комментарий по динамике

Наиболее сильные месяцы по приросту к аналогичному месяцу прошлого года:

- **2025-06**: 80 320 291 руб. (162,2%).
- **2026-10**: 69 107 698 руб. (66,5%).
- **2026-11**: 62 743 154 руб. (90,2%).

Наиболее слабые месяцы по сравнению с аналогичным месяцем прошлого года:

- **2025-11**: -46 440 670 руб. (-40,0%).
- **2026-01**: -28 470 143 руб. (-24,4%).
- **2025-10**: -24 154 858 руб. (-18,8%).


## 4. Графики

### 4.1. Помесячная динамика факта и прогноза
![](/Users/daria/Documents/Projects/ts/utils/forecast/output/charts/plan_fact_monthly.png)
<div class="chart-caption">Основной график для оценки уровня выручки, перехода от факта к прогнозу и общей траектории.</div>

### 4.2. Изменение к аналогичному месяцу прошлого года
![](/Users/daria/Documents/Projects/ts/utils/forecast/output/charts/yoy_change_monthly.png)
<div class="chart-caption">Показывает месяцы, формирующие рост или просадку относительно прошлого года.</div>

### 4.3. Формирование итога текущего года по месяцам
![](/Users/daria/Documents/Projects/ts/utils/forecast/output/charts/waterfall_current_year.png)
<div class="chart-caption">Показывает вклад каждого месяца в ожидаемый годовой результат.</div>

### 4.4. Квартальная динамика
![](/Users/daria/Documents/Projects/ts/utils/forecast/output/charts/quarterly_revenue.png)
<div class="chart-caption">Сглаженный взгляд на динамику без избыточного месячного шума.</div>

<div class="page-break"></div>

## 5. Сводка по годам

<table class="report-table"><thead><tr><th>Год</th><th>Факт</th><th>Прогноз</th><th>Итог</th><th>Статус года</th><th>Изменение к пред. году, ₽</th><th>Изменение к пред. году, %</th></tr></thead><tbody><tr><td class="center">2 024</td><td class="num">1 067 124 636</td><td class="">—</td><td class="num">1 067 124 636</td><td class="">Факт</td><td class="">—</td><td class="">—</td></tr><tr><td class="center">2 025</td><td class="num">1 257 633 931</td><td class="">—</td><td class="num">1 257 633 931</td><td class="">Факт</td><td class="num">190 509 295</td><td class="num">17,9%</td></tr><tr><td class="center">2 026</td><td class="num">305 727 187</td><td class="num">1 316 732 601</td><td class="num">1 622 459 788</td><td class="">Текущий год: факт + прогноз</td><td class="num">364 825 857</td><td class="num">29,0%</td></tr></tbody></table>

## 6. Сводка по кварталам

<table class="report-table"><thead><tr><th>Квартал</th><th>Факт</th><th>Прогноз</th><th>Итог</th><th>Изменение к пред. кварталу, ₽</th><th>Изменение к пред. кварталу, %</th></tr></thead><tbody><tr><td class="">2024Q1</td><td class="num">259 374 609</td><td class="num">0</td><td class="num">259 374 609</td><td class="">—</td><td class="">—</td></tr><tr><td class="">2024Q2</td><td class="num">204 780 056</td><td class="num">0</td><td class="num">204 780 056</td><td class="num">-54 594 553</td><td class="num">-21,0%</td></tr><tr><td class="">2024Q3</td><td class="num">234 149 589</td><td class="num">0</td><td class="num">234 149 589</td><td class="num">29 369 533</td><td class="num">14,3%</td></tr><tr><td class="">2024Q4</td><td class="num">368 820 382</td><td class="num">0</td><td class="num">368 820 382</td><td class="num">134 670 793</td><td class="num">57,5%</td></tr><tr><td class="">2025Q1</td><td class="num">316 403 200</td><td class="num">0</td><td class="num">316 403 200</td><td class="num">-52 417 181</td><td class="num">-14,2%</td></tr><tr><td class="">2025Q2</td><td class="num">338 154 256</td><td class="num">0</td><td class="num">338 154 256</td><td class="num">21 751 055</td><td class="num">6,9%</td></tr><tr><td class="">2025Q3</td><td class="num">318 428 478</td><td class="num">0</td><td class="num">318 428 478</td><td class="num">-19 725 778</td><td class="num">-5,8%</td></tr><tr><td class="">2025Q4</td><td class="num">284 647 997</td><td class="num">0</td><td class="num">284 647 997</td><td class="num">-33 780 481</td><td class="num">-10,6%</td></tr><tr><td class="">2026Q1</td><td class="num">305 727 187</td><td class="num">21 556 964</td><td class="num">327 284 151</td><td class="num">42 636 154</td><td class="num">15,0%</td></tr><tr><td class="">2026Q2</td><td class="num">0</td><td class="num">398 689 671</td><td class="num">398 689 671</td><td class="num">71 405 520</td><td class="num">21,8%</td></tr><tr><td class="">2026Q3</td><td class="num">0</td><td class="num">431 820 041</td><td class="num">431 820 041</td><td class="num">33 130 370</td><td class="num">8,3%</td></tr><tr><td class="">2026Q4</td><td class="num">0</td><td class="num">464 665 925</td><td class="num">464 665 925</td><td class="num">32 845 883</td><td class="num">7,6%</td></tr></tbody></table>

<div class="page-break"></div>

## 7. Сводка по месяцам

<table class="report-table"><thead><tr><th>Месяц</th><th>Статус месяца</th><th>Факт</th><th>Прогноз</th><th>Итог</th><th>Доля факта в месяце, %</th><th>Доля прогноза в месяце, %</th></tr></thead><tbody><tr><td class="">2024-01</td><td class="">Факт</td><td class="num">59 898 066</td><td class="num">0</td><td class="num">59 898 066</td><td class="num">100,0%</td><td class="num">0,0%</td></tr><tr><td class="">2024-02</td><td class="">Факт</td><td class="num">93 707 199</td><td class="num">0</td><td class="num">93 707 199</td><td class="num">100,0%</td><td class="num">0,0%</td></tr><tr><td class="">2024-03</td><td class="">Факт</td><td class="num">105 769 344</td><td class="num">0</td><td class="num">105 769 344</td><td class="num">100,0%</td><td class="num">0,0%</td></tr><tr><td class="">2024-04</td><td class="">Факт</td><td class="num">87 573 602</td><td class="num">0</td><td class="num">87 573 602</td><td class="num">100,0%</td><td class="num">0,0%</td></tr><tr><td class="">2024-05</td><td class="">Факт</td><td class="num">67 684 867</td><td class="num">0</td><td class="num">67 684 867</td><td class="num">100,0%</td><td class="num">0,0%</td></tr><tr><td class="">2024-06</td><td class="">Факт</td><td class="num">49 521 587</td><td class="num">0</td><td class="num">49 521 587</td><td class="num">100,0%</td><td class="num">0,0%</td></tr><tr><td class="">2024-07</td><td class="">Факт</td><td class="num">54 647 434</td><td class="num">0</td><td class="num">54 647 434</td><td class="num">100,0%</td><td class="num">0,0%</td></tr><tr><td class="">2024-08</td><td class="">Факт</td><td class="num">68 229 139</td><td class="num">0</td><td class="num">68 229 139</td><td class="num">100,0%</td><td class="num">0,0%</td></tr><tr><td class="">2024-09</td><td class="">Факт</td><td class="num">111 273 016</td><td class="num">0</td><td class="num">111 273 016</td><td class="num">100,0%</td><td class="num">0,0%</td></tr><tr><td class="">2024-10</td><td class="">Факт</td><td class="num">128 151 094</td><td class="num">0</td><td class="num">128 151 094</td><td class="num">100,0%</td><td class="num">0,0%</td></tr><tr><td class="">2024-11</td><td class="">Факт</td><td class="num">116 021 145</td><td class="num">0</td><td class="num">116 021 145</td><td class="num">100,0%</td><td class="num">0,0%</td></tr><tr><td class="">2024-12</td><td class="">Факт</td><td class="num">124 648 143</td><td class="num">0</td><td class="num">124 648 143</td><td class="num">100,0%</td><td class="num">0,0%</td></tr><tr><td class="">2025-01</td><td class="">Факт</td><td class="num">116 802 110</td><td class="num">0</td><td class="num">116 802 110</td><td class="num">100,0%</td><td class="num">0,0%</td></tr><tr><td class="">2025-02</td><td class="">Факт</td><td class="num">101 522 884</td><td class="num">0</td><td class="num">101 522 884</td><td class="num">100,0%</td><td class="num">0,0%</td></tr><tr><td class="">2025-03</td><td class="">Факт</td><td class="num">98 078 207</td><td class="num">0</td><td class="num">98 078 207</td><td class="num">100,0%</td><td class="num">0,0%</td></tr><tr><td class="">2025-04</td><td class="">Факт</td><td class="num">87 812 987</td><td class="num">0</td><td class="num">87 812 987</td><td class="num">100,0%</td><td class="num">0,0%</td></tr><tr><td class="">2025-05</td><td class="">Факт</td><td class="num">120 499 391</td><td class="num">0</td><td class="num">120 499 391</td><td class="num">100,0%</td><td class="num">0,0%</td></tr><tr><td class="">2025-06</td><td class="">Факт</td><td class="num">129 841 878</td><td class="num">0</td><td class="num">129 841 878</td><td class="num">100,0%</td><td class="num">0,0%</td></tr><tr><td class="">2025-07</td><td class="">Факт</td><td class="num">89 850 643</td><td class="num">0</td><td class="num">89 850 643</td><td class="num">100,0%</td><td class="num">0,0%</td></tr><tr><td class="">2025-08</td><td class="">Факт</td><td class="num">87 161 959</td><td class="num">0</td><td class="num">87 161 959</td><td class="num">100,0%</td><td class="num">0,0%</td></tr><tr><td class="">2025-09</td><td class="">Факт</td><td class="num">141 415 875</td><td class="num">0</td><td class="num">141 415 875</td><td class="num">100,0%</td><td class="num">0,0%</td></tr><tr><td class="">2025-10</td><td class="">Факт</td><td class="num">103 996 235</td><td class="num">0</td><td class="num">103 996 235</td><td class="num">100,0%</td><td class="num">0,0%</td></tr><tr><td class="">2025-11</td><td class="">Факт</td><td class="num">69 580 475</td><td class="num">0</td><td class="num">69 580 475</td><td class="num">100,0%</td><td class="num">0,0%</td></tr><tr><td class="">2025-12</td><td class="">Факт</td><td class="num">111 071 287</td><td class="num">0</td><td class="num">111 071 287</td><td class="num">100,0%</td><td class="num">0,0%</td></tr><tr><td class="">2026-01</td><td class="">Факт</td><td class="num">88 331 967</td><td class="num">0</td><td class="num">88 331 967</td><td class="num">100,0%</td><td class="num">0,0%</td></tr><tr><td class="">2026-02</td><td class="">Факт</td><td class="num">113 781 294</td><td class="num">0</td><td class="num">113 781 294</td><td class="num">100,0%</td><td class="num">0,0%</td></tr><tr><td class="">2026-03</td><td class="">Текущий месяц</td><td class="num">103 613 926</td><td class="num">21 556 964</td><td class="num">125 170 890</td><td class="num">82,8%</td><td class="num">17,2%</td></tr><tr><td class="">2026-04</td><td class="">Прогноз</td><td class="num">0</td><td class="num">110 506 762</td><td class="num">110 506 762</td><td class="num">0,0%</td><td class="num">100,0%</td></tr><tr><td class="">2026-05</td><td class="">Прогноз</td><td class="num">0</td><td class="num">138 520 187</td><td class="num">138 520 187</td><td class="num">0,0%</td><td class="num">100,0%</td></tr><tr><td class="">2026-06</td><td class="">Прогноз</td><td class="num">0</td><td class="num">149 662 722</td><td class="num">149 662 722</td><td class="num">0,0%</td><td class="num">100,0%</td></tr><tr><td class="">2026-07</td><td class="">Прогноз</td><td class="num">0</td><td class="num">116 636 791</td><td class="num">116 636 791</td><td class="num">0,0%</td><td class="num">100,0%</td></tr><tr><td class="">2026-08</td><td class="">Прогноз</td><td class="num">0</td><td class="num">120 201 553</td><td class="num">120 201 553</td><td class="num">0,0%</td><td class="num">100,0%</td></tr><tr><td class="">2026-09</td><td class="">Прогноз</td><td class="num">0</td><td class="num">194 981 697</td><td class="num">194 981 697</td><td class="num">0,0%</td><td class="num">100,0%</td></tr><tr><td class="">2026-10</td><td class="">Прогноз</td><td class="num">0</td><td class="num">173 103 933</td><td class="num">173 103 933</td><td class="num">0,0%</td><td class="num">100,0%</td></tr><tr><td class="">2026-11</td><td class="">Прогноз</td><td class="num">0</td><td class="num">132 323 628</td><td class="num">132 323 628</td><td class="num">0,0%</td><td class="num">100,0%</td></tr><tr><td class="">2026-12</td><td class="">Прогноз</td><td class="num">0</td><td class="num">159 238 363</td><td class="num">159 238 363</td><td class="num">0,0%</td><td class="num">100,0%</td></tr></tbody></table>

## 8. Сводка по месяцам: динамика

<table class="report-table"><thead><tr><th>Месяц</th><th>Изменение к пред. месяцу, ₽</th><th>Изменение к пред. месяцу, %</th><th>Изменение к тому же месяцу прошлого года, ₽</th><th>Изменение к тому же месяцу прошлого года, %</th></tr></thead><tbody><tr><td class="">2024-01</td><td class="">—</td><td class="">—</td><td class="">—</td><td class="">—</td></tr><tr><td class="">2024-02</td><td class="num">33 809 133</td><td class="num">56,4%</td><td class="">—</td><td class="">—</td></tr><tr><td class="">2024-03</td><td class="num">12 062 145</td><td class="num">12,9%</td><td class="">—</td><td class="">—</td></tr><tr><td class="">2024-04</td><td class="num">-18 195 742</td><td class="num">-17,2%</td><td class="">—</td><td class="">—</td></tr><tr><td class="">2024-05</td><td class="num">-19 888 736</td><td class="num">-22,7%</td><td class="">—</td><td class="">—</td></tr><tr><td class="">2024-06</td><td class="num">-18 163 279</td><td class="num">-26,8%</td><td class="">—</td><td class="">—</td></tr><tr><td class="">2024-07</td><td class="num">5 125 847</td><td class="num">10,4%</td><td class="">—</td><td class="">—</td></tr><tr><td class="">2024-08</td><td class="num">13 581 705</td><td class="num">24,9%</td><td class="">—</td><td class="">—</td></tr><tr><td class="">2024-09</td><td class="num">43 043 878</td><td class="num">63,1%</td><td class="">—</td><td class="">—</td></tr><tr><td class="">2024-10</td><td class="num">16 878 077</td><td class="num">15,2%</td><td class="">—</td><td class="">—</td></tr><tr><td class="">2024-11</td><td class="num">-12 129 949</td><td class="num">-9,5%</td><td class="">—</td><td class="">—</td></tr><tr><td class="">2024-12</td><td class="num">8 626 999</td><td class="num">7,4%</td><td class="">—</td><td class="">—</td></tr><tr><td class="">2025-01</td><td class="num">-7 846 034</td><td class="num">-6,3%</td><td class="num">56 904 044</td><td class="num">95,0%</td></tr><tr><td class="">2025-02</td><td class="num">-15 279 226</td><td class="num">-13,1%</td><td class="num">7 815 685</td><td class="num">8,3%</td></tr><tr><td class="">2025-03</td><td class="num">-3 444 677</td><td class="num">-3,4%</td><td class="num">-7 691 138</td><td class="num">-7,3%</td></tr><tr><td class="">2025-04</td><td class="num">-10 265 220</td><td class="num">-10,5%</td><td class="num">239 384</td><td class="num">0,3%</td></tr><tr><td class="">2025-05</td><td class="num">32 686 405</td><td class="num">37,2%</td><td class="num">52 814 524</td><td class="num">78,0%</td></tr><tr><td class="">2025-06</td><td class="num">9 342 487</td><td class="num">7,8%</td><td class="num">80 320 291</td><td class="num">162,2%</td></tr><tr><td class="">2025-07</td><td class="num">-39 991 235</td><td class="num">-30,8%</td><td class="num">35 203 209</td><td class="num">64,4%</td></tr><tr><td class="">2025-08</td><td class="num">-2 688 684</td><td class="num">-3,0%</td><td class="num">18 932 821</td><td class="num">27,7%</td></tr><tr><td class="">2025-09</td><td class="num">54 253 916</td><td class="num">62,2%</td><td class="num">30 142 859</td><td class="num">27,1%</td></tr><tr><td class="">2025-10</td><td class="num">-37 419 640</td><td class="num">-26,5%</td><td class="num">-24 154 858</td><td class="num">-18,8%</td></tr><tr><td class="">2025-11</td><td class="num">-34 415 761</td><td class="num">-33,1%</td><td class="num">-46 440 670</td><td class="num">-40,0%</td></tr><tr><td class="">2025-12</td><td class="num">41 490 812</td><td class="num">59,6%</td><td class="num">-13 576 856</td><td class="num">-10,9%</td></tr><tr><td class="">2026-01</td><td class="num">-22 739 320</td><td class="num">-20,5%</td><td class="num">-28 470 143</td><td class="num">-24,4%</td></tr><tr><td class="">2026-02</td><td class="num">25 449 327</td><td class="num">28,8%</td><td class="num">12 258 410</td><td class="num">12,1%</td></tr><tr><td class="">2026-03</td><td class="num">11 389 597</td><td class="num">10,0%</td><td class="num">27 092 684</td><td class="num">27,6%</td></tr><tr><td class="">2026-04</td><td class="num">-14 664 128</td><td class="num">-11,7%</td><td class="num">22 693 775</td><td class="num">25,8%</td></tr><tr><td class="">2026-05</td><td class="num">28 013 425</td><td class="num">25,3%</td><td class="num">18 020 796</td><td class="num">15,0%</td></tr><tr><td class="">2026-06</td><td class="num">11 142 535</td><td class="num">8,0%</td><td class="num">19 820 844</td><td class="num">15,3%</td></tr><tr><td class="">2026-07</td><td class="num">-33 025 931</td><td class="num">-22,1%</td><td class="num">26 786 148</td><td class="num">29,8%</td></tr><tr><td class="">2026-08</td><td class="num">3 564 762</td><td class="num">3,1%</td><td class="num">33 039 594</td><td class="num">37,9%</td></tr><tr><td class="">2026-09</td><td class="num">74 780 144</td><td class="num">62,2%</td><td class="num">53 565 821</td><td class="num">37,9%</td></tr><tr><td class="">2026-10</td><td class="num">-21 877 763</td><td class="num">-11,2%</td><td class="num">69 107 698</td><td class="num">66,5%</td></tr><tr><td class="">2026-11</td><td class="num">-40 780 305</td><td class="num">-23,6%</td><td class="num">62 743 154</td><td class="num">90,2%</td></tr><tr><td class="">2026-12</td><td class="num">26 914 734</td><td class="num">20,3%</td><td class="num">48 167 076</td><td class="num">43,4%</td></tr></tbody></table>
