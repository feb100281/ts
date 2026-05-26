from django.urls import path

from .views import download_report_pdf


urlpatterns = [
    path(
        "report/<int:report_id>/pdf/",
        download_report_pdf,
        name="download_report_pdf",
    ),
]