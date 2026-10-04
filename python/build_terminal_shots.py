#!/usr/bin/env python3
"""build_terminal_shots.py — renders two terminal-style screenshots used
in the case study: the mapping report (sql/03_abgleich.sql) and the
classification run (python/klassifikation.py), captured from the real
output of each, not hand-typed."""
import subprocess
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
IMG_DIR = ROOT / "images"


def render_terminal(lines, out_path, title, width_chars=100):
    n = len(lines)
    fig_h = 0.34 * n + 0.9
    fig, ax = plt.subplots(figsize=(11.5, fig_h), facecolor="#0f1117")
    ax.set_facecolor("#0f1117")
    ax.axis("off")
    ax.text(0.015, 1 - 0.35 / fig_h, title, transform=ax.transAxes, color="#8fa6c9",
             fontsize=10.5, family="monospace", va="top")
    y0 = 1 - 0.75 / fig_h
    line_h = 0.34 / fig_h
    for i, line in enumerate(lines):
        color = "#d7e0ee"
        if line.startswith("$"):
            color = "#7fd99a"
        elif "PASS" in line or "Bestanden" in line:
            color = "#7fd99a"
        ax.text(0.015, y0 - i * line_h, line, transform=ax.transAxes, color=color,
                 fontsize=9.6, family="monospace", va="top")
    fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="#0f1117")
    plt.close(fig)
    print(f"geschrieben: {out_path}")


def main():
    env_prefix = "PGPASSWORD=cockpit_dev psql -U postgres -h localhost -d cockpit"

    out = subprocess.run(
        f"{env_prefix} -c \"SELECT match_methode, count(*) AS anzahl, konfidenz FROM kunde_mapping GROUP BY match_methode, konfidenz ORDER BY konfidenz DESC;\"",
        shell=True, capture_output=True, text=True,
    ).stdout
    out2 = subprocess.run(
        f"{env_prefix} -c \"SELECT (SELECT count(*) FROM crm_kunde) crm_kunde_gesamt, (SELECT count(*) FROM ticket_kunde) ticket_kunde_gesamt, (SELECT count(*) FROM kunde_mapping) mappings_gesamt, (SELECT count(*) FROM crm_kunde WHERE kunden_nr NOT IN (SELECT crm_kunden_nr FROM kunde_mapping)) crm_offen, (SELECT count(*) FROM ticket_kunde WHERE customer_id NOT IN (SELECT ticket_customer_id FROM kunde_mapping)) ticket_offen;\"",
        shell=True, capture_output=True, text=True,
    ).stdout

    lines = ["$ psql -d cockpit -f sql/03_abgleich.sql", ""] + out.strip("\n").split("\n")
    lines += ["", "-- Zusammenfassung --"] + out2.strip("\n").split("\n")
    render_terminal(lines, IMG_DIR / "mapping-report.png", "sql/03_abgleich.sql")

    result = subprocess.run(
        "cd " + str(ROOT) + " && python3 python/klassifikation.py",
        shell=True, capture_output=True, text=True,
    )
    lines2 = ["$ python3 python/klassifikation.py", ""] + result.stdout.strip("\n").split("\n")
    render_terminal(lines2, IMG_DIR / "klassifikation-run.png", "python/klassifikation.py")


if __name__ == "__main__":
    main()
