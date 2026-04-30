from django.db import models

from django.db import models
from django.core.validators import FileExtensionValidator


class Lot(models.Model):
    name = models.CharField(
        max_length=100,
        verbose_name='Название лота',
        unique=True
    )
    description = models.TextField(verbose_name='Описание лота')

    class Meta:
        verbose_name = "Лот"
        verbose_name_plural = "Лоты"

    def __str__(self):
        return f"Лот {self.name}"


class Delivery(models.Model):
    lot = models.ForeignKey(
        Lot,
        verbose_name='Лот',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    date = models.DateField(verbose_name='Дата поставки')
    number = models.CharField(
        max_length=100,
        verbose_name='Номер поставки',
        unique=True
    )
    file = models.FileField(
        verbose_name='CSV-упаковочный файл',
        upload_to='deliveries/csv/',
        validators=[FileExtensionValidator(allowed_extensions=['csv'])]
    )
    
    description = models.TextField(verbose_name='Описание поставки', help_text='Короткое описание')

    class Meta:
        verbose_name = "Поставка"
        verbose_name_plural = "Поставки"

    def __str__(self):
        return f"Поставка {self.number} от {self.date:%d.%m.%Y} ({self.lot or 'без лота'})"
    
    