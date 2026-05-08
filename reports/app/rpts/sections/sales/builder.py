import dash_mantine_components as dmc
from reports.app.rpts.report_context import ReportContext
from .summary import slides as summary_slides
from .aims import slides as aims_slides
from .statistics import slides as stat_slides

SECTION_NAME = "Продажи"


def collect_slides(ctx: ReportContext):
    slide_groups = [
        summary_slides(ctx),
        aims_slides(ctx),
        stat_slides(ctx)
        
    ]

    subtitles = []

    for group in slide_groups:
        subtitles.extend(group.keys())

    return subtitles, slide_groups


def make_header(subtitles, active_subtitle):
    return [
        dmc.Title(SECTION_NAME.upper(), order=3),

        dmc.SegmentedControl(
            data=subtitles,
            color="grape",
            size="xs",
            value=active_subtitle,
        ),

        dmc.Divider(size="xs"),
    ]


def make_titles(ctx):
    subtitles, slide_groups = collect_slides(ctx)

    slides_with_header = []

    for group in slide_groups:
        for subtitle, slides in group.items():
            for slide_body in slides:
                slide = dmc.Container(
                    [
                        *make_header(subtitles, subtitle),
                        slide_body,
                    ],
                    fluid=True,
                    px=0,
                )

                slides_with_header.append(slide)

    return slides_with_header
    
    
    