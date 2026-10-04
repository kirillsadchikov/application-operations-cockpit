# Incident-Beispiel: "SLA-Meldungen kamen doppelt"

Dieser Vorfall ist reproduziert, nicht nur beschrieben — die Befehle
darunter laufen gegen eine Kopie der echten Datenbank dieses Projekts.

## Symptom

Beim Testen des Mapping-Schritts fiel auf: ein einzelner Kunde
(K-10041, "Baumgartner Recycling GmbH") wurde in `v_kunde_360` mit
38 Tickets geführt. Die direkte Abfrage auf `ticket_kunde` zeigte aber
nur 19 tatsächliche Tickets für diesen Kunden.

## Analyse

Nachgestellt wurde der Fall, dass der UID-Matching-Schritt (Tier 1 aus
`sql/02_mapping.sql`) zweimal läuft — zum Beispiel, weil ein
Scheduler nach einem Timeout automatisch erneut auslöst. Eine
Mapping-Tabelle **ohne** den `UNIQUE`-Constraint nimmt beide Durchläufe
anstandslos an:

```sql
-- Tabelle ohne UNIQUE-Constraint, zwei Durchläufe des UID-Matchings
INSERT 0 155   -- erster Durchlauf
INSERT 0 155   -- zweiter Durchlauf, keine Sperre verhindert das

SELECT count(*) FROM kunde_mapping_scratch;  --> 310 statt 155
```

Der `LEFT JOIN` in `v_kunde_360` zählt Tickets dann für jede passende
Mapping-Zeile mit — bei zwei identischen Zeilen pro Kunde also doppelt:

```sql
-- mit doppeltem Mapping
SELECT count(t.ticket_id) FROM ... WHERE kunden_nr = 'K-10041';  --> 38

-- mit korrektem (einfachem) Mapping
SELECT count(t.ticket_id) FROM ... WHERE kunden_nr = 'K-10041';  --> 19
```

## Ursache

`kunde_mapping` hatte in diesem nachgestellten Fall keinen
`UNIQUE`-Constraint auf `(crm_kunden_nr, ticket_customer_id)`. Ohne ihn
gibt es nichts, was einen zweiten, inhaltsgleichen Insert verhindert —
der Fehler liegt nicht im Join, sondern eine Ebene darunter, in der
fehlenden Eindeutigkeitsgarantie.

Ein Nebenbefund dabei: Der Constraint lässt sich nicht einfach
nachträglich hinzufügen, solange die Duplikate noch in der Tabelle
stehen —

```
ERROR:  could not create unique index "uq_scratch"
DETAIL:  Key (crm_kunden_nr, ticket_customer_id)=(K-10078, 88250) is duplicated.
```

— die Bereinigung muss also vor der Absicherung passieren, nicht danach.

## Behebung

1. Duplikate bereinigen (niedrigste `id` je Paar behalten):
   ```sql
   DELETE FROM kunde_mapping a USING kunde_mapping b
   WHERE a.crm_kunden_nr = b.crm_kunden_nr
     AND a.ticket_customer_id = b.ticket_customer_id
     AND a.id > b.id;
   ```
2. `UNIQUE (crm_kunden_nr, ticket_customer_id)` als Constraint ergänzen
   (im echten Schema von Anfang an vorhanden, siehe `sql/01_schema.sql`).
3. Jeden Insert in `sql/02_mapping.sql` mit
   `ON CONFLICT (crm_kunden_nr, ticket_customer_id) DO NOTHING` absichern,
   damit ein zweiter Lauf ein No-Op ist statt ein Duplikat zu erzeugen.

Mit beiden Absicherungen bleibt ein zweiter Durchlauf des exakt gleichen
Matching-Passes folgenlos: `INSERT 0 0`, Zeilenzahl unverändert bei 155.

## Vermeidung

Der eigentliche Fehler war nicht "der Join ist falsch", sondern "die
Tabelle darunter erlaubt einen Zustand, den der Join nicht verkraftet".
Seitdem gilt für dieses Projekt: jede Tabelle, die über einen Join in
eine Kennzahl einfliesst, bekommt ihre Eindeutigkeitsgarantie als
Constraint in der Datenbank, nicht nur als Annahme im Kopf der Person,
die das SQL schreibt — und jeder Insert, der mehrfach laufen könnte,
bekommt eine `ON CONFLICT`-Klausel von Anfang an.
