"use strict";

requireAuth();
renderNav("warehouse.html");

let warehouseId = null;

document.getElementById("warehouse-form").addEventListener("submit", _saveWarehouse);

init();

// Load the default warehouse into the form.
async function init() {
  try {
    const warehouses = await apiGet("/warehouses/");
    _fill(warehouses.find((w) => w.is_default) || warehouses[0]);
  } catch (err) {
    showMessage(errorText(err));
  }
}

function _fill(warehouse) {
  if (!warehouse) return;
  warehouseId = warehouse.id;
  const set = (id, value) => { document.getElementById(id).value = value ?? ""; };
  set("w-name", warehouse.name);
  set("w-street", warehouse.street);
  set("w-zip", warehouse.zip_code);
  set("w-city", warehouse.city);
  set("w-country", warehouse.country);
}

async function _saveWarehouse(e) {
  e.preventDefault();
  try {
    const saved = warehouseId
      ? await apiSend(`/warehouses/${warehouseId}/`, "PATCH", _payload())
      : await apiSend("/warehouses/", "POST", _payload());
    _fill(saved);
    showMessage("Lagerort gespeichert. Adresse geändert? Im eBay-Reiter erneut übertragen.", false);
  } catch (err) {
    showMessage(errorText(err));
  }
}

function _payload() {
  return {
    name: inputValue("w-name"),
    street: inputValue("w-street"),
    zip_code: inputValue("w-zip"),
    city: inputValue("w-city"),
    country: inputValue("w-country"),
    is_default: true,
  };
}
