#!/usr/bin/env python3
"""
build_dashboard.py — renders the three dashboard pages as static images
straight from the live PostgreSQL views.

Honesty note: the build plan calls for Power BI or Looker Studio
connected live to PostgreSQL. Neither is available in this sandbox (no
desktop Power BI, no Google account to provision Looker Studio against
a database only this session can reach), so these are rendered directly
from the same views Power BI or Looker Studio would query — real numbers
from the real database, just drawn with matplotlib instead of a BI tool.
Pointing either tool at this same PostgreSQL instance later needs no
changes to the SQL below it.
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import psycopg2

DSN = "host=localhost dbname=cockpit user=postgres password=cockpit_dev"
IMG_DIR = Path(__file__).resolve().parent.parent / "images"
IMG_DIR.mkdir(exist_ok=True)

NAVY = "#0f2942"
ACCENT = "#2f6fed"
PASS = "#16794f"
WARN = "#9a5b00"
MUTED = "#5a6676"


def fetch_df(cur, sql):
    cur.execute(sql)
    cols = [d[0] for d in cur.description]
    return cols, cur.fetchall()


def page_overview(cur):
    cur.execute("SELECT count(*) FROM ticket")
    total = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM ticket WHERE geloest_am IS NULL")
    offen = cur.fetchone()[0]
    cur.execute("SELECT round(100.0*count(*) FILTER (WHERE sla_verletzt)/count(*),1) FROM v_sla_verletzung")
    sla_quote = cur.fetchone()[0]
    cur.execute("SELECT round(percentile_cont(0.5) WITHIN GROUP (ORDER BY median_minuten)) FROM v_erstreaktion")
    cur.execute("SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (erste_antwort_am-erstellt_am))/60) FROM ticket WHERE erste_antwort_am IS NOT NULL")
    median_erst = cur.fetchone()[0]

    cur.execute("""
        SELECT date_trunc('week', erstellt_am)::date AS woche, count(*) AS n
        FROM ticket GROUP BY 1 ORDER BY 1
    """)
    weeks = cur.fetchall()

    fig = plt.figure(figsize=(11, 6.2), facecolor="white")
    fig.suptitle("Überblick", fontsize=15, fontweight="bold", color=NAVY, x=0.03, ha="left")

    stats = [
        ("Tickets gesamt", f"{total:,}"),
        ("Offen", f"{offen}"),
        ("SLA-Verletzungsquote", f"{sla_quote}%"),
        ("Median Erstreaktion", f"{median_erst:.0f} Min"),
    ]
    for i, (label, value) in enumerate(stats):
        ax = fig.add_axes([0.03 + i * 0.245, 0.68, 0.22, 0.18])
        ax.axis("off")
        ax.text(0, 0.55, value, fontsize=22, fontweight="bold", color=NAVY)
        ax.text(0, 0.05, label, fontsize=10, color=MUTED)
        ax.add_patch(plt.Rectangle((0, 0), 1, 1, transform=ax.transAxes, fill=False,
                                     edgecolor="#e3e8ef", linewidth=1))

    ax2 = fig.add_axes([0.06, 0.1, 0.9, 0.48])
    xs = [w[0] for w in weeks]
    ys = [w[1] for w in weeks]
    ax2.plot(xs, ys, color=ACCENT, linewidth=2)
    ax2.fill_between(xs, ys, color=ACCENT, alpha=0.08)
    ax2.set_title("Tickets pro Woche, letzte 6 Monate", fontsize=11, color=MUTED, loc="left")
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    ax2.spines[["top", "right"]].set_visible(False)
    ax2.tick_params(colors=MUTED, labelsize=9)

    fig.savefig(IMG_DIR / "dashboard-overview.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def page_betrieb(cur):
    cur.execute("""
        SELECT kategorie, kanal, count(*) AS n
        FROM ticket GROUP BY kategorie, kanal
    """)
    rows = cur.fetchall()
    cats = sorted({r[0] for r in rows})
    kanaele = sorted({r[1] for r in rows})
    data = {k: [0] * len(cats) for k in kanaele}
    for kat, kanal, n in rows:
        data[kanal][cats.index(kat)] = n

    fig, ax = plt.subplots(figsize=(11, 5.2), facecolor="white")
    fig.suptitle("Betrieb — Backlog nach Kategorie und Kanal", fontsize=15, fontweight="bold",
                 color=NAVY, x=0.03, ha="left", y=0.98)
    bottom = [0] * len(cats)
    colors = [NAVY, ACCENT, "#6fa0f0", "#b8cdf2"]
    for i, kanal in enumerate(kanaele):
        ax.bar(cats, data[kanal], bottom=bottom, label=kanal, color=colors[i % len(colors)])
        bottom = [b + v for b, v in zip(bottom, data[kanal])]
    ax.set_xticklabels(cats, rotation=20, ha="right", fontsize=9)
    ax.legend(frameon=False, fontsize=9, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.18))
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(colors=MUTED)
    fig.subplots_adjust(top=0.85, bottom=0.28)
    fig.savefig(IMG_DIR / "dashboard-betrieb.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def page_datenqualitaet(cur):
    cur.execute("SELECT match_methode, count(*) FROM kunde_mapping GROUP BY match_methode")
    methoden = cur.fetchall()
    cur.execute("SELECT count(*) FROM crm_kunde WHERE kunden_nr NOT IN (SELECT crm_kunden_nr FROM kunde_mapping)")
    crm_offen = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM ticket_kunde WHERE customer_id NOT IN (SELECT ticket_customer_id FROM kunde_mapping)")
    ticket_offen = cur.fetchone()[0]
    cur.execute("SELECT status, count(*) FROM ticket_klassifikation GROUP BY status")
    status_counts = dict(cur.fetchall())

    fig = plt.figure(figsize=(11, 5.2), facecolor="white")
    fig.suptitle("Datenqualität", fontsize=15, fontweight="bold", color=NAVY, x=0.03, ha="left")

    ax1 = fig.add_axes([0.05, 0.15, 0.4, 0.68])
    labels = [f"{m}\n(Konf. {('1.00' if m=='uid' else '0.95' if m=='email' else '0.70')})" for m, _ in methoden]
    values = [c for _, c in methoden]
    ax1.bar(labels, values, color=[NAVY, ACCENT, "#9fc0f5"])
    ax1.set_title("Mapping nach Methode", fontsize=11, color=MUTED, loc="left")
    ax1.spines[["top", "right"]].set_visible(False)
    ax1.tick_params(colors=MUTED, labelsize=8)

    ax2 = fig.add_axes([0.55, 0.15, 0.4, 0.68])
    auto = status_counts.get("automatisch_gesetzt", 0)
    review = status_counts.get("zur_pruefung", 0)
    ax2.pie([auto, review], labels=["automatisch gesetzt", "zur Prüfung"],
            colors=[PASS, WARN], autopct="%1.0f%%", startangle=90,
            wedgeprops={"edgecolor": "white", "linewidth": 2},
            textprops={"fontsize": 9, "color": MUTED})
    ax2.set_title("KI-Vorkategorisierung nach Schwellenwert 0,85", fontsize=11, color=MUTED, loc="left")

    fig.text(0.05, 0.02, f"Nicht zugeordnet: {crm_offen} CRM-Kunden, {ticket_offen} Ticket-System-Kunden",
              fontsize=9, color=MUTED)

    fig.savefig(IMG_DIR / "dashboard-datenqualitaet.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def main():
    conn = psycopg2.connect(DSN)
    cur = conn.cursor()
    page_overview(cur)
    page_betrieb(cur)
    page_datenqualitaet(cur)
    cur.close()
    conn.close()
    print("geschrieben: images/dashboard-overview.png, dashboard-betrieb.png, dashboard-datenqualitaet.png")


if __name__ == "__main__":
    main()
