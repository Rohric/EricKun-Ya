# EricKun-Ya

Verkaufstool für kleine Händler: Artikel, Lager, Bestellungen und Finanzen liegen in einer eigenen
Datenbank – eBay (später weitere Portale) ist nur ein Ausgabekanal. Artikel werden im Programm
gepflegt, auf Knopfdruck inseriert, Verkäufe kommen als Bestellungen zurück. Bis auf die
Kommunikation mit Käufern läuft alles über das Programm.

> **Stand:** läuft gegen die **eBay-Sandbox**. Für den Live-Betrieb fehlt noch ein Baustein
> (siehe [Live-Schaltung](#live-schaltung)).

## Inhalt

1. [Funktionen](#funktionen)
2. [Technik](#technik)
3. [Aufbau](#aufbau)
4. [Regeln für Verkaufskanäle](#regeln-für-verkaufskanäle)
5. [Installation](#installation)
6. [Einstellungen (`.env`)](#einstellungen-env)
7. [Erste Schritte](#erste-schritte)
8. [eBay-Sandbox einrichten](#ebay-sandbox-einrichten)
9. [Verkauf simulieren](#verkauf-simulieren)
10. [Live-Schaltung](#live-schaltung)
11. [API-Überblick](#api-überblick)
12. [Projektstruktur](#projektstruktur)
13. [Bekannte Grenzen](#bekannte-grenzen)

## Funktionen

- **Artikel** mit Kategorien, Zustand, Preisen, Bestand, Bildern und eigener Artikelnummer (`EK-000123`)
- **Bestellungen** mit Positionen, Lieferadresse, Zahlungs- und Versandstatus; der Bestand wird
  automatisch gebucht, Stornos buchen zurück
- **eBay:** verbinden, Versandprofile und Vorlagen pflegen, inserieren (Kategorie-Vorschläge,
  Pflicht-Merkmale, Bild-Upload, Gebühren-Vorschau), synchronisieren, beenden, Verkäufe abholen,
  Versand melden
- **Zuordnung:** Inserate, die schon bei eBay stehen, werden abgeglichen und entweder mit einem
  vorhandenen Artikel verknüpft oder als neuer Artikel übernommen
- **Finanzen:** Umsatz, Einkauf, geschätzte Gebühren, Steuerrücklage, Ziele, Auswertung je Verkauf,
  Kanal und Kategorie
- **Dashboard** mit den wichtigsten Kennzahlen

## Technik

| Bereich | Eingesetzt |
|---|---|
| Backend | Python 3.14, Django 6.1, Django REST Framework 3.18, SimpleJWT |
| Datenbank | SQLite (Standard), PostgreSQL optional |
| eBay | REST-APIs (Inventory, Account, Fulfillment, Taxonomy, Metadata, Media, Browse) und die XML-Trading-API für Inserate, die nicht über die API angelegt wurden |
| Frontend | HTML, CSS, JavaScript ohne Framework (wird später in Angular neu gebaut) |

## Aufbau

```
auth_app       Login, Registrierung, Nutzer
products_app   Artikel, Kategorien, Bilder, Artikelnummern      ← Kern, kennt kein Portal
orders_app     Bestellungen, Bestand, Storno
finance_app    Auswertungen, Ziele, Steuerrücklage
logistics_app  Lagerort
ebay_app       Verbindung zu eBay, Inserate, Zuordnung, Verkäufe
core           Einstellungen, Routing, gemeinsame Bausteine
```

**Abhängigkeitsrichtung:** `ebay_app` kennt `products_app`, `orders_app` und `logistics_app` –
nie umgekehrt. Der Kern weiß nichts von eBay. Das Frontend führt die Daten zusammen (z. B. die
Spalte „Kanäle" der Artikelliste aus `/api/ebay/listing-states/`).

Jede App hat eine eigene README mit Models, Logik und **vollständiger API-Dokumentation**:
[auth_app](backend/auth_app/README.md) · [products_app](backend/products_app/README.md) ·
[orders_app](backend/orders_app/README.md) · [finance_app](backend/finance_app/README.md) ·
[logistics_app](backend/logistics_app/README.md) · [ebay_app](backend/ebay_app/README.md) ·
[core](backend/core/README.md) · [frontend](frontend/README.md)

## Regeln für Verkaufskanäle

Diese Regeln gelten für eBay und für jedes Portal, das später dazukommt.

1. **Ein Artikel ist ein Lagerbestand.** Portale sind Ausgabekanäle.
2. **Je Portal höchstens ein Inserat pro Artikel;** ein Inserat gehört zu höchstens einem Artikel.
3. **Ein Abgleich legt nie von selbst Dubletten an.** Automatisch verknüpft wird nur bei exakt
   gleicher Artikelnummer. Alles andere landet in der Ansicht „Zuordnung".
4. **Die interne Artikelnummer führt.** Inserate, die das Programm anlegt oder umwandelt, tragen
   sie. Nur wo ein Portal die Nummer eines bestehenden Eintrags nicht ändern lässt, bleibt die
   fremde Nummer am Inserat gespeichert.
5. **Nach dem Verknüpfen gilt der Artikel.** Abweichungen (Preis, Menge, Daten) werden als
   „Geändert" angezeigt und per „Synchronisieren" zum Portal übertragen.
6. **Ein Verkauf bucht den gemeinsamen Bestand.** Bei Bestand 0 enden die Inserate auf allen Portalen.
7. **Jedes Portal ist eine eigene App,** die Artikel und Bestellungen kennt – nie umgekehrt. Sie
   liefert ihre Inserate im selben Format; das Frontend führt die Portale zusammen.

**Artikelnummern**

| Nummer | Wer vergibt sie | Beispiel |
|---|---|---|
| Interne Artikelnummer | das Programm, fortlaufend, nie zweimal | `EK-000123` |
| Nummer beim Portal (SKU) | wir, wenn wir inserieren – sonst der bisherige Verkäufer | `EK-000123` oder `VASE-ALT` |
| Inseratsnummer | das Portal | `110591031053` |

Das Kürzel (`EK`) steht in der `.env` (`SKU_PREFIX`). Artikel, die vor der Umstellung angelegt
wurden, behalten ihre `ART-…`-Nummer. Lücken in der Nummernfolge sind normal (gelöschte Artikel,
abgelehnte Übernahmen) – eine vergebene Nummer wird nie wiederverwendet.

**Ein weiteres Portal andocken:** eigene App nach dem Vorbild der `ebay_app`, dieselben Endpoints
unter eigenem Pfad (`/api/<portal>/unassigned/…`, `/api/<portal>/listing-states/`), ein Eintrag in
`CHANNELS` in `frontend/js/channels.js`. Am Kern ändert sich nichts.

## Installation

**Voraussetzungen:** Python 3.12 oder neuer (entwickelt mit 3.14), Git. Ein eBay-Entwicklerkonto
braucht nur, wer eBay anbinden will – Artikel, Bestellungen und Finanzen laufen auch ohne.

### Windows (PowerShell)

```powershell
git clone https://github.com/Rohric/EricKun-Ya.git
cd EricKun-Ya\backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

### macOS / Linux

```bash
git clone https://github.com/Rohric/EricKun-Ya.git
cd EricKun-Ya/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### Danach auf allen Systemen (aus `backend/`, venv aktiv)

1. **Schlüssel erzeugen** und in die `.env` eintragen:

   ```bash
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```

   → `SECRET_KEY`

   ```bash
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```

   → `EBAY_TOKEN_KEY` (verschlüsselt die gespeicherten eBay-Tokens; nur nötig für eBay)

2. **Datenbank anlegen:**

   ```bash
   python manage.py migrate
   ```

3. **Admin-Zugang anlegen** (für `/admin/`, optional):

   ```bash
   python manage.py createsuperuser
   ```

4. **Starten:**

   ```bash
   python manage.py runserver
   ```

5. Im Browser `http://127.0.0.1:8000/` öffnen, **registrieren** und anmelden. Django liefert das
   Frontend im Entwicklungsbetrieb gleich mit aus – ein zweiter Server ist nicht nötig.

Die Datenbank und alle hochgeladenen Bilder liegen in `backend/data/` (über `DATA_DIR` änderbar).
Dieser Ordner und die `.env` werden nicht ins Git übernommen.

## Einstellungen (`.env`)

| Variable | Bedeutung | Standard |
|---|---|---|
| `SECRET_KEY` | Django-Schlüssel, selbst erzeugen | unsicherer Entwicklungswert |
| `DEBUG` | Entwicklungsbetrieb; liefert auch Frontend und Bilder aus | `True` |
| `ALLOWED_HOSTS` | erlaubte Hostnamen, mit Komma getrennt | `localhost,127.0.0.1` |
| `CORS_ALLOWED_ORIGINS` | nur nötig, wenn das Frontend von einem anderen Server kommt | lokale Entwicklungsadressen |
| `TAX_RESERVE_RATE` | Startwert der Steuerrücklage in Prozent | `25` |
| `SKU_PREFIX` | Kürzel der internen Artikelnummer | `EK` |
| `DATA_DIR` | Ordner für Datenbank und Bilder | `backend/data` |
| `DB_ENGINE`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | PostgreSQL statt SQLite (`DB_ENGINE=postgres`) | SQLite |
| `EBAY_ENV` | `sandbox` oder `production` | `sandbox` |
| `EBAY_CLIENT_ID` | App ID des eBay-Schlüsselsatzes | – |
| `EBAY_CLIENT_SECRET` | Cert ID des eBay-Schlüsselsatzes | – |
| `EBAY_RUNAME` | der von eBay erzeugte RuName (nicht der Anzeigename) | – |
| `EBAY_MARKETPLACE_ID` | Marktplatz | `EBAY_DE` |
| `EBAY_TOKEN_KEY` | Fernet-Schlüssel für die gespeicherten eBay-Tokens | – |

Zugangsdaten gehören ausschließlich in die `.env`, nie in den Code und nie ins Git.

## Erste Schritte

Zuerst unter **Artikel → Lager** den Lagerort anlegen (die Adresse, von der verschickt wird).
Danach gibt es zwei Startwege – beide lassen sich mischen.

### Weg A: Es gibt schon Inserate bei eBay (leere Datenbank)

1. **eBay → Übersicht:** „Mit eBay verbinden" (siehe [Sandbox einrichten](#ebay-sandbox-einrichten)).
2. **Artikel → Zuordnung:** „Mit eBay abgleichen". Alle laufenden Inserate erscheinen in der Liste.
3. „Alle als neue Artikel anlegen" – jedes Inserat wird ein Artikel mit eigener Nummer; Titel,
   Beschreibung, Merkmale, Zustand, Preis, Menge und Bilder kommen von eBay. Versand-, Rückgabe-
   und Zahlungsvorlage der Inserate werden übernommen.
4. **Artikel:** Einkaufspreise nachtragen (stehen auf 0 und sind mit „nachtragen" markiert).
5. **eBay → Vorlagen:** Lagerort übertragen. Ab jetzt ist die Checkliste vollständig.

### Weg B: Erst eigene Artikel, eBay später

1. **Artikel:** Kategorien und Artikel anlegen, Bilder hochladen.
2. **eBay → Übersicht:** verbinden. **eBay → Vorlagen:** Versandprofil, Rückgabe/Zahlung, Lagerort.
3. **eBay → Neu inserieren:** Artikel auswählen, Kategorie und Merkmale bestätigen, inserieren.
4. Stehen dieselben Artikel schon bei eBay: **Artikel → Zuordnung**, abgleichen und je Inserat
   „Verknüpfen" wählen (ein ähnlicher Titel wird vorgeschlagen). Weicht der Preis ab, steht das
   Inserat danach auf „Geändert" – der Artikel gilt.

### Alltag

- Artikel ändern → Inserat steht auf „Geändert" → **eBay → Inserate → Synchronisieren**
- Verkäufe kommen automatisch beim Öffnen des Dashboards oder per „eBay-Verkäufe abholen"
- Verschickt: **Versand melden** (Dienstleister und Trackingnummer gehen an eBay)
- Ausverkauft oder archiviert → das Inserat endet von selbst

**Wichtig bei übernommenen Inseraten:** Ein Inserat, das nicht über die API angelegt wurde, wird
beim Zuordnen von eBay umgewandelt. Danach lässt es sich **nur noch über dieses Programm** ändern,
nicht mehr auf der eBay-Seite. eBay verlangt dafür: Festpreis (keine Auktion, keine Varianten) und
Versand-, Rückgabe- und Zahlungsvorlage („Geschäftsbedingungen") am Inserat. Lehnt eBay ab, bleibt
das Inserat unverändert und zeigt den Grund.

## eBay-Sandbox einrichten

1. Auf [developer.ebay.com](https://developer.ebay.com) anmelden, unter **Application Keysets**
   einen **Sandbox**-Schlüsselsatz anlegen.
2. Unter **User Tokens → Get a Token from eBay via Your Application** einen RuName anlegen
   (Typ OAuth). In der `.env` steht der erzeugte RuName, z. B. `Vorname_Nachname-AppName-…`.
3. Unter **Sandbox → Test Users** einen Verkäufer und einen Käufer anlegen.
4. `EBAY_CLIENT_ID`, `EBAY_CLIENT_SECRET`, `EBAY_RUNAME`, `EBAY_TOKEN_KEY` in die `.env`, Server neu starten.
5. Im Programm **eBay → Übersicht → Mit eBay verbinden.** Mit dem Sandbox-**Verkäufer** anmelden
   und zustimmen. eBay leitet auf eine Seite weiter – die **komplette Adresse** aus der
   Browserleiste kopieren, im Programm einfügen und „Verbindung abschließen".
   (eBay akzeptiert als Rücksprung nur HTTPS und kein `localhost`, deshalb dieser Umweg.)
6. **eBay → Vorlagen:** Versandprofil anlegen, Rückgabe/Zahlung speichern, Lagerort übertragen.

Eigenheiten der Sandbox: Kategorien kennen oft nur wenige Zustände, der Käuferpreis wird mit
Aufschlag angezeigt, die Gebühren-Vorschau liefert 0, und die Kasse legt meist keine Bestellung an.

## Verkauf simulieren

Weil die Sandbox-Kasse keine Bestellungen anlegt, gibt es einen Befehl, der einen Verkauf so
einspielt, wie eBay ihn melden würde. Er läuft durch denselben Code wie der echte Abruf und
funktioniert **nur in der Sandbox**.

```bash
python manage.py simulate_ebay_sale EK-000001
```

```bash
python manage.py simulate_ebay_sale EK-000001 --quantity 2 --unpaid
```

```bash
python manage.py simulate_ebay_sale --pay 12
```

```bash
python manage.py simulate_ebay_sale --cancel 12
```

`--pay` und `--cancel` erwarten die Bestell-ID aus dem Programm. Mehr dazu in der
[ebay_app](backend/ebay_app/README.md#anwendung).

## Live-Schaltung

Checkliste für den Wechsel von der Sandbox auf das echte eBay-Konto.

- [ ] **Production-Schlüsselsatz** bei eBay anlegen. eBay schaltet ihn erst frei, wenn die App
      Benachrichtigungen über **gelöschte Konten** entgegennimmt (Marketplace Account Deletion) –
      dafür braucht es eine öffentlich erreichbare HTTPS-Adresse. **Dieser Endpunkt ist noch nicht
      gebaut.**
- [ ] Eigenen **RuName** für Production anlegen.
- [ ] `.env`: `EBAY_ENV=production`, die drei Production-Werte, ein **neuer** `EBAY_TOKEN_KEY`,
      ein eigener `SECRET_KEY`.
- [ ] `DATA_DIR` auf einen **eigenen, leeren Ordner** setzen, `python manage.py migrate` ausführen.
      Sandbox- und echte Daten dürfen nie in derselben Datenbank liegen.
- [ ] Registrieren, Lagerort anlegen, mit dem **echten** Verkäuferkonto verbinden.
- [ ] **Artikel → Zuordnung:** abgleichen und den Altbestand zuordnen (siehe Weg A).
      Vorher eine Sicherung des Datenordners anlegen.
- [ ] Vorlagen prüfen: Versandprofile, Rückgabe, Zahlung, Lagerort.
- [ ] Geschätzten eBay-Gebührensatz unter **Finanzen → Einstellungen** eintragen.
- [ ] **Erster echter Verkauf als Test:** einen günstigen Artikel inserieren, kaufen lassen,
      „eBay-Verkäufe abholen", Versand melden. Erst dieser Lauf zeigt, ob eBays echtes
      Bestellformat zur Dokumentation passt – in der Sandbox ließ sich das nur nachstellen.
- [ ] Datenordner regelmäßig sichern (eine Kopie des Ordners genügt).

## API-Überblick

Alle Pfade beginnen mit `/api/`. Bis auf Registrierung und Login braucht jeder Aufruf den Header
`Authorization: Bearer <access-token>`. Fehler haben immer die Form `{"error": …}`.

| Bereich | Pfade | Dokumentation |
|---|---|---|
| Anmeldung | `registration/`, `login/`, `token/refresh/`, `logout/` | [auth_app](backend/auth_app/README.md) |
| Artikel | `categories/`, `products/`, `products/counts/`, `products/<id>/images/`, `product-images/<id>/` | [products_app](backend/products_app/README.md) |
| Bestellungen | `orders/`, `orders/product-sales/`, `orders/<id>/cancel/` | [orders_app](backend/orders_app/README.md) |
| Finanzen | `goals/`, `finance/settings/`, `finance/reports/…` | [finance_app](backend/finance_app/README.md) |
| Lager | `warehouses/` | [logistics_app](backend/logistics_app/README.md) |
| eBay | `ebay/status/`, `ebay/connect/…`, `ebay/shipping-profiles/`, `ebay/policies/`, `ebay/listings/…`, `ebay/unassigned/…`, `ebay/orders/…` | [ebay_app](backend/ebay_app/README.md) |
| Dashboard | `dashboard/summary/` | [core](backend/core/README.md) |

Schnelltest mit `curl`:

```bash
curl -X POST http://127.0.0.1:8000/api/login/ -H "Content-Type: application/json" -d '{"email": "du@example.org", "password": "dein-passwort"}'
```

```bash
curl http://127.0.0.1:8000/api/products/ -H "Authorization: Bearer <access-token>"
```

## Projektstruktur

```
EricKun-Ya/
  README.md
  backend/
    manage.py
    requirements.txt
    .env.example          Vorlage für die .env
    core/                 Einstellungen, Routing, Fehlerformat, Pagination, Dashboard
    auth_app/  products_app/  orders_app/  finance_app/  logistics_app/  ebay_app/
    data/                 Datenbank + Bilder (nicht im Git)
  frontend/
    *.html                eine Datei je Seite
    css/style.css
    js/                   gemeinsame Helfer + ein Skript je Seite
```

Jede App folgt demselben Muster: `models.py`, Logik in `services.py` / `services/` / `utils.py`,
Nebenwirkungen in `signals.py`, die API in `api/` (`serializers.py`, `views.py`, `urls.py`).

## Bekannte Grenzen

- **Keine Rollen und Rechte:** Jedes angemeldete Konto darf alles.
- **Die Registrierung ist offen:** Wer die Adresse erreicht, kann sich ein Konto anlegen. Das
  Programm ist für den Betrieb auf dem eigenen Rechner gedacht – nicht offen ins Internet stellen.
- **Kein Produktivbetrieb als Webserver:** Django liefert Frontend und Bilder nur mit `DEBUG=True` aus.
- **Keine automatisierten Tests:** Geprüft wird über API-Aufrufe gegen eine Datenkopie und gegen
  die eBay-Sandbox.
- **Finanzen sind keine Buchhaltung:** Die eBay-Gebühren sind eine Schätzung über einen Prozentsatz.
- **Sandbox-Kasse:** Abholen von Verkäufen, eBay-Storno und Versandmeldung sind nur mit
  nachgestellten eBay-Antworten geprüft.
- **Storno geht nicht an eBay:** Eine eBay-Bestellung wird bei eBay storniert; der nächste Abruf
  übernimmt das.
- **Nicht unterstützt:** Auktionen, Inserate mit Varianten, Käufernachrichten.
- **Frontend nur für Laptop-Bildschirme,** ohne Anpassung an kleine Displays.
