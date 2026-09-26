# finance_app

Kalkulationshilfe: Ziele, Steuerrechnung, Monatsumsatz und Einkaufsausgaben – für
frei wählbare Zeiträume.

> **GoBD-Leitplanke:** Orientierung, keine rechtssichere Buchhaltung. Zahlen fürs
> Finanzamt gehören in echte Buchhaltungssoftware bzw. zum Steuerberater.

## Aufgaben

- Ziele (Umsatz oder Gewinn) anlegen, bearbeiten, (de)aktivieren, Fortschritt berechnen
- **Steuerrechnung:** Brutto-Gewinn = Steuerrücklage + Netto-Gewinn
- Umsatz, Einkauf und Gewinn für beliebige Zeiträume
- Monatsumsatz eines wählbaren Jahres
- Rücklagensatz jederzeit änderbar

## Models

- **`Goal`**: `title`, `target_amount`, `metric` (Umsatz / Gewinn), `period`
  (monatlich / jährlich / gesamt), `start_date`, `end_date` (optional), `is_active`.
  Der Fortschritt ist **kein Feld**, er wird berechnet.
- **`FinanceSettings`**: Singleton (`pk=1`) mit `tax_reserve_rate` in Prozent;
  `load()` legt die Zeile beim ersten Zugriff an (Default aus `TAX_RESERVE_RATE`).

## Services / Logik

Reine Berechnungen in `services.py`, nichts wird gespeichert:
- `_items_in_period` – Positionen im Zeitraum, **ohne stornierte Bestellungen**; filtert
  über einen Datetime-Bereich, damit der Index auf `sold_at` greift
- `revenue_for_period`, `profit_for_period`, `purchase_expenses_for_period`
- `tax_reserve`, `financial_summary` (Umsatz, Einkauf, Brutto, Rücklage, Netto)
- `monthly_revenue` – alle 12 Monate in **einer** gruppierten Query
- `goal_progress`

Query-Parameter werden über `ReportRangeSerializer` / `ReportYearSerializer` validiert –
ungültige Werte liefern 400 mit deutscher Meldung.

## API-Endpoints

| Methode | Pfad | Zweck |
|---|---|---|
| GET / POST | `/api/goals/` | Ziele auflisten (inkl. `progress`) / anlegen |
| GET / PUT / PATCH / DELETE | `/api/goals/<id>/` | Einzelnes Ziel |
| GET / PUT / PATCH | `/api/finance/settings/` | Rücklagensatz lesen / ändern |
| GET | `/api/finance/reports/profit-loss/?from=&to=` | `revenue`, `expenses`, `gross_profit`, `tax_reserve`, `net_profit`, `tax_rate` (Default: laufendes Jahr) |
| GET | `/api/finance/reports/monthly-revenue/?year=` | 12 Monatsumsätze |

## Verbindungen

- **`orders_app`**: liest `OrderItem` (nach `Order.sold_at`, ohne stornierte).
- **`products_app`**: liest `purchase_price` / `purchase_date` für den Einkauf.

## Dateien

- `models.py` – `Goal`, `FinanceSettings`
- `services.py` – Auswertungslogik
- `api/serializers.py` – Goal-/Settings-Serializer + Parameter-Validierung
- `api/views.py`, `api/urls.py` – API
- `admin.py` – `GoalAdmin`, `FinanceSettingsAdmin`
