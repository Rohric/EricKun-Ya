# products_app

Der **plattform-neutrale Kern** und die Source of Truth für alle Artikel. Enthält
ausschließlich Artikel-Inhaltsdaten – **kein** eBay- oder sonstiges Plattform-Wissen.

> Leitprinzip: Das Tool besitzt die Artikel. eBay (und später Amazon) sind nur
> Ausgabekanäle. `products_app` kennt **keine** Plattform-App (kein Import in diese
> Richtung); die Plattform-Apps hängen sich an `Product` an.

## Aufgabe

- Verwaltung der Artikelstammdaten (Titel, Zustand, Ein-/Verkaufspreis, Menge, Aspekte)
- Automatische, eindeutige SKU-Vergabe
- Gewinn pro Stück als Berechnung (kein gespeichertes Feld)

## Model

- **`Product`**: `sku` (auto-generiert, `ART-XXXXXXXX`, nicht editierbar), `title`,
  `description`, `condition` (`TextChoices`, englische Werte / deutsche Labels),
  `purchase_price`, `sale_price`, `quantity`, `aspects` (`JSONField`, weil eBay-Aspekte
  kategorieabhängig sind), `purchase_date`, `created_at`, `updated_at`.
  - `profit` ist eine **`@property`** (`sale_price − purchase_price`), kein Feld.

## Endpoints

| Methode | Pfad | Zweck |
|---|---|---|
| GET / POST | `/api/products/` | Alle Artikel auflisten / neuen anlegen |
| GET / PUT / PATCH / DELETE | `/api/products/<id>/` | Einzelnen Artikel lesen/ändern/löschen |

Alle Endpoints erfordern Authentifizierung (`IsAuthenticated`).

## Verbindungen

- **`orders_app`**: `OrderItem` referenziert `Product` per ForeignKey (`related_name="order_items"`).
- **`finance_app`**: liest `purchase_price` / `purchase_date` für Einkaufs- und GuV-Auswertungen.
- **`ebay_app`** (geplant): `EbayListing` wird `Product` per OneToOne referenzieren
  (`product.ebay_listing`) – Datenverknüpfung ja, Code-Abhängigkeit nur einseitig.

## Dateien

- `models.py` – `Product`
- `utils.py` – `generate_sku()`
- `api/serializers.py`, `api/views.py`, `api/urls.py` – CRUD-API
- `admin.py` – `ProductAdmin` (z. B. zum Einpflegen der Altartikel von Hand)
