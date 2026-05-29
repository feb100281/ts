from django import forms
from django.core.exceptions import ValidationError
import pandas as pd

class UpdReconciliationForm(forms.Form):
    excel_file = forms.FileField(
        label='Файл выгрузки из 1С',
        help_text='Загрузите Excel-файл с выгрузкой УПД',
        widget=forms.FileInput(attrs={'accept': '.xlsx,.xls', 'class': 'vTextField'})
    )
    


class ArticlesAnalysisForm(forms.Form):
    excel_file = forms.FileField(
        label='Excel файл с артиклями',
        help_text='Загрузите Excel файл с колонкой "Article" (или "Артикул")',
        widget=forms.FileInput(attrs={'accept': '.xlsx, .xls'})
    )
    
    def clean_excel_file(self):
        excel_file = self.cleaned_data['excel_file']
        
        try:
            df = pd.read_excel(
                excel_file,
                dtype=str,
                keep_default_na=False
            )
        except Exception as e:
            raise ValidationError(f'Не удалось прочитать файл: {e}')
        
        article_col = None
        for col in ['Article', 'Артикул', 'article', 'артикул']:
            if col in df.columns:
                article_col = col
                break
        
        if not article_col:
            raise ValidationError('Файл должен содержать колонку "Article" или "Артикул"')
        
        articles = (
            df[article_col]
            .astype(str)
            .str.strip()
            .str.replace(r'\.0$', '', regex=True)
        )
        
        articles = articles[articles != ''].unique().tolist()
        
        if not articles:
            raise ValidationError('В файле нет ни одного артикля')
        
        self.cleaned_articles = articles
        
        return excel_file
    
    def get_articles(self):
        return getattr(self, 'cleaned_articles', [])