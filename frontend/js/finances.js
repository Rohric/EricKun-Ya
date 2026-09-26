"use strict";

requireAuth();
renderNav("finances.html");

const MONTHS = ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"];
const YEAR = new Date().getFullYear();

let range = periodRange("year");

document.getElementById("year-label").textContent = YEAR;
document.getElementById("save-reserve").addEventListener("click", _saveReserve);
document.getElementById("new-goal-btn").addEventListener("click", _toggleGoalForm);
document.getElementById("cancel-goal").addEventListener("click", _toggleGoalForm);
document.getElementById("goal-form").addEventListener("submit", _saveGoal);
document.getElementById("apply-range").addEventListener("click", _applyCustomRange);
document.querySelectorAll("#period-switch button").forEach((btn) =>
  btn.addEventListener("click", () => _selectPeriod(btn.dataset.period))
);

init();

async function init() {
  try {
    await Promise.all([_loadSummary(), _loadMonthly(), _loadSettings(), _loadGoals()]);
  } catch (err) {
    showMessage(errorText(err));
  }
}

function _selectPeriod(preset) {
  range = periodRange(preset);
  document.querySelectorAll("#period-switch button").forEach((btn) =>
    btn.classList.toggle("active", btn.dataset.period === preset)
  );
  _loadSummary().catch((err) => showMessage(errorText(err)));
}

function _applyCustomRange() {
  const from = document.getElementById("range-from").value;
  const to = document.getElementById("range-to").value;
  if (!from || !to) return showMessage("Bitte von und bis wählen.");
  range = { from, to };
  document.querySelectorAll("#period-switch button").forEach((btn) => btn.classList.remove("active"));
  _loadSummary().catch((err) => showMessage(errorText(err)));
}

// Load the tax breakdown + revenue/expense tiles for the current range.
async function _loadSummary() {
  const data = await apiGet(`/finance/reports/profit-loss/?from=${range.from}&to=${range.to}`);
  _renderTax(data);
  const tiles = [["Umsatz", data.revenue], ["Einkauf", data.expenses]];
  document.getElementById("pl-tiles").innerHTML = tiles.map(([label, value]) =>
    `<div class="tile"><span class="tile-label">${label}</span>
     <span class="tile-value">${formatEuro(value)}</span></div>`
  ).join("");
}

function _renderTax(data) {
  document.getElementById("tax-period").textContent = `(${range.from} – ${range.to})`;
  document.getElementById("tax-gross").textContent = formatEuro(data.gross_profit);
  document.getElementById("tax-rate").textContent = data.tax_rate;
  document.getElementById("tax-reserve").textContent = formatEuro(data.tax_reserve);
  document.getElementById("tax-net").textContent = formatEuro(data.net_profit);
}

async function _loadMonthly() {
  const data = await apiGet(`/finance/reports/monthly-revenue/?year=${YEAR}`);
  const values = data.monthly_revenue.map(Number);
  const max = Math.max(...values, 1);
  document.getElementById("monthly-chart").innerHTML = values.map((v, i) => `
    <div class="bar-col" title="${formatEuro(v)}">
      <div class="bar" style="height:${(v / max) * 100}%"></div>
      <span class="bar-label">${MONTHS[i]}</span>
    </div>`).join("");
}

async function _loadSettings() {
  const data = await apiGet("/finance/settings/");
  document.getElementById("reserve-rate").value = data.tax_reserve_rate;
}

async function _saveReserve() {
  try {
    await apiSend("/finance/settings/", "PATCH", { tax_reserve_rate: document.getElementById("reserve-rate").value });
    showMessage("Rücklagensatz gespeichert.", false);
    _loadSummary();
  } catch (err) {
    showMessage(errorText(err));
  }
}

async function _loadGoals() {
  const goals = await apiGet("/goals/");
  const active = goals.filter((g) => g.is_active);
  document.getElementById("goals").innerHTML = active.length
    ? active.map(_goalCard).join("")
    : `<p class="empty">Noch keine aktiven Ziele.</p>`;
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

function _toggleGoalForm() {
  const form = document.getElementById("goal-form");
  form.style.display = form.style.display === "none" ? "grid" : "none";
  showMessage("", false);
}

async function _saveGoal(e) {
  e.preventDefault();
  const payload = {
    title: document.getElementById("g-title").value.trim(),
    target_amount: document.getElementById("g-target").value,
    metric: document.getElementById("g-metric").value,
    period: document.getElementById("g-period").value,
    start_date: document.getElementById("g-start").value,
    end_date: document.getElementById("g-end").value || null,
  };
  try {
    await apiSend("/goals/", "POST", payload);
    document.getElementById("goal-form").reset();
    _toggleGoalForm();
    _loadGoals();
  } catch (err) {
    showMessage(errorText(err));
  }
}
