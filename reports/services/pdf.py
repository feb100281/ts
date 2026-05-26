from pathlib import Path
from urllib.parse import urlencode

from django.conf import settings
from playwright.sync_api import sync_playwright


def export_report_pdf(request, report_id):

    query = urlencode({
        "object_id": report_id
    })

    relative_url = (
        f"/apps/app/rpt_app/?{query}"
    )

    url = request.build_absolute_uri(
        relative_url
    )

    output_dir = (
        Path(settings.MEDIA_ROOT)
        / "reports"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    output_file = (
        output_dir
        / f"report_{report_id}.pdf"
    )

    with sync_playwright() as p:

        browser = p.chromium.launch()

        page = browser.new_page(
            viewport={
                "width": 1280,
                "height": 720,
            },
            device_scale_factor=2,
        )

        page.goto(
            url,
            wait_until="networkidle",
        )

        page.wait_for_timeout(2000)

        page.pdf(
            path=str(output_file),
            print_background=True,
            prefer_css_page_size=True,
        )

        browser.close()

    return output_file