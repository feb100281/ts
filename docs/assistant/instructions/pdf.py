import html, asyncio, sys
sys.argv=['x']
import mk
from mk import SALES, FIN, CONTACT, SEND
e = html.escape

CSS = """
@page { size: A4; margin: 12mm 16mm 14mm; }
* { box-sizing: border-box; }
body { margin: 0; font-family: 'Liberation Sans', Arial, sans-serif; color: #1F1F1F; font-size: 10.2pt; line-height: 1.5; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
.page { }
.page:last-child { page-break-after: auto; }
.cover { margin: 0; padding: 8mm 9mm 7.5mm; background: linear-gradient(135deg, #1F5E4E 0%, #2F6656 55%, #3D7A67 100%); color: #fff; display: flex; gap: 14px; align-items: center; }
.cover.small { margin: 0; padding: 0 0 2.4mm; background: none; color: #1F1F1F; border-bottom: 2px solid #2F6656; }
.cover.small .sub { color: #6B7280; opacity: 1; }
.logo { flex: none; width: 58px; height: 58px; border-radius: 50%; background: linear-gradient(135deg, #2FB7A4, #6B6EE6); display: flex; align-items: center; justify-content: center; box-shadow: 0 0 0 5px rgba(255,255,255,.16); }
.cover.small .logo { width: 40px; height: 40px; }
.logo svg { width: 55%; height: 55%; }
.kicker { font-size: 8.5pt; letter-spacing: .14em; text-transform: uppercase; opacity: .75; font-weight: 700; }
.cover h1 { margin: 3px 0 2px; font-size: 25pt; line-height: 1.1; font-weight: 700; letter-spacing: -.01em; }
.cover.small h1 { font-size: 16pt; }
.cover .sub { font-size: 10.5pt; opacity: .85; }
section { margin-top: 4.6mm; }
h2 { break-after: avoid; }
.steps, .alert, .note, .where, .two, .chips, .cmp { break-inside: avoid; }
.brk { page-break-before: always; }
h2 { display: flex; align-items: center; gap: 10px; margin: 0 0 2.4mm; font-size: 12.5pt; font-weight: 700; color: #1F5E4E; }
h2 .n { flex: none; width: 24px; height: 24px; background: #2F6656; color: #fff; font-size: 9pt; display: flex; align-items: center; justify-content: center; font-weight: 700; }
h2::after { content: ""; flex: 1; height: 1px; background: #D5E0DC; }
p { margin: 0 0 2.2mm; }
.lead { color: #3A3F44; }
.where { display: flex; gap: 12px; align-items: center; padding: 3.2mm 4mm; background: #F3F8F6; border-left: 3px solid #2F6656; margin-top: 1mm; }
.where .dot { flex: none; width: 30px; height: 30px; border-radius: 50%; background: linear-gradient(135deg, #2FB7A4, #6B6EE6); display: flex; align-items: center; justify-content: center; }
.where .dot svg { width: 55%; height: 55%; }
.steps { display: grid; grid-template-columns: repeat(5, 1fr); gap: 2.4mm; }
.step { border: 1px solid #E3E8E6; border-top: 3px solid #2F6656; padding: 3mm 3mm 3.2mm; font-size: 8.6pt; line-height: 1.42; }
.step .num { font-size: 17pt; font-weight: 700; color: #C9DCD5; line-height: 1; }
.step .t { font-weight: 700; font-size: 9.4pt; color: #1F5E4E; margin: 1.2mm 0 1mm; }
.step .tip { margin-top: 1.6mm; padding-top: 1.6mm; border-top: 1px dashed #D5E0DC; color: #6B7280; font-size: 8.1pt; }
.cmp td:first-child { width: 19%; font-size: 7.6pt; letter-spacing: .07em; text-transform: uppercase; color: #6B7280; font-weight: 700; background: #F3F8F6 !important; }
.cmp th:nth-child(3) { background: #5B6770; }
.cmp th:first-child { background: #fff; }
.cmp td { width: 40.5%; }
.vs { display: grid; grid-template-columns: 1fr 1fr; gap: 3mm; }
.vs .col { border: 1px solid #E3E8E6; }
.vs .head { padding: 2.6mm 3.6mm; font-weight: 700; font-size: 10.5pt; color: #fff; background: #2F6656; }
.vs .col.b .head { background: #5B6770; }
.vs .row { padding: 2.1mm 3.6mm; border-top: 1px solid #EEF1F0; font-size: 9pt; line-height: 1.42; }
.vs .row:first-of-type { border-top: 0; }
.vs .lbl { font-size: 7.4pt; letter-spacing: .08em; text-transform: uppercase; color: #8A8A8A; font-weight: 700; }
.note { margin-top: 3mm; padding: 2.8mm 4mm; background: #F3F8F6; border-left: 3px solid #2F6656; font-size: 9.4pt; }
table { width: 100%; border-collapse: collapse; font-size: 8.7pt; line-height: 1.38; }
th { background: #2F6656; color: #fff; text-align: left; font-size: 7.4pt; letter-spacing: .07em; text-transform: uppercase; padding: 1.7mm 3mm; font-weight: 700; }
td { padding: 1.45mm 3mm; border-bottom: 1px solid #E8ECEA; vertical-align: top; }
tr:nth-child(even) td { background: #F7F9F8; }
tr { break-inside: avoid; }
td.topic { font-weight: 700; color: #1F5E4E; width: 24%; }
td.q, .q { width: 36%; }
.bubble { display: inline-block; background: #EEF0FB; border: 1px solid #DADDF5; border-radius: 10px 10px 10px 2px; padding: .7mm 2.4mm; color: #2B2E6B; font-size: 8.5pt; }
ul { margin: 0; padding: 0; list-style: none; }
li { position: relative; padding: 1.1mm 0 1.1mm 5mm; border-bottom: 1px solid #EEF1F0; font-size: 9pt; line-height: 1.4; }
li::before { content: ""; position: absolute; left: 0; top: 2.7mm; width: 6px; height: 6px; background: #2F6656; }
ul.no li::before { background: #A15C38; }
.chips { display: flex; flex-wrap: wrap; gap: 1.6mm 2mm; margin-top: 1mm; }
.two { display: grid; grid-template-columns: 1fr 1fr; gap: 6mm; }
.alert { padding: 3.2mm 4.2mm; font-size: 9pt; line-height: 1.42; background: #FBF5F1; border: 1px solid #EBD9CF; border-left: 4px solid #A15C38; }
.alert .t { font-weight: 700; font-size: 11pt; color: #7B4437; margin-bottom: 1.2mm; }
.alert ol { margin: 1.6mm 0 0; padding-left: 4.5mm; font-size: 8.8pt; }
.alert li { border: 0; padding: .3mm 0; }
.alert li::before { display: none; }
.two { align-items: start; }
.foot { display: none; position: absolute; left: 16mm; right: 16mm; bottom: 7mm; display: flex; justify-content: space-between; font-size: 7.6pt; color: #9AA3A0; border-top: 1px solid #E3E8E6; padding-top: 2mm; }
.grp { margin-top: 4mm; }
.grp table td:first-child { width: 6%; color: #9AA3A0; font-weight: 700; }
.grp td.q { width: 54%; }
"""
SPARK = '<svg viewBox="0 0 24 24" fill="#fff"><path d="M10 3l1.8 4.7L16.5 9.5l-4.7 1.8L10 16l-1.8-4.7L3.5 9.5l4.7-1.8z"/><path d="M17.5 13l1 2.5 2.5 1-2.5 1-1 2.5-1-2.5-2.5-1 2.5-1z"/></svg>'

def doc(cfg, tag):
    what, where = cfg["what"]
    steps = "".join(
        f'<div class="step"><div class="num">{i+1}</div><div class="t">{e(a.split(". ",1)[1])}</div>{e(b)}<div class="tip">{e(c)}</div></div>'
        for i, (a, b, c) in enumerate(cfg["steps"]))
    cmp = "".join(f"<tr><td>{e(r[0])}</td><td>{e(r[1])}</td><td>{e(r[2])}</td></tr>" for r in cfg["two"])
    colA = "".join(f'<div class="row"><div class="lbl">{e(r[0])}</div>{e(r[1])}</div>' for r in cfg["two"])
    colB = "".join(f'<div class="row"><div class="lbl">{e(r[0])}</div>{e(r[2])}</div>' for r in cfg["two"])
    can = "".join(f'<tr><td class="topic">{e(a)}</td><td>{e(b)}</td><td class="q"><span class="bubble">{e(c)}</span></td></tr>' for a, b, c in cfg["can"])
    ex = "".join(f'<span class="bubble">{e(x)}</span>' for x in cfg["excel_ex"])
    cant = "".join(f"<li>{e(x)}</li>" for x in cfg["cant"])
    send = "".join(f"<li>{e(x)}</li>" for x in SEND)
    groups = "".join(
        f'<div class="grp"><h2><span class="n">{k+1:02d}</span>{e(g)}</h2><table><tr><th>№</th><th>Вопрос</th><th>Что получите</th></tr>'
        + "".join(f'<tr><td>{i+1}</td><td class="q"><span class="bubble">{e(a)}</span></td><td>{e(b)}</td></tr>' for i, (a, b) in enumerate(items))
        + "</table></div>" for k, (g, items) in enumerate(cfg["examples"]))
    foot = lambda n: f'<div class="foot"><span>{e(cfg["title"])} · инструкция</span><span>{n}</span></div>'
    return f"""<!doctype html><html lang="ru"><head><meta charset="utf-8"><style>{CSS}</style></head><body>
<div class="page">
  <div class="cover"><div class="logo">{SPARK}</div><div><div class="kicker">Инструкция</div><h1>{e(cfg['title'])}</h1><div class="sub">{e(cfg['sub'])}</div></div></div>
  <section><h2><span class="n">01</span>Что это и где найти</h2><p class="lead">{e(what)}</p>
    <div class="where"><div class="dot">{SPARK}</div><div>{e(where)}</div></div></section>
  <section><h2><span class="n">02</span>Как задать вопрос</h2><div class="steps">{steps}</div></section>
  <section><h2><span class="n">03</span>{e(cfg['two_title'])}</h2><p class="lead">{e(cfg['two_lead'])}</p>
    <table class="cmp"><tr><th></th><th>Как на сайте WB</th><th>Управленческие (мэн пак)</th></tr>{cmp}</table>
    <div class="note">{e(cfg['two_tip'])}</div></section>
  
</div>
<div class="page brk">
  <section style="margin-top:0"><h2><span class="n">04</span>Что умеет помощник</h2><table><tr><th>Тема</th><th>Что можно спросить</th><th>Пример вопроса</th></tr>{can}</table></section>
  <section><h2><span class="n">05</span>Выгрузки в Excel</h2><p>{e(cfg['excel'][0])}</p><p class="lead">{e(cfg['excel'][1])}</p><div class="chips">{ex}</div></section>
  <section class="two"><div><h2><span class="n">06</span>Чего помощник не делает</h2><ul class="no">{cant}</ul></div>
  <div><h2><span class="n">07</span>Если помощник ошибся</h2><div class="alert"><div class="t">Напишите Дарье в Telegram</div>{e(CONTACT)}<div style="margin-top:1.6mm;font-weight:700">Что прислать:</div><ol>{send}</ol></div></div></section>
  
</div>
<div class="page brk">
  <div class="cover small"><div class="logo">{SPARK}</div><div><h1>Примеры вопросов</h1><div class="sub">Можно копировать и менять период, бренд или контрагента</div></div></div>
  {groups}
  <div class="note" style="margin-top:4mm">Пишите своими словами — точные формулировки не обязательны. Главное — период и что именно посчитать. Помощник работает в тестовом режиме: важные цифры перед отправкой руководству сверяйте с дашбордом.</div>
  
</div></body></html>"""

async def main():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page()
        for cfg, name in ((SALES, "Продажи"), (FIN, "Финансы")):
            h = doc(cfg, name)
            open(f"{name}.html", "w").write(h)
            await pg.set_content(h)
            await pg.pdf(path=f"/mnt/user-data/outputs/Инструкция_ИИ-помощник_{name}.pdf", format="A4", print_background=True, prefer_css_page_size=True, scale=0.88, display_header_footer=True, header_template="<span></span>",
                footer_template=f'<div style="width:100%;padding:0 16mm;font-family:Liberation Sans,Arial;font-size:7pt;color:#9AA3A0;display:flex;justify-content:space-between"><span>{cfg["title"]} · инструкция</span><span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>')
        await b.close()
asyncio.run(main())
