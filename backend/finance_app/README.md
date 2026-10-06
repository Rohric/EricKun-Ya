# finance_app

## Kurzbeschreibung

Kalkulationshilfe: Umsatz, Einkauf, geschätzte Gebühren, Steuerrücklage, Ziele und Auswertungen
je Verkauf, Kanal und Kategorie – für frei wählbare Zeiträume.

**Abgrenzung:** Orientierung, **keine Buchhaltung**. Zahlen fürs Finanzamt gehören in echte
Buchhaltungssoftware oder zum Steuerberater. Die eBay-Gebühren sind eine Schätzung über einen
einstellbaren Prozentsatz. Die App speichert nur Ziele und zwei Einstellungen; alles andere wird
aus `orders_app` und `products_app` berechnet.

## Aufgaben

- Umsatz, Einkauf und Gewinn für beliebige Zeiträume berechnen
- Steuerrechnung: Brutto-Gewinn = Steuerrücklage + Netto-Gewinn
- Monatsumsatz eines Jahres
- Verkaufsbericht je Position mit Einkaufspreis, Verkaufspreis, geschätzter Gebühr, Gewinn, Marge
- Aufteilung nach Kanal (eBay / eigene Verkäufe) und nach Kategorie
- Ziele (Umsatz oder Gewinn) mit berechnetem Fortschritt
- Rücklagensatz und geschätzten eBay-Gebührensatz verwalten

## Models

| Model | Felder | Hinweise |
|---|---|---|
| `Goal` | `title`, `target_amount`, `metric`, `period`, `start_date`, `end_date`, `is_active` | der Fortschritt ist kein Feld, er wird berechnet |
| `FinanceSettings` | `tax_reserve_rate`, `ebay_fee_rate` | eine Zeile; beide Werte in Prozent. Die Rücklage startet mit `TAX_RESERVE_RATE` aus der `.env`, der Gebührensatz mit 0 |

`metric`: `revenue`, `profit` · `period`: `monthly`, `yearly`, `total`

## Logik

Reine Berechnungen, nichts wird gespeichert.

**Was zählt:** nur Positionen aus Bestellungen, die **nicht storniert** und **bezahlt** sind.
Umsatz mit offener Zahlung wird getrennt ausgewiesen (`pending_revenue`).

`services.py`
- `revenue_for_period`, `pending_revenue_for_period`, `purchase_expenses_for_period`
- `estimated_fee`, `estimated_fees_for_period` – Gebührensatz × Umsatz der eBay-Verkäufe
- `profit_for_period` – Verkauf − Einkauf − geschätzte eBay-Gebühren. Dashboard, Steuerrechnung
  und Ziele rechnen dadurch gleich
- `tax_reserve`, `financial_summary`, `monthly_revenue` (zwölf Monate in einer Abfrage),
  `goal_progress`

`reports.py`
- `sales_report(start, end, category, channel)` – eine Zeile je verkaufter Position plus Summen.
  Der Kanal ergibt sich aus `Order.ebay_order_id`. Fehlt der Artikel einer Position, zählen
  Einkaufspreis, Gebühr und Gewinn als 0
- `breakdown(start, end, by)` – Summen je Kanal oder je Oberkategorie

Die Parameter der Berichte prüfen Serializer; ungültige Werte ergeben `400` mit deutscher Meldung.

## API-Übersicht

| Methode | Pfad | Zweck |
|---|---|---|
| GET, POST | `/api/goals/` | Ziele auflisten, anlegen |
| GET, PUT, PATCH, DELETE | `/api/goals/<id>/` | einzelnes Ziel |
| GET, PUT, PATCH | `/api/finance/settings/` | Rücklagensatz und Gebührensatz |
| GET | `/api/finance/reports/profit-loss/` | Steuerrechnung für einen Zeitraum |
| GET | `/api/finance/reports/monthly-revenue/` | zwölf Monatsumsätze |
| GET | `/api/finance/reports/sales/` | Verkaufsbericht je Position |
| GET | `/api/finance/reports/breakdown/` | Aufteilung nach Kanal oder Kategorie |

Alle Endpoints verlangen einen angemeldeten Nutzer. `from` und `to` haben das Format
`JJJJ-MM-TT`; fehlen sie, gilt das laufende Jahr.

## API im Detail

### `GET /api/goals/` · `POST /api/goals/`

Pflicht beim Anlegen: `title`, `target_amount`, `start_date`. Optional: `metric` (Standard
`revenue`), `period`, `end_date`, `is_active`.

```json
{"title": "Umsatz Oktober", "target_amount": "500.00", "metric": "revenue", "period": "monthly", "start_date": "2026-10-01"}
```

Antwort `201`:

```json
{
  "id": 3,
  "title": "Umsatz Oktober",
  "target_amount": "500.00",
  "metric": "revenue",
  "period": "monthly",
  "start_date": "2026-10-01",
  "end_date": null,
  "is_active": true,
  "progress": {"current": "67.20", "target": "500.00", "percent": "13.4"}
}
```

`progress` misst von `start_date` bis `end_date` (ohne Enddatum bis heute).

### `GET|PUT|PATCH|DELETE /api/goals/<id>/`

Wie oben für ein Ziel; `PATCH {"is_active": false}` deaktiviert es. `DELETE` antwortet mit `204`.

### `GET|PUT|PATCH /api/finance/settings/`

```json
{"ebay_fee_rate": "11.00"}
```

Antwort `200`:

```json
{"tax_reserve_rate": "25.00", "ebay_fee_rate": "11.00"}
```

Beide Werte müssen zwischen 0 und 100 liegen, sonst `400`:

```json
{"error": {"ebay_fee_rate": ["Ensure this value is less than or equal to 100."]}}
```

### `GET /api/finance/reports/profit-loss/?from=&to=`

```json
{
  "revenue": "67.20",
  "pending_revenue": "0.00",
  "expenses": "0.00",
  "estimated_fees": "7.39",
  "gross_profit": "46.81",
  "tax_reserve": "11.70",
  "net_profit": "35.11",
  "from": "2026-10-01",
  "to": "2026-10-31",
  "tax_rate": "25.00"
}
```

`expenses` ist die Summe der Einkaufspreise der Artikel, deren Einkaufsdatum im Zeitraum liegt.
`gross_profit` enthält die geschätzten Gebühren bereits als Abzug.

Fehler `400`:

```json
{"error": {"from": ["Ungültiges Datum (Format JJJJ-MM-TT)."]}}
```

Liegt `from` nach `to`:

```json
{"error": {"non_field_errors": ["„von“ darf nicht nach „bis“ liegen."]}}
```

### `GET /api/finance/reports/monthly-revenue/?year=`

Ohne `year` das laufende Jahr; erlaubt sind 2000 bis 2100.

```json
{"year": 2026, "monthly_revenue": ["0.00", "0.00", "0.00", "0.00", "0.00", "0.00", "0.00", "0.00", "0.00", "67.20", "0.00", "0.00"]}
```

### `GET /api/finance/reports/sales/?from=&to=&category=&channel=`

`category` ist die ID einer Kategorie, `channel` ist `ebay` oder `manual`.

```json
{
  "from": "2026-10-01",
  "to": "2026-10-31",
  "rows": [
    {
      "date": "2026-10-06 09:34:00+00:00",
      "order": 5,
      "channel": "ebay",
      "channel_label": "eBay",
      "title": "Fotodruck Reisfeld mit Torii 40x30 cm",
      "sku": "ART-05092934",
      "category": "",
      "category_group": "Ohne Kategorie",
      "quantity": 1,
      "purchase_price": "4.00",
      "sold_price": "19.90",
      "revenue": "19.90",
      "fee": "2.19",
      "profit": "13.71",
      "margin": "68.9"
    }
  ],
  "totals": {"revenue": "67.20", "fee": "7.40", "profit": "46.80", "positions": 4, "quantity": 4, "margin": "69.6"},
  "fee_rate": "11.00"
}
```

Die Summe der Gebühren kann um einen Cent von `estimated_fees` der Steuerrechnung abweichen: hier
wird je Position gerundet, dort einmal über den Gesamtumsatz.

Fehler `400` bei unbekanntem Kanal:

```json
{"error": {"channel": ["Unbekannter Kanal. Erlaubt: ebay, manual."]}}
```

### `GET /api/finance/reports/breakdown/?from=&to=&by=`

`by` ist `channel` (Standard) oder `category`.

```json
{
  "from": "2026-10-01",
  "to": "2026-10-31",
  "by": "channel",
  "groups": [
    {"key": "ebay", "label": "eBay", "revenue": "67.20", "fee": "7.40", "profit": "46.80", "positions": 4, "quantity": 4, "margin": "69.6"}
  ]
}
```

## Anwendung

Wie viel bleibt in diesem Monat übrig?

```bash
curl "http://127.0.0.1:8000/api/finance/reports/profit-loss/?from=2026-10-01&to=2026-10-31" -H "Authorization: Bearer <token>"
```

Welche Verkäufe über eBay haben sich gelohnt?

```bash
curl "http://127.0.0.1:8000/api/finance/reports/sales/?from=2026-10-01&to=2026-10-31&channel=ebay" -H "Authorization: Bearer <token>"
```

Im Frontend: **Dashboard → Finanzen** mit den Reitern Übersicht, Verkäufe, Aufteilung, Ziele,
Einstellungen. Zuerst unter „Einstellungen" den eBay-Gebührensatz eintragen, sonst rechnet der
Gewinn ohne Gebühren.

## Verbindungen

- **`orders_app`**: liest `OrderItem`, `Order.sold_at`, `Order.payment_status` und
  `Order.ebay_order_id` (für den Kanal).
- **`products_app`**: liest `purchase_price`, `purchase_date` und die Kategorie.
- **`core`**: `core/dashboard.py` nutzt Umsatz und Gewinn für die Dashboard-Kachel.

## Dateien

| Datei | Inhalt |
|---|---|
| `models.py` | `Goal`, `FinanceSettings` |
| `services.py` | Summen, Steuerrechnung, Gebührenschätzung, Ziel-Fortschritt |
| `reports.py` | Verkaufsbericht und Aufteilung |
| `api/serializers.py` | Ziel und Einstellungen, Prüfung der Berichts-Parameter |
| `api/views.py`, `api/urls.py` | die API |
| `admin.py` | Ziele, Einstellungen |
