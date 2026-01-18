# counterparties/services.py

from datetime import timedelta

from django.db.models import (
    Q,
    Count,
    Case,
    When,
    Value,
    CharField,
)
from django.db.models.functions import Substr
from django.utils import timezone
from .models import CounterpartyFinancialYear 
from .checko_client import finances_by_inn, CheckoError





# ---------------------------------------------------------------------------
#  КОНТРАГЕНТЫ: общая аналитика
# ---------------------------------------------------------------------------

def build_counterparty_stats(qs):
    """
    Принимает queryset Counterparty и возвращает dict с данными для дэшборда.
    Никакого request / render / шаблонов – только расчёты.
    """
    total = qs.count()

    # ---- Риски ----
    # логика ДОЛЖНА совпадать с CounterpartyRiskLevelFilter

    # 🔴 высокий риск: санкции / санкционный учредитель / непустой список стран
    high_q = (
        Q(risk_sanctions=True)
        | Q(risk_sanctioned_founder=True)
        | (
            Q(risk_sanctions_countries__isnull=False)
            & ~Q(risk_sanctions_countries__exact="")
        )
    )

    # 🟡 средний риск: нет high, но есть другие флаги
    mid_q = (
        Q(risk_illegal_fin=True)
        | Q(risk_mass_directors=True)
        | Q(risk_mass_founders=True)
        | Q(risk_disq_persons=True)
    )

    high_risk = qs.filter(high_q).distinct().count()
    mid_risk = qs.exclude(high_q).filter(mid_q).distinct().count()

    # 🟢 низкий риск: нет high и нет mid-флагов
    low_risk = qs.exclude(high_q).filter(
        risk_illegal_fin=False,
        risk_mass_directors=False,
        risk_mass_founders=False,
        risk_disq_persons=False,
    ).count()

    # ---- ФНС / Checko ----
    now = timezone.now()
    cutoff_recent = now - timedelta(days=90)
    cutoff_mid = now - timedelta(days=365)

    fns_never = qs.filter(checko_updated_at__isnull=True).count()
    fns_recent = qs.filter(checko_updated_at__gte=cutoff_recent).count()
    fns_mid = qs.filter(
        checko_updated_at__lt=cutoff_recent,
        checko_updated_at__gte=cutoff_mid,
    ).count()
    fns_old = qs.filter(checko_updated_at__lt=cutoff_mid).count()

    # ---- По группам ----
    by_group = (
        qs.values("gr__id", "gr__name")
        .annotate(cnt=Count("id"))
        .order_by("gr__name")
    )

    # ---- ТОП регионов ----
    by_region = (
        qs.values("region")
        .annotate(cnt=Count("id"))
        .order_by("-cnt", "region")[:10]
    )

    # ---- ОПФ по ОКОПФ ----
    by_opf_qs = (
        qs.filter(
            Q(okopf_code__isnull=False, okopf_code__gt="")
            | Q(okopf_name__isnull=False, okopf_name__gt="")
        )
        .values("okopf_code", "okopf_name")
        .annotate(cnt=Count("id"))
        .order_by("-cnt", "okopf_name", "okopf_code")
    )

    by_opf = []
    for row in by_opf_qs:
        code = (row["okopf_code"] or "").strip()
        name = (row["okopf_name"] or "").strip()
        label_name = name or code or "Без названия"

        if code:
            opf_key = code
        else:
            # тот же формат, что и в LegalFormFilter
            opf_key = f"name::{label_name}"

        row["opf_key"] = opf_key                # ключ для ссылки
        row["okopf_name_display"] = label_name  # запасной вариант для отображения
        by_opf.append(row)

    # ---- Сколько вообще без ОПФ (и кода, и названия нет) ----
    opf_missing_cnt = qs.filter(
        (Q(okopf_code__isnull=True) | Q(okopf_code__exact=""))
        & (Q(okopf_name__isnull=True) | Q(okopf_name__exact=""))
    ).count()

    # ---- ОКВЭД: топ по полным кодам ----
    by_okved = (
        qs.exclude(okved_code__isnull=True)
        .exclude(okved_code__exact="")
        .values("okved_code", "okved_name")
        .annotate(cnt=Count("id"))
        .order_by("-cnt", "okved_code")[:10]
    )

    return {
        "total": total,
        "high_risk": high_risk,
        "mid_risk": mid_risk,
        "low_risk": low_risk,
        "fns_never": fns_never,
        "fns_recent": fns_recent,
        "fns_mid": fns_mid,
        "fns_old": fns_old,
        "by_group": by_group,
        "by_region": by_region,
        "by_opf": by_opf,
        "opf_missing_cnt": opf_missing_cnt,
        "by_okved": by_okved,
    }
# ---------------------------------------------------------------------------
#  КОНТРАГЕНТЫ: аналитика по группе (GrAdmin.group_analytics)
# ---------------------------------------------------------------------------


def build_group_counterparty_stats(qs):
    """
    Принимает queryset Counterparty внутри конкретной группы
    и возвращает dict с данными для group_analytics.
    Логика соответствует GrAdmin.group_analytics.
    """
    total = qs.count()

    # ---- Риски ----
    high_risk = (
        qs.filter(risk_sanctions=True).count()
        + qs.filter(risk_sanctioned_founder=True).count()
    )

    mid_risk = (
        qs.filter(
            risk_sanctions=False,
            risk_sanctioned_founder=False,
        )
        .filter(risk_illegal_fin=True)
        .count()
        + qs.filter(
            risk_sanctions=False,
            risk_sanctioned_founder=False,
            risk_illegal_fin=False,
        )
        .filter(risk_mass_directors=True)
        .count()
        + qs.filter(
            risk_sanctions=False,
            risk_sanctioned_founder=False,
            risk_illegal_fin=False,
        )
        .filter(risk_mass_founders=True)
        .count()
        + qs.filter(
            risk_sanctions=False,
            risk_sanctioned_founder=False,
            risk_illegal_fin=False,
        )
        .filter(risk_disq_persons=True)
        .count()
    )

    low_risk = max(total - high_risk - mid_risk, 0)

    # ---- ФНС / Checko ----
    now = timezone.now()
    cutoff_recent = now - timedelta(days=90)
    cutoff_mid = now - timedelta(days=365)

    fns_never = qs.filter(checko_updated_at__isnull=True).count()
    fns_recent = qs.filter(checko_updated_at__gte=cutoff_recent).count()
    fns_mid = qs.filter(
        checko_updated_at__lt=cutoff_recent,
        checko_updated_at__gte=cutoff_mid,
    ).count()
    fns_old = qs.filter(checko_updated_at__lt=cutoff_mid).count()

    # ---- ТОП регионов внутри группы ----
    by_region = (
        qs.values("region")
        .annotate(cnt=Count("id"))
        .order_by("-cnt", "region")[:10]
    )

    # ---- ОПФ по fullname (грубая классификация) ----
    legal_form_case = Case(
        When(fullname__istartswith="ООО ", then=Value("ООО")),
        When(
            fullname__icontains="ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ",
            then=Value("ООО"),
        ),
        When(fullname__istartswith="ПАО ", then=Value("ПАО")),
        When(fullname__istartswith="АО ", then=Value("АО")),
        When(
            fullname__icontains="АКЦИОНЕРНОЕ ОБЩЕСТВО",
            then=Value("АО"),
        ),
        When(fullname__istartswith="ИП ", then=Value("ИП")),
        When(
            fullname__icontains="ИНДИВИДУАЛЬНЫЙ ПРЕДПРИНИМАТЕЛЬ",
            then=Value("ИП"),
        ),
        When(
            fullname__isnull=False,
            fullname__gt="",
            then=Value("Прочие юрлица"),
        ),
        default=Value("Физическое лицо"),
        output_field=CharField(),
    )

    by_opf = (
        qs.annotate(opf=legal_form_case)
        .values("opf")
        .annotate(cnt=Count("id"))
        .order_by("-cnt")
    )

    # ---- ОКВЭД внутри группы (по префиксу 2 цифры) ----
    by_okved = (
        qs.exclude(okved_code__isnull=True)
        .exclude(okved_code__exact="")
        .annotate(okved_prefix=Substr("okved_code", 1, 2))
        .values("okved_prefix", "okved_name")
        .annotate(cnt=Count("id"))
        .order_by("-cnt", "okved_prefix")[:10]
    )

    return {
        "total": total,
        "high_risk": high_risk,
        "mid_risk": mid_risk,
        "low_risk": low_risk,
        "fns_never": fns_never,
        "fns_recent": fns_recent,
        "fns_mid": fns_mid,
        "fns_old": fns_old,
        "by_region": by_region,
        "by_opf": by_opf,
        "by_okved": by_okved,
    }


# ---------------------------------------------------------------------------
#  КОНТРАГЕНТЫ: загрузка финансов по ИНН из Checko в CounterpartyFinancialYear
# ---------------------------------------------------------------------------

def _val_fin(fin_year: dict, code: str):
    """
    Достаём значение по коду строки отчётности (например, '2110', '2400').
    Поддерживает extended-формат, где значение может быть словарём.
    """
    v = fin_year.get(code)
    if isinstance(v, dict):
        # extended-формат: пытаемся найти числовое поле
        for k in ("СумОтч", "Итог", "Sum", "Value", "sum", "value"):
            if k in v and isinstance(v[k], (int, float)):
                return v[k]
        for vv in v.values():
            if isinstance(vv, (int, float)):
                return vv
        return None
    return v

def _val_fin_total(fin_year: dict, total_code: str, component_codes: tuple[str, ...]):
    """
    Возвращает значение агрегированной строки:
      - если есть total_code (например, 1400 / 1500) → берём его;
      - иначе суммируем дочерние строки (1410,1420… / 1510,1520…).
    """
    total = _val_fin(fin_year, total_code)
    if isinstance(total, (int, float)):
        return total

    parts = []
    for code in component_codes:
        v = _val_fin(fin_year, code)
        if isinstance(v, (int, float)):
            parts.append(v)

    if parts:
        return sum(parts)
    return None


def update_counterparty_financials(counterparty, years_limit: int = 3) -> int:
    """
    Тянет finances по ИНН через Checko и сохраняет последние N лет
    в CounterpartyFinancialYear.

    Возвращает: сколько лет удалось сохранить.
    """
    inn = (counterparty.tax_id or "").strip()
    if not inn:
        return 0

    # ВАЖНО: используем тот же ключ, что и в build_counterparty_payload
    fin_payload = finances_by_inn(inn, extended=True, key="SIwfo6CFilGM4fUX")

    # Обычно Checko отдаёт: {"meta": ..., "data": {"2021": {...}, "2020": {...}, ...}}
    raw_data = fin_payload.get("data")

    if isinstance(raw_data, dict) and any(str(k).isdigit() for k in raw_data.keys()):
        data = raw_data
    elif isinstance(fin_payload, dict) and any(str(k).isdigit() for k in fin_payload.keys()):
        # fallback, если вдруг годы лежат прямо в корне
        data = fin_payload
    else:
        return 0

    year_keys = sorted(
        [str(y) for y in data.keys() if str(y).isdigit()],
        key=lambda y: int(y),
        reverse=True,
    )

    saved = 0

    for year_str in year_keys[:years_limit]:
        fy = data.get(year_str) or {}
        if not isinstance(fy, dict):
            continue

        year = int(year_str)

        # Коды строк:
        # 2110 — Выручка, 2400 — Чистая прибыль, 1300 — Собств. капитал,
        # 1310 — Уставный капитал, 1520 — Кредиторская задолженность (краткосрочная),
        # 4100 — Операционный денежный поток
        revenue       = _val_fin(fy, "2110")
        net_profit    = _val_fin(fy, "2400")
        equity        = _val_fin(fy, "1300")
        share_capital = _val_fin(fy, "1310")
        payables      = _val_fin(fy, "1520")
        cf_operating  = _val_fin(fy, "4100")
        liabilities_long  = _val_fin_total(fy, "1400", ("1410", "1420", "1430", "1440", "1450"))
        liabilities_short = _val_fin_total(fy, "1500", ("1510", "1520", "1530", "1540", "1550"))


        CounterpartyFinancialYear.objects.update_or_create(
            counterparty=counterparty,
            year=year,
            defaults={
                "revenue":       revenue,
                "net_profit":    net_profit,
                "equity":        equity,
                "payables":      payables,
                "share_capital": share_capital,
                "cf_operating":  cf_operating,
                "liabilities_long":  liabilities_long,
                "liabilities_short": liabilities_short,
                "source":        "Checko",
            },
        )
        saved += 1

    return saved


# ---------------------------------------------------------------------------
#  ЛИЧНЫЕ КАБИНЕТЫ: аналитика и фильтрация
# ---------------------------------------------------------------------------


def build_tenant_stats(qs):
    """
    Принимает queryset Tenant и возвращает dict с данными для дэшборда.
    Никакого request / render / шаблонов – только расчёты.
    """
    total = qs.count()
    with_user = qs.filter(user__isnull=False).count()
    without_user = total - with_user

    now = timezone.now()
    cutoff_7 = now - timedelta(days=7)
    cutoff_30 = now - timedelta(days=30)

    login_7 = qs.filter(user__last_login__gte=cutoff_7).count()
    login_7_30 = qs.filter(
        user__last_login__lt=cutoff_7,
        user__last_login__gte=cutoff_30,
    ).count()
    login_old = qs.filter(user__last_login__lt=cutoff_30).count()
    login_never = qs.filter(
        user__isnull=False,
        user__last_login__isnull=True,
    ).count()

    users_total = (
        qs.filter(user__isnull=False)
        .values("user")
        .distinct()
        .count()
    )

    by_group = (
        qs.values("counterparty__gr__id", "counterparty__gr__name")
        .annotate(cnt=Count("id"))
        .order_by("counterparty__gr__name")
    )

    by_user = (
        qs.values(
            "user__id",
            "user__username",
            "user__first_name",
            "user__last_name",
        )
        .annotate(cnt=Count("id"))
        .order_by("-cnt", "user__username")
    )

    stale_tenants = (
        qs.filter(user__isnull=False)
        .order_by("user__last_login")[:10]
    )

    return {
        "total": total,
        "with_user": with_user,
        "without_user": without_user,
        "login_7": login_7,
        "login_7_30": login_7_30,
        "login_old": login_old,
        "login_never": login_never,
        "users_total": users_total,
        "by_group": by_group,
        "by_user": by_user,
        "stale_tenants": stale_tenants,
    }


def apply_tenant_filter(qs, tenant_filter: str | None, now=None):
    """
    Применяет URL-параметр tenant_filter к queryset Tenant.
    Используется в TenantAdmin.get_queryset, чтобы разгрузить admin.py.

    tenant_filter:
      - with_user
      - without_user
      - login_never
      - login_7
      - login_7_30
      - login_old
    """
    if not tenant_filter:
        return qs

    if now is None:
        now = timezone.now()

    cutoff_7 = now - timedelta(days=7)
    cutoff_30 = now - timedelta(days=30)

    if tenant_filter == "with_user":
        return qs.filter(user__isnull=False)

    if tenant_filter == "without_user":
        return qs.filter(user__isnull=True)

    if tenant_filter == "login_never":
        return qs.filter(user__isnull=False, user__last_login__isnull=True)

    if tenant_filter == "login_7":
        return qs.filter(user__last_login__gte=cutoff_7)

    if tenant_filter == "login_7_30":
        return qs.filter(
            user__last_login__lt=cutoff_7,
            user__last_login__gte=cutoff_30,
        )

    if tenant_filter == "login_old":
        return qs.filter(user__last_login__lt=cutoff_30)

    # неизвестный фильтр – возвращаем как есть
    return qs
