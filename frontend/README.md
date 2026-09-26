# frontend

Einfaches Übergangs-Frontend (Vanilla HTML/CSS/JS), das die DRF-API des Backends bedient.
Wird später sauber in Angular neu gebaut – deshalb bewusst schlank und ohne Framework.

## Aufbau

```
frontend/
  index.html      Login + Registrierung
  dashboard.html  Finanz-Dashboard (GuV, Monatsumsatz, Rücklage, Ziele)
  products.html   Artikel-Verwaltung
  orders.html     Bestellungen + Status
  css/style.css   gemeinsames Styling + Navigation
  js/             config, api (fetch+JWT), auth, ui, sowie je Seite ein Modul
```

## Starten

1. **Backend** starten (aus `backend/`):
   ```
   .\venv\Scripts\python.exe manage.py runserver
   ```
2. **Frontend** über einen kleinen Static-Server ausliefern (aus `frontend/`):
   ```
   python -m http.server 5500
   ```
   Alternativ die VS-Code-Erweiterung **Live Server** (Standard-Port 5500).
3. Im Browser öffnen: `http://localhost:5500/`

## Konfiguration

- `js/config.js` → `API_BASE_URL` zeigt auf `http://127.0.0.1:8000/api`.
- Das Backend muss den Frontend-Origin in `CORS_ALLOWED_ORIGINS` erlauben
  (`http://localhost:5500`, `http://127.0.0.1:5500`) – ist in `core/settings.py` bzw. `.env`
  bereits eingetragen.

## Authentifizierung

Login/Registrierung liefern ein JWT-Paar (access + refresh), das im `localStorage` liegt.
Jeder API-Request schickt `Authorization: Bearer <access>`; bei `401` wird der Token einmal
über `/api/token/refresh/` erneuert. Logout setzt den Refresh-Token serverseitig auf die
Blacklist.

## Hinweis

JWT im `localStorage` ist für dieses kleine Tool ausreichend (XSS-Risiko bekannt). Beim
Angular-Umbau lässt sich das Token-Handling härten.
