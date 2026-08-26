# Wohnungssuche Oberbayern

Automatische Wohnungssuche: durchsucht mehrmals täglich WG-gesucht nach günstigen
1-Zimmer-Wohnungen in Oberbayern und schickt **eine gesammelte E-Mail** mit allen
neuen Treffern — statt einer Mail pro Angebot.

Läuft komplett kostenlos in GitHub Actions. Kein Server, kein lokaler Rechner nötig.

## Was du einstellen kannst — nur eine Datei

Alle Zahlen stehen in **[`suche.yml`](suche.yml)**. Zum Ändern:

1. [`suche.yml`](suche.yml) hier auf GitHub öffnen
2. Auf das **Stift-Symbol** (✏️ Edit) klicken
3. Zahl ändern → unten auf **Commit changes** klicken

Der nächste Lauf benutzt automatisch die neuen Werte. Kein Code, kein Terminal.

```yaml
max_warm: 600     # Obergrenze Warmmiete (Gesamtmiete)
max_kalt: 450     # Obergrenze Kaltmiete
min_qm: 28
max_qm: 50
radius_km: 30
staedte: [ ... ]
```

### Warum zwei Preisgrenzen?

Die Portale meinen mit „Miete" nicht dasselbe:

| Quelle | zeigt | wird geprüft gegen |
|--------|-------|--------------------|
| WG-gesucht | meist **Gesamtmiete (warm)** | `max_warm` |
| Immowelt (per E-Mail) | **Kaltmiete** | `max_kalt` |

Deshalb wird jedes Angebot gegen die passende Grenze geprüft. Faustregel: bei 28–50 m²
liegen die Nebenkosten grob bei 100–180 €, `max_kalt` sollte also rund 150 € unter
`max_warm` liegen.

### Einmalig anders suchen, ohne etwas zu ändern

**Actions → Wohnungssuche Scraper → Run workflow** — dort lassen sich `max_warm`,
`max_kalt` und `radius_km` für genau diesen einen Lauf überschreiben.

## Wie es funktioniert

```
GitHub Actions (3x täglich)
   └─ build_config.py   suche.yml ──> config.yaml (WG-gesucht-Such-URLs)
   └─ run_digest.py     flathunter als Bibliothek + Immowelt-Mails
        └─ Preisfilter (warm/kalt)
             └─ eine Sammel-E-Mail via Apprise
```

- `tool/build_config.py` – baut die Portal-URLs aus `suche.yml`
- `tool/run_digest.py` – sammelt neue Angebote und verschickt **einen** Digest
- `tool/immowelt_mail_parser.py` – liest Immowelt-Benachrichtigungen per IMAP
- `tool/state/processed_ids.db` – schon gesehene Angebote (verhindert Doppel-Mails)
- `kriterien.md` – inhaltliche Wunschkriterien (rein informativ)

## Einrichtung

Nötig ist genau ein Repository-Secret:

| Secret | Inhalt |
|--------|--------|
| `FLATHUNTER_APPRISE_URL` | `mailto://ADRESSE:APP_PASSWORT@gmail.com?to=ADRESSE@gmail.com` |

Anlegen unter **Settings → Secrets and variables → Actions → New repository secret**.
Details und die Immowelt-Einrichtung: [`tool/SETUP-ANLEITUNG.md`](tool/SETUP-ANLEITUNG.md).

> Das Secret enthält ein Google-App-Passwort. Es steht **nur** in den GitHub-Secrets;
> die daraus erzeugte `config.yaml` ist per `.gitignore` ausgeschlossen.

## Mehr Treffer bekommen

WG-gesucht ist außerhalb der größeren Städte dünn besetzt. Der wirksamste Zusatz sind
**gespeicherte Suchen auf immowelt.de** für Oberbayern mit Kaltmiete ≤ `max_kalt`, deren
E-Mail-Benachrichtigungen an dieselbe Adresse gehen — `immowelt_mail_parser.py` liest sie
automatisch mit. ImmoScout24 wird bewusst nicht gescrapt (Captcha-Schutz).

## Lokal testen

```bash
pip install PyYAML
python tool/build_config.py     # erzeugt tool/config.yaml + tool/limits.yaml
```

## Lizenz / Hinweis

Nutzt [flathunter](https://github.com/flathunters/flathunter) (als Submodul) für das
Auslesen der Portale. Private Nutzung; bitte die Nutzungsbedingungen der Portale beachten.
