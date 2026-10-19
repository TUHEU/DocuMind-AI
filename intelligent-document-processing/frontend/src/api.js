// One place for all calls to the backend. Screens never call fetch directly.
const BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

async function get(path) {
  const res = await fetch(BASE + path);
  let body = null;
  try {
    body = await res.json();
  } catch {
    /* response had no JSON */
  }
  return { ok: res.ok, status: res.status, body };
}

export const getHealth = () => get("/api/v1/health");
export const getDbHealth = () => get("/api/v1/health/db");
