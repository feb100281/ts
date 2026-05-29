from django.contrib import admin, messages
from django.db.models import Count
from django.utils.html import format_html

from unfold.admin import ModelAdmin
from unfold.decorators import display

from corporate.models import Owners
from corporate.services.checko_company import (
    get_company_data_by_inn,
    CheckoCompanyClientError,
)

from .inlines import BankAccountInline


@admin.register(Owners)
class OwnersAdmin(ModelAdmin):

    list_display = (
        "name",
        "inn",
        "ceo_display",
        "bankaccounts_count_display",
    )

    search_fields = (
        "name",
        "inn",
        "full_name",
        "ceo_name",
        "email",
    )

    inlines = [
        BankAccountInline,
    ]

    fieldsets = (
        (
            "Наименование",
            {
                "classes": ["tab"],
                "fields": (
                    "name",
                ),
            },
        ),
        (
            "Реквизиты",
            {
                "classes": ["tab"],
                "fields": (
                    "full_name",
                    "inn",
                    "kpp",
                    "ogrn",
                ),
            },
        ),
        (
            "Контакты",
            {
                "classes": ["tab"],
                "fields": (
                    "address",
                    "phone",
                    "email",
                    "website",
                ),
            },
        ),
        (
            "Руководитель",
            {
                "classes": ["tab"],
                "fields": (
                    "ceo_name",
                    "ceo_post",
                    "ceo_record_date",
                ),
            },
        ),
    )

    class Media:
        css = {
            "all": (
                "fonts/glyphs.css",
                "css/admin_overrides.css",
            )
        }
        js = (
            "corporate/js/owners_fill.js",
        )

    @display(description="Руководитель")
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
        return (
            super()
            .get_queryset(request)
            .annotate(
                _bankaccounts_count=Count("bankaccount")
            )
        )

    @display(
        description="Счетов",
        ordering="_bankaccounts_count",
    )
    def bankaccounts_count_display(self, obj):
        return obj._bankaccounts_count

    def changeform_view(
        self,
        request,
        object_id=None,
        form_url="",
        extra_context=None,
    ):
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
                    messages.error(
                        request,
                        f"Ошибка при обращении к API Checko: {e}",
                    )
                else:
                    if data:
                        post["kpp"] = data.get("kpp") or post.get("kpp", "")
                        post["ogrn"] = data.get("ogrn") or post.get("ogrn", "")
                        post["address"] = data.get("address") or post.get("address", "")
                        post["phone"] = data.get("phone") or post.get("phone", "")
                        post["email"] = data.get("email") or post.get("email", "")
                        post["website"] = data.get("website") or post.get("website", "")
                        post["full_name"] = data.get("full_name") or post.get("full_name", "")
                        post["ceo_name"] = data.get("ceo_name") or post.get("ceo_name", "")
                        post["ceo_post"] = data.get("ceo_post") or post.get("ceo_post", "")
                        post["ceo_record_date"] = (
                            data.get("ceo_record_date")
                            or post.get("ceo_record_date", "")
                        )

                        post["_continue"] = "1"
                        post.pop("_fill_by_inn", None)

                        request.POST = post

                        messages.success(
                            request,
                            f"Данные по компании с ИНН {inn} подтянуты.",
                        )
                    else:
                        messages.warning(
                            request,
                            f"Компания по ИНН {inn} не найдена.",
                        )

        return super().changeform_view(
            request,
            object_id,
            form_url,
            extra_context,
        )