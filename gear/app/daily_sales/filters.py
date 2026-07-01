### Здесь прописываем фильтры Класс можем переиспользовать в SegmentAnalysis

from .data import brand_filter,cat_filter,gender_filter
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from dash import dcc, html, Input, Output, State, no_update
import pandas as pd
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta


class WbFilters:
    def __init__(self):       
    
        
        self.date_picker_id = 'date-filter-id'
        self.brand_multy_id = 'brand-multy-id'
        self.cat_multy_id = 'cat-multy-id'
        self.gender_multy_id = 'gender-multy-id'
        
    def get_date_filter(self,width=500,mindate=date(2024,1,1)):
        # DatePicker
        today = date.today()
        dpicker = dmc.DatePickerInput(
            type="range",
            allowSingleDateInRange=True,
            label="Выбор периода",
            valueFormat="dd DD, MMMM YYYY",
            placeholder="Select date",
            id = self.date_picker_id,
            minDate=mindate,
            w=width,
            presets=[
                {
                    "value": [
                        (today - timedelta(days=2)).isoformat(),
                        today.isoformat(),
                    ],
                    "label": "Последние два дня",
                },
                {
                    "value": [
                        (
                            today
                            - timedelta(days=today.weekday() + 7)
                        ).isoformat(),
                        (
                            today
                            - timedelta(days=today.weekday() + 1)
                        ).isoformat(),
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
                        (
                            (
                                today.replace(
                                    month=((today.month - 1) // 3) * 3 + 1,
                                    day=1,
                                )
                                - relativedelta(months=3)
                            )
                        ).isoformat(),

                        (
                            today.replace(
                                month=((today.month - 1) // 3) * 3 + 1,
                                day=1,
                            )
                            - timedelta(days=1)
                        ).isoformat(),
                    ],
                    "label": "Предыдущий квартал",
                },
                {
                    "value": [
                        date(today.year - 1, 1, 1).isoformat(),
                        date(today.year - 1, 12, 31).isoformat(),
                    ],
                    "label": "Прошлый год",
                },
            ],
            maw=320
        )
        return dmc.DatesProvider(
            children=dpicker,
            settings={
                "locale": "ru",
                "firstDayOfWeek": 1,
                "weekendDays": [0, 6],
            }
        )
        
    #Brand Multiselect
    def get_brand_filter(self,width=500,icon='icon-park-outline:trademark'):
        return dmc.MultiSelect(
        placeholder="Выбор",
        label="Brand filter",
        description="Фильтр по брэндам",
        variant="default",
        size="xs",
        radius="xl",
        withAsterisk=False,
        disabled=False,
        clearable=True,
        data=brand_filter(),
        id=self.brand_multy_id,
        w=width,
        leftSectionPointerEvents="none",
        leftSection=DashIconify(icon=icon)      
        )
        
    #Cat Multiselect
    def get_cat_filter(self,width=500,icon='mdi:category-plus-outline'):
        return dmc.MultiSelect(
        placeholder="Выбор",
        label="WB Cat filter",
        description="Фильтр по Категориям",
        variant="default",
        size="xs",
        radius="xl",
        withAsterisk=False,
        disabled=False,
        clearable=True,
        data=cat_filter(),
        id=self.cat_multy_id,
        w=width,
        leftSectionPointerEvents="none",
        leftSection=DashIconify(icon=icon),
        searchable=True,
        )
        
    #Gender Multiselect
    def get_gender_filter(self,width=500,icon='icons8:gender'):
        return dmc.MultiSelect(
        placeholder="Выбор",
        label="Gender filter",
        description="Фильтр полов",
        variant="default",
        size="xs",
        radius="xl",
        withAsterisk=False,
        disabled=False,
        clearable=True,
        data=gender_filter(),
        id=self.gender_multy_id,
        w=width,
        leftSectionPointerEvents="none",
        leftSection=DashIconify(icon=icon),
        searchable=True      
        )
        
        
        
        
        
    
    