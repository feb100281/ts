"""Значение по умолчанию для hint_auto в самой базе: загрузчик выписок РФ вставляет строки SQL-запросом без этой колонки."""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("treasury", "0015_bankstatements_file_sha1")]

    operations = [
        migrations.AlterField(
            model_name="cfdata",
            name="hint_auto",
            field=models.BooleanField(db_default=False, default=False, verbose_name="Разметка автоматически"),
        ),
    ]
