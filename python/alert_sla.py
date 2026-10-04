#!/usr/bin/env python3
"""
alert_sla.py — the logic behind the daily automation step.

Honesty note: the build plan calls for this to run as a scheduled Power
Automate or n8n flow. Neither is available to actually wire up inside
this sandbox (no tenant, no n8n instance), so this script is the exact
query-and-condition logic that flow would run, runnable on its own or
from cron — which is also, concretely, what the flow's "action" step
would call out to if it were built. It prints what the flow's Teams/
email step would send; swapping the print() calls for an actual webhook
POST is the only change needed to make this a real scheduled flow.

Two branches, same as the plan:
  1. open tickets within 4 hours of SLA breach -> one alert per ticket
  2. anything rejected by the last ingest run, or sitting in
     ticket_klassifikation with status='zur_pruefung' -> a data-quality digest
"""
import psycopg2

DSN = "host=localhost dbname=cockpit user=postgres password=cockpit_dev"


def check_sla_warnings(cur):
    cur.execute("""
        SELECT ticket_id, ticket_customer_id, kategorie, prioritaet, sla_rest_stunden
        FROM v_sla_verletzung
        WHERE sla_rest_stunden BETWEEN 0 AND 4
        ORDER BY sla_rest_stunden
    """)
    rows = cur.fetchall()
    print(f"[Zweig 1: SLA-Warnung] {len(rows)} Ticket(s) mit weniger als 4 Stunden Restzeit")
    for ticket_id, kunde_id, kategorie, prioritaet, rest in rows[:10]:
        print(f"  -> Teams-Nachricht: Ticket #{ticket_id} (Kunde {kunde_id}, {kategorie}, "
              f"{prioritaet}) — noch {rest:.1f} Std. bis SLA-Frist")
    if len(rows) > 10:
        print(f"  ... und {len(rows) - 10} weitere")
    return len(rows)


def check_data_quality(cur):
    cur.execute("""
        SELECT zeilen_abgelehnt FROM ingest_log ORDER BY gestartet_am DESC LIMIT 1
    """)
    row = cur.fetchone()
    letzte_ablehnungen = row[0] if row else 0

    cur.execute("SELECT count(*) FROM ticket_klassifikation WHERE status = 'zur_pruefung'")
    zur_pruefung = cur.fetchone()[0]

    print(f"\n[Zweig 2: Datenqualitaet] letzter Ingest-Lauf: {letzte_ablehnungen} abgelehnte Zeile(n)")
    print(f"  Klassifikationen mit Status 'zur_pruefung': {zur_pruefung}")
    if letzte_ablehnungen > 0 or zur_pruefung > 0:
        print(f"  -> Mail an Datenqualitaet: {letzte_ablehnungen} Ablehnung(en), "
              f"{zur_pruefung} Fall/Faelle zur manuellen Pruefung")
    else:
        print("  -> keine Meldung (Bedingung: nur bei Treffern)")
    return letzte_ablehnungen, zur_pruefung


def main():
    conn = psycopg2.connect(DSN)
    cur = conn.cursor()
    check_sla_warnings(cur)
    check_data_quality(cur)
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
