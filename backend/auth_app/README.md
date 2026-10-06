# auth_app

## Kurzbeschreibung

Anmeldung am Programm: das Nutzermodell des Projekts (E-Mail statt Benutzername), die
Registrierung und die Anmeldung über JSON Web Tokens.

**Abgrenzung:** Hier geht es nur darum, **wer das Programm benutzen darf**. Die Verbindung zum
eBay-Konto und deren Tokens liegen in der `ebay_app`. Rollen und Rechte gibt es noch nicht.

## Aufgaben

- Nutzermodell des ganzen Projekts bereitstellen (`AUTH_USER_MODEL`)
- Neue Nutzer registrieren
- Anmelden, Token erneuern, abmelden

## Models

| Model | Felder | Hinweise |
|---|---|---|
| `User` | `email`, `first_name`, `password`, … (von Djangos `AbstractUser`) | `email` ist eindeutig und das Login-Feld, `username` entfällt; der Anzeigename steht in `first_name`; eigener `UserManager` für `createsuperuser` |

## Logik

- Anmelden, Erneuern und Abmelden sind die Standard-Views von `djangorestframework-simplejwt`.
- `RegistrationSerializer` prüft, dass beide Passwörter gleich sind und die E-Mail frei ist.
  Nach der Registrierung gibt es sofort ein Token-Paar – ein zweiter Login ist nicht nötig.
- Token-Laufzeiten (aus `core/settings.py`): Access 60 Minuten, Refresh 7 Tage. Beim Erneuern
  gibt es auch einen neuen Refresh-Token, der alte wird gesperrt.

**Bekannte Grenzen**
- **Die Registrierung ist offen:** Jeder, der die Adresse erreicht, kann ein Konto anlegen.
- **Jedes Konto darf alles:** Es gibt keine Rollen; alle anderen Endpoints prüfen nur, ob ein
  gültiger Token mitkommt.

Für den Betrieb auf dem eigenen Rechner genügt das. Bevor das Programm für andere erreichbar ist,
muss die Registrierung geschlossen werden.

## API-Übersicht

| Methode | Pfad | Zweck | Anmeldung nötig |
|---|---|---|---|
| POST | `/api/registration/` | Konto anlegen, liefert ein Token-Paar | nein |
| POST | `/api/login/` | anmelden, liefert ein Token-Paar | nein |
| POST | `/api/token/refresh/` | neuen Access-Token holen | nein (Refresh-Token im Body) |
| POST | `/api/logout/` | Refresh-Token sperren | nein (Refresh-Token im Body) |

## API im Detail

### `POST /api/registration/`

Alle vier Felder sind Pflicht.

```json
{"email": "eric@example.org", "fullname": "Eric Beispiel", "password": "…", "repeated_password": "…"}
```

Antwort `201`:

```json
{"refresh": "eyJhbGciOiJI…", "access": "eyJhbGciOiJI…", "email": "eric@example.org", "user_id": 7}
```

Fehler `400`, wenn die E-Mail schon vergeben ist:

```json
{"error": {"email": ["user with this email already exists."]}}
```

Stimmen die Passwörter nicht überein:

```json
{"error": {"non_field_errors": ["Die Passwörter stimmen nicht überein."]}}
```

### `POST /api/login/`

```json
{"email": "eric@example.org", "password": "…"}
```

Antwort `200`:

```json
{"refresh": "eyJhbGciOiJI…", "access": "eyJhbGciOiJI…"}
```

Fehler `401`:

```json
{"error": {"detail": "No active account found with the given credentials"}}
```

### `POST /api/token/refresh/`

```json
{"refresh": "eyJhbGciOiJI…"}
```

Antwort `200` – beide Tokens sind neu, der alte Refresh-Token gilt nicht mehr:

```json
{"access": "eyJhbGciOiJI…", "refresh": "eyJhbGciOiJI…"}
```

Fehler `401`, wenn der Refresh-Token abgelaufen oder gesperrt ist.

### `POST /api/logout/`

```json
{"refresh": "eyJhbGciOiJI…"}
```

Antwort `200` mit leerem Objekt `{}`. Der Refresh-Token ist danach gesperrt; der Access-Token
läuft von selbst ab.

### Geschützte Endpoints aufrufen

Jeder andere Endpoint erwartet den Header `Authorization: Bearer <access>`. Ohne ihn:

```json
{"error": {"detail": "Authentication credentials were not provided."}}
```

## Anwendung

```bash
curl -X POST http://127.0.0.1:8000/api/login/ -H "Content-Type: application/json" -d '{"email": "eric@example.org", "password": "…"}'
```

```bash
curl http://127.0.0.1:8000/api/products/ -H "Authorization: Bearer <access>"
```

Im Frontend: Startseite mit Anmeldung und Umschalter zur Registrierung. Das Token-Paar liegt im
`localStorage`; läuft der Access-Token ab, holt das Frontend einmal automatisch einen neuen.
Einen Admin-Zugang für `/admin/` legt `python manage.py createsuperuser` an.

## Verbindungen

- Über `AUTH_USER_MODEL` das Nutzermodell des **ganzen Projekts**.
- Alle geschützten Endpoints der anderen Apps prüfen die hier ausgestellten Tokens
  (`IsAuthenticated`).

## Dateien

| Datei | Inhalt |
|---|---|
| `models.py` | `User`, `UserManager` |
| `api/serializers.py` | `RegistrationSerializer` |
| `api/views.py` | `RegistrationView` |
| `api/urls.py` | Routen, inklusive der simplejwt-Views |
| `admin.py` | Nutzerverwaltung im Admin |
