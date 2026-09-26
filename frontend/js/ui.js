"use strict";

// Render the shared top navigation into the element with id "nav".
function renderNav(active) {
  const nav = document.getElementById("nav");
  if (!nav) return;
  const links = [
    ["dashboard.html", "Dashboard"],
    ["products.html", "Artikel"],
    ["orders.html", "Bestellungen"],
  ];
  const items = links.map(([href, label]) => `<a href="${href}" class="${href === active ? "active" : ""}">${label}</a>`).join("");
  nav.innerHTML = `<div class="nav-inner">
      <span class="brand">EricKun-Ya</span>
      <div class="nav-links">${items}</div>
      <button id="logout-btn" class="link-btn">Logout</button>
    </div>`;
  document.getElementById("logout-btn").addEventListener("click", logout);
}

// Format a numeric value as euro currency.
function formatEuro(value) {
  return Number(value || 0).toLocaleString("de-DE", { style: "currency", currency: "EUR" });
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
