"use strict";

// Shared dialog "Versand an eBay melden", used on the orders page and in the eBay tab.
// It builds its own markup, so a page only has to load this script.

let shipDialog = null;       // the modal element, created on first use
let shipDialogOrder = null;  // order the dialog is open for
let shipDialogDone = null;   // callback after a successful report
let shipCarriersLoaded = false;

// Open the dialog for an order; onDone(order) runs after eBay accepted the shipment.
async function openShipDialog(order, onDone) {
  shipDialog = shipDialog || _buildShipDialog();
  shipDialogOrder = order;
  shipDialogDone = onDone;
  _shipDialogMessage("");
  shipDialog.querySelector("#ship-tracking").value = order.tracking_number || "";
  shipDialog.style.display = "flex";
  if (!shipCarriersLoaded) await _loadShipCarriers();
}

function _buildShipDialog() {
  const modal = document.createElement("div");
  modal.className = "modal";
  modal.innerHTML = `
    <form class="modal-card">
      <h3>Versand an eBay melden</h3>
      <p class="hint">eBay markiert die Bestellung als verschickt und zeigt dem Käufer die Sendungsverfolgung.</p>
      <div id="ship-message" class="message error" style="display:none"></div>
      <label>Versanddienstleister<select id="ship-carrier" required></select></label>
      <label>Trackingnummer (nur Buchstaben und Ziffern)
        <input type="text" id="ship-tracking" required />
      </label>
      <div class="form-actions">
        <button type="submit" id="ship-submit">Versand melden</button>
        <button type="button" id="ship-abort" class="secondary">Abbrechen</button>
      </div>
    </form>`;
  modal.querySelector("form").addEventListener("submit", _submitShipDialog);
  modal.querySelector("#ship-abort").addEventListener("click", _closeShipDialog);
  document.body.appendChild(modal);
  return modal;
}

async function _loadShipCarriers() {
  try {
    const carriers = await apiGet("/ebay/carriers/");
    shipDialog.querySelector("#ship-carrier").innerHTML = carriers.map((carrier) =>
      `<option value="${escapeHtml(carrier.code)}">${escapeHtml(carrier.name)}</option>`
    ).join("");
    shipCarriersLoaded = true;
  } catch (err) {
    _shipDialogMessage(errorText(err));
  }
}

function _closeShipDialog() {
  shipDialogOrder = null;
  shipDialog.style.display = "none";
}

function _shipDialogMessage(text) {
  const box = shipDialog.querySelector("#ship-message");
  box.textContent = text;
  box.style.display = text ? "block" : "none";
}

async function _submitShipDialog(e) {
  e.preventDefault();
  const payload = {
    carrier: shipDialog.querySelector("#ship-carrier").value,
    tracking_number: shipDialog.querySelector("#ship-tracking").value.trim(),
  };
  const button = shipDialog.querySelector("#ship-submit");
  button.disabled = true;
  try {
    const order = await apiSend(`/ebay/orders/${shipDialogOrder.id}/ship/`, "POST", payload);
    const done = shipDialogDone;
    _closeShipDialog();
    if (done) done(order);
  } catch (err) {
    _shipDialogMessage(errorText(err));
  }
  button.disabled = false;
}
