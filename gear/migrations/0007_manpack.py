from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gear', '0006_exports'),
    ]

    operations = [
        migrations.CreateModel(
            name='ManPack',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
            options={
                'verbose_name': 'Управленческий пакет',
                'verbose_name_plural': 'Управленческий пакет',
                'managed': False,
            },
        ),
    ]
