# from django.contrib import admin, messages
# from django.shortcuts import redirect
# from .models import BankStatements, CfData, CfSplits
# from utils.bsparsers.bsupdater import update_cf_data
# from django.utils.safestring import mark_safe

# from django.shortcuts import redirect


# class CfSplitsInline(admin.StackedInline):
#     model = CfSplits
#     extra = 1

# @admin.register(BankStatements)
# class MigrationsAdmin(admin.ModelAdmin):
#     list_display = ("__str__","bb", "eb", "uploaded_at", 'file')
#     change_form_template = "admin/services/migrations/change_form.html"
#     file_path = None
    
#     fieldsets = (
#         (
#             "Файл выписки",
#             {"fields": ("file",)},
#         ),
#         (
#             "Информация",
#             {
#                 "fields": (
#                     "owner",
#                     "ba",
#                     "start",
#                     "finish",
#                     "bb",
#                     "eb"
                    
#                 )
#             },
#         )
        
#     )
    
    

#     def render_change_form(self, request, context, *args, **kwargs):
#         obj = context.get('original')
#         if obj and obj.file:
#             self.file_path = obj.file.path
#         return super().render_change_form(request, context, *args, **kwargs)

#     def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
#         if request.method == "POST" and "apply_migration" in request.POST:
#             obj = self.get_object(request, object_id)

#             if obj and obj.file:
#                 result = update_cf_data(obj.file.path, obj.pk)   # или object_id
#                 messages.success(request, mark_safe(result))
#             else:
#                 messages.error(request, "Файл не найден")

#             return redirect(request.path)

#         return super().changeform_view(request, object_id, form_url, extra_context)


# @admin.register(CfData)
# class CfDataAdmin(admin.ModelAdmin):
#     list_display = ("date","dt", "cr", "temp", 'cp',"intercompany")
#     inlines = [CfSplitsInline,]
    
    
#     fieldsets = (
#         (
#             "Основное",
#             {"fields": ("bs","doc_type",'doc_numner',"doc_date","date","temp","dt","cr")},
#         ),
        
#         (
#             "Реффересы",
#             {"fields": ("cp_bs_name","cp","cp_final","contract","cfitem")},
#         ),        
        
#         (
#             "Детали",
#             {
#                 "fields": (
#                     "ba",
#                     "tax_id",                   
#                     "payer_account",
#                     "reciver_account",
#                     "vat_rate",                    
#                     "intercompany"
                    
#                 )
#             },
#         )
#     )




# treasury/admin.py

from django.contrib import admin, messages
from django.db.models import Sum, Count
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import BankStatements, CfData, CfSplits
from utils.bsparsers.bsupdater import update_cf_data

from utils.choises import CURRENCY_FLAGS, CURRENCY_SYMBOLS
# ---------- UI helpers ----------

def money(v):
    if v is None:
        return "—"
    return f"{v:,.2f}".replace(",", " ")


def badge(text, tone="slate"):
    tones = {
        "slate": ("#0f172a", "rgba(148,163,184,.25)"),
        "green": ("#052e16", "rgba(34,197,94,.22)"),
        "red": ("#450a0a", "rgba(239,68,68,.22)"),
        "amber": ("#451a03", "rgba(245,158,11,.22)"),
        "blue": ("#0b2559", "rgba(59,130,246,.22)"),
        "pink": ("#4a044e", "rgba(236,72,153,.22)"),
    }
    fg, bg = tones.get(tone, tones["slate"])
    return format_html(
        '<span style="display:inline-flex;align-items:center;gap:6px;'
        'padding:2px 8px;border-radius:999px;'
        'background:{};color:{};font-weight:700;font-size:12px;'
        'box-shadow:0 0 0 1px rgba(148,163,184,.20) inset;">{}</span>',
        bg, fg, text
    )


# ---------- Inlines ----------

class CfDataInline(admin.TabularInline):
    """
    Транзакции прямо на форме выписки.
    Чтобы не тормозило на больших выписках — показываем только первые N строк
    через max_num (БЕЗ slice, иначе Django ругается при фильтрах).
    """
    model = CfData
    extra = 0
    can_delete = False
    fields = ("date", "flow", "amount", "cp_final", "contract", "cfitem", "intercompany", "open_link")
    readonly_fields = ("flow", "amount", "open_link")
    autocomplete_fields = ("cp_final", "contract", "cfitem")
    show_change_link = False

    max_num = 80  # <-- ограничение количества строк, которые админка покажет

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("cp_final", "contract", "cfitem").order_by("-date", "-id")
        # ВАЖНО: никаких [:self.max_num] тут быть не должно

    @admin.display(description="Поток")
    def flow(self, obj):
        if (obj.dt or 0) > 0:
            return badge("Дт", "red")
        if (obj.cr or 0) > 0:
            return badge("Кт", "green")
        return "—"

    @admin.display(description="Сумма")
    def amount(self, obj):
        val = (obj.dt or 0) - (obj.cr or 0)
        tone = "green" if val >= 0 else "red"
        return badge(money(abs(val)), tone)

    @admin.display(description="Открыть")
    def open_link(self, obj):
        url = reverse("admin:treasury_cfdata_change", args=[obj.pk])
        return format_html('<a class="button" href="{}">↗</a>', url)



class CfSplitsInline(admin.TabularInline):
    model = CfSplits
    extra = 0
    fields = ("flow", "amount", "cfitem", "contract", "vat_rate", "temp")
    readonly_fields = ("flow", "amount")
    autocomplete_fields = ("cfitem", "contract")

    @admin.display(description="Поток")
    def flow(self, obj):
        if (obj.dt or 0) > 0:
            return badge("Дт", "red")
        if (obj.cr or 0) > 0:
            return badge("Кт", "green")
        return "—"

    @admin.display(description="Сумма")
    def amount(self, obj):
        val = (obj.dt or 0) - (obj.cr or 0)
        tone = "green" if val >= 0 else "red"
        return badge(money(abs(val)), tone)


# ---------- BankStatements Admin ----------

@admin.register(BankStatements)
class BankStatementsAdmin(admin.ModelAdmin):
    change_form_template = "admin/services/migrations/change_form.html"
    change_list_template = "admin/treasury/bankstatements/change_list.html"
    inlines = [CfDataInline]

    list_display = (
        "period",

        "ba_pretty",
        "bb_pretty",
        "turnover",
        "eb_pretty",
        "uploaded_at",
        "file_link",
    )
    list_display_links = ("period",)
    search_fields = ("owner__name", "ba__account", "ba__bank__name")
    list_filter = ("owner", "ba", "uploaded_at")
    date_hierarchy = "uploaded_at"
    ordering = ("-uploaded_at",)
    list_select_related = ("owner", "ba")

    fieldsets = (
        ("📄 Файл выписки", {"fields": ("file",)}),
        ("🧾 Период и реквизиты", {"fields": ("owner", "ba", "start", "finish")}),
        ("💰 Остатки", {"fields": ("bb", "eb")}),
        ("🕒 Система", {"fields": ("uploaded_at",)}),
    )
    readonly_fields = ("uploaded_at",)

    class Media:
        css = {
            "all": (
                "css/admin_overrides.css",
                "css/admin_treasury.css",
                "fonts/glyphs.css", 
            )
        }

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return (
            qs.select_related("owner", "ba")
              .annotate(
                  dt_sum=Sum("cfdata__dt"),
                  cr_sum=Sum("cfdata__cr"),
                  rows=Count("cfdata", distinct=True),
              )
        )

    @admin.display(description="Период", ordering="start")
    def period(self, obj):
        if obj.start and obj.finish:
            rows = getattr(obj, "rows", 0) or 0
            status_txt = "загружено" if rows > 0 else "не обработано"
            return format_html(
                '<div style="display:flex;flex-direction:column;gap:2px;line-height:1.15;">'
                '<div style="font-weight:800;">{} — {}</div>'
                '<div style="opacity:.65;font-size:12px;">{} строк • {}</div>'
                "</div>",
                obj.start.strftime("%d.%m.%Y"),
                obj.finish.strftime("%d.%m.%Y"),
                rows,
                status_txt,
            )
        return badge("Не распознано", "amber")

    @admin.display(description="Счет")
    def ba_pretty(self, obj):
        if not obj.ba_id:
            return "—"

        ba = obj.ba
        bank = getattr(ba, "bank", None)

        bank_name = getattr(bank, "name", None) or (str(bank).strip() if bank else "")
        acc = getattr(ba, "account", None) or ""

        # --- глиф банка ---
        logo_html = ""
        if bank and getattr(bank, "logo", None):
            outer = (
                "display:inline-flex;align-items:center;justify-content:center;"
                "width:24px;height:24px;border-radius:6px;"
                "background:linear-gradient(135deg,#f8fafc,#f1f5f9);"
                "box-shadow:0 0 0 1px rgba(148,163,184,.35);"
                "flex-shrink:0;"
            )
            inner = "font-family:NotoManu;font-size:16px;line-height:1;"
            logo_html = format_html(
                '<span style="{}"><span style="{}">{}</span></span>',
                outer, inner, bank.logo
            )

        # --- валюта (как в BankAccountAdmin, только компактнее) ---
        code = (ba.currency or "").upper()
        flag = CURRENCY_FLAGS.get(code, "")
        sym = CURRENCY_SYMBOLS.get(code, "")
        currency_html = ""
        if code:
            currency_html = format_html(
                '<span style="display:inline-flex;align-items:center;gap:6px;'
                'opacity:.65;font-size:12px;white-space:nowrap;margin-left:10px;">'
                '<span style="font-size:14px;line-height:1;">{}</span>'
                '<span style="font-weight:700;">{}</span>'
                '<span style="opacity:.85;">{}</span>'
                '</span>',
                flag, sym, code
            )

        title = bank_name or str(ba)

        return format_html(
            '<div style="display:flex;align-items:flex-start;gap:8px;">'
            '{}'
            '<div style="display:flex;flex-direction:column;line-height:1.15;min-width:0;">'
            '<div style="font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{}</div>'
            '<div style="display:flex;align-items:baseline;gap:8px;min-width:0;">'
            '<span style="opacity:.65;font-size:12px;white-space:nowrap;">{}</span>'
            '{}'
            '</div>'
            '</div>'
            '</div>',
            logo_html,
            title,
            acc,
            currency_html,
        )


    @admin.display(description="Нач. остаток", ordering="bb")
    def bb_pretty(self, obj):
        return money(obj.bb)

    @admin.display(description="Кон. остаток", ordering="eb")
    def eb_pretty(self, obj):
        return money(obj.eb)

    @admin.display(description="Обороты")
    def turnover(self, obj):
        dt = getattr(obj, "dt_sum", None) or 0
        cr = getattr(obj, "cr_sum", None) or 0
        return format_html(
            '<div style="display:flex;flex-direction:column;gap:2px;line-height:1.15;">'
            '<div>Дт: <b>{}</b></div>'
            '<div>Кт: <b>{}</b></div>'
            "</div>",
            money(dt),
            money(cr),
        )

    @admin.display(description="Строк", ordering="rows")
    def rows_count(self, obj):
        rows = getattr(obj, "rows", None) or 0
        return badge(str(rows), "green" if rows > 0 else "amber")

    @admin.display(description="Статус")
    def status(self, obj):
        rows = getattr(obj, "rows", None) or 0
        if not obj.file:
            return badge("Нет файла", "red")
        if rows > 0:
            return badge("Загружено", "green")
        return badge("Не обработано", "amber")

    @admin.display(description="Файл")
    def file_link(self, obj):
        if not obj.file:
            return "—"
        return format_html('<a href="{}" target="_blank">файл</a>', obj.file.url)

    # кнопка "apply_migration"
    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        if request.method == "POST" and "apply_migration" in request.POST:
            obj = self.get_object(request, object_id)

            if obj and obj.file:
                result = update_cf_data(obj.file.path, obj.pk)
                messages.success(request, mark_safe(result))
            else:
                messages.error(request, "Файл не найден")

            return redirect(request.path)

        extra_context = extra_context or {}
        extra_context["show_apply_migration"] = True

        # ссылка на журнал CfData по этой выписке
        if object_id:
            changelist = reverse("admin:treasury_cfdata_changelist")
            extra_context["cfdata_changelist_url"] = f"{changelist}?bs__id__exact={object_id}"

        return super().changeform_view(request, object_id, form_url, extra_context)


# ---------- CfData Admin ----------

@admin.register(CfData)
class CfDataAdmin(admin.ModelAdmin):
    inlines = [CfSplitsInline]

    list_display = (
        "date",
        "flow_amount",
        "cp_block",
        "contract",
        "cfitem",
        "vat_badge",
        "intercompany_badge",
        "temp_short",
        "bs_link",
    )
    list_display_links = ("date", "flow_amount")

    search_fields = (
        "temp",
        "cp_bs_name",
        "tax_id",
        "payer_account",
        "reciver_account",
        "doc_numner",
        "cp_final__name",
        "contract__number",
    )
    list_filter = ("intercompany", "owner", "ba", "cfitem", "contract", "bs")
    date_hierarchy = "date"
    ordering = ("-date", "-id")

    autocomplete_fields = ("cp", "cp_final", "contract", "cfitem", "bs", "ba")
    list_select_related = ("cp_final", "contract", "cfitem", "bs", "owner", "ba")

    fieldsets = (
        ("🧾 Основное", {"fields": ("bs", "doc_type", "doc_numner", "doc_date", "date", "temp", "dt", "cr")}),
        ("🔗 Связи", {"fields": ("cp_bs_name", "cp", "cp_final", "contract", "cfitem")}),
        ("🏦 Детали", {"fields": ("owner", "ba", "tax_id", "payer_account", "reciver_account", "vat_rate", "intercompany")}),
    )

    @admin.display(description="Поток / сумма")
    def flow_amount(self, obj):
        if (obj.dt or 0) > 0:
            return format_html("{} {}", badge("Дт", "red"), badge(money(obj.dt), "red"))
        if (obj.cr or 0) > 0:
            return format_html("{} {}", badge("Кт", "green"), badge(money(obj.cr), "green"))
        return "—"

    @admin.display(description="Контрагент")
    def cp_block(self, obj):
        if obj.cp_final:
            return format_html("<b>{}</b>", obj.cp_final)
        if obj.cp:
            return format_html("{} {}", badge("по ИНН", "blue"), obj.cp)
        if obj.cp_bs_name:
            return format_html("{} {}", badge("из выписки", "amber"), obj.cp_bs_name)
        return "—"

    @admin.display(description="НДС")
    def vat_badge(self, obj):
        if obj.vat_rate is None:
            return "—"
        return badge(f"{obj.vat_rate}%", "pink")

    @admin.display(description="Группа")
    def intercompany_badge(self, obj):
        return badge("IG", "blue") if obj.intercompany else "—"

    @admin.display(description="Назначение")
    def temp_short(self, obj):
        if not obj.temp:
            return "—"
        s = obj.temp.strip().replace("\n", " ")
        return (s[:90] + "…") if len(s) > 90 else s

    @admin.display(description="Выписка")
    def bs_link(self, obj):
        if not obj.bs_id:
            return "—"
        url = reverse("admin:treasury_bankstatements_change", args=[obj.bs_id])
        # выводим аккуратно: период в одну строку
        start = obj.bs.start.strftime("%d.%m.%Y") if obj.bs.start else "—"
        finish = obj.bs.finish.strftime("%d.%m.%Y") if obj.bs.finish else "—"
        return format_html('<a href="{}">↗ {}–{}</a>', url, start, finish)
