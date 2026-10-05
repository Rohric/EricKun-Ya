# ebay_app

Adapter **und** Zustandshalter für den Verkaufskanal eBay. Verbindet das Tool mit dem
eBay-Verkäuferkonto und richtet es zum Inserieren ein.

> **Stand:** Verbindung (A) und Einrichtung (B) sind fertig. Inserieren (C), Verkäufe holen (D)
> und die Inserat-Übersicht (E) folgen. Immer erst **Sandbox**, dann Production.

## Aufgaben

- Mit dem eBay-Konto verbinden (OAuth 2.0 Authorization Code Grant) und die Verbindung halten
- Tokens **verschlüsselt** speichern, den Access-Token (2 h) automatisch per Refresh-Token
  (18 Monate) erneuern
- Business Policies (Versand, Rückgabe, Zahlung) anlegen bzw. aktualisieren
- Den Standard-Lagerort als eBay-Inventory-Location übertragen

## Models

- **`EbayAccount`** (Singleton): verschlüsselte `access_token` / `refresh_token` mit
  Ablaufzeiten, `connected_at`, `oauth_state` (+ Zeitstempel) für die Login-Prüfung,
  `fulfillment_policy_id`, `return_policy_id`, `payment_policy_id`.
  Berechnet: `is_connected`, `has_policies`.
- **`EbayLocation`**: OneToOne zu `logistics_app.Warehouse`, `merchant_location_key`,
  `last_synced`. Berechnet: `needs_resync` (Adresse nach der Übertragung geändert).

## Services / Logik

- `client.py` – Basis-URLs je Umgebung, Scopes, HTTP-Helper; eBay-/Netzwerkfehler →
  `EbayApiError`
- `crypto.py` – Fernet-Verschlüsselung der Tokens (`EBAY_TOKEN_KEY`)
- `services/oauth.py` – Consent-URL mit Zufalls-`state` (10 min gültig), eingefügte
  Rücksprung-URL prüfen, Code gegen Tokens tauschen, automatische Erneuerung, `call()` für
  alle Aufrufe im Namen des Verkäufers
- `services/account.py` – Opt-in zu Business Policies, Versanddienste über die Metadata API,
  drei Policies anlegen oder aktualisieren (vorhandene mit gleichem Namen werden
  wiederverwendet)
- `services/locations.py` – Standard-Lagerort übertragen; nach einer Adressänderung mit
  neuem Key, weil eBay Adressen nicht ändern lässt
- `services/overview.py` – Status für die Checkliste im Frontend
- Fehler: `EbayApiError` (502), `EbayNotConnected` (409), `EbayNotConfigured` (503)

**Warum die Rücksprung-URL eingefügt wird:** eBay akzeptiert als Rücksprung nur HTTPS und
kein `localhost`. Nach dem eBay-Login kopiert man die Adresse aus der Browserleiste in die
App – das funktioniert lokal und später in der Desktop-App.

## API-Endpoints

| Methode | Pfad | Zweck |
|---|---|---|
| GET | `/api/ebay/status/` | Umgebung, fehlende Einstellungen, Verbindung, Einrichtung, „bereit" |
| POST | `/api/ebay/connect/start/` | Neue Anmeldung starten, liefert `consent_url` |
| POST | `/api/ebay/connect/finish/` | Body `redirect_url`: Code tauschen, Tokens speichern |
| POST | `/api/ebay/disconnect/` | Gespeicherte Tokens löschen |
| GET | `/api/ebay/shipping-services/` | Inländische Versanddienste des Marktplatzes |
| GET / PUT | `/api/ebay/policies/` | Policy-Werte lesen / alle drei Policies speichern |
| POST | `/api/ebay/location/sync/` | Standard-Lagerort an eBay übertragen |

## Verbindungen

- Kennt `logistics_app` (Lagerort) und später `products_app` / `orders_app` –
  **nie umgekehrt** (einseitige Code-Abhängigkeit).
- Einstellungen aus `core/settings.py` (`EBAY_*` aus der `.env`).

## Dateien

- `models.py` – `EbayAccount`, `EbayLocation`
- `client.py`, `crypto.py`, `exceptions.py`
- `services/` – `oauth.py`, `account.py`, `locations.py`, `overview.py`
- `api/serializers.py`, `api/views.py`, `api/urls.py`
- `admin.py` – Verbindung und Lagerort-Keys (Tokens werden nie angezeigt)
