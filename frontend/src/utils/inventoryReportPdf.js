/**
 * Uniform GHS-style PDF exports for inventory reports (same visual language as Management transactions PDF).
 */
const LOGO_MOH = '/logos/ministry-of-health-logo.png';
const LOGO_GHS = '/logos/ghana-health-service-logo.png';

async function fetchLogoDataUrl(url) {
  try {
    const res = await fetch(url);
    if (!res.ok) return null;
    const blob = await res.blob();
    return await new Promise((resolve, reject) => {
      const fr = new FileReader();
      fr.onload = () => resolve(fr.result);
      fr.onerror = reject;
      fr.readAsDataURL(blob);
    });
  } catch {
    return null;
  }
}

function naturalSizeFromDataUrl(dataUrl) {
  return new Promise((resolve) => {
    if (!dataUrl) {
      resolve(null);
      return;
    }
    const img = new Image();
    img.onload = () => resolve({ w: img.naturalWidth, h: img.naturalHeight });
    img.onerror = () => resolve(null);
    img.src = dataUrl;
  });
}

function slugFile(s) {
  return String(s || 'report')
    .replace(/[^\w\-]+/g, '_')
    .replace(/_+/g, '_')
    .slice(0, 80);
}

/**
 * @param {object} opts
 * @param {string} opts.facilityName
 * @param {string} opts.reportTitle - e.g. "Inventory — Requisitions"
 * @param {string} [opts.subtitle]
 * @param {string} opts.periodLine - e.g. "2026-01-01 – 2026-01-31"
 * @param {string} [opts.filterNote]
 * @param {string} [opts.summaryLine]
 * @param {string[][]} opts.head - single row of column labels
 * @param {string[][]} opts.body
 * @param {string} opts.filename - without .pdf
 * @param {'landscape'|'portrait'} [opts.orientation]
 */
export async function downloadInventoryReportPdf(opts) {
  const {
    facilityName,
    reportTitle,
    subtitle = 'Inventory management',
    periodLine,
    filterNote,
    summaryLine,
    head,
    body,
    filename,
    orientation = 'landscape',
  } = opts;

  const [{ jsPDF }, autoMod] = await Promise.all([import('jspdf'), import('jspdf-autotable')]);
  const autoTable = autoMod.default;

  const doc = new jsPDF({ orientation, unit: 'mm', format: 'a4' });
  const pageW = doc.internal.pageSize.getWidth();
  let y = 7;

  const logoMaxH = 14;
  const [mohData, ghsData] = await Promise.all([fetchLogoDataUrl(LOGO_MOH), fetchLogoDataUrl(LOGO_GHS)]);

  if (mohData && ghsData) {
    const [d1, d2] = await Promise.all([naturalSizeFromDataUrl(mohData), naturalSizeFromDataUrl(ghsData)]);
    if (d1 && d2 && d1.h > 0 && d2.h > 0) {
      const w1 = (d1.w / d1.h) * logoMaxH;
      const w2 = (d2.w / d2.h) * logoMaxH;
      const gap = 6;
      const totalW = w1 + gap + w2;
      const x0 = (pageW - totalW) / 2;
      doc.addImage(mohData, 'PNG', x0, y, w1, logoMaxH);
      doc.addImage(ghsData, 'PNG', x0 + w1 + gap, y, w2, logoMaxH);
    }
  } else if (mohData) {
    const d1 = await naturalSizeFromDataUrl(mohData);
    if (d1 && d1.h > 0) {
      const w1 = (d1.w / d1.h) * logoMaxH;
      doc.addImage(mohData, 'PNG', (pageW - w1) / 2, y, w1, logoMaxH);
    }
  } else if (ghsData) {
    const d2 = await naturalSizeFromDataUrl(ghsData);
    if (d2 && d2.h > 0) {
      const w2 = (d2.w / d2.h) * logoMaxH;
      doc.addImage(ghsData, 'PNG', (pageW - w2) / 2, y, w2, logoMaxH);
    }
  }

  if (mohData || ghsData) {
    y += logoMaxH + 2;
  }

  doc.setFontSize(10);
  doc.setFont('helvetica', 'bold');
  doc.text('GHANA HEALTH SERVICE', pageW / 2, y, { align: 'center' });
  y += 5;
  doc.setFontSize(14);
  doc.setFont('helvetica', 'bold');
  doc.text(facilityName || 'Facility', pageW / 2, y, { align: 'center' });
  y += 7;
  doc.setFontSize(12);
  doc.text(reportTitle, pageW / 2, y, { align: 'center' });
  y += 6;
  doc.setFontSize(9);
  doc.setFont('helvetica', 'normal');
  doc.text(subtitle, pageW / 2, y, { align: 'center' });
  y += 6;

  const gen = new Date().toLocaleString();
  doc.text(`Generated: ${gen}`, 14, y);
  y += 5;
  doc.text(`Period: ${periodLine}`, 14, y);
  y += 5;
  if (filterNote) {
    doc.text(`Filter: ${filterNote}`, 14, y);
    y += 5;
  }
  if (summaryLine) {
    doc.setFont('helvetica', 'bold');
    doc.text(summaryLine, 14, y);
    doc.setFont('helvetica', 'normal');
    y += 4;
  }
  doc.setDrawColor(180);
  doc.line(14, y, pageW - 14, y);
  y += 6;

  autoTable(doc, {
    startY: y,
    head,
    body,
    styles: { fontSize: orientation === 'landscape' ? 7 : 8, cellPadding: 1.5 },
    headStyles: { fillColor: [46, 125, 50] },
    margin: { left: 14, right: 14 },
    didDrawPage: (data) => {
      if (data.pageNumber > 1) {
        doc.setFontSize(8);
        doc.setTextColor(100);
        doc.text(`${facilityName || 'Facility'} — ${reportTitle}`, 14, 8);
        doc.setTextColor(0);
      }
    },
  });

  doc.save(`${slugFile(filename)}.pdf`);
}
