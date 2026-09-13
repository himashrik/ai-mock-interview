const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

// The refresh token is never handled in JS at all -- it lives in an httpOnly cookie set by the
// backend on /auth/login and /auth/refresh (scoped to path=/auth), so it's invisible to any
// script running on this page (mitigates XSS token theft). We only ever hold the short-lived
// access token here, in memory, and it's lost on a full page reload by design; `bootstrapAuth()`
// silently re-mints one from the cookie on load.
let accessToken = null;

export function setAccessToken(token) {
  accessToken = token ?? null;
}

async function rawRequest(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }
  if (accessToken) {
    headers["Authorization"] = `Bearer ${accessToken}`;
  }

  return fetch(`${BASE_URL}${path}`, {
    ...options,
    headers,
    credentials: "include", // send the httpOnly refresh cookie on same-site /auth/* requests
  });
}

async function tryRefresh() {
  const response = await fetch(`${BASE_URL}/auth/refresh`, {
    method: "POST",
    credentials: "include",
  });
  if (!response.ok) return false;
  const data = await response.json();
  setAccessToken(data.access_token);
  return true;
}

/** Call once on app load: attempts to mint a fresh access token from the refresh cookie,
 * if one is present. Returns true if the user is (still) authenticated. */
export async function bootstrapAuth() {
  return tryRefresh();
}

export async function apiRequest(path, options = {}) {
  let response = await rawRequest(path, options);

  if (response.status === 401 && path !== "/auth/refresh" && path !== "/auth/login") {
    const refreshed = await tryRefresh();
    if (refreshed) {
      response = await rawRequest(path, options);
    }
  }

  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      detail = body.detail || detail;
    } catch {
      /* ignore non-JSON error body */
    }
    throw new Error(detail);
  }

  if (response.status === 204) return null;
  return response.json();
}

export const api = {
  get: (path) => apiRequest(path, { method: "GET" }),
  post: (path, body) => apiRequest(path, { method: "POST", body: JSON.stringify(body) }),
  postForm: (path, formData) => apiRequest(path, { method: "POST", body: formData }),
  delete: (path) => apiRequest(path, { method: "DELETE" }),
};
