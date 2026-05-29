import pandas as pd
from io import BytesIO
from ..models import UPDData
from ..reporting.article_analyzer.report_builder import ArticleAnalysisReportBuilder


class ArticleAnalyzer:
    """Анализатор данных по артиклям"""
    
    def __init__(self, articles_list):
        self.articles = [str(a).strip() for a in articles_list if str(a).strip()]
        
    def analyze(self):
        """Основной метод анализа"""
        if not self.articles:
            return {
                'details': pd.DataFrame(),
                'summary': pd.DataFrame(),
                'articles_found': 0,
                'articles_not_found': 0,
                'total_amount': 0,
                'total_qty': 0,
                'not_found_list': [],
                'total_articles': 0,
            }
        
        total_articles_count = len(self.articles)
        
        # Получаем все строки УПД по артиклям с дополнительными связями
        upd_lines = UPDData.objects.filter(
            upd_sa_name__in=self.articles
        ).select_related(
            'upd_document',
            'upd_document__counterparty',  # Добавляем контрагента
            'nm',
        )
        
        # Собираем данные
        results = []
        
        for line in upd_lines:
            # Получаем название контрагента
            counterparty_name = ''
            if line.upd_document and line.upd_document.counterparty:
                counterparty_name = str(line.upd_document.counterparty)
                # Очищаем от ИНН если есть
                if ' (ИНН:' in counterparty_name:
                    counterparty_name = counterparty_name.split(' (ИНН:')[0]
            
            results.append({
                'Артикул (из УПД)': line.upd_sa_name,
                'Название из УПД': line.upd_title,
                'Бренд': line.brand,
                'nm_id': line.nm.nm_id if line.nm else None,
                'УПД': line.upd_document.number if line.upd_document else None,
                'Дата УПД': line.upd_document.date if line.upd_document else None,
                'Контрагент': counterparty_name,  # Добавляем контрагента
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
            }
        
        df = pd.DataFrame(results)
        
        # Агрегация по артиклям для сводной статистики
        summary = []
        
        for article in self.articles:
            article_data = df[df['Артикул (из УПД)'] == article]
            
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
        
        # Определяем ненайденные артикли
        found_articles = summary_df[summary_df['Найден в системе'] == 'Да']['Артикль'].tolist()
        articles_not_found = [a for a in self.articles if a not in found_articles]
        
        return {
            'details': df,  # Теперь в df есть колонка 'Контрагент'
            'summary': summary_df[summary_df['Найден в системе'] == 'Да'],
            'articles_found': len(found_articles),
            'articles_not_found': len(articles_not_found),
            'total_amount': summary_df['Общая стоимость (с НДС)'].sum() if not summary_df.empty else 0,
            'total_qty': summary_df['Общее кол-во товара'].sum() if not summary_df.empty else 0,
            'not_found_list': articles_not_found,
            'total_articles': total_articles_count,
        }
    
    def to_excel(self):
        """Экспорт в Excel с помощью ReportBuilder"""
        result = self.analyze()
        
        # Строим отчет
        builder = ArticleAnalysisReportBuilder()
        workbook = builder.build(
            summary_df=result['summary'],
            details_df=result['details'],
            articles_not_found=result['not_found_list'],
            total_articles=result.get('total_articles', 0),
            articles_found=result.get('articles_found', 0)
        )
        
        # Сохраняем в BytesIO
        output = BytesIO()
        workbook.save(output)
        output.seek(0)
        return output