# gear/app/daily_sales/assistant/digest_charts.py
"""Картинки для утренней сводки: PNG в памяти, под экран телефона."""
from __future__ import annotations

import io

GREEN, MID, PALE, WARM = "#1F5E4E", "#7FA89B", "#CBD9D4", "#B45309"
INK, MUTED, GRID, AXIS = "#1F1F1F", "#6B7280", "#E6EBE9", "#9AA3A0"
WD = ("пн", "вт", "ср", "чт", "пт", "сб", "вс")


def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 15})
    return plt


def _png(plt, fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor="white")
    plt.close(fig)
    return buf.getvalue()


def _head(fig, title, sub, y=0.94):
    fig.text(0.06, y, title, fontsize=23, fontweight="bold", color=INK)
    fig.text(0.06, y - 0.047, sub, fontsize=13.5, color=MUTED)


def _num(v, d=0):
    return f"{v:,.{d}f}".replace(",", " ").replace(".", ",").replace("-", "−")


def _clean(ax):
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0)


def sales_days(days, values, title, sub) -> bytes:
    """Столбики по дням (млн ₽): последний день выделен, тот же день недели назад — тоном."""
    plt = _plt()
    n = len(days)
    fig, ax = plt.subplots(figsize=(10.8, 7.6), dpi=100)
    colors = [PALE] * n
    colors[-1] = GREEN
    if n > 7:
        colors[-8] = MID
    ax.bar(range(n), values, width=0.72, color=colors)
    top = max(values) or 1
    ax.set_xlim(-0.7, n - 0.3)
    ax.set_ylim(0, top * 1.16)
    ax.set_xticks(range(n))
    ax.set_xticklabels([f"{WD[d.weekday()]}\n{d:%d.%m}" for d in days], color=MUTED, fontsize=13)
    for i, d in enumerate(days):
        if d.weekday() >= 5:
            ax.get_xticklabels()[i].set_color(WARM)
    ax.yaxis.set_major_locator(plt.MaxNLocator(4))
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:g}".replace(".", ","))
    ax.tick_params(axis="y", labelcolor=MUTED, labelsize=13)
    ax.yaxis.grid(True, color=GRID, lw=1)
    ax.set_axisbelow(True)
    _clean(ax)
    ax.text(n - 1, values[-1] + top * 0.02, _num(values[-1], 2), ha="center", va="bottom",
            fontsize=17, fontweight="bold", color=INK)
    if n > 7:
        ax.text(n - 8, values[-8] + top * 0.02, _num(values[-8], 2), ha="center", va="bottom",
                fontsize=15, color=MUTED)
    _head(fig, title, sub)
    fig.subplots_adjust(left=0.07, right=0.95, top=0.84, bottom=0.12)
    return _png(plt, fig)


def brands(rows, title, sub) -> bytes:
    """rows: [(бренд, изменение в ₽)], рост вправо, падение влево."""
    plt = _plt()
    rows = sorted(rows, key=lambda r: -r[1])
    fig, ax = plt.subplots(figsize=(10.8, 1.6 + 0.85 * len(rows)), dpi=100)
    m = max(abs(v) for _, v in rows) or 1
    for i, (name, v) in enumerate(rows):
        y = len(rows) - 1 - i
        ax.barh(y, v, height=0.6, color=GREEN if v > 0 else WARM)
        money = ("+" if v > 0 else "−") + (_num(abs(v) / 1000) + " тыс ₽")
        name = name if len(name) <= 22 else name[:21] + "…"
        ax.text(v + (m * 0.03 if v > 0 else -m * 0.03), y, money, va="center",
                ha="left" if v > 0 else "right", fontsize=15, fontweight="bold", color=INK)
        ax.text(-m * 0.04 if v > 0 else m * 0.04, y, name, va="center",
                ha="right" if v > 0 else "left", fontsize=14, color=INK)
    ax.axvline(0, color=AXIS, lw=1)
    ax.set_xlim(-m * 1.8, m * 1.8)
    ax.set_ylim(-0.7, len(rows) - 0.3)
    ax.axis("off")
    h = fig.get_figheight()
    _head(fig, title, sub, y=1 - 0.42 / h)
    fig.subplots_adjust(left=0.04, right=0.96, top=1 - 1.25 / h, bottom=0.03)
    return _png(plt, fig)


def stocks(days, totals, parts, title, sub) -> bytes:
    """Линия общего остатка (шт) и состав: parts = [(место, шт, изменение за неделю | None)]."""
    plt = _plt()
    fig = plt.figure(figsize=(10.8, 9.2), dpi=100)
    ax = fig.add_axes([0.08, 0.47, 0.85, 0.35])
    xs, ys = range(len(days)), [t / 1000 for t in totals]
    ax.plot(xs, ys, color=GREEN, lw=2.5, solid_capstyle="round")
    ax.scatter([xs[-1]], [ys[-1]], s=110, color=GREEN, zorder=3, edgecolors="white", linewidths=2)
    lo, hi = min(ys), max(ys)
    pad = max((hi - lo) * 0.35, hi * 0.02, 0.5)
    ax.set_ylim(lo - pad, hi + pad * 1.5)
    ax.set_xlim(-0.4, len(days) - 0.4)
    ax.text(xs[-1], ys[-1] + pad * 0.35, _num(ys[-1], 1), ha="center", fontsize=17,
            fontweight="bold", color=INK)
    if len(days) > 7:
        ax.scatter([xs[-8]], [ys[-8]], s=70, color=MID, zorder=3, edgecolors="white", linewidths=2)
        ax.text(xs[-8], ys[-8] + pad * 0.35, _num(ys[-8], 1), ha="center", fontsize=14, color=MUTED)
    step = 2 if len(days) > 8 else 1
    ax.set_xticks(list(xs))
    ax.set_xticklabels([f"{d:%d.%m}" if (len(days) - 1 - i) % step == 0 else ""
                        for i, d in enumerate(days)], color=MUTED, fontsize=12.5)
    ax.yaxis.set_major_locator(plt.MaxNLocator(4))
    ax.tick_params(axis="y", labelcolor=MUTED, labelsize=12.5)
    ax.yaxis.grid(True, color=GRID, lw=1)
    ax.set_axisbelow(True)
    _clean(ax)

    ax2 = fig.add_axes([0.08, 0.04, 0.85, 0.33])
    parts = sorted(parts, key=lambda p: -p[1])
    mx = max(p[1] for p in parts) or 1
    for i, (name, v, ch) in enumerate(parts):
        y = len(parts) - 1 - i
        ax2.barh(y, v, height=0.56, color=MID)
        ax2.text(-mx * 0.02, y, name, va="center", ha="right", fontsize=14, color=INK)
        ax2.text(v + mx * 0.02, y, _num(v), va="center", ha="left", fontsize=15,
                 fontweight="bold", color=INK)
        if ch is not None:
            note = ("▲ " if ch > 0 else "▼ " if ch < 0 else "") + _num(abs(ch)) + " за неделю"
            ax2.text(v + mx * 0.22, y, note, va="center", ha="left", fontsize=13, color=MUTED)
    ax2.set_xlim(-mx * 0.42, mx * 1.65)
    ax2.set_ylim(-0.6, len(parts) - 0.4)
    ax2.axis("off")
    _head(fig, title, sub, y=0.945)
    fig.text(0.06, 0.845, f"Всего, тыс. шт · {len(days)} дн.", fontsize=13, fontweight="bold",
             color=INK)
    fig.text(0.06, 0.39, "Где лежит товар", fontsize=13, fontweight="bold", color=INK)
    return _png(plt, fig)


def margin(rows, avg, title, sub) -> bytes:
    """rows: [(бренд, маржа %, маржинальный доход ₽)], убыточные — влево."""
    plt = _plt()
    rows = sorted(rows, key=lambda r: -r[1])
    fig, ax = plt.subplots(figsize=(10.8, 1.9 + 0.85 * len(rows)), dpi=100)
    cap = lambda p: max(-60.0, min(80.0, p))            # выбросы не растягивают шкалу
    hi = max(max(cap(r[1]) for r in rows), avg, 5)
    lo = min(min(cap(r[1]) for r in rows), 0)
    span = hi - lo
    after = []                                           # сумма — сразу за процентом
    ax.set_xlim(lo - span * 0.42, hi + span * 0.42)
    ax.set_ylim(-0.7, len(rows) - 0.05)
    for i, (name, pct, md) in enumerate(rows):
        y = len(rows) - 1 - i
        p = cap(pct)
        ax.barh(y, p, height=0.58, color=GREEN if pct >= 0 else WARM)
        lab = _num(pct, 1) + "%"
        money = ("+" if md >= 0 else "−") + (
            _num(abs(md) / 1e6, 2) + " млн ₽" if abs(md) >= 1e6 else _num(abs(md) / 1e3) + " тыс ₽")
        name = name if len(name) <= 20 else name[:19] + "…"
        if pct >= 0:
            t = ax.text(p + span * 0.012, y, lab, va="center", ha="left", fontsize=15,
                        fontweight="bold", color=INK)
            after.append((t, y, money))
            ax.text(-span * 0.012, y, name, va="center", ha="right", fontsize=14, color=INK)
        else:
            ax.text(p - span * 0.012, y, lab, va="center", ha="right", fontsize=15,
                    fontweight="bold", color=INK)
            ax.text(span * 0.012, y, f"{name}   {money}", va="center", ha="left", fontsize=14,
                    color=INK)
    fig.subplots_adjust(left=0.03, right=0.97, top=1 - 1.3 / fig.get_figheight(), bottom=0.02)
    fig.canvas.draw()
    inv = ax.transData.inverted()
    for t, y, money in after:
        x1 = inv.transform((t.get_window_extent().x1, 0))[0]
        ax.text(x1 + span * 0.02, y, money, va="center", ha="left", fontsize=13, color=MUTED)
    ax.axvline(0, color=AXIS, lw=1)
    ax.axvline(avg, color=MUTED, lw=1, ls=(0, (4, 4)))
    ax.text(avg, len(rows) - 0.42, f"в среднем {_num(avg, 1)}%", ha="center", va="bottom",
            fontsize=12.5, color=MUTED)
    ax.axis("off")
    _head(fig, title, sub, y=1 - 0.45 / fig.get_figheight())
    return _png(plt, fig)
