# gear/app/daily_sales/column_picker.py
"""Кнопка «Столбцы»: каждый пользователь скрывает и показывает колонки таблицы.

Работает в браузере, данные не пересчитываются. Выбор запоминается
в браузере пользователя (persistence local) отдельно для каждой таблицы.

Подключение к таблице с id {"type": <grid_type>, "index": <index>}:

    column_picker(index, column_defs, grid_type=GRID_TYPE)

Колбэк регистрируется один раз на тип таблиц:
register_column_picker_callbacks(app, grid_type).
"""
from __future__ import annotations

import dash_mantine_components as dmc
from dash import MATCH, Input, Output, State, no_update
from dash_iconify import DashIconify

PICKER_TYPE = "col-picker"


def _picker_type(grid_type):
    return f"{PICKER_TYPE}-{grid_type}"


def column_picker(index, column_defs, grid_type):
    """Кнопка со списком колонок; закреплённые слева колонки не скрываются."""
    fields = [c for c in column_defs if c.get("field") and not c.get("pinned")]
    return dmc.Popover(
        position="bottom-end",
        shadow="md",
        withArrow=True,
        children=[
            dmc.PopoverTarget(
                dmc.Button(
                    "Столбцы",
                    variant="default",
                    size="sm",
                    radius="sm",
                    leftSection=DashIconify(icon="solar:list-check-linear", width=16),
                )
            ),
            dmc.PopoverDropdown(
                dmc.CheckboxGroup(
                    id={"type": _picker_type(grid_type), "index": index},
                    value=[c["field"] for c in fields],
                    persistence=True,
                    persistence_type="local",
                    children=dmc.Stack(
                        gap=6,
                        style={"maxHeight": "360px", "overflowY": "auto"},
                        children=[
                            dmc.Checkbox(label=c.get("headerName") or c["field"],
                                         value=c["field"], size="xs")
                            for c in fields
                        ],
                    ),
                )
            ),
        ],
    )


def register_column_picker_callbacks(app, grid_type):
    @app.callback(
        Output({"type": grid_type, "index": MATCH}, "columnDefs"),
        Input({"type": _picker_type(grid_type), "index": MATCH}, "value"),
        State({"type": grid_type, "index": MATCH}, "columnDefs"),
    )
    def apply_columns(visible, defs):
        if visible is None or not defs:
            return no_update
        keep = set(visible)
        out = []
        for c in defs:
            c = dict(c)
            if c.get("field") and not c.get("pinned"):
                c["hide"] = c["field"] not in keep
            out.append(c)
        return out
