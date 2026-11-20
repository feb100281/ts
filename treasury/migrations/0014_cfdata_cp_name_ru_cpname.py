from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("treasury", "0013_counterpartyaccount_texttranslation"),
    ]

    operations = [
        migrations.AddField(
            model_name="cfdata",
            name="cp_name_ru",
            field=models.CharField(blank=True, max_length=250, null=True, verbose_name="Контрагент по-русски",
                                   help_text="Из справочника «Названия контрагентов»"),
        ),
        migrations.CreateModel(
            name="CpName",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source", models.CharField(max_length=250, unique=True, verbose_name="В выписке")),
                ("name_ru", models.CharField(blank=True, default="", max_length=250, verbose_name="По-русски")),
                ("is_checked", models.BooleanField(default=False, verbose_name="Проверено")),
                ("hits", models.PositiveIntegerField(default=0, verbose_name="Операций")),
            ],
            options={"verbose_name": "Название контрагента", "verbose_name_plural": "Названия контрагентов",
                     "ordering": ("-hits",)},
        ),
    ]
