"use strict";

requireAuth();
renderNav("orders.html");

const FULFILLMENT = {
  open: "Offen", packed: "Verpackt", shipped: "Verschickt",
  delivered: "Zugestellt", in_return: "In Reklamation", cancelled: "Storniert",
};

let productsCache = [];
let cancelOrderId = null;

document.getElementById("new-order-btn").addEventListener("click", _openNewForm);
document.getElementById("cancel-order").addEventListener("click", _closeForm);
document.getElementById("add-item").addEventListener("click", () => _addItemRow());
document.getElementById("order-form").addEventListener("submit", _saveOrder);
document.getElementById("o-status").addEventListener("change", _syncReklamation);
document.getElementById("confirm-cancel").addEventListener("click", _confirmCancel);
document.getElementById("abort-cancel").addEventListener("click", _closeCancelModal);

init();

// Load available products (for new-order positions) and the orders.
async function init() {
  try {
    productsCache = await apiGet("/products/?view=active");
    await loadOrders();
  } catch (err) {
    showMessage(errorText(err));
  }
}

async function loadOrders() {
  _renderRows(await apiGet("/orders/"));
}

function _renderRows(orders) {
  const rows = orders.map((o) => `
    <tr>
      <td>${o.id}</td>
      <td>${_formatDate(o.sold_at)}</td>
      <td><span class="badge badge-${o.fulfillment_status}">${FULFILLMENT[o.fulfillment_status] || o.fulfillment_status}</span></td>
      <td>${escapeHtml(o.buyer_name) || "–"}</td>
      <td>${escapeHtml(o.ship_city) || "–"}</td>
      <td>${formatEuro(o.total_revenue)}</td>
      <td>${formatEuro(o.total_profit)}</td>
      <td>${_itemSummary(o.items)}</td>
      <td class="actions">${_rowActions(o)}</td>
    </tr>`).join("");
  document.getElementById("order-rows").innerHTML =
    rows || `<tr><td colspan="9" class="empty">Noch keine Bestellungen.</td></tr>`;
  _bindRowActions(orders);
}

function _rowActions(order) {
  const edit = `<button data-edit="${order.id}" class="link-btn">Bearbeiten</button>`;
  if (order.fulfillment_status === "cancelled") return edit;
  return `${edit}<button data-cancel="${order.id}" class="link-btn danger">Storno</button>`;
}

function _itemSummary(items) {
  if (!items || !items.length) return "–";
  return items.map((i) => `${i.quantity}× ${escapeHtml(i.product_title)}`).join(", ");
}

function _bindRowActions(orders) {
  document.querySelectorAll("[data-edit]").forEach((btn) =>
    btn.addEventListener("click", () => _openEditForm(orders.find((o) => o.id === Number(btn.dataset.edit))))
  );
  document.querySelectorAll("[data-cancel]").forEach((btn) =>
    btn.addEventListener("click", () => _openCancelModal(Number(btn.dataset.cancel)))
  );
}

// --- Form ---

function _openNewForm() {
  const form = document.getElementById("order-form");
  form.reset();
  document.getElementById("order-id").value = "";
  document.getElementById("items-section").style.display = "block";
  document.getElementById("item-rows").innerHTML = "";
  _addItemRow();
  _syncReklamation();
  form.style.display = "block";
  showMessage("", false);
}

function _openEditForm(order) {
  const set = (id, value) => { document.getElementById(id).value = value ?? ""; };
  set("order-id", order.id);
  set("o-sold-at", _toLocalInput(order.sold_at));
  set("o-status", order.fulfillment_status === "cancelled" ? "open" : order.fulfillment_status);
  set("o-tracking", order.tracking_number);
  set("o-ebay", order.ebay_username);
  set("o-buyer", order.buyer_name);
  set("o-street", order.ship_street);
  set("o-zip", order.ship_zip);
  set("o-city", order.ship_city);
  set("o-country", order.ship_country);
  set("o-reklamation", order.reklamation_note);
  document.getElementById("items-section").style.display = "none";  // positions are fixed after creation
  _syncReklamation();
  document.getElementById("order-form").style.display = "block";
  showMessage("", false);
}

function _closeForm() {
  document.getElementById("order-form").reset();
  document.getElementById("order-form").style.display = "none";
}

function _syncReklamation() {
  const show = document.getElementById("o-status").value === "in_return";
  document.getElementById("reklamation-wrap").style.display = show ? "block" : "none";
}

async function _saveOrder(e) {
  e.preventDefault();
  const id = document.getElementById("order-id").value;
  try {
    if (id) {
      await apiSend(`/orders/${id}/`, "PATCH", _orderFields());
    } else {
      const items = _collectItems();
      if (!items.length) return showMessage("Mindestens eine Position nötig.");
      await apiSend("/orders/", "POST", Object.assign(_orderFields(), { items }));
    }
    _closeForm();
    loadOrders();
  } catch (err) {
    showMessage(errorText(err));
  }
}

function _orderFields() {
  return {
    sold_at: new Date(document.getElementById("o-sold-at").value).toISOString(),
    fulfillment_status: document.getElementById("o-status").value,
    tracking_number: _val("o-tracking"),
    ebay_username: _val("o-ebay"),
    buyer_name: _val("o-buyer"),
    ship_street: _val("o-street"),
    ship_zip: _val("o-zip"),
    ship_city: _val("o-city"),
    ship_country: _val("o-country"),
    reklamation_note: _val("o-reklamation"),
  };
}

// --- Positions (only when creating) ---

function _addItemRow() {
  const options = productsCache.map((p) =>
    `<option value="${p.id}">${escapeHtml(p.title)} (${escapeHtml(p.sku)})</option>`
  ).join("");
  const row = document.createElement("div");
  row.className = "item-row";
  row.innerHTML = `
    <select class="item-product">${options}</select>
    <input type="number" step="0.01" class="item-price" placeholder="Verkaufspreis" required />
    <input type="number" class="item-qty" value="1" min="1" />
    <button type="button" class="link-btn danger remove-item">✕</button>`;
  row.querySelector(".remove-item").addEventListener("click", () => row.remove());
  document.getElementById("item-rows").appendChild(row);
}

function _collectItems() {
  return Array.from(document.querySelectorAll(".item-row")).map((row) => ({
    product: Number(row.querySelector(".item-product").value),
    sold_price: row.querySelector(".item-price").value,
    quantity: Number(row.querySelector(".item-qty").value || 1),
  })).filter((i) => i.product && i.sold_price);
}

// --- Cancel modal ---

function _openCancelModal(orderId) {
  cancelOrderId = orderId;
  document.getElementById("cancel-modal").style.display = "flex";
}

function _closeCancelModal() {
  cancelOrderId = null;
  document.getElementById("cancel-modal").style.display = "none";
}

async function _confirmCancel() {
  const action = document.querySelector('input[name="item-action"]:checked').value;
  try {
    await apiSend(`/orders/${cancelOrderId}/cancel/`, "POST", { item_action: action });
    _closeCancelModal();
    showMessage("Bestellung storniert.", false);
    loadOrders();
  } catch (err) {
    showMessage(errorText(err));
  }
}

function _formatDate(iso) {
  return new Date(iso).toLocaleDateString("de-DE");
}

function _toLocalInput(iso) {
  const d = new Date(iso);
  const p = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`;
}

function _val(id) {
  return document.getElementById(id).value.trim();
}
