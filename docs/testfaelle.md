# Testfälle

Acht Testfälle, alle tatsächlich ausgeführt gegen die echte PostgreSQL-
Datenbank dieses Projekts (nicht nur beschrieben). Die letzten beiden sind
die geforderten Negativtests.

| # | Testfall | Vorbedingung | Schritte | Erwartet | Ergebnis |
|---|---|---|---|---|---|
| 1 | UID-Match | CRM- und Ticket-Kunde haben dieselbe UID (ggf. mit Leerzeichen) | `sql/02_mapping.sql`, Tier 1 ausführen | Zuordnung mit `match_methode='uid'`, `konfidenz=1.00` | Bestanden — 155 Zuordnungen |
| 2 | Namens-Match bei abweichender Rechtsform | Kein UID-/E-Mail-Treffer, Firmenname normalisiert identisch (`GmbH` vs. `G.m.b.H.`) | `sql/02_mapping.sql`, Tier 3 | Zuordnung mit `match_methode='name_normalisiert'`, `konfidenz=0.70` | Bestanden — 15 Zuordnungen |
| 3 | E-Mail-Match bei fehlender UID | UID auf einer Seite leer, E-Mail stimmt (Gross-/Kleinschreibung ignoriert) | `sql/02_mapping.sql`, Tier 2 | Zuordnung mit `match_methode='email'`, `konfidenz=0.95` | Bestanden — 15 Zuordnungen |
| 4 | Gültiges Ticket wird importiert | Kunde existiert in `ticket_kunde`, alle Pflichtfelder vorhanden | `python3 python/ingest.py --source data/eingang_feed.jsonl` | Zeile landet in `ticket`, erscheint nicht in `rejected.jsonl` | Bestanden — 3 von 8 Zeilen übernommen |
| 5 | SLA-Verletzung wird erkannt | Ticket mit `geloest_am > sla_frist` | `SELECT * FROM v_sla_verletzung WHERE sla_verletzt` | Ticket erscheint mit `sla_verletzt=true` und positivem `verzug_stunden` | Bestanden |
| 6 | Klassifikation unter Schwellenwert geht zur Prüfung | Freitext mit mehrdeutigen oder wenigen Schlüsselwörtern | `python3 python/klassifikation.py` | `status='zur_pruefung'` bei Konfidenz < 0,85, Kategorie wird NICHT automatisch übernommen | Bestanden — 86,6 % der Tickets zur Prüfung, 13,4 % automatisch |
| 7 | **Negativtest** — kaputtes JSON in der Eingangsdatei | Eine Zeile in `eingang_feed.jsonl` ist kein valides JSON | `python3 python/ingest.py --source data/eingang_feed.jsonl` | Zeile landet mit Fehlermeldung in `rejected.jsonl`, der restliche Lauf bricht nicht ab | Bestanden — Lauf verarbeitet die übrigen 7 Zeilen normal weiter |
| 8 | **Negativtest** — doppeltes Mapping ohne UNIQUE-Constraint | Mapping-Tabelle ohne `UNIQUE`-Constraint, Matching-Pass läuft zweimal | Siehe `docs/incident_beispiel.md` | Ticketanzahl pro Kunde wird doppelt gezählt (Fan-out im `LEFT JOIN`) | Reproduziert — 38 statt 19 Tickets für Testkunde K-10041; mit Constraint + `ON CONFLICT DO NOTHING` korrekt (19) |
