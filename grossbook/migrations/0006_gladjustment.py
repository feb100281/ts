from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("grossbook", "0005_vatadjustment"),
        ("contracts", "0022_conditions_vat_mode_by_payment"),
        ("corporate", "0016_coafn_conditionscoa"),
    ]

    operations = [
        migrations.CreateModel(
            name="GlAdjustment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("date", models.DateField(verbose_name="Дата")),
                ("amount", models.DecimalField(decimal_places=2, max_digits=14, verbose_name="Сумма, ₽")),
                ("comment", models.TextField(verbose_name="Описание операции")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Создано")),
                ("owner", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="corporate.owners", verbose_name="Компания")),
                ("dt_acc", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="+", to="corporate.coa", verbose_name="Дт: счёт")),
                ("dt_contract", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="+", to="contracts.contracts", verbose_name="Дт: договор")),
                ("dt_subconto", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="+", to="corporate.cfitems", verbose_name="Дт: статья")),
                ("cr_acc", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="+", to="corporate.coa", verbose_name="Кт: счёт")),
                ("cr_contract", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="+", to="contracts.contracts", verbose_name="Кт: договор")),
                ("cr_subconto", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="+", to="corporate.cfitems", verbose_name="Кт: статья")),
            ],
            options={
                "verbose_name": "Корректировка GL",
                "verbose_name_plural": "Корректировки GL",
                "ordering": ("-date", "-id"),
            },
        ),
    ]
