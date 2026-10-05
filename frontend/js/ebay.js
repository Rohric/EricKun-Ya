"use strict";

requireAuth();
renderNav("ebay.html");

let servicesLoaded = false;

document.getElementById("connect-btn").addEventListener("click", _startConnect);
document.getElementById("finish-btn").addEventListener("click", _finishConnect);
document.getElementById("disconnect-btn").addEventListener("click", _disconnect);
document.getElementById("policies-form").addEventListener("submit", _savePolicies);
document.getElementById("location-btn").addEventListener("click", _syncLocation);

init();

async function init() {
  try {
    await refresh();
  } catch (err) {
    showMessage(errorText(err));
  }
}

// Reload the eBay status and render every section.
async function refresh() {
  const status = await apiGet("/ebay/status/");
  _renderBadge(status.environment);
  _renderChecklist(status);
  _renderConnection(status);
  _toggleSetup(status.connected);
  if (status.connected) await _loadSetup(status);
  await loadListings(status);  // see ebay-listings.js
}

function _renderBadge(environment) {
  const badge = document.getElementById("env-badge");
  badge.textContent = environment === "production" ? "Production (echt)" : "Sandbox (Test)";
  badge.className = `env-badge env-${environment}`;
}

function _renderChecklist(status) {
  const missing = status.missing_settings;
  const steps = [
    [!missing.length, missing.length ? `Zugangsdaten in der .env – fehlt: ${missing.join(", ")}` : "Zugangsdaten in der .env"],
    [status.connected, "Mit eBay verbunden"],
    [status.policies_ready, "Versand, Rückgabe und Zahlung eingerichtet"],
    [Boolean(status.location) && !status.location.needs_resync, "Lagerort an eBay übertragen"],
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

function _toggleSetup(connected) {
  ["policies-card", "location-card"].forEach((id) =>
    document.getElementById(id).classList.toggle("disabled", !connected)
  );
}

// --- Connection ---

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
    servicesLoaded = false;
    await refresh();
  } catch (err) {
    showMessage(errorText(err));
  }
}

// --- Setup: policies + location ---

async function _loadSetup(status) {
  if (!servicesLoaded) await _loadShippingServices();
  _fillPolicies(await apiGet("/ebay/policies/"));
  await _renderLocation(status.location);
}

async function _loadShippingServices() {
  const services = await apiGet("/ebay/shipping-services/");
  document.getElementById("p-service").innerHTML = services.map((s) =>
    `<option value="${escapeHtml(s.code)}">${escapeHtml(s.name)}</option>`
  ).join("");
  servicesLoaded = true;
}

function _fillPolicies(values) {
  const set = (id, value) => {
    if (value !== "" && value != null) document.getElementById(id).value = value;
  };
  set("p-service", values.shipping_service);
  set("p-cost", values.shipping_cost);
  set("p-handling", values.handling_days);
  set("p-return-days", values.return_days);
  set("p-return-payer", values.return_cost_payer);
}

async function _savePolicies(e) {
  e.preventDefault();
  const payload = {
    shipping_service: inputValue("p-service"),
    shipping_cost: inputValue("p-cost"),
    handling_days: Number(inputValue("p-handling")),
    return_days: Number(inputValue("p-return-days")),
    return_cost_payer: inputValue("p-return-payer"),
  };
  try {
    await apiSend("/ebay/policies/", "PUT", payload);
    showMessage("Versand, Rückgabe und Zahlung bei eBay gespeichert.", false);
    await refresh();
  } catch (err) {
    showMessage(errorText(err));
  }
}

async function _renderLocation(location) {
  const warehouse = (await apiGet("/warehouses/")).find((w) => w.is_default);
  const info = document.getElementById("location-info");
  document.getElementById("location-btn").disabled = !warehouse;
  if (!warehouse) {
    info.innerHTML = 'Noch kein Lagerort angelegt. <a href="warehouse.html">Im Reiter „Lager“ anlegen</a>.';
    return;
  }
  const address = `${warehouse.street}, ${warehouse.zip_code} ${warehouse.city}`;
  info.textContent = `${warehouse.name} – ${address} – ${_locationState(location)}`;
}

function _locationState(location) {
  if (!location) return "noch nicht an eBay übertragen.";
  if (location.needs_resync) return "Adresse geändert, bitte erneut übertragen.";
  return `übertragen am ${new Date(location.last_synced).toLocaleDateString("de-DE")}.`;
}

async function _syncLocation() {
  try {
    await apiSend("/ebay/location/sync/", "POST", {});
    showMessage("Lagerort an eBay übertragen.", false);
    await refresh();
  } catch (err) {
    showMessage(errorText(err));
  }
}
