const { config, resolvedPrivateKeyPem, companyInitials } = require("./config");
const { getDb, nowSql, lockClause } = require("./db");
const { buildSignedDocument } = require("./cryptoSign");
const {
  toIsoZ,
  toSqlDatetime,
  parseDatetime,
  utcNow,
  randomUuid,
  addMonthsUtc,
  formatPeriodLabel,
  periodMonthTitle,
} = require("./dates");

/**
 * Netflix / Starlink style: next paid month starts the second after the current
 * license end (billing_deadline). Example: deadline 31 Aug 23:59:59 →
 * 1 Sep 00:00:00 through 30 Sep 23:59:59.
 */
function computePurchasedPeriod(existing, durationMonths, now, pendingRows = [], billingDeadline = null) {
  const months = Math.max(1, parseInt(durationMonths, 10) || 1);
  let cycleEnd = null;
  const consider = (value) => {
    const d = parseDatetime(value);
    if (d && (!cycleEnd || d > cycleEnd)) cycleEnd = d;
  };
  consider(billingDeadline);
  if (!cycleEnd && existing) consider(existing.valid_until);
  for (const row of pendingRows || []) {
    if (row && row.period_until) consider(row.period_until);
  }
  if (!cycleEnd) {
    const err = new Error("Set the current license end date (renewal deadline) on this hospital first.");
    err.status = 400;
    throw err;
  }

  let start;
  if (cycleEnd >= now) {
    start = new Date(cycleEnd.getTime() + 1000);
  } else {
    start = new Date(now.getTime());
    start.setUTCMilliseconds(0);
  }
  const validUntil = new Date(addMonthsUtc(start, months).getTime() - 1000);
  return { validFrom: start, validUntil };
}

function unionStoredWindow(existing, purchased, now) {
  if (!existing) return { validFrom: purchased.validFrom, validUntil: purchased.validUntil };
  const existingFrom = parseDatetime(existing.valid_from);
  const existingUntil = parseDatetime(existing.valid_until);
  if (existingUntil && existingUntil >= now) {
    const validFrom = existingFrom && existingFrom < purchased.validFrom ? existingFrom : purchased.validFrom;
    const validUntil =
      existingUntil > purchased.validUntil ? existingUntil : purchased.validUntil;
    return { validFrom, validUntil };
  }
  return { validFrom: purchased.validFrom, validUntil: purchased.validUntil };
}

function serializePeriod(period) {
  if (!period || !period.validFrom || !period.validUntil) return null;
  return {
    valid_from: toIsoZ(period.validFrom),
    valid_until: toIsoZ(period.validUntil),
    label: formatPeriodLabel(period.validFrom, period.validUntil),
    title: periodMonthTitle(period.validFrom),
  };
}

function computeWindow(existing, durationMonths, now, pendingRows = []) {
  return computePurchasedPeriod(existing, durationMonths, now, pendingRows);
}

async function getLicenseByCustomer(customerId, runner = null) {
  const db = runner || getDb();
  const { rows } = await db.query("SELECT * FROM licenses WHERE customer_id = ? LIMIT 1", [customerId]);
  return rows[0] || null;
}

async function getLicenseByPublicId(licenseId, runner = null) {
  const db = runner || getDb();
  const { rows } = await db.query("SELECT * FROM licenses WHERE license_id = ?", [String(licenseId || "").trim()]);
  return rows[0] || null;
}

async function pendingPeriodsForCustomer(customerId, runner = null) {
  const db = runner || getDb();
  const { rows } = await db.query(
    `SELECT period_from, period_until FROM payments
     WHERE customer_id = ? AND status = 'pending' AND period_until IS NOT NULL`,
    [customerId]
  );
  return rows;
}

function buildClaims(row, periodOverride = null) {
  const issuer = (config.issuerSlug || "").trim();
  if (!issuer) {
    throw new Error("ISSUER_SLUG is not configured");
  }
  const from = periodOverride && (periodOverride.validFrom || periodOverride.period_from || periodOverride.valid_from);
  const until = periodOverride && (periodOverride.validUntil || periodOverride.period_until || periodOverride.valid_until);
  const claims = {
    v: 1,
    license_id: row.license_id,
    customer_label: row.customer_label,
    facility_code: (row.facility_code || "").trim() || null,
    valid_from: toIsoZ(from || row.valid_from),
    valid_until: toIsoZ(until || row.valid_until),
    issuer_slug: issuer,
  };
  const dist = (config.distributionId || "").trim();
  if (dist) claims.distribution_id = dist;
  return claims;
}

function signedDocumentFor(row, periodOverride = null) {
  const pem = resolvedPrivateKeyPem();
  if (!pem) throw new Error("RSA private key is not configured");
  return buildSignedDocument(buildClaims(row, periodOverride), pem);
}

async function latestPaidPayment(customerId, runner = null) {
  const db = runner || getDb();
  const { rows } = await db.query(
    `SELECT * FROM payments WHERE customer_id = ? AND status = 'success' ORDER BY id DESC LIMIT 1`,
    [customerId]
  );
  return rows[0] || null;
}

function paymentCovers(payment, now) {
  if (!payment || payment.status !== "success") return false;
  const from = parseDatetime(payment.period_from);
  const until = parseDatetime(payment.period_until);
  if (!from || !until) return false;
  return from <= now && now <= until;
}

async function coveringPaidPayment(customerId, now = utcNow(), runner = null) {
  const db = runner || getDb();
  const { rows } = await db.query(
    `SELECT * FROM payments
     WHERE customer_id = ? AND status = 'success' AND period_from IS NOT NULL AND period_until IS NOT NULL
     ORDER BY id DESC`,
    [customerId]
  );
  return rows.find((row) => paymentCovers(row, now)) || null;
}

async function upcomingPaidPayment(customerId, now = utcNow(), runner = null) {
  const db = runner || getDb();
  const { rows } = await db.query(
    `SELECT * FROM payments
     WHERE customer_id = ? AND status = 'success' AND period_from IS NOT NULL
     ORDER BY period_from ASC, id ASC`,
    [customerId]
  );
  return (
    rows.find((row) => {
      const from = parseDatetime(row.period_from);
      return from && from > now;
    }) || null
  );
}

async function findLicenseForPull({ licenseId, facilityCode }, runner = null) {
  const db = runner || getDb();
  const id = String(licenseId || "").trim();
  const facility = String(facilityCode || "").trim();
  if (id) {
    const byId = await getLicenseByPublicId(id, db);
    if (byId) return byId;
  }
  if (facility) {
    const { rows } = await db.query("SELECT * FROM licenses WHERE facility_code = ?", [facility]);
    if (rows.length === 1) return rows[0];
    if (rows.length > 1) {
      const err = new Error("More than one license uses that facility code.");
      err.status = 400;
      err.reason = "ambiguous_facility";
      throw err;
    }
    const customers = await db.query("SELECT * FROM customers WHERE facility_code = ?", [facility]);
    if (customers.rows.length === 1) {
      return getLicenseByCustomer(customers.rows[0].id, db);
    }
  }
  return null;
}

async function currentSignedDocumentForHms({ licenseId, facilityCode }, now = utcNow()) {
  const license = await findLicenseForPull({ licenseId, facilityCode });
  if (!license) {
    return { ok: false, reason: "unknown_license" };
  }
  const claimedFacility = String(facilityCode || "").trim();
  const bound = String(license.facility_code || "").trim();
  if (claimedFacility && bound && claimedFacility !== bound) {
    return { ok: false, reason: "facility_mismatch" };
  }
  const covering = await coveringPaidPayment(license.customer_id, now);
  if (covering) {
    return {
      ok: true,
      reason: "current",
      document: signedDocumentFor(license, {
        period_from: covering.period_from,
        period_until: covering.period_until,
      }),
      period: {
        valid_from: toIsoZ(covering.period_from),
        valid_until: toIsoZ(covering.period_until),
        label: formatPeriodLabel(covering.period_from, covering.period_until),
        title: periodMonthTitle(covering.period_from),
      },
      license_id: license.license_id,
    };
  }
  const upcoming = await upcomingPaidPayment(license.customer_id, now);
  if (upcoming) {
    return {
      ok: false,
      reason: "not_yet",
      valid_from: toIsoZ(upcoming.period_from),
      valid_until: toIsoZ(upcoming.period_until),
      period: {
        valid_from: toIsoZ(upcoming.period_from),
        valid_until: toIsoZ(upcoming.period_until),
        label: formatPeriodLabel(upcoming.period_from, upcoming.period_until),
        title: periodMonthTitle(upcoming.period_from),
      },
      license_id: license.license_id,
    };
  }
  return { ok: false, reason: "unpaid", license_id: license.license_id };
}

async function extendLicenseForCustomer(tx, customer, durationMonths, now = utcNow(), purchased = null, opts = {}) {
  const updateBillingDeadline = opts.updateBillingDeadline !== false;
  let license = await getLicenseByCustomer(customer.id, tx);
  const pending = purchased ? [] : await pendingPeriodsForCustomer(customer.id, tx);
  const period = purchased || computePurchasedPeriod(license, durationMonths, now, pending, customer.billing_deadline);
  const stored = unionStoredWindow(license, period, now);
  const label = customer.hospital_name;
  const facility = (customer.facility_code || "").trim() || null;
  const ts = nowSql();

  if (!license) {
    const licenseId = randomUuid();
    const inserted = await tx.query(
      `INSERT INTO licenses
        (customer_id, license_id, customer_label, facility_code, valid_from, valid_until, notes, created_at, updated_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      [
        customer.id,
        licenseId,
        label,
        facility,
        toSqlDatetime(stored.validFrom),
        toSqlDatetime(stored.validUntil),
        null,
        ts,
        ts,
      ]
    );
    license = {
      id: inserted.insertId,
      customer_id: customer.id,
      license_id: licenseId,
      customer_label: label,
      facility_code: facility,
      valid_from: toSqlDatetime(stored.validFrom),
      valid_until: toSqlDatetime(stored.validUntil),
    };
  } else {
    await tx.query(
      `UPDATE licenses
       SET customer_label = ?, facility_code = ?, valid_from = ?, valid_until = ?, updated_at = ?
       WHERE id = ?`,
      [
        label,
        facility,
        toSqlDatetime(stored.validFrom),
        toSqlDatetime(stored.validUntil),
        ts,
        license.id,
      ]
    );
    license = {
      ...license,
      customer_label: label,
      facility_code: facility,
      valid_from: toSqlDatetime(stored.validFrom),
      valid_until: toSqlDatetime(stored.validUntil),
    };
  }
  license.purchased_from = toSqlDatetime(period.validFrom);
  license.purchased_until = toSqlDatetime(period.validUntil);
  license.purchased = period;
  if (updateBillingDeadline) {
    await tx.query("UPDATE customers SET billing_deadline = ?, updated_at = ? WHERE id = ?", [
      toSqlDatetime(period.validUntil),
      ts,
      customer.id,
    ]);
  }
  return license;
}

async function nextDocNumber(tx, kind) {
  const year = utcNow().getUTCFullYear();
  const lock = lockClause(tx);
  const { rows } = await tx.query(`SELECT name, next_value FROM sequences WHERE name = ?${lock}`, [kind]);
  if (!rows.length) {
    throw new Error(`Missing sequence ${kind}`);
  }
  const n = Number(rows[0].next_value) || 1;
  await tx.query("UPDATE sequences SET next_value = ? WHERE name = ?", [n + 1, kind]);
  const mid = kind === "invoice" ? "HMS" : "RCP";
  return `${companyInitials()}-${mid}-${year}-${String(n).padStart(6, "0")}`;
}

function selftestCalendar() {
  const now = new Date("2026-08-28T12:00:00Z");
  const p = computePurchasedPeriod(null, 1, now, [], "2026-08-31 23:59:59");
  if (toIsoZ(p.validFrom) !== "2026-09-01T00:00:00Z") {
    throw new Error(`expected Sept 1 start, got ${toIsoZ(p.validFrom)}`);
  }
  if (toIsoZ(p.validUntil) !== "2026-09-30T23:59:59Z") {
    throw new Error(`expected Sept 30 23:59:59, got ${toIsoZ(p.validUntil)}`);
  }
  const stacked = computePurchasedPeriod({ valid_until: "2026-09-30 23:59:59" }, 1, now, [], "2026-09-30 23:59:59");
  if (toIsoZ(stacked.validFrom) !== "2026-10-01T00:00:00Z") {
    throw new Error(`expected Oct 1 start, got ${toIsoZ(stacked.validFrom)}`);
  }
  if (toIsoZ(stacked.validUntil) !== "2026-10-31T23:59:59Z") {
    throw new Error(`expected Oct 31 end, got ${toIsoZ(stacked.validUntil)}`);
  }
  const q = computePurchasedPeriod(null, 3, now, [], "2026-08-31 23:59:59");
  if (toIsoZ(q.validUntil) !== "2026-11-30T23:59:59Z") {
    throw new Error(`expected Nov 30 for 3 months, got ${toIsoZ(q.validUntil)}`);
  }
  const anniversary = computePurchasedPeriod(null, 1, now, [], "2026-08-28 12:18:03");
  if (toIsoZ(anniversary.validFrom) !== "2026-08-28T12:18:04Z") {
    throw new Error(`expected anniversary start, got ${toIsoZ(anniversary.validFrom)}`);
  }
  if (toIsoZ(anniversary.validUntil) !== "2026-09-28T12:18:03Z") {
    throw new Error(`expected anniversary end, got ${toIsoZ(anniversary.validUntil)}`);
  }
  const previewIgnoresPending = computePurchasedPeriod(null, 1, now, [], "2026-08-31 23:59:59");
  const withPending = computePurchasedPeriod(
    null,
    1,
    now,
    [{ period_until: "2026-09-30 23:59:59" }],
    "2026-08-31 23:59:59"
  );
  if (toIsoZ(previewIgnoresPending.validFrom) !== "2026-09-01T00:00:00Z") {
    throw new Error("next unpaid month without pending rows should stay September");
  }
  if (toIsoZ(withPending.validFrom) !== "2026-10-01T00:00:00Z") {
    throw new Error("open pending coverage still stacks when explicitly passed in");
  }
  const patchDoesNotSkip = computePurchasedPeriod(
    { valid_until: "2026-12-31 23:59:59" },
    1,
    now,
    [],
    "2026-08-31 23:59:59"
  );
  if (toIsoZ(patchDoesNotSkip.validFrom) !== "2026-09-01T00:00:00Z") {
    throw new Error("a patch license window must not skip the next paid month");
  }
  console.log("license calendar selftest ok");
}

if (require.main === module && process.argv.includes("--selftest")) {
  selftestCalendar();
}

module.exports = {
  computeWindow,
  computePurchasedPeriod,
  unionStoredWindow,
  serializePeriod,
  getLicenseByCustomer,
  getLicenseByPublicId,
  pendingPeriodsForCustomer,
  signedDocumentFor,
  latestPaidPayment,
  coveringPaidPayment,
  upcomingPaidPayment,
  currentSignedDocumentForHms,
  extendLicenseForCustomer,
  nextDocNumber,
  buildClaims,
  selftestCalendar,
};
