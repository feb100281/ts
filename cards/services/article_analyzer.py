# # cards/services/article_analyzer.py
# import pandas as pd
# from io import BytesIO
# from ..models import UPDData
# from ..reporting.article_analyzer.report_builder import ArticleAnalysisReportBuilder


# class ArticleAnalyzer:
#     """Анализатор данных по артиклям"""
    
#     def __init__(self, articles_list):
#         self.articles = [str(a).strip() for a in articles_list if str(a).strip()]
        
#     def analyze(self):
#         """Основной метод анализа"""
#         if not self.articles:
#             return {
#                 'details': pd.DataFrame(),
#                 'summary': pd.DataFrame(),
#                 'articles_found': 0,
#                 'articles_not_found': 0,
#                 'total_amount': 0,
#                 'total_qty': 0,
#                 'not_found_list': [],
#                 'total_articles': 0,
#             }
        
#         total_articles_count = len(self.articles)
        
#         # Получаем все строки УПД по артиклям с дополнительными связями
#         upd_lines = UPDData.objects.filter(
#             upd_sa_name__in=self.articles
#         ).select_related(
#             'upd_document',
#             'upd_document__counterparty',  # Добавляем контрагента
#             'nm',
#         )
        
#         # Собираем данные
#         results = []
        
#         for line in upd_lines:
#             # Получаем название контрагента
#             counterparty_name = ''
#             if line.upd_document and line.upd_document.counterparty:
#                 counterparty_name = str(line.upd_document.counterparty)
#                 # Очищаем от ИНН если есть
#                 if ' (ИНН:' in counterparty_name:
#                     counterparty_name = counterparty_name.split(' (ИНН:')[0]
            
#             results.append({
#                 'Артикул (из УПД)': line.upd_sa_name,
#                 'Название из УПД': line.upd_title,
#                 'Бренд': line.brand,
#                 'nm_id': line.nm.nm_id if line.nm else None,
#                 'УПД': line.upd_document.number if line.upd_document else None,
#                 'Дата УПД': line.upd_document.date if line.upd_document else None,
#                 'Контрагент': counterparty_name,  # Добавляем контрагента
#                 'Количество': float(line.upd_qty) if line.upd_qty else 0,
#                 'Цена без НДС': float(line.upd_price_vatless) if line.upd_price_vatless else 0,
#                 'Стоимость с НДС': float(line.upd_amount_vatadd) if line.upd_amount_vatadd else 0,
#             })
        
#         if not results:
#             return {
#                 'details': pd.DataFrame(),
#                 'summary': pd.DataFrame(),
#                 'articles_found': 0,
#                 'articles_not_found': total_articles_count,
#                 'total_amount': 0,
#                 'total_qty': 0,
#                 'not_found_list': self.articles,
#                 'total_articles': total_articles_count,
#             }
        
#         df = pd.DataFrame(results)
        
#         # Агрегация по артиклям для сводной статистики
#         summary = []
        
#         for article in self.articles:
#             article_data = df[df['Артикул (из УПД)'] == article]
            
#             if article_data.empty:
#                 summary.append({
#                     'Артикль': article,
#                     'Найден в системе': 'Нет',
#                     'Кол-во позиций': 0,
#                     'Общее кол-во товара': 0,
#                     'Общая стоимость (с НДС)': 0,
#                     'Мин. цена': None,
#                     'Макс. цена': None,
#                     'Средняя цена': None,
#                     'Медианная цена': None,
#                 })
#                 continue
            
#             prices = article_data['Цена без НДС']
            
#             summary.append({
#                 'Артикль': article,
#                 'Найден в системе': 'Да',
#                 'Кол-во позиций': len(article_data),
#                 'Общее кол-во товара': article_data['Количество'].sum(),
#                 'Общая стоимость (с НДС)': article_data['Стоимость с НДС'].sum(),
#                 'Мин. цена': prices.min() if not prices.empty else None,
#                 'Макс. цена': prices.max() if not prices.empty else None,
#                 'Средняя цена': prices.mean() if not prices.empty else None,
#                 'Медианная цена': prices.median() if not prices.empty else None,
#             })
        
#         summary_df = pd.DataFrame(summary)
        
#         # Определяем ненайденные артикли
#         found_articles = summary_df[summary_df['Найден в системе'] == 'Да']['Артикль'].tolist()
#         articles_not_found = [a for a in self.articles if a not in found_articles]
        
#         return {
#             'details': df,  # Теперь в df есть колонка 'Контрагент'
#             'summary': summary_df[summary_df['Найден в системе'] == 'Да'],
#             'articles_found': len(found_articles),
#             'articles_not_found': len(articles_not_found),
#             'total_amount': summary_df['Общая стоимость (с НДС)'].sum() if not summary_df.empty else 0,
#             'total_qty': summary_df['Общее кол-во товара'].sum() if not summary_df.empty else 0,
#             'not_found_list': articles_not_found,
#             'total_articles': total_articles_count,
#         }
    
#     def to_excel(self):
#         """Экспорт в Excel с помощью ReportBuilder"""
#         result = self.analyze()
        
#         # Строим отчет
#         builder = ArticleAnalysisReportBuilder()
#         workbook = builder.build(
#             summary_df=result['summary'],
#             details_df=result['details'],
#             articles_not_found=result['not_found_list'],
#             total_articles=result.get('total_articles', 0),
#             articles_found=result.get('articles_found', 0)
#         )
        
#         # Сохраняем в BytesIO
#         output = BytesIO()
#         workbook.save(output)
#         output.seek(0)
#         return output



# # cards/services/article_analyzer.py
# import pandas as pd
# from io import BytesIO
# from django.db.models import Q
# from ..models import UPDData, USK  # USK, а не CardUSK
# from ..reporting.article_analyzer.report_builder import ArticleAnalysisReportBuilder


# class ArticleAnalyzer:
#     """Анализатор данных по артиклям с поддержкой USK-маппинга"""
    
#     def __init__(self, articles_list):
#         self.articles = [str(a).strip() for a in articles_list if str(a).strip()]
        
#     def _get_mapped_articles(self):
#         """
#         Маппинг исходных артиклей на usk_sa_name.
#         Возвращает:
#             - original_to_usk: dict {original_article: usk_article}
#             - not_mapped_articles: list артиклей, которых нет в USK
#         """
#         if not self.articles:
#             return {}, []
        
#         # Ищем все соответствия в USK
#         usk_records = USK.objects.filter(
#             sa_name__in=self.articles
#         ).values('sa_name', 'usk_sa_name')
        
#         original_to_usk = {}
#         found_in_usk = set()
        
#         for record in usk_records:
#             original = record['sa_name']
#             usk_article = record['usk_sa_name']
#             original_to_usk[original] = usk_article
#             found_in_usk.add(original)
        
#         not_mapped_articles = [a for a in self.articles if a not in found_in_usk]
        
#         return original_to_usk, not_mapped_articles
    
#     def analyze(self):
#         """Основной метод анализа с маппингом через USK"""
#         if not self.articles:
#             return self._empty_result()
        
#         total_articles_count = len(self.articles)
        
#         # 1. Получаем маппинг артиклей
#         original_to_usk, not_mapped_articles = self._get_mapped_articles()
        
#         # 2. Формируем список артикулов для поиска в UPDData
#         # Если у артикля есть usk_sa_name — ищем его, иначе ищем исходный
#         search_articles = []
#         article_search_map = {}  # {search_article: original_article}
        
#         for original in self.articles:
#             search_article = original_to_usk.get(original, original)
#             search_articles.append(search_article)
#             article_search_map[search_article] = original
        
#         # 3. Ищем строки УПД по этим артикулам
#         upd_lines = UPDData.objects.filter(
#             upd_sa_name__in=search_articles
#         ).select_related(
#             'upd_document',
#             'upd_document__counterparty',
#             'nm',
#         )
        
#         # 4. Собираем детальные данные
#         results = []
#         found_search_articles = set()
        
#         for line in upd_lines:
#             search_article = line.upd_sa_name
#             original_article = article_search_map.get(search_article, search_article)
#             found_search_articles.add(search_article)
            
#             counterparty_name = ''
#             if line.upd_document and line.upd_document.counterparty:
#                 counterparty_name = str(line.upd_document.counterparty)
#                 if ' (ИНН:' in counterparty_name:
#                     counterparty_name = counterparty_name.split(' (ИНН:')[0]
            
#             results.append({
#                 'Исходный артикль': original_article,
#                 'Артикул USK': search_article if original_to_usk.get(original_article) else None,
#                 'Артикул (из УПД)': line.upd_sa_name,
#                 'Название из УПД': line.upd_title,
#                 'Бренд': line.brand,
#                 'nm_id': line.nm.nm_id if line.nm else None,
#                 'УПД': line.upd_document.number if line.upd_document else None,
#                 'Дата УПД': line.upd_document.date if line.upd_document else None,
#                 'Контрагент': counterparty_name,
#                 'Количество': float(line.upd_qty) if line.upd_qty else 0,
#                 'Цена без НДС': float(line.upd_price_vatless) if line.upd_price_vatless else 0,
#                 'Стоимость с НДС': float(line.upd_amount_vatadd) if line.upd_amount_vatadd else 0,
#             })
        
#         if not results:
#             return {
#                 'details': pd.DataFrame(),
#                 'summary': pd.DataFrame(),
#                 'articles_found': 0,
#                 'articles_not_found': total_articles_count,
#                 'total_amount': 0,
#                 'total_qty': 0,
#                 'not_found_list': self.articles,
#                 'total_articles': total_articles_count,
#                 'not_mapped_articles': not_mapped_articles,
#             }
        
#         df = pd.DataFrame(results)
        
#         # 5. Агрегация по ИСХОДНЫМ артиклям
#         summary = []
        
#         for article in self.articles:
#             article_data = df[df['Исходный артикль'] == article]
            
#             if article_data.empty:
#                 summary.append({
#                     'Артикль': article,
#                     'Найден в системе': 'Нет',
#                     'Кол-во позиций': 0,
#                     'Общее кол-во товара': 0,
#                     'Общая стоимость (с НДС)': 0,
#                     'Мин. цена': None,
#                     'Макс. цена': None,
#                     'Средняя цена': None,
#                     'Медианная цена': None,
#                 })
#                 continue
            
#             prices = article_data['Цена без НДС']
            
#             summary.append({
#                 'Артикль': article,
#                 'Найден в системе': 'Да',
#                 'Кол-во позиций': len(article_data),
#                 'Общее кол-во товара': article_data['Количество'].sum(),
#                 'Общая стоимость (с НДС)': article_data['Стоимость с НДС'].sum(),
#                 'Мин. цена': prices.min() if not prices.empty else None,
#                 'Макс. цена': prices.max() if not prices.empty else None,
#                 'Средняя цена': prices.mean() if not prices.empty else None,
#                 'Медианная цена': prices.median() if not prices.empty else None,
#             })
        
#         summary_df = pd.DataFrame(summary)
        
#         found_articles = summary_df[summary_df['Найден в системе'] == 'Да']['Артикль'].tolist()
#         articles_not_found = [a for a in self.articles if a not in found_articles]
        
#         return {
#             'details': df,
#             'summary': summary_df[summary_df['Найден в системе'] == 'Да'],
#             'articles_found': len(found_articles),
#             'articles_not_found': len(articles_not_found),
#             'total_amount': summary_df['Общая стоимость (с НДС)'].sum() if not summary_df.empty else 0,
#             'total_qty': summary_df['Общее кол-во товара'].sum() if not summary_df.empty else 0,
#             'not_found_list': articles_not_found,
#             'not_mapped_articles': not_mapped_articles,
#             'total_articles': total_articles_count,
#         }
    
#     def _empty_result(self):
#         return {
#             'details': pd.DataFrame(),
#             'summary': pd.DataFrame(),
#             'articles_found': 0,
#             'articles_not_found': 0,
#             'total_amount': 0,
#             'total_qty': 0,
#             'not_found_list': [],
#             'not_mapped_articles': [],
#             'total_articles': 0,
#         }
    
#     def to_excel(self):
#         """Экспорт в Excel"""
#         result = self.analyze()
        
#         builder = ArticleAnalysisReportBuilder()
#         workbook = builder.build(
#             summary_df=result['summary'],
#             details_df=result['details'],
#             articles_not_found=result['not_found_list'],
#             total_articles=result.get('total_articles', 0),
#             articles_found=result.get('articles_found', 0),
#             not_mapped_articles=result.get('not_mapped_articles', [])
#         )
        
#         output = BytesIO()
#         workbook.save(output)
#         output.seek(0)
#         return output




# cards/services/article_analyzer.py
import pandas as pd
from io import BytesIO
from django.db.models import Q
from ..models import UPDData, USK
from ..reporting.article_analyzer.report_builder import ArticleAnalysisReportBuilder




class ArticleAnalyzer:
    """Анализатор данных по артиклям с поддержкой USK-маппинга"""
    
    def __init__(self, articles_list):
        self.articles = [str(a).strip() for a in articles_list if str(a).strip()]
        
    def _get_mapped_articles(self):
        """
        Маппинг исходных артиклей на usk (числовой ID).
        Возвращает:
            - original_to_usk: dict {original_article: usk_number}  # ← теперь число!
            - not_mapped_articles: list артиклей, которых нет в USK
        """
        if not self.articles:
            return {}, []
        
        # Ищем все соответствия в USK
        usk_records = USK.objects.filter(
            sa_name__in=self.articles
        ).values('sa_name', 'usk')  # ← берем usk (числовой)
        
        original_to_usk = {}
        found_in_usk = set()
        
        for record in usk_records:
            original = record['sa_name']
            usk_number = record['usk']  # ← это число (например, 975101002)
            original_to_usk[original] = usk_number
            found_in_usk.add(original)
        
        not_mapped_articles = [a for a in self.articles if a not in found_in_usk]
        
        return original_to_usk, not_mapped_articles
    
    def analyze(self):
        """Основной метод анализа с маппингом через USK"""
        if not self.articles:
            return self._empty_result()
        
        total_articles_count = len(self.articles)
        
        # 1. Получаем маппинг артиклей (оригинал → usk число)
        original_to_usk, not_mapped_articles = self._get_mapped_articles()
        
        # 2. Формируем список для поиска в UPDData
        # Если у артикля есть usk (число) — ищем по nm_id
        # Если нет — ищем по upd_sa_name
        search_nm_ids = []      # для поиска по nm_id
        search_sa_names = []    # для поиска по upd_sa_name
        article_search_map = {}  # {search_value: original_article, type: 'nm_id' or 'sa_name'}
        
        for original in self.articles:
            if original in original_to_usk:
                usk_number = original_to_usk[original]
                search_nm_ids.append(usk_number)
                article_search_map[usk_number] = {
                    'original': original,
                    'type': 'nm_id'
                }
            else:
                search_sa_names.append(original)
                article_search_map[original] = {
                    'original': original,
                    'type': 'sa_name'
                }
        
        # 3. Ищем строки УПД
        upd_lines = UPDData.objects.filter(
            Q(nm_id__in=search_nm_ids) |      # ← ищем по числовому nm_id
            Q(upd_sa_name__in=search_sa_names)  # ← ищем по строковому артикулу
        ).select_related(
            'upd_document',
            'upd_document__counterparty',
            'nm',
        )
        
        # 4. Собираем детальные данные
        results = []
        
        for line in upd_lines:
            # Определяем, как нашли эту строку
            original_article = None
            match_type = None
            
            # Проверяем, нашли по nm_id?
            if line.nm_id and line.nm_id in article_search_map:
                original_article = article_search_map[line.nm_id]['original']
                match_type = 'nm_id (USK)'
            # Или нашли по upd_sa_name?
            elif line.upd_sa_name in article_search_map:
                original_article = article_search_map[line.upd_sa_name]['original']
                match_type = 'upd_sa_name'
            else:
                continue  # такой строки быть не должно
            
            counterparty_name = ''
            if line.upd_document and line.upd_document.counterparty:
                counterparty_name = str(line.upd_document.counterparty)
                if ' (ИНН:' in counterparty_name:
                    counterparty_name = counterparty_name.split(' (ИНН:')[0]
            
            results.append({
                'Исходный артикль': original_article,
                'Тип совпадения': match_type,
                'USK (nm_id)': line.nm_id,
                'Артикул USK': original_to_usk.get(original_article),
                'Артикул (из УПД)': line.upd_sa_name,
                'Название из УПД': line.upd_title,
                'Бренд': line.brand,
                'УПД': line.upd_document.number if line.upd_document else None,
                'Дата УПД': line.upd_document.date if line.upd_document else None,
                'Контрагент': counterparty_name,
                'Количество': float(line.upd_qty) if line.upd_qty else 0,
                'Цена без НДС': float(line.upd_price_vatless) if line.upd_price_vatless else 0,
                'Стоимость с НДС': float(line.upd_amount_vatadd) if line.upd_amount_vatadd else 0,
            })
        
        if not results:
            return {
                'details': pd.DataFrame(),
                'summary': pd.DataFrame(),
                'articles_found': 0,
                'articles_not_found': total_articles_count,
                'total_amount': 0,
                'total_qty': 0,
                'not_found_list': self.articles,
                'total_articles': total_articles_count,
                'not_mapped_articles': not_mapped_articles,
            }
        
        df = pd.DataFrame(results)
        
        # 5. Агрегация по ИСХОДНЫМ артиклям
        summary = []
        
        for article in self.articles:
            article_data = df[df['Исходный артикль'] == article]
            
            if article_data.empty:
                summary.append({
                    'Артикль': article,
                    'Найден в системе': 'Нет',
                    'Кол-во позиций': 0,
                    'Общее кол-во товара': 0,
                    'Общая стоимость (с НДС)': 0,
                    'Мин. цена': None,
                    'Макс. цена': None,
                    'Средняя цена': None,
                    'Медианная цена': None,
                })
                continue
            
            prices = article_data['Цена без НДС']
            
            summary.append({
                'Артикль': article,
                'Найден в системе': 'Да',
                'Кол-во позиций': len(article_data),
                'Общее кол-во товара': article_data['Количество'].sum(),
                'Общая стоимость (с НДС)': article_data['Стоимость с НДС'].sum(),
                'Мин. цена': prices.min() if not prices.empty else None,
                'Макс. цена': prices.max() if not prices.empty else None,
                'Средняя цена': prices.mean() if not prices.empty else None,
                'Медианная цена': prices.median() if not prices.empty else None,
            })
        
        summary_df = pd.DataFrame(summary)
        
        found_articles = summary_df[summary_df['Найден в системе'] == 'Да']['Артикль'].tolist()
        articles_not_found = [a for a in self.articles if a not in found_articles]
        
        return {
            'details': df,
            'summary': summary_df[summary_df['Найден в системе'] == 'Да'],
            'articles_found': len(found_articles),
            'articles_not_found': len(articles_not_found),
            'total_amount': summary_df['Общая стоимость (с НДС)'].sum() if not summary_df.empty else 0,
            'total_qty': summary_df['Общее кол-во товара'].sum() if not summary_df.empty else 0,
            'not_found_list': articles_not_found,
            'not_mapped_articles': not_mapped_articles,
            'total_articles': total_articles_count,
        }
    
    def _empty_result(self):
        return {
            'details': pd.DataFrame(),
            'summary': pd.DataFrame(),
            'articles_found': 0,
            'articles_not_found': 0,
            'total_amount': 0,
            'total_qty': 0,
            'not_found_list': [],
            'not_mapped_articles': [],
            'total_articles': 0,
        }
    
    def to_excel(self):
        """Экспорт в Excel"""
        result = self.analyze()
        
        builder = ArticleAnalysisReportBuilder()
        workbook = builder.build(
            summary_df=result['summary'],
            details_df=result['details'],
            articles_not_found=result['not_found_list'],
            total_articles=result.get('total_articles', 0),
            articles_found=result.get('articles_found', 0),
            not_mapped_articles=result.get('not_mapped_articles', [])
        )
        
        output = BytesIO()
        workbook.save(output)
        output.seek(0)
        return output