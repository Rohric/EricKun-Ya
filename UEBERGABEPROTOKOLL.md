# Übergabeprotokoll – EricKun-Ya Verkaufstool

> **Zweck:** Vollständige Übergabe an ein neues Kontextfenster. Wer das liest, kann ohne
> Kenntnis der bisherigen Sitzung weiterarbeiten.
> **Stand:** 2026-10-05 · Branch `main` · HEAD `90df3e7` · Arbeitsverzeichnis sauber.
> Enthält **keine Secrets** (die stehen nur in `backend/.env`, git-ignoriert).
>
> **Einstieg im neuen Fenster:** „Lies `UEBERGABEPROTOKOLL.md` und mach mit dem nächsten
> Schritt weiter." Details zu jeder App stehen in deren `README.md`.

---

## 1. Projekt in Kürze

Emil baut für seinen Kollegen **Eric** ein Tool für den eBay-Verkauf – gleichzeitig
Portfolio-Projekt. Eric pflegt Artikel, Bestellungen und Finanzen und soll Artikel später
per Knopfdruck auf eBay inserieren.

- **Stack:** Python 3.14, Django 6.1.1, DRF 3.18.1, simplejwt, SQLite, Pillow, requests,
  cryptography. Windows, PowerShell, venv unter `backend/venv`.
- **Frontend:** Vanilla HTML/CSS/JS als Übergang; Emil baut es später in **Angular** neu.
- **Ziel-Auslieferung:** eine **Desktop-App für Mac**, lokal auf Erics Rechner. Deshalb
  SQLite und ein konfigurierbarer Datenordner (`DATA_DIR`), den die App beim ersten Start
  abfragen soll. Das Packaging ist noch nicht begonnen.

## 2. Zusammenarbeit (verbindlich)

- **Sprache:** mit Emil Deutsch. Code, Kommentare, Docstrings, Commit-Messages Englisch;
  sichtbare UI-Texte und API-Fehlermeldungen Deutsch.
- **Code-Stil:** Skill `emil-code-style` laden. Kernpunkte: Apps enden auf `_app`,
  Settings-Modul `core`; je App `api/` mit `views.py`, `serializers.py`, `urls.py`,
  `permissions.py`; Logik in `services.py`/`utils.py`, Side-Effects in `signals.py`;
  Python-Funktionen max. 14 Zeilen, Early Returns, DRY; generic views für CRUD, `APIView`
  nur für Sonderlogik; `permission_classes` explizit; benannte URLs; `TextChoices`;
  **kein try/except in Views** (zentraler `EXCEPTION_HANDLER`); doppelte Anführungszeichen.
- **Arbeitsmodus in diesem Projekt:** Emil hat „mach das" gesagt – Dateien werden **komplett
  ausgeschrieben**, nicht nur Schnipsel.
- **Nie selbst committen.** Commit-Messages vorschlagen; Emil committet.
- **Große Blöcke im Plan-Modus:** erst die echten Designentscheidungen per Rückfrage klären,
  Plan schreiben, freigeben lassen, dann bauen und selbst testen.
- **Tempo:** zügig handeln, nicht lange grübeln. Emil mag kurze, klare Antworten.
- **Befehle** copy-paste-fertig für PowerShell, immer über die **venv** (das globale Python
  hat kein Pillow → `runserver` scheitert dort).
- **Secrets nie im Chat.** Emil trägt sie selbst in `backend/.env` ein.
- **Frontend:** bewusst **keine Media Queries**, nur Laptop-Ansicht.
- **READMEs:** jede App hat eine, alle im selben Schema (Aufgaben · Models ·
  Services/Logik · API-Endpoints · Verbindungen · Dateien). Bei Änderungen mitpflegen.

## 3. Architektur-Leitprinzipien

1. **Eigene DB ist die Source of Truth**, eBay ist nur ein Ausgabekanal.
2. **Adapter-Pattern, einseitige Abhängigkeit:** `ebay_app` kennt `products_app`,
   `orders_app`, `logistics_app` – nie umgekehrt.
3. **Nur speichern, was nicht ableitbar ist** (Gewinn, Fortschritt, Summen sind Properties
   oder Services).
4. **Eine App nur bei eigenem Model.**
5. **Finanzen sind Orientierung, keine Buchhaltung** (GoBD).
6. **Erst Sandbox, dann Production.**

## 4. Stand der Apps (alles committet)

| App | Stand | Inhalt |
|---|---|---|
| `core` | fertig | Settings über `.env`, `DATA_DIR` (DB + `media/`), JWT, CORS, `EBAY_*`; Routing; zentraler Exception-Handler (`{"error": …}`); `OptionalPagePagination` (paginiert nur mit `?page=`); liefert im DEBUG Frontend und Medien aus |
| `auth_app` | fertig | Custom `User` (Login per E-Mail), Registrierung, Login/Refresh/Logout per JWT (Blacklist) |
| `products_app` | fertig | `Category` (Baum), `Product` (Auto-SKU, Status verfügbar/reserviert/verkauft/archiviert, Kategorie, Preise, Menge, Aspekte), `ProductImage` (Ordner je SKU, Aufräum-Signals); Liste mit `?view=active\|archive\|all` |
| `orders_app` | fertig | `Order` (Käufer- und Lieferdaten, Status inkl. „In Reklamation"/„Storniert", `return_note`), `OrderItem` (`product` mit `SET_NULL`); automatische Bestandsführung, Bestandsprüfung, Storno-Endpoint mit Artikel-Aktion; alles transaktional |
| `finance_app` | fertig | `Goal`, `FinanceSettings` (Rücklagensatz); Steuerrechnung Brutto = Rücklage + Netto, Monatsumsatz, Einkauf; stornierte Bestellungen zählen nicht mit |
| `logistics_app` | fertig (Stufe 1) | `Warehouse` – ein Standard-Lagerort; später Lagerplätze, Einlagern, Finden |
| `ebay_app` | **A–E gebaut (D + E uncommittet), echter Sandbox-Lauf offen** | siehe Abschnitt 6 |

**Wichtige Detail-Entscheidungen:**
- Archiv = Artikel mit Status `sold` oder `archived`. Menge 0 durch Verkauf → `sold`;
  Rückbuchung → wieder `available`.
- Positionen einer Bestellung sind im Frontend nach dem Anlegen fest (Änderung = Storno +
  neu anlegen). Das Backend kann Positionen ersetzen und bucht dann korrekt um.
- Kundendaten werden vorerst manuell erfasst; der spätere eBay-Sync füllt dieselben Felder.
- `Goal.period` ist nur beschreibend; der Fortschritt rechnet von `start_date` bis
  `end_date` (oder heute).
- Ungültige Query-Parameter liefern 400 mit deutscher Meldung.

## 5. Frontend

Sieben Seiten unter `frontend/`: `index` (Login), `dashboard`, `products`, `orders`,
`warehouse` (Lager), `finances`, `ebay`. Gemeinsame Module: `config.js` (`API_BASE_URL = "/api"`,
`PAGE_SIZE = 25`), `api.js` (fetch mit JWT und automatischem Refresh, `apiUpload` für
Bilder), `auth.js`, `ui.js` (Navigation, `showMessage`, `errorText`, `escapeHtml`,
`formatEuro`, `inputValue`, `markActive`, `renderTiles`, `renderGoalCard`, `renderPager`,
`periodRange`, `isoDate`). Branding überall „EricKun-Ya". Details: `frontend/README.md`.

## 6. eBay – Stand und nächste Schritte

### Gebaut (A: Verbindung, B: Einrichtung)
- `EbayAccount` (Singleton): Tokens **Fernet-verschlüsselt**, OAuth-`state`, drei Policy-IDs.
  `EbayLocation`: OneToOne zu `Warehouse`, `merchant_location_key`.
- `client.py` (URLs je Umgebung, Scopes, Fehler → `EbayApiError`), `crypto.py`,
  `exceptions.py` (502 / 409 / 503).
- `services/oauth.py` (Consent-URL, eingefügte Rücksprung-URL prüfen, Code tauschen,
  automatische Erneuerung, `call()`), `services/account.py` (Opt-in, Versanddienste,
  Policies anlegen/aktualisieren), `services/locations.py`, `services/overview.py`.
- Endpoints: `ebay/status/`, `ebay/connect/start/`, `ebay/connect/finish/`,
  `ebay/disconnect/`, `ebay/shipping-services/`, `ebay/policies/`, `ebay/location/sync/`.

### Fakten
- eBay akzeptiert als Rücksprung nur **HTTPS über einen RuName, kein `localhost`**. Deshalb
  kopiert der Nutzer nach dem eBay-Login die Adresse aus der Browserleiste in die App.
- Access-Token 2 Stunden, Refresh-Token 18 Monate.
- `.env` hat alle sechs Werte gesetzt: `EBAY_ENV=sandbox`, `EBAY_CLIENT_ID`,
  `EBAY_CLIENT_SECRET`, `EBAY_RUNAME`, `EBAY_MARKETPLACE_ID=EBAY_DE`, `EBAY_TOKEN_KEY`.
- Entscheidungen: Policies über ein Formular in der App; Rückgabe-Standard 30 Tage, Käufer
  zahlt; Zahlung = Sofortzahlung.

### Was geprüft ist – und was nicht
- **Geprüft:** Die Sandbox-Keys sind gültig (eBay hat ein App-Token ausgestellt). Der
  Verbindungsablauf lief mit **simulierten** eBay-Antworten durch (Consent-URL, Code,
  Verschlüsselung, Erneuerung, Fehlerfälle). Beide Reiter rendern.
- **Nicht geprüft:** der echte Login sowie die echten Aufrufe für Opt-in, Versanddienste,
  Policies und Lagerort. Die Payloads stammen aus der Doku-Recherche und können beim ersten
  echten Lauf Korrekturen brauchen.
- **Datenbank am 2026-10-05:** nicht verbunden, keine Policies, kein Lagerort.

### Offener Test (macht Emil, Server vorher neu starten)
1. Reiter „Lager": Lagerort eintragen.
2. Reiter „eBay" → „Mit eBay verbinden" → mit dem **Sandbox-Testuser** einloggen → Adresse
   aus der Browserleiste einfügen → „Verbindung abschließen".
3. Versanddienst und Versandkosten wählen → „Bei eBay speichern".
4. „An eBay übertragen".
5. Checkliste komplett grün → „Bereit zum Inserieren".

Bekanntes Sandbox-Problem: Das Opt-in zu Business Policies schlägt manchmal fehl; Umweg
über eBays API Explorer.

### Nachtrag 2026-10-05 (zweite Sitzung) – C, D und E gebaut

Freigegebener Plan: `C:\Users\emilm\.claude\plans\erstelle-einen-plan-und-shimmying-puffin.md`.
C ist committet (`ed40456`); D, E, die Kategorie-Merkliste und Korrekturen an C sind noch
uncommittet.

- **Entscheidungen:** eBay-Kategorie und Pflicht-Merkmale werden beim Inserieren gewählt ·
  Sync manuell per Button, nur Bestand 0 / archiviert beendet das Inserat automatisch ·
  Verkäufe per Button und automatisch beim Öffnen abholen · Versand an eBay melden ·
  eBay-Stornos übernehmen · eigenes Model `Cancellation` in `orders_app` · eBays
  Kategoriebaum wird **nicht** gespiegelt, stattdessen merkt sich `EbayCategoryMapping` die
  zuletzt gewählte eBay-Kategorie je interner Kategorie.
- **C – Inserieren:** Models `EbayListing`, `EbayImage`, `EbayCategoryMapping`, Feld
  `EbayAccount.orders_synced_at`; Services `taxonomy`, `conditions`, `images`, `listings`;
  `signals.py`.
- **D – Verkäufe:** `orders_app` hat `Order.ebay_order_id`, `Order.shipping_carrier`,
  `OrderItem.ebay_line_item_id` und das Model `Cancellation`; `ebay_app/services/orders.py`
  importiert Bestellungen, übernimmt eBay-Stornos und meldet den Versand.
- **E – Frontend:** Karte „4. Inserate" im eBay-Reiter mit Inserieren-Dialog
  (`js/ebay-listings.js`); Bestellseite mit „eBay-Verkäufe abholen", „Versand melden" und
  Storno-Grund; automatischer Abruf über `js/ebay-orders.js` (Dashboard + Bestellungen).
- **Migrationen (angewendet):** `ebay_app` `0002_listings_and_images`, `0003_category_mapping`;
  `orders_app` `0006_ebay_fields_and_cancellation`. Alle Endpoints stehen in den App-READMEs.
- **Echt gegen die Sandbox geprüft (App-Token):** Kategorie-Vorschläge, Merkmale, erlaubte
  Zustände, Versanddienste. Erkenntnisse: Viele Kategorien erlauben nur die Zustände
  1000 / 1500 / 3000 / 7000 – deshalb weicht das Mapping auf „Gebraucht" aus. eBay liefert
  Versanddienste mehrfach je Code – wird jetzt dedupliziert.
- **Nur mit nachgestellten eBay-Antworten geprüft:** Inserieren, Ändern, Synchronisieren,
  Ausverkauf, Beenden, Bestell-Import (neu, doppelt, unbekannte SKU, unbezahlt, storniert),
  Versandmeldung, Storno mit Grund – per API-Skript und einmal im Browser gegen eine Kopie
  der Daten.
- **Noch nie echt gelaufen:** jeder Aufruf im Namen des Verkäufers – Opt-in, Policies,
  Lagerort, Bild-Upload (Media API, Host `apim.sandbox.ebay.com`, unbestätigt), Inventory Item,
  Offer, Publish, `getOrders`, `createShippingFulfillment`. Braucht Emils einmaligen eBay-Login
  in der App; danach kann die Assistenz alle eBay-Endpoints über die Django-Shell aufrufen
  (`ebay_app.services.oauth.call`).
- **Nicht enthalten:** Storno/Erstattung an eBay senden, echte eBay-Gebühren (Finances API),
  Käufernachrichten.
- **Daten:** Standard-Lagerort „Lager", Teststraße 1, 66333 Völklingen wurde als Testadresse
  angelegt. Das Bild `test.png` des Artikels „Vintage Kamera" ist ein **Platzhalter**: das
  Original wurde bei einem Testlauf der Assistenz gelöscht (Lösch-Signal entfernt Dateien,
  der DB-Rollback stellt sie nicht wieder her).
- **Arbeitsteilung beim Testen:** Emil testet das Frontend selbst, die Assistenz macht API-Tests.
- **Postman** (Workspace `Erik-Kun_Ya`): Environment `EricKun-Ya – Sandbox`, Collections
  `eBay Sandbox (direkt)` und `EricKun-Ya API (Django)` (inkl. Ordner „eBay – Inserate" und
  „eBay – Verkäufe").

### Nachtrag 2026-10-06 – erster echter Sandbox-Lauf

- **Echt bestätigt:** Verbinden, drei Vorlagen, Lagerort, Bild-Upload (Media API funktioniert),
  Inventory Item, Offer, Publish, Sync (Menge, Kategorie-Wechsel), Löschen eines Artikels bei eBay.
- **Stolperstein `.env`:** `EBAY_RUNAME` muss der von eBay erzeugte RuName sein (Developer-Portal →
  Sandbox-Keyset → „User Tokens"), nicht der Anzeigename. Ein falscher Wert endet beim Login mit
  `invalid_request`.
- **Sandbox-Kasse legt keine Bestellungen an:** mehrere Käufe als Buyer zeigten „Vielen Dank",
  eBay führt aber weder Bestellung noch verkaufte Menge. eBay meldet für den Seller-Testuser
  `sellerRegistrationCompleted: false` und zeigt Käufern den Preis mit 19 % Aufschlag
  (85,00 € → 101,15 €). Vermutung: unvollständige Verkäufer-Registrierung des Testusers. Beim
  Go-Live an einem echten Inserat prüfen, dass der Preis dem eingestellten entspricht.
- **Deshalb neu:** Befehl `python manage.py simulate_ebay_sale <SKU>` (siehe
  `backend/ebay_app/README.md`). Verkäufe abholen, eBay-Storno und Versandmeldung sind weiterhin
  **nie** mit einer echten eBay-Bestellung gelaufen.
- **Daten:** Testdaten vom 26.09. wurden gelöscht. Aktuell 5 Artikel („Emils Test Spiel" nicht
  inseriert; „Emils Test Kamera" und drei Kunstdrucke online, je Restmenge 1) und 3 simulierte
  eBay-Bestellungen (`SIM-…`). Sicherungen: `backend/data/db-backup-2026-10-06*.sqlite3`.
- **Offene Ideen:** mehrere Versandprofile statt einer Vorlage für alle Artikel; Spalte
  „Preis bei eBay" im eBay-Reiter; Hilfetexte zum Ablauf im Frontend.

### Danach
- **Echter Sandbox-Durchlauf:** verbinden → Policies → Lagerort → inserieren → als Buyer
  kaufen → Verkäufe abholen → Versand melden; dabei abgelehnte Payloads korrigieren.
- Später: Production-Keyset (inkl. Pflicht-Entscheidung zu „Marketplace Account Deletion"),
  Storno an eBay, Finances API, Desktop-Packaging, Angular.

## 7. Starten

Aus `backend/`:

```
.\venv\Scripts\Activate.ps1
python manage.py runserver
```

- Frontend: `http://127.0.0.1:8000/` · Admin: `http://127.0.0.1:8000/admin/`
- Nach Änderungen an JS/CSS im Browser **Strg+Shift+R**.
- Daten liegen in `backend/data/` (DB + `media/`), git-ignoriert. Aktuell 1 Artikel,
  1 Kategorie, 1 Bestellung, 2 Ziele.
- Logins: Emils eigener Superuser und der Testnutzer `eric@test.de`.
- Für eigene Browser-Tests einen zweiten Server auf Port 8010 starten
  (`runserver 127.0.0.1:8010 --noreload`), damit Emils Server auf 8000 ungestört bleibt.

## 8. Offene Punkte

- **Keine automatisierten Tests** – alle `tests.py` sind leer. Bisherige Prüfungen liefen
  als Wegwerf-Skripte außerhalb des Repos.
- Zwei alte `.pyc`-Dateien sind noch getrackt:
  `git rm -r --cached backend/core/__pycache__`.
- Die Sandbox-Cert-ID war einmal in einem Screenshot im Chat sichtbar. Unkritisch für die
  Sandbox; optional im Portal rotieren und in der `.env` ersetzen.
- Desktop-Packaging: Datenordner-Abfrage beim ersten Start und Umgang mit dem
  Client-Secret in einer ausgelieferten App sind ungeklärt.
- GoBD: Finanzzahlen bleiben Schätzung; nichts bauen, was Buchhaltung vortäuscht.
- Rückgaberegeln: für gewerbliche Verkäufer gilt mindestens das 14-tägige Widerrufsrecht –
  im Zweifel fachlich klären lassen.

## 9. Git

- Branch `main`, alles committet, HEAD `90df3e7` („Implement eBay integration …").
- Commit-Vorschläge im Format `feat(app): …`, `fix: …`, `docs: …`; optional mit
  `Co-Authored-By`-Zeile.
