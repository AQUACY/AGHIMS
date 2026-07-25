/**
 * Shared confirmation and helpers for Get CCC on claim edit screens.
 */

import { rebaseDatesForCccPreview, rebaseDatesForServiceDateChange } from './claimCccDateRebase';

export const CLAIM_GET_CCC_WARNING =
  '<div style="line-height:1.45">'
  + '<div><b>This will update your Claim Check Code</b> and <b>rebase service dates</b> on this screen only.</div>'
  + '<div style="margin-top:10px"><b>What changes</b></div>'
  + '<ul style="margin:6px 0 0 18px; padding:0">'
  + '<li>Claim Check Code is replaced with the new CCC</li>'
  + '<li>Visit dates and line-item dates (medicines, investigations, procedures) may change</li>'
  + '</ul>'
  + '<div style="margin-top:10px"><b>OPD</b></div>'
  + '<div style="margin-top:4px">All visit + line-item dates become <b>today</b>.</div>'
  + '<div style="margin-top:10px"><b>IPD</b></div>'
  + '<ul style="margin:6px 0 0 18px; padding:0">'
  + '<li>Admission becomes <b>today</b></li>'
  + '<li>Discharge shifts by the <b>same length of stay</b></li>'
  + '<li>Each line keeps its <b>day offset</b> from the old admission</li>'
  + '<li>Lines outside the new stay are kept and <b>highlighted in yellow</b></li>'
  + '</ul>'
  + '<div style="margin-top:10px"><b>Safety</b></div>'
  + '<ul style="margin:6px 0 0 18px; padding:0">'
  + '<li><b>Nothing is saved</b> until you click <b>Save and Finalize</b></li>'
  + '<li>Refresh the page to undo this preview</li>'
  + '</ul>'
  + '<div style="margin-top:10px"><b>Continue?</b></div>'
  + '</div>';

/**
 * @param {import('quasar').QVueGlobals['dialog']} $q
 * @returns {Promise<boolean>}
 */
export function confirmClaimGetCcc($q) {
  return new Promise((resolve) => {
    $q.dialog({
      title: 'Get CCC',
      message: CLAIM_GET_CCC_WARNING,
      html: true,
      cancel: true,
      persistent: true,
      ok: {
        label: 'Yes',
        color: 'primary',
      },
      cancel: {
        label: 'No',
        flat: true,
      },
    })
      .onOk(() => resolve(true))
      .onCancel(() => resolve(false))
      .onDismiss(() => resolve(false));
  });
}

/**
 * @param {{ insured?: boolean, nhis_active?: boolean, insurance_id?: string, memberNo?: string, member_number?: string, ghanaCard?: string, ghana_card?: string }} source
 */
export function canFetchClaimCcc(source) {
  const ghanaCard = source?.ghanaCard || source?.ghana_card || '';
  const member = (
    source?.insurance_id
    || source?.memberNo
    || source?.member_number
    || ''
  ).toString().trim();

  // Prefer Ghana Card for CCC when present (HIN cannot generate CCC)
  const forCcc = (ghanaCard && String(ghanaCard).trim()) || member;
  if (!forCcc) return false;

  // Imported claims: any usable member/Ghana Card is enough
  if (source?.memberNo != null || source?.ghanaCard != null) {
    return !!forCcc;
  }
  return !!(
    source?.insured
    && source?.nhis_active
    && forCcc
  );
}

function applyRebasedLinesToEditForm(ctx, rebased) {
  if (!rebased) return;
  if (rebased.duration_of_spell != null && ctx.services) {
    ctx.services.duration_of_spell = rebased.duration_of_spell;
  }
  (rebased.investigations || []).forEach((line, i) => {
    const row = ctx.investigationsList.value[i];
    if (!row) return;
    row.date = line.date;
    row.outside_service_span = line.outside_span;
  });
  (rebased.prescriptions || []).forEach((line, i) => {
    const row = ctx.prescriptionsList.value[i];
    if (!row) return;
    row.date = line.date;
    row.outside_service_span = line.outside_span;
  });
  (rebased.procedures || []).forEach((line, i) => {
    const row = ctx.proceduresList.value[i];
    if (!row) return;
    row.date = line.date;
    row.outside_service_span = line.outside_span;
  });
}

function ghimsLineInputs(payload) {
  return {
    investigations: (payload.investigations || []).map((inv) => ({
      date: inv?.serviceDate,
      description: inv?._serviceName || inv?.gdrgCode,
      gdrg: inv?.gdrgCode,
    })),
    prescriptions: (payload.medicines || []).map((med) => ({
      date: med?.serviceDate,
      description: med?._serviceName,
      code: med?.medicineCode,
    })),
    procedures: (payload.procedures || []).map((proc) => ({
      date: proc?.serviceDate,
      description: proc?._serviceName || proc?.description,
      gdrg: proc?.gdrgCode,
    })),
  };
}

function applyRebasedLinesToGhimsPayload(payload, rebased) {
  if (!rebased) return;
  if (Array.isArray(rebased.date_of_service)) {
    payload.dateOfService = rebased.date_of_service;
  }
  (rebased.investigations || []).forEach((line, i) => {
    const row = payload.investigations?.[i];
    if (!row) return;
    row.serviceDate = line.date;
    row.outside_service_span = line.outside_span;
  });
  (rebased.prescriptions || []).forEach((line, i) => {
    const row = payload.medicines?.[i];
    if (!row) return;
    row.serviceDate = line.date;
    row.outside_service_span = line.outside_span;
  });
  (rebased.procedures || []).forEach((line, i) => {
    const row = payload.procedures?.[i];
    if (!row) return;
    row.serviceDate = line.date;
    row.outside_service_span = line.outside_span;
  });
}

/**
 * Rebase line-item dates when service/visit dates are edited on EditClaim.
 * @param {object} ctx
 * @param {{ first_visit?: string, second_visit?: string, dateOfService?: string[] }} previous
 */
export function applyServiceDateChangeToEditForm(ctx, previous) {
  const rebased = rebaseDatesForServiceDateChange({
    typeOfService: ctx.services.type_of_service,
    previousFirstVisit: previous?.first_visit,
    previousSecondVisit: previous?.second_visit,
    newFirstVisit: ctx.services.first_visit,
    newSecondVisit: ctx.services.second_visit,
    investigations: ctx.investigationsList.value,
    prescriptions: ctx.prescriptionsList.value,
    procedures: ctx.proceduresList.value,
  });
  if (!rebased) return false;
  applyRebasedLinesToEditForm(ctx, rebased);
  return true;
}

/**
 * Rebase line-item dates when dateOfService is edited on GHIMS imported claim.
 * @param {object} payload
 * @param {string[]} previousDateOfService
 */
export function applyServiceDateChangeToGhimsPayload(payload, previousDateOfService) {
  const lines = ghimsLineInputs(payload);
  const rebased = rebaseDatesForServiceDateChange({
    typeOfService: payload.typeOfService,
    previousDateOfService: previousDateOfService || [],
    previousFirstVisit: previousDateOfService?.[0],
    previousSecondVisit: previousDateOfService?.[1],
    newDateOfService: payload.dateOfService,
    newFirstVisit: payload.dateOfService?.[0],
    newSecondVisit: payload.dateOfService?.[1],
    investigations: lines.investigations,
    prescriptions: lines.prescriptions,
    procedures: lines.procedures,
  });
  if (!rebased) return false;
  applyRebasedLinesToGhimsPayload(payload, rebased);
  return true;
}

/**
 * Apply fetch-ccc API response to EditClaim form state.
 */
export function applyClaimFetchCccToEditForm(ctx, data) {
  const checkCode = data.claim_check_code || data.ccc;
  if (checkCode && ctx.claimMeta) {
    ctx.claimMeta.claim_check_code = checkCode;
  }
  if (data.member_no && !ctx.patientInfo.ghana_card) {
    // Do not overwrite HIN with Ghana Card used for CCC lookup
    ctx.patientInfo.member_number = data.member_no;
  }

  const rebased = rebaseDatesForCccPreview({
    typeOfService: ctx.services.type_of_service,
    firstVisit: ctx.services.first_visit,
    secondVisit: ctx.services.second_visit,
    thirdVisit: ctx.services.third_visit,
    fourthVisit: ctx.services.fourth_visit,
    investigations: ctx.investigationsList.value,
    prescriptions: ctx.prescriptionsList.value,
    procedures: ctx.proceduresList.value,
  });

  ctx.services.first_visit = rebased.first_visit;
  ctx.services.second_visit = rebased.second_visit;
  ctx.services.third_visit = rebased.third_visit;
  ctx.services.fourth_visit = rebased.fourth_visit;
  ctx.services.duration_of_spell = rebased.duration_of_spell;

  applyRebasedLinesToEditForm(ctx, rebased);
}

/**
 * Apply fetch-ccc API response to GHIMS imported claim payload.
 */
export function applyGhimsFetchCccToPayload(payload, data) {
  const checkCode = data.claim_check_code || data.ccc;
  if (checkCode) payload.claimCheckCode = checkCode;

  const rebased = rebaseDatesForCccPreview({
    typeOfService: payload.typeOfService,
    firstVisit: payload.dateOfService?.[0],
    secondVisit: payload.dateOfService?.[1],
    thirdVisit: payload.dateOfService?.[2],
    fourthVisit: payload.dateOfService?.[3],
    dateOfService: payload.dateOfService,
    ...ghimsLineInputs(payload),
  });

  applyRebasedLinesToGhimsPayload(payload, rebased);
}
