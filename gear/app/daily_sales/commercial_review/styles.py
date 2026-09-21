# gear/app/daily_sales/commercial_review/styles.py
"""
Вёрстка отчёта.

Документ, а не дашборд: серифные заголовки, тёплая бумага,
тонкие линейки, нумерация разделов, живые колонтитулы.

Приёмы, на которых всё держится:
  • одна мысль — один блок, блоки не разрываются между страницами;
  • числа выровнены по правому краю и набраны моноширинными
    цифрами, чтобы разряды стояли друг под другом;
  • отрицательные значения в скобках, как в управленческой
    отчётности;
  • цвет никогда не единственный носитель смысла — рядом
    всегда подпись или значок.
"""

from __future__ import annotations

from . import config as C


CSS = f"""
@page {{
    size: A4 portrait;
    margin: 16mm 15mm 15mm 15mm;

    /* Бумага красится целиком, вместе с полями: иначе по краям
       остаётся белая рамка, и разворот выглядит как веб-страница,
       которую отправили на печать. */
    background: {C.PAGE_BG};

    @top-left {{
        content: "ТРЕНДСЕТТЕР · КОММЕРЧЕСКИЙ ОБЗОР";
        font-family: {C.SANS};
        font-size: 6.9pt;
        letter-spacing: 1.1pt;
        color: {C.MUTED};
        padding-bottom: 3mm;
        vertical-align: bottom;
    }}

    @top-right {{
        content: string(chapter);
        font-family: {C.SANS};
        font-size: 6.9pt;
        letter-spacing: 1.1pt;
        color: {C.NAVY};
        padding-bottom: 3mm;
        vertical-align: bottom;
    }}

    @bottom-left {{
        content: string(issue);
        font-family: {C.SANS};
        font-size: 6.9pt;
        color: {C.MUTED};
        padding-top: 3mm;
    }}

    @bottom-right {{
        content: "стр. " counter(page) " из " counter(pages);
        font-family: {C.SANS};
        font-size: 6.9pt;
        color: {C.MUTED};
        padding-top: 3mm;
    }}
}}

/* Широкие таблицы разворачиваем в альбом: девять колонок
   в портрете либо обрезаются, либо ужимаются до нечитаемого
   кегля. Колонтитулы у именованной страницы не наследуются,
   поэтому повторяем их здесь. */
@page landscape {{
    size: A4 landscape;
    margin: 14mm 15mm 13mm 15mm;
    background: {C.PAGE_BG};

    @top-left {{
        content: "ТРЕНДСЕТТЕР · КОММЕРЧЕСКИЙ ОБЗОР";
        font-family: {C.SANS};
        font-size: 6.9pt;
        letter-spacing: 1.1pt;
        color: {C.MUTED};
        padding-bottom: 3mm;
        vertical-align: bottom;
    }}

    @top-right {{
        content: string(chapter);
        font-family: {C.SANS};
        font-size: 6.9pt;
        letter-spacing: 1.1pt;
        color: {C.NAVY};
        padding-bottom: 3mm;
        vertical-align: bottom;
    }}

    @bottom-left {{
        content: string(issue);
        font-family: {C.SANS};
        font-size: 6.9pt;
        color: {C.MUTED};
        padding-top: 3mm;
    }}

    @bottom-right {{
        content: "стр. " counter(page) " из " counter(pages);
        font-family: {C.SANS};
        font-size: 6.9pt;
        color: {C.MUTED};
        padding-top: 3mm;
    }}
}}

.page-landscape {{
    page: landscape;
    page-break-after: always;
    page-break-before: always;
}}

/* Обложка без колонтитулов: они мешают титулу. */
@page cover {{
    margin: 0;
    background: {C.PAGE_BG};

    @top-left {{ content: none; }}
    @top-right {{ content: none; }}
    @bottom-left {{ content: none; }}
    @bottom-right {{ content: none; }}
}}

* {{
    box-sizing: border-box;
}}

html, body {{
    margin: 0;
    padding: 0;
    color: {C.INK};
    background: {C.PAGE_BG};
    font-family: {C.SANS};
    font-size: 11.2px;
    line-height: 1.5;
}}

/* ============================================================
   СТРАНИЦА И ЕЁ ШАПКА
   ============================================================ */

.page {{
    page-break-after: always;
    page-break-inside: auto;
}}

.page:last-child {{
    page-break-after: auto;
}}

.page-cover {{
    page: cover;
    page-break-after: always;
}}

/* Невидимые носители текста для колонтитулов. */
.chapter {{
    string-set: chapter content();
    position: absolute;
    left: -9999px;
    height: 0;
    overflow: hidden;
}}

.issue {{
    string-set: issue content();
    position: absolute;
    left: -9999px;
    height: 0;
    overflow: hidden;
}}

.head {{
    margin-bottom: 13px;
}}

.head-rule {{
    display: flex;
    align-items: center;
    gap: 9px;
    border-bottom: 2px solid {C.NAVY};
    padding-bottom: 5px;
    margin-bottom: 8px;
}}

.head-number {{
    font-family: {C.SERIF};
    font-size: 25px;
    font-weight: 700;
    line-height: 1;
    color: {C.NAVY};
    letter-spacing: -0.5px;
}}

.head-kicker {{
    flex: 1;
    font-size: 8px;
    font-weight: 800;
    letter-spacing: 1.7px;
    text-transform: uppercase;
    color: {C.MUTED};
}}

.head-date {{
    font-size: 8px;
    letter-spacing: 0.6px;
    color: {C.MUTED};
    white-space: nowrap;
}}

h1 {{
    font-family: {C.SERIF};
    font-size: 28px;
    line-height: 1.1;
    font-weight: 700;
    letter-spacing: -0.6px;
    margin: 0 0 8px;
}}

h2 {{
    font-family: {C.SERIF};
    font-size: 23px;
    line-height: 1.12;
    font-weight: 700;
    letter-spacing: -0.5px;
    margin: 0 0 5px;
    color: {C.INK};
    page-break-after: avoid;
}}

h3 {{
    font-family: {C.SERIF};
    font-size: 14.5px;
    font-weight: 700;
    margin: 14px 0 6px;
    color: {C.NAVY_3};
    page-break-after: avoid;
}}

h4 {{
    font-size: 8.4px;
    font-weight: 800;
    letter-spacing: 1.3px;
    text-transform: uppercase;
    color: {C.MUTED};
    margin: 0 0 4px;
    page-break-after: avoid;
}}

p {{ margin: 0 0 7px; }}

.head-note {{
    color: {C.INK_2};
    font-size: 10.6px;
    line-height: 1.5;
    margin: 0;
    max-width: none;
}}

.rule-soft {{
    height: 1px;
    background: {C.LINE_SOFT};
    margin: 14px 0;
}}

.muted {{ color: {C.MUTED}; }}
.dim {{ color: {C.INK_2}; }}
.small {{ font-size: 9.6px; }}
.tiny {{ font-size: 8.4px; }}
.pos {{ color: {C.GOOD}; }}
.neg {{ color: {C.CRITICAL}; }}

/* ============================================================
   ОБЛОЖКА
   ============================================================ */

.cover-band {{
    background: {C.NAVY};
    color: #FFFFFF;
    padding: 30mm 18mm 15mm;
}}

.cover-brand {{
    font-size: 8.8px;
    font-weight: 800;
    letter-spacing: 4.2px;
    text-transform: uppercase;
    opacity: 0.8;
    padding-bottom: 5mm;
    border-bottom: 1px solid rgba(255, 255, 255, 0.28);
    margin-bottom: 16mm;
}}

.cover-title {{
    font-family: {C.SERIF};
    font-size: 46px;
    line-height: 1.0;
    font-weight: 700;
    letter-spacing: -1.4px;
    margin: 0 0 8px;
}}

.cover-sub {{
    font-size: 13px;
    letter-spacing: 0.3px;
    opacity: 0.88;
    margin: 0;
}}

.cover-body {{ padding: 11mm 18mm 0; }}

.cover-headline {{
    border-left: 3px solid {C.NAVY};
    padding: 2px 0 2px 13px;
    font-family: {C.SERIF};
    font-size: 15.5px;
    line-height: 1.42;
    color: {C.INK};
    margin-bottom: 10mm;
}}

.agenda {{
    border-top: 1px solid {C.LINE_SOFT};
    padding-top: 9px;
    margin-bottom: 9mm;
}}

.agenda-row {{
    display: flex;
    align-items: baseline;
    gap: 12px;
    border-bottom: 1px solid {C.LINE_SOFT};
    padding: 7px 0;
}}

.agenda-metric {{
    font-family: {C.SERIF};
    font-size: 15px;
    font-weight: 700;
    color: {C.NAVY};
    width: 26mm;
    flex: none;
    font-variant-numeric: tabular-nums;
}}

.agenda-title {{
    font-size: 11.5px;
    font-weight: 700;
    line-height: 1.35;
}}

.cover-foot {{
    padding: 0 18mm;
    color: {C.MUTED};
    font-size: 9px;
    line-height: 1.5;
}}

/* ============================================================
   KPI
   ============================================================ */

.kpi-grid {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 7px;
    margin-bottom: 12px;
}}

.kpi-grid.three {{ grid-template-columns: repeat(3, 1fr); }}
.kpi-grid.two {{ grid-template-columns: repeat(2, 1fr); }}
.kpi-grid.five {{ grid-template-columns: repeat(5, 1fr); }}

.kpi {{
    border: 1px solid {C.LINE_SOFT};
    border-top: 2.5px solid {C.NAVY};
    background: {C.SURFACE};
    padding: 8px 9px 9px;
    page-break-inside: avoid;
}}

.kpi-label {{
    font-size: 8.2px;
    font-weight: 800;
    letter-spacing: 0.9px;
    text-transform: uppercase;
    color: {C.MUTED};
    line-height: 1.3;
    /* Две строки заголовка максимум: иначе значения
       в соседних карточках встают на разной высоте. */
    height: 22px;
    overflow: hidden;
}}

.kpi-value {{
    font-family: {C.SERIF};
    font-size: 21px;
    font-weight: 700;
    letter-spacing: -0.5px;
    margin: 5px 0 2px;
    white-space: nowrap;
    font-variant-numeric: tabular-nums;
}}

.kpi-delta {{
    font-size: 9.6px;
    font-weight: 700;
}}

.kpi-note {{
    font-size: 8.6px;
    color: {C.MUTED};
    line-height: 1.35;
    margin-top: 2px;
}}

/* ============================================================
   ВЫВОД
   ============================================================ */

.finding {{
    border: 1px solid {C.LINE_SOFT};
    border-left: 3px solid {C.MUTED};
    background: {C.SURFACE};
    padding: 9px 12px 10px;
    margin-bottom: 8px;
    page-break-inside: avoid;
}}

.finding-head {{
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 10px;
    margin-bottom: 5px;
}}

.finding-title {{
    font-family: {C.SERIF};
    font-size: 14px;
    font-weight: 700;
    line-height: 1.25;
}}

.finding-metric {{
    font-family: {C.SERIF};
    font-size: 15px;
    font-weight: 700;
    white-space: nowrap;
    font-variant-numeric: tabular-nums;
}}

.finding-tag {{
    display: inline-block;
    font-size: 7.8px;
    font-weight: 800;
    letter-spacing: 1px;
    text-transform: uppercase;
    padding: 2px 7px;
    margin-bottom: 6px;
}}

.finding-line {{
    font-size: 10.5px;
    line-height: 1.48;
    margin-bottom: 4px;
}}

.finding-line b {{
    color: {C.MUTED};
    font-weight: 800;
    font-size: 8.2px;
    letter-spacing: 0.9px;
    text-transform: uppercase;
}}

.finding-action {{
    background: {C.TINT_3};
    border-left: 2px solid {C.NAVY_2};
    padding: 6px 10px;
    margin-top: 6px;
    font-size: 10.5px;
    line-height: 1.48;
}}

/* ============================================================
   ГРАФИК
   ============================================================ */

.figure {{
    margin: 0 0 14px;
    page-break-inside: avoid;
}}

.figure-title {{
    font-family: {C.SERIF};
    font-size: 13px;
    font-weight: 700;
    margin-bottom: 1px;
}}

.figure-sub {{
    font-size: 9.2px;
    color: {C.MUTED};
    margin-bottom: 6px;
}}

.figure img {{
    display: block;
    width: 100%;
}}

.figure-note {{
    margin-top: 6px;
    border-top: 1px solid {C.LINE_SOFT};
    padding-top: 6px;
    font-size: 10.2px;
    line-height: 1.48;
    color: {C.INK_2};
}}

.figure-note b {{ color: {C.INK}; }}

.figure-empty {{
    border: 1px dashed {C.LINE};
    background: {C.SURFACE_SOFT};
    padding: 16px;
    text-align: center;
    color: {C.MUTED};
    font-size: 9.8px;
}}

/* ============================================================
   ТАБЛИЦА
   ============================================================ */

table.tbl {{
    width: 100%;
    border-collapse: collapse;
    font-size: 9.8px;
    margin-bottom: 9px;
    page-break-inside: auto;
}}

table.tbl thead th {{
    background: {C.NAVY};
    color: #FFFFFF;
    font-size: 8.2px;
    font-weight: 800;
    letter-spacing: 0.6px;
    text-transform: uppercase;
    text-align: left;
    padding: 6px;
    line-height: 1.25;
}}

table.tbl thead {{ display: table-header-group; }}

table.tbl th.num,
table.tbl td.num {{
    text-align: right;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
}}

table.tbl tbody td {{
    padding: 4px 6px;
    border-bottom: 1px solid {C.LINE_SOFT};
    vertical-align: top;
}}

table.tbl tbody tr:nth-child(even) td {{
    background: {C.SURFACE_SOFT};
}}

table.tbl tbody tr.total td {{
    background: {C.TINT};
    font-weight: 800;
    border-top: 2px solid {C.NAVY};
    border-bottom: none;
}}

/* Зебра задана через :nth-child и по специфичности сильнее
   простого класса, поэтому подсветку пишем так же «весомо» —
   иначе строки-минусы остаются незакрашенными. */
table.tbl tbody tr.alert td,
table.tbl tbody tr.alert:nth-child(even) td,
table.tbl tbody tr.alert:nth-child(odd) td {{
    background: {C.CRITICAL_BG};
}}

table.tbl caption {{
    caption-side: top;
    text-align: left;
    font-family: {C.SERIF};
    font-size: 13px;
    font-weight: 700;
    padding-bottom: 5px;
}}

table.tbl.wide {{
    font-size: 9.2px;
}}

table.tbl.wide thead th {{
    font-size: 7.8px;
    padding: 5px;
}}

table.tbl.wide tbody td {{
    padding: 3.5px 5px;
}}

.table-note {{
    font-size: 9px;
    color: {C.MUTED};
    margin: -4px 0 12px;
}}

/* ============================================================
   БЛОКИ
   ============================================================ */

.two {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 11px;
    align-items: start;
}}

.two-wide {{
    display: grid;
    grid-template-columns: 1.45fr 1fr;
    gap: 11px;
    align-items: start;
}}

.callout {{
    border: 1px solid {C.LINE_SOFT};
    border-left: 3px solid {C.NAVY};
    background: {C.TINT_3};
    padding: 9px 12px;
    margin-bottom: 11px;
    font-size: 10.5px;
    line-height: 1.5;
    page-break-inside: avoid;
}}

.callout h4 {{ color: {C.NAVY}; margin-bottom: 3px; }}

.callout.plain {{
    background: {C.SURFACE_SOFT};
    border-left-color: {C.LINE};
}}

.bullets {{
    margin: 0 0 10px;
    padding-left: 15px;
    font-size: 10.5px;
    line-height: 1.5;
}}

.bullets li {{ margin-bottom: 5px; }}

/* Прогресс-полоса выполнения плана. */
.bullet-bar {{ margin-bottom: 12px; page-break-inside: avoid; }}

.bullet-track {{
    position: relative;
    height: 22px;
    background: {C.LINE_SOFT};
}}

.bullet-fill {{ height: 22px; background: {C.NAVY}; }}

.bullet-marker {{
    position: absolute;
    top: -4px;
    width: 2px;
    height: 30px;
    background: {C.SERIES_2};
}}

.bullet-legend {{
    display: flex;
    justify-content: space-between;
    font-size: 9px;
    color: {C.MUTED};
    margin-top: 5px;
}}

/* ============================================================
   КАЛЕНДАРЬ ВЫРУЧКИ
   ============================================================ */

.cal {{
    width: 100%;
    border-collapse: separate;
    border-spacing: 3px;
    margin-bottom: 6px;
    page-break-inside: avoid;
}}

.cal th {{
    font-size: 8.4px;
    font-weight: 700;
    color: {C.MUTED};
    text-align: center;
    padding-bottom: 1px;
}}

.cal th.cal-week-head {{
    text-align: right;
    color: {C.INK};
    padding-right: 6px;
}}

.cal td {{
    width: 12%;
    height: 44px;
    vertical-align: top;
    padding: 5px 6px;
    border: 1px solid {C.LINE_SOFT};
}}

.cal td.cal-empty {{
    background: {C.SURFACE_SOFT};
    border-color: {C.LINE_SOFT};
}}

.cal-date {{
    font-size: 9.4px;
    font-weight: 800;
    line-height: 1.1;
}}

.cal-value {{
    font-size: 9.2px;
    font-variant-numeric: tabular-nums;
    margin-top: 11px;
}}

.cal td.cal-week {{
    width: 16%;
    background: {C.SURFACE_SOFT};
    border-color: {C.LINE};
}}

.cal-week-label {{
    font-size: 7.6px;
    font-weight: 800;
    letter-spacing: 0.9px;
    text-transform: uppercase;
    color: {C.MUTED};
}}

.cal-week-value {{
    font-family: {C.SERIF};
    font-size: 13.5px;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
    line-height: 1.2;
    margin: 1px 0;
}}

.cal-week-delta {{
    font-size: 8.4px;
    font-weight: 700;
}}

.cal-week-extra {{
    font-size: 7.3px;
    font-weight: 600;
    color: {C.MUTED};
    margin-top: 2px;
    line-height: 1.15;
}}

.cal-legend {{
    display: flex;
    justify-content: space-between;
    font-size: 8.6px;
    color: {C.MUTED};
    margin-bottom: 13px;
}}

/* ============================================================
   ПЛИТКИ НЕДЕЛЬ
   ============================================================ */

.wtiles {{
    display: grid;
    gap: 5px;
    margin-bottom: 7px;
    page-break-inside: avoid;
}}

.wtile {{
    border: 1px solid {C.LINE_SOFT};
    padding: 6px 5px 7px;
    text-align: center;
}}

.wtile.current {{
    border: 2px solid {C.NAVY};
}}

.wtile-label {{
    font-size: 7.6px;
    font-weight: 800;
    letter-spacing: 0.7px;
    color: {C.INK_2};
}}

.wtile-dates {{
    font-size: 7px;
    color: {C.MUTED};
    margin-bottom: 4px;
}}

.wtile-value {{
    font-family: {C.SERIF};
    font-size: 16px;
    font-weight: 700;
    letter-spacing: -0.4px;
    font-variant-numeric: tabular-nums;
    line-height: 1.1;
}}

.wtile-amount {{
    font-size: 8px;
    color: {C.INK_2};
    margin-top: 3px;
    font-variant-numeric: tabular-nums;
}}

.wtile-note {{
    font-size: 6.8px;
    color: {C.MUTED};
    margin-top: 1px;
}}

/* ============================================================
   ОГЛАВЛЕНИЕ
   ============================================================ */

.toc {{ margin-top: 8px; }}

.toc-row {{
    display: flex;
    align-items: baseline;
    gap: 9px;
    border-bottom: 1px solid {C.LINE_SOFT};
    padding: 6px 0 5px;
    font-size: 10.8px;
    text-decoration: none;
    color: {C.INK};
}}

.toc-num {{
    font-family: {C.SERIF};
    font-size: 12.5px;
    font-weight: 700;
    color: {C.NAVY};
    width: 24px;
    flex: none;
}}

.toc-name {{ font-weight: 700; width: 62mm; flex: none; }}

.toc-what {{
    color: {C.MUTED};
    font-size: 9.4px;
    flex: 1;
}}

.toc-page {{
    color: {C.INK_2};
    font-weight: 700;
    white-space: nowrap;
    font-variant-numeric: tabular-nums;
}}

/* Номер страницы подтягивается из PDF по якорю ссылки —
   его не нужно вычислять руками и он не разъедется с версткой.
   Если движок рендера не понимает target-counter, колонка
   просто остаётся пустой: на кликабельность оглавления
   это не влияет. */
.toc-row::after {{
    content: target-counter(attr(href), page);
    color: {C.INK_2};
    font-weight: 700;
    font-family: {C.SERIF};
    white-space: nowrap;
    font-variant-numeric: tabular-nums;
    margin-left: auto;
    padding-left: 9px;
}}

/* Легенда цветов состояния. */
.legend {{
    display: flex;
    gap: 15px;
    flex-wrap: wrap;
    font-size: 9px;
    color: {C.INK_2};
    margin-bottom: 10px;
}}

.legend i {{
    display: inline-block;
    width: 9px;
    height: 9px;
    margin-right: 5px;
    vertical-align: -1px;
}}

.source {{
    margin-top: 12px;
    border-top: 1px solid {C.LINE_SOFT};
    padding-top: 6px;
    font-size: 8.4px;
    color: {C.MUTED};
    line-height: 1.45;
}}
"""
