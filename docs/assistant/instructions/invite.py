"""Приглашения в Telegram-ботов: компактная карточка A5 (альбом), бело-красный стиль.
python invite.py  →  два PDF. Нужны playwright (chromium) и reportlab (QR)."""
import html, asyncio, sys
from reportlab.graphics.barcode.qr import QrCodeWidget
e = html.escape
OUT = sys.argv[1] if len(sys.argv) > 1 else "/mnt/user-data/outputs"
RED, DARK = "#B01E28", "#1A1A1A"


def qr_svg(url):
    q = QrCodeWidget(url, barLevel="M").qr
    q.make()
    n = q.getModuleCount()
    cells = "".join(f'<rect x="{c}" y="{r}" width="1.02" height="1.02"/>'
                    for r in range(n) for c in range(n) if q.modules[r][c])
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-2 -2 {n + 4} {n + 4}" fill="{DARK}"><rect x="-2" y="-2" width="{n + 4}" height="{n + 4}" fill="#fff"/>{cells}</svg>'


CSS = f"""
@page {{ size: 210mm 148mm; margin: 0; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; font-family: 'Liberation Sans', Arial, sans-serif; color: {DARK}; font-size: 10.5pt; line-height: 1.45; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
.page {{ width: 210mm; height: 147.5mm; overflow: hidden; padding: 10mm 13mm 8mm; display: flex; flex-direction: column; }}
.top {{ display: flex; justify-content: space-between; align-items: flex-end; border-bottom: 3px solid {RED}; padding-bottom: 3mm; }}
.brand {{ color: {RED}; font-weight: 700; font-size: 18pt; letter-spacing: .06em; line-height: 1; transform: scaleX(1.18); transform-origin: left; }}
.tag {{ color: {RED}; font-weight: 700; font-size: 8pt; letter-spacing: .16em; text-transform: uppercase; }}
.main {{ display: flex; gap: 9mm; margin-top: 6mm; flex: 1; }}
.left {{ flex: 1; display: flex; flex-direction: column; }}
h1 {{ margin: 0 0 2mm; font-size: 23.5pt; line-height: 1.1; font-weight: 700; letter-spacing: -.01em; }}
.lead {{ margin: 0 0 5mm; font-size: 12pt; color: #444; }}
.ask {{ display: grid; grid-template-columns: 1fr 1fr; gap: 0 6mm; }}
.ask div {{ padding: 2.3mm 0 2.3mm 4.6mm; border-bottom: 1px solid #EEE; position: relative; font-size: 11.5pt; }}
.ask div::before {{ content: ""; position: absolute; left: 0; top: 4.5mm; width: 2.1mm; height: 2.1mm; background: {RED}; }}
.know {{ margin-top: auto; background: #F1F1F1; padding: 3mm 4.5mm; font-size: 10pt; line-height: 1.45; color: #333; }}
.eg {{ margin-top: 5mm; font-size: 11pt; font-style: italic; color: #555; border-left: 3px solid {RED}; padding-left: 4mm; }}
.know b {{ color: {DARK}; }}
.right {{ flex: none; width: 56mm; background: {RED}; color: #fff; padding: 5mm; display: flex; flex-direction: column; align-items: center; text-align: center; }}
.right .k {{ font-size: 8pt; font-weight: 700; letter-spacing: .16em; text-transform: uppercase; opacity: .85; }}
.qr {{ background: #fff; padding: 1.5mm; margin: 3mm 0; width: 44mm; height: 44mm; }}
.qr svg {{ width: 100%; height: 100%; display: block; }}
.right a {{ color: #fff; font-weight: 700; font-size: 12pt; text-decoration: none; }}
.steps {{ margin-top: auto; padding-top: 3mm; border-top: 1px solid rgba(255,255,255,.35); font-size: 10pt; line-height: 1.6; text-align: left; width: 100%; }}
.steps b {{ display: inline-block; width: 4.5mm; }}
"""

KNOW = ("<b>Отвечает по очереди</b> — если вопросов много, ответ придёт чуть позже. "
        "<b>С 23:20 до 23:57 мск</b> обновляются данные, бот не отвечает.")
DOCS = {
    "Продажи": dict(url="https://t.me/tr_sales_bot", nick="t.me/tr_sales_bot",
                    title="ИИ-помощник по продажам", lead="Спросите про продажи на Wildberries обычными словами — прямо в Telegram.",
                    ask=["Продажи и возвраты", "Топ брендов и артикулов",
                         "Маржа по категориям", "Что продаётся в убыток"], eg="Топ-10 брендов за прошлую неделю"),
    "Финансы": dict(url="https://t.me/tr_finance_bot", nick="t.me/tr_finance_bot",
                    title="Финансовый ИИ-помощник", lead="Спросите про финансы компании обычными словами — прямо в Telegram.",
                    ask=["Прибыль и безубыточность", "Деньги на счетах",
                         "Займы и сроки погашения", "Договоры и контрагенты"], eg="Сколько денег на счетах?"),
}


def doc(name, c):
    return f"""<!doctype html><html lang="ru"><head><meta charset="utf-8"><style>{CSS}</style></head><body><div class="page">
<div class="top"><div class="brand">TRENDSETTER</div><div class="tag">ИИ-помощник · {e(name)}</div></div>
<div class="main">
 <div class="left">
  <h1>{e(c['title'])}</h1><p class="lead">{e(c['lead'])}</p>
  <div class="ask">{''.join(f'<div>{e(x)}</div>' for x in c['ask'])}</div>
  <div class="ask" style="grid-template-columns:1fr"><div>Любой расчёт пришлёт файлом Excel</div></div>
  <div class="eg">Например: «{e(c['eg'])}»</div>
  <div class="know">{KNOW}</div>
 </div>
 <div class="right">
  <div class="k">Открыть бота</div>
  <div class="qr">{qr_svg(c['url'])}</div>
  <a href="{c['url']}">{c['nick']}</a>
  <div class="steps"><b>1</b>Откройте бота<br><b>2</b>Нажмите «Старт»<br><b>3</b>Ждите подтверждения</div>
 </div>
</div></div></body></html>"""


async def main():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page()
        for name, c in DOCS.items():
            await pg.set_content(doc(name, c))
            await pg.pdf(path=f"{OUT}/Приглашение_ИИ-помощник_{name}.pdf", print_background=True, prefer_css_page_size=True)
        await b.close()
asyncio.run(main())
