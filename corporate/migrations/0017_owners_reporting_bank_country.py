from django.db import migrations, models

from utils.choises import COUNTRY_CHOICES, CURRENCY_CHOISE


class Migration(migrations.Migration):

    dependencies = [
        ("corporate", "0016_coafn_conditionscoa"),
    ]

    operations = [
        migrations.AddField(
            model_name="owners",
            name="country",
            field=models.CharField(choices=COUNTRY_CHOICES, default="RU", max_length=2, verbose_name="Страна"),
        ),
        migrations.AddField(
            model_name="owners",
            name="currency",
            field=models.CharField(choices=CURRENCY_CHOISE, default="RUB", max_length=3, verbose_name="Валюта учёта"),
        ),
        migrations.AddField(
            model_name="owners",
            name="report_group",
            field=models.CharField(
                default="Трендсеттер РФ", max_length=100, verbose_name="Группа отчётности",
                help_text="Компании одной группы показываются в отчётах вместе",
            ),
        ),
        migrations.AddField(
            model_name="owners",
            name="in_reports",
            field=models.BooleanField(default=True, verbose_name="Показывать в отчётах"),
        ),
        migrations.AlterField(
            model_name="bank",
            name="bik",
            field=models.CharField(
                blank=True, max_length=9, null=True, unique=True, verbose_name="БИК",
                help_text="9 цифр, без пробелов. Для банков вне РФ не заполняется",
            ),
        ),
        migrations.AddField(
            model_name="bank",
            name="country",
            field=models.CharField(choices=COUNTRY_CHOICES, default="RU", max_length=2, verbose_name="Страна"),
        ),
        migrations.AddField(
            model_name="bank",
            name="code",
            field=models.CharField(
                blank=True, db_index=True, max_length=10, null=True, verbose_name="Код банка",
                help_text="Для банков вне РФ: код из номера счёта (Армения — первые 3 цифры)",
            ),
        ),
    ]
