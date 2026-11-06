from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contracts', '0021_conditions_vat_mode_vat_only'),
    ]

    operations = [
        migrations.AlterField(
            model_name='conditions',
            name='vat_mode',
            field=models.CharField(
                choices=[('included', 'НДС включён'), ('excluded', 'НДС сверху'),
                         ('exempt', 'Без НДС / не облагается'), ('unknown', 'Не задано'),
                         ('vat_only', 'Только НДС (вся сумма — НДС)'),
                         ('by_payment', 'По назначению платежа (Cash Based)')],
                default='unknown', max_length=20, verbose_name='Режим НДС'),
        ),
    ]
