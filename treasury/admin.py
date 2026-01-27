# treasury/admin.py

from django.http import JsonResponse
from django.urls import path
from django.db.models import F, Value, DecimalField, ExpressionWrapper
import csv
from django.http import HttpResponse
from django.contrib import admin, messages
from django.db.models import Sum, Count
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.db.models.functions import Coalesce

from datetime import datetime
from django.db.models import Q
from django.contrib.admin import SimpleListFilter
from django import forms
from contracts.models import Contracts
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
        'padding:2px 8px;border-radius:6px;'
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


class ByInnBadgeFilter(SimpleListFilter):
    title = "Определение контрагента"
    parameter_name = "by_inn"

    def lookups(self, request, model_admin):
        return (
            ("yes", "по ИНН"),
            ("no", "не по ИНН"),
        )

    def queryset(self, request, queryset):
        v = self.value()
        if v == "yes":
            # ровно как бейдж: cp есть, а cp_final нет
            return queryset.filter(cp__isnull=False, cp_final__isnull=True)

        if v == "no":
            # всё остальное: либо cp_final есть, либо cp нет
            return queryset.filter(Q(cp_final__isnull=False) | Q(cp__isnull=True))

        return queryset

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
    # inlines = [CfDataInline]


    list_display = (
        "period",

        "ba_pretty",
        "bb_pretty",
        "turnover",
        "eb_pretty",
        "uploaded_at_short",
        "quality_badge",
    )
    list_display_links = ("period",)
    search_fields = ("owner__name", "ba__account", "ba__bank__name")
    list_filter = ("owner", "ba", "uploaded_at", InPeriodDateFilter)
    # date_hierarchy = "uploaded_at"
  
    ordering = ("-uploaded_at",)
    list_select_related = ("owner", "ba")

    fieldsets = (
        ("📄 Файл выписки", {"fields": ("file",)}),
        (
        "🧾 Период и реквизиты",
        {
            "fields": (
                "owner",
                "ba",
                ("start", "finish"),  
            )
        },
            ),
        
        ("💰 Остатки", {"fields": ("bb", "eb")}), 
        ("🕒 Система", {"fields": ("uploaded_at",)}),
    )
    readonly_fields = ("uploaded_at", "owner", "ba", "start", "finish", "bb", "eb")

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
                "process-selected/",
                self.admin_site.admin_view(self.process_selected_view),
                name="treasury_bankstatements_process_selected",
            ),
            path(
                "export-eod-xlsx/",
                self.admin_site.admin_view(export_eod_xlsx),
                name="treasury_bankstatements_export_eod_xlsx",
            ),

        ]
        return custom_urls + urls
    


    
    
    def process_selected_view(self, request):
        """
        POST принимает ids выбранных выписок.
        Мы будем передавать их как:
          - statement_ids: "1,2,3"
        """
        if request.method != "POST":
            return redirect("..")

        raw = (request.POST.get("statement_ids") or "").strip()
        if not raw:
            messages.warning(request, "Выберите выписку чекбоксом.")
            return redirect(request.META.get("HTTP_REFERER", ".."))

        ids = []
        for x in raw.split(","):
            x = x.strip()
            if x.isdigit():
                ids.append(int(x))

        if not ids:
            messages.warning(request, "Не удалось прочитать выбранные id.")
            return redirect(request.META.get("HTTP_REFERER", ".."))

        qs = BankStatements.objects.filter(pk__in=ids).select_related("ba", "owner")

        ok = 0
        bad = 0
        for obj in qs:
            try:
                if not obj.file:
                    bad += 1
                    continue
                result = update_cf_data(obj.file.path, obj.pk)
                # можно либо копить результаты, либо показывать кратко
                ok += 1
            except Exception as e:
                bad += 1

        if ok:
            messages.success(request, f"Обработано выписок: {ok}")
        if bad:
            messages.error(request, f"Ошибок/пропусков: {bad} (нет файла или ошибка обработки).")

        # вернуть обратно на changelist с теми же фильтрами
        return redirect(request.META.get("HTTP_REFERER", ".."))



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
    #         bss = (
    #             BankStatements.objects
    #             .filter(start__lte=selected_date, finish__gte=selected_date)
    #             .select_related("owner", "ba", "ba__bank")
    #         )

    #         owner_id = request.GET.get("owner__id__exact")
    #         ba_id = request.GET.get("ba__id__exact")
    #         if owner_id:
    #             bss = bss.filter(owner_id=owner_id)
    #         if ba_id:
    #             bss = bss.filter(ba_id=ba_id)

    #         blocks = []
            
            
            

    #         # --- итоги по валютам ---
    #         totals_by_ccy = {}  # code -> {"dt": Decimal, "cr": Decimal, "eod": Decimal, "cnt": int}

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

    #             ba = bs.ba
    #             bank = getattr(ba, "bank", None) if ba else None

    #             bank_name = (getattr(bank, "name", None) or "").strip()
    #             account = (getattr(ba, "account", None) or "").strip()
    #             owner_name = str(bs.owner) if bs.owner else ""

    #             # валюта счета
    #             code = (getattr(ba, "currency", None) or "").upper() if ba else ""
    #             sym = CURRENCY_SYMBOLS.get(code, "") if code else ""
    #             flag = CURRENCY_FLAGS.get(code, "") if code else ""

    #             blocks.append({
    #                 "bs": bs,
    #                 "dt_sum": dt_sum,
    #                 "cr_sum": cr_sum,
    #                 "eod": eod,

    #                 "bank_name": bank_name,
    #                 "account": account,
    #                 "owner_name": owner_name,
    #                 "open_url": reverse("admin:treasury_bankstatements_change", args=[bs.pk]),

    #                 # валюта для строки
    #                 "currency_code": code,
    #                 "currency_symbol": sym,
    #                 "currency_flag": flag,
    #             })

    #             # копим итоги по валюте (если валюта пустая — складываем в '—')
    #             ccy_key = code or "—"
    #             acc = totals_by_ccy.get(ccy_key)
    #             if not acc:
    #                 acc = {"dt": Decimal("0.00"), "cr": Decimal("0.00"), "eod": Decimal("0.00"), "cnt": 0}
    #                 totals_by_ccy[ccy_key] = acc

    #             acc["dt"] += dt_sum
    #             acc["cr"] += cr_sum
    #             acc["eod"] += eod
    #             acc["cnt"] += 1

    #         extra_context["day_blocks"] = blocks

    #         # список для шаблона: сортировка (сначала нормальные валюты, потом '—')
    #         totals_list = []
    #         for code, a in totals_by_ccy.items():
    #             totals_list.append({
    #                 "currency_code": code,
    #                 "currency_symbol": CURRENCY_SYMBOLS.get(code, "") if code != "—" else "",
    #                 "currency_flag": CURRENCY_FLAGS.get(code, "") if code != "—" else "",
    #                 "dt": a["dt"],
    #                 "cr": a["cr"],
    #                 "eod": a["eod"],
    #                 "cnt": a["cnt"],
    #             })

    #         totals_list.sort(key=lambda x: (x["currency_code"] == "—", x["currency_code"]))

    #         extra_context["totals_by_ccy"] = totals_list

    #         # для обратной совместимости: если валюта одна — оставим total_* как раньше
    #         if len(totals_list) == 1:
    #             only = totals_list[0]
    #             extra_context["total_dt"] = only["dt"]
    #             extra_context["total_cr"] = only["cr"]
    #             extra_context["total_eod"] = only["eod"]
    #             extra_context["total_currency_code"] = only["currency_code"]
    #             extra_context["total_currency_symbol"] = only["currency_symbol"]
    #             extra_context["total_currency_flag"] = only["currency_flag"]
    #         else:
    #             extra_context["total_dt"] = None
    #             extra_context["total_cr"] = None
    #             extra_context["total_eod"] = None

    #     return super().changelist_view(request, extra_context=extra_context)
    
    
    
    
    
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}

        # ✅ ВСЕГДА объявляем фильтры (иначе UnboundLocalError)
        owner_id = request.GET.get("owner__id__exact")
        ba_id = request.GET.get("ba__id__exact")

        # ✅ Дата среза (может быть None)
        selected_date = None
        raw = request.GET.get("in_period_date")
        if raw:
            try:
                selected_date = datetime.strptime(raw, "%Y-%m-%d").date()
            except ValueError:
                selected_date = None

        extra_context["selected_date"] = selected_date

        # =========================================================
        # ✅ ГЛОБАЛЬНЫЙ КОНТРОЛЬ ВНУТРИГРУППОВЫХ (НЕ в разрезе выписки)
        #    Показываем всегда на экране "Выписки"
        #    (опционально учитываем текущие фильтры owner/ba и дату-срез)
        # =========================================================
        ic_qs = CfData.objects.filter(intercompany=True)

        # если на странице выбран owner / ba — логично считать в том же контексте
        if owner_id:
            ic_qs = ic_qs.filter(owner_id=owner_id)
        if ba_id:
            ic_qs = ic_qs.filter(ba_id=ba_id)

        # если выбрана дата — считаем "на дату" (до выбранной даты включительно)
        if selected_date:
            ic_qs = ic_qs.filter(date__lte=selected_date)

        ic = ic_qs.aggregate(
            dt=Coalesce(Sum("dt"), Decimal("0.00")),
            cr=Coalesce(Sum("cr"), Decimal("0.00")),
        )

        ic_dt = ic["dt"] or Decimal("0.00")
        ic_cr = ic["cr"] or Decimal("0.00")
        ic_net = ic_dt - ic_cr

        extra_context["ic_total_dt"] = ic_dt
        extra_context["ic_total_cr"] = ic_cr
        extra_context["ic_total_net"] = ic_net

        # =========================================================
        # ✅ ТВОЯ ТЕКУЩАЯ ЛОГИКА EOD (только если выбрана дата)
        # =========================================================
        if selected_date:
            bss = (
                BankStatements.objects
                .filter(start__lte=selected_date, finish__gte=selected_date)
                .select_related("owner", "ba", "ba__bank")
            )

            # ✅ используем уже прочитанные owner_id / ba_id (не читаем повторно)
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

    @admin.display(description="Качество", ordering="missing_cnt")
    def quality_badge(self, obj):
        """
        ✅ если в выписке НЕТ строк CfData, у которых отсутствует:
        - contract
        - cfitem
        - cp_final
        ⚠️ иначе предупреждение + расшифровка.
        """

        # Если выписка ещё не обработана (нет строк)
        rows = getattr(obj, "rows", None)
        if rows is not None and rows == 0:
            return badge("⏳ не обработано", "amber")

        # Считаем «плохие» строки (хотя бы одно из полей пустое)
        base = CfData.objects.filter(bs_id=obj.pk)

        missing_contract = base.filter(contract__isnull=True).count()
        missing_cfitem = base.filter(cfitem__isnull=True).count()
        missing_cp_final = base.filter(cp_final__isnull=True).count()

        missing_any = base.filter(
            Q(contract__isnull=True) | Q(cfitem__isnull=True) | Q(cp_final__isnull=True)
        ).count()

        if missing_any == 0 and base.exists():
            return format_html(
                '<div style="display:inline-flex;align-items:center;gap:8px;">'
                '{}'
                '</div>',
                badge("✅ OK", "green"),
            )

        # если вообще нет строк (на всякий)
        if not base.exists():
            return badge("— нет строк", "amber")

        # расшифровка чего не хватает
        parts = []
        if missing_cp_final:
            parts.append(f"контрагент: {missing_cp_final}")
        if missing_contract:
            parts.append(f"договор: {missing_contract}")
        if missing_cfitem:
            parts.append(f"статья CF: {missing_cfitem}")

        detail = "; ".join(parts) if parts else "есть незаполненные поля"

        return format_html(
            '<div style="display:flex;flex-direction:column;gap:2px;line-height:1.15;">'
            '<div>{}</div>'
            '<div style="opacity:.65;font-size:12px;">{}</div>'
            '</div>',
            badge("⚠️ проверить", "amber"),
            detail,
            missing_any,
        )


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

class CfDataAdminForm(forms.ModelForm):
    class Meta:
        model = CfData
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        cp = None
        # приоритет: финальный контрагент
        if self.instance and getattr(self.instance, "cp_final_id", None):
            cp = self.instance.cp_final
        elif self.instance and getattr(self.instance, "cp_id", None):
            cp = self.instance.cp

        if cp:
            self.fields["contract"].queryset = Contracts.objects.filter(cp=cp).order_by("-date")
        else:
            # если контрагент не определён — ничего не показываем
            self.fields["contract"].queryset = Contracts.objects.none()



@admin.register(CfData)
class CfDataAdmin(admin.ModelAdmin):
    inlines = [CfSplitsInline]
    form = CfDataAdminForm
    list_per_page = 25
    change_list_template = "admin/treasury/cfdata/change_list.html"

    list_display = (
        "date_short",
        "dt_amount",
        "cr_amount",
        "cp_short",
        "contract_block",
        "cfitem_block",
        "vat_badge",
        "temp_short",
        "bs_link",
    )
    list_display_links = ("date_short", "dt_amount", "cr_amount")

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
    list_filter = ( ByInnBadgeFilter, 'cp', "intercompany", "owner", "ba", "cfitem", "contract", "bs")
    date_hierarchy = "date"
    ordering = ("-date", "-id")

    autocomplete_fields = ("cp", "cp_final", "cfitem", "bs", "ba")
    list_select_related = ("cp_final", "contract", "cfitem", "bs", "owner", "ba")

    fieldsets = (
        ("🧾 Основное", {"fields": ("bs", "doc_type", "doc_numner", "doc_date", "date",  "dt", "cr")}),
        ("🔗 Связи", {"fields": ("cp_bs_name", "cp", "cp_final", "contract",  "temp", "cfitem")}),
        ("🏦 Детали", {"fields": ("owner", "ba", "tax_id", "payer_account", "reciver_account", "vat_rate", "intercompany")}),
    )

    # -------------------- Колонки списка --------------------
    def _currency_code(self, obj) -> str:
        ba = getattr(obj, "ba", None) or getattr(getattr(obj, "bs", None), "ba", None)
        return (getattr(ba, "currency", None) or "").upper()



    def get_urls(self):
            urls = super().get_urls()
            custom = [
                path(
                    "export-csv/",
                    self.admin_site.admin_view(self.export_csv_view),
                    name="treasury_cfdata_export_csv",
                )
            ]
            return custom + urls
        

    
    def export_csv_view(self, request):
        cl = self.get_changelist_instance(request)
        qs = cl.get_queryset(request).select_related(
            "cp",            # <-- добавили
            "cp_final",
            "contract",
            "cfitem",
            "owner",
            "ba",
            "ba__bank",
            "bs",
        )

        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="cf_data.csv"'
        response.write("\ufeff")  # UTF-8 BOM для Excel

        writer = csv.writer(
            response,
            delimiter="|",
            quoting=csv.QUOTE_MINIMAL,
        )

        LEVELS = 4

        header = [
            "date", "dt", "cr", "amount",
            "cp_inn_name",        # <-- НОВОЕ (перед финальным)
            "cp_final_name",
            "cp_final_match",     # <-- НОВОЕ (рулевая колонка)
            "contract_number",
            "cfitem_name",
            "cfitem_path_names",
        ]
        for i in range(1, LEVELS + 1):
            header += [f"cfitem_lvl{i}_name"]

        header += [
            "temp", "tax_id",
            "owner_name",
            "ba_currency",
            "ba_bank_account",
            "bs_start", "bs_finish",
        ]

        writer.writerow(header)

        for obj in qs:
            # --- даты операции (YYYY-MM-DD) ---
            op_date_txt = obj.date.isoformat() if obj.date else ""
            bs_start = obj.bs.start.isoformat() if obj.bs and obj.bs.start else ""
            bs_finish = obj.bs.finish.isoformat() if obj.bs and obj.bs.finish else ""

            # --- dt/cr -> amount (+/-) ---
            dt_val = obj.dt or Decimal("0")
            cr_val = obj.cr or Decimal("0")

            if dt_val > 0:
                amount = dt_val
            elif cr_val > 0:
                amount = -cr_val
            else:
                amount = Decimal("0")

            # --- договор: дата договора в формате DD.MM.YYYY ---
            contract_txt = ""
            if obj.contract:
                title = getattr(getattr(obj.contract, "title", None), "title", "") or ""
                num = (obj.contract.number or "").strip() or "б/н"

                contract_date_part = ""
                if obj.contract.date:
                    contract_date_txt = obj.contract.date.strftime("%d.%m.%Y")
                    contract_date_part = f" от {contract_date_txt}"

                if title:
                    contract_txt = f"{title} № {num}{contract_date_part}"
                else:
                    contract_txt = f"{num}{contract_date_part}"

            # --- CF item и иерархия ---
            it = obj.cfitem
            if it:
                ancestors = list(it.get_ancestors(include_self=True))  # [root, ..., self]
                path_names = " / ".join(a.name for a in ancestors)
                it_name = it.name
            else:
                ancestors = []
                path_names = ""
                it_name = ""

            # --- банк / счет / валюта ---
            ba_account = obj.ba.account if obj.ba else ""
            ba_bank_name = obj.ba.bank.name if (obj.ba and obj.ba.bank) else ""
            ba_currency = obj.ba.currency if obj.ba else ""
            ba_bank_account = f"{ba_bank_name} | {ba_account}".strip(" |")

            # --- контрагент по ИНН (из выписки) / финальный / матч ---
            cp_inn_name = obj.cp.name if getattr(obj, "cp", None) else ""
            cp_final_name = obj.cp_final.name if getattr(obj, "cp_final", None) else ""

            if obj.cp_final_id and obj.cp_id:
                cp_final_match = "MATCH" if obj.cp_final_id == obj.cp_id else "MISMATCH"
            elif obj.cp_final_id and not obj.cp_id:
                cp_final_match = "NO_INN_CP"
            elif obj.cp_id and not obj.cp_final_id:
                cp_final_match = "NO_FINAL"
            else:
                cp_final_match = "EMPTY"

            row = [
                op_date_txt,  # <-- дата операции ISO
                (str(dt_val) if dt_val else ""),
                (str(cr_val) if cr_val else ""),
                str(amount),

                cp_inn_name,       # <-- НОВОЕ
                cp_final_name,     # <-- финальный
                cp_final_match,    # <-- НОВОЕ (рулевая)

                contract_txt,
                it_name,
                path_names,
            ]

            # lvl1..lvlN: root -> ...
            for idx in range(LEVELS):
                if idx < len(ancestors):
                    row += [ancestors[idx].name]
                else:
                    row += [""]

            row += [
                (obj.temp or "").replace("\n", " ").strip(),
                obj.tax_id or "",
                (obj.owner.name if obj.owner else ""),
                ba_currency,
                ba_bank_account,
                bs_start,
                bs_finish,
            ]

            writer.writerow(row)

        return response


    
    
    
    @admin.display(description="Дата платежа", ordering="date")
    def date_short(self, obj):
        if not obj.date:
            return "—"
        d = obj.date
        return f"{d.day:02d} {RU_MONTHS_SHORT.get(d.month, d.month)} {d.year}"

    @admin.display(description="Дт (поступление)", ordering="dt")
    def dt_amount(self, obj):
        if not obj.dt:
            return "—"

        code = self._currency_code(obj)
        ccy = format_html(
            '<div style="font-size:11px;color:#94a3b8;line-height:1;margin-top:2px;">{}</div>',
            code or "—",
        )

        return format_html(
            '<div style="display:flex;flex-direction:column;line-height:1.1;">'
                '<div style="color:#16a34a;font-weight:700;">{}</div>'
                '{}'
            '</div>',
            money(obj.dt),
            ccy,
        )


    @admin.display(description="Кт (списание)", ordering="cr")
    def cr_amount(self, obj):
        if not obj.cr:
            return "—"

        code = self._currency_code(obj)
        ccy = format_html(
            '<div style="font-size:11px;color:#94a3b8;line-height:1;margin-top:2px;">{}</div>',
            code or "—",
        )

        return format_html(
            '<div style="display:flex;flex-direction:column;line-height:1.1;">'
                '<div style="color:#dc2626;font-weight:700;">{}</div>'
                '{}'
            '</div>',
            money(obj.cr),
            ccy,
        )


    @admin.display(description="Контрагент")
    def cp_short(self, obj):
        # 1) финальный контрагент
        if obj.cp_final:
            name = getattr(obj.cp_final, "name", None) or str(obj.cp_final)
            return format_html("<b>{}</b>", name)

        # 2) контрагент определён по ИНН (cp есть, но cp_final нет)
        if obj.cp:
            name = getattr(obj.cp, "name", None) or str(obj.cp)

            inn_tag = format_html(
                '<span style="display:inline-flex;align-items:center;gap:6px;'
                'padding:2px 8px;border-radius:6px;'
                'background:rgba(59,130,246,.14);'
                'border:1px solid rgba(59,130,246,.28);'
                'color:#1d4ed8;font-weight:900;font-size:11px;'
                'box-shadow:0 8px 20px rgba(59,130,246,.12);'
                'margin-top:4px;">'
                '🧾 по ИНН'
                '</span>'
            )

            return format_html(
                '<div style="line-height:1.15;">'
                '<div style="font-weight:900;">{}</div>'
                '{}'
                '</div>',
                name,
                inn_tag
            )

        # 3) только имя из выписки (не матчится на контрагента)
        if obj.cp_bs_name:
            bs_tag = format_html(
                '<span style="display:inline-flex;align-items:center;gap:6px;'
                'padding:2px 8px;border-radius:999px;'
                'background:rgba(148,163,184,.16);'
                'border:1px solid rgba(148,163,184,.30);'
                'color:#475569;font-weight:800;font-size:11px;'
                'margin-top:4px;">'
                'из выписки'
                '</span>'
            )

            return format_html(
                '<div style="line-height:1.15;">'
                '<div style="font-weight:900;">{}</div>'
                '{}'
                '</div>',
                obj.cp_bs_name,
                bs_tag
            )

        return "—"



    @admin.display(description="Статья CF", ordering="cfitem__code")
    def cfitem_block(self, obj):
        it = getattr(obj, "cfitem", None)
        if not it:
            return "—"

        code = getattr(it, "code", None) or getattr(it, "number", None) or getattr(it, "id", None) or "—"
        name = getattr(it, "name", None) or str(it)

        code_style = (
            "display:inline-block;"
            "padding:1px 6px;"
            "border-radius:4px;"
            "font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,'Liberation Mono','Courier New',monospace;"
            "font-size:12px;"
            "font-weight:700;"
            "background:rgba(15,23,42,.06);"
            "box-shadow:0 0 0 1px rgba(148,163,184,.35) inset;"
            "margin-right:8px;"
            "white-space:nowrap;"
        )
        name_style = "font-size:13px;line-height:1.15;"

        return format_html(
            '<span style="{}">{}</span><span style="{}">{}</span>',
            code_style, code, name_style, name
        )

    @admin.display(description="Договор", ordering="contract__number")
    def contract_block(self, obj):
        c = getattr(obj, "contract", None)
        if not c:
            return "—"

        # 1) тип договора
        title = getattr(getattr(c, "title", None), "title", "") or "Договор"

        # 2) номер договора
        number = c.number or "б/н"

        # 3) дата договора (русский формат)
        if c.date:
            months = {
                1: "января", 2: "февраля", 3: "марта", 4: "апреля",
                5: "мая", 6: "июня", 7: "июля", 8: "августа",
                9: "сентября", 10: "октября", 11: "ноября", 12: "декабря",
            }
            d = c.date
            date_txt = f"{d.day} {months[d.month]} {d.year}"
        else:
            date_txt = "без даты"

        # Идея: дата НЕ отдельным цветом, а тем же «вторичным» стилем, что и id
        secondary = "#6b7280"  # аккуратный нейтральный серый (не синий)

        return format_html(
            '<div style="line-height:1.25;max-width:520px;">'
                # 1 строка — тип договора
                '<div style="font-weight:800;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{}</div>'
                # 2 строка — номер
                '<div style="font-size:13px;font-weight:650;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">№ {}</div>'
                # 3 строка — дата (вторичный стиль, без «синевы»)
                '<div style="font-size:12px;color:%s;font-weight:500;">от {}</div>'
                # 4 строка — id (тот же стиль)
                '<div style="font-size:11px;color:%s;">id: {}</div>'
            '</div>' % (secondary, secondary),
            title,
            number,
            date_txt,
            c.id,
        )


    # --------------------  --------------------
    @admin.display(description="НДС")
    def vat_badge(self, obj):
        if obj.vat_rate is None:
            return "—"
        return badge(f"{obj.vat_rate}%", "pink")



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
        start = obj.bs.start.strftime("%d.%m.%Y") if obj.bs.start else "—"
        finish = obj.bs.finish.strftime("%d.%m.%Y") if obj.bs.finish else "—"
        return format_html('<a href="{}">↗ {}–{}</a>', url, start, finish)

    class Media:
        css = {"all": ("css/admin_overrides.css", "css/admin_treasury.css", "fonts/glyphs.css")}




# ---------- REGEX ----------

@admin.register(ContractsRexex)
class ContractsRexexAdmin(admin.ModelAdmin):

    list_per_page = 50
    change_list_template = "admin/treasury/contractsrexex/change_list.html"  


    # autocomplete_fields = ("cp", )
    
    class Media:
        css = {"all": ("fonts/glyphs.css", "css/admin_overrides.css")}



    list_select_related = ("cp", "contract", "contract__title")

    # колонки
    list_display = (
        "cp_logo",
        "cp_link",
        "contract_id_col",
        "contract_type_col",
        "contract_link",
        "regex_short",
    )
    list_display_links = ("cp_link", "contract_link", "regex_short")
    
    
    @admin.display(description="Тип договора", ordering="contract__title__title")
    def contract_type_col(self, obj):
        # contract__title уже подтянут select_related, будет быстро
        c = obj.contract
        if not c or not getattr(c, "title_id", None):
            return "—"
        return c.title.title  # ContractsTitle.title

    # search_fields = (
    #     "cp__tax_id",
    #     "cp__name",
    #     "contract__number",
    #     "contract__id",
    #     "regex",
    #     'contract__cp'
    # )

  
    list_filter = (
        ("cp", admin.RelatedOnlyFieldListFilter),
    )

    ordering = ("cp__name", )



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
        return format_html("<b>{}</b>", cp.name)

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

  
