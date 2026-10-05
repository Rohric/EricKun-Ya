# frontend

Übergangs-Frontend in Vanilla HTML/CSS/JS für das EricKun-Ya Verkaufstool. Es bedient die
DRF-API des Backends und wird später in Angular neu gebaut – deshalb bewusst schlank und
ohne Framework.

## Überblick

- Sieben Seiten: Login, Dashboard, Artikel, Bestellungen, Lager, Finanzen, eBay
- Gemeinsame Navigation mit Logout auf allen Seiten außer dem Login
- Alle Daten kommen über `/api/…` vom Django-Backend (same-origin, kein CORS nötig)

## Starten

Das Backend liefert das Frontend im DEBUG-Betrieb mit aus – ein Befehl reicht (aus `backend/`,
venv aktiviert):

```
python manage.py runserver
```

Dann `http://127.0.0.1:8000/` öffnen. Nach Änderungen an JS/CSS einmal **Strg+Shift+R**
(Browser-Cache).

## Aufbau

```
frontend/
  index.html       Login + Registrierung
  dashboard.html   Startübersicht
  products.html    Artikel, Kategorien, Archiv, Bilder
  orders.html      Bestellungen, Storno, eBay-Verkäufe, Versand melden
  warehouse.html   Lagerort (Versandadresse)
  finances.html    Steuerrechnung, Zeitfilter, Monatsumsatz, Ziele
  ebay.html        eBay-Verbindung, Einrichtung und Inserate
  css/style.css    gesamtes Styling
  js/config.js     API-Pfad, Seitengröße
  js/api.js        fetch-Wrapper mit JWT + Token-Refresh
  js/auth.js       Login, Registrierung, Logout, Seitenschutz
  js/ui.js         gemeinsame Helfer (Navigation, Formatierung, Kacheln, Pager, …)
  js/ebay-listings.js  Inserate-Tabelle und Inserieren-Dialog im eBay-Reiter
  js/ebay-orders.js    eBay-Verkäufe abholen (Dashboard + Bestellungen)
  js/<seite>.js    Logik je Seite
```

## Seiten & Funktionen

### Login (`index.html`, `login.js`)
- Anmelden mit E-Mail + Passwort
- Umschalter zur Registrierung (Name, E-Mail, Passwort ×2)
- Wer schon angemeldet ist, landet direkt im Dashboard

### Dashboard (`dashboard.html`, `dashboard.js`)
- Kacheln: Umsatz, Netto-Gewinn, Rücklage, Brutto-Gewinn
- Zeitraum-Umschalter: Heute / Monat / Jahr / Gesamt
- Kurzblick auf die **aktiven** Ziele mit Fortschrittsbalken, Link „Verwalten" zu Finanzen
- Holt beim Öffnen neue eBay-Verkäufe ab (höchstens alle 10 Minuten) und meldet, was kam

### Artikel (`products.html`, `products.js`)
- Umschalter **Aktiv / Archiv** (Archiv = verkaufte und archivierte Artikel)
- Tabelle mit Bild, SKU, Titel, Kategorie, Status, Zustand, Preisen, Gewinn, Menge;
  seitenweise (25 pro Seite)
- Anlegen / Bearbeiten: Titel, Status, Ober- + Unterkategorie, Zustand, Menge, Preise,
  Einkaufsdatum, Beschreibung
- Bilder: nach dem ersten Speichern mehrere hochladen, einzeln löschen; das erste Bild
  erscheint als Vorschau in der Tabelle
- Archiv: Artikel **reaktivieren** oder löschen
- **Kategorien verwalten:** Ober- und Unterkategorien anlegen und löschen

### Bestellungen (`orders.html`, `orders.js`)
- Tabelle mit Datum, Status, Kunde, Ort, Umsatz, Gewinn, Positionen; neueste zuerst,
  seitenweise
- Neue Bestellung: Verkaufsdatum, Status, Käufer- und Lieferdaten, Tracking; Positionen
  mit Artikelauswahl (zeigt den **verfügbaren Bestand**, Menge ist darauf begrenzt,
  Verkaufspreis wird vorbefüllt)
- Beim Speichern wird der **Bestand automatisch abgebucht**
- Bearbeiten: Status, Kunden- und Versanddaten, Tracking; bei „In Reklamation" zusätzlich
  eine Notiz. Positionen sind nach dem Anlegen fest
- **Storno** mit Auswahl: Artikel wieder verfügbar, ins Archiv oder löschen – der Bestand
  wird zurückgebucht. Optionaler Grund; Grund und Herkunft (manuell / eBay) stehen danach
  unter dem Status
- **eBay-Verkäufe abholen:** Button oben, zusätzlich automatisch beim Öffnen (höchstens alle
  10 Minuten). eBay-Bestellungen tragen ein „eBay"-Kennzeichen
- **Versand melden** (nur eBay-Bestellungen, Status offen / verpackt): Dienstleister und
  Trackingnummer gehen an eBay, die Bestellung wird „Verschickt"
- Ein Storno einer eBay-Bestellung wird **nicht** an eBay gemeldet – der Dialog weist darauf hin

### Lager (`warehouse.html`, `warehouse.js`)
- Lagerort anlegen bzw. bearbeiten: Bezeichnung, Straße, PLZ, Ort, Ländercode
- Das ist die Adresse, von der verschickt wird; eBay bekommt sie als Artikelstandort
- Nach einer Adressänderung im eBay-Reiter erneut übertragen

### Finanzen (`finances.html`, `finances.js`)
- Zeitfilter: Heute / Monat / Jahr / Gesamt **oder** freier Zeitraum von–bis
- **Steuerrechnung:** Brutto-Gewinn − Rücklage = Netto-Gewinn (stornierte Bestellungen
  zählen nicht mit)
- Kacheln: Umsatz, Einkauf
- Rücklagensatz ändern
- Monatsumsatz als Balkendiagramm mit **Jahr-Umschalter**
- Ziele anlegen, **bearbeiten, deaktivieren/aktivieren und löschen**

### eBay (`ebay.html`, `ebay.js`, `ebay-listings.js`)
- Badge zeigt die Umgebung (Sandbox / Production)
- **Checkliste:** Zugangsdaten in der `.env` → verbunden → Policies → Lagerort → „Bereit zum
  Inserieren"
- **Verbindung:** „Mit eBay verbinden" öffnet den eBay-Login in einem neuen Tab; danach die
  Adresse aus der Browserleiste einfügen und „Verbindung abschließen". „Trennen" löscht die
  gespeicherten Tokens
- **Versand, Rückgabe, Zahlung:** Versanddienst (Liste kommt live von eBay), Versandkosten,
  Bearbeitungszeit, Rückgabefrist (Standard 30 Tage), Rücksendekosten (Standard Käufer)
- **Lagerort:** zeigt den Standard-Lagerort und überträgt ihn an eBay
- Einrichtung ist erst nach der Verbindung bedienbar
- **Inserate** (bedienbar, sobald die Checkliste grün ist): Tabelle der verkaufbaren Artikel
  mit Status „Nicht inseriert / Entwurf / Online / Geändert / Beendet / Fehler" und der
  Fehlermeldung von eBay direkt in der Zeile
  - **Inserieren:** Dialog mit eBay-Kategorievorschlägen zum Titel (eigener Suchbegriff
    möglich), Pflicht-Merkmalen mit Vorschlagsliste und aufklappbaren empfohlenen Merkmalen.
    Die zuletzt für die interne Kategorie gewählte eBay-Kategorie steht als „gemerkt" oben
    und ist vorausgewählt, wenn eBay sie für den Titel ebenfalls vorschlägt
  - **Synchronisieren / Alle synchronisieren**, **Beenden**, **Wieder einstellen**,
    **Merkmale** (Kategorie und Merkmale nachträglich ändern), **Ansehen** (Inserat bei eBay)

## Gemeinsame Module

- **`config.js`** – `API_BASE_URL = "/api"`, `PAGE_SIZE = 25`
- **`api.js`** – `apiGet`, `apiSend`, `apiDelete`, `apiUpload` (multipart); hängt den
  Bearer-Token an, erneuert ihn bei 401 einmal automatisch
- **`auth.js`** – Token-Speicher, `login`, `register`, `logout`, `requireAuth`
- **`ui.js`** – `renderNav`, `showMessage`, `errorText`, `escapeHtml`, `formatEuro`,
  `inputValue`, `markActive`, `renderTiles`, `renderGoalCard`, `renderPager`,
  `periodRange`, `isoDate`
- **`ebay-orders.js`** – `importEbayOrders`, `autoImportEbayOrders` (still, nur wenn verbunden
  und der letzte Abruf älter als 10 Minuten ist), `ebayImportChanged`, `ebayImportText`

## Authentifizierung

Login und Registrierung liefern ein JWT-Paar, das im `localStorage` liegt. Jeder Request
schickt `Authorization: Bearer <access>`; bei 401 wird über `/api/token/refresh/` erneuert
und die Anfrage wiederholt. Logout setzt den Refresh-Token serverseitig auf die Blacklist.

## Grenzen

- **Nur Laptop-Ansicht** – bewusst ohne Media Queries
- JWT im `localStorage` ist für das Tool ausreichend; beim Angular-Umbau härten
- Übergangslösung: Struktur und API bleiben, das UI wird in Angular neu gebaut
