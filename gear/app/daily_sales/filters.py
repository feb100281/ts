# gear/app/daily_sales/filters.py
     
from datetime import date, timedelta

import dash_mantine_components as dmc
from dash_iconify import DashIconify
from dateutil.relativedelta import relativedelta

from .data import brand_filter, cat_filter, gender_filter


class WbFilters:
    def __init__(self):
        self.date_picker_id = "date-filter-id"
        self.brand_multy_id = "brand-multy-id"
        self.cat_multy_id = "cat-multy-id"
        self.gender_multy_id = "gender-multy-id"

    @staticmethod
    def _icon(icon, size=16):
        return DashIconify(icon=icon, width=size, height=size)

    def get_date_filter(self, width="100%", mindate=date(2024, 1, 1)):
        today = date.today()
        current_quarter_start = today.replace(
            month=((today.month - 1) // 3) * 3 + 1,
            day=1,
        )

        picker = dmc.DatePickerInput(
            id=self.date_picker_id,
            type="range",
            allowSingleDateInRange=True,
            label="Период",
            placeholder="Выберите период",
            valueFormat="DD.MM.YYYY",
            minDate=mindate,
            w=width,
            size="sm",
            radius=0,
            clearable=True,
            leftSection=self._icon("solar:calendar-linear"),
            leftSectionPointerEvents="none",
            presets=[
                    {
                        "value": [
                            (today - timedelta(days=2)).isoformat(),
                            today.isoformat(),
                        ],
                        "label": "Последние 2 дня",
                    },
                    {
                        "value": [
                            (today - timedelta(days=today.weekday() + 7)).isoformat(),
                            (today - timedelta(days=today.weekday() + 1)).isoformat(),
                        ],
                        "label": "Предыдущая неделя",
                    },
                    {
                        "value": [
                            today.replace(day=1).isoformat(),
                            today.isoformat(),
                        ],
                        "label": "Текущий месяц",
                    },
                    {
                        "value": [
                            (today - relativedelta(months=1)).replace(day=1).isoformat(),
                            (today.replace(day=1) - timedelta(days=1)).isoformat(),
                        ],
                        "label": "Предыдущий месяц",
                    },
                    {
                        "value": [
                            current_quarter_start.isoformat(),
                            today.isoformat(),
                        ],
                        "label": "Текущий квартал",
                    },
                    {
                        "value": [
                            (current_quarter_start - relativedelta(months=3)).isoformat(),
                            (current_quarter_start - timedelta(days=1)).isoformat(),
                        ],
                        "label": "Предыдущий квартал",
                    },
                    {
                        "value": [
                            date(today.year, 1, 1).isoformat(),
                            today.isoformat(),
                        ],
                        "label": "С начала года",
                    },
                    {
                        "value": [
                            date(today.year - 1, 1, 1).isoformat(),
                            date(today.year - 1, 12, 31).isoformat(),
                        ],
                        "label": "Прошлый год",
                    },
                ],
        )

        return dmc.DatesProvider(
            picker,
            settings={
                "locale": "ru",
                "firstDayOfWeek": 1,
                "weekendDays": [0, 6],
            },
        )

    def _multi_select(self, component_id, label, placeholder, data, icon):
        return dmc.MultiSelect(
            id=component_id,
            label=label,
            value=[], 
            placeholder=placeholder,
            data=data,
            w="100%",
            size="sm",
            radius=0,
            clearable=True,
            searchable=True,
            maxDropdownHeight=300,
            nothingFoundMessage="Ничего не найдено",
            leftSection=self._icon(icon),
            leftSectionPointerEvents="none",
            comboboxProps={
                "shadow": "md",
            },
        )

    def get_brand_filter(self):
        return self._multi_select(
            self.brand_multy_id,
            "Бренд",
            "Выберите бренды",
            brand_filter(),
            "icon-park-outline:trademark",
        )

    def get_cat_filter(self):
        return self._multi_select(
            self.cat_multy_id,
            "Категория WB",
            "Выберите категории",
            cat_filter(),
            "mdi:category-plus-outline",
        )

    def get_gender_filter(self):
        return self._multi_select(
            self.gender_multy_id,
            "Пол",
            "Выберите пол",
            gender_filter(),
            "icons8:gender",
        )

    def get_filters_panel(self):
        return dmc.Paper(
            withBorder=True,
            radius=0,
            shadow="xs",
            px="md",
            py="sm",
            mb="md",
            style={
                "width": "100%",
                "backgroundColor": "#fbfcfe",
                "borderColor": "#d9e0e8",
            },
            children=[
                dmc.Group(
                    justify="space-between",
                    align="center",
                    mb="xs",
                    children=[
                        dmc.Group(
                            gap=8,
                            children=[
                                DashIconify(
                                    icon="solar:filter-linear",
                                    width=20,
                                    height=20,
                                    color="#228be6",
                                ),
                                dmc.Text(
                                    "Фильтры отчета",
                                    fw=800,
                                    size="md",
                                    c="#228be6",
                                ),
                                dmc.Text(
                                    "· период, бренд, категория и пол",
                                    size="sm",
                                    c="dimmed",
                                ),
                            ],
                        ),
                    ],
                ),
                dmc.Grid(
                    gutter="md",
                    align="flex-end",
                    children=[
                        dmc.GridCol(self.get_date_filter(), span={"base": 12, "md": 6, "xl": 3}),
                        dmc.GridCol(self.get_brand_filter(), span={"base": 12, "md": 6, "xl": 3}),
                        dmc.GridCol(self.get_cat_filter(), span={"base": 12, "md": 6, "xl": 3}),
                        dmc.GridCol(self.get_gender_filter(), span={"base": 12, "md": 6, "xl": 3}),
                    ],
                ),
            ],
        )