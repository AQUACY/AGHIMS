const crypto = require("crypto");
const bcrypt = require("bcryptjs");
const jwt = require("jsonwebtoken");
const { config } = require("./config");
const { getDb, nowSql } = require("./db");

const COOKIE = "portal_token";
const SALT_ROUNDS = 10;

function hashPassword(plain) {
  return bcrypt.hashSync(plain, SALT_ROUNDS);
}

function verifyPassword(plain, hash) {
  return bcrypt.compareSync(plain || "", hash || "");
}

function createToken(user) {
  const exp = Math.floor(Date.now() / 1000) + Math.max(15, config.jwtExpireMinutes) * 60;
  return jwt.sign({ sub: String(user.id), role: user.role, email: user.email, exp }, config.jwtSecret);
}

function cookieOptions() {
  return {
    httpOnly: true,
    sameSite: "lax",
    secure: config.cookieSecure,
    maxAge: Math.max(15, config.jwtExpireMinutes) * 60 * 1000,
    path: "/",
  };
}

function setAuthCookie(res, token) {
  res.cookie(COOKIE, token, cookieOptions());
}

function clearAuthCookie(res) {
  res.clearCookie(COOKIE, { ...cookieOptions(), maxAge: 0 });
}

function readToken(req) {
  const cookie = req.cookies && req.cookies[COOKIE];
  if (cookie) return cookie;
  const header = req.headers.authorization || "";
  if (header.toLowerCase().startsWith("bearer ")) {
    return header.slice(7).trim();
  }
  return "";
}

function decodeToken(token) {
  return jwt.verify(token, config.jwtSecret);
}

function generatePassword(length = 12) {
  const alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789";
  const bytes = crypto.randomBytes(length);
  let out = "";
  for (let i = 0; i < length; i += 1) {
    out += alphabet[bytes[i] % alphabet.length];
  }
  return out;
}

async function seedAdmin() {
  const db = getDb();
  const existing = await db.query("SELECT id FROM users WHERE role = ? LIMIT 1", ["admin"]);
  if (existing.rows.length) return;
  if (!config.adminPassword) {
    console.warn("PORTAL_ADMIN_PASSWORD is not set; skipping admin seed");
    return;
  }
  const email = (config.adminEmail || "license_admin").trim().toLowerCase();
  await db.query(
    "INSERT INTO users (email, password_hash, role, customer_id, created_at) VALUES (?, ?, ?, ?, ?)",
    [email, hashPassword(config.adminPassword), "admin", null, nowSql()]
  );
  console.log(`Seeded admin user: ${email}`);
}

async function loadUser(id) {
  const db = getDb();
  const { rows } = await db.query("SELECT id, email, password_hash, role, customer_id, created_at FROM users WHERE id = ?", [
    id,
  ]);
  return rows[0] || null;
}

async function findUserByEmail(email) {
  const db = getDb();
  const { rows } = await db.query(
    "SELECT id, email, password_hash, role, customer_id, created_at FROM users WHERE email = ?",
    [String(email || "").trim().toLowerCase()]
  );
  return rows[0] || null;
}

function publicUser(user) {
  if (!user) return null;
  return {
    id: user.id,
    email: user.email,
    role: user.role,
    customer_id: user.customer_id,
  };
}

async function authRequired(req, res, next) {
  try {
    const token = readToken(req);
    if (!token) {
      return res.status(401).json({ error: "Not signed in" });
    }
    const payload = decodeToken(token);
    const user = await loadUser(payload.sub);
    if (!user) {
      return res.status(401).json({ error: "Invalid token" });
    }
    req.user = user;
    return next();
  } catch (err) {
    return res.status(401).json({ error: "Invalid or expired token" });
  }
}

function adminRequired(req, res, next) {
  if (!req.user || req.user.role !== "admin") {
    return res.status(403).json({ error: "Admin only" });
  }
  return next();
}

function customerRequired(req, res, next) {
  if (!req.user || req.user.role !== "customer") {
    return res.status(403).json({ error: "Customer account required" });
  }
  return next();
}

async function changeOwnPassword(user, currentPassword, newPassword) {
  if (!verifyPassword(currentPassword, user.password_hash)) {
    const err = new Error("Current password is incorrect");
    err.status = 400;
    throw err;
  }
  const next = String(newPassword || "");
  if (next.length < 8) {
    const err = new Error("New password must be at least 8 characters");
    err.status = 400;
    throw err;
  }
  if (next === String(currentPassword || "")) {
    const err = new Error("New password must be different from the current password");
    err.status = 400;
    throw err;
  }
  await getDb().query("UPDATE users SET password_hash = ? WHERE id = ?", [hashPassword(next), user.id]);
}

module.exports = {
  COOKIE,
  hashPassword,
  verifyPassword,
  createToken,
  setAuthCookie,
  clearAuthCookie,
  generatePassword,
  seedAdmin,
  loadUser,
  findUserByEmail,
  publicUser,
  authRequired,
  adminRequired,
  customerRequired,
  changeOwnPassword,
};
