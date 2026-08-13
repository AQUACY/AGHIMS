/**
 * Sort claim medicines by service date ascending (earliest day first).
 * Rows without a date stay at the end so dated lines keep chronological order.
 */

export function medicineServiceDateKey(row) {
  const raw = String(row?.serviceDate ?? row?.date ?? '').trim();
  if (!raw) return '';
  return raw.length >= 10 ? raw.slice(0, 10) : raw;
}

export function sortClaimMedicinesByDateAsc(medicines) {
  if (!Array.isArray(medicines) || medicines.length < 2) {
    return Array.isArray(medicines) ? [...medicines] : [];
  }
  return [...medicines].sort((a, b) => {
    const da = medicineServiceDateKey(a);
    const db = medicineServiceDateKey(b);
    if (!da && !db) return 0;
    if (!da) return 1;
    if (!db) return -1;
    if (da < db) return -1;
    if (da > db) return 1;
    return 0;
  });
}
