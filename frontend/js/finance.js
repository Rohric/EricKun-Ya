"use strict";

requireAuth();
renderNav("dashboard.html");

const MONTHS = ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"];
const YEAR = new Date().getFullYear();

document.getElementById("year-label").textContent = YEAR;
document.getElementById("save-reserve").addEventListener("click", _saveReserve);
document.getElementById("new-goal-btn").addEventListener("click", _toggleGoalForm);
document.getElementById("cancel-goal").addEventListener("click", _toggleGoalForm);
document.getElementById("goal-form").addEventListener("submit", _saveGoal);

init();

// Load all dashboard sections in parallel.
async function init() {
  try {
    await Promise.all([_loadProfitLoss(), _loadMonthly(), _loadSettings(), _loadGoals()]);
  } catch (err) {
    showMessage(errorText(err));
  }
}

async function _loadProfitLoss() {
  const data = await apiGet(`/finance/reports/profit-loss/?from=${YEAR}-01-01&to=${YEAR}-12-31`);
  const tiles = [
    ["Umsatz", data.revenue], ["Gewinn", data.profit],
    ["Einkauf", data.expenses], ["Rücklage", data.tax_reserve],
  ];
  document.getElementById("pl-tiles").innerHTML = tiles.map(([label, value]) =>
    `<div class="tile"><span class="tile-label">${label}</span>
     <span class="tile-value">${formatEuro(value)}</span></div>`
  ).join("");
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
    _loadProfitLoss();
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
