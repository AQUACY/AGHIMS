const { config } = require("./config");
const { getDb, nowSql } = require("./db");
const { parseDatetime, toSqlDatetime, utcNow, formatAccraStamp, formatGhs } = require("./dates");
const { getCustomer, customerLoginEmail } = require("./payments");
const { smtpConfigured, sendMail } = require("./mailer");

const DAY_MS = 24 * 60 * 60 * 1000;
const HOUR_MS = 60 * 60 * 1000;

function httpError(status, message) {
  const err = new Error(message);
  err.status = status;
  return err;
}

function payUrl() {
  return `${config.publicBaseUrl}/dashboard`;
}

function kindLabel(kind) {
  if (kind === "day") return "24-hour notice";
  if (kind === "hour") return "1-hour notice";
  return "reminder";
}

function dueKindForDeadline(deadline, now = utcNow()) {
  if (!deadline) return null;
  const msLeft = deadline.getTime() - now.getTime();
  if (msLeft <= 0) return null;
  if (msLeft <= HOUR_MS) return "hour";
  if (msLeft <= DAY_MS) return "day";
  return null;
}

function cycleKey(kind, deadline) {
  if (kind === "manual") return `manual:${Date.now()}`;
  return toSqlDatetime(deadline);
}

function buildCopy({ kind, customer, email, deadline }) {
  const company = config.company.name || "License Portal";
  const hospital = customer.hospital_name || "your hospital";
  const when = deadline ? formatAccraStamp(deadline) : "the current licence end date";
  const amount = formatGhs(customer.amount_pesewas);
  const link = payUrl();
  const phone = config.company.phone || "";
  let headline;
  let lead;
  if (kind === "day") {
    headline = "Your HMS licence renews in 24 hours";
    lead = `This is a 24-hour notice. The HMS licence for ${hospital} ends on ${when}.`;
  } else if (kind === "hour") {
    headline = "Your HMS licence expires in one hour";
    lead = `This is a one-hour notice. The HMS licence for ${hospital} ends on ${when}. Pay now so HMS stays licensed.`;
  } else {
    headline = "Reminder: renew your HMS licence";
    lead = `This is a reminder from ${company}. Please renew the HMS licence for ${hospital}${deadline ? `, which ends on ${when}` : ""}.`;
  }
  const subject = `${headline} — ${hospital}`;
  const text = [
    lead,
    "",
    `Hospital: ${hospital}`,
    customer.facility_code ? `Facility code: ${customer.facility_code}` : "",
    `Amount due: ${amount}`,
    deadline ? `Licence ends: ${when}` : "",
    `Pay here: ${link}`,
    "",
    "Sign in with the IT manager email on the license portal, then pay with Paystack (card or mobile money).",
    phone ? `Questions: ${phone}` : "",
    "",
    company,
  ]
    .filter((line) => line !== "")
    .join("\n");
  const html = `<!DOCTYPE html>
<html><body style="margin:0;padding:0;background:#f4efe6;font-family:Segoe UI,Arial,sans-serif;color:#14213d;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f4efe6;padding:24px 12px;">
    <tr><td align="center">
      <table role="presentation" width="560" cellspacing="0" cellpadding="0" style="background:#ffffff;border-radius:16px;padding:28px 28px 24px;max-width:560px;">
        <tr><td style="font-size:12px;letter-spacing:0.14em;text-transform:uppercase;color:#c4a35a;font-weight:700;">${escapeHtml(company)}</td></tr>
        <tr><td style="padding-top:10px;font-size:22px;line-height:1.3;font-weight:700;">${escapeHtml(headline)}</td></tr>
        <tr><td style="padding-top:12px;font-size:15px;line-height:1.55;color:#333;">${escapeHtml(lead)}</td></tr>
        <tr><td style="padding-top:18px;">
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f7f4ee;border-radius:12px;">
            <tr><td style="padding:14px 16px;font-size:14px;line-height:1.7;">
              <strong>Hospital</strong><br>${escapeHtml(hospital)}<br>
              ${customer.facility_code ? `<strong>Facility</strong><br>${escapeHtml(customer.facility_code)}<br>` : ""}
              <strong>Amount due</strong><br>${escapeHtml(amount)}<br>
              ${deadline ? `<strong>Licence ends</strong><br>${escapeHtml(when)}` : ""}
            </td></tr>
          </table>
        </td></tr>
        <tr><td style="padding-top:22px;">
          <a href="${escapeHtml(link)}" style="display:inline-block;background:#c4a35a;color:#1b1408;text-decoration:none;font-weight:700;padding:12px 20px;border-radius:999px;">Pay on the license portal</a>
        </td></tr>
        <tr><td style="padding-top:16px;font-size:13px;color:#5c6470;line-height:1.5;">
          Sign in as ${escapeHtml(email || "the IT manager")} and pay with Paystack. Invoice is for accounts; the receipt is issued after payment succeeds.
        </td></tr>
      </table>
    </td></tr>
  </table>
</body></html>`;
  return { subject, text, html };
}

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[c]));
}

async function alreadySent(customerId, kind, key) {
  const { rows } = await getDb().query(
    "SELECT id FROM reminder_sends WHERE customer_id = ? AND kind = ? AND cycle_key = ? AND status = 'sent' LIMIT 1",
    [customerId, kind, key]
  );
  return rows.length > 0;
}

async function recordSend({ customerId, kind, cycleKey: key, toEmail, subject, status, error }) {
  await getDb().query(
    `INSERT INTO reminder_sends
      (customer_id, kind, cycle_key, to_email, subject, status, error, created_at)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
    [customerId, kind, key, toEmail || "", subject || "", status, error || null, nowSql()]
  );
}

async function listReminders(customerId) {
  const { rows } = await getDb().query(
    "SELECT id, kind, to_email, subject, status, error, created_at FROM reminder_sends WHERE customer_id = ? ORDER BY id DESC LIMIT 20",
    [customerId]
  );
  return rows.map((r) => ({
    id: r.id,
    kind: r.kind,
    kind_label: kindLabel(r.kind),
    to_email: r.to_email,
    subject: r.subject,
    status: r.status,
    error: r.error,
    created_at: r.created_at,
  }));
}

async function sendReminderForCustomer(customer, kind, { deadline } = {}) {
  if (!smtpConfigured()) {
    throw httpError(503, "Email is not configured. Set SMTP_HOST, SMTP_USER, and SMTP_PASS.");
  }
  const email = await customerLoginEmail(customer.id);
  if (!email) throw httpError(400, "This hospital has no login email.");
  const due = deadline || parseDatetime(customer.billing_deadline);
  if (kind !== "manual" && !due) throw httpError(400, "Set the current license end date first.");
  const key = cycleKey(kind, due);
  if (kind !== "manual" && (await alreadySent(customer.id, kind, key))) {
    return { skipped: true, reason: "already_sent", kind };
  }
  const copy = buildCopy({ kind, customer, email, deadline: due });
  try {
    await sendMail({ to: email, subject: copy.subject, text: copy.text, html: copy.html, kind });
    await recordSend({
      customerId: customer.id,
      kind,
      cycleKey: key,
      toEmail: email,
      subject: copy.subject,
      status: "sent",
    });
  } catch (err) {
    await recordSend({
      customerId: customer.id,
      kind,
      cycleKey: key,
      toEmail: email,
      subject: copy.subject,
      status: "failed",
      error: err.message,
    });
    throw err;
  }
  return { skipped: false, kind, to: email, subject: copy.subject };
}

async function sendManualReminder(customerId) {
  const customer = await getCustomer(customerId);
  if (!customer) throw httpError(404, "Not found");
  return sendReminderForCustomer(customer, "manual", {
    deadline: parseDatetime(customer.billing_deadline),
  });
}

async function runScheduledReminders(now = utcNow()) {
  const { rows } = await getDb().query("SELECT * FROM customers WHERE status = ?", ["active"]);
  const sent = [];
  const skipped = [];
  const errors = [];
  for (const customer of rows) {
    const deadline = parseDatetime(customer.billing_deadline);
    const kind = dueKindForDeadline(deadline, now);
    if (!kind) continue;
    try {
      const result = await sendReminderForCustomer(customer, kind, { deadline });
      if (result.skipped) skipped.push({ id: customer.id, kind, reason: result.reason });
      else sent.push({ id: customer.id, kind, to: result.to });
    } catch (err) {
      errors.push({ id: customer.id, kind, error: err.message });
    }
  }
  return { sent: sent.length, skipped: skipped.length, errors: errors.length, details: { sent, skipped, errors } };
}

let loopTimer = null;

function startReminderLoop() {
  if (loopTimer) return;
  const interval = Math.max(60 * 1000, config.reminderIntervalMs || 10 * 60 * 1000);
  const tick = async () => {
    try {
      const result = await runScheduledReminders();
      if (result.sent || result.errors) {
        console.log(
          `reminders: sent ${result.sent}, skipped ${result.skipped}, errors ${result.errors}`
        );
      }
    } catch (err) {
      console.error("reminder loop", err);
    }
  };
  setTimeout(tick, 20 * 1000);
  loopTimer = setInterval(tick, interval);
  if (typeof loopTimer.unref === "function") loopTimer.unref();
}

module.exports = {
  dueKindForDeadline,
  sendManualReminder,
  sendReminderForCustomer,
  runScheduledReminders,
  listReminders,
  startReminderLoop,
  kindLabel,
};
