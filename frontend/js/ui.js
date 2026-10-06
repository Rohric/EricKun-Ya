"use strict";

// Display names of the listing states the backend reports (used on several pages).
const LISTING_STATE_LABELS = {
  none: "Nicht inseriert", draft: "Entwurf", online: "Online",
  changed: "Geändert", ended: "Beendet", error: "Fehler",
};
const PAYMENT_LABELS = { paid: "Bezahlt", pending: "Zahlung offen" };
const FULFILLMENT_LABELS = {
  open: "Offen", packed: "Verpackt", shipped: "Verschickt",
  delivered: "Zugestellt", in_return: "In Reklamation", cancelled: "Storniert",
};

// Main areas shown in the header; every other page is reached through the dashboard.
const NAV_LINKS = [
  ["dashboard.html", "Dashboard"],
  ["products.html", "Artikel"],
  ["ebay.html", "eBay"],
];

// Render the shared top navigation into the element with id "nav".
function renderNav(active) {
  const nav = document.getElementById("nav");
  if (!nav) return;
  const items = NAV_LINKS.map(([href, label]) =>
    `<a href="${href}" class="${href === active ? "active" : ""}">${label}</a>`
  ).join("");
  nav.innerHTML = `<div class="nav-inner">
      <span class="brand">EricKun-Ya</span>
      <div class="nav-links">${items}</div>
      <button id="logout-btn" class="link-btn">Logout</button>
    </div>`;
  document.getElementById("logout-btn").addEventListener("click", logout);
  if (!NAV_LINKS.some(([href]) => href === active)) renderBackLink();
}

// Put a link back to the dashboard above the content of pages that are not in the header.
function renderBackLink() {
  const page = document.querySelector("main.page");
  if (!page || page.querySelector(".back-link")) return;
  const link = document.createElement("a");
  link.className = "back-link";
  link.href = "dashboard.html";
  link.textContent = "← Dashboard";
  page.prepend(link);
}

// Render sub-tabs from [key, label] pairs into a container and call onSelect(key) on click.
function renderTabs(containerId, tabs, activeKey, onSelect) {
  const box = document.getElementById(containerId);
  box.className = "tabs";
  box.innerHTML = tabs.map(([key, label]) =>
    `<button type="button" class="${key === activeKey ? "active" : ""}" data-tab="${key}">${label}</button>`
  ).join("");
  box.querySelectorAll("[data-tab]").forEach((btn) =>
    btn.addEventListener("click", () => onSelect(btn.dataset.tab))
  );
}

// Format a numeric value as euro currency.
function formatEuro(value) {
  return Number(value || 0).toLocaleString("de-DE", { style: "currency", currency: "EUR" });
}

// Format a percentage with a comma as decimal separator; "–" if there is no value.
function formatPercent(value) {
  if (value == null || value === "") return "–";
  return `${Number(value).toLocaleString("de-DE", { maximumFractionDigits: 1 })} %`;
}

// Show a short status message in the element with id "message".
function showMessage(text, isError = true) {
  const box = document.getElementById("message");
  if (!box) return;
  box.textContent = text;
  box.className = isError ? "message error" : "message success";
  box.style.display = text ? "block" : "none";
}

// Turn an ApiError body into a readable German string.
function errorText(err) {
  const body = err && err.data ? err.data.error || err.data : null;
  if (typeof body === "string") return body;
  if (body) {
    const first = Object.values(body)[0];
    if (Array.isArray(first)) return first[0];
    if (typeof first === "string") return first;
  }
  return "Ein Fehler ist aufgetreten.";
}

// Escape user-provided text before inserting it into HTML.
function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = value == null ? "" : String(value);
  return div.innerHTML;
}

// Return the trimmed value of the form field with the given id.
function inputValue(id) {
  return document.getElementById(id).value.trim();
}

// Highlight the button of a switch whose data-<key> equals value.
function markActive(switchId, key, value) {
  document.querySelectorAll(`#${switchId} button`).forEach((btn) =>
    btn.classList.toggle("active", btn.dataset[key] === value)
  );
}

// Render [label, amount] pairs as euro tiles into a container.
function renderTiles(containerId, tiles) {
  document.getElementById(containerId).innerHTML = tiles.map(([label, value]) =>
    `<div class="tile"><span class="tile-label">${label}</span>
     <span class="tile-value">${formatEuro(value)}</span></div>`
  ).join("");
}

// Return the HTML card of a goal; withActions adds edit/toggle/delete buttons.
function renderGoalCard(goal, withActions = false) {
  const percent = Math.min(Number(goal.progress.percent), 100);
  const metric = goal.metric === "profit" ? "Gewinn" : "Umsatz";
  return `
    <div class="goal ${goal.is_active ? "" : "inactive"}">
      <div class="goal-head">
        <strong>${escapeHtml(goal.title)}${goal.is_active ? "" : " (inaktiv)"}</strong>
        <span>${formatEuro(goal.progress.current)} / ${formatEuro(goal.target_amount)} (${metric})</span>
      </div>
      <div class="progress"><div class="progress-bar" style="width:${percent}%"></div></div>
      <span class="goal-percent">${goal.progress.percent}%</span>
      ${withActions ? _goalActions(goal) : ""}
    </div>`;
}

function _goalActions(goal) {
  return `<div class="goal-actions">
      <button type="button" class="link-btn" data-goal-edit="${goal.id}">Bearbeiten</button>
      <button type="button" class="link-btn" data-goal-toggle="${goal.id}">${goal.is_active ? "Deaktivieren" : "Aktivieren"}</button>
      <button type="button" class="link-btn danger" data-goal-del="${goal.id}">Löschen</button>
    </div>`;
}

// Render a pager for a paginated DRF response and call onChange(page) on click.
function renderPager(containerId, data, page, onChange) {
  const box = document.getElementById(containerId);
  const pages = Math.max(Math.ceil(data.count / PAGE_SIZE), 1);
  box.innerHTML = `
    <button type="button" class="secondary" data-page="${page - 1}" ${data.previous ? "" : "disabled"}>← Zurück</button>
    <span>Seite ${page} von ${pages} · ${data.count} Einträge</span>
    <button type="button" class="secondary" data-page="${page + 1}" ${data.next ? "" : "disabled"}>Weiter →</button>`;
  box.querySelectorAll("[data-page]").forEach((btn) =>
    btn.addEventListener("click", () => onChange(Number(btn.dataset.page)))
  );
}

// Return a local YYYY-MM-DD string for a Date.
function isoDate(d) {
  const p = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

// Return {from, to} ISO dates for a named period preset (today/month/year/all).
function periodRange(preset) {
  const today = new Date();
  if (preset === "today") return { from: isoDate(today), to: isoDate(today) };
  if (preset === "month") {
    return { from: isoDate(new Date(today.getFullYear(), today.getMonth(), 1)), to: isoDate(today) };
  }
  if (preset === "all") return { from: "2000-01-01", to: isoDate(today) };
  return { from: `${today.getFullYear()}-01-01`, to: isoDate(today) };
}
