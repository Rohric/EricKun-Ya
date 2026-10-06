"use strict";

requireAuth();
renderNav("dashboard.html");

let currentPeriod = "year";

document.querySelectorAll("#period-switch button").forEach((btn) =>
  btn.addEventListener("click", () => _selectPeriod(btn.dataset.period))
);

init();

async function init() {
  try {
    await _loadAll();
  } catch (err) {
    showMessage(errorText(err));
  }
  _fetchEbaySales();
}

function _loadAll() {
  return Promise.all([_loadAreas(), _loadTiles(), _loadGoals()]);
}

// Pick up new eBay sales in the background and refresh the numbers if something came in.
async function _fetchEbaySales() {
  const result = await autoImportEbayOrders();
  if (!ebayImportChanged(result)) return;
  showMessage(ebayImportText(result), false);
  await _loadAll().catch(() => {});
}

// Area tiles: one per section, each with its key figure and a link into the section.
async function _loadAreas() {
  const [summary, ebay] = await Promise.all([apiGet("/dashboard/summary/"), apiGet("/ebay/status/")]);
  const tiles = [
    _ordersTile(summary.orders), _financeTile(summary.finance),
    _stockTile(summary.stock), _ebayTile(ebay),
  ];
  document.getElementById("area-tiles").innerHTML = tiles.map(_areaTile).join("");
}

function _areaTile({ href, title, value, note }) {
  return `<a class="area-tile" href="${href}">
      <span class="area-title">${title}</span>
      <span class="area-value">${value}</span>
      <span class="area-note">${note}</span>
    </a>`;
}

function _ordersTile(orders) {
  const notes = [];
  if (orders.unpaid) notes.push(`${orders.unpaid} Zahlung offen`);
  if (orders.in_return) notes.push(`${orders.in_return} in Reklamation`);
  const note = notes.join(" · ") || "alles bezahlt, keine Reklamation";
  return { href: "orders.html", title: "Bestellungen", value: `${orders.to_ship} zu verschicken`, note };
}

function _financeTile(finance) {
  const note = `Gewinn ${formatEuro(finance.profit_month)} in diesem Monat`;
  return { href: "finances.html", title: "Finanzen", value: formatEuro(finance.revenue_month), note };
}

function _stockTile(stock) {
  return { href: "warehouse.html", title: "Lager", value: `${stock.products} Artikel`, note: `${stock.units} Stück verkaufbar` };
}

function _ebayTile(ebay) {
  if (!ebay.connected) return { href: "ebay.html", title: "eBay", value: "nicht verbunden", note: "Verbindung einrichten" };
  const counts = ebay.listings;
  const note = `${counts.changed} geändert · ${counts.error} mit Fehler`;
  return { href: "ebay.html", title: "eBay", value: `${counts.online + counts.changed} online`, note };
}

function _selectPeriod(preset) {
  currentPeriod = preset;
  markActive("period-switch", "period", preset);
  _loadTiles().catch((err) => showMessage(errorText(err)));
}

// Load the summary tiles for the selected period.
async function _loadTiles() {
  const { from, to } = periodRange(currentPeriod);
  const data = await apiGet(`/finance/reports/profit-loss/?from=${from}&to=${to}`);
  renderTiles("pl-tiles", [
    ["Umsatz", data.revenue], ["Netto-Gewinn", data.net_profit],
    ["Rücklage", data.tax_reserve], ["Brutto-Gewinn", data.gross_profit],
  ]);
}

async function _loadGoals() {
  const active = (await apiGet("/goals/")).filter((goal) => goal.is_active);
  document.getElementById("goals").innerHTML = active.length
    ? active.map((goal) => renderGoalCard(goal)).join("")
    : `<p class="empty">Noch keine aktiven Ziele. <a href="finances.html">Anlegen</a></p>`;
}
