# auth_app

App-Login und Registrierung. Stellt das **Custom User Model** des Projekts bereit
(E-Mail statt Username als Login) und die JWT-basierte Authentifizierung.

> Abgrenzung: Hier lebt **nur der App-Login** (wer darf das Tool nutzen). Die
> eBay-OAuth-Tokens (Zugang zu einem Fremddienst) gehören später in `ebay_app`, **nicht**
> hierher.

## Aufgabe

- Custom User als projektweites `AUTH_USER_MODEL`
- Registrierung neuer Nutzer
- Login / Token-Refresh / Logout über JSON Web Tokens (`djangorestframework-simplejwt`)

## Model

- **`User`** (`AbstractUser`): `email` ist unique und `USERNAME_FIELD`, `username` entfällt,
  `REQUIRED_FIELDS = []`. Eigener `UserManager` (`create_user`/`create_superuser` per E-Mail).
  Der Anzeigename wird in `first_name` gespeichert.

## Endpoints

| Methode | Pfad | Auth | Zweck |
|---|---|---|---|
| POST | `/api/registration/` | – | Nutzer anlegen, gibt access + refresh Token zurück |
| POST | `/api/login/` | – | Login mit `email` + `password`, gibt Token-Paar zurück |
| POST | `/api/token/refresh/` | – | Access-Token per Refresh-Token erneuern |
| POST | `/api/logout/` | ✔ | Refresh-Token auf die Blacklist setzen |

`login`, `token/refresh` und `logout` sind die Standard-Views von simplejwt
(`TokenObtainPairView`, `TokenRefreshView`, `TokenBlacklistView`).

## Verbindungen

- Wird über `AUTH_USER_MODEL` vom **gesamten Projekt** als Nutzermodell verwendet.
- Alle geschützten Endpoints der anderen Apps prüfen Tokens, die hier ausgestellt werden.

## Dateien

- `models.py` – `User`, `UserManager`
- `admin.py` – angepasster `UserAdmin` (Pflicht bei Custom User)
- `api/serializers.py` – `RegistrationSerializer`
- `api/views.py` – `RegistrationView`
- `api/urls.py` – Routen inkl. der simplejwt-Views
