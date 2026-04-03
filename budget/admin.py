# budget/admin.py
from copy import deepcopy

from django.contrib import admin, messages
from django.urls import path, reverse
from django.utils.html import format_html
from django.http import HttpResponse, Http404
from django.db import models, connection, transaction
from django.utils import timezone

from jsoneditor.forms import JSONEditor

from .models import BudgetVersion, Gl


@admin.register(BudgetVersion)
class BudgetVersionAdmin(admin.ModelAdmin):
    change_list_template = "admin/budget/budgetversion/change_list.html"
    change_form_template = "admin/budget/budgetversion/change_form.html"

    actions = [
        "duplicate_budget_versions",
        "approve_budget_versions",
        "archive_budget_versions",
        "return_to_draft",
        "export_compare_excel",
    ]

    list_display = (
        "number",
        "budget_type",
        "scenario_display",
        "colored_status",
        # "recalculation_badge",
        "date_from",
        "date_to",
        # "description_short",
        "export_buttons",
    )
    list_filter = ("budget_type", "status", "date_from", "date_to")
    search_fields = ("number", "description")
    save_on_top = True

    fieldsets = (
        ("Карточка версии", {
            "fields": (
                "number",
                "budget_type",
                "status",
                "description",
                "date_from",
                "date_to",
                "needs_recalculation",
                "approved_at",
                "approved_by",
            )
        }),
        ("Модель доходов", {
            "fields": ("revenue_param",),
            "classes": ("wide",),
        }),
        ("Модель WB расходов", {
            "fields": ("wb_costs_params",),
            "classes": ("wide",),
        }),
        ("Cash Flow", {
            "fields": ("cf_params",),
            "classes": ("wide",),
        }),
        ("Отчет", {
            "fields": ("report",),
            "classes": ("wide",),
        }),
    )

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
        
        
    
    @admin.action(description="Сравнить выбранные бюджеты (Excel)")
    def export_compare_excel(self, request, queryset):
        count = queryset.count()

        if count < 2:
            self.message_user(
                request,
                "Для сравнения нужно выбрать минимум 2 версии бюджета.",
                level=messages.WARNING,
            )
            return

        if count > 3:
            self.message_user(
                request,
                "Для сравнения можно выбрать не более 3 версий бюджета.",
                level=messages.WARNING,
            )
            return

        versions = list(queryset.order_by("date_from", "id"))

        from budget.reporting.excel.compare_exporter import build_budget_compare_excel_response
        return build_budget_compare_excel_response(versions)
        
        
    @admin.action(description="Вернуть выбранные версии в черновик")
    def return_to_draft(self, request, queryset):
        updated = 0

        for obj in queryset:
            if obj.status == BudgetVersion.Status.DRAFT:
                continue

            obj.status = BudgetVersion.Status.DRAFT
            obj.approved_at = None
            obj.approved_by = None
            obj.save(update_fields=["status", "approved_at", "approved_by"])
            updated += 1

        self.message_user(
            request,
            f"Возвращено в черновик версий: {updated}.",
            level=messages.SUCCESS,
        )

    def get_readonly_fields(self, request, obj=None):
        base_readonly = ("approved_at", "approved_by")

        if obj and obj.status == BudgetVersion.Status.APPROVED:
            return base_readonly + (
                "number",
                "budget_type",
                "status",
                "description",
                "date_from",
                "date_to",
                "revenue_param",
                "wb_costs_params",
                "cf_params",
                "report",
                "needs_recalculation",
            )

        return base_readonly
    
    

    def save_model(self, request, obj, form, change):
        if change and obj.status != BudgetVersion.Status.APPROVED:
            watched_fields = {
                "number",
                "budget_type",
                "description",
                "date_from",
                "date_to",
                "revenue_param",
                "wb_costs_params",
                "cf_params",
            }

            if any(field in form.changed_data for field in watched_fields):
                obj.needs_recalculation = True

        super().save_model(request, obj, form, change)

    def _make_copy_number(self, base_number):
        candidate = f"{base_number} (копия)"
        index = 2

        while BudgetVersion.objects.filter(number=candidate).exists():
            candidate = f"{base_number} (копия {index})"
            index += 1

        return candidate
    
    
    
    @admin.display(description="Сценарий")
    def scenario_display(self, obj):
        scenario_raw = (obj.revenue_param or {}).get("scenario", "base")

        scenario_map = {
            "base": ("#dbeafe", "#1d4ed8", "Базовый"),
            "optimistic": ("#dcfce7", "#166534", "Оптимистичный"),
            "conservative": ("#fef3c7", "#92400e", "Консервативный"),
        }

        bg, color, label = scenario_map.get(
            str(scenario_raw).lower(),
            ("#f3f4f6", "#374151", str(scenario_raw))
        )

        return format_html(
            '<span style="padding:3px 8px;border-radius:2px;'
            'background:{};color:{};font-size:11px;font-weight:700;">{}</span>',
            bg, color, label
        )

    @admin.action(description="Дублировать выбранные версии бюджета")
    def duplicate_budget_versions(self, request, queryset):
        created_versions = 0
        created_gl = 0

        with transaction.atomic():
            for obj in queryset:
                new_version = BudgetVersion.objects.create(
                    number=self._make_copy_number(obj.number),
                    budget_type=obj.budget_type,
                    status=BudgetVersion.Status.DRAFT,
                    description=obj.description,
                    date_from=obj.date_from,
                    date_to=obj.date_to,
                    revenue_param=deepcopy(obj.revenue_param),
                    wb_costs_params=deepcopy(obj.wb_costs_params),
                    cf_params=deepcopy(obj.cf_params),
                    report=None,
                    needs_recalculation=True,
                    approved_at=None,
                    approved_by=None,
                )
                created_versions += 1

                old_gl_rows = Gl.objects.filter(version=obj)

                gl_to_create = []
                for row in old_gl_rows.iterator():
                    gl_to_create.append(
                        Gl(
                            version=new_version,
                            date=row.date,
                            acc=row.acc,
                            subconto=row.subconto,
                            contract=row.contract,
                            dt=row.dt,
                            cr=row.cr,
                            description=row.description,
                            chapter=row.chapter,
                        )
                    )

                if gl_to_create:
                    Gl.objects.bulk_create(gl_to_create, batch_size=1000)
                    created_gl += len(gl_to_create)

        self.message_user(
            request,
            f"Успешно создано версий: {created_versions}. "
            f"Скопировано проводок GL: {created_gl}.",
            level=messages.SUCCESS,
        )

    @admin.action(description="Утвердить выбранные версии бюджета")
    def approve_budget_versions(self, request, queryset):
        updated = 0
        skipped_recalc = 0
        skipped_archived = 0

        for obj in queryset:
            if obj.status == BudgetVersion.Status.ARCHIVED:
                skipped_archived += 1
                continue

            if obj.needs_recalculation:
                skipped_recalc += 1
                continue

            if obj.status == BudgetVersion.Status.APPROVED:
                continue

            obj.status = BudgetVersion.Status.APPROVED
            obj.approved_at = timezone.now()
            obj.approved_by = request.user
            obj.save(update_fields=["status", "approved_at", "approved_by"])
            updated += 1

        if updated:
            self.message_user(
                request,
                f"Утверждено версий: {updated}.",
                level=messages.SUCCESS,
            )

        if skipped_recalc:
            self.message_user(
                request,
                f"Не утверждено версий, т.к. требуется пересчет: {skipped_recalc}.",
                level=messages.WARNING,
            )

        if skipped_archived:
            self.message_user(
                request,
                f"Не утверждено архивных версий: {skipped_archived}.",
                level=messages.WARNING,
            )

    @admin.action(description="Архивировать выбранные версии бюджета")
    def archive_budget_versions(self, request, queryset):
        updated = 0

        for obj in queryset:
            if obj.status == BudgetVersion.Status.ARCHIVED:
                continue

            obj.status = BudgetVersion.Status.ARCHIVED
            obj.save(update_fields=["status"])
            updated += 1

        self.message_user(
            request,
            f"Архивировано версий: {updated}.",
            level=messages.SUCCESS,
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
            path(
                "<int:object_id>/export-excel/",
                self.admin_site.admin_view(self.export_excel),
                name="budget_budgetversion_export_excel",
            ),
        ]
        return custom_urls + urls



    @admin.display(description="Статус")
    def colored_status(self, obj):
        styles = {
            "draft": ("#e5e7eb", "#374151", "Черновик"),
            "approved": ("#dcfce7", "#166534", "Утвержден"),
            "archived": ("#f3f4f6", "#6b7280", "Архив"),
        }
        bg, color, label = styles.get(
            obj.status,
            ("#f3f4f6", "#374151", obj.get_status_display())
        )
        return format_html(
            '<span style="padding:3px 8px;border-radius:2px;'
            'background:{};color:{};font-size:11px;font-weight:700;">{}</span>',
            bg, color, label
        )

    @admin.display(description="Пересчет")
    def recalculation_badge(self, obj):
        if obj.needs_recalculation:
            return format_html(
                '<span style="padding:3px 8px;border-radius:2px;'
                'background:#fef3c7;color:#92400e;font-size:11px;font-weight:700;">'
                'Требует пересчета</span>'
            )

        return format_html(
            '<span style="padding:3px 8px;border-radius:2px;'
            'background:#dcfce7;color:#166534;font-size:11px;font-weight:700;">'
            'Актуален</span>'
        )

    @admin.display(description="Описание")
    def description_short(self, obj):
        if not obj.description:
            return format_html('<span style="color:#9ca3af;">—</span>')
        text = obj.description
        if len(text) > 70:
            text = text[:67] + "..."
        return text

    @admin.display(description="Экспорт")
    def export_buttons(self, obj):
        csv_url = reverse("admin:budget_budgetversion_export_csv", args=[obj.pk])
        pdf_url = reverse("admin:budget_budgetversion_export_pdf", args=[obj.pk])
        excel_url = reverse("admin:budget_budgetversion_export_excel", args=[obj.pk])

        return format_html(
            '<a class="button" href="{}" style="margin-right:6px;">CSV</a>'
            '<a class="button" href="{}" style="margin-right:6px;">PDF</a>'
            '<a class="button" href="{}">Excel</a>',
            csv_url,
            pdf_url,
            excel_url,
        )

    def export_csv(self, request, object_id):
        obj = self.get_object(request, object_id)
        if obj is None:
            raise Http404("BudgetVersion not found")

        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="budget_{obj.id}.csv"'

        sql = """
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

        raw_conn = connection.connection
        if raw_conn is None:
            connection.ensure_connection()
            raw_conn = connection.connection

        with raw_conn.cursor() as cur:
            with cur.copy(sql, (obj.id,)) as copy:
                for chunk in copy:
                    response.write(chunk)

        return response

    def export_pdf(self, request, object_id):
        obj = self.get_object(request, object_id)
        if obj is None:
            raise Http404("BudgetVersion not found")

        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="budget_{obj.id}.pdf"'
        response.write(b"%PDF-1.4\n% test pdf\n")
        return response

    def export_excel(self, request, object_id):
        obj = self.get_object(request, object_id)
        if obj is None:
            raise Http404("BudgetVersion not found")

        from budget.reporting.excel.exporter import build_budget_excel_response
        return build_budget_excel_response(obj)


@admin.register(Gl)
class GlAdmin(admin.ModelAdmin):
    list_display = (
        "date",
        "version",
        "acc",
        "subconto",
        "contract",
        "dt_amount",
        "cr_amount",
        "description",
    )
    list_filter = ("version", "date", "acc")
    search_fields = ("description", "contract__number", "acc__name", "subconto__name")
    autocomplete_fields = ("version", "acc", "subconto", "contract")

    class Media:
        css = {
            "all": (
                "fonts/glyphs.css",
                "css/admin_overrides.css",
            )
        }

    @admin.display(description="Дебет")
    def dt_amount(self, obj):
        return f"{obj.dt / 100:,.2f}".replace(",", " ")

    @admin.display(description="Кредит")
    def cr_amount(self, obj):
        return f"{obj.cr / 100:,.2f}".replace(",", " ")
