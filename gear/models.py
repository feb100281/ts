from django.db import models

# Create your models here.
class SegmentsSales(models.Model):
    class Meta:
        managed = False
        verbose_name = "Сегментный анализ"
        verbose_name_plural = "Сегментный анализ"