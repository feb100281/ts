from django.contrib import admin, messages
from django.shortcuts import redirect
from django.utils.html import format_html

from unfold.admin import ModelAdmin
from unfold.decorators import display

from corporate.models import Bank
from corporate.services.checko_bank import (
    get_bank_data_by_bik,
    CheckoBankClientError,
)

from .forms import BankForm


@admin.register(Bank)
class BankAdmin(ModelAdmin):
    form = BankForm

    exclude = (
        "inn",
        "kpp",
    )

    list_display = (
        "logo_preview",
        "name",
        "bik",
        "corr_account",
    )

    list_display_links = (
        "name",
    )

    search_fields = (
        "name",
        "bik",
    )

    readonly_fields = (
        "type",
        "address",
    )

    list_filter = (
        "bik",
        "name",
    )

    fieldsets = (
        (
            "Банк",
            {
                "classes": ["tab"],
                "fields": (
                    "name",
                    "name_eng",
                ),
            },
        ),
        (
            "Платёжные реквизиты",
            {
                "classes": ["tab"],
                "fields": (
                    "bik",
                    "corr_account",
                ),
            },
        ),
        (
            "Логотип",
            {
                "classes": ["tab"],
                "fields": (
                    "logo_glyph",
                    "logo",
                ),
            },
        ),
        (
            "Адрес и тип",
            {
                "classes": ["tab"],
                "fields": (
                    "type",
                    "address",
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
            "corporate/js/bank_fill.js",
            "js/glyph_select2.js",
        )

    @display(description="Лого")
    def logo_preview(self, obj):
        if not obj.logo:
            return "—"

        outer = (
            "display:inline-flex;align-items:center;justify-content:center;"
            "width:28px;height:28px;border-radius:6px;"
            "background:linear-gradient(135deg,#f8fafc,#f1f5f9);"
            "box-shadow:0 0 0 1px rgba(148,163,184,.35);"
        )

        inner = (
            "font-family:NotoManu;"
            "font-size:20px;"
            "line-height:1;"
        )

        return format_html(
            '<span style="{}"><span style="{}">{}</span></span>',
            outer,
            inner,
            obj.logo,
        )

    def changeform_view(
        self,
        request,
        object_id=None,
        form_url="",
        extra_context=None,
    ):
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
                messages.error(
                    request,
                    f"Ошибка при обращении к API Checko: {e}",
                )
                return redirect(request.path)

            if data:
                post["name"] = data.get("name") or post.get("name", "")
                post["name_eng"] = data.get("name_eng") or post.get("name_eng", "")
                post["address"] = data.get("address") or post.get("address", "")
                post["corr_account"] = (
                    data.get("corr_account")
                    or post.get("corr_account", "")
                )
                post["type"] = data.get("type") or post.get("type", "")

                post["_continue"] = "1"
                post.pop("_fill_by_bik", None)

                request.POST = post

                messages.success(
                    request,
                    f"Данные по банку с БИК {bik} подтянуты.",
                )
            else:
                messages.warning(
                    request,
                    f"Банк по БИК {bik} не найден.",
                )
                return redirect(request.path)

        return super().changeform_view(
            request,
            object_id,
            form_url,
            extra_context,
        )