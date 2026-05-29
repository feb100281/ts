from django import forms

from corporate.models import Bank
from counterparties.models import Glyph
from counterparties.helpers.glyph_fields import (
    GlyphChoiceField,
    char_to_code,
    code_to_char,
)


class BankForm(forms.ModelForm):
    logo_glyph = GlyphChoiceField(
        queryset=Glyph.objects.all().order_by("sort", "title"),
        required=False,
        label="Логотип (глиф)",
        help_text="Выберите глиф банка. В базе сохранится символ.",
    )

    class Meta:
        model = Bank
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if "logo" in self.fields:
            self.fields["logo"].widget = forms.HiddenInput()
            self.fields["logo"].required = False

        current = getattr(self.instance, "logo", None)
        code = char_to_code(current)

        if code:
            self.fields["logo_glyph"].initial = (
                Glyph.objects.filter(code=code).first()
            )

        self.fields["logo_glyph"].widget.attrs.update(
            {
                "style": (
                    "font-family:NotoManu, sans-serif; "
                    "font-size:18px;"
                )
            }
        )

    def save(self, commit=True):
        instance = super().save(commit=False)

        g = self.cleaned_data.get("logo_glyph")
        instance.logo = code_to_char(g.code) if g else None

        if commit:
            instance.save()
            self.save_m2m()

        return instance