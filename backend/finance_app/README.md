# finance_app

Kalkulationshilfe: Ziele, Gewinn/Verlust-Auswertungen, Monatsumsatz und eine
Steuer-Rücklagen-Schätzung.

> **GoBD-Leitplanke:** Diese App ist **Orientierung/Kalkulation**, keine rechtssichere
> Buchhaltung. Zahlen fürs Finanzamt gehören in echte Buchhaltungssoftware bzw. zum
> Steuerberater – hierhin wird höchstens exportiert.

## Aufgabe

- Sparziele definieren und deren Fortschritt anzeigen
- Gewinn/Verlust über einen Zeitraum berechnen
- Monatsumsatz und Einkaufsverlauf auswerten
- Steuer-Rücklage schätzen (Prozentsatz jederzeit änderbar)

## Models

- **`Goal`**: `title`, `target_amount`, `metric` (`TextChoices`: Umsatz/Gewinn – **pro Ziel
  wählbar**), `period` (monatlich/jährlich/gesamt), `start_date`, `end_date` (optional),
  `is_active`. **Fortschritt ist kein Feld** – er wird aus den Orders berechnet.
- **`FinanceSettings`**: Singleton (`pk=1`) mit `tax_reserve_rate` (Prozent), jederzeit
  über die API/Admin änderbar. `load()` liefert die Zeile (Default aus `TAX_RESERVE_RATE`).

## Services (`services.py`)

Reine Berechnungen (keine gespeicherten Ergebnisse):
`revenue_for_period`, `profit_for_period`, `purchase_expenses_for_period`,
`monthly_revenue(year)`, `tax_reserve(profit)`, `goal_progress(goal)`.

## Endpoints

| Methode | Pfad | Zweck |
|---|---|---|
| GET / POST | `/api/goals/` | Ziele auflisten / anlegen (Antwort enthält `progress`) |
| GET / PUT / PATCH / DELETE | `/api/goals/<id>/` | Einzelnes Ziel |
| GET / PUT / PATCH | `/api/finance/settings/` | Rücklagensatz lesen/ändern (Singleton) |
| GET | `/api/finance/reports/profit-loss/?from=&to=` | Umsatz, Gewinn, Ausgaben, Rücklage |
| GET | `/api/finance/reports/monthly-revenue/?year=` | 12 Monatsumsätze eines Jahres |

Alle Endpoints erfordern Authentifizierung.

## Verbindungen

- **`orders_app`**: liest `OrderItem` (nach `Order.sold_at`) für Umsatz/Gewinn/Ziel-Fortschritt.
- **`products_app`**: liest `purchase_price` / `purchase_date` für den Einkaufsverlauf.

## Dateien

- `models.py` – `Goal`, `FinanceSettings`
- `services.py` – Auswertungs-Logik
- `api/serializers.py`, `api/views.py`, `api/urls.py` – API
- `admin.py` – `GoalAdmin`, `FinanceSettingsAdmin`
