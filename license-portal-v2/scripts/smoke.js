#!/usr/bin/env node
/**
 * In-process smoke test: admin seed, hospital CRUD, manual license, PDFs, verify/online.
 */
const fs = require("fs");
const http = require("http");
const os = require("os");
const path = require("path");
const crypto = require("crypto");

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "lpv2-"));
const { privateKey } = crypto.generateKeyPairSync("rsa", {
  modulusLength: 2048,
  publicKeyEncoding: { type: "spki", format: "pem" },
  privateKeyEncoding: { type: "pkcs1", format: "pem" },
});
const keyPath = path.join(tmp, "license_private.pem");
fs.writeFileSync(keyPath, privateKey);

process.env.DATABASE_MODE = "sqlite";
process.env.SQLITE_DB_PATH = path.join(tmp, "test.db");
process.env.PORTAL_ADMIN_EMAIL = "license_admin";
process.env.PORTAL_ADMIN_PASSWORD = "smoke-admin-pass";
process.env.PORTAL_JWT_SECRET = "smoke-jwt-secret-not-for-prod";
process.env.ISSUER_SLUG = "smoke-issuer";
process.env.VERIFY_SHARED_SECRET = "smoke-verify-secret";
process.env.RSA_PRIVATE_KEY_FILE = keyPath;
process.env.PUBLIC_BASE_URL = "http://127.0.0.1";
process.env.COMPANY_NAME = "Smoke Test Ltd";
process.env.COMPANY_INITIALS = "STL";
process.env.COMPANY_EMAIL = "billing@smoke.test";
process.env.SMTP_HOST = "test";
process.env.CRON_SECRET = "smoke-cron";
process.env.PAYSTACK_SECRET_KEY = "sk_test_smoke";
process.env.DOTENV_CONFIG_PATH = path.join(tmp, "no.env");

const { createApp } = require("../src/app");
const { verifyDocument } = require("../src/cryptoSign");

function listen(app) {
  return new Promise((resolve) => {
    const server = http.createServer(app);
    server.listen(0, "127.0.0.1", () => resolve(server));
  });
}

async function req(server, pathname, { method = "GET", body, headers = {}, token } = {}) {
  const { port } = server.address();
  const h = { ...headers };
  if (body && !h["Content-Type"]) h["Content-Type"] = "application/json";
  if (token) h.Authorization = `Bearer ${token}`;
  const res = await fetch(`http://127.0.0.1:${port}${pathname}`, {
    method,
    headers: h,
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await res.text();
  let json = null;
  try {
    json = text ? JSON.parse(text) : null;
  } catch (_) {
    json = null;
  }
  return { status: res.status, json, text, headers: res.headers };
}

async function main() {
  require("../src/cryptoSign").selftest();
  require("../src/license").selftestCalendar();
  const app = await createApp();
  const server = await listen(app);
  try {
    const login = await req(server, "/api/auth/login", {
      method: "POST",
      body: { email: "license_admin", password: "smoke-admin-pass" },
    });
    if (login.status !== 200) throw new Error(`login failed: ${login.text}`);
    const adminToken = login.json.access_token;

    const created = await req(server, "/api/admin/customers", {
      method: "POST",
      token: adminToken,
      body: {
        hospital_name: "Ridge Clinic",
        facility_code: "RIDGE01",
        amount_ghs: 2500,
        duration_months: 1,
        billing_deadline: "2026-08-31T23:59:59Z",
        email: "it@ridge.test",
        password: "it-pass-1234",
      },
    });
    if (created.status !== 201) throw new Error(`create customer: ${created.text}`);
    const customerId = created.json.customer.id;
    if (created.json.login.password !== "it-pass-1234") throw new Error("password not returned");

    const { getDb, nowSql } = require("../src/db");
    const ts = nowSql();
    await getDb().query(
      `INSERT INTO payments
        (customer_id, license_id, paystack_reference, paystack_access_code, amount_pesewas, currency,
         duration_months, status, channel, paid_at, period_from, period_until, raw_payload, notes, created_at, updated_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      [
        customerId,
        null,
        "LPV2-smoke-open",
        null,
        250000,
        "GHS",
        1,
        "pending",
        "paystack",
        null,
        "2026-09-01 00:00:00",
        "2026-09-30 23:59:59",
        null,
        null,
        ts,
        ts,
      ]
    );
    const itLoginOpen = await req(server, "/api/auth/login", {
      method: "POST",
      body: { email: "it@ridge.test", password: "it-pass-1234" },
    });
    if (itLoginOpen.status !== 200) throw new Error(`it login: ${itLoginOpen.text}`);
    const meOpen = await req(server, "/api/me", { token: itLoginOpen.json.access_token });
    const nextFrom = meOpen.json && meOpen.json.next_period && meOpen.json.next_period.valid_from;
    if (!String(nextFrom || "").startsWith("2026-09-01")) {
      throw new Error(`open pending must not skip next month, got ${JSON.stringify(meOpen.json && meOpen.json.next_period)}`);
    }
    const openRow = (meOpen.json.payments || [])[0];
    if (!openRow || !openRow.can_retry) throw new Error("pending Paystack row should be retryable");
    await getDb().query("DELETE FROM payments WHERE customer_id = ?", [customerId]);

    const pendingRef = "LPV2-smoke-ref-1";
    await getDb().query(
      `INSERT INTO payments
        (customer_id, license_id, paystack_reference, paystack_access_code, amount_pesewas, currency,
         duration_months, status, channel, paid_at, raw_payload, notes, created_at, updated_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      [customerId, null, pendingRef, null, 250000, "GHS", 1, "pending", "paystack", null, null, null, ts, ts]
    );
    const eventBody = JSON.stringify({
      event: "charge.success",
      data: { reference: pendingRef, amount: 250000, status: "success" },
    });
    const badHook = await req(server, "/api/paystack/webhook", {
      method: "POST",
      headers: { "Content-Type": "application/json", "x-paystack-signature": "deadbeef" },
      body: JSON.parse(eventBody),
    });
    if (badHook.status !== 401) throw new Error(`expected webhook 401, got ${badHook.status} ${badHook.text}`);

    const sig = crypto.createHmac("sha512", "sk_test_smoke").update(eventBody).digest("hex");
    const { port } = server.address();
    const hookRes = await fetch(`http://127.0.0.1:${port}/api/paystack/webhook`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "x-paystack-signature": sig },
      body: eventBody,
    });
    if (!hookRes.ok) throw new Error(`webhook failed: ${await hookRes.text()}`);
    const hookAgain = await fetch(`http://127.0.0.1:${port}/api/paystack/webhook`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "x-paystack-signature": sig },
      body: eventBody,
    });
    if (!hookAgain.ok) throw new Error(`idempotent webhook failed: ${await hookAgain.text()}`);

    const issued = await req(server, `/api/admin/customers/${customerId}/issue-manual`, {
      method: "POST",
      token: adminToken,
      body: { notes: "smoke", period_from: "2026-09-01T00:00:00Z", period_until: "2026-09-30T23:59:59Z" },
    });
    if (issued.status !== 200) throw new Error(`issue-manual: ${issued.text}`);
    const licenseId = issued.json.license.license_id;
    if (!issued.json.payment.is_patch) throw new Error("manual issue should be a patch license");
    if (!issued.json.payment.license_url) throw new Error("missing payment license_url");
    if (issued.json.payment.download_label !== "Patch license JSON") throw new Error("patch download label");
    if (issued.json.payment.invoice || issued.json.payment.receipt) {
      throw new Error("patch license should not create invoice or receipt");
    }
    const firstPayId = issued.json.payment.id;
    const firstLicense = await req(server, issued.json.payment.license_url, { token: adminToken });
    if (firstLicense.status !== 200) throw new Error(`payment license: ${firstLicense.text}`);
    const disp = String(firstLicense.headers.get("content-disposition") || "");
    if (!disp.includes("patch-license")) throw new Error(`expected patch-license filename, got ${disp}`);

    const issuedAgain = await req(server, `/api/admin/customers/${customerId}/issue-manual`, {
      method: "POST",
      token: adminToken,
      body: { notes: "smoke second month", period_from: "2026-10-01T00:00:00Z", period_until: "2026-10-31T23:59:59Z" },
    });
    if (issuedAgain.status !== 200) throw new Error(`issue-manual 2: ${issuedAgain.text}`);
    const secondLicense = await req(server, issuedAgain.json.payment.license_url, { token: adminToken });
    if (secondLicense.status !== 200) throw new Error(`second payment license: ${secondLicense.text}`);
    if (firstLicense.json.claims.valid_from === secondLicense.json.claims.valid_from) {
      throw new Error("each paid month should have its own license window");
    }
    const replayFirst = await req(server, `/api/payments/${firstPayId}/license.json`, { token: adminToken });
    if (replayFirst.json.claims.valid_from !== firstLicense.json.claims.valid_from) {
      throw new Error("previous license file should stay tied to that payment");
    }

    const signed = await req(server, `/api/admin/licenses/${licenseId}/signed.json`, { token: adminToken });
    if (signed.status !== 200) throw new Error(`signed.json: ${signed.text}`);
    if (!signed.json.claims || !signed.json.signature_b64) throw new Error("bad signed document");
    if (signed.json.claims.issuer_slug !== "smoke-issuer") throw new Error("issuer mismatch");
    if (signed.json.claims.facility_code !== "RIDGE01") throw new Error("facility mismatch");

    const pub = crypto.createPublicKey(privateKey).export({ type: "spki", format: "pem" });
    const checked = verifyDocument(signed.json, pub);
    if (!checked.ok) throw new Error(`signature verify failed: ${checked.error}`);

    const verifyOk = await req(server, "/api/verify/online", {
      method: "POST",
      body: { license_id: licenseId, facility_code: "RIDGE01" },
      headers: { "X-License-Server-Key": "smoke-verify-secret" },
    });
    const starts = new Date(signed.json.claims.valid_from);
    if (starts > new Date()) {
      if (!verifyOk.json || verifyOk.json.reason !== "out_of_window") {
        throw new Error(`advance month should be out_of_window until the 1st, got ${verifyOk.text}`);
      }
    } else if (!verifyOk.json || verifyOk.json.ok !== true) {
      throw new Error(`verify: ${verifyOk.text}`);
    }

    const mismatch = await req(server, "/api/verify/online", {
      method: "POST",
      body: { license_id: licenseId, facility_code: "OTHER" },
      headers: { "X-License-Server-Key": "smoke-verify-secret" },
    });
    if (starts > new Date()) {
      if (!mismatch.json || mismatch.json.reason !== "out_of_window") {
        throw new Error(`expected out_of_window before coverage, got ${mismatch.text}`);
      }
    } else if (!mismatch.json || mismatch.json.reason !== "facility_mismatch") {
      throw new Error(`expected facility_mismatch, got ${mismatch.text}`);
    }

    const unknown = await req(server, "/api/verify/online", {
      method: "POST",
      body: { license_id: "does-not-exist", facility_code: "RIDGE01" },
      headers: { "X-License-Server-Key": "smoke-verify-secret" },
    });
    if (!unknown.json || unknown.json.reason !== "unknown_license") {
      throw new Error(`expected unknown_license, got ${unknown.text}`);
    }

    const itLogin = await req(server, "/api/auth/login", {
      method: "POST",
      body: { email: "it@ridge.test", password: "it-pass-1234" },
    });
    if (itLogin.status !== 200) throw new Error(`it login: ${itLogin.text}`);
    const itToken = itLogin.json.access_token;
    const me = await req(server, "/api/me", { token: itToken });
    if (!me.json.license || me.json.customer.amount_ghs !== 2500) throw new Error(`me: ${me.text}`);
    const paidHistory = (me.json.payments || []).filter((p) => p.status === "success");
    if (paidHistory.length < 2) throw new Error(`expected at least 2 paid months, got ${paidHistory.length}`);
    if (paidHistory.some((p) => !p.license_url)) throw new Error("each successful payment should expose license_url");
    const historic = await req(server, `/api/payments/${firstPayId}/license.json`, { token: itToken });
    if (historic.status !== 200) throw new Error(`customer historic license: ${historic.text}`);
    if (historic.json.claims.valid_from !== firstLicense.json.claims.valid_from) {
      throw new Error("IT manager should download the original month from history");
    }
    if (!String(me.json.next_period && me.json.next_period.valid_from || "").startsWith("2026-10-01")) {
      throw new Error(`patch must not skip the next paid month, got ${JSON.stringify(me.json.next_period)}`);
    }
    const receiptPay = (me.json.payments || []).find((p) => p.receipt && !p.is_patch);
    if (!receiptPay) throw new Error("Paystack payment should still have a receipt PDF");
    const refuseSub = await req(server, `/api/admin/payments/${receiptPay.id}`, { method: "DELETE", token: adminToken });
    if (refuseSub.status !== 400) {
      throw new Error(`expected 400 deleting subscription payment, got ${refuseSub.status} ${refuseSub.text}`);
    }
    const deleted = await req(server, `/api/admin/payments/${firstPayId}`, { method: "DELETE", token: adminToken });
    if (deleted.status !== 200) throw new Error(`delete patch: ${deleted.text}`);
    const gone = await req(server, `/api/payments/${firstPayId}/license.json`, { token: adminToken });
    if (gone.status === 200) throw new Error("deleted patch license should not download");
    const stillSecond = await req(server, issuedAgain.json.payment.license_url, { token: adminToken });
    if (stillSecond.status !== 200) throw new Error("remaining patch should still download");
    const claims = signed.json.claims;
    if (!String(claims.valid_from).endsWith("T00:00:00Z")) {
      throw new Error(`license should start at 00:00:00, got ${claims.valid_from}`);
    }
    if (!String(claims.valid_until).endsWith("T23:59:59Z")) {
      throw new Error(`license should end at 23:59:59, got ${claims.valid_until}`);
    }
    if (!me.json.next_period || !me.json.next_period.label) {
      throw new Error(`next_period missing: ${me.text}`);
    }

    const pdf = await req(server, receiptPay.receipt.url, { token: itToken });
    if (pdf.status !== 200 || !pdf.text.startsWith("%PDF")) {
      throw new Error(`receipt pdf missing, status ${pdf.status}`);
    }
    if (!/^STL-RCP-\d{4}-\d{6}$/.test(receiptPay.receipt.doc_number)) {
      throw new Error(`receipt number format: ${receiptPay.receipt.doc_number}`);
    }
    if (!receiptPay.invoice || !/^STL-HMS-\d{4}-\d{6}$/.test(receiptPay.invoice.doc_number)) {
      throw new Error(`invoice number format: ${JSON.stringify(receiptPay.invoice)}`);
    }
    const invoicePdf = await req(server, receiptPay.invoice.url, { token: itToken });
    if (invoicePdf.status !== 200 || !invoicePdf.text.startsWith("%PDF")) {
      throw new Error(`invoice pdf missing, status ${invoicePdf.status}`);
    }
    const verified = await req(server, `/api/verify/receipt/${receiptPay.receipt.doc_number}`);
    if (verified.status !== 200 || !verified.json.genuine || verified.json.payment_status !== "PAID") {
      throw new Error(`receipt verify api: ${verified.text}`);
    }
    if (verified.json.invoice_no !== receiptPay.invoice.doc_number) {
      throw new Error("verified receipt should cite the invoice number");
    }
    const verifyPage = await req(server, `/verify/${receiptPay.receipt.doc_number}`);
    if (verifyPage.status !== 200 || !verifyPage.text.includes("PAYMENT RECEIPT")) {
      throw new Error("verify page should load for a genuine receipt");
    }
    const fakeVerify = await req(server, "/api/verify/receipt/STL-RCP-1999-999999");
    if (fakeVerify.status !== 404 || fakeVerify.json.genuine !== false) {
      throw new Error(`expected 404 for unknown receipt, got ${fakeVerify.status} ${fakeVerify.text}`);
    }

    const badPw = await req(server, "/api/me/password", {
      method: "POST",
      token: itToken,
      body: { current_password: "wrong", new_password: "new-pass-9999" },
    });
    if (badPw.status !== 400) throw new Error(`expected bad current password, got ${badPw.status} ${badPw.text}`);
    const pw = await req(server, "/api/me/password", {
      method: "POST",
      token: itToken,
      body: { current_password: "it-pass-1234", new_password: "new-pass-9999" },
    });
    if (pw.status !== 200) throw new Error(`password change: ${pw.text}`);
    const relogin = await req(server, "/api/auth/login", {
      method: "POST",
      body: { email: "it@ridge.test", password: "new-pass-9999" },
    });
    if (relogin.status !== 200) throw new Error(`relogin after password change: ${relogin.text}`);

    const png =
      "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==";
    const logo = await req(server, "/api/admin/branding/logo", {
      method: "POST",
      token: adminToken,
      body: { data: png, mime: "image/png", filename: "mark.png" },
    });
    if (logo.status !== 200 || !logo.json.logo_url) throw new Error(`logo upload: ${logo.text}`);
    const cfg = await req(server, "/api/public-config");
    if (!cfg.json.logo_url) throw new Error("public-config missing logo_url");
    const logoGet = await req(server, cfg.json.logo_url.split("?")[0]);
    if (logoGet.status !== 200) throw new Error(`logo get: ${logoGet.status}`);

    const yesterday = new Date();
    yesterday.setUTCDate(yesterday.getUTCDate() - 2);
    yesterday.setUTCHours(23, 59, 59, 0);
    const cover = await req(server, "/api/admin/customers", {
      method: "POST",
      token: adminToken,
      body: {
        hospital_name: "Cover Clinic",
        facility_code: "COVER01",
        amount_ghs: 100,
        duration_months: 1,
        billing_deadline: yesterday.toISOString(),
        email: "it@cover.test",
        password: "cover-pass-1234",
      },
    });
    if (cover.status !== 201) throw new Error(`cover customer: ${cover.text}`);
    const coverId = cover.json.customer.id;
    const coverIssue = await req(server, `/api/admin/customers/${coverId}/issue-manual`, {
      method: "POST",
      token: adminToken,
      body: {
        notes: "covering now",
        period_from: new Date(Date.now() - 24 * 3600 * 1000).toISOString(),
        period_until: new Date(Date.now() + 10 * 24 * 3600 * 1000).toISOString(),
      },
    });
    if (coverIssue.status !== 200) throw new Error(`cover issue: ${coverIssue.text}`);
    const denied = await req(server, "/api/license/current", {
      method: "POST",
      headers: { "X-License-Server-Key": "nope" },
      body: { facility_code: "COVER01" },
    });
    if (denied.status !== 403) throw new Error(`expected 403 for bad server key, got ${denied.status}`);
    const current = await req(server, "/api/license/current", {
      method: "POST",
      headers: { "X-License-Server-Key": "smoke-verify-secret" },
      body: { facility_code: "COVER01" },
    });
    if (current.status !== 200 || !current.json.ok || !current.json.document) {
      throw new Error(`current license pull: ${current.text}`);
    }
    const coverIssue2 = await req(server, `/api/admin/customers/${coverId}/issue-manual`, {
      method: "POST",
      token: adminToken,
      body: {
        notes: "newer covering patch",
        period_from: new Date(Date.now() - 2 * 3600 * 1000).toISOString(),
        period_until: new Date(Date.now() + 11 * 24 * 3600 * 1000).toISOString(),
      },
    });
    if (coverIssue2.status !== 200) throw new Error(`cover issue 2: ${coverIssue2.text}`);
    const replaced = await req(server, "/api/license/current", {
      method: "POST",
      headers: { "X-License-Server-Key": "smoke-verify-secret" },
      body: { facility_code: "COVER01" },
    });
    if (replaced.status !== 200 || !replaced.json.ok) throw new Error(`replaced pull: ${replaced.text}`);
    if (replaced.json.document.claims.valid_from === current.json.document.claims.valid_from) {
      throw new Error("newer covering patch should replace the HMS current file");
    }
    await req(server, `/api/admin/customers/${coverId}/issue-manual`, {
      method: "POST",
      token: adminToken,
      body: {
        notes: "future month",
        period_from: new Date(Date.now() + 40 * 24 * 3600 * 1000).toISOString(),
        period_until: new Date(Date.now() + 70 * 24 * 3600 * 1000).toISOString(),
      },
    });
    const stillCurrent = await req(server, "/api/license/current", {
      method: "POST",
      headers: { "X-License-Server-Key": "smoke-verify-secret" },
      body: { facility_code: "COVER01" },
    });
    if (stillCurrent.json.document.claims.valid_from !== replaced.json.document.claims.valid_from) {
      throw new Error("HMS pull must keep the in-force month, not a future prepaid month");
    }

    const patched = await req(server, `/api/admin/customers/${customerId}`, {
      method: "PATCH",
      token: adminToken,
      body: { amount_ghs: 4500, duration_months: 6 },
    });
    if (patched.json.customer.amount_ghs !== 4500 || patched.json.customer.duration_months !== 6) {
      throw new Error(`patch failed: ${patched.text}`);
    }

    const { capturedMails } = require("../src/mailer");
    const { runScheduledReminders } = require("../src/reminders");
    capturedMails.length = 0;
    const dayCust = await req(server, "/api/admin/customers", {
      method: "POST",
      token: adminToken,
      body: {
        hospital_name: "Day Notice Clinic",
        facility_code: "DAY01",
        amount_ghs: 500,
        duration_months: 1,
        billing_deadline: new Date(Date.now() + 20 * 3600 * 1000).toISOString(),
        email: "it@day.test",
        password: "day-pass-1234",
      },
    });
    if (dayCust.status !== 201) throw new Error(`day customer: ${dayCust.text}`);
    const hourCust = await req(server, "/api/admin/customers", {
      method: "POST",
      token: adminToken,
      body: {
        hospital_name: "Hour Notice Clinic",
        facility_code: "HOUR01",
        amount_ghs: 500,
        duration_months: 1,
        billing_deadline: new Date(Date.now() + 40 * 60 * 1000).toISOString(),
        email: "it@hour.test",
        password: "hour-pass-1234",
      },
    });
    if (hourCust.status !== 201) throw new Error(`hour customer: ${hourCust.text}`);
    const batch = await runScheduledReminders();
    if (!capturedMails.some((m) => m.to === "it@day.test" && m.kind === "day")) {
      throw new Error(`expected 24-hour notice, sent=${batch.sent} ${JSON.stringify(capturedMails.map((m) => m.kind + ":" + m.to))}`);
    }
    if (!capturedMails.some((m) => m.to === "it@hour.test" && m.kind === "hour")) {
      throw new Error(`expected 1-hour notice, sent=${batch.sent}`);
    }
    const afterFirst = capturedMails.length;
    await runScheduledReminders();
    if (capturedMails.length !== afterFirst) throw new Error("scheduled reminders must not duplicate");
    const manual = await req(server, `/api/admin/customers/${dayCust.json.customer.id}/remind`, {
      method: "POST",
      token: adminToken,
    });
    if (manual.status !== 200 || manual.json.kind !== "manual") {
      throw new Error(`manual reminder: ${manual.status} ${manual.text}`);
    }
    const deniedCron = await req(server, "/api/cron/reminders", { method: "POST" });
    if (deniedCron.status !== 403) throw new Error(`cron without key: ${deniedCron.status}`);
    const cronOk = await req(server, "/api/cron/reminders", {
      method: "GET",
      headers: { "X-Cron-Key": "smoke-cron" },
    });
    if (cronOk.status !== 200) throw new Error(`cron with key: ${cronOk.text}`);

    console.log("smoke ok");
  } finally {
    server.close();
    fs.rmSync(tmp, { recursive: true, force: true });
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
