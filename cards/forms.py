# # cards/forms.py
# from django import forms
# from django.core.exceptions import ValidationError
# import pandas as pd

# class UpdReconciliationForm(forms.Form):
#     excel_file = forms.FileField(
#         label='Файл выгрузки из 1С',
#         help_text='Загрузите Excel-файл с выгрузкой УПД',
#         widget=forms.FileInput(attrs={'accept': '.xlsx,.xls', 'class': 'vTextField'})
#     )
    


# class ArticlesAnalysisForm(forms.Form):
#     excel_file = forms.FileField(
#         label='Excel файл с артиклями',
#         help_text='Загрузите Excel файл с колонкой "Article" (или "Артикул")',
#         widget=forms.FileInput(attrs={'accept': '.xlsx, .xls'})
#     )
    
#     def clean_excel_file(self):
#         excel_file = self.cleaned_data['excel_file']
        
        
#         try:
#             df = pd.read_excel(
#                 excel_file,
#                 dtype=str,
#                 keep_default_na=False
#             )
            
#         except Exception as e:
#             raise ValidationError(f'Не удалось прочитать файл: {e}')
        
#         print(df.columns)
#         article_col = None
#         for col in ['Article', 'Артикул', 'article', 'артикул', 'Article ID']:
#             if col in df.columns:
#                 article_col = col
#                 break
        
        
        
#         if not article_col:
            
#             raise ValidationError('Файл должен содержать колонку "Article" или "Артикул"')
#         # print('launch fnc try', article_col)
        
#         articles = (
#             df[article_col]
#             .astype(str)
#             .str.strip()
#             .str.replace(r'\.0$', '', regex=True)
#         )
        
#         articles = articles[articles != ''].unique().tolist()
        
#         if not articles:
#             raise ValidationError('В файле нет ни одного артикля')
        
#         self.cleaned_articles = articles
        
#         return excel_file
    
#     def get_articles(self):
#         return getattr(self, 'cleaned_articles', [])




# cards/forms.py
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
        
        # Сначала читаем только заголовки
        try:
            df_headers = pd.read_excel(excel_file, nrows=0)
        except Exception as e:
            raise ValidationError(f'Не удалось прочитать файл: {e}')
        
        # Ищем колонку с артиклями
        article_col = None
        for col in ['Article', 'Артикул', 'article', 'артикул', 'Article ID']:
            if col in df_headers.columns:
                article_col = col
                break
        
        if not article_col:
            raise ValidationError('Файл должен содержать колонку "Article" или "Артикул"')
        
        # Читаем файл, указывая что колонка с артиклями - строка
        try:
            # ВАЖНО: используем converters или dtype для сохранения ведущих нулей
            df = pd.read_excel(
                excel_file,
                dtype={article_col: str},  # Указываем тип для конкретной колонки
                keep_default_na=False
            )
        except Exception as e:
            raise ValidationError(f'Не удалось прочитать файл: {e}')
        
        # Получаем артикли
        articles_series = df[article_col].astype(str).str.strip()
        
        # Убираем пустые значения
        articles_series = articles_series[articles_series != '']
        articles_series = articles_series[~articles_series.isin(['nan', 'None', ''])]
        
        # ⚠️ НЕ УДАЛЯЕМ .0 !!! Просто берем как есть
        # Ведущие нули сохранятся, потому что мы указали dtype=str
        
        # Уникальные значения
        articles = articles_series.unique().tolist()
        
        if not articles:
            raise ValidationError('В файле нет ни одного артикля')
        
        # Для отладки - проверяем сохранились ли нули
        print(f"Найдено артиклей: {len(articles)}")
        print(f"Примеры с ведущими нулями: {[a for a in articles[:5] if a.startswith('0')]}")
        
        self.cleaned_articles = articles
        
        return excel_file
    
    def get_articles(self):
        return getattr(self, 'cleaned_articles', [])