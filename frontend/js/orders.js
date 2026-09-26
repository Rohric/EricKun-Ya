"use strict";

requireAuth();
renderNav("orders.html");

const FULFILLMENT = {
  open: "Offen", packed: "Verpackt", shipped: "Verschickt", delivered: "Zugestellt",
};

let productsCache = [];

document.getElementById("new-order-btn").addEventListener("click", _openForm);
document.getElementById("cancel-order").addEventListener("click", _closeForm);
document.getElementById("add-item").addEventListener("click", () => _addItemRow());
document.getElementById("order-form").addEventListener("submit", _saveOrder);

init();

// Load products (for the item selects) and then the orders.
async function init() {
  try {
    productsCache = await apiGet("/products/");
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
      <td>${_statusSelect(o)}</td>
      <td>${formatEuro(o.total_revenue)}</td>
      <td>${formatEuro(o.total_profit)}</td>
      <td>${escapeHtml(o.tracking_number) || "–"}</td>
      <td>${_itemSummary(o.items)}</td>
    </tr>`).join("");
  document.getElementById("order-rows").innerHTML =
    rows || `<tr><td colspan="7" class="empty">Noch keine Bestellungen.</td></tr>`;
  _bindStatusSelects();
}

function _statusSelect(order) {
  const options = Object.entries(FULFILLMENT).map(([value, label]) =>
    `<option value="${value}" ${value === order.fulfillment_status ? "selected" : ""}>${label}</option>`
  ).join("");
  return `<select data-status="${order.id}">${options}</select>`;
}

function _itemSummary(items) {
  if (!items || !items.length) return "–";
  return items.map((i) => {
    const product = productsCache.find((p) => p.id === i.product);
    return `${i.quantity}× ${escapeHtml(product ? product.title : "#" + i.product)}`;
  }).join(", ");
}

function _bindStatusSelects() {
  document.querySelectorAll("[data-status]").forEach((sel) =>
    sel.addEventListener("change", () => _updateStatus(Number(sel.dataset.status), sel.value))
  );
}

async function _updateStatus(id, status) {
  try {
    await apiSend(`/orders/${id}/`, "PATCH", { fulfillment_status: status });
    showMessage("Status aktualisiert.", false);
  } catch (err) {
    showMessage(errorText(err));
  }
}

function _openForm() {
  document.getElementById("item-rows").innerHTML = "";
  _addItemRow();
  document.getElementById("order-form").style.display = "block";
  showMessage("", false);
}

function _closeForm() {
  document.getElementById("order-form").reset();
  document.getElementById("order-form").style.display = "none";
}

// Append an empty position row (product + price + quantity) to the form.
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

async function _saveOrder(e) {
  e.preventDefault();
  const items = _collectItems();
  if (!items.length) return showMessage("Mindestens eine Position nötig.");
  const payload = {
    sold_at: new Date(document.getElementById("o-sold-at").value).toISOString(),
    tracking_number: document.getElementById("o-tracking").value.trim(),
    items,
  };
  try {
    await apiSend("/orders/", "POST", payload);
    _closeForm();
    loadOrders();
  } catch (err) {
    showMessage(errorText(err));
  }
}

function _collectItems() {
  return Array.from(document.querySelectorAll(".item-row")).map((row) => ({
    product: Number(row.querySelector(".item-product").value),
    sold_price: row.querySelector(".item-price").value,
    quantity: Number(row.querySelector(".item-qty").value || 1),
  })).filter((i) => i.product && i.sold_price);
}

function _formatDate(iso) {
  return new Date(iso).toLocaleDateString("de-DE");
}
