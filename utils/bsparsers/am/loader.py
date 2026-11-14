"""
Загрузка армянских выписок в treasury (BankStatements / CfData).

Отличия от загрузки выписок РФ:
  * операции не удаляются: повторная загрузка добавляет только новые (по row_key);
  * договоры, контрагенты и статьи подбираются только для новых строк и только среди договоров этой компании;
  * выписка с нарушенным сальдо не загружается.
"""

from __future__ import annotations

from collections import Counter
from datetime import timedelta
from pathlib import Path

from django.core.files import File
from django.db import connection, transaction
from django.db import models
from django.db.models import F

from corporate.models import Bank, BankAccount, Owners
from treasury.models import BankStatements, CfData, CounterpartyAccount, HintRule, TextTranslation

from .parser import Statement, StatementError, parse_statement
from .translate import fill, key_of, template

DOC_TYPE = "Банковская операция"
SEED = Path(__file__).with_name("translations_hy_ru.json")

NEW_OWNER = {
    "country": "AM", "currency": "AMD", "report_group": "Армения", "in_reports": True,
}


def sniff(path) -> bool:
    """Быстрая проверка: армянская выписка или нет (для BankStatements.save и am_load)."""
    import zipfile

    path = Path(path)
    marks = ["Տեղեկանք".encode(), "Ժամանակահատված".encode(), b"AccountStatementReport",
             "î»Õ»Ï³Ýù".encode(),                       # Տեղեկանք в ArmSCII-8, сохранённый как текст
             b"\xee\xbb\xd5\xbb\xcf\xb3\xdd\xf9"]          # то же в однобайтовой кодировке
    try:
        if path.suffix.lower() in (".xlsx", ".xlsm"):
            with zipfile.ZipFile(path) as z:            # текст внутри xlsx сжат — читаем части книги
                names = [n for n in z.namelist() if n in ("xl/workbook.xml", "xl/sharedStrings.xml")
                         or n.startswith("xl/worksheets/sheet1")]
                head = b"".join(z.read(n)[:400_000] for n in names)
        else:
            head = path.read_bytes()[:400_000]
            if b"<Workbook" not in head:
                return False
    except (OSError, zipfile.BadZipFile):
        return False
    return any(m in head for m in marks)


# ============================================================
# Справочники
# ============================================================

def get_owner(st: Statement, log) -> Owners:
    owner = Owners.objects.filter(inn=st.owner_tax_id).first() if st.owner_tax_id else None
    if owner:
        return owner
    if not st.owner_tax_id:
        raise StatementError("в выписке нет ИНН (ՀՎՀՀ) владельца счёта")
    owner = Owners.objects.create(name=f"{st.owner_name or 'Компания'} (Армения)", inn=st.owner_tax_id, **NEW_OWNER)
    log(f"  + новая компания: {owner.name}, ИНН {owner.inn} — проверьте карточку")
    return owner


def get_account(st: Statement, owner: Owners, log) -> BankAccount:
    ba = BankAccount.objects.select_related("corporate").filter(account=st.account).first()
    if ba:
        if ba.corporate_id != owner.id:
            raise StatementError(f"счёт {st.account} заведён на другую компанию: {ba.corporate}")
        return ba
    code = st.account[:3]
    bank = Bank.objects.filter(code=code, country="AM").first()
    if bank is None:
        bank = Bank.objects.create(name=st.bank or f"Банк {code}", code=code, country="AM")
        log(f"  + новый банк: {bank.name} (код {code})")
    ba = BankAccount.objects.create(corporate=owner, bank=bank, account=st.account,
                                    currency=st.currency or "AMD", is_active=True)
    log(f"  + новый счёт: {ba}")
    return ba


_seed = None


def seed() -> dict[str, str]:
    """Начальный словарь переводов (шаблон → перевод)."""
    global _seed
    if _seed is None:
        import json
        _seed = json.loads(SEED.read_text(encoding="utf-8")) if SEED.exists() else {}
    return _seed


def translations(texts: list[str]) -> dict[str, str | None]:
    """Перевод для каждого текста; новые шаблоны добавляются в словарь без перевода."""
    tpls = {t: template(t) for t in set(texts)}
    keys = {t: key_of(tpl) for t, (tpl, _) in tpls.items()}
    known = {x.key: x for x in TextTranslation.objects.filter(key__in=set(keys.values()))}
    hits = Counter(keys[t] for t in texts)
    new = {}
    for t, (tpl, _) in tpls.items():
        k = keys[t]
        if k not in known and k not in new:
            new[k] = TextTranslation(key=k, source=tpl, hits=0, translation=seed().get(tpl))
    TextTranslation.objects.bulk_create(new.values(), ignore_conflicts=True)
    for k, n in hits.items():
        TextTranslation.objects.filter(key=k).update(hits=F("hits") + n)
    known = {x.key: x for x in TextTranslation.objects.filter(key__in=set(keys.values()))}
    out = {}
    for t, (tpl, nums) in tpls.items():
        tr = known[keys[t]].translation
        out[t] = fill(tr, nums) if tr else None
    return out


# ============================================================
# Авторазноска новых строк
# ============================================================

AUTO_SQL = [
    ("договоры по назначению", """
        WITH m AS (
            SELECT DISTINCT ON (d.id) d.id AS cf_id, c.id AS contract_id
            FROM treasury_cfdata d
            JOIN contracts_contracts c
              ON c.owner_id = d.owner_id AND c.regex IS NOT NULL AND c.regex <> '' AND d.temp ~* c.regex
            WHERE d.id = ANY(%(ids)s) AND d.contract_id IS NULL
            ORDER BY d.id, length(c.regex) DESC, c.id
        )
        UPDATE treasury_cfdata d SET contract_id = m.contract_id FROM m WHERE d.id = m.cf_id
    """),
    ("договоры по контрагенту", """
        UPDATE treasury_cfdata d SET contract_id = r.contract_id
        FROM treasury_contractsrexex r
        JOIN contracts_contracts c ON c.id = r.contract_id
        WHERE d.id = ANY(%(ids)s) AND d.contract_id IS NULL AND d.cp_id = r.cp_id
          AND c.owner_id = d.owner_id AND d.temp ~* r.regex
    """),
    ("контрагент по договору", """
        UPDATE treasury_cfdata d SET cp_final_id = c.cp_id
        FROM contracts_contracts c
        WHERE d.id = ANY(%(ids)s) AND d.contract_id = c.id AND d.cp_final_id IS NULL
    """),
    ("статьи", """
        WITH m AS (
            SELECT DISTINCT ON (d.id) d.id AS cf_id,
                   CASE WHEN d.dt = 0 THEN t.defaultcfcr_id ELSE t.defaultcfdt_id END AS cf_item
            FROM treasury_cfdata d
            JOIN contracts_cfitemauto t ON t.contract_id = d.contract_id AND d.temp ~* t.regex
            WHERE d.id = ANY(%(ids)s) AND d.cfitem_id IS NULL
            ORDER BY d.id, length(t.regex) DESC, t.id
        )
        UPDATE treasury_cfdata d SET cfitem_id = m.cf_item FROM m WHERE d.id = m.cf_id AND m.cf_item IS NOT NULL
    """),
    ("разметка по похожим операциям", """
        WITH stat AS (
            SELECT owner_id, op_type, (dt > 0) AS incoming, hint, count(*) AS n
            FROM treasury_cfdata
            WHERE owner_id = %(owner)s AND hint <> '' AND NOT hint_auto AND op_type IS NOT NULL
            GROUP BY 1, 2, 3, 4
        ), best AS (
            SELECT *, sum(n) OVER w AS total, row_number() OVER (w ORDER BY n DESC) AS rn
            FROM stat WINDOW w AS (PARTITION BY owner_id, op_type, incoming)
        )
        UPDATE treasury_cfdata d SET hint = b.hint, hint_auto = TRUE
        FROM best b
        WHERE d.id = ANY(%(ids)s) AND coalesce(d.hint, '') = ''
          AND b.owner_id = d.owner_id AND b.op_type = d.op_type AND b.incoming = (d.dt > 0)
          AND b.rn = 1 AND b.n >= 3 AND b.n >= 0.9 * b.total
    """),
    ("статьи по разметке", """
        UPDATE treasury_cfdata d
        SET cfitem_id = CASE WHEN d.dt > 0 THEN r.cfitem_dt_id ELSE r.cfitem_cr_id END
        FROM treasury_hintrule r
        WHERE d.id = ANY(%(ids)s) AND d.cfitem_id IS NULL AND d.hint = r.hint
          AND (CASE WHEN d.dt > 0 THEN r.cfitem_dt_id ELSE r.cfitem_cr_id END) IS NOT NULL
    """),
]


def auto_assign(ids: list[int], owner_id: int, log):
    if not ids:
        return
    with connection.cursor() as cur:
        for title, sql in AUTO_SQL:
            cur.execute(sql, {"ids": ids, "owner": owner_id})
            log(f"  {title}: {cur.rowcount}")


def reassign(owner_id: int, log=print) -> None:
    """Повторная авторазноска по всем операциям компании, где что-то не заполнено. Заполненное не меняется."""
    ids = list(CfData.objects.filter(owner_id=owner_id)
               .filter(models.Q(cfitem__isnull=True) | models.Q(contract__isnull=True) | models.Q(hint__isnull=True)
                       | models.Q(hint=""))
               .values_list("id", flat=True))
    log(f"Повторная разноска незаполненных операций: {len(ids)}")
    with transaction.atomic():
        auto_assign(ids, owner_id, log)


# ============================================================
# Загрузка
# ============================================================

def check_chain(ba: BankAccount, st: Statement, log) -> list[str]:
    """Сверка с соседними выписками по счёту: остатки и разрывы."""
    warns = []
    prev = (BankStatements.objects.filter(ba=ba, finish__lt=st.start)
            .exclude(start=st.start, finish=st.finish).order_by("-finish").first())
    if prev:
        if prev.finish != st.start - timedelta(days=1):
            warns.append(f"разрыв: нет выписок с {prev.finish + timedelta(days=1)} по {st.start - timedelta(days=1)}")
        elif prev.eb is not None and prev.eb != st.bb:
            warns.append(f"вход {st.bb:,} ≠ исход предыдущей выписки {prev.eb:,} (разница {st.bb - prev.eb:,})")
    nxt = (BankStatements.objects.filter(ba=ba, start=st.finish + timedelta(days=1)).first())
    if nxt and nxt.bb is not None and nxt.bb != st.eb:
        warns.append(f"исход {st.eb:,} ≠ вход следующей выписки {nxt.bb:,}")
    for w in warns:
        log(f"  ! {w}")
    return warns


def load_statement(path, log=print, bs: BankStatements | None = None) -> dict:
    path = Path(path)
    st = parse_statement(path)
    log(f"{st.bank} {st.currency} {st.account}: {st.start:%d.%m.%Y}–{st.finish:%d.%m.%Y}, строк {len(st.rows)}")
    if st.balance_gap:
        raise StatementError(f"сальдо не сходится: вход {st.bb:,} + приход {st.total_dt:,} − расход "
                             f"{st.total_cr:,} ≠ исход {st.eb:,} (разница {st.balance_gap:,}) — выписка не загружена")

    with transaction.atomic():
        owner = get_owner(st, log)
        ba = get_account(st, owner, log)
        warns = check_chain(ba, st, log)

        if bs is None:
            bs = BankStatements.objects.filter(ba=ba, start=st.start, finish=st.finish).first()
        if bs is None:
            bs = BankStatements(owner=owner, ba=ba, start=st.start, finish=st.finish, bb=st.bb, eb=st.eb)
            with path.open("rb") as f:
                bs.file.save(path.name, File(f), save=False)
            bs.save()
        else:
            BankStatements.objects.filter(pk=bs.pk).update(owner=owner, ba=ba, start=st.start, finish=st.finish,
                                                           bb=st.bb, eb=st.eb)

        keys = [r.key for r in st.rows]
        have = set(CfData.objects.filter(ba=ba, row_key__in=keys).values_list("row_key", flat=True))
        new_rows = [r for r in st.rows if r.key not in have]

        ours = set(BankAccount.objects.values_list("account", flat=True))
        cp_map = dict(CounterpartyAccount.objects.filter(
            account__in={r.cp_account for r in new_rows}).values_list("account", "cp_id"))
        tr = translations([r.purpose for r in new_rows])
        used = set(CfData.objects.filter(bs=bs).values_list("doc_numner", "date", "dt", "cr"))

        objs = []
        for r in new_rows:
            doc = r.doc_number or "б/н"
            n = 1
            while (doc, r.date, r.dt, r.cr) in used:          # уникальность в пределах выписки
                n += 1
                doc = f"{r.doc_number}/{n}"
            used.add((doc, r.date, r.dt, r.cr))
            incoming = r.dt > 0
            objs.append(CfData(
                bs=bs, owner=owner, ba=ba, doc_type=DOC_TYPE, doc_numner=doc,
                doc_date=r.date.strftime("%d.%m.%Y"), date=r.date, dt=r.dt, cr=r.cr,
                source_dt=r.dt, source_cr=r.cr, dt_eq=r.dt_eq, cr_eq=r.cr_eq,
                temp=r.purpose, temp_ru=tr.get(r.purpose), op_type=r.op_type, cp_bs_name=r.cp_name,
                payer_account=r.cp_account if incoming else st.account,
                reciver_account=st.account if incoming else r.cp_account,
                intercompany=r.cp_account in ours and r.cp_account != st.account, cp_id=cp_map.get(r.cp_account), row_key=r.key,
                hint=r.hint or None,
            ))
        HintRule.objects.bulk_create([HintRule(hint=h) for h in {o.hint for o in objs if o.hint}],
                                     ignore_conflicts=True)            # новые метки — в справочник
        created = CfData.objects.bulk_create(objs, batch_size=500)
        ids = [o.pk for o in created if o.pk]
        if len(ids) != len(created):
            ids = list(CfData.objects.filter(ba=ba, row_key__in=[o.row_key for o in objs]).values_list("id", flat=True))
        auto_assign(ids, owner.id, log)

    no_tr = sum(1 for o in objs if not o.temp_ru)
    log(f"  новых операций: {len(objs)}, уже были: {len(have)}, без перевода: {no_tr}")
    return {"bs_id": bs.pk, "owner_id": owner.id, "new": len(objs), "existing": len(have), "warnings": warns,
            "account": st.account, "period": (st.start, st.finish)}
