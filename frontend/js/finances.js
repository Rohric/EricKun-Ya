"use strict";

requireAuth();
renderNav("finances.html");

const MONTHS = ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"];
const FINANCE_TABS = [
  ["overview", "Übersicht"], ["sales", "Verkäufe"], ["breakdown", "Aufteilung"],
  ["goals", "Ziele"], ["settings", "Einstellungen"],
];
const PANEL_LOADERS = {
  overview: _loadOverview, sales: _loadSales, breakdown: _loadBreakdown,
  goals: _loadGoals, settings: _loadSettings,
};
const PERIOD_PANELS = ["overview", "sales", "breakdown"];  // panels the period filter applies to

let range = periodRange("year");
let chartYear = new Date().getFullYear();
let goals = [];
let activeTab = _tabFromHash();
let categoriesLoaded = false;

document.getElementById("settings-form").addEventListener("submit", _saveSettings);
document.getElementById("new-goal-btn").addEventListener("click", () => _openGoalForm());
document.getElementById("cancel-goal").addEventListener("click", _closeGoalForm);
document.getElementById("goal-form").addEventListener("submit", _saveGoal);
document.getElementById("apply-range").addEventListener("click", _applyCustomRange);
document.getElementById("year-prev").addEventListener("click", () => _shiftYear(-1));
document.getElementById("year-next").addEventListener("click", () => _shiftYear(1));
document.getElementById("report-category").addEventListener("change", _reloadPanel);
document.getElementById("report-channel").addEventListener("change", _reloadPanel);
document.querySelectorAll("#period-switch button").forEach((btn) =>
  btn.addEventListener("click", () => _selectPeriod(btn.dataset.period))
);

_showTab(activeTab);

// --- Tabs ---

function _tabFromHash() {
  const tab = window.location.hash.replace("#", "");
  return FINANCE_TABS.some(([key]) => key === tab) ? tab : "overview";
}

function _showTab(tab) {
  activeTab = tab;
  window.location.hash = tab;
  renderTabs("finance-tabs", FINANCE_TABS, tab, _showTab);
  document.querySelectorAll(".panel").forEach((panel) => {
    panel.style.display = panel.dataset.panel === tab ? "block" : "none";
  });
  document.getElementById("period-card").style.display = PERIOD_PANELS.includes(tab) ? "block" : "none";
  showMessage("", false);
  _reloadPanel();
}

function _reloadPanel() {
  document.getElementById("period-label").textContent = `${_germanDate(range.from)} – ${_germanDate(range.to)}`;
  PANEL_LOADERS[activeTab]().catch((err) => showMessage(errorText(err)));
}

function _germanDate(iso) {
  return new Date(`${iso}T00:00:00`).toLocaleDateString("de-DE");
}

// --- Period filter ---

function _selectPeriod(preset) {
  range = periodRange(preset);
  markActive("period-switch", "period", preset);
  _reloadPanel();
}

function _applyCustomRange() {
  const from = inputValue("range-from");
  const to = inputValue("range-to");
  if (!from || !to) return showMessage("Bitte von und bis wählen.");
  range = { from, to };
  markActive("period-switch", "period", "");
  _reloadPanel();
}

function _rangeQuery() {
  return `from=${range.from}&to=${range.to}`;
}

// --- Overview: tax breakdown, tiles, monthly chart ---

async function _loadOverview() {
  const [data] = await Promise.all([apiGet(`/finance/reports/profit-loss/?${_rangeQuery()}`), _loadMonthly()]);
  _renderTax(data);
  renderTiles("pl-tiles", [
    ["Umsatz", data.revenue], ["Einkauf", data.expenses],
    ["Geschätzte eBay-Gebühren", data.estimated_fees], ["Zahlung offen", data.pending_revenue],
  ]);
}

function _renderTax(data) {
  document.getElementById("tax-gross").textContent = formatEuro(data.gross_profit);
  document.getElementById("tax-rate").textContent = data.tax_rate;
  document.getElementById("tax-reserve").textContent = formatEuro(data.tax_reserve);
  document.getElementById("tax-net").textContent = formatEuro(data.net_profit);
  document.getElementById("fee-note").textContent = Number(data.estimated_fees) > 0
    ? `Im Brutto-Gewinn sind geschätzte eBay-Gebühren von ${formatEuro(data.estimated_fees)} bereits abgezogen.`
    : "";
}

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

// --- Sales: purchase and sale price per sold position ---

async function _loadSales() {
  if (!categoriesLoaded) await _fillCategoryFilter();
  const filters = { ...range, category: inputValue("report-category"), channel: inputValue("report-channel") };
  await renderSalesReport("sales-report", filters);
}

async function _fillCategoryFilter() {
  const categories = await apiGet("/categories/");
  const select = document.getElementById("report-category");
  select.innerHTML = "";
  select.appendChild(new Option("Alle Kategorien", ""));
  categories.forEach((category) => select.appendChild(new Option(category.path, category.id)));
  categoriesLoaded = true;
}

// --- Breakdown by channel and by category ---

async function _loadBreakdown() {
  const [channels, categories] = await Promise.all([
    apiGet(`/finance/reports/breakdown/?${_rangeQuery()}&by=channel`),
    apiGet(`/finance/reports/breakdown/?${_rangeQuery()}&by=category`),
  ]);
  _renderBreakdown("breakdown-channel", channels.groups);
  _renderBreakdown("breakdown-category", categories.groups);
}

// Table with a bar per group showing its share of the total revenue.
function _renderBreakdown(containerId, groups) {
  const total = groups.reduce((sum, group) => sum + Number(group.revenue), 0) || 1;
  const rows = groups.map((group) => `
    <tr>
      <td>${escapeHtml(group.label)}</td>
      <td class="share-cell"><div class="share-bar" style="width:${(Number(group.revenue) / total) * 100}%"></div></td>
      <td class="num">${group.positions}</td>
      <td class="num">${formatEuro(group.revenue)}</td>
      <td class="num">${formatEuro(group.fee)}</td>
      <td class="num">${formatEuro(group.profit)}</td>
      <td class="num">${formatPercent(group.margin)}</td>
    </tr>`).join("");
  document.getElementById(containerId).innerHTML = `
    <table class="data-table report-table">
      <thead><tr><th></th><th>Anteil am Umsatz</th><th class="num">Positionen</th><th class="num">Umsatz</th>
        <th class="num">Gebühr (geschätzt)</th><th class="num">Gewinn</th><th class="num">Marge</th></tr></thead>
      <tbody>${rows || `<tr><td colspan="7" class="empty">Keine Verkäufe in diesem Zeitraum.</td></tr>`}</tbody>
    </table>`;
}

// --- Settings: reserve rate and estimated fee rate ---

async function _loadSettings() {
  const data = await apiGet("/finance/settings/");
  document.getElementById("reserve-rate").value = data.tax_reserve_rate;
  document.getElementById("fee-rate").value = data.ebay_fee_rate;
}

async function _saveSettings(e) {
  e.preventDefault();
  const payload = { tax_reserve_rate: inputValue("reserve-rate"), ebay_fee_rate: inputValue("fee-rate") };
  try {
    await apiSend("/finance/settings/", "PATCH", payload);
    showMessage("Einstellungen gespeichert.", false);
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
    await _loadGoals();
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
    await _loadGoals();
  } catch (err) {
    showMessage(errorText(err));
  }
}

async function _deleteGoal(id) {
  if (!confirm("Dieses Ziel wirklich löschen?")) return;
  try {
    await apiDelete(`/goals/${id}/`);
    await _loadGoals();
  } catch (err) {
    showMessage(errorText(err));
  }
}
