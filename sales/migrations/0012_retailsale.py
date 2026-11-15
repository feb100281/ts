import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("corporate", "0017_owners_reporting_bank_country"),
        ("sales", "0011_alter_wbdocument_table"),
    ]

    operations = [
        migrations.CreateModel(
            name="RetailSale",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("kind", models.CharField(choices=[("sale", "Продажа"), ("return", "Возврат")], db_index=True, max_length=10, verbose_name="Вид")),
                ("period", models.DateField(db_index=True, verbose_name="Месяц")),
                ("doc_number", models.CharField(max_length=50, verbose_name="Документ")),
                ("doc_date", models.DateTimeField(db_index=True, verbose_name="Дата")),
                ("check_number", models.CharField(blank=True, default="", max_length=50, verbose_name="Чек продажи")),
                ("check_date", models.DateTimeField(blank=True, null=True, verbose_name="Дата чека продажи")),
                ("article_invoice", models.CharField(blank=True, default="", max_length=100, verbose_name="Артикул инвойс")),
                ("article", models.CharField(blank=True, db_index=True, default="", max_length=100, verbose_name="Артикул")),
                ("size", models.CharField(blank=True, default="", max_length=100, verbose_name="Размер")),
                ("barcode", models.CharField(blank=True, default="", max_length=50, verbose_name="Штрихкод")),
                ("name", models.CharField(blank=True, default="", max_length=500, verbose_name="Наименование")),
                ("qty", models.DecimalField(decimal_places=3, default=0, max_digits=14, verbose_name="Количество")),
                ("price", models.DecimalField(decimal_places=2, default=0, max_digits=16, verbose_name="Цена")),
                ("amount", models.DecimalField(decimal_places=2, default=0, max_digits=16, verbose_name="Сумма с НДС")),
                ("amount_novat", models.DecimalField(decimal_places=2, default=0, max_digits=16, verbose_name="Сумма без НДС")),
                ("cost_unit", models.DecimalField(decimal_places=2, default=0, max_digits=16, verbose_name="Себестоимость ед.")),
                ("cost_total", models.DecimalField(decimal_places=2, default=0, max_digits=16, verbose_name="Себестоимость")),
                ("disc_manual_pct", models.DecimalField(decimal_places=4, default=0, max_digits=9, verbose_name="Скидка ручная, %")),
                ("disc_manual_sum", models.DecimalField(decimal_places=2, default=0, max_digits=16, verbose_name="Скидка ручная")),
                ("disc_auto_pct", models.DecimalField(decimal_places=4, default=0, max_digits=9, verbose_name="Скидка авто, %")),
                ("disc_auto_sum", models.DecimalField(decimal_places=2, default=0, max_digits=16, verbose_name="Скидка авто")),
                ("bonus_sum", models.DecimalField(decimal_places=2, default=0, max_digits=16, verbose_name="Бонусы")),
                ("row_key", models.CharField(max_length=40, verbose_name="Ключ строки")),
                ("source_file", models.CharField(blank=True, default="", max_length=255, verbose_name="Файл")),
                ("owner", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="corporate.owners", verbose_name="Компания")),
            ],
            options={
                "verbose_name": "Розничная продажа",
                "verbose_name_plural": "Розничные продажи",
                "indexes": [models.Index(fields=["owner", "period", "kind"], name="retailsale_owner_period_kind")],
                "constraints": [models.UniqueConstraint(fields=("owner", "row_key"), name="uniq_retailsale_owner_key")],
            },
        ),
    ]
