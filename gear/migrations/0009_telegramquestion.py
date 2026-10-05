import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gear', '0008_telegramaccess'),
    ]

    operations = [
        migrations.CreateModel(
            name='TelegramQuestion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('bot', models.CharField(choices=[('sales', 'Продажи'), ('finance', 'Финансы')], max_length=16, verbose_name='Помощник')),
                ('asked_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Когда')),
                ('text', models.TextField(verbose_name='Вопрос')),
                ('seconds', models.FloatField(default=0, verbose_name='Ответ, с')),
                ('cost_usd', models.FloatField(blank=True, null=True, verbose_name='Стоимость, $')),
                ('has_file', models.BooleanField(default=False, verbose_name='Excel')),
                ('is_error', models.BooleanField(default=False, verbose_name='Ошибка')),
                ('access', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='questions', to='gear.telegramaccess', verbose_name='Кто')),
            ],
            options={
                'verbose_name': 'Вопрос помощнику в Telegram',
                'verbose_name_plural': 'Помощник в Telegram: вопросы',
                'ordering': ('-asked_at',),
            },
        ),
    ]
