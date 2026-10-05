"use strict";

// Listings section of the eBay tab: status per product, publish dialog, sync and withdraw.
// loadListings() is called by ebay.js after every status refresh.

const LISTING_STATES = {
  none: "Nicht inseriert", draft: "Entwurf", online: "Online",
  changed: "Geändert", ended: "Beendet", error: "Fehler",
};

let listingProducts = [];
let publishProduct = null;   // product the publish dialog is open for
let categoryOptions = [];    // categories offered in the dialog

document.getElementById("sync-all-btn").addEventListener("click", _syncAll);
document.getElementById("cat-search-btn").addEventListener("click", _searchCategories);
document.getElementById("publish-form").addEventListener("submit", _submitPublish);
document.getElementById("publish-abort").addEventListener("click", _closePublish);
document.getElementById("cat-query").addEventListener("keydown", _searchOnEnter);

// --- Table ---

async function loadListings(status) {
  document.getElementById("listings-card").classList.toggle("disabled", !status.ready);
  listingProducts = await apiGet("/ebay/listings/");
  _renderListings();
}

async function _reloadListings() {
  listingProducts = await apiGet("/ebay/listings/");
  _renderListings();
}

function _renderListings() {
  const rows = listingProducts.map(_listingRow).join("");
  document.getElementById("listing-rows").innerHTML =
    rows || `<tr><td colspan="7" class="empty">Noch keine verkaufbaren Artikel.</td></tr>`;
  _bindListingActions();
}

function _listingRow(product) {
  const listing = product.listing;
  const state = listing ? listing.state : "none";
  const thumb = product.image
    ? `<img class="thumb" src="${escapeHtml(product.image)}" alt="" />`
    : `<span class="no-thumb">–</span>`;
  return `
    <tr>
      <td>${thumb}</td>
      <td><strong>${escapeHtml(product.title)}</strong><br><span class="hint">${escapeHtml(product.sku)}</span></td>
      <td>${formatEuro(product.sale_price)}</td>
      <td>${product.quantity}</td>
      <td><span class="badge badge-listing-${state}">${LISTING_STATES[state]}</span>${_errorLine(listing)}</td>
      <td>${listing ? escapeHtml(listing.category_name) : "–"}</td>
      <td class="actions">${_listingActions(product)}</td>
    </tr>`;
}

function _errorLine(listing) {
  if (!listing || !listing.sync_error) return "";
  return `<span class="row-error">${escapeHtml(listing.sync_error)}</span>`;
}

// Offer the actions that make sense for the stored listing status.
function _listingActions(product) {
  const listing = product.listing;
  const button = (action, label, extra = "") =>
    `<button type="button" class="link-btn ${extra}" data-${action}="${product.id}">${label}</button>`;
  if (!listing || listing.status === "draft") return button("publish", "Inserieren");
  if (listing.status === "ended") return button("sync", "Wieder einstellen") + button("publish", "Merkmale");
  const view = listing.url
    ? `<a class="link-btn" href="${escapeHtml(listing.url)}" target="_blank" rel="noopener">Ansehen</a>`
    : "";
  return button("sync", "Synchronisieren") + button("publish", "Merkmale")
    + button("withdraw", "Beenden", "danger") + view;
}

function _bindListingActions() {
  const bind = (action, handler) => document.querySelectorAll(`[data-${action}]`).forEach((btn) =>
    btn.addEventListener("click", () => handler(Number(btn.getAttribute(`data-${action}`))))
  );
  bind("publish", (id) => _openPublish(listingProducts.find((p) => p.id === id)));
  bind("sync", (id) => _runAction(id, "sync", "Inserat ist auf dem aktuellen Stand."));
  bind("withdraw", _withdraw);
}

// --- Row actions ---

// Show feedback inside the listings card, because the page message is out of view down here.
function _listingMessage(text, isError = true) {
  const box = document.getElementById("listing-message");
  box.textContent = text;
  box.className = isError ? "message error" : "message success";
  box.style.display = text ? "block" : "none";
}

async function _runAction(id, action, successText) {
  _listingMessage("Wird an eBay übertragen …", false);
  try {
    await apiSend(`/ebay/listings/${id}/${action}/`, "POST", {});
    _listingMessage(successText, false);
  } catch (err) {
    _listingMessage(errorText(err));
  }
  await _reloadListings().catch(() => {});
}

function _withdraw(id) {
  if (!confirm("Inserat bei eBay wirklich beenden?")) return;
  _runAction(id, "withdraw", "Inserat beendet.");
}

async function _syncAll() {
  _listingMessage("Wird an eBay übertragen …", false);
  try {
    const result = await apiSend("/ebay/listings/sync-all/", "POST", {});
    const text = `${result.synced} synchronisiert, ${result.failed} fehlgeschlagen.`;
    _listingMessage(result.synced + result.failed ? text : "Alle Inserate sind aktuell.", result.failed > 0);
  } catch (err) {
    _listingMessage(errorText(err));
  }
  await _reloadListings().catch(() => {});
}

// --- Publish dialog ---

function _openPublish(product) {
  publishProduct = product;
  document.getElementById("publish-title").textContent = `„${product.title}“ bei eBay inserieren`;
  document.getElementById("cat-query").value = product.title;
  document.getElementById("aspect-fields").innerHTML = "";
  _setHint("");
  _publishMessage("");
  _showCategories([], false);
  document.getElementById("publish-modal").style.display = "flex";
  _searchCategories();  // lists the known category first and loads its aspects
}

function _closePublish() {
  publishProduct = null;
  document.getElementById("publish-modal").style.display = "none";
}

// Category already used for this product, or remembered for its internal category.
function _knownCategory(product) {
  if (product.listing) return { id: product.listing.category_id, path: product.listing.category_name, note: "aktuell" };
  const remembered = product.remembered_category;
  return remembered ? { id: remembered.id, path: remembered.name, note: "gemerkt" } : null;
}

function _publishMessage(text) {
  const box = document.getElementById("publish-message");
  box.textContent = text;
  box.style.display = text ? "block" : "none";
}

function _setHint(text) {
  const hint = document.getElementById("condition-hint");
  hint.textContent = text;
  hint.style.display = text ? "block" : "none";
}

function _searchOnEnter(e) {
  if (e.key !== "Enter") return;
  e.preventDefault();  // Enter in the search field must not submit the dialog
  _searchCategories();
}

async function _searchCategories() {
  const query = inputValue("cat-query");
  if (!query) return;
  try {
    const found = await apiGet(`/ebay/categories/suggest/?q=${encodeURIComponent(query)}`);
    const known = publishProduct ? _knownCategory(publishProduct) : null;
    const others = found.filter((category) => !known || category.id !== known.id);
    // A remembered category is only pre-selected if eBay also suggests it for this title.
    const trusted = known && (known.note === "aktuell" || found.some((category) => category.id === known.id));
    _showCategories(known ? [known, ...others] : others, Boolean(trusted));
    _publishMessage(known || others.length ? "" : "Keine Vorschläge – bitte einen anderen Suchbegriff probieren.");
  } catch (err) {
    _publishMessage(errorText(err));
  }
}

// Render the category radios; optionally select the first one and load its aspects.
function _showCategories(categories, selectFirst) {
  categoryOptions = categories;
  const box = document.getElementById("cat-suggestions");
  box.innerHTML = "";
  categories.forEach((category, index) => box.appendChild(_categoryRadio(category, index)));
  if (selectFirst && categories.length) {
    box.querySelector("input").checked = true;
    _loadRequirements(categories[0].id);
  }
}

function _categoryRadio(category, index) {
  const label = document.createElement("label");
  label.className = "radio";
  const input = document.createElement("input");
  input.type = "radio";
  input.name = "ebay-category";
  input.value = String(index);
  input.addEventListener("change", () => _loadRequirements(category.id));
  label.append(input, document.createTextNode(category.note ? `${category.path} (${category.note})` : category.path));
  return label;
}

async function _loadRequirements(categoryId) {
  const box = document.getElementById("aspect-fields");
  box.textContent = "Merkmale werden geladen …";
  try {
    const data = await apiGet(`/ebay/categories/${encodeURIComponent(categoryId)}/requirements/?product=${publishProduct.id}`);
    _setHint(data.condition_hint);
    _renderAspects(data.aspects);
  } catch (err) {
    box.textContent = "";
    _publishMessage(errorText(err));
  }
}

// Required aspects are shown directly, recommended ones in a collapsible block.
function _renderAspects(aspects) {
  const box = document.getElementById("aspect-fields");
  box.innerHTML = "";
  const required = aspects.filter((aspect) => aspect.required);
  const recommended = aspects.filter((aspect) => !aspect.required);
  if (required.length) box.appendChild(_aspectGrid(required));
  if (!recommended.length) return;
  const details = document.createElement("details");
  details.className = "aspect-more";
  const summary = document.createElement("summary");
  summary.textContent = `Weitere empfohlene Merkmale (${recommended.length})`;
  details.append(summary, _aspectGrid(recommended));
  box.appendChild(details);
}

function _aspectGrid(aspects) {
  const grid = document.createElement("div");
  grid.className = "form-grid";
  aspects.forEach((aspect) => grid.appendChild(_aspectField(aspect)));
  return grid;
}

function _aspectField(aspect) {
  const label = document.createElement("label");
  const suffix = (aspect.required ? " *" : "") + (aspect.multiple ? " (mehrere mit Komma trennen)" : "");
  label.textContent = aspect.name + suffix;
  const field = aspect.free_text ? _aspectInput(aspect, label) : _aspectSelect(aspect);
  field.dataset.aspect = aspect.name;
  field.dataset.multiple = aspect.multiple ? "1" : "";
  field.required = aspect.required;
  field.value = [].concat(publishProduct.aspects[aspect.name] || []).join(", ");
  label.appendChild(field);
  return label;
}

// Free-text aspect: an input with eBay's known values as suggestions.
function _aspectInput(aspect, label) {
  const input = document.createElement("input");
  input.type = "text";
  if (!aspect.values.length) return input;
  const list = document.createElement("datalist");
  list.id = `aspect-list-${Math.random().toString(36).slice(2)}`;
  aspect.values.forEach((value) => list.appendChild(new Option(value, value)));
  input.setAttribute("list", list.id);
  label.appendChild(list);
  return input;
}

function _aspectSelect(aspect) {
  const select = document.createElement("select");
  select.appendChild(new Option("– bitte wählen –", ""));
  aspect.values.forEach((value) => select.appendChild(new Option(value, value)));
  return select;
}

function _collectAspects() {
  const aspects = {};
  document.querySelectorAll("#aspect-fields [data-aspect]").forEach((field) => {
    const values = field.dataset.multiple ? field.value.split(",") : [field.value];
    aspects[field.dataset.aspect] = values.map((value) => value.trim()).filter(Boolean);
  });
  return aspects;
}

async function _submitPublish(e) {
  e.preventDefault();
  const chosen = document.querySelector('input[name="ebay-category"]:checked');
  if (!chosen) return _publishMessage("Bitte eine eBay-Kategorie auswählen.");
  const category = categoryOptions[Number(chosen.value)];
  const payload = { category_id: category.id, category_name: category.path, aspects: _collectAspects() };
  _setPublishing(true);
  try {
    await apiSend(`/ebay/listings/${publishProduct.id}/publish/`, "POST", payload);
    _closePublish();
    _listingMessage("Artikel ist bei eBay online.", false);
  } catch (err) {
    _publishMessage(errorText(err));
  }
  _setPublishing(false);
  await _reloadListings().catch(() => {});
}

function _setPublishing(busy) {
  const button = document.getElementById("publish-submit");
  button.disabled = busy;
  button.textContent = busy ? "Wird übertragen …" : "Jetzt inserieren";
}
