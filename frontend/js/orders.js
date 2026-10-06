"use strict";

requireAuth();
renderNav("orders.html");

const CANCEL_SOURCES = { manual: "Manuell storniert", ebay: "Bei eBay storniert" };
const SHIPPABLE = ["open", "packed"];
const FILTER_IDS = { source: "filter-source", payment: "filter-payment", status: "filter-status" };

let productsCache = [];
let ordersCache = [];
let currentPage = 1;
let cancelOrderId = null;
let editedOrder = null;  // order shown in the form, null while creating

document.getElementById("new-order-btn").addEventListener("click", _openNewForm);
document.getElementById("ebay-import-btn").addEventListener("click", _importFromEbay);
document.getElementById("cancel-order").addEventListener("click", _closeForm);
document.getElementById("add-item").addEventListener("click", () => _addItemRow());
document.getElementById("order-form").addEventListener("submit", _saveOrder);
document.getElementById("o-status").addEventListener("change", _statusChanged);
document.getElementById("confirm-cancel").addEventListener("click", _confirmCancel);
document.getElementById("abort-cancel").addEventListener("click", _closeCancelModal);
document.getElementById("filter-reset").addEventListener("click", _resetFilters);
Object.values(FILTER_IDS).forEach((id) =>
  document.getElementById(id).addEventListener("change", _applyFilters)
);

init();

async function init() {
  try {
    await _loadProductsCache();
    await loadOrders();
  } catch (err) {
    showMessage(errorText(err));
  }
  _autoImport();
}

// Load active products that still have stock (for new-order positions).
async function _loadProductsCache() {
  productsCache = (await apiGet("/products/?view=active")).filter((p) => p.quantity > 0);
}

function _reloadAll() {
  return Promise.all([loadOrders(), _loadProductsCache()]);
}

// --- eBay import ---

// Background import when the page opens; only speaks up if something came in.
async function _autoImport() {
  const result = await autoImportEbayOrders();
  if (!ebayImportChanged(result)) return;
  showMessage(ebayImportText(result), false);
  await _reloadAll().catch(() => {});
}

async function _importFromEbay() {
  const button = document.getElementById("ebay-import-btn");
  button.disabled = true;
  try {
    const result = await importEbayOrders();
    showMessage(ebayImportText(result), result.unknown_skus.length > 0);
    currentPage = 1;
    await _reloadAll();
  } catch (err) {
    showMessage(errorText(err));
  }
  button.disabled = false;
}

// --- Filters, list and paging ---

function _applyFilters() {
  currentPage = 1;
  loadOrders().catch((err) => showMessage(errorText(err)));
}

function _resetFilters() {
  Object.values(FILTER_IDS).forEach((id) => { document.getElementById(id).value = ""; });
  _applyFilters();
}

function _listQuery() {
  const params = new URLSearchParams({ page: currentPage });
  Object.entries(FILTER_IDS).forEach(([name, id]) => {
    const value = inputValue(id);
    if (value) params.set(name, value);
  });
  return params;
}

async function loadOrders() {
  const data = await apiGet(`/orders/?${_listQuery()}`);
  ordersCache = data.results;
  _renderRows(ordersCache);
  renderPager("order-pager", data, currentPage, _goToPage);
}

function _goToPage(page) {
  currentPage = page;
  loadOrders().catch((err) => showMessage(errorText(err)));
}

function _renderRows(orders) {
  const rows = orders.map((o) => `
    <tr>
      <td>${o.id}${o.ebay_order_id ? ' <span class="chip">eBay</span>' : ""}</td>
      <td>${_formatDate(o.sold_at)}</td>
      <td>${_statusCell(o)}</td>
      <td>${_paymentBadge(o)}</td>
      <td>${escapeHtml(o.buyer_name) || "–"}</td>
      <td>${escapeHtml(o.ship_city) || "–"}</td>
      <td>${formatEuro(o.total_revenue)}</td>
      <td>${formatEuro(o.total_profit)}</td>
      <td>${_itemSummary(o.items)}</td>
      <td class="actions">${_rowActions(o)}</td>
    </tr>`).join("");
  document.getElementById("order-rows").innerHTML =
    rows || `<tr><td colspan="10" class="empty">Keine Bestellungen.</td></tr>`;
  _bindRowActions();
}

// Status badge plus tracking (shipped) or the cancellation reason (cancelled).
function _statusCell(order) {
  const status = order.fulfillment_status;
  const badge = `<span class="badge badge-${status}">${FULFILLMENT_LABELS[status] || status}</span>`;
  return badge + _statusNote(order);
}

function _statusNote(order) {
  const note = (text) => `<span class="row-note">${escapeHtml(text)}</span>`;
  if (order.cancellation) {
    const source = CANCEL_SOURCES[order.cancellation.source] || "";
    return note(order.cancellation.reason ? `${source}: ${order.cancellation.reason}` : source);
  }
  if (order.tracking_number) return note(`${order.shipping_carrier} ${order.tracking_number}`.trim());
  return "";
}

function _paymentBadge(order) {
  if (order.fulfillment_status === "cancelled") return "–";
  const status = order.payment_status;
  return `<span class="badge badge-pay-${status}">${PAYMENT_LABELS[status] || status}</span>`;
}

function _rowActions(order) {
  const edit = `<button data-edit="${order.id}" class="link-btn">Bearbeiten</button>`;
  if (order.fulfillment_status === "cancelled") return edit;
  return `${edit}${_shipButton(order)}<button data-cancel="${order.id}" class="link-btn danger">Storno</button>`;
}

// "Versand melden" exists for eBay orders that wait for shipping; it is locked until they are paid.
function _shipButton(order) {
  if (!order.ebay_order_id || !SHIPPABLE.includes(order.fulfillment_status)) return "";
  if (order.payment_status !== "paid") {
    return `<button class="link-btn" disabled title="Die Zahlung ist noch offen.">Versand melden</button>`;
  }
  return `<button data-ship="${order.id}" class="link-btn">Versand melden</button>`;
}

function _itemSummary(items) {
  if (!items || !items.length) return "–";
  return items.map((i) => `${i.quantity}× ${escapeHtml(i.product_title)}`).join(", ");
}

function _bindRowActions() {
  const bind = (attr, handler) => document.querySelectorAll(`[data-${attr}]`).forEach((btn) =>
    btn.addEventListener("click", () => handler(_orderById(btn.getAttribute(`data-${attr}`))))
  );
  bind("edit", _openEditForm);
  bind("cancel", _openCancelModal);
  bind("ship", _reportShipment);
}

function _orderById(id) {
  return ordersCache.find((order) => order.id === Number(id));
}

function _reportShipment(order) {
  openShipDialog(order, async () => {
    _closeForm();
    showMessage("Versand an eBay gemeldet.", false);
    await loadOrders().catch((err) => showMessage(errorText(err)));
  });
}

// --- Form ---

function _openNewForm() {
  if (!productsCache.length) return showMessage("Kein Artikel mit Bestand verfügbar.");
  const form = document.getElementById("order-form");
  form.reset();
  editedOrder = null;
  document.getElementById("order-id").value = "";
  document.getElementById("item-rows").innerHTML = "";
  _setItemsEditable(true);
  _applyEbayRules(null);
  _addItemRow();
  _syncReturnNote();
  form.style.display = "block";
  showMessage("", false);
}

function _openEditForm(order) {
  const set = (id, value) => { document.getElementById(id).value = value ?? ""; };
  editedOrder = order;
  set("order-id", order.id);
  set("o-sold-at", _toLocalInput(order.sold_at));
  set("o-status", order.fulfillment_status === "cancelled" ? "open" : order.fulfillment_status);
  set("o-payment", order.payment_status);
  set("o-tracking", order.tracking_number);
  set("o-ebay", order.ebay_username);
  set("o-buyer", order.buyer_name);
  set("o-street", order.ship_street);
  set("o-zip", order.ship_zip);
  set("o-city", order.ship_city);
  set("o-country", order.ship_country);
  set("o-return-note", order.return_note);
  _setItemsEditable(false);
  _applyEbayRules(order);
  _syncReturnNote();
  document.getElementById("order-form").style.display = "block";
  showMessage("", false);
}

// eBay orders: payment and tracking come from eBay, "Zugestellt" needs a reported shipment first.
function _applyEbayRules(order) {
  const fromEbay = Boolean(order && order.ebay_order_id);
  const wasShipped = Boolean(order) && ["shipped", "delivered"].includes(order.fulfillment_status);
  document.getElementById("ebay-order-hint").style.display = fromEbay ? "block" : "none";
  document.getElementById("o-payment").disabled = fromEbay;
  document.getElementById("o-tracking").disabled = fromEbay;
  document.querySelector('#o-status option[value="delivered"]').disabled = fromEbay && !wasShipped;
}

// Show the position editor when creating, the 'positions are fixed' hint when editing.
function _setItemsEditable(editable) {
  document.getElementById("items-section").style.display = editable ? "block" : "none";
  document.getElementById("items-locked-hint").style.display = editable ? "none" : "block";
}

function _closeForm() {
  document.getElementById("order-form").reset();
  document.getElementById("order-form").style.display = "none";
  editedOrder = null;
}

// Choosing "Verschickt" for an eBay order opens the shipment dialog instead of changing the status.
function _statusChanged() {
  const order = editedOrder;
  const needsEbay = order && order.ebay_order_id && order.fulfillment_status !== "shipped";
  if (needsEbay && inputValue("o-status") === "shipped") {
    document.getElementById("o-status").value = order.fulfillment_status;
    if (order.payment_status !== "paid") return showMessage("Die Zahlung ist noch offen – erst danach verschicken.");
    return _reportShipment(order);
  }
  _syncReturnNote();
}

function _syncReturnNote() {
  const show = inputValue("o-status") === "in_return";
  document.getElementById("return-note-wrap").style.display = show ? "block" : "none";
}

async function _saveOrder(e) {
  e.preventDefault();
  const id = inputValue("order-id");
  try {
    if (id) await apiSend(`/orders/${id}/`, "PATCH", _orderFields());
    else await _createOrder();
    _closeForm();
    await _reloadAll();
  } catch (err) {
    showMessage(errorText(err));
  }
}

async function _createOrder() {
  const items = _collectItems();
  if (!items.length) throw new ApiError(400, "Mindestens eine Position nötig.");
  await apiSend("/orders/", "POST", Object.assign(_orderFields(), { items }));
  currentPage = 1;
}

function _orderFields() {
  const fields = {
    sold_at: new Date(inputValue("o-sold-at")).toISOString(),
    fulfillment_status: inputValue("o-status"),
    ebay_username: inputValue("o-ebay"),
    buyer_name: inputValue("o-buyer"),
    ship_street: inputValue("o-street"),
    ship_zip: inputValue("o-zip"),
    ship_city: inputValue("o-city"),
    ship_country: inputValue("o-country"),
    return_note: inputValue("o-return-note"),
  };
  if (editedOrder && editedOrder.ebay_order_id) return fields;  // payment and tracking come from eBay
  return Object.assign(fields, { payment_status: inputValue("o-payment"), tracking_number: inputValue("o-tracking") });
}

// --- Positions (only when creating) ---

function _addItemRow() {
  const options = productsCache.map((p) =>
    `<option value="${p.id}">${escapeHtml(p.title)} (${escapeHtml(p.sku)}) – ${p.quantity} verfügbar</option>`
  ).join("");
  const row = document.createElement("div");
  row.className = "item-row";
  row.innerHTML = `
    <select class="item-product">${options}</select>
    <input type="number" step="0.01" class="item-price" placeholder="Verkaufspreis" required />
    <input type="number" class="item-qty" value="1" min="1" />
    <button type="button" class="link-btn danger remove-item">✕</button>`;
  row.querySelector(".remove-item").addEventListener("click", () => row.remove());
  _syncItemRow(row);
  document.getElementById("item-rows").appendChild(row);
}

// Prefill the sale price and cap the quantity at the selected product's stock.
function _syncItemRow(row) {
  const select = row.querySelector(".item-product");
  const sync = () => {
    const product = productsCache.find((p) => p.id === Number(select.value));
    row.querySelector(".item-qty").max = product ? product.quantity : 1;
    row.querySelector(".item-price").value = product ? product.sale_price : "";
  };
  select.addEventListener("change", sync);
  sync();
}

function _collectItems() {
  return Array.from(document.querySelectorAll(".item-row")).map((row) => ({
    product: Number(row.querySelector(".item-product").value),
    sold_price: row.querySelector(".item-price").value,
    quantity: Number(row.querySelector(".item-qty").value || 1),
  })).filter((i) => i.product && i.sold_price);
}

// --- Cancel modal ---

function _openCancelModal(order) {
  cancelOrderId = order.id;
  document.getElementById("cancel-reason").value = "";
  document.getElementById("cancel-ebay-hint").style.display = order.ebay_order_id ? "block" : "none";
  document.getElementById("cancel-modal").style.display = "flex";
}

function _closeCancelModal() {
  cancelOrderId = null;
  document.getElementById("cancel-modal").style.display = "none";
}

async function _confirmCancel() {
  const action = document.querySelector('input[name="item-action"]:checked').value;
  const payload = { item_action: action, reason: inputValue("cancel-reason") };
  try {
    await apiSend(`/orders/${cancelOrderId}/cancel/`, "POST", payload);
    _closeCancelModal();
    showMessage("Bestellung storniert.", false);
    await _reloadAll();
  } catch (err) {
    _closeCancelModal();
    showMessage(errorText(err));
  }
}

function _formatDate(iso) {
  return new Date(iso).toLocaleDateString("de-DE");
}

function _toLocalInput(iso) {
  const d = new Date(iso);
  const p = (n) => String(n).padStart(2, "0");
  return `${isoDate(d)}T${p(d.getHours())}:${p(d.getMinutes())}`;
}
