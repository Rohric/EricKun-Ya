# frontend

Übergangs-Frontend in Vanilla HTML/CSS/JS für das EricKun-Ya Verkaufstool. Es bedient die
DRF-API des Backends und wird später in Angular neu gebaut – deshalb bewusst schlank und
ohne Framework.

## Überblick

- Sieben Seiten: Login, Dashboard, Artikel, Bestellungen, Lager, Finanzen, eBay
- Der Header zeigt nur die drei Bereiche **Dashboard, Artikel, eBay**. Darunter steht eine
  **zweite Navigationszeile** mit den Ansichten des Bereichs:
  - Dashboard: Übersicht · Finanzen
  - Artikel: Artikel · Bestellungen · Lager · eBay-Inserate
  - eBay: Übersicht · Inserate · Neu inserieren · Vorlagen · Verkäufe · Auswertung
- Die Kacheln auf dem Dashboard führen zusätzlich als Abkürzung in die Bereiche
- Artikel und Finanzen haben eigene Reiter innerhalb der Seite; eBay und Finanzen merken sich
  die Ansicht in der Adresse (`#…`), sie bleibt beim Neuladen erhalten
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
  dashboard.html   Bereichs-Kacheln, Kennzahlen, Ziele
  products.html    Artikel mit Status-Reitern, Filtern, Kanälen, Kategorien, Bildern
  orders.html      Bestellungen, Zahlung, Storno, eBay-Verkäufe, Versand melden
  warehouse.html   Lagerort (Versandadresse)
  finances.html    Übersicht, Verkäufe, Aufteilung, Ziele, Einstellungen
  ebay.html        Übersicht, Inserate, Neu inserieren, Vorlagen, Verkäufe, Auswertung
  css/style.css    gesamtes Styling
  js/config.js     API-Pfad, Seitengröße
  js/api.js        fetch-Wrapper mit JWT + Token-Refresh
  js/auth.js       Login, Registrierung, Logout, Seitenschutz
  js/ui.js         gemeinsame Helfer (Navigation, Reiter, Formatierung, Kacheln, Pager, …)
  js/ship-dialog.js    Dialog „Versand an eBay melden" (Bestellungen + eBay)
  js/sales-report.js   Verkaufstabelle mit EK/VK (Finanzen + eBay)
  js/ebay-orders.js    eBay-Verkäufe abholen (Dashboard, Bestellungen, eBay)
  js/ebay.js           eBay-Reiter: Gerüst, Übersicht, Auswertung
  js/ebay-listings.js  eBay-Reiter: Inserate, Neu inserieren, Inserieren-Dialog
  js/ebay-templates.js eBay-Reiter: Versandprofile, Rückgabe/Zahlung, Lagerort
  js/ebay-sales.js     eBay-Reiter: Verkäufe
  js/<seite>.js    Logik je Seite
```

## Seiten & Funktionen

### Login (`index.html`, `login.js`)
- Anmelden mit E-Mail + Passwort
- Umschalter zur Registrierung (Name, E-Mail, Passwort ×2)
- Wer schon angemeldet ist, landet direkt im Dashboard

### Dashboard (`dashboard.html`, `dashboard.js`)
- **Bereichs-Kacheln** mit Kennzahl und Link: Bestellungen (zu verschicken, Zahlung offen,
  Reklamationen), Finanzen (Umsatz und Gewinn des Monats), Lager (Artikel, Stück), eBay
  (online, geändert, Fehler)
- Kacheln: Umsatz, Netto-Gewinn, Rücklage, Brutto-Gewinn mit Zeitraum-Umschalter
- Kurzblick auf die **aktiven** Ziele
- Holt beim Öffnen neue eBay-Verkäufe ab (höchstens alle 10 Minuten) und meldet, was kam

### Artikel (`products.html`, `products.js`)
- Reiter **Alle · Verfügbar · Reserviert · Verkauft · Archiv**, jeweils mit Anzahl
- Filter: Kategorie (inkl. Unterkategorien) und Suche nach Titel oder Artikelnummer
- Tabelle mit Bild, SKU, Titel, Kategorie, Status, **Kanäle**, Zustand, Preisen, Gewinn,
  **Bestand**; seitenweise (25 pro Seite)
- Spalte „Bestand": `noch da / insgesamt`, z. B. „1 / 2", mit Balken für den verkauften Anteil.
  Hat ein Artikel Verkäufe, lässt sich die Zeile aufklappen: eine Kachel „im Lager" (Status,
  Inserat) und je Verkauf eine Kachel mit Datum, Preis, Kanal, Käufer, Bestell- und
  Zahlungsstatus. Die Daten kommen aus `/api/orders/product-sales/`
- Spalte „Kanäle": je Verkaufskanal ein Badge (heute „eBay · Online / Geändert / Beendet /
  Entwurf / Fehler"), bei laufendem Inserat als Link. Die Daten kommen getrennt aus
  `/api/ebay/listing-states/`; ein weiterer Kanal wäre nur ein weiterer Eintrag
- Anlegen / Bearbeiten, Bilder hochladen und löschen; verkaufte und archivierte Artikel
  reaktivieren oder löschen
- **Kategorien verwalten:** Ober- und Unterkategorien anlegen und löschen

### Bestellungen (`orders.html`, `orders.js`, `ship-dialog.js`)
- Tabelle mit Datum, Status, **Zahlung**, Kunde, Ort, Umsatz, Gewinn, Positionen; neueste zuerst
- Filter: Herkunft (eBay / manuell), Zahlung (bezahlt / offen), Status
- Neue Bestellung: Datum, Status, Zahlung, Käufer- und Lieferdaten, Tracking; Positionen mit
  Artikelauswahl (zeigt den verfügbaren Bestand, Verkaufspreis wird vorbefüllt); der Bestand
  wird beim Speichern abgebucht
- Bearbeiten: Status, Kunden- und Versanddaten; Positionen sind nach dem Anlegen fest
- **eBay-Bestellungen:** „eBay"-Kennzeichen; Zahlung und Tracking kommen von eBay. „Verschickt"
  lässt sich nicht von Hand setzen – die Auswahl öffnet „Versand melden". „Versand melden" ist
  gesperrt, solange die Zahlung offen ist. „Zugestellt" geht erst nach dem gemeldeten Versand
- **Storno** mit Auswahl (verfügbar / Archiv / löschen) und optionalem Grund; Grund und
  Herkunft stehen danach unter dem Status. Ein Storno einer eBay-Bestellung wird **nicht** an
  eBay gemeldet – der Dialog weist darauf hin
- **eBay-Verkäufe abholen:** Button oben, zusätzlich automatisch beim Öffnen

### Lager (`warehouse.html`, `warehouse.js`)
- Lagerort anlegen bzw. bearbeiten: Bezeichnung, Straße, PLZ, Ort, Ländercode
- Das ist die Adresse, von der verschickt wird; eBay bekommt sie als Artikelstandort
- Nach einer Adressänderung im eBay-Reiter unter „Vorlagen" erneut übertragen

### Finanzen (`finances.html`, `finances.js`, `sales-report.js`)
Zeitfilter (Heute / Monat / Jahr / Gesamt oder von–bis) gilt für die ersten drei Reiter.
- **Übersicht:** Steuerrechnung (Brutto − Rücklage = Netto; geschätzte eBay-Gebühren sind im
  Brutto bereits abgezogen), Kacheln Umsatz, Einkauf, geschätzte Gebühren, Zahlung offen;
  Monatsumsatz mit Jahr-Umschalter
- **Verkäufe:** je verkaufter Position EK, VK, Umsatz, geschätzte Gebühr, Gewinn, Marge;
  Filter Kategorie und Kanal; Summenzeile
- **Aufteilung:** Umsatz, Gebühr, Gewinn und Marge nach Kanal und nach Kategorie, mit Balken
  für den Umsatzanteil
- **Ziele:** anlegen, bearbeiten, deaktivieren/aktivieren, löschen
- **Einstellungen:** Rücklagensatz und geschätzter eBay-Gebührensatz

Stornierte Bestellungen und Bestellungen mit offener Zahlung zählen nirgends als Umsatz.

### eBay (`ebay.html`, `ebay*.js`)
Badge oben zeigt die Umgebung (Sandbox / Production).
- **Übersicht:** Kennzahlen (online, geändert, Fehler, beendet, zu verschicken, Zahlung offen),
  Checkliste, Verbindung („Mit eBay verbinden" öffnet den eBay-Login; danach die Adresse aus der
  Browserleiste einfügen und „Verbindung abschließen")
- **Inserate:** laufende und beendete Inserate mit Preis, **Preis bei eBay** (markiert, wenn er
  abweicht), Menge, verkaufter Stückzahl, Status samt eBays Fehlermeldung, eBay-Kategorie und
  Versandprofil. Aktionen: Synchronisieren, Bearbeiten, Beenden, Wieder einstellen, Ansehen;
  oben „Alle synchronisieren" und „Von eBay aktualisieren"
- **Neu inserieren:** verkaufbare Artikel ohne Inserat mit Hinweis, was fehlt (Bild, Titellänge).
  Dialog: eBay-Kategorievorschläge zum Titel (gemerkte Kategorie oben, vorausgewählt nur wenn
  eBay sie ebenfalls vorschlägt), Pflicht-Merkmale mit Vorschlagsliste, empfohlene aufklappbar,
  Versandprofil, „Preisvorschlag erlauben", „Gebühren prüfen", „Jetzt inserieren"
- **Vorlagen:** Versandprofile anlegen, ändern, als Standard setzen, löschen; Rückgabefrist und
  Kostenträger; Lagerort übertragen
- **Verkäufe:** eBay-Bestellungen mit Zahlung und Status, „eBay-Verkäufe abholen",
  „Versand melden"
- **Auswertung:** die Verkaufstabelle aus den Finanzen, fest auf eBay gefiltert

Inserieren ist erst möglich, wenn die Checkliste vollständig ist; gesperrte Reiter zeigen
einen Hinweis.

## Gemeinsame Module

- **`config.js`** – `API_BASE_URL = "/api"`, `PAGE_SIZE = 25`
- **`api.js`** – `apiGet`, `apiSend`, `apiDelete`, `apiUpload` (multipart); hängt den
  Bearer-Token an, erneuert ihn bei 401 einmal automatisch
- **`auth.js`** – Token-Speicher, `login`, `register`, `logout`, `requireAuth`
- **`ui.js`** – `renderNav` (Header + zweite Zeile, Bereiche in `NAV_AREAS`), `renderTabs`,
  `showMessage`, `errorText`,
  `escapeHtml`, `formatEuro`, `formatPercent`, `inputValue`, `markActive`, `renderTiles`,
  `renderGoalCard`, `renderPager`, `periodRange`, `isoDate`; Beschriftungen
  `LISTING_STATE_LABELS`, `PAYMENT_LABELS`, `FULFILLMENT_LABELS`
- **`ebay-orders.js`** – `importEbayOrders`, `autoImportEbayOrders` (still, nur wenn verbunden
  und der letzte Abruf älter als 10 Minuten ist), `ebayImportChanged`, `ebayImportText`
- **`ship-dialog.js`** – `openShipDialog(order, onDone)`; baut seinen Dialog selbst
- **`sales-report.js`** – `renderSalesReport(containerId, filters)`

## Authentifizierung

Login und Registrierung liefern ein JWT-Paar, das im `localStorage` liegt. Jeder Request
schickt `Authorization: Bearer <access>`; bei 401 wird über `/api/token/refresh/` erneuert
und die Anfrage wiederholt. Logout setzt den Refresh-Token serverseitig auf die Blacklist.

## Grenzen

- **Nur Laptop-Ansicht** – bewusst ohne Media Queries
- JWT im `localStorage` ist für das Tool ausreichend; beim Angular-Umbau härten
- Übergangslösung: Struktur und API bleiben, das UI wird in Angular neu gebaut
