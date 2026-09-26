# auth_app

App-Login und Registrierung. Stellt das **Custom User Model** des Projekts bereit
(E-Mail statt Username) und die JWT-Authentifizierung.

> Abgrenzung: Hier lebt **nur der App-Login** (wer darf das Tool nutzen). Die
> eBay-OAuth-Tokens gehören in `ebay_app`, **nicht** hierher.

## Aufgaben

- Custom User als projektweites `AUTH_USER_MODEL`
- Registrierung neuer Nutzer
- Login, Token-Refresh und Logout über JSON Web Tokens

## Models

- **`User`** (`AbstractUser`): `email` ist unique und Login-Feld (`USERNAME_FIELD`),
  `username` entfällt, `REQUIRED_FIELDS = []`. Anzeigename in `first_name`.
  Eigener `UserManager` (`create_user` / `create_superuser` per E-Mail).

## Services / Logik

Keine eigenen – Login, Refresh und Logout sind die Standard-Views von
`djangorestframework-simplejwt`. Die Registrierung validiert im `RegistrationSerializer`
(Passwörter gleich, E-Mail eindeutig).

## API-Endpoints

| Methode | Pfad | Zweck |
|---|---|---|
| POST | `/api/registration/` | Nutzer anlegen, liefert access + refresh Token |
| POST | `/api/login/` | Login mit `email` + `password`, liefert Token-Paar |
| POST | `/api/token/refresh/` | Access-Token per Refresh-Token erneuern |
| POST | `/api/logout/` | Refresh-Token auf die Blacklist setzen |

## Verbindungen

- Über `AUTH_USER_MODEL` das Nutzermodell des **gesamten Projekts**.
- Alle geschützten Endpoints der anderen Apps prüfen die hier ausgestellten Tokens.

## Dateien

- `models.py` – `User`, `UserManager`
- `admin.py` – angepasster `UserAdmin` (Pflicht bei Custom User)
- `api/serializers.py` – `RegistrationSerializer`
- `api/views.py` – `RegistrationView`
- `api/urls.py` – Routen inkl. der simplejwt-Views
- `api/permissions.py` – leer (vorerst nicht nötig)
