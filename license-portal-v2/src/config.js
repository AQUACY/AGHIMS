const path = require("path");
const fs = require("fs");
require("dotenv").config({ path: path.join(__dirname, "..", ".env") });

function env(name, fallback = "") {
  const v = process.env[name];
  return v === undefined || v === null ? fallback : String(v);
}

function unquote(value) {
  let s = String(value || "").replace(/^\uFEFF/, "").trim();
  s = s.replace(/[\u200B-\u200D\uFEFF]/g, "");
  if ((s.startsWith('"') && s.endsWith('"')) || (s.startsWith("'") && s.endsWith("'"))) {
    s = s.slice(1, -1).trim();
  }
  return s.replace(/[\r\n\t]/g, "");
}

function mysqlHost(raw) {
  const host = unquote(raw) || "localhost";
  // Node resolves "localhost" to IPv6 ::1 first. Hostinger MySQL users are
  // typically user@localhost / user@127.0.0.1, not user@::1.
  if (host.toLowerCase() === "localhost") return "127.0.0.1";
  return host;
}

function envInt(name, fallback) {
  const n = parseInt(env(name, String(fallback)), 10);
  return Number.isFinite(n) ? n : fallback;
}

function envBool(name, fallback = false) {
  const v = env(name, "").trim().toLowerCase();
  if (!v) return fallback;
  return v === "1" || v === "true" || v === "yes";
}

const ROOT = path.join(__dirname, "..");
const PUBLIC_BASE_URL = env("PUBLIC_BASE_URL", "http://127.0.0.1:9500").replace(/\/$/, "");

function hostingerPersistentAppRoot(buildRoot) {
  const resolved = path.resolve(buildRoot);
  const match = resolved.match(/^(.*)[/\\]hbuilds[/\\]versions[/\\][^/\\]+[/\\]?nodejs$/i);
  if (!match) return "";
  return path.join(match[1], "nodejs");
}

const PERSISTENT_ROOT = hostingerPersistentAppRoot(ROOT);
const DATA_ROOT =
  PERSISTENT_ROOT && fs.existsSync(PERSISTENT_ROOT) ? PERSISTENT_ROOT : ROOT;

const config = {
  ROOT,
  databaseMode: env("DATABASE_MODE", "sqlite").toLowerCase(),
  sqlitePath: path.resolve(ROOT, env("SQLITE_DB_PATH", "./data/license_portal_v2.db")),
  mysql: {
    host: mysqlHost(env("MYSQL_HOST", "localhost")),
    port: envInt("MYSQL_PORT", 3306),
    user: unquote(env("MYSQL_USER", "root")),
    password: unquote(env("MYSQL_PASSWORD", "")),
    database: unquote(env("MYSQL_DATABASE", "hms_licenses_v2")),
    socketPath: unquote(env("MYSQL_SOCKET", "")),
  },
  issuerSlug: env("ISSUER_SLUG", "").trim(),
  distributionId: env("DISTRIBUTION_ID", "").trim(),
  rsaPrivateKeyFile: env("RSA_PRIVATE_KEY_FILE", "").trim(),
  rsaPrivateKeyPem: env("RSA_PRIVATE_KEY_PEM", "").trim(),
  verifySharedSecret: env("VERIFY_SHARED_SECRET", "").trim(),
  adminEmail: env("PORTAL_ADMIN_EMAIL", env("PORTAL_ADMIN_USERNAME", "license_admin")).trim(),
  adminPassword: env("PORTAL_ADMIN_PASSWORD", ""),
  jwtSecret: env("PORTAL_JWT_SECRET", "change-portal-jwt"),
  jwtExpireMinutes: envInt("PORTAL_JWT_EXPIRE_MINUTES", 480),
  publicBaseUrl: PUBLIC_BASE_URL,
  paystackSecretKey: env("PAYSTACK_SECRET_KEY", "").trim(),
  paystackPublicKey: env("PAYSTACK_PUBLIC_KEY", "").trim(),
  company: {
    name: env("COMPANY_NAME", "License Portal"),
    address: env("COMPANY_ADDRESS", ""),
    phone: env("COMPANY_PHONE", ""),
    email: env("COMPANY_EMAIL", ""),
    tin: env("COMPANY_TIN", ""),
  },
  cookieSecure: env("COOKIE_SECURE", "")
    ? envBool("COOKIE_SECURE", false)
    : PUBLIC_BASE_URL.startsWith("https://"),
  host: env("HOST", "0.0.0.0"),
  port: envInt("PORT", 9500),
  dataDir: path.join(DATA_ROOT, "data"),
  documentsDir: path.join(DATA_ROOT, "data", "documents"),
  brandingDir: path.join(DATA_ROOT, "data", "branding"),
};

function privateKeyFileCandidates() {
  const file = unquote(config.rsaPrivateKeyFile);
  const base = file ? path.basename(file) : "license_private.pem";
  const out = [];
  const add = (p) => {
    if (p && !out.includes(p)) out.push(p);
  };
  if (file) {
    add(path.isAbsolute(file) ? file : path.resolve(ROOT, file));
  }
  add(path.resolve(ROOT, base));
  if (PERSISTENT_ROOT) add(path.join(PERSISTENT_ROOT, base));
  if (process.env.HOME) add(path.join(process.env.HOME, base));
  add(path.join(ROOT, "license_private.pem"));
  return out;
}

let cachedPrivateKeyPem = "";

function resolvedPrivateKeyPem() {
  if (cachedPrivateKeyPem) return cachedPrivateKeyPem;
  const inline = (config.rsaPrivateKeyPem || "").trim();
  if (/BEGIN [A-Z ]*PRIVATE KEY/.test(inline)) {
    cachedPrivateKeyPem = inline;
    return cachedPrivateKeyPem;
  }
  const tried = [];
  for (const abs of privateKeyFileCandidates()) {
    tried.push(abs);
    try {
      if (fs.existsSync(abs) && fs.statSync(abs).isFile()) {
        cachedPrivateKeyPem = fs.readFileSync(abs, "utf8").trim();
        console.log(`RSA private key loaded from ${abs}`);
        return cachedPrivateKeyPem;
      }
    } catch (_) {
      /* try next */
    }
  }
  const hint = PERSISTENT_ROOT
    ? path.join(PERSISTENT_ROOT, "license_private.pem")
    : "/home/USER/domains/YOUR_DOMAIN/nodejs/license_private.pem";
  throw new Error(
    `RSA private key not found. Upload license_private.pem to ${hint} ` +
      `(outside hbuilds) and set RSA_PRIVATE_KEY_FILE to that absolute path, or set RSA_PRIVATE_KEY_PEM. ` +
      `Tried: ${tried.join(", ")}`
  );
}

module.exports = { config, resolvedPrivateKeyPem };
