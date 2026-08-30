# # budget/fns/render.py
# from pathlib import Path
# from jinja2 import Environment, FileSystemLoader, select_autoescape
# from weasyprint import HTML, CSS

# from demo_report import a

# import pandas as pd


# def render_pdf(report: dict, output_name: str = "report.pdf") -> Path:
#     current_dir = Path(__file__).resolve().parent           
#     project_dir = current_dir.parent.parent                

#     templates_dir = current_dir / "templates"
#     static_dir = project_dir / "static"

#     env = Environment(
#         loader=FileSystemLoader(str(templates_dir)),
#         autoescape=select_autoescape(["html", "xml"]),
#     )

#     logo_path = static_dir / "img" / "logo_ts.jpg"

#     if logo_path.exists():
#         report["logo_svg"] = logo_path.read_text(encoding="utf-8")

#     else:
#         print("WARNING: Logo file not found!")

#     template = env.get_template("budget.j2")
#     html = template.render(report=report)

#     output_path = current_dir / output_name
#     css_path = templates_dir / "budget.css"
#     cover_css_path = templates_dir / "cover.css"

#     stylesheets = [
#         CSS(filename=str(css_path)),
#         CSS(filename=str(cover_css_path))
#     ]

#     HTML(string=html, base_url=str(project_dir)).write_pdf(
#         str(output_path),
#         stylesheets=stylesheets
#     )

#     return output_path


# if __name__ == "__main__":
#     g = a
#     render_pdf(g)





# budget/fns/render.py
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML, CSS

from demo_report import a
import pandas as pd


def render_pdf(report: dict, output_name: str = "report.pdf") -> Path:
    current_dir = Path(__file__).resolve().parent
    project_dir = current_dir.parent.parent

    templates_dir = current_dir / "templates"
    static_dir = project_dir / "static"

    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(["html", "xml"]),
    )

    # ✅ Путь к логотипу через static (как в Django)
    logo_path = static_dir / "img" / "logo_ts.jpg"

    if logo_path.exists():
        # ВАЖНО: передаем URI, а не читаем файл
        report["logo_path"] = logo_path.as_uri()
    else:
        print(f"WARNING: Logo file not found: {logo_path}")
        report["logo_path"] = None

    template = env.get_template("budget.j2")
    html = template.render(report=report)

    output_path = current_dir / output_name
    
    # ✅ Пути к CSS файлам
    css_path = templates_dir / "budget.css"
    cover_css_path = templates_dir / "cover.css"
    toc_css_path = templates_dir / "toc.css"

    stylesheets = [
        CSS(filename=str(css_path)),
        CSS(filename=str(cover_css_path)),
        CSS(filename=str(toc_css_path))  
    ]

    HTML(string=html, base_url=str(project_dir)).write_pdf(
        str(output_path),
        stylesheets=stylesheets
    )

    return output_path


if __name__ == "__main__":
    g = a
    render_pdf(g)