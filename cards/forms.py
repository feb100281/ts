from django import forms

class UpdReconciliationForm(forms.Form):
    excel_file = forms.FileField(
        label='Файл выгрузки из 1С',
        help_text='Загрузите Excel-файл с выгрузкой УПД',
        widget=forms.FileInput(attrs={'accept': '.xlsx,.xls', 'class': 'vTextField'})
    )