#!/usr/bin/env python3
"""Loads the two raw source files and the generated ticket history straight
into Postgres. This simulates the "landing" step before any matching or
cleanup happens — the data goes in exactly as messy as it came out of
generate_data.py."""
import csv
import json
from pathlib import Path

import psycopg2

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DSN = "host=localhost dbname=cockpit user=postgres password=cockpit_dev"


def main():
    conn = psycopg2.connect(DSN)
    cur = conn.cursor()

    with open(DATA_DIR / "crm_kunden.csv", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = [(r["kunden_nr"], r["firmenname"], r["uid"] or None, r["email"] or None, r["land"] or None)
                for r in reader]
    cur.executemany(
        "INSERT INTO crm_kunde (kunden_nr, firmenname, uid, email, land) VALUES (%s,%s,%s,%s,%s)",
        rows,
    )
    print(f"crm_kunde: inserted {len(rows)}")

    with open(DATA_DIR / "ticket_kunden.json", encoding="utf-8") as f:
        ticket_kunden = json.load(f)
    rows = [(r["customer_id"], r["company"], r["vat"], r["contact"]) for r in ticket_kunden]
    cur.executemany(
        "INSERT INTO ticket_kunde (customer_id, company, vat, contact) VALUES (%s,%s,%s,%s)",
        rows,
    )
    print(f"ticket_kunde: inserted {len(rows)}")

    with open(DATA_DIR / "tickets.json", encoding="utf-8") as f:
        tickets = json.load(f)
    rows = [(
        t["ticket_customer_id"], t["betreff"], t["beschreibung"], t["kategorie"], t["kanal"],
        t["prioritaet"], t["erstellt_am"], t["erste_antwort_am"], t["geloest_am"],
        t["wiedereroeffnet"], t["sla_frist"],
    ) for t in tickets]
    cur.executemany(
        """INSERT INTO ticket (ticket_customer_id, betreff, beschreibung, kategorie, kanal,
                                prioritaet, erstellt_am, erste_antwort_am, geloest_am,
                                wiedereroeffnet, sla_frist)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        rows,
    )
    print(f"ticket: inserted {len(rows)}")

    conn.commit()
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
