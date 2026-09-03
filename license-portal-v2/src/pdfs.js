const fs = require("fs");
const path = require("path");
const PDFDocument = require("pdfkit");
const QRCode = require("qrcode");
const { config } = require("./config");
const { formatGhs, formatCoverageRange, formatLicencePeriod, formatAccraDate } = require("./dates");

const FONT_REG = path.join(config.ROOT, "fonts", "NotoSans-Regular.ttf");
const FONT_BOLD = path.join(config.ROOT, "fonts", "NotoSans-Bold.ttf");
const NAVY = "#14213d";
const GOLD = "#c4a35a";
const MUTED = "#5c6470";
const INK = "#1c1c1c";
const LEFT = 56;
const RIGHT = 539;
const WIDTH = RIGHT - LEFT;

function letterhead() {
  return {
    name: (config.company.name || "").trim() || "License Portal",
    address: (config.company.address || "").trim(),
    phone: (config.company.phone || "").trim(),
    email: (config.company.email || "").trim(),
    tin: (config.company.tin || "").trim(),
    tagline: (config.company.tagline || "").trim() || "Software • IT Infrastructure • Digital Solutions",
    vatRegistered: Boolean(config.company.vatRegistered),
  };
}

function licenceServiceTitle(durationMonths) {
  const n = Math.max(1, parseInt(durationMonths, 10) || 1);
  if (n === 12) return "HMS Annual Software Licence Renewal";
  if (n === 1) return "HMS Monthly Software Licence Renewal";
  return `HMS ${n}-Month Software Licence Renewal`;
}

function coverageForPayment(payment) {
  if (payment && payment.period_from && payment.period_until) {
    return formatCoverageRange(payment.period_from, payment.period_until);
  }
  const months = Math.max(1, parseInt(payment && payment.duration_months, 10) || 1);
  return `${months} month${months === 1 ? "" : "s"}`;
}

function licencePeriodForPayment(payment) {
  if (payment && payment.period_from && payment.period_until) {
    return formatLicencePeriod(payment.period_from, payment.period_until);
  }
  return coverageForPayment(payment);
}

function paymentMethodLabel(payment) {
  const ch = String((payment && payment.channel) || "").toLowerCase();
  if (ch === "patch" || ch === "manual") return "Issued by provider";
  return "Paystack";
}

function paymentStatusLabel(payment) {
  return String((payment && payment.status) || "").toLowerCase() === "success" ? "PAID" : "PENDING";
}

function taxNote(company) {
  return `.`;
}

// function taxNote(company) {
//   return `${company.name} is not currently registered for VAT. VAT, NHIL and GETFund Levy have therefore not been charged.`;
// }

function receiptVerifyUrl(receiptNumber) {
  return `${config.publicBaseUrl}/verify/${encodeURIComponent(receiptNumber)}`;
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
    const doc = new PDFDocument({ size: "A4", margin: 50 });
    const stream = fs.createWriteStream(filePath);
    doc.pipe(stream);
    try {
      draw(doc);
      doc.end();
    } catch (err) {
      try {
        doc.end();
      } catch (_) {
        /* ignore */
      }
      reject(err);
      return;
    }
    stream.on("finish", () => resolve(filePath));
    stream.on("error", reject);
  });
}

function drawHeader(doc, fonts, title) {
  const company = letterhead();
  const { pdfLogoPath } = require("./branding");
  const logoPath = pdfLogoPath();
  let nameX = LEFT;
  let nameWidth = 300;
  if (logoPath) {
    try {
      doc.image(logoPath, LEFT, 44, { fit: [48, 48] });
      nameX = 110;
      nameWidth = 250;
    } catch (_) {
      nameX = LEFT;
      nameWidth = 300;
    }
  }
  doc.fillColor(NAVY).font(fonts.bold).fontSize(16).text(company.name, nameX, 46, { width: nameWidth });
  doc.font(fonts.body).fontSize(8).fillColor(MUTED).text(company.tagline, nameX, doc.y, { width: nameWidth });
  const lines = [company.address, [company.phone, company.email].filter(Boolean).join(" · ")].filter(Boolean);
  if (company.tin) lines.push(`TIN: ${company.tin}`);
  if (lines.length) {
    doc.font(fonts.body).fontSize(8).fillColor(MUTED).text(lines.join("\n"), nameX, doc.y + 2, { width: nameWidth });
  }

  doc.fillColor(NAVY).font(fonts.bold).fontSize(14).text(title, 330, 46, { width: 209, align: "right" });
  const headerBottom = Math.max(doc.y, 108);
  doc.moveTo(LEFT, headerBottom + 10).lineTo(RIGHT, headerBottom + 10).strokeColor(GOLD).lineWidth(1.5).stroke();
  return headerBottom + 22;
}

function kv(doc, fonts, x, y, label, value, valueWidth = 280) {
  doc.font(fonts.bold).fontSize(9).fillColor(MUTED).text(label, x, y, { width: 118 });
  doc.font(fonts.body).fontSize(10).fillColor(INK).text(value || "—", x + 122, y, { width: valueWidth });
  return Math.max(y + 16, doc.y + 4);
}

function drawTaxBreakdown(doc, fonts, y, amountPesewas) {
  const company = letterhead();
  const zero = formatGhs(0);
  const total = formatGhs(amountPesewas);
  const colLabel = 280;
  const colAmt = 400;
  const amtWidth = RIGHT - colAmt;
  const rows = [
    ["VAT", zero, false, ""],
    // ["VAT", zero, false, company.vatRegistered ? "" : "Not VAT registered"],
    ["NHIL", zero, false, ""],
    ["GETFund Levy", zero, false, ""],
    ["Amount Payable", total, true, ""],
  ];
  doc.moveTo(LEFT, y).lineTo(RIGHT, y).strokeColor("#e6e6e6").lineWidth(0.5).stroke();
  y += 12;
  for (const [label, amount, emphasize, note] of rows) {
    const rowTop = y;
    doc.font(emphasize ? fonts.bold : fonts.body).fontSize(emphasize ? 11 : 9).fillColor(emphasize ? NAVY : MUTED);
    doc.text(label, colLabel, rowTop, { width: 110, lineBreak: false });
    doc.font(emphasize ? fonts.bold : fonts.body).fillColor(emphasize ? NAVY : INK);
    doc.text(amount, colAmt, rowTop, { width: amtWidth, align: "right", lineBreak: false });
    y = rowTop + (emphasize ? 18 : 14);
    if (note) {
      doc.font(fonts.body).fontSize(8).fillColor(MUTED).text(note, colLabel, y, { width: amtWidth + 110 });
      y = doc.y + 4;
    }
  }
  if (!company.vatRegistered) {
    y += 6;
    doc.font(fonts.body).fontSize(8).fillColor(MUTED).text(taxNote(company), LEFT, y, { width: WIDTH });
    y = doc.y + 8;
  }
  return y;
}

function drawStatus(doc, fonts, y, status, method, extra = "") {
  doc.font(fonts.bold).fontSize(10).fillColor(NAVY).text(`Payment Status: ${status}`, LEFT, y);
  y = doc.y + 4;
  doc.font(fonts.body).fontSize(10).fillColor(INK).text(`Payment Method: ${method}`, LEFT, y);
  if (extra) {
    y = doc.y + 4;
    doc.text(extra, LEFT, y);
  }
  return doc.y + 10;
}

async function writeInvoicePdf({ filePath, number, customer, email, payment, issuedAt }) {
  const company = letterhead();
  const service = licenceServiceTitle(payment.duration_months);
  const coverage = coverageForPayment(payment);
  const amount = formatGhs(payment.amount_pesewas);
  const status = paymentStatusLabel(payment);
  const method = paymentMethodLabel(payment);
  const issued = formatAccraDate(issuedAt || Date.now(), { padDay: false });

  await writePdf(filePath, (doc) => {
    const fonts = registerFonts(doc);
    let y = drawHeader(doc, fonts, "INVOICE");
    doc.font(fonts.bold).fontSize(9).fillColor(MUTED).text("Invoice No.", LEFT, y);
    doc.font(fonts.body).fontSize(10).fillColor(INK).text(number, LEFT, y + 12);
    doc.font(fonts.bold).fontSize(9).fillColor(MUTED).text("Invoice Date", 330, y, { width: 209, align: "right" });
    doc.font(fonts.body).fontSize(10).fillColor(INK).text(issued, 330, y + 12, { width: 209, align: "right" });
    y += 40;

    doc.font(fonts.bold).fontSize(9).fillColor(MUTED).text("BILL TO", LEFT, y);
    y += 14;
    doc.font(fonts.bold).fontSize(12).fillColor(NAVY).text(customer.hospital_name || "Customer", LEFT, y, { width: WIDTH });
    y = doc.y + 2;
    const bits = [];
    if (customer.facility_code) bits.push(`Facility code: ${customer.facility_code}`);
    if (email) bits.push(email);
    if (bits.length) {
      doc.font(fonts.body).fontSize(9).fillColor(MUTED).text(bits.join("  ·  "), LEFT, y, { width: WIDTH });
      y = doc.y + 14;
    } else {
      y += 12;
    }

    doc.moveTo(LEFT, y).lineTo(RIGHT, y).strokeColor("#ddd").lineWidth(0.6).stroke();
    y += 8;
    doc.font(fonts.bold).fontSize(8).fillColor(MUTED);
    doc.text("INVOICE ITEM", LEFT, y, { width: 170 });
    doc.text("COVERAGE", 230, y, { width: 200 });
    doc.text("AMOUNT", 430, y, { width: 109, align: "right" });
    y += 16;
    doc.moveTo(LEFT, y).lineTo(RIGHT, y).strokeColor("#ddd").lineWidth(0.6).stroke();
    y += 10;
    const itemTop = y;
    doc.font(fonts.body).fontSize(9).fillColor(INK).text(service, LEFT, itemTop, { width: 168 });
    const afterItem = doc.y;
    doc.text(coverage, 230, itemTop, { width: 198 });
    const afterCover = doc.y;
    doc.font(fonts.bold).text(amount, 430, itemTop, { width: 109, align: "right" });
    y = Math.max(afterItem, afterCover, itemTop + 14) + 14;

    y = drawTaxBreakdown(doc, fonts, y, payment.amount_pesewas);
    y = drawStatus(doc, fonts, y + 8, status, method);
    doc.font(fonts.body).fontSize(8).fillColor(MUTED).text(
      "This invoice is a reference for accounts. Arrange payment on the license portal. A receipt is issued only after Paystack confirms the payment.",
      LEFT,
      Math.min(y + 16, 720),
      { width: WIDTH }
    );
    doc.font(fonts.body).fontSize(8).fillColor("#999").text(
      `Computer-generated invoice — ${company.name}`,
      LEFT,
      780,
      { width: WIDTH, align: "center" }
    );
  });
}

async function writeReceiptPdf({
  filePath,
  number,
  customer,
  email,
  payment,
  paidAt,
  reference,
  invoiceNumber,
}) {
  const company = letterhead();
  const service = licenceServiceTitle(payment.duration_months);
  const period = licencePeriodForPayment(payment);
  const amount = formatGhs(payment.amount_pesewas);
  const method = paymentMethodLabel(payment);
  const paid = formatAccraDate(paidAt || Date.now(), { padDay: false });
  const verifyUrl = receiptVerifyUrl(number);
  const qrPng = await QRCode.toBuffer(verifyUrl, {
    type: "png",
    width: 280,
    margin: 1,
    errorCorrectionLevel: "M",
    color: { dark: NAVY, light: "#ffffff" },
  });

  await writePdf(filePath, (doc) => {
    const fonts = registerFonts(doc);
    let y = drawHeader(doc, fonts, "PAYMENT RECEIPT");
    y = kv(doc, fonts, LEFT, y, "Receipt No.", number);
    y = kv(doc, fonts, LEFT, y, "Invoice No.", invoiceNumber || "—");
    y = kv(doc, fonts, LEFT, y, "Payment Date", paid);
    y += 8;
    doc.moveTo(LEFT, y).lineTo(RIGHT, y).strokeColor("#e6e6e6").lineWidth(0.5).stroke();
    y += 12;
    y = kv(doc, fonts, LEFT, y, "Customer", customer.hospital_name || "—");
    if (customer.facility_code) y = kv(doc, fonts, LEFT, y, "Facility", customer.facility_code);
    if (email) y = kv(doc, fonts, LEFT, y, "Email", email);
    y = kv(doc, fonts, LEFT, y, "Service", service, 360);
    y = kv(doc, fonts, LEFT, y, "Licence Period", period, 360);
    y += 6;
    doc.font(fonts.bold).fontSize(9).fillColor(MUTED).text("Amount Paid", LEFT, y);
    doc.font(fonts.bold).fontSize(16).fillColor(NAVY).text(amount, LEFT + 122, y - 4);
    y = doc.y + 10;
    y = kv(doc, fonts, LEFT, y, "Payment Method", method);
    y = kv(doc, fonts, LEFT, y, "Transaction Ref.", reference || payment.paystack_reference || "—", 360);
    y += 8;
    doc.moveTo(LEFT, y).lineTo(RIGHT, y).strokeColor(GOLD).lineWidth(1).stroke();
    y += 14;
    doc.font(fonts.bold).fontSize(9).fillColor(NAVY).text("Tax Information", LEFT, y);
    y = doc.y + 4;
    doc.font(fonts.body).fontSize(9).fillColor(INK).text(taxNote(company), LEFT, y, { width: 360 });
    y = doc.y + 14;
    doc.font(fonts.bold).fontSize(11).fillColor(NAVY).text("Payment Status: PAID", LEFT, y);
    y = doc.y + 24;

    const qrSize = 86;
    const qrX = RIGHT - qrSize;
    const qrY = Math.min(Math.max(y, 560), 668);
    try {
      doc.image(qrPng, qrX, qrY, { width: qrSize, height: qrSize });
    } catch (_) {
      /* still a valid receipt without the mark */
    }
    doc.font(fonts.bold).fontSize(7).fillColor(NAVY).text("Scan to verify", qrX, qrY + qrSize + 4, {
      width: qrSize,
      align: "center",
    });
    doc.font(fonts.body).fontSize(6).fillColor(MUTED).text(verifyUrl, LEFT, qrY + qrSize + 16, {
      width: WIDTH,
      align: "right",
    });

    doc.font(fonts.body).fontSize(8).fillColor("#999").text(
      `Computer-generated receipt — ${company.name}`,
      LEFT,
      780,
      { width: WIDTH, align: "center" }
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
  licenceServiceTitle,
  receiptVerifyUrl,
  taxNote,
};
