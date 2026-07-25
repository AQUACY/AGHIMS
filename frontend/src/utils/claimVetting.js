/**
 * Helpers for pharmacy / doctor (prescriber) claim vetting + export warnings.
 * Statuses: draft | flagged | pharmacy_vetted | doctor_vetted | finalized | reopened
 */

export const EXPORTABLE_STATUSES = new Set([
  'finalized',
  'pharmacy_vetted',
  'doctor_vetted',
]);

export function claimStatusOf(row) {
  return String(row?.claim_status || row?.status || '').trim().toLowerCase();
}

export function isClaimExportable(row) {
  return EXPORTABLE_STATUSES.has(claimStatusOf(row));
}

export function isManagerFinalized(row) {
  return claimStatusOf(row) === 'finalized';
}

export function isPharmacyVettedStatus(row) {
  return claimStatusOf(row) === 'pharmacy_vetted';
}

export function isDoctorVettedStatus(row) {
  return claimStatusOf(row) === 'doctor_vetted';
}

export function statusLabel(status) {
  const s = String(status || '').toLowerCase();
  const map = {
    draft: 'draft',
    flagged: 'flagged',
    pharmacy_vetted: 'pharmacy vetted',
    doctor_vetted: 'doctor vetted',
    finalized: 'finalized',
    reopened: 'reopened',
  };
  return map[s] || s || '—';
}

export function statusColor(status) {
  const s = String(status || '').toLowerCase();
  const map = {
    draft: 'orange',
    flagged: 'negative',
    pharmacy_vetted: 'teal',
    doctor_vetted: 'indigo',
    finalized: 'positive',
    reopened: 'warning',
  };
  return map[s] || 'grey';
}

/**
 * Build export warning message when some selected rows are vetted but not manager-finalized.
 * Returns null if no warning needed.
 */
export function buildExportVettingWarning(rows) {
  const list = Array.isArray(rows) ? rows : [];
  const total = list.length;
  if (!total) return null;
  const notFinalized = list.filter((r) => !isManagerFinalized(r));
  if (!notFinalized.length) return null;
  const pharmacyOnly = notFinalized.filter((r) => isPharmacyVettedStatus(r)).length;
  const doctorOnly = notFinalized.filter((r) => isDoctorVettedStatus(r)).length;
  return (
    `This export has ${total} claim(s). ` +
    `${notFinalized.length} are not finalized by the claims manager` +
    ` (${pharmacyOnly} pharmacy-vetted, ${doctorOnly} doctor-vetted). ` +
    `Are you sure you want to download the XML file?`
  );
}

export function confirmExportWithVettingWarning($q, rows) {
  const message = buildExportVettingWarning(rows);
  if (!message) return Promise.resolve(true);
  return new Promise((resolve) => {
    $q.dialog({
      title: 'Export includes unfinalized claims',
      message,
      cancel: { label: 'Cancel', flat: true },
      ok: { label: 'Yes, download XML', color: 'primary' },
      persistent: true,
    })
      .onOk(() => resolve(true))
      .onCancel(() => resolve(false))
      .onDismiss(() => resolve(false));
  });
}
