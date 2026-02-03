from django_plotly_dash import DjangoDash
from dash import Input, Output, State, no_update,dcc, MATCH, html
import pandas as pd
import numpy as np
from dash_iconify import DashIconify
import dash_mantine_components as dmc
from utils.dash_components.common import CommonComponents as CC  #Отсюда импортируем компоненты одинаковые для все приложений
from utils.dash_components.dftotable import df_dmc_table
import locale
locale.setlocale(locale.LC_TIME, "ru_RU.UTF-8")
from .data import get_product_info
from django.urls import reverse, NoReverseMatch
import pprint


class MainWindow:
    def __init__(self, product_id=None):
        
        
        self.product_info = get_product_info(product_id)
       
        
       
        
        
    def layout(self):
        
        try:
            back_url = reverse("admin:sales/mvdatamartproduct_changelist")
        except NoReverseMatch:
            back_url = "/admin/sales/mvdatamartproduct/"

        
        la = dmc.AppShell(
            [
                dmc.AppShellHeader(
                dmc.Group(
                    
                    [
                        
                        dmc.Anchor(
                            dmc.Button(
                                [DashIconify(icon="tabler:arrow-left", width=18), "Назад"],
                                variant="subtle",
                                size="sm",
                            ),
                            href=back_url,
                            target="_top",
                            style={"textDecoration": "none"},
                        ),

                        DashIconify(icon='streamline-freehand:cash-payment-bag-1',width=40,color='blue'),
                        CC.report_title(f"КАРТОЧКА ТОВАРА {self.product_info['Наименование'].upper()}")
                    ],
                h="100%",
                px="md",
                mb='lg',
                
                )
                ),
                dmc.AppShellMain(
                    [
                        # df_dmc_table(self.make_dayly_summary(),formaters=FORMATERS,className='classic-table'),
                        # dmc.Space(h=30),
                        # df_dmc_table(self.make_ytd_summary(),formaters=FORMATERS,className='classic-table')
                        # dmc.Text(self.product_info)
                    ]
                    ),
            ],
            header={"height": 60},
            padding="md",
        )
        
        
        
        
        
        
        return dmc.Container(
            [
            la
            
            ],
            fluid=True           
        )
    
    def registered_callbacks(self,app):
        pass