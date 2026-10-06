# orders_app

Bestellungen mit Positionen, Kunden- und Versanddaten. Führt den **Bestand automatisch**
mit und ist die Datengrundlage für alle Auswertungen in `finance_app`.

> Bestellungen werden manuell angelegt oder kommen über die `ebay_app` aus eBay herein.
> `orders_app` selbst kennt eBay nicht – die `ebay_app` füllt nur die dafür vorgesehenen Felder.

## Aufgaben

- Verkäufe mit einer oder mehreren Positionen erfassen
- Käufer- und Lieferdaten festhalten („welche Bestellung geht wohin")
- Versand- und Reklamationsstatus pflegen
- Bestand beim Verkauf abbuchen, bei Storno zurückbuchen
- Storno mit Wahl, was mit den Artikeln passiert, und festgehaltenem Grund

## Models

- **`Order`**: `sold_at` (**indexiert**), `fulfillment_status` (offen / verpackt / verschickt /
  zugestellt / in Reklamation / storniert), `payment_status` (bezahlt / Zahlung offen, Standard
  bezahlt), `tracking_number`, `shipping_carrier`, `buyer_name`,
  `ship_street`, `ship_zip`, `ship_city`, `ship_country`, `ebay_username`, `ebay_order_id`
  (eindeutig, `NULL` bei manuellen Bestellungen), `return_note`, `created_at`.
  Berechnet: `total_revenue`, `total_profit`.
- **`OrderItem`**: `order`, `product` (`SET_NULL` – wird ein Artikel gelöscht, bleibt die
  Position im Verlauf erhalten), `sold_price`, `quantity` (≥ 1), `ebay_line_item_id`.
  Berechnet: `subtotal`, `profit`.
- **`Cancellation`**: OneToOne zu `Order`, `reason`, `source` (manuell / eBay), `item_action`
  (verfügbar / Archiv / gelöscht), `created_at` – hält fest, warum und woher ein Storno kam.

## Services / Logik

- `services.filter_orders` – Filter der Liste nach Herkunft (eBay / manuell), Zahlungsstatus
  und Bestellstatus; ungültige Werte liefern 400 mit deutscher Meldung
- `services.apply_stock_change` – ändert die Menge; Menge 0 → Status „verkauft",
  Menge wieder > 0 → „verfügbar"
- `services.sync_stock` – bucht alle Positionen einer Bestellung ab oder zurück
- `services.cancel_order(order, item_action, reason, source)` – **atomar**: zurückbuchen,
  Status „storniert", `Cancellation` anlegen, dann Artikel „verfügbar", „archiviert" oder gelöscht
- `OrderSerializer`:
  - prüft den Bestand – bei Überbestellung 400 („Nur X Stück von … verfügbar.")
  - `create` / `update` laufen in einer Transaktion
  - neue Positionen beim Update = alte zurück-, neue abbuchen
  - liefert `cancellation` (oder `null`) und `ebay_order_id` nur lesend
  - eine Bestellung mit `ebay_order_id` lässt sich hier nicht auf „verschickt" setzen und nur
    von „verschickt" auf „zugestellt" – der Versand muss über die `ebay_app` gemeldet werden
- Listen laden Positionen, Artikel und Storno vorab → konstante Query-Anzahl

## API-Endpoints

| Methode | Pfad | Zweck |
|---|---|---|
| GET / POST | `/api/orders/` | Bestellungen (neueste zuerst; `?source=ebay\|manual`, `?payment=paid\|pending`, `?status=`, optional `?page=N`) / neue inkl. `items` |
| GET / PUT / PATCH / DELETE | `/api/orders/<id>/` | Einzelne Bestellung; Löschen bucht den Bestand zurück |
| POST | `/api/orders/<id>/cancel/` | Stornieren; Body `item_action`: `available` \| `archive` \| `delete`, optional `reason` |

Abholen von eBay-Verkäufen und das Melden des Versands liegen in der `ebay_app`
(`/api/ebay/orders/…`).

## Verbindungen

- **`products_app`**: `OrderItem.product`; ändert `Product.quantity` und `Product.status`.
- **`finance_app`**: aggregiert die Positionen **nicht stornierter, bezahlter** Bestellungen;
  Umsatz mit offener Zahlung wird getrennt ausgewiesen.
- **`ebay_app`**: legt Bestellungen aus eBay an und storniert sie über `cancel_order` –
  die Abhängigkeit zeigt nur von `ebay_app` hierher.

## Dateien

- `models.py` – `Order`, `OrderItem`, `Cancellation`
- `services.py` – Listenfilter, Bestandsführung und Storno
- `api/serializers.py` – `OrderSerializer` (verschachtelte `items`, Bestandsprüfung),
  `CancelSerializer`, `CancellationSerializer`
- `api/views.py`, `api/urls.py` – API inkl. Storno-Endpoint
- `admin.py` – Bestellungen mit Positions-Inline, Stornos
