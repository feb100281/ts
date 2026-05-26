from dash import html
from django.templatetags.static import static

from reports.models import Report


class ReportBuilder:

    def __init__(self, report_id):

        self.report = Report.objects.get(
            pk=report_id
        )

    def layout(self):

        slide = html.Div(
            [

                html.H1(
                    self.report.title
                ),

                html.H3(
                    self.report.subtitle
                ),

                html.Hr(),

                html.P(
                    self.report.description
                ),

                html.P(
                    f"Author: {self.report.author}"
                ),

                html.P(
                    f"Company: {self.report.company}"
                ),

                html.P(
                    f"Type: {self.report.report_type}"
                ),

            ],
            style=self.report.slide_style,
            className="report-slide",
        )

        slides = [
            slide,
            slide,
        ]

        return html.Div(
            [

                html.Link(
                    rel="stylesheet",
                    href=static(
                        f"css/{self.report.css}"
                    )
                ),

                html.Div(
                    slides,
                    id="report-container",
                ),
            ]
        )