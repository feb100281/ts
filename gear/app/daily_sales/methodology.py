# gear/app/daily_sales/methodology.py

import dash_mantine_components as dmc
from dash_iconify import DashIconify


METHODOLOGY_MODAL_ID = "daily-sales-methodology-modal"
METHODOLOGY_BUTTON_ID = "daily-sales-methodology-btn"


def methodology_button():
    return dmc.Tooltip(
        label="Методология расчёта",
        position="left",
        withArrow=True,
        children=dmc.ActionIcon(
            id=METHODOLOGY_BUTTON_ID,
            variant="light",
            color="yellow",
            radius=0,
            size="lg",
            children=DashIconify(
                icon="solar:lightbulb-linear",
                width=20,
                height=20,
            ),
        ),
    )


def methodology_modal():
    return dmc.Modal(
        id=METHODOLOGY_MODAL_ID,
        title=dmc.Group(
            gap=8,
            children=[
                DashIconify(
                    icon="solar:lightbulb-linear",
                    width=20,
                    height=20,
                    color="#f59f00",
                ),
                dmc.Text("Методология расчёта показателей", fw=800),
            ],
        ),
        opened=False,
        size="lg",
        radius=0,
        centered=True,
        children=[
            dmc.Stack(
                gap="sm",
                children=[
                    dmc.Alert(
                        title="WB расходы / overheads",
                        color="blue",
                        radius=0,
                        variant="light",
                        children=(
                            "К WB расходам относятся дополнительные расходы маркетплейса: "
                            "логистика, хранение, приёмка, удержания, штрафы, корректировки "
                            "и прочие сервисные начисления. Расходы начисляются не по каждой "
                            "продаже напрямую, а агрегируются по неделе и распределяются "
                            "пропорционально количеству проданных изделий в соответствующей неделе."
                        ),
                    ),
                    dmc.Alert(
                        title="Финансовый результат",
                        color="green",
                        radius=0,
                        variant="light",
                        children=(
                            "Бухгалтерский финрезультат рассчитывается на базе бухгалтерской "
                            "себестоимости, управленческий — на базе управленческой себестоимости. "
                            "После расчёта маржи дополнительно вычитается распределённая доля "
                            "WB расходов."
                        ),
                    ),
                    dmc.Alert(
                        title="Себестоимость при отсутствии данных",
                        color="orange",
                        radius=0,
                        variant="light",
                        children=(
                            "Если товар отсутствует на складе, но ранее уже продавался, "
                            "используется последняя известная себестоимость продажи. "
                            "Если по товару нет приходов, применяется резервная себестоимость: "
                            "для управленческого учёта — 620 ₽ за изделие, для бухгалтерского "
                            "учёта — 920 ₽ за изделие."
                        ),
                    ),
                    dmc.Text(
                        "Методика позволяет не занижать себестоимость и финансовый результат "
                        "по товарам с неполной складской историей.",
                        size="sm",
                        c="dimmed",
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