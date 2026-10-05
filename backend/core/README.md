# core

Projekt- und Settings-Modul (Konvention: heißt immer `core`). Hält die zentrale
Konfiguration, das URL-Routing und die DRF-Bausteine, die alle Apps teilen.

## Aufgaben

- Zentrale Django-Konfiguration (`settings.py`), gesteuert über `backend/.env`
- Routing aller App-APIs unter `/api/`
- Einheitliches Fehlerformat für die API
- Optionale Pagination für Listen-Endpoints
- Im DEBUG-Betrieb: Auslieferung von Frontend und hochgeladenen Bildern, damit ein
  einziges `runserver` reicht

## Models

Keine.

## Services / Logik

- **`exceptions.api_exception_handler`** – verpackt jeden DRF-Fehler als `{"error": …}`;
  deshalb kein `try/except` in den Views.
- **`pagination.OptionalPagePagination`** – paginiert **nur**, wenn `?page=` gesetzt ist
  (25 pro Seite, `?page_size=` bis 100). Ohne `page` kommt die normale Liste zurück.
- **Einstellungen (Auszug):**
  - `AUTH_USER_MODEL = "auth_app.User"` (Login per E-Mail)
  - JWT: Access 60 min, Refresh 7 Tage, Rotation + Blacklist
  - `DATA_DIR` (Default `backend/data`) enthält **SQLite-DB und `media/`** – die spätere
    Desktop-App setzt hier den vom Nutzer gewählten Ordner
  - CORS für `localhost:5500` und `localhost:4200` (späteres Angular)
  - Postgres optional über `DB_ENGINE=postgres`
  - eBay: `EBAY_ENV`, `EBAY_CLIENT_ID`, `EBAY_CLIENT_SECRET`, `EBAY_RUNAME`,
    `EBAY_MARKETPLACE_ID`, `EBAY_TOKEN_KEY` (Schlüssel für die Token-Verschlüsselung)

## API-Endpoints

| Methode | Pfad | Zweck |
|---|---|---|
| – | `/admin/` | Django-Admin |
| – | `/api/…` | App-APIs (siehe READMEs der Apps) |
| GET | `/media/…` | Hochgeladene Bilder (nur DEBUG) |
| GET | `/`, `/<datei>` | Frontend aus `../frontend` (nur DEBUG) |

## Verbindungen

- `urls.py` bindet `auth_app`, `products_app`, `orders_app`, `finance_app`,
  `logistics_app` und `ebay_app` ein.
- `pagination.py` wird von `products_app` und `orders_app` genutzt.

## Dateien

- `settings.py` – Konfiguration
- `urls.py` – Routing inkl. Frontend-/Media-Auslieferung im DEBUG
- `exceptions.py` – zentraler Exception-Handler
- `pagination.py` – `OptionalPagePagination`
- `backend/.env.example` – alle Umgebungsvariablen dokumentiert
