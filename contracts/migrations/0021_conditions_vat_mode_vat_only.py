from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contracts', '0020_alter_accuralfn_options_alter_contracts_bs_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='conditions',
            name='vat_mode',
            field=models.CharField(
                choices=[('included', 'НДС включён'), ('excluded', 'НДС сверху'),
                         ('exempt', 'Без НДС / не облагается'), ('unknown', 'Не задано'),
                         ('vat_only', 'Только НДС (вся сумма — НДС)')],
                default='unknown', max_length=20, verbose_name='Режим НДС'),
        ),
    ]
