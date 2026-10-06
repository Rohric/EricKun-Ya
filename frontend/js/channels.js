"use strict";

// Page "Zuordnung": listings that are online on a sales channel but belong to no article yet.
// Each one can be linked to an article, turned into a new article or ignored.

requireAuth();
renderNav("channels.html");

// The sales channels. A further portal only needs an entry here – its app has to offer the same
// endpoints below its base path and answer in the same format as the eBay app.
const CHANNELS = [
  { key: "ebay", label: "eBay", base: "/ebay" },
];
const COLUMN_COUNT = 9;
const ONLINE = "online";
const LEGACY_WARNING =
  "Dieses Inserat wurde nicht über das Programm angelegt. Es bekommt beim Portal die Artikelnummer des " +
  "Artikels und wird umgestellt. Danach lässt es sich nur noch über dieses Programm ändern. Fortfahren?";

let listings = [];        // unassigned listings of all channels
let products = [];        // all articles that are not archived
let channelStates = {};   // {channel key: {product id: [channel entries]}}

document.getElementById("filter-channel").addEventListener("change", _render);
document.getElementById("show-ignored").addEventListener("change", _reload);
document.getElementById("create-all-btn").addEventListener("click", _createAll);

init();

async function init() {
  _renderChannelControls();
  try {
    await loadListings();
  } catch (err) {
    showMessage(errorText(err));
  }
}

// Fill the channel filter and add one "abgleichen" button per channel.
function _renderChannelControls() {
  const options = CHANNELS.map((channel) => `<option value="${channel.key}">${channel.label}</option>`).join("");
  document.getElementById("filter-channel").innerHTML = `<option value="">Alle Portale</option>${options}`;
  const box = document.getElementById("pull-buttons");
  box.innerHTML = CHANNELS.map((channel) =>
    `<button type="button" data-pull="${channel.key}">Mit ${channel.label} abgleichen</button>`
  ).join("");
  box.querySelectorAll("[data-pull]").forEach((btn) =>
    btn.addEventListener("click", () => _pull(_channel(btn.dataset.pull)))
  );
}

function _channel(key) {
  return CHANNELS.find((channel) => channel.key === key);
}

// --- Loading ---

async function loadListings() {
  const ignored = document.getElementById("show-ignored").checked ? "?ignored=1" : "";
  const perChannel = await Promise.all(CHANNELS.map((channel) => apiGet(`${channel.base}/unassigned/${ignored}`)));
  listings = perChannel.flat();
  products = (await apiGet("/products/?view=all")).filter((product) => product.status !== "archived");
  await _loadChannelStates();
  _render();
}

async function _loadChannelStates() {
  const states = await Promise.all(CHANNELS.map((channel) => apiGet(`${channel.base}/listing-states/`)));
  channelStates = Object.fromEntries(CHANNELS.map((channel, index) => [channel.key, states[index]]));
}

function _reload() {
  return loadListings().catch((err) => showMessage(errorText(err)));
}

// --- Table ---

function _render() {
  const wanted = inputValue("filter-channel");
  const rows = listings.filter((listing) => !wanted || listing.channel === wanted);
  document.getElementById("listing-rows").innerHTML =
    rows.map(_row).join("") || `<tr><td colspan="${COLUMN_COUNT}" class="empty">${_emptyText()}</td></tr>`;
  document.getElementById("create-all-btn").disabled = !rows.some(_canBecomeProduct);
  _bindActions();
}

function _emptyText() {
  return document.getElementById("show-ignored").checked
    ? "Keine ignorierten Inserate."
    : "Alle Inserate sind zugeordnet. „Abgleichen“ holt neue Inserate vom Portal.";
}

function _canBecomeProduct(listing) {
  return listing.supported && !listing.ignored;
}

function _row(listing) {
  const key = `${listing.channel}:${listing.id}`;
  return `
    <tr class="${listing.ignored ? "row-muted" : ""}">
      <td><span class="chip">${escapeHtml(listing.channel_label)}</span></td>
      <td>${_thumb(listing)}</td>
      <td>${_titleCell(listing)}</td>
      <td>${escapeHtml(listing.channel_sku) || '<span class="hint">keine</span>'}<span class="row-note">Inserat ${escapeHtml(listing.listing_id) || "–"}</span></td>
      <td>${listing.price == null ? "–" : formatEuro(listing.price)}</td>
      <td>${listing.quantity}</td>
      <td>${_notes(listing)}</td>
      <td>${_canBecomeProduct(listing) ? _productSelect(listing, key) : ""}</td>
      <td class="actions">${_actions(listing, key)}</td>
    </tr>`;
}

function _thumb(listing) {
  return listing.image
    ? `<img class="thumb" src="${escapeHtml(listing.image)}" alt="" />`
    : `<span class="no-thumb">–</span>`;
}

function _titleCell(listing) {
  const link = listing.url
    ? `<br><a class="link-btn" href="${escapeHtml(listing.url)}" target="_blank" rel="noopener">Ansehen</a>`
    : "";
  return `<strong>${escapeHtml(listing.title)}</strong>${link}`;
}

function _notes(listing) {
  if (!listing.notes.length) return '<span class="hint">–</span>';
  return listing.notes.map((note) => `<span class="row-note">${escapeHtml(note)}</span>`).join("");
}

// Articles this listing can be linked to: every article without an online listing on the same channel.
function _freeProducts(listing) {
  const states = channelStates[listing.channel] || {};
  return products.filter((product) =>
    !(states[product.id] || []).some((entry) => entry.status === ONLINE)
  );
}

function _productSelect(listing, key) {
  const suggested = listing.suggestion ? listing.suggestion.id : null;
  const options = _freeProducts(listing).map((product) =>
    `<option value="${product.id}" ${product.id === suggested ? "selected" : ""}>${escapeHtml(product.sku)} – ${escapeHtml(product.title)}</option>`
  ).join("");
  const hint = suggested ? '<span class="row-note">Vorschlag – bitte prüfen</span>' : "";
  return `<select class="product-pick" data-product="${key}"><option value="">– Artikel wählen –</option>${options}</select>${hint}`;
}

function _actions(listing, key) {
  const button = (action, label, extra = "") =>
    `<button type="button" class="link-btn ${extra}" data-${action}="${key}">${label}</button>`;
  if (listing.ignored) return button("show", "Wieder anzeigen");
  if (!listing.supported) return button("ignore", "Ignorieren");
  return button("link", "Verknüpfen") + button("create", "Neuer Artikel") + button("ignore", "Ignorieren");
}

function _bindActions() {
  const table = document.getElementById("listing-rows");
  const bind = (action, handler) => table.querySelectorAll(`[data-${action}]`).forEach((btn) =>
    btn.addEventListener("click", () => handler(_listingByKey(btn.getAttribute(`data-${action}`))))
  );
  bind("link", _link);
  bind("create", _create);
  bind("ignore", (listing) => _setIgnored(listing, true));
  bind("show", (listing) => _setIgnored(listing, false));
}

function _listingByKey(key) {
  return listings.find((listing) => `${listing.channel}:${listing.id}` === key);
}

function _path(listing, action) {
  return `${_channel(listing.channel).base}/unassigned/${listing.id}/${action}/`;
}

// --- Actions ---

async function _pull(channel) {
  showMessage(`Inserate werden von ${channel.label} geholt …`, false);
  try {
    const result = await apiSend(`${channel.base}/listings/pull/`, "POST", {});
    await loadListings();
    showMessage(
      `${result.found} Inserate bei ${channel.label} gefunden, ${result.linked} automatisch verknüpft, ` +
      `${result.unassigned} warten auf Zuordnung.`, false
    );
  } catch (err) {
    showMessage(errorText(err));
  }
}

async function _link(listing) {
  const select = document.querySelector(`[data-product="${listing.channel}:${listing.id}"]`);
  if (!select.value) return showMessage("Bitte zuerst einen Artikel wählen.");
  if (listing.needs_migration && !confirm(LEGACY_WARNING)) return;
  await _run(
    () => apiSend(_path(listing, "link"), "POST", { product: Number(select.value) }),
    (product) => `Verknüpft mit ${product.sku}. ${_stateHint(product)}`
  );
}

// After linking, the article is the truth; say so if the listing differs from it.
function _stateHint(product) {
  return product.listing && product.listing.state === "changed"
    ? "Preis oder Menge weichen ab – das Inserat steht auf „Geändert“ und wird beim Synchronisieren angepasst."
    : "";
}

async function _create(listing) {
  if (listing.needs_migration && !confirm(LEGACY_WARNING)) return;
  await _run(
    () => apiSend(_path(listing, "create-product"), "POST", {}),
    (product) => `Artikel ${product.sku} angelegt. Bitte den Einkaufspreis unter „Artikel“ nachtragen.`
  );
}

async function _setIgnored(listing, ignored) {
  await _run(
    () => apiSend(_path(listing, "ignore"), "POST", { ignored }),
    () => (ignored ? "Inserat wird ignoriert." : "Inserat wird wieder angezeigt.")
  );
}

async function _createAll() {
  const wanted = inputValue("filter-channel");
  const channels = CHANNELS.filter((channel) => !wanted || channel.key === wanted);
  const count = listings.filter((listing) => _canBecomeProduct(listing) && (!wanted || listing.channel === wanted)).length;
  const question = `Für ${count} Inserate je einen neuen Artikel anlegen? Inserate, die nicht über das Programm ` +
    "angelegt wurden, bekommen dabei die neue Artikelnummer und werden umgestellt.";
  if (!confirm(question)) return;
  await _run(
    () => Promise.all(channels.map((channel) => apiSend(`${channel.base}/unassigned/create-products/`, "POST", {}))),
    _createAllText
  );
}

function _createAllText(results) {
  const created = results.reduce((sum, result) => sum + result.created, 0);
  const failed = results.reduce((sum, result) => sum + result.failed, 0);
  const rest = failed ? ` ${failed} hat das Portal abgelehnt – der Grund steht beim Inserat.` : "";
  return `${created} Artikel angelegt. Bitte die Einkaufspreise unter „Artikel“ nachtragen.${rest}`;
}

// Run an action, reload the table and report the outcome (the reason stays visible on failure).
async function _run(action, describe) {
  showMessage("Bitte warten …", false);
  let text = "";
  let failed = false;
  try {
    text = describe(await action());
  } catch (err) {
    text = errorText(err);
    failed = true;
  }
  await _reload();
  showMessage(text, failed);
}
