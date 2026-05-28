/**
 * Rebase claim service/medicine/investigation dates when Get CCC is used.
 * OPD: all dates → anchor day (today).
 * IPD: preserve day-offsets from old admission; visit span shifts to anchor..anchor+length of stay.
 */

function parseIsoDate(value) {
  if (!value) return null;
  const raw = String(value).trim().split('T')[0];
  if (!raw) return null;
  const d = new Date(`${raw}T12:00:00`);
  return Number.isNaN(d.getTime()) ? null : d;
}

function toIsoDate(d) {
  if (!d) return '';
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

function todayIso() {
  return toIsoDate(new Date());
}

function diffDays(fromIso, toIso) {
  const a = parseIsoDate(fromIso);
  const b = parseIsoDate(toIso);
  if (!a || !b) return 0;
  return Math.round((b.getTime() - a.getTime()) / 86400000);
}

function addDays(iso, days) {
  const d = parseIsoDate(iso);
  if (!d) return '';
  d.setDate(d.getDate() + days);
  return toIsoDate(d);
}

function hasLineContent(row, kind) {
  if (!row) return false;
  if (kind === 'medicine') {
    return Boolean(String(row.description || '').trim() || String(row.code || '').trim());
  }
  if (kind === 'investigation' || kind === 'procedure') {
    return Boolean(String(row.description || '').trim() || String(row.gdrg || '').trim());
  }
  return Boolean(String(row.date || row.serviceDate || '').trim());
}

function rebaseLineDate(oldAnchorIso, newAnchorIso, spanStartIso, spanEndIso, oldDateIso) {
  if (!oldDateIso) {
    return { date: newAnchorIso, outside_span: false };
  }
  const offset = diffDays(oldAnchorIso, oldDateIso);
  const newDate = addDays(newAnchorIso, offset);
  const newD = parseIsoDate(newDate);
  const startD = parseIsoDate(spanStartIso);
  const endD = parseIsoDate(spanEndIso);
  const outside = Boolean(
    newD && startD && endD && (newD < startD || newD > endD)
  );
  return { date: newDate, outside_span: outside };
}

/**
 * @param {object} input
 * @returns {object}
 */
export function rebaseDatesForCccPreview(input) {
  const typeOfService = String(input?.typeOfService || 'OPD').trim().toUpperCase();
  const anchorDay = parseIsoDate(input?.anchorDay) ? toIsoDate(parseIsoDate(input.anchorDay)) : todayIso();
  const isIpd = typeOfService === 'IPD';

  const investigations = (input?.investigations || []).map((row, index) => ({
    index,
    row,
    kind: 'investigation',
  }));
  const prescriptions = (input?.prescriptions || []).map((row, index) => ({
    index,
    row,
    kind: 'medicine',
  }));
  const procedures = (input?.procedures || []).map((row, index) => ({
    index,
    row,
    kind: 'procedure',
  }));

  if (!isIpd) {
    const applyDay = (row, kind) => {
      if (!hasLineContent(row, kind)) {
        return { date: row.date || row.serviceDate || '', outside_span: false };
      }
      return { date: anchorDay, outside_span: false };
    };

    return {
      type_of_service: 'OPD',
      anchor_day: anchorDay,
      first_visit: anchorDay,
      second_visit: anchorDay,
      third_visit: input?.thirdVisit || '',
      fourth_visit: input?.fourthVisit || '',
      duration_of_spell: 0,
      date_of_service: [anchorDay],
      investigations: investigations.map(({ row }) => ({
        date: applyDay(row, 'investigation').date,
        outside_span: false,
      })),
      prescriptions: prescriptions.map(({ row }) => ({
        date: applyDay(row, 'medicine').date,
        outside_span: false,
      })),
      procedures: procedures.map(({ row }) => ({
        date: applyDay(row, 'procedure').date,
        outside_span: false,
      })),
    };
  }

  const firstFallback = Array.isArray(input?.dateOfService) ? input.dateOfService?.[0] : null;
  const secondFallback = Array.isArray(input?.dateOfService) ? input.dateOfService?.[1] : null;
  const oldFirst = parseIsoDate(input?.firstVisit || firstFallback);
  const oldSecond = parseIsoDate(input?.secondVisit || secondFallback);
  const oldAnchorIso = oldFirst ? toIsoDate(oldFirst) : (oldSecond ? toIsoDate(oldSecond) : anchorDay);
  let oldDischargeIso = oldSecond ? toIsoDate(oldSecond) : oldAnchorIso;
  if (parseIsoDate(oldDischargeIso) < parseIsoDate(oldAnchorIso)) {
    oldDischargeIso = oldAnchorIso;
  }

  const spanDays = Math.max(0, diffDays(oldAnchorIso, oldDischargeIso));
  const newFirst = anchorDay;
  const newSecond = addDays(anchorDay, spanDays);

  const dateOfServiceIn = Array.isArray(input?.dateOfService) ? input.dateOfService : [];
  let dateOfService;
  if (dateOfServiceIn.length >= 2) {
    dateOfService = dateOfServiceIn.map((dt, i) => {
      if (i === 0) return newFirst;
      if (i === 1) return newSecond;
      const rebased = rebaseLineDate(oldAnchorIso, newFirst, newFirst, newSecond, dt);
      return rebased.date;
    });
  } else if (dateOfServiceIn.length === 1) {
    dateOfService = [newFirst];
  } else {
    dateOfService = [newFirst, newSecond];
  }

  const mapLines = (entries, kind) =>
    entries.map(({ row }) => {
      const oldDate = row.date || row.serviceDate || '';
      if (!hasLineContent(row, kind)) {
        return { date: oldDate, outside_span: false };
      }
      return rebaseLineDate(oldAnchorIso, newFirst, newFirst, newSecond, oldDate);
    });

  return {
    type_of_service: 'IPD',
    anchor_day: anchorDay,
    first_visit: newFirst,
    second_visit: newSecond,
    third_visit: input?.thirdVisit || '',
    fourth_visit: input?.fourthVisit || '',
    duration_of_spell: spanDays,
    date_of_service: dateOfService,
    investigations: mapLines(investigations, 'investigation'),
    prescriptions: mapLines(prescriptions, 'medicine'),
    procedures: mapLines(procedures, 'procedure'),
    span_start: newFirst,
    span_end: newSecond,
  };
}
