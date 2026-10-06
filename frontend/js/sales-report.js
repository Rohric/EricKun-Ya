"use strict";

// Shared sales report table (purchase price, sale price, estimated fee, profit per sold position).
// Used by the finance page and by the eBay tab.

// Load the report for filters {from, to, category, channel} and render it into a container.
async function renderSalesReport(containerId, filters) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([name, value]) => { if (value) params.set(name, value); });
  const data = await apiGet(`/finance/reports/sales/?${params}`);
  const rows = data.rows.map(_reportRow).join("");
  document.getElementById(containerId).innerHTML = `
    <table class="data-table report-table">
      <thead>${_reportHead(data.fee_rate)}</thead>
      <tbody>${rows || `<tr><td colspan="12" class="empty">Keine Verkäufe in diesem Zeitraum.</td></tr>`}</tbody>
      ${data.rows.length ? `<tfoot>${_reportTotals(data.totals)}</tfoot>` : ""}
    </table>`;
  return data;
}

function _reportHead(feeRate) {
  const fee = `Gebühr (geschätzt, ${formatPercent(feeRate)})`;
  const columns = ["Datum", "Nr.", "Artikel", "Kategorie", "Kanal"];
  const numbers = ["Menge", "EK", "VK", "Umsatz", fee, "Gewinn", "Marge"];
  return `<tr>${columns.map((c) => `<th>${c}</th>`).join("")}${numbers.map((c) => `<th class="num">${c}</th>`).join("")}</tr>`;
}

function _reportRow(row) {
  const purchase = row.purchase_price == null ? "–" : formatEuro(row.purchase_price);
  return `
    <tr>
      <td>${new Date(row.date).toLocaleDateString("de-DE")}</td>
      <td>${row.order}</td>
      <td>${escapeHtml(row.title)}${row.sku ? `<br><span class="hint">${escapeHtml(row.sku)}</span>` : ""}</td>
      <td>${escapeHtml(row.category) || "–"}</td>
      <td>${escapeHtml(row.channel_label)}</td>
      <td class="num">${row.quantity}</td>
      <td class="num">${purchase}</td>
      <td class="num">${formatEuro(row.sold_price)}</td>
      <td class="num">${formatEuro(row.revenue)}</td>
      <td class="num">${formatEuro(row.fee)}</td>
      <td class="num">${formatEuro(row.profit)}</td>
      <td class="num">${formatPercent(row.margin)}</td>
    </tr>`;
}

function _reportTotals(totals) {
  return `
    <tr>
      <td colspan="5">Summe (${totals.positions} Positionen)</td>
      <td class="num">${totals.quantity}</td>
      <td class="num"></td><td class="num"></td>
      <td class="num">${formatEuro(totals.revenue)}</td>
      <td class="num">${formatEuro(totals.fee)}</td>
      <td class="num">${formatEuro(totals.profit)}</td>
      <td class="num">${formatPercent(totals.margin)}</td>
    </tr>`;
}
