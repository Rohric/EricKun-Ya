# finance_app

Kalkulationshilfe: Ziele, Steuerrechnung, Monatsumsatz, Einkaufsausgaben und Auswertungen
je Verkauf, Kanal und Kategorie – für frei wählbare Zeiträume.

> **GoBD-Leitplanke:** Orientierung, keine rechtssichere Buchhaltung. Zahlen fürs
> Finanzamt gehören in echte Buchhaltungssoftware bzw. zum Steuerberater. Die eBay-Gebühren
> sind eine **Schätzung** über einen einstellbaren Prozentsatz, keine echten Gebühren.

## Aufgaben

- Ziele (Umsatz oder Gewinn) anlegen, bearbeiten, (de)aktivieren, Fortschritt berechnen
- **Steuerrechnung:** Brutto-Gewinn = Steuerrücklage + Netto-Gewinn
- Umsatz, Einkauf und Gewinn für beliebige Zeiträume
- Monatsumsatz eines wählbaren Jahres
- Verkaufsbericht: je verkaufter Position Einkaufspreis, Verkaufspreis, geschätzte Gebühr,
  Gewinn und Marge – filterbar nach Kategorie und Kanal
- Aufteilung von Umsatz und Gewinn nach Kanal (eBay / manuell) und nach Kategorie
- Rücklagensatz und geschätzter eBay-Gebührensatz jederzeit änderbar

## Models

- **`Goal`**: `title`, `target_amount`, `metric` (Umsatz / Gewinn), `period`
  (monatlich / jährlich / gesamt), `start_date`, `end_date` (optional), `is_active`.
  Der Fortschritt ist **kein Feld**, er wird berechnet.
- **`FinanceSettings`**: Singleton (`pk=1`) mit `tax_reserve_rate` und `ebay_fee_rate`
  (beide in Prozent, Gebührensatz Standard 0); `load()` legt die Zeile beim ersten Zugriff an
  (Default der Rücklage aus `TAX_RESERVE_RATE`).

## Services / Logik

Reine Berechnungen, nichts wird gespeichert.

`services.py`
- `counted_items` – Positionen im Zeitraum, **ohne stornierte Bestellungen und ohne
  Bestellungen mit offener Zahlung**; filtert über einen Datetime-Bereich, damit der Index
  auf `sold_at` greift
- `revenue_for_period`, `pending_revenue_for_period` (Umsatz mit offener Zahlung, getrennt
  ausgewiesen), `purchase_expenses_for_period`
- `estimated_fee`, `estimated_fees_for_period` – Gebührensatz × Umsatz der eBay-Verkäufe
- `profit_for_period` – Verkauf − Einkauf − geschätzte eBay-Gebühren; Dashboard,
  Steuerrechnung und Ziele rechnen dadurch einheitlich
- `tax_reserve`, `financial_summary`, `monthly_revenue` (12 Monate in **einer** Query),
  `goal_progress`

`reports.py`
- `sales_report(start, end, category, channel)` – Zeilen je verkaufter Position plus Summen.
  Der Kanal ergibt sich aus `Order.ebay_order_id`. Fehlt der Artikel einer Position, sind
  Einkaufspreis, Gebühr und Gewinn unbekannt und zählen als 0.
- `breakdown(start, end, by)` – Summen je Kanal oder je Oberkategorie

Query-Parameter werden über Serializer validiert (`ReportRangeSerializer`,
`ReportYearSerializer`, `SalesFilterSerializer`, `BreakdownSerializer`) – ungültige Werte
liefern 400 mit deutscher Meldung.

## API-Endpoints

| Methode | Pfad | Zweck |
|---|---|---|
| GET / POST | `/api/goals/` | Ziele auflisten (inkl. `progress`) / anlegen |
| GET / PUT / PATCH / DELETE | `/api/goals/<id>/` | Einzelnes Ziel |
| GET / PUT / PATCH | `/api/finance/settings/` | `tax_reserve_rate`, `ebay_fee_rate` lesen / ändern (0–100) |
| GET | `/api/finance/reports/profit-loss/?from=&to=` | `revenue`, `pending_revenue`, `expenses`, `estimated_fees`, `gross_profit`, `tax_reserve`, `net_profit`, `tax_rate` (Default: laufendes Jahr) |
| GET | `/api/finance/reports/monthly-revenue/?year=` | 12 Monatsumsätze |
| GET | `/api/finance/reports/sales/?from=&to=&category=&channel=` | `rows`, `totals`, `fee_rate`; `channel` = `ebay` \| `manual` |
| GET | `/api/finance/reports/breakdown/?from=&to=&by=` | `groups`; `by` = `channel` (Default) \| `category` |

## Verbindungen

- **`orders_app`**: liest `OrderItem` (nach `Order.sold_at`), `Order.payment_status` und
  `Order.ebay_order_id` (für den Kanal).
- **`products_app`**: liest `purchase_price` / `purchase_date` und die Kategorie.
- **`core`**: `core/dashboard.py` nutzt Umsatz und Gewinn für die Dashboard-Kachel.

## Dateien

- `models.py` – `Goal`, `FinanceSettings`
- `services.py` – Summen, Steuerrechnung, Gebührenschätzung, Ziel-Fortschritt
- `reports.py` – Verkaufsbericht und Aufteilung
- `api/serializers.py` – Goal-/Settings-Serializer + Parameter-Validierung
- `api/views.py`, `api/urls.py` – API
- `admin.py` – `GoalAdmin`, `FinanceSettingsAdmin`
