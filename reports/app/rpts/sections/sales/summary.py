import dash_mantine_components as dmc
from reports.app.rpts.report_context import ReportContext


def slide1(ctx:ReportContext):
    return dmc.Container(
        [
        dmc.Text(ctx.report_date),
        dmc.Text(ctx.author)
        ],
        fluid=True
    )

def slide2(ctx:ReportContext):
    return dmc.Container(
        [
        dmc.Text(ctx.report_date),
        dmc.Text(ctx.author)
        ],
        fluid=True,
        px=1,
    )
    
def slides(ctx):
    return {"Резюме":[
        slide1(ctx),
        slide2(ctx)
    ]}


