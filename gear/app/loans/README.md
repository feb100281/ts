# Loans app

Папка:
`gear/app/loans/`

Файлы:
- `app.py` — регистрация DjangoDash.
- `config.py` — название, цвета, настройки.
- `ids.py` — все Dash ID.
- `components.py` — UI-компоненты.
- `data.py` — SQL к `gl.borrowings_tp` и справочникам договоров.
- `calculations.py` — статусы, сроки, KPI, фильтры.
- `charts.py` — Plotly-графики.
- `grid.py` — реестр договоров и операции.
- `filters.py` — панель фильтров и callbacks options.
- `export.py` — Excel.
- `layout.py` — полный layout.
- `callbacks.py` — основная логика приложения.

## apps.py

В `gear/apps.py` должен быть импорт:

```python
from .app.loans import app as loans_app
```

## Admin model

В `gear/admin.py` регистрируется `Loans`, а не `Stats`:

```python
@admin.register(Loans)
class LoansDashboardAdmin(admin.ModelAdmin):
    change_list_template = "admin/gear/loans/loans.html"
```

## URL

`/apps/app/loans_app/`

## Важное по валютам

KPI суммируют денежные значения выбранной выборки.
Если в портфеле есть несколько валют, выбирайте одну валюту в фильтре
перед интерпретацией общего долга и денежных KPI.
