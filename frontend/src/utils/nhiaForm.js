/**
 * Apply NHIA lookup / CCC response fields to patient registration forms.
 */
export const BABY_MAX_AGE_DAYS = 92;

export function isWithinBabyWindow(dobStr) {
  if (!dobStr) return false;
  const dob = new Date(`${dobStr}T12:00:00`);
  if (Number.isNaN(dob.getTime())) return false;
  const today = new Date();
  today.setHours(12, 0, 0, 0);
  const diffDays = Math.floor((today - dob) / (1000 * 60 * 60 * 24));
  return diffDays >= 0 && diffDays <= BABY_MAX_AGE_DAYS;
}

export function firstNameFromFullName(fullName) {
  if (!fullName?.trim()) return '';
  return fullName.trim().split(/\s+/)[0] || '';
}

export function babyNameFromFirstName(firstName) {
  const first = (firstName || '').trim();
  return first ? `Baby of ${first}` : 'Baby of';
}

export function babyNameFromFullName(fullName) {
  return babyNameFromFirstName(firstNameFromFullName(fullName));
}

export function babySurnameFromFullName(fullName) {
  if (!fullName?.trim()) return null;
  const parts = fullName.trim().split(/\s+/);
  return parts.length > 1 ? parts.slice(1).join(' ') : null;
}

/** Apply NHIA portal fields to a registration form (standard import — no baby logic here). */
export function applyNhiaDataToForm(form, data) {
  if (!data) return;

  if (data.hin) {
    form.insurance_id = data.hin;
    form.insured = true;
  }

  if (data.name) {
    const parts = data.name.trim().split(/\s+/);
    if (parts.length === 1) {
      form.name = parts[0];
    } else {
      form.name = parts[0];
      form.surname = parts.slice(1).join(' ');
    }
  }

  if (data.gender) {
    const g = data.gender.toString().trim().toUpperCase();
    if (g.startsWith('M')) form.gender = 'M';
    else if (g.startsWith('F')) form.gender = 'F';
  }

  if (data.dob) {
    const parsed = parsePortalDate(data.dob);
    if (parsed) form.date_of_birth = parsed;
  }

  if (data.start) {
    const parsed = parsePortalDate(data.start);
    if (parsed) form.insurance_start_date = parsed;
  }

  if (data.end) {
    const parsed = parsePortalDate(data.end);
    if (parsed) form.insurance_end_date = parsed;
  }

  if (data.ccc) {
    form.ccc_number = data.ccc;
  }

  if (data.status) {
    form.ccc_status = data.status;
    form.nhis_active = data.status.toString().toUpperCase() === 'ACTIVE';
  }
}

/** Apply only CCC fields from NHIA (Get CCC) — do not overwrite name/DOB from registration. */
export function applyNhiaCccToForm(form, data) {
  if (!data) return;
  if (data.ccc) {
    form.ccc_number = data.ccc;
  }
  if (data.status) {
    form.ccc_status = data.status;
    form.nhis_active = data.status.toString().toUpperCase() === 'ACTIVE';
  }
}

function parsePortalDate(value) {
  if (!value) return null;
  const trimmed = value.trim();
  const dmy = /^(\d{1,2})-(\d{1,2})-(\d{4})$/;
  const ymd = /^(\d{4})-(\d{1,2})-(\d{1,2})$/;
  let match = trimmed.match(dmy);
  if (match) {
    const [, d, m, y] = match;
    return `${y}-${m.padStart(2, '0')}-${d.padStart(2, '0')}`;
  }
  match = trimmed.match(ymd);
  if (match) {
    const [, y, m, d] = match;
    return `${y}-${m.padStart(2, '0')}-${d.padStart(2, '0')}`;
  }
  return null;
}

export function canFetchNhiaCcc(patientOrForm) {
  return !!(
    patientOrForm?.insured
    && patientOrForm?.nhis_active
    && patientOrForm?.insurance_id
    && String(patientOrForm.insurance_id).trim()
  );
}

/** Patient shape from admission recommendation confirm dialog */
export function nhiaPatientFromAdmission(admission) {
  if (!admission) return null;
  return {
    id: admission.patient_id,
    insured: admission.patient_insured,
    nhis_active: admission.patient_nhis_active,
    insurance_id: admission.patient_insurance_id,
  };
}

export function canGenerateNhiaCcc(patientOrForm) {
  return canFetchNhiaCcc(patientOrForm) && !!patientOrForm?.id;
}
