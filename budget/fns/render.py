from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML, CSS

from reporter_builder import Section, Report, P, T


def render_pdf(report: dict, output_name: str = "report.pdf") -> Path:
    base_dir = Path(__file__).resolve().parent
    templates_dir = base_dir / "templates"

    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(["html", "xml"]),
    )

    template = env.get_template("budget.j2")
    html = template.render(report=report)

    output_path = base_dir / output_name
    css_path = templates_dir / "budget.css"

    HTML(string=html, base_url=str(templates_dir)).write_pdf(
        str(output_path),
        stylesheets=[CSS(filename=str(css_path))]
    )

    return output_path

