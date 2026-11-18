"""Индекс (договор, дата): обновление gl.mv_accurals ищет операцию выписки по договору и дате для каждой проводки."""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("treasury", "0016_cfdata_hint_auto_db_default")]

    operations = [
        migrations.AddIndex(
            model_name="cfdata",
            index=models.Index(fields=["contract", "date"], name="cfdata_contract_date"),
        ),
    ]
