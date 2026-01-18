from django.contrib import admin
from django.db.models import Count
from django.utils.html import format_html
from django.contrib import messages
from django.shortcuts import redirect
from .models import Owners, BankAccount, Bank, СfItems, COA
from .services.checko_bank import get_bank_data_by_bik, CheckoBankClientError
from .services.checko_company import get_company_data_by_inn, CheckoCompanyClientError
from mptt.admin import DraggableMPTTAdmin




class BankAccountInline(admin.TabularInline):
    model = BankAccount
    extra = 1
    # bik убрали — у собственника только выбор банка, счёт и валюта
    fields = ("bank", "account", "currency")
    autocomplete_fields = ("bank",)
    

#----- СОБСТВЕННИКИ ----#
@admin.register(Owners)
class OwnersAdmin(admin.ModelAdmin):

    list_display = ("name", "inn", "ceo_display", "bankaccounts_count_display")
    inlines = [BankAccountInline]

    class Media:
        js = ("corporate/js/owners_fill.js",)

    fieldsets = (
        (
            "Отображение в системе",
            {"fields": ("name",)},
        ),
        (
            "Юридические реквизиты",
            {
                "fields": (
                    "full_name",
                    "inn",
                    "kpp",
                    "ogrn",
                )
            },
        ),
        (
            "Контакты и адрес",
            {
                "fields": (
                    "address",
                    "phone",
                    "email",
                    "website",
                )
            },
        ),
        (
            "Руководитель",
            {
                "fields": (
                    "ceo_name",
                    "ceo_post",
                    "ceo_record_date",
                )
            },
        ),
    )

    @admin.display(description="Руководитель")
    def ceo_display(self, obj):
        if not obj.ceo_name and not obj.ceo_post:
            return "—"
        if obj.ceo_post:
            return format_html(
                "{}<br><span style='color:#666;font-size:11px;'>{}</span>",
                obj.ceo_name or "",
                obj.ceo_post,
            )
        return obj.ceo_name or "—"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_bankaccounts_count=Count("bankaccount"))

    @admin.display(description="Кол-во расчётных счетов", ordering="_bankaccounts_count")
    def bankaccounts_count_display(self, obj):
        return obj._bankaccounts_count

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        if "_fill_by_inn" in request.POST:
            post = request.POST.copy()
            inn = (post.get("inn") or "").strip()

            if not inn:
                messages.warning(request, "Сначала введите ИНН.")
            else:
                try:
                    data = get_company_data_by_inn(inn)
                except CheckoCompanyClientError as e:
                    messages.error(request, f"Ошибка Checko: {e}")
                except Exception as e:
                    messages.error(request, f"Ошибка при обращении к API Checko: {e}")
                else:
                    if data:
                        # name не трогаем
                        post["kpp"] = data.get("kpp") or post.get("kpp", "")
                        post["ogrn"] = data.get("ogrn") or post.get("ogrn", "")
                        post["address"] = data.get("address") or post.get("address", "")
                        post["phone"] = data.get("phone") or post.get("phone", "")
                        post["email"] = data.get("email") or post.get("email", "")
                        post["website"] = data.get("website") or post.get("website", "")

                        post["full_name"] = data.get("full_name") or post.get("full_name", "")
                        post["ceo_name"] = data.get("ceo_name") or post.get("ceo_name", "")
                        post["ceo_post"] = data.get("ceo_post") or post.get("ceo_post", "")
                        post["ceo_record_date"] = data.get("ceo_record_date") or post.get(
                            "ceo_record_date", ""
                        )

                        post["_continue"] = "1"
                        if "_fill_by_inn" in post:
                            del post["_fill_by_inn"]

                        request.POST = post

                        messages.success(
                            request,
                            f"Данные по компании с ИНН {inn} подтянуты и подставлены в форму.",
                        )
                    else:
                        messages.warning(request, f"Компания по ИНН {inn} не найдена.")

        return super().changeform_view(request, object_id, form_url, extra_context)
    
    

# ----- БАНКИ ---- #
@admin.register(Bank)
class BankAdmin(admin.ModelAdmin):
    exclude = ("inn", "kpp")
    list_display = ("name", "bik", "corr_account")
    search_fields = ("name", "bik")

    fieldsets = (
        (
            "Реквизиты банка",
            {
                "fields": (
                    "name",
                    "name_eng",
                    "bik",
                    "corr_account",
                )
            },
        ),
        (
            "Адрес и тип",
            {
                "fields": (
                    "type",
                    "address",
                )
            },
        ),
    )

    class Media:
        js = ("corporate/js/bank_fill.js",)

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        """
        Обработка кнопки 'Заполнить по БИК' на форме банка.
        """
        if "_fill_by_bik" in request.POST:
            post = request.POST.copy()
            bik = (post.get("bik") or "").strip()

            if not bik:
                messages.warning(request, "Сначала введите БИК.")
                return redirect(request.path)

            try:
                data = get_bank_data_by_bik(bik)
            except CheckoBankClientError as e:
                messages.error(request, f"Ошибка Checko: {e}")
                return redirect(request.path)
            except Exception as e:
                messages.error(request, f"Ошибка при обращении к API Checko: {e}")
                return redirect(request.path)
            else:
                if data:
                    post["name"] = data.get("name") or post.get("name", "")
                    post["name_eng"] = data.get("name_eng") or post.get("name_eng", "")
                    post["address"] = data.get("address") or post.get("address", "")
                    post["corr_account"] = data.get("corr_account") or post.get(
                        "corr_account", ""
                    )
                    post["type"] = data.get("type") or post.get("type", "")

                    # Остаёмся на форме
                    post["_continue"] = "1"
                    if "_fill_by_bik" in post:
                        del post["_fill_by_bik"]

                    request.POST = post

                    messages.success(
                        request,
                        f"Данные по банку с БИК {bik} подтянуты и подставлены в форму.",
                    )
                else:
                    messages.warning(request, f"Банк по БИК {bik} не найден.")
                    return redirect(request.path)

        return super().changeform_view(request, object_id, form_url, extra_context)


# ----- БАНКОВСКИЕ СЧЕТА ---- #
@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ("corporate", "bank", "bik", "account", "currency")
    search_fields = ("corporate__name", "bank__name", "bik", "account")


@admin.register(COA)
class AccountAdmin(DraggableMPTTAdmin):
    mptt_level_indent = 7
    list_display = ("tree_actions", "indented_title", "code", "is_active")
    list_display_links = ("indented_title",)
    search_fields = ("code", "name")

@admin.register(СfItems)
class CashFlowItemAdmin(DraggableMPTTAdmin):
    mptt_level_indent = 7
    list_display = ("tree_actions", "indented_title", "code", "is_active")
    list_display_links = ("indented_title",)
    search_fields = ("code", "name")