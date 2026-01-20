from __future__ import annotations
from django.contrib import admin, messages
from django.contrib.auth.admin import (
    UserAdmin as DjangoUserAdmin,
    GroupAdmin as DjangoGroupAdmin,
)
from django.http import HttpResponseRedirect
from django import forms
from django.utils.safestring import mark_safe
from .utils.admin_calendar import WorkingCalendar
import json
from django.utils.http import url_has_allowed_host_and_scheme

from collections import OrderedDict
from django.contrib.auth.models import Permission
from collections import defaultdict
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path 
from django.contrib.auth.models import User, Group
from django.db.models import Count
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.html import format_html
from django.utils.dateparse import parse_date


from datetime import date as dt_date, timedelta
import datetime
import subprocess

from .calendar_render import build_year_calendar
from .utils.calendar_loader import load_work_calendar_for_year
from utils.choises import CURRENCY_SYMBOLS, CURRENCY_FLAGS





from decimal import Decimal
from typing import Iterable, Optional, List
from django.db import transaction
from django.db.models import OuterRef, Subquery, F, Q
from django.http import HttpRequest
from django.urls import path
from django.utils import timezone


from macro.services.cian_import import run_cian_import





from .service_funcs import sync_keyrates_from_cbr, sync_inflation_from_cbr
from .models import (
    WACC,
    Inflation,
    KeyRate,
    CalendarExceptions,
    TaxesList,
    TaxRates,
    CurrencyRate, 
    
    MarketRegion,
    MarketDistrict,
    OfficeClass,
    MarketSource,
    PropertyType,
    MarketListingObservation,
    MarketSnapshot,
    

)

from .constants import INFLATION_TARGET


# =====================================================================
#  КАСТОМНЫЙ ADMIN ДЛЯ ПОЛЬЗОВАТЕЛЕЙ И ГРУПП
# =====================================================================

# Снимаем стандартную регистрацию User/Group,
# чтобы переопределить их админ-классы.
admin.site.unregister(User)
admin.site.unregister(Group)


# ---------------------- Пользователи ----------------------


@admin.display(description="Пользователь")
def column_user_avatar_and_name(obj: User):
    """
    Аватар с инициалами + имя и @username в одном столбце.
    """
    initials = (obj.first_name[:1] + obj.last_name[:1]).strip()
    if not initials:
        initials = (obj.username[:2] or "U").upper()

    full_name = obj.get_full_name() or obj.username

    return format_html(
        '<div style="display:flex;align-items:center;gap:10px;">'
        '  <div style="'
        '      width:32px;height:32px;border-radius:999px;'
        '      background:#111827;color:#f9fafb;'
        '      display:flex;align-items:center;justify-content:center;'
        '      font-size:13px;font-weight:600;'
        '      box-shadow:0 0 0 1px rgba(15,23,42,.12);'
        '  ">{}</div>'
        '  <div style="display:flex;flex-direction:column;line-height:1.3;">'
        '    <span style="font-size:13px;font-weight:600;color:#111827;">{}</span>'
        '    <span style="font-size:11px;color:#6b7280;">@{}</span>'
        '  </div>'
        '</div>',
        initials,
        full_name,
        obj.username,
    )


@admin.display(description="Статус", ordering="is_active")
def column_user_status(obj: User):
    """
    Цветные бейджи: активен / отключен + роль (staff/superuser).
    """
    badges = []

    if obj.is_active:
        badges.append(
            '<span style="background:#dcfce7;color:#166534;padding:2px 6px;'
            'border-radius:6px;font-size:11px;font-weight:600;">Активен</span>'
        )
    else:
        badges.append(
            '<span style="background:#fee2e2;color:#991b1b;padding:2px 6px;'
            'border-radius:6px;font-size:11px;font-weight:600;">Отключен</span>'
        )

    if obj.is_superuser:
        badges.append(
            '<span style="background:#fef3c7;color:#92400e;padding:2px 6px;'
            'border-radius:6px;font-size:11px;font-weight:600;">Суперпользователь</span>'
        )
    elif obj.is_staff:
        badges.append(
            '<span style="background:#e0f2fe;color:#1d4ed8;padding:2px 6px;'
            'border-radius:6px;font-size:11px;font-weight:600;">Персонал</span>'
        )

    return format_html(" ".join(badges))


@admin.display(description="Email", ordering="email")
def column_user_email(obj: User):
    """
    Почта с иконкой письма.
    """
    if not obj.email:
        return "—"

    return format_html(
        '<a href="mailto:{0}" style="color:#2563eb;text-decoration:none;">'
        '✉ {0}'
        '</a>',
        obj.email,
    )


@admin.display(description="Группы", ordering="groups_count")
def column_user_groups(obj: User):
    """
    Список групп пользователя — КЛИКАБЕЛЬНЫЕ ссылки на форму редактирования группы.
    """
    groups = list(obj.groups.all())
    count = getattr(obj, "groups_count", len(groups))

    if not groups:
        return format_html(
            '<span style="font-size:11px;color:#9ca3af;">нет групп</span>'
        )

    links = []
    for g in groups[:3]:
        url = reverse("admin:auth_group_change", args=[g.pk])
        links.append(
            '<a href="{}" style="color:#2563eb;text-decoration:none;">{}</a>'.format(
                url, g.name
            )
        )

    names_html = ", ".join(links)

    if len(groups) > 3:
        names_html += f" +{len(groups) - 3}"

    return format_html(
        '<span style="font-size:11px;font-weight:500;color:#374151;">{}</span><br>'
        '<span style="font-size:11px;color:#6b7280;">({} шт.)</span>',
        format_html(names_html),
        count,
    )



class UserAdmin(DjangoUserAdmin):
    """
    Кастомный список пользователей с аватаром, статусами и группами.
    """

    list_display = (
        column_user_avatar_and_name,
        column_user_email,
        column_user_status,
        column_user_groups,
        "last_login",
        "date_joined",
    )
    list_display_links = (column_user_avatar_and_name,)
    search_fields = ("username", "first_name", "last_name", "email")
    list_filter = ("is_active", "is_staff",  "groups")
    ordering = ("username",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # чтобы не плодить запросы к groups
        return qs.annotate(groups_count=Count("groups"))
    
    
    class Media:
        css = {
            "all": (
                "css/admin_overrides.css", 
            )
        }


# ---------------------- Группы ----------------------


class GroupPermissionsForm(forms.ModelForm):
    """
    Права группируются по приложению с заголовками + иконки.
    """

    permissions = forms.ModelMultipleChoiceField(
        label="Права",
        required=False,
        queryset=Permission.objects.select_related("content_type"),
        widget=forms.CheckboxSelectMultiple,
        help_text="Отметьте права, которые должны быть у группы.",
    )

    class Meta:
        model = Group
        fields = ["name", "permissions"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # иконки для разных content_type
        APP_ICONS = {
            "log entry": "🗒",
            "group": "🧩",
            "permission": "🔐",
            "Пользователь": "👤",
            # твои приложения:
            "properties": "🏢",
            "counterparties": "🤝",
            "corporate": "🏛",
            "la": "📄",
            "services": "🛠",
            "macro": "📊",
        }

        perms = (
            self.fields["permissions"]
            .queryset
            .order_by("content_type__app_label", "codename")
        )

        grouped = OrderedDict()

        for p in perms:
            # “сырое” имя app’а (как в БД)
            raw_name = p.content_type.app_label.lower()
            # человекочитаемое имя (как раньше)
            app_label = p.content_type.name.capitalize()
            icon = APP_ICONS.get(raw_name, "📁")

            # заголовок группы: иконка + название
            group_title = f"{icon} {app_label}"

            # подпись для самого права
            label = f"{p.codename} — {p.name}"

            grouped.setdefault(group_title, []).append((str(p.pk), label))

        # optgroup’ы: [(заголовок, [(value, label), ...]), ...]
        self.fields["permissions"].choices = [
            (group_title, options) for group_title, options in grouped.items()
        ]


@admin.display(description="Пользователей", ordering="users_count")
def column_group_users_count(obj: Group):
    """
    Кол-во пользователей в группе — кликабельная ссылка в список Users.
    """
    count = getattr(obj, "users_count", obj.user_set.count())
    url = reverse("admin:auth_user_changelist") + f"?groups__id__exact={obj.id}"

    return format_html(
        '<a href="{}" style="text-decoration:none;">'
        '  <span style="'
        '     padding:2px 8px;border-radius:999px;'
        '     background:#eff6ff;color:#1d4ed8;'
        '     font-size:12px;font-weight:600;'
        '  ">{}</span>'
        '</a>',
        url,
        count,
    )


@admin.display(description="Группа")
def column_group_avatar_and_name(obj: Group):
    """
    Аватар + название группы в одном столбце.
    """
    initials = (obj.name[:2] or "GR").upper()

    return format_html(
        '<div style="display:flex;align-items:center;gap:10px;">'
        '  <div style="'
        '      width:28px;height:28px;border-radius:6px;'
        '      background:#111827;color:#f9fafb;'
        '      display:flex;align-items:center;justify-content:center;'
        '      font-size:13px;font-weight:600;'
        '      box-shadow:0 0 0 1px rgba(15,23,42,.12);'
        '  ">{}</div>'
        '  <div style="display:flex;flex-direction:column;line-height:1.3;">'
        '    <span style="font-size:13px;font-weight:600;color:#111827;">{}</span>'
        '  </div>'
        '</div>',
        initials,
        obj.name,
    )


@admin.display(description="Прав", ordering="perms_count")
def column_group_permissions_count(obj: Group):
    """
    Количество прав + иконка-глаз, по клику открывается модалка.
    """
    count = getattr(obj, "perms_count", obj.permissions.count())
    url = reverse("admin:auth_group_permissions", args=[obj.pk])

    return format_html(
        '<a href="#" '
        '   class="js-show-perms" '
        '   data-url="{}" '
        '   style="font-size:14px;padding:2px 8px;border-radius:999px;'
        '          background:#f3f4f6;color:#4b5563;text-decoration:none;'
        '          display:inline-flex;align-items:center;gap:4px;'
        '          border:1px solid #e5e7eb;'
        '          cursor:pointer;">'
        '    👁 {}'
        '</a>',
        url,
        count,
    )


class GroupAdmin(DjangoGroupAdmin):
    """
    Кастомный список групп: аватар, пользователи, количество прав.
    """
    form = GroupPermissionsForm

    list_display = (
        column_group_avatar_and_name,
        column_group_users_count,
        column_group_permissions_count,
    )
    list_display_links = (column_group_avatar_and_name,)
    search_fields = ("name",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            users_count=Count("user", distinct=True),
            perms_count=Count("permissions", distinct=True),
        )
    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path(
                "<int:pk>/permissions/",
                self.admin_site.admin_view(self.permissions_modal_view),
                name="auth_group_permissions",
            ),
        ]
        return my_urls + urls

    def permissions_modal_view(self, request, pk):
        """
        Группируем права по приложению и типу действия:
        view / add / change / delete / other.
        """
        group = get_object_or_404(Group, pk=pk)
        perms = (
            group.permissions
            .select_related("content_type")
            .order_by("content_type__app_label", "codename")
        )

        apps = defaultdict(lambda: {
            "label": "",
            "by_action": {
                "view": [],
                "add": [],
                "change": [],
                "delete": [],
                "other": [],
            },
        })

        for p in perms:
            app_key = p.content_type.app_label
            app_verbose = p.content_type.name

            data = apps[app_key]
            if not data["label"]:
                data["label"] = app_verbose

            if p.codename.startswith("view_"):
                action = "view"
            elif p.codename.startswith("add_"):
                action = "add"
            elif p.codename.startswith("change_"):
                action = "change"
            elif p.codename.startswith("delete_"):
                action = "delete"
            else:
                action = "other"

            data["by_action"][action].append(p)

        # превращаем в отсортованный список для шаблона
        apps_list = []
        for key in sorted(apps.keys()):
            apps_list.append(apps[key])

        context = {
            "group": group,
            "apps": apps_list,
        }

        return TemplateResponse(
            request,
            "admin/auth/group/permissions_modal.html",
            context,
        )
    
    class Media:
        css = {
            "all": (
                "css/admin_overrides.css", 
            )
        }






# =====================================================================
#  MACRO-МОДЕЛИ (WACC, инфляция, ставки, календарь и т.п.)
# =====================================================================

#----- КЛЮЧЕВАЯ СТАВКА -----#

class KeyRateAdmin(admin.ModelAdmin):
    list_display = ("date", "key_rate", "print_link")
    exclude = ('comment',)

    # ------- Кнопка "Печать" в списке -------
    def print_link(self, obj):
        url = reverse("admin:macro_keyrate_print", args=[obj.pk])
        return format_html(
            '<a href="{}" class="button">🖨</a>',
            url,
        )
    print_link.short_description = "Печать"
    print_link.allow_tags = True
    
    list_per_page = 10

    # ------- кастомные URL: sync + print -------
    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path(
                "sync-from-cbr/",
                self.admin_site.admin_view(self.sync_from_cbr_view),
                name="macro_keyrate_sync_from_cbr",
            ),
            path(
                "print/<int:pk>/",
                self.admin_site.admin_view(self.print_view),
                name="macro_keyrate_print",
            ),
        ]
        return my_urls + urls

    # ------- синхронизация с сайта ЦБ -------
    def sync_from_cbr_view(self, request):
        if not self.has_change_permission(request):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied

        cnt = sync_keyrates_from_cbr()
        self.message_user(
            request,
            f"С сайта ЦБ загружено / обновлено записей: {cnt}",
            level=messages.SUCCESS,
        )
        return HttpResponseRedirect(
            reverse("admin:macro_keyrate_changelist")
        )

    # ------- список (мы уже делали "по изменениям") -------
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        qs = self.get_queryset(request)

        FIELD_NAME = "key_rate"

        changes = []
        last_rate = None
        for obj in qs.order_by("date"):
            r = getattr(obj, FIELD_NAME, None)
            if r is None:
                continue
            r_float = float(r)
            if last_rate is None or r_float != last_rate:
                changes.append({"obj": obj, "rate": r_float})
                last_rate = r_float

        current_rate = None
        current_rate_date = None
        prev_rate = None
        prev_rate_date = None
        rate_change = None

        if changes:
            last_change = changes[-1]
            current_obj = last_change["obj"]
            current_rate = last_change["rate"]
            current_rate_date = current_obj.date

            if len(changes) > 1:
                prev_change = changes[-2]
                prev_obj = prev_change["obj"]
                prev_rate = prev_change["rate"]
                prev_rate_date = prev_obj.date
                rate_change = current_rate - prev_rate

        # история для графика (последние 12 изменений)
        history = []
        if changes:
            for item in changes[-12:]:
                obj = item["obj"]
                history.append({
                    "date": obj.date.isoformat(),
                    "rate": item["rate"],
                })

        extra_context.update({
            "current_rate": current_rate,
            "current_rate_date": current_rate_date,
            "prev_rate": prev_rate,
            "prev_rate_date": prev_rate_date,
            "rate_change": rate_change,
            "history_json": mark_safe(json.dumps(history)),
        })

        return super().changelist_view(request, extra_context=extra_context)

    # ------- ПЕЧАТНАЯ ФОРМА ДЛЯ ОДНОЙ СТАВКИ -------
    def print_view(self, request, pk):
        FIELD_NAME = "key_rate"

        obj = get_object_or_404(KeyRate, pk=pk)

        # ряд только по изменениям ставки (по всей истории)
        qs_all = KeyRate.objects.all().order_by("date")
        changes = []
        last_rate_raw = None
        for item in qs_all:
            r = getattr(item, FIELD_NAME, None)
            if r is None:
                continue
            r_float = float(r)
            if last_rate_raw is None or r_float != last_rate_raw:
                changes.append({"obj": item, "rate": r_float})
                last_rate_raw = r_float

        # находим выбранную запись в ряду изменений
        current_rate = None
        current_rate_date = None
        prev_rate = None
        prev_rate_date = None
        rate_change = None
        current_index = None

        for idx, item in enumerate(changes):
            if item["obj"].pk == obj.pk:
                current_index = idx
                break

        if current_index is not None:
            cur = changes[current_index]
            current_rate = cur["rate"]
            current_rate_date = cur["obj"].date

            if current_index > 0:
                prev = changes[current_index - 1]
                prev_rate = prev["rate"]
                prev_rate_date = prev["obj"].date
                rate_change = current_rate - prev_rate
        else:
            # запасной вариант
            r = getattr(obj, FIELD_NAME, None)
            current_rate = float(r) if r is not None else None
            current_rate_date = obj.date

        # --- история для таблицы и графика ---
        # сначала хронологически (по возрастанию даты) считаем дельты
        history_chrono = []
        prev_val = None
        for item in changes:
            o = item["obj"]
            rate_val = item["rate"]
            if prev_val is None:
                delta = None
            else:
                delta = rate_val - prev_val
            history_chrono.append({
                "date": o.date,
                "rate": rate_val,
                "delta": delta,
            })
            prev_val = rate_val

        # для отображения: новые сверху → разворачиваем
        history_display = list(reversed(history_chrono))

        # для Plotly: оставляем в хронологическом порядке, как раньше
        history_for_js = [
            {"date": h["date"].isoformat(), "rate": h["rate"]}
            for h in history_chrono
        ]

        context = {
            "opts": self.model._meta,
            "original": obj,
            "current_rate": current_rate,
            "current_rate_date": current_rate_date,
            "prev_rate": prev_rate,
            "prev_rate_date": prev_rate_date,
            "rate_change": rate_change,
            "history": history_display,                     # новые сверху, с delta
            "history_json": mark_safe(json.dumps(history_for_js)),  # для графика
            "title": "Печатная форма ключевой ставки",
        }

        return TemplateResponse(
            request,
            "admin/macro/keyrate/print.html",
            context,
        )
    
    
    class Media:
        css = {
            "all": (
                "fonts/glyphs.css",
                "css/admin_overrides.css",  
            )
        }
    

#----- ИНФЛЯЦИЯ -----#
class InflationAdmin(admin.ModelAdmin):
    list_display = ("date", "inflation_rate", 'print_link')
    ordering = ("-date",)
    exclude = ('comment',)
    
    list_per_page = 25
    
    
    # ----- колонка "Печать" -----
    def print_link(self, obj):
        url = reverse("admin:macro_inflation_print", args=[obj.pk])
        return format_html('<a href="{}" class="button">🖨</a>', url)

    print_link.short_description = "Печать"
    
    # ----- кастомные URL: sync + print -----
    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path(
                "sync-from-cbr/",
                self.admin_site.admin_view(self.sync_from_cbr_view),
                name="macro_inflation_sync_from_cbr",
            ),
            path(
                "print/<int:pk>/",
                self.admin_site.admin_view(self.print_view),
                name="macro_inflation_print",
            ),
        ]
        return my_urls + urls


    # ----- синхронизация с ЦБ -----
    def sync_from_cbr_view(self, request):
        if not self.has_change_permission(request):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied

        cnt = sync_inflation_from_cbr()
        self.message_user(
            request,
            f"С сайта ЦБ загружено / обновлено записей по инфляции: {cnt}",
            level=messages.SUCCESS,
        )
        return HttpResponseRedirect(
            reverse("admin:macro_inflation_changelist")
        ) 
        
        
    # ----- печатная форма одной записи -----
    def print_view(self, request, pk):
        FIELD_NAME = "inflation_rate"

        obj = get_object_or_404(Inflation, pk=pk)

        # вся история (по дате, для графика и таблиц)
        qs_all = Inflation.objects.all().order_by("date")

        history_chrono = []
        prev_val = None

        for item in qs_all:
            r = getattr(item, FIELD_NAME, None)
            if r is None:
                continue
            r_float = float(r)
            if prev_val is None:
                delta = None
            else:
                delta = r_float - prev_val
            history_chrono.append({
                "obj": item,
                "date": item.date,
                "rate": r_float,
                "delta": delta,   # изменение к предыдущему периоду
            })
            prev_val = r_float

        # ищем текущую запись в истории
        current_rate = None
        current_rate_date = None
        prev_rate = None
        prev_rate_date = None
        rate_change = None
        current_index = None

        for idx, item in enumerate(history_chrono):
            if item["obj"].pk == obj.pk:
                current_index = idx
                break

        if current_index is not None:
            cur = history_chrono[current_index]
            current_rate = cur["rate"]
            current_rate_date = cur["date"]

            if current_index > 0:
                prev = history_chrono[current_index - 1]
                prev_rate = prev["rate"]
                prev_rate_date = prev["date"]
                rate_change = current_rate - prev_rate
        else:
            r = getattr(obj, FIELD_NAME, None)
            current_rate = float(r) if r is not None else None
            current_rate_date = obj.date

        # для отображения в таблицах — новые сверху
        history_display = []
        for item in reversed(history_chrono):
            history_display.append({
                "date": item["date"],
                "rate": item["rate"],
                "delta": item["delta"],
            })

        # для графиков — хронология (старые → новые)
        # добавляем и rate, и delta
        history_for_js = [
            {
                "date": item["date"].isoformat(),
                "rate": item["rate"],
                "delta": item["delta"],
            }
            for item in history_chrono
        ]

        # --- таргет по инфляции и отклонение от него ---
        TARGET_RATE = INFLATION_TARGET  # из constants.py
        diff_to_target = None
        if current_rate is not None:
            diff_to_target = current_rate - TARGET_RATE

        context = {
            "opts": self.model._meta,
            "original": obj,
            "current_rate": current_rate,
            "current_rate_date": current_rate_date,
            "prev_rate": prev_rate,
            "prev_rate_date": prev_rate_date,
            "rate_change": rate_change,
            "history": history_display,                           # новые сверху
            "history_json": mark_safe(json.dumps(history_for_js)),  # для JS-графиков
            "title": "Печатная форма инфляции",
            "target_rate": TARGET_RATE,
            "diff_to_target": diff_to_target,
        }

        return TemplateResponse(
            request,
            "admin/macro/inflation/print.html",
            context,
        )
    
    class Media:
        css = {
            "all": (
                "fonts/glyphs.css",
                "css/admin_overrides.css",  
            )
        }



    def changelist_view(self, request, extra_context=None):

            extra_context = extra_context or {}

            FIELD_NAME = "inflation_rate"

            # Берём queryset с учётом фильтров/поиска в админке
            qs = self.get_queryset(request).exclude(**{f"{FIELD_NAME}__isnull": True}).order_by("date")

            history_chrono = []
            for item in qs:
                r = getattr(item, FIELD_NAME, None)
                if r is None:
                    continue
                history_chrono.append({
                    "date": item.date,
                    "rate": float(r),
                })

            current_rate = current_rate_date = None
            rate_change = None

            if history_chrono:
                last = history_chrono[-1]
                current_rate = last["rate"]
                current_rate_date = last["date"]

                if len(history_chrono) > 1:
                    prev = history_chrono[-2]
                    rate_change = current_rate - prev["rate"]

            history_for_js = [
                {"date": item["date"].isoformat(), "rate": item["rate"]}
                for item in history_chrono
            ]

            extra_context.update(
                current_rate=current_rate,
                current_rate_date=current_rate_date,
                rate_change=rate_change,
                history_json=mark_safe(json.dumps(history_for_js)),
            )

            return super().changelist_view(request, extra_context=extra_context)




#----- КАЛЕНДАРЬ -----#

class CalendarExceptionsAdmin(admin.ModelAdmin):

    def changelist_view(self, request, extra_context=None):
        year_param = request.GET.get("year")
        try:
            year = int(year_param) if year_param else dt_date.today().year
        except (TypeError, ValueError):
            year = dt_date.today().year

        qs = CalendarExceptions.objects.filter(date__year=year)
        exceptions = {obj.date: obj.is_working_day for obj in qs}

        calendar_html = build_year_calendar(year, exceptions)

        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "title": f"Календарь — {year}",
            "year": year,
            "year_str": str(year),
            "calendar_html": calendar_html,
        }

        return TemplateResponse(
            request,
            "admin/macro/calendarexceptions/calendar_view.html",
            context,
        )

    # ---------- URL'ы: загрузка + печать ----------
    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path(
                "load/",
                self.admin_site.admin_view(self.load_calendar),
                name="macro_calendarexceptions_load",
            ),
            path(
                "print/",
                self.admin_site.admin_view(self.print_view),
                name="macro_calendarexceptions_print",
            ),
        ]
        return my_urls + urls

    # ---------- загрузка П-календаря ----------
    def load_calendar(self, request):
        year_param = request.GET.get("year")
        try:
            year = int(year_param) if year_param else dt_date.today().year
        except (TypeError, ValueError):
            year = dt_date.today().year

        try:
            count = load_work_calendar_for_year(year)
            messages.success(
                request,
                f"Производственный календарь за {year} загружен. "
                f"Создано {count} записей.",
            )
        except Exception as e:
            messages.error(
                request,
                f"Ошибка загрузки календаря за {year}: {e}",
            )

        changelist_url = reverse("admin:macro_calendarexceptions_changelist")
        return redirect(f"{changelist_url}?year={year}")

    # ---------- печатная форма ----------
    def print_view(self, request):
        """
        Печатная версия годового производственного календаря.
        URL: /admin/macro/calendarexceptions/print/?year=2025
        """
        year_param = request.GET.get("year")
        try:
            year = int(year_param) if year_param else dt_date.today().year
        except (TypeError, ValueError):
            year = dt_date.today().year

        # исключения за год
        qs = CalendarExceptions.objects.filter(date__year=year)
        exceptions_map = {obj.date: obj.is_working_day for obj in qs}

        # HTML календаря (тот же, что на экране)
        calendar_html = build_year_calendar(year, exceptions_map)

        # простая сводка по году
        totals = self._calc_year_totals(year, exceptions_map)

        context = {
            "opts": self.model._meta,
            "title": f"Производственный календарь {year} — печать",
            "year": year,
            "year_str": str(year),
            "calendar_html": mark_safe(calendar_html),
            "totals": totals,
            "exceptions": qs,  # на случай приложения табличкой
        }

        return TemplateResponse(
            request,
            "admin/macro/calendarexceptions/print.html",
            context,
        )

    def _calc_year_totals(self, year: int, exceptions_map: dict):
        """
        Грубая сводка по году:
        - всего дней
        - рабочих (с учётом исключений)
        - остальных (выходные/праздники)
        - количество "особых" дней из исключений
        """
        first = dt_date(year, 1, 1)
        last = dt_date(year + 1, 1, 1)
        day = first

        days_total = 0
        workdays = 0
        special_days = 0

        while day < last:
            days_total += 1

            base_work = day.weekday() < 5  # пн–пт
            if day in exceptions_map:
                is_work = exceptions_map[day]
                special_days += 1
            else:
                is_work = base_work

            if is_work:
                workdays += 1

            day += timedelta(days=1)

        return {
            "days_total": days_total,
            "workdays": workdays,
            "weekends": days_total - workdays,
            "holidays": special_days,  # "праздничных / переносов" по модели
        }



#----- НАЛОГИ -----#

class TaxRatesInline(admin.TabularInline):
    """
    Вложенные ставки налога внутри TaxesList.
    """
    model = TaxRates
    extra = 1
    show_change_link = True
    verbose_name = "Ставка налога"
    verbose_name_plural = "Ставки налога"
    fields = ("date", "rate", )
    ordering = ("-date",)


@admin.display(description="Текущая ставка")
def column_current_rate(obj: TaxesList):

    rate = obj.get_current_rate()
    if rate is None:
        return format_html(
            '<span style="font-size:11px;color:#9ca3af;">нет ставки</span>'
        )

    return format_html(
        '<span style="'
        '  display:inline-flex;align-items:center;gap:4px;'
        '  padding:2px 8px;border-radius:6px;'
        '  background:#ecfdf5;color:#166534;'
        '  font-size:12px;font-weight:600;'
        '">'
        '  {}'
        '</span>',
        rate,
    )


@admin.display(description="История ставок")
def column_rates_count(obj: TaxesList):
    """
    Кол-во исторических ставок как маленький бейдж.
    """
    cnt = obj.taxrates_set.count()
    if not cnt:
        return format_html(
            '<span style="font-size:11px;color:#9ca3af;">нет истории</span>'
        )

    return format_html(
        '<span style="'
        '  padding:2px 8px;border-radius:6px;'
        '  background:#eff6ff;color:#1d4ed8;'
        '  font-size:11px;font-weight:600;'
        '">'
        '  {} записей'
        '</span>',
        cnt,
    )


class TaxesListAdmin(admin.ModelAdmin):
    change_list_template = "admin/macro/taxeslist/change_list.html"

    list_display = ("tax_name", column_current_rate, column_rates_count)
    search_fields = ("tax_name",)
    ordering = ("tax_name",)
    exclude = ("description", )
    inlines = [TaxRatesInline]

    def changelist_view(self, request, extra_context=None):
        qs = self.get_queryset(request)

        summary_current = 0
        summary_without = 0

        for tax in qs:
            rate = tax.get_current_rate()
            if rate is None:
                summary_without += 1
            else:
                summary_current += 1

        extra_context = extra_context or {}
        extra_context["summary_current"] = summary_current
        extra_context["summary_without"] = summary_without

        return super().changelist_view(request, extra_context=extra_context)
    
    
    class Media:
        css = {
            "all": (
                "fonts/glyphs.css",
                "css/admin_overrides.css", 
            )
        }
    






#----- КУРСЫ ВАЛЮТ -----#

def format_currency_with_flag(code: str) -> str:
    symbol = CURRENCY_SYMBOLS.get(code, "")
    flag = CURRENCY_FLAGS.get(code, "")
    # можно без mark_safe, т.к. тут эмодзи, но пусть будет, если потом захочешь HTML
    return mark_safe(f"{flag} {symbol} {code}")

class CurrencyRateAdmin(admin.ModelAdmin):
    list_display = ("date", "currency_with_flag", "base_currency", "rate", "source", "print_link")
    list_filter = ("currency",)
    ordering = ("-date", "currency")
    
    list_per_page = 25

    # ─────────────────────
    #   отображение валюты
    # ─────────────────────
    def currency_with_symbol(self, obj):
        symbol = CURRENCY_SYMBOLS.get(obj.currency, "¤")
        return mark_safe(
            '<span style="font-size:14px;margin-right:4px;">{}</span>{}'.format(
                symbol, obj.currency
            )
        )

    currency_with_symbol.short_description = "Валюта"
    currency_with_symbol.admin_order_field = "currency"

    def currency_with_flag(self, obj):
        return format_currency_with_flag(obj.currency)

    currency_with_flag.short_description = "Валюта"

    # ─────────────────────
    #   кнопка печати
    # ─────────────────────
    def print_link(self, obj):
        url = reverse("admin:macro_currencyrate_print", args=[obj.pk])
        return mark_safe(f'<a href="{url}" class="button">🖨</a>')

    print_link.short_description = "Печать"

    # ─────────────────────
    #   контекст для списка (сегодня по умолчанию)
    # ─────────────────────
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["today"] = datetime.date.today().strftime("%Y-%m-%d")
        return super().changelist_view(request, extra_context=extra_context)

    # ─────────────────────
    #   свои URL'ы
    # ─────────────────────
    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path(
                "load/",
                self.admin_site.admin_view(self.load_rates),
                name="macro_currency_load",
            ),
            path(
                "print/<int:pk>/",
                self.admin_site.admin_view(self.print_view),
                name="macro_currencyrate_print",
            ),
        ]
        return my_urls + urls

    # ─────────────────────
    #   загрузка курсов
    # ─────────────────────
    def load_rates(self, request):
        """
        Загружаем курсы за выбранный диапазон дат.
        Если даты не указаны — берём сегодня.
        Если currencies не указаны — команда возьмёт все валюты из CURRENCY_CHOISE.
        """
        today_str = datetime.date.today().strftime("%Y-%m-%d")

        date_from = request.GET.get("date_from") or today_str
        date_to = request.GET.get("date_to") or date_from
        currencies = request.GET.get("currencies")

        cmd = [
            "python",
            "manage.py",
            "load_currency_rates",
            "--from",
            date_from,
            "--to",
            date_to,
        ]

        if currencies:
            cmd += ["--currencies", currencies]

        try:
            subprocess.check_call(cmd)
            messages.success(
                request,
                f"Курсы валют загружены за период {date_from} — {date_to}.",
            )
        except Exception as e:
            messages.error(request, f"Ошибка при загрузке: {e}")

        changelist_url = reverse("admin:macro_currencyrate_changelist")
        return redirect(changelist_url)

    # ─────────────────────
    #   ПЕЧАТНАЯ ФОРМА ДЛЯ ОДНОГО КУРСА
    # ─────────────────────
    def print_view(self, request, pk):
        obj = get_object_or_404(CurrencyRate, pk=pk)

        current_date = obj.date
        # Берём данные за последний год относительно выбранной даты
        start_date = current_date - timedelta(days=365)

        # история за год по этой валюте (хронологически)
        qs_year = (
            CurrencyRate.objects
            .filter(
                currency=obj.currency,
                date__gte=start_date,
                date__lte=current_date,
            )
            .order_by("date")
        )

        history_chrono = []
        prev_rate_val = None
        for item in qs_year:
            rate_val = float(item.rate) if item.rate is not None else None
            if rate_val is None:
                continue

            if prev_rate_val is None:
                delta = None
            else:
                delta = rate_val - prev_rate_val

            history_chrono.append(
                {
                    "date": item.date,
                    "rate": rate_val,
                    "delta": delta,
                }
            )
            prev_rate_val = rate_val

        # для таблицы: последние 12 записей (если их меньше — все), новые сверху
        history_display = list(reversed(history_chrono[-12:]))

        # для графика: весь ряд за год в хронологическом порядке
        history_for_js = [
            {"date": h["date"].isoformat(), "rate": h["rate"]}
            for h in history_chrono
        ]

        # предыдущий курс (по дате) — по всей истории, не только за год
        prev_obj = (
            CurrencyRate.objects
            .filter(currency=obj.currency, date__lt=current_date)
            .order_by("-date")
            .first()
        )

        current_rate = float(obj.rate) if obj.rate is not None else None
        prev_rate = (
            float(prev_obj.rate)
            if prev_obj is not None and prev_obj.rate is not None
            else None
        )
        prev_date = prev_obj.date if prev_obj else None

        rate_change = None
        if current_rate is not None and prev_rate is not None:
            rate_change = current_rate - prev_rate

        context = {
            "opts": self.model._meta,
            "original": obj,
            "currency": obj.currency,
            "base_currency": obj.base_currency,
            "currency_with_flag": format_currency_with_flag(obj.currency),
            "base_currency_with_flag": format_currency_with_flag(obj.base_currency),
            "current_rate": current_rate,
            "current_date": current_date,
            "prev_rate": prev_rate,
            "prev_date": prev_date,
            "rate_change": rate_change,
            "source": obj.source,
            "history": history_display,
            "history_json": mark_safe(json.dumps(history_for_js)),
            "title": "Печатная форма курса валюты",
        }

        return TemplateResponse(
            request,
            "admin/macro/currencyrate/print.html",
            context,
        )
    
    class Media:
        css = {
            "all": (
                "fonts/glyphs.css",
                "css/admin_overrides.css",  
            )
        }







 #=========================



#----- РЫНОЧНЫЕ ЦЕНЫ -----#
def quantile(sorted_vals, q: Decimal):
    n = len(sorted_vals)
    if n == 0:
        return None
    if n == 1:
        return sorted_vals[0]

    pos = (Decimal(n) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, n - 1)
    frac = pos - Decimal(lo)

    if lo == hi:
        return sorted_vals[lo]

    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * frac


class ReturnToNextMixin:
    """
    Если в URL есть ?next=/admin/.../analyze/ — после add/change/delete
    возвращаемся на next.
    """

    def _get_next_url(self, request):
        nxt = request.GET.get("next")
        if not nxt:
            return None
        # безопасность: разрешаем только локальные пути
        if url_has_allowed_host_and_scheme(
            url=nxt,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            return nxt
        return None

    def response_add(self, request, obj, post_url_continue=None):
        nxt = self._get_next_url(request)
        if nxt:
            return HttpResponseRedirect(nxt)
        return super().response_add(request, obj, post_url_continue=post_url_continue)

    def response_change(self, request, obj):
        nxt = self._get_next_url(request)
        if nxt:
            return HttpResponseRedirect(nxt)
        return super().response_change(request, obj)

    def response_delete(self, request, obj_display, obj_id):
        nxt = self._get_next_url(request)
        if nxt:
            return HttpResponseRedirect(nxt)
        return super().response_delete(request, obj_display, obj_id)



@admin.register(MarketRegion)
class MarketRegionAdmin(ReturnToNextMixin, admin.ModelAdmin):
    search_fields = ("name",)
    def get_model_perms(self, request):
        return {}


@admin.register(MarketDistrict)
class MarketDistrictAdmin(ReturnToNextMixin, admin.ModelAdmin):
    search_fields = ("name",)
    list_filter = ("region",)
    autocomplete_fields = ("region",)
    def get_model_perms(self, request):
        return {}


@admin.register(OfficeClass)
class OfficeClassAdmin(ReturnToNextMixin, admin.ModelAdmin):
    search_fields = ("code", "name")
    def get_model_perms(self, request):
        return {}


@admin.register(PropertyType)
class PropertyTypeAdmin(ReturnToNextMixin, admin.ModelAdmin):
    search_fields = ("code", "name")
    list_filter = ("is_active",)
    def get_model_perms(self, request):
        return {}


@admin.register(MarketSource)
class MarketSourceAdmin(ReturnToNextMixin, admin.ModelAdmin):
    search_fields = ("code", "name")
    def get_model_perms(self, request):
        return {}



def admin_url_for(model_cls, action: str, args=None):
    """
    action: add / change / delete
    """
    opts = model_cls._meta
    return reverse(f"admin:{opts.app_label}_{opts.model_name}_{action}", args=args or [])


@admin.register(MarketSnapshot)
class MarketAnalyticsAdminView(admin.ModelAdmin):
    change_list_template = "admin/macro/marketsnapshot/market_analyze.html"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request):
        return False

    def changelist_view(self, request, extra_context=None):
        context = extra_context or {}

        # справочники
        context["regions"] = MarketRegion.objects.all()
        context["districts"] = MarketDistrict.objects.select_related("region")
        context["office_classes"] = OfficeClass.objects.all()
        context["sources"] = MarketSource.objects.all()
        context["property_types"] = PropertyType.objects.filter(is_active=True)

        # чтобы template не падал
        context["selected"] = request.POST if request.method == "POST" else {}

        next_url = request.get_full_path()

        def admin_url_for(model_cls, action: str, args=None):
            opts = model_cls._meta
            return reverse(f"admin:{opts.app_label}_{opts.model_name}_{action}", args=args or [])

        def _base(model_cls, action):
            u = admin_url_for(model_cls, action, args=[0])
            return u.replace("/0/", "/__id__/")

        context["admin_links"] = {
            "property_type_add": admin_url_for(PropertyType, "add") + f"?_popup=1&next={next_url}",
            "region_add": admin_url_for(MarketRegion, "add") + f"?_popup=1&next={next_url}",
            "district_add": admin_url_for(MarketDistrict, "add") + f"?_popup=1&next={next_url}",
            "office_class_add": admin_url_for(OfficeClass, "add") + f"?_popup=1&next={next_url}",

            "property_type_change_base": _base(PropertyType, "change") + f"?_popup=1&next={next_url}",
            "region_change_base": _base(MarketRegion, "change") + f"?_popup=1&next={next_url}",
            "district_change_base": _base(MarketDistrict, "change") + f"?_popup=1&next={next_url}",
            "office_class_change_base": _base(OfficeClass, "change") + f"?_popup=1&next={next_url}",

            "property_type_delete_base": _base(PropertyType, "delete") + f"?next={next_url}",
            "region_delete_base": _base(MarketRegion, "delete") + f"?next={next_url}",
            "district_delete_base": _base(MarketDistrict, "delete") + f"?next={next_url}",
            "office_class_delete_base": _base(OfficeClass, "delete") + f"?next={next_url}",
        }

        result = None

        if request.method == "POST":
            action = request.POST.get("action")

            # ВСЕ поля читаем СРАЗУ (важно: и для load, и для calc)
            region_id = request.POST.get("region")
            district_id = request.POST.get("district")
            office_class_id = request.POST.get("office_class")
            property_type_id = request.POST.get("property_type")
            deal_type = request.POST.get("deal_type")

            date_from = request.POST.get("date_from")
            date_to = request.POST.get("date_to")
            save_snapshot = request.POST.get("save_snapshot") == "1"

            # ─────────────────────────────
            # 1) LOAD
            # ─────────────────────────────
            if action == "load":
                try:
                    list_url = (request.POST.get("cian_list_url") or "").strip()
                    pages = int(request.POST.get("pages") or 1)

                    if not list_url:
                        raise ValueError("Укажи CIAN URL (выдача)")

                    # для подгрузки обязательны сегментные поля
                    if not all([region_id, district_id, office_class_id, property_type_id, deal_type]):
                        raise ValueError("Для подгрузки выбери: Тип, Город, Район, Класс и Сделку.")

                    stats = run_cian_import(
                        list_url=list_url,
                        region_id=int(region_id),
                        district_id=int(district_id),
                        office_class_id=int(office_class_id),
                        property_type_id=int(property_type_id),
                        deal_type=deal_type,
                        pages=pages,
                    )

                    messages.success(
                        request,
                        f"Импорт ЦИАН: обработано {stats.get('processed', 0)}, "
                        f"новых наблюдений {stats.get('created_obs', 0)}, "
                        f"обновлено {stats.get('updated_obs', 0)}."
                    )
                except Exception as e:
                    messages.error(request, f"Ошибка подгрузки данных: {e}")

                context["result"] = None
                context["selected"] = request.POST
                return super().changelist_view(request, extra_context=context)

            # ─────────────────────────────
            # 2) CALC
            # ─────────────────────────────
            if not all([region_id, district_id, office_class_id, property_type_id, deal_type, date_from, date_to]):
                messages.warning(request, "Заполните все поля фильтра.")
                context["result"] = None
                context["selected"] = request.POST
                return super().changelist_view(request, extra_context=context)

            qs = MarketListingObservation.objects.filter(
                observed_date__gte=date_from,
                observed_date__lte=date_to,
                is_active=True,
                norm_rub_m2_month__gt=0,
                norm_rub_m2_month__isnull=False,
                listing__region_id=region_id,
                listing__district_id=district_id,
                listing__office_class_id=office_class_id,
                listing__property_type_id=property_type_id,
                listing__deal_type=deal_type,
            )

            values = sorted(
                Decimal(v) for v in qs.values_list("norm_rub_m2_month", flat=True)
                if v is not None
            )

            if values:
                result = {
                    "count": len(values),
                    "median": quantile(values, Decimal("0.5")),
                    "p25": quantile(values, Decimal("0.25")),
                    "p75": quantile(values, Decimal("0.75")),
                }

                if save_snapshot:
                    MarketSnapshot.objects.create(
                        period=date_from,
                        property_type_id=property_type_id,
                        deal_type=deal_type,
                        region_id=region_id,
                        district_id=district_id,
                        office_class_id=office_class_id,
                        metric="norm_rub_m2_month",
                        currency="RUB",
                        listings_count=result["count"],
                        median_price=result["median"],
                        p25_price=result["p25"],
                        p75_price=result["p75"],
                    )
                    messages.success(request, "Снимок рынка сохранён.")
            else:
                messages.warning(request, "Нет данных по выбранным фильтрам.")

            context["result"] = result
            context["selected"] = request.POST

        return super().changelist_view(request, extra_context=context)





# Регистрация macro-моделей
admin.site.register(WACC)
admin.site.register(Inflation, InflationAdmin)
admin.site.register(KeyRate, KeyRateAdmin)
admin.site.register(CalendarExceptions, CalendarExceptionsAdmin)
admin.site.register(TaxesList, TaxesListAdmin)
admin.site.register(CurrencyRate, CurrencyRateAdmin)
admin.site.register(User, UserAdmin)
admin.site.register(Group, GroupAdmin)


