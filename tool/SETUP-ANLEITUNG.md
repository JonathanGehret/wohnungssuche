# Setup-Anleitung: Wohnungs-Scraper in Betrieb nehmen

**Start hier.** Diese Anleitung führt dich einmalig durch die Aktivierung. Danach läuft der Scraper automatisch stündlich und schickt dir neue Wohnungsangebote per E-Mail.

Der Ablauf hat drei Teile:
- **Teil 1** – Du selbst (Zugangsdaten), ~15 Min
- **Teil 2** – Ein Browser-Agent legt die 8 Suchen an
- **Teil 3** – Du selbst (Abschluss + Test), ~5 Min

---

## Teil 1: Was DU selbst machst (~15 Min)

Diese Schritte betreffen deine Konto-Sicherheit – die macht bitte **nur du selbst**, nicht der Browser-Agent.

### 1a) Gmail-App-Passwort erstellen

**Was ist ein App-Passwort und warum?**
Der Scraper muss sich an deinem Gmail-Konto anmelden, um dir Mails zu schicken. Er soll dafür aber **nicht dein echtes Passwort** kennen. Ein App-Passwort ist ein **16-stelliger Einmal-Code**, den Google speziell für ein Programm erzeugt. Vorteile:
- funktioniert nur für den Mailversand, nicht zum Einloggen in dein Konto
- du kannst es **jederzeit einzeln widerrufen**, ohne dein echtes Passwort zu ändern
- dein Hauptpasswort bleibt geheim

**Welches deiner Gmail-Konten?**
Da Versand und Empfang **dasselbe Konto** sind (der Scraper schickt „von dir an dich" – das ist bei automatischen Tools völlig normal), nimm am besten **das Postfach, in dem du die Angebote lesen willst**. Wichtig: dieses Konto braucht **2-Faktor-Authentisierung (2FA)** – ohne 2FA blendet Google die App-Passwort-Seite gar nicht ein.

**Schritte:**
1. Gehe zu [myaccount.google.com](https://myaccount.google.com) und melde dich mit dem gewünschten Konto an.
2. Links **Sicherheit** öffnen.
3. Falls **„Bestätigung in zwei Schritten" (2FA)** noch nicht aktiv ist → jetzt aktivieren (Handynummer o. Authenticator). Ohne diesen Schritt geht es nicht weiter.
4. Danach die Seite **App-Passwörter** öffnen: direkt [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) oder über die Suche im Konto nach „App-Passwörter".
5. Als App-Namen z. B. `Wohnungssuche` eingeben → **Erstellen**.
6. Google zeigt einen **16-Zeichen-Code** (in 4er-Gruppen, z. B. `abcd efgh ijkl mnop`). **Kopiere ihn** – er wird nur einmal angezeigt.

### 1b) Die Apprise-Benachrichtigungs-URL bauen

Aus deiner Adresse + dem App-Passwort baust du eine einzige URL nach diesem Muster:

```
mailto://DEINEADRESSE:APPPASSWORT@gmail.com?to=DEINEADRESSE@gmail.com
```

**Beispiel** (Konto `deine-adresse@example.com`, App-Passwort `DEIN_APP_PASSWORT`):

```
mailto://deine-adresse:DEIN_APP_PASSWORT@gmail.com?to=deine-adresse@example.com
```

Hinweise:
- Das **App-Passwort ohne Leerzeichen** einsetzen (die 4er-Gruppen zusammenschreiben).
- Nur den **Teil vor dem @** als Benutzernamen (also `deine-adresse`, nicht die volle Adresse) – die Domain `@gmail.com` steht separat dahinter.
- `to=` ist die Empfängeradresse (hier dasselbe Konto = volle Adresse).
- Falls dein App-Passwort ausnahmsweise ein Sonderzeichen enthielte, müsste es URL-codiert werden – bei den reinen Buchstaben-Codes von Google ist das aber nicht nötig.

### 1c) Die URL als GitHub-Secret hinterlegen

Damit landet das Passwort **verschlüsselt** bei GitHub und **nie im Code**:

1. Im Browser dein Repo `Berufung` auf GitHub öffnen.
2. **Settings** → links **Secrets and variables** → **Actions**.
3. Button **New repository secret**.
4. **Name:** `FLATHUNTER_APPRISE_URL` (exakt so schreiben).
5. **Secret:** die komplette `mailto://...`-URL aus Schritt 1b einfügen.
6. **Add secret**.

### 1d) Dem Workflow Schreibrechte geben

Der Scraper merkt sich schon gemeldete Wohnungen in einer kleinen Datei und schreibt sie ins Repo zurück – dafür braucht der Workflow Schreibrechte:

1. Repo → **Settings** → **Actions** → **General**.
2. Runter zu **Workflow permissions**.
3. **„Read and write permissions"** auswählen → **Save**.

### 1e) Immowelt: gespeicherte Suchen + E-Mail statt Scraping

**Warum:** Immowelt blockt automatisiertes Scraping inzwischen mit einem Bot-Schutz (DataDome, 403-Fehler) – auch mit den besten Absichten kommt man da nicht zuverlässig durch. Statt dagegen anzukämpfen, nutzen wir, was Immowelt **selbst und beabsichtigt** anbietet: gespeicherte Suchen mit E-Mail-Benachrichtigung. Das Skript liest diese Mails per IMAP vom selben Gmail-Konto (kein zusätzliches Secret nötig – die Zugangsdaten werden aus der bereits hinterlegten Apprise-URL extrahiert) und baut daraus Einträge für den gemeinsamen Digest.

**Schritte:**
1. **IMAP in Gmail aktivieren** (falls nicht schon an): Gmail → Zahnrad → **Alle Einstellungen ansehen** → Tab **„Weiterleitung und POP/IMAP"** → **„IMAP aktivieren"** → Speichern.
2. Auf **[immowelt.de](https://www.immowelt.de)** für jede der 4 Regionen (Rosenheim, Ammersee/Inning, Würzburg, Münchner Umland) eine Suche mit denselben Filtern wie in Teil 2 (1-Zimmer-Wohnung, 28–50 m², passendes Preisband) anlegen.
3. Bei jeder Suche die **E-Mail-Benachrichtigung aktivieren** (i. d. R. ein Glocken-/Speichern-Symbol bei den Suchergebnissen, „Suche speichern" + „Per E-Mail benachrichtigen"). Empfänger: **dasselbe Gmail-Konto**, das schon für den Versand genutzt wird.
4. Nichts weiter einzurichten – das Skript sucht bei jedem Lauf automatisch nach ungelesenen E-Mails von `immowelt.de`, parst sie und markiert sie danach als gelesen.

**Wichtig zu wissen:** Der Parser liest das aktuelle Immowelt-Mail-Layout aus (Links zu Objektseiten + Preis/Größe/Zimmer aus dem umgebenden Text). Ändert Immowelt das Layout, bleibt der Link zum Angebot meist trotzdem erhalten, auch wenn einzelne Felder dann "N/A" zeigen. Bei Bedarf lässt sich der Parser in `immowelt_mail_parser.py` gezielt nachjustieren, sobald eine echte Beispiel-Mail vorliegt.

✅ **Teil 1 fertig.** Jetzt die Suchen anlegen.

---

## Teil 2: Browser-Agent – die WG-Gesucht-Suchen anlegen

> **Stand:** Nur noch **WG-Gesucht** wird direkt gescraped (Immowelt läuft jetzt über E-Mail-Benachrichtigung, siehe Teil 1e – Immowelt selbst blockt automatisiertes Scraping mit einem Bot-Schutz).

Gib deinem Browser-Agenten (z. B. Claude in einem Browser-Tool) den folgenden Prompt. Er legt die gefilterten Suchen auf **wg-gesucht.de** an und liefert dir die URLs zurück, die du in Teil 3 einsetzt.

> **Kopiervorlage für den Browser-Agenten:**
>
> ---
>
> Du sollst mir auf **wg-gesucht.de** gefilterte Wohnungssuchen aufsetzen und die URLs der Ergebnisseiten sammeln. Ich suche eine **1-Zimmer-Wohnung** (eine echte Wohnung, **keine WG / kein WG-Zimmer**) in vier bayerischen Regionen (Region 2 hat zusätzlich eine Extra-Suche für Gilching).
>
> **So gehst du pro Region vor:**
> 1. Öffne wg-gesucht.de.
> 2. Wähle als Objekttyp **1-Zimmer-Wohnung** (**nicht** „WG").
> 3. Setze den **Ort** (siehe Tabelle) und einen **Umkreis von ca. 10–15 km**.
> 4. Setze **Wohnfläche: 28–50 m²**.
> 5. Setze die **Warmmiete** auf den in der Tabelle angegebenen Bereich.
> 6. Sortiere die Ergebnisse nach **„Neueste zuerst"**.
> 7. **Kopiere die URL aus der Adresszeile** der gefilterten, sortierten Ergebnisseite.
>
> **Die Regionen:**
>
> | # | Region | Hauptort (+ Umkreis deckt ab) | Warmmiete |
> |---|--------|-------------------------------|-----------|
> | 1 | Rosenheim | Rosenheim (deckt Aising, Happing, Pang, Stephanskirchen) | 500–900 € |
> | 2 | Ammersee / Inning | Inning am Ammersee (+ Weßling, Germering, Herrsching) | 550–950 € |
> | 2b | Gilching (Extra) | Gilching direkt | 550–950 € |
> | 3 | Unterfranken / Würzburg | Würzburg + Umland | 400–800 € |
> | 4 | Südl. Münchner Umland | München-Umkreis (deckt Hohenschäftlarn-Richtung) | 550–900 € |
>
> **Am Ende gib mir die 5 URLs als beschriftete Liste zurück.**
>
> ---

**Falls du keinen Browser-Agenten hast:** Du kannst die Suchen auch selbst in ~10 Minuten anlegen – dieselben Filter, dann jeweils die URL aus der Adresszeile kopieren.

---

## Teil 3: Was DU selbst zum Abschluss machst (~5 Min)

### 3a) Die URLs in die Config einsetzen ✅ Bereits erledigt

Die 5 WG-Gesucht-URLs (4 Regionen + zusätzliche Gilching-Suche im Ammersee/Inning-Cluster) sind bereits in `wohnungssuche/tool/config.yaml.template` eingetragen und als valides YAML geprüft. Die ursprünglich zusätzlich eingetragenen Immowelt-URLs wurden wieder entfernt, nachdem sich zeigte, dass Immowelt automatisiertes Scraping per Bot-Schutz (DataDome, 403) blockt – Immowelt läuft jetzt stattdessen über den E-Mail-Weg aus Teil 1e.

**Kleine Korrektur beim Eintragen:** Der globale Sicherheitsnetz-Filter `max_size` stand noch auf `48`, während die Portal-Suchen bis `50 m²` gehen – wurde auf `50` angepasst, damit 49–50 m²-Treffer nicht versehentlich nach dem Scrapen wieder rausgefiltert werden.

**Hinweis zu Region 4 (Münchner Umland):** Die URLs nutzen München als Ortsbasis (city_id=115) mit 15 km Umkreis, nicht Hohenschäftlarn direkt – das Preisband 550–900 € filtert Innenstadt-Preise aber ohnehin weitgehend heraus. Falls dir das zu münchen-zentrisch ist, kannst du die Ortsbasis später auf Hohenschäftlarn ändern.

**Zusammenfassung Digest-Verhalten:** Statt einer E-Mail pro Angebot (wie beim allerersten Testlauf mit 26 Einzelmails) sammelt `run_digest.py` jetzt alle neuen Angebote eines Laufs – von WG-Gesucht/Kleinanzeigen (direkt gescraped) UND von Immowelt (per E-Mail-Parsing) – und verschickt **eine** zusammengefasste E-Mail pro Lauf.

### 3b) Committen und pushen

Die Template-Datei ist versioniert und enthält **keine** Secrets (das Passwort liegt ja im GitHub-Secret). Also gefahrlos:
```bash
git add wohnungssuche/tool/config.yaml.template
git commit -m "config: Wohnungssuche-URLs eingetragen"
git push
```

### 3c) Ersten Testlauf starten

1. Repo auf GitHub → Reiter **Actions**.
2. Links **„Wohnungssuche Scraper"** wählen.
3. **Run workflow** → **Run workflow** (manuell auslösen).
4. Lauf öffnen und die Logs beobachten – bei Erfolg wird gescraped und ggf. eine Mail verschickt.

### 3d) Test-E-Mail prüfen

- Schau in dein Gmail-Postfach (**auch Spam-Ordner** prüfen – die erste automatische Mail landet dort gern).
- **Tipp zum Erzwingen eines Treffers:** Falls gerade nichts Neues gelistet ist, kannst du in `config.yaml.template` testweise `max_price` kurz hochsetzen (z. B. auf `2000`) und die Größenfilter weiten, damit garantiert etwas gefunden wird. Danach die Testwerte wieder zurücksetzen und erneut committen.

✅ **Fertig!** Ab jetzt läuft der Scraper **automatisch stündlich** (7 Min. nach der vollen Stunde). Du bekommst nur **neue** Angebote – dank der `processed_ids.db` keine Doppel-Mails.

---

## Sicherheits-Hinweise

- Das **App-Passwort** und die **Apprise-URL** gehören **ausschließlich** ins GitHub-Secret – niemals in eine Datei committen, die im Repo landet.
- Die zur Laufzeit erzeugte echte `config.yaml` (mit eingesetztem Passwort) ist bereits über `.gitignore` vom Repo ausgeschlossen.
- App-Passwort verloren oder kompromittiert? Einfach unter [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) widerrufen, ein neues erstellen und das GitHub-Secret aktualisieren.

## Bei Problemen

Siehe den Abschnitt **„Fehlerbehandlung"** in `README.md` (keine Mails? Workflow schlägt fehl? Dedupe-DB zurücksetzen?).
