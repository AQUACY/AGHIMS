function pad2(n) {
  return String(n).padStart(2, "0");
}

function toSqlDatetime(d) {
  const date = d instanceof Date ? d : new Date(d);
  return `${date.getUTCFullYear()}-${pad2(date.getUTCMonth() + 1)}-${pad2(date.getUTCDate())} ${pad2(date.getUTCHours())}:${pad2(date.getUTCMinutes())}:${pad2(date.getUTCSeconds())}`;
}

function parseDatetime(value) {
  if (!value) return null;
  if (value instanceof Date) {
    return Number.isNaN(value.getTime()) ? null : value;
  }
  const s = String(value).trim();
  if (!s) return null;
  if (/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}/.test(s)) {
    return new Date(s.replace(" ", "T") + "Z");
  }
  const parsed = new Date(s.endsWith("Z") || s.includes("+") ? s : `${s}Z`);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function toIsoZ(value) {
  const date = parseDatetime(value) || new Date(value);
  return date.toISOString().replace(/\.\d{3}Z$/, "Z");
}

function addMonthsUtc(date, months) {
  const d = new Date(date.getTime());
  const day = d.getUTCDate();
  d.setUTCMonth(d.getUTCMonth() + months);
  if (d.getUTCDate() !== day) {
    d.setUTCDate(0);
  }
  return d;
}

/** datetime-local or ISO, treated as Ghana / GMT. */
function parseAdminDatetime(value) {
  if (!value) return null;
  if (value instanceof Date) return Number.isNaN(value.getTime()) ? null : value;
  const s = String(value).trim();
  if (!s) return null;
  if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(s)) {
    return new Date(`${s}:59+00:00`);
  }
  if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$/.test(s)) {
    return new Date(`${s}+00:00`);
  }
  return parseDatetime(s);
}

function toDatetimeLocalValue(value) {
  const d = parseDatetime(value) || parseAdminDatetime(value);
  if (!d) return "";
  return `${d.getUTCFullYear()}-${pad2(d.getUTCMonth() + 1)}-${pad2(d.getUTCDate())}T${pad2(d.getUTCHours())}:${pad2(d.getUTCMinutes())}`;
}

/** Ghana (Africa/Accra) is GMT year-round — calendar months are UTC dates. */
function startOfMonthUtc(year, monthIndex) {
  return new Date(Date.UTC(year, monthIndex, 1, 0, 0, 0));
}

function endOfMonthUtc(year, monthIndex) {
  return new Date(Date.UTC(year, monthIndex + 1, 0, 23, 59, 59));
}

function startOfNextCalendarMonth(now) {
  const d = now instanceof Date ? now : new Date(now);
  return startOfMonthUtc(d.getUTCFullYear(), d.getUTCMonth() + 1);
}

function startOfMonthAfter(date) {
  const d = date instanceof Date ? date : parseDatetime(date);
  return startOfMonthUtc(d.getUTCFullYear(), d.getUTCMonth() + 1);
}

function formatAccraStamp(date) {
  const d = date instanceof Date ? date : parseDatetime(date);
  if (!d) return "";
  return new Intl.DateTimeFormat("en-GB", {
    timeZone: "Africa/Accra",
    day: "numeric",
    month: "long",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  }).format(d);
}

function formatPeriodLabel(from, until) {
  const a = formatAccraStamp(from);
  const b = formatAccraStamp(until);
  if (!a || !b) return "";
  return `${a} – ${b}`;
}

function periodMonthTitle(from) {
  const d = from instanceof Date ? from : parseDatetime(from);
  if (!d) return "";
  return new Intl.DateTimeFormat("en-GB", {
    timeZone: "Africa/Accra",
    month: "long",
    year: "numeric",
  }).format(d);
}

function utcNow() {
  return new Date();
}

function formatGhs(pesewas) {
  const n = Number(pesewas) / 100;
  const [whole, frac] = n.toFixed(2).split(".");
  const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  return `GH₵ ${grouped}.${frac}`;
}

function ghsToPesewas(amountGhs) {
  const n = Number(amountGhs);
  if (!Number.isFinite(n) || n <= 0) {
    throw new Error("Amount must be a positive number in GH₵");
  }
  return Math.round(n * 100);
}

function pesewasToGhsNumber(pesewas) {
  return Number(pesewas) / 100;
}

function randomUuid() {
  return require("crypto").randomUUID();
}

module.exports = {
  toSqlDatetime,
  parseDatetime,
  toIsoZ,
  addMonthsUtc,
  utcNow,
  formatGhs,
  ghsToPesewas,
  pesewasToGhsNumber,
  randomUuid,
  startOfMonthUtc,
  endOfMonthUtc,
  startOfNextCalendarMonth,
  startOfMonthAfter,
  formatAccraStamp,
  formatPeriodLabel,
  periodMonthTitle,
  parseAdminDatetime,
  toDatetimeLocalValue,
};
