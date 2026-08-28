const fs = require("fs");
const path = require("path");
const PDFDocument = require("pdfkit");
const { config } = require("./config");
const { formatGhs, formatPeriodLabel } = require("./dates");

const FONT_REG = path.join(config.ROOT, "fonts", "NotoSans-Regular.ttf");
const FONT_BOLD = path.join(config.ROOT, "fonts", "NotoSans-Bold.ttf");

function letterhead() {
  return {
    name: (process.env.COMPANY_NAME || "").trim() || "License Portal",
    address: (process.env.COMPANY_ADDRESS || "").trim(),
    phone: (process.env.COMPANY_PHONE || "").trim(),
    email: (process.env.COMPANY_EMAIL || "").trim(),
    tin: (process.env.COMPANY_TIN || "").trim(),
  };
}

function ensureDir(filePath) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
}

function registerFonts(doc) {
  if (fs.existsSync(FONT_REG)) doc.registerFont("Body", FONT_REG);
  if (fs.existsSync(FONT_BOLD)) doc.registerFont("BodyBold", FONT_BOLD);
  const body = fs.existsSync(FONT_REG) ? "Body" : "Times-Roman";
  const bold = fs.existsSync(FONT_BOLD) ? "BodyBold" : fs.existsSync(FONT_REG) ? "Body" : "Times-Bold";
  return { body, bold };
}

function writePdf(filePath, draw) {
  ensureDir(filePath);
  return new Promise((resolve, reject) => {
    const doc = new PDFDocument({ size: "A4", margin: 56 });
    const stream = fs.createWriteStream(filePath);
    doc.pipe(stream);
    try {
      draw(doc);
      doc.end();
    } catch (err) {
      reject(err);
      return;
    }
    stream.on("finish", () => resolve(filePath));
    stream.on("error", reject);
  });
}

function header(doc, fonts, title, number, dateLabel) {
  const company = letterhead();
  const { pdfLogoPath } = require("./branding");
  const logoPath = pdfLogoPath();
  let nameX = 56;
  let nameWidth = 300;
  if (logoPath) {
    try {
      doc.image(logoPath, 56, 48, { fit: [52, 52] });
      nameX = 118;
      nameWidth = 238;
    } catch (_) {
      nameX = 56;
      nameWidth = 300;
    }
  }
  doc.fillColor("#14213d").font(fonts.bold).fontSize(18).text(company.name || "License Portal", nameX, 56, {
    width: nameWidth,
  });
  doc.font(fonts.body).fontSize(9).fillColor("#4a4a4a");
  const lines = [company.address, company.phone, company.email].filter(Boolean);
  if (company.tin) lines.push(`TIN: ${company.tin}`);
  doc.text(lines.join("\n"), nameX, 82, { width: nameWidth });

  doc.fillColor("#14213d").font(fonts.bold).fontSize(16).text(title, 340, 56, { width: 200, align: "right" });
  doc.font(fonts.body).fontSize(10).fillColor("#333");
  doc.text(number, 340, 80, { width: 200, align: "right" });
  doc.text(dateLabel, 340, 96, { width: 200, align: "right" });

  doc.moveTo(56, 140).lineTo(539, 140).strokeColor("#c4a35a").lineWidth(1.5).stroke();
}

function billTo(doc, fonts, customer, userEmail) {
  doc.fillColor("#14213d").font(fonts.bold).fontSize(10).text("BILL TO", 56, 158);
  doc.font(fonts.body).fontSize(11).fillColor("#222");
  const bits = [customer.hospital_name];
  if (customer.facility_code) bits.push(`Facility code: ${customer.facility_code}`);
  if (userEmail) bits.push(userEmail);
  doc.text(bits.join("\n"), 56, 174, { width: 400 });
}

function lineTable(doc, fonts, y, durationMonths, amountPesewas, periodLabel) {
  doc.moveTo(56, y).lineTo(539, y).strokeColor("#ddd").lineWidth(0.5).stroke();
  doc.fillColor("#666").font(fonts.bold).fontSize(9);
  doc.text("DESCRIPTION", 56, y + 8);
  doc.text("COVERAGE", 250, y + 8);
  doc.text("AMOUNT", 450, y + 8, { width: 89, align: "right" });
  doc.moveTo(56, y + 24).lineTo(539, y + 24).strokeColor("#ddd").stroke();

  doc.fillColor("#222").font(fonts.body).fontSize(9);
  doc.text("HMS software license renewal", 56, y + 36, { width: 190 });
  doc.text(periodLabel || `${durationMonths} month${durationMonths === 1 ? "" : "s"}`, 250, y + 36, { width: 190 });
  doc.font(fonts.bold).text(formatGhs(amountPesewas), 430, y + 36, { width: 109, align: "right" });

  doc.moveTo(56, y + 78).lineTo(539, y + 78).strokeColor("#c4a35a").lineWidth(1).stroke();
  doc.font(fonts.bold).fontSize(12).fillColor("#14213d");
  doc.text("Total", 320, y + 90);
  doc.text(formatGhs(amountPesewas), 430, y + 90, { width: 109, align: "right" });
  return y + 124;
}

function footer(doc, fonts, note) {
  doc.font(fonts.body).fontSize(8).fillColor("#777");
  doc.text(note, 56, 740, { width: 483, align: "center" });
}

function coverageLabel(payment) {
  if (payment.period_from && payment.period_until) {
    return formatPeriodLabel(payment.period_from, payment.period_until);
  }
  return null;
}

async function writeInvoicePdf({ filePath, number, customer, email, payment, issuedAt }) {
  const dateLabel = new Date(issuedAt || Date.now()).toUTCString().replace(/ GMT$/, " UTC");
  await writePdf(filePath, (doc) => {
    const fonts = registerFonts(doc);
    header(doc, fonts, "INVOICE", number, dateLabel);
    billTo(doc, fonts, customer, email);
    lineTable(doc, fonts, 240, payment.duration_months, payment.amount_pesewas, coverageLabel(payment));
    doc.font(fonts.body).fontSize(10).fillColor("#333").text(
      "Payment status: Awaiting Paystack (card or mobile money).",
      56,
      400
    );
    footer(doc, fonts, "Computer-generated invoice. Present this to management as the amount due for HMS license renewal.");
  });
}

async function writeReceiptPdf({ filePath, number, customer, email, payment, paidAt, reference }) {
  const dateLabel = new Date(paidAt || Date.now()).toUTCString().replace(/ GMT$/, " UTC");
  await writePdf(filePath, (doc) => {
    const fonts = registerFonts(doc);
    header(doc, fonts, "RECEIPT", number, dateLabel);
    billTo(doc, fonts, customer, email);
    lineTable(doc, fonts, 240, payment.duration_months, payment.amount_pesewas, coverageLabel(payment));
    doc.font(fonts.body).fontSize(10).fillColor("#333");
    const method = payment.channel === "manual" ? "Recorded by issuer (non-Paystack)" : "Paystack (card / mobile money)";
    doc.text(`Payment received: ${formatGhs(payment.amount_pesewas)}`, 56, 400);
    doc.text(`Method: ${method}`, 56, 416);
    doc.text(`Reference: ${reference || payment.paystack_reference}`, 56, 432);
    if (payment.license_id) {
      doc.text(`License ID: ${payment.license_id}`, 56, 448);
    }
    footer(
      doc,
      fonts,
      "Computer-generated receipt. This confirms payment was received. Keep with the invoice for management."
    );
  });
}

function documentAbsPath(relOrAbs) {
  if (path.isAbsolute(relOrAbs)) return relOrAbs;
  return path.join(config.ROOT, relOrAbs);
}

function relativeDocumentPath(absPath) {
  return path.relative(config.ROOT, absPath).split(path.sep).join("/");
}

module.exports = {
  writeInvoicePdf,
  writeReceiptPdf,
  documentAbsPath,
  relativeDocumentPath,
};
