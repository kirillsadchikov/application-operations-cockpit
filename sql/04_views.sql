-- 04_views.sql — the five reporting views behind the dashboard.
-- Each one answers one specific operational question; the comment above
-- it is that question, not a restatement of the SQL.

DROP VIEW IF EXISTS v_kunde_360;
DROP VIEW IF EXISTS v_wiedereroeffnungsquote;
DROP VIEW IF EXISTS v_erstreaktion;
DROP VIEW IF EXISTS v_sla_verletzung;
DROP VIEW IF EXISTS v_backlog_taeglich;

-- v_backlog_taeglich — "how many tickets are open, broken down by day
-- they were created and by category?" Used for the backlog trend.
CREATE VIEW v_backlog_taeglich AS
SELECT date_trunc('day', erstellt_am)::date AS tag,
       kategorie,
       count(*) AS tickets_erstellt,
       count(*) FILTER (WHERE geloest_am IS NULL) AS noch_offen
FROM ticket
GROUP BY date_trunc('day', erstellt_am)::date, kategorie
ORDER BY tag, kategorie;

-- v_sla_verletzung — "which tickets breached their SLA, and by how much?"
-- Also carries remaining time for tickets still open and still within SLA
-- (negative sla_rest_stunden = already breached), since that is what the
-- daily alert (python/alert_sla.py) actually queries.
CREATE VIEW v_sla_verletzung AS
SELECT ticket_id, ticket_customer_id, kategorie, prioritaet, erstellt_am,
       sla_frist, geloest_am,
       CASE
         WHEN geloest_am IS NOT NULL AND geloest_am > sla_frist THEN TRUE
         WHEN geloest_am IS NULL AND now() > sla_frist THEN TRUE
         ELSE FALSE
       END AS sla_verletzt,
       CASE
         WHEN geloest_am IS NOT NULL THEN EXTRACT(EPOCH FROM (geloest_am - sla_frist)) / 3600
         ELSE EXTRACT(EPOCH FROM (now() - sla_frist)) / 3600
       END AS verzug_stunden,
       EXTRACT(EPOCH FROM (sla_frist - now())) / 3600 AS sla_rest_stunden
FROM ticket;

-- v_erstreaktion — "what's the median time to first response, by channel?"
CREATE VIEW v_erstreaktion AS
SELECT kanal,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (erste_antwort_am - erstellt_am)) / 60) AS median_minuten,
       count(*) AS tickets
FROM ticket
WHERE erste_antwort_am IS NOT NULL
GROUP BY kanal
ORDER BY median_minuten;

-- v_wiedereroeffnungsquote — "of tickets resolved in the last 4 weeks
-- (rolling), what share got reopened, by category?" A CTE plus a window
-- function doing the rolling-window bucketing.
CREATE VIEW v_wiedereroeffnungsquote AS
WITH wochen AS (
  SELECT ticket_id, kategorie, wiedereroeffnet,
         date_trunc('week', geloest_am)::date AS woche
  FROM ticket
  WHERE geloest_am IS NOT NULL
)
SELECT woche, kategorie,
       count(*) AS geloest_gesamt,
       count(*) FILTER (WHERE wiedereroeffnet) AS wiedereroeffnet_gesamt,
       round(100.0 * count(*) FILTER (WHERE wiedereroeffnet) / count(*), 1) AS quote_prozent,
       sum(count(*)) OVER (PARTITION BY kategorie ORDER BY woche
                           ROWS BETWEEN 3 PRECEDING AND CURRENT ROW) AS geloest_rollierend_4w,
       sum(count(*) FILTER (WHERE wiedereroeffnet)) OVER (PARTITION BY kategorie ORDER BY woche
                           ROWS BETWEEN 3 PRECEDING AND CURRENT ROW) AS wiedereroeffnet_rollierend_4w
FROM wochen
GROUP BY woche, kategorie
ORDER BY woche, kategorie;

-- v_kunde_360 — "for each CRM customer, how many tickets do they actually
-- have, and how confident are we in that number?" This is the join that
-- doesn't work without Day 1's mapping table at all — ticket and crm_kunde
-- share no key of their own.
CREATE VIEW v_kunde_360 AS
SELECT c.kunden_nr, c.firmenname, m.match_methode, m.konfidenz,
       count(t.ticket_id) AS tickets_gesamt,
       count(*) FILTER (WHERE t.geloest_am > t.sla_frist) AS sla_verletzt
FROM crm_kunde c
LEFT JOIN kunde_mapping m ON m.crm_kunden_nr = c.kunden_nr
LEFT JOIN ticket t        ON t.ticket_customer_id = m.ticket_customer_id
GROUP BY c.kunden_nr, c.firmenname, m.match_methode, m.konfidenz;
