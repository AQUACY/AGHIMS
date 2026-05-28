/**
 * Shared confirmation and helpers for Get CCC on claim edit screens.
 */

import { rebaseDatesForCccPreview } from './claimCccDateRebase';

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
 * @param {{ insured?: boolean, nhis_active?: boolean, insurance_id?: string, memberNo?: string, member_number?: string }} source
 */
export function canFetchClaimCcc(source) {
  const member = (
    source?.insurance_id
    || source?.memberNo
    || source?.member_number
    || ''
  ).toString().trim();
  if (!member) return false;
  if (source?.memberNo) return true;
  return !!(
    source?.insured
    && source?.nhis_active
    && member
  );
}

/**
 * Apply fetch-ccc API response to EditClaim form state.
 */
export function applyClaimFetchCccToEditForm(ctx, data) {
  const checkCode = data.claim_check_code || data.ccc;
  if (checkCode && ctx.claimMeta) {
    ctx.claimMeta.claim_check_code = checkCode;
  }
  if (data.member_no) {
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
  });

  payload.dateOfService = rebased.date_of_service;
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
