# accounting_analysis/services/runner.py
import os
import re

from django.core.files import File

from accounting_analysis.services.registry import ANALYSIS_REGISTRY


def make_safe_filename(name: str) -> str:
    name = (name or "report").strip().lower()
    name = name.replace(" ", "_")
    name = re.sub(r"[^a-zA-Z0-9а-яА-Я_-]+", "", name)
    return name[:100] or "report"


def run_analysis(analysis):
    func = ANALYSIS_REGISTRY.get(analysis.script.code)

    if not func:
        analysis.status = "error"
        analysis.error_text = f"Скрипт с кодом '{analysis.script.code}' не найден"
        analysis.save(update_fields=["status", "error_text"])
        raise Exception(f"Скрипт с кодом '{analysis.script.code}' не найден")

    try:
        # путь к временному файлу (который создает твой скрипт)
        output_path = func(analysis.file.path)

        if not output_path or not os.path.exists(output_path):
            raise FileNotFoundError(f"Отчетный файл не найден: {output_path}")

        # формируем красивое имя
        safe_name = make_safe_filename(analysis.name)
        filename = f"analysis_{safe_name}.xlsx"

        # удаляем старый отчет, если есть
        if analysis.report_file:
            analysis.report_file.delete(save=False)

        # сохраняем новый отчет в Django
        with open(output_path, "rb") as f:
            analysis.report_file.save(filename, File(f), save=False)

        # ❗ УДАЛЯЕМ временный файл (очень важно)
        # но не трогаем исходный загруженный файл
        if os.path.exists(output_path) and os.path.abspath(output_path) != os.path.abspath(analysis.file.path):
            os.remove(output_path)

        # обновляем статус
        analysis.status = "done"
        analysis.error_text = ""
        analysis.save(update_fields=["report_file", "status", "error_text"])

    except Exception as e:
        analysis.status = "error"
        analysis.error_text = str(e)
        analysis.save(update_fields=["status", "error_text"])
        raise