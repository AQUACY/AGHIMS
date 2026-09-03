const { getDb, nowSql } = require("./db");
const {
  hashPassword,
  verifyPassword,
  createToken,
  setAuthCookie,
  clearAuthCookie,
  generatePassword,
  findUserByEmail,
  publicUser,
  authRequired,
  adminRequired,
  customerRequired,
  changeOwnPassword,
} = require("./auth");
const { config } = require("./config");
const { getLicenseByCustomer, getLicenseByPublicId, latestPaidPayment, coveringPaidPayment, currentSignedDocumentForHms } = require("./license");
const {
  httpError,
  getCustomer,
  customerLoginEmail,
  documentsForPayment,
  serializePayment,
  serializeCustomer,
  serializeLicense,
  createCheckout,
  ensureCurrentBillInvoice,
  retryPaymentById,
  fulfillByReference,
  getPaymentStatus,
  issueManual,
  deletePatchPayment,
  getDocumentForUser,
  getPaymentForUser,
  signedLicenseForPayment,
  findPublicReceipt,
  refreshDocumentPdf,
  previewNextPeriod,
  findPaymentByReference,
} = require("./payments");
const { sendManualReminder, runScheduledReminders, listReminders } = require("./reminders");
const { smtpConfigured } = require("./mailer");
const { ghsToPesewas, utcNow, toIsoZ, parseAdminDatetime, toSqlDatetime } = require("./dates");
const { verifyWebhookSignature } = require("./paystack");
const { documentAbsPath } = require("./pdfs");
const { getLogo, publicLogoUrl, saveLogo, deleteLogo } = require("./branding");
const fs = require("fs");
const express = require("express");

function asyncHandler(fn) {
  return (req, res, next) => Promise.resolve(fn(req, res, next)).catch(next);
}

async function listPayments(customerId) {
  const db = getDb();
  const { rows } = await db.query(
    "SELECT * FROM payments WHERE customer_id = ? ORDER BY id DESC",
    [customerId]
  );
  const out = [];
  for (const p of rows) {
    const docs = await documentsForPayment(p.id);
    out.push(serializePayment(p, docs));
  }
  return out;
}

function mountRoutes(app) {
  app.get("/api/health", (req, res) => {
    res.json({ service: "license-portal-v2", ok: true });
  });

  async function cronReminders(req, res) {
    const secret = config.cronSecret;
    const given = String(req.headers["x-cron-key"] || req.query.key || "").trim();
    if (!secret || given !== secret) {
      return res.status(403).json({ error: "Invalid cron key" });
    }
    const result = await runScheduledReminders();
    res.json(result);
  }
  app.post("/api/cron/reminders", asyncHandler(cronReminders));
  app.get("/api/cron/reminders", asyncHandler(cronReminders));

  app.get("/api/public-config", (req, res) => {
    res.json({
      company_name: config.company.name,
      company_tagline: config.company.tagline,
      version: "2.0.0",
      logo_url: publicLogoUrl(),
    });
  });

  app.get(
    "/api/verify/receipt/:docNumber",
    asyncHandler(async (req, res) => {
      const found = await findPublicReceipt(req.params.docNumber);
      if (!found) {
        return res.status(404).json({
          ok: false,
          genuine: false,
          error: "No genuine receipt was found for that number.",
        });
      }
      res.json(found);
    })
  );

  app.get("/api/branding/logo", (req, res) => {
    const logo = getLogo();
    if (!logo) return res.status(404).end();
    res.setHeader("Content-Type", logo.mime);
    res.setHeader("Cache-Control", "public, max-age=3600");
    fs.createReadStream(logo.absPath).pipe(res);
  });

  app.post(
    "/api/auth/login",
    asyncHandler(async (req, res) => {
      const email = String((req.body && req.body.email) || "").trim().toLowerCase();
      const password = (req.body && req.body.password) || "";
      if (!email || !password) {
        return res.status(400).json({ error: "Email and password are required" });
      }
      const user = await findUserByEmail(email);
      if (!user || !verifyPassword(password, user.password_hash)) {
        return res.status(401).json({ error: "Invalid credentials" });
      }
      const token = createToken(user);
      setAuthCookie(res, token);
      return res.json({ access_token: token, token_type: "bearer", user: publicUser(user) });
    })
  );

  app.post("/api/auth/logout", (req, res) => {
    clearAuthCookie(res);
    res.json({ ok: true });
  });

  app.get(
    "/api/me",
    authRequired,
    asyncHandler(async (req, res) => {
      const payload = { user: publicUser(req.user) };
      if (req.user.role === "customer" && req.user.customer_id) {
        const customer = await getCustomer(req.user.customer_id);
        const license = await getLicenseByCustomer(req.user.customer_id);
        const payments = await listPayments(req.user.customer_id);
        payload.customer = serializeCustomer(customer);
        payload.license = serializeLicense(license);
        payload.payments = payments;
        payload.next_period = await previewNextPeriod(customer);
        const latestPaid = payments.find((p) => p.status === "success");
        payload.latest_paid = latestPaid || null;
        payload.current_invoice_url = payload.next_period ? "/api/invoice/current.pdf" : null;
      }
      res.json(payload);
    })
  );

  app.post(
    "/api/me/password",
    authRequired,
    asyncHandler(async (req, res) => {
      const currentPassword = (req.body && req.body.current_password) || "";
      const newPassword = (req.body && req.body.new_password) || "";
      await changeOwnPassword(req.user, currentPassword, newPassword);
      res.json({ ok: true });
    })
  );

  app.post(
    "/api/pay/initialize",
    authRequired,
    customerRequired,
    asyncHandler(async (req, res) => {
      const customer = await getCustomer(req.user.customer_id);
      if (!customer) return res.status(404).json({ error: "Hospital account not found" });
      const result = await createCheckout(customer, req.user);
      res.json(result);
    })
  );

  async function sendCurrentInvoicePdf(res, customer, user) {
    const payment = await ensureCurrentBillInvoice(customer, user);
    if (!payment || !payment.invoice) {
      return res.status(404).json({ error: "Invoice could not be created" });
    }
    const doc = await getDocumentForUser(payment.invoice.id, user);
    if (!doc) return res.status(404).json({ error: "Invoice not found" });
    await refreshDocumentPdf(doc);
    const abs = documentAbsPath(doc.file_path);
    if (!fs.existsSync(abs)) return res.status(404).json({ error: "File missing on server" });
    res.setHeader("Content-Type", "application/pdf");
    res.setHeader("Content-Disposition", `attachment; filename="${doc.doc_number}.pdf"`);
    fs.createReadStream(abs).pipe(res);
  }

  app.get(
    "/api/invoice/current.pdf",
    authRequired,
    customerRequired,
    asyncHandler(async (req, res) => {
      const customer = await getCustomer(req.user.customer_id);
      if (!customer) return res.status(404).json({ error: "Hospital account not found" });
      await sendCurrentInvoicePdf(res, customer, req.user);
    })
  );

  app.post(
    "/api/payments/:id/retry",
    authRequired,
    customerRequired,
    asyncHandler(async (req, res) => {
      const result = await retryPaymentById(req.params.id, req.user);
      res.json(result);
    })
  );

  app.get(
    "/api/pay/status",
    authRequired,
    asyncHandler(async (req, res) => {
      const reference = String(req.query.reference || "").trim();
      if (!reference) return res.status(400).json({ error: "reference is required" });
      const payment = await findPaymentByReference(reference);
      if (!payment) return res.status(404).json({ error: "Unknown payment reference" });
      if (req.user.role !== "admin" && Number(req.user.customer_id) !== Number(payment.customer_id)) {
        return res.status(403).json({ error: "Not allowed" });
      }
      const result = await getPaymentStatus(reference);
      res.json(result);
    })
  );

  app.get(
    "/api/pay/:id",
    authRequired,
    asyncHandler(async (req, res) => {
      const { rows } = await getDb().query("SELECT * FROM payments WHERE id = ?", [req.params.id]);
      if (!rows.length) return res.status(404).json({ error: "Payment not found" });
      if (req.user.role !== "admin" && Number(req.user.customer_id) !== Number(rows[0].customer_id)) {
        return res.status(403).json({ error: "Not allowed" });
      }
      const docs = await documentsForPayment(rows[0].id);
      res.json({ payment: serializePayment(rows[0], docs) });
    })
  );

  app.get(
    "/api/payments/:id/license.json",
    authRequired,
    asyncHandler(async (req, res) => {
      const payment = await getPaymentForUser(req.params.id, req.user);
      if (!payment) return res.status(404).json({ error: "Payment not found" });
      const { document, filename } = await signedLicenseForPayment(payment);
      res.setHeader("Content-Disposition", `attachment; filename="${filename}"`);
      res.json(document);
    })
  );

  app.get(
    "/api/license/signed.json",
    authRequired,
    customerRequired,
    asyncHandler(async (req, res) => {
      const paid = await latestPaidPayment(req.user.customer_id);
      if (!paid) return res.status(404).json({ error: "No license yet. Complete payment first." });
      const { document, filename } = await signedLicenseForPayment(paid);
      res.setHeader("Content-Disposition", `attachment; filename="${filename}"`);
      res.json(document);
    })
  );

  app.get(
    "/api/documents/:id.pdf",
    authRequired,
    asyncHandler(async (req, res) => {
      const doc = await getDocumentForUser(req.params.id, req.user);
      if (!doc) return res.status(404).json({ error: "Document not found" });
      await refreshDocumentPdf(doc);
      const abs = documentAbsPath(doc.file_path);
      if (!fs.existsSync(abs)) return res.status(404).json({ error: "File missing on server" });
      res.setHeader("Content-Type", "application/pdf");
      res.setHeader("Content-Disposition", `attachment; filename="${doc.doc_number}.pdf"`);
      fs.createReadStream(abs).pipe(res);
    })
  );

  app.get(
    "/api/invoices/:id.pdf",
    authRequired,
    asyncHandler(async (req, res) => {
      req.url = `/api/documents/${req.params.id}.pdf`;
      const doc = await getDocumentForUser(req.params.id, req.user);
      if (!doc || doc.doc_type !== "invoice") return res.status(404).json({ error: "Invoice not found" });
      await refreshDocumentPdf(doc);
      const abs = documentAbsPath(doc.file_path);
      if (!fs.existsSync(abs)) return res.status(404).json({ error: "File missing on server" });
      res.setHeader("Content-Type", "application/pdf");
      res.setHeader("Content-Disposition", `attachment; filename="${doc.doc_number}.pdf"`);
      fs.createReadStream(abs).pipe(res);
    })
  );

  app.get(
    "/api/receipts/:id.pdf",
    authRequired,
    asyncHandler(async (req, res) => {
      const doc = await getDocumentForUser(req.params.id, req.user);
      if (!doc || doc.doc_type !== "receipt") return res.status(404).json({ error: "Receipt not found" });
      await refreshDocumentPdf(doc);
      const abs = documentAbsPath(doc.file_path);
      if (!fs.existsSync(abs)) return res.status(404).json({ error: "File missing on server" });
      res.setHeader("Content-Type", "application/pdf");
      res.setHeader("Content-Disposition", `attachment; filename="${doc.doc_number}.pdf"`);
      fs.createReadStream(abs).pipe(res);
    })
  );

  app.get(
    "/api/admin/customers",
    authRequired,
    adminRequired,
    asyncHandler(async (req, res) => {
      const { rows } = await getDb().query("SELECT * FROM customers ORDER BY id DESC");
      const out = [];
      for (const c of rows) {
        const email = await customerLoginEmail(c.id);
        const license = await getLicenseByCustomer(c.id);
        out.push(serializeCustomer(c, { email, license: serializeLicense(license) }));
      }
      res.json(out);
    })
  );

  app.post(
    "/api/admin/customers",
    authRequired,
    adminRequired,
    asyncHandler(async (req, res) => {
      const body = req.body || {};
      const hospitalName = String(body.hospital_name || "").trim();
      const email = String(body.email || "").trim().toLowerCase();
      if (!hospitalName) return res.status(400).json({ error: "hospital_name is required" });
      if (!email) return res.status(400).json({ error: "email is required" });
      const existing = await findUserByEmail(email);
      if (existing) return res.status(400).json({ error: "That login email is already in use" });

      let amountPesewas;
      try {
        amountPesewas = ghsToPesewas(body.amount_ghs);
      } catch (err) {
        return res.status(400).json({ error: err.message });
      }
      const duration = Math.max(1, parseInt(body.duration_months, 10) || 0);
      if (!duration) return res.status(400).json({ error: "duration_months must be at least 1" });
      const password = String(body.password || "").trim() || generatePassword();
      const ts = nowSql();
      const facility = String(body.facility_code || "").trim() || null;
      const notes = String(body.notes || "").trim() || null;
      const deadline = parseAdminDatetime(body.billing_deadline);
      if (!deadline) {
        return res.status(400).json({ error: "Set the current license end date and time (renewal deadline)." });
      }

      const created = await getDb().withTransaction(async (tx) => {
        const inserted = await tx.query(
          `INSERT INTO customers
            (hospital_name, facility_code, amount_pesewas, duration_months, currency, notes, status, billing_deadline, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
          [hospitalName, facility, amountPesewas, duration, "GHS", notes, "active", toSqlDatetime(deadline), ts, ts]
        );
        const customerId = inserted.insertId;
        await tx.query(
          "INSERT INTO users (email, password_hash, role, customer_id, created_at) VALUES (?, ?, ?, ?, ?)",
          [email, hashPassword(password), "customer", customerId, ts]
        );
        const { rows } = await tx.query("SELECT * FROM customers WHERE id = ?", [customerId]);
        return rows[0];
      });

      res.status(201).json({
        customer: serializeCustomer(created, { email }),
        login: { email, password },
      });
    })
  );

  app.get(
    "/api/admin/customers/:id",
    authRequired,
    adminRequired,
    asyncHandler(async (req, res) => {
      const customer = await getCustomer(req.params.id);
      if (!customer) return res.status(404).json({ error: "Not found" });
      const email = await customerLoginEmail(customer.id);
      const license = await getLicenseByCustomer(customer.id);
      const payments = await listPayments(customer.id);
      res.json({
        customer: serializeCustomer(customer, { email }),
        license: serializeLicense(license),
        payments,
        reminders: await listReminders(customer.id),
        mail_configured: smtpConfigured(),
      });
    })
  );

  app.patch(
    "/api/admin/customers/:id",
    authRequired,
    adminRequired,
    asyncHandler(async (req, res) => {
      const customer = await getCustomer(req.params.id);
      if (!customer) return res.status(404).json({ error: "Not found" });
      const body = req.body || {};
      const hospitalName = body.hospital_name !== undefined ? String(body.hospital_name).trim() : customer.hospital_name;
      const facility =
        body.facility_code !== undefined ? String(body.facility_code).trim() || null : customer.facility_code;
      const notes = body.notes !== undefined ? String(body.notes).trim() || null : customer.notes;
      const status = body.status !== undefined ? String(body.status).trim() : customer.status;
      let amountPesewas = customer.amount_pesewas;
      if (body.amount_ghs !== undefined && body.amount_ghs !== null && body.amount_ghs !== "") {
        try {
          amountPesewas = ghsToPesewas(body.amount_ghs);
        } catch (err) {
          return res.status(400).json({ error: err.message });
        }
      }
      let duration = customer.duration_months;
      if (body.duration_months !== undefined) {
        duration = Math.max(1, parseInt(body.duration_months, 10) || 0);
        if (!duration) return res.status(400).json({ error: "duration_months must be at least 1" });
      }
      let billingDeadline = customer.billing_deadline;
      if (body.billing_deadline !== undefined) {
        const parsed = parseAdminDatetime(body.billing_deadline);
        if (!parsed) return res.status(400).json({ error: "Invalid license end date and time." });
        billingDeadline = toSqlDatetime(parsed);
      }
      await getDb().query(
        `UPDATE customers
         SET hospital_name = ?, facility_code = ?, amount_pesewas = ?, duration_months = ?, notes = ?, status = ?, billing_deadline = ?, updated_at = ?
         WHERE id = ?`,
        [hospitalName, facility, amountPesewas, duration, notes, status, billingDeadline, nowSql(), customer.id]
      );
      const updated = await getCustomer(customer.id);
      const email = await customerLoginEmail(updated.id);
      res.json({ customer: serializeCustomer(updated, { email }) });
    })
  );

  app.post(
    "/api/admin/customers/:id/reset-password",
    authRequired,
    adminRequired,
    asyncHandler(async (req, res) => {
      const customer = await getCustomer(req.params.id);
      if (!customer) return res.status(404).json({ error: "Not found" });
      const { rows } = await getDb().query("SELECT * FROM users WHERE customer_id = ? AND role = ? LIMIT 1", [
        customer.id,
        "customer",
      ]);
      if (!rows.length) return res.status(404).json({ error: "No login for this hospital" });
      const password = String((req.body && req.body.password) || "").trim() || generatePassword();
      await getDb().query("UPDATE users SET password_hash = ? WHERE id = ?", [hashPassword(password), rows[0].id]);
      res.json({ email: rows[0].email, password });
    })
  );

  app.get(
    "/api/admin/customers/:id/invoice.pdf",
    authRequired,
    adminRequired,
    asyncHandler(async (req, res) => {
      const customer = await getCustomer(req.params.id);
      if (!customer) return res.status(404).json({ error: "Not found" });
      await sendCurrentInvoicePdf(res, customer, req.user);
    })
  );

  app.post(
    "/api/admin/customers/:id/issue-manual",
    authRequired,
    adminRequired,
    asyncHandler(async (req, res) => {
      const customer = await getCustomer(req.params.id);
      if (!customer) return res.status(404).json({ error: "Not found" });
      const notes = (req.body && req.body.notes) || "";
      const result = await issueManual(customer, {
        notes,
        email: await customerLoginEmail(customer.id),
        periodFrom: req.body && (req.body.period_from || req.body.patch_from),
        periodUntil: req.body && (req.body.period_until || req.body.patch_until),
      });
      res.json(result);
    })
  );

  app.post(
    "/api/admin/customers/:id/remind",
    authRequired,
    adminRequired,
    asyncHandler(async (req, res) => {
      const result = await sendManualReminder(req.params.id);
      res.json(result);
    })
  );

  app.post(
    "/api/admin/reminders/run",
    authRequired,
    adminRequired,
    asyncHandler(async (req, res) => {
      const result = await runScheduledReminders();
      res.json(result);
    })
  );

  app.delete(
    "/api/admin/payments/:id",
    authRequired,
    adminRequired,
    asyncHandler(async (req, res) => {
      const result = await deletePatchPayment(req.params.id);
      res.json(result);
    })
  );

  app.get(
    "/api/admin/payments",
    authRequired,
    adminRequired,
    asyncHandler(async (req, res) => {
      const { rows } = await getDb().query("SELECT * FROM payments ORDER BY id DESC LIMIT 200");
      const out = [];
      for (const p of rows) {
        const docs = await documentsForPayment(p.id);
        const customer = await getCustomer(p.customer_id);
        out.push({
          ...serializePayment(p, docs),
          hospital_name: customer ? customer.hospital_name : "",
        });
      }
      res.json(out);
    })
  );

  app.post(
    "/api/admin/branding/logo",
    authRequired,
    adminRequired,
    asyncHandler(async (req, res) => {
      const body = req.body || {};
      const logo = saveLogo({
        data: body.data,
        mime: body.mime,
        filename: body.filename,
      });
      res.json({
        ok: true,
        logo_url: publicLogoUrl(),
        mime: logo && logo.mime,
      });
    })
  );

  app.delete(
    "/api/admin/branding/logo",
    authRequired,
    adminRequired,
    asyncHandler(async (req, res) => {
      deleteLogo();
      res.json({ ok: true, logo_url: null });
    })
  );

  app.get(
    "/api/admin/licenses/:licenseId/signed.json",
    authRequired,
    adminRequired,
    asyncHandler(async (req, res) => {
      const license = await getLicenseByPublicId(req.params.licenseId);
      if (!license) return res.status(404).json({ error: "License not found" });
      const paid = await latestPaidPayment(license.customer_id);
      if (!paid) return res.status(404).json({ error: "No successful payment for this license" });
      const { document, filename } = await signedLicenseForPayment(paid);
      res.setHeader("Content-Disposition", `attachment; filename="${filename}"`);
      res.json(document);
    })
  );

  app.post(
    "/api/license/current",
    asyncHandler(async (req, res) => {
      const secret = config.verifySharedSecret;
      const given = String(req.headers["x-license-server-key"] || "").trim();
      if (!secret || given !== secret) {
        return res.status(403).json({ error: "Invalid license server key" });
      }
      const body = req.body || {};
      const result = await currentSignedDocumentForHms({
        licenseId: body.license_id,
        facilityCode: body.facility_code,
      });
      res.json(result);
    })
  );

  app.post(
    "/api/verify/online",
    asyncHandler(async (req, res) => {
      const secret = config.verifySharedSecret;
      const given = String(req.headers["x-license-server-key"] || "").trim();
      if (!secret || given !== secret) {
        return res.status(403).json({ error: "Invalid license server key" });
      }
      const licenseId = String((req.body && req.body.license_id) || "").trim();
      const row = await getLicenseByPublicId(licenseId);
      if (!row) return res.json({ ok: false, reason: "unknown_license" });
      const now = utcNow();
      const covering = await coveringPaidPayment(row.customer_id, now);
      if (!covering) {
        return res.json({ ok: false, reason: "out_of_window" });
      }
      const fc = (row.facility_code || "").trim();
      if (fc) {
        const reqFc = String((req.body && req.body.facility_code) || "").trim();
        if (reqFc !== fc) return res.json({ ok: false, reason: "facility_mismatch" });
      }
      return res.json({ ok: true, valid_until: toIsoZ(covering.period_until) });
    })
  );
}

function mountWebhook(app) {
  app.post(
    "/api/paystack/webhook",
    express.raw({ type: "*/*" }),
    asyncHandler(async (req, res) => {
      const raw = Buffer.isBuffer(req.body) ? req.body : Buffer.from(req.body || "");
      if (!verifyWebhookSignature(raw, req.headers["x-paystack-signature"])) {
        return res.status(401).json({ error: "Invalid signature" });
      }
      let event;
      try {
        event = JSON.parse(raw.toString("utf8"));
      } catch (_) {
        return res.status(400).json({ error: "Invalid JSON" });
      }
      if (event.event === "charge.success") {
        const reference = event.data && event.data.reference;
        if (reference) {
          try {
            await fulfillByReference(reference, event.data);
          } catch (err) {
            if (err.status !== 404) {
              console.error("webhook fulfill error", err);
              return res.status(500).json({ error: "Fulfill failed" });
            }
          }
        }
      }
      return res.json({ received: true });
    })
  );
}

function errorHandler(err, req, res, next) {
  if (res.headersSent) return next(err);
  const status = err.status || 500;
  if (status >= 500) console.error(err);
  res.status(status).json({ error: err.message || "Server error" });
}

module.exports = { mountRoutes, mountWebhook, errorHandler };
