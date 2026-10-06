"use strict";

// eBay tab, panel "Verkäufe": the orders that came from eBay, with import and shipment report.
// loadSales() is called by ebay.js.

const SALE_SHIPPABLE = ["open", "packed"];

let salesOrders = [];

document.getElementById("sales-import-btn").addEventListener("click", _importSales);

async function loadSales(status) {
  _renderSyncedAt(status.orders_synced_at);
  salesOrders = await apiGet("/orders/?source=ebay");
  const rows = salesOrders.map(_saleRow).join("");
  document.getElementById("sales-rows").innerHTML =
    rows || `<tr><td colspan="8" class="empty">Noch keine eBay-Verkäufe.</td></tr>`;
  document.querySelectorAll("[data-sale-ship]").forEach((btn) =>
    btn.addEventListener("click", () => _shipSale(Number(btn.dataset.saleShip)))
  );
}

function _renderSyncedAt(syncedAt) {
  const text = syncedAt
    ? `Letzter Abruf: ${new Date(syncedAt).toLocaleString("de-DE")}. Beim Öffnen von Dashboard und Bestellungen wird automatisch abgeholt.`
    : "Es wurde noch nie abgeholt.";
  document.getElementById("sales-synced").textContent = text;
}

function _saleRow(order) {
  const items = order.items.map((item) => `${item.quantity}× ${escapeHtml(item.product_title)}`).join(", ");
  const buyer = [order.buyer_name, order.ebay_username].filter(Boolean).map(escapeHtml).join("<br>");
  return `
    <tr>
      <td>${order.id}</td>
      <td>${new Date(order.sold_at).toLocaleDateString("de-DE")}</td>
      <td>${buyer || "–"}</td>
      <td>${items || "–"}</td>
      <td>${formatEuro(order.total_revenue)}</td>
      <td>${_salePayment(order)}</td>
      <td>${_saleStatus(order)}</td>
      <td class="actions">${_saleActions(order)}</td>
    </tr>`;
}

function _salePayment(order) {
  if (order.fulfillment_status === "cancelled") return "–";
  const status = order.payment_status;
  return `<span class="badge badge-pay-${status}">${PAYMENT_LABELS[status] || status}</span>`;
}

function _saleStatus(order) {
  const status = order.fulfillment_status;
  const badge = `<span class="badge badge-${status}">${FULFILLMENT_LABELS[status] || status}</span>`;
  const tracking = order.tracking_number ? `${order.shipping_carrier} ${order.tracking_number}`.trim() : "";
  return tracking ? `${badge}<span class="row-note">${escapeHtml(tracking)}</span>` : badge;
}

function _saleActions(order) {
  const open = `<a class="link-btn" href="orders.html">Bestellungen</a>`;
  if (!SALE_SHIPPABLE.includes(order.fulfillment_status)) return open;
  if (order.payment_status !== "paid") {
    return `<button class="link-btn" disabled title="Die Zahlung ist noch offen.">Versand melden</button>${open}`;
  }
  return `<button type="button" class="link-btn" data-sale-ship="${order.id}">Versand melden</button>${open}`;
}

function _salesMessage(text, isError = true) {
  const box = document.getElementById("sales-message");
  box.textContent = text;
  box.className = isError ? "message error" : "message success";
  box.style.display = text ? "block" : "none";
}

function _shipSale(id) {
  const order = salesOrders.find((entry) => entry.id === id);
  openShipDialog(order, async () => {
    await refresh().catch(() => {});
    _salesMessage("Versand an eBay gemeldet.", false);
  });
}

async function _importSales() {
  const button = document.getElementById("sales-import-btn");
  button.disabled = true;
  let outcome;
  try {
    const result = await importEbayOrders();
    outcome = [ebayImportText(result), result.unknown_skus.length > 0];
  } catch (err) {
    outcome = [errorText(err), true];
  }
  await refresh().catch(() => {});
  _salesMessage(outcome[0], outcome[1]);
  button.disabled = false;
}
