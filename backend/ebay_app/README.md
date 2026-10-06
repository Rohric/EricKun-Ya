# ebay_app

## Kurzbeschreibung

Der Verkaufskanal eBay: verbindet das Programm mit dem Verkäuferkonto, richtet es ein, stellt
Artikel aus `products_app` ein, gleicht vorhandene Inserate ab und holt Verkäufe nach `orders_app`.

**Abgrenzung:** Artikel, Bestand und Bestellungen gehören dem Kern – diese App hält nur fest, was
bei eBay dazu existiert. Sie kennt `products_app`, `orders_app` und `logistics_app`, nie umgekehrt.
Nicht enthalten: Käufernachrichten, Storno oder Erstattung **an** eBay, echte eBay-Gebühren,
Auktionen, Inserate mit Varianten.

**Stand der Prüfung**

| Echt gegen die Sandbox bestätigt | Nur mit nachgestellten eBay-Antworten geprüft |
|---|---|
| Verbinden, Rückgabe- und Zahlungsvorlage, Versandprofile, Lagerort, Bild-Upload, Inserieren, Synchronisieren, Löschen, Preisvorschlag, Gebühren-Vorschau, Preis- und Verkaufsabruf | Verkäufe abholen, eBay-Storno, Versand melden – die Sandbox-Kasse legt keine Bestellungen an |
| Abgleich vorhandener Inserate, Artikel aus Inseraten anlegen (mit Bildern und Vorlagen) | Ablehnung einer Umwandlung durch eBay |
| Altes Inserat: finden, Artikelnummer setzen und zurücknehmen, umwandeln, danach synchronisieren | Auktionen und Varianten als „nicht unterstützt" erkennen |

## Aufgaben

- Mit dem eBay-Konto verbinden (OAuth 2.0) und die Verbindung halten; Tokens verschlüsselt speichern
- Vorlagen pflegen: mehrere Versandprofile, je eine Rückgabe- und Zahlungsvorlage
- Den Standard-Lagerort als Artikelstandort übertragen
- Inserieren: Kategorie vorschlagen, Merkmale abfragen, Bilder bei eBay hosten, Gebühren vorab zeigen
- Synchronisieren, beenden und automatisch beenden, wenn ein Artikel ausverkauft oder archiviert ist
- **Abgleichen:** Inserate, die schon bei eBay stehen, holen – auch solche, die nicht über die API
  angelegt wurden
- **Zuordnen:** ein Inserat mit einem Artikel verknüpfen, einen Artikel daraus anlegen oder es ignorieren
- Verkäufe als Bestellungen anlegen, Zahlungseingänge und eBay-Stornos übernehmen, Versand melden

## Models

| Model | Felder | Hinweise |
|---|---|---|
| `EbayAccount` | `access_token`, `refresh_token` (verschlüsselt), Ablaufzeiten, `connected_at`, `oauth_state`, `return_policy_id`, `payment_policy_id`, `orders_synced_at` | eine Zeile; berechnet: `is_connected`, `has_policies` |
| `EbayLocation` | `warehouse`, `merchant_location_key`, `last_synced` | OneToOne zu `logistics_app.Warehouse`; berechnet: `needs_resync` |
| `EbayShippingProfile` | `name`, `shipping_service`, `shipping_cost`, `handling_days`, `policy_id`, `is_default` | steht für eine Versandvorlage bei eBay; genau ein Profil ist Standard |
| `EbayListing` | siehe unten | ein Inserat bei eBay |
| `EbayCategoryMapping` | `category`, `ebay_category_id`, `ebay_category_name` | merkt sich je interner Kategorie die zuletzt gewählte eBay-Kategorie |
| `EbayImage` | `image`, `eps_url`, `source_name`, `expires_at` | Adresse eines bei eBay gehosteten Bildes, damit jede Datei nur einmal hochgeladen wird |

**`EbayListing` – ein Inserat steht für sich und gehört zu höchstens einem Artikel**

| Feld | Bedeutung |
|---|---|
| `product` | der Artikel; **leer** bei einem Inserat, das noch nicht zugeordnet ist |
| `sku` | die Artikelnummer, unter der eBay das Inserat führt. Unsere bei Inseraten, die wir anlegen oder umwandeln – eine fremde, wo eBay einen bestehenden Eintrag nicht umbenennen lässt |
| `offer_id`, `listing_id` | eBays Angebots- und Inseratsnummer |
| `status` | `draft`, `online`, `ended` |
| `category_id`, `category_name`, `shipping_profile`, `best_offer` | Einstellungen des Inserats (`shipping_profile` leer = Standard-Profil) |
| `title`, `price`, `synced_quantity`, `image_url` | was eBay gerade hält; geschrieben nach jeder Übertragung und beim Abgleich |
| `last_synced`, `sync_error` | letzte Übertragung und eBays letzter Ablehnungsgrund |
| `needs_migration` | Inserat wurde nicht über die API angelegt und ist noch nicht umgewandelt |
| `supported` | `false` bei Auktionen und Inseraten mit Varianten |
| `ignored` | in der Zuordnung ausgeblendet |
| `ebay_price`, `sold_quantity`, `facts_synced_at` | zurückgelesen: Preis, den eBay dem Käufer zeigt, und eBays Verkaufszahl |

Berechnet: `has_unsynced_changes` (Artikel nach der letzten Übertragung geändert, oder Menge oder
Preis weichen von dem ab, was eBay hält) und `state` für die Anzeige: `ignored` → `unassigned` →
`error` → `changed` → sonst der `status`.

## Logik

**Grundsätze**
- Änderungen gehen **nicht automatisch** zu eBay. Das Inserat steht auf „Geändert" und wird per
  Knopfdruck übertragen. Einzige Automatik: Bestand 0 oder „archiviert" beendet das Inserat.
- Alle Aufrufe an eBay verwenden `listing.sku`, nicht die Artikelnummer des Artikels – so
  funktionieren auch übernommene Inserate mit fremder Nummer.
- Lehnt eBay etwas ab, bleibt der Grund am Inserat stehen (`sync_error`).

**Dienste (`services/`)**

| Datei | Aufgabe |
|---|---|
| `oauth.py` | Anmelde-Adresse erzeugen, Rücksprung prüfen, Code tauschen, Token automatisch erneuern; `call()` für REST, `trading_call()` für die XML-Trading-API |
| `account.py` | Teilnahme an eBays Geschäftsbedingungen, Versanddienste, Rückgabe- und Zahlungsvorlage |
| `shipping_profiles.py` | Versandprofile samt eBay-Vorlage anlegen, ändern, löschen, Standard setzen; `adopt()` übernimmt eine Vorlage, die schon bei eBay existiert |
| `locations.py` | Standard-Lagerort übertragen; nach einer Adressänderung mit neuem Schlüssel, weil eBay Adressen nicht ändern lässt |
| `taxonomy.py` | Kategorie-Vorschläge, Pflicht- und empfohlene Merkmale, erlaubte Zustände (24 Stunden im Cache) |
| `conditions.py` | unser Zustand ↔ eBay-Zustand. Viele Kategorien kennen nur „Gebraucht", dann steht unsere feinere Stufe als Notiz im Inserat – und wird bei einer Übernahme von dort zurückgelesen |
| `images.py` | Bilddateien zu eBay hochladen |
| `listings.py` | `publish`, `preview`, `sync`, `withdraw`, `sync_all`, `end_if_unsellable`, `remove_item`, `channel_states` |
| `facts.py` | Käuferpreis und Verkaufszahl von eBay zurücklesen |
| `snapshots.py` | liest, was eBay zu einer Artikelnummer hält, und schreibt es auf die Inseratszeile |
| `legacy.py` | Inserate, die nicht über die API angelegt wurden: auflisten, Artikelnummer setzen, umwandeln, Vorlagen lesen |
| `pull.py` | `pull_listings()` – der Abgleich |
| `assignment.py` | `suggest`, `link`, `create_product`, `create_all`, `ignore`, `unlink` |
| `orders.py` | Verkäufe importieren, Versand melden |
| `simulation.py` | Verkäufe, Zahlungen und Stornos für die Sandbox simulieren |
| `overview.py` | Status für Checkliste und Kennzahlen |

**Der Abgleich (`pull.pull_listings`)** ändert nichts bei eBay.
1. Alle Artikel und Angebote aus eBays Inventory API: Zu jedem, der **online** ist, wird eine
   Inseratszeile angelegt oder aufgefrischt. Ein bekanntes Inserat, das bei eBay nicht mehr läuft,
   wird „beendet".
2. Alle laufenden Inserate aus der Trading API, die Schritt 1 nicht kennt: Das sind Inserate, die
   auf der eBay-Seite oder mit einem anderen Werkzeug angelegt wurden. Sie werden mit
   `needs_migration` gespeichert.
3. Inserate ohne Artikel, deren Nummer **exakt** der Nummer eines freien Artikels entspricht,
   werden verknüpft. Alte Inserate (Schritt 2) werden nie automatisch verknüpft, weil das eine
   Änderung bei eBay auslöst.

**Die Zuordnung (`assignment`)**
- `link(listing, product)` – verknüpft. Übernimmt die Versandvorlage des Inserats als Profil und
  ergänzt am Artikel, was ihm fehlt (Merkmale, Beschreibung); seine eigenen Daten bleiben. Weichen
  Preis oder Menge ab, steht das Inserat danach auf „Geändert".
- `create_product(listing)` – legt einen Artikel mit neuer interner Nummer an: Titel,
  Beschreibung, Merkmale, Zustand, Preis und Menge von eBay, Bilder heruntergeladen,
  **Einkaufspreis 0**. Rückgabe- und Zahlungsvorlage werden übernommen, falls noch keine
  eingerichtet ist.
- **Altes Inserat** (in beiden Fällen): Erst schreibt das Programm unsere Artikelnummer ans Inserat
  (`ReviseFixedPriceItem`), dann wandelt eBay es um (`bulk_migrate_listing`). Lehnt eBay die
  Umwandlung ab, bekommt das Inserat seine alte Nummer zurück, bleibt unzugeordnet und zeigt eBays
  Grund; ein dafür angelegter Artikel wird wieder entfernt.
- `unlink(product)` – löst die Verknüpfung, ohne bei eBay etwas zu ändern. Ein laufendes Inserat
  erscheint wieder in der Zuordnung, ein beendetes wird vergessen.
- Ein Artikel mit laufendem Inserat kann kein zweites bekommen (Regel: je Portal ein Inserat).

**Was eBay für die Umwandlung verlangt:** Festpreis, Versand-, Rückgabe- und Zahlungsvorlage am
Inserat, Sofortzahlung, Standort mit PLZ oder Ort. **Danach lässt sich das Inserat nur noch über
die API ändern, nicht mehr auf der eBay-Seite.**

**Verkäufe (`orders`)** – `import_orders` holt geänderte Bestellungen seit dem letzten Abruf (beim
ersten Mal 90 Tage). Neue werden angelegt und der Bestand sofort gebucht; ein Zahlungseingang
setzt den Zahlungsstatus; ein eBay-Storno storniert und bucht zurück. Der Artikel einer Position
wird über die Nummer des Inserats gefunden, bei alten Inseraten über die Inseratsnummer.
Verkäufe, die zu keinem Artikel passen, werden ohne Artikel gespeichert und als `unknown_skus`
gemeldet – deshalb erst zuordnen, dann Verkäufe abholen.

**Signals** – Artikel ausverkauft oder archiviert → Inserat beenden. Artikel gelöscht → Artikel
bei eBay löschen (unter der Nummer, die eBay kennt). Beides läuft nach dem Speichern; Fehler
landen in `sync_error`.

**Fehler** – `EbayApiError` (502), `EbayNotConnected` (409), `EbayNotConfigured` (503).

## API-Übersicht

Alle Endpoints verlangen einen angemeldeten Nutzer und beginnen mit `/api/ebay/`.

| Methode | Pfad | Zweck |
|---|---|---|
| **Verbindung** | | |
| GET | `status/` | Umgebung, Verbindung, Checkliste, Zähler |
| POST | `connect/start/` | Anmeldung starten |
| POST | `connect/finish/` | Anmeldung abschließen |
| POST | `disconnect/` | gespeicherte Tokens löschen |
| **Vorlagen** | | |
| GET | `shipping-services/` | Versanddienste des Marktplatzes |
| GET, POST | `shipping-profiles/` | Versandprofile auflisten, anlegen |
| GET, PUT, PATCH, DELETE | `shipping-profiles/<id>/` | einzelnes Profil |
| POST | `shipping-profiles/<id>/default/` | als Standard festlegen |
| GET, PUT | `policies/` | Rückgabe- und Zahlungsvorlage |
| POST | `location/sync/` | Lagerort übertragen |
| **Kategorien** | | |
| GET | `categories/suggest/` | eBay-Kategorien zu einem Titel |
| GET | `categories/<category_id>/requirements/` | Merkmale und erlaubte Zustände |
| **Inserate** | | |
| GET | `listings/` | Artikel mit ihrem Inserat |
| GET | `listing-states/` | je Artikel, wo er inseriert ist |
| POST | `listings/<product_id>/preview/` | Gebühren-Vorschau |
| POST | `listings/<product_id>/publish/` | inserieren |
| POST | `listings/<product_id>/sync/` | aktuellen Stand übertragen |
| POST | `listings/<product_id>/withdraw/` | beenden |
| POST | `listings/<product_id>/unlink/` | Verknüpfung lösen |
| POST | `listings/sync-all/` | alle geänderten übertragen |
| POST | `listings/refresh/` | Käuferpreis und Verkaufszahl neu lesen |
| **Abgleich und Zuordnung** | | |
| POST | `listings/pull/` | Inserate von eBay holen |
| GET | `unassigned/` | Inserate ohne Artikel |
| POST | `unassigned/<id>/link/` | mit einem Artikel verknüpfen |
| POST | `unassigned/<id>/create-product/` | Artikel aus dem Inserat anlegen |
| POST | `unassigned/create-products/` | für alle offenen Inserate Artikel anlegen |
| POST | `unassigned/<id>/ignore/` | ausblenden oder wieder zeigen |
| **Verkäufe** | | |
| POST | `orders/import/` | Verkäufe abholen |
| POST | `orders/<order_id>/ship/` | Versand melden |
| GET | `carriers/` | Versanddienstleister für die Versandmeldung |

## API im Detail

Fehler, die überall vorkommen können: `409`, wenn nicht verbunden; `503`, wenn eBay-Werte in der
`.env` fehlen; `502` mit eBays eigener Meldung, wenn eBay ablehnt (Beispiele in der
[core-README](../core/README.md#fehlerformat-aller-endpoints)).

### Verbindung

#### `GET /api/ebay/status/`

```json
{
  "environment": "sandbox",
  "missing_settings": [],
  "connected": true,
  "refresh_expires_at": "2028-04-05 19:21:15.069060+00:00",
  "policies_ready": true,
  "location": {"key": "warehouse-3-20261006072220", "warehouse": "Lager (Musterstadt)", "last_synced": "2026-10-06 07:22:21.569586+00:00", "needs_resync": false},
  "ready": true,
  "orders_synced_at": "2026-10-06 10:46:39.460072+00:00",
  "listings": {"online": 3, "changed": 0, "ended": 1, "draft": 0, "error": 0, "unassigned": 0}
}
```

`ready` ist `true`, wenn verbunden, alle Vorlagen vorhanden und der Lagerort aktuell übertragen
ist. `missing_settings` nennt fehlende `.env`-Werte, `location` ist `null`, solange kein Lagerort
übertragen wurde.

#### `POST /api/ebay/connect/start/`

Kein Body. Antwort `200`:

```json
{"consent_url": "https://auth.sandbox.ebay.com/oauth2/authorize?client_id=…&redirect_uri=…&response_type=code&scope=…&state=…"}
```

Diese Adresse im Browser öffnen, mit dem Verkäuferkonto anmelden und zustimmen.

#### `POST /api/ebay/connect/finish/`

`redirect_url` ist die komplette Adresse, auf der eBay nach der Zustimmung landet.

```json
{"redirect_url": "https://…?code=v%5E1.1%23…&state=…&expires_in=299"}
```

Antwort `200`: der Status wie oben, jetzt mit `connected: true`. Fehler `400`:

```json
{"error": ["In der Adresse steht kein eBay-Code. Bitte die komplette Adresse aus der Browserleiste einfügen."]}
```

Nach mehr als 10 Minuten oder mit der Adresse einer anderen Anmeldung: „Die Anmeldung ist
abgelaufen oder passt nicht. Bitte erneut „Mit eBay verbinden" klicken."

#### `POST /api/ebay/disconnect/`

Kein Body. Antwort `200`: der Status mit `connected: false`, `ready: false`. Vorlagen und Inserate
bleiben gespeichert.

### Vorlagen

#### `GET /api/ebay/shipping-services/`

```json
[
  {"code": "DE_DeutschePostBrief", "name": "Deutsche Post Brief"},
  {"code": "DE_DPBuecherWarensendung", "name": "Deutsche Post Warensendung"},
  {"code": "DE_Einschreiben", "name": "Einschreiben"}
]
```

(gekürzt – die Sandbox liefert 49 Dienste)

#### `GET /api/ebay/shipping-profiles/` · `POST /api/ebay/shipping-profiles/`

```json
[
  {"id": 1, "name": "Standard", "shipping_service": "DE_DeutschePostBrief", "shipping_cost": "0.00", "handling_days": 2, "is_default": true, "policy_id": "6256602000", "listing_count": 4},
  {"id": 2, "name": "Päckchen", "shipping_service": "DE_DHLPackchen", "shipping_cost": "3.99", "handling_days": 2, "is_default": false, "policy_id": "6256639000", "listing_count": 0}
]
```

Anlegen – alle vier Felder sind Pflicht; `shipping_service` ist ein `code` aus
`shipping-services/`, `handling_days` einer von 1, 2, 3, 4, 5, 10:

```json
{"name": "Paket versichert", "shipping_service": "DE_DHLPaket", "shipping_cost": "5.49", "handling_days": 2}
```

Antwort `201` – die Vorlage ist bei eBay angelegt, `policy_id` ist eBays Nummer:

```json
{"id": 3, "name": "Paket versichert", "shipping_service": "DE_DHLPaket", "shipping_cost": "5.49", "handling_days": 2, "is_default": false, "policy_id": "6256700000", "listing_count": 0}
```

#### `GET|PUT|PATCH|DELETE /api/ebay/shipping-profiles/<id>/`

Ändern überträgt die Änderung an eBays Vorlage. `DELETE` antwortet mit `204` und löscht auch die
Vorlage bei eBay. Fehler `400`:

```json
{"error": ["Das Standard-Profil kann nicht gelöscht werden. Bitte zuerst ein anderes als Standard festlegen."]}
```

oder „Dieses Versandprofil wird noch von 2 Inserat(en) verwendet."

#### `POST /api/ebay/shipping-profiles/<id>/default/`

Kein Body. Antwort `200`: das Profil mit `is_default: true`.

#### `GET /api/ebay/policies/` · `PUT /api/ebay/policies/`

```json
{"return_days": 14, "return_cost_payer": "SELLER", "saved": true}
```

`PUT` legt Rückgabe- und Zahlungsvorlage bei eBay an oder aktualisiert sie. `return_days`: 14, 30
oder 60; `return_cost_payer`: `BUYER` oder `SELLER`. Die Zahlungsvorlage hat keine Optionen
(Zahlungsabwicklung durch eBay, Sofortzahlung).

```json
{"return_days": 30, "return_cost_payer": "BUYER"}
```

Antwort `200`: der Status wie bei `status/`.

#### `POST /api/ebay/location/sync/`

Kein Body. Überträgt den Standard-Lagerort. Antwort `200`: der Status. Fehler `400`: „Es gibt noch
keinen Lagerort. Bitte zuerst im Reiter „Lager" anlegen."

### Kategorien

#### `GET /api/ebay/categories/suggest/?q=Poster`

```json
[
  {"id": "52324", "name": "Poster", "path": "Musik › Fanartikel & Merchandise › Poster"},
  {"id": "41511", "name": "Bilder & Drucke", "path": "Möbel & Wohnen › Dekoration › Bilder & Drucke"},
  {"id": "28009", "name": "Kunstplakate", "path": "Antiquitäten & Kunst › Kunst › Kunstplakate"}
]
```

Fehler `400` ohne Suchbegriff:

```json
{"error": ["Bitte einen Suchbegriff angeben (?q=)."]}
```

#### `GET /api/ebay/categories/<category_id>/requirements/?product=<id>`

`product` ist optional und ergänzt einen Hinweis zum Zustand dieses Artikels.

```json
{
  "aspects": [
    {"name": "Marke", "required": true, "recommended": true, "multiple": false, "free_text": true, "values": ["Markenlos", "3M"]},
    {"name": "Modell", "required": true, "recommended": true, "multiple": false, "free_text": true, "values": ["1008 XL", "150"]}
  ],
  "condition_ids": ["1000", "1500", "3000", "7000"],
  "condition_hint": "eBay kennt in dieser Kategorie nur „Gebraucht“. Dein Zustand „Gut“ steht zusätzlich als Notiz im Inserat."
}
```

(gekürzt – Kategorie 15230 hat 11 Merkmale, „Marke" allein 479 Vorschlagswerte)

### Inserate

#### `GET /api/ebay/listings/?scope=`

`scope`: `all` (Standard: alle verkaufbaren Artikel), `listed` (online oder beendet), `unlisted`
(ohne Inserat oder nur Entwurf). Mit `?page=` seitenweise.

```json
[
  {
    "id": 36,
    "sku": "ART-22BADA57",
    "title": "Fotodruck Sommergarten 30x20 cm",
    "condition": "new",
    "status": "available",
    "sale_price": "14.90",
    "quantity": 1,
    "aspects": {},
    "category_path": "",
    "image": "/media/products/ART-22BADA57/sommergarten.jpg",
    "listing": {
      "sku": "ART-22BADA57",
      "category_id": "360",
      "category_name": "Antiquitäten & Kunst › Kunst › Kunstdrucke",
      "shipping_profile": 1,
      "shipping_profile_name": "Standard",
      "best_offer": false,
      "offer_id": "11834163010",
      "listing_id": "110591031593",
      "status": "online",
      "state": "online",
      "has_unsynced_changes": false,
      "last_synced": "2026-10-06T09:13:18.740551Z",
      "sync_error": "",
      "url": "https://www.sandbox.ebay.de/itm/110591031593",
      "ebay_price": "17.73",
      "sold_quantity": 0,
      "facts_synced_at": "2026-10-06T10:19:46.202698Z"
    },
    "remembered_category": null,
    "sold_units": 1
  }
]
```

`listing` ist `null`, wenn der Artikel nie inseriert wurde. `listing.sku` ist die Nummer bei eBay
und kann von `sku` (unsere Artikelnummer) abweichen. `sold_units` zählt die Stück aus unseren
eBay-Bestellungen, `sold_quantity` ist eBays eigene Zahl.

#### `GET /api/ebay/listing-states/`

Für die Spalte „Kanäle" der Artikelliste. Schlüssel ist die Artikel-ID; jeder Kanal liefert
Einträge in genau dieser Form.

```json
{
  "33": [{"channel": "ebay", "label": "eBay", "state": "online", "status": "online", "sku": "ART-6320F084", "url": "https://www.sandbox.ebay.de/itm/110591031053"}],
  "34": [{"channel": "ebay", "label": "eBay", "state": "ended", "status": "ended", "sku": "ART-05092934", "url": ""}]
}
```

#### `POST /api/ebay/listings/<product_id>/preview/`

Gleicher Body wie `publish/`. Überträgt Artikel und Angebot **unveröffentlicht** und fragt eBay
nach den Gebühren.

```json
{"fees": [{"type": "InsertionFee", "amount": "0.35"}], "total": "0.35", "currency": "EUR"}
```

Fehler `400` für ein laufendes Inserat: „Für ein laufendes Inserat gibt es keine Gebühren-Vorschau."

#### `POST /api/ebay/listings/<product_id>/publish/`

Pflicht: `category_id`. Optional: `category_name`, `aspects`, `shipping_profile` (ID oder `null`
für das Standard-Profil), `best_offer`.

```json
{"category_id": "38172", "category_name": "Vasen", "aspects": {"Farbe": ["Blau"]}, "shipping_profile": 3, "best_offer": true}
```

Antwort `200`: der Artikel wie in `listings/`, das Inserat jetzt `online`:

```json
"listing": {"sku": "EK-000001", "category_id": "38172", "category_name": "Vasen", "shipping_profile": 3, "shipping_profile_name": "Paket versichert", "best_offer": true, "status": "online", "state": "online", "…": "…"},
"remembered_category": {"id": "38172", "name": "Vasen"}
```

`aspects` werden mit den Merkmalen des Artikels zusammengeführt und dort gespeichert. Fehler `400`:
- „eBay ist noch nicht fertig eingerichtet. Bitte zuerst die Checkliste im eBay-Reiter abschließen."
- „Nur verfügbare Artikel mit Bestand können inseriert werden."
- „Der Titel darf bei eBay höchstens 80 Zeichen haben."
- „Pflicht-Merkmale fehlen: Marke, Modell"
- „eBay verlangt mindestens ein Bild. Bitte zuerst ein Bild am Artikel hochladen."

Lehnt eBay ab (`502`), steht der Grund danach in `listing.sync_error` und das Inserat zeigt `error`.

#### `POST /api/ebay/listings/<product_id>/sync/`

Kein Body. Überträgt den aktuellen Stand des Artikels; ein beendetes Inserat geht wieder online.
Antwort `200`: der Artikel mit Inserat. Fehler `400`, wenn der Artikel nie inseriert wurde:

```json
{"error": ["Dieser Artikel wurde noch nicht inseriert."]}
```

#### `POST /api/ebay/listings/<product_id>/withdraw/`

Kein Body. Beendet das Inserat bei eBay; das Angebot bleibt und kann per `sync/` wieder
eingestellt werden. Antwort `200`: der Artikel, `listing.status` ist `ended`, `listing.url` leer.

#### `POST /api/ebay/listings/<product_id>/unlink/`

Kein Body. Löst die Verknüpfung, ohne bei eBay etwas zu ändern. Antwort `200`: der Artikel mit
`"listing": null`. War das Inserat online, steht es danach wieder unter `unassigned/`.

#### `POST /api/ebay/listings/sync-all/`

Überträgt alle laufenden Inserate, die geändert sind oder einen Fehler tragen.

```json
{"synced": 1, "failed": 0}
```

#### `POST /api/ebay/listings/refresh/`

Liest für alle laufenden Inserate den Käuferpreis und eBays Verkaufszahl neu.

```json
{"refreshed": 4, "failed": 0}
```

### Abgleich und Zuordnung

#### `POST /api/ebay/listings/pull/`

Kein Body. Holt die Inserate von eBay; bei eBay wird nur gelesen.

```json
{"found": 7, "linked": 0, "unassigned": 4}
```

`found`: laufende Inserate bei eBay · `linked`: in diesem Lauf über die exakt gleiche
Artikelnummer verknüpft · `unassigned`: warten jetzt auf Zuordnung.

#### `GET /api/ebay/unassigned/`

Inserate ohne Artikel. `?ignored=1` zeigt stattdessen die ignorierten. Das ist das **Format, das
jedes Portal liefert** – ein weiterer Kanal antwortet unter seinem eigenen Pfad genauso.

```json
[
  {
    "id": 9,
    "channel": "ebay",
    "channel_label": "eBay",
    "channel_sku": "",
    "listing_id": "110591099001",
    "title": "Alter Wecker, mechanisch",
    "price": "12.00",
    "quantity": 1,
    "image": "https://i.ebayimg.com/110591099001/1.png",
    "url": "https://www.sandbox.ebay.de/itm/110591099001",
    "status": "online",
    "ignored": false,
    "supported": true,
    "needs_migration": true,
    "notes": ["Altes Inserat: Beim Zuordnen bekommt es unsere Artikelnummer und wird umgewandelt."],
    "suggestion": null
  },
  {
    "id": 7,
    "channel": "ebay",
    "channel_label": "eBay",
    "channel_sku": "KERZE-07",
    "listing_id": "110591099003",
    "title": "Kerzenständer Messing",
    "price": "15.00",
    "quantity": 2,
    "image": "https://i.ebayimg.com/KERZE-07/1.png",
    "url": "https://www.sandbox.ebay.de/itm/110591099003",
    "status": "online",
    "ignored": false,
    "supported": true,
    "needs_migration": false,
    "notes": [],
    "suggestion": null
  }
]
```

| Feld | Bedeutung |
|---|---|
| `channel`, `channel_label` | Portal |
| `channel_sku` | Artikelnummer beim Portal; leer, wenn das Inserat keine hat |
| `listing_id` | Inseratsnummer des Portals |
| `supported` | `false`: Auktion oder Varianten – nur „Ignorieren" ist möglich |
| `needs_migration` | wird beim Zuordnen umgewandelt |
| `notes` | Hinweise für den Nutzer, darunter eBays letzter Ablehnungsgrund |
| `suggestion` | passender freier Artikel als `{"id", "sku", "title"}` (gleiche Nummer, sonst ähnlicher Titel) oder `null` – nur ein Vorschlag |

#### `POST /api/ebay/unassigned/<id>/link/`

```json
{"product": 38}
```

Antwort `200`: der Artikel wie in `listings/`. Hier weicht der Preis ab (26,00 € bei eBay,
23,90 € bei uns) – das Inserat behält eBays Nummer und steht auf „Geändert":

```json
{
  "id": 38,
  "sku": "EK-000001",
  "sale_price": "23.90",
  "listing": {"sku": "VASE-ALT", "status": "online", "state": "changed", "has_unsynced_changes": true, "shipping_profile_name": "Standard", "…": "…"}
}
```

Fehler `400`:

```json
{"error": ["Auktionen und Inserate mit Varianten werden nicht unterstützt."]}
```

- „Dieses Inserat ist bereits einem Artikel zugeordnet."
- „Dieser Artikel hat bereits ein laufendes eBay-Inserat."

Fehler `502` mit eBays Grund, wenn ein altes Inserat nicht umgewandelt werden kann; der Grund
steht danach in `notes`.

#### `POST /api/ebay/unassigned/<id>/create-product/`

Kein Body. Antwort `201` – hier aus einem alten Inserat: Der Artikel hat die neue Nummer
`EK-000002`, das Inserat trägt sie jetzt auch bei eBay:

```json
{
  "id": 39,
  "sku": "EK-000002",
  "title": "Alter Wecker, mechanisch",
  "condition": "very_good",
  "status": "available",
  "sale_price": "12.00",
  "quantity": 1,
  "aspects": {"Marke": ["Ohne"]},
  "image": "/media/products/EK-000002/1.png",
  "listing": {"sku": "EK-000002", "category_id": "261186", "category_name": "", "shipping_profile_name": "Versand DHL Paket", "listing_id": "110591099001", "status": "online", "state": "online", "…": "…"}
}
```

`category_name` ist bei übernommenen Inseraten leer, bis das Inserat einmal über „Bearbeiten" neu
gespeichert wird. Der Einkaufspreis des neuen Artikels ist 0.

#### `POST /api/ebay/unassigned/create-products/`

Kein Body. Legt für jedes offene, unterstützte Inserat einen Artikel an.

```json
{"created": 1, "failed": 0}
```

`failed` zählt Inserate, die eBay abgelehnt hat; ihr Grund steht in `notes`.

#### `POST /api/ebay/unassigned/<id>/ignore/`

Ohne Body wird ausgeblendet, `{"ignored": false}` zeigt das Inserat wieder. Antwort `200`: das
Inserat im Format von `unassigned/` mit dem neuen `ignored`.

### Verkäufe

#### `POST /api/ebay/orders/import/`

Kein Body.

```json
{"created": 1, "paid": 0, "cancelled": 0, "unknown_skus": []}
```

`created`: neue Bestellungen · `paid`: Zahlungseingänge zu wartenden Bestellungen ·
`cancelled`: bei eBay stornierte · `unknown_skus`: Nummern verkaufter Positionen, zu denen es
keinen Artikel gibt.

#### `POST /api/ebay/orders/<order_id>/ship/`

`carrier` ist ein `code` aus `carriers/`; die Trackingnummer darf nur Buchstaben und Ziffern enthalten.

```json
{"carrier": "DHL", "tracking_number": "00340434161094042557"}
```

Antwort `200`: die Bestellung wie in der [orders_app](../orders_app/README.md), jetzt mit
`"fulfillment_status": "shipped"`, `"shipping_carrier": "DHL"` und der Trackingnummer. Fehler `400`:

```json
{"error": {"tracking_number": ["Die Trackingnummer darf nur Buchstaben und Ziffern enthalten (ohne Leerzeichen)."]}}
```

- „Diese Bestellung stammt nicht von eBay."
- „Eine stornierte Bestellung kann nicht verschickt werden."
- „Die Zahlung ist noch offen. Bitte erst nach Zahlungseingang verschicken."

#### `GET /api/ebay/carriers/`

```json
[{"code": "DHL", "name": "DHL"}, {"code": "Hermes", "name": "Hermes"}, {"code": "DPD", "name": "DPD"}, {"code": "GLS", "name": "GLS"}, {"code": "UPS", "name": "UPS"}, {"code": "DeutschePost", "name": "Deutsche Post"}]
```

## Anwendung

### Einrichten

1. `.env` füllen (`EBAY_CLIENT_ID`, `EBAY_CLIENT_SECRET`, `EBAY_RUNAME`, `EBAY_TOKEN_KEY`) –
   siehe [Haupt-README](../../README.md#ebay-sandbox-einrichten).
2. `POST connect/start/` → Adresse öffnen, anmelden → `POST connect/finish/` mit der Adresse aus
   der Browserleiste.
3. `POST shipping-profiles/`, `PUT policies/`, `POST location/sync/`.
4. `GET status/` zeigt `ready: true`.

`EBAY_RUNAME` muss der von eBay erzeugte RuName sein, nicht der Anzeigename. eBay akzeptiert als
Rücksprung nur HTTPS und kein `localhost` – deshalb wird die Adresse von Hand eingefügt.

### Einen Artikel inserieren

```bash
curl "http://127.0.0.1:8000/api/ebay/categories/suggest/?q=Vase%20blau" -H "Authorization: Bearer <token>"
```

```bash
curl "http://127.0.0.1:8000/api/ebay/categories/38172/requirements/?product=38" -H "Authorization: Bearer <token>"
```

```bash
curl -X POST http://127.0.0.1:8000/api/ebay/listings/38/publish/ -H "Authorization: Bearer <token>" -H "Content-Type: application/json" -d '{"category_id": "38172", "category_name": "Vasen", "aspects": {"Farbe": ["Blau"]}}'
```

Später den Artikel ändern und mit `POST listings/38/sync/` übertragen.

### Vorhandene Inserate übernehmen

```bash
curl -X POST http://127.0.0.1:8000/api/ebay/listings/pull/ -H "Authorization: Bearer <token>"
```

```bash
curl http://127.0.0.1:8000/api/ebay/unassigned/ -H "Authorization: Bearer <token>"
```

Dann je Inserat `link/` (Artikel existiert), `create-product/` (neuer Artikel) oder `ignore/` –
oder `create-products/` für alle auf einmal. Im Frontend: **Artikel → Zuordnung**.

### Verkauf simulieren (nur Sandbox)

Die Sandbox-Kasse legt meist keine Bestellung an. Aus `backend/`, venv aktiv:

```bash
python manage.py simulate_ebay_sale EK-000001
```

```bash
python manage.py simulate_ebay_sale EK-000001 --quantity 2 --unpaid
```

```bash
python manage.py simulate_ebay_sale --pay 12
```

```bash
python manage.py simulate_ebay_sale --cancel 12
```

- Angegeben wird **unsere** Artikelnummer; `--pay` und `--cancel` erwarten die Bestell-ID.
- Die Bestellung (`SIM-…`) läuft durch denselben Code wie der echte Abruf.
- Nach einem Teilverkauf überträgt der Befehl die Restmenge an eBay; bei Menge 0 endet das Inserat.
- „Versand melden" markiert simulierte Bestellungen nur bei uns als verschickt, weil eBay sie
  nicht kennt.
- Der Befehl bricht ab, wenn `EBAY_ENV` nicht `sandbox` ist.

## Verbindungen

- Kennt **`products_app`** (Artikel, Bilder, Kategorien), **`orders_app`** (Bestellungen, Storno)
  und **`logistics_app`** (Lagerort) – nie umgekehrt.
- Auf Änderungen an Artikeln reagiert die App über Signals; `products_app` weiß nichts von eBay.
- Einstellungen aus **`core`** (`EBAY_*`), Pagination aus `core/pagination.py`.
- Das Frontend führt die Daten zusammen: `listing-states/` für die Artikelliste, `unassigned/`
  für die Zuordnung.

## Dateien

| Datei | Inhalt |
|---|---|
| `models.py` | `EbayAccount`, `EbayLocation`, `EbayShippingProfile`, `EbayListing`, `EbayCategoryMapping`, `EbayImage` |
| `client.py` | HTTP-Zugriff auf eBay: REST und die XML-Trading-API, Adressen je Umgebung |
| `crypto.py` | Verschlüsselung der gespeicherten Tokens |
| `exceptions.py` | `EbayApiError`, `EbayNotConnected`, `EbayNotConfigured` |
| `utils.py` | kleine gemeinsame Helfer |
| `signals.py` | Reaktion auf Artikel-Änderungen |
| `services/` | die Logik, siehe Tabelle unter „Logik" |
| `management/commands/simulate_ebay_sale.py` | Befehl zum Simulieren von Verkäufen |
| `api/serializers.py`, `api/views.py`, `api/urls.py` | die API |
| `admin.py` | Verbindung, Lagerort, Versandprofile, Inserate, Merkliste, gehostete Bilder |
