"use strict";

// Shell of the eBay tab: sub-tabs, the overview panel and the report panel.
// The other panels live in ebay-listings.js, ebay-templates.js and ebay-sales.js.

requireAuth();
renderNav("ebay.html");

const EBAY_TABS = [
  ["overview", "Übersicht"], ["listings", "Inserate"], ["new", "Neu inserieren"],
  ["templates", "Vorlagen"], ["sales", "Verkäufe"], ["report", "Auswertung"],
];
const TAB_LOADERS = {
  overview: loadOverview, listings: loadListings, new: loadUnlisted,
  templates: loadTemplates, sales: loadSales, report: loadEbayReport,
};
const NEEDS_SETUP = ["listings", "new"];  // only usable once the checklist is complete
const NEEDS_CONNECTION = ["templates"];
const WAITING_STATES = ["open", "packed"];

let ebayStatus = null;
let activeTab = _tabFromHash();
let reportPeriod = "year";

document.getElementById("connect-btn").addEventListener("click", _startConnect);
document.getElementById("finish-btn").addEventListener("click", _finishConnect);
document.getElementById("disconnect-btn").addEventListener("click", _disconnect);
document.querySelectorAll("#report-period button").forEach((btn) =>
  btn.addEventListener("click", () => _selectReportPeriod(btn.dataset.period))
);
// Follow the browser's back/forward buttons between sub-tabs.
window.addEventListener("hashchange", () => {
  if (_tabFromHash() !== activeTab) selectTab(_tabFromHash());
});

init();

async function init() {
  try {
    await refresh();
  } catch (err) {
    showMessage(errorText(err));
  }
}

function _tabFromHash() {
  const tab = window.location.hash.replace("#", "");
  return EBAY_TABS.some(([key]) => key === tab) ? tab : "overview";
}

// Reload the eBay status, redraw the sub-tabs and load the active panel.
async function refresh() {
  ebayStatus = await apiGet("/ebay/status/");
  _renderBadge(ebayStatus.environment);
  renderTabs(SUBNAV_ID, EBAY_TABS, activeTab, selectTab);  // the sub-tabs are the second navigation row
  await _showPanel();
}

function selectTab(tab) {
  activeTab = tab;
  window.location.hash = tab;
  showMessage("", false);
  refresh().catch((err) => showMessage(errorText(err)));
}

// Show the active panel, or a hint if it cannot be used yet.
async function _showPanel() {
  const lock = _lockReason(activeTab);
  document.querySelectorAll(".panel").forEach((panel) => {
    panel.style.display = !lock && panel.dataset.panel === activeTab ? "block" : "none";
  });
  const hint = document.getElementById("locked-hint");
  hint.textContent = lock;
  hint.style.display = lock ? "block" : "none";
  if (!lock) await TAB_LOADERS[activeTab](ebayStatus);
}

function _lockReason(tab) {
  if (NEEDS_CONNECTION.includes(tab) && !ebayStatus.connected) {
    return "Bitte zuerst im Reiter „Übersicht“ mit eBay verbinden.";
  }
  if (NEEDS_SETUP.includes(tab) && !ebayStatus.ready) {
    return "Inserieren geht erst, wenn die Checkliste im Reiter „Übersicht“ vollständig ist (Verbindung, Vorlagen, Lagerort).";
  }
  return "";
}

function _renderBadge(environment) {
  const badge = document.getElementById("env-badge");
  badge.textContent = environment === "production" ? "Production (echt)" : "Sandbox (Test)";
  badge.className = `env-badge env-${environment}`;
}

// --- Overview ---

async function loadOverview(status) {
  _renderChecklist(status);
  _renderConnection(status);
  const sales = await apiGet("/orders/?source=ebay").catch(() => []);
  _renderFigures(status, sales);
}

function _renderFigures(status, sales) {
  const waiting = sales.filter((order) => WAITING_STATES.includes(order.fulfillment_status));
  const unpaid = waiting.filter((order) => order.payment_status === "pending").length;
  const counts = status.listings;
  const figures = [
    ["Inserate online", counts.online + counts.changed], ["Geändert, nicht übertragen", counts.changed],
    ["Mit Fehler", counts.error], ["Beendet", counts.ended],
    ["Verkäufe zu verschicken", waiting.length], ["davon Zahlung offen", unpaid],
  ];
  document.getElementById("ebay-figures").innerHTML = figures.map(([label, value]) =>
    `<div class="tile"><span class="tile-label">${label}</span><span class="tile-value">${value}</span></div>`
  ).join("");
}

function _renderChecklist(status) {
  const missing = status.missing_settings;
  const steps = [
    [!missing.length, missing.length ? `Zugangsdaten in der .env – fehlt: ${missing.join(", ")}` : "Zugangsdaten in der .env"],
    [status.connected, "Mit eBay verbunden"],
    [status.policies_ready, "Versandprofil, Rückgabe und Zahlung eingerichtet (Reiter „Vorlagen“)"],
    [Boolean(status.location) && !status.location.needs_resync, "Lagerort an eBay übertragen (Reiter „Vorlagen“)"],
    [status.ready, "Bereit zum Inserieren"],
  ];
  document.getElementById("checklist").innerHTML = steps.map(([done, label]) =>
    `<li class="${done ? "done" : ""}"><span class="check-icon">${done ? "✓" : "–"}</span>${escapeHtml(label)}</li>`
  ).join("");
}

function _renderConnection(status) {
  const until = status.refresh_expires_at ? new Date(status.refresh_expires_at).toLocaleDateString("de-DE") : "";
  document.getElementById("connect-status").textContent = status.connected
    ? `Verbunden – die Verbindung gilt bis ${until}.`
    : "Noch nicht verbunden.";
  document.getElementById("connect-btn").textContent = status.connected ? "Neu verbinden" : "Mit eBay verbinden";
  document.getElementById("disconnect-btn").style.display = status.connected ? "inline-block" : "none";
}

async function _startConnect() {
  const tab = window.open("", "_blank");  // open synchronously so the browser does not block it
  try {
    const data = await apiSend("/ebay/connect/start/", "POST", {});
    if (tab) tab.location = data.consent_url;
    document.getElementById("consent-link").href = data.consent_url;
    document.getElementById("finish-box").style.display = "block";
    showMessage("", false);
  } catch (err) {
    if (tab) tab.close();
    showMessage(errorText(err));
  }
}

async function _finishConnect() {
  try {
    await apiSend("/ebay/connect/finish/", "POST", { redirect_url: inputValue("redirect-url") });
    document.getElementById("finish-box").style.display = "none";
    document.getElementById("redirect-url").value = "";
    showMessage("Mit eBay verbunden.", false);
    await refresh();
  } catch (err) {
    showMessage(errorText(err));
  }
}

async function _disconnect() {
  if (!confirm("Verbindung zu eBay wirklich trennen?")) return;
  try {
    await apiSend("/ebay/disconnect/", "POST", {});
    await refresh();
  } catch (err) {
    showMessage(errorText(err));
  }
}

// --- Report (eBay sales only) ---

async function loadEbayReport() {
  const { from, to } = periodRange(reportPeriod);
  await renderSalesReport("ebay-report", { from, to, channel: "ebay" });
}

function _selectReportPeriod(period) {
  reportPeriod = period;
  markActive("report-period", "period", period);
  loadEbayReport().catch((err) => showMessage(errorText(err)));
}
