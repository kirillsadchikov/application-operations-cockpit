#!/usr/bin/env python3
"""
klassifikation.py — ticket pre-categorization.

Honesty note, because this is the one part of the build plan that could
not be built as originally specified: the original design calls for an
LLM call (a prompt with the fixed category list, asking for a category
and a confidence score back as JSON). This sandbox has no LLM API key
available to it, so this script implements the SAME architecture — a
classifier that returns a structured, validated proposal with a
confidence score, auto-applies at >= 0.85 and routes everything else to
manual review — using a deterministic keyword-weighted scorer instead of
an actual model call. The `modell` column is written as
"regelbasiert-v1" rather than naming an LLM, precisely so this is never
misread later as a real model call.

Swapping in a real LLM later means replacing `_score_kategorie()` with an
API call that returns the same {kategorie, prioritaet, konfidenz} shape —
everything downstream (JSON validation, the 0.85 threshold, routing to
ticket_klassifikation) stays the same.
"""
import json

import psycopg2

DSN = "host=localhost dbname=cockpit user=postgres password=cockpit_dev"
SCHWELLENWERT = 0.85
MODELL_NAME = "regelbasiert-v1"

KATEGORIEN = [
    "Zugriff_Login",
    "Rechnung_Zahlung",
    "Fehler_Stoerung",
    "Frage_Nutzung",
    "Auftrag_Bestellung",
    "Reklamation",
]

KEYWORDS = {
    "Zugriff_Login": ["login", "passwort", "zugang", "anmelden", "gesperrt", "zwei-faktor",
                        "zugangsdaten", "benutzerzugang", "freischalten", "reset-link"],
    "Rechnung_Zahlung": ["rechnung", "zahlung", "mahnung", "abgebucht", "ueberwiesen", "gutschrift",
                          "iban", "bankverbindung", "erstattung", "betrag", "buchhaltung"],
    "Fehler_Stoerung": ["fehlermeldung", "stuerzt ab", "fehlercode", "bricht ab", "laedt nicht",
                         "weissen bildschirm", "export", "schlaegt fehl", "500", "findet.*nicht"],
    "Frage_Nutzung": ["wie kann ich", "gibt es eine", "wo finde ich", "koennen sie erklaeren",
                        "ist es moeglich", "wie aendere ich", "einstellen"],
    "Auftrag_Bestellung": ["bestellung", "auftrag", "liefertermin", "lieferung", "storniert",
                             "katalog", "eilbestellung", "menge"],
    "Reklamation": ["reklamation", "entspricht nicht", "unfreundlich", "unzufrieden", "beschaedigt",
                      "keine rueckmeldung", "entschaedigung", "wiederholten mal"],
}

URGENT_WORDS = ["dringend", "sofort", "stuerzt ab", "seit wochen", "zum wiederholten mal"]


def _score_kategorie(text: str):
    """Deterministic keyword-weighted score. Returns (kategorie, konfidenz)."""
    t = text.lower()
    scores = {}
    for kat, words in KEYWORDS.items():
        hits = sum(1 for w in words if w in t)
        scores[kat] = hits
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    best_kat, best_score = ranked[0]
    second_score = ranked[1][1] if len(ranked) > 1 else 0

    if best_score == 0:
        # no keyword matched at all — lowest-confidence fallback
        return "Frage_Nutzung", 0.40

    konfidenz = best_score / (best_score + second_score + 0.5)
    konfidenz = min(0.98, max(0.5, round(konfidenz, 3)))
    return best_kat, konfidenz


def _propose_prioritaet(text: str) -> str:
    t = text.lower()
    if any(w in t for w in URGENT_WORDS):
        return "hoch"
    return "normal"


def klassifiziere_ticket(beschreibung: str) -> dict:
    """The one function that would be replaced by a real LLM call. Returns
    the same validated shape either way."""
    kategorie, konfidenz = _score_kategorie(beschreibung)
    prioritaet = _propose_prioritaet(beschreibung)
    antwort = {"kategorie": kategorie, "prioritaet": prioritaet, "konfidenz": konfidenz}
    return validiere_antwort(antwort)


def validiere_antwort(antwort: dict) -> dict:
    """Schema validation — exactly what the build plan calls for even when
    the proposal comes from a model: never trust that the response is
    clean without checking."""
    if not isinstance(antwort, dict):
        raise ValueError("Antwort ist kein JSON-Objekt")
    for feld in ("kategorie", "prioritaet", "konfidenz"):
        if feld not in antwort:
            raise ValueError(f"Pflichtfeld fehlt: {feld}")
    if antwort["kategorie"] not in KATEGORIEN:
        raise ValueError(f"Unbekannte Kategorie: {antwort['kategorie']}")
    if not (0.0 <= float(antwort["konfidenz"]) <= 1.0):
        raise ValueError("Konfidenz ausserhalb [0,1]")
    return antwort


def main():
    conn = psycopg2.connect(DSN)
    cur = conn.cursor()
    cur.execute("DELETE FROM ticket_klassifikation")

    cur.execute("SELECT ticket_id, beschreibung, kategorie FROM ticket ORDER BY ticket_id")
    rows = cur.fetchall()

    treffer = 0
    automatisch = 0
    zur_pruefung = 0
    insert_rows = []

    for ticket_id, beschreibung, tatsaechliche_kategorie in rows:
        try:
            antwort = klassifiziere_ticket(beschreibung)
        except ValueError as e:
            # a real LLM call could return garbage; this is the fallback path
            antwort = {"kategorie": "Frage_Nutzung", "prioritaet": "normal", "konfidenz": 0.0}

        status = "automatisch_gesetzt" if antwort["konfidenz"] >= SCHWELLENWERT else "zur_pruefung"
        if status == "automatisch_gesetzt":
            automatisch += 1
        else:
            zur_pruefung += 1
        if antwort["kategorie"] == tatsaechliche_kategorie:
            treffer += 1

        insert_rows.append((ticket_id, antwort["kategorie"], antwort["prioritaet"],
                             antwort["konfidenz"], status, MODELL_NAME))

    cur.executemany(
        """INSERT INTO ticket_klassifikation
               (ticket_id, vorschlag_kategorie, vorschlag_prioritaet, konfidenz, status, modell)
           VALUES (%s,%s,%s,%s,%s,%s)""",
        insert_rows,
    )
    conn.commit()

    n = len(rows)
    print(f"Tickets klassifiziert: {n}")
    print(f"  automatisch gesetzt (Konfidenz >= {SCHWELLENWERT}): {automatisch} ({100*automatisch/n:.1f}%)")
    print(f"  zur Pruefung weitergeleitet: {zur_pruefung} ({100*zur_pruefung/n:.1f}%)")
    print(f"Trefferquote (Vorschlag == tatsaechliche Kategorie), gesamt: {100*treffer/n:.1f}%")

    cur.execute("""
        SELECT status, count(*) AS n,
               round(100.0 * count(*) FILTER (
                 WHERE k.vorschlag_kategorie = t.kategorie
               ) / count(*), 1) AS trefferquote_prozent
        FROM ticket_klassifikation k
        JOIN ticket t ON t.ticket_id = k.ticket_id
        GROUP BY status
    """)
    print("\nTrefferquote nach Status:")
    for status, n_status, quote in cur.fetchall():
        print(f"  {status}: n={n_status}, Trefferquote={quote}%")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
