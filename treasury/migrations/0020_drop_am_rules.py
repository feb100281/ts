from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("treasury", "0019_am_resolver")]

    operations = [
        migrations.DeleteModel(name="AmRule"),
        migrations.DeleteModel(name="AmResolver"),
        migrations.AlterField(model_name="ammode", name="on",
                              field=models.BooleanField(default=False, verbose_name="Новая разноска по карточкам договоров")),
    ]
