# inventories/models.py
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


def lot_file_upload_to(instance, filename):
    return f"lots/{instance.lot.id}/{filename}"


class LotFile(models.Model):
    lot = models.ForeignKey(
        Lot,
        on_delete=models.CASCADE,
        related_name="files",
        verbose_name="Лот"
    )
    file = models.FileField(
        upload_to=lot_file_upload_to,
        verbose_name="Файл"
    )
    name = models.CharField(
        max_length=255,
        verbose_name="Название файла",
        blank=True
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Файл лота"
        verbose_name_plural = "Файлы лота"

    def __str__(self):
        return self.name or self.file.name
    
    
def delivery_file_upload_to(instance, filename):
    return f"deliveries/{instance.delivery.id}/{filename}"


class DeliveryFile(models.Model):
    delivery = models.ForeignKey(
        Delivery,
        on_delete=models.CASCADE,
        related_name="files",
        verbose_name="Поставка"
    )
    file = models.FileField(
        upload_to=delivery_file_upload_to,
        verbose_name="Файл"
    )
    name = models.CharField(
        max_length=255,
        verbose_name="Название файла",
        blank=True
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Файл поставки"
        verbose_name_plural = "Файлы поставки"

    def __str__(self):
        return self.name or self.file.name
    