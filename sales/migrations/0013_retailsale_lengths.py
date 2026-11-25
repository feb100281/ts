from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("sales", "0012_retailsale"),
    ]

    operations = [
        migrations.AlterField(
            model_name="retailsale",
            name="barcode",
            field=models.CharField(blank=True, default="", max_length=255, verbose_name="Штрихкод / код маркировки"),
        ),
        migrations.AlterField(
            model_name="retailsale",
            name="doc_number",
            field=models.CharField(max_length=100, verbose_name="Документ"),
        ),
        migrations.AlterField(
            model_name="retailsale",
            name="check_number",
            field=models.CharField(blank=True, default="", max_length=100, verbose_name="Чек продажи"),
        ),
    ]
