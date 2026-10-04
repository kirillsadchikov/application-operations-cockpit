-- 02_mapping.sql
-- Tiered-confidence matching between crm_kunde and ticket_kunde.
-- Runs in order: the strongest signal first, each subsequent pass only
-- considers customers neither side has already matched. Nothing below
-- is a guess — every row gets a method and a confidence score, and the
-- rows that don't clear any tier are left open for the review list in
-- sql/03_abgleich.sql instead of being matched anyway.
--
-- ON CONFLICT DO NOTHING is what makes this script idempotent — running
-- it twice does not create duplicate mapping rows. See
-- docs/incident_beispiel.md for what happens without it.

-- Tier 1 — UID, normalized (strip spaces/hyphens, uppercase). Confidence 1.00.
INSERT INTO kunde_mapping (crm_kunden_nr, ticket_customer_id, match_methode, konfidenz)
SELECT c.kunden_nr, t.customer_id, 'uid', 1.00
FROM crm_kunde c
JOIN ticket_kunde t
  ON c.uid IS NOT NULL AND t.vat IS NOT NULL
 AND upper(replace(replace(c.uid, ' ', ''), '-', '')) = upper(replace(replace(t.vat, ' ', ''), '-', ''))
ON CONFLICT (crm_kunden_nr, ticket_customer_id) DO NOTHING;

-- Tier 2 — email, lowercased. Confidence 0.95. Only customers not already
-- matched by UID on EITHER side are considered.
INSERT INTO kunde_mapping (crm_kunden_nr, ticket_customer_id, match_methode, konfidenz)
SELECT c.kunden_nr, t.customer_id, 'email', 0.95
FROM crm_kunde c
JOIN ticket_kunde t
  ON c.email IS NOT NULL AND t.contact IS NOT NULL
 AND lower(c.email) = lower(t.contact)
WHERE c.kunden_nr NOT IN (SELECT crm_kunden_nr FROM kunde_mapping)
  AND t.customer_id NOT IN (SELECT ticket_customer_id FROM kunde_mapping)
ON CONFLICT (crm_kunden_nr, ticket_customer_id) DO NOTHING;

-- Tier 3 — company name, normalized (lowercase, legal-form suffixes and
-- punctuation stripped, "&" folded to "und"). Confidence 0.70 — this is
-- the weakest signal the pipeline will act on automatically.
INSERT INTO kunde_mapping (crm_kunden_nr, ticket_customer_id, match_methode, konfidenz)
SELECT c.kunden_nr, t.customer_id, 'name_normalisiert', 0.70
FROM crm_kunde c
JOIN ticket_kunde t
  ON regexp_replace(
       lower(replace(c.firmenname, '&', 'und')),
       '\s*(gmbh|g\.m\.b\.h\.|kg|og|ag|e\.u\.)\.?\s*$', '', 'i'
     ) = regexp_replace(
       lower(replace(t.company, '&', 'und')),
       '\s*(gmbh|g\.m\.b\.h\.|kg|og|ag|e\.u\.)\.?\s*$', '', 'i'
     )
WHERE c.kunden_nr NOT IN (SELECT crm_kunden_nr FROM kunde_mapping)
  AND t.customer_id NOT IN (SELECT ticket_customer_id FROM kunde_mapping)
ON CONFLICT (crm_kunden_nr, ticket_customer_id) DO NOTHING;

-- Everything else is left unmatched on purpose. sql/03_abgleich.sql reports
-- it as a review list rather than silently leaving it invisible.
