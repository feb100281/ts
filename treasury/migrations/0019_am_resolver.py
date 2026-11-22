"""Резолверы разноски зарубежных компаний и отметка ручной разноски."""
import django.db.models.deletion
from django.db import migrations, models


def seed_transit(apps, schema_editor):
    T = apps.get_model("treasury", "TransitAccount")
    for acc, note in (("16000001146200", "ВТБ-Армения, рублёвые переводы"),
                      ("2470059669470000", "Ардшинбанк, рублёвые переводы"),
                      ("2470001038351000", "Ардшинбанк, SWIFT")):
        T.objects.get_or_create(account=acc, defaults={"comment": note})


class Migration(migrations.Migration):

    dependencies = [
        ("contracts", "0022_conditions_vat_mode_by_payment"),
        ("corporate", "0018_owners_activity_start"),
        ("counterparties", "0001_initial"),
        ("treasury", "0018_counterpartyaccount_contract"),
    ]

    operations = [
        migrations.CreateModel(
            name="TransitAccount",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("account", models.CharField(max_length=50, unique=True, verbose_name="Счёт")),
                ("comment", models.CharField(blank=True, max_length=255, null=True, verbose_name="Банк / комментарий")),
            ],
            options={"verbose_name": "Транзитный счёт банка", "verbose_name_plural": "Транзитные счета банков"},
        ),
        migrations.RunPython(seed_transit, migrations.RunPython.noop),
        migrations.AddField(
            model_name="cfdata",
            name="manual",
            field=models.BooleanField(db_default=False, default=False, verbose_name="Разнесено руками",
                                      help_text="Контрагент, договор и статья заданы вручную — пересборка их не меняет"),
        ),
        migrations.CreateModel(
            name="AmResolver",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("comment", models.CharField(blank=True, max_length=255, null=True, verbose_name="Комментарий")),
                ("cp", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                                         related_name="am_resolvers", to="counterparties.counterparty",
                                         verbose_name="Контрагент",
                                         help_text="Пусто — общие правила для операций без контрагента")),
                ("owner", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="corporate.owners",
                                            verbose_name="Компания")),
            ],
            options={"verbose_name": "Правила разноски контрагента",
                     "verbose_name_plural": "Правила разноски (зарубежные компании)"},
        ),
        migrations.AddConstraint(
            model_name="amresolver",
            constraint=models.UniqueConstraint(fields=("owner", "cp"), name="uniq_am_resolver_owner_cp"),
        ),
        migrations.CreateModel(
            name="AmRule",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("order", models.PositiveSmallIntegerField(default=10, verbose_name="№")),
                ("text_regex", models.CharField(blank=True, default="", max_length=500, verbose_name="Назначение содержит",
                                                help_text="Слова через | , регистр не важен. Пусто — всё остальное")),
                ("hits", models.PositiveIntegerField(default=0, verbose_name="Строк")),
                ("contract", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="am_rules",
                                               to="contracts.contracts", verbose_name="Договор")),
                ("cf_item_dt", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                                                 related_name="am_rules_dt", to="corporate.cfitems",
                                                 verbose_name="Статья для поступлений")),
                ("cf_item_cr", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                                                 related_name="am_rules_cr", to="corporate.cfitems",
                                                 verbose_name="Статья для списаний")),
                ("resolver", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="rules",
                                               to="treasury.amresolver", verbose_name="Контрагент")),
            ],
            options={"verbose_name": "Правило", "verbose_name_plural": "Правила", "ordering": ["order", "id"]},
        ),
        migrations.CreateModel(
            name="AmMode",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("on", models.BooleanField(default=False, verbose_name="Разноска по «Правилам разноски»")),
                ("switched_at", models.DateTimeField(blank=True, null=True, verbose_name="Переключено")),
                ("owner", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="am_mode",
                                               to="corporate.owners", verbose_name="Компания")),
            ],
            options={"verbose_name": "Режим разноски", "verbose_name_plural": "Режим разноски"},
        ),
    ]
