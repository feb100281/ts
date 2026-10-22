# gear/app/daily_sales/methodology.py

import dash_mantine_components as dmc
from dash_iconify import DashIconify
from dash import html


METHODOLOGY_MODAL_ID = "daily-sales-methodology-modal"
METHODOLOGY_BUTTON_ID = "daily-sales-methodology-btn"


def methodology_button():
    return dmc.Tooltip(
        label="Методология расчёта",
        position="left",
        withArrow=True,
        children=dmc.ActionIcon(
            id=METHODOLOGY_BUTTON_ID,
            variant="subtle",
            color="#2F6656",
            radius=0,
            size="lg",
            children=DashIconify(
                icon="solar:lightbulb-linear",
                width=20,
                height=20,
            ),
        ),
    )


_SECTION_NO = {"n": 0}


def _method_section(title, children):
    """Раздел методики: номер, заголовок, текст — без цветных плашек."""
    _SECTION_NO["n"] += 1
    return html.Div(
        className="mt-section",
        children=[
            html.Div(f"{_SECTION_NO['n']:02d}", className="mt-no"),
            html.Div(
                className="mt-content",
                children=[html.Div(title, className="mt-title"), children],
            ),
        ],
    )


def methodology_modal():
    _SECTION_NO["n"] = 0
    return dmc.Modal(
        id=METHODOLOGY_MODAL_ID,
        title=dmc.Group(
            gap=8,
            children=[
                DashIconify(
                    icon="solar:lightbulb-linear",
                    width=20,
                    height=20,
                    color="#2F6656",
                ),
                dmc.Text("Методология расчёта показателей", fw=700, c="#1F1F1F"),
            ],
        ),
        opened=False,
        size="lg",
        radius=0,
        centered=True,
        classNames={"header": "mt-header"},
        children=[
            dmc.Stack(
                gap=0,
                className="mt-body",
                children=[
                    _method_section(
                        title="WB расходы / overheads",
                        children=dmc.Text(
                            [
                                "К WB расходам относятся дополнительные расходы маркетплейса: "
                                "логистика, хранение, приёмка, удержания, штрафы, корректировки "
                                "и прочие сервисные начисления. Расходы начисляются не по каждой "
                                "продаже напрямую, а агрегируются по неделе и ",
                                html.Strong(
                                    "распределяются пропорционально количеству проданных изделий"
                                ),
                                " в соответствующей неделе.",
                            ],
                            size="sm",
                        ),
                    ),

                    _method_section(
                        title="Признание выручки и себестоимости",
                        children=dmc.Text(
                            [
                                html.Strong(
                                    "Выручка и себестоимость признаются по дате исходной реализации. "
                                ),
                                "Последующие возвраты корректируют показатели именно той даты, "
                                "в которую была совершена продажа. Например, если продажа была отражена ",
                                html.Strong("5 декабря"),
                                ", а возврат оформлен ",
                                html.Strong("15 декабря"),
                                ", то выручка, себестоимость и количество продаж будут уменьшены ",
                                html.Strong("за 5 декабря"),
                                ". Списание себестоимости осуществляется по методу ",
                                html.Strong("FIFO"),
                                " с учётом последующих возвратов.",
                            ],
                            size="sm",
                        ),
                    ),

                    _method_section(
                        title="Финансовый результат",
                        children=dmc.Text(
                            [
                                "Бухгалтерский финрезультат рассчитывается на базе ",
                                html.Strong("бухгалтерской себестоимости"),
                                ", управленческий — на базе ",
                                html.Strong("управленческой себестоимости"),
                                ". После расчёта маржи дополнительно вычитается распределённая доля ",
                                html.Strong("WB расходов"),
                                ".",
                            ],
                            size="sm",
                        ),
                    ),

                    _method_section(
                        title="Себестоимость при отсутствии данных",
                        children=dmc.Text(
                            [
                                "Если товар отсутствует на складе, но ранее уже продавался, "
                                "используется последняя известная себестоимость продажи. "
                                "Если по товару нет приходов, применяется резервная себестоимость: ",
                                html.Strong("для управленческого учёта"),
                                " — ",
                                html.Strong("620 ₽"),
                                " за изделие, ",
                                html.Strong("для бухгалтерского учёта"),
                                " — ",
                                html.Strong("950 ₽"),
                                " за изделие.",
                            ],
                            size="sm",
                        ),
                    ),

                    html.Div(
                        "Методика позволяет не занижать себестоимость и финансовый результат "
                        "по товарам с неполной складской историей.",
                        className="mt-note",
                    ),
                ],
            )
        ],
    )


def register_methodology_callbacks(app):
    from dash import Input, Output, State

    @app.callback(
        Output(METHODOLOGY_MODAL_ID, "opened"),
        Input(METHODOLOGY_BUTTON_ID, "n_clicks"),
        State(METHODOLOGY_MODAL_ID, "opened"),
        prevent_initial_call=True,
    )
    def toggle_methodology_modal(n_clicks, opened):
        if not n_clicks:
            return opened
        return not opened