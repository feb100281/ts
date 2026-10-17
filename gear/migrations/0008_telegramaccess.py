from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gear', '0007_manpack'),
    ]

    operations = [
        migrations.CreateModel(
            name='TelegramAccess',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tg_id', models.BigIntegerField(verbose_name='Telegram ID')),
                ('bot', models.CharField(choices=[('sales', 'Продажи'), ('finance', 'Финансы')], max_length=16, verbose_name='Помощник')),
                ('full_name', models.CharField(blank=True, max_length=255, verbose_name='Имя в Telegram')),
                ('username', models.CharField(blank=True, max_length=255, verbose_name='Ник')),
                ('is_allowed', models.BooleanField(default=False, verbose_name='Доступ разрешён')),
                ('comment', models.CharField(blank=True, max_length=255, verbose_name='Кто это (для себя)')),
                ('requests', models.PositiveIntegerField(default=0, verbose_name='Вопросов')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Первое обращение')),
                ('last_seen', models.DateTimeField(blank=True, null=True, verbose_name='Последнее обращение')),
            ],
            options={
                'verbose_name': 'Доступ к помощнику в Telegram',
                'verbose_name_plural': 'Помощник в Telegram: доступ',
                'ordering': ('is_allowed', '-created_at'),
                'unique_together': {('tg_id', 'bot')},
            },
        ),
    ]
