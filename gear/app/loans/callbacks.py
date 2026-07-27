# gear/app/loans/callbacks.py
from __future__ import annotations

from datetime import date, datetime
from time import time
from dash import html
from dash_iconify import DashIconify


from .config import COLORS

import pandas as pd
from dash import (
    Input,
    Output,
    State,
    dcc,
    no_update,
)

from .calculations import (
    apply_filters,
    calculate_kpis,
    enrich_snapshot,
    serialize_dataframe,
)
from .charts import (
    build_counterparty_debt_chart,
    build_debt_dynamics_chart,
    build_interest_flow_chart,
    build_maturity_chart,
    build_selected_loan_chart,
    empty_figure,
)
from .data import (
    get_contract_transactions,
    get_interest_flow,
    get_loans_snapshot,
    get_portfolio_dynamics,
)
from .export import build_excel_bytes
from .filters import (
    normalise_history_range,
    register_filter_callbacks,
)
from .ids import (
    CONTRACT_TYPE_FILTER_ID,
    COUNTERPARTY_DEBT_CHART_ID,
    COUNTERPARTY_FILTER_ID,
    CURRENCY_FILTER_ID,
    DASHBOARD_LOADING_TRIGGER_ID,
    DATA_SIGNAL_ID,
    DEBT_DYNAMICS_CHART_ID,
    DOWNLOAD_EXCEL_BTN_ID,
    DOWNLOAD_ID,
    FILTER_STORE_ID,
    HISTORY_DATE_RANGE_ID,
    INTEREST_FLOW_CHART_ID,
    KPI_ACTIVE_LOANS_ID,
    KPI_DUE_30_ID,
    KPI_INTEREST_DEBT_ID,
    KPI_OVERDUE_ID,
    KPI_PRINCIPAL_DEBT_ID,
    KPI_TOTAL_DEBT_ID,
    KPI_TOTAL_DRAWNDOWN_ID,
    KPI_WEIGHTED_RATE_ID,
    LAST_UPDATE_ID,
    LOANS_GRID_ID,
    MATURITY_CHART_ID,
    REFRESH_BTN_ID,
    REPORT_DATE_ID,
    SELECTED_LOAN_CHART_ID,
    SELECTED_LOAN_META_ID,
    SELECTED_LOAN_STORE_ID,
    SELECTED_LOAN_TITLE_ID,
    STATUS_FILTER_ID,
    TRANSACTIONS_GRID_ID,
    DEBT_DYNAMICS_INSIGHT_ID,
    COUNTERPARTY_DEBT_INSIGHT_ID,
    MATURITY_INSIGHT_ID,
    INTEREST_FLOW_INSIGHT_ID,
    TRANSACTIONS_TITLE_ID,
    RECONCILIATION_EXPORT_BTN_ID,
    RECONCILIATION_DOWNLOAD_ID,
)

from .insights import (
    build_debt_dynamics_insight,
    build_counterparty_debt_insight,
    build_maturity_insight,
    build_interest_flow_insight,
)

from .excel import (
    build_reconciliation_excel,
)



def _format_integer(value) -> str:
    try:
        return f"{int(value):,}".replace(",", " ")
    except (TypeError, ValueError):
        return "0"


def _format_money(value) -> str:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return "—"

    abs_value = abs(numeric)

    if abs_value >= 1_000_000_000:
        return (
            f"{numeric / 1_000_000_000:,.2f}"
            .replace(",", " ")
            + " млрд"
        )

    if abs_value >= 1_000_000:
        return (
            f"{numeric / 1_000_000:,.2f}"
            .replace(",", " ")
            + " млн"
        )

    return (
        f"{numeric:,.2f}"
        .replace(",", " ")
    )


def _format_percent(value) -> str:
    if value is None:
        return "—"

    try:
        return (
            f"{float(value):,.2f}%"
            .replace(",", " ")
        )
    except (TypeError, ValueError):
        return "—"


def _filtered_snapshot(
    *,
    report_date,
    counterparties,
    contract_types,
    currencies,
    statuses,
):
    if not report_date:
        return pd.DataFrame()

    snapshot = get_loans_snapshot(
        str(report_date)[:10]
    )

    snapshot = enrich_snapshot(
        snapshot,
        str(report_date)[:10],
    )

    return apply_filters(
        snapshot,
        counterparties=counterparties,
        contract_types=contract_types,
        currencies=currencies,
        statuses=statuses,
    )
    

def _render_insights(
    insights: list[dict],
):
    if not insights:
        return html.Div(
            "Недостаточно данных для анализа.",
            style={
                "fontSize": "11px",
                "color": COLORS["muted"],
            },
        )

    styles = {
        "positive": {
            "icon": "solar:check-circle-linear",
            "color": COLORS["green"],
        },
        "warning": {
            "icon": "solar:danger-triangle-linear",
            "color": COLORS["orange"],
        },
        "negative": {
            "icon": "solar:danger-circle-linear",
            "color": COLORS["red"],
        },
        "neutral": {
            "icon": "solar:info-circle-linear",
            "color": COLORS["blue"],
        },
    }

    children = []

    for index, insight in enumerate(
        insights
    ):
        insight_type = (
            insight.get("type")
            or "neutral"
        )

        style = styles.get(
            insight_type,
            styles["neutral"],
        )

        children.append(
            html.Div(
                style={
                    "display": "flex",
                    "alignItems": "flex-start",
                    "gap": "7px",

                    "paddingBottom": (
                        "7px"
                        if index < len(insights) - 1
                        else "0"
                    ),

                    "marginBottom": (
                        "7px"
                        if index < len(insights) - 1
                        else "0"
                    ),

                    "borderBottom": (
                        f"1px solid {COLORS['border']}"
                        if index < len(insights) - 1
                        else "none"
                    ),
                },
                children=[
                    DashIconify(
                        icon=style["icon"],
                        width=15,
                        height=15,
                        color=style["color"],
                        style={
                            "marginTop": "1px",
                            "flex": "0 0 auto",
                        },
                    ),

                    html.Div(
                        style={
                            "minWidth": 0,
                        },
                        children=[
                            html.Div(
                                insight.get(
                                    "title",
                                    "",
                                ),
                                style={
                                    "fontSize": "11px",
                                    "fontWeight": 700,
                                    "lineHeight": "15px",
                                    "color": COLORS["text"],
                                },
                            ),

                            html.Div(
                                insight.get(
                                    "text",
                                    "",
                                ),
                                style={
                                    "marginTop": "1px",
                                    "fontSize": "11px",
                                    "lineHeight": "15px",
                                    "color": COLORS["muted"],
                                },
                            ),
                        ],
                    ),
                ],
            )
        )

    return children


def register_loans_callbacks(app):
    register_filter_callbacks(app)

    @app.callback(
        Output(DATA_SIGNAL_ID, "data"),
        Output(LAST_UPDATE_ID, "children"),
        Input(REFRESH_BTN_ID, "n_clicks"),
        prevent_initial_call=False,
    )
    def load_data_signal(
        refresh_clicks,
    ):
        now = datetime.now()

        return (
            {
                "version": now.isoformat(),
                "refresh_clicks": int(
                    refresh_clicks or 0
                ),
            },
            now.strftime("%d.%m.%Y %H:%M"),
        )

    @app.callback(
        Output(FILTER_STORE_ID, "data"),
        Output(KPI_ACTIVE_LOANS_ID, "children"),
        Output(KPI_TOTAL_DEBT_ID, "children"),
        Output(KPI_PRINCIPAL_DEBT_ID, "children"),
        Output(KPI_INTEREST_DEBT_ID, "children"),
        Output(KPI_WEIGHTED_RATE_ID, "children"),
        Output(KPI_DUE_30_ID, "children"),
        Output(KPI_OVERDUE_ID, "children"),
        Output(KPI_TOTAL_DRAWNDOWN_ID, "children"),
        
        Output(DEBT_DYNAMICS_CHART_ID, "figure"),
        Output(DEBT_DYNAMICS_INSIGHT_ID,"children",),
        
        Output(COUNTERPARTY_DEBT_CHART_ID, "figure"),
        Output( COUNTERPARTY_DEBT_INSIGHT_ID,"children",),

        Output(MATURITY_CHART_ID, "figure"),
        Output(MATURITY_INSIGHT_ID, "children",),
        
        Output(INTEREST_FLOW_CHART_ID, "figure"),
        Output(INTEREST_FLOW_INSIGHT_ID, "children",),
        
        Output(LOANS_GRID_ID, "rowData"),
        Output(
            DASHBOARD_LOADING_TRIGGER_ID,
            "children",
        ),
        Input(DATA_SIGNAL_ID, "data"),
        Input(REPORT_DATE_ID, "value"),
        Input(HISTORY_DATE_RANGE_ID, "value"),
        Input(COUNTERPARTY_FILTER_ID, "value"),
        Input(CONTRACT_TYPE_FILTER_ID, "value"),
        Input(CURRENCY_FILTER_ID, "value"),
        Input(STATUS_FILTER_ID, "value"),
    )
    def update_dashboard(
        data_signal,
        report_date,
        history_range,
        counterparties,
        contract_types,
        currencies,
        statuses,
    ):
        if not report_date:
            empty = empty_figure()

            return (
                {},      # FILTER_STORE_ID

                "0",     # KPI_ACTIVE_LOANS_ID
                "—",     # KPI_TOTAL_DEBT_ID
                "—",     # KPI_PRINCIPAL_DEBT_ID
                "—",     # KPI_INTEREST_DEBT_ID
                "—",     # KPI_WEIGHTED_RATE_ID
                "0",     # KPI_DUE_30_ID
                "0",     # KPI_OVERDUE_ID
                "—",     # KPI_TOTAL_DRAWNDOWN_ID

                empty,   # DEBT_DYNAMICS_CHART_ID
                html.Div( "Нет данных для анализа.",style={"fontSize": "11px","color": COLORS["muted"],},),       # DEBT_DYNAMICS_INSIGHT_ID

                empty,   # COUNTERPARTY_DEBT_CHART_ID
                html.Div("Нет данных для анализа.",style={"fontSize": "11px","color": COLORS["muted"],},), 
                  
                empty,   # MATURITY_CHART_ID
                html.Div("Нет данных для анализа.",style={"fontSize": "11px", "color": COLORS["muted"],},),      # MATURITY_INSIGHT_ID


                empty,   # INTEREST_FLOW_CHART_ID
                html.Div("Нет данных для анализа.",style={"fontSize": "11px","color": COLORS["muted"], },),     # I


                [],      # LOANS_GRID_ID

                str(time()),  # loader
            )

        filtered = _filtered_snapshot(
            report_date=report_date,
            counterparties=counterparties,
            contract_types=contract_types,
            currencies=currencies,
            statuses=statuses,
        )

        kpis = calculate_kpis(filtered)

        contract_ids = (
            filtered["contract_id"]
            .dropna()
            .astype(int)
            .unique()
            .tolist()
            if not filtered.empty
            else []
        )

        date_from, date_to = (
            normalise_history_range(
                history_range
            )
        )

        if contract_ids:
            dynamics_df = (
                get_portfolio_dynamics(
                    date_from,
                    date_to,
                    contract_ids,
                )
            )
            interest_df = (
                get_interest_flow(
                    date_from,
                    date_to,
                    contract_ids,
                )
            )
        else:
            dynamics_df = pd.DataFrame()
            interest_df = pd.DataFrame()

        filter_store = {
            "report_date": str(report_date)[:10],
            "history_range": [
                date_from,
                date_to,
            ],
            "counterparties": counterparties or [],
            "contract_types": contract_types or [],
            "currencies": currencies or [],
            "statuses": statuses or [],
        }

        return (
            filter_store,
            _format_integer(
                kpis["active_loans"]
            ),
            _format_money(
                kpis["total_debt"]
            ),
            _format_money(
                kpis["principal_debt"]
            ),
            _format_money(
                kpis["interest_debt"]
            ),
            _format_percent(
                kpis["weighted_rate"]
            ),
            _format_integer(
                kpis["due_30"]
            ),
            _format_integer(
                kpis["overdue"]
            ),
            _format_money(
                kpis["total_drawdown"]
            ),
            
            build_debt_dynamics_chart(dynamics_df),
            _render_insights(build_debt_dynamics_insight(dynamics_df)),
            
            build_counterparty_debt_chart(filtered),
            _render_insights(build_counterparty_debt_insight(filtered)),
            
            build_maturity_chart(filtered),
            _render_insights( build_maturity_insight( filtered)),
            
            build_interest_flow_chart(interest_df),
            _render_insights(build_interest_flow_insight(interest_df,filtered,)),
            
            
            serialize_dataframe(filtered),
            str(time()),
        )

    @app.callback(
        Output(
            SELECTED_LOAN_STORE_ID,
            "data",
        ),
        Input(
            LOANS_GRID_ID,
            "selectedRows",
        ),
        prevent_initial_call=True,
    )
    def select_loan(
        selected_rows,
    ):
        if not selected_rows:
            return None

        row = selected_rows[0]

        return {
            "contract_id": row.get(
                "contract_id"
            ),

            "contract_number": row.get(
                "contract_number"
            ),

            "contract_date": row.get(
                "contract_date"
            ),

            "counterparty_name": row.get(
                "counterparty_name"
            ),

            "inn": row.get(
                "inn"
            ),

            "contract_type": row.get(
                "contract_type"
            ),

            "currency": row.get(
                "currency"
            ),

            "rate": row.get(
                "rate"
            ),

            "repayment_date": row.get(
                "repayment_date"
            ),

            "contract_amount": row.get(
                "contract_amount"
            ),

            "total_drawdown": row.get(
                "total_drawdown"
            ),

            "total_repaid": row.get(
                "total_repaid"
            ),

            "ending_balance": row.get(
                "ending_balance"
            ),

            "interest_balance": row.get(
                "interest_balance"
            ),

            "total_debt": row.get(
                "total_debt"
            ),

            "penalty_rate": row.get(
                "penalty_rate"
            ),

            "repayment_profile": row.get(
                "repayment_profile"
            ),
        }
    
    @app.callback(
        Output(
            SELECTED_LOAN_TITLE_ID,
            "children",
        ),
        Output(
            SELECTED_LOAN_META_ID,
            "children",
        ),
        Output(
            SELECTED_LOAN_CHART_ID,
            "figure",
        ),
        Output(
            TRANSACTIONS_GRID_ID,
            "rowData",
        ),
        Output(
            TRANSACTIONS_TITLE_ID,
            "children",
        ),

        Input(
            SELECTED_LOAN_STORE_ID,
            "data",
        ),
        State(
            REPORT_DATE_ID,
            "value",
        ),
    )
    def update_selected_loan(
        selected_loan,
        report_date,
    ):
        # =============================================================
        # Ничего не выбрано
        # =============================================================

        if not selected_loan:
            return (
                "Договор не выбран",

                "Выберите договор в реестре выше",

                empty_figure(
                    "Выберите договор в реестре",
                    height=360,
                ),

                [],

                # TRANSACTIONS_TITLE_ID
                "История операций",
            )

        # =============================================================
        # Contract ID
        # =============================================================

        contract_id = selected_loan.get(
            "contract_id"
        )

        if contract_id is None:
            return (
                "Договор не выбран",

                "",

                empty_figure(
                    "Нет данных",
                    height=360,
                ),

                [],

                # TRANSACTIONS_TITLE_ID
                "История операций",
            )

        # =============================================================
        # Операции по договору
        # =============================================================

        transactions = (
            get_contract_transactions(
                int(contract_id),

                str(report_date)[:10]
                if report_date
                else None,
            )
        )

        # =============================================================
        # Метаданные договора
        # =============================================================

        number = (
            selected_loan.get(
                "contract_number"
            )
            or "без номера"
        )

        counterparty = (
            selected_loan.get(
                "counterparty_name"
            )
            or "Контрагент не указан"
        )

        currency = (
            selected_loan.get(
                "currency"
            )
            or "—"
        )

        rate = selected_loan.get(
            "rate"
        )

        rate_text = (
            _format_percent(rate)
            if rate is not None
            else "—"
        )

        repayment_date = (
            selected_loan.get(
                "repayment_date"
            )
            or "—"
        )

        # =============================================================
        # Верхний заголовок блока
        # =============================================================

        title = (
            f"{counterparty} · "
            f"договор № {number}"
        )

        meta = (
            f"Валюта: {currency} · "
            f"Ставка: {rate_text} · "
            f"Погашение: {repayment_date}"
        )

        # =============================================================
        # Заголовок истории операций
        # =============================================================

        transactions_title = (
            f"История операций · "
            f"{counterparty} · "
            f"договор № {number}"
        )

        # =============================================================
        # Return
        # =============================================================

        return (
            title,

            meta,

            build_selected_loan_chart(
                transactions
            ),

            serialize_dataframe(
                transactions
            ),

            transactions_title,
        )
    
    @app.callback(
        Output(DOWNLOAD_ID, "data"),
        Input(
            DOWNLOAD_EXCEL_BTN_ID,
            "n_clicks",
        ),
        State(REPORT_DATE_ID, "value"),
        State(
            COUNTERPARTY_FILTER_ID,
            "value",
        ),
        State(
            CONTRACT_TYPE_FILTER_ID,
            "value",
        ),
        State(
            CURRENCY_FILTER_ID,
            "value",
        ),
        State(
            STATUS_FILTER_ID,
            "value",
        ),
        State(
            SELECTED_LOAN_STORE_ID,
            "data",
        ),
        prevent_initial_call=True,
    )
    def download_excel(
        n_clicks,
        report_date,
        counterparties,
        contract_types,
        currencies,
        statuses,
        selected_loan,
    ):
        if not n_clicks or not report_date:
            return no_update

        filtered = _filtered_snapshot(
            report_date=report_date,
            counterparties=counterparties,
            contract_types=contract_types,
            currencies=currencies,
            statuses=statuses,
        )

        transactions = pd.DataFrame()

        if selected_loan:
            contract_id = selected_loan.get(
                "contract_id"
            )
            if contract_id is not None:
                transactions = (
                    get_contract_transactions(
                        int(contract_id),
                        str(report_date)[:10],
                    )
                )

        content = build_excel_bytes(
            filtered,
            transactions,
        )

        filename = (
            "loans_"
            f"{str(report_date)[:10]}.xlsx"
        )

        return dcc.send_bytes(
            content,
            filename,
        )
        
        
    @app.callback(
        Output(
            RECONCILIATION_DOWNLOAD_ID,
            "data",
        ),

        Input(
            RECONCILIATION_EXPORT_BTN_ID,
            "n_clicks",
        ),

        State(
            SELECTED_LOAN_STORE_ID,
            "data",
        ),

        State(
            REPORT_DATE_ID,
            "value",
        ),

        prevent_initial_call=True,
    )
    def download_reconciliation_excel(
        n_clicks,
        selected_loan,
        report_date,
    ):
        if not n_clicks:
            return no_update

        if not selected_loan:
            return no_update

        contract_id = selected_loan.get(
            "contract_id"
        )

        if contract_id is None:
            return no_update

        # =============================================================
        # Дата сверки
        # =============================================================

        today = date.today()

        selected_date = pd.to_datetime(
            report_date,
            errors="coerce",
        )

        if pd.isna(selected_date):
            reconciliation_date = today

        else:
            selected_date = (
                selected_date.date()
            )

            # Сверка не должна включать
            # будущие начисления.
            reconciliation_date = min(
                selected_date,
                today,
            )

        reconciliation_date_str = (
            reconciliation_date.isoformat()
        )

        # =============================================================
        # История ТОЛЬКО по дату сверки
        # =============================================================

        transactions = (
            get_contract_transactions(
                int(contract_id),
                reconciliation_date_str,
            )
        )

        # =============================================================
        # Excel
        # =============================================================

        content = (
            build_reconciliation_excel(
                loan=selected_loan,
                transactions=transactions,
                report_date=(
                    reconciliation_date_str
                ),
            )
        )

        # =============================================================
        # Имя файла
        # =============================================================

        counterparty = (
            selected_loan.get(
                "counterparty_name"
            )
            or "контрагент"
        )

        contract_number = (
            selected_loan.get(
                "contract_number"
            )
            or "бн"
        )

        def safe_filename_part(
            value,
        ) -> str:
            return (
                str(value)
                .strip()
                .replace("/", "_")
                .replace("\\", "_")
                .replace(":", "_")
                .replace("*", "_")
                .replace("?", "_")
                .replace('"', "_")
                .replace("<", "_")
                .replace(">", "_")
                .replace("|", "_")
                .replace(" ", "_")
            )

        filename = (
            "Сверка_по_договору_"
            f"{safe_filename_part(counterparty)}_"
            f"{safe_filename_part(contract_number)}_"
            f"на_{reconciliation_date.strftime('%d.%m.%Y')}"
            ".xlsx"
        )

        return dcc.send_bytes(
            content,
            filename,
        )