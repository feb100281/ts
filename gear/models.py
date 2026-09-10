# gear/models.py
from django.db import models

# Заглушка для сегментного анализа.
class SegmentsSales(models.Model):
    class Meta:
        managed = False
        verbose_name = "Сегментный анализ"
        verbose_name_plural = "Сегментный анализ"


# Заглушка для анализа продаж по периодам.
class DailySales(models.Model):
    class Meta:
        managed = False
        verbose_name = "Продажи за период"
        verbose_name_plural = "Продажи за период"

class CostsControl(models.Model):
    class Meta:
        managed = False
        verbose_name = "Контроль закупочных цен"
        verbose_name_plural = "Контроль закупочных цен"
        
        
class Stats(models.Model):
    class Meta:
        managed = False
        verbose_name = "Статистика и прочее"
        verbose_name_plural = "Статистика и прочее"
        
        

class Loans(models.Model):
    class Meta:
        managed = False
        verbose_name = "Займы и кредиты"
        verbose_name_plural = "Займы и кредиты"
