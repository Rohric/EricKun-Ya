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
    await Promise.all([_loadTiles(), _loadGoals()]);
  } catch (err) {
    showMessage(errorText(err));
  }
  _fetchEbaySales();
}

// Pick up new eBay sales in the background and refresh the numbers if something came in.
async function _fetchEbaySales() {
  const result = await autoImportEbayOrders();
  if (!ebayImportChanged(result)) return;
  showMessage(ebayImportText(result), false);
  await Promise.all([_loadTiles(), _loadGoals()]).catch(() => {});
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
