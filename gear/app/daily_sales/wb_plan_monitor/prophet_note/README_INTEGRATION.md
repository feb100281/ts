# Интеграция пояснительной записки Prophet

## 1. Размещение папки

Скопировать папку:

    prophet_note/

в:

    gear/app/daily_sales/wb_plan_monitor/prophet_note/

Итоговая структура:

    wb_plan_monitor/
        prophet_forecast.py
        prophet_note/
            __init__.py
            builder.py
            calculations.py
            charts.py
            config.py
            formatting.py
            styles.py

## 2. Зависимости

    python -m pip install reportlab matplotlib

## 3. settings.py

    PROPHET_REPORT_COMPANY = "ТРЕНДСЕТТЕР"
    PROPHET_REPORT_AUTHOR = "Дарья Войтенко"
    PROPHET_REPORT_POSITION = "Финансовый аналитик"

## 4. Импорт в prophet_forecast.py

    from .prophet_note import (
        build_prophet_note_pdf,
        get_prophet_note_filename,
    )

## 5. Новые ID

    PDF_DOWNLOAD_BTN_ID = "wb-prophet-pdf-download-btn"
    PDF_DOWNLOAD_ID = "wb-prophet-pdf-download"

## 6. dcc.Download

В prophet_tab_panel(), рядом с dcc.Download(id=DOWNLOAD_ID):

    dcc.Download(
        id=PDF_DOWNLOAD_ID,
    ),

## 7. Кнопка

Рядом с кнопкой Excel:

    dmc.Button(
        "Скачать пояснительную записку",
        id=PDF_DOWNLOAD_BTN_ID,
        radius=0,
        variant="outline",
        color="gray",
        disabled=True,
        leftSection=DashIconify(
            icon="solar:file-text-linear",
            width=18,
            color="#B91C1C",
        ),
        styles={
            "root": {
                "backgroundColor": "#FFFFFF",
                "border": "1px solid #D1D5DB",
                "color": "#374151",
            },
        },
    ),

## 8. Основной callback

Добавить Output:

    Output(PDF_DOWNLOAD_BTN_ID, "disabled"),

При успешном расчёте вернуть:

    False,  # Excel
    False,  # PDF

При ошибке:

    True,   # Excel
    True,   # PDF

## 9. Callback PDF

    @app.callback(
        Output(PDF_DOWNLOAD_ID, "data"),
        Input(PDF_DOWNLOAD_BTN_ID, "n_clicks"),
        State(STORE_ID, "data"),
        prevent_initial_call=True,
    )
    def _download_note(n_clicks, result):
        if not n_clicks or not result:
            return no_update

        pdf_bytes = build_prophet_note_pdf(
            result=result,
        )

        return dcc.send_bytes(
            pdf_bytes,
            get_prophet_note_filename(result),
        )
