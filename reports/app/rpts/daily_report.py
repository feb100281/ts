from dash import html
import dash_mantine_components as dmc
from .report_context import ReportContext
from .sections.sales import builder

SLIDE_STYLE = {
    "width": "1280px",
    "height": "720px",
    "margin": "0 auto 24px auto",
    "padding": "40px",
    "boxSizing": "border-box",
    "backgroundColor": "white",
    "overflow": "hidden",
    "position": "relative",
    "boxShadow": "0 0 8px rgba(0,0,0,0.15)",
}



def collectsection(ctx):
    slides = []
    slides.extend(
        builder.make_titles(ctx))
    return slides


def main():

    ctx = ReportContext(
        report_date='2026-03-01'
    )

    layout = []

    for slide in collectsection(ctx):

        layout.append(
            dmc.Container(
                [
                    dmc.Box(
                        slide,
                        style={
                            "paddingBottom": "50px",
                        },
                    ),

                    dmc.Box(
                        [
                            dmc.Divider(color="blue"),
                            dmc.Text(ctx.author),
                        ],
                        style={
                            "position": "absolute",
                            "left": "40px",
                            "right": "40px",
                            "bottom": "24px",
                        },
                    ),
                ],
                fluid=True,
                className="report-slide",
                style={
                    **SLIDE_STYLE,
                    "position": "relative",
                },
            )
        )

    return dmc.MantineProvider(
        [
            dmc.Container(
                layout,
                fluid=True
                # className='report-root',
            )
        ]
    )

    