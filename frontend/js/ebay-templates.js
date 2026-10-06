"use strict";

// eBay tab, panel "Vorlagen": shipping profiles, return/payment policy and the inventory location.
// loadTemplates() is called by ebay.js.

let templateProfiles = [];
let templateServices = null;  // eBay's shipping services, loaded once

document.getElementById("new-profile-btn").addEventListener("click", () => _openProfileForm());
document.getElementById("cancel-profile").addEventListener("click", _closeProfileForm);
document.getElementById("profile-form").addEventListener("submit", _saveProfile);
document.getElementById("policies-form").addEventListener("submit", _savePolicies);
document.getElementById("location-btn").addEventListener("click", _syncLocation);

async function loadTemplates(status) {
  if (!templateServices) await _loadShippingServices();
  await Promise.all([_loadProfiles(), _loadPolicies(), _renderLocation(status.location)]);
}

// --- Shipping profiles ---

async function _loadShippingServices() {
  templateServices = await apiGet("/ebay/shipping-services/");
  const select = document.getElementById("profile-service");
  select.innerHTML = "";
  templateServices.forEach((service) => select.appendChild(new Option(service.name, service.code)));
}

async function _loadProfiles() {
  templateProfiles = await apiGet("/ebay/shipping-profiles/");
  const rows = templateProfiles.map(_profileRow).join("");
  document.getElementById("profile-rows").innerHTML =
    rows || `<tr><td colspan="6" class="empty">Noch kein Versandprofil – lege das erste an.</td></tr>`;
  _bindProfileActions();
}

function _profileRow(profile) {
  const standard = profile.is_default ? ' <span class="chip">Standard</span>' : "";
  const cost = Number(profile.shipping_cost) === 0 ? "kostenlos" : formatEuro(profile.shipping_cost);
  const days = `${profile.handling_days} Werktag${profile.handling_days === 1 ? "" : "e"}`;
  return `
    <tr>
      <td><strong>${escapeHtml(profile.name)}</strong>${standard}</td>
      <td>${escapeHtml(_serviceName(profile.shipping_service))}</td>
      <td>${cost}</td>
      <td>${days}</td>
      <td>${profile.listing_count}</td>
      <td class="actions">${_profileActions(profile)}</td>
    </tr>`;
}

function _serviceName(code) {
  const service = (templateServices || []).find((entry) => entry.code === code);
  return service ? service.name : code || "–";
}

function _profileActions(profile) {
  const button = (action, label, extra = "") =>
    `<button type="button" class="link-btn ${extra}" data-profile-${action}="${profile.id}">${label}</button>`;
  const edit = button("edit", "Bearbeiten");
  if (profile.is_default) return edit;
  return edit + button("default", "Als Standard") + button("delete", "Löschen", "danger");
}

function _bindProfileActions() {
  const bind = (action, handler) => document.querySelectorAll(`[data-profile-${action}]`).forEach((btn) =>
    btn.addEventListener("click", () => handler(Number(btn.getAttribute(`data-profile-${action}`))))
  );
  bind("edit", (id) => _openProfileForm(templateProfiles.find((profile) => profile.id === id)));
  bind("default", _makeDefault);
  bind("delete", _deleteProfile);
}

function _profileMessage(text, isError = true) {
  const box = document.getElementById("profile-message");
  box.textContent = text;
  box.className = isError ? "message error" : "message success";
  box.style.display = text ? "block" : "none";
}

function _openProfileForm(profile) {
  const set = (id, value) => { document.getElementById(id).value = value ?? ""; };
  set("profile-id", profile ? profile.id : "");
  set("profile-name", profile ? profile.name : "");
  set("profile-cost", profile ? profile.shipping_cost : "");
  set("profile-handling", profile ? profile.handling_days : 1);
  if (profile && profile.shipping_service) set("profile-service", profile.shipping_service);
  document.getElementById("profile-form").style.display = "grid";
  _profileMessage("");
}

function _closeProfileForm() {
  document.getElementById("profile-form").reset();
  document.getElementById("profile-form").style.display = "none";
}

async function _saveProfile(e) {
  e.preventDefault();
  const id = inputValue("profile-id");
  const payload = {
    name: inputValue("profile-name"),
    shipping_service: inputValue("profile-service"),
    shipping_cost: inputValue("profile-cost"),
    handling_days: Number(inputValue("profile-handling")),
  };
  await _profileRequest(
    () => (id ? apiSend(`/ebay/shipping-profiles/${id}/`, "PUT", payload) : apiSend("/ebay/shipping-profiles/", "POST", payload)),
    "Versandprofil bei eBay gespeichert.",
  );
}

function _makeDefault(id) {
  return _profileRequest(() => apiSend(`/ebay/shipping-profiles/${id}/default/`, "POST", {}), "Standard-Profil geändert.");
}

function _deleteProfile(id) {
  if (!confirm("Versandprofil wirklich löschen? Die Vorlage wird auch bei eBay gelöscht.")) return;
  return _profileRequest(() => apiDelete(`/ebay/shipping-profiles/${id}/`), "Versandprofil gelöscht.");
}

// Run a profile request, then reload the panel and show the outcome.
async function _profileRequest(send, successText) {
  let failure = "";
  try {
    await send();
    _closeProfileForm();
  } catch (err) {
    failure = errorText(err);
  }
  await refresh().catch(() => {});
  _profileMessage(failure || successText, Boolean(failure));
}

// --- Return and payment policy ---

async function _loadPolicies() {
  const values = await apiGet("/ebay/policies/");
  document.getElementById("p-return-days").value = values.return_days;
  document.getElementById("p-return-payer").value = values.return_cost_payer;
  document.getElementById("policy-state").textContent = values.saved
    ? "Rückgabe- und Zahlungsvorlage sind bei eBay gespeichert."
    : "Noch nicht bei eBay gespeichert – einmal „Bei eBay speichern“ klicken.";
}

async function _savePolicies(e) {
  e.preventDefault();
  const payload = {
    return_days: Number(inputValue("p-return-days")),
    return_cost_payer: inputValue("p-return-payer"),
  };
  try {
    await apiSend("/ebay/policies/", "PUT", payload);
    showMessage("Rückgabe und Zahlung bei eBay gespeichert.", false);
    await refresh();
  } catch (err) {
    showMessage(errorText(err));
  }
}

// --- Inventory location ---

async function _renderLocation(location) {
  const warehouse = (await apiGet("/warehouses/")).find((w) => w.is_default);
  const info = document.getElementById("location-info");
  document.getElementById("location-btn").disabled = !warehouse;
  if (!warehouse) {
    info.innerHTML = 'Noch kein Lagerort angelegt. <a href="warehouse.html">Im Bereich „Lager“ anlegen</a>.';
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
