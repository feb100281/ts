from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("treasury", "0011_cfdata_source_cr_cfdata_source_dt_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="cfdata",
            name="temp_ru",
            field=models.TextField(blank=True, null=True, verbose_name="Назначение (перевод)"),
        ),
        migrations.AddField(
            model_name="cfdata",
            name="op_type",
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name="Тип операции банка"),
        ),
        migrations.AddField(
            model_name="cfdata",
            name="dt_eq",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True, verbose_name="Дт в валюте учёта"),
        ),
        migrations.AddField(
            model_name="cfdata",
            name="cr_eq",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True, verbose_name="Кр в валюте учёта"),
        ),
        migrations.AddField(
            model_name="cfdata",
            name="row_key",
            field=models.CharField(blank=True, db_index=True, max_length=40, null=True, verbose_name="Ключ операции"),
        ),
        migrations.AddField(
            model_name="cfdata",
            name="hint",
            field=models.CharField(blank=True, db_index=True, max_length=100, null=True, verbose_name="Разметка",
                                   help_text="Ручная разметка из файла выписки или по похожим операциям"),
        ),
        migrations.AddField(
            model_name="cfdata",
            name="hint_auto",
            field=models.BooleanField(default=False, verbose_name="Разметка автоматически"),
        ),
    ]
