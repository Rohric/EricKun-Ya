# orders_app

Bestellungen und ihre Positionen. Eine Bestellung ist eine eigene Entität mit eigenem
Lebenszyklus (offen → verpackt → verschickt → zugestellt) und die **Datengrundlage für
alle Gewinn/Verlust-Auswertungen** in `finance_app`.

> In v1 werden Orders **manuell** (API/Admin) angelegt. Sobald `ebay_app` steht, kommen
> sie zusätzlich per eBay Fulfillment API (`getOrders`) herein – die Struktur ist dafür
> schon vorbereitet.

## Aufgabe

- Verkäufe erfassen (echter Verkaufspreis, Verkaufszeitpunkt)
- Versand-Status pro Bestellung verwalten
- Umsatz/Gewinn pro Bestellung ableiten (als Berechnung, kein Feld)

## Models

- **`Order`**: `sold_at`, `fulfillment_status` (`TextChoices`), `tracking_number`,
  `created_at`. Der **Versand-Status hängt an der Order** (nicht am Product/Listing –
  Versand ist nicht plattform-spezifisch).
  - `total_revenue` / `total_profit` als **Properties** über die Positionen.
- **`OrderItem`**: FK → `Order` (`related_name="items"`), FK → `Product` (`PROTECT`),
  `sold_price` (kann vom `Product.sale_price` abweichen), `quantity`.
  - `subtotal` / `profit` als **Properties**.

Eine Order kann mehrere Positionen haben (ein Kauf, ein Versand).

## Endpoints

| Methode | Pfad | Zweck |
|---|---|---|
| GET / POST | `/api/orders/` | Bestellungen auflisten / neue anlegen (inkl. `items`) |
| GET / PUT / PATCH / DELETE | `/api/orders/<id>/` | Einzelne Bestellung lesen/ändern/löschen |

Positionen werden **verschachtelt** im selben Request mitgeschickt
(`items: [{product, sold_price, quantity}]`). Alle Endpoints erfordern Authentifizierung.

## Verbindungen

- **`products_app`**: `OrderItem.product` (ForeignKey, `PROTECT`).
- **`finance_app`**: aggregiert `OrderItem`s (nach `Order.sold_at`) für GuV, Monatsumsatz
  und Ziel-Fortschritt.

## Dateien

- `models.py` – `Order`, `OrderItem`
- `api/serializers.py` – `OrderSerializer` (writable nested `items`), `OrderItemSerializer`
- `api/views.py`, `api/urls.py` – CRUD-API
- `admin.py` – `OrderAdmin` mit `OrderItem`-Inline
