#!/usr/bin/env python
"""Erzeugt config.yaml aus suche.yml + config.yaml.template.

So muss man zum Ändern der Suche nur suche.yml anfassen (reine Zahlen,
direkt auf github.com editierbar) und nicht die Flathunter-Konfiguration
mit ihren langen Portal-URLs.

Umgebungsvariablen (optional, für einmalige manuelle Läufe):
  OVERRIDE_MAX_WARM, OVERRIDE_MAX_KALT, OVERRIDE_RADIUS_KM
überschreiben die Werte aus suche.yml, ohne dass etwas committet wird.
"""
import os
import sys
from urllib.parse import quote

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

SUCHE = os.path.join(ROOT, "suche.yml")
TEMPLATE = os.path.join(HERE, "config.yaml.template")
OUTPUT = os.path.join(HERE, "config.yaml")

# WG-gesucht akzeptiert nur diese Radius-Stufen (Meter).
ERLAUBTE_RADIEN_KM = [0, 5, 10, 15, 20, 30, 40, 50]


def _int_env(name, fallback):
    raw = os.environ.get(name, "").strip()
    if not raw:
        return fallback
    try:
        return int(float(raw))
    except ValueError:
        print(f"WARNUNG: {name}={raw!r} ist keine Zahl - ignoriert.", file=sys.stderr)
        return fallback


def naechster_radius(km):
    """WG-gesucht kennt nur feste Stufen; auf die nächstgelegene runden."""
    return min(ERLAUBTE_RADIEN_KM, key=lambda stufe: abs(stufe - km))


def baue_url(stadt_id, min_qm, max_qm, max_warm, radius_km, nur_unbefristet=True):
    """Eine WG-gesucht-Suche für 1-Zimmer-Wohnungen in einer Stadt.

    Die Preisspanne beginnt bei 0: eine untere Grenze würde günstige
    Treffer verwerfen, und genau die suchen wir.
    """
    radius_m = naechster_radius(radius_km) * 1000
    rent_range = quote(f"0,{max_warm}")
    # rent_types: 2 = unbefristet, 1/3 = befristet bzw. Zwischenmiete.
    # Ohne Filter besteht das Ergebnis fast nur aus Kurzzeit-Untermieten.
    rent_types = "&rent_types%5B%5D=2" if nur_unbefristet else (
        "&rent_types%5B%5D=2&rent_types%5B%5D=1&rent_types%5B%5D=3")
    return (
        f"https://www.wg-gesucht.de/1-zimmer-wohnungen-in-Oberbayern.{stadt_id}.1.1.0.html"
        f"?categories%5B%5D=1"
        f"{rent_types}"
        f"&min_size={min_qm}&max_size={max_qm}"
        f"&rent_range={rent_range}&rMin=0&rMax={max_warm}"
        f"&sMin={min_qm}&sMax={max_qm}"
        f"&offer_filter=1&city_id={stadt_id}&sort_order=0&noDeact=1"
        f"&radDis={radius_m}"
    )


def main():
    with open(SUCHE, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)

    max_warm = _int_env("OVERRIDE_MAX_WARM", int(cfg["max_warm"]))
    max_kalt = _int_env("OVERRIDE_MAX_KALT", int(cfg["max_kalt"]))
    radius_km = _int_env("OVERRIDE_RADIUS_KM", int(cfg["radius_km"]))
    min_qm, max_qm = int(cfg["min_qm"]), int(cfg["max_qm"])
    nur_unbefristet = bool(cfg.get("nur_unbefristet", True))
    staedte = cfg["staedte"]

    if max_kalt > max_warm:
        print(
            f"WARNUNG: max_kalt ({max_kalt}) > max_warm ({max_warm}). "
            "Die Kaltmiete sollte niedriger sein als die Warmmiete.",
            file=sys.stderr,
        )

    urls = []
    for stadt in staedte:
        urls.append(f"  # {stadt['name']} ({naechster_radius(radius_km)} km Umkreis)")
        urls.append(f"  - {baue_url(stadt['id'], min_qm, max_qm, max_warm, radius_km, nur_unbefristet)}")

    with open(TEMPLATE, encoding="utf-8") as fh:
        template = fh.read()

    # Der Template-Block zwischen "urls:" und "filters:" wird komplett ersetzt.
    kopf, _, rest = template.partition("urls:")
    _, _, schwanz = rest.partition("\nfilters:")
    if not schwanz:
        print("FEHLER: config.yaml.template hat keinen 'filters:'-Block.", file=sys.stderr)
        return 1

    schwanz = schwanz.replace("min_size: 28", f"min_size: {min_qm}")
    schwanz = schwanz.replace("max_size: 50", f"max_size: {max_qm}")
    # Flathunters globaler Filter bleibt bewusst großzügig (Warmwert):
    # die genaue warm/kalt-Unterscheidung macht run_digest.py.
    schwanz = schwanz.replace("max_price: 950", f"max_price: {max_warm}")

    ergebnis = kopf + "urls:\n" + "\n".join(urls) + "\nfilters:" + schwanz

    with open(OUTPUT, "w", encoding="utf-8") as fh:
        fh.write(ergebnis)

    # Von run_digest.py gelesen, damit dort warm/kalt getrennt gefiltert wird.
    limits_path = os.path.join(HERE, "limits.yaml")
    with open(limits_path, "w", encoding="utf-8") as fh:
        yaml.safe_dump({"max_warm": max_warm, "max_kalt": max_kalt}, fh)

    print(
        f"config.yaml erzeugt: {len(staedte)} Städte, "
        f"{min_qm}-{max_qm} m², max {max_warm} EUR warm / {max_kalt} EUR kalt, "
        f"{naechster_radius(radius_km)} km Umkreis"
        + (", nur unbefristet" if nur_unbefristet else ", auch befristet")
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
