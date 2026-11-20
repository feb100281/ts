from django.db import migrations, models

CHANNELS = [("wb", "ВБ"), ("retail", "Розница"), ("none", "Не распределено")]


class Migration(migrations.Migration):

    dependencies = [
        ("cards", "0008_wodashboard"),
    ]

    operations = [
        migrations.AddField(
            model_name="upddocument",
            name="default_channel",
            field=models.CharField(
                choices=CHANNELS, default="wb", max_length=10,
                help_text="Для строк без своего канала. На склад WB идут только строки «ВБ».",
                verbose_name="Канал по умолчанию"),
        ),
        migrations.AddField(
            model_name="upddata",
            name="channel",
            field=models.CharField(
                blank=True, choices=CHANNELS, max_length=10, null=True,
                help_text="Пусто — канал по умолчанию из УПД", verbose_name="Канал"),
        ),
        migrations.AddField(
            model_name="upddata",
            name="shipped",
            field=models.BooleanField(blank=True, null=True, verbose_name="Отгружено"),
        ),
    ]
