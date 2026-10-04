#!/usr/bin/env python3
"""test_ingest.py — the one test the build plan asks for: a record with a
missing required field is rejected, and the run still completes rather
than crashing. Run with: python3 python/test_ingest.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ingest import validiere_zeile  # noqa: E402


def test_missing_required_field_is_rejected():
    row = {
        "ticket_customer_id": 88213,
        # "betreff" is missing on purpose
        "beschreibung": "Testfall ohne Betreff.",
        "kategorie": "Fehler_Stoerung",
        "kanal": "chat",
        "prioritaet": "normal",
        "erstellt_am": "2026-10-02T12:00:00",
        "sla_frist": "2026-10-03T12:00:00",
    }
    ok, grund = validiere_zeile(row, bekannte_customer_ids={88213})
    assert ok is False, "Zeile mit fehlendem Pflichtfeld hätte abgelehnt werden müssen"
    assert "betreff" in grund
    print(f"PASS: fehlendes Pflichtfeld wird abgelehnt ({grund})")


def test_valid_row_is_accepted():
    row = {
        "ticket_customer_id": 88213,
        "betreff": "Login klappt nicht",
        "beschreibung": "Komme nicht ins Portal.",
        "kategorie": "Zugriff_Login",
        "kanal": "email",
        "prioritaet": "hoch",
        "erstellt_am": "2026-10-02T09:15:00",
        "sla_frist": "2026-10-02T17:15:00",
    }
    ok, grund = validiere_zeile(row, bekannte_customer_ids={88213})
    assert ok is True, f"gueltige Zeile wurde abgelehnt: {grund}"
    print("PASS: gueltige Zeile wird akzeptiert")


def test_unknown_customer_is_rejected():
    row = {
        "ticket_customer_id": 123,
        "betreff": "x", "beschreibung": "x", "kategorie": "Frage_Nutzung",
        "kanal": "email", "prioritaet": "normal",
        "erstellt_am": "2026-10-02T09:15:00", "sla_frist": "2026-10-02T17:15:00",
    }
    ok, grund = validiere_zeile(row, bekannte_customer_ids={88213})
    assert ok is False
    print(f"PASS: unbekannte customer_id wird abgelehnt ({grund})")


if __name__ == "__main__":
    test_missing_required_field_is_rejected()
    test_valid_row_is_accepted()
    test_unknown_customer_is_rejected()
    print("\nAlle Tests bestanden.")
