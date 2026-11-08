# # inventories/admin.py
# from django.contrib import admin, messages
# from django.core.management import call_command

# from .models import Lot, Delivery, LotFile, DeliveryFile


# # =========================
# # INLINES
# # =========================

# class LotFileInline(admin.TabularInline):
#     model = LotFile
#     extra = 1
#     fields = ("name", "file", "uploaded_at")
#     readonly_fields = ("uploaded_at",)
#     verbose_name = "Файл"
#     verbose_name_plural = "Файлы лота"


# class DeliveryFileInline(admin.TabularInline):
#     model = DeliveryFile
#     extra = 1
#     fields = ("name", "file", "uploaded_at")
#     readonly_fields = ("uploaded_at",)
#     verbose_name = "Документ"
#     verbose_name_plural = "Документы поставки"


# # =========================
# # LOT
# # =========================

# @admin.register(Lot)
# class LotAdmin(admin.ModelAdmin):
#     list_display = ("name", "description_short")
#     search_fields = ("name", "description")
#     inlines = [LotFileInline]

#     class Media:
#         css = {
#             "all": (
#                 "fonts/glyphs.css",
#                 "css/admin_overrides.css",
#             )
#         }

#     def description_short(self, obj):
#         return (obj.description[:80] + "...") if obj.description else ""

#     description_short.short_description = "Описание"


# # =========================
# # DELIVERY
# # =========================

# @admin.register(Delivery)
# class DeliveryAdmin(admin.ModelAdmin):
#     fieldsets = (
#         ("Основная информация", {
#             "fields": ("lot", "date", "number", "description")
#         }),
#         ("CSV загрузки", {
#             "fields": ("file",),
#             "description": "Файл для загрузки данных (основной CSV)"
#         }),
#     )

#     list_display = ("number", "date", "lot", "file", "description_short")
#     list_filter = ("date", "lot")
#     search_fields = ("number", "description", "lot__name")
#     autocomplete_fields = ("lot",)
#     date_hierarchy = "date"
#     inlines = [DeliveryFileInline]

#     # 🔥 ВОТ ОНО — кнопка
#     actions = ["build_parquet"]

#     @admin.action(description="Собрать parquet")
#     def build_parquet(self, request, queryset):
#         for delivery in queryset:
#             try:
#                 call_command("csv_parquet", delivery.id)

#                 self.message_user(
#                     request,
#                     f"OK: delivery {delivery.id}",
#                     level=messages.SUCCESS
#                 )

#             except Exception as e:
#                 self.message_user(
#                     request,
#                     f"Ошибка {delivery.id}: {e}",
#                     level=messages.ERROR
#                 )

#     class Media:
#         css = {
#             "all": (
#                 "fonts/glyphs.css",
#                 "css/admin_overrides.css",
#             )
#         }

#     def description_short(self, obj):
#         return (obj.description[:80] + "...") if obj.description else ""

#     description_short.short_description = "Описание"


# # =========================
# # LOT FILE
# # =========================

# @admin.register(LotFile)
# class LotFileAdmin(admin.ModelAdmin):
#     list_display = ("name", "lot", "file", "uploaded_at")
#     list_filter = ("lot", "uploaded_at")
#     search_fields = ("name", "file", "lot__name")
#     autocomplete_fields = ("lot",)
#     readonly_fields = ("uploaded_at",)


# # =========================
# # DELIVERY FILE
# # =========================

# @admin.register(DeliveryFile)
# class DeliveryFileAdmin(admin.ModelAdmin):
#     list_display = ("name", "delivery", "file", "uploaded_at")
#     list_filter = ("delivery", "uploaded_at")
#     search_fields = ("name", "file", "delivery__number", "delivery__lot__name")
#     autocomplete_fields = ("delivery",)
#     readonly_fields = ("uploaded_at",)





# inventories/admin.py
from django.contrib import admin, messages
from django.core.management import call_command

from .models import Lot, Delivery, LotFile, DeliveryFile


# =========================
# INLINES
# =========================

class LotFileInline(admin.TabularInline):
    model = LotFile
    extra = 1
    fields = ("name", "file", "uploaded_at")
    readonly_fields = ("uploaded_at",)
    verbose_name = "Файл"
    verbose_name_plural = "Файлы лота"


class DeliveryFileInline(admin.TabularInline):
    model = DeliveryFile
    extra = 1
    fields = ("name", "file", "uploaded_at")
    readonly_fields = ("uploaded_at",)
    verbose_name = "Документ"
    verbose_name_plural = "Документы поставки"


# =========================
# LOT
# =========================

@admin.register(Lot)
class LotAdmin(admin.ModelAdmin):
    list_display = ("name", "description_short")
    search_fields = ("name", "description")
    inlines = [LotFileInline]

    class Media:
        css = {
            "all": (
                "fonts/glyphs.css",
                "css/admin_overrides.css",
            )
        }

    def description_short(self, obj):
        return (obj.description[:80] + "...") if obj.description else ""

    description_short.short_description = "Описание"


# =========================
# DELIVERY
# =========================

@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Основная информация", {
            "fields": ("lot", "date", "number", "description")
        }),
        ("CSV загрузки", {
            "fields": ("file",),
            "description": "Файл для загрузки данных (основной CSV)"
        }),
    )

    list_display = ("number", "date", "lot", "file", "description_short")
    list_filter = ("date", "lot")
    search_fields = ("number", "description", "lot__name")
    autocomplete_fields = ("lot",)
    date_hierarchy = "date"
    inlines = [DeliveryFileInline]

    actions = ["build_parquet"]

    @admin.action(description="Собрать parquet")
    def build_parquet(self, request, queryset):
        for delivery in queryset:
            try:
                call_command("csv_parquet", delivery.id)

                self.message_user(
                    request,
                    f"OK: delivery {delivery.id}",
                    level=messages.SUCCESS
                )

            except Exception as e:
                self.message_user(
                    request,
                    f"Ошибка {delivery.id}: {e}",
                    level=messages.ERROR
                )

    class Media:
        css = {
            "all": (
                "fonts/glyphs.css",
                "css/admin_overrides.css",
            )
        }

    def description_short(self, obj):
        return (obj.description[:80] + "...") if obj.description else ""

    description_short.short_description = "Описание"


# =========================
# LOT FILE
# =========================

@admin.register(LotFile)
class LotFileAdmin(admin.ModelAdmin):
    list_display = ("name", "lot", "file", "uploaded_at")
    list_filter = ("lot", "uploaded_at")
    search_fields = ("name", "file", "lot__name")
    autocomplete_fields = ("lot",)
    readonly_fields = ("uploaded_at",)


# =========================
# DELIVERY FILE
# =========================

@admin.register(DeliveryFile)
class DeliveryFileAdmin(admin.ModelAdmin):
    list_display = ("name", "delivery", "file", "uploaded_at")
    list_filter = ("delivery", "uploaded_at")
    search_fields = ("name", "file", "delivery__number", "delivery__lot__name")
    autocomplete_fields = ("delivery",)
    readonly_fields = ("uploaded_at",)