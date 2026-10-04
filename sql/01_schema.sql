-- 01_schema.sql
-- Core tables: two messy source systems (crm_kunde, ticket_kunde), the
-- confidence-scored mapping between them, and the ticket data itself.

DROP TABLE IF EXISTS ticket_klassifikation CASCADE;
DROP TABLE IF EXISTS ingest_log CASCADE;
DROP TABLE IF EXISTS ticket CASCADE;
DROP TABLE IF EXISTS kunde_mapping CASCADE;
DROP TABLE IF EXISTS crm_kunde CASCADE;
DROP TABLE IF EXISTS ticket_kunde CASCADE;

-- Source system 1: CRM export. Clean-ish, but UID formatting and nullability
-- are inconsistent because three different sales reps maintain it by hand.
CREATE TABLE crm_kunde (
    kunden_nr      TEXT PRIMARY KEY,
    firmenname     TEXT NOT NULL,
    uid            TEXT,
    email          TEXT,
    land           TEXT
);

-- Source system 2: the ticketing tool's own customer export. Different ID
-- space, different column names, no shared primary key with the CRM.
CREATE TABLE ticket_kunde (
    customer_id    INTEGER PRIMARY KEY,
    company        TEXT NOT NULL,
    vat             TEXT,
    contact         TEXT
);

-- The mapping between the two systems. Nothing is "guessed" silently: every
-- row carries the method that produced it and a confidence score, so a
-- low-confidence row can be routed to manual review instead of trusted
-- outright. UNIQUE prevents the same pair being inserted twice by two
-- different matching passes (see docs/incident_beispiel.md for what
-- happens when this constraint is missing).
CREATE TABLE kunde_mapping (
    id                  SERIAL PRIMARY KEY,
    crm_kunden_nr       TEXT REFERENCES crm_kunde(kunden_nr),
    ticket_customer_id  INTEGER REFERENCES ticket_kunde(customer_id),
    match_methode       TEXT NOT NULL,   -- 'uid' | 'email' | 'name_normalisiert' | 'manuell'
    konfidenz           NUMERIC(3,2) NOT NULL,
    geprueft_von        TEXT,
    geprueft_am         TIMESTAMP,
    UNIQUE (crm_kunden_nr, ticket_customer_id)
);

CREATE TABLE ticket (
    ticket_id           SERIAL PRIMARY KEY,
    ticket_customer_id  INTEGER REFERENCES ticket_kunde(customer_id),
    betreff             TEXT NOT NULL,
    beschreibung        TEXT NOT NULL,
    kategorie           TEXT NOT NULL,   -- ground-truth category, as the agent set it
    kanal               TEXT NOT NULL,   -- email | telefon | portal | chat
    prioritaet          TEXT NOT NULL,   -- niedrig | normal | hoch | kritisch
    erstellt_am         TIMESTAMP NOT NULL,
    erste_antwort_am    TIMESTAMP,
    geloest_am          TIMESTAMP,
    wiedereroeffnet     BOOLEAN NOT NULL DEFAULT FALSE,
    sla_frist           TIMESTAMP NOT NULL
);

-- Output of the classification step (python/klassifikation.py). Kept apart
-- from `ticket` so the proposal, its confidence, and what happened with it
-- are auditable independently of the ticket's real category.
CREATE TABLE ticket_klassifikation (
    id                  SERIAL PRIMARY KEY,
    ticket_id           INTEGER REFERENCES ticket(ticket_id),
    vorschlag_kategorie TEXT NOT NULL,
    vorschlag_prioritaet TEXT NOT NULL,
    konfidenz           NUMERIC(4,3) NOT NULL,
    status              TEXT NOT NULL,   -- 'automatisch_gesetzt' | 'zur_pruefung'
    modell              TEXT NOT NULL,
    klassifiziert_am    TIMESTAMP NOT NULL DEFAULT now()
);

-- One row per ingest run (python/ingest.py), so "what happened the last
-- time this ran" is a query, not a guess.
CREATE TABLE ingest_log (
    id              SERIAL PRIMARY KEY,
    gestartet_am    TIMESTAMP NOT NULL DEFAULT now(),
    quelle          TEXT NOT NULL,
    zeilen_gesamt   INTEGER NOT NULL,
    zeilen_ok       INTEGER NOT NULL,
    zeilen_abgelehnt INTEGER NOT NULL,
    dry_run         BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX idx_ticket_customer ON ticket(ticket_customer_id);
CREATE INDEX idx_ticket_erstellt ON ticket(erstellt_am);
CREATE INDEX idx_mapping_crm ON kunde_mapping(crm_kunden_nr);
CREATE INDEX idx_mapping_ticket ON kunde_mapping(ticket_customer_id);
