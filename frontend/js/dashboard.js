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
}

function _selectPeriod(preset) {
  currentPeriod = preset;
  document.querySelectorAll("#period-switch button").forEach((btn) =>
    btn.classList.toggle("active", btn.dataset.period === preset)
  );
  _loadTiles().catch((err) => showMessage(errorText(err)));
}

// Load the summary tiles for the selected period.
async function _loadTiles() {
  const { from, to } = periodRange(currentPeriod);
  const data = await apiGet(`/finance/reports/profit-loss/?from=${from}&to=${to}`);
  const tiles = [
    ["Umsatz", data.revenue], ["Netto-Gewinn", data.net_profit],
    ["Rücklage", data.tax_reserve], ["Brutto-Gewinn", data.gross_profit],
  ];
  document.getElementById("pl-tiles").innerHTML = tiles.map(([label, value]) =>
    `<div class="tile"><span class="tile-label">${label}</span>
     <span class="tile-value">${formatEuro(value)}</span></div>`
  ).join("");
}

async function _loadGoals() {
  const goals = await apiGet("/goals/");
  const active = goals.filter((g) => g.is_active);
  document.getElementById("goals").innerHTML = active.length
    ? active.map(_goalCard).join("")
    : `<p class="empty">Noch keine aktiven Ziele. <a href="finances.html">Anlegen</a></p>`;
}

function _goalCard(goal) {
  const percent = Math.min(Number(goal.progress.percent), 100);
  const metric = goal.metric === "profit" ? "Gewinn" : "Umsatz";
  return `
    <div class="goal">
      <div class="goal-head">
        <strong>${escapeHtml(goal.title)}</strong>
        <span>${formatEuro(goal.progress.current)} / ${formatEuro(goal.target_amount)} (${metric})</span>
      </div>
      <div class="progress"><div class="progress-bar" style="width:${percent}%"></div></div>
      <span class="goal-percent">${goal.progress.percent}%</span>
    </div>`;
}
