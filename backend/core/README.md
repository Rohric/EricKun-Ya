# core

Projekt- und Settings-Modul (Emils Konvention: heißt immer `core`). Enthält **kein
eigenes Model** und keine fachlichen Endpoints – nur die zentrale Konfiguration und das
URL-Routing, an dem alle Apps hängen.

## Aufgabe

- Zentrale Django-Konfiguration (`settings.py`)
- Haupt-URL-Routing (`urls.py`) – bindet alle App-APIs unter `/api/` ein
- Projektweites DRF-Fehlerhandling (`exceptions.py`)
- WSGI/ASGI-Einstiegspunkte

## Wichtige Einstellungen

- **Custom User:** `AUTH_USER_MODEL = "auth_app.User"`
- **DRF:** JWT-Authentifizierung + `IsAuthenticated` als Default, zentraler
  `EXCEPTION_HANDLER` (kein try/except pro View)
- **JWT (`SIMPLE_JWT`):** Access-Token 60 min, Refresh-Token 7 Tage, Rotation + Blacklist
- **CORS:** `CORS_ALLOWED_ORIGINS` für das Angular-Frontend (Default `http://localhost:4200`)
- **Config über Umgebungsvariablen** (`.env`, via `python-dotenv`): `SECRET_KEY`, `DEBUG`,
  `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `TAX_RESERVE_RATE`
- **Datenbank:** SQLite für lokale Entwicklung; per `DB_ENGINE=postgres` auf PostgreSQL
  umstellbar (für das Deployment)

## Endpoints

| Pfad | Zweck |
|---|---|
| `/admin/` | Django-Admin |
| `/api/…` | Sammelpunkt aller App-APIs (siehe die READMEs der einzelnen Apps) |

## Verbindungen

`core/urls.py` inkludiert die `api/urls.py` von `auth_app`, `products_app`, `orders_app`
und `finance_app`. Weitere Apps (z. B. `ebay_app`) werden hier eingehängt, sobald sie
Endpoints bereitstellen.

## Dateien

- `settings.py` – Konfiguration
- `urls.py` – Routing
- `exceptions.py` – `api_exception_handler` (einheitliches `{"error": ...}`-Format)
- `.env.example` (in `backend/`) – dokumentiert alle Umgebungsvariablen
