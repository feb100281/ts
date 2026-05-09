# # utils/upd_issues/pdf_exporter.py
# from pathlib import Path
# from datetime import datetime
# from django.conf import settings
# from django.http import HttpResponse
# from django.template.loader import render_to_string
# from weasyprint import CSS, HTML


# def build_upd_issues_pdf_response(files_df, summary_stats):
#     """
#     Генерация PDF-сопроводилки к отчету по ошибкам в УПД
#     """
    
#     # Формируем список файлов с ошибками
#     files_list = []
#     for _, row in files_df.iterrows():
#         files_list.append({
#             'full_name': row['full_name'],
#             'supplier': row.get('supplier', '—'),
#             'total_issues': int(row['total_issues']),
#             'name_mismatch': int(row['name_mismatch']),
#             'article_mismatch': int(row.get('article_mismatch', 0)),
#             'size_mismatch': int(row['size_mismatch']),
#             'vat_mismatch': int(row['vat_mismatch']),
#             'cert_issues': int(row['cert_issues']),
#             'total_positions': int(row['total_positions']),
#         })
    
#     # Группируем по поставщикам
#     suppliers_dict = {}
#     for file in files_list:
#         supplier = file['supplier']
#         if supplier not in suppliers_dict:
#             suppliers_dict[supplier] = []
#         suppliers_dict[supplier].append(file)
    
#     # Формируем структуру для шаблона с итогами по каждому поставщику
#     supplier_groups = []
#     for supplier, files in suppliers_dict.items():
#         group = {
#             'supplier': supplier,
#             'files': files,
#             'total_positions': sum(f['total_positions'] for f in files),
#             'total_name_mismatch': sum(f['name_mismatch'] for f in files),
#             'total_article_mismatch': sum(f['article_mismatch'] for f in files),
#             'total_size_mismatch': sum(f['size_mismatch'] for f in files),
#             'total_vat_mismatch': sum(f['vat_mismatch'] for f in files),
#             'total_cert_issues': sum(f['cert_issues'] for f in files),
#         }
#         supplier_groups.append(group)
    
#     # Контекст для шаблона
#     context = {
#         'company': 'ООО "ТРЕНДСЕТТЕР"',
#         'title': 'Отчет по результатам проверки УПД',
#         'report_date': datetime.now().strftime('%d.%m.%Y'),
#         'report_time': datetime.now().strftime('%H:%M'),
#         'total_files': summary_stats.get('total_files', 0),
#         'total_issues': summary_stats.get('total_issues', 0),
#         'total_positions': summary_stats.get('total_positions', 0),
#         'name_mismatch': summary_stats.get('name_mismatch', 0),
#         'article_mismatch': summary_stats.get('article_mismatch', 0),
#         'size_mismatch': summary_stats.get('size_mismatch', 0),
#         'vat_mismatch': summary_stats.get('vat_mismatch', 0),
#         'cert_issues': summary_stats.get('cert_issues', 0),
#         'supplier_groups': supplier_groups,
#     }
    
#     # Генерируем HTML
#     html = render_to_string(
#         "upd_issues/upd_issues_report.html",
#         context,
#     )
    
#     # Путь к CSS файлу в статике
#     css_path = Path(settings.BASE_DIR) / "static" / "css" / "upd_issues" / "report.css"
    
#     stylesheets = []
#     if css_path.exists():
#         stylesheets.append(CSS(filename=str(css_path)))
    
#     # Генерируем PDF
#     pdf_bytes = HTML(
#         string=html,
#         base_url=str(settings.BASE_DIR),
#     ).write_pdf(
#         stylesheets=stylesheets,
#         presentational_hints=True,
#     )
    
#     # Формируем ответ
#     response = HttpResponse(pdf_bytes, content_type="application/pdf")
#     response["Content-Disposition"] = f'attachment; filename="upd_issues_report_{datetime.now().strftime("%Y%m%d_%H%M")}.pdf"'
    
#     return response



# utils/upd_issues/pdf_exporter.py
from pathlib import Path
from datetime import datetime
from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import CSS, HTML


def build_upd_issues_pdf_response(files_df, summary_stats):
    """
    Генерация PDF-сопроводилки к отчету по ошибкам в УПД
    """
    
    # Формируем список файлов с ошибками
    files_list = []
    for _, row in files_df.iterrows():
        files_list.append({
            'full_name': row['full_name'],
            'supplier': row.get('supplier', '—'),
            'total_issues': int(row['total_issues']),
            'name_mismatch': int(row['name_mismatch']),
            'article_mismatch': int(row.get('article_mismatch', 0)),
            'size_mismatch': int(row['size_mismatch']),
            'vat_mismatch': int(row['vat_mismatch']),
            'cert_issues': int(row['cert_issues']),
            'total_positions': int(row['total_positions']),  # количество позиций
        })
    
    # Группируем по поставщикам
    suppliers_dict = {}
    for file in files_list:
        supplier = file['supplier']
        if supplier not in suppliers_dict:
            suppliers_dict[supplier] = []
        suppliers_dict[supplier].append(file)
    
    # Формируем структуру для шаблона с итогами по каждому поставщику
    supplier_groups = []
    for supplier, files in suppliers_dict.items():
        group = {
            'supplier': supplier,
            'files': files,
            'total_positions': sum(f['total_positions'] for f in files),
            'total_name_mismatch': sum(f['name_mismatch'] for f in files),
            'total_article_mismatch': sum(f['article_mismatch'] for f in files),
            'total_size_mismatch': sum(f['size_mismatch'] for f in files),
            'total_vat_mismatch': sum(f['vat_mismatch'] for f in files),
            'total_cert_issues': sum(f['cert_issues'] for f in files),
        }
        supplier_groups.append(group)
    
    # Для общего итога используем summary_stats (там правильные суммы)
    context = {
        'company': 'ООО "ТРЕНДСЕТТЕР"',
        'title': 'Отчет по результатам проверки УПД',
        'report_date': datetime.now().strftime('%d.%m.%Y'),
        'report_time': datetime.now().strftime('%H:%M'),
        'total_files': summary_stats.get('total_files', 0),
        'total_issues': summary_stats.get('total_issues', 0),
        'total_positions': summary_stats.get('total_positions', 0),  # берем из summary_stats
        'name_mismatch': summary_stats.get('name_mismatch', 0),
        'article_mismatch': summary_stats.get('article_mismatch', 0),
        'size_mismatch': summary_stats.get('size_mismatch', 0),
        'vat_mismatch': summary_stats.get('vat_mismatch', 0),
        'cert_issues': summary_stats.get('cert_issues', 0),
        'supplier_groups': supplier_groups,
    }
    
    # Генерируем HTML
    html = render_to_string(
        "upd_issues/upd_issues_report.html",
        context,
    )
    
    # Путь к CSS файлу в статике
    css_path = Path(settings.BASE_DIR) / "static" / "css" / "upd_issues" / "report.css"
    
    stylesheets = []
    if css_path.exists():
        stylesheets.append(CSS(filename=str(css_path)))
    
    # Генерируем PDF
    pdf_bytes = HTML(
        string=html,
        base_url=str(settings.BASE_DIR),
    ).write_pdf(
        stylesheets=stylesheets,
        presentational_hints=True,
    )
    
    # Формируем ответ
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="upd_issues_report_{datetime.now().strftime("%Y%m%d_%H%M")}.pdf"'
    
    return response