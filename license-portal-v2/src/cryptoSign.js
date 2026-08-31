/**
 * RSA-SHA256 PKCS#1 v1.5 signing matching license-portal/app/crypto_sign.py
 *
 * Canonical message: JSON with sorted keys, compact separators, Python
 * json.dumps(ensure_ascii=True) compatible Unicode escaping.
 */
const crypto = require("crypto");

function sortKeys(value) {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    return value;
  }
  const out = {};
  for (const key of Object.keys(value).sort()) {
    if (value[key] === undefined) continue;
    out[key] = sortKeys(value[key]);
  }
  return out;
}

function pythonAsciiEscape(json) {
  return json.replace(/[\u007f-\uffff]/g, (ch) => {
    const hex = ch.charCodeAt(0).toString(16).padStart(4, "0");
    return `\\u${hex}`;
  });
}

function canonicalClaimsBytes(claims) {
  const json = pythonAsciiEscape(JSON.stringify(sortKeys(claims)));
  return Buffer.from(json, "utf8");
}

function signClaims(claims, privateKeyPem) {
  const pem = (privateKeyPem || "").trim();
  if (!pem) throw new Error("Missing RSA private key PEM");
  const key = crypto.createPrivateKey(pem);
  const sig = crypto.sign("sha256", canonicalClaimsBytes(claims), {
    key,
    padding: crypto.constants.RSA_PKCS1_PADDING,
  });
  return sig.toString("base64");
}

function buildSignedDocument(claims, privateKeyPem) {
  return { claims, signature_b64: signClaims(claims, privateKeyPem) };
}

function verifyDocument(document, publicKeyPem) {
  if (!document || typeof document !== "object") {
    return { ok: false, error: "License file must be a JSON object" };
  }
  const claims = document.claims;
  const sigB64 = document.signature_b64;
  if (!claims || typeof claims !== "object") {
    return { ok: false, error: "Missing or invalid claims" };
  }
  if (!sigB64 || typeof sigB64 !== "string") {
    return { ok: false, error: "Missing signature_b64" };
  }
  const key = crypto.createPublicKey((publicKeyPem || "").trim());
  const ok = crypto.verify(
    "sha256",
    canonicalClaimsBytes(claims),
    { key, padding: crypto.constants.RSA_PKCS1_PADDING },
    Buffer.from(sigB64, "base64")
  );
  return ok ? { ok: true, claims } : { ok: false, error: "Signature verification failed" };
}

function generateKeyPairPem() {
  const { publicKey, privateKey } = crypto.generateKeyPairSync("rsa", {
    modulusLength: 2048,
    publicKeyEncoding: { type: "spki", format: "pem" },
    privateKeyEncoding: { type: "pkcs1", format: "pem" },
  });
  return { publicKey, privateKey };
}

function selftest() {
  const { publicKey, privateKey } = generateKeyPairPem();
  const claims = {
    v: 1,
    license_id: "abc-123",
    customer_label: "Test Hospital",
    facility_code: "FAC1",
    valid_from: "2026-01-01T00:00:00Z",
    valid_until: "2027-01-01T00:00:00Z",
    issuer_slug: "test-issuer",
  };
  const doc = buildSignedDocument(claims, privateKey);
  const checked = verifyDocument(doc, publicKey);
  if (!checked.ok) {
    throw new Error(`selftest failed: ${checked.error}`);
  }
  const canon = canonicalClaimsBytes(claims).toString("utf8");
  const expected =
    '{"customer_label":"Test Hospital","facility_code":"FAC1","issuer_slug":"test-issuer","license_id":"abc-123","v":1,"valid_from":"2026-01-01T00:00:00Z","valid_until":"2027-01-01T00:00:00Z"}';
  if (canon !== expected) {
    throw new Error(`canonical mismatch:\n${canon}\n${expected}`);
  }
  const unicode = canonicalClaimsBytes({ name: "café" }).toString("utf8");
  if (unicode !== '{"name":"caf\\u00e9"}') {
    throw new Error(`unicode escape mismatch: ${unicode}`);
  }
  console.log("cryptoSign selftest ok");
}

if (require.main === module && process.argv.includes("--selftest")) {
  selftest();
}

module.exports = {
  canonicalClaimsBytes,
  signClaims,
  buildSignedDocument,
  verifyDocument,
  generateKeyPairPem,
  selftest,
};
