# counterparties/filters.py

from datetime import timedelta

from django.contrib import admin
from django.contrib.auth.models import User
from django.db.models import Q, Count
from django.db.models.functions import Substr
from django.utils import timezone

from .models import Gr


# ---------------------------------------------------------------------------
#  Фильтры для Counterparty
# ---------------------------------------------------------------------------


class CounterpartyCheckoUpdatedFilter(admin.SimpleListFilter):
    """
    Фильтр по давности обновления данных ФНС / Checko.
    """
    title = "Обновление ФНС"
    parameter_name = "checko_status"

    def lookups(self, request, model_admin):
        return [
            ("never", "Нет отметки"),
            ("recent", "До 90 дней"),
            ("mid", "3–12 месяцев"),
            ("old", "Более года"),
        ]

    def queryset(self, request, queryset):
        value = self.value()
        if not value:
            return queryset

        now = timezone.now()

        if value == "never":
            return queryset.filter(checko_updated_at__isnull=True)

        if value == "recent":
            cutoff = now - timedelta(days=90)
            return queryset.filter(checko_updated_at__gte=cutoff)

        if value == "mid":
            cutoff_low = now - timedelta(days=365)
            cutoff_high = now - timedelta(days=90)
            return queryset.filter(
                checko_updated_at__lt=cutoff_high,
                checko_updated_at__gte=cutoff_low,
            )

        if value == "old":
            cutoff = now - timedelta(days=365)
            return queryset.filter(checko_updated_at__lt=cutoff)

        return queryset


# class CounterpartyRiskLevelFilter(admin.SimpleListFilter):
#     """
#     Фильтр по уровню риска (высокий / средний / низкий).
#     """
#     title = "Уровень риска"
#     parameter_name = "risk_level"

#     def lookups(self, request, model_admin):
#         return [
#             ("high", "Высокий риск"),
#             ("mid", "Средний риск"),
#             ("low", "Низкий риск"),
#         ]

#     def queryset(self, request, queryset):
#         value = self.value()
#         if not value:
#             return queryset

#         # 🔴 Высокий риск
#         if value == "high":
#             return queryset.filter(
#                 Q(risk_sanctions=True) | Q(risk_sanctioned_founder=True)
#             ).distinct()

#         # 🟡 Средний риск
#         if value == "mid":
#             return queryset.filter(
#                 risk_sanctions=False,
#                 risk_sanctioned_founder=False,
#             ).filter(
#                 Q(risk_illegal_fin=True)
#                 | Q(risk_mass_directors=True)
#                 | Q(risk_mass_founders=True)
#                 | Q(risk_disq_persons=True)
#             ).distinct()

#         # 🟢 Низкий риск
#         if value == "low":
#             return queryset.filter(
#                 risk_sanctions=False,
#                 risk_sanctioned_founder=False,
#                 risk_illegal_fin=False,
#                 risk_mass_directors=False,
#                 risk_mass_founders=False,
#                 risk_disq_persons=False,
#             )

#         return queryset



class CounterpartyRiskLevelFilter(admin.SimpleListFilter):
    """
    Фильтр по уровню риска (высокий / средний / низкий).
    """
    title = "Уровень риска"
    parameter_name = "risk_level"

    def lookups(self, request, model_admin):
        return [
            ("high", "Высокий риск"),
            ("mid", "Средний риск"),
            ("low", "Низкий риск"),
        ]

    def queryset(self, request, queryset):
        value = self.value()
        if not value:
            return queryset

        # 🔴 Условие высокого риска
        high_q = (
            Q(risk_sanctions=True)
            | Q(risk_sanctioned_founder=True)
            | (Q(risk_sanctions_countries__isnull=False) &
               ~Q(risk_sanctions_countries__exact=""))
        )

        # 🟡 Условие среднего риска
        mid_q = (
            Q(risk_illegal_fin=True)
            | Q(risk_mass_directors=True)
            | Q(risk_mass_founders=True)
            | Q(risk_disq_persons=True)
        )

        # 🔴 Высокий риск
        if value == "high":
            return queryset.filter(high_q).distinct()

        # 🟡 Средний риск — всё, что не high, но подпадает под mid-флаги
        if value == "mid":
            return queryset.exclude(high_q).filter(mid_q).distinct()

        # 🟢 Низкий риск — ничего из high и ничего из mid
        if value == "low":
            return queryset.exclude(high_q).filter(
                risk_illegal_fin=False,
                risk_mass_directors=False,
                risk_mass_founders=False,
                risk_disq_persons=False,
            )

        return queryset



class CounterpartyLegalFormFilter(admin.SimpleListFilter):
    """
    Фильтр по ОПФ (ОКОПФ): код / название / отсутствие ОПФ.
    """
    title = "ОПФ (ОКОПФ)"
    parameter_name = "okopf_code"

    def lookups(self, request, model_admin):
        base_qs = model_admin.get_queryset(request)

        # все, у кого есть либо код, либо название ОПФ
        qs = (
            base_qs.filter(
                Q(okopf_code__isnull=False, okopf_code__gt="")
                | Q(okopf_name__isnull=False, okopf_name__gt="")
            )
            .values("okopf_code", "okopf_name")
            .annotate(cnt=Count("id"))
            .order_by("okopf_name", "okopf_code")
        )

        items = []
        for row in qs:
            code = (row["okopf_code"] or "").strip()
            name = (row["okopf_name"] or "").strip()

            label_name = name or code or "Без названия"

            if code:
                key = code
                label = f"{code} — {label_name} ({row['cnt']})"
            else:
                key = f"name::{label_name}"
                label = f"{label_name} ({row['cnt']})"

            items.append((key, label))

        # пункт "Без ОПФ" (нет ни кода, ни названия)
        missing_cnt = base_qs.filter(
            (Q(okopf_code__isnull=True) | Q(okopf_code__exact=""))
            & (Q(okopf_name__isnull=True) | Q(okopf_name__exact=""))
        ).count()
        if missing_cnt:
            items.insert(0, ("_none", f"Без ОПФ ({missing_cnt})"))

        return items

    def queryset(self, request, queryset):
        value = self.value()
        if not value:
            return queryset

        if value == "_none":
            # совсем без ОПФ (ни кода, ни имени)
            return queryset.filter(
                (Q(okopf_code__isnull=True) | Q(okopf_code__exact=""))
                & (Q(okopf_name__isnull=True) | Q(okopf_name__exact=""))
            )

        if value.startswith("name::"):
            # кейс, когда кода нет, но есть имя (например, "Физическое лицо")
            name = value.split("name::", 1)[1]
            return queryset.filter(okopf_name=name)

        # обычный кейс — фильтрация по коду
        return queryset.filter(okopf_code=value)


class CounterpartyOkvedPrefixFilter(admin.SimpleListFilter):
    """
    Фильтр по префиксу ОКВЭД (первые две цифры).
    """
    title = "ОКВЭД (2 цифры)"
    parameter_name = "okved_prefix"

    def lookups(self, request, model_admin):
        qs = (
            model_admin.get_queryset(request)
            .exclude(okved_code__isnull=True)
            .exclude(okved_code__exact="")
            .annotate(prefix=Substr("okved_code", 1, 2))
            .values("prefix")
            .annotate(cnt=Count("id"))
            .order_by("prefix")
        )
        return [
            (row["prefix"], f'{row["prefix"]} ({row["cnt"]})')
            for row in qs
        ]

    def queryset(self, request, queryset):
        value = self.value()
        if not value:
            return queryset
        return queryset.filter(okved_code__startswith=value)


# ---------------------------------------------------------------------------
#  Фильтры для Tenant
# ---------------------------------------------------------------------------


class TenantUserPrettyFilter(admin.SimpleListFilter):
    """
    Фильтр по ответственному лицу (User) в кабинетах арендаторов.
    """
    title = "Ответств. лицо"
    parameter_name = "user"

    def lookups(self, request, model_admin):
        qs = User.objects.filter(tenant__isnull=False).distinct()
        return [
            (u.pk, f"{u.get_full_name() or u.username} ({u.username})")
            for u in qs
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(user__pk=self.value())
        return queryset


class TenantGroupFilter(admin.SimpleListFilter):
    """
    Фильтр по группе контрагентов в кабинетах арендаторов.
    Использует параметр group_id (также читается в TenantAdmin.get_queryset).
    """
    title = "Группа контрагентов"
    parameter_name = "group_id"

    def lookups(self, request, model_admin):
        qs = Gr.objects.filter(counterparty__tenant__isnull=False).distinct()
        return [(g.pk, g.name) for g in qs]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(counterparty__gr_id=self.value())
        return queryset
