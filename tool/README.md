# Scraper-Tool für Wohnungsangebote

## Übersicht

Automatisierter Scraper für neue Wohnungsangebote in Bayern, basierend auf **Flathunter** (github.com/flathunters/flathunter), mit E-Mail-Benachrichtigung via GitHub Actions (stündlich).

### Portale

Aktuell unterstützt:
- **WG-Gesucht** (reine HTTP-Crawler, keine Captcha)
- **Immowelt** (reine HTTP-Crawler, keine Captcha)
- **Kleinanzeigen** (Selenium/Headless-Chrome nötig, aber funktionstüchtig auf GitHub Actions)

Nicht hinzugefügt (zu viel Captcha-Aufwand):
- **ImmoScout24** (aktuell auch mit bezahltem Solver unreliable laut Flathunter-Upstream)

## Setup

> ➡️ **Für die geführte Erstinbetriebnahme** (Schritt für Schritt, inkl. fertigem Browser-Agent-Prompt zum Anlegen der 8 Suchen) siehe **[`SETUP-ANLEITUNG.md`](SETUP-ANLEITUNG.md)**. Der folgende Abschnitt ist die kompaktere Referenz.

### 1. GitHub Secrets setzen

Repository-Einstellung **Settings → Secrets and variables → Actions**:

- **`FLATHUNTER_APPRISE_URL`** – die echte Apprise-Benachrichtigungs-URL
  - Beispiel für Gmail: `mailto://deine-adresse:DEIN_APP_PASSWORT@gmail.com?to=deine-adresse@example.com`
  - (Andere SMTP-Provider: siehe [Apprise Wiki](https://github.com/caronc/apprise/wiki/Notify_Email))

### 2. Gespeicherte Suchen anlegen

Für jede der 4 Zielregionen und beide Portale (WG-Gesucht, Immowelt) müssen Sie jeweils:

1. Zur Portal-Website gehen
2. Suche mit den Filtern anlegen:
   - **Ort:** der Zielort (z.B. "Rosenheim")
   - **Größe:** 28–50 m²
   - **Preis:** Region-spezifisch (z.B. 500–900 für Rosenheim)
   - **Sortieren:** nach Neuesten
3. Die resultierende URL kopieren und in `config.yaml.template` unter der richtigen Region einfügen

→ Das ergibt insgesamt **8 URLs** (4 Regionen × 2 Portale).

Beispiel (WG-Gesucht):
```
https://www.wg-gesucht.de/1-zimmer-wohnungen-in-Rosenheim.html?noDeact=1&listsize=25&...
```

### 3. Repo-Einstellung: Workflow Permissions

Repository **Settings → Actions → General → Workflow permissions:**
- Stelle auf **"Read and write permissions"** 
  - (Der Workflow muss die aktualisierte `processed_ids.db` zurückcommitten können)

### 4. Workflow testen

Navigiere im Repo zu **Actions** → **Wohnungssuche** → **Run workflow** → **Run workflow** (manuell auslösen).

Überprüfe die Logs:
- Config wird ohne Fehler gerendert
- Mindestens ein Portal liefert Treffer
- E-Mail wird versendet (prüfe dein Postfach)
- `processed_ids.db` wird committet

---

## Verwendung

### Automatische Läufe
Wenn alles konfiguriert ist, läuft der Scraper **stündlich um 7 Minuten nach der vollen Stunde** (z.B. 10:07, 11:07, ...) – Google-Actions-Docs-freundlich versetzt, um das Hochlast-Fenster zu meiden.

→ Du erhältst **eine E-Mail pro Stunde** mit **neuen** Angeboten, die noch nicht gesehen wurden.

### Manuelle Läufe
- Im Repo **Actions** → **Wohnungssuche** → **Run workflow** → **Run workflow**
- Nützlich für schnelle Tests oder wenn du eine sofortige Überprüfung brauchst (z.B. nach regionalen Suchparamter-Änderungen)

### Lokale Testläufe (optional)

Falls du lokal testen willst, ohne GitHub Actions:

```bash
cd wohnungssuche/tool/flathunter

# Abhängigkeiten installieren
pip install pipenv
pipenv install --deploy --system

# Config rendern (ersetzt ${FLATHUNTER_APPRISE_URL} durch eine Test-URL)
# (oder manuell config.yaml mit echten Secrets aus .env.example erstellen)

# Scraper ausführen
export FLATHUNTER_DATABASE_LOCATION="../state"
export FLATHUNTER_APPRISE_URL="mailto://test@example.com"
export FLATHUNTER_HEADLESS_BROWSER=1

python -m flathunt --config ../config.yaml
```

→ Logs zeigen, was gescraped wurde; Benachrichtigungen werden über Apprise versendet.

---

## Struktur

```
wohnungssuche/tool/
├── flathunter/                  # Vendor: git submodule, gepinnt auf einen Commit-SHA
│   └── (Flathunter-Quellcode, nicht anfassen)
├── config.yaml.template         # Template mit Platzhalt-Tokens, versioniert
├── state/
│   └── processed_ids.db         # SQLite-Dedupe-Datenbank, vom Workflow gepflegt
├── .env.example                 # Dokumentation der Umgebungsvariablen
└── README.md                    # Diese Datei
```

Die echte, secret-haltige `config.yaml` wird **zur Laufzeit** vom Workflow generiert und **nie ins Repo** committet.

---

## Fehlerbehandlung

### Keine E-Mails erhalten?

1. **Apprise-URL korrekt?** Öffne `github.secrets.FLATHUNTER_APPRISE_URL` → syntax prüfen (z.B. falsch URL-codiert?)
2. **Spam-Folder?** Gmail und andere Filter aggressive → prüf Spam
3. **Workflow fehlgeschlagen?** Repo **Actions** → **Wohnungssuche** → letzter Lauf → Logs prüfen
4. **Zu viele Filter?** Falls kein Portal Treffer liefert: die regionalen Suchparameter in den Portal-URLs prüfen (zu restriktiv?)

### Dedupe-DB verloren?
Falls `processed_ids.db` corrupt wird oder gelöscht werden muss:
- Einfach löschen/zurücksetzen
- Der nächste Workflow-Lauf erstellt sie neu
- Nebeneffekt: aktuell gelistete Angebote werden (einmalig) re-notifiziert – nicht tragisch, kein Crash

### Workflow läuft nicht?

1. **Repo-Einstellung:** Workflow permissions auf read/write?
2. **Secret gesetzt?** → `FLATHUNTER_APPRISE_URL` muss existieren (ohne dieses Secret wird der Schritt `envsubst` fehlschlagen)
3. **Git-Submodule initialisiert?** → `git submodule update --init --recursive` lokal ausführen, wenn nötig
4. **Nächster manueller Trigger:** **Actions** → **Wohnungssuche** → **Run workflow**

---

## Regionsspezifische Preiskalibrierung

Die Preisfilter in den Portal-URLs sollen die regionale Realität widerspiegeln:

| Region | WG-Gesucht-Filter | Immowelt-Filter | Grund |
|--------|-------------------|-----------------|-------|
| Rosenheim | €500–900 warm | €500–900 warm | Basis-Region, erforscht |
| Ammersee/Inning | €550–950 warm | €550–950 warm | Höher als Rosenheim, München-nähe |
| Unterfranken | €400–800 warm | €400–800 warm | Günstiger, ländlicher |
| Münch. Umland | €550–900 warm | €550–900 warm | zwischen Rosenheim + Ammersee |

**Hinweis:** Das ist nicht "hart" – die globale `filters:`-Block hat noch `max_price: 950` als Sicherheitsnetz. Aber die regionsspezifische Obergrenze in der portal-spezifischen URL ist das, was wirklich zählt.

---

## Zukunfts-Optionen

### Kleinanzeigen hinzufügen
Bereits vorbereitet. Nötig:
- Kleinanzeigen-URLs (wie oben) zu `config.yaml.template` hinzufügen
- Im Workflow `FLATHUNTER_HEADLESS_BROWSER=1` setzen (bereits der Fall)

### ImmoScout24 (nicht empfohlen)
Falls irgendwann ImmoScout24-Unterstützung erstrebenswert ist:
- `FLATHUNTER_CAPMONSTER_KEY` GitHub Secret setzen (mit echtem Capmonster-Account + Guthaben)
- ImmoScout24-URL zu config hinzufügen
- **Caveat:** Laut Flathunter-Upstream funktioniert es auch damit nicht zuverlässig (siehe GitHub-Issues #296/#302) – braucht kontinuierliche Überwachung

---

## Referenzen

- Flathunter GitHub: https://github.com/flathunters/flathunter
- Flathunter README: https://github.com/flathunters/flathunter/blob/main/README.md
- Apprise (Benachrichtigungen): https://github.com/caronc/apprise

---

*Zuletzt aktualisiert: Juli 2026*
