"use strict";

// localStorage keys for the JWT pair.
const ACCESS_KEY = "ebay_access";
const REFRESH_KEY = "ebay_refresh";

function getAccess() {
  return localStorage.getItem(ACCESS_KEY);
}

function getRefresh() {
  return localStorage.getItem(REFRESH_KEY);
}

function storeTokens(access, refresh) {
  if (access) localStorage.setItem(ACCESS_KEY, access);
  if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
}

function clearTokens() {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

// Redirect to the login page when no token is present (page guard).
function requireAuth() {
  if (!getAccess()) window.location.href = "index.html";
}

// Send credentials, store the returned token pair, return the response body.
async function login(email, password) {
  const data = await _postPublic("/login/", { email, password });
  storeTokens(data.access, data.refresh);
  return data;
}

// Register a new user and store the returned token pair.
async function register(email, fullname, password, repeatedPassword) {
  const data = await _postPublic("/registration/", {
    email, fullname, password, repeated_password: repeatedPassword,
  });
  storeTokens(data.access, data.refresh);
  return data;
}

// Blacklist the refresh token server-side and clear the local session.
async function logout() {
  const refresh = getRefresh();
  if (refresh) {
    await apiFetch("/logout/", { method: "POST", body: JSON.stringify({ refresh }) }).catch(() => {});
  }
  clearTokens();
  window.location.href = "index.html";
}

// Try to renew the access token via the refresh token; return true on success.
async function refreshAccess() {
  const refresh = getRefresh();
  if (!refresh) return false;
  const response = await fetch(`${API_BASE_URL}/token/refresh/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh }),
  });
  if (!response.ok) return false;
  const data = await response.json();
  storeTokens(data.access, data.refresh);
  return true;
}

// POST to a public endpoint and return parsed JSON, throwing ApiError on failure.
async function _postPublic(path, body) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await response.json().catch(() => null);
  if (!response.ok) throw new ApiError(response.status, data);
  return data;
}
