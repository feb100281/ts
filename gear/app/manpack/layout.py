# gear/app/manpack/layout.py
from __future__ import annotations

from datetime import date

import dash_mantine_components as dmc
from dash import dcc, html

from . import data
from .config import (CONTENT_ID, EXPORTS, LOANS_APP_URL, METHOD_BTN_ID, METHOD_MODAL_ID, MONTH_ID, PACK_BTN_ID, PACK_DL_ID,
                     PACK_STATUS_ID, TAB_ID, TABS, x_dl)
from . import methodology
from .theme import icon, month_title
from ..daily_sales.assistant import assistant_widget


def _tab_label(icon_name, text):
    return dmc.Group(gap=7, justify="center", wrap="nowrap",
                     children=[icon(icon_name, 16), html.Span(text, className="ds-tab-text")])


def _months():
    """Месяцы для выбора — без обращения к данным, чтобы страница открывалась сразу."""
    try:
        from gear.management.commands.mp import DEFAULT_START_YEAR as start_year
    except Exception:
        start_year = date.today().year - 1
    cur = data.month_end(date.today())
    out, m = [], cur
    while m.year >= start_year:
        out.append(m)
        m = data.prev_month_end(m)
    return out


def layout():
    months = _months()
    # в первые дни месяца данных за него ещё нет — открываем прошлый месяц
    default = months[1] if date.today().day <= 5 and len(months) > 1 else months[0]
    return dmc.MantineProvider(
        withCssVariables=True, withGlobalClasses=True,
        children=html.Div(className="mp-page", children=[
            html.Div(className="mp-top", children=[
                html.Div(className="mp-top-title", children=[
                    html.Div("Управленческий пакет", className="mp-title"),
                    html.Div("P&L · прогноз · деньги · займы · договоры · приходы · курсы валют",
                             className="mp-subtitle"),
                ]),
                html.Div(className="mp-top-actions", children=[
                    dmc.Select(
                        id=MONTH_ID, value=default.isoformat(), allowDeselect=False,
                        data=[{"value": m.isoformat(), "label": month_title(m)} for m in months],
                        radius=0, size="sm", w=190, comboboxProps={"zIndex": 10020},
                        leftSection=icon("solar:calendar-linear", 16),
                    ),
                    dmc.Button("Методика", id=METHOD_BTN_ID, n_clicks=0, radius=0, size="sm",
                               variant="default", className="ds-head-btn",
                               leftSection=icon("solar:lightbulb-minimalistic-linear", 16)),
                    html.A(dmc.Button("Займы", radius=0, size="sm", variant="default",
                                      className="ds-head-btn",
                                      leftSection=icon("solar:hand-money-linear", 16)),
                           href=LOANS_APP_URL, target="_blank"),
                    dmc.Button("Мэн пак, Excel", id=PACK_BTN_ID, n_clicks=0, radius=0,
                               size="sm", color="#2F6656", className="ds-head-btn primary",
                               leftSection=icon("solar:download-minimalistic-bold", 16)),
                ]),
            ]),
            dcc.Loading(type="dot", color="#2F6656",
                        children=html.Div(id=PACK_STATUS_ID, className="mp-pack-status")),
            dmc.SegmentedControl(
                id=TAB_ID, value="overview", fullWidth=True, radius=0, size="sm",
                color="#2F6656", withItemsBorders=False, className="ds-tabs mp-tabs",
                data=[{"value": k, "label": _tab_label(ic, t)} for k, t, ic in TABS],
            ),
            dcc.Loading(type="dot", color="#2F6656", delay_show=150,
                        children=html.Div(id=CONTENT_ID, className="mp-content")),
            dmc.Modal(id=METHOD_MODAL_ID, title="Как мы считаем", size="xl", radius=0,
                      zIndex=10030, children=methodology.content()),
            dcc.Download(id=PACK_DL_ID),
            *[dcc.Download(id=x_dl(k)) for k in EXPORTS],
            assistant_widget("finance"),
        ]),
    )
