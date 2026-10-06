"use strict";

// eBay tab, panels "Inserate" and "Neu inserieren": listing tables, row actions and the
// publish dialog. loadListings() / loadUnlisted() are called by ebay.js.

const TITLE_MAX = 80;

let listedProducts = [];
let unlistedProducts = [];
let shippingProfiles = [];
let publishProduct = null;   // product the publish dialog is open for
let categoryOptions = [];    // categories offered in the dialog

document.getElementById("sync-all-btn").addEventListener("click", _syncAll);
document.getElementById("refresh-facts-btn").addEventListener("click", _refreshFacts);
document.getElementById("cat-search-btn").addEventListener("click", _searchCategories);
document.getElementById("publish-form").addEventListener("submit", _submitPublish);
document.getElementById("publish-abort").addEventListener("click", _closePublish);
document.getElementById("fee-btn").addEventListener("click", _previewFees);
document.getElementById("cat-query").addEventListener("keydown", _searchOnEnter);

// --- Panel "Inserate" ---

async function loadListings() {
  _renderUnassignedHint();
  listedProducts = await apiGet("/ebay/listings/?scope=listed");
  const rows = listedProducts.map(_listingRow).join("");
  document.getElementById("listing-rows").innerHTML =
    rows || `<tr><td colspan="10" class="empty">Noch nichts inseriert – siehe Reiter „Neu inserieren“.</td></tr>`;
  _bindActions("listing-rows", listedProducts);
}

// Point to the assignment page while listings on eBay still belong to no article.
function _renderUnassignedHint() {
  const count = ebayStatus ? ebayStatus.listings.unassigned : 0;
  const box = document.getElementById("unassigned-hint");
  box.style.display = count ? "block" : "none";
  box.innerHTML = `${count} Inserat${count === 1 ? "" : "e"} bei eBay ${count === 1 ? "gehört" : "gehören"} noch zu keinem Artikel.
    <a href="channels.html">Zur Zuordnung</a>`;
}

function _listingRow(product) {
  const listing = product.listing;
  return `
    <tr>
      <td>${_thumb(product)}</td>
      <td>${_titleCell(product)}</td>
      <td>${formatEuro(product.sale_price)}</td>
      <td>${_ebayPrice(product)}</td>
      <td>${product.quantity}</td>
      <td>${product.sold_units}</td>
      <td>${_stateBadge(listing)}${_errorLine(listing)}</td>
      <td>${_categoryCell(listing)}</td>
      <td>${escapeHtml(listing.shipping_profile_name) || "Standard"}${listing.best_offer ? '<span class="row-note">Preisvorschlag</span>' : ""}</td>
      <td class="actions">${_listingActions(product)}</td>
    </tr>`;
}

// The eBay category by name; a listing taken over from eBay only knows the number at first.
function _categoryCell(listing) {
  if (listing.category_name) return escapeHtml(listing.category_name);
  return listing.category_id ? `<span class="hint">Nr. ${escapeHtml(listing.category_id)}</span>` : "–";
}

// The price eBay shows to buyers; highlighted when it differs from our own price.
function _ebayPrice(product) {
  const price = product.listing.ebay_price;
  if (price == null) return "–";
  if (Number(price) === Number(product.sale_price)) return formatEuro(price);
  const title = `eBay zeigt dem Käufer ${formatEuro(price)}, dein Preis ist ${formatEuro(product.sale_price)}.`;
  return `<span class="price-diff" title="${escapeHtml(title)}">${formatEuro(price)}</span>`;
}

// Offer the actions that make sense for the stored listing status.
function _listingActions(product) {
  const listing = product.listing;
  const edit = _actionButton(product, "publish", "Bearbeiten");
  const unlink = _actionButton(product, "unlink", "Lösen");
  if (listing.status === "ended") {
    const sellable = product.status === "available" && product.quantity > 0;
    return (sellable ? _actionButton(product, "sync", "Wieder einstellen") + edit : '<span class="hint">nicht verkaufbar</span>') + unlink;
  }
  const view = listing.url
    ? `<a class="link-btn" href="${escapeHtml(listing.url)}" target="_blank" rel="noopener">Ansehen</a>`
    : "";
  return _actionButton(product, "sync", "Synchronisieren") + edit + _actionButton(product, "withdraw", "Beenden", "danger") + unlink + view;
}

// --- Panel "Neu inserieren" ---

async function loadUnlisted() {
  unlistedProducts = await apiGet("/ebay/listings/?scope=unlisted");
  const rows = unlistedProducts.map(_unlistedRow).join("");
  document.getElementById("unlisted-rows").innerHTML =
    rows || `<tr><td colspan="7" class="empty">Alle verkaufbaren Artikel sind bereits inseriert.</td></tr>`;
  _bindActions("unlisted-rows", unlistedProducts);
}

function _unlistedRow(product) {
  return `
    <tr>
      <td>${_thumb(product)}</td>
      <td>${_titleCell(product)}</td>
      <td>${escapeHtml(product.category_path) || "–"}</td>
      <td>${formatEuro(product.sale_price)}</td>
      <td>${product.quantity}</td>
      <td>${_problemHints(product)}${_errorLine(product.listing)}</td>
      <td class="actions">${_actionButton(product, "publish", "Inserieren")}</td>
    </tr>`;
}

// What eBay would reject right away, so it can be fixed before opening the dialog.
function _problemHints(product) {
  const problems = [];
  if (!product.image) problems.push("kein Bild");
  if (product.title.length > TITLE_MAX) problems.push(`Titel zu lang (${product.title.length}/${TITLE_MAX})`);
  if (product.status !== "available") problems.push("nicht verfügbar");
  if (!problems.length) return product.listing ? '<span class="hint">Entwurf</span>' : '<span class="hint">bereit</span>';
  return `<span class="row-error">${problems.join(", ")}</span>`;
}

// --- Shared row pieces ---

function _thumb(product) {
  return product.image
    ? `<img class="thumb" src="${escapeHtml(product.image)}" alt="" />`
    : `<span class="no-thumb">–</span>`;
}

// Title and article number; a listing taken over from eBay may carry another number there.
function _titleCell(product) {
  const foreign = product.listing && product.listing.sku && product.listing.sku !== product.sku
    ? `<span class="row-note">bei eBay: ${escapeHtml(product.listing.sku)}</span>`
    : "";
  return `<strong>${escapeHtml(product.title)}</strong><br><span class="hint">${escapeHtml(product.sku)}</span>${foreign}`;
}

function _stateBadge(listing) {
  const state = listing ? listing.state : "none";
  return `<span class="badge badge-listing-${state}">${LISTING_STATE_LABELS[state]}</span>`;
}

function _errorLine(listing) {
  if (!listing || !listing.sync_error) return "";
  return `<span class="row-error">${escapeHtml(listing.sync_error)}</span>`;
}

function _actionButton(product, action, label, extra = "") {
  return `<button type="button" class="link-btn ${extra}" data-${action}="${product.id}">${label}</button>`;
}

function _bindActions(tableId, products) {
  const table = document.getElementById(tableId);
  const bind = (action, handler) => table.querySelectorAll(`[data-${action}]`).forEach((btn) =>
    btn.addEventListener("click", () => handler(Number(btn.getAttribute(`data-${action}`))))
  );
  bind("publish", (id) => _openPublish(products.find((p) => p.id === id)));
  bind("sync", (id) => _runAction(id, "sync", "Inserat ist auf dem aktuellen Stand."));
  bind("withdraw", _withdraw);
  bind("unlink", _unlink);
}

// Show feedback inside the active panel, because the page message is out of view down here.
function _panelMessage(text, isError = true) {
  ["listing-message", "unlisted-message"].forEach((id) => {
    const box = document.getElementById(id);
    box.textContent = text;
    box.className = isError ? "message error" : "message success";
    box.style.display = text ? "block" : "none";
  });
}

// Reload both tables and the counters in the tab shell.
function _reloadListings() {
  return refresh().catch(() => {});
}

// --- Row actions ---

async function _runAction(id, action, successText) {
  _panelMessage("Wird an eBay übertragen …", false);
  let failure = "";
  try {
    await apiSend(`/ebay/listings/${id}/${action}/`, "POST", {});
  } catch (err) {
    failure = errorText(err);
  }
  await _reloadListings();
  _panelMessage(failure || successText, Boolean(failure));
}

function _withdraw(id) {
  if (!confirm("Inserat bei eBay wirklich beenden?")) return;
  _runAction(id, "withdraw", "Inserat beendet.");
}

// Detach article and listing; the listing itself stays untouched on eBay.
function _unlink(id) {
  const question = "Verknüpfung lösen? Das Inserat bleibt bei eBay unverändert. Läuft es noch, " +
    "erscheint es wieder unter „Zuordnung“ – Änderungen am Artikel erreichen es dann nicht mehr.";
  if (!confirm(question)) return;
  _runAction(id, "unlink", "Verknüpfung gelöst.");
}

async function _syncAll() {
  await _runBulk("/ebay/listings/sync-all/", (result) =>
    result.synced + result.failed
      ? [`${result.synced} synchronisiert, ${result.failed} fehlgeschlagen.`, result.failed > 0]
      : ["Alle Inserate sind aktuell.", false]
  );
}

async function _refreshFacts() {
  await _runBulk("/ebay/listings/refresh/", (result) =>
    [`${result.refreshed} Inserate von eBay aktualisiert${result.failed ? `, ${result.failed} fehlgeschlagen` : ""}.`, result.failed > 0]
  );
}

// Run an action over all listings and report its summary.
async function _runBulk(path, describe) {
  _panelMessage("Wird mit eBay abgeglichen …", false);
  let outcome;
  try {
    outcome = describe(await apiSend(path, "POST", {}));
  } catch (err) {
    outcome = [errorText(err), true];
  }
  await _reloadListings();
  _panelMessage(outcome[0], outcome[1]);
}

// --- Publish dialog ---

async function _openPublish(product) {
  publishProduct = product;
  const online = Boolean(product.listing) && product.listing.status === "online";
  document.getElementById("publish-title").textContent = `„${product.title}“ ${online ? "bearbeiten" : "bei eBay inserieren"}`;
  document.getElementById("publish-submit").textContent = online ? "Speichern und übertragen" : "Jetzt inserieren";
  document.getElementById("fee-btn").style.display = online ? "none" : "inline-block";
  document.getElementById("cat-query").value = product.title;
  document.getElementById("aspect-fields").innerHTML = "";
  document.getElementById("publish-best-offer").checked = Boolean(product.listing && product.listing.best_offer);
  _setText("condition-hint", "");
  _setText("fee-result", "");
  _publishMessage("");
  _showCategories([], false);
  document.getElementById("publish-modal").style.display = "flex";
  await _fillProfiles(product);
  _searchCategories();  // lists the known category first and loads its aspects
}

function _closePublish() {
  publishProduct = null;
  document.getElementById("publish-modal").style.display = "none";
}

// Shipping profile dropdown; the product's current profile (or the default) is selected.
async function _fillProfiles(product) {
  shippingProfiles = await apiGet("/ebay/shipping-profiles/").catch(() => []);
  const select = document.getElementById("publish-profile");
  select.innerHTML = "";
  shippingProfiles.forEach((profile) => {
    const label = `${profile.name} – ${formatEuro(profile.shipping_cost)}${profile.is_default ? " (Standard)" : ""}`;
    select.appendChild(new Option(label, profile.id));
  });
  const current = product.listing && product.listing.shipping_profile;
  const fallback = shippingProfiles.find((profile) => profile.is_default);
  select.value = current || (fallback ? fallback.id : "");
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

function _setText(id, text) {
  const element = document.getElementById(id);
  element.textContent = text;
  element.style.display = text ? "block" : "none";
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
    _setText("condition-hint", data.condition_hint);
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

// Everything the dialog sends; null if no category is chosen yet.
function _publishPayload() {
  const chosen = document.querySelector('input[name="ebay-category"]:checked');
  if (!chosen) return null;
  const category = categoryOptions[Number(chosen.value)];
  const profile = inputValue("publish-profile");
  return {
    category_id: category.id,
    category_name: category.path,
    aspects: _collectAspects(),
    shipping_profile: profile ? Number(profile) : null,
    best_offer: document.getElementById("publish-best-offer").checked,
  };
}

async function _submitPublish(e) {
  e.preventDefault();
  const payload = _publishPayload();
  if (!payload) return _publishMessage("Bitte eine eBay-Kategorie auswählen.");
  _setBusy("publish-submit", true);
  let published = false;
  try {
    await apiSend(`/ebay/listings/${publishProduct.id}/publish/`, "POST", payload);
    published = true;
  } catch (err) {
    _publishMessage(errorText(err));
  }
  _setBusy("publish-submit", false);
  if (published) _closePublish();
  await _reloadListings();
  if (published) _panelMessage("Artikel ist bei eBay online – siehe Reiter „Inserate“.", false);
}

// Ask eBay what listing this article would cost, without publishing it.
async function _previewFees() {
  const payload = _publishPayload();
  if (!payload) return _publishMessage("Bitte eine eBay-Kategorie auswählen.");
  if (!document.getElementById("publish-form").reportValidity()) return;
  _setBusy("fee-btn", true);
  try {
    const data = await apiSend(`/ebay/listings/${publishProduct.id}/preview/`, "POST", payload);
    _setText("fee-result", _feeText(data));
    _publishMessage("");
  } catch (err) {
    _publishMessage(errorText(err));
  }
  _setBusy("fee-btn", false);
}

function _feeText(data) {
  if (!data.fees.length) return "eBay berechnet für dieses Inserat keine Einstellgebühren (Verkaufsprovision fällt erst beim Verkauf an).";
  const parts = data.fees.map((fee) => `${fee.type}: ${formatEuro(fee.amount)}`).join(" · ");
  return `Einstellgebühren laut eBay: ${formatEuro(data.total)} (${parts}).`;
}

function _setBusy(buttonId, busy) {
  const button = document.getElementById(buttonId);
  if (busy) button.dataset.label = button.textContent;
  button.disabled = busy;
  button.textContent = busy ? "Wird übertragen …" : button.dataset.label;
}
