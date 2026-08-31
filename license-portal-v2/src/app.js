const path = require("path");
const express = require("express");
const cookieParser = require("cookie-parser");
const { config } = require("./config");
const { initDb } = require("./db");
const { seedAdmin } = require("./auth");
const { mountRoutes, mountWebhook, errorHandler } = require("./routes");

async function createApp() {
  await initDb();
  await seedAdmin();

  const app = express();
  app.set("trust proxy", 1);
  app.disable("x-powered-by");

  mountWebhook(app);
  app.use(express.json({ limit: "4mb" }));
  app.use(express.urlencoded({ extended: false }));
  app.use(cookieParser());

  mountRoutes(app);

  const publicDir = path.join(config.ROOT, "public");
  app.use(express.static(publicDir));
  app.get("/", (req, res) => res.sendFile(path.join(publicDir, "index.html")));
  app.get("/admin", (req, res) => res.sendFile(path.join(publicDir, "admin.html")));
  app.get("/dashboard", (req, res) => res.sendFile(path.join(publicDir, "dashboard.html")));
  app.get("/profile", (req, res) => res.sendFile(path.join(publicDir, "profile.html")));
  app.get("/pay/return", (req, res) => res.sendFile(path.join(publicDir, "pay-return.html")));
  app.get("/verify", (req, res) => res.sendFile(path.join(publicDir, "verify.html")));
  app.get("/verify/:docNumber", (req, res) => res.sendFile(path.join(publicDir, "verify.html")));

  app.use(errorHandler);
  return app;
}

module.exports = { createApp };
