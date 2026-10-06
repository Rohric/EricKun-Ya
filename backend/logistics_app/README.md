# logistics_app

## Kurzbeschreibung

Lager und Logistik, portal-neutral. Heute verwaltet die App den **Lagerort** – die Adresse, von
der verschickt wird.

**Abgrenzung:** keine Lagerplätze je Artikel, kein Wareneingang. Den Bestand führen
`products_app` (Menge) und `orders_app` (Buchungen). `logistics_app` kennt eBay nicht.

## Aufgaben

- Lagerorte mit Adresse pflegen
- Genau einen Lagerort als Standard führen

Geplante Ausbaustufen: mehrere Lager, Lagerplätze (Regal, Fach) je Artikel, Einlagern und Finden.

## Models

| Model | Felder | Hinweise |
|---|---|---|
| `Warehouse` | `name`, `street`, `zip_code`, `city`, `country`, `is_default`, `created_at`, `updated_at` | `country` ist ein zweistelliger Ländercode (Standard `DE`); `Warehouse.default()` liefert den Standard-Lagerort |

## Logik

- `Warehouse.save()` sorgt dafür, dass immer genau ein Lagerort Standard ist: Der erste wird es
  automatisch; wird ein anderer zum Standard, verliert ihn der bisherige.
- Der Serializer prüft und normalisiert den Ländercode (`de` → `DE`).

## API-Übersicht

| Methode | Pfad | Zweck |
|---|---|---|
| GET, POST | `/api/warehouses/` | Lagerorte auflisten (Standard zuerst), anlegen |
| GET, PUT, PATCH, DELETE | `/api/warehouses/<id>/` | einzelner Lagerort |

Alle Endpoints verlangen einen angemeldeten Nutzer.

## API im Detail

### `GET /api/warehouses/` · `POST /api/warehouses/`

Pflicht beim Anlegen: `name`, `street`, `zip_code`, `city`. Optional: `country`, `is_default`.

```json
{"name": "Keller", "street": "Musterstraße 1", "zip_code": "12345", "city": "Musterstadt", "country": "de"}
```

Antwort `201`:

```json
{
  "id": 4,
  "name": "Keller",
  "street": "Musterstraße 1",
  "zip_code": "12345",
  "city": "Musterstadt",
  "country": "DE",
  "is_default": false,
  "created_at": "2026-10-06T12:08:05.922253Z",
  "updated_at": "2026-10-06T12:08:05.922304Z"
}
```

`GET` liefert ein Array in dieser Form. Fehler `400` bei einem ungültigen Ländercode:
„Bitte einen 2-stelligen Ländercode angeben (z. B. DE)."

### `GET|PUT|PATCH|DELETE /api/warehouses/<id>/`

```json
{"name": "Kellerlager"}
```

Antwort `200`: der ganze Lagerort mit neuem `updated_at`. `PATCH {"is_default": true}` macht ihn
zum Standard. `DELETE` antwortet mit `204`.

## Anwendung

```bash
curl -X POST http://127.0.0.1:8000/api/warehouses/ -H "Authorization: Bearer <token>" -H "Content-Type: application/json" -d '{"name": "Lager", "street": "Musterstraße 1", "zip_code": "12345", "city": "Musterstadt"}'
```

Im Frontend: **Artikel → Lager**. Der Lagerort ist Voraussetzung für eBay: Er wird unter
**eBay → Vorlagen** als Artikelstandort übertragen. Nach einer Adressänderung dort erneut
übertragen – die Checkliste zeigt das an.

## Verbindungen

- **`ebay_app`** überträgt den Standard-Lagerort an eBay und merkt sich das in `EbayLocation`
  (OneToOne zu `Warehouse`). Die Abhängigkeit zeigt nur von dort hierher.

## Dateien

| Datei | Inhalt |
|---|---|
| `models.py` | `Warehouse` |
| `api/serializers.py`, `api/views.py`, `api/urls.py` | die API |
| `admin.py` | Lagerorte |
