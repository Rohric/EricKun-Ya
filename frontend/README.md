# frontend

Übergangs-Frontend in Vanilla HTML/CSS/JS für das EricKun-Ya Verkaufstool. Es bedient die
DRF-API des Backends und wird später in Angular neu gebaut – deshalb bewusst schlank und
ohne Framework.

## Überblick

- Fünf Seiten: Login, Dashboard, Artikel, Bestellungen, Finanzen
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
  orders.html      Bestellungen, Storno
  finances.html    Steuerrechnung, Zeitfilter, Monatsumsatz, Ziele
  css/style.css    gesamtes Styling
  js/config.js     API-Pfad, Seitengröße
  js/api.js        fetch-Wrapper mit JWT + Token-Refresh
  js/auth.js       Login, Registrierung, Logout, Seitenschutz
  js/ui.js         gemeinsame Helfer (Navigation, Formatierung, Kacheln, Pager, …)
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
  wird zurückgebucht

### Finanzen (`finances.html`, `finances.js`)
- Zeitfilter: Heute / Monat / Jahr / Gesamt **oder** freier Zeitraum von–bis
- **Steuerrechnung:** Brutto-Gewinn − Rücklage = Netto-Gewinn (stornierte Bestellungen
  zählen nicht mit)
- Kacheln: Umsatz, Einkauf
- Rücklagensatz ändern
- Monatsumsatz als Balkendiagramm mit **Jahr-Umschalter**
- Ziele anlegen, **bearbeiten, deaktivieren/aktivieren und löschen**

## Gemeinsame Module

- **`config.js`** – `API_BASE_URL = "/api"`, `PAGE_SIZE = 25`
- **`api.js`** – `apiGet`, `apiSend`, `apiDelete`, `apiUpload` (multipart); hängt den
  Bearer-Token an, erneuert ihn bei 401 einmal automatisch
- **`auth.js`** – Token-Speicher, `login`, `register`, `logout`, `requireAuth`
- **`ui.js`** – `renderNav`, `showMessage`, `errorText`, `escapeHtml`, `formatEuro`,
  `inputValue`, `markActive`, `renderTiles`, `renderGoalCard`, `renderPager`,
  `periodRange`, `isoDate`

## Authentifizierung

Login und Registrierung liefern ein JWT-Paar, das im `localStorage` liegt. Jeder Request
schickt `Authorization: Bearer <access>`; bei 401 wird über `/api/token/refresh/` erneuert
und die Anfrage wiederholt. Logout setzt den Refresh-Token serverseitig auf die Blacklist.

## Grenzen

- **Nur Laptop-Ansicht** – bewusst ohne Media Queries
- JWT im `localStorage` ist für das Tool ausreichend; beim Angular-Umbau härten
- Übergangslösung: Struktur und API bleiben, das UI wird in Angular neu gebaut
