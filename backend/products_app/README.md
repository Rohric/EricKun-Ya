# products_app

Der **plattform-neutrale Kern** und die Source of Truth für alle Artikel – inklusive
Kategorien, Verkaufsstatus, Archiv und Bildern. Enthält **kein** eBay-Wissen.

> Leitprinzip: Das Tool besitzt die Artikel, eBay (später Amazon) sind nur Ausgabekanäle.
> `products_app` importiert **keine** Plattform-App; die Plattform-Apps hängen sich an `Product`.

## Aufgaben

- Artikelstammdaten pflegen (Titel, Zustand, Preise, Menge, Aspekte, Einkaufsdatum)
- Eindeutige SKU automatisch vergeben
- Interne Kategorien als Baum (Ober-/Unterkategorie)
- Verkaufsstatus und **Archiv** (verkaufte/archivierte Artikel getrennt von den aktiven)
- Mehrere Bilder pro Artikel in einem Ordner je SKU, mit automatischem Aufräumen

## Models

- **`Category`**: `name`, `parent` (Self-FK → `children`); eindeutig je Oberkategorie.
  `str()` liefert den Pfad „Oberkategorie › Unterkategorie".
- **`Product`**: `sku` (auto, `ART-XXXXXXXX`, nicht editierbar), `title`, `description`,
  `category`, `condition` (Neu … Defekt), `status` (verfügbar / reserviert / verkauft /
  archiviert, **indexiert**), `purchase_price`, `sale_price`, `quantity`, `aspects` (JSON),
  `purchase_date` (**indexiert**), Zeitstempel.
  Berechnet statt gespeichert: `profit`, `category_path`.
- **`ProductImage`**: `product`, `image` (abgelegt unter `media/products/<sku>/`),
  `position` (0 = Hauptbild), `uploaded_at`.

## Services / Logik

- `utils.generate_sku()` – kollisionsfreie SKU
- `utils.filter_products()` – Filter der Liste nach Status, Kategorie (inkl. Unterkategorien)
  und Suchtext (Titel oder SKU); ungültige Werte liefern 400 mit deutscher Meldung
- `utils.status_counts()` – Anzahl je Status für die Reiter der Artikelseite
- `signals.py` – löscht Bilddateien beim Löschen/Ersetzen und den ganzen SKU-Ordner beim
  Löschen des Artikels
- Archiv = Status `sold` oder `archived`; die Liste filtert per `?view=` oder genauer per `?status=`
- Bestand und „verkauft" bucht `orders_app` automatisch (siehe dort)
- Listen laden Kategorie, Oberkategorie und Bilder vorab (`select_related` /
  `prefetch_related`) → konstante Query-Anzahl, egal wie viele Artikel

## API-Endpoints

| Methode | Pfad | Zweck |
|---|---|---|
| GET / POST | `/api/categories/` | Kategorien auflisten / anlegen |
| GET / PUT / PATCH / DELETE | `/api/categories/<id>/` | Einzelne Kategorie |
| GET / POST | `/api/products/` | Artikel; `?view=active` (Default) \| `archive` \| `all` oder `?status=available\|reserved\|sold\|archived`; dazu `?category=<id>`, `?search=<text>`, optional `?page=N` |
| GET | `/api/products/counts/` | Anzahl je Status plus `all`; berücksichtigt `?category=` und `?search=` |
| GET / PUT / PATCH / DELETE | `/api/products/<id>/` | Einzelner Artikel |
| GET / POST | `/api/products/<id>/images/` | Bilder auflisten / hochladen (multipart, Feld `image`) |
| DELETE | `/api/product-images/<id>/` | Einzelnes Bild löschen |

## Verbindungen

- **`orders_app`**: `OrderItem.product` (FK, `SET_NULL`); bucht Bestand und Status.
- **`finance_app`**: liest `purchase_price` / `purchase_date` für Einkauf und Gewinn.
- **`ebay_app`**: hängt `EbayListing` (OneToOne zu `Product`), gehostete Bilder und die
  Kategorie-Merkliste an; reagiert über Signals auf Artikel-Änderungen. Wo ein Artikel
  inseriert ist, liefert `GET /api/ebay/listing-states/` – `products_app` kennt die Kanäle nicht.

## Dateien

- `models.py` – `Category`, `Product`, `ProductImage`
- `utils.py` – `generate_sku()`, `filter_products()`, `status_counts()`
- `signals.py` – Aufräumen der Bilddateien
- `apps.py` – registriert die Signals in `ready()`
- `api/serializers.py`, `api/views.py`, `api/urls.py` – API
- `admin.py` – Kategorien, Artikel mit Bild-Inline
