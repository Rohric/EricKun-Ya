# ebay_app

Adapter **und** Zustandshalter für den Verkaufskanal eBay. Verbindet das Tool mit dem
eBay-Verkäuferkonto, richtet es ein und stellt Artikel aus `products_app` bei eBay ein.

> **Stand:** Verbindung (A), Einrichtung (B), Inserieren (C), Verkäufe/Versand (D) und die
> Oberfläche (E) sind gebaut. Immer erst **Sandbox**, dann Production.
> Echt gegen die Sandbox geprüft sind bisher die Kategorie-, Merkmal-, Zustands- und
> Versanddienst-Abfragen; alle Aufrufe im Namen des Verkäufers sind nur mit nachgestellten
> eBay-Antworten geprüft und warten auf den ersten echten Lauf.

## Aufgaben

- Mit dem eBay-Konto verbinden (OAuth 2.0 Authorization Code Grant) und die Verbindung halten
- Tokens **verschlüsselt** speichern, den Access-Token (2 h) automatisch per Refresh-Token
  (18 Monate) erneuern
- Business Policies (Versand, Rückgabe, Zahlung) anlegen bzw. aktualisieren
- Den Standard-Lagerort als eBay-Inventory-Location übertragen
- Artikel inserieren: eBay-Kategorie vorschlagen, Pflicht-Merkmale abfragen, Bilder bei eBay
  hosten, Inventory Item und Offer anlegen, veröffentlichen
- Inserate nach lokalen Änderungen synchronisieren, beenden und automatisch beenden, sobald
  ein Artikel ausverkauft oder archiviert ist
- eBay-Verkäufe als Bestellungen in `orders_app` anlegen, eBay-Stornos übernehmen
- Versand mit Dienstleister und Trackingnummer an eBay melden

## Models

- **`EbayAccount`** (Singleton): verschlüsselte `access_token` / `refresh_token` mit
  Ablaufzeiten, `connected_at`, `oauth_state` (+ Zeitstempel) für die Login-Prüfung,
  `fulfillment_policy_id`, `return_policy_id`, `payment_policy_id`, `orders_synced_at`.
  Berechnet: `is_connected`, `has_policies`.
- **`EbayLocation`**: OneToOne zu `logistics_app.Warehouse`, `merchant_location_key`,
  `last_synced`. Berechnet: `needs_resync` (Adresse nach der Übertragung geändert).
- **`EbayListing`**: OneToOne zu `products_app.Product`, `category_id`, `category_name`,
  `offer_id`, `listing_id`, `status` (Entwurf / Online / Beendet), `synced_quantity`,
  `last_synced`, `sync_error`. Berechnet: `has_unsynced_changes` (Artikel nach der letzten
  Übertragung geändert oder Menge weicht ab), `state` (Anzeige: Fehler und „geändert" gehen vor).
- **`EbayCategoryMapping`**: OneToOne zu `products_app.Category`, `ebay_category_id`,
  `ebay_category_name` – die zuletzt gewählte eBay-Kategorie je interner Kategorie
  (Merkliste statt gespiegeltem eBay-Kategoriebaum).
- **`EbayImage`**: OneToOne zu `products_app.ProductImage`, `eps_url`, `source_name`,
  `expires_at` – merkt sich die von eBay gehostete Bild-URL, damit jede Datei nur einmal
  hochgeladen wird.

## Services / Logik

- `client.py` – Basis-URLs je Umgebung (API, Media, Login, Webseite), Scopes, HTTP-Helper;
  eBay-/Netzwerkfehler → `EbayApiError` (mit eBays HTTP-Status in `http_status`)
- `crypto.py` – Fernet-Verschlüsselung der Tokens (`EBAY_TOKEN_KEY`)
- `services/oauth.py` – Consent-URL mit Zufalls-`state` (10 min gültig), eingefügte
  Rücksprung-URL prüfen, Code gegen Tokens tauschen, automatische Erneuerung, `call()` für
  alle Aufrufe im Namen des Verkäufers
- `services/account.py` – Opt-in zu Business Policies, Versanddienste über die Metadata API
  (je Code nur ein Eintrag), drei Policies anlegen oder aktualisieren (vorhandene mit gleichem
  Namen werden wiederverwendet)
- `services/locations.py` – Standard-Lagerort übertragen; nach einer Adressänderung mit
  neuem Key, weil eBay Adressen nicht ändern lässt
- `services/taxonomy.py` – Kategorie-Vorschläge aus dem Titel, Pflicht- und empfohlene
  Merkmale, erlaubte Zustände je Kategorie; alles 24 h im Cache
- `services/conditions.py` – `Product.Condition` → eBay-Zustand. Viele Kategorien kennen nur
  „Gebraucht"; dann wird darauf ausgewichen und unsere feinere Stufe als Zustandsnotiz mitgegeben
- `services/images.py` – Bilddateien über die Media API zu eBay hochladen (die Desktop-App hat
  keine öffentlichen URLs)
- `services/listings.py` – `publish` (Kategorie + Merkmale speichern, übertragen,
  veröffentlichen, Kategorie merken), `sync`, `withdraw`, `sync_all`, `end_if_unsellable`,
  `remove_item`, `requirements`. Ein vorhandenes Offer zur SKU wird übernommen statt ein
  zweites anzulegen; ob veröffentlicht werden muss, entscheidet eBays eigener Offer-Status
- `services/orders.py` – `import_orders` (Fulfillment API `getOrders` seit dem letzten Abruf,
  erster Lauf 90 Tage; neue bezahlte Bestellung → `Order` + Positionen + Bestand, bei eBay
  storniert → `cancel_order`), `report_shipment` (`createShippingFulfillment`), `CARRIERS`.
  Eine unbekannte SKU wird als Position ohne Artikel angelegt und im Ergebnis gemeldet
- `services/overview.py` – Status für die Checkliste im Frontend
- `signals.py` – Artikel ausverkauft/archiviert → Inserat beenden; Artikel gelöscht →
  Inventory Item bei eBay löschen. Läuft nach dem Commit, eBay-Fehler landen in `sync_error`
  und blockieren das lokale Speichern nicht
- Fehler: `EbayApiError` (502), `EbayNotConnected` (409), `EbayNotConfigured` (503)

**Warum die Rücksprung-URL eingefügt wird:** eBay akzeptiert als Rücksprung nur HTTPS und
kein `localhost`. Nach dem eBay-Login kopiert man die Adresse aus der Browserleiste in die
App – das funktioniert lokal und später in der Desktop-App.

**Synchronisation:** Änderungen gehen nicht automatisch zu eBay. Das Inserat wird als
„geändert" markiert und per Button übertragen. Einzige Automatik: Bestand 0 oder archiviert
beendet das Inserat.

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
| GET | `/api/ebay/categories/suggest/?q=` | eBay-Kategorien zu einem Titel vorschlagen |
| GET | `/api/ebay/categories/<id>/requirements/` | Merkmale und erlaubte Zustands-IDs einer Kategorie; `?product=<id>` ergänzt einen Zustands-Hinweis |
| GET | `/api/ebay/listings/` | Verkaufbare Artikel mit Inserat-Status (`?page=` optional) |
| POST | `/api/ebay/listings/<product_id>/publish/` | Body `category_id`, `category_name`, `aspects`: inserieren |
| POST | `/api/ebay/listings/<product_id>/sync/` | Aktuellen Stand übertragen; beendetes Inserat geht wieder online |
| POST | `/api/ebay/listings/<product_id>/withdraw/` | Inserat beenden |
| POST | `/api/ebay/listings/sync-all/` | Alle geänderten Inserate übertragen, liefert `synced` / `failed` |
| POST | `/api/ebay/orders/import/` | eBay-Verkäufe abholen, liefert `created` / `cancelled` / `unknown_skus` |
| POST | `/api/ebay/orders/<order_id>/ship/` | Body `carrier`, `tracking_number`: Versand an eBay melden |
| GET | `/api/ebay/carriers/` | Versanddienstleister für die Versandmeldung |

`aspects` hat die Form `{"Marke": ["Nintendo"], "Farbe": ["Schwarz"]}` und wird im
`Product.aspects` gespeichert.

## Verkauf simulieren (nur Sandbox)

Die Sandbox-Kasse legt oft keine Bestellung an. Damit sich der Ablauf nach einem Verkauf trotzdem
testen lässt, gibt es einen eigenen Befehl (aus `backend/`, venv aktiv):

```
python manage.py simulate_ebay_sale <SKU>                # 1 Stück verkaufen
python manage.py simulate_ebay_sale <SKU> --quantity 2   # mehrere Stück
python manage.py simulate_ebay_sale --cancel <Bestell-ID> # simulierte Bestellung wie ein eBay-Storno behandeln
```

- `services/simulation.py` baut eine Bestellung im Format von eBays `getOrders` (Bestellnummer
  `SIM-…`, Beispiel-Käufer) und gibt sie an `orders.import_payloads` – denselben Code, den der
  echte Abruf benutzt.
- Nach einem Teilverkauf überträgt der Befehl die Restmenge an eBay (echtes eBay senkt sie selbst);
  bei Menge 0 beendet das Signal das Inserat.
- Der Befehl bricht ab, wenn `EBAY_ENV` nicht `sandbox` ist, die SKU unbekannt ist oder der
  Bestand nicht reicht.
- Grenzen: Bei eBay entsteht keine Bestellung; „Versand melden" scheitert deshalb für simulierte
  Bestellungen. Ob eBays echtes Format der Dokumentation entspricht, zeigt erst ein echter Verkauf.

**Nicht enthalten:** Storno oder Erstattung **an** eBay senden. Eine eBay-Bestellung wird bei
eBay storniert; der nächste Abruf übernimmt das Storno und bucht den Bestand zurück.

## Verbindungen

- Kennt `logistics_app` (Lagerort), `products_app` (Artikel, Bilder, Kategorien) und
  `orders_app` (Bestellungen, Storno) – **nie umgekehrt** (einseitige Code-Abhängigkeit).
  Auf Artikel-Änderungen reagiert die App über Signals, `products_app` weiß nichts von eBay.
- Einstellungen aus `core/settings.py` (`EBAY_*` aus der `.env`).

## Dateien

- `models.py` – `EbayAccount`, `EbayLocation`, `EbayListing`, `EbayCategoryMapping`, `EbayImage`
- `client.py`, `crypto.py`, `exceptions.py`, `signals.py`
- `services/` – `oauth.py`, `account.py`, `locations.py`, `taxonomy.py`, `conditions.py`,
  `images.py`, `listings.py`, `orders.py`, `simulation.py`, `overview.py`
- `management/commands/simulate_ebay_sale.py` – Befehl zum Simulieren eines Verkaufs
- `api/serializers.py`, `api/views.py`, `api/urls.py`
- `admin.py` – Verbindung, Lagerort-Keys, Inserate, gehostete Bilder (Tokens werden nie angezeigt)
