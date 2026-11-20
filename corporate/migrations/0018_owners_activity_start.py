import datetime

from django.db import migrations, models


def armenia_start(apps, schema_editor):
    Owners = apps.get_model("corporate", "Owners")
    Owners.objects.filter(name__icontains="АРМЕН", activity_start__isnull=True).update(
        activity_start=datetime.date(2024, 12, 3))


class Migration(migrations.Migration):

    dependencies = [
        ("corporate", "0017_owners_reporting_bank_country"),
    ]

    operations = [
        migrations.AddField(
            model_name="owners",
            name="activity_start",
            field=models.DateField(blank=True, help_text="С этой даты проверяется полнота банковских выписок",
                                   null=True, verbose_name="Начало деятельности"),
        ),
        migrations.RunPython(armenia_start, migrations.RunPython.noop),
    ]
