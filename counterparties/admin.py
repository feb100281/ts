# counterparties/admin.py

from django import forms
from django.contrib import admin
from django.db import transaction
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html

from django.core.mail import EmailMultiAlternatives
from django.http import HttpResponseRedirect
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from decimal import Decimal
import base64

from .models import Tenant, Counterparty, Gr, CounterpartyFinancialYear
from counterparties.checko_client import (
    build_counterparty_payload,
    PhysicalPersonNotFound,
    finances_by_inn,
    CheckoError,
)
from .services import (
    build_counterparty_stats,
    build_group_counterparty_stats,
    build_tenant_stats,
    apply_tenant_filter,
    update_counterparty_financials
)
from .filters import (
    CounterpartyCheckoUpdatedFilter,
    CounterpartyRiskLevelFilter,
    CounterpartyLegalFormFilter,
    CounterpartyOkvedPrefixFilter,
    TenantUserPrettyFilter,
    TenantGroupFilter,
)

from .checko_client import CheckoError
from .services import _val_fin, _val_fin_total
from django.forms.models import BaseInlineFormSet
from django.core.exceptions import ValidationError

# ---------------------- FORM ----------------------


class CounterpartyForm(forms.ModelForm):
    # оставляем только историю "было"
    was_notes = forms.CharField(
        widget=forms.HiddenInput(),
        required=False,
    )

    class Meta:
        model = Counterparty
        fields = "__all__"


# ---------------------- АНАЛИЗ АРЕНДАТОРОВ ----------------------

class CounterpartyFinancialYearFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()

        years = set()

        for form in self.forms:
            if not hasattr(form, "cleaned_data"):
                continue

            if form.cleaned_data.get("DELETE"):
                continue

            year = form.cleaned_data.get("year")
            if not year:
                continue

            if year in years:
                raise ValidationError(
                    "Финансовые показатели за один и тот же год "
                    "нельзя указывать более одного раза."
                )
            years.add(year)


class CounterpartyFinancialYearInline(admin.TabularInline):
    model = CounterpartyFinancialYear
    extra = 3
    formset = CounterpartyFinancialYearFormSet



# ---------------------- КОНТРАГЕНТЫ ----------------------


class CounterpartyAdmin(admin.ModelAdmin):
    form = CounterpartyForm
    actions = ["print_counterparty_registry"]
    inlines = [CounterpartyFinancialYearInline]

    # ---------- список / поиск / фильтры ----------

    list_display = (
        "name",
        "tax_id",
        "logo_preview",
        "ceo_display",
        "website_link",
        "checko_status_column",
        "print_counterparty_link",
    )

    search_fields = (
        "name",
        "tax_id",
        "ceo",
        "website",
        "country",
        "adress",
        "region",
    )

    list_filter = (
        ("gr", admin.RelatedOnlyFieldListFilter),
        "name",
        CounterpartyRiskLevelFilter,
        CounterpartyCheckoUpdatedFilter,
        CounterpartyLegalFormFilter,
        # CounterpartyOkvedPrefixFilter,  # можно включить при необходимости
        ("logo_svg", admin.EmptyFieldListFilter),
    )

    list_display_links = ("name",)
    search_help_text = "Поиск по названию и ИНН"

    fieldsets = (
        (
            "🧾 Основное",
            {
                "fields": (
                    "tax_id",
                    "gr",
                    "name",
                    "fullname",
                    "ogrn",
                    "kpp",
                    "taxregime",
                )
            },
        ),
        ("📍 Адрес", {"fields": ("country", "adress", "region")}),
        (
            "👤 Контакты",
            {
                "fields": (
                    "ceo",
                    "ceo_post",
                    "ceo_record_date",
                    "ceo_hidden_by_fns",
                    "manager_is_org",
                    "website",
                    "email",
                )
            },
        ),
        ("🖼️ Логотипы", {"fields": ("logo", "logo_svg")}),
        ("История полей", {"fields": ("was_notes",)}),
        (
            "📊 ОКВЭД / ОКОПФ",
            {
                "fields": (
                    "okved_code",
                    "okved_name",
                    "okved_version",
                    "okopf_code",
                    "okopf_name",
                )
            },
        ),
        (
            "⚠️ Факторы риска",
            {
                "classes": ("collapse",),
                "fields": (
                    "risk_disq_persons",
                    "risk_mass_directors",
                    "risk_mass_founders",
                    "risk_illegal_fin",
                    "risk_illegal_fin_status",
                    "risk_sanctions",
                    "risk_sanctions_countries",
                    "risk_sanctioned_founder",
                    "risk_json",
                ),
            },
        ),
    )

    readonly_fields = ("risk_json",)

    # ---------- badges / helpers ----------

    def website_link(self, obj):
        if not obj.website:
            return "—"

        url = obj.website.strip()
        if not url.startswith("http"):
            url = "https://" + url

        return format_html(
            '<a href="{}" target="_blank" rel="noopener noreferrer">🌐 {}</a>',
            url,
            obj.website,
        )

    website_link.short_description = "🌐 Сайт"

    def ceo_display(self, obj):
        if obj.ceo:
            return obj.ceo

        if getattr(obj, "ceo_hidden_by_fns", False):
            return format_html(
                '<span style="color:#b00020;">ФИО скрыто ФНС</span>'
            )

        return "—"

    ceo_display.short_description = "👤 Руководитель"

    def logo_preview(self, obj):
        if obj.logo:
            return format_html(
                '<span style="font-family: NotoManu; font-size:24px;">{}</span>',
                obj.logo,
            )
        return "—"

    logo_preview.short_description = "Лого"

    def ceo_restriction_note(self, obj):
        if getattr(obj, "ceo_hidden_by_fns", False):
            return format_html(
                '<div style="margin-top:4px;color:#b00020;">'
                "<em>ФИО руководителя скрыто ФНС (ограничение доступа)</em>"
                "</div>"
            )
        return ""

    ceo_restriction_note.short_description = "Примечание"

    def checko_status_column(self, obj):
        """
        Индикатор свежести данных ФНС / Checko:
        цветная иконка + тултип с датой обновления.
        """
        if not obj.checko_updated_at:
            icon = "⚪"
            color = "#9ca3af"
            label = "Нет отметки об обновлении"
            title = "Данные ФНС не обновлялись"
        else:
            delta = timezone.now() - obj.checko_updated_at
            days = delta.days

            if days <= 90:
                icon = "🟢"
                color = "#16a34a"
                label = "Данные свежие"
            elif days <= 365:
                icon = "🟡"
                color = "#f59e0b"
                label = "Обновлено более 3 месяцев назад"
            else:
                icon = "🔴"
                color = "#b91c1c"
                label = "Давно не обновлялось"

            title = (
                f"{label}\n"
                f"Дата обновления: {obj.checko_updated_at:%d.%m.%Y}\n"
                f"Прошло дней: {days}"
            )

        return format_html(
            '<span style="color:{color}; white-space:pre;" title="{title}">{icon}</span>',
            color=color,
            title=title,
            icon=icon,
        )

    checko_status_column.short_description = "ФНС"
    checko_status_column.admin_order_field = "checko_updated_at"

    # ---------- кнопка печати карточки контрагента ----------

    def print_counterparty_link(self, obj):
        url = reverse(
            f"admin:{Counterparty._meta.app_label}_{Counterparty._meta.model_name}_print",
            args=[obj.pk],
        )
        return format_html(
            '<a href="{}?src=list" title="Печатная карточка контрагента" '
            'style="text-decoration:none;font-size:14px;">🖨</a>',
            url,
        )

    print_counterparty_link.short_description = "Печать"

    # ---------- action: печатный реестр выбранных контрагентов ----------

    def print_counterparty_registry(self, request, queryset):
        counterparties = queryset.order_by("name")
        context = {
            "counterparties": counterparties,
            "total": counterparties.count(),
        }
        return render(
            request,
            "admin/counterparty_registry_print.html",
            context,
        )

    print_counterparty_registry.short_description = (
        "Печатный реестр выбранных контрагентов"
    )

    # ---------- urls ----------

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path(
                "fill-by-inn/",
                self.admin_site.admin_view(self.fetch_data),
                name="counterparties_counterparty_fill_by_inn",
            ),
            path(
                "<int:pk>/print/",
                self.admin_site.admin_view(self.print_counterparty),
                name=(
                    f"{Counterparty._meta.app_label}_"
                    f"{Counterparty._meta.model_name}_print"
                ),
            ),
            path(
                "stats/",
                self.admin_site.admin_view(self.stats_view),
                name="counterparties_counterparty_stats",
            ),
        ]
        return my_urls + urls

    
    # ---------- печатная карточка контрагента ----------

    def print_counterparty(self, request, pk):
        cp = get_object_or_404(Counterparty, pk=pk)

        website = (cp.website or "").strip()
        if website and not website.startswith("http"):
            website_full = "https://" + website
        else:
            website_full = website

        # Финансовые показатели по годам (последние годы сверху)
        qs = (
            CounterpartyFinancialYear.objects
            .filter(counterparty=cp)
            .order_by("-year")
        )

        financial_years = []
        max_abs = Decimal("0")

        for fy in qs:
            # Приводим всё к Decimal и считаем показатели
            revenue = fy.revenue if fy.revenue is not None else Decimal("0")
            net_profit = fy.net_profit if fy.net_profit is not None else Decimal("0")
            equity = fy.equity if fy.equity is not None else Decimal("0")

            liabilities_long = getattr(fy, "liabilities_long", None) or Decimal("0")
            liabilities_short = getattr(fy, "liabilities_short", None) or Decimal("0")
            cf_operating = getattr(fy, "cf_operating", None) or Decimal("0")

            # Рентабельность продаж = ЧП / Выручка * 100
            if revenue != 0:
                fy.margin = (net_profit / revenue) * Decimal("100")
            else:
                fy.margin = None

            # Коэффициент долг / капитал
            total_debt = liabilities_long + liabilities_short
            if equity != 0 and total_debt != 0:
                fy.debt_to_equity = total_debt / equity
            else:
                fy.debt_to_equity = None

            # Чтобы проще обращаться в шаблоне
            fy.liabilities_long = liabilities_long if liabilities_long != 0 else None
            fy.liabilities_short = liabilities_short if liabilities_short != 0 else None
            fy.cf_operating = cf_operating if cf_operating != 0 else None

            # Для выбора масштаба (тыс/млн/млрд)
            for v in (
                revenue,
                net_profit,
                equity,
                liabilities_long,
                liabilities_short,
                cf_operating,
            ):
                if v is not None and abs(v) > max_abs:
                    max_abs = abs(v)

            financial_years.append(fy)

        # ---------- Масштаб: тыс / млн / млрд ----------

        unit_divisor = Decimal("1")
        unit_label = ""  # "", "тыс", "млн", "млрд"

        if max_abs >= Decimal("1000000000"):
            unit_divisor = Decimal("1000000000")
            unit_label = "млрд"
        elif max_abs >= Decimal("1000000"):
            unit_divisor = Decimal("1000000")
            unit_label = "млн"
        elif max_abs >= Decimal("1000"):
            unit_divisor = Decimal("1000")
            unit_label = "тыс"

        def _scale(val):
            if val is None:
                return None
            try:
                return val / unit_divisor
            except Exception:
                return None

        # Скейлим деньги в каждом годе
        for fy in financial_years:
            fy.revenue_scaled = _scale(fy.revenue)
            fy.net_profit_scaled = _scale(fy.net_profit)
            fy.equity_scaled = _scale(fy.equity)
            fy.liabilities_long_scaled = _scale(getattr(fy, "liabilities_long", None))
            fy.liabilities_short_scaled = _scale(getattr(fy, "liabilities_short", None))
            fy.cf_operating_scaled = _scale(getattr(fy, "cf_operating", None))

        # ---------- Мини-бары по выручке (относительные %) ----------

        max_rev = max(
            [fy.revenue or Decimal("0") for fy in financial_years],
            default=Decimal("0"),
        )

        if max_rev > 0:
            for fy in financial_years:
                if fy.revenue:
                    fy.rev_rel = int((fy.revenue / max_rev) * 100)
                else:
                    fy.rev_rel = 0
        else:
            for fy in financial_years:
                fy.rev_rel = 0

        # ---------- fin_summary по последнему году ----------

        fin_summary = None
        if financial_years:
            last_fy = financial_years[0]
            prev_fy = financial_years[1] if len(financial_years) > 1 else None

            change_abs = None
            change_pct = None
            if (
                prev_fy
                and last_fy.revenue is not None
                and prev_fy.revenue not in (None, 0)
            ):
                change_abs = (last_fy.revenue - prev_fy.revenue) / unit_divisor
                change_pct = (
                    (last_fy.revenue - prev_fy.revenue)
                    / prev_fy.revenue
                    * Decimal("100")
                )

            fin_summary = {
                "year": last_fy.year,
                "revenue": last_fy.revenue_scaled,
                "change_abs": change_abs,
                "change_pct": change_pct,
                "margin": last_fy.margin,
                "debt_to_equity": last_fy.debt_to_equity,
            }

        # ---------- Долговая нагрузка: уровень + мини-спарклайн ----------

        # 1) уровни долговой нагрузки для последнего года
        if fin_summary and fin_summary["debt_to_equity"] is not None:
            de = fin_summary["debt_to_equity"]

            if de < Decimal("0.5"):
                debt_level = "low"
                debt_level_label = "Комфортная долговая нагрузка"
            elif de < Decimal("1.5"):
                debt_level = "moderate"
                debt_level_label = "Умеренная долговая нагрузка"
            elif de < Decimal("3"):
                debt_level = "high"
                debt_level_label = "Повышенная долговая нагрузка"
            else:
                debt_level = "critical"
                debt_level_label = "Критическая долговая нагрузка"

            fin_summary["debt_level"] = debt_level
            fin_summary["debt_level_label"] = debt_level_label

        # 2) спарклайн по Debt / Equity за несколько лет (относительные значения)
        max_de_ratio = Decimal("0")
        for fy in financial_years:
            if fy.debt_to_equity is not None and fy.debt_to_equity > max_de_ratio:
                max_de_ratio = fy.debt_to_equity

        if max_de_ratio > 0:
            for fy in financial_years:
                if fy.debt_to_equity is not None:
                    fy.de_rel = int((fy.debt_to_equity / max_de_ratio) * 100)
                else:
                    fy.de_rel = 0
        else:
            for fy in financial_years:
                fy.de_rel = 0


        context = {
            "cp": cp,
            "website": website,
            "website_full": website_full,
            "financial_years": financial_years,
            "fin_summary": fin_summary,
            "unit_label": unit_label,   # "тыс" / "млн" / "млрд" / ""

        }
        return render(request, "admin/counterparty_print.html", context)

    # ---------- Дэшборд по контрагентам ----------

    def stats_view(self, request):
        qs = Counterparty.objects.all()
        context = build_counterparty_stats(qs)
        context["title"] = "Аналитика по контрагентам"
        return render(request, "admin/counterparty_stats.html", context)



    
    # ---------- fill-by-inn: только данные для формы ----------
    def fetch_data(self, request):
        inn = (request.GET.get("inn") or "").strip()
        if not inn:
            return JsonResponse({"error": "ИНН не передан"}, status=400)

        def physical_response(
            message="По данным ФНС организация или ИП не найдены",
        ):
            # ✅ Считаем, что проверка по ИНН выполнена, даже если это физлицо
            Counterparty.objects.filter(tax_id=inn).update(
                checko_updated_at=timezone.now()
            )
            return JsonResponse(
                {
                    "not_found": True,
                    "is_physical": True,
                    "error": message,
                },
                status=200,
            )

        try:
            # 1) обычные данные контрагента
            payload = build_counterparty_payload(inn)
        except PhysicalPersonNotFound as e:
            # ⬅ сюда попадаем, когда ФНС сказала "физлицо"
            return physical_response(str(e))
        except Exception as e:
            return JsonResponse({"error": f"Ошибка: {e}"}, status=500)

        # 2) Пытаемся подтянуть финпоказатели
        financial_years = []
        try:
            fin_payload = finances_by_inn(inn, extended=True, key="SIwfo6CFilGM4fUX")
            raw_data = fin_payload.get("data") or {}

            if isinstance(raw_data, dict):
                year_keys = sorted(
                    [str(y) for y in raw_data.keys() if str(y).isdigit()],
                    key=lambda y: int(y),
                    reverse=True,
                )

                for year_str in year_keys[:3]:  # последние 3 года
                    fy = raw_data.get(year_str) or {}
                    if not isinstance(fy, dict):
                        continue

                    year = int(year_str)

                    financial_years.append({
                        "year": year,
                        "revenue":       _val_fin(fy, "2110"),
                        "net_profit":    _val_fin(fy, "2400"),
                        "equity":        _val_fin(fy, "1300"),
                        "share_capital": _val_fin(fy, "1310"),
                        "liabilities_long":  _val_fin_total(fy, "1400", ("1410","1420","1430","1440","1450")),
                        "liabilities_short": _val_fin_total(fy, "1500", ("1510","1520","1530","1540","1550")),
                        "payables":      _val_fin(fy, "1520"),
                        "cf_operating":  _val_fin(fy, "4100"),
                    })
        except CheckoError:
            # молча игнорируем — финпоказатели просто не подставятся
            pass
        except Exception:
            pass

        # 3) кладём список годов в ответ
        payload["financial_years"] = financial_years

        # 4) 🔹 Помечаем всех существующих контрагентов с этим ИНН как обновлённых (юрлица)
        Counterparty.objects.filter(tax_id=inn).update(
            checko_updated_at=timezone.now()
        )

        return JsonResponse(payload)



    # ---------- static ----------

    class Media:
        css = {"all": ("fonts/glyphs.css", "css/admin_overrides.css")}
        js = ("js/counterparty_search.js", "js/counterparty_fill_by_inn.js")

    # ---------- save_model ----------

    @transaction.atomic
    def save_model(self, request, obj, form, change):
        if obj.logo and obj.logo.startswith("\\u"):
            try:
                obj.logo = obj.logo.encode().decode("unicode_escape")
            except Exception:
                pass

        super().save_model(request, obj, form, change)







# ---------------------- ЛИЧНЫЙ КАБИНЕТ ----------------------


class TenantAdmin(admin.ModelAdmin):
    list_display = (
        "counterparty_column",
        "tax_id_column",
        "user_column",
        "email_column", 
        "logo_svg_column",
        "last_login_column",
        "print_access_link",
    )
    list_select_related = ("counterparty", "user")
    ordering = ("counterparty__name",)

    search_fields = (
        "counterparty__name",
        "counterparty__tax_id",
        "user__username",
        "user__first_name",
        "user__last_name",
        "user__email",
    )

    list_filter = (
        ("counterparty", admin.RelatedOnlyFieldListFilter),
        TenantUserPrettyFilter,
        TenantGroupFilter,
    )

    autocomplete_fields = ("counterparty", "user")

    class Media:
        css = {"all": ("fonts/glyphs.css",)}

    # ---------- кастомные URL: печать + аналитика ----------

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path(
                "stats/",
                self.admin_site.admin_view(self.stats_view),
                name=f"{Tenant._meta.app_label}_{Tenant._meta.model_name}_stats",
            ),
            path(
                "<int:pk>/print-access/",
                self.admin_site.admin_view(self.print_access),
                name=(
                    f"{Tenant._meta.app_label}_"
                    f"{Tenant._meta.model_name}_print_access"
                ),
            ),
        ]
        return my_urls + urls

    # ------- колонка с кнопкой печати -------

    def print_access_link(self, obj: Tenant):
        if not obj.user:
            return ""
        url = reverse(
            f"admin:{Tenant._meta.app_label}_{Tenant._meta.model_name}_print_access",
            args=[obj.pk],
        )
        return format_html(
            '<a href="{}" title="Печатная карточка доступа" '
            'style="text-decoration:none;font-size:14px;">🖨</a>',
            url,
        )

    print_access_link.short_description = "Печать"

    # ------- колонки --------

    def counterparty_column(self, obj: Tenant):
        cp = obj.counterparty
        if cp.logo:
            return format_html(
                '<span style="font-family:NotoManu;font-size:20px;'
                'margin-right:4px;">{}</span>{}',
                cp.logo,
                cp.name,
            )
        return cp.name

    counterparty_column.short_description = "Контрагент"
    counterparty_column.admin_order_field = "counterparty__name"

    def tax_id_column(self, obj: Tenant):
        return obj.counterparty.tax_id

    tax_id_column.short_description = "ИНН"
    tax_id_column.admin_order_field = "counterparty__tax_id"

    def user_column(self, obj: Tenant):
        if not obj.user:
            return format_html('<span style="color:#b00020;">не назначен</span>')

        user = obj.user
        url = reverse("admin:auth_user_change", args=[user.pk])

        label = user.get_full_name() or user.username
        username = user.username
        email = user.email or "email не указан"

        return format_html(
            '<a href="{url}" title="Логин: {username} | Email: {email}">'
            "👤 {label} "
            '<span style="color:#9e9e9e;font-size:11px;">({username})</span>'
            "</a>",
            url=url,
            label=label,
            username=username,
            email=email,
        )

    user_column.short_description = "Ответственное лицо"
    user_column.admin_order_field = "user__username"
    
    def email_column(self, obj: Tenant):
        user = obj.user
        if not user or not user.email:
            return format_html('<span style="color:#b0bec5;">—</span>')

        url = reverse("admin:auth_user_change", args=[user.pk])
        return format_html(
            '<a href="{}" style="text-decoration:none;">{}</a>',
            url,
            user.email
        )

    email_column.short_description = "Email"
    email_column.admin_order_field = "user__email"


    def country_column(self, obj: Tenant):
        code = obj.counterparty.country or ""
        if code == "RU":
            flag = "🇷🇺"
        elif code == "KZ":
            flag = "🇰🇿"
        elif code == "BY":
            flag = "🇧🇾"
        else:
            flag = "🌍"
        return flag

    country_column.short_description = "Страна"

    def group_column(self, obj: Tenant):
        gr = obj.counterparty.gr
        if not gr:
            return format_html('<span style="color:#b0bec5;">—</span>')

        return format_html(
            '<span style="padding:2px 8px;'
            "border:1px solid #263238;"
            "font-size:11px;"
            "color:#263238;"
            'border-radius:0;">{}</span>',
            gr.name,
        )

    group_column.short_description = "Группа контрагентов"
    group_column.admin_order_field = "counterparty__gr__name"

    def logo_svg_column(self, obj: Tenant):
        if obj.counterparty.logo_svg:
            return format_html('<span style="color:#4caf50;">✔ SVG</span>')
        return format_html('<span style="color:#b0bec5;">—</span>')

    logo_svg_column.short_description = "SVG логотип"
    logo_svg_column.admin_order_field = "counterparty__logo_svg"

    def last_login_column(self, obj: Tenant):
        user = obj.user
        if not user or not user.last_login:
            return format_html('<span style="color:#b0bec5;">—</span>')

        dt = user.last_login
        pretty = dt.strftime("%d.%m.%Y %H:%M")

        delta = timezone.now() - dt
        if delta.days < 1:
            color = "#4caf50"  # сегодня/вчера
        elif delta.days < 7:
            color = "#2196f3"  # последняя неделя
        else:
            color = "#b0bec5"  # давно

        return format_html('<span style="color:{};">{}</span>', color, pretty)

    last_login_column.short_description = "Последний вход"
    last_login_column.admin_order_field = "user__last_login"

    # ------- печатная карточка доступа -------

    # def print_access(self, request, pk):
    #     tenant = get_object_or_404(Tenant, pk=pk)
    #     user = tenant.user
    #     cp = tenant.counterparty

    #     try:
    #         login_url = request.build_absolute_uri(reverse("login"))
    #     except Exception:
    #         login_url = request.build_absolute_uri("/login/")

    #     group_name = cp.gr.name if getattr(cp, "gr", None) else "Не указана"

    #     context = {
    #         "tenant": tenant,
    #         "user": user,
    #         "cp": cp,
    #         "login_url": login_url,
    #         "group_name": group_name,
    #     }
    #     return render(request, "admin/tenant_access_print.html", context)
    
    
    def print_access(self, request, pk):
        tenant = get_object_or_404(Tenant, pk=pk)
        user = tenant.user
        cp = tenant.counterparty

        try:
            login_url = request.build_absolute_uri(reverse("login"))
        except Exception:
            login_url = request.build_absolute_uri("/login/")

        group_name = cp.gr.name if getattr(cp, "gr", None) else "Не указана"

        context = {
            "tenant": tenant,
            "user": user,
            "cp": cp,
            "login_url": login_url,
            "group_name": group_name,
        }

        # --- режим "отправить на e-mail" ---
        if request.GET.get("email") == "1":
            if not user or not user.email:
                self.message_user(
                    request,
                    "У ответственного лица не указан e-mail.",
                    level="error",
                )
                return HttpResponseRedirect(
                    reverse(
                        f"admin:{Tenant._meta.app_label}_{Tenant._meta.model_name}_change",
                        args=[tenant.pk],
                    )
                )

            html_body = render_to_string("admin/tenant_access_email.html", context)
            text_body = strip_tags(html_body)

            msg = EmailMultiAlternatives(
                subject="Доступ в личный кабинет арендатора",
                body=text_body,
                to=[user.email],
            )
            msg.attach_alternative(html_body, "text/html")
            msg.send()

            self.message_user(
                request,
                f"Инструкция по доступу отправлена на {user.email}.",
            )
            return HttpResponseRedirect(
                reverse(
                    f"admin:{Tenant._meta.app_label}_{Tenant._meta.model_name}_change",
                    args=[tenant.pk],
                )
            )

        # --- обычный режим: показать печатную карточку ---
        return render(request, "admin/tenant_access_print.html", context)

    # ------- queryset с фильтрами по URL-параметрам -------

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.select_related("counterparty", "user")

        # фильтр по группе из дэшборда
        group_id = request.GET.get("group_id")
        if group_id:
            qs = qs.filter(counterparty__gr_id=group_id)

        # фильтр по активности / наличию пользователя
        tenant_filter = request.GET.get("tenant_filter")
        qs = apply_tenant_filter(qs, tenant_filter)

        return qs

    # ------- Дэшборд по кабинетам арендаторов -------

    def stats_view(self, request):
        qs = (
            Tenant.objects
            .select_related("user", "counterparty", "counterparty__gr")
        )

        # --- логика back_url / back_label ---
        tenant_pk = request.GET.get("pk")

        if tenant_pk:
            try:
                back_url = reverse(
                    f"admin:{Tenant._meta.app_label}_{Tenant._meta.model_name}_change",
                    args=[tenant_pk],
                )
                back_label = "← К карточке кабинета"
            except Exception:
                back_url = reverse(
                    f"admin:{Tenant._meta.app_label}_{Tenant._meta.model_name}_changelist"
                )
                back_label = "← К списку кабинетов"
        else:
            back_url = reverse(
                f"admin:{Tenant._meta.app_label}_{Tenant._meta.model_name}_changelist"
            )
            back_label = "← К списку кабинетов"

        # --- расчёты в сервисе ---
        stats = build_tenant_stats(qs)

        context = {
            "title": "Аналитика по кабинетам арендаторов",
            "back_url": back_url,
            "back_label": back_label,
            **stats,
        }
        return render(request, "admin/tenant_stats.html", context)


# ---------------------- ГРУППА АРЕНДАТОРОВ ----------------------


class GrAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "counterparty_count_link",
        "analytics_link",
        "print_counterparties_link",
    )
    search_fields = ("name", "description")
    ordering = ("name",)
    actions = []

    # ---------- queryset с числом контрагентов ----------
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(num_counterparties=Count("counterparty"))

    # ---------- кастомные урлы (печать + аналитика) ----------
    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path(
                "<int:pk>/print-counterparties/",
                self.admin_site.admin_view(self.print_counterparties),
                name=(
                    f"{Gr._meta.app_label}_"
                    f"{Gr._meta.model_name}_print_counterparties"
                ),
            ),
            path(
                "<int:pk>/analytics/",
                self.admin_site.admin_view(self.group_analytics),
                name=f"{Gr._meta.app_label}_{Gr._meta.model_name}_analytics",
            ),
        ]
        return my_urls + urls

    # ---------- колонка "Контрагентов" со ссылкой ----------
    def counterparty_count_link(self, obj: Gr):
        if not obj.num_counterparties:
            return "0"
        url = (
            reverse(
                f"admin:{Counterparty._meta.app_label}_"
                f"{Counterparty._meta.model_name}_changelist"
            )
            + f"?gr__id__exact={obj.pk}"
        )
        return format_html('<a href="{}">{}</a>', url, obj.num_counterparties)

    counterparty_count_link.short_description = "Контрагентов"
    counterparty_count_link.admin_order_field = "num_counterparties"

    # ---------- колонка "Аналитика" с 📊 ----------
    def analytics_link(self, obj: Gr):
        if not obj.num_counterparties:
            return ""
        url = reverse(
            f"admin:{Gr._meta.app_label}_{Gr._meta.model_name}_analytics",
            args=[obj.pk],
        )
        return format_html(
            '<a href="{}" title="Аналитика по группе контрагентов" '
            'style="text-decoration:none;font-size:14px;">📊</a>',
            url,
        )

    analytics_link.short_description = "Аналитика"

    # ---------- колонка "Печать" с 🖨 ----------
    def print_counterparties_link(self, obj: Gr):
        if not obj.num_counterparties:
            return ""
        url = reverse(
            f"admin:{Gr._meta.app_label}_{Gr._meta.model_name}_print_counterparties",
            args=[obj.pk],
        )
        return format_html(
            '<a href="{}" title="Печатная версия списка контрагентов" '
            'style="text-decoration:none;font-size:14px;">🖨</a>',
            url,
        )

    print_counterparties_link.short_description = "Печать"

    # ---------- печатная страница ----------
    def print_counterparties(self, request, pk):
        group = get_object_or_404(Gr, pk=pk)
        counterparties = Counterparty.objects.filter(gr=group).order_by("name")

        context = {
            "group": group,
            "counterparties": counterparties,
            "counterparty_count": counterparties.count(),
        }
        return render(request, "admin/gr_counterparties_print.html", context)

    # ---------- аналитика по группе ----------
    def group_analytics(self, request, pk):
        group = get_object_or_404(Gr, pk=pk)
        qs = Counterparty.objects.filter(gr=group)

        stats = build_group_counterparty_stats(qs)

        context = {
            "title": f"Аналитика по группе: {group.name}",
            "group": group,
            **stats,
        }
        return render(request, "admin/gr_counterparty_stats.html", context)




# ---------------------- REGISTRY ----------------------

admin.site.register(Gr, GrAdmin)
admin.site.register(Tenant, TenantAdmin)
admin.site.register(Counterparty, CounterpartyAdmin)
