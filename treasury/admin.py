
# treasury/admin.py

from django.urls import path
from django.http import HttpResponse
from django.contrib import admin, messages
from django.db.models import Sum, Count
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.db.models.functions import Coalesce

from datetime import datetime

from django.contrib.admin import SimpleListFilter

from .models import BankStatements, CfData, CfSplits,ContractsRexex
from utils.bsparsers.bsupdater import update_cf_data
from decimal import Decimal




from utils.choises import CURRENCY_FLAGS, CURRENCY_SYMBOLS
from treasury.services.eod_export import export_eod_xlsx

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
    

RU_MONTHS_SHORT = {
    1: "янв",  2: "фев",  3: "мар",  4: "апр",
    5: "май",  6: "июн",  7: "июл",  8: "авг",
    9: "сен", 10: "окт", 11: "ноя", 12: "дек",
}


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


class InPeriodDateFilter(SimpleListFilter):
    title = "Дата (внутри выписки)"
    parameter_name = "in_period_date"   # будет в URL: ?in_period_date=YYYY-MM-DD
    template = "admin/filters/date_in_period.html"

    def lookups(self, request, model_admin):
        return ()

    def queryset(self, request, queryset):
        value = self.value()
        if not value:
            return queryset
        try:
            d = datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            return queryset
        return queryset.filter(start__lte=d, finish__gte=d)

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
        "uploaded_at_short",
        "file_link",
    )
    list_display_links = ("period",)
    search_fields = ("owner__name", "ba__account", "ba__bank__name")
    list_filter = ("owner", "ba", "uploaded_at", InPeriodDateFilter)
    # date_hierarchy = "uploaded_at"
  
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
    
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "export-eod-xlsx/",
                self.admin_site.admin_view(export_eod_xlsx),
                name="treasury_bankstatements_export_eod_xlsx",
            ),
        ]
        return custom_urls + urls

    
    
    

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
        
        
    # def changelist_view(self, request, extra_context=None):
    #     extra_context = extra_context or {}

    #     selected_date = None
    #     raw = request.GET.get("in_period_date")
    #     if raw:
    #         try:
    #             selected_date = datetime.strptime(raw, "%Y-%m-%d").date()
    #         except ValueError:
    #             selected_date = None

    #     extra_context["selected_date"] = selected_date

    #     if selected_date:
    #         # берём выписки, которые покрывают дату + учитываем выбранные фильтры owner/ba
    #         bss = (
    #             BankStatements.objects
    #             .filter(start__lte=selected_date, finish__gte=selected_date)
    #             .select_related("owner", "ba")
    #         )

    #         owner_id = request.GET.get("owner__id__exact")
    #         ba_id = request.GET.get("ba__id__exact")
    #         if owner_id:
    #             bss = bss.filter(owner_id=owner_id)
    #         if ba_id:
    #             bss = bss.filter(ba_id=ba_id)

    #         blocks = []

    #         # ИТОГИ
    #         total_dt = Decimal("0.00")
    #         total_cr = Decimal("0.00")
    #         total_eod = Decimal("0.00")

    #         for bs in bss:
    #             agg = (
    #                 CfData.objects
    #                 .filter(bs=bs, date__lte=selected_date)
    #                 .aggregate(
    #                     dt=Coalesce(Sum("dt"), Decimal("0.00")),
    #                     cr=Coalesce(Sum("cr"), Decimal("0.00")),
    #                 )
    #             )

    #             dt_sum = agg["dt"] or Decimal("0.00")
    #             cr_sum = agg["cr"] or Decimal("0.00")

    #             bb = bs.bb if bs.bb is not None else Decimal("0.00")
    #             eod = bb + dt_sum - cr_sum

    #             blocks.append({
    #                 "bs": bs,
    #                 "dt_sum": dt_sum,
    #                 "cr_sum": cr_sum,
    #                 "eod": eod,
    #             })

    #             total_dt += dt_sum
    #             total_cr += cr_sum
    #             total_eod += eod

    #         extra_context["day_blocks"] = blocks

    #         # прокидываем в шаблон (чтобы блок "Итого" появился)
    #         extra_context["total_dt"] = total_dt
    #         extra_context["total_cr"] = total_cr
    #         extra_context["total_eod"] = total_eod

    #     return super().changelist_view(request, extra_context=extra_context)
    
    
    


    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}

        selected_date = None
        raw = request.GET.get("in_period_date")
        if raw:
            try:
                selected_date = datetime.strptime(raw, "%Y-%m-%d").date()
            except ValueError:
                selected_date = None

        extra_context["selected_date"] = selected_date

        if selected_date:
            bss = (
                BankStatements.objects
                .filter(start__lte=selected_date, finish__gte=selected_date)
                .select_related("owner", "ba", "ba__bank")
            )

            owner_id = request.GET.get("owner__id__exact")
            ba_id = request.GET.get("ba__id__exact")
            if owner_id:
                bss = bss.filter(owner_id=owner_id)
            if ba_id:
                bss = bss.filter(ba_id=ba_id)

            blocks = []

            # --- итоги по валютам ---
            totals_by_ccy = {}  # code -> {"dt": Decimal, "cr": Decimal, "eod": Decimal, "cnt": int}

            for bs in bss:
                agg = (
                    CfData.objects
                    .filter(bs=bs, date__lte=selected_date)
                    .aggregate(
                        dt=Coalesce(Sum("dt"), Decimal("0.00")),
                        cr=Coalesce(Sum("cr"), Decimal("0.00")),
                    )
                )

                dt_sum = agg["dt"] or Decimal("0.00")
                cr_sum = agg["cr"] or Decimal("0.00")

                bb = bs.bb if bs.bb is not None else Decimal("0.00")
                eod = bb + dt_sum - cr_sum

                ba = bs.ba
                bank = getattr(ba, "bank", None) if ba else None

                bank_name = (getattr(bank, "name", None) or "").strip()
                account = (getattr(ba, "account", None) or "").strip()
                owner_name = str(bs.owner) if bs.owner else ""

                # валюта счета
                code = (getattr(ba, "currency", None) or "").upper() if ba else ""
                sym = CURRENCY_SYMBOLS.get(code, "") if code else ""
                flag = CURRENCY_FLAGS.get(code, "") if code else ""

                blocks.append({
                    "bs": bs,
                    "dt_sum": dt_sum,
                    "cr_sum": cr_sum,
                    "eod": eod,

                    "bank_name": bank_name,
                    "account": account,
                    "owner_name": owner_name,
                    "open_url": reverse("admin:treasury_bankstatements_change", args=[bs.pk]),

                    # валюта для строки
                    "currency_code": code,
                    "currency_symbol": sym,
                    "currency_flag": flag,
                })

                # копим итоги по валюте (если валюта пустая — складываем в '—')
                ccy_key = code or "—"
                acc = totals_by_ccy.get(ccy_key)
                if not acc:
                    acc = {"dt": Decimal("0.00"), "cr": Decimal("0.00"), "eod": Decimal("0.00"), "cnt": 0}
                    totals_by_ccy[ccy_key] = acc

                acc["dt"] += dt_sum
                acc["cr"] += cr_sum
                acc["eod"] += eod
                acc["cnt"] += 1

            extra_context["day_blocks"] = blocks

            # список для шаблона: сортировка (сначала нормальные валюты, потом '—')
            totals_list = []
            for code, a in totals_by_ccy.items():
                totals_list.append({
                    "currency_code": code,
                    "currency_symbol": CURRENCY_SYMBOLS.get(code, "") if code != "—" else "",
                    "currency_flag": CURRENCY_FLAGS.get(code, "") if code != "—" else "",
                    "dt": a["dt"],
                    "cr": a["cr"],
                    "eod": a["eod"],
                    "cnt": a["cnt"],
                })

            totals_list.sort(key=lambda x: (x["currency_code"] == "—", x["currency_code"]))

            extra_context["totals_by_ccy"] = totals_list

            # для обратной совместимости: если валюта одна — оставим total_* как раньше
            if len(totals_list) == 1:
                only = totals_list[0]
                extra_context["total_dt"] = only["dt"]
                extra_context["total_cr"] = only["cr"]
                extra_context["total_eod"] = only["eod"]
                extra_context["total_currency_code"] = only["currency_code"]
                extra_context["total_currency_symbol"] = only["currency_symbol"]
                extra_context["total_currency_flag"] = only["currency_flag"]
            else:
                extra_context["total_dt"] = None
                extra_context["total_cr"] = None
                extra_context["total_eod"] = None

        return super().changelist_view(request, extra_context=extra_context)


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
    
    
    @admin.display(description="Дата загрузки", ordering="uploaded_at")
    def uploaded_at_short(self, obj):
        if not obj.uploaded_at:
            return "—"

        dt = obj.uploaded_at  
        month = RU_MONTHS_SHORT.get(dt.month, str(dt.month))
        return f"{dt.day:02d} {month} {dt.year} г. {dt:%H:%M}"

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



@admin.register(ContractsRexex)
class ContractsRexexAdmin(admin.ModelAdmin):
    list_per_page = 50
    change_list_template = "admin/treasury/contractsrexex/change_list.html"  


    autocomplete_fields = ("cp", "contract")

    list_select_related = ("cp", "contract")

    # колонки
    list_display = (
        "cp_logo",
        "cp_link",
        "contract_id_col",
        "contract_link",
        "regex_short",
    )
    list_display_links = ("cp_link", "contract_link", "regex_short")

    search_fields = (
        "cp__tax_id",
        "cp__name",
        "contract__number",
        "contract__id",
        "regex",
    )

  
    list_filter = (
        ("cp", admin.RelatedOnlyFieldListFilter),
    )

    ordering = ("cp__name", "contract__id")

    class Media:
        css = {"all": ("fonts/glyphs.css", "css/admin_overrides.css")}

    # ---------- колонки ----------

    @admin.display(description="Лого", ordering="cp__name")
    def cp_logo(self, obj):
        cp = obj.cp
        if not cp or not getattr(cp, "logo", None):
            return "—"

        outer = (
            "display:inline-flex;align-items:center;justify-content:center;"
            "width:28px;height:28px;border-radius:6px;"
            "background:linear-gradient(135deg,#f8fafc,#f1f5f9);"
            "box-shadow:0 0 0 1px rgba(148,163,184,.35);"
        )
        inner = "font-family:NotoManu;font-size:20px;line-height:1;"
        return format_html('<span style="{}"><span style="{}">{}</span></span>', outer, inner, cp.logo)

    @admin.display(description="Контрагент", ordering="cp__name")
    def cp_link(self, obj):
        cp = obj.cp
        if not cp:
            return "—"
        url = reverse("admin:counterparties_counterparty_change", args=[cp.pk])
        #  имя, без ИНН 
        return format_html('<a href="{}"><b>{}</b></a>', url, cp.name)

    @admin.display(description="ID договора", ordering="contract__id")
    def contract_id_col(self, obj):
        return obj.contract_id or "—"

    @admin.display(description="№ договора", ordering="contract__number")
    def contract_link(self, obj):
        c = obj.contract
        if not c:
            return "—"
        url = reverse("admin:contracts_contracts_change", args=[c.pk])
        label = getattr(c, "number", None) or f"{c.pk}"
        return format_html('<a href="{}">{}</a>', url, label)

    @admin.display(description="RegEx")
    def regex_short(self, obj):
        s = (obj.regex or "").strip()
        return (s[:80] + "…") if len(s) > 80 else (s or "—")

  
