from pathlib import Path
from urllib.parse import urlencode

from django.conf import settings
from playwright.sync_api import sync_playwright


def export_report_pdf(request, report_id):

    query = urlencode({
        "object_id": report_id
    })

    relative_url = f"/apps/app/rpt_app/?{query}"

    # Локально, без DNS/HTTPS
    url = f"https://www.ts-bias.ru/apps/app/rpt_app{relative_url}"

    output_dir = Path(settings.MEDIA_ROOT) / "reports"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / f"report_{report_id}.pdf"

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ],
        )

        page = browser.new_page(
            viewport={
                "width": 1280,
                "height": 720,
            },
            device_scale_factor=2,
        )

        page.goto(
            url,
            wait_until="commit",
            timeout=120_000,
        )

        page.wait_for_load_state(
            "domcontentloaded",
            timeout=120_000,
        )

        

        # Небольшой добор на графики/шрифты
        page.wait_for_timeout(5_000)

        page.pdf(
            path=str(output_file),
            print_background=True,
            prefer_css_page_size=True,
        )

        browser.close()

    return output_file