from django.db import models
from django.utils import timezone
from utils.choises import CURRENCY_CHOISE


#-----WACC-----#

class WACC(models.Model):
    date = models.DateField(verbose_name="Дата начала действия")
    wacc = models.FloatField(verbose_name="WACC (%)")
    comment = models.TextField(verbose_name="Комментарий", null=True, blank=True)
    class Meta:
        verbose_name = "WACC"
        verbose_name_plural = "WACC"

    def __str__(self):
        return f"{self.date}: {self.wacc}%"

#-----ИНФЛЯЦИЯ-----#
class Inflation(models.Model):
    date = models.DateField(verbose_name="Дата начала действия")
    inflation_rate = models.FloatField(verbose_name="ИПЦ (%)")
    comment = models.TextField(verbose_name="Комментарий", null=True, blank=True)
    class Meta:
        verbose_name = "ИПЦ"
        verbose_name_plural = "ИПЦ"

    def __str__(self):
        return f"{self.date}: {self.inflation_rate}%"

#-----СТАВКА РЕФИНАНСИРОВАНИЯ-----#    
class KeyRate(models.Model):
    date = models.DateField(verbose_name="Дата начала действия")
    key_rate = models.FloatField(verbose_name="Ключевая ставка (%)")
    comment = models.TextField(verbose_name="Комментарий", null=True, blank=True)
    class Meta:
        verbose_name = "Ключевая ставка"
        verbose_name_plural = "Ключевые ставки"

    def __str__(self):
        return f"{self.key_rate}%"

#-----КАЛЕНДАРЬ-----#
class CalendarExceptions(models.Model):
    date = models.DateField(primary_key=True, verbose_name='Дата')
    is_working_day = models.BooleanField(default=False, verbose_name='Рабочий день?')

    class Meta:
        verbose_name = "Клендарь"
        verbose_name_plural = "Календарь"


#-----НАЛОГИ-----#        
class TaxesList(models.Model):
    tax_name = models.CharField(max_length=255, verbose_name="Наименование налога", unique=True)
    description = models.TextField(verbose_name="Описание", null=True, blank=True)    

    class Meta:
        verbose_name = "Налог"
        verbose_name_plural = "Налоги"

    def __str__(self):
        return f"{self.tax_name}"
    
    def get_current_rate(self):
        today = timezone.now().date()
        rate = self.taxrates_set.filter(date__lte=today).order_by('-date').first()
        return f"{rate.rate}%" if rate else "—"
    get_current_rate.short_description = "Текущая ставка"
    
class TaxRates(models.Model):
    tax = models.ForeignKey(TaxesList, on_delete=models.CASCADE, verbose_name="Налог")
    date = models.DateField(verbose_name="Дата начала действия")
    rate = models.FloatField(verbose_name="Ставка (%)")
    comment = models.TextField(verbose_name="Комментарий", null=True, blank=True)

    class Meta:
        verbose_name = "Ставки налогов"
        verbose_name_plural = "Ставки налогов"

    def __str__(self):
        return f"{self.tax.tax_name} - {self.date}: {self.rate}%"
    


#-----КУРСЫ ВАЛЮТ-----#

class CurrencyRate(models.Model):

    date = models.DateField(verbose_name="Дата курса")
    base_currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOISE,
        verbose_name="Базовая валюта",
        default="RUB",
    )
    currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOISE,
        verbose_name="Валюта",
    )
    rate = models.DecimalField(
        max_digits=12,
        decimal_places=6,
        verbose_name="Курс",
        help_text="Сколько базовой валюты за 1 единицу выбранной валюты",
    )
    source = models.CharField(
        max_length=255,
        verbose_name="Источник",
        null=True,
        blank=True,
        help_text="Например: ЦБ РФ, ECB и т.п.",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")

    class Meta:
        verbose_name = "Курс валюты"
        verbose_name_plural = "Курсы валют"
        ordering = ["-date", "currency"]
        unique_together = ("date", "base_currency", "currency")

    def __str__(self):
        return f"{self.date} — {self.currency}/{self.base_currency}: {self.rate}"

    @classmethod
    def get_latest_rate(cls, currency: str, base_currency: str = "RUB"):

        obj = (
            cls.objects.filter(currency=currency, base_currency=base_currency)
            .order_by("-date")
            .first()
        )
        return obj.rate if obj else None







