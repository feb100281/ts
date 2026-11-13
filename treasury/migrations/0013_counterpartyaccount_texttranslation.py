import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("counterparties", "0001_initial"),
        ("treasury", "0012_cfdata_foreign_statements"),
    ]

    operations = [
        migrations.CreateModel(
            name="CounterpartyAccount",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("account", models.CharField(max_length=50, unique=True, verbose_name="Счёт контрагента")),
                ("comment", models.CharField(blank=True, max_length=255, null=True, verbose_name="Комментарий")),
                ("cp", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="bank_accounts",
                                         to="counterparties.counterparty", verbose_name="Контрагент")),
            ],
            options={"verbose_name": "Счёт контрагента", "verbose_name_plural": "Счета контрагентов"},
        ),
        migrations.CreateModel(
            name="TextTranslation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.CharField(max_length=40, unique=True, verbose_name="Ключ")),
                ("source", models.TextField(verbose_name="Шаблон (оригинал)")),
                ("translation", models.TextField(blank=True, null=True, verbose_name="Перевод",
                                                 help_text="Числа обозначены # — в том же порядке, что в оригинале")),
                ("is_checked", models.BooleanField(default=False, verbose_name="Проверен")),
                ("hits", models.PositiveIntegerField(default=0, verbose_name="Встречается, строк")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Добавлен")),
            ],
            options={"verbose_name": "Перевод назначения", "verbose_name_plural": "Словарь переводов", "ordering": ("-hits",)},
        ),
    ]
