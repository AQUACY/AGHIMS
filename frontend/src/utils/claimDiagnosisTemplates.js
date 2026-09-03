/**
 * Helpers for claim diagnosis templates (investigations + medicines presets).
 */

export function specialtyPrefixFromGdrg(code) {
  const raw = String(code || '').trim().toUpperCase();
  return raw ? raw.slice(0, 4) : '';
}

export function buildTemplateMatchFromPrincipal({ icd10, diagnosis, gdrg } = {}) {
  const icd = String(icd10 || '').trim().toUpperCase();
  const diag = String(diagnosis || '').trim();
  const g = String(gdrg || '').trim().toUpperCase();
  const prefix = specialtyPrefixFromGdrg(g);
  const keyword = diag.split(/\s+/).filter(Boolean).slice(0, 2).join(' ');
  return {
    match_icd10: icd || '',
    match_diagnosis: diag || '',
    match_gdrg_prefix: prefix || '',
    match_keywords: keyword || '',
    sample_icd10: icd || '',
    sample_diagnosis: diag || '',
    sample_gdrg: g || '',
  };
}

export function investigationFromTemplateItem(item, serviceDate = '') {
  return {
    serviceDate: serviceDate || '',
    gdrgCode: String(item?.gdrgCode || item?.gdrg || item?.g_drg_code || '').trim(),
    _serviceName: String(item?.serviceName || item?._serviceName || item?.description || '').trim(),
  };
}

export function medicineFromTemplateItem(item, serviceDate = '') {
  return {
    medicineCode: String(item?.medicineCode || item?.code || '').trim(),
    dispensedQty: String(item?.dispensedQty || item?.quantity || '1').trim() || '1',
    serviceDate: serviceDate || '',
    _serviceName: String(item?.serviceName || item?._serviceName || item?.description || '').trim(),
    insurance_covered: item?.insurance_covered || 'yes',
    prescription: {
      dose: String(item?.dose || item?.prescription?.dose || '').trim(),
      frequency: String(item?.frequency || item?.prescription?.frequency || '').trim(),
      duration: String(item?.duration || item?.prescription?.duration || '').trim(),
      unparsed: String(item?.unparsed || item?.prescription?.unparsed || '').trim(),
    },
  };
}

export function normalizeClaimCode(value) {
  return String(value || '').trim().toUpperCase();
}

function isBlankClaimValue(value) {
  if (value == null) return true;
  if (typeof value === 'number') return !Number.isFinite(value) || value === 0;
  return String(value).trim() === '';
}

/** Keep an existing claim value; fill from the template when the claim field is empty. */
export function fillBlankClaimValue(current, incoming) {
  return isBlankClaimValue(current) && !isBlankClaimValue(incoming) ? incoming : current;
}

/**
 * Find a claim line that already represents this template item.
 * Match medicine/G-DRG code first; fall back to name when codes are missing or equal.
 */
export function findExistingClaimItemIndex(list, { code, name } = {}, { getCode, getName } = {}) {
  const items = Array.isArray(list) ? list : [];
  const needleCode = normalizeClaimCode(code);
  if (needleCode && typeof getCode === 'function') {
    const idx = items.findIndex((x) => normalizeClaimCode(getCode(x)) === needleCode);
    if (idx >= 0) return idx;
  }
  const needleName = String(name || '').trim().toLowerCase();
  if (needleName && typeof getName === 'function') {
    const idx = items.findIndex((x) => {
      const existingCode = typeof getCode === 'function' ? normalizeClaimCode(getCode(x)) : '';
      if (needleCode && existingCode && needleCode !== existingCode) return false;
      return String(getName(x) || '').trim().toLowerCase() === needleName;
    });
    if (idx >= 0) return idx;
  }
  return -1;
}

export function serializeInvestigationForTemplate(inv) {
  return {
    gdrgCode: String(inv?.gdrgCode || inv?.gdrg || '').trim(),
    serviceName: String(inv?._serviceName || inv?.description || '').trim(),
  };
}

export function serializeMedicineForTemplate(med) {
  return {
    medicineCode: String(med?.medicineCode || med?.code || '').trim(),
    serviceName: String(med?._serviceName || med?.description || '').trim(),
    dispensedQty: String(med?.dispensedQty || med?.quantity || '1').trim() || '1',
    dose: String(med?.prescription?.dose || med?.dose || '').trim(),
    frequency: String(med?.prescription?.frequency || med?.frequency || '').trim(),
    duration: String(med?.prescription?.duration || med?.duration || '').trim(),
    unparsed: String(med?.prescription?.unparsed || med?.unparsed || '').trim(),
    insurance_covered: med?.insurance_covered || 'yes',
  };
}

/** True when template has 2+ investigations or 2+ medicines (checkbox picker needed). */
export function templateNeedsItemPicker(template) {
  const inv = Array.isArray(template?.investigations) ? template.investigations.length : 0;
  const med = Array.isArray(template?.medicines) ? template.medicines.length : 0;
  return inv > 1 || med > 1;
}

/**
 * Merge matched templates (first) with the full active list so users can always pick any template.
 * Returns { templates, matchedIds, hasExactMatch }.
 */
export function mergeMatchedAndAllTemplates(matched = [], all = []) {
  const matchedList = Array.isArray(matched) ? matched : [];
  const allList = Array.isArray(all) ? all : [];
  const matchedIds = new Set(matchedList.map((t) => t?.id).filter((id) => id != null));
  const rest = allList.filter((t) => t?.id != null && !matchedIds.has(t.id));
  // Prefer match order, then remaining by name
  const templates = [...matchedList, ...rest];
  return {
    templates,
    matchedIds,
    hasExactMatch: matchedIds.size > 0,
  };
}
