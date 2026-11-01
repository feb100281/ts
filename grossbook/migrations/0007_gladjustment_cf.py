from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("grossbook", "0006_gladjustment"),
        ("corporate", "0016_coafn_conditionscoa"),
    ]

    operations = [
        migrations.AddField(
            model_name="gladjustment",
            name="cf",
            field=models.BooleanField(default=False, help_text="Перенести сумму из одной статьи Cash Flow в другую", verbose_name="Отразить в Cash Flow"),
        ),
        migrations.AddField(
            model_name="gladjustment",
            name="cf_from",
            field=models.ForeignKey(blank=True, help_text="Пусто — 122501 Удержания с продаж", null=True, on_delete=django.db.models.deletion.PROTECT, related_name="+", to="corporate.cfitems", verbose_name="Статья CF: откуда"),
        ),
        migrations.AddField(
            model_name="gladjustment",
            name="cf_to",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="+", to="corporate.cfitems", verbose_name="Статья CF: куда"),
        ),
        migrations.AddField(
            model_name="gladjustment",
            name="cf_acc",
            field=models.ForeignKey(blank=True, help_text="Пусто — 114001 Баланс WB", null=True, on_delete=django.db.models.deletion.PROTECT, related_name="+", to="corporate.coa", verbose_name="Счёт денег для CF"),
        ),
    ]
