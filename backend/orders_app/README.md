# orders_app

## Kurzbeschreibung

Bestellungen mit Positionen, Käufer- und Lieferdaten. Die App führt den **Bestand automatisch**
mit und ist die Datengrundlage für alle Auswertungen der `finance_app`.

**Abgrenzung:** `orders_app` kennt kein Portal. Bestellungen entstehen von Hand oder werden von der
`ebay_app` angelegt, die dafür nur die vorgesehenen Felder füllt. Verkäufe von eBay abholen und den
Versand an eBay melden liegt in der `ebay_app`.

## Aufgaben

- Verkäufe mit einer oder mehreren Positionen erfassen
- Käufer- und Lieferdaten, Zahlungs- und Versandstatus festhalten
- Bestand beim Verkauf abbuchen, bei Storno und beim Löschen zurückbuchen
- Stornieren mit der Wahl, was mit den Artikeln passiert, und einem festgehaltenen Grund
- Verkaufte Stückzahl je Artikel liefern (für „noch da / insgesamt" in der Artikelliste)

## Models

| Model | Felder | Hinweise |
|---|---|---|
| `Order` | `sold_at`, `fulfillment_status`, `payment_status`, `tracking_number`, `shipping_carrier`, `buyer_name`, `ship_street`, `ship_zip`, `ship_city`, `ship_country`, `ebay_username`, `ebay_order_id`, `return_note`, `created_at` | `ebay_order_id` ist eindeutig und bei eigenen Bestellungen `null`; berechnet: `total_revenue`, `total_profit` |
| `OrderItem` | `order`, `product`, `sold_price`, `quantity`, `ebay_line_item_id` | wird ein Artikel gelöscht, bleibt die Position erhalten (`product` wird `null`); berechnet: `subtotal`, `profit` |
| `Cancellation` | `order`, `reason`, `source`, `item_action`, `created_at` | hält fest, warum und woher ein Storno kam |

`fulfillment_status`: `open`, `packed`, `shipped`, `delivered`, `in_return`, `cancelled`
`payment_status`: `paid` (Standard), `pending`
`source` eines Stornos: `manual`, `ebay` · `item_action`: `available`, `archive`, `delete`

## Logik

- **`services.sync_stock(order, sign)`** – bucht alle Positionen einer Bestellung ab (`-1`) oder
  zurück (`+1`). Menge 0 setzt den Artikel auf „verkauft", Menge wieder über 0 auf „verfügbar".
- **`services.cancel_order(order, item_action, reason, source)`** – in einer Transaktion:
  zurückbuchen, Status „storniert", `Cancellation` anlegen, dann die Artikel verfügbar lassen,
  archivieren oder löschen.
- **`services.filter_orders()`** – Listenfilter nach Herkunft, Zahlung und Status.
- **`services.product_sales()`** – verkaufte Stück und einzelne Verkäufe je Artikel aus nicht
  stornierten Bestellungen.
- **`OrderSerializer`**
  - prüft den Bestand: Wer mehr bestellt, als da ist, bekommt `400`
  - `create` und `update` laufen in einer Transaktion; neue Positionen beim Ändern heißt: alte
    zurückbuchen, neue abbuchen
  - eBay-Bestellungen lassen sich hier **nicht** auf „verschickt" setzen und nur von „verschickt"
    auf „zugestellt" – der Versand muss über die `ebay_app` an eBay gemeldet werden

## API-Übersicht

| Methode | Pfad | Zweck |
|---|---|---|
| GET, POST | `/api/orders/` | Bestellungen auflisten, anlegen |
| GET, PUT, PATCH, DELETE | `/api/orders/<id>/` | einzelne Bestellung |
| GET | `/api/orders/product-sales/` | verkaufte Stück je Artikel |
| POST | `/api/orders/<id>/cancel/` | stornieren |

Alle Endpoints verlangen einen angemeldeten Nutzer.

## API im Detail

### `GET /api/orders/`

Neueste zuerst.

| Parameter | Bedeutung |
|---|---|
| `source` | `ebay` oder `manual` |
| `payment` | `paid` oder `pending` |
| `status` | ein Wert von `fulfillment_status` |
| `page` | Seite (25 je Seite); ohne `page` die ganze Liste als Array |

Antwort: Array (oder Seite) von Bestellungen in der Form unten.

### `POST /api/orders/`

Pflicht: `sold_at`, `items` mit `product`, `quantity`, `sold_price`. Alles andere ist optional.

```json
{
  "sold_at": "2026-10-06T09:30:00Z",
  "buyer_name": "Mara Muster",
  "ship_street": "Hafenstraße 12",
  "ship_zip": "20457",
  "ship_city": "Hamburg",
  "ship_country": "DE",
  "items": [{"product": 38, "quantity": 1, "sold_price": "22.90"}]
}
```

Antwort `201` – der Bestand des Artikels ist danach um 1 gesunken:

```json
{
  "id": 6,
  "sold_at": "2026-10-06T09:30:00Z",
  "fulfillment_status": "open",
  "payment_status": "paid",
  "tracking_number": "",
  "shipping_carrier": "",
  "buyer_name": "Mara Muster",
  "ship_street": "Hafenstraße 12",
  "ship_zip": "20457",
  "ship_city": "Hamburg",
  "ship_country": "DE",
  "ebay_username": "",
  "ebay_order_id": null,
  "return_note": "",
  "cancellation": null,
  "items": [
    {"id": 6, "product": 38, "product_title": "Vase blau, Keramik", "sold_price": "22.90", "quantity": 1, "subtotal": "22.90", "profit": "16.90"}
  ],
  "total_revenue": "22.90",
  "total_profit": "16.90",
  "created_at": "2026-10-06T12:08:05.944423Z"
}
```

Fehler `400`, wenn der Bestand nicht reicht:

```json
{"error": {"non_field_errors": ["Nur 2 Stück von „Vase blau, Keramik“ verfügbar."]}}
```

### `GET|PUT|PATCH|DELETE /api/orders/<id>/`

`PATCH` für Status und Versanddaten:

```json
{"fulfillment_status": "shipped", "tracking_number": "00340434161094042557", "shipping_carrier": "DHL"}
```

Antwort `200`: die ganze Bestellung. `DELETE` antwortet mit `204` und bucht den Bestand zurück.

Fehler `400` bei einer eBay-Bestellung, die von Hand auf „verschickt" gesetzt werden soll:

```json
{"error": {"non_field_errors": ["Diese Bestellung stammt von eBay. Bitte den Versand über „Versand melden“ an eBay übertragen."]}}
```

`ebay_order_id`, `ebay_username` und `cancellation` sind nur lesbar.

### `GET /api/orders/product-sales/`

`?products=38,39` beschränkt auf diese Artikel; ohne den Parameter kommen alle. Stornierte
Bestellungen zählen nicht.

```json
{
  "38": {
    "sold": 1,
    "sales": [
      {
        "order": 6,
        "sold_at": "2026-10-06 09:30:00+00:00",
        "quantity": 1,
        "sold_price": "22.90",
        "fulfillment_status": "shipped",
        "payment_status": "paid",
        "source": "manual",
        "buyer_name": "Mara Muster"
      }
    ]
  }
}
```

### `POST /api/orders/<id>/cancel/`

`item_action`: `available` (Standard – Artikel wieder verkaufbar), `archive` oder `delete`.
`reason` ist optional.

```json
{"item_action": "available", "reason": "Käufer hat sich umentschieden."}
```

Antwort `200`: die Bestellung mit `fulfillment_status: "cancelled"` und

```json
"cancellation": {"reason": "Käufer hat sich umentschieden.", "source": "manual", "item_action": "available", "created_at": "2026-10-06T12:08:06.021451Z"}
```

Fehler `400`, wenn `item_action` einen unbekannten Wert hat oder die Bestellung schon storniert ist:

```json
{"error": ["Diese Bestellung ist bereits storniert."]}
```
Ein Storno einer eBay-Bestellung wird **nicht** an eBay gemeldet.

## Anwendung

Ein Verkauf von Hand, vom Anlegen bis zum Versand:

```bash
curl -X POST http://127.0.0.1:8000/api/orders/ -H "Authorization: Bearer <token>" -H "Content-Type: application/json" -d '{"sold_at": "2026-10-06T09:30:00Z", "buyer_name": "Mara Muster", "items": [{"product": 38, "quantity": 1, "sold_price": "22.90"}]}'
```

```bash
curl -X PATCH http://127.0.0.1:8000/api/orders/6/ -H "Authorization: Bearer <token>" -H "Content-Type: application/json" -d '{"fulfillment_status": "shipped", "tracking_number": "00340434161094042557"}'
```

Im Frontend: **Artikel → Bestellungen → + Neue Bestellung**. eBay-Bestellungen tragen ein
„eBay"-Kennzeichen; ihr Versand läuft über „Versand melden".

## Verbindungen

- **`products_app`**: `OrderItem.product`; ändert `Product.quantity` und `Product.status`.
- **`finance_app`** wertet die Positionen nicht stornierter, bezahlter Bestellungen aus.
- **`ebay_app`** legt Bestellungen aus eBay an, setzt Zahlungseingänge und storniert über
  `cancel_order`. Die Abhängigkeit zeigt nur von dort hierher.

## Dateien

| Datei | Inhalt |
|---|---|
| `models.py` | `Order`, `OrderItem`, `Cancellation` |
| `services.py` | Listenfilter, Verkäufe je Artikel, Bestandsführung, Storno |
| `api/serializers.py` | `OrderSerializer`, `CancelSerializer`, `CancellationSerializer` |
| `api/views.py`, `api/urls.py` | die API |
| `admin.py` | Bestellungen mit Positionen, Stornos |
