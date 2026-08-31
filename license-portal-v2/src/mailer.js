const nodemailer = require("nodemailer");
const { config } = require("./config");

const capturedMails = [];

function smtpConfigured() {
  if (config.smtp.testMode) return true;
  return Boolean(config.smtp.host && (config.smtp.user || config.smtp.from || config.company.email));
}

function fromAddress() {
  if (config.smtp.from) return config.smtp.from;
  const email = (config.company.email || config.smtp.user || "").trim();
  const name = (config.company.name || "License Portal").replace(/"/g, "");
  if (email) return `"${name}" <${email}>`;
  return name;
}

let transport = null;

function getTransport() {
  if (transport) return transport;
  if (config.smtp.testMode) {
    transport = nodemailer.createTransport({ jsonTransport: true });
    return transport;
  }
  if (!config.smtp.host) {
    const err = new Error("SMTP is not configured. Set SMTP_HOST, SMTP_USER, and SMTP_PASS.");
    err.status = 503;
    throw err;
  }
  transport = nodemailer.createTransport({
    host: config.smtp.host,
    port: config.smtp.port,
    secure: config.smtp.secure,
    auth: config.smtp.user
      ? {
          user: config.smtp.user,
          pass: config.smtp.pass,
        }
      : undefined,
  });
  return transport;
}

async function sendMail({ to, subject, text, html, kind }) {
  if (!to) {
    const err = new Error("No recipient email.");
    err.status = 400;
    throw err;
  }
  const payload = {
    from: fromAddress(),
    to,
    replyTo: config.company.email || undefined,
    subject,
    text,
    html,
  };
  capturedMails.push({
    to,
    subject,
    text,
    html,
    kind: kind || null,
    at: new Date().toISOString(),
  });
  const info = await getTransport().sendMail(payload);
  return { messageId: info && info.messageId, test: config.smtp.testMode };
}

module.exports = {
  smtpConfigured,
  fromAddress,
  sendMail,
  capturedMails,
};
