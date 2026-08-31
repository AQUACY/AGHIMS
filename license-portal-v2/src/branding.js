const fs = require("fs");
const path = require("path");
const { config } = require("./config");

const MIME_EXT = {
  "image/png": ".png",
  "image/jpeg": ".jpg",
  "image/jpg": ".jpg",
};

function brandingDir() {
  return config.brandingDir;
}

function metaPath() {
  return path.join(brandingDir(), "meta.json");
}

function ensureBrandingDir() {
  fs.mkdirSync(brandingDir(), { recursive: true });
}

function readMeta() {
  try {
    const raw = fs.readFileSync(metaPath(), "utf8");
    const meta = JSON.parse(raw);
    if (!meta || !meta.ext || !meta.mime) return null;
    return meta;
  } catch (_) {
    return null;
  }
}

function logoAbsPath(meta) {
  return path.join(brandingDir(), `logo${meta.ext}`);
}

function getLogo() {
  const meta = readMeta();
  if (!meta) return null;
  const absPath = logoAbsPath(meta);
  if (!fs.existsSync(absPath)) return null;
  const st = fs.statSync(absPath);
  return {
    absPath,
    mime: meta.mime,
    ext: meta.ext,
    originalName: meta.originalName || `logo${meta.ext}`,
    mtime: Math.floor(st.mtimeMs),
    size: st.size,
  };
}

function publicLogoUrl() {
  const logo = getLogo();
  if (!logo) return null;
  return `/api/branding/logo?v=${logo.mtime}`;
}

function pdfLogoPath() {
  const logo = getLogo();
  if (!logo) return null;
  if (logo.mime !== "image/png" && logo.mime !== "image/jpeg") return null;
  return logo.absPath;
}

function decodeDataUrl(data) {
  const raw = String(data || "").trim();
  const match = raw.match(/^data:([^;]+);base64,(.+)$/s);
  if (match) {
    return { mime: match[1].trim().toLowerCase(), buffer: Buffer.from(match[2], "base64") };
  }
  return { mime: "", buffer: Buffer.from(raw, "base64") };
}

function saveLogo({ data, mime, filename }) {
  const decoded = decodeDataUrl(data);
  const type = String(mime || decoded.mime || "").trim().toLowerCase();
  const ext = MIME_EXT[type];
  if (!ext) {
    const err = new Error("Use a PNG or JPEG logo.");
    err.status = 400;
    throw err;
  }
  if (!decoded.buffer.length) {
    const err = new Error("Logo file is empty.");
    err.status = 400;
    throw err;
  }
  if (decoded.buffer.length > 1.5 * 1024 * 1024) {
    const err = new Error("Logo must be 1.5 MB or smaller.");
    err.status = 400;
    throw err;
  }
  ensureBrandingDir();
  const previous = getLogo();
  if (previous) {
    try {
      fs.unlinkSync(previous.absPath);
    } catch (_) {
      /* ignore */
    }
  }
  const meta = {
    mime: type === "image/jpg" ? "image/jpeg" : type,
    ext,
    originalName: String(filename || `logo${ext}`).slice(0, 180),
  };
  fs.writeFileSync(logoAbsPath(meta), decoded.buffer);
  fs.writeFileSync(metaPath(), JSON.stringify(meta));
  return getLogo();
}

function deleteLogo() {
  const logo = getLogo();
  if (logo) {
    try {
      fs.unlinkSync(logo.absPath);
    } catch (_) {
      /* ignore */
    }
  }
  try {
    fs.unlinkSync(metaPath());
  } catch (_) {
    /* ignore */
  }
}

module.exports = {
  ensureBrandingDir,
  getLogo,
  publicLogoUrl,
  pdfLogoPath,
  saveLogo,
  deleteLogo,
};
