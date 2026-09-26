# ebay_app

> **Status: geplant / noch nicht implementiert.** Aktuell ein leeres Gerüst; wird in einem
> eigenen Durchgang gebaut (eBay-OAuth + Inventory/Fulfillment API).

Adapter **und** Zustands-Halter für den Verkaufskanal eBay. Kein reiner API-Client –
speichert eigenen State (welcher Artikel ist online, verkauft, zuletzt synchronisiert),
damit nicht bei jedem Blick live gegen die eBay-API abgefragt werden muss.

## Geplante Aufgabe

- Artikel aus `products_app` auf eBay **inserieren** (Inventory Item → Offer → Publish)
- eBay-seitigen Zustand halten und synchronisieren (online / verkauft / beendet)
- eBay-OAuth-Tokens (access/refresh) sicher speichern und erneuern
- Duplikat-Schutz beim Inserieren (Guard + OneToOne + eBays `createOrReplace`)

## Geplantes Model

- **`EbayListing`**: OneToOne zu `Product` (`related_name="ebay_listing"`), `offer_id`,
  `listing_id`, `category_id` (eBay-spezifisch, **nicht** im Product), `status`
  (`TextChoices`: draft/online/sold/ended), `last_synced`.
  - `has_unsynced_changes` als **`@property`** (lokale Änderung neuer als letzter Sync).

## Geplante Endpoints

- Publish-Flow (Artikel → eBay), Sync-Trigger (Zustand von eBay zurückholen).
  Konkrete Pfade werden beim Bau festgelegt.

## Verbindungen

- Importiert `Product` aus `products_app` (**einseitige** Code-Abhängigkeit).
- Verkaufsdaten wandern später in `orders_app` (der `sold_at`-Platzhalter verlässt dann
  `EbayListing`).

## Technischer Kontext

Siehe Übergabeprotokoll §6 und §10 (Sell Inventory API, OAuth 2.0, Business Policies +
Location als Publish-Voraussetzung, Taxonomy API für Kategorien/Aspekte, erst Sandbox).
