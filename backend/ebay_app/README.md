# ebay_app

Adapter **und** Zustandshalter für den Verkaufskanal eBay. Verbindet das Tool mit dem
eBay-Verkäuferkonto, richtet es ein, stellt Artikel aus `products_app` bei eBay ein und holt
die Verkäufe zurück nach `orders_app`.

> **Stand:** Immer erst **Sandbox**, dann Production.
> **Echt gegen die Sandbox bestätigt:** Verbinden, Rückgabe-/Zahlungsvorlage, Versandprofile,
> Lagerort, Bild-Upload, Artikel, Angebot, Veröffentlichen, Synchronisieren, Löschen,
> Preisvorschlag, Gebühren-Vorschau, Preis-/Verkaufsabruf.
> **Nur mit nachgestellten eBay-Antworten geprüft:** Verkäufe abholen, eBay-Storno, Versand
> melden – die Sandbox-Kasse legt keine Bestellungen an (siehe „Verkauf simulieren").

## Aufgaben

- Mit dem eBay-Konto verbinden (OAuth 2.0 Authorization Code Grant) und die Verbindung halten
- Tokens **verschlüsselt** speichern, den Access-Token (2 h) automatisch per Refresh-Token
  (18 Monate) erneuern
- Vorlagen pflegen: mehrere **Versandprofile**, je eine Rückgabe- und Zahlungsvorlage
- Den Standard-Lagerort als eBay-Inventory-Location übertragen
- Artikel inserieren: eBay-Kategorie vorschlagen, Pflicht-Merkmale abfragen, Bilder bei eBay
  hosten, Artikel und Angebot anlegen, Gebühren vorab anzeigen, veröffentlichen
- Inserate synchronisieren, beenden und automatisch beenden, sobald ein Artikel ausverkauft
  oder archiviert ist
- Zurücklesen, welchen Preis eBay dem Käufer zeigt und wie viel eBay als verkauft zählt
- eBay-Verkäufe als Bestellungen anlegen (bezahlt oder mit offener Zahlung), Zahlungseingang
  und eBay-Stornos übernehmen, Versand an eBay melden

## Models

- **`EbayAccount`** (Singleton): verschlüsselte `access_token` / `refresh_token` mit
  Ablaufzeiten, `connected_at`, `oauth_state` (+ Zeitstempel), `return_policy_id`,
  `payment_policy_id`, `orders_synced_at`. Berechnet: `is_connected`, `has_policies`
  (Rückgabe + Zahlung + ein Standard-Versandprofil mit eBay-Vorlage).
- **`EbayLocation`**: OneToOne zu `logistics_app.Warehouse`, `merchant_location_key`,
  `last_synced`. Berechnet: `needs_resync`.
- **`EbayShippingProfile`**: `name` (eindeutig), `shipping_service`, `shipping_cost`,
  `handling_days`, `policy_id` (eBays Versandvorlage), `is_default`. Genau ein Profil ist Standard.
- **`EbayListing`**: OneToOne zu `products_app.Product`, `category_id`, `category_name`,
  `shipping_profile` (leer = Standard-Profil), `best_offer`, `offer_id`, `listing_id`, `status`
  (Entwurf / Online / Beendet), `synced_quantity`, `last_synced`, `sync_error`, dazu von eBay
  zurückgelesen: `ebay_price`, `sold_quantity`, `facts_synced_at`.
  Berechnet: `has_unsynced_changes`, `state` (Anzeige: Fehler und „geändert" gehen vor).
- **`EbayCategoryMapping`**: OneToOne zu `products_app.Category` – die zuletzt gewählte
  eBay-Kategorie je interner Kategorie (Merkliste statt gespiegeltem eBay-Kategoriebaum).
- **`EbayImage`**: OneToOne zu `products_app.ProductImage`, `eps_url`, `source_name`,
  `expires_at` – jede Bilddatei wird nur einmal zu eBay hochgeladen.

## Services / Logik

- `client.py` – Basis-URLs je Umgebung (API, Media, Login, Webseite), Scopes, HTTP-Helper;
  eBay-/Netzwerkfehler → `EbayApiError` (mit eBays HTTP-Status in `http_status`)
- `crypto.py` – Fernet-Verschlüsselung der Tokens (`EBAY_TOKEN_KEY`)
- `services/oauth.py` – Consent-URL, Rücksprung-URL prüfen, Code tauschen, automatische
  Erneuerung, `call()` für Aufrufe im Namen des Verkäufers, `get_app_token()` für öffentliche Daten
- `services/account.py` – Opt-in zu Business Policies, Versanddienste (je Code ein Eintrag),
  Rückgabe- und Zahlungsvorlage anlegen oder aktualisieren
- `services/shipping_profiles.py` – Versandprofile mit ihrer eBay-Vorlage anlegen, ändern,
  löschen (nicht das Standard-Profil, nicht solange ein Inserat es nutzt), Standard setzen
- `services/locations.py` – Standard-Lagerort übertragen; nach einer Adressänderung mit
  neuem Key, weil eBay Adressen nicht ändern lässt
- `services/taxonomy.py` – Kategorie-Vorschläge, Pflicht- und empfohlene Merkmale, erlaubte
  Zustände; 24 h im Cache
- `services/conditions.py` – `Product.Condition` → eBay-Zustand; viele Kategorien kennen nur
  „Gebraucht", dann steht unsere feinere Stufe als Zustandsnotiz im Inserat
- `services/images.py` – Bilddateien über die Media API zu eBay hochladen
- `services/listings.py` – `publish`, `preview` (Gebühren ohne Veröffentlichen), `sync`,
  `withdraw`, `sync_all`, `end_if_unsellable`, `remove_item`, `products_in_scope`,
  `channel_states`. Ein vorhandenes Angebot zur SKU wird übernommen; ob veröffentlicht werden
  muss, entscheidet eBays eigener Angebots-Status. eBays Ablehnungsgrund bleibt am Inserat stehen.
- `services/facts.py` – liest nach jeder Übertragung und auf Knopfdruck den Käuferpreis
  (Browse API) und eBays Verkaufszahl; ein Fehler dabei bricht nichts ab
- `services/orders.py` – `import_orders` / `import_payloads` (neu → Bestellung, Bestand sofort
  gebucht; bezahlt → Zahlungsstatus; storniert → `cancel_order`), `report_shipment`
  (nur bezahlte, nicht stornierte eBay-Bestellungen), `CARRIERS`
- `services/simulation.py` – simulierte Verkäufe, Zahlungen und Stornos für die Sandbox
- `services/overview.py` – Status für Checkliste und Kennzahlen
- `signals.py` – Artikel ausverkauft/archiviert → Inserat beenden; Artikel gelöscht →
  Artikel bei eBay löschen. Läuft nach dem Commit; Fehler landen in `sync_error`
- Fehler: `EbayApiError` (502), `EbayNotConnected` (409), `EbayNotConfigured` (503)

**Warum die Rücksprung-URL eingefügt wird:** eBay akzeptiert als Rücksprung nur HTTPS und
kein `localhost`. Nach dem eBay-Login kopiert man die Adresse aus der Browserleiste in die App.
`EBAY_RUNAME` in der `.env` muss der von eBay erzeugte RuName sein, nicht der Anzeigename.

**Synchronisation:** Änderungen gehen nicht automatisch zu eBay. Das Inserat wird als
„geändert" markiert und per Button übertragen. Einzige Automatik: Bestand 0 oder archiviert
beendet das Inserat.

## Verkauf simulieren (nur Sandbox)

Die Sandbox-Kasse legt oft keine Bestellung an. Aus `backend/`, venv aktiv:

```
python manage.py simulate_ebay_sale <SKU>                 # 1 Stück, bezahlt
python manage.py simulate_ebay_sale <SKU> --quantity 2    # mehrere Stück
python manage.py simulate_ebay_sale <SKU> --unpaid        # Zahlung offen
python manage.py simulate_ebay_sale --pay <Bestell-ID>    # Zahlung einer simulierten Bestellung melden
python manage.py simulate_ebay_sale --cancel <Bestell-ID> # wie ein eBay-Storno behandeln
```

- Die Bestellung (`SIM-…`) läuft durch `orders.import_payloads` – denselben Code wie der echte Abruf.
- Nach einem Teilverkauf überträgt der Befehl die Restmenge an eBay; bei Menge 0 beendet das
  Signal das Inserat.
- „Versand melden" markiert simulierte Bestellungen nur lokal als verschickt, weil eBay sie
  nicht kennt (`orders.is_simulated`).
- Der Befehl bricht ab, wenn `EBAY_ENV` nicht `sandbox` ist.
- Grenze: Ob eBays echtes Bestellformat der Dokumentation entspricht, zeigt erst ein echter Verkauf.

## API-Endpoints

| Methode | Pfad | Zweck |
|---|---|---|
| GET | `/api/ebay/status/` | Umgebung, Verbindung, Einrichtung, „bereit", `orders_synced_at`, Inserat-Zähler |
| POST | `/api/ebay/connect/start/` | Neue Anmeldung starten, liefert `consent_url` |
| POST | `/api/ebay/connect/finish/` | Body `redirect_url`: Code tauschen, Tokens speichern |
| POST | `/api/ebay/disconnect/` | Gespeicherte Tokens löschen |
| GET | `/api/ebay/shipping-services/` | Inländische Versanddienste des Marktplatzes |
| GET / POST | `/api/ebay/shipping-profiles/` | Versandprofile (mit `listing_count`) / neues Profil samt eBay-Vorlage |
| GET / PUT / PATCH / DELETE | `/api/ebay/shipping-profiles/<id>/` | Profil lesen, ändern, löschen |
| POST | `/api/ebay/shipping-profiles/<id>/default/` | Als Standard festlegen |
| GET / PUT | `/api/ebay/policies/` | Rückgabe-Werte lesen / Rückgabe- und Zahlungsvorlage speichern |
| POST | `/api/ebay/location/sync/` | Standard-Lagerort an eBay übertragen |
| GET | `/api/ebay/categories/suggest/?q=` | eBay-Kategorien zu einem Titel vorschlagen |
| GET | `/api/ebay/categories/<id>/requirements/` | Merkmale und erlaubte Zustands-IDs; `?product=<id>` ergänzt einen Zustands-Hinweis |
| GET | `/api/ebay/listings/?scope=` | Artikel mit Inserat: `all` (verkaufbare, Default), `listed`, `unlisted` |
| GET | `/api/ebay/listing-states/` | `{Artikel-ID: [Kanal-Einträge]}` für die Spalte „Kanäle" der Artikelseite |
| POST | `/api/ebay/listings/<product_id>/publish/` | Body `category_id`, `category_name`, `aspects`, `shipping_profile`, `best_offer` |
| POST | `/api/ebay/listings/<product_id>/preview/` | Gleicher Body; überträgt unveröffentlicht und liefert `fees`, `total` |
| POST | `/api/ebay/listings/<product_id>/sync/` | Aktuellen Stand übertragen; beendetes Inserat geht wieder online |
| POST | `/api/ebay/listings/<product_id>/withdraw/` | Inserat beenden |
| POST | `/api/ebay/listings/sync-all/` | Alle geänderten Inserate übertragen (`synced` / `failed`) |
| POST | `/api/ebay/listings/refresh/` | Käuferpreis und Verkaufszahl aller Online-Inserate neu lesen |
| POST | `/api/ebay/orders/import/` | Verkäufe abholen (`created` / `paid` / `cancelled` / `unknown_skus`) |
| POST | `/api/ebay/orders/<order_id>/ship/` | Body `carrier`, `tracking_number`: Versand melden |
| GET | `/api/ebay/carriers/` | Versanddienstleister für die Versandmeldung |

`aspects` hat die Form `{"Marke": ["Nintendo"], "Farbe": ["Schwarz"]}` und wird im
`Product.aspects` gespeichert.

**Nicht enthalten:** Storno oder Erstattung **an** eBay senden (eBay-Bestellungen werden bei
eBay storniert, der nächste Abruf übernimmt das), echte eBay-Gebühren, Käufernachrichten.

## Verbindungen

- Kennt `logistics_app` (Lagerort), `products_app` (Artikel, Bilder, Kategorien) und
  `orders_app` (Bestellungen, Storno) – **nie umgekehrt** (einseitige Code-Abhängigkeit).
  Auf Artikel-Änderungen reagiert die App über Signals, `products_app` weiß nichts von eBay.
- Einstellungen aus `core/settings.py` (`EBAY_*` aus der `.env`).

## Dateien

- `models.py` – `EbayAccount`, `EbayLocation`, `EbayShippingProfile`, `EbayListing`,
  `EbayCategoryMapping`, `EbayImage`
- `client.py`, `crypto.py`, `exceptions.py`, `signals.py`
- `services/` – `oauth.py`, `account.py`, `shipping_profiles.py`, `locations.py`, `taxonomy.py`,
  `conditions.py`, `images.py`, `listings.py`, `facts.py`, `orders.py`, `simulation.py`, `overview.py`
- `management/commands/simulate_ebay_sale.py` – Befehl zum Simulieren von Verkäufen
- `api/serializers.py`, `api/views.py`, `api/urls.py`
- `admin.py` – Verbindung, Lagerort, Versandprofile, Inserate, Merkliste, gehostete Bilder
