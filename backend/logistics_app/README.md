# logistics_app

Lager und Logistik – plattform-neutral. Aktuell der **Lagerort**, von dem aus verschickt
wird; die App ist so angelegt, dass sie später wachsen kann.

> Ausbaustufen (später): mehrere Lager, Lagerplätze (Regal/Fach) pro Artikel,
> „Einlagern" und „Finden", interner Lagerstatus.

## Aufgaben

- Lagerorte pflegen (Adresse, von der verschickt wird)
- Genau einen Lagerort als Standard führen

## Models

- **`Warehouse`**: `name`, `street`, `zip_code`, `city`, `country` (ISO-Code, Default `DE`),
  `is_default`, Zeitstempel. `save()` sorgt dafür, dass immer genau ein Lagerort Standard
  ist (der erste automatisch). `Warehouse.default()` liefert ihn.

## Services / Logik

Keine eigenen. Der Serializer normalisiert den Ländercode (`de` → `DE`).

## API-Endpoints

| Methode | Pfad | Zweck |
|---|---|---|
| GET / POST | `/api/warehouses/` | Lagerorte auflisten (Standard zuerst) / anlegen |
| GET / PUT / PATCH / DELETE | `/api/warehouses/<id>/` | Einzelner Lagerort |

## Verbindungen

- **`ebay_app`**: überträgt den Standard-Lagerort als Inventory Location
  (`EbayLocation`, OneToOne). `logistics_app` kennt `ebay_app` nicht.

## Dateien

- `models.py` – `Warehouse`
- `api/serializers.py`, `api/views.py`, `api/urls.py`
- `admin.py` – `WarehouseAdmin`
