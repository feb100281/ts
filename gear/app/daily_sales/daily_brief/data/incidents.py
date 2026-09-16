# gear/app/daily_sales/daily_brief/data/incidents.py

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pandas as pd

from gear.app.daily_sales.stocks.dashboard_data import (
    get_warehouse_incident_snapshot,
)
from gear.app.daily_sales.stocks.dashboard_stock.warehouse_incidents import (
    WAREHOUSE_INCIDENTS,
)

from ..helpers import json_safe, number


def get_incidents_data(
    report_date: date,
) -> dict[str, Any]:
    events: list[dict] = []

    for warehouse_name, incidents in WAREHOUSE_INCIDENTS.items():
        for incident in incidents:
            incident_date = pd.to_datetime(
                incident.get("date"),
                errors="coerce",
            )

            if pd.isna(incident_date):
                continue

            if incident_date.date() != report_date:
                continue

            requested_snapshot_date = (
                report_date
                - timedelta(days=1)
            )

            snapshot = (
                get_warehouse_incident_snapshot(
                    warehouse_name=warehouse_name,
                    incident_date=(
                        requested_snapshot_date.isoformat()
                    ),
                )
                or {}
            )

            events.append(
                {
                    "warehouse_name": warehouse_name,
                    "date": report_date.isoformat(),
                    "type": incident.get(
                        "type",
                        "incident",
                    ),
                    "title": incident.get(
                        "title",
                        "Происшествие",
                    ),
                    "status": incident.get(
                        "status",
                        "Происшествие",
                    ),
                    "description": incident.get(
                        "description",
                        "",
                    ),
                    "requested_snapshot_date": (
                        requested_snapshot_date.isoformat()
                    ),
                    "effective_date": json_safe(
                        snapshot.get("effective_date")
                    ),
                    "on_hand": number(
                        snapshot.get("on_hand")
                    ),
                    "nm_count": int(
                        number(
                            snapshot.get("nm_count")
                        )
                    ),
                    "accounting_cost": number(
                        snapshot.get(
                            "accounting_cost"
                        )
                    ),
                    "management_cost": number(
                        snapshot.get(
                            "management_cost"
                        )
                    ),
                    "no_accounting_cost_qty": int(
                        number(
                            snapshot.get(
                                "no_accounting_cost_qty"
                            )
                        )
                    ),
                    "no_management_cost_qty": int(
                        number(
                            snapshot.get(
                                "no_management_cost_qty"
                            )
                        )
                    ),
                }
            )

    return {
        "available": bool(events),
        "count": len(events),
        "events": events,
    }