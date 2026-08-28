const crypto = require("crypto");
const { config } = require("./config");

const PAYSTACK_BASE = "https://api.paystack.co";

function requirePaystackSecret() {
  if (!config.paystackSecretKey) {
    const err = new Error("PAYSTACK_SECRET_KEY is not configured");
    err.status = 503;
    throw err;
  }
  return config.paystackSecretKey;
}

async function paystackRequest(pathname, { method = "GET", body } = {}) {
  const secret = requirePaystackSecret();
  const res = await fetch(`${PAYSTACK_BASE}${pathname}`, {
    method,
    headers: {
      Authorization: `Bearer ${secret}`,
      "Content-Type": "application/json",
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  const json = await res.json().catch(() => ({}));
  if (!res.ok || json.status === false) {
    const err = new Error((json && json.message) || `Paystack error (${res.status})`);
    err.status = 400;
    err.payload = json;
    throw err;
  }
  return json;
}

async function initializeTransaction({ email, amountPesewas, reference, callbackUrl, metadata }) {
  const json = await paystackRequest("/transaction/initialize", {
    method: "POST",
    body: {
      email,
      amount: amountPesewas,
      currency: "GHS",
      reference,
      callback_url: callbackUrl,
      metadata,
      channels: ["card", "mobile_money", "ussd", "bank", "qr"],
    },
  });
  return json.data;
}

async function verifyTransaction(reference) {
  const json = await paystackRequest(`/transaction/verify/${encodeURIComponent(reference)}`);
  return json.data;
}

function verifyWebhookSignature(rawBody, signatureHeader) {
  const secret = requirePaystackSecret();
  const hash = crypto.createHmac("sha512", secret).update(rawBody).digest("hex");
  const given = String(signatureHeader || "").trim();
  if (!given || given.length !== hash.length) return false;
  try {
    return crypto.timingSafeEqual(Buffer.from(hash, "utf8"), Buffer.from(given, "utf8"));
  } catch (_) {
    return false;
  }
}

module.exports = {
  initializeTransaction,
  verifyTransaction,
  verifyWebhookSignature,
};
