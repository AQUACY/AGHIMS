/**
 * Helpers for pharmacy / doctor (prescriber) claim vetting + export warnings.
 * Vet flags are independent and persist after claims-manager finalize.
 * Workflow statuses: draft | flagged | pharmacy_vetted | doctor_vetted | vetted | finalized | reopened
 */

export const EXPORTABLE_STATUSES = new Set([
  'finalized',
  'pharmacy_vetted',
  'doctor_vetted',
  'vetted',
]);

export function claimStatusOf(row) {
  return String(row?.claim_status || row?.status || '').trim().toLowerCase();
}

export function hasPharmacyVetted(row) {
  return Boolean(row?.pharmacy_vetted || row?.pharmacy_vetted_at || claimStatusOf(row) === 'pharmacy_vetted' || claimStatusOf(row) === 'vetted');
}

export function hasDoctorVetted(row) {
  return Boolean(row?.doctor_vetted || row?.doctor_vetted_at || claimStatusOf(row) === 'doctor_vetted' || claimStatusOf(row) === 'vetted');
}

export function isClaimExportable(row) {
  if (!row) return false;
  if (EXPORTABLE_STATUSES.has(claimStatusOf(row))) return true;
  return hasPharmacyVetted(row) || hasDoctorVetted(row);
}

export function isManagerFinalized(row) {
  return claimStatusOf(row) === 'finalized';
}

/** @deprecated use hasPharmacyVetted — kept for list count helpers */
export function isPharmacyVettedStatus(row) {
  return hasPharmacyVetted(row);
}

/** @deprecated use hasDoctorVetted */
export function isDoctorVettedStatus(row) {
  return hasDoctorVetted(row);
}

export function statusLabel(status) {
  const s = String(status || '').toLowerCase();
  const map = {
    draft: 'draft',
    flagged: 'flagged',
    pharmacy_vetted: 'pharmacy vetted',
    doctor_vetted: 'doctor vetted',
    vetted: 'pharmacy + doctor vetted',
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
    vetted: 'deep-purple',
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
  const pharmacyCount = notFinalized.filter((r) => hasPharmacyVetted(r)).length;
  const doctorCount = notFinalized.filter((r) => hasDoctorVetted(r)).length;
  return (
    `This export has ${total} claim(s). ` +
    `${notFinalized.length} are not finalized by the claims manager` +
    ` (${pharmacyCount} pharmacy-vetted, ${doctorCount} doctor-vetted). ` +
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
