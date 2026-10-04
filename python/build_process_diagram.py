#!/usr/bin/env python3
"""build_process_diagram.py — renders docs/prozess.png: the ticket
lifecycle from intake to resolution, including the branch point this
project is actually about (automatic vs. routed-to-review)."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

OUT = Path(__file__).resolve().parent.parent / "docs" / "prozess.png"

NAVY = "#0f2942"
ACCENT = "#2f6fed"
PASS = "#16794f"
WARN = "#9a5b00"
LINE = "#c7d2e0"
INK = "#1b2430"


def box(ax, x, y, w, h, text, fc="white", ec=NAVY, tc=INK, fontsize=10.5, weight="normal"):
    r = mpatches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.06",
                                 linewidth=1.4, edgecolor=ec, facecolor=fc)
    ax.add_patch(r)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fontsize,
             color=tc, weight=weight, wrap=True)


def arrow(ax, x1, y1, x2, y2, label=None, color=NAVY, style="-"):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=color, lw=1.4, linestyle=style))
    if label:
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 0.12, label, ha="center", fontsize=8.5, color="#5a6676")


def main():
    fig, ax = plt.subplots(figsize=(12, 6), facecolor="white")
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 6)
    ax.axis("off")

    box(ax, 0.3, 4.3, 1.9, 1.0, "Ticket kommt rein\n(E-Mail / Portal /\nTelefon / Chat)", fc="#eaf1fe", ec=ACCENT)
    box(ax, 2.9, 4.3, 2.0, 1.0, "Vorkategorisierung\n(Konfidenzwert)", fc="white")

    box(ax, 5.6, 5.1, 2.2, 0.85, "Konfidenz ≥ 0,85\n→ automatisch gesetzt", fc="#e9f7f0", ec=PASS, tc=PASS)
    box(ax, 5.6, 3.5, 2.2, 0.85, "Konfidenz < 0,85\n→ zur Prüfung", fc="#fff4e2", ec=WARN, tc=WARN)

    box(ax, 8.5, 4.3, 1.8, 1.0, "Bearbeitung\ndurch Mitarbeiter:in")
    box(ax, 8.5, 2.6, 1.8, 1.0, "SLA-Prüfung\n(Restzeit < 4 Std.\n→ Warnung)")
    box(ax, 5.6, 2.6, 1.8, 0.9, "Lösung")
    box(ax, 5.6, 1.1, 2.2, 0.9, "Wiedereröffnet?\n(rollierende Quote)", fc="#eaf1fe", ec=ACCENT)

    arrow(ax, 2.2, 4.8, 2.9, 4.8)
    arrow(ax, 4.9, 4.9, 5.6, 5.5)
    arrow(ax, 4.9, 4.7, 5.6, 3.95)
    arrow(ax, 7.8, 5.5, 8.5, 5.0)
    arrow(ax, 7.8, 3.95, 8.5, 4.6)
    arrow(ax, 9.4, 4.3, 9.4, 3.6, label="geloest_am gesetzt")
    arrow(ax, 8.5, 3.0, 7.4, 3.0, label="SLA eingehalten /\nverletzt")
    arrow(ax, 6.5, 2.6, 6.5, 2.0)
    arrow(ax, 6.0, 1.1, 2.0, 1.1, color="#9aa7b8", style="--")
    arrow(ax, 1.3, 1.5, 1.3, 4.3, label="neues Ticket,\nwenn wiedereröffnet", color="#9aa7b8", style="--")

    fig.suptitle("Ticket-Lebenszyklus", fontsize=14, fontweight="bold", color=NAVY, x=0.03, ha="left", y=0.98)
    fig.savefig(OUT, dpi=150, bbox_inches="tight")
    print(f"geschrieben: {OUT}")


if __name__ == "__main__":
    main()
