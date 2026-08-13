<template>
  <q-page class="hms-page claim-edit-page" :class="{ 'revert-bar-visible': !loading && status === 'finalized' }">
    <HmsPageHeader :title="status === 'finalized' ? 'View imported claim' : 'Edit imported claim'">
      <template #actions>
        <div v-if="claimNav.hasNav" class="row items-center no-wrap q-gutter-xs claim-nav-controls">
          <q-btn
            outline
            color="primary"
            icon="chevron_left"
            label="Previous"
            dense
            :disable="!claimNav.prevId || loading"
            @click="goToAdjacentClaim(claimNav.prevId)"
          />
          <span class="text-body2 text-grey-8 text-weight-medium q-px-sm claim-nav-position">
            {{ claimNav.position }} of {{ claimNav.total }}
          </span>
          <q-btn
            outline
            color="primary"
            icon-right="chevron_right"
            label="Next"
            dense
            :disable="!claimNav.nextId || loading"
            @click="goToAdjacentClaim(claimNav.nextId)"
          />
        </div>
        <HmsButton variant="ghost" size="sm" @click="$router.back()">Back</HmsButton>
      </template>
    </HmsPageHeader>

    <div v-if="!loading" class="claim-hero">
      <div class="claim-hero__main">
        <div class="claim-hero__avatar" aria-hidden="true">{{ ghimsInitials }}</div>
        <div>
          <h2 class="claim-hero__name">{{ ghimsDisplayName }}</h2>
          <div class="claim-hero__meta">
            <span class="mono">{{ payload.claimID || `Item #${itemId}` }}</span>
            <span v-if="payload.hospitalRecNo">Rec {{ payload.hospitalRecNo }}</span>
            <span v-if="payload.memberNo" class="mono">{{ payload.memberNo }}</span>
            <span v-if="payload.claimCheckCode" class="mono">CCC {{ payload.claimCheckCode }}</span>
          </div>
        </div>
      </div>
      <div class="claim-hero__aside">
        <div class="claim-hero__badges">
          <q-badge
            :color="status === 'finalized' ? 'positive' : (status === 'flagged' ? 'negative' : (status === 'vetted' ? 'deep-purple' : (status === 'pharmacy_vetted' ? 'teal' : (status === 'doctor_vetted' ? 'indigo' : 'warning'))))"
            :label="status === 'vetted' ? 'pharmacy + doctor vetted' : (status === 'pharmacy_vetted' ? 'pharmacy vetted' : (status === 'doctor_vetted' ? 'doctor vetted' : status))"
          />
          <q-badge v-if="vetting.pharmacy_vetted" color="teal" label="Pharmacy" />
          <q-badge v-if="vetting.doctor_vetted" color="indigo" label="Doctor" />
          <q-badge
            v-if="ownership.assigned_to_name"
            color="blue-grey"
            :label="ownership.assignment_note ? `Owner: ${ownership.assigned_to_name} (${ownership.assignment_note})` : `Owner: ${ownership.assigned_to_name}`"
          />
          <q-badge v-else color="grey-5" text-color="grey-9" label="Unassigned" />
        </div>
        <div
          v-if="vetting.pharmacy_vetted_by_name || vetting.doctor_vetted_by_name"
          class="text-caption text-grey-7 q-mt-xs"
        >
          <span v-if="vetting.pharmacy_vetted_by_name">Pharmacy vetted by {{ vetting.pharmacy_vetted_by_name }}</span>
          <span v-if="vetting.pharmacy_vetted_by_name && vetting.doctor_vetted_by_name"> · </span>
          <span v-if="vetting.doctor_vetted_by_name">Doctor vetted by {{ vetting.doctor_vetted_by_name }}</span>
        </div>
      </div>
    </div>

    <q-card v-if="loading" flat bordered class="q-pa-md">
      <q-inner-loading showing color="primary" />
    </q-card>

    <q-banner
      v-if="!loading && status === 'finalized'"
      class="bg-amber-2 q-mb-md"
      rounded
    >
      <template #avatar>
        <q-icon name="lock_open" color="amber-9" />
      </template>
      <strong>Imported claim is finalized</strong>
      <div class="text-caption q-mt-xs">
        To make changes, click <strong>Revert to draft</strong> below. Then edit and use <strong>Save and Finalize</strong> when done.
      </div>
      <template #action>
        <q-btn
          flat
          color="primary"
          label="Revert to draft"
          :loading="reverting"
          @click="revertToDraft"
        />
      </template>
    </q-banner>

    <q-form
      v-if="!loading"
      @submit.prevent="saveAndFinalize"
      class="q-gutter-md"
      :inert="status === 'finalized' || undefined"
    >
      <q-banner v-if="claimitErrors.by_section?.other?.length" class="bg-orange-1 q-mb-md" rounded dense>
        <template #avatar><q-icon name="warning" color="orange" /></template>
        <div class="text-subtitle2">ClaimIT reported (fix in the section below if applicable):</div>
        <ul class="q-mt-xs q-mb-none q-pl-md">
          <li v-for="(msg, i) in claimitErrors.by_section.other" :key="i" class="text-body2">{{ msg }}</li>
        </ul>
      </q-banner>

      <q-banner
        v-if="status === 'flagged' && flagComment"
        class="bg-grey-2 q-mb-md"
        rounded
        dense
      >
        <template #avatar><q-icon name="comment" color="dark" /></template>
        <div class="text-subtitle2">Flag reason</div>
        <div class="text-body2">{{ flagComment }}</div>
      </q-banner>

      <AiClaimVettingPanel
        :item-id="itemId"
        :disabled="status === 'finalized'"
        :auto-run="false"
        class="q-mb-md"
        @payload-updated="onAiPayloadUpdated"
      />

      <q-card flat bordered>
        <q-card-section>
          <div class="text-h6 q-mb-md">Provider / Claim Header</div>
          <q-banner v-if="claimitErrors.by_section?.provider?.length" class="bg-orange-1 q-mb-md" rounded dense>
            <template #avatar><q-icon name="warning" color="orange" /></template>
            <div class="text-subtitle2">ClaimIT reported:</div>
            <ul class="q-mt-xs q-mb-none q-pl-md">
              <li v-for="(msg, i) in claimitErrors.by_section.provider" :key="i" class="text-body2">{{ msg }}</li>
            </ul>
          </q-banner>
          <div class="row q-col-gutter-md">
            <q-input v-model="payload.claimID" label="Claim ID" filled class="col-12 col-md-3" />
            <q-input v-model="payload.claimCheckCode" label="Claim Check Code" filled class="col-12 col-md-3" />
            <div class="col-12 col-md-6 row items-center q-gutter-sm">
              <q-btn
                color="secondary"
                icon="cloud_download"
                label="Get CCC"
                :loading="fetchingClaimCcc"
                :disable="status === 'finalized' || !canGetGhimsCcc || loading"
                @click="onGetGhimsClaimCcc"
              >
                <q-tooltip v-if="!canGetGhimsCcc">
                  Enter a member number to fetch CCC from NHIA
                </q-tooltip>
              </q-btn>
              <span class="text-caption text-grey-7">
                Preview only until Save and Finalize — refresh the page to undo.
              </span>
            </div>
            <q-input v-model="payload.preAuthorizationCodes" label="Pre-Authorization Codes" filled class="col-12 col-md-3" />
            <q-input v-model="payload.physicianID" label="Physician ID" filled class="col-12 col-md-3" />
          </div>
        </q-card-section>
      </q-card>

      <q-card flat bordered>
        <q-card-section>
          <div class="text-h6 q-mb-md">Client Information</div>
          <q-banner v-if="claimitErrors.by_section?.client?.length" class="bg-orange-1 q-mb-md" rounded dense>
            <template #avatar><q-icon name="warning" color="orange" /></template>
            <div class="text-subtitle2">ClaimIT reported:</div>
            <ul class="q-mt-xs q-mb-none q-pl-md">
              <li v-for="(msg, i) in claimitErrors.by_section.client" :key="i" class="text-body2">{{ msg }}</li>
            </ul>
          </q-banner>
          <div class="row q-col-gutter-md">
            <div class="col-12 col-md-3">
              <q-input v-model="payload.memberNo" label="Member No" filled>
                <template v-if="showConvertToHin" v-slot:append>
                  <q-btn
                    flat
                    dense
                    color="primary"
                    label="To HIN"
                    :loading="convertingGhanaCard"
                    :disable="status === 'finalized'"
                    @click="onConvertGhanaCardToHin"
                  >
                    <q-tooltip>ClaimIT rejects Ghana Cards — convert to HIN (keeps Ghana Card below)</q-tooltip>
                  </q-btn>
                </template>
              </q-input>
              <div v-if="isMemberNoGhanaCard" class="text-caption text-orange-8 q-mt-xs">
                Ghana Card detected — ClaimIT needs HIN or NHIA number
              </div>
            </div>
            <q-input
              v-if="payload.ghanaCard || showConvertToHin"
              v-model="payload.ghanaCard"
              label="Ghana Card"
              filled
              class="col-12 col-md-3"
              hint="Saved when converting Member No to HIN (used for Get CCC)"
            />
            <q-input v-model="payload.cardSerialNo" label="Card Serial No" filled class="col-12 col-md-3" />
            <q-input v-model="payload.hospitalRecNo" label="Hospital Record No" filled class="col-12 col-md-3" />
            <q-input v-model="payload.gender" label="Gender" filled class="col-12 col-md-3" />
            <q-input v-model="payload.surname" label="Surname" filled class="col-12 col-md-4" />
            <q-input v-model="payload.otherNames" label="Other Names" filled class="col-12 col-md-4" />
            <q-input v-model="payload.dateOfBirth" label="Date of Birth" type="date" filled class="col-12 col-md-4" />
          </div>
        </q-card-section>
      </q-card>

      <q-card flat bordered>
        <q-card-section>
          <div class="text-h6 q-mb-md">Services</div>
          <q-banner v-if="claimitErrors.by_section?.services?.length" class="bg-orange-1 q-mb-md" rounded dense>
            <template #avatar><q-icon name="warning" color="orange" /></template>
            <div class="text-subtitle2">ClaimIT reported:</div>
            <ul class="q-mt-xs q-mb-none q-pl-md">
              <li v-for="(msg, i) in claimitErrors.by_section.services" :key="i" class="text-body2">{{ msg }}</li>
            </ul>
          </q-banner>
          <div class="row q-col-gutter-md q-mb-md">
            <q-select
              v-model="payload.typeOfService"
              :options="serviceTypeOptions"
              emit-value
              map-options
              filled
              label="Type of Service"
              class="col-12 col-md-3"
            />
            <q-select
              v-model="payload.typeOfAttendance"
              :options="attendanceTypeOptions"
              emit-value
              map-options
              filled
              label="Type of Attendance"
              class="col-12 col-md-3"
            />
            <q-select
              v-model="payload.specialtyAttended"
              :options="specialtyAttendedOptions"
              emit-value
              map-options
              filled
              label="Specialty Attended"
              class="col-12 col-md-3"
              hint="Defaults from principal GDRG; change if needed"
            />
            <q-input v-model="payload.serviceOutcome" label="Service Outcome" filled class="col-12 col-md-3" />
            <q-input v-model="payload.principalGDRG" label="Principal GDRG" filled class="col-12 col-md-3" />
            <q-input v-model="payload.isDependant" label="Is Dependant (0/1)" filled class="col-12 col-md-3" />
            <q-input v-model="payload.isUnbundled" label="Is Unbundled (0/1)" filled class="col-12 col-md-3" />
            <q-input v-model="payload.includesPharmacy" label="Includes Pharmacy (0/1)" filled class="col-12 col-md-3" />
          </div>
          <div class="text-subtitle1 q-mb-sm">Date(s) of Service</div>
          <div v-for="(dt, i) in payload.dateOfService" :key="`date-${i}`" class="row q-col-gutter-sm q-mb-sm">
            <q-input v-model="payload.dateOfService[i]" type="date" filled dense class="col-12 col-md-4" />
            <q-btn
              v-if="status !== 'finalized'"
              flat
              dense
              color="negative"
              icon="delete"
              @click="payload.dateOfService.splice(i, 1)"
            />
          </div>
          <q-btn
            v-if="status !== 'finalized'"
            flat
            color="primary"
            icon="add"
            label="Add Service Date"
            @click="payload.dateOfService.push('')"
          />
        </q-card-section>
      </q-card>

      <q-card flat bordered>
        <q-card-section>
          <div class="row items-center q-mb-sm">
            <div class="text-h6">Diagnosis(es)</div>
            <q-space />
            <q-btn
              v-if="status !== 'finalized' && principalDiagnosisIndex >= 0"
              flat
              dense
              color="primary"
              icon="playlist_add"
              label="Apply template"
              :loading="loadingTemplates"
              @click="openApplyTemplate"
            >
              <q-tooltip>Fill investigations &amp; medicines from a saved diagnosis template</q-tooltip>
            </q-btn>
            <q-btn
              v-if="status !== 'finalized' && principalDiagnosisIndex >= 0"
              flat
              dense
              color="secondary"
              icon="save"
              label="Save as template"
              class="q-ml-xs"
              @click="openSaveTemplate"
            >
              <q-tooltip>Save current investigations &amp; medicines for this principal diagnosis</q-tooltip>
            </q-btn>
          </div>
          <q-banner v-if="claimitErrors.by_section?.diagnosis?.length" class="bg-orange-1 q-mb-md" rounded dense>
            <template #avatar><q-icon name="warning" color="orange" /></template>
            <div class="text-subtitle2">ClaimIT reported:</div>
            <ul class="q-mt-xs q-mb-none q-pl-md">
              <li v-for="(msg, i) in claimitErrors.by_section.diagnosis" :key="i" class="text-body2">{{ msg }}</li>
            </ul>
          </q-banner>
          <div v-for="(d, i) in payload.diagnoses" :key="`diag-${i}`" class="row q-col-gutter-sm q-mb-sm">
            <div class="col-12 text-caption text-grey-7 text-weight-medium">Diagnosis Section {{ i + 1 }}</div>
            <q-select
              :model-value="d._selectedOption || d.icd10"
              :options="diagnosisSearchOptions"
              option-label="optionLabel"
              use-input
              input-debounce="250"
              fill-input
              hide-selected
              clearable
              dense
              filled
              label="Diagnosis (search by code/name)"
              class="col-12 col-md-6"
              @filter="filterDiagnosisSearch"
              @update:model-value="(val) => onDiagnosisSelect(i, val)"
            />
            <q-input v-model="d._diagnosisName" label="Diagnosis Name" filled dense class="col-12 col-md-6" />
            <q-select
              v-if="(d._drgOptions || []).length > 1"
              :model-value="d.gdrgCode"
              :options="d._drgOptions || []"
              emit-value
              map-options
              clearable
              filled
              dense
              label="Mapped DRG options"
              hint="Pick a mapped DRG, or type your own in GDRG"
              class="col-12 col-md-3"
              @update:model-value="(val) => onMappedDrgSelect(i, val)"
            />
            <q-input
              v-model="d.gdrgCode"
              label="GDRG"
              filled
              dense
              class="col-12 col-md-2"
              hint="Editable"
              @update:model-value="() => onDiagnosisGdrgEdited(i)"
            />
            <q-checkbox
              :model-value="principalDiagnosisIndex === i"
              label="Principal diagnosis"
              dense
              class="col-12 col-md-3"
              @update:model-value="(checked) => setPrincipalDiagnosis(i, checked)"
            />
            <q-input v-model="d.icd10" label="ICD10" filled dense class="col-12 col-md-2" />
            <q-input v-model="d.diagnosis" label="Diagnosis" filled dense class="col-12 col-md-7" />
            <q-btn
              v-if="status !== 'finalized'"
              flat
              dense
              color="negative"
              icon="delete"
              @click="removeDiagnosis(i)"
            />
          </div>
          <q-btn
            v-if="status !== 'finalized'"
            flat
            color="primary"
            icon="add"
            label="Add Diagnosis"
            @click="payload.diagnoses.push({ icd10:'', gdrgCode:'', diagnosis:'' })"
          />
        </q-card-section>
      </q-card>

      <q-card flat bordered>
        <q-card-section>
          <div class="text-h6 q-mb-sm">Investigations</div>
          <q-banner v-if="claimitErrors.by_section?.investigations?.length" class="bg-orange-1 q-mb-md" rounded dense>
            <template #avatar><q-icon name="warning" color="orange" /></template>
            <div class="text-subtitle2">ClaimIT reported:</div>
            <ul class="q-mt-xs q-mb-none q-pl-md">
              <li v-for="(msg, i) in claimitErrors.by_section.investigations" :key="i" class="text-body2">{{ msg }}</li>
            </ul>
          </q-banner>
          <div
            v-for="(inv, i) in payload.investigations"
            :key="`inv-${i}`"
            class="row q-col-gutter-sm q-mb-sm"
            :class="claimLineSectionClass(inv) || undefined"
          >
            <div v-if="isOutsideServiceSpan(inv)" class="col-12">
              <q-chip
                dense
                size="sm"
                color="amber-2"
                text-color="amber-10"
                icon="event_busy"
                label="Outside service span (after Get CCC)"
              />
            </div>
            <q-input v-model="inv.serviceDate" type="date" label="Date" filled dense class="col-12 col-md-4" />
            <q-select
              :model-value="inv._selectedOption || inv.gdrgCode"
              :options="investigationSearchOptions"
              option-label="optionLabel"
              use-input
              input-debounce="250"
              fill-input
              hide-selected
              clearable
              dense
              filled
              label="Investigation (search by name/code)"
              class="col-12 col-md-7"
              @filter="filterInvestigationSearch"
              @update:model-value="(val) => onInvestigationSelect(i, val)"
            />
            <q-input v-model="inv._serviceName" label="Service Name" filled dense class="col-12 col-md-7" />
            <q-input v-model="inv.gdrgCode" label="GDRG Code" filled dense class="col-12 col-md-4" />
            <q-btn
              v-if="status !== 'finalized'"
              flat
              dense
              color="negative"
              icon="delete"
              @click="payload.investigations.splice(i,1)"
            />
          </div>
          <q-btn
            v-if="status !== 'finalized'"
            flat
            color="primary"
            icon="add"
            label="Add Investigation"
            @click="addInvestigationRow"
          />
        </q-card-section>
      </q-card>

      <q-card flat bordered>
        <q-card-section>
          <div class="text-h6 q-mb-sm">Medicines</div>
          <q-banner v-if="claimitErrors.by_section?.medicines?.length" class="bg-orange-1 q-mb-md" rounded dense>
            <template #avatar><q-icon name="warning" color="orange" /></template>
            <div class="text-subtitle2">ClaimIT reported:</div>
            <ul class="q-mt-xs q-mb-none q-pl-md">
              <li v-for="(msg, i) in claimitErrors.by_section.medicines" :key="i" class="text-body2">{{ msg }}</li>
            </ul>
          </q-banner>
          <div
            v-for="(m, i) in payload.medicines"
            :key="`med-${i}`"
            class="row q-col-gutter-sm q-mb-sm medicine-section-row"
            :class="claimLineSectionClass(m) || undefined"
          >
            <div class="col-12 row items-center q-gutter-xs">
              <div class="text-caption text-grey-7 text-weight-medium">Medicine Section {{ i + 1 }}</div>
              <q-chip
                v-if="isMedicineNotCovered(m)"
                dense
                size="sm"
                color="red-2"
                text-color="negative"
                icon="warning"
                label="Not covered by insurance"
              />
              <q-chip
                v-else-if="isOutsideServiceSpan(m)"
                dense
                size="sm"
                color="amber-2"
                text-color="amber-10"
                icon="event_busy"
                label="Outside service span (after Get CCC)"
              />
            </div>
            <q-select
              :model-value="m._selectedOption || m.medicineCode"
              :options="medicineSearchOptions"
              option-label="optionLabel"
              use-input
              input-debounce="250"
              fill-input
              hide-selected
              clearable
              dense
              filled
              label="Medicine (search by name/code)"
              class="col-12 col-md-4"
              @filter="filterMedicineSearch"
              @update:model-value="(val) => onMedicineSelect(i, val)"
            />
            <q-input v-model="m._serviceName" label="Medicine Name" filled dense class="col-12 col-md-4" />
            <q-input v-model="m.medicineCode" label="Medicine Code" filled dense class="col-12 col-md-2" />
            <q-input v-model="m.dispensedQty" label="Qty" filled dense class="col-12 col-md-1" />
            <q-input v-model="m.serviceDate" type="date" label="Date" filled dense class="col-12 col-md-2" />
            <q-input
              v-model="m.prescription.dose"
              label="Dose"
              filled
              dense
              class="col-12 col-md-2"
              @update:model-value="() => syncPrescriptionUnparsed(m)"
            />
            <q-input
              v-model="m.prescription.frequency"
              label="Frequency"
              filled
              dense
              class="col-12 col-md-2"
              @update:model-value="() => syncPrescriptionUnparsed(m)"
            />
            <q-input
              v-model="m.prescription.duration"
              label="Duration"
              filled
              dense
              class="col-12 col-md-2"
              hint="Type number, then space / Tab / leave field for “days”"
              @update:model-value="() => onDurationInput(m)"
              @blur="() => onDurationCommit(m)"
              @keydown.tab="() => onDurationCommit(m)"
            />
            <q-input v-model="m.prescription.unparsed" label="Unparsed" filled dense class="col-12 col-md-10" />
            <q-btn
              v-if="status !== 'finalized'"
              flat
              dense
              color="negative"
              icon="delete"
              @click="payload.medicines.splice(i,1)"
            />
          </div>
          <q-btn
            v-if="status !== 'finalized'"
            flat
            color="primary"
            icon="add"
            label="Add Medicine"
            @click="addMedicine"
          />
        </q-card-section>
      </q-card>

      <q-card flat bordered>
        <q-card-section>
          <div class="text-h6 q-mb-sm">Procedures</div>
          <q-banner v-if="claimitErrors.by_section?.procedures?.length" class="bg-orange-1 q-mb-md" rounded dense>
            <template #avatar><q-icon name="warning" color="orange" /></template>
            <div class="text-subtitle2">ClaimIT reported:</div>
            <ul class="q-mt-xs q-mb-none q-pl-md">
              <li v-for="(msg, i) in claimitErrors.by_section.procedures" :key="i" class="text-body2">{{ msg }}</li>
            </ul>
          </q-banner>
          <div
            v-for="(p, i) in payload.procedures"
            :key="`proc-${i}`"
            class="row q-col-gutter-sm q-mb-sm"
            :class="claimLineSectionClass(p) || undefined"
          >
            <div v-if="isOutsideServiceSpan(p)" class="col-12">
              <q-chip
                dense
                size="sm"
                color="amber-2"
                text-color="amber-10"
                icon="event_busy"
                label="Outside service span (after Get CCC)"
              />
            </div>
            <q-input v-model="p.serviceDate" type="date" label="Date" filled dense class="col-12 col-md-2" />
            <q-select
              :model-value="p._selectedOption || p.gdrgCode"
              :options="procedureSearchOptions"
              option-label="optionLabel"
              use-input
              input-debounce="250"
              fill-input
              hide-selected
              clearable
              dense
              filled
              label="Procedure (search by name/code)"
              class="col-12 col-md-5"
              @filter="filterProcedureSearch"
              @update:model-value="(val) => onProcedureSelect(i, val)"
            />
            <q-input v-model="p._serviceName" label="Procedure Name" filled dense class="col-12 col-md-4" />
            <q-checkbox
              v-if="showProcedurePrincipalPicker"
              :model-value="!!p.is_principal"
              label="Principal"
              dense
              class="col-12 col-md-2"
              :disable="!(p.description || p._serviceName || p.gdrgCode)"
              @update:model-value="(checked) => setPrincipalProcedure(i, checked)"
            />
            <q-input
              v-model="p.gdrgCode"
              label="GDRG Code"
              filled
              dense
              class="col-12 col-md-2"
              @blur="onProcedureGdrgChange(i)"
            />
            <q-select
              :model-value="p.diagnosis || p.icd10"
              :options="diagnosisSearchOptions"
              option-label="optionLabel"
              use-input
              input-debounce="250"
              fill-input
              hide-selected
              clearable
              dense
              filled
              label="Diagnosis (search ICD-10)"
              class="col-12 col-md-6"
              @filter="filterDiagnosisSearch"
              @update:model-value="(val) => onProcedureDiagnosisSelect(i, val)"
            />
            <q-input v-model="p.icd10" label="ICD10" filled dense class="col-12 col-md-2" />
            <q-input v-model="p.description" label="Description" filled dense class="col-12 col-md-5" />
            <q-input v-model="p.diagnosis" label="Diagnosis text" filled dense class="col-12 col-md-10" />
            <q-btn
              v-if="status !== 'finalized'"
              flat
              dense
              color="negative"
              icon="delete"
              @click="removeProcedure(i)"
            />
          </div>
          <q-btn
            v-if="status !== 'finalized'"
            flat
            color="primary"
            icon="add"
            label="Add Procedure"
            @click="addProcedureRow"
          />
        </q-card-section>
      </q-card>

      <!-- Client Claim Summary -->
      <q-card flat bordered>
        <q-card-section>
          <div class="text-h6 q-mb-md">Client Claim Summary</div>
          <q-table
            :rows="claimSummary"
            :columns="summaryColumns"
            row-key="type"
            flat
            dense
          >
            <template v-slot:body-cell-tariff_amount="props">
              <q-td :props="props" class="text-right">
                {{ formatCurrency(props.value) }}
              </q-td>
            </template>
          </q-table>
          <div class="text-h6 q-mt-md text-right">
            Total: {{ formatCurrency(totalClaimAmount) }}
          </div>
        </q-card-section>
      </q-card>

      <div class="row q-gutter-md">
        <q-btn
          v-if="status !== 'finalized' && canVetPharmacy"
          :color="vetting.pharmacy_vetted ? 'orange-9' : 'teal-7'"
          text-color="white"
          unelevated
          :icon="vetting.pharmacy_vetted ? 'undo' : 'local_pharmacy'"
          :label="vetting.pharmacy_vetted ? 'Revert pharmacy vet' : 'Vet by Pharmacy'"
          :loading="vettingPharmacy"
          @click="vetByPharmacy"
        >
          <q-tooltip v-if="vetting.pharmacy_vetted_by_name">
            Pharmacy vetted by {{ vetting.pharmacy_vetted_by_name }}
          </q-tooltip>
        </q-btn>
        <q-btn
          v-if="status !== 'finalized' && canVetDoctor"
          :color="vetting.doctor_vetted ? 'orange-9' : 'indigo-7'"
          text-color="white"
          unelevated
          :icon="vetting.doctor_vetted ? 'undo' : 'medical_services'"
          :label="vetting.doctor_vetted ? 'Revert doctor vet' : 'Vet by Doctor'"
          :loading="vettingDoctor"
          @click="vetByDoctor"
        >
          <q-tooltip v-if="vetting.doctor_vetted_by_name">
            Doctor vetted by {{ vetting.doctor_vetted_by_name }}
          </q-tooltip>
        </q-btn>
        <q-btn v-if="status !== 'finalized'" type="submit" color="primary" label="Save and Finalize" :loading="saving" />
        <q-btn v-if="status !== 'finalized'" color="negative" :label="status === 'flagged' ? 'Flagged' : 'Flag claim'" :disable="status === 'flagged'" outline :loading="saving" @click="flagClaim" />
      </div>
    </q-form>

    <div
      v-if="!loading && status === 'finalized'"
      class="revert-claim-fixed-bar row items-center justify-center q-pa-sm shadow-6"
    >
      <span class="q-mr-md text-weight-medium">Imported claim is finalized.</span>
      <q-btn
        color="primary"
        label="Revert to draft"
        :loading="reverting"
        icon="undo"
        @click="revertToDraft"
      />
    </div>

    <!-- Apply diagnosis template -->
    <q-dialog v-model="showApplyTemplateDialog" persistent>
      <q-card style="min-width: 520px; max-width: 720px">
        <q-card-section>
          <div class="text-h6">Apply diagnosis template</div>
          <div class="text-caption text-grey-7">
            Principal: {{ principalDiagnosisLabel }}
          </div>
        </q-card-section>
        <q-card-section v-if="!selectedApplyTemplate">
          <q-banner
            v-if="!templatesHaveExactMatch && (matchedTemplates || []).length"
            dense
            rounded
            class="bg-orange-1 text-orange-10 q-mb-md"
          >
            <template #avatar><q-icon name="info" color="orange" /></template>
            No templates are mapped to this diagnosis. You can still choose any template below and pick its investigations and medicines.
          </q-banner>
          <div v-if="!(matchedTemplates || []).length" class="text-grey-7">
            No templates available. Create one from Claims → Diagnosis Templates, or Save as template from this claim.
          </div>
          <q-list v-else bordered separator>
            <q-item
              v-for="t in matchedTemplates"
              :key="t.id"
              clickable
              v-ripple
              @click="selectApplyTemplate(t)"
            >
              <q-item-section>
                <q-item-label>{{ t.name }}</q-item-label>
                <q-item-label caption>
                  {{ (t.investigations || []).length }} investigations · {{ (t.medicines || []).length }} medicines
                  <span v-if="matchedTemplateIds.has(t.id)" class="text-positive"> · matched</span>
                  <span v-else class="text-orange-8"> · not mapped to this diagnosis</span>
                </q-item-label>
              </q-item-section>
              <q-item-section side>
                <q-icon name="chevron_right" />
              </q-item-section>
            </q-item>
          </q-list>
        </q-card-section>
        <q-card-section v-else>
          <div class="text-subtitle2 q-mb-sm">{{ selectedApplyTemplate.name }} — tick items to apply</div>
          <div class="text-caption text-grey-7 q-mb-sm">Unticked items will not be added to the claim.</div>
          <div v-if="(applyInvChoices || []).length" class="q-mb-md">
            <div class="text-weight-medium q-mb-xs">Investigations</div>
            <q-input
              v-model="applyTemplateServiceDate"
              type="date"
              filled
              dense
              class="q-mb-sm"
              label="Investigation service date"
              hint="Used for all selected investigations"
            />
            <q-option-group v-model="selectedApplyInvIndexes" :options="applyInvChoices" type="checkbox" color="primary" />
          </div>
          <div v-if="(applyMedChoices || []).length">
            <div class="text-weight-medium q-mb-xs">Medicines</div>
            <div class="text-caption text-grey-7 q-mb-sm">Set a date for each medicine you tick.</div>
            <div
              v-for="opt in applyMedChoices"
              :key="`apply-med-${opt.value}`"
              class="row items-center q-col-gutter-sm q-mb-sm"
            >
              <div class="col-auto">
                <q-checkbox
                  :model-value="selectedApplyMedIndexes.includes(opt.value)"
                  @update:model-value="(v) => toggleApplyMed(opt.value, v)"
                />
              </div>
              <div class="col">
                <div class="text-body2">{{ opt.label }}</div>
              </div>
              <div class="col-12 col-sm-4">
                <q-input
                  v-model="applyMedServiceDates[opt.value]"
                  type="date"
                  filled
                  dense
                  label="Date"
                  :disable="!selectedApplyMedIndexes.includes(opt.value)"
                />
              </div>
            </div>
          </div>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Cancel" @click="closeApplyTemplate" />
          <q-btn
            v-if="selectedApplyTemplate"
            flat
            label="Back"
            @click="selectedApplyTemplate = null"
          />
          <q-btn
            v-if="selectedApplyTemplate"
            color="primary"
            label="Apply selected"
            @click="confirmApplyTemplate"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Save diagnosis template from claim -->
    <q-dialog v-model="showSaveTemplateDialog" persistent>
      <q-card style="min-width: 520px; max-width: 720px">
        <q-card-section>
          <div class="text-h6">Save as diagnosis template</div>
          <div class="text-caption text-grey-7">{{ principalDiagnosisLabel }}</div>
        </q-card-section>
        <q-card-section class="q-gutter-md">
          <q-input v-model="saveTemplateForm.name" filled label="Template name *" />
          <q-input v-model="saveTemplateForm.match_keywords" filled dense label="Match keywords" hint="comma-separated; used to find this template later" />
          <div class="text-caption">Tick investigations &amp; medicines to include</div>
          <div v-if="(saveInvChoices || []).length">
            <div class="text-weight-medium q-mb-xs">Investigations</div>
            <q-option-group v-model="selectedSaveInvIndexes" :options="saveInvChoices" type="checkbox" color="primary" />
          </div>
          <div v-if="(saveMedChoices || []).length">
            <div class="text-weight-medium q-mb-xs">Medicines</div>
            <q-option-group v-model="selectedSaveMedIndexes" :options="saveMedChoices" type="checkbox" color="primary" />
          </div>
          <q-toggle v-model="saveTemplateForm.is_shared" label="Share with other claims users" />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Cancel" v-close-popup />
          <q-btn color="primary" label="Save template" :loading="savingTemplate" @click="confirmSaveTemplate" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue';
import HmsPageHeader from '../components/ui/HmsPageHeader.vue';
import HmsButton from '../components/ui/HmsButton.vue';
import AiClaimVettingPanel from '../components/claims/AiClaimVettingPanel.vue';
import { useRoute, useRouter } from 'vue-router';
import { useQuasar } from 'quasar';
import { claimsAPI, priceListAPI } from '../services/api';
import { useAuthStore } from '../stores/auth';
import {
  confirmClaimGetCcc,
  canFetchClaimCcc,
  applyGhimsFetchCccToPayload,
  applyServiceDateChangeToGhimsPayload,
} from '../utils/claimGetCcc';
import { isGhanaCard, memberNoForCcc, normalizeGhanaCard } from '../utils/memberIdentity';
import {
  buildTemplateMatchFromPrincipal,
  investigationFromTemplateItem,
  medicineFromTemplateItem,
  serializeInvestigationForTemplate,
  serializeMedicineForTemplate,
  mergeMatchedAndAllTemplates,
} from '../utils/claimDiagnosisTemplates';
import {
  asMedicineList,
  isMedicineNotCovered,
  isOutsideServiceSpan,
  normalizeInsuranceCovered,
  claimLineSectionClass,
} from '../utils/claimMedicineCoverage';
import { getGhimsNavPosition } from '../utils/claimNav';
import { sortClaimMedicinesByDateAsc } from '../utils/claimMedicineSort';

const route = useRoute();
const $router = useRouter();
const $q = useQuasar();
const authStore = useAuthStore();
const loading = ref(true);
const saving = ref(false);
const reverting = ref(false);
const vettingPharmacy = ref(false);
const vettingDoctor = ref(false);
const vetting = reactive({
  pharmacy_vetted: false,
  pharmacy_vetted_at: null,
  pharmacy_vetted_by_name: null,
  doctor_vetted: false,
  doctor_vetted_at: null,
  doctor_vetted_by_name: null,
});
const ownership = reactive({
  assigned_to_id: null,
  assigned_to_name: null,
  assignment_note: null,
});
const canVetPharmacy = computed(() =>
  authStore.canAccess(['Pharmacy', 'Pharmacy Head', 'Claims', 'Admin'])
);
const canVetDoctor = computed(() =>
  authStore.canAccess(['Doctor', 'PA', 'Claims', 'Admin'])
);

function applyVettingFromItem(data = {}) {
  if (data.status) status.value = data.status;
  vetting.pharmacy_vetted = !!data.pharmacy_vetted || !!data.pharmacy_vetted_at;
  vetting.pharmacy_vetted_at = data.pharmacy_vetted_at || null;
  vetting.pharmacy_vetted_by_name = data.pharmacy_vetted_by_name || null;
  vetting.doctor_vetted = !!data.doctor_vetted || !!data.doctor_vetted_at;
  vetting.doctor_vetted_at = data.doctor_vetted_at || null;
  vetting.doctor_vetted_by_name = data.doctor_vetted_by_name || null;
  ownership.assigned_to_id = data.assigned_to_id ?? null;
  ownership.assigned_to_name = data.assigned_to_name || null;
  ownership.assignment_note = data.assignment_note || null;
}

async function vetByPharmacy() {
  if (!itemId.value || status.value === 'finalized') return;
  const clearing = !!vetting.pharmacy_vetted;
  if (clearing) {
    const ok = await new Promise((resolve) => {
      $q.dialog({
        title: 'Revert pharmacy vet',
        message: 'Remove pharmacy vetted status from this claim?',
        cancel: true,
        persistent: true,
      }).onOk(() => resolve(true)).onCancel(() => resolve(false)).onDismiss(() => resolve(false));
    });
    if (!ok) return;
  }
  vettingPharmacy.value = true;
  try {
    const res = await claimsAPI.vetGhimsImportItem(itemId.value, 'pharmacy', clearing);
    applyVettingFromItem(res.data || {});
    $q.notify({
      type: 'positive',
      message: clearing ? 'Pharmacy vet removed' : 'Pharmacy vet recorded',
    });
  } catch (e) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Failed to update pharmacy vet' });
  } finally {
    vettingPharmacy.value = false;
  }
}

async function vetByDoctor() {
  if (!itemId.value || status.value === 'finalized') return;
  const clearing = !!vetting.doctor_vetted;
  if (clearing) {
    const ok = await new Promise((resolve) => {
      $q.dialog({
        title: 'Revert doctor vet',
        message: 'Remove doctor vetted status from this claim?',
        cancel: true,
        persistent: true,
      }).onOk(() => resolve(true)).onCancel(() => resolve(false)).onDismiss(() => resolve(false));
    });
    if (!ok) return;
  }
  vettingDoctor.value = true;
  try {
    const res = await claimsAPI.vetGhimsImportItem(itemId.value, 'doctor', clearing);
    applyVettingFromItem(res.data || {});
    $q.notify({
      type: 'positive',
      message: clearing ? 'Doctor vet removed' : 'Doctor vet recorded',
    });
  } catch (e) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Failed to update doctor vet' });
  } finally {
    vettingDoctor.value = false;
  }
}
const fetchingClaimCcc = ref(false);
const convertingGhanaCard = ref(false);
const loadingTemplates = ref(false);
const savingTemplate = ref(false);
const showApplyTemplateDialog = ref(false);
const showSaveTemplateDialog = ref(false);
const matchedTemplates = ref([]);
const matchedTemplateIds = ref(new Set());
const templatesHaveExactMatch = ref(false);
const selectedApplyTemplate = ref(null);
const applyTemplateServiceDate = ref('');
const applyMedServiceDates = ref([]);
const selectedApplyInvIndexes = ref([]);
const selectedApplyMedIndexes = ref([]);
const selectedSaveInvIndexes = ref([]);
const selectedSaveMedIndexes = ref([]);
const saveTemplateForm = ref({ name: '', match_keywords: '', is_shared: true });
const status = ref('draft');
const flagComment = ref('');
const principalDiagnosisIndex = ref(-1);
const itemId = ref(Number(route.params.itemId));
const diagnosisSearchOptions = ref([]);
const investigationSearchOptions = ref([]);

const serviceTypeOptions = [
  { label: 'OPD', value: 'OPD' },
  { label: 'IPD', value: 'IPD' },
];
const attendanceTypeOptions = [
  { label: 'EAE', value: 'EAE' },
  { label: 'CFU', value: 'CFU' },
  { label: 'ANC', value: 'ANC' },
  { label: 'PNC', value: 'PNC' },
];
const SPECIALTY_ATTENDED_CODES = [
  'ASUR', 'DENT', 'ENTH', 'MEDI', 'OBGY', 'OPDC', 'OPTH', 'ORTH', 'PAED', 'PSUR', 'RSUR',
];
const specialtyAttendedOptions = computed(() => {
  const base = SPECIALTY_ATTENDED_CODES.map((code) => ({ label: code, value: code }));
  const current = String(payload.specialtyAttended || '').trim().toUpperCase();
  if (current && !SPECIALTY_ATTENDED_CODES.includes(current)) {
    return [{ label: current, value: current }, ...base];
  }
  return base;
});
const procedureSearchOptions = ref([]);
const medicineSearchOptions = ref([]);
const payload = reactive({
  claimID: '', claimCheckCode: '', memberNo: '', ghanaCard: '', hin: '',
  surname: '', otherNames: '', dateOfBirth: '',
  typeOfService: '', typeOfAttendance: '', specialtyAttended: '', diagnoses: [], medicines: [],
});

const claimNav = computed(() => getGhimsNavPosition(itemId.value));

const ghimsDisplayName = computed(() => {
  const parts = [payload.otherNames, payload.surname].map((x) => String(x || '').trim()).filter(Boolean);
  return parts.join(' ') || 'Imported claim';
});

const ghimsInitials = computed(() => {
  const bits = ghimsDisplayName.value.split(/\s+/).filter(Boolean);
  if (!bits.length) return 'IC';
  if (bits.length === 1) return bits[0].slice(0, 2).toUpperCase();
  return `${bits[0][0] || ''}${bits[bits.length - 1][0] || ''}`.toUpperCase();
});

function goToAdjacentClaim(targetId) {
  if (!targetId || loading.value) return;
  $router.push({ path: `/claims/ghims-import/item/${targetId}` });
}

const isMemberNoGhanaCard = computed(() => isGhanaCard(payload.memberNo));
const showConvertToHin = computed(
  () => isMemberNoGhanaCard.value || (isGhanaCard(payload.ghanaCard) && !String(payload.memberNo || '').trim())
);

const canGetGhimsCcc = computed(() =>
  canFetchClaimCcc({
    memberNo: payload.memberNo,
    ghanaCard: payload.ghanaCard,
  })
);

const serviceDateSnapshot = ref([]);
let skipServiceDateRebase = false;

function syncGhimsServiceDateSnapshot() {
  serviceDateSnapshot.value = [...(payload.dateOfService || [])];
}

function onGhimsServiceDatesChanged() {
  if (skipServiceDateRebase || loading.value) return;

  const prev = serviceDateSnapshot.value;
  const curr = payload.dateOfService || [];
  if (JSON.stringify(prev) === JSON.stringify(curr)) return;

  const type = String(payload.typeOfService || 'OPD').toUpperCase();
  const newFirst = curr[0] || '';
  if (!newFirst) {
    syncGhimsServiceDateSnapshot();
    return;
  }

  if (type === 'IPD') {
    const firstChanged = (prev[0] || '') !== (curr[0] || '');
    const secondChanged = (prev[1] || '') !== (curr[1] || '');
    if (!firstChanged && !secondChanged) {
      syncGhimsServiceDateSnapshot();
      return;
    }
  } else if ((prev[0] || '') === newFirst) {
    syncGhimsServiceDateSnapshot();
    return;
  }

  skipServiceDateRebase = true;
  applyServiceDateChangeToGhimsPayload(payload, prev);
  syncGhimsServiceDateSnapshot();
  skipServiceDateRebase = false;
}

watch(
  () => payload.dateOfService?.map((d) => d || ''),
  onGhimsServiceDatesChanged,
  { deep: true }
);

function emptyClaimitBySection() {
  return {
    client: [],
    provider: [],
    services: [],
    procedures: [],
    diagnosis: [],
    investigations: [],
    medicines: [],
    other: [],
  };
}

const claimitErrors = ref({ messages: [], by_section: emptyClaimitBySection() });

const claimSummary = ref([
  { index: 0, type: 'A In-Patient', gdrg_code: '', tariff_amount: 0 },
  { index: 1, type: 'B Out-Patient', gdrg_code: '', tariff_amount: 0 },
  { index: 2, type: 'C Investigations', gdrg_code: '', tariff_amount: 0 },
  { index: 3, type: 'D Pharmacy', gdrg_code: '', tariff_amount: 0 },
  { index: 4, type: 'TOTAL', gdrg_code: '', tariff_amount: 0 },
]);

const summaryColumns = [
  { name: 'type', label: 'Type of Service', field: 'type', align: 'left' },
  { name: 'gdrg_code', label: 'G-DRG/Code', field: 'gdrg_code', align: 'left' },
  { name: 'tariff_amount', label: 'Tariff Amount', field: 'tariff_amount', align: 'right' },
];

const totalClaimAmount = computed(() =>
  claimSummary.value
    .filter((item) => item.type !== 'TOTAL')
    .reduce((sum, item) => sum + (Number(item.tariff_amount) || 0), 0)
);

const getClaimPrice = (item) => {
  if (!item) return 0;
  return Number(item.claim_amount ?? item.nhia_app ?? item.base_rate ?? item.insured_price ?? 0) || 0;
};

function withServiceOptionLabel(item) {
  if (!item || typeof item !== 'object') return item;
  if (item.optionLabel) return item;
  const name = item.service_name || item.item_name || '';
  const code = item.g_drg_code || item.item_code || '';
  const optionLabel = (name && code) ? `${name} (${code})` : (name || code);
  return { ...item, optionLabel };
}

function withProductOptionLabel(item) {
  if (!item || typeof item !== 'object') return item;
  if (item.optionLabel) return item;
  const name = item.product_name || item.item_name || '';
  const code = item.medication_code || item.item_code || '';
  const optionLabel = (name && code) ? `${name} (${code})` : (name || code);
  return { ...item, optionLabel };
}

const formatCurrency = (amount) => {
  if (amount == null || Number.isNaN(Number(amount))) return 'N/A';
  return new Intl.NumberFormat('en-GH', { style: 'currency', currency: 'GHS' }).format(Number(amount));
};

function applyClaimSummaryFromApi(summary) {
  if (!summary) {
    recalculateClaimSummary();
    return;
  }
  claimSummary.value[0].tariff_amount = summary.inpatient_amount || 0;
  claimSummary.value[1].tariff_amount = summary.outpatient_amount || 0;
  claimSummary.value[2].tariff_amount = summary.investigations_amount || 0;
  claimSummary.value[3].tariff_amount = summary.pharmacy_amount || 0;
  claimSummary.value[4].tariff_amount = summary.total_amount ?? totalClaimAmount.value;
}

function recalculateClaimSummary() {
  const tos = String(payload.typeOfService || 'OPD').toUpperCase();

  let procedureTotal = 0;
  for (const proc of payload.procedures || []) {
    const code = String(proc.gdrgCode || '').trim();
    if (!code) continue;
    if (proc._selectedOption) procedureTotal += getClaimPrice(proc._selectedOption);
  }

  let inpatient = tos === 'IPD' ? procedureTotal : 0;
  let outpatient = tos === 'OPD' ? procedureTotal : 0;

  let investigationsTotal = 0;
  for (const inv of payload.investigations || []) {
    const code = String(inv.gdrgCode || '').trim();
    if (!code) continue;
    if (inv._selectedOption) investigationsTotal += getClaimPrice(inv._selectedOption);
  }

  let pharmacyTotal = 0;
  for (const med of payload.medicines || []) {
    const code = String(med.medicineCode || '').trim();
    let qty = Number(med.dispensedQty) || 0;
    if (code && qty > 0 && med._selectedOption) {
      pharmacyTotal += getClaimPrice(med._selectedOption) * qty;
    }
  }

  claimSummary.value[0].tariff_amount = inpatient;
  claimSummary.value[1].tariff_amount = outpatient;
  claimSummary.value[2].tariff_amount = investigationsTotal;
  claimSummary.value[3].tariff_amount = pharmacyTotal;
  claimSummary.value[4].tariff_amount = inpatient + outpatient + investigationsTotal + pharmacyTotal;
}

function addInvestigationRow() {
  payload.investigations.push({
    serviceDate: firstClaimServiceDate(),
    gdrgCode: '',
  });
}

function addMedicine() {
  payload.medicines.push({
    medicineCode: '',
    dispensedQty: '',
    serviceDate: firstClaimServiceDate(),
    prescription: { dose: '', frequency: '', duration: '', unparsed: '' },
  });
}

function syncIncludesPharmacy() {
  payload.includesPharmacy = (payload.medicines || []).length > 0 ? '1' : '0';
}

const filterInvestigationSearch = (val, update) => {
  update(async () => {
    if (!val || val.length < 1) {
      investigationSearchOptions.value = [];
      return;
    }
    try {
      const res = await priceListAPI.search(val, undefined, 'procedure');
      investigationSearchOptions.value = (res.data || []).map((item) => ({
        ...item,
        optionLabel: `${item.service_name || item.item_name || ''} (${item.g_drg_code || item.item_code || ''})`,
      }));
    } catch (_) {
      investigationSearchOptions.value = [];
    }
  });
};

const filterDiagnosisSearch = (val, update) => {
  update(async () => {
    if (!val || val.length < 1) {
      diagnosisSearchOptions.value = [];
      return;
    }
    try {
      const res = await priceListAPI.searchIcd10(val, 50);
      diagnosisSearchOptions.value = (res.data || []).map((item) => ({
        ...item,
        optionLabel: `${item.icd10_code || ''} - ${item.icd10_description || ''}`.trim(),
      }));
    } catch (_) {
      diagnosisSearchOptions.value = [];
    }
  });
};

const filterProcedureSearch = (val, update) => {
  update(async () => {
    if (!val || val.length < 1) {
      procedureSearchOptions.value = [];
      return;
    }
    try {
      const [procRes, surgRes] = await Promise.all([
        priceListAPI.search(val, undefined, 'procedure'),
        priceListAPI.search(val, undefined, 'surgery'),
      ]);
      const merged = [...(procRes.data || []), ...(surgRes.data || [])];
      procedureSearchOptions.value = merged.map((item) => ({
        ...item,
        optionLabel: `${item.service_name || item.item_name || ''} (${item.g_drg_code || item.item_code || ''})`,
      }));
    } catch (_) {
      procedureSearchOptions.value = [];
    }
  });
};

const filterMedicineSearch = (val, update) => {
  update(async () => {
    if (!val || val.length < 1) {
      medicineSearchOptions.value = [];
      return;
    }
    try {
      const res = await priceListAPI.search(val, undefined, 'product');
      medicineSearchOptions.value = (res.data || []).map((item) => ({
        ...item,
        optionLabel: `${item.product_name || item.item_name || ''} (${item.medication_code || item.item_code || ''})`,
      }));
    } catch (_) {
      medicineSearchOptions.value = [];
    }
  });
};

function onInvestigationSelect(index, val) {
  const row = payload.investigations[index];
  if (!row) return;
  if (!val) {
    row.gdrgCode = '';
    row._serviceName = '';
    row._selectedOption = null;
    recalculateClaimSummary();
    return;
  }
  if (typeof val === 'object') {
    row.gdrgCode = val.g_drg_code || val.item_code || row.gdrgCode || '';
    row._serviceName = val.service_name || val.item_name || row._serviceName || '';
    row._selectedOption = withServiceOptionLabel(val);
    if (!row.serviceDate) {
      row.serviceDate = firstClaimServiceDate();
    }
    recalculateClaimSummary();
    return;
  }
}

async function onDiagnosisSelect(index, val) {
  const row = payload.diagnoses[index];
  if (!row) return;
  if (!val) {
    row.icd10 = '';
    row.diagnosis = '';
    row._diagnosisName = '';
    row.gdrgCode = '';
    row._drgOptions = [];
    row._selectedOption = null;
    return;
  }
  if (typeof val === 'object') {
    row.icd10 = val.icd10_code || row.icd10 || '';
    row.diagnosis = val.icd10_description || row.diagnosis || '';
    row._diagnosisName = val.icd10_description || row._diagnosisName || '';
    row._selectedOption = val;
    row._drgOptions = [];

    let drgItems = [];
    const fromSearch = Array.isArray(val.drg_codes) ? val.drg_codes.filter(Boolean) : [];
    if (fromSearch.length) {
      drgItems = fromSearch.map((code) =>
        typeof code === 'string' ? { drg_code: code, drg_description: '' } : code
      );
    }
    if (row.icd10) {
      try {
        const res = await priceListAPI.getDrgCodesFromIcd10(row.icd10);
        if (Array.isArray(res.data) && res.data.length) {
          drgItems = res.data;
        }
      } catch (_) {
        /* keep search-based options */
      }
    }

    const seen = new Set();
    row._drgOptions = (drgItems || [])
      .map((d) => {
        const code = String(d.drg_code || d || '').trim();
        if (!code || seen.has(code)) return null;
        seen.add(code);
        const desc = String(d.drg_description || '').trim();
        return { label: desc ? `${code} — ${desc}` : code, value: code };
      })
      .filter(Boolean);

    if (row._drgOptions.length === 1) {
      row.gdrgCode = row._drgOptions[0].value;
    } else if (row._drgOptions.length > 1) {
      const existing = String(row.gdrgCode || '').trim();
      const stillValid = row._drgOptions.some((o) => o.value === existing);
      row.gdrgCode = stillValid ? existing : '';
      $q.notify({
        type: 'info',
        message: `This ICD-10 maps to ${row._drgOptions.length} DRGs — select one or type your own in GDRG`,
        timeout: 3500,
      });
    } else {
      row.gdrgCode = val.gdrg_code || val.g_drg_code || val.drg_code || val.gdrgCode || '';
    }
    if (principalDiagnosisIndex.value === index) {
      payload.principalGDRG = row.gdrgCode || '';
      syncSpecialtyFromPrincipalDiagnosis();
    }
  }
}

function specialtyFromGdrg(code) {
  const raw = String(code || '').trim().toUpperCase();
  if (!raw) return '';
  const prefix = raw.slice(0, 4);
  // ZOOM* GDRGs (e.g. dressings) always use OPDC specialty for ClaimIT
  if (prefix === 'ZOOM') return 'OPDC';
  return prefix;
}

function syncSpecialtyFromPrincipalDiagnosis() {
  const idx = principalDiagnosisIndex.value;
  const row = idx >= 0 ? payload.diagnoses?.[idx] : null;
  const gdrg = String(row?.gdrgCode || payload.principalGDRG || '').trim();
  const specialty = specialtyFromGdrg(gdrg);
  if (specialty) {
    payload.specialtyAttended = specialty;
  }
}

function onMappedDrgSelect(index, val) {
  const row = payload.diagnoses[index];
  if (!row) return;
  row.gdrgCode = val || '';
  if (principalDiagnosisIndex.value === index) {
    payload.principalGDRG = row.gdrgCode || '';
    syncSpecialtyFromPrincipalDiagnosis();
  }
}

function onDiagnosisGdrgEdited(index) {
  if (principalDiagnosisIndex.value !== index) return;
  const row = payload.diagnoses[index];
  payload.principalGDRG = row?.gdrgCode || '';
  syncSpecialtyFromPrincipalDiagnosis();
}

function moveDiagnosisToFirst(index) {
  const list = payload.diagnoses || [];
  if (index <= 0 || index >= list.length) return;
  const [row] = list.splice(index, 1);
  list.unshift(row);
}

function reorderDiagnosesWithPrincipalFirst({ syncSpecialty = false } = {}) {
  const list = payload.diagnoses || [];
  if (!list.length) {
    principalDiagnosisIndex.value = -1;
    return;
  }
  const principalGdrg = String(payload.principalGDRG || '').trim();
  if (!principalGdrg) {
    principalDiagnosisIndex.value = -1;
    return;
  }
  const idx = list.findIndex((d) => String(d?.gdrgCode || '').trim() === principalGdrg);
  if (idx > 0) moveDiagnosisToFirst(idx);
  principalDiagnosisIndex.value = idx >= 0 ? 0 : -1;
  if (syncSpecialty) {
    syncSpecialtyFromPrincipalDiagnosis();
  } else if (String(payload.specialtyAttended || '').trim().toUpperCase() === 'ZOOM') {
    // Legacy claims may still have ZOOM stored — normalize to OPDC
    payload.specialtyAttended = 'OPDC';
  }
}

function setPrincipalDiagnosis(index, checked) {
  if (!checked) {
    if (principalDiagnosisIndex.value === index) {
      principalDiagnosisIndex.value = -1;
      payload.principalGDRG = '';
    }
    return;
  }
  moveDiagnosisToFirst(index);
  principalDiagnosisIndex.value = 0;
  const row = payload.diagnoses[0];
  payload.principalGDRG = row?.gdrgCode || '';
  syncSpecialtyFromPrincipalDiagnosis();
}

const principalDiagnosisLabel = computed(() => {
  const idx = principalDiagnosisIndex.value;
  const row = idx >= 0 ? payload.diagnoses?.[idx] : null;
  if (!row) return '';
  const name = row._diagnosisName || row.diagnosis || '';
  const icd = row.icd10 || '';
  const gdrg = row.gdrgCode || '';
  return [name, icd, gdrg].filter(Boolean).join(' · ');
});

const applyInvChoices = computed(() =>
  (selectedApplyTemplate.value?.investigations || []).map((item, i) => ({
    label: `${item.serviceName || item._serviceName || 'Investigation'} (${item.gdrgCode || item.gdrg || '—'})`,
    value: i,
  }))
);
const applyMedChoices = computed(() =>
  (selectedApplyTemplate.value?.medicines || []).map((item, i) => ({
    label: `${item.serviceName || item._serviceName || 'Medicine'} (${item.medicineCode || item.code || '—'})`,
    value: i,
  }))
);

const saveInvChoices = computed(() =>
  (payload.investigations || [])
    .map((inv, i) => ({ inv, i }))
    .filter(({ inv }) => String(inv?.gdrgCode || inv?._serviceName || '').trim())
    .map(({ inv, i }) => ({
      label: `${inv._serviceName || 'Investigation'} (${inv.gdrgCode || '—'})`,
      value: i,
    }))
);
const saveMedChoices = computed(() =>
  (payload.medicines || [])
    .map((med, i) => ({ med, i }))
    .filter(({ med }) => String(med?.medicineCode || med?._serviceName || '').trim())
    .map(({ med, i }) => ({
      label: `${med._serviceName || 'Medicine'} (${med.medicineCode || '—'})`,
      value: i,
    }))
);

function getPrincipalDiagnosisSnapshot() {
  const idx = principalDiagnosisIndex.value;
  const row = idx >= 0 ? payload.diagnoses?.[idx] : null;
  if (!row) return null;
  return {
    icd10: row.icd10 || '',
    diagnosis: row._diagnosisName || row.diagnosis || '',
    gdrg: row.gdrgCode || '',
  };
}

async function openApplyTemplate() {
  const snap = getPrincipalDiagnosisSnapshot();
  if (!snap) {
    $q.notify({ type: 'warning', message: 'Select a principal diagnosis first' });
    return;
  }
  loadingTemplates.value = true;
  selectedApplyTemplate.value = null;
  try {
    const [matchRes, listRes] = await Promise.all([
      claimsAPI.matchDiagnosisTemplates(snap),
      claimsAPI.listDiagnosisTemplates({ active_only: true }),
    ]);
    const merged = mergeMatchedAndAllTemplates(matchRes.data || [], listRes.data || []);
    matchedTemplates.value = merged.templates;
    matchedTemplateIds.value = merged.matchedIds;
    templatesHaveExactMatch.value = merged.hasExactMatch;
    showApplyTemplateDialog.value = true;
  } catch (e) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Failed to load templates' });
  } finally {
    loadingTemplates.value = false;
  }
}

function applySelectTemplate(t) {
  selectedApplyTemplate.value = t;
  const defaultDate = firstClaimServiceDate();
  applyTemplateServiceDate.value = defaultDate;
  const invCount = (t.investigations || []).length;
  const medCount = (t.medicines || []).length;
  selectedApplyInvIndexes.value = Array.from({ length: invCount }, (_, i) => i);
  selectedApplyMedIndexes.value = Array.from({ length: medCount }, (_, i) => i);
  applyMedServiceDates.value = Array.from({ length: medCount }, () => defaultDate);
}

function toggleApplyMed(index, checked) {
  const set = new Set(selectedApplyMedIndexes.value || []);
  if (checked) set.add(index);
  else set.delete(index);
  selectedApplyMedIndexes.value = [...set].sort((a, b) => a - b);
  if (checked && !String(applyMedServiceDates.value[index] || '').trim()) {
    const dates = [...(applyMedServiceDates.value || [])];
    dates[index] = applyTemplateServiceDate.value || firstClaimServiceDate();
    applyMedServiceDates.value = dates;
  }
}

function selectApplyTemplate(t) {
  if (!t) return;
  if (matchedTemplateIds.value.has(t.id)) {
    applySelectTemplate(t);
    return;
  }
  $q.dialog({
    title: 'Template not mapped to this diagnosis',
    message:
      'This template does not map to the selected diagnosis. You can still go ahead and choose it, then pick which investigations and medicines to add.',
    cancel: { label: 'Cancel', flat: true },
    ok: { label: 'Continue', color: 'primary', unelevated: true },
    persistent: true,
  }).onOk(() => {
    applySelectTemplate(t);
  });
}

function closeApplyTemplate() {
  showApplyTemplateDialog.value = false;
  selectedApplyTemplate.value = null;
  applyTemplateServiceDate.value = '';
  applyMedServiceDates.value = [];
  matchedTemplates.value = [];
  matchedTemplateIds.value = new Set();
  templatesHaveExactMatch.value = false;
}

function confirmApplyTemplate() {
  const t = selectedApplyTemplate.value;
  if (!t) return;
  const invs = t.investigations || [];
  const meds = t.medicines || [];
  const pickInv = new Set(selectedApplyInvIndexes.value || []);
  const pickMed = new Set(selectedApplyMedIndexes.value || []);
  const invServiceDate = String(applyTemplateServiceDate.value || firstClaimServiceDate() || '').trim();

  if (pickInv.size && !invServiceDate) {
    $q.notify({ type: 'warning', message: 'Choose a service date for investigations' });
    return;
  }
  for (const i of pickMed) {
    const medDate = String(applyMedServiceDates.value?.[i] || '').trim();
    if (!medDate) {
      $q.notify({ type: 'warning', message: 'Set a date for each selected medicine' });
      return;
    }
  }

  for (const i of pickInv) {
    const item = invs[i];
    if (!item) continue;
    const row = investigationFromTemplateItem(item, invServiceDate);
    if (!row.gdrgCode && !row._serviceName) continue;
    // Skip exact duplicate gdrg already present
    const exists = (payload.investigations || []).some(
      (x) => String(x.gdrgCode || '').trim() === row.gdrgCode && row.gdrgCode
    );
    if (!exists) payload.investigations.push(row);
  }
  for (const i of pickMed) {
    const item = meds[i];
    if (!item) continue;
    const medDate = String(applyMedServiceDates.value?.[i] || '').trim();
    const row = medicineFromTemplateItem(item, medDate);
    if (!row.medicineCode && !row._serviceName) continue;
    const exists = (payload.medicines || []).some(
      (x) => String(x.medicineCode || '').trim() === row.medicineCode && row.medicineCode
    );
    if (!exists) {
      payload.medicines.push(row);
      syncPrescriptionUnparsed(row);
    }
  }
  syncIncludesPharmacy();
  recalculateClaimSummary();
  closeApplyTemplate();
  $q.notify({ type: 'positive', message: 'Template items applied — review and edit as needed' });
}

function openSaveTemplate() {
  const snap = getPrincipalDiagnosisSnapshot();
  if (!snap) {
    $q.notify({ type: 'warning', message: 'Select a principal diagnosis first' });
    return;
  }
  const match = buildTemplateMatchFromPrincipal(snap);
  saveTemplateForm.value = {
    name: snap.diagnosis || snap.icd10 || 'Diagnosis template',
    match_keywords: match.match_keywords,
    is_shared: true,
    ...match,
  };
  selectedSaveInvIndexes.value = saveInvChoices.value.map((o) => o.value);
  selectedSaveMedIndexes.value = saveMedChoices.value.map((o) => o.value);
  showSaveTemplateDialog.value = true;
}

async function confirmSaveTemplate() {
  const name = String(saveTemplateForm.value.name || '').trim();
  if (!name) {
    $q.notify({ type: 'warning', message: 'Template name is required' });
    return;
  }
  const invPick = new Set(selectedSaveInvIndexes.value || []);
  const medPick = new Set(selectedSaveMedIndexes.value || []);
  const investigations = (payload.investigations || [])
    .filter((_, i) => invPick.has(i))
    .map(serializeInvestigationForTemplate)
    .filter((x) => x.gdrgCode || x.serviceName);
  const medicines = (payload.medicines || [])
    .filter((_, i) => medPick.has(i))
    .map(serializeMedicineForTemplate)
    .filter((x) => x.medicineCode || x.serviceName);
  if (!investigations.length && !medicines.length) {
    $q.notify({ type: 'warning', message: 'Tick at least one investigation or medicine' });
    return;
  }
  savingTemplate.value = true;
  try {
    await claimsAPI.createDiagnosisTemplate({
      name,
      description: `From claim ${payload.claimID || ''}`.trim(),
      match_icd10: saveTemplateForm.value.match_icd10,
      match_diagnosis: saveTemplateForm.value.match_diagnosis,
      match_gdrg_prefix: saveTemplateForm.value.match_gdrg_prefix,
      match_keywords: saveTemplateForm.value.match_keywords,
      sample_icd10: saveTemplateForm.value.sample_icd10,
      sample_diagnosis: saveTemplateForm.value.sample_diagnosis,
      sample_gdrg: saveTemplateForm.value.sample_gdrg,
      investigations,
      medicines,
      is_shared: !!saveTemplateForm.value.is_shared,
      is_active: true,
    });
    showSaveTemplateDialog.value = false;
    $q.notify({ type: 'positive', message: 'Diagnosis template saved' });
  } catch (e) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Failed to save template' });
  } finally {
    savingTemplate.value = false;
  }
}

function removeDiagnosis(index) {
  payload.diagnoses.splice(index, 1);
  if (principalDiagnosisIndex.value === index) {
    principalDiagnosisIndex.value = -1;
    payload.principalGDRG = '';
    return;
  }
  if (principalDiagnosisIndex.value > index) {
    principalDiagnosisIndex.value -= 1;
  }
}

function onProcedureSelect(index, val) {
  const row = payload.procedures[index];
  if (!row) return;
  if (!val) {
    row.gdrgCode = '';
    row._serviceName = '';
    row.description = '';
    row.icd10 = '';
    row.diagnosis = '';
    row.is_principal = false;
    row._selectedOption = null;
    syncPrincipalFromProcedures();
    recalculateClaimSummary();
    return;
  }
  if (typeof val === 'object') {
    row.gdrgCode = val.g_drg_code || val.item_code || row.gdrgCode || '';
    row._serviceName = val.service_name || val.item_name || row._serviceName || '';
    if (!row.description) row.description = row._serviceName || '';
    row._selectedOption = withServiceOptionLabel(val);
    if (!row.serviceDate) {
      row.serviceDate = firstClaimServiceDate();
    }
    if (row.icd10 && row.gdrgCode) {
      upsertDiagnosisFromProcedure(row);
    }
    syncPrincipalFromProcedures();
    recalculateClaimSummary();
    return;
  }
}

function firstClaimServiceDate() {
  const dates = (payload.dateOfService || [])
    .map((d) => String(d || '').trim())
    .filter(Boolean)
    .sort();
  return dates[0] || '';
}

const filledProcedures = computed(() =>
  (payload.procedures || []).filter(
    (p) => String(p.description || p._serviceName || p.gdrgCode || '').trim()
  )
);

const showProcedurePrincipalPicker = computed(() => filledProcedures.value.length >= 2);

function upsertDiagnosisFromProcedure(proc) {
  const icd10 = String(proc.icd10 || '').trim();
  const description = String(proc.diagnosis || '').trim();
  const gdrg = String(proc.gdrgCode || '').trim();
  if (!icd10 && !description) return;

  let row = (payload.diagnoses || []).find(
    (d) => String(d.icd10 || '').trim().toUpperCase() === icd10.toUpperCase() && icd10
  );
  if (!row) {
    row = (payload.diagnoses || []).find(
      (d) => !String(d.diagnosis || d._diagnosisName || '').trim() && !String(d.icd10 || '').trim()
    );
  }
  if (!row) {
    row = { icd10: '', gdrgCode: '', diagnosis: '', _diagnosisName: '' };
    payload.diagnoses.push(row);
  }
  row.icd10 = icd10 || row.icd10;
  row.diagnosis = description || row.diagnosis;
  row._diagnosisName = description || row._diagnosisName || '';
  if (gdrg) row.gdrgCode = gdrg;
}

function syncPrincipalFromProcedures() {
  const filled = filledProcedures.value;
  if (!filled.length) return;

  if (filled.length === 1) {
    (payload.procedures || []).forEach((p) => {
      p.is_principal = p === filled[0];
    });
  }

  let principal = filled.find((p) => p.is_principal);
  if (!principal && filled.length === 1) {
    principal = filled[0];
    principal.is_principal = true;
  }
  if (!principal) return;

  const gdrg = String(principal.gdrgCode || '').trim();
  if (gdrg) {
    payload.principalGDRG = gdrg;
  }
  if (principal.icd10 || principal.diagnosis) {
    upsertDiagnosisFromProcedure(principal);
  }

  const principalIcd = String(principal.icd10 || '').trim().toUpperCase();
  const principalGdrg = String(principal.gdrgCode || '').trim();
  let principalIdx = -1;
  (payload.diagnoses || []).forEach((d, i) => {
    const matchIcd = principalIcd && String(d.icd10 || '').trim().toUpperCase() === principalIcd;
    const matchGdrg = principalGdrg && String(d.gdrgCode || '').trim() === principalGdrg;
    if (matchIcd || (matchGdrg && principalIdx < 0)) {
      if (principalIdx < 0) principalIdx = i;
    }
  });
  if (principalIdx >= 0) {
    moveDiagnosisToFirst(principalIdx);
    principalDiagnosisIndex.value = 0;
    payload.principalGDRG = payload.diagnoses[0]?.gdrgCode || gdrg || payload.principalGDRG;
  }
}

function setPrincipalProcedure(index, checked) {
  const row = payload.procedures[index];
  if (!row) return;
  if (!checked) {
    row.is_principal = false;
    return;
  }
  (payload.procedures || []).forEach((p, i) => {
    p.is_principal = i === index;
  });
  syncPrincipalFromProcedures();
}

function onProcedureGdrgChange(index) {
  const row = payload.procedures[index];
  if (!row) return;
  if (row.icd10 || row.diagnosis) {
    upsertDiagnosisFromProcedure(row);
  }
  if (row.is_principal || filledProcedures.value.length === 1) {
    syncPrincipalFromProcedures();
  }
  recalculateClaimSummary();
}

function onProcedureDiagnosisSelect(index, val) {
  const row = payload.procedures[index];
  if (!row) return;
  if (val == null || val === '') {
    row.diagnosis = '';
    row.icd10 = '';
    syncPrincipalFromProcedures();
    return;
  }
  if (typeof val === 'object') {
    row.diagnosis = val.icd10_description || '';
    row.icd10 = val.icd10_code || '';
    upsertDiagnosisFromProcedure(row);
    const filled = filledProcedures.value;
    if (filled.length === 1 || row.is_principal || !filled.some((p) => p.is_principal)) {
      row.is_principal = true;
      (payload.procedures || []).forEach((p, i) => {
        if (i !== index) p.is_principal = false;
      });
    }
    syncPrincipalFromProcedures();
  }
}

function addProcedureRow() {
  payload.procedures.push({
    serviceDate: firstClaimServiceDate(),
    gdrgCode: '',
    description: '',
    icd10: '',
    diagnosis: '',
    is_principal: false,
  });
  syncPrincipalFromProcedures();
}

function removeProcedure(index) {
  payload.procedures.splice(index, 1);
  syncPrincipalFromProcedures();
  recalculateClaimSummary();
}

function onMedicineSelect(index, val) {
  const row = payload.medicines[index];
  if (!row) return;
  if (!val) {
    row.medicineCode = '';
    row._serviceName = '';
    row._selectedOption = null;
    recalculateClaimSummary();
    return;
  }
  if (typeof val === 'object') {
    row.medicineCode = val.medication_code || val.item_code || row.medicineCode || '';
    row._serviceName = val.product_name || val.item_name || row._serviceName || '';
    row.insurance_covered = val.insurance_covered || 'yes';
    row._selectedOption = withProductOptionLabel(val);
    if (!row.serviceDate) {
      row.serviceDate = firstClaimServiceDate();
    }
    recalculateClaimSummary();
    if (normalizeInsuranceCovered(row.insurance_covered) === 'no') {
      $q.notify({
        type: 'warning',
        message: `Medicine section ${index + 1} is not covered by insurance. It is highlighted in red and must be changed or removed before saving.`,
        position: 'top',
      });
    }
    return;
  }
}

function validateCoveredMedicinesOrThrow(source) {
  const bad = [];
  asMedicineList(source).forEach((m, index) => {
    if (isMedicineNotCovered(m)) bad.push(index + 1);
  });
  if (bad.length) {
    throw new Error(`Medicine not covered by insurance. Change or remove medicine section(s): ${bad.join(', ')}`);
  }
}

function parsePrescriptionUnparsed(text) {
  const raw = String(text || '').trim();
  if (!raw) return null;
  const compact = raw.replace(/\s+/g, ' ');
  const m = compact.match(
    /^\s*([^,]+?)\s*,\s*([^x×]+?)\s*(?:[x×]\s*|\bfor\s+)?(\d+(?:\.\d+)?\s*(?:day|days|week|weeks|month|months|hour|hours|hr|hrs)\b)?\s*$/i
  );
  if (!m) return null;
  return {
    dose: (m[1] || '').trim(),
    frequency: (m[2] || '').trim(),
    duration: (m[3] || '').trim(),
  };
}

function buildUnparsedFromPrescription(prescription, { commitDuration = true } = {}) {
  const dose = String(prescription?.dose || '').trim();
  const frequency = String(prescription?.frequency || '').trim();
  const duration = commitDuration
    ? normalizeDuration(prescription?.duration, { commit: true })
    : String(prescription?.duration || '').trim();
  if (!dose && !frequency && !duration) return '';
  if (!frequency) return dose;
  if (!duration) return `${dose}, ${frequency}`;
  return `${dose}, ${frequency} X ${duration}`;
}

function syncPrescriptionUnparsed(med) {
  if (!med) return;
  if (!med.prescription || typeof med.prescription !== 'object') {
    med.prescription = { dose: '', frequency: '', duration: '', unparsed: '' };
  }
  med.prescription.dose = normalizeDose(med.prescription.dose);
  med.prescription.duration = normalizeDuration(med.prescription.duration, { commit: true });
  med.prescription.unparsed = buildUnparsedFromPrescription(med.prescription, { commitDuration: true });
}

/** While typing duration: only append “days” after a trailing space (or already has a unit). */
function onDurationInput(med) {
  if (!med) return;
  if (!med.prescription || typeof med.prescription !== 'object') {
    med.prescription = { dose: '', frequency: '', duration: '', unparsed: '' };
  }
  const raw = String(med.prescription.duration || '');
  // Space after number(s) → append days now
  if (/^\s*\d+(?:\.\d+)?\s+$/.test(raw)) {
    med.prescription.duration = normalizeDuration(raw, { commit: true });
  }
  med.prescription.unparsed = buildUnparsedFromPrescription(med.prescription, { commitDuration: false });
}

/** Tab / blur / leave field → finalize “N days”. */
function onDurationCommit(med) {
  syncPrescriptionUnparsed(med);
}

function normalizeDose(value) {
  const raw = String(value || '').trim();
  if (!raw) return '';
  const compact = raw.replace(/\s+/g, ' ');
  const match = compact.match(/^(\d+(?:\.\d+)?)\s*([A-Za-z][A-Za-z0-9\/%.-]*)$/);
  if (!match) return compact.toUpperCase();
  const amount = match[1];
  const unit = match[2].toUpperCase();
  return `${amount} ${unit}`;
}

function normalizeDuration(value, { commit = false } = {}) {
  const raw = String(value || '');
  if (!raw.trim()) return '';
  const endsWithSpaceAfterNumber = /^\s*\d+(?:\.\d+)?\s+$/.test(raw);
  const compact = raw.trim().replace(/\s+/g, ' ');
  const numberOnly = compact.match(/^(\d+(?:\.\d+)?)$/);
  if (numberOnly) {
    if (commit || endsWithSpaceAfterNumber) {
      return `${numberOnly[1]} days`;
    }
    // Still typing digits (e.g. "2" before "20") — do not append days yet
    return numberOnly[1];
  }
  const dayBased = compact.match(/^(\d+(?:\.\d+)?)\s*day(?:s)?$/i);
  if (dayBased) return `${dayBased[1]} days`;
  return compact;
}

function validateMedicineDoses(medicines) {
  const invalidSectionIndexes = [];
  (medicines || []).forEach((med, index) => {
    const dose = normalizeDose(med?.prescription?.dose);
    if (!dose) {
      invalidSectionIndexes.push(index + 1);
      return;
    }
    if (med?.prescription && typeof med.prescription === 'object') {
      med.prescription.dose = dose;
    }
  });
  return invalidSectionIndexes;
}

function validateDiagnosisGdrg(diagnoses) {
  const invalidSectionIndexes = [];
  (diagnoses || []).forEach((diag, index) => {
    const gdrgCode = String(diag?.gdrgCode || '').trim();
    const icd10 = String(diag?.icd10 || '').trim();
    const diagnosis = String(diag?.diagnosis || '').trim();
    const hasAnyDiagnosisData = Boolean(icd10 || diagnosis || gdrgCode);
    if (hasAnyDiagnosisData && !gdrgCode) invalidSectionIndexes.push(index + 1);
  });
  return invalidSectionIndexes;
}

function validateServiceDates(clean) {
  const missingMedicineDates = [];
  const missingInvestigationDates = [];
  const missingProcedureDates = [];

  (clean?.medicines || []).forEach((m, index) => {
    const serviceDate = String(m?.serviceDate || '').trim();
    const hasData = Boolean(
      String(m?.medicineCode || '').trim()
      || String(m?.dispensedQty || '').trim()
      || String(m?.prescription?.dose || '').trim()
      || String(m?.prescription?.frequency || '').trim()
      || String(m?.prescription?.duration || '').trim()
      || String(m?.prescription?.unparsed || '').trim()
    );
    if (hasData && !serviceDate) missingMedicineDates.push(index + 1);
  });

  (clean?.investigations || []).forEach((inv, index) => {
    const serviceDate = String(inv?.serviceDate || '').trim();
    const hasData = Boolean(String(inv?.gdrgCode || '').trim());
    if (hasData && !serviceDate) missingInvestigationDates.push(index + 1);
  });

  (clean?.procedures || []).forEach((proc, index) => {
    const serviceDate = String(proc?.serviceDate || '').trim();
    const hasData = Boolean(
      String(proc?.gdrgCode || '').trim()
      || String(proc?.description || '').trim()
      || String(proc?.icd10 || '').trim()
      || String(proc?.diagnosis || '').trim()
    );
    if (hasData && !serviceDate) missingProcedureDates.push(index + 1);
  });

  return { missingMedicineDates, missingInvestigationDates, missingProcedureDates };
}

function applyUnparsedPrescriptionFields(med) {
  if (!med) return;
  if (!med.prescription || typeof med.prescription !== 'object') {
    med.prescription = { dose: '', frequency: '', duration: '', unparsed: '' };
  }
  const parsed = parsePrescriptionUnparsed(med.prescription.unparsed);
  if (!parsed) return;
  if (!String(med.prescription.dose || '').trim()) med.prescription.dose = parsed.dose;
  if (!String(med.prescription.frequency || '').trim()) med.prescription.frequency = parsed.frequency;
  if (!String(med.prescription.duration || '').trim()) med.prescription.duration = parsed.duration;
  syncPrescriptionUnparsed(med);
}

async function resolveServiceNames() {
  const lookups = [];
  for (const diag of payload.diagnoses || []) {
    if (diag.icd10 && !diag._diagnosisName) {
      lookups.push(
        priceListAPI.searchIcd10(diag.icd10, 10)
          .then((res) => {
            const first = (res.data || []).find((x) => (x.icd10_code || '').toUpperCase() === String(diag.icd10).toUpperCase()) || (res.data || [])[0];
            if (first) {
              diag._diagnosisName = first.icd10_description || '';
              if (!diag.diagnosis) diag.diagnosis = first.icd10_description || '';
              const drgCodes = Array.isArray(first.drg_codes) ? first.drg_codes.filter(Boolean) : [];
              diag._drgOptions = drgCodes.map((code) => ({ label: code, value: code }));
              if (drgCodes.length === 1) {
                if (!diag.gdrgCode) diag.gdrgCode = drgCodes[0];
              }
              // Prefer full DRG list (with descriptions) from mapping API
              return priceListAPI.getDrgCodesFromIcd10(diag.icd10).then((drgRes) => {
                const items = drgRes.data || [];
                if (!items.length) return;
                const seen = new Set();
                diag._drgOptions = items
                  .map((d) => {
                    const code = String(d.drg_code || '').trim();
                    if (!code || seen.has(code)) return null;
                    seen.add(code);
                    const desc = String(d.drg_description || '').trim();
                    return { label: desc ? `${code} — ${desc}` : code, value: code };
                  })
                  .filter(Boolean);
                if (diag._drgOptions.length === 1 && !diag.gdrgCode) {
                  diag.gdrgCode = diag._drgOptions[0].value;
                }
              }).catch(() => {});
            }
          })
          .catch(() => {})
      );
    }
  }
  for (const inv of payload.investigations || []) {
    if (inv._selectedOption && typeof inv._selectedOption === 'object') {
      inv._selectedOption = withServiceOptionLabel(inv._selectedOption);
    }
    if (inv.gdrgCode && !inv._serviceName) {
      lookups.push(
        priceListAPI.search(inv.gdrgCode, undefined, 'procedure')
          .then((res) => {
            const first = (res.data || [])[0];
            if (first) {
              inv._serviceName = first.service_name || first.item_name || '';
              inv._selectedOption = withServiceOptionLabel(first);
            }
          })
          .catch(() => {})
      );
    }
  }
  for (const proc of payload.procedures || []) {
    if (proc._selectedOption && typeof proc._selectedOption === 'object') {
      proc._selectedOption = withServiceOptionLabel(proc._selectedOption);
    }
    if (proc.gdrgCode && !proc._serviceName) {
      lookups.push(
        priceListAPI.search(proc.gdrgCode, undefined, 'procedure')
          .then((res) => {
            const first = (res.data || [])[0];
            if (first) {
              proc._serviceName = first.service_name || first.item_name || '';
              proc._selectedOption = withServiceOptionLabel(first);
            }
          })
          .catch(() => {})
      );
    }
  }
  for (const med of payload.medicines || []) {
    applyUnparsedPrescriptionFields(med);
    if (med.medicineCode) {
      lookups.push(
        priceListAPI.search(med.medicineCode, undefined, 'product')
          .then((res) => {
            const items = res.data || [];
            const code = String(med.medicineCode || '').trim();
            const match = items.find(
              (p) => String(p.medication_code || p.item_code || '').trim() === code
            ) || items[0];
            if (match) {
              if (!med._serviceName) med._serviceName = match.product_name || match.item_name || '';
              med.insurance_covered = match.insurance_covered || 'yes';
              if (!med._selectedOption) {
                med._selectedOption = withProductOptionLabel(match);
              } else {
                med._selectedOption = withProductOptionLabel(med._selectedOption);
              }
            } else {
              med.insurance_covered = med.insurance_covered || 'yes';
            }
          })
          .catch(() => {})
      );
    }
  }
  if (lookups.length) await Promise.all(lookups);
  recalculateClaimSummary();
}

function normalize(p) {
  const memberNo = p.memberNo || '';
  let ghanaCard = p.ghanaCard || '';
  let hin = p.hin || '';
  // If memberNo is still Ghana Card but hin already known, prefer showing converted state
  if (isGhanaCard(memberNo) && hin && !isGhanaCard(hin)) {
    ghanaCard = ghanaCard || normalizeGhanaCard(memberNo);
  }
  return {
    claimID: p.claimID || '',
    claimCheckCode: p.claimCheckCode || '',
    memberNo: memberNo,
    ghanaCard: ghanaCard,
    hin: hin,
    surname: p.surname || '',
    otherNames: p.otherNames || '',
    dateOfBirth: p.dateOfBirth || '',
    typeOfService: p.typeOfService || '',
    typeOfAttendance: p.typeOfAttendance || '',
    specialtyAttended: p.specialtyAttended || '',
    diagnoses: Array.isArray(p.diagnoses) ? p.diagnoses : [],
    medicines: sortClaimMedicinesByDateAsc(Array.isArray(p.medicines) ? p.medicines : []),
    investigations: Array.isArray(p.investigations) ? p.investigations : [],
    procedures: Array.isArray(p.procedures) ? p.procedures : [],
    dateOfService: Array.isArray(p.dateOfService) ? p.dateOfService : [],
    preAuthorizationCodes: p.preAuthorizationCodes || '',
    physicianID: p.physicianID || '',
    cardSerialNo: p.cardSerialNo || '',
    gender: p.gender || '',
    hospitalRecNo: p.hospitalRecNo || '',
    isDependant: p.isDependant || '',
    isUnbundled: p.isUnbundled || '',
    includesPharmacy: p.includesPharmacy || '',
    serviceOutcome: p.serviceOutcome || '',
    principalGDRG: p.principalGDRG || '',
  };
}

async function revertToDraft() {
  if (status.value !== 'finalized') return;
  reverting.value = true;
  try {
    await claimsAPI.reopenGhimsImportItem(itemId.value);
    $q.notify({
      type: 'positive',
      message: 'Imported claim reverted to draft. You can now edit and save.',
      position: 'top',
    });
    await load();
  } catch (e) {
    $q.notify({
      type: 'negative',
      message: e.response?.data?.detail || e.message || 'Failed to revert imported claim',
      position: 'top',
    });
  } finally {
    reverting.value = false;
  }
}

async function onConvertGhanaCardToHin() {
  if (status.value === 'finalized') return;
  const ghanaCard = normalizeGhanaCard(payload.ghanaCard || payload.memberNo);
  if (!isGhanaCard(ghanaCard)) {
    $q.notify({
      type: 'warning',
      message: 'Member No is not a Ghana Card (expected GHA-xxxxxxxx-x)',
      position: 'top',
    });
    return;
  }
  convertingGhanaCard.value = true;
  try {
    const res = await claimsAPI.convertGhimsGhanaCardToHin(itemId.value, ghanaCard);
    const data = res.data || {};
    const hin = (data.hin || data.member_no || '').trim();
    if (!hin) {
      throw new Error(data.message || 'No HIN returned from NHIA');
    }
    payload.ghanaCard = data.ghana_card || ghanaCard;
    payload.hin = hin;
    payload.memberNo = hin;
    $q.notify({
      type: 'positive',
      message: 'Member No set to HIN. Ghana Card saved for CCC. Save the claim to keep this change.',
      position: 'top',
      timeout: 4500,
    });
  } catch (e) {
    $q.notify({
      type: 'negative',
      message: e.response?.data?.detail || e.message || 'Failed to convert Ghana Card to HIN',
      position: 'top',
    });
  } finally {
    convertingGhanaCard.value = false;
  }
}

function onAiPayloadUpdated(nextPayload) {
  if (!nextPayload || typeof nextPayload !== 'object') return;
  Object.assign(payload, normalize(nextPayload));
  syncGhimsServiceDateSnapshot();
}

async function onGetGhimsClaimCcc() {
  if (!canGetGhimsCcc.value) return;
  const confirmed = await confirmClaimGetCcc($q);
  if (!confirmed) return;

  fetchingClaimCcc.value = true;
  try {
    // HIN cannot generate CCC — use Ghana Card when present
    const memberNo = memberNoForCcc({
      memberNo: payload.memberNo,
      ghanaCard: payload.ghanaCard,
    });
    if (!memberNo) {
      $q.notify({
        type: 'warning',
        message: 'Enter an NHIA number or Ghana Card to fetch CCC (HIN cannot generate CCC)',
        position: 'top',
      });
      return;
    }
    const res = await claimsAPI.fetchGhimsImportCcc(itemId.value, memberNo);
    applyGhimsFetchCccToPayload(payload, res.data);
    skipServiceDateRebase = true;
    syncGhimsServiceDateSnapshot();
    skipServiceDateRebase = false;
    $q.notify({
      type: 'positive',
      message: `Claim check code updated to ${res.data.claim_check_code || res.data.ccc}. Save and finalize to keep changes.`,
      position: 'top',
    });
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || error.message || 'Failed to fetch CCC',
      position: 'top',
    });
  } finally {
    fetchingClaimCcc.value = false;
  }
}

async function load() {
  loading.value = true;
  try {
    const res = await claimsAPI.getGhimsImportItem(itemId.value);
    status.value = res.data.status || 'draft';
    applyVettingFromItem(res.data || {});
    flagComment.value = String(res.data.flag_comment || '').trim();
    Object.assign(payload, normalize(res.data.payload || {}));
    const ce = res.data.claimit_errors || {};
    claimitErrors.value = {
      messages: Array.isArray(ce.messages) ? ce.messages : [],
      by_section: { ...emptyClaimitBySection(), ...(ce.by_section || {}) },
    };
    reorderDiagnosesWithPrincipalFirst();
    await resolveServiceNames();
    const principalGdrg = String(payload.principalGDRG || '').trim();
    if (principalGdrg) {
      const matchProc = (payload.procedures || []).find(
        (p) => String(p.gdrgCode || '').trim() === principalGdrg
      );
      if (matchProc) matchProc.is_principal = true;
    }
    syncPrincipalFromProcedures();
    if (res.data.claim_summary) {
      applyClaimSummaryFromApi(res.data.claim_summary);
    } else {
      recalculateClaimSummary();
    }
  } catch (e) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Failed to load imported claim' });
  } finally {
    skipServiceDateRebase = true;
    syncGhimsServiceDateSnapshot();
    skipServiceDateRebase = false;
    loading.value = false;
  }
}

async function saveAndFinalize() {
  saving.value = true;
  try {
    reorderDiagnosesWithPrincipalFirst();
    const clean = normalize(payload);
    validateCoveredMedicinesOrThrow(payload.medicines);
    const { missingMedicineDates, missingInvestigationDates, missingProcedureDates } = validateServiceDates(clean);
    if (missingMedicineDates.length) {
      throw new Error(`Medicine section(s) missing service date. Please enter date: medicine section(s): ${missingMedicineDates.join(', ')}`);
    }
    if (missingInvestigationDates.length) {
      throw new Error(`Investigation section(s) missing service date. Please enter date: investigation section(s): ${missingInvestigationDates.join(', ')}`);
    }
    if (missingProcedureDates.length) {
      throw new Error(`Procedure section(s) missing service date. Please enter date: procedure section(s): ${missingProcedureDates.join(', ')}`);
    }
    const invalidDiagnosisSections = validateDiagnosisGdrg(clean.diagnoses || []);
    if (invalidDiagnosisSections.length) {
      throw new Error(`Diagnosis section(s) missing GDRG. Please enter GDRG before saving: ${invalidDiagnosisSections.join(', ')}`);
    }
    const invalidDoseSections = validateMedicineDoses(clean.medicines || []);
    if (invalidDoseSections.length) {
      throw new Error(`Medicine section(s) missing dose. Please enter dose: ${invalidDoseSections.join(', ')}`);
    }
    (payload.medicines || []).forEach((m) => syncPrescriptionUnparsed(m));
    (clean.medicines || []).forEach((m) => applyUnparsedPrescriptionFields(m));
    clean.investigations = (clean.investigations || []).map(({ serviceDate, gdrgCode }) => ({ serviceDate, gdrgCode }));
    clean.procedures = (clean.procedures || []).map(({ serviceDate, gdrgCode, description, icd10, diagnosis }) => ({ serviceDate, gdrgCode, description, icd10, diagnosis }));
    clean.medicines = (clean.medicines || []).map((m) => ({
      medicineCode: m.medicineCode,
      dispensedQty: m.dispensedQty,
      serviceDate: m.serviceDate,
      prescription: {
        dose: m.prescription?.dose || '',
        frequency: m.prescription?.frequency || '',
        duration: normalizeDuration(m.prescription?.duration, { commit: true }),
        unparsed: m.prescription?.unparsed || '',
      },
    }));
    await claimsAPI.updateGhimsImportItem(itemId.value, clean);
    if (status.value !== 'finalized') {
      await claimsAPI.finalizeGhimsImportItem(itemId.value);
    }
    $q.notify({ type: 'positive', message: 'Imported claim saved and finalized' });
    await load();
  } catch (e) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || e.message || 'Failed to save and finalize imported claim' });
  } finally {
    saving.value = false;
  }
}

async function flagClaim() {
  saving.value = true;
  try {
    reorderDiagnosesWithPrincipalFirst();
    const clean = normalize(payload);
    validateCoveredMedicinesOrThrow(payload.medicines);
    const { missingMedicineDates, missingInvestigationDates, missingProcedureDates } = validateServiceDates(clean);
    if (missingMedicineDates.length) {
      throw new Error(`Medicine section(s) missing service date. Please enter date: ${missingMedicineDates.join(', ')}`);
    }
    if (missingInvestigationDates.length) {
      throw new Error(`Investigation section(s) missing service date. Please enter date: ${missingInvestigationDates.join(', ')}`);
    }
    if (missingProcedureDates.length) {
      throw new Error(`Procedure section(s) missing service date. Please enter date: ${missingProcedureDates.join(', ')}`);
    }
    const invalidDiagnosisSections = validateDiagnosisGdrg(clean.diagnoses || []);
    if (invalidDiagnosisSections.length) {
      throw new Error(`Diagnosis section(s) missing GDRG. Please enter GDRG before saving: ${invalidDiagnosisSections.join(', ')}`);
    }
    const invalidDoseSections = validateMedicineDoses(clean.medicines || []);
    if (invalidDoseSections.length) {
      throw new Error(`Medicine section(s) missing dose. Please enter dose: ${invalidDoseSections.join(', ')}`);
    }
    (payload.medicines || []).forEach((m) => syncPrescriptionUnparsed(m));
    (clean.medicines || []).forEach((m) => applyUnparsedPrescriptionFields(m));
    clean.investigations = (clean.investigations || []).map(({ serviceDate, gdrgCode }) => ({ serviceDate, gdrgCode }));
    clean.procedures = (clean.procedures || []).map(({ serviceDate, gdrgCode, description, icd10, diagnosis }) => ({ serviceDate, gdrgCode, description, icd10, diagnosis }));
    clean.medicines = (clean.medicines || []).map((m) => ({
      medicineCode: m.medicineCode,
      dispensedQty: m.dispensedQty,
      serviceDate: m.serviceDate,
      prescription: {
        dose: m.prescription?.dose || '',
        frequency: m.prescription?.frequency || '',
        duration: normalizeDuration(m.prescription?.duration, { commit: true }),
        unparsed: m.prescription?.unparsed || '',
      },
    }));
    await claimsAPI.updateGhimsImportItem(itemId.value, clean);
    const comment = await new Promise((resolve) => {
      $q.dialog({
        title: 'Flag imported claim',
        message: 'Enter a short reason (required). This helps other staff understand why it was flagged.',
        prompt: {
          model: '',
          type: 'textarea',
          isValid: (val) => Boolean(String(val || '').trim()),
          autogrow: true,
        },
        cancel: true,
        persistent: true,
        ok: { label: 'Flag', color: 'negative' },
      })
        .onOk((val) => resolve(String(val || '').trim()))
        .onCancel(() => resolve(null))
        .onDismiss(() => resolve(null));
    });
    if (!comment) return;
    await claimsAPI.flagGhimsImportItem(itemId.value, comment);
    $q.notify({ type: 'positive', message: 'Imported claim flagged' });
    await load();
  } catch (e) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || e.message || 'Failed to flag imported claim' });
  } finally {
    saving.value = false;
  }
}

watch(
  () => route.params.itemId,
  async (newId) => {
    const id = Number(newId);
    if (!id) return;
    itemId.value = id;
    await load();
  },
  { immediate: true }
);

watch(
  () => payload.medicines.length,
  () => {
    syncIncludesPharmacy();
  },
  { immediate: true }
);

watch(
  () => payload.diagnoses.map((d) => d?.gdrgCode || ''),
  () => {
    if (principalDiagnosisIndex.value < 0) return;
    const row = payload.diagnoses[principalDiagnosisIndex.value];
    const nextPrincipal = row?.gdrgCode || '';
    const prevPrincipal = String(payload.principalGDRG || '');
    payload.principalGDRG = nextPrincipal;
    // Only auto-fill specialty when the principal GDRG itself changes — never on save/reorder noise
    if (String(nextPrincipal).trim() !== String(prevPrincipal).trim()) {
      syncSpecialtyFromPrincipalDiagnosis();
    }
  },
  { deep: true }
);
</script>

<style scoped>
.medicine-not-covered-section {
  margin: 0 -4px;
  padding: 8px 8px 4px;
  border-radius: 6px;
  background-color: rgba(244, 67, 54, 0.08);
  box-shadow: inset 0 0 0 1px rgba(244, 67, 54, 0.2);
}

.service-outside-span-section {
  margin: 0 -4px;
  padding: 8px 8px 4px;
  border-radius: 6px;
  background-color: rgba(255, 193, 7, 0.1);
  box-shadow: inset 0 0 0 1px rgba(255, 193, 7, 0.28);
}

.revert-claim-fixed-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  background: var(--q-color-amber-2);
  border-top: 1px solid rgba(0, 0, 0, 0.12);
  z-index: 2000;
}

.q-page.revert-bar-visible {
  padding-bottom: 64px;
}

.hms-page > form > .q-card,
.hms-page .q-form > .q-card {
  border-radius: var(--hms-radius-xl);
  border-color: var(--hms-border);
  background: var(--hms-panel-bg);
  margin-bottom: 1rem;
}

.claim-nav-controls {
  margin-left: 8px;
}

.claim-nav-position {
  min-width: 4.5rem;
  text-align: center;
}
</style>
