# inventories/urls.py
from django.urls import path
from . import views

app_name = 'inventories'

urlpatterns = [
    path('export-stocks/', views.export_stocks_excel, name='export_stocks'),
]