from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("sales", "0013_retailsale_lengths"),
    ]

    operations = [
        migrations.AddField(
            model_name="retailsale",
            name="source_sha1",
            field=models.CharField(blank=True, db_index=True, default="", max_length=40, verbose_name="Отпечаток файла"),
        ),
    ]
