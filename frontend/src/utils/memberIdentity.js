/**
 * Ghana Card / NHIA / HIN helpers for ClaimIT member numbers.
 * ClaimIT accepts NHIA membership numbers or HIN — not Ghana Cards (GHA-...).
 * HIN must not be used to generate CCC; use Ghana Card or NHIA instead.
 */

/** GHA-xxxxxxxx-x or GHA-xxxxxxxx-xx */
export const GHANA_CARD_PATTERN = /^GHA-\d+-\d{1,2}$/i;

export function isGhanaCard(value) {
  const cleaned = String(value || '').replace(/\s+/g, '').trim();
  return GHANA_CARD_PATTERN.test(cleaned);
}

export function normalizeGhanaCard(value) {
  if (!isGhanaCard(value)) return String(value || '').trim();
  return String(value).replace(/\s+/g, '').trim().toUpperCase();
}

/**
 * Identifier to send to NHIA for CCC lookup.
 * Prefer saved Ghana Card; never use HIN when Ghana Card is on file.
 */
export function memberNoForCcc({ memberNo, ghanaCard, insurance_id } = {}) {
  const card = String(ghanaCard || '').trim();
  if (card && isGhanaCard(card)) return normalizeGhanaCard(card);

  const member = String(memberNo || insurance_id || '').trim();
  if (isGhanaCard(member)) return normalizeGhanaCard(member);

  // NHIA membership number (or other non-Ghana identifier). HIN is OK for ClaimIT
  // export only — CCC must use Ghana Card when that was the original member id.
  return member;
}

export function canUseMemberForCcc(source = {}) {
  return !!memberNoForCcc(source);
}
