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


class ManPack(models.Model):
    class Meta:
        managed = False
        verbose_name = "Управленческий пакет"
        verbose_name_plural = "Управленческий пакет"


class Exports(models.Model):
    """Заглушка: держит права на выгрузки из верхнего меню админки.

    Таблицы и записей у модели нет, нужна она только ради прав. Право
    выдаётся пользователю или группе как обычно, в разделе «Пользователи».
    Без права пункт меню не показывается и сам адрес выгрузки отдаёт 403 —
    проверка стоит и на меню, и на самой ссылке.
    """

    class Meta:
        managed = False
        default_permissions = ()
        verbose_name = "Выгрузки из меню «Экспорт»"
        verbose_name_plural = "Выгрузки из меню «Экспорт»"
        permissions = [
            ("export_gl", "Выгрузка: главная книга (GL)"),
            ("export_arap", "Выгрузка: дебиторы / кредиторы (ARAP)"),
            ("export_contracts_check",
             "Выгрузка: проверка договоров на списание в PL"),
            ("export_manpack", "Выгрузка: Management Pack"),
            ("export_management_pack",
             "Выгрузка: управленческий пакет (P&L + CF) и csv к нему"),
            ("export_stocks", "Выгрузка: остатки на складах"),
            ("export_budget_analysis", "Выгрузка: контроль выручки"),
        ]


class TelegramAccess(models.Model):
    """Доступ к ИИ-помощнику в Telegram: кто написал боту и разрешено ли отвечать."""

    BOTS = (("sales", "Продажи"), ("finance", "Финансы"))

    tg_id = models.BigIntegerField("Telegram ID")
    bot = models.CharField("Помощник", max_length=16, choices=BOTS)
    full_name = models.CharField("Имя в Telegram", max_length=255, blank=True)
    username = models.CharField("Ник", max_length=255, blank=True)
    is_allowed = models.BooleanField("Доступ разрешён", default=False)
    comment = models.CharField("Кто это (для себя)", max_length=255, blank=True)
    requests = models.PositiveIntegerField("Вопросов", default=0)
    created_at = models.DateTimeField("Первое обращение", auto_now_add=True)
    last_seen = models.DateTimeField("Последнее обращение", null=True, blank=True)

    class Meta:
        verbose_name = "Доступ к помощнику в Telegram"
        verbose_name_plural = "Помощник в Telegram: доступ"
        unique_together = (("tg_id", "bot"),)
        ordering = ("is_allowed", "-created_at")

    def __str__(self):
        return f"{self.full_name or self.username or self.tg_id} · {self.get_bot_display()}"
