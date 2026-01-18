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



#-----ЦЕНЫ НА НЕДВИЖИМОСТЬ-----#
from django.db import models
from django.utils import timezone
from django.db.models import Q


# ─────────────────────────────
# Справочники
# ─────────────────────────────

class MarketRegion(models.Model):
    name = models.CharField(max_length=255, unique=True, verbose_name="Город / регион")

    class Meta:
        verbose_name = "Рынок: регион"
        verbose_name_plural = "Рынок: регионы"

    def __str__(self):
        return self.name

class MarketDistrict(models.Model):
    region = models.ForeignKey(
        MarketRegion,
        on_delete=models.CASCADE,
        related_name="districts",
        verbose_name="Город / регион",
    )
    name = models.CharField(max_length=255, verbose_name="Район / округ")

    class Meta:
        verbose_name = "Рынок: район"
        verbose_name_plural = "Рынок: районы"
        unique_together = ("region", "name")

    def __str__(self):
        return f"{self.region} — {self.name}"

class OfficeClass(models.Model):
    code = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="Код",
        help_text="A, B, C, UNKNOWN",
    )
    name = models.CharField(max_length=255, verbose_name="Название")

    class Meta:
        verbose_name = "Рынок: класс объекта"
        verbose_name_plural = "Рынок: классы объектов"

    def __str__(self):
        return self.name

class MarketSource(models.Model):
    code = models.CharField(max_length=50, unique=True, verbose_name="Код источника")
    name = models.CharField(max_length=255, verbose_name="Название")

    class Meta:
        verbose_name = "Рынок: источник"
        verbose_name_plural = "Рынок: источники"

    def __str__(self):
        return self.name

class PropertyType(models.Model):
    """
    Тип недвижимости: офис, паркинг, склад, ритейл и т.д.
    """
    code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Код",
        help_text="office, parking, warehouse, retail и т.п.",
    )
    name = models.CharField(max_length=255, verbose_name="Название")

    is_active = models.BooleanField(default=True, verbose_name="Активен?")

    class Meta:
        verbose_name = "Рынок: тип недвижимости"
        verbose_name_plural = "Рынок: типы недвижимости"

    def __str__(self):
        return self.name


class MarketListing(models.Model):
    DEAL_TYPES = [
        ("rent", "Аренда"),
        ("sale", "Продажа"),
    ]

    source = models.ForeignKey(MarketSource, on_delete=models.PROTECT, verbose_name="Источник")
    external_id = models.CharField(max_length=128, verbose_name="ID в источнике")
    url = models.URLField(verbose_name="Ссылка")

    property_type = models.ForeignKey(
        PropertyType,
        on_delete=models.PROTECT,
        verbose_name="Тип недвижимости",
    )

    deal_type = models.CharField(
        max_length=20,
        choices=DEAL_TYPES,
        verbose_name="Тип сделки",
    )

    region = models.ForeignKey(MarketRegion, on_delete=models.PROTECT, verbose_name="Город / регион")
    district = models.ForeignKey(MarketDistrict, on_delete=models.PROTECT, verbose_name="Район")
    office_class = models.ForeignKey(OfficeClass, on_delete=models.PROTECT, verbose_name="Класс")

    office_class_raw = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="Класс (сырой)",
    )

    title = models.CharField(max_length=500, null=True, blank=True, verbose_name="Заголовок")
    description = models.TextField(null=True, blank=True, verbose_name="Описание")
    address_text = models.CharField(max_length=500, null=True, blank=True, verbose_name="Адрес (текст)")

    lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name="Широта")
    lon = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name="Долгота")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлено")

    class Meta:
        verbose_name = "Рынок: объявление"
        verbose_name_plural = "Рынок: объявления"
        constraints = [
            models.UniqueConstraint(
                fields=["source", "external_id"],
                name="uq_market_listing_source_external_id",
            )
        ]
        indexes = [
            models.Index(fields=["property_type", "region", "district", "office_class", "deal_type"]),
            models.Index(fields=["updated_at"]),
        ]

    def __str__(self):
        return f"{self.source.code} #{self.external_id}"


class MarketListingObservation(models.Model):
    CURRENCY_CHOICES = [
        ("RUB", "RUB"),
        ("USD", "USD"),
        ("EUR", "EUR"),
    ]

    RENT_RATE_UNITS = [
        ("m2_month", "₽/м²/мес"),
        ("m2_year", "₽/м²/год"),
        ("total_month", "₽/мес"),
        ("total_year", "₽/год"),
    ]

    listing = models.ForeignKey(
        MarketListing,
        on_delete=models.CASCADE,
        related_name="observations",
        verbose_name="Объявление",
    )

    observed_at = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        verbose_name="Дата наблюдения",
    )
    
    observed_date = models.DateField(
        default=timezone.now,   
        db_index=True,
        verbose_name="Дата наблюдения (день)",
    )
    
    raw = models.JSONField(          
        null=True, blank=True, verbose_name="Сырые данные (JSON/слепок)"
    )


    is_active = models.BooleanField(default=True, db_index=True, verbose_name="Активно")

    area_m2 = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Площадь, м²",
    )

    currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES,
        default="RUB",
        verbose_name="Валюта",
    )

    price_total = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Цена всего",
    )

    rent_rate_value = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Ставка",
    )
    rent_rate_unit = models.CharField(
        max_length=20,
        choices=RENT_RATE_UNITS,
        null=True,
        blank=True,
        verbose_name="Ед. ставки",
    )

    vat_included = models.BooleanField(null=True, blank=True, verbose_name="НДС включён")
    opex_included = models.BooleanField(null=True, blank=True, verbose_name="OPEX включён")

    norm_rub_m2_month = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True,
        db_index=True,
        verbose_name="Норм. ставка, ₽/м²/мес",
    )

    published_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата публикации")

    class Meta:
        verbose_name = "Рынок: наблюдение"
        verbose_name_plural = "Рынок: наблюдения"
        indexes = [
            models.Index(fields=["listing", "observed_date"]),
            models.Index(fields=["listing", "-observed_at"]),
            models.Index(fields=["observed_at"]),
            models.Index(fields=["is_active", "observed_at"]),
            models.Index(fields=["norm_rub_m2_month"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["listing", "observed_date"],
                name="uq_obs_listing_day",
            )
        ]


class MarketSnapshot(models.Model):
    period = models.DateField(verbose_name="Период")

    property_type = models.ForeignKey(
        PropertyType,
        on_delete=models.PROTECT,
        verbose_name="Тип недвижимости",
    )

    deal_type = models.CharField(
        max_length=20,
        choices=MarketListing.DEAL_TYPES,
        verbose_name="Тип сделки",
    )

    region = models.ForeignKey(MarketRegion, on_delete=models.PROTECT, verbose_name="Город / регион")
    district = models.ForeignKey(MarketDistrict, on_delete=models.PROTECT, verbose_name="Район")
    office_class = models.ForeignKey(OfficeClass, on_delete=models.PROTECT, verbose_name="Класс")

    metric = models.CharField(
        max_length=30,
        default="norm_rub_m2_month",
        verbose_name="Метрика",
    )

    currency = models.CharField(max_length=3, default="RUB", verbose_name="Валюта")

    listings_count = models.IntegerField(verbose_name="Кол-во объявлений")

    median_price = models.DecimalField(max_digits=18, decimal_places=2, verbose_name="Медиана")
    p25_price = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True, verbose_name="P25")
    p75_price = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True, verbose_name="P75")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Анализ рынка"
        verbose_name_plural = "Анализ рынка"
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "period",
                    "property_type",
                    "deal_type",
                    "region",
                    "district",
                    "office_class",
                    "metric",
                ],
                name="uq_market_snapshot_segment_metric",
            )
        ]
        indexes = [
            models.Index(fields=["period", "property_type", "region", "district", "office_class", "deal_type"]),
        ]
