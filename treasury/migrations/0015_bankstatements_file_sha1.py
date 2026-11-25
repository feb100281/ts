from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("treasury", "0014_cfdata_cp_name_ru_cpname"),
    ]

    operations = [
        migrations.AddField(
            model_name="bankstatements",
            name="file_sha1",
            field=models.CharField(blank=True, db_index=True, max_length=40, null=True, verbose_name="Отпечаток файла"),
        ),
    ]
