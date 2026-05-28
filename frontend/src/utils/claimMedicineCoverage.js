/**
 * Helpers for NHIS insurance coverage on claim medicines.
 */

export function asMedicineList(source) {
  if (Array.isArray(source)) return source;
  if (source && Array.isArray(source.medicines)) return source.medicines;
  return [];
}

export function normalizeInsuranceCovered(value) {
  return String(value ?? 'yes').trim().toLowerCase();
}

export function isMedicineNotCovered(row) {
  if (!row) return false;
  const hasMedicine = Boolean(
    String(row.medicineCode || row.code || '').trim()
    || String(row._serviceName || row.description || '').trim()
  );
  if (!hasMedicine) return false;
  const covered = normalizeInsuranceCovered(
    row.insurance_covered ?? row._selectedOption?.insurance_covered
  );
  return covered === 'no';
}

export function isOutsideServiceSpan(row) {
  return !!row?.outside_service_span;
}

export function medicineNotCoveredRowClass(row) {
  return isMedicineNotCovered(row) ? 'medicine-not-covered-row' : '';
}

export function medicineNotCoveredSectionClass(row) {
  return isMedicineNotCovered(row) ? 'medicine-not-covered-section' : '';
}

/** Table row class: red for non-covered drugs, yellow for dates outside IPD span after Get CCC. */
export function claimLineRowClass(row) {
  if (isMedicineNotCovered(row)) return 'medicine-not-covered-row';
  if (isOutsideServiceSpan(row)) return 'service-outside-span-row';
  return '';
}

/** GHIMS section row class (same priority as claimLineRowClass). */
export function claimLineSectionClass(row) {
  if (isMedicineNotCovered(row)) return 'medicine-not-covered-section';
  if (isOutsideServiceSpan(row)) return 'service-outside-span-section';
  return '';
}
