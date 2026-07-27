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
