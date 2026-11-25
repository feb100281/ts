# accounting_analysis/models.py
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class AnalysisScript(models.Model):
    code = models.CharField("Код", max_length=100, unique=True)
    name = models.CharField("Название", max_length=255)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Функции"
        verbose_name_plural = "Функции"

    def __str__(self):
        return self.name


class AccountingAnalysis(models.Model):
    STATUS_CHOICES = [
        ("new", "Новый"),
        ("done", "Готов"),
        ("error", "Ошибка"),
    ]

    name = models.CharField("Название", max_length=255)

    file = models.FileField(
        upload_to="accounting_uploads/",
        verbose_name="Файл Excel"
    )

    script = models.ForeignKey(
        AnalysisScript,
        on_delete=models.CASCADE,
        verbose_name="Сценарий"
    )

    account = models.CharField(
        "Счет",
        max_length=20,
        null=True,
        blank=True
    )

    status = models.CharField(
        "Статус",
        max_length=20,
        choices=STATUS_CHOICES,
        default="new"
    )

    report_file = models.FileField(
        upload_to="accounting_reports/",
        null=True,
        blank=True,
        verbose_name="Отчет"
    )

    error_text = models.TextField(
        "Ошибка",
        blank=True,
        null=True
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Кто создал"
    )

    created_at = models.DateTimeField(
            auto_now_add=True,
            verbose_name="Создано"
        )
            
    
    def delete(self, *args, **kwargs):
        if self.report_file:
            self.report_file.delete(save=False)

        if self.file:
            self.file.delete(save=False)

        super().delete(*args, **kwargs)
    
    class Meta:
        verbose_name = "Анализ файла"
        verbose_name_plural = "Анализы файлов"

    def __str__(self):
        return self.name


class AccountingMetric(models.Model):
    PERIOD_TYPE_CHOICES = [
        ("month_end", "Конец месяца"),
        ("day", "День"),
    ]

    analysis = models.ForeignKey(
        AccountingAnalysis,
        on_delete=models.CASCADE,
        related_name="metrics",
        verbose_name="Анализ"
    )

    account = models.CharField("Счет", max_length=20)

    metric_name = models.CharField("Показатель", max_length=100)

    value = models.DecimalField(
        "Значение",
        max_digits=15,
        decimal_places=2
    )

    period = models.DateField("Дата")

    period_type = models.CharField(
        "Тип периода",
        max_length=20,
        choices=PERIOD_TYPE_CHOICES,
        default="month_end"
    )

    created_at = models.DateTimeField(
                auto_now_add=True,
                verbose_name="Создано"
            )

        
    class Meta:
        verbose_name = "Показатель"
        verbose_name_plural = "Показатели"
        unique_together = ("analysis", "account", "metric_name", "period")

    def __str__(self):
        return f"{self.account} | {self.metric_name} | {self.period} = {self.value}"