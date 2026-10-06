# frontend

## Kurzbeschreibung

Die Bedienoberfläche: HTML, CSS und JavaScript ohne Framework. Sie spricht ausschließlich mit der
API des Backends und führt die Daten der Apps zusammen.

**Abgrenzung:** Übergangslösung – das Frontend wird später in Angular neu gebaut. Deshalb bewusst
schlank, nur für Laptop-Bildschirme und ohne Anpassung an kleine Displays. Fachlogik liegt im
Backend; hier wird angezeigt, eingegeben und zusammengeführt.

## Aufgaben

- Anmelden, registrieren, abmelden
- Artikel, Bestellungen, Lager und Finanzen bedienen
- eBay einrichten, inserieren, Inserate und Verkäufe verwalten
- Inserate von Portalen den Artikeln zuordnen
- Daten mehrerer Apps zusammenführen (z. B. Artikel + Kanäle + Verkäufe in einer Tabelle)

## Models

Keine. Das Frontend speichert nur das Token-Paar der Anmeldung im `localStorage`.

## Logik

**Navigation** – Der Header zeigt drei Bereiche; darunter liegt eine zweite Zeile mit den
Ansichten des Bereichs. Beides steht in `NAV_AREAS` in `js/ui.js`.

| Bereich | Ansichten |
|---|---|
| Dashboard | Übersicht · Finanzen |
| Artikel | Artikel · Bestellungen · Lager · Zuordnung · eBay-Inserate |
| eBay | Übersicht · Inserate · Neu inserieren · Vorlagen · Verkäufe · Auswertung |

eBay und Finanzen merken sich den Reiter in der Adresse (`#…`), er bleibt beim Neuladen erhalten.

**Gemeinsame Module**

| Datei | Inhalt |
|---|---|
| `js/config.js` | `API_BASE_URL = "/api"`, `PAGE_SIZE = 25` |
| `js/api.js` | `apiGet`, `apiSend`, `apiDelete`, `apiUpload`; hängt den Token an und erneuert ihn bei `401` einmal automatisch |
| `js/auth.js` | Token-Speicher, `login`, `register`, `logout`, `requireAuth` |
| `js/ui.js` | Navigation, Reiter, Meldungen, Formatierung, Kacheln, Pager; Beschriftungen für Inserats-, Zahlungs- und Versandstatus |
| `js/ebay-orders.js` | eBay-Verkäufe abholen, auch still beim Öffnen des Dashboards (höchstens alle 10 Minuten) |
| `js/ship-dialog.js` | Dialog „Versand an eBay melden" |
| `js/sales-report.js` | Verkaufstabelle mit Einkaufs- und Verkaufspreis (Finanzen und eBay) |

**Anmeldung** – Login und Registrierung liefern ein Token-Paar. Jeder Aufruf schickt
`Authorization: Bearer <access>`; bei `401` holt `api.js` über `/api/token/refresh/` einen neuen
Token und wiederholt den Aufruf. Abmelden sperrt den Refresh-Token auf dem Server.

**Portale zusammenführen** – Die Artikelliste lädt die Kanäle getrennt (`/api/ebay/listing-states/`),
die Seite „Zuordnung" lädt die offenen Inserate je Portal. Die Liste der Portale steht an genau
einer Stelle: `CHANNELS` in `js/channels.js`. Ein weiteres Portal ist dort ein weiterer Eintrag.

## API-Übersicht

Welche Seite welche Endpoints verwendet (alle unter `/api/`):

| Seite | Endpoints |
|---|---|
| `index.html` | `login/`, `registration/` |
| `dashboard.html` | `dashboard/summary/`, `finance/reports/profit-loss/`, `goals/`, `ebay/status/`, `ebay/orders/import/` |
| `products.html` | `products/`, `products/counts/`, `categories/`, `products/<id>/images/`, `product-images/<id>/`, `orders/product-sales/`, `ebay/listing-states/` |
| `orders.html` | `orders/`, `orders/<id>/cancel/`, `products/`, `ebay/status/`, `ebay/orders/import/`, `ebay/orders/<id>/ship/`, `ebay/carriers/` |
| `warehouse.html` | `warehouses/` |
| `channels.html` | `ebay/listings/pull/`, `ebay/unassigned/…`, `ebay/listing-states/`, `products/` |
| `finances.html` | `finance/reports/…`, `finance/settings/`, `goals/`, `categories/` |
| `ebay.html` | alle Endpoints unter `ebay/` außer `unassigned/…` und `listings/pull/`, dazu `orders/`, `warehouses/` und `finance/reports/sales/` |
| alle Seiten | `token/refresh/` (automatisch bei abgelaufenem Token), `logout/` |

## API im Detail

Die Endpoints sind in den READMEs der Apps beschrieben:
[auth_app](../backend/auth_app/README.md) · [products_app](../backend/products_app/README.md) ·
[orders_app](../backend/orders_app/README.md) · [finance_app](../backend/finance_app/README.md) ·
[logistics_app](../backend/logistics_app/README.md) · [ebay_app](../backend/ebay_app/README.md) ·
[core](../backend/core/README.md)

Das Frontend erwartet von jedem Fehler die Form `{"error": …}` und zeigt die erste Meldung darin
an (`errorText` in `js/ui.js`).

## Anwendung

**Starten** – Das Backend liefert das Frontend im Entwicklungsbetrieb mit aus (aus `backend/`,
venv aktiv):

```bash
python manage.py runserver
```

Dann `http://127.0.0.1:8000/` öffnen. Nach Änderungen an JavaScript oder CSS einmal
**Strg+Shift+R**, damit der Browser die neuen Dateien lädt.

**Die Seiten**

*Login* – anmelden mit E-Mail und Passwort, Umschalter zur Registrierung.

*Dashboard* – Kacheln für Bestellungen, Finanzen, Lager und eBay mit Kennzahl und Link; Umsatz,
Gewinn und Rücklage mit Zeitraum-Umschalter; die aktiven Ziele.

*Artikel* – Reiter Alle · Verfügbar · Reserviert · Verkauft · Archiv mit Anzahl, Filter nach
Kategorie und Suche. Die Spalte **Bestand** zeigt „noch da / insgesamt" (z. B. „1 / 2") und lässt
sich bei Artikeln mit Verkäufen aufklappen. Die Spalte **Kanäle** zeigt je Portal ein Kennzeichen
mit Status. Steht beim Einkaufspreis „nachtragen", wurde der Artikel aus einem Inserat übernommen.

*Bestellungen* – Liste mit Filtern (Herkunft, Zahlung, Status), neue Bestellung, Storno mit Wahl,
was mit den Artikeln passiert. eBay-Bestellungen lassen sich nur über „Versand melden" auf
„verschickt" setzen, und erst nach Zahlungseingang.

*Lager* – der Lagerort, von dem verschickt wird.

*Zuordnung* – Inserate, die bei einem Portal online sind, aber zu keinem Artikel gehören.
1. **„Mit eBay abgleichen"** holt die Inserate.
2. Je Inserat: **Verknüpfen** (Artikel in der Auswahl wählen – ein Vorschlag ist vorausgewählt und
   will geprüft werden), **Neuer Artikel** oder **Ignorieren**.
3. **„Alle als neue Artikel anlegen"** ist der Weg bei leerer Datenbank.
4. „Ignorierte anzeigen" blendet ausgeblendete Inserate wieder ein.

Vor dem Umwandeln eines Inserats, das nicht über das Programm angelegt wurde, fragt die Seite
nach: Es lässt sich danach nur noch über das Programm ändern. Lehnt eBay ab, steht der Grund in
der Spalte „Hinweis".

*Finanzen* – Reiter Übersicht (Steuerrechnung, Monatsumsatz), Verkäufe (je Position mit Gebühr,
Gewinn, Marge), Aufteilung (nach Kanal und Kategorie), Ziele, Einstellungen.

*eBay* – oben die Umgebung (Sandbox oder Production).
- **Übersicht:** Kennzahlen, Checkliste, Verbindung
- **Inserate:** laufende und beendete Inserate; Synchronisieren, Bearbeiten, Beenden, **Lösen**
  (trennt Artikel und Inserat, ohne bei eBay etwas zu ändern), Ansehen. Trägt ein Inserat bei eBay
  eine andere Nummer als der Artikel, steht sie unter der Artikelnummer. Ein Hinweis führt zur
  Zuordnung, solange Inserate keinem Artikel gehören
- **Neu inserieren:** verkaufbare Artikel ohne Inserat; Dialog mit Kategorie-Vorschlägen,
  Merkmalen, Versandprofil, Preisvorschlag und Gebühren-Vorschau
- **Vorlagen:** Versandprofile, Rückgabe und Zahlung, Lagerort übertragen
- **Verkäufe:** eBay-Bestellungen, abholen, Versand melden
- **Auswertung:** die Verkaufstabelle der Finanzen, auf eBay gefiltert

Inserieren geht erst, wenn die Checkliste vollständig ist; gesperrte Reiter zeigen einen Hinweis.

## Verbindungen

- Spricht nur mit dem Backend unter `/api/…` (gleicher Server, kein CORS nötig).
- Kennt keine Datenbank und keine eBay-Zugangsdaten; die Verbindung zu eBay hält das Backend.

## Dateien

```
frontend/
  index.html       Login und Registrierung
  dashboard.html   Kacheln, Kennzahlen, Ziele
  products.html    Artikel, Kategorien, Bilder
  orders.html      Bestellungen, Storno, Versand melden
  warehouse.html   Lagerort
  channels.html    Zuordnung von Inseraten zu Artikeln
  finances.html    Auswertungen, Ziele, Einstellungen
  ebay.html        alle eBay-Reiter
  css/style.css    das gesamte Styling
  js/config.js  api.js  auth.js  ui.js         gemeinsame Grundlagen
  js/ship-dialog.js  sales-report.js  ebay-orders.js   von mehreren Seiten genutzt
  js/ebay.js             eBay: Gerüst, Übersicht, Auswertung
  js/ebay-listings.js    eBay: Inserate, Neu inserieren, Inserieren-Dialog
  js/ebay-templates.js   eBay: Versandprofile, Rückgabe und Zahlung, Lagerort
  js/ebay-sales.js       eBay: Verkäufe
  js/channels.js         Zuordnung; hier steht die Liste der Portale
  js/<seite>.js          die Logik je Seite
```
