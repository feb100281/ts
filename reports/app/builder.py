from django.utils.module_loading import import_string
from django.templatetags.static import static
import pandas as pd

from dash import html
import dash_mantine_components as dmc

from reports.models import (
    Report,
    ReportConstructor,
)


# Функкция header и footer нужно потом в отдельный файл вынести misc
def stepper_header():
    pass



def fancy_header(row, section_content):

    title = str(row["section"]).upper()
    subtitle = str(row["slide_title"])

    data = [
        {
            "value": r["slide_title"],
            "label": r["slide_title"],
        }
        for _, r in section_content.iterrows()
    ]

    subtitle_segment = dmc.SegmentedControl(
        data=data,
        value=subtitle,
        # fullWidth=True,
        size="xs",
        color="brown",
    )

    return dmc.Stack(
        [
            dmc.Title(title, order=2),
            subtitle_segment,
            dmc.Divider(size="xs"),
        ],
        gap="xs",
        align="flex-start",
    )


def fancncy_footer(page, report_title, report_subtile):

    return dmc.Stack(
        [
            dmc.Divider(size="xs"),

            dmc.Group(
                [
                    dmc.Text(
                        f"{report_title} / {report_subtile}",
                        c="dimmed",
                        size="xs",
                    ),

                    dmc.Text(
                        str(page),
                        c="dimmed",
                        size="xs",
                    ),
                ],
                justify="space-between",
            ),
        ],
        gap="xs",
    )


class ReportBuilder:

    def __init__(self, report_id):

        self.report = Report.objects.get(pk=report_id)

        self.page_number = 0

    def get_slides_df(self):

        rows = (
            ReportConstructor.objects.filter(
                report=self.report,
                is_active=True,
            )
            .select_related(
                "slide",
                "section",
            )
            .order_by(
                "order",
                "id",
            )
        )

        data = []

        for i, row in enumerate(rows, start=1):

            data.append(
                {
                    "page": i,
                    "section": (row.section.title if row.section else ""),
                    "slide_title": row.slide.title,
                    "python_path": row.slide.python_path,
                    "filters": row.filters or {},
                    "item": row,
                }
            )

        return pd.DataFrame(data)

    def wrap_slide(self, row, content, section_content):

        return dmc.Box(
            [
                fancy_header(row, section_content),

                dmc.Box(
                    content,
                    style={
                        "flex": 1,
                        "overflow": "hidden",
                    },
                ),

                fancncy_footer(
                    row["page"],
                    self.report.title,
                    self.report.subtitle,
                ),
            ],
            className="report-slide",
            style={
                **self.report.slide_style,

                "display": "flex",
                "flexDirection": "column",

                # header top / footer bottom
                "justifyContent": "space-between",
            },
        )

    def build_slide(self, row, section):

        render_func = import_string(row.python_path)

        contents = render_func(
            report=self.report,
            filters=row.filters,
        )

        if not isinstance(contents, list):
            contents = [contents]

        slides = []

        for content in contents:

            slides.append(
                self.wrap_slide(row=row, content=content, section_content=section)
            )

        return slides

    def layout(self):

        slides_df = self.get_slides_df()

        slides = []

        for _, row in slides_df.iterrows():
            section_content = slides_df[slides_df["section"] == row["section"]]

            slides.extend(self.build_slide(row, section_content))

        return [
            html.Link(rel="stylesheet", href=static(f"css/{self.report.css}")),
            *slides,
        ]
