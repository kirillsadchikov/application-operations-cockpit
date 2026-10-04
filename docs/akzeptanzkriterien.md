# User Stories und Akzeptanzkriterien

Fünf User Stories, abgeleitet aus den tatsächlichen Anforderungen hinter dem
Projekt (zwei Quellsysteme mit unterschiedlichen Kundenschlüsseln, ein
schwankend sicherer KI-Kategorisierungsschritt, ein täglicher SLA-Check).
Jede Kriterienliste beschreibt, was tatsächlich implementiert und getestet
ist — nicht, was im Idealfall wünschenswert wäre.

## 1. SLA-Warnung

**Als** Serviceverantwortlicher **möchte ich** vor einer SLA-Verletzung
benachrichtigt werden, **damit** ich noch eingreifen kann.

- Meldung bei Restzeit unter 4 Stunden (`v_sla_verletzung.sla_rest_stunden`)
- Meldung enthält Ticketnummer, Kunde, Kategorie, Priorität und Restzeit
- Gelöste Tickets lösen keine Meldung aus (Filter auf `geloest_am IS NULL`)

## 2. Kundenzuordnung über zwei Systeme

**Als** Prozessverantwortlicher **möchte ich** wissen, welche Kunden
zwischen CRM und Ticketsystem eindeutig, unsicher oder gar nicht
zugeordnet sind, **damit** ich keine blinden Flecken in der
Kundenhistorie habe.

- Jede Zuordnung trägt eine Methode (`uid` / `email` / `name_normalisiert`)
  und einen Konfidenzwert — nichts wird ohne diese Angaben gespeichert
- Nicht zugeordnete Kunden auf beiden Seiten sind über
  `sql/03_abgleich.sql` als konkrete Liste abrufbar, nicht nur als Zahl
- Ein Kunde kann nie zwei Zuordnungen zum selben Ticket-Kunden erhalten
  (`UNIQUE (crm_kunden_nr, ticket_customer_id)`)

## 3. KI-Vorkategorisierung mit Schwellenwert

**Als** Teamleiter **möchte ich**, dass eingehende Tickets automatisch
vorkategorisiert werden, aber nur übernommen, wenn die Kategorie sicher
genug ist, **damit** niemand eine falsche automatische Kategorie
unbemerkt übernimmt.

- Vorschläge mit Konfidenz ≥ 0,85 erhalten den Status `automatisch_gesetzt`
- Alles darunter erhält den Status `zur_pruefung` und wird nicht
  automatisch in `ticket.kategorie` übernommen
- Jeder Vorschlag wird vor dem Speichern gegen das erlaubte
  Kategorie-Schema validiert (`validiere_antwort()`)

## 4. Robuster Import

**Als** Datenqualitätsverantwortlicher **möchte ich**, dass ein einzelner
fehlerhafter Datensatz nicht den gesamten Importlauf stoppt, **damit**
der Tagesimport nicht an einer kaputten Zeile scheitert.

- Jede Zeile wird unabhängig von den anderen validiert
- Abgelehnte Zeilen landen mit Begründung in `data/rejected.jsonl`,
  gültige Zeilen werden trotzdem geschrieben
- Jeder Lauf wird in `ingest_log` protokolliert (Quelle, Anzahl, Modus)

## 5. Wiedereröffnungsquote als Frühwarnung

**Als** Serviceverantwortlicher **möchte ich** die Wiedereröffnungsquote
je Kategorie rollierend über 4 Wochen sehen, **damit** ich wiederkehrende
Problemfelder erkenne, bevor sie sich häufen.

- Rollierende 4-Wochen-Summe je Kategorie (`v_wiedereroeffnungsquote`)
- Quote in Prozent, nicht nur als absolute Zahl
- Nur tatsächlich gelöste Tickets fließen ein (offene Tickets verzerren
  die Quote nicht)
