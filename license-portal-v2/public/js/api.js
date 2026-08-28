async function api(path, opts = {}) {
  const options = { credentials: "include", ...opts };
  const headers = { ...(opts.headers || {}) };
  if (opts.body && typeof opts.body !== "string" && !(opts.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(opts.body);
  }
  options.headers = headers;
  const res = await fetch(path, options);
  const text = await res.text();
  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch (_) { data = { raw: text }; }
  if (!res.ok) {
    const err = new Error((data && (data.error || data.detail)) || text || res.statusText);
    err.status = res.status;
    err.data = data;
    throw err;
  }
  return data;
}

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

function fmtPeriod(from, until) {
  if (!from || !until) return "—";
  const opts = { timeZone: "Africa/Accra", day: "numeric", month: "long", year: "numeric", hour: "numeric", minute: "2-digit", hour12: true };
  const a = new Date(String(from).includes("T") || String(from).endsWith("Z") ? from : String(from).replace(" ", "T") + "Z");
  const b = new Date(String(until).includes("T") || String(until).endsWith("Z") ? until : String(until).replace(" ", "T") + "Z");
  if (Number.isNaN(a.getTime()) || Number.isNaN(b.getTime())) return "—";
  return `${a.toLocaleString("en-GB", opts)} – ${b.toLocaleString("en-GB", opts)}`;
}

function fmtDt(value) {
  if (!value) return "—";
  const d = new Date(String(value).includes("T") || String(value).endsWith("Z") ? value : String(value).replace(" ", "T") + "Z");
  if (Number.isNaN(d.getTime())) return String(value);
  return d.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

function statusPill(status) {
  const s = String(status || "").toLowerCase();
  const cls = s === "success" || s === "active" ? "ok" : s === "pending" || s === "abandoned" ? "warn" : s === "failed" ? "bad" : "idle";
  return `<span class="pill ${cls}">${escapeHtml(s || "unknown")}</span>`;
}

function paymentRetryable(p) {
  if (!p) return false;
  if (p.can_retry === true) return true;
  if (String(p.channel || "").toLowerCase() === "manual") return false;
  const s = String(p.status || "").toLowerCase();
  return s === "pending" || s === "failed" || s === "abandoned";
}

async function requireSession() {
  try {
    return await api("/api/me");
  } catch (err) {
    window.location.href = "/";
    throw err;
  }
}

async function logout() {
  await api("/api/auth/logout", { method: "POST" });
  window.location.href = "/";
}

function applyBranding(config) {
  const name = (config && config.company_name) || "";
  const logoUrl = config && config.logo_url;
  document.querySelectorAll("[data-brand-name]").forEach((el) => {
    if (name) el.textContent = name;
  });
  document.querySelectorAll("[data-brand-mark]").forEach((el) => {
    if (!logoUrl) return;
    if (el.tagName === "IMG") {
      el.src = logoUrl;
      el.alt = name || "Logo";
      return;
    }
    const img = document.createElement("img");
    img.src = logoUrl;
    img.alt = name || "Logo";
    img.className = "brand-logo";
    img.setAttribute("data-brand-mark", "");
    el.replaceWith(img);
  });
}

async function loadBranding() {
  try {
    const c = await api("/api/public-config");
    applyBranding(c);
    return c;
  } catch (_) {
    return null;
  }
}

loadBranding();
