"use strict";

requireAuth();
renderNav("products.html");

const CONDITION_LABELS = {
  new: "Neu", like_new: "Wie neu", very_good: "Sehr gut",
  good: "Gut", acceptable: "Akzeptabel", for_parts: "Defekt / Ersatzteile",
};

document.getElementById("new-product-btn").addEventListener("click", () => _openForm());
document.getElementById("cancel-product").addEventListener("click", _closeForm);
document.getElementById("product-form").addEventListener("submit", _saveProduct);

loadProducts();

// Load all products and render them into the table.
async function loadProducts() {
  try {
    _renderRows(await apiGet("/products/"));
  } catch (err) {
    showMessage(errorText(err));
  }
}

function _renderRows(products) {
  const rows = products.map((p) => `
    <tr>
      <td>${escapeHtml(p.sku)}</td>
      <td>${escapeHtml(p.title)}</td>
      <td>${CONDITION_LABELS[p.condition] || p.condition}</td>
      <td>${formatEuro(p.purchase_price)}</td>
      <td>${formatEuro(p.sale_price)}</td>
      <td>${formatEuro(p.profit)}</td>
      <td>${p.quantity}</td>
      <td class="actions">
        <button data-edit="${p.id}" class="link-btn">Bearbeiten</button>
        <button data-del="${p.id}" class="link-btn danger">Löschen</button>
      </td>
    </tr>`).join("");
  document.getElementById("product-rows").innerHTML =
    rows || `<tr><td colspan="8" class="empty">Noch keine Artikel.</td></tr>`;
  _bindRowActions(products);
}

function _bindRowActions(products) {
  document.querySelectorAll("[data-edit]").forEach((btn) =>
    btn.addEventListener("click", () => _openForm(products.find((p) => p.id === Number(btn.dataset.edit))))
  );
  document.querySelectorAll("[data-del]").forEach((btn) =>
    btn.addEventListener("click", () => _deleteProduct(Number(btn.dataset.del)))
  );
}

function _openForm(product) {
  _fill(product);
  document.getElementById("product-form").style.display = "grid";
  showMessage("", false);
}

function _closeForm() {
  document.getElementById("product-form").reset();
  document.getElementById("product-id").value = "";
  document.getElementById("product-form").style.display = "none";
}

function _fill(product) {
  const set = (id, value) => { document.getElementById(id).value = value ?? ""; };
  set("product-id", product ? product.id : "");
  set("p-title", product ? product.title : "");
  set("p-purchase", product ? product.purchase_price : "");
  set("p-sale", product ? product.sale_price : "");
  set("p-quantity", product ? product.quantity : 1);
  set("p-date", product ? product.purchase_date : "");
  set("p-description", product ? product.description : "");
  document.getElementById("p-condition").value = product ? product.condition : "good";
}

async function _saveProduct(e) {
  e.preventDefault();
  const id = document.getElementById("product-id").value;
  try {
    if (id) await apiSend(`/products/${id}/`, "PATCH", _formPayload());
    else await apiSend("/products/", "POST", _formPayload());
    _closeForm();
    loadProducts();
  } catch (err) {
    showMessage(errorText(err));
  }
}

function _formPayload() {
  return {
    title: document.getElementById("p-title").value.trim(),
    condition: document.getElementById("p-condition").value,
    purchase_price: document.getElementById("p-purchase").value,
    sale_price: document.getElementById("p-sale").value,
    quantity: Number(document.getElementById("p-quantity").value || 0),
    purchase_date: document.getElementById("p-date").value || null,
    description: document.getElementById("p-description").value.trim(),
  };
}

async function _deleteProduct(id) {
  if (!confirm("Diesen Artikel wirklich löschen?")) return;
  try {
    await apiDelete(`/products/${id}/`);
    loadProducts();
  } catch (err) {
    showMessage(errorText(err));
  }
}
