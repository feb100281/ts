
# pricing_strategy

Полный модуль вкладки управления ценами.

## Что считается

- `buyer_price` — фактическая цена реализации WB покупателю:
  `retail_amount / positive_sales_qty`.
- `seller_price` — наша фактическая цена:
  `cr_rev / positive_sales_qty`.
- Маржа:
  `amount_vatless - cogs_man + net_comission`.
- `cogs_man` — управленческая FIFO-себестоимость.
- Эластичность:
  `ln(Q) = a + b * ln(buyer_price)`.

## Интеграция в main.py

```python
from .pricing_strategy import (
    PricingStrategyDashboard,
    register_pricing_strategy_callbacks,
)

PRICING_STRATEGY_DASHBOARD = PricingStrategyDashboard()
```

Добавить в `SegmentedControl.data`:

```python
{
    "label": "Цены",
    "value": "4",
},
```

В `render_tab` ДО общего `return`:

```python
if tab_value == "4":
    return PRICING_STRATEGY_DASHBOARD.layout(
        report_date=end,
        cat_list=cat_list,
        brand_list=brand_list,
        gender_list=gender_list,
    )
```

Внизу `register_callbacks`:

```python
register_pricing_strategy_callbacks(app)
```
