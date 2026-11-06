from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gear', '0005_loans'),
    ]

    operations = [
        migrations.CreateModel(
            name='Exports',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
            options={
                'verbose_name': 'Выгрузки из меню «Экспорт»',
                'verbose_name_plural': 'Выгрузки из меню «Экспорт»',
                'permissions': [
                    ('export_gl', 'Выгрузка: главная книга (GL)'),
                    ('export_arap', 'Выгрузка: дебиторы / кредиторы (ARAP)'),
                    ('export_contracts_check', 'Выгрузка: проверка договоров на списание в PL'),
                    ('export_manpack', 'Выгрузка: Management Pack'),
                    ('export_management_pack', 'Выгрузка: управленческий пакет (P&L + CF) и csv к нему'),
                    ('export_stocks', 'Выгрузка: остатки на складах'),
                    ('export_budget_analysis', 'Выгрузка: контроль выручки'),
                ],
                'managed': False,
                'default_permissions': (),
            },
        ),
    ]
