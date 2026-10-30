from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('grossbook', '0004_loanadjustment'),
    ]

    operations = [
        migrations.CreateModel(
            name='VatAdjustment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(verbose_name='Дата')),
                ('kind', models.CharField(choices=[('writeoff', 'НДС списан в расходы (не принят к вычету)'), ('balance', 'Корректировка сальдо НДС (без P&L)')], default='writeoff', max_length=20, verbose_name='Вид')),
                ('amount', models.DecimalField(decimal_places=2, help_text='Списание — положительной суммой. Корректировка сальдо — со знаком: плюс увеличивает переплату, минус уменьшает.', max_digits=14, verbose_name='Сумма, ₽')),
                ('comment', models.TextField(blank=True, verbose_name='Комментарий')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создано')),
            ],
            options={
                'verbose_name': 'Корректировка НДС',
                'verbose_name_plural': 'Корректировки НДС',
                'ordering': ('-date',),
            },
        ),
    ]
