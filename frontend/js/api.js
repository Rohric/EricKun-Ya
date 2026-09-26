"use strict";

// Error carrying the HTTP status and parsed body of a failed request.
class ApiError extends Error {
  constructor(status, data) {
    super(`API error ${status}`);
    this.status = status;
    this.data = data;
  }
}

// Fetch with the Bearer header; on 401 refresh the token once and retry.
async function apiFetch(path, options = {}) {
  const response = await _fetchWithAuth(path, options);
  if (response.status !== 401) return response;

  const refreshed = await refreshAccess();
  if (!refreshed) {
    clearTokens();
    window.location.href = "index.html";
    throw new ApiError(401, { detail: "Sitzung abgelaufen." });
  }
  return _fetchWithAuth(path, options);
}

function _fetchWithAuth(path, options) {
  const headers = Object.assign({ "Content-Type": "application/json" }, options.headers || {});
  const access = getAccess();
  if (access) headers["Authorization"] = `Bearer ${access}`;
  return fetch(`${API_BASE_URL}${path}`, Object.assign({}, options, { headers }));
}

// GET JSON from an authenticated endpoint.
async function apiGet(path) {
  return _parse(await apiFetch(path));
}

// Send a JSON body with the given method and return the parsed response.
async function apiSend(path, method, body) {
  return _parse(await apiFetch(path, { method, body: JSON.stringify(body) }));
}

// DELETE a resource; return true on success.
async function apiDelete(path) {
  const response = await apiFetch(path, { method: "DELETE" });
  if (!response.ok) throw new ApiError(response.status, await _safeJson(response));
  return true;
}

async function _parse(response) {
  const data = await _safeJson(response);
  if (!response.ok) throw new ApiError(response.status, data);
  return data;
}

async function _safeJson(response) {
  return response.json().catch(() => null);
}
