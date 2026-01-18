# counterparties/helpers/glyph_fields.py

from django import forms

class GlyphChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.code} — {obj.title}"



def char_to_code(val: str | None) -> str | None:
    """
    Приводит текущее значение logo к коду вида uE003.
    Поддерживает:
      - реальный символ PUA (например '')
      - строку вида '\\uE003'
      - строку вида 'uE003' / 'UE003' / 'E003'
    """
    if not val:
        return None

    s = str(val).strip()
    if not s:
        return None

    # уже код
    if s.lower().startswith("u") and len(s) >= 5:
        return "u" + s[1:5].upper()

    if s.lower().startswith("\\u") and len(s) >= 6:
        return "u" + s[2:6].upper()

    # если это один символ (реальный глиф)
    if len(s) == 1:
        return f"u{ord(s):04X}"

    # если вдруг "E003"
    if len(s) == 4:
        try:
            int(s, 16)
            return "u" + s.upper()
        except Exception:
            return None

    return None



def code_to_char(code: str | None) -> str | None:
    """
    uE003 / \\uE003 / E003 -> реальный символ
    """
    if not code:
        return None

    s = str(code).strip()
    if not s:
        return None

    if s.lower().startswith("\\u"):
        s = s[2:]
    if s.lower().startswith("u"):
        s = s[1:]

    try:
        return chr(int(s, 16))
    except Exception:
        return None
