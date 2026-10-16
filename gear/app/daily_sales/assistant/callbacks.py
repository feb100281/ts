# gear/app/daily_sales/assistant/callbacks.py
from __future__ import annotations

import logging
import time

from dash import Input, Output, State, dcc, html, no_update
from dash.exceptions import PreventUpdate
from dash_iconify import DashIconify

from .ids import (
    ASSISTANT_FAB_ID, ASSISTANT_PANEL_ID, ASSISTANT_CLOSE_BTN_ID,
    ASSISTANT_CLEAR_BTN_ID, ASSISTANT_HISTORY_STORE_ID, ASSISTANT_SEEN_STORE_ID,
    ASSISTANT_UI_STORE_ID, ASSISTANT_MESSAGES_ID, ASSISTANT_CHIPS_ID,
    ASSISTANT_INPUT_ID, ASSISTANT_SEND_BTN_ID, chip_id,
)
from .layout import N_CHIPS, PROFILES, welcome
from .llm import AssistantError, ask

log = logging.getLogger(__name__)
MAX_HISTORY = 20


# ------------------------------------------------------------------ render
def _meta_line(meta):
    u = meta.get("usage") or {}
    if not u:
        return None
    cost = meta.get("cost_usd")
    txt = (f"{u.get('input', 0) + u.get('cache_read', 0):,} → "
           f"{u.get('output', 0):,} токенов").replace(",", " ")
    if cost is not None:
        txt += f" · ≈ ${cost:.3f}"
    return html.Span(txt, className="asst-meta")


def _file_card(f):
    rows = f"{f.get('rows', 0):,}".replace(",", " ")
    return html.A(
        href=f"/admin/assistant/file/{f['id']}/",
        className="asst-file", download=f.get("name"), target="_blank",
        children=[
            html.Div(DashIconify(icon="vscode-icons:file-type-excel", width=26),
                     className="asst-file-icon"),
            html.Div(className="asst-file-text", children=[
                html.Div(f.get("name"), className="asst-file-name"),
                html.Div(f"Excel · строк: {rows}"
                         + (" · обрезано" if f.get("cut") else ""),
                         className="asst-file-sub"),
            ]),
            DashIconify(icon="solar:download-minimalistic-bold", width=20,
                        className="asst-file-dl"),
        ])


def _bubble(msg: dict):
    if msg["role"] == "user":
        return html.Div(className="asst-row user", children=html.Div(
            msg["content"], className="asst-msg user"))

    meta = msg.get("meta") or {}
    if meta.get("error"):
        return html.Div(className="asst-row bot", children=html.Div(
            className="asst-msg error", children=[
                DashIconify(icon="solar:danger-triangle-linear", width=16),
                html.Span(msg["content"])]))

    footer = []
    line = _meta_line(meta)
    if line:
        footer.append(line)
    return html.Div(className="asst-row bot", children=[
        html.Div(DashIconify(icon="solar:stars-bold", width=14),
                 className="asst-mini-avatar"),
        html.Div(className="asst-msg bot", children=[
            dcc.Markdown(msg["content"], className="asst-md"),
            *[_file_card(f) for f in meta.get("files") or []],
            html.Div(footer, className="asst-msg-footer") if footer else None,
        ]),
    ])


# ------------------------------------------------------------------ logic
def _convo(history):
    convo = [{"role": m["role"], "content": m["content"]}
             for m in history if not (m.get("meta") or {}).get("error")]
    convo = convo[-MAX_HISTORY:]
    while convo and convo[0]["role"] != "user":
        convo.pop(0)
    return convo


def _ask_msg(convo, profile="sales"):
    t0 = time.time()
    try:
        res = ask(convo, profile)
        msg = {"role": "assistant", "content": res["text"],
               "meta": {"usage": res["usage"], "files": res.get("files", []),
                        "cost_usd": res["cost_usd"]}}
    except AssistantError as e:
        msg = {"role": "assistant", "content": str(e), "meta": {"error": True}}
    except Exception as e:
        log.exception("assistant failed")
        msg = {"role": "assistant", "content": f"Ошибка: {e}",
               "meta": {"error": True}}
    print(f"[assistant] ответ за {time.time() - t0:.1f} c, "
          f"ошибка={bool(msg['meta'].get('error'))}: "
          f"{msg['content'][:200]}", flush=True)
    return msg


def _clicked(seen, key, n):
    """Сравнение счётчика нажатий с сохранённым (ctx под django-plotly-dash не работает)."""
    n = n or 0
    hit = n != seen.get(key, 0)
    seen[key] = n
    return hit


def register_assistant_callbacks(app, profile="sales"):
    examples = PROFILES.get(profile, PROFILES["sales"])["examples"][:N_CHIPS]

    @app.callback(
        Output(ASSISTANT_PANEL_ID, "className"),
        Output(ASSISTANT_FAB_ID, "className"),
        Output(ASSISTANT_UI_STORE_ID, "data"),
        Input(ASSISTANT_FAB_ID, "n_clicks"),
        Input(ASSISTANT_CLOSE_BTN_ID, "n_clicks"),
        State(ASSISTANT_UI_STORE_ID, "data"),
        prevent_initial_call=True,
    )
    def _toggle(n_fab, n_close, ui):
        ui = dict(ui or {})
        if _clicked(ui, "close", n_close):
            ui["open"] = False
        elif _clicked(ui, "fab", n_fab):
            ui["open"] = not ui.get("open")
        else:
            raise PreventUpdate
        is_open = ui["open"]
        return ("asst-panel open" if is_open else "asst-panel",
                "asst-fab active" if is_open else "asst-fab", ui)

    chip_inputs = [Input(chip_id(i), "n_clicks") for i in range(len(examples))]

    @app.callback(
        Output(ASSISTANT_HISTORY_STORE_ID, "data"),
        Output(ASSISTANT_INPUT_ID, "value"),
        Output(ASSISTANT_SEEN_STORE_ID, "data"),
        Input(ASSISTANT_SEND_BTN_ID, "n_clicks"),
        Input(ASSISTANT_INPUT_ID, "n_submit"),
        Input(ASSISTANT_CLEAR_BTN_ID, "n_clicks"),
        *chip_inputs,
        State(ASSISTANT_INPUT_ID, "value"),
        State(ASSISTANT_HISTORY_STORE_ID, "data"),
        State(ASSISTANT_SEEN_STORE_ID, "data"),
        prevent_initial_call=True,
    )
    def _update(n_send, n_submit, n_clear, *rest):
        chips = rest[:len(examples)]
        text, history, seen = rest[len(examples):]
        history = list(history or [])
        seen = dict(seen or {})

        sent = _clicked(seen, "send", n_send)
        submitted = _clicked(seen, "submit", n_submit)
        cleared = _clicked(seen, "clear", n_clear)
        chip_text = None
        for i, n in enumerate(chips):
            if _clicked(seen, f"chip{i}", n):
                chip_text = examples[i]

        if cleared:
            return [], "", seen
        if chip_text:
            text = chip_text
        elif not (sent or submitted):
            raise PreventUpdate

        text = (text or "").strip()
        if not text:
            return no_update, no_update, seen

        history.append({"role": "user", "content": text})
        print(f"[assistant] вопрос: {text[:80]}", flush=True)
        history.append(_ask_msg(_convo(history), profile))
        return history, "", seen

    @app.callback(
        Output(ASSISTANT_MESSAGES_ID, "children"),
        Output(ASSISTANT_CHIPS_ID, "style"),
        Input(ASSISTANT_HISTORY_STORE_ID, "data"),
    )
    def _render(history):
        if not history:
            return welcome(profile), {}
        return [_bubble(m) for m in history], {"display": "none"}
