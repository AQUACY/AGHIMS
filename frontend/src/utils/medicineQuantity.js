/**
 * Dispensed quantity from the pack strength in the drug name,
 * the dose, how many times a day, and how many days.
 *
 * Cefuroxime Injection 750mg, dose 750mg, TID, 5 days → 1 × 3 × 5 = 15
 * Paracetamol 250mg, dose 500mg, BID, 2 days → 2 × 2 × 2 = 8
 */

const MASS_TO_MCG = { mcg: 1, mg: 1000, g: 1_000_000 };
const VOLUME_TO_ML = { ml: 1, l: 1000 };

function normalizeUnit(unit) {
  const text = String(unit || '').trim().toLowerCase();
  if (text === 'ug' || text === 'μg') return 'mcg';
  return text;
}

function unitFamily(unit) {
  if (MASS_TO_MCG[unit]) return 'mass';
  if (VOLUME_TO_ML[unit]) return 'volume';
  return '';
}

function toBase(amount, unit) {
  if (MASS_TO_MCG[unit]) return amount * MASS_TO_MCG[unit];
  if (VOLUME_TO_ML[unit]) return amount * VOLUME_TO_ML[unit];
  return null;
}

function productStrength(medicineName) {
  const text = String(medicineName || '');
  if (/\d+(?:\.\d+)?\s*\/\s*\d+(?:\.\d+)?\s*(?:mg|mcg|μg|ug|g|ml|iu)\b/i.test(text)) {
    return null;
  }
  const matches = [...text.matchAll(/(\d+(?:\.\d+)?)\s*(mg|mcg|μg|ug|g|ml|iu)\b/gi)];
  if (!matches.length) return null;
  const last = matches[matches.length - 1];
  const amount = Number(last[1]);
  const unit = normalizeUnit(last[2]);
  if (!amount || !unitFamily(unit)) return null;
  return { amount, unit };
}

function parseDose(dose, strength) {
  const text = String(dose || '').trim();
  if (!text) return null;
  const measured = text.match(/^(\d+(?:\.\d+)?)\s*(mg|mcg|μg|ug|g|ml|iu)\b/i);
  if (measured) {
    const unit = normalizeUnit(measured[2]);
    if (!unitFamily(unit)) return null;
    return { amount: Number(measured[1]), unit, kind: 'measured' };
  }
  const count = text.match(/^(\d+(?:\.\d+)?)(?:\s*(?:tab|tabs|tablet|tablets|cap|caps|capsule|capsules|vial|vials|amp|ampoule|injection|inj|syringe|sachet))?$/i);
  if (!count) return null;
  const amount = Number(count[1]);
  if (!amount) return null;
  if (strength && amount > 12) {
    return { amount, unit: strength.unit, kind: 'measured' };
  }
  return { amount, unit: 'count', kind: 'count' };
}

export function timesPerDay(frequency) {
  const text = String(frequency || '').trim().toLowerCase().replace(/\s+/g, ' ');
  if (!text) return null;
  const hourly = text.match(/(\d+(?:\.\d+)?)\s*(?:hourly|hrs?|hours?)/);
  if (hourly) {
    const hours = Number(hourly[1]);
    if (hours > 0 && hours <= 24) return Math.max(1, Math.round(24 / hours));
  }
  const named = [
    [/^(?:qid|qds|q\.i\.d\.?)$|\b(?:qid|qds)\b|\b4\s*(?:x|times)\b|\bfour times\b/, 4],
    [/^(?:tid|tds|cid|cib|t\.i\.d\.?)$|\b(?:tid|tds|cid|cib)\b|\b3\s*(?:x|times)\b|\bthree times\b/, 3],
    [/^(?:bid|bd|bds|b\.i\.d\.?)$|\b(?:bid|bds)\b|\bbd\b|\b2\s*(?:x|times)\b|\btwice\b|\btwo times\b/, 2],
    [/^(?:od|qd|om|nocte|stat|once|daily|mane)$|\b(?:once daily|nocte|stat)\b|\b1\s*(?:x|times)\b/, 1],
    [/^(?:5x|5 x)$|\b5\s*(?:x|times)\b|\bfive times\b/, 5],
    [/\b6\s*(?:x|times)\b|\bsix times\b/, 6],
  ];
  for (const [pattern, times] of named) {
    if (pattern.test(text)) return times;
  }
  const counted = text.match(/^(\d+(?:\.\d+)?)(?:\s*(?:x|times?))?(?:\s*(?:daily|a day|per day))?$/);
  if (counted) {
    const times = Number(counted[1]);
    if (times > 0 && times <= 12) return times;
  }
  return null;
}

export function durationDays(duration) {
  const text = String(duration || '').trim().toLowerCase();
  if (!text) return null;
  const amount = text.match(/(\d+(?:\.\d+)?)/);
  if (!amount) return null;
  const value = Number(amount[1]);
  if (!value || value <= 0) return null;
  if (/week/.test(text)) return value * 7;
  return value;
}

function formatFactor(value) {
  const rounded = Math.round(value * 1000) / 1000;
  return String(rounded);
}

export function unitsPerDose(dose, medicineName) {
  const strength = productStrength(medicineName);
  const parsed = parseDose(dose, strength);
  if (!parsed || !(parsed.amount > 0)) return null;
  if (parsed.kind === 'count') return parsed.amount;
  if (!strength) return null;
  if (unitFamily(parsed.unit) !== unitFamily(strength.unit)) return null;
  const doseBase = toBase(parsed.amount, parsed.unit);
  const strengthBase = toBase(strength.amount, strength.unit);
  if (!doseBase || !strengthBase) return null;
  return doseBase / strengthBase;
}

export function calculateDispensedQuantity({ medicineName, dose, frequency, duration }) {
  const perDose = unitsPerDose(dose, medicineName);
  const times = timesPerDay(frequency);
  const days = durationDays(duration);
  if (perDose == null || times == null || days == null) return null;
  if (perDose <= 0 || times <= 0 || days <= 0) return null;
  const raw = perDose * times * days;
  const quantity = Math.ceil(raw - 1e-9);
  if (quantity <= 0) return null;
  return {
    quantity,
    perDose,
    times,
    days,
    hint: `${formatFactor(perDose)} × ${times} a day × ${days} days = ${quantity}`,
  };
}
