from django.db import models
from counterparties.models import Counterparty
from contracts.models import Contracts


class WbCardRaw(models.Model):

    nm_id = models.BigIntegerField(primary_key=True)
    payload = models.JSONField()
    loaded_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'wb_cards_raw'

class WbSizes(models.Model):
    chrt_id = models.BigIntegerField(primary_key=True)
    nm = models.ForeignKey(
        WbCardRaw,
        on_delete=models.PROTECT,
        db_column='nm_id',
        related_name='sizes'
    )
    tech_size = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )
    class Meta:
        db_table = 'wb_sizes'


class WbBarcodes(models.Model):
    id = models.BigAutoField(primary_key=True)
    barcode = models.CharField(max_length=100)
    chrt = models.ForeignKey(
        WbSizes,
        on_delete=models.PROTECT,
        db_column='chrt_id',
        related_name='barcodes'
    )
    class Meta:
        db_table = 'wb_barcodes'
        constraints = [
            models.UniqueConstraint(
                fields=['barcode', 'chrt'],
                name='wb_barcode_chrt_unique'
            )
        ]
        
        
# Пилим модель для ЛОТОВ

class Lot(models.Model):

    name = models.CharField(
        max_length=100,
        verbose_name='Название лота',
        unique=True
    )

    description = models.TextField(
        verbose_name='Описание лота',
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Лот"
        verbose_name_plural = "Лоты"

    def __str__(self):
        return self.name
    
# Пилим модель для файлов лотов

def lot_file_upload_to(instance, filename):
    return f"lots/{instance.lot_id}/{filename}"

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

    uploaded_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        verbose_name = "Файл лота"
        verbose_name_plural = "Файлы лота"

    def __str__(self):
        return self.name or self.file.name

# Пилим модель c УПД

class UpdDocument(models.Model):

    lot = models.ForeignKey(
        Lot,
        on_delete=models.CASCADE,
        related_name='upd_documents',
        verbose_name='Лот',
        null=True, blank=True
    )
    counterparty = models.ForeignKey(
        Counterparty,
        on_delete=models.PROTECT,
        related_name='upd_documents',
        verbose_name='Поставщик',
        null=True, blank=True
    )
    contract = models.ForeignKey(
        Contracts,
        on_delete=models.PROTECT,
        related_name='upd_documents',
        verbose_name='Договор',
        null=True,
        blank=True,
    )

    number = models.CharField(
        max_length=100,
        verbose_name='Номер УПД'
    )

    date = models.DateField(
        verbose_name='Дата УПД'
    )

    comment = models.TextField(
        blank=True
    )
    
    class Meta:       

        verbose_name = 'УПД'
        verbose_name_plural = 'УПД'

    def __str__(self):
        return f'{self.number} от {self.date}'

def upd_file_upload_to(instance, filename):
    return f"upd/{instance.upd_document_id}/{filename}"


class UpdDocumentFile(models.Model):

    upd_document = models.ForeignKey(
        UpdDocument,
        on_delete=models.CASCADE,
        related_name='files',
        verbose_name='УПД'
    )

    file = models.FileField(
        upload_to=upd_file_upload_to,
        verbose_name='Файл'
    )

    name = models.CharField(
        max_length=255,
        verbose_name='Название файла',
        blank=True
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        verbose_name = 'Файл УПД'
        verbose_name_plural = 'Файлы УПД'

    def __str__(self):
        return self.name or self.file.name

from django.contrib.postgres.fields import ArrayField
from django.db import models


class WbProduct(models.Model):

    card = models.OneToOneField(
        WbCardRaw,
        on_delete=models.CASCADE,
        primary_key=True,
        db_column='nm_id',
        related_name='product',
        verbose_name='Карточка WB'
    )

    nm_pid = models.BigIntegerField(null=True, blank=True)
    sa_name = models.CharField(max_length=255, null=True, blank=True)
    sa_pid = models.CharField(max_length=255, null=True, blank=True)

    title = models.TextField(null=True, blank=True)
    alternative_name = models.TextField(null=True, blank=True)

    subject_name = models.CharField(max_length=255, null=True, blank=True)
    brand = models.CharField(max_length=255, null=True, blank=True)
    subject_id = models.BigIntegerField(null=True, blank=True)

    has_parent = models.BooleanField(default=False)

    vat_rate = models.FloatField(null=True, blank=True)
    discount_vat = models.BooleanField(default=False)

    tnved = models.CharField(max_length=100, null=True, blank=True)
    gender = models.CharField(max_length=100, null=True, blank=True)
    origin_country = models.CharField(max_length=100, null=True, blank=True)

    photo_hq = models.URLField(max_length=1000, null=True, blank=True)

    cert_end_date = models.DateField(null=True, blank=True)

    wb_created_at = models.DateTimeField(null=True, blank=True)
    wb_updated_at = models.DateTimeField(null=True, blank=True)

    available_sizes = ArrayField(
        models.CharField(max_length=100),
        default=list,
        blank=True
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'wb_products'
        verbose_name = 'Товар WB'
        verbose_name_plural = 'Товары WB'

    def __str__(self):
        return f'{self.card_id} — {self.sa_name or self.title}'
