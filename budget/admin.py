from django.contrib import admin
from django.urls import path, reverse
from django.utils.html import format_html
from django.http import HttpResponse
from .models import BudgetVersion
from django.db import models, connection

from jsoneditor.forms import JSONEditor

# Register your models here.
@admin.register(BudgetVersion)
class BudgetVersionAdmin(admin.ModelAdmin):
    

    list_display = (
        "number",
        "budget_type",
        "date_from",
        "date_to",
        "description",
        "export_buttons",
        
    )
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:object_id>/export-csv/",
                self.admin_site.admin_view(self.export_csv),
                name="budget_budgetversion_export_csv",
            ),
            path(
                "<int:object_id>/export-pdf/",
                self.admin_site.admin_view(self.export_pdf),
                name="budget_budgetversion_export_pdf",
            ),
        ]
        return custom_urls + urls

    # 🔥 кнопки в списке
    @admin.display(description="Экспорт")
    def export_buttons(self, obj):
        csv_url = reverse(
            "admin:budget_budgetversion_export_csv",
            args=[obj.pk],
        )
        pdf_url = reverse(
            "admin:budget_budgetversion_export_pdf",
            args=[obj.pk],
        )

        return format_html(
            '<a class="button" href="{}">CSV</a>&nbsp;'
            '<a class="button" href="{}">PDF</a>',
            csv_url,
            pdf_url,
        )

    def export_csv(self, request, object_id):
            obj = self.get_object(request, object_id)

            response = HttpResponse(content_type="text/csv; charset=utf-8")
            response["Content-Disposition"] = f'attachment; filename="budget_{obj.id}.csv"'

            sql = f"""
                COPY (
                    SELECT
                        x.date_from,
                        (lv1.code::text || ' ' || lv1.name::text) AS activity,
                        (lv2.code::text || ' ' || lv2.name::text) AS operation,
                        (lv3.code::text || ' ' || lv3.name::text) AS item,
                        (i.code::text || ' ' || i.name::text) AS subitem,
                        x.dt,
                        x.cr,
                        x.amount,
                        x.description
                    FROM (
                        SELECT
                            "date" AS date_from,
                            round(dt / 100.0, 2) AS dt,
                            round(cr / 100.0, 2) AS cr,
                            round((dt - cr) / 100.0, 2) AS amount,
                            subconto_id,
                            description
                        FROM public.budget_gl
                        WHERE version_id = %s
                    ) x
                    JOIN corporate_cfitems i   ON i.id = x.subconto_id
                    JOIN corporate_cfitems lv3 ON lv3.id = i.parent_id
                    JOIN corporate_cfitems lv2 ON lv2.id = lv3.parent_id
                    JOIN corporate_cfitems lv1 ON lv1.id = lv2.parent_id
                )
                TO STDOUT WITH (FORMAT CSV, HEADER TRUE)
            """

            # raw psycopg3 connection
            raw_conn = connection.connection
            if raw_conn is None:
                connection.ensure_connection()
                raw_conn = connection.connection

            with raw_conn.cursor() as cur:
                with cur.copy(sql, (obj.id,)) as copy:
                    for chunk in copy:
                        response.write(chunk)

            return response

    # 🔥 PDF
    def export_pdf(self, request, object_id):
        obj = self.get_object(request, object_id)

        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="budget_{obj.id}.pdf"'
        )

        # заглушка
        response.write(b"%PDF-1.4\n% test pdf\n")

        return response
    

    formfield_overrides = {
        models.JSONField: {"widget": JSONEditor},
    }

    class Media:
        css = {
            "all": (
                "fonts/glyphs.css",
                "css/admin_overrides.css",
            )
        }