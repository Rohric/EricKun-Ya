"use strict";

requireAuth();
renderNav("products.html");

const CONDITION_LABELS = {
  new: "Neu", like_new: "Wie neu", very_good: "Sehr gut",
  good: "Gut", acceptable: "Akzeptabel", for_parts: "Defekt / Ersatzteile",
};
const STATUS_LABELS = {
  available: "Verfügbar", reserved: "Reserviert", sold: "Verkauft", archived: "Archiviert",
};

let categories = [];
let currentView = "active";
let currentPage = 1;
let currentProductId = null;

document.getElementById("new-product-btn").addEventListener("click", _newProduct);
document.getElementById("cancel-product").addEventListener("click", _closeForm);
document.getElementById("product-form").addEventListener("submit", _saveProduct);
document.getElementById("image-input").addEventListener("change", _uploadImages);
document.getElementById("manage-cats-btn").addEventListener("click", _toggleCatManager);
document.getElementById("add-parent").addEventListener("click", _addParentCategory);
document.getElementById("add-sub").addEventListener("click", _addSubCategory);
document.getElementById("p-parent-cat").addEventListener("change", () =>
  _fillSubDropdown("p-sub-cat", inputValue("p-parent-cat"))
);
document.querySelectorAll("#view-switch button").forEach((btn) =>
  btn.addEventListener("click", () => _selectView(btn.dataset.view))
);

init();

async function init() {
  try {
    await loadCategories();
    await loadProducts();
  } catch (err) {
    showMessage(errorText(err));
  }
}

// --- View switch (active vs. archive) + paging ---

function _selectView(view) {
  currentView = view;
  currentPage = 1;
  markActive("view-switch", "view", view);
  _closeForm();
  loadProducts().catch((err) => showMessage(errorText(err)));
}

function _goToPage(page) {
  currentPage = page;
  loadProducts().catch((err) => showMessage(errorText(err)));
}

// Reload the list; step back a page if the current one became empty.
async function _reloadAfterRemoval() {
  try {
    await loadProducts();
  } catch (err) {
    if (err.status !== 404 || currentPage === 1) throw err;
    currentPage -= 1;
    await loadProducts();
  }
}

// --- Categories ---

async function loadCategories() {
  categories = await apiGet("/categories/");
  _fillParentDropdowns();
  _renderCatList();
}

function _parents() {
  return categories.filter((c) => !c.parent);
}

function _fillParentDropdowns() {
  const opts = _parents().map((c) => `<option value="${c.id}">${escapeHtml(c.name)}</option>`).join("");
  document.getElementById("p-parent-cat").innerHTML = `<option value="">– keine –</option>${opts}`;
  document.getElementById("sub-parent-select").innerHTML = opts || `<option value="">(erst Oberkategorie)</option>`;
}

function _fillSubDropdown(selectId, parentId, selected) {
  const subs = categories.filter((c) => String(c.parent) === String(parentId));
  const opts = subs.map((c) =>
    `<option value="${c.id}" ${String(c.id) === String(selected) ? "selected" : ""}>${escapeHtml(c.name)}</option>`
  ).join("");
  document.getElementById(selectId).innerHTML = `<option value="">– keine –</option>${opts}`;
}

function _toggleCatManager() {
  const el = document.getElementById("cat-manager");
  el.style.display = el.style.display === "none" ? "block" : "none";
}

function _renderCatList() {
  document.getElementById("cat-list").innerHTML = _parents().map((p) => `
    <div class="cat-group">
      <span class="cat-parent">${escapeHtml(p.name)}
        <button type="button" class="chip-del" data-delcat="${p.id}">✕</button>
      </span>
      <span class="cat-subs">${_subChips(p.id)}</span>
    </div>`).join("") || `<p class="empty">Noch keine Kategorien.</p>`;
  document.querySelectorAll("[data-delcat]").forEach((btn) =>
    btn.addEventListener("click", () => _deleteCategory(Number(btn.dataset.delcat)))
  );
}

function _subChips(parentId) {
  return categories.filter((c) => c.parent === parentId).map((c) =>
    `<span class="chip">${escapeHtml(c.name)}<button type="button" class="chip-del" data-delcat="${c.id}">✕</button></span>`
  ).join("");
}

async function _addParentCategory() {
  const name = inputValue("new-parent-name");
  if (!name) return;
  try {
    await apiSend("/categories/", "POST", { name, parent: null });
    document.getElementById("new-parent-name").value = "";
    await loadCategories();
  } catch (err) {
    showMessage(errorText(err));
  }
}

async function _addSubCategory() {
  const name = inputValue("new-sub-name");
  const parent = inputValue("sub-parent-select");
  if (!name || !parent) return showMessage("Oberkategorie + Name nötig.");
  try {
    await apiSend("/categories/", "POST", { name, parent: Number(parent) });
    document.getElementById("new-sub-name").value = "";
    await loadCategories();
  } catch (err) {
    showMessage(errorText(err));
  }
}

async function _deleteCategory(id) {
  if (!confirm("Kategorie löschen? Artikel behalten dann keine Kategorie.")) return;
  try {
    await apiDelete(`/categories/${id}/`);
    await loadCategories();
    await loadProducts();
  } catch (err) {
    showMessage(errorText(err));
  }
}

// --- Product list ---

async function loadProducts() {
  const data = await apiGet(`/products/?view=${currentView}&page=${currentPage}`);
  _renderRows(data.results);
  renderPager("product-pager", data, currentPage, _goToPage);
}

function _renderRows(products) {
  const rows = products.map((p) => `
    <tr>
      <td>${_thumb(p)}</td>
      <td>${escapeHtml(p.sku)}</td>
      <td>${escapeHtml(p.title)}</td>
      <td>${escapeHtml(p.category_path) || "–"}</td>
      <td><span class="badge badge-${p.status}">${STATUS_LABELS[p.status] || p.status}</span></td>
      <td>${CONDITION_LABELS[p.condition] || p.condition}</td>
      <td>${formatEuro(p.purchase_price)}</td>
      <td>${formatEuro(p.sale_price)}</td>
      <td>${formatEuro(p.profit)}</td>
      <td>${p.quantity}</td>
      <td class="actions">${_rowActions(p)}</td>
    </tr>`).join("");
  document.getElementById("product-rows").innerHTML =
    rows || `<tr><td colspan="11" class="empty">Keine Artikel.</td></tr>`;
  _bindRowActions(products);
}

function _rowActions(product) {
  const del = `<button data-del="${product.id}" class="link-btn danger">Löschen</button>`;
  if (currentView === "archive") {
    return `<button data-react="${product.id}" class="link-btn">Reaktivieren</button>${del}`;
  }
  return `<button data-edit="${product.id}" class="link-btn">Bearbeiten</button>${del}`;
}

function _thumb(product) {
  if (!product.images || !product.images.length) return '<span class="no-thumb">–</span>';
  return `<img class="thumb" src="${product.images[0].image}" alt="" />`;
}

function _bindRowActions(products) {
  const bind = (attr, handler) => document.querySelectorAll(`[data-${attr}]`).forEach((btn) =>
    btn.addEventListener("click", () => handler(Number(btn.getAttribute(`data-${attr}`))))
  );
  bind("edit", (id) => _openForm(products.find((p) => p.id === id)));
  bind("react", _reactivate);
  bind("del", _deleteProduct);
}

async function _reactivate(id) {
  try {
    await apiSend(`/products/${id}/`, "PATCH", { status: "available" });
    await _reloadAfterRemoval();
  } catch (err) {
    showMessage(errorText(err));
  }
}

async function _deleteProduct(id) {
  if (!confirm("Diesen Artikel wirklich löschen?")) return;
  try {
    await apiDelete(`/products/${id}/`);
    if (currentProductId === id) _closeForm();
    await _reloadAfterRemoval();
  } catch (err) {
    showMessage(errorText(err));
  }
}

// --- Product form ---

function _newProduct() {
  if (currentView !== "active") _selectView("active");
  _openForm();
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
  document.getElementById("p-status").value = product ? product.status : "available";
  _fillCategorySelectors(product ? product.category : null);
}

// Set the parent + sub category dropdowns from a product's category id.
function _fillCategorySelectors(categoryId) {
  const cat = categories.find((c) => c.id === categoryId);
  const parentId = cat ? (cat.parent || cat.id) : "";
  const subId = cat && cat.parent ? cat.id : "";
  document.getElementById("p-parent-cat").value = parentId ? String(parentId) : "";
  _fillSubDropdown("p-sub-cat", parentId, subId);
}

async function _saveProduct(e) {
  e.preventDefault();
  const id = inputValue("product-id");
  try {
    const saved = id
      ? await apiSend(`/products/${id}/`, "PATCH", _formPayload())
      : await apiSend("/products/", "POST", _formPayload());
    showMessage("Gespeichert.", false);
    currentProductId = saved.id;
    document.getElementById("product-id").value = saved.id;
    _syncImageSection(saved);
    await _reloadAfterRemoval();
  } catch (err) {
    showMessage(errorText(err));
  }
}

function _formPayload() {
  return {
    title: inputValue("p-title"),
    condition: inputValue("p-condition"),
    status: inputValue("p-status"),
    category: _selectedCategory(),
    purchase_price: inputValue("p-purchase"),
    sale_price: inputValue("p-sale"),
    quantity: Number(inputValue("p-quantity") || 0),
    purchase_date: inputValue("p-date") || null,
    description: inputValue("p-description"),
  };
}

// Return the chosen category id: sub if picked, else parent, else null.
function _selectedCategory() {
  const sub = inputValue("p-sub-cat");
  const parent = inputValue("p-parent-cat");
  return sub ? Number(sub) : (parent ? Number(parent) : null);
}

// --- Images ---

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

async function _refreshImages() {
  _renderGallery(await apiGet(`/products/${currentProductId}/images/`));
  await loadProducts();
}
