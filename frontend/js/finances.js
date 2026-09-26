"use strict";

requireAuth();
renderNav("finances.html");

const MONTHS = ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"];

let range = periodRange("year");
let chartYear = new Date().getFullYear();
let goals = [];

document.getElementById("save-reserve").addEventListener("click", _saveReserve);
document.getElementById("new-goal-btn").addEventListener("click", () => _openGoalForm());
document.getElementById("cancel-goal").addEventListener("click", _closeGoalForm);
document.getElementById("goal-form").addEventListener("submit", _saveGoal);
document.getElementById("apply-range").addEventListener("click", _applyCustomRange);
document.getElementById("year-prev").addEventListener("click", () => _shiftYear(-1));
document.getElementById("year-next").addEventListener("click", () => _shiftYear(1));
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

// --- Period filter + tax breakdown ---

function _selectPeriod(preset) {
  range = periodRange(preset);
  markActive("period-switch", "period", preset);
  _loadSummary().catch((err) => showMessage(errorText(err)));
}

function _applyCustomRange() {
  const from = inputValue("range-from");
  const to = inputValue("range-to");
  if (!from || !to) return showMessage("Bitte von und bis wählen.");
  range = { from, to };
  markActive("period-switch", "period", "");
  _loadSummary().catch((err) => showMessage(errorText(err)));
}

// Load the tax breakdown + revenue/expense tiles for the current range.
async function _loadSummary() {
  const data = await apiGet(`/finance/reports/profit-loss/?from=${range.from}&to=${range.to}`);
  _renderTax(data);
  renderTiles("pl-tiles", [["Umsatz", data.revenue], ["Einkauf", data.expenses]]);
}

function _renderTax(data) {
  document.getElementById("tax-period").textContent = `(${range.from} – ${range.to})`;
  document.getElementById("tax-gross").textContent = formatEuro(data.gross_profit);
  document.getElementById("tax-rate").textContent = data.tax_rate;
  document.getElementById("tax-reserve").textContent = formatEuro(data.tax_reserve);
  document.getElementById("tax-net").textContent = formatEuro(data.net_profit);
}

// --- Monthly chart with year switch ---

function _shiftYear(delta) {
  chartYear += delta;
  _loadMonthly().catch((err) => showMessage(errorText(err)));
}

async function _loadMonthly() {
  document.getElementById("year-label").textContent = chartYear;
  const data = await apiGet(`/finance/reports/monthly-revenue/?year=${chartYear}`);
  const values = data.monthly_revenue.map(Number);
  const max = Math.max(...values, 1);
  document.getElementById("monthly-chart").innerHTML = values.map((v, i) => `
    <div class="bar-col" title="${formatEuro(v)}">
      <div class="bar" style="height:${(v / max) * 100}%"></div>
      <span class="bar-label">${MONTHS[i]}</span>
    </div>`).join("");
}

// --- Reserve rate ---

async function _loadSettings() {
  const data = await apiGet("/finance/settings/");
  document.getElementById("reserve-rate").value = data.tax_reserve_rate;
}

async function _saveReserve() {
  try {
    await apiSend("/finance/settings/", "PATCH", { tax_reserve_rate: inputValue("reserve-rate") });
    showMessage("Rücklagensatz gespeichert.", false);
    _loadSummary();
  } catch (err) {
    showMessage(errorText(err));
  }
}

// --- Goals (all goals, editable) ---

async function _loadGoals() {
  goals = await apiGet("/goals/");
  document.getElementById("goals").innerHTML = goals.length
    ? goals.map((goal) => renderGoalCard(goal, true)).join("")
    : `<p class="empty">Noch keine Ziele.</p>`;
  _bindGoalActions();
}

function _bindGoalActions() {
  const bind = (attr, handler) => document.querySelectorAll(`[data-${attr}]`).forEach((btn) =>
    btn.addEventListener("click", () => handler(Number(btn.getAttribute(`data-${attr}`))))
  );
  bind("goal-edit", (id) => _openGoalForm(goals.find((goal) => goal.id === id)));
  bind("goal-toggle", _toggleGoal);
  bind("goal-del", _deleteGoal);
}

function _openGoalForm(goal) {
  const set = (id, value) => { document.getElementById(id).value = value ?? ""; };
  set("g-id", goal ? goal.id : "");
  set("g-title", goal ? goal.title : "");
  set("g-target", goal ? goal.target_amount : "");
  set("g-start", goal ? goal.start_date : "");
  set("g-end", goal ? goal.end_date : "");
  document.getElementById("g-metric").value = goal ? goal.metric : "revenue";
  document.getElementById("g-period").value = goal ? goal.period : "yearly";
  document.getElementById("goal-form").style.display = "grid";
  showMessage("", false);
}

function _closeGoalForm() {
  document.getElementById("goal-form").reset();
  document.getElementById("g-id").value = "";
  document.getElementById("goal-form").style.display = "none";
}

async function _saveGoal(e) {
  e.preventDefault();
  const id = inputValue("g-id");
  try {
    if (id) await apiSend(`/goals/${id}/`, "PATCH", _goalPayload());
    else await apiSend("/goals/", "POST", _goalPayload());
    _closeGoalForm();
    _loadGoals();
  } catch (err) {
    showMessage(errorText(err));
  }
}

function _goalPayload() {
  return {
    title: inputValue("g-title"),
    target_amount: inputValue("g-target"),
    metric: inputValue("g-metric"),
    period: inputValue("g-period"),
    start_date: inputValue("g-start"),
    end_date: inputValue("g-end") || null,
  };
}

async function _toggleGoal(id) {
  const goal = goals.find((item) => item.id === id);
  try {
    await apiSend(`/goals/${id}/`, "PATCH", { is_active: !goal.is_active });
    _loadGoals();
  } catch (err) {
    showMessage(errorText(err));
  }
}

async function _deleteGoal(id) {
  if (!confirm("Dieses Ziel wirklich löschen?")) return;
  try {
    await apiDelete(`/goals/${id}/`);
    _loadGoals();
  } catch (err) {
    showMessage(errorText(err));
  }
}
