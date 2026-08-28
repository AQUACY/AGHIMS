const path = require("path");
const fs = require("fs");
require("dotenv").config({ path: path.join(__dirname, "..", ".env") });

function env(name, fallback = "") {
  const v = process.env[name];
  return v === undefined || v === null ? fallback : String(v);
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

const config = {
  ROOT,
  databaseMode: env("DATABASE_MODE", "sqlite").toLowerCase(),
  sqlitePath: path.resolve(ROOT, env("SQLITE_DB_PATH", "./data/license_portal_v2.db")),
  mysql: {
    host: env("MYSQL_HOST", "localhost"),
    port: envInt("MYSQL_PORT", 3306),
    user: env("MYSQL_USER", "root"),
    password: env("MYSQL_PASSWORD", ""),
    database: env("MYSQL_DATABASE", "hms_licenses_v2"),
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
  dataDir: path.join(ROOT, "data"),
  documentsDir: path.join(ROOT, "data", "documents"),
  brandingDir: path.join(ROOT, "data", "branding"),
};

function resolvedPrivateKeyPem() {
  const file = config.rsaPrivateKeyFile;
  if (file) {
    const abs = path.isAbsolute(file) ? file : path.resolve(ROOT, file);
    return fs.readFileSync(abs, "utf8").trim();
  }
  return (config.rsaPrivateKeyPem || "").trim();
}

module.exports = { config, resolvedPrivateKeyPem };
