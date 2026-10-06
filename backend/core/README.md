# core

## Kurzbeschreibung

Das Projektmodul: zentrale Einstellungen, das Routing aller APIs und die Bausteine, die sich alle
Apps teilen (Fehlerformat, Pagination). Dazu die Kennzahlen für das Dashboard.

**Abgrenzung:** keine eigene Fachlogik und keine Models. Was zu einem Fachgebiet gehört, liegt in
der jeweiligen App.

## Aufgaben

- Django konfigurieren, gesteuert über `backend/.env`
- Alle App-APIs unter `/api/` einbinden
- Fehler einheitlich als `{"error": …}` ausgeben
- Listen nur dann seitenweise liefern, wenn der Aufrufer es verlangt
- Kennzahlen aus mehreren Apps für das Dashboard zusammenstellen
- Im Entwicklungsbetrieb Frontend und hochgeladene Bilder ausliefern, damit ein `runserver` reicht

## Models

Keine.

## Logik

- **`exceptions.api_exception_handler`** – verpackt jeden Fehler der API als `{"error": …}`.
  Deshalb gibt es in den Views kein `try/except`: Services lösen eine Ausnahme aus, hier wird
  sie zur Antwort.
- **`pagination.OptionalPagePagination`** – paginiert nur, wenn `?page=` gesetzt ist (25 je Seite,
  `?page_size=` bis 100). Ohne `page` kommt die ganze Liste als Array.
- **`dashboard.dashboard_summary()`** – Bestellungen, die zu verschicken sind, Umsatz und Gewinn
  des Monats, verkaufbare Artikel und Stückzahl.
- **`settings.py`** (Auszug)
  - `AUTH_USER_MODEL = "auth_app.User"` – Anmeldung per E-Mail
  - JWT: Access 60 Minuten, Refresh 7 Tage, mit Rotation und Sperrliste
  - `DATA_DIR` – Ordner für SQLite-Datenbank und `media/`; Standard `backend/data`
  - `SKU_PREFIX` – Kürzel der internen Artikelnummer
  - `EBAY_*` – Umgebung, Schlüssel, RuName, Marktplatz, Schlüssel für die Token-Verschlüsselung
  - PostgreSQL optional über `DB_ENGINE=postgres`

Alle Variablen sind in der [Haupt-README](../../README.md#einstellungen-env) und in
`backend/.env.example` beschrieben.

## API-Übersicht

| Methode | Pfad | Zweck |
|---|---|---|
| GET | `/api/dashboard/summary/` | Kennzahlen für die Kacheln des Dashboards |
| – | `/api/…` | die APIs der Apps (siehe deren READMEs) |
| – | `/admin/` | Django-Admin |
| GET | `/media/…` | hochgeladene Bilder (nur mit `DEBUG=True`) |
| GET | `/`, `/<datei>` | das Frontend aus `../frontend` (nur mit `DEBUG=True`) |

## API im Detail

### `GET /api/dashboard/summary/`

Verlangt einen angemeldeten Nutzer, keine Parameter.

```json
{
  "orders": {"to_ship": 2, "unpaid": 0, "in_return": 0},
  "finance": {"revenue_month": "67.20", "profit_month": "46.81"},
  "stock": {"products": 5, "units": 7}
}
```

| Feld | Bedeutung |
|---|---|
| `orders.to_ship` | Bestellungen mit Status offen oder verpackt |
| `orders.unpaid` | davon mit offener Zahlung |
| `orders.in_return` | Bestellungen in Reklamation |
| `finance.revenue_month`, `finance.profit_month` | Umsatz und Brutto-Gewinn seit Monatsanfang |
| `stock.products`, `stock.units` | verfügbare oder reservierte Artikel und ihre Stückzahl |

### Fehlerformat aller Endpoints

| Status | Wann | Beispiel |
|---|---|---|
| `400` | ein Feld fehlt oder ist ungültig | `{"error": {"purchase_price": ["This field is required."], "sale_price": ["This field is required."]}}` |
| `400` | eine Regel ist verletzt | `{"error": ["Unbekannter Status. Erlaubt: available, reserved, sold, archived."]}` |
| `401` | kein oder abgelaufener Token | `{"error": {"detail": "Authentication credentials were not provided."}}` |
| `404` | das Objekt gibt es nicht | `{"error": {"detail": "No Product matches the given query."}}` |
| `409` | nicht mit eBay verbunden | `{"error": {"detail": "Nicht mit eBay verbunden. Bitte im eBay-Reiter verbinden."}}` |
| `502` | eBay hat abgelehnt oder ist nicht erreichbar | `{"error": {"detail": "Die Versandkosten dürfen in dieser Kategorie nicht mehr als EUR 4,00 betragen."}}` |
| `503` | eBay-Werte in der `.env` fehlen | `{"error": {"detail": "In der .env fehlt: EBAY_CLIENT_ID"}}` |

Meldungen, die das Programm selbst formuliert, sind deutsch. Die Standardprüfungen des Frameworks
(Pflichtfeld, ungültige Auswahl, „nicht gefunden") kommen englisch zurück.

### Pagination

`GET /api/products/?status=available&page=1` liefert statt eines Arrays ein Objekt mit der
Gesamtzahl, den Adressen der Nachbarseiten (oder `null`) und den Einträgen der Seite:

```
{"count": 5, "next": null, "previous": null, "results": [ … ]}
```

## Anwendung

```bash
python manage.py runserver
```

startet API, Admin und Frontend auf `http://127.0.0.1:8000/`. Eine neue App wird in
`INSTALLED_APPS` eingetragen und ihre `api/urls.py` in `core/urls.py` eingebunden – mehr braucht
es nicht, um unter `/api/` erreichbar zu sein.

```bash
curl http://127.0.0.1:8000/api/dashboard/summary/ -H "Authorization: Bearer <token>"
```

## Verbindungen

- `urls.py` bindet `auth_app`, `products_app`, `orders_app`, `finance_app`, `logistics_app` und
  `ebay_app` ein.
- `dashboard.py` liest aus `orders_app`, `products_app` und `finance_app`.
- `pagination.py` nutzen `products_app`, `orders_app` und `ebay_app`.

## Dateien

| Datei | Inhalt |
|---|---|
| `settings.py` | Konfiguration |
| `urls.py` | Routing, im Entwicklungsbetrieb auch Frontend und Bilder |
| `exceptions.py` | zentrales Fehlerformat |
| `pagination.py` | `OptionalPagePagination` |
| `dashboard.py`, `views.py` | Kennzahlen für das Dashboard |
| `asgi.py`, `wsgi.py` | Einstiegspunkte für einen Webserver |
