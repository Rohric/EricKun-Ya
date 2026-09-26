"use strict";

requireAuth();
renderNav("products.html");

const CONDITION_LABELS = {
  new: "Neu", like_new: "Wie neu", very_good: "Sehr gut",
  good: "Gut", acceptable: "Akzeptabel", for_parts: "Defekt / Ersatzteile",
};

let currentProductId = null;

document.getElementById("new-product-btn").addEventListener("click", () => _openForm());
document.getElementById("cancel-product").addEventListener("click", _closeForm);
document.getElementById("product-form").addEventListener("submit", _saveProduct);
document.getElementById("image-input").addEventListener("change", _uploadImages);

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
      <td>${_thumb(p)}</td>
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
    rows || `<tr><td colspan="9" class="empty">Noch keine Artikel.</td></tr>`;
  _bindRowActions(products);
}

function _thumb(product) {
  if (!product.images || !product.images.length) return '<span class="no-thumb">–</span>';
  return `<img class="thumb" src="${product.images[0].image}" alt="" />`;
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
  currentProductId = product ? product.id : null;
  _syncImageSection(product);
  document.getElementById("product-form").style.display = "block";
  showMessage("", false);
}

function _closeForm() {
  const form = document.getElementById("product-form");
  form.reset();
  document.getElementById("product-id").value = "";
  currentProductId = null;
  form.style.display = "none";
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

// Enable the image tools only once the product exists (upload needs its id).
function _syncImageSection(product) {
  const hasId = Boolean(product);
  document.getElementById("image-input").disabled = !hasId;
  document.getElementById("image-hint").style.display = hasId ? "none" : "block";
  _renderGallery(product ? product.images : []);
}

function _renderGallery(images) {
  const gallery = document.getElementById("image-gallery");
  gallery.innerHTML = (images || []).map((img) => `
    <div class="gallery-item">
      <img src="${img.image}" alt="" />
      <button type="button" class="img-del" data-img="${img.id}">✕</button>
    </div>`).join("");
  gallery.querySelectorAll("[data-img]").forEach((btn) =>
    btn.addEventListener("click", () => _deleteImage(Number(btn.dataset.img)))
  );
}

async function _saveProduct(e) {
  e.preventDefault();
  const id = document.getElementById("product-id").value;
  try {
    const saved = id
      ? await apiSend(`/products/${id}/`, "PATCH", _formPayload())
      : await apiSend("/products/", "POST", _formPayload());
    showMessage("Gespeichert.", false);
    currentProductId = saved.id;
    document.getElementById("product-id").value = saved.id;
    _syncImageSection(saved);
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

// Upload each selected file to the current product, then refresh the gallery.
async function _uploadImages(e) {
  if (!currentProductId) return;
  try {
    for (const file of e.target.files) {
      const data = new FormData();
      data.append("image", file);
      await apiUpload(`/products/${currentProductId}/images/`, data);
    }
    e.target.value = "";
    await _refreshImages();
  } catch (err) {
    showMessage(errorText(err));
  }
}

async function _deleteImage(imageId) {
  try {
    await apiDelete(`/product-images/${imageId}/`);
    await _refreshImages();
  } catch (err) {
    showMessage(errorText(err));
  }
}

// Reload the current product's images (gallery + table thumbnails).
async function _refreshImages() {
  _renderGallery(await apiGet(`/products/${currentProductId}/images/`));
  loadProducts();
}

async function _deleteProduct(id) {
  if (!confirm("Diesen Artikel wirklich löschen?")) return;
  try {
    await apiDelete(`/products/${id}/`);
    if (currentProductId === id) _closeForm();
    loadProducts();
  } catch (err) {
    showMessage(errorText(err));
  }
}
