# ebay_app

Adapter **und** Zustandshalter für den Verkaufskanal eBay: bringt Artikel aus
`products_app` auf eBay und holt Verkäufe zurück.

> **Status: geplant.** Aktuell nur das App-Gerüst. Gebaut wird, sobald der eBay-Developer-
> Account (Sandbox) aktiv ist – immer erst Sandbox, dann Production.

## Aufgaben

- Artikel inserieren: `createOrReplaceInventoryItem` → `createOffer` → `publishOffer`
  (einzeln und „alle")
- eBay-Zustand je Artikel halten (Entwurf / online / verkauft / beendet)
- OAuth-Tokens speichern und den Access-Token (2 h) per Refresh-Token (18 Monate) erneuern
- Verkäufe über die Fulfillment API (`getOrders`) holen und mit `orders_app` verknüpfen
  (inkl. Käuferdaten)
- Duplikat-Schutz: pro Artikel höchstens ein Inserat

## Models

Geplant:
- **`EbayToken`** (Singleton): Refresh-/Access-Token und Ablaufzeit.
- **`EbayListing`**: OneToOne zu `Product`, `offer_id`, `listing_id`, `category_id`,
  `merchant_location_key`, `status`, `last_synced`; `has_unsynced_changes` berechnet.

## Services / Logik

Geplant: OAuth-Service (Consent-URL, Code gegen Token tauschen, Refresh),
Inventory-Service (Mapping `Product` → eBay-Payload), Publish-Flow mit Guard, Orders-Sync.
Einmalige Voraussetzung zum Publishen: Business Policies (Versand, Rückgabe, Zahlung) und
eine Inventory Location. Offener Punkt: eBay braucht **öffentliche Bild-URLs** – die
lokalen Bilder der Desktop-App müssen dafür bereitgestellt werden.

## API-Endpoints

Noch keine. Geplant: OAuth-Callback, Publish (einzeln / alle), Sync.

## Verbindungen

- Importiert `Product` aus `products_app` (einseitige Code-Abhängigkeit).
- Schreibt Verkäufe in `orders_app`.

## Dateien

- `apps.py` – App-Konfiguration
- `models.py` – noch leer
