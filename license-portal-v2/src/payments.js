const path = require("path");
const { config } = require("./config");
const { getDb, nowSql, lockClause } = require("./db");
const { getLicenseByCustomer, extendLicenseForCustomer, nextDocNumber, computePurchasedPeriod, serializePeriod, latestPaidPayment, signedDocumentFor } = require("./license");
const { writeInvoicePdf, writeReceiptPdf, relativeDocumentPath, documentAbsPath } = require("./pdfs");
const { initializeTransaction, verifyTransaction } = require("./paystack");
const { formatGhs, pesewasToGhsNumber, randomUuid, utcNow, toSqlDatetime, parseDatetime, formatPeriodLabel, periodMonthTitle, toDatetimeLocalValue } = require("./dates");

function httpError(status, message) {
  const err = new Error(message);
  err.status = status;
  return err;
}

async function getCustomer(id, runner = null) {
  const db = runner || getDb();
  const { rows } = await db.query("SELECT * FROM customers WHERE id = ?", [id]);
  return rows[0] || null;
}

async function customerLoginEmail(customerId, runner = null) {
  const db = runner || getDb();
  const { rows } = await db.query(
    "SELECT email FROM users WHERE customer_id = ? AND role = ? LIMIT 1",
    [customerId, "customer"]
  );
  return rows[0] ? rows[0].email : "";
}

async function documentsForPayment(paymentId, runner = null) {
  const db = runner || getDb();
  const { rows } = await db.query("SELECT * FROM documents WHERE payment_id = ? ORDER BY id ASC", [paymentId]);
  return rows;
}

function serializeDoc(d) {
  if (!d) return null;
  return {
    id: d.id,
    doc_type: d.doc_type,
    doc_number: d.doc_number,
    created_at: d.created_at,
    url: `/api/documents/${d.id}.pdf`,
  };
}

function paymentLicenseUrl(p) {
  if (!p || p.status !== "success" || !p.period_from || !p.period_until) return null;
  return `/api/payments/${p.id}/license.json`;
}

function paymentLicenseFilename(payment) {
  const title = payment.period_from ? periodMonthTitle(payment.period_from) : "";
  const slug = String(title || `payment-${payment.id}`)
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
  return `license-${slug || payment.id}.json`;
}

function paymentCanRetry(p) {
  if (!p) return false;
  if (p.channel === "manual") return false;
  const status = String(p.status || "").toLowerCase();
  return status === "pending" || status === "failed";
}

function parsePriorRefs(value) {
  if (!value) return [];
  try {
    const parsed = JSON.parse(value);
    return Array.isArray(parsed) ? parsed.map(String).filter(Boolean) : [];
  } catch (_) {
    return String(value)
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
  }
}

function samePeriod(payment, period) {
  const from = parseDatetime(payment && payment.period_from);
  const until = parseDatetime(payment && payment.period_until);
  if (!from || !until || !period || !period.validFrom || !period.validUntil) return false;
  return from.getTime() === period.validFrom.getTime() && until.getTime() === period.validUntil.getTime();
}

async function findPaymentByReference(reference, runner = null) {
  const db = runner || getDb();
  const ref = String(reference || "").trim();
  if (!ref) return null;
  const { rows } = await db.query("SELECT * FROM payments WHERE paystack_reference = ?", [ref]);
  if (rows[0]) return rows[0];
  const { rows: listed } = await db.query(
    "SELECT * FROM payments WHERE paystack_prior_refs IS NOT NULL AND paystack_prior_refs != ''"
  );
  return listed.find((p) => parsePriorRefs(p.paystack_prior_refs).includes(ref)) || null;
}

async function failOtherPending(customerId, exceptPaymentId) {
  const ts = nowSql();
  if (exceptPaymentId) {
    await getDb().query(
      `UPDATE payments SET status = ?, notes = ?, updated_at = ?
       WHERE customer_id = ? AND status = ? AND id != ?`,
      ["failed", "Superseded by a new checkout", ts, customerId, "pending", exceptPaymentId]
    );
    return;
  }
  await getDb().query(
    `UPDATE payments SET status = ?, notes = ?, updated_at = ?
     WHERE customer_id = ? AND status = ?`,
    ["failed", "Superseded by a new checkout", ts, customerId, "pending"]
  );
}

function serializePayment(p, docs = []) {
  const list = docs.filter((d) => d.payment_id === p.id || d.payment_id === undefined);
  const attached = docs.length && docs[0].payment_id !== undefined ? docs.filter((d) => Number(d.payment_id) === Number(p.id)) : docs;
  const use = attached.length ? attached : list;
  const licenseUrl = paymentLicenseUrl(p);
  return {
    id: p.id,
    reference: p.paystack_reference,
    amount_pesewas: p.amount_pesewas,
    amount_ghs: pesewasToGhsNumber(p.amount_pesewas),
    amount_label: formatGhs(p.amount_pesewas),
    currency: p.currency,
    duration_months: p.duration_months,
    status: p.status,
    channel: p.channel,
    paid_at: p.paid_at,
    period_from: p.period_from,
    period_until: p.period_until,
    period_label: p.period_from && p.period_until ? formatPeriodLabel(p.period_from, p.period_until) : null,
    period_title: p.period_from ? periodMonthTitle(p.period_from) : null,
    license_id: p.license_id,
    license_url: licenseUrl,
    can_retry: paymentCanRetry(p),
    notes: p.notes,
    created_at: p.created_at,
    invoice: serializeDoc(use.find((d) => d.doc_type === "invoice")),
    receipt: serializeDoc(use.find((d) => d.doc_type === "receipt")),
  };
}

function serializeCustomer(c, extra = {}) {
  if (!c) return null;
  return {
    id: c.id,
    hospital_name: c.hospital_name,
    facility_code: c.facility_code,
    amount_pesewas: c.amount_pesewas,
    amount_ghs: pesewasToGhsNumber(c.amount_pesewas),
    amount_label: formatGhs(c.amount_pesewas),
    duration_months: c.duration_months,
    currency: c.currency,
    notes: c.notes,
    status: c.status,
    billing_deadline: c.billing_deadline || null,
    billing_deadline_local: c.billing_deadline ? toDatetimeLocalValue(c.billing_deadline) : "",
    created_at: c.created_at,
    updated_at: c.updated_at,
    ...extra,
  };
}

function serializeLicense(row) {
  if (!row) return null;
  return {
    license_id: row.license_id,
    customer_label: row.customer_label,
    facility_code: row.facility_code,
    valid_from: row.valid_from,
    valid_until: row.valid_until,
    purchased_from: row.purchased_from || null,
    purchased_until: row.purchased_until || null,
  };
}

async function previewNextPeriod(customer) {
  const license = await getLicenseByCustomer(customer.id);
  try {
    const period = computePurchasedPeriod(
      license,
      customer.duration_months,
      utcNow(),
      [],
      customer.billing_deadline
    );
    return serializePeriod(period);
  } catch (err) {
    if (err.status === 400) return null;
    throw err;
  }
}

async function insertDocument(tx, { paymentId, customerId, docType, docNumber, filePath }) {
  const ts = nowSql();
  const rel = relativeDocumentPath(filePath);
  const inserted = await tx.query(
    `INSERT INTO documents (payment_id, customer_id, doc_type, doc_number, file_path, created_at)
     VALUES (?, ?, ?, ?, ?, ?)`,
    [paymentId, customerId, docType, docNumber, rel, ts]
  );
  return {
    id: inserted.insertId,
    payment_id: paymentId,
    customer_id: customerId,
    doc_type: docType,
    doc_number: docNumber,
    file_path: rel,
    created_at: ts,
  };
}

async function writeMissingPdf(doc, payment, customer, email) {
  const abs = documentAbsPath(doc.file_path);
  const fs = require("fs");
  if (fs.existsSync(abs) && fs.statSync(abs).size > 0) return;
  if (doc.doc_type === "invoice") {
    await writeInvoicePdf({
      filePath: abs,
      number: doc.doc_number,
      customer,
      email,
      payment,
      issuedAt: doc.created_at,
    });
  } else {
    await writeReceiptPdf({
      filePath: abs,
      number: doc.doc_number,
      customer,
      email,
      payment,
      paidAt: payment.paid_at,
      reference: payment.paystack_reference,
    });
  }
}

async function startPaystackCheckout(payment, customer, user, { rotateReference = false } = {}) {
  const email = user.email || (await customerLoginEmail(customer.id));
  let reference = payment.paystack_reference;
  let priorRefs = parsePriorRefs(payment.paystack_prior_refs);
  if (rotateReference && reference) {
    priorRefs = [...new Set([...priorRefs, reference])];
    reference = `LPV2-${randomUuid()}`;
    await getDb().query(
      `UPDATE payments
       SET paystack_reference = ?, paystack_prior_refs = ?, status = ?, notes = ?, updated_at = ?
       WHERE id = ?`,
      [reference, JSON.stringify(priorRefs), "pending", "Retry checkout", nowSql(), payment.id]
    );
  } else if (payment.status !== "pending") {
    await getDb().query("UPDATE payments SET status = ?, notes = ?, updated_at = ? WHERE id = ?", [
      "pending",
      "Retry checkout",
      nowSql(),
      payment.id,
    ]);
  }

  const callbackUrl = `${config.publicBaseUrl}/pay/return?reference=${encodeURIComponent(reference)}`;
  let paystackData;
  try {
    paystackData = await initializeTransaction({
      email,
      amountPesewas: payment.amount_pesewas || customer.amount_pesewas,
      reference,
      callbackUrl,
      metadata: {
        customer_id: customer.id,
        payment_id: payment.id,
        license_id: payment.license_id || null,
        retry: rotateReference || undefined,
      },
    });
  } catch (err) {
    await getDb().query("UPDATE payments SET status = ?, notes = ?, updated_at = ? WHERE id = ?", [
      "failed",
      err.message || "Paystack initialize failed",
      nowSql(),
      payment.id,
    ]);
    throw err;
  }

  await getDb().query("UPDATE payments SET paystack_access_code = ?, updated_at = ? WHERE id = ?", [
    paystackData.access_code || null,
    nowSql(),
    payment.id,
  ]);

  const docs = await documentsForPayment(payment.id);
  const { rows } = await getDb().query("SELECT * FROM payments WHERE id = ?", [payment.id]);
  return {
    authorization_url: paystackData.authorization_url,
    access_code: paystackData.access_code,
    reference,
    payment: serializePayment(rows[0], docs),
  };
}

async function retryPayment(payment, user) {
  if (!payment) throw httpError(404, "Payment not found");
  if (payment.status === "success") {
    throw httpError(400, "This payment already succeeded");
  }
  if (payment.channel === "manual") {
    throw httpError(400, "Manual issues cannot be retried through Paystack");
  }
  const customer = await getCustomer(payment.customer_id);
  if (!customer) throw httpError(404, "Hospital account not found");
  if (customer.status !== "active") {
    throw httpError(400, "This hospital account is not active");
  }

  const paidSame = await periodAlreadyPaid(customer.id, payment);
  if (paidSame) {
    throw httpError(400, "This month is already paid. Start the next payment from Pay with Paystack.");
  }

  const license = await getLicenseByCustomer(customer.id);
  const due = computePurchasedPeriod(
    license,
    customer.duration_months,
    utcNow(),
    [],
    customer.billing_deadline
  );
  if (payment.period_from && payment.period_until && !samePeriod(payment, due)) {
    throw httpError(
      400,
      `This checkout is for ${periodMonthTitle(payment.period_from) || "another month"}. Use Pay with Paystack for ${periodMonthTitle(due.validFrom)} first.`
    );
  }

  try {
    const data = await verifyTransaction(payment.paystack_reference);
    if (data && data.status === "success") {
      const fulfilled = await fulfillPayment(payment, data);
      return { fulfilled: true, authorization_url: null, ...fulfilled };
    }
  } catch (_) {
    /* abandoned / unknown reference — open a new Paystack checkout */
  }

  if (!payment.period_from || !payment.period_until) {
    await getDb().query("UPDATE payments SET period_from = ?, period_until = ?, updated_at = ? WHERE id = ?", [
      toSqlDatetime(due.validFrom),
      toSqlDatetime(due.validUntil),
      nowSql(),
      payment.id,
    ]);
    const { rows } = await getDb().query("SELECT * FROM payments WHERE id = ?", [payment.id]);
    payment = rows[0];
  }

  await failOtherPending(customer.id, payment.id);
  return startPaystackCheckout(payment, customer, user, { rotateReference: true });
}

async function periodAlreadyPaid(customerId, payment) {
  if (!payment.period_from || !payment.period_until) return false;
  const from = parseDatetime(payment.period_from);
  const until = parseDatetime(payment.period_until);
  if (!from || !until) return false;
  const { rows } = await getDb().query(
    `SELECT period_from, period_until FROM payments
     WHERE customer_id = ? AND status = 'success' AND id != ? AND period_from IS NOT NULL`,
    [customerId, payment.id]
  );
  return rows.some((row) => {
    const a = parseDatetime(row.period_from);
    const b = parseDatetime(row.period_until);
    return a && b && a.getTime() === from.getTime() && b.getTime() === until.getTime();
  });
}

async function findRetryableForPeriod(customerId, period) {
  const { rows } = await getDb().query(
    `SELECT * FROM payments
     WHERE customer_id = ? AND channel != 'manual' AND status IN ('pending', 'failed')
     ORDER BY id DESC`,
    [customerId]
  );
  return rows.find((p) => samePeriod(p, period)) || rows.find((p) => paymentCanRetry(p) && !p.period_from) || null;
}

async function createCheckout(customer, user) {
  if (customer.status !== "active") {
    throw httpError(400, "This hospital account is not active");
  }
  if (!customer.amount_pesewas || customer.amount_pesewas < 100) {
    throw httpError(400, "Amount is not set. Ask the issuer to set the GH₵ amount.");
  }
  const license = await getLicenseByCustomer(customer.id);
  const period = computePurchasedPeriod(
    license,
    customer.duration_months,
    utcNow(),
    [],
    customer.billing_deadline
  );
  const existing = await findRetryableForPeriod(customer.id, period);
  if (existing) {
    return retryPayment(existing, user);
  }

  await failOtherPending(customer.id);
  const ts = nowSql();
  const reference = `LPV2-${randomUuid()}`;

  const created = await getDb().withTransaction(async (tx) => {
    const inserted = await tx.query(
      `INSERT INTO payments
        (customer_id, license_id, paystack_reference, paystack_access_code, amount_pesewas, currency,
         duration_months, status, channel, paid_at, period_from, period_until, raw_payload, notes, created_at, updated_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      [
        customer.id,
        license ? license.license_id : null,
        reference,
        null,
        customer.amount_pesewas,
        customer.currency || "GHS",
        customer.duration_months,
        "pending",
        "paystack",
        null,
        toSqlDatetime(period.validFrom),
        toSqlDatetime(period.validUntil),
        null,
        null,
        ts,
        ts,
      ]
    );
    const paymentId = inserted.insertId;
    const invoiceNumber = await nextDocNumber(tx, "invoice");
    const filePath = path.join(config.documentsDir, `${invoiceNumber}.pdf`);
    await insertDocument(tx, {
      paymentId,
      customerId: customer.id,
      docType: "invoice",
      docNumber: invoiceNumber,
      filePath,
    });
    const { rows } = await tx.query("SELECT * FROM payments WHERE id = ?", [paymentId]);
    return { payment: rows[0], invoiceNumber, filePath };
  });

  await writeInvoicePdf({
    filePath: created.filePath,
    number: created.invoiceNumber,
    customer,
    email: user.email || (await customerLoginEmail(customer.id)),
    payment: created.payment,
    issuedAt: utcNow(),
  });

  return startPaystackCheckout(created.payment, customer, user, { rotateReference: false });
}

async function retryPaymentById(paymentId, user) {
  const payment = await getPaymentForUser(paymentId, user);
  if (!payment) throw httpError(404, "Payment not found");
  return retryPayment(payment, user);
}

async function fulfillByReference(reference, rawPayload) {
  const payment = await findPaymentByReference(reference);
  if (!payment) throw httpError(404, "Unknown payment reference");
  return fulfillPayment(payment, rawPayload);
}

async function fulfillPayment(payment, rawPayload) {
  const outcome = await getDb().withTransaction(async (tx) => {
    const lock = lockClause(tx);
    const { rows } = await tx.query(`SELECT * FROM payments WHERE id = ?${lock}`, [payment.id]);
    const row = rows[0];
    if (!row) throw httpError(404, "Payment not found");
    if (row.status === "success") {
      const license = await getLicenseByCustomer(row.customer_id, tx);
      const customer = await getCustomer(row.customer_id, tx);
      return { payment: row, customer, license, already: true };
    }

    const customer = await getCustomer(row.customer_id, tx);
    if (!customer) throw httpError(400, "Hospital account missing");
    if (rawPayload && rawPayload.amount != null && Number(rawPayload.amount) !== Number(row.amount_pesewas)) {
      throw httpError(400, "Paid amount does not match invoice");
    }
    let purchased = null;
    if (row.period_from && row.period_until) {
      purchased = {
        validFrom: parseDatetime(row.period_from),
        validUntil: parseDatetime(row.period_until),
      };
      const existingLic = await getLicenseByCustomer(row.customer_id, tx);
      if (existingLic) {
        const until = parseDatetime(existingLic.valid_until);
        if (until && purchased.validUntil && until >= purchased.validUntil) {
          purchased = computePurchasedPeriod(
            existingLic,
            row.duration_months,
            utcNow(),
            [],
            customer.billing_deadline
          );
        }
      }
    }
    const license = await extendLicenseForCustomer(tx, customer, row.duration_months, utcNow(), purchased);
    const ts = nowSql();
    const payload = rawPayload ? JSON.stringify(rawPayload) : row.raw_payload;
    const periodFrom = license.purchased_from || row.period_from;
    const periodUntil = license.purchased_until || row.period_until;
    await tx.query(
      `UPDATE payments
       SET status = ?, paid_at = ?, license_id = ?, raw_payload = ?, period_from = ?, period_until = ?, updated_at = ?
       WHERE id = ?`,
      ["success", ts, license.license_id, payload, periodFrom, periodUntil, ts, row.id]
    );

    const receiptNumber = await nextDocNumber(tx, "receipt");
    const filePath = path.join(config.documentsDir, `${receiptNumber}.pdf`);
    await insertDocument(tx, {
      paymentId: row.id,
      customerId: customer.id,
      docType: "receipt",
      docNumber: receiptNumber,
      filePath,
    });

    return {
      payment: {
        ...row,
        status: "success",
        paid_at: ts,
        license_id: license.license_id,
        raw_payload: payload,
        period_from: periodFrom,
        period_until: periodUntil,
      },
      customer,
      license,
      already: false,
    };
  });

  const email = await customerLoginEmail(outcome.customer.id);
  const docs = await documentsForPayment(outcome.payment.id);
  for (const doc of docs) {
    await writeMissingPdf(doc, outcome.payment, outcome.customer, email);
  }
  return {
    already: outcome.already,
    payment: serializePayment(outcome.payment, docs),
    license: serializeLicense(outcome.license),
    customer: serializeCustomer(outcome.customer),
  };
}

async function verifyAndFulfill(reference) {
  const data = await verifyTransaction(reference);
  if (!data || data.status !== "success") {
    const payment = await findPaymentByReference(reference);
    if (payment && payment.status === "success") {
      return fulfillByReference(reference, null);
    }
    return {
      payment: payment ? serializePayment(payment, await documentsForPayment(payment.id)) : null,
      pending: true,
      paystack_status: data && data.status,
    };
  }
  const paidAmount = Number(data.amount);
  const payment = await findPaymentByReference(reference);
  if (!payment) throw httpError(404, "Unknown payment reference");
  if (paidAmount && paidAmount !== Number(payment.amount_pesewas)) {
    throw httpError(400, "Paid amount does not match invoice");
  }
  return fulfillPayment(payment, data);
}

async function getPaymentStatus(reference) {
  const payment = await findPaymentByReference(reference);
  if (!payment) throw httpError(404, "Unknown payment reference");
  if (payment.status === "success") {
    const docs = await documentsForPayment(payment.id);
    const license = await getLicenseByCustomer(payment.customer_id);
    return { payment: serializePayment(payment, docs), license: serializeLicense(license), pending: false };
  }
  try {
    return await verifyAndFulfill(reference);
  } catch (err) {
    if (err.status === 400 || err.status === 404) throw err;
    const docs = await documentsForPayment(payment.id);
    return { payment: serializePayment(payment, docs), pending: true, error: err.message };
  }
}

async function issueManual(customer, { notes, email } = {}) {
  if (!customer.amount_pesewas || customer.amount_pesewas < 100) {
    throw httpError(400, "Set a GH₵ amount before issuing a license");
  }
  const reference = `MANUAL-${randomUuid()}`;
  const ts = nowSql();

  const created = await getDb().withTransaction(async (tx) => {
    await tx.query(
      `UPDATE payments SET status = ?, notes = ?, updated_at = ?
       WHERE customer_id = ? AND status = ?`,
      ["failed", "Superseded by a manual issue", ts, customer.id, "pending"]
    );
    const current = await getLicenseByCustomer(customer.id, tx);
    const period = computePurchasedPeriod(
      current,
      customer.duration_months,
      utcNow(),
      [],
      customer.billing_deadline
    );
    const license = await extendLicenseForCustomer(tx, customer, customer.duration_months, utcNow(), period);
    const inserted = await tx.query(
      `INSERT INTO payments
        (customer_id, license_id, paystack_reference, paystack_access_code, amount_pesewas, currency,
         duration_months, status, channel, paid_at, period_from, period_until, raw_payload, notes, created_at, updated_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      [
        customer.id,
        license.license_id,
        reference,
        null,
        customer.amount_pesewas,
        customer.currency || "GHS",
        customer.duration_months,
        "success",
        "manual",
        ts,
        toSqlDatetime(period.validFrom),
        toSqlDatetime(period.validUntil),
        null,
        notes || "Issued without Paystack",
        ts,
        ts,
      ]
    );
    const paymentId = inserted.insertId;
    const invoiceNumber = await nextDocNumber(tx, "invoice");
    const receiptNumber = await nextDocNumber(tx, "receipt");
    const invoicePath = path.join(config.documentsDir, `${invoiceNumber}.pdf`);
    const receiptPath = path.join(config.documentsDir, `${receiptNumber}.pdf`);
    await insertDocument(tx, {
      paymentId,
      customerId: customer.id,
      docType: "invoice",
      docNumber: invoiceNumber,
      filePath: invoicePath,
    });
    await insertDocument(tx, {
      paymentId,
      customerId: customer.id,
      docType: "receipt",
      docNumber: receiptNumber,
      filePath: receiptPath,
    });
    const { rows } = await tx.query("SELECT * FROM payments WHERE id = ?", [paymentId]);
    return { payment: rows[0], license, invoicePath, receiptPath, invoiceNumber, receiptNumber };
  });

  const loginEmail = email || (await customerLoginEmail(customer.id));
  await writeInvoicePdf({
    filePath: created.invoicePath,
    number: created.invoiceNumber,
    customer,
    email: loginEmail,
    payment: created.payment,
    issuedAt: utcNow(),
  });
  await writeReceiptPdf({
    filePath: created.receiptPath,
    number: created.receiptNumber,
    customer,
    email: loginEmail,
    payment: created.payment,
    paidAt: created.payment.paid_at,
    reference,
  });

  const docs = await documentsForPayment(created.payment.id);
  return {
    payment: serializePayment(created.payment, docs),
    license: serializeLicense(created.license),
  };
}

async function getPaymentForUser(paymentId, user) {
  const { rows } = await getDb().query("SELECT * FROM payments WHERE id = ?", [paymentId]);
  const payment = rows[0];
  if (!payment) return null;
  if (user.role !== "admin" && Number(user.customer_id) !== Number(payment.customer_id)) {
    throw httpError(403, "Not allowed");
  }
  return payment;
}

async function signedLicenseForPayment(payment) {
  if (!payment) throw httpError(404, "Payment not found");
  if (payment.status !== "success") {
    throw httpError(400, "License file is available after payment succeeds.");
  }
  if (!payment.period_from || !payment.period_until) {
    throw httpError(400, "This payment has no coverage period.");
  }
  const license = await getLicenseByCustomer(payment.customer_id);
  if (!license) throw httpError(404, "No license record for this hospital.");
  return {
    document: signedDocumentFor(license, {
      period_from: payment.period_from,
      period_until: payment.period_until,
    }),
    filename: paymentLicenseFilename(payment),
  };
}

async function getDocumentForUser(docId, user) {
  const { rows } = await getDb().query("SELECT * FROM documents WHERE id = ?", [docId]);
  const doc = rows[0];
  if (!doc) return null;
  if (user.role !== "admin" && Number(user.customer_id) !== Number(doc.customer_id)) {
    const err = httpError(403, "Not allowed");
    throw err;
  }
  return doc;
}

async function refreshDocumentPdf(doc) {
  const { rows } = await getDb().query("SELECT * FROM payments WHERE id = ?", [doc.payment_id]);
  const payment = rows[0];
  if (!payment) return;
  const customer = await getCustomer(payment.customer_id);
  const email = await customerLoginEmail(payment.customer_id);
  const abs = documentAbsPath(doc.file_path);
  if (doc.doc_type === "invoice") {
    await writeInvoicePdf({
      filePath: abs,
      number: doc.doc_number,
      customer,
      email,
      payment,
      issuedAt: doc.created_at,
    });
  } else if (doc.doc_type === "receipt") {
    await writeReceiptPdf({
      filePath: abs,
      number: doc.doc_number,
      customer,
      email,
      payment,
      paidAt: payment.paid_at,
      reference: payment.paystack_reference,
    });
  }
}

module.exports = {
  httpError,
  getCustomer,
  customerLoginEmail,
  documentsForPayment,
  serializeDoc,
  serializePayment,
  serializeCustomer,
  serializeLicense,
  createCheckout,
  retryPaymentById,
  fulfillByReference,
  fulfillPayment,
  verifyAndFulfill,
  getPaymentStatus,
  issueManual,
  getPaymentForUser,
  signedLicenseForPayment,
  getDocumentForUser,
  refreshDocumentPdf,
  previewNextPeriod,
  findPaymentByReference,
  latestPaidPayment,
  signedDocumentFor,
};
