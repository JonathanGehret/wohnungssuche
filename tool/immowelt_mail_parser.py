#!/usr/bin/env python
"""Holt neue Immowelt-Benachrichtigungs-E-Mails per IMAP und parst Angebote daraus.

Ersetzt das direkte Scrapen von Immowelt (seit einem DataDome-Bot-Schutz mit
403-Fehlern blockiert). Stattdessen legt der Nutzer gespeicherte Suchen direkt
auf immowelt.de an und lässt sich E-Mail-Benachrichtigungen schicken - Daten,
die Immowelt selbst und beabsichtigt verschickt, kein Scraping-Graubereich.

Dieses Skript liest diese Mails per IMAP vom selben Gmail-Konto, das auch für
den E-Mail-Versand genutzt wird (Zugangsdaten werden aus der ohnehin
konfigurierten Apprise-URL extrahiert, kein zusätzliches Secret nötig), parst
die enthaltenen Angebote und gibt sie im gleichen Format wie Flathunter-
Exposés zurück, damit sie in den gemeinsamen Digest einfließen.

HINWEIS: Das Parsing basiert auf dem aktuellen Immowelt-E-Mail-Layout (Stand:
Ersteinrichtung). Ändert Immowelt das Layout, liefert der Parser ggf. weniger
Details (Preis/Größe/Zimmer als "N/A"), der Link zum Angebot bleibt aber in
den allermeisten Fällen erhalten, da nur nach dem URL-Muster gesucht wird.
"""
import email
import imaplib
import json
import re
from email.header import decode_header
from pathlib import Path
from urllib.parse import urlparse

from bs4 import BeautifulSoup

IMAP_HOST = "imap.gmail.com"
SEEN_STATE_FILE = Path(__file__).parent / "state" / "immowelt_seen.json"

LISTING_URL_PATTERN = re.compile(r"https://www\.immowelt\.de/expose/[a-zA-Z0-9]+")
PRICE_PATTERN = re.compile(r"(\d[\d.,]*)\s?€")
SIZE_PATTERN = re.compile(r"(\d[\d.,]*)\s?m²")
ROOMS_PATTERN = re.compile(r"(\d[\d.,]*)\s?Zimmer")


def _credentials_from_apprise_url(apprise_url: str):
    """Extrahiert Gmail-Adresse + App-Passwort aus der bestehenden Apprise-URL,
    damit kein zweites Secret für IMAP-Zugriff nötig ist."""
    parsed = urlparse(apprise_url)
    address = f"{parsed.username}@{parsed.hostname}"
    return address, parsed.password


def _load_seen() -> set:
    if not SEEN_STATE_FILE.exists():
        return set()
    return set(json.loads(SEEN_STATE_FILE.read_text(encoding="utf-8")))


def _save_seen(seen: set) -> None:
    SEEN_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    SEEN_STATE_FILE.write_text(
        json.dumps(sorted(seen), ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _extract_html_body(msg) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                charset = part.get_content_charset() or "utf-8"
                payload = part.get_payload(decode=True)
                return payload.decode(charset, errors="replace") if payload else ""
        return ""
    if msg.get_content_type() == "text/html":
        charset = msg.get_content_charset() or "utf-8"
        payload = msg.get_payload(decode=True)
        return payload.decode(charset, errors="replace") if payload else ""
    return ""


def _parse_listings_from_html(html: str) -> list:
    """Best-effort-Parser für Immowelt-Benachrichtigungs-E-Mails.

    Sucht nach Links zu Objekt-Detailseiten und extrahiert Preis/Größe/Zimmer
    aus dem umgebenden Text. Fehlt ein Einzelfeld, wird trotzdem der Link mit
    "N/A"-Platzhaltern zurückgegeben, statt den gesamten Eintrag zu verwerfen.
    """
    soup = BeautifulSoup(html, "html.parser")
    listings = []
    seen_urls_in_mail = set()

    for link in soup.find_all("a", href=True):
        match = LISTING_URL_PATTERN.search(link["href"])
        if not match:
            continue
        url = match.group(0)
        if url in seen_urls_in_mail:
            continue
        seen_urls_in_mail.add(url)

        container = link.find_parent(["td", "div", "li", "table"]) or link
        context_text = container.get_text(separator=" ", strip=True)
        title = link.get_text(strip=True) or context_text[:80]

        price_match = PRICE_PATTERN.search(context_text)
        size_match = SIZE_PATTERN.search(context_text)
        rooms_match = ROOMS_PATTERN.search(context_text)

        listings.append({
            "crawler": "Immowelt (E-Mail)",
            "title": title or "N/A",
            "url": url,
            "price": f"{price_match.group(1)} €" if price_match else "N/A",
            "size": f"{size_match.group(1)} m²" if size_match else "N/A",
            "rooms": rooms_match.group(1) if rooms_match else "N/A",
            "address": "N/A",
        })

    return listings


def fetch_new_immowelt_listings(apprise_url: str, logger=None) -> list:
    """Holt neue, noch nicht gesehene Immowelt-Angebote aus ungelesenen E-Mails.

    Gibt bei jedem Fehler (Login, IMAP nicht aktiviert, etc.) eine leere Liste
    zurück statt den gesamten Digest-Lauf abzubrechen - Immowelt-Mails sind
    eine Ergänzung, kein kritischer Pfad.
    """
    def log(msg, *args):
        if logger:
            logger.info(msg, *args)

    def log_warn(msg, *args):
        if logger:
            logger.warning(msg, *args)

    try:
        address, app_password = _credentials_from_apprise_url(apprise_url)
    except (ValueError, AttributeError):
        log_warn("Konnte keine Zugangsdaten aus der Apprise-URL extrahieren - "
                  "Immowelt-Mail-Abruf übersprungen")
        return []

    seen = _load_seen()
    new_listings = []

    try:
        conn = imaplib.IMAP4_SSL(IMAP_HOST)
    except OSError:
        log_warn("Konnte keine Verbindung zu %s aufbauen - Immowelt-Mail-Abruf übersprungen",
                  IMAP_HOST)
        return []

    try:
        conn.login(address, app_password)
        conn.select("INBOX")
        status, data = conn.search(None, '(UNSEEN FROM "immowelt.de")')
        if status != "OK":
            log_warn("IMAP-Suche fehlgeschlagen - Immowelt-Mail-Abruf übersprungen")
            return []

        message_ids = data[0].split()
        log("%d ungelesene Immowelt-E-Mail(s) gefunden", len(message_ids))

        for msg_id in message_ids:
            status, msg_data = conn.fetch(msg_id, "(BODY.PEEK[])")
            if status != "OK" or not msg_data or not msg_data[0]:
                continue
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)
            html = _extract_html_body(msg)
            if not html:
                continue

            for listing in _parse_listings_from_html(html):
                if listing["url"] in seen:
                    continue
                seen.add(listing["url"])
                new_listings.append(listing)

            # Erst nach erfolgreichem Parsen als gelesen markieren
            conn.store(msg_id, "+FLAGS", "\\Seen")
    except imaplib.IMAP4.error as exc:
        log_warn("IMAP-Fehler beim Immowelt-Mail-Abruf: %s", exc)
        return new_listings
    finally:
        try:
            conn.logout()
        except Exception:
            pass

    if new_listings:
        _save_seen(seen)

    return new_listings
