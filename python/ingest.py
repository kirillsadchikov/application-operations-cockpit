#!/usr/bin/env python3
"""
ingest.py — validating ingest pipeline for incoming ticket records.

Simulates the REST feed from the build plan: rather than requiring a
live external endpoint (which would not survive past this session), it
reads a local JSON-lines file shaped exactly like a REST response body
would be — one ticket object per line — via `--source`. Swapping in a
real `requests.get(...)` call means replacing `_lade_rohdaten()`; every
validation, logging, and rejection step downstream is unchanged.

Behavior:
  - every row is validated independently; one bad row never aborts the run
  - rows that fail validation go to data/rejected.jsonl with a reason,
    not into the database
  - every run is logged to ingest_log (source, counts, dry_run)
  - --dry-run validates and logs, but writes nothing to `ticket`
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import psycopg2

DSN = "host=localhost dbname=cockpit user=postgres password=cockpit_dev"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

REQUIRED_FIELDS = ["ticket_customer_id", "betreff", "beschreibung", "kategorie",
                    "kanal", "prioritaet", "erstellt_am", "sla_frist"]
GUELTIGE_PRIORITAETEN = {"niedrig", "normal", "hoch", "kritisch"}
GUELTIGE_KANAELE = {"email", "telefon", "portal", "chat"}


def _lade_rohdaten(pfad: Path):
    rows = []
    with open(pfad, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                rows.append({"__parse_error__": str(e), "__raw__": line})
    return rows


def _parse_datum(value):
    """Returns a datetime or raises ValueError — isoformat only, no silent
    coercion of ambiguous formats."""
    return datetime.fromisoformat(value)


def validiere_zeile(row: dict, bekannte_customer_ids: set):
    """Returns (ok: bool, grund: str|None). Checks every required field
    before returning, rather than stopping at the first problem, so the
    rejection reason is complete."""
    if "__parse_error__" in row:
        return False, f"ungueltiges JSON: {row['__parse_error__']}"

    fehlende = [f for f in REQUIRED_FIELDS if f not in row or row[f] in (None, "")]
    if fehlende:
        return False, f"Pflichtfeld(er) fehlen: {', '.join(fehlende)}"

    if row["ticket_customer_id"] not in bekannte_customer_ids:
        return False, f"unbekannte ticket_customer_id: {row['ticket_customer_id']}"

    if row["prioritaet"] not in GUELTIGE_PRIORITAETEN:
        return False, f"ungueltige prioritaet: {row['prioritaet']}"

    if row["kanal"] not in GUELTIGE_KANAELE:
        return False, f"ungueltiger kanal: {row['kanal']}"

    for feld in ("erstellt_am", "sla_frist"):
        try:
            _parse_datum(row[feld])
        except (ValueError, TypeError):
            return False, f"ungueltiges Datumsformat in {feld}: {row[feld]!r}"

    return True, None


def run(source_path: Path, dry_run: bool):
    conn = psycopg2.connect(DSN)
    cur = conn.cursor()
    cur.execute("SELECT customer_id FROM ticket_kunde")
    bekannte_customer_ids = {r[0] for r in cur.fetchall()}

    rohdaten = _lade_rohdaten(source_path)
    ok_rows, rejected = [], []

    for row in rohdaten:
        ok, grund = validiere_zeile(row, bekannte_customer_ids)
        if ok:
            ok_rows.append(row)
        else:
            rejected.append({"zeile": row, "grund": grund})

    if rejected:
        with open(DATA_DIR / "rejected.jsonl", "a", encoding="utf-8") as f:
            for r in rejected:
                f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")

    if not dry_run and ok_rows:
        insert = [(
            r["ticket_customer_id"], r["betreff"], r["beschreibung"], r["kategorie"], r["kanal"],
            r["prioritaet"], r["erstellt_am"], r.get("erste_antwort_am"), r.get("geloest_am"),
            bool(r.get("wiedereroeffnet", False)), r["sla_frist"],
        ) for r in ok_rows]
        cur.executemany(
            """INSERT INTO ticket (ticket_customer_id, betreff, beschreibung, kategorie, kanal,
                                    prioritaet, erstellt_am, erste_antwort_am, geloest_am,
                                    wiedereroeffnet, sla_frist)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            insert,
        )

    cur.execute(
        """INSERT INTO ingest_log (quelle, zeilen_gesamt, zeilen_ok, zeilen_abgelehnt, dry_run)
           VALUES (%s,%s,%s,%s,%s)""",
        (str(source_path.name), len(rohdaten), len(ok_rows), len(rejected), dry_run),
    )
    conn.commit()
    cur.close()
    conn.close()

    print(f"Quelle: {source_path.name}")
    print(f"Zeilen gesamt: {len(rohdaten)}")
    print(f"  OK{'  (dry-run, nicht geschrieben)' if dry_run else ' (in ticket geschrieben)'}: {len(ok_rows)}")
    print(f"  abgelehnt (data/rejected.jsonl): {len(rejected)}")
    for r in rejected:
        print(f"    - {r['grund']}")
    return len(rohdaten), len(ok_rows), len(rejected)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=str(DATA_DIR / "eingang_feed.jsonl"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(Path(args.source), args.dry_run)
