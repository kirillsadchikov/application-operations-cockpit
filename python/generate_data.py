#!/usr/bin/env python3
"""
generate_data.py — builds the two messy synthetic source systems
(data/crm_kunden.csv, data/ticket_kunden.json) and the ticket history
(loaded straight into the `ticket` table, see load_tickets() below).

The messiness is deliberate, not a side effect: it's what Day-1 mapping
exists to resolve, and what the Data-quality dashboard later reports on.

Customer population (~200 real-world companies):
  150  "clean"   — same UID on both sides (formatting noise only)   -> matches via UID,  confidence 1.00
   15  "email"   — UID missing/blank on one side, email matches     -> matches via email, confidence 0.95
   15  "name"    — neither UID nor email align, company name does  -> matches via name,  confidence 0.70
    8  CRM-only  — never made it into the ticketing tool
    7  ticket-only — walk-in support contacts, never entered the CRM
    5  duplicated in the ticket system (signed up twice under two customer_ids)
"""
import csv
import json
import random
from pathlib import Path

random.seed(42)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

LEGAL_FORMS = ["GmbH", "G.m.b.H.", "KG", "OG", "AG", "e.U."]
NAME_STEMS = [
    "Mayer Bau", "Huber Logistik", "Steiner Elektro", "Wimmer Transport",
    "Gruber Consulting", "Leitner Handel", "Berger Metallbau", "Fuchs Software",
    "Pichler Gastro", "Winkler Reinigung", "Moser Druck", "Schwarz Textil",
    "Hofer Installation", "Lang Immobilien", "Brunner Agrar", "Egger Holzbau",
    "Aigner Sicherheit", "Wolf Grafik", "Maier Catering", "Schmid Fuhrpark",
    "Reiter Garten", "Haas Spedition", "Binder Werbung", "Lechner Event",
    "Auer Installationstechnik", "Baumgartner Recycling", "Ebner IT-Service",
    "Fischer Malerei", "Gatterer Steuerberatung", "Hiller Personalvermittlung",
    "Jenewein Fenster", "Kofler Maschinenbau", "Lindner Papier", "Mader Optik",
    "Niedermayer Verpackung", "Oberleitner Fliesen", "Payer Buchhaltung",
    "Rauch Dachdecker", "Scheidl Sanitaer", "Trenker Logistik", "Unterberger Agrar",
    "Vogl Elektrotechnik", "Wallner Spedition", "Zeiler Catering", "Amann Bau",
    "Bachmann Consulting", "Colli Transport", "Dobler Handel", "Eder Metallbau",
    "Falk Software",
]
STREETS = ["Hauptstrasse", "Bahnhofstrasse", "Industriestrasse", "Ringstrasse", "Feldweg"]
CITIES_AT = ["Wien", "Graz", "Linz", "Salzburg", "Innsbruck", "Klagenfurt", "Villach", "Wels"]

CATEGORIES = [
    "Zugriff_Login",
    "Rechnung_Zahlung",
    "Fehler_Stoerung",
    "Frage_Nutzung",
    "Auftrag_Bestellung",
    "Reklamation",
]

CHANNELS = ["email", "telefon", "portal", "chat"]
PRIORITIES = ["niedrig", "normal", "hoch", "kritisch"]
SLA_HOURS = {"kritisch": 4, "hoch": 8, "normal": 24, "niedrig": 72}

# Free-text templates per category. Deliberately written the way real tickets
# read — some overlap in vocabulary between categories, so a keyword
# classifier doesn't get every single one right. That's the point: the
# accuracy number in docs is real, not staged.
TEMPLATES = {
    "Zugriff_Login": [
        "Ich komme seit heute Morgen nicht mehr ins Portal, Passwort wird als falsch abgelehnt.",
        "Login funktioniert nicht, bekomme immer 'Zugangsdaten ungueltig'. Bitte Account freischalten.",
        "Mein Benutzerzugang wurde offenbar gesperrt, ich brauche dringend wieder Zugriff.",
        "Zwei-Faktor-Code kommt nicht an, kann mich seit gestern nicht mehr anmelden.",
        "Neuer Mitarbeiter braucht einen Zugang zum Kundenportal, bitte anlegen.",
        "Passwort vergessen, der Reset-Link im Mail funktioniert nicht.",
    ],
    "Rechnung_Zahlung": [
        "Die Rechnung vom letzten Monat wurde doppelt abgebucht, bitte um Erstattung.",
        "Wir haben eine Mahnung bekommen, obwohl die Zahlung bereits ueberwiesen wurde.",
        "Auf der Rechnung steht ein falscher Betrag, kann das bitte korrigiert werden?",
        "Benoetigen eine Rechnungskopie fuer die Buchhaltung, Original ist nicht angekommen.",
        "Zahlung wurde zurueckgewiesen, IBAN im System ist noch die alte Bankverbindung.",
        "Gutschrift aus der Reklamation letzten Monat ist noch nicht auf dem Konto sichtbar.",
    ],
    "Fehler_Stoerung": [
        "Beim Speichern eines Auftrags kommt eine Fehlermeldung, Vorgang bricht ab.",
        "Export nach Excel liefert eine leere Datei, seit dem letzten Update.",
        "Die Anwendung stuerzt ab, sobald ich den Bericht fuer letzten Monat oeffne.",
        "Seit heute laedt die Startseite nicht mehr, Browser zeigt nur einen weissen Bildschirm.",
        "Suchfunktion findet bestehende Kunden nicht mehr, obwohl sie definitiv angelegt sind.",
        "Upload von Belegen schlaegt staendig fehl mit Fehlercode 500.",
    ],
    "Frage_Nutzung": [
        "Wie kann ich einen zweiten Standort im System anlegen?",
        "Gibt es eine Moeglichkeit, mehrere Auftraege gleichzeitig zu exportieren?",
        "Wo finde ich die Historie aller bisherigen Bestellungen?",
        "Koennen Sie kurz erklaeren, wie die automatische Erinnerung eingestellt wird?",
        "Ist es moeglich, Benachrichtigungen per SMS statt per E-Mail zu bekommen?",
        "Wie aendere ich die hinterlegte Lieferadresse fuer kuenftige Bestellungen?",
    ],
    "Auftrag_Bestellung": [
        "Unsere letzte Bestellung ist noch nicht angekommen, Liefertermin war letzte Woche.",
        "Bitte Auftrag Nr. aendern, Menge wurde falsch erfasst.",
        "Wollen eine neue Bestellung aufgeben, Katalog ist aber nicht erreichbar.",
        "Lieferung kam unvollstaendig an, zwei Positionen haben gefehlt.",
        "Auftrag wurde storniert, obwohl wir das nicht beantragt haben.",
        "Brauchen eine Eilbestellung, regulaere Lieferzeit ist zu lang.",
    ],
    "Reklamation": [
        "Die gelieferte Ware entspricht nicht der Bestellung, bitte um Ruecknahme.",
        "Mitarbeiter am Telefon war sehr unfreundlich, moechte das melden.",
        "Zum wiederholten Mal Probleme mit der gleichen Bestellung, sehr unzufrieden.",
        "Produkt kam beschaedigt an, Verpackung war bereits eingerissen.",
        "Seit Wochen keine Rueckmeldung auf unsere letzte Anfrage, das ist inakzeptabel.",
        "Erwarten eine Entschaedigung fuer den entstandenen Ausfall.",
    ],
}


def normalize_uid(uid):
    return uid.replace(" ", "").replace("-", "").upper() if uid else uid


def make_uid(i):
    return f"ATU{10000000 + i * 37 % 89999999}"


def legal_name(stem, form):
    if form == "GmbH":
        return f"{stem} GmbH"
    if form == "G.m.b.H.":
        return f"{stem} G.m.b.H."
    return f"{stem} {form}"


def build_customers():
    """Returns crm_rows, ticket_rows, and the list of 'clean+email+name' pairs
    (used later to know which ticket_customer_id values should generate
    tickets with a real, known customer behind them)."""
    crm_rows = []
    ticket_rows = []
    pairs = []  # (crm_kunden_nr, ticket_customer_id, expected_method)

    stems = NAME_STEMS[:]
    random.shuffle(stems)
    idx = 0

    def next_stem():
        nonlocal idx
        s = stems[idx % len(stems)]
        idx += 1
        return s

    crm_counter = 10041
    ticket_counter = 88213

    # --- 150 clean: UID matches on both sides (minor formatting noise) ---
    for i in range(150):
        stem = next_stem()
        form = random.choice(["GmbH", "GmbH", "KG", "OG"])
        name = legal_name(stem, form)
        uid_clean = make_uid(crm_counter)
        uid_crm = uid_clean if random.random() > 0.3 else f"{uid_clean[:3]} {uid_clean[3:]}"
        email = f"office@{stem.split()[0].lower()}.at"
        crm_nr = f"K-{crm_counter}"
        crm_rows.append({"kunden_nr": crm_nr, "firmenname": name, "uid": uid_crm,
                          "email": email, "land": "AT"})
        tkt_name = name if random.random() > 0.4 else legal_name(stem, "G.m.b.H.")
        tkt_vat = uid_clean if random.random() > 0.3 else f"{uid_clean[:3]} {uid_clean[3:]}"
        tkt_email = email.upper() if random.random() > 0.5 else email
        ticket_rows.append({"customer_id": ticket_counter, "company": tkt_name,
                             "vat": tkt_vat, "contact": tkt_email})
        pairs.append((crm_nr, ticket_counter, "uid"))
        crm_counter += 1
        ticket_counter += 1

    # --- 15 duplicated in the ticket system: a second customer_id, same company ---
    dup_targets = random.sample(pairs, 5)
    for crm_nr, orig_tid, _ in dup_targets:
        crm_row = next(r for r in crm_rows if r["kunden_nr"] == crm_nr)
        dup_row = dict(crm_row)
        ticket_rows.append({"customer_id": ticket_counter, "company": dup_row["firmenname"],
                             "vat": normalize_uid(dup_row["uid"]), "contact": dup_row["email"]})
        pairs.append((crm_nr, ticket_counter, "uid"))
        ticket_counter += 1

    # --- 15 email-only matches: UID blank/mismatched on one side ---
    for i in range(15):
        stem = next_stem()
        name = legal_name(stem, "GmbH")
        email = f"info@{stem.split()[0].lower()}.co.at"
        crm_nr = f"K-{crm_counter}"
        crm_rows.append({"kunden_nr": crm_nr, "firmenname": name, "uid": None,
                          "email": email, "land": "AT"})
        tkt_name = legal_name(stem, random.choice(["G.m.b.H.", "KG"]))  # name differs too
        ticket_rows.append({"customer_id": ticket_counter, "company": tkt_name,
                             "vat": None, "contact": email.upper()})
        pairs.append((crm_nr, ticket_counter, "email"))
        crm_counter += 1
        ticket_counter += 1

    # --- 15 name-normalized-only matches: neither UID nor email align ---
    for i in range(15):
        stem = next_stem()
        name = legal_name(stem, "GmbH").replace("&", "und")
        crm_nr = f"K-{crm_counter}"
        crm_rows.append({"kunden_nr": crm_nr, "firmenname": name, "uid": None,
                          "email": f"kontakt{crm_counter}@{stem.split()[0].lower()}.at",
                          "land": random.choice(["AT", "DE"])})
        tkt_name = name.replace("GmbH", "G.m.b.H.")
        ticket_rows.append({"customer_id": ticket_counter, "company": tkt_name,
                             "vat": None, "contact": f"support-contact-{ticket_counter}@extern.example"})
        pairs.append((crm_nr, ticket_counter, "name_normalisiert"))
        crm_counter += 1
        ticket_counter += 1

    # --- 8 CRM-only (never made it into the ticket system) ---
    for i in range(8):
        stem = next_stem()
        name = legal_name(stem, "e.U.")
        crm_nr = f"K-{crm_counter}"
        crm_rows.append({"kunden_nr": crm_nr, "firmenname": name, "uid": make_uid(crm_counter),
                          "email": f"office@{stem.split()[0].lower()}.at", "land": "AT"})
        crm_counter += 1

    # --- 7 ticket-only (walk-in support contacts, never entered the CRM) ---
    for i in range(7):
        stem = next_stem()
        name = legal_name(stem, "KG")
        ticket_rows.append({"customer_id": ticket_counter, "company": name,
                             "vat": None, "contact": f"anfrage-{ticket_counter}@extern.example"})
        ticket_counter += 1

    return crm_rows, ticket_rows, pairs


def write_sources(crm_rows, ticket_rows):
    with open(DATA_DIR / "crm_kunden.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["kunden_nr", "firmenname", "uid", "email", "land"])
        w.writeheader()
        for r in crm_rows:
            w.writerow({k: ("" if v is None else v) for k, v in r.items()})

    with open(DATA_DIR / "ticket_kunden.json", "w", encoding="utf-8") as f:
        json.dump(ticket_rows, f, ensure_ascii=False, indent=2)


def generate_tickets(ticket_rows, n=3000, months_back=6):
    """Generates ticket rows as dicts, ready to insert. ~12% breach SLA,
    ~6% get reopened. Free text + category come from the same template
    (ground truth), channel/priority are independent of category."""
    import datetime
    now = datetime.datetime(2026, 10, 1, 9, 0, 0)
    start = now - datetime.timedelta(days=30 * months_back)
    customer_ids = [r["customer_id"] for r in ticket_rows]

    tickets = []
    for i in range(n):
        category = random.choice(CATEGORIES)
        text = random.choice(TEMPLATES[category])
        customer_id = random.choice(customer_ids)
        channel = random.choices(CHANNELS, weights=[40, 20, 30, 10])[0]
        priority = random.choices(PRIORITIES, weights=[25, 45, 22, 8])[0]

        created_offset = random.random() * (now - start).total_seconds()
        erstellt_am = start + datetime.timedelta(seconds=created_offset)
        sla_hours = SLA_HOURS[priority]
        sla_frist = erstellt_am + datetime.timedelta(hours=sla_hours)

        first_resp_minutes = random.expovariate(1 / 90)  # ~90 min average
        erste_antwort_am = erstellt_am + datetime.timedelta(minutes=min(first_resp_minutes, 2800))

        breach = random.random() < 0.12
        if breach:
            resolve_hours = sla_hours * random.uniform(1.1, 3.0)
        else:
            resolve_hours = sla_hours * random.uniform(0.1, 0.95)
        geloest_am = erstellt_am + datetime.timedelta(hours=resolve_hours)
        if geloest_am > now:
            geloest_am = None  # still open

        wiedereroeffnet = bool(geloest_am and random.random() < 0.06)

        tickets.append({
            "ticket_customer_id": customer_id,
            "betreff": text[:48] + ("…" if len(text) > 48 else ""),
            "beschreibung": text,
            "kategorie": category,
            "kanal": channel,
            "prioritaet": priority,
            "erstellt_am": erstellt_am,
            "erste_antwort_am": erste_antwort_am,
            "geloest_am": geloest_am,
            "wiedereroeffnet": wiedereroeffnet,
            "sla_frist": sla_frist,
        })
    return tickets


if __name__ == "__main__":
    crm_rows, ticket_rows, pairs = build_customers()
    write_sources(crm_rows, ticket_rows)
    print(f"crm_kunde: {len(crm_rows)} rows -> data/crm_kunden.csv")
    print(f"ticket_kunde: {len(ticket_rows)} rows -> data/ticket_kunden.json")
    print(f"expected pairs (ground truth for the matching report): {len(pairs)}")

    tickets = generate_tickets(ticket_rows)
    with open(DATA_DIR / "tickets.json", "w", encoding="utf-8") as f:
        import datetime
        json.dump(tickets, f, default=str, ensure_ascii=False, indent=2)
    print(f"ticket: {len(tickets)} rows -> data/tickets.json")

    # ground truth pairs, used by sql/03_abgleich.sql's sanity check and by
    # docs — not part of the "real" pipeline, just how we know the matcher
    # is actually getting the right answer and not just a plausible one.
    with open(DATA_DIR / "_ground_truth_pairs.json", "w", encoding="utf-8") as f:
        json.dump(pairs, f, indent=2)
