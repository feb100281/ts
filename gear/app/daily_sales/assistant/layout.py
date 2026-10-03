# gear/app/daily_sales/assistant/layout.py
from __future__ import annotations

from dash import dcc, html
from dash_iconify import DashIconify

from .ids import (
    ASSISTANT_FAB_ID, ASSISTANT_PANEL_ID, ASSISTANT_CLOSE_BTN_ID,
    ASSISTANT_CLEAR_BTN_ID, ASSISTANT_HISTORY_STORE_ID, ASSISTANT_SEEN_STORE_ID,
    ASSISTANT_UI_STORE_ID, ASSISTANT_MESSAGES_ID, ASSISTANT_CHIPS_ID,
    ASSISTANT_INPUT_ID, ASSISTANT_SEND_BTN_ID, chip_id,
)

PROFILES = {
    "sales": {
        "subtitle": "продажи · реклама · маркетинг",
        "title": "Привет! Я помогу с цифрами",
        "text": "Спросите про продажи, бренды и категории, маржинальность, "
                "рекламу, комиссии и штрафы WB — я найду данные, посчитаю и объясню.",
        "examples": [
            "Топ-10 брендов за сентябрь как на сайте WB",
            "Какие бренды продаются в убыток за сентябрь?",
            "Маржинальность по категориям за сентябрь — в Excel",
            "Продажи и возвраты за прошлую неделю как на сайте WB",
        ],
    },
    "finance": {
        "subtitle": "P&L · деньги · займы · продажи",
        "title": "Финансовый помощник",
        "text": "Спросите про прибыль и точку безубыточности, движение денег, "
                "остатки на счетах, займы, контрагентов и договоры или продажи — "
                "отвечу по данным мэн пака.",
        "examples": [
            "Чистая прибыль и ТБУ за последние 3 месяца",
            "Сколько денег на счетах и на какую дату?",
            "Кому начислялись проценты по займам в этом месяце?",
            "Топ-10 контрагентов по выплатам за месяц",
        ],
    },
}
EXAMPLES = PROFILES["sales"]["examples"]  # совместимость
N_CHIPS = 4


def _icon(name, size=18):
    return DashIconify(icon=name, width=size, height=size)


def welcome(profile="sales"):
    p = PROFILES.get(profile, PROFILES["sales"])
    return html.Div(className="asst-welcome", children=[
        html.Div(_icon("solar:stars-bold", 28), className="asst-welcome-icon"),
        html.Div(p["title"], className="asst-welcome-title"),
        html.Div(p["text"], className="asst-welcome-text"),
    ])


def assistant_widget(profile="sales"):
    prof = PROFILES.get(profile, PROFILES["sales"])
    return html.Div(className="asst-root", children=[
        dcc.Store(id=ASSISTANT_HISTORY_STORE_ID, data=[]),
        dcc.Store(id=ASSISTANT_SEEN_STORE_ID, data={}),
        dcc.Store(id=ASSISTANT_UI_STORE_ID, data={"open": False}),

        html.Div(id=ASSISTANT_PANEL_ID, className="asst-panel", children=[
            html.Div(className="asst-header", children=[
                html.Div(_icon("solar:stars-bold", 20), className="asst-avatar"),
                html.Div(className="asst-header-text", children=[
                    html.Div(["ИИ-помощник", html.Span("бета", className="asst-badge")],
                             className="asst-title"),
                    html.Div([html.Span(className="asst-dot"),
                              prof["subtitle"]], className="asst-subtitle"),
                ]),
                html.Button(_icon("solar:broom-linear"), id=ASSISTANT_CLEAR_BTN_ID,
                            className="asst-hbtn", title="Очистить чат"),
                html.Button(_icon("solar:close-circle-linear"), id=ASSISTANT_CLOSE_BTN_ID,
                            className="asst-hbtn", title="Свернуть"),
            ]),

            # column-reverse: лента всегда прижата к последнему сообщению
            html.Div(className="asst-body", children=html.Div(
                className="asst-scroll-inner",
                children=[
                    html.Div(id=ASSISTANT_MESSAGES_ID, children=welcome(profile)),
                    html.Div(className="asst-typing", children=[
                        html.Span(), html.Span(), html.Span(),
                        html.Em("смотрю данные…"),
                    ]),
                ],
            )),

            html.Div(id=ASSISTANT_CHIPS_ID, className="asst-chips", children=[
                html.Div("Попробуйте спросить", className="asst-chips-label"),
                *[html.Button(e, id=chip_id(i), className="asst-chip")
                  for i, e in enumerate(prof["examples"][:N_CHIPS])],
            ]),

            html.Div(className="asst-composer", children=[
                dcc.Input(id=ASSISTANT_INPUT_ID, type="text", debounce=False,
                          placeholder="Спросите что-нибудь…",
                          className="asst-input", autoComplete="off"),
                html.Button(_icon("solar:plain-3-bold", 18), id=ASSISTANT_SEND_BTN_ID,
                            className="asst-send", title="Отправить (Enter)"),
            ]),
            html.Div("Только чтение данных · цифры проверяйте в отчётах",
                     className="asst-footnote"),
        ]),

        html.Button(id=ASSISTANT_FAB_ID, className="asst-fab", title="ИИ-помощник",
                    children=[html.Span(className="asst-fab-ring"),
                              _icon("solar:stars-bold", 26)]),
    ])
