# products_app

## Kurzbeschreibung

Der **portal-neutrale Kern**: Artikel, Kategorien, Bilder und die interne Artikelnummer. Diese App
ist die Quelle der Wahrheit für alles, was verkauft wird.

**Abgrenzung:** kein Wissen über eBay oder andere Portale, keine Bestellungen. `products_app`
importiert keine andere App des Projekts – die anderen Apps hängen sich an `Product`.

## Aufgaben

- Artikelstammdaten pflegen (Titel, Beschreibung, Zustand, Preise, Menge, Merkmale, Einkaufsdatum)
- Die interne Artikelnummer vergeben: fortlaufend, nie zweimal
- Interne Kategorien als Baum führen (Ober- und Unterkategorie)
- Verkaufsstatus und Archiv
- Mehrere Bilder je Artikel ablegen und beim Löschen aufräumen

## Models

| Model | Felder | Hinweise |
|---|---|---|
| `Category` | `name`, `parent` | je Oberkategorie eindeutig; `str()` liefert „Ober › Unter" |
| `Product` | `sku`, `title`, `description`, `category`, `condition`, `status`, `purchase_price`, `sale_price`, `quantity`, `aspects` (JSON), `purchase_date`, `created_at`, `updated_at` | `sku` wird beim ersten Speichern vergeben und ist nicht änderbar; berechnet: `profit`, `category_path` |
| `ProductImage` | `product`, `image`, `position`, `uploaded_at` | Datei unter `media/products/<sku>/`; Position 0 ist das Hauptbild |
| `SkuSequence` | `last_number` | eine Zeile: der Zähler der Artikelnummern |

`condition`: `new`, `like_new`, `very_good`, `good` (Standard), `acceptable`, `for_parts`
`status`: `available` (Standard), `reserved`, `sold`, `archived`

## Logik

- **`utils.generate_sku()`** – erhöht den Zähler in einer Transaktion und liefert die nächste
  Nummer im Format `<SKU_PREFIX>-<sechs Stellen>`, z. B. `EK-000123`. Eine Nummer wird nie
  zweimal vergeben, auch nicht nach dem Löschen eines Artikels. Artikel aus der Zeit vor dem
  Zähler behalten ihre `ART-…`-Nummer.
- **`utils.filter_products()`** – filtert nach Status, Kategorie (inklusive Unterkategorien) und
  Suchtext (Titel oder Artikelnummer); ungültige Werte ergeben 400.
- **`utils.status_counts()`** – Anzahl je Status für die Reiter der Artikelseite.
- **`signals.py`** – löscht Bilddateien, wenn ein Bild gelöscht oder ersetzt wird, und den ganzen
  Bildordner, wenn der Artikel gelöscht wird.
- Archiv = Status `sold` oder `archived`.
- Bestand und Status „verkauft" bucht `orders_app`; hier wird nur gespeichert.

## API-Übersicht

| Methode | Pfad | Zweck |
|---|---|---|
| GET, POST | `/api/categories/` | Kategorien auflisten, anlegen |
| GET, PUT, PATCH, DELETE | `/api/categories/<id>/` | einzelne Kategorie |
| GET, POST | `/api/products/` | Artikel auflisten, anlegen |
| GET | `/api/products/counts/` | Anzahl je Status |
| GET, PUT, PATCH, DELETE | `/api/products/<id>/` | einzelner Artikel |
| GET, POST | `/api/products/<id>/images/` | Bilder auflisten, hochladen |
| DELETE | `/api/product-images/<id>/` | einzelnes Bild löschen |

Alle Endpoints verlangen einen angemeldeten Nutzer.

## API im Detail

### `GET /api/categories/` · `POST /api/categories/`

Body beim Anlegen: `name` (Pflicht), `parent` (ID der Oberkategorie oder `null`).

```json
{"name": "Vasen", "parent": 7}
```

Antwort `201`:

```json
{"id": 8, "name": "Vasen", "parent": 7, "path": "Deko › Vasen"}
```

`GET` liefert die Liste in derselben Form. Unterkategorien sind je Oberkategorie eindeutig; ein
zweiter gleicher Name wird mit `400` abgelehnt. Oberkategorien werden nicht auf Dubletten geprüft.

### `GET|PUT|PATCH|DELETE /api/categories/<id>/`

Wie oben für eine Kategorie. `DELETE` antwortet mit `204`; Unterkategorien werden mit gelöscht,
Artikel behalten dann keine Kategorie.

### `GET /api/products/`

| Parameter | Bedeutung |
|---|---|
| `view` | `active` (Standard: ohne verkauft/archiviert), `archive`, `all` |
| `status` | genau ein Status: `available`, `reserved`, `sold`, `archived` (hat Vorrang vor `view`) |
| `category` | ID einer Kategorie, Unterkategorien eingeschlossen |
| `search` | Text im Titel oder in der Artikelnummer |
| `page` | Seite (25 je Seite, `page_size` bis 100). Ohne `page` kommt die ganze Liste als Array |

Beispiel `GET /api/products/?status=available&page=1`:

```json
{
  "count": 5,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 38,
      "sku": "EK-000001",
      "title": "Vase blau, Keramik",
      "description": "Handgetöpfert, 24 cm hoch.",
      "category": 8,
      "category_path": "Deko › Vasen",
      "condition": "very_good",
      "status": "available",
      "purchase_price": "6.00",
      "sale_price": "24.90",
      "quantity": 3,
      "aspects": {"Marke": ["Ohne"]},
      "purchase_date": "2026-09-30",
      "profit": "18.90",
      "images": [],
      "created_at": "2026-10-06T12:08:05.741285Z",
      "updated_at": "2026-10-06T12:08:05.741312Z"
    }
  ]
}
```

Fehler `400` bei unbekanntem Status:

```json
{"error": ["Unbekannter Status. Erlaubt: available, reserved, sold, archived."]}
```

### `POST /api/products/`

Pflicht: `title`, `purchase_price`, `sale_price`. Optional: `description`, `category`, `condition`,
`status`, `quantity` (Standard 1), `aspects`, `purchase_date`. `sku` lässt sich nicht mitgeben.

```json
{
  "title": "Vase blau, Keramik",
  "description": "Handgetöpfert, 24 cm hoch.",
  "category": 8,
  "condition": "very_good",
  "purchase_price": "6.00",
  "sale_price": "24.90",
  "quantity": 3,
  "purchase_date": "2026-09-30",
  "aspects": {"Marke": ["Ohne"]}
}
```

Antwort `201`: der Artikel wie in der Liste oben, mit vergebener Nummer `EK-000001`.

Fehler `400`, wenn Pflichtfelder fehlen:

```json
{"error": {"purchase_price": ["This field is required."], "sale_price": ["This field is required."]}}
```

`aspects` sind die Merkmale für die Portale in der Form `{"Name": ["Wert", …]}`.

### `GET|PUT|PATCH|DELETE /api/products/<id>/`

`PATCH` ändert einzelne Felder:

```json
{"sale_price": "22.90"}
```

Antwort `200`: der ganze Artikel, `profit` neu berechnet (`"16.90"`).

`DELETE` antwortet mit `204`, löscht Bilder und Bildordner und – über die `ebay_app` – auch den
Artikel bei eBay, falls er dort inseriert ist. Positionen in Bestellungen bleiben erhalten.

### `GET /api/products/counts/`

Berücksichtigt `category` und `search`, damit die Zahlen zu den Filtern passen.

```json
{"available": 5, "reserved": 0, "sold": 1, "archived": 0, "all": 6}
```

### `GET /api/products/<id>/images/` · `POST /api/products/<id>/images/`

Upload als `multipart/form-data` mit dem Feld `image`. Das Bild wird hinten angehängt.

Antwort `201`:

```json
{"id": 9, "image": "http://127.0.0.1:8000/media/products/EK-000001/vase.png", "position": 0}
```

Fehler: `400`, wenn keine Datei mitkommt (`{"error": {"image": ["No file was submitted."]}}`) oder
die Datei kein Bild ist; `404`, wenn es den Artikel nicht gibt.

### `DELETE /api/product-images/<id>/`

Antwort `204`; die Datei wird von der Festplatte entfernt.

## Anwendung

Ein Artikel von der Kategorie bis zum Bild:

```bash
curl -X POST http://127.0.0.1:8000/api/categories/ -H "Authorization: Bearer <token>" -H "Content-Type: application/json" -d '{"name": "Deko", "parent": null}'
```

```bash
curl -X POST http://127.0.0.1:8000/api/products/ -H "Authorization: Bearer <token>" -H "Content-Type: application/json" -d '{"title": "Vase blau, Keramik", "purchase_price": "6.00", "sale_price": "24.90", "quantity": 3}'
```

```bash
curl -X POST http://127.0.0.1:8000/api/products/38/images/ -H "Authorization: Bearer <token>" -F "image=@vase.png"
```

Im Frontend: **Artikel → + Neuer Artikel**, speichern, danach Bilder hinzufügen. Artikel, die aus
einem Inserat übernommen wurden, haben den Einkaufspreis 0 und sind in der Liste mit
„nachtragen" markiert.

## Verbindungen

- **`orders_app`** hängt `OrderItem.product` an und bucht `quantity` und `status`.
- **`finance_app`** liest `purchase_price`, `purchase_date` und die Kategorie.
- **`ebay_app`** hängt Inserat, gehostete Bilder und die Kategorie-Merkliste an und reagiert über
  Signals auf Änderungen. Wo ein Artikel inseriert ist, liefert `/api/ebay/listing-states/`.
- Aus **`core`**: Pagination und das Kürzel `SKU_PREFIX`.

## Dateien

| Datei | Inhalt |
|---|---|
| `models.py` | `Category`, `Product`, `ProductImage`, `SkuSequence` |
| `utils.py` | Artikelnummer, Listenfilter, Zähler je Status |
| `signals.py` | Aufräumen der Bilddateien |
| `apps.py` | registriert die Signals |
| `api/serializers.py`, `api/views.py`, `api/urls.py` | die API |
| `admin.py` | Kategorien, Artikel mit Bildern |
