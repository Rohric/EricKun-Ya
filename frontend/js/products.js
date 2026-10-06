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
const STATUS_TABS = [
  ["all", "Alle"], ["available", "Verfügbar"], ["reserved", "Reserviert"],
  ["sold", "Verkauft"], ["archived", "Archiv"],
];
const INACTIVE_STATES = ["sold", "archived"];
const COLUMN_COUNT = 12;  // columns of the product table, for rows that span all of them
const SEARCH_DELAY_MS = 300;

let categories = [];
let currentStatus = "all";
let currentPage = 1;
let currentProductId = null;
let channelStates = {};
let productSales = {};                // {product id: {sold, sales}} for the products on this page
const expandedProducts = new Set();   // products whose sales are unfolded
let searchTimer = null;

document.getElementById("new-product-btn").addEventListener("click", () => _openForm());
document.getElementById("cancel-product").addEventListener("click", _closeForm);
document.getElementById("product-form").addEventListener("submit", _saveProduct);
document.getElementById("image-input").addEventListener("change", _uploadImages);
document.getElementById("manage-cats-btn").addEventListener("click", _toggleCatManager);
document.getElementById("add-parent").addEventListener("click", _addParentCategory);
document.getElementById("add-sub").addEventListener("click", _addSubCategory);
document.getElementById("filter-category").addEventListener("change", _applyFilters);
document.getElementById("filter-search").addEventListener("input", _searchSoon);
document.getElementById("filter-reset").addEventListener("click", _resetFilters);
document.getElementById("p-parent-cat").addEventListener("change", () =>
  _fillSubDropdown("p-sub-cat", inputValue("p-parent-cat"))
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

// --- Status tabs, filters and paging ---

function _selectStatus(status) {
  currentStatus = status;
  currentPage = 1;
  _closeForm();
  _reload();
}

function _applyFilters() {
  currentPage = 1;
  _reload();
}

// Wait until typing pauses before searching.
function _searchSoon() {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(_applyFilters, SEARCH_DELAY_MS);
}

function _resetFilters() {
  document.getElementById("filter-category").value = "";
  document.getElementById("filter-search").value = "";
  _applyFilters();
}

function _goToPage(page) {
  currentPage = page;
  _reload();
}

function _reload() {
  loadProducts().catch((err) => showMessage(errorText(err)));
}

// Query string of the category and search filters (shared by list and counts).
function _filterQuery() {
  const params = new URLSearchParams();
  const category = inputValue("filter-category");
  const search = inputValue("filter-search");
  if (category) params.set("category", category);
  if (search) params.set("search", search);
  return params;
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
  _fillCategoryFilter();
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

// Category filter: parents with their sub-categories indented below them.
function _fillCategoryFilter() {
  const select = document.getElementById("filter-category");
  const chosen = select.value;
  const option = (c, indent) => `<option value="${c.id}">${indent}${escapeHtml(c.name)}</option>`;
  select.innerHTML = `<option value="">Alle Kategorien</option>` + _parents().map((parent) =>
    option(parent, "") + categories.filter((c) => c.parent === parent.id).map((sub) => option(sub, "– ")).join("")
  ).join("");
  select.value = chosen;
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
  const [data, counts] = await Promise.all([
    apiGet(`/products/?${_listQuery()}`),
    apiGet(`/products/counts/?${_filterQuery()}`),
    _loadChannelStates(),
  ]);
  productSales = await _loadSales(data.results);
  _renderTabs(counts);
  _renderRows(data.results);
  renderPager("product-pager", data, currentPage, _goToPage);
}

// Sold units per product on this page; without them the table simply shows the stock.
function _loadSales(products) {
  if (!products.length) return {};
  const ids = products.map((product) => product.id).join(",");
  return apiGet(`/orders/product-sales/?products=${ids}`).catch(() => ({}));
}

function _listQuery() {
  const params = _filterQuery();
  params.set("page", currentPage);
  if (currentStatus === "all") params.set("view", "all");
  else params.set("status", currentStatus);
  return params;
}

// Where each product is listed; the table still works if eBay data cannot be loaded.
async function _loadChannelStates() {
  channelStates = await apiGet("/ebay/listing-states/").catch(() => ({}));
}

function _renderTabs(counts) {
  const tabs = STATUS_TABS.map(([key, label]) => [key, `${label} (${counts[key]})`]);
  renderTabs("status-tabs", tabs, currentStatus, _selectStatus);
}

function _renderRows(products) {
  const rows = products.map(_productRows).join("");
  document.getElementById("product-rows").innerHTML =
    rows || `<tr><td colspan="${COLUMN_COUNT}" class="empty">Keine Artikel.</td></tr>`;
  _bindRowActions(products);
  _bindStockToggles(products);
}

// The product's table row, followed by its unfolded sales if they are open.
function _productRows(p) {
  const open = expandedProducts.has(p.id) && Boolean(productSales[p.id]);
  return `
    <tr class="${open ? "row-open" : ""}">
      <td>${_thumb(p)}</td>
      <td>${escapeHtml(p.sku)}</td>
      <td>${escapeHtml(p.title)}</td>
      <td>${escapeHtml(p.category_path) || "–"}</td>
      <td>${_statusBadge(p)}</td>
      <td>${_channelBadges(p.id)}</td>
      <td>${CONDITION_LABELS[p.condition] || p.condition}</td>
      <td>${formatEuro(p.purchase_price)}</td>
      <td>${formatEuro(p.sale_price)}</td>
      <td>${formatEuro(p.profit)}</td>
      <td>${_stockCell(p, open)}</td>
      <td class="actions">${_rowActions(p)}</td>
    </tr>${open ? _unitsRow(p) : ""}`;
}

function _statusBadge(product) {
  return `<span class="badge badge-${product.status}">${STATUS_LABELS[product.status] || product.status}</span>`;
}

// --- Stock "left / total" and the unfolded sales below a product ---

// "1 / 2" = one unit left of two; with sales the cell is a toggle for the details below.
function _stockCell(product, open) {
  const sold = productSales[product.id] ? productSales[product.id].sold : 0;
  const total = product.quantity + sold;
  const share = total ? (sold / total) * 100 : 0;
  const title = `${product.quantity} von ${total} noch im Lager, ${sold} verkauft`;
  const label = `<span class="stock-numbers">${product.quantity} / ${total}</span>
    <span class="stock-bar"><span style="width:${share}%"></span></span>`;
  if (!sold) return `<span class="stock" title="${title}">${label}</span>`;
  const arrow = `<span class="stock-arrow">${open ? "▾" : "▸"}</span>`;
  return `<button type="button" class="stock stock-toggle" data-units="${product.id}" title="${title} – Verkäufe anzeigen">${arrow}${label}</button>`;
}

function _unitsRow(product) {
  const sales = productSales[product.id].sales.map(_saleTile).join("");
  return `
    <tr class="units-row">
      <td colspan="${COLUMN_COUNT}"><div class="unit-list">${_stockTile(product)}${sales}</div></td>
    </tr>`;
}

// What is still in stock, with the product status and where it is listed.
function _stockTile(product) {
  if (!product.quantity) return "";
  const channels = _channelBadges(product.id);
  return `
    <div class="unit unit-stock">
      <strong>${product.quantity}× im Lager</strong>
      ${_statusBadge(product)}
      ${channels === "–" ? '<span class="hint">nicht inseriert</span>' : channels}
    </div>`;
}

// One sale of the product: when, for how much, through which channel and how far the order is.
function _saleTile(sale) {
  const date = new Date(sale.sold_at).toLocaleDateString("de-DE");
  const channel = sale.source === "ebay" ? "eBay" : "Manuell";
  const buyer = sale.buyer_name ? `<span>an ${escapeHtml(sale.buyer_name)}</span>` : "";
  return `
    <div class="unit unit-sold">
      <strong>${sale.quantity}× verkauft</strong>
      <span>am ${date} für ${formatEuro(sale.sold_price)}</span>
      <span class="chip">${channel}</span>
      ${buyer}
      <span class="badge badge-${sale.fulfillment_status}">${FULFILLMENT_LABELS[sale.fulfillment_status]}</span>
      <span class="badge badge-pay-${sale.payment_status}">${PAYMENT_LABELS[sale.payment_status]}</span>
      <a class="link-btn" href="orders.html">Bestellung #${sale.order}</a>
    </div>`;
}

function _bindStockToggles(products) {
  document.querySelectorAll("[data-units]").forEach((btn) =>
    btn.addEventListener("click", () => {
      const id = Number(btn.dataset.units);
      if (!expandedProducts.delete(id)) expandedProducts.add(id);
      _renderRows(products);
    })
  );
}

// One badge per sales channel the product is listed on (linked to the listing if online).
function _channelBadges(productId) {
  const channels = channelStates[productId] || [];
  if (!channels.length) return "–";
  return channels.map((channel) => {
    const text = `${escapeHtml(channel.label)} · ${LISTING_STATE_LABELS[channel.state] || channel.state}`;
    const badge = `<span class="badge badge-listing-${channel.state}">${text}</span>`;
    return channel.url ? `<a href="${escapeHtml(channel.url)}" target="_blank" rel="noopener">${badge}</a>` : badge;
  }).join(" ");
}

function _rowActions(product) {
  const del = `<button data-del="${product.id}" class="link-btn danger">Löschen</button>`;
  if (INACTIVE_STATES.includes(product.status)) {
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
  if (!confirm("Diesen Artikel wirklich löschen? Ein laufendes eBay-Inserat wird dabei beendet.")) return;
  try {
    await apiDelete(`/products/${id}/`);
    if (currentProductId === id) _closeForm();
    await _reloadAfterRemoval();
  } catch (err) {
    showMessage(errorText(err));
  }
}

// --- Product form ---

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
