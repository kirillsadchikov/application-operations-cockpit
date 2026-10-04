-- 03_abgleich.sql
-- The mapping report: how many matched per method, and — just as
-- important — exactly who is still unmatched on either side, so that list
-- is a concrete query result, not a vague "some gaps remain".

-- 1. Matches by method
SELECT match_methode, count(*) AS anzahl, konfidenz
FROM kunde_mapping
GROUP BY match_methode, konfidenz
ORDER BY konfidenz DESC;

-- 2. CRM customers with no mapping at all
SELECT c.kunden_nr, c.firmenname, c.email
FROM crm_kunde c
WHERE c.kunden_nr NOT IN (SELECT crm_kunden_nr FROM kunde_mapping)
ORDER BY c.kunden_nr;

-- 3. Ticket-system customers with no mapping at all
SELECT t.customer_id, t.company, t.contact
FROM ticket_kunde t
WHERE t.customer_id NOT IN (SELECT ticket_customer_id FROM kunde_mapping)
ORDER BY t.customer_id;

-- 4. CRM customers mapped to more than one ticket_customer_id — not an
-- error (these are the 5 deliberately duplicated ticket-system signups),
-- but worth surfacing on the data-quality dashboard.
SELECT crm_kunden_nr, count(*) AS anzahl_ticket_ids,
       array_agg(ticket_customer_id ORDER BY ticket_customer_id) AS ticket_ids
FROM kunde_mapping
GROUP BY crm_kunden_nr
HAVING count(*) > 1
ORDER BY crm_kunden_nr;

-- 5. Summary counts
SELECT
  (SELECT count(*) FROM crm_kunde) AS crm_kunde_gesamt,
  (SELECT count(*) FROM ticket_kunde) AS ticket_kunde_gesamt,
  (SELECT count(*) FROM kunde_mapping) AS mappings_gesamt,
  (SELECT count(DISTINCT crm_kunden_nr) FROM kunde_mapping) AS crm_kunden_gemappt,
  (SELECT count(*) FROM crm_kunde WHERE kunden_nr NOT IN (SELECT crm_kunden_nr FROM kunde_mapping)) AS crm_offen,
  (SELECT count(*) FROM ticket_kunde WHERE customer_id NOT IN (SELECT ticket_customer_id FROM kunde_mapping)) AS ticket_offen;
