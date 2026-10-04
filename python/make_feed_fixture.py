#!/usr/bin/env python3
"""Builds data/eingang_feed.jsonl — a one-off fixture standing in for a
day's worth of incoming REST ticket records, with a handful of
deliberately broken rows mixed in (missing field, bad date, unknown
customer, malformed JSON) so ingest.py's rejection path is exercised by
real validation failures rather than asserted in the abstract."""
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

GOOD = [
    {"ticket_customer_id": 88213, "betreff": "Login klappt nicht", "beschreibung": "Komme nicht ins Portal.",
     "kategorie": "Zugriff_Login", "kanal": "email", "prioritaet": "hoch",
     "erstellt_am": "2026-10-02T09:15:00", "sla_frist": "2026-10-02T17:15:00"},
    {"ticket_customer_id": 88245, "betreff": "Rechnung falsch", "beschreibung": "Betrag auf Rechnung stimmt nicht.",
     "kategorie": "Rechnung_Zahlung", "kanal": "portal", "prioritaet": "normal",
     "erstellt_am": "2026-10-02T10:02:00", "sla_frist": "2026-10-03T10:02:00"},
    {"ticket_customer_id": 88317, "betreff": "Lieferung fehlt", "beschreibung": "Bestellung noch nicht angekommen.",
     "kategorie": "Auftrag_Bestellung", "kanal": "telefon", "prioritaet": "normal",
     "erstellt_am": "2026-10-02T11:40:00", "sla_frist": "2026-10-03T11:40:00"},
]

BROKEN = [
    # missing required field (betreff)
    {"ticket_customer_id": 88213, "beschreibung": "Fehlt der Betreff.", "kategorie": "Fehler_Stoerung",
     "kanal": "chat", "prioritaet": "normal", "erstellt_am": "2026-10-02T12:00:00",
     "sla_frist": "2026-10-03T12:00:00"},
    # unknown customer id (does not exist in ticket_kunde)
    {"ticket_customer_id": 999999, "betreff": "Unbekannter Kunde", "beschreibung": "Test.",
     "kategorie": "Frage_Nutzung", "kanal": "email", "prioritaet": "niedrig",
     "erstellt_am": "2026-10-02T12:10:00", "sla_frist": "2026-10-05T12:10:00"},
    # bad date format
    {"ticket_customer_id": 88245, "betreff": "Datum kaputt", "beschreibung": "Testfall fuer Datumsformat.",
     "kategorie": "Reklamation", "kanal": "portal", "prioritaet": "hoch",
     "erstellt_am": "02.10.2026", "sla_frist": "2026-10-02T20:10:00"},
    # invalid priority value
    {"ticket_customer_id": 88317, "betreff": "Prioritaet ungueltig", "beschreibung": "Testfall.",
     "kategorie": "Fehler_Stoerung", "kanal": "email", "prioritaet": "super-dringend",
     "erstellt_am": "2026-10-02T13:00:00", "sla_frist": "2026-10-02T17:00:00"},
]

MALFORMED_JSON_LINE = '{"ticket_customer_id": 88213, "betreff": "kaputtes JSON",'  # intentionally truncated


def main():
    with open(DATA_DIR / "eingang_feed.jsonl", "w", encoding="utf-8") as f:
        for row in GOOD + BROKEN:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        f.write(MALFORMED_JSON_LINE + "\n")
    print(f"Fixture geschrieben: {len(GOOD)} gueltige, {len(BROKEN)} ungueltige, 1 kaputtes JSON")


if __name__ == "__main__":
    main()
