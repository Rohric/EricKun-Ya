"use strict";

// Shared eBay order import for the dashboard and the orders page.

const EBAY_IMPORT_INTERVAL_MS = 10 * 60 * 1000;

// Fetch new and changed eBay sales; resolves to {created, cancelled, unknown_skus}.
function importEbayOrders() {
  return apiSend("/ebay/orders/import/", "POST", {});
}

// Import in the background when connected and the last run is older than the interval.
// Resolves to the import result, or null if nothing was done; never throws.
async function autoImportEbayOrders() {
  try {
    const status = await apiGet("/ebay/status/");
    if (!status.connected || !_ebayImportDue(status.orders_synced_at)) return null;
    return await importEbayOrders();
  } catch (err) {
    return null;  // the automatic run must never disturb the page
  }
}

function _ebayImportDue(lastSync) {
  return !lastSync || Date.now() - new Date(lastSync).getTime() > EBAY_IMPORT_INTERVAL_MS;
}

// Return true if an import result contains anything worth showing.
function ebayImportChanged(result) {
  return Boolean(result) && (result.created > 0 || result.cancelled > 0 || result.unknown_skus.length > 0);
}

// Turn an import result into a German sentence.
function ebayImportText(result) {
  if (!ebayImportChanged(result)) return "Keine neuen eBay-Verkäufe.";
  const parts = [];
  if (result.created) parts.push(`${result.created} neue${result.created === 1 ? "r Verkauf" : " Verkäufe"} von eBay`);
  if (result.cancelled) parts.push(`${result.cancelled} Storno von eBay übernommen`);
  if (result.unknown_skus.length) parts.push(`unbekannte Artikelnummer: ${result.unknown_skus.join(", ")}`);
  return `${parts.join(" · ")}.`;
}
