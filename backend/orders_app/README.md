# orders_app

Bestellungen mit Positionen, Kunden- und Versanddaten. Führt den **Bestand automatisch**
mit und ist die Datengrundlage für alle Auswertungen in `finance_app`.

> In v1 werden Bestellungen manuell angelegt. Mit der `ebay_app` kommen sie zusätzlich
> über eBays `getOrders` herein – Felder und Status sind dafür vorbereitet.

## Aufgaben

- Verkäufe mit einer oder mehreren Positionen erfassen
- Käufer- und Lieferdaten festhalten („welche Bestellung geht wohin")
- Versand- und Reklamationsstatus pflegen
- Bestand beim Verkauf abbuchen, bei Storno zurückbuchen
- Storno mit Wahl, was mit den Artikeln passiert

## Models

- **`Order`**: `sold_at` (**indexiert**), `fulfillment_status` (offen / verpackt / verschickt /
  zugestellt / in Reklamation / storniert), `tracking_number`, `buyer_name`, `ship_street`,
  `ship_zip`, `ship_city`, `ship_country`, `ebay_username`, `return_note`, `created_at`.
  Berechnet: `total_revenue`, `total_profit`.
- **`OrderItem`**: `order`, `product` (`SET_NULL` – wird ein Artikel gelöscht, bleibt die
  Position im Verlauf erhalten), `sold_price`, `quantity` (≥ 1).
  Berechnet: `subtotal`, `profit`.

## Services / Logik

- `services.apply_stock_change` – ändert die Menge; Menge 0 → Status „verkauft",
  Menge wieder > 0 → „verfügbar"
- `services.sync_stock` – bucht alle Positionen einer Bestellung ab oder zurück
- `services.cancel_order` – **atomar**: zurückbuchen, Status „storniert", dann Artikel
  „verfügbar", „archiviert" oder gelöscht
- `OrderSerializer`:
  - prüft den Bestand – bei Überbestellung 400 („Nur X Stück von … verfügbar.")
  - `create` / `update` laufen in einer Transaktion
  - neue Positionen beim Update = alte zurück-, neue abbuchen
- Listen laden Positionen und Artikel vorab → konstante Query-Anzahl

## API-Endpoints

| Methode | Pfad | Zweck |
|---|---|---|
| GET / POST | `/api/orders/` | Bestellungen (neueste zuerst, optional `?page=N`) / neue inkl. `items` |
| GET / PUT / PATCH / DELETE | `/api/orders/<id>/` | Einzelne Bestellung; Löschen bucht den Bestand zurück |
| POST | `/api/orders/<id>/cancel/` | Stornieren; Body `item_action`: `available` \| `archive` \| `delete` |

## Verbindungen

- **`products_app`**: `OrderItem.product`; ändert `Product.quantity` und `Product.status`.
- **`finance_app`**: aggregiert die Positionen **nicht stornierter** Bestellungen.

## Dateien

- `models.py` – `Order`, `OrderItem`
- `services.py` – Bestandsführung und Storno
- `api/serializers.py` – `OrderSerializer` (verschachtelte `items`, Bestandsprüfung)
- `api/views.py`, `api/urls.py` – API inkl. Storno-Endpoint
- `admin.py` – Bestellungen mit Positions-Inline
