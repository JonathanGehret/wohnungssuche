#!/usr/bin/env python
"""Eigenständiges Digest-Skript für den Wohnungssuche-Scraper.

Nutzt Flathunter nur als Bibliothek (kein Eingriff in den Vendor-Code
unter flathunter/). Statt jedes neue Angebot einzeln per Apprise zu
versenden (Flathunters Standardverhalten), werden alle neuen Angebote
eines Laufs gesammelt und als EINE zusammengefasste E-Mail verschickt.

Voraussetzung: config.yaml.template setzt "notifiers: []", damit
Flathunter selbst keine Einzel-Benachrichtigungen verschickt - dieses
Skript übernimmt den Versand komplett.
"""
import argparse
import os
import re
import sys
from typing import Optional

FLATHUNTER_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "flathunter")
sys.path.insert(0, FLATHUNTER_DIR)

# Der vendorte Flathunter-Code setzt bei requests.get()/post()-Aufrufen keinen
# expliziten Timeout - eine Verbindung, die angenommen aber nie beantwortet
# wird, blockiert dann unbegrenzt (ohne Timeout hängt requests im Zweifel
# ewig). Statt den Vendor-Code selbst zu patchen, wird hier von außen ein
# Default-Timeout erzwungen, bevor irgendein flathunter-Modul importiert wird.
import requests  # noqa: E402

_original_request = requests.Session.request


def _request_with_default_timeout(self, method, url, **kwargs):
    kwargs.setdefault("timeout", 30)
    return _original_request(self, method, url, **kwargs)


requests.Session.request = _request_with_default_timeout

import apprise  # noqa: E402  (import after sys.path setup)
import yaml  # noqa: E402
from flathunter.config import Config  # noqa: E402
from flathunter.hunter import Hunter  # noqa: E402
from flathunter.idmaintainer import IdMaintainer  # noqa: E402
from flathunter.logging import logger, configure_logging  # noqa: E402

from immowelt_mail_parser import fetch_new_immowelt_listings  # noqa: E402


ITEM_TEMPLATE = (
    "{crawler}: {title}\n"
    "Ort: {address}\n"
    "Zimmer: {rooms} | Größe: {size}m² | Preis: {price}€ {basis}\n"
    "{url}"
)


# Welcher Preis steht in einem Angebot? WG-gesucht nennt in der Regel die
# Gesamtmiete (warm), die Immowelt-Mails dagegen die Kaltmiete. Deshalb wird
# je Quelle gegen eine andere Obergrenze geprueft.
KALT_QUELLEN = ("immowelt", "immobilienscout", "immoscout")


def preis_basis(expose: dict) -> str:
    """'kalt' oder 'warm' - je nachdem, was das Portal ausweist."""
    crawler = str(expose.get("crawler", "")).lower()
    return "kalt" if any(q in crawler for q in KALT_QUELLEN) else "warm"


def parse_preis(rohwert):
    """Zieht die erste Zahl aus z.B. '580 EUR' oder '1.250 EUR'."""
    if rohwert is None:
        return None
    text = str(rohwert).replace(".", "").replace(",", ".")
    treffer = re.search(r"\d+(?:\.\d+)?", text)
    return float(treffer.group()) if treffer else None


def lade_limits() -> dict:
    """Grenzwerte aus limits.yaml (von build_config.py aus suche.yml erzeugt)."""
    pfad = os.path.join(os.path.dirname(os.path.abspath(__file__)), "limits.yaml")
    if not os.path.exists(pfad):
        logger.warning("limits.yaml fehlt - Preisfilter wird uebersprungen")
        return {}
    with open(pfad, encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def filtere_nach_preis(exposes: list, limits: dict) -> list:
    """Verwirft Angebote ueber der jeweiligen warm-/kalt-Obergrenze.

    Ein Angebot ohne erkennbaren Preis wird behalten - lieber ein Treffer
    zu viel als eine verpasste guenstige Wohnung.
    """
    max_warm = limits.get("max_warm")
    max_kalt = limits.get("max_kalt")
    if max_warm is None and max_kalt is None:
        return exposes

    behalten = []
    for expose in exposes:
        basis = preis_basis(expose)
        grenze = max_kalt if basis == "kalt" else max_warm
        preis = parse_preis(expose.get("price"))
        if grenze is not None and preis is not None and preis > grenze:
            logger.info("Verworfen (%.0f EUR %s > %s EUR): %s",
                        preis, basis, grenze, str(expose.get("title"))[:60])
            continue
        behalten.append(expose)
    return behalten


def format_digest(exposes: list) -> str:
    """Baut eine einzige zusammengefasste Nachricht aus mehreren Exposés."""
    blocks = []
    for expose in exposes:
        blocks.append(ITEM_TEMPLATE.format(
            crawler=expose.get("crawler", "N/A"),
            title=expose.get("title", "N/A"),
            rooms=expose.get("rooms", "N/A"),
            size=expose.get("size", "N/A"),
            price=expose.get("price", "N/A"),
            url=expose.get("url", "N/A"),
            address=expose.get("address", "N/A"),
            basis=preis_basis(expose),
        ))
    header = f"{len(exposes)} neue Wohnungsangebote gefunden:\n\n"
    return header + "\n\n---\n\n".join(blocks)


def send_digest(config: Config, message: str) -> None:
    """Verschickt die zusammengefasste Nachricht über die konfigurierten Apprise-URLs."""
    apprise_urls = config.get("apprise", []) or []
    if not apprise_urls:
        logger.warning("Keine Apprise-URL konfiguriert - Digest wird nur geloggt, nicht versendet")
        return
    apobj = apprise.Apprise()
    for url in apprise_urls:
        apobj.add(url)
    apobj.notify(
        body=message,
        title="Wohnungssuche: neue Angebote",
        body_format=apprise.NotifyFormat.TEXT,
    )


def main():
    parser = argparse.ArgumentParser(description="Wohnungssuche-Scraper mit gesammelter Digest-E-Mail")
    parser.add_argument("--config", "-c", required=True, help="Pfad zur gerenderten config.yaml")
    args = parser.parse_args()

    config = Config(args.config)
    configure_logging(config)
    config.init_searchers()

    id_watch = IdMaintainer(f"{config.database_location()}/processed_ids.db")
    hunter = Hunter(config, id_watch)

    new_exposes = list(hunter.hunt_flats())

    apprise_urls = config.get("apprise", []) or []
    if apprise_urls:
        immowelt_listings = fetch_new_immowelt_listings(apprise_urls[0], logger=logger)
        new_exposes.extend(immowelt_listings)

    vorher = len(new_exposes)
    new_exposes = filtere_nach_preis(new_exposes, lade_limits())
    if vorher != len(new_exposes):
        logger.info("%d von %d Angeboten wegen Preisgrenze verworfen",
                    vorher - len(new_exposes), vorher)

    vorher = len(new_exposes)
    new_exposes = filtere_nach_preis(new_exposes, lade_limits())
    if vorher != len(new_exposes):
        logger.info("%d von %d Angeboten wegen Preisgrenze verworfen",
                    vorher - len(new_exposes), vorher)

    if not new_exposes:
        logger.info("Keine neuen Angebote in diesem Lauf")
        return

    logger.info("%d neue Angebote gefunden - verschicke gesammelten Digest", len(new_exposes))
    message = format_digest(new_exposes)
    send_digest(config, message)
    logger.info("Digest versendet")


if __name__ == "__main__":
    main()
