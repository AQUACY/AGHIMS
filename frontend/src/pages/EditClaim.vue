<template>
  <q-page class="hms-page claim-edit-page" :class="{ 'reopen-bar-visible': !loading && claimStatus === 'finalized' }">
    <HmsPageHeader :title="isViewMode ? 'View NHIS claim' : 'Edit NHIS claim'">
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
        <HmsButton variant="ghost" size="sm" @click="$router.push('/claims')">Back</HmsButton>
      </template>
    </HmsPageHeader>

    <div v-if="!loading" class="claim-hero">
      <div class="claim-hero__main">
        <div class="claim-hero__avatar" aria-hidden="true">{{ claimInitials }}</div>
        <div>
          <h2 class="claim-hero__name">{{ claimDisplayName }}</h2>
          <div class="claim-hero__meta">
            <span class="mono">Claim #{{ claimId }}</span>
            <span v-if="patientInfo.hospital_record_no">Rec {{ patientInfo.hospital_record_no }}</span>
            <span v-if="patientInfo.member_number" class="mono">{{ patientInfo.member_number }}</span>
            <span v-if="claimMeta.claim_check_code" class="mono">CCC {{ claimMeta.claim_check_code }}</span>
          </div>
        </div>
      </div>
      <div class="claim-hero__aside">
        <div class="claim-hero__badges">
          <q-badge
            v-if="claimStatus"
            :color="claimStatus === 'finalized' ? 'positive' : (claimStatus === 'vetted' ? 'deep-purple' : (claimStatus === 'pharmacy_vetted' ? 'teal' : (claimStatus === 'doctor_vetted' ? 'indigo' : 'warning')))"
            :label="claimStatus === 'vetted' ? 'pharmacy + doctor vetted' : (claimStatus === 'pharmacy_vetted' ? 'pharmacy vetted' : (claimStatus === 'doctor_vetted' ? 'doctor vetted' : claimStatus))"
          />
          <q-badge v-if="vetting.pharmacy_vetted" color="teal" label="Pharmacy" />
          <q-badge v-if="vetting.doctor_vetted" color="indigo" label="Doctor" />
        </div>
      </div>
    </div>

    <q-banner
      v-if="isViewMode"
      class="soft-banner q-mb-md"
      rounded
    >
      <template v-slot:avatar>
        <q-icon name="info" />
      </template>
      <strong>View Mode</strong>
      <div class="text-caption q-mt-xs">
        Use <strong>Save Changes</strong> to apply edits and finalize (you will be asked to confirm). If you made no edits, use <strong>Save & Finalize</strong> to finalize without changes.
      </div>
    </q-banner>

    <!-- Reopen finalized claim to allow editing (view mode or from Correct Errors) -->
    <q-banner
      v-if="!loading && claimStatus === 'finalized'"
      class="bg-amber-2 q-mb-md"
      rounded
    >
      <template v-slot:avatar>
        <q-icon name="lock_open" color="amber-9" />
      </template>
      <strong>Claim is finalized</strong>
      <div class="text-caption q-mt-xs">
        <template v-if="isViewMode">
          You are viewing this claim. To make changes, click <strong>Revert to draft</strong> below. Then edit and use <strong>Save & Finalize</strong> when done.
        </template>
        <template v-else>
          To correct errors and re-export, revert the claim to draft first. Then make your changes and use <strong>Save & Finalize</strong> before exporting again.
        </template>
      </div>
      <template v-slot:action>
        <q-btn
          flat
          color="primary"
          label="Revert to draft"
          :loading="reopening"
          @click="reopenClaim"
        />
      </template>
    </q-banner>

    <q-card v-if="loading" class="q-pa-md">
      <q-inner-loading showing color="primary" />
    </q-card>

    <q-form v-else @submit="saveClaim" class="q-gutter-md">
      <!-- ClaimIT errors not mapped to a section -->
      <q-banner v-if="claimitErrors.by_section?.other?.length" class="bg-orange-1 q-mb-md" rounded dense>
        <template v-slot:avatar><q-icon name="warning" color="orange" /></template>
        <div class="text-subtitle2">ClaimIT reported (fix in relevant section):</div>
        <ul class="q-mt-xs q-mb-none q-pl-md">
          <li v-for="(msg, i) in claimitErrors.by_section.other" :key="i" class="text-body2">{{ msg }}</li>
        </ul>
      </q-banner>

      <!-- Provider Information -->
      <q-card>
        <q-card-section>
          <div class="text-h6 q-mb-md">Provider Information</div>
          <q-banner v-if="claimitErrors.by_section?.provider?.length" class="bg-orange-1 q-mb-md" rounded dense>
            <template v-slot:avatar><q-icon name="warning" color="orange" /></template>
            <div class="text-subtitle2">ClaimIT reported:</div>
            <ul class="q-mt-xs q-mb-none q-pl-md">
              <li v-for="(msg, i) in claimitErrors.by_section.provider" :key="i" class="text-body2">{{ msg }}</li>
            </ul>
          </q-banner>
          <div class="row q-gutter-md">
            <q-input
              v-model="providerInfo.provider_name"
              filled
              label="Provider's Name"
              class="col-12"
              readonly
            />
            <q-input
              v-model="providerInfo.scheme_code"
              filled
              label="Scheme Code"
              class="col-12 col-md-6"
            />
            <q-input
              v-model="providerInfo.month_of_claim"
              filled
              type="date"
              label="Month of Claim"
              class="col-12 col-md-6"
            />
            <q-input
              v-model="claimMeta.claim_check_code"
              filled
              label="Claim Check Code"
              class="col-12 col-md-4"
              readonly
            />
            <div class="col-12 col-md-8 row items-center q-gutter-sm">
              <q-btn
                color="secondary"
                icon="cloud_download"
                label="Get CCC"
                :loading="fetchingClaimCcc"
                :disable="!canGetClaimCcc || loading"
                @click="onGetClaimCcc"
              >
                <q-tooltip v-if="!canGetClaimCcc">
                  Requires active NHIS with a member number
                </q-tooltip>
              </q-btn>
              <span class="text-caption text-grey-7">
                Preview only until Save and Finalize — refresh the page to undo.
              </span>
            </div>
          </div>
        </q-card-section>
      </q-card>

      <!-- Client Information -->
      <q-card>
        <q-card-section>
          <div class="text-h6 q-mb-md">Client Information</div>
          <q-banner v-if="claimitErrors.by_section?.client?.length" class="bg-orange-1 q-mb-md" rounded dense>
            <template v-slot:avatar><q-icon name="warning" color="orange" /></template>
            <div class="text-subtitle2">ClaimIT reported:</div>
            <ul class="q-mt-xs q-mb-none q-pl-md">
              <li v-for="(msg, i) in claimitErrors.by_section.client" :key="i" class="text-body2">{{ msg }}</li>
            </ul>
          </q-banner>
          <div class="row q-gutter-md">
            <q-input
              v-model="patientInfo.surname"
              filled
              label="Surname"
              class="col-12 col-md-4"
            />
            <q-input
              v-model="patientInfo.other_names"
              filled
              label="Other Names"
              class="col-12 col-md-4"
            />
            <q-input
              v-model="patientInfo.date_of_birth"
              filled
              type="date"
              label="Date of Birth"
              class="col-12 col-md-4"
            />
            <q-input
              v-model="patientInfo.age"
              filled
              type="number"
              label="Age"
              class="col-12 col-md-3"
            />
            <div class="col-12 col-md-4">
              <div class="text-subtitle2 q-mb-xs">Gender</div>
              <q-option-group
                v-model="patientInfo.gender"
                :options="genderOptions"
                type="radio"
              />
            </div>
            <div class="col-12 col-md-5">
              <q-input
                v-model="patientInfo.member_number"
                filled
                label="Member Number"
                :disable="claimStatus === 'finalized' && !isViewMode"
              >
                <template v-if="showConvertToHin" v-slot:append>
                  <q-btn
                    flat
                    dense
                    color="primary"
                    label="To HIN"
                    :loading="convertingGhanaCard"
                    :disable="claimStatus === 'finalized'"
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
              v-if="patientInfo.ghana_card || showConvertToHin"
              v-model="patientInfo.ghana_card"
              filled
              label="Ghana Card"
              class="col-12 col-md-4"
              hint="Saved when converting Member No to HIN (used for Get CCC)"
              :disable="claimStatus === 'finalized'"
            />
            <q-input
              v-model="patientInfo.hospital_record_no"
              filled
              label="Hospital Record No."
              class="col-12 col-md-4"
            />
            <q-input
              v-model="patientInfo.card_serial_no"
              filled
              label="Card Serial No."
              class="col-12 col-md-3"
            />
          </div>
        </q-card-section>
      </q-card>

      <!-- Services Provided -->
      <q-card>
        <q-card-section>
          <div class="text-h6 q-mb-md">Services Provided</div>
          <q-banner v-if="claimitErrors.by_section?.services?.length" class="bg-orange-1 q-mb-md" rounded dense>
            <template v-slot:avatar><q-icon name="warning" color="orange" /></template>
            <div class="text-subtitle2">ClaimIT reported:</div>
            <ul class="q-mt-xs q-mb-none q-pl-md">
              <li v-for="(msg, i) in claimitErrors.by_section.services" :key="i" class="text-body2">{{ msg }}</li>
            </ul>
          </q-banner>
          <div class="row q-gutter-md q-mb-md">
            <div class="col-12 col-md-3">
              <q-select
                v-model="services.type_of_service"
                :options="serviceTypeOptions"
                emit-value
                map-options
                filled
                label="Type of Service"
              />
            </div>
            <div class="col-12 col-md-3">
              <q-checkbox
                v-model="services.includes_pharmacy"
                :false-value="false"
                :true-value="true"
                label="Pharmacy (claim includes drugs)"
              />
            </div>
          </div>

          <div class="row q-gutter-md q-mb-md">
            <q-input
              v-model="services.first_visit"
              filled
              type="date"
              label="1st Visit/Admission"
              class="col-12 col-md-3"
            />
            <q-input
              v-model="services.second_visit"
              filled
              type="date"
              label="2nd Visit/Discharge"
              class="col-12 col-md-3"
            />
            <q-input
              v-model="services.third_visit"
              filled
              type="date"
              label="3rd Visit"
              class="col-12 col-md-3"
            />
            <q-input
              v-model="services.fourth_visit"
              filled
              type="date"
              label="4th Visit"
              class="col-12 col-md-3"
            />
            <q-input
              v-model="services.duration_of_spell"
              filled
              type="number"
              label="Duration of Spell (days)"
              class="col-12 col-md-4"
            />
          </div>

          <div class="row q-gutter-md q-mb-md">
            <div class="col-12 col-md-6">
              <div class="text-subtitle2 q-mb-xs">All Inclusive / Unbundled</div>
              <q-option-group
                v-model="services.all_inclusive"
                :options="[{label: 'All Inclusive', value: true}, {label: 'Unbundled', value: false}]"
                type="radio"
              />
            </div>
            <div class="col-12 col-md-6">
              <div class="text-subtitle2 q-mb-xs">Outcome</div>
              <q-select
                v-model="services.outcome"
                :options="outcomeOptions"
                filled
                label="Outcome"
              />
            </div>
            <div class="col-12 col-md-6">
              <q-select
                v-model="services.type_of_attendance"
                :options="attendanceOptions"
                emit-value
                map-options
                filled
                label="Type of Attendance"
              />
            </div>
            <q-select
              v-model="services.specialty_code"
              :options="specialtyAttendedOptions"
              emit-value
              map-options
              filled
              label="Specialty Attended"
              class="col-12 col-md-6"
              hint="Defaults from principal GDRG; change if needed"
            />
          </div>
          
          <div class="row q-gutter-md">
            <q-input
              v-model="services.principal_gdrg"
              filled
              label="Principal G-DRG Code"
              class="col-12 col-md-6"
              :disable="claimStatus === 'finalized'"
              hint="Main diagnosis code for this claim"
            />
          </div>
        </q-card-section>
      </q-card>

      <!-- Procedures (Surgeries) -->
      <q-card>
        <q-card-section>
          <q-banner v-if="claimitErrors.by_section?.procedures?.length" class="bg-orange-1 q-mb-md" rounded dense>
            <template v-slot:avatar><q-icon name="warning" color="orange" /></template>
            <div class="text-subtitle2">ClaimIT reported:</div>
            <ul class="q-mt-xs q-mb-none q-pl-md">
              <li v-for="(msg, i) in claimitErrors.by_section.procedures" :key="i" class="text-body2">{{ msg }}</li>
            </ul>
          </q-banner>
          <div class="row items-center q-mb-md">
            <div class="text-h6">Surgery(ies)</div>
            <q-icon
              v-if="pendingClaimSurgeries.length > 0"
              name="warning"
              color="orange"
              size="sm"
              class="q-ml-sm cursor-pointer"
              @click="showPendingSurgeriesDialog = true"
            >
              <q-tooltip>
                {{ pendingClaimSurgeries.length }} pending surgery(ies) – click to mark complete and add to claim
              </q-tooltip>
            </q-icon>
            <q-space />
            <q-btn
              v-if="claimStatus !== 'finalized' && !isViewMode"
              size="sm"
              color="primary"
              icon="add"
              label="Add Surgery"
              @click="addProcedure"
              class="glass-button"
            />
          </div>
          <div class="row q-gutter-md">
            <div class="col-12">
              <q-input
                v-model="procedures.physician_name"
                filled
                label="Physician/Clinician Name"
              />
            </div>
            <q-input
              v-model="procedures.physician_id"
              filled
              label="Physician/Clinician ID"
              class="col-12 col-md-6"
            />
          </div>
          
          <q-table
            :rows="proceduresList"
            :columns="procedureColumns"
            row-key="index"
            flat
            dense
            class="q-mt-md"
            :table-row-class-fn="claimLineRowClass"
          >
            <template v-slot:body-cell-description="props">
              <q-td :props="props">
                <q-select
                  :model-value="proceduresList[props.row.index].description"
                  :options="surgerySearchOptions"
                  option-label="optionLabel"
                  use-input
                  input-debounce="250"
                  fill-input
                  hide-selected
                  clearable
                  dense
                  filled
                  :disable="claimStatus === 'finalized' || isViewMode"
                  @filter="filterSurgerySearch"
                  @update:model-value="(val) => onProcedureSelect(props.row.index, val)"
                >
                  <template v-slot:no-option>
                    <q-item>
                      <q-item-section class="text-grey">Type to search surgeries / procedures</q-item-section>
                    </q-item>
                  </template>
                </q-select>
              </q-td>
            </template>
            <template v-slot:body-cell-diagnosis="props">
              <q-td :props="props">
                <q-select
                  :model-value="proceduresList[props.row.index].diagnosis || proceduresList[props.row.index].icd10"
                  :options="diagnosisSearchOptions"
                  option-label="display"
                  use-input
                  input-debounce="250"
                  fill-input
                  hide-selected
                  clearable
                  dense
                  filled
                  :disable="claimStatus === 'finalized' || isViewMode"
                  @filter="filterDiagnosisSearch"
                  @update:model-value="(val) => onProcedureDiagnosisSelect(props.row.index, val)"
                >
                  <template v-slot:no-option>
                    <q-item>
                      <q-item-section class="text-grey">Type to search diagnoses (ICD-10)</q-item-section>
                    </q-item>
                  </template>
                </q-select>
              </q-td>
            </template>
            <template v-slot:body-cell-is_principal="props">
              <q-td :props="props">
                <q-checkbox
                  v-if="showProcedurePrincipalPicker"
                  :model-value="!!proceduresList[props.row.index].is_principal"
                  :disable="claimStatus === 'finalized' || isViewMode || !(proceduresList[props.row.index].description || '').trim()"
                  dense
                  @update:model-value="(checked) => setPrincipalProcedure(props.row.index, checked)"
                >
                  <q-tooltip>Mark this procedure's diagnosis as principal G-DRG</q-tooltip>
                </q-checkbox>
                <span v-else-if="(proceduresList[props.row.index].description || '').trim() && proceduresList[props.row.index].is_principal" class="text-caption text-positive">Yes</span>
                <span v-else class="text-grey-5">—</span>
              </q-td>
            </template>
            <template v-slot:body-cell-date="props">
              <q-td :props="props">
                <q-input
                  v-model="proceduresList[props.row.index].date"
                  dense
                  filled
                  type="date"
                  :disable="claimStatus === 'finalized' || isViewMode"
                />
              </q-td>
            </template>
            <template v-slot:body-cell-icd10="props">
              <q-td :props="props">
                <q-input
                  v-model="proceduresList[props.row.index].icd10"
                  dense
                  filled
                  :disable="claimStatus === 'finalized' || isViewMode"
                />
              </q-td>
            </template>
            <template v-slot:body-cell-gdrg="props">
              <q-td :props="props">
                <q-input
                  v-model="proceduresList[props.row.index].gdrg"
                  dense
                  filled
                  :disable="claimStatus === 'finalized' || isViewMode"
                  @blur="onProcedureGdrgChange(props.row.index)"
                />
              </q-td>
            </template>
            <template v-slot:body-cell-actions="props">
              <q-td :props="props">
                <q-btn
                  v-if="proceduresList[props.row.index].description && proceduresList[props.row.index].description.trim() !== '' && (claimStatus !== 'finalized' || isViewMode)"
                  size="sm"
                  color="negative"
                  icon="delete"
                  flat
                  round
                  dense
                  @click="deleteProcedure(props.row.index)"
                >
                  <q-tooltip>Delete Surgery</q-tooltip>
                </q-btn>
              </q-td>
            </template>
          </q-table>
        </q-card-section>
      </q-card>

      <!-- Diagnoses -->
      <q-card>
        <q-card-section>
          <q-banner v-if="claimitErrors.by_section?.diagnosis?.length" class="bg-orange-1 q-mb-md" rounded dense>
            <template v-slot:avatar><q-icon name="warning" color="orange" /></template>
            <div class="text-subtitle2">ClaimIT reported:</div>
            <ul class="q-mt-xs q-mb-none q-pl-md">
              <li v-for="(msg, i) in claimitErrors.by_section.diagnosis" :key="i" class="text-body2">{{ msg }}</li>
            </ul>
          </q-banner>
          <div class="row items-center q-mb-md">
            <div class="text-h6">Diagnosis(es)</div>
            <q-space />
            <q-btn
              v-if="claimStatus !== 'finalized' && !isViewMode && hasChiefDiagnosis"
              size="sm"
              flat
              color="primary"
              icon="playlist_add"
              label="Apply template"
              :loading="loadingTemplates"
              @click="openApplyTemplate"
              class="q-mr-xs"
            />
            <q-btn
              v-if="claimStatus !== 'finalized' && !isViewMode && hasChiefDiagnosis"
              size="sm"
              flat
              color="secondary"
              icon="save"
              label="Save as template"
              @click="openSaveTemplate"
              class="q-mr-sm"
            />
            <q-btn
              v-if="claimStatus !== 'finalized' && !isViewMode"
              size="sm"
              color="primary"
              icon="add"
              label="Add Diagnosis"
              @click="addDiagnosis"
              class="glass-button"
            />
          </div>
          <q-table
            :rows="diagnosesList"
            :columns="diagnosisColumns"
            row-key="index"
            flat
            dense
            v-model:pagination="diagnosisPagination"
            :rows-per-page-options="[5, 10, 15, 20]"
            rows-per-page-label="Records per page"
          >
            <template v-slot:body-cell-description="props">
              <q-td :props="props">
                <q-select
                  :model-value="diagnosesList[props.row.index].description"
                  :options="diagnosisSearchOptions"
                  option-label="display"
                  use-input
                  input-debounce="250"
                  fill-input
                  hide-selected
                  clearable
                  dense
                  filled
                  :disable="claimStatus === 'finalized' || isViewMode"
                  @filter="filterDiagnosisSearch"
                  @update:model-value="(val) => onDiagnosisSelect(props.row.index, val)"
                >
                  <template v-slot:no-option>
                    <q-item>
                      <q-item-section class="text-grey">Type to search ICD-10 diagnosis</q-item-section>
                    </q-item>
                  </template>
                </q-select>
              </q-td>
            </template>
            <template v-slot:body-cell-icd10="props">
              <q-td :props="props">
                <q-input
                  v-model="diagnosesList[props.row.index].icd10"
                  dense
                  filled
                  :disable="claimStatus === 'finalized' || isViewMode"
                />
              </q-td>
            </template>
            <template v-slot:body-cell-gdrg="props">
              <q-td :props="props">
                <div class="column q-gutter-xs" style="min-width: 140px">
                  <q-select
                    v-if="(diagnosesList[props.row.index]._drgOptions || []).length > 1"
                    :model-value="diagnosesList[props.row.index].gdrg"
                    :options="diagnosesList[props.row.index]._drgOptions"
                    emit-value
                    map-options
                    dense
                    filled
                    clearable
                    label="Mapped DRG options"
                    :disable="claimStatus === 'finalized' || isViewMode"
                    @update:model-value="(val) => onDiagnosisMappedDrgSelect(props.row.index, val)"
                  />
                  <q-input
                    v-model="diagnosesList[props.row.index].gdrg"
                    dense
                    filled
                    label="G-DRG"
                    hint="Editable — type your own code if needed"
                    :disable="claimStatus === 'finalized' || isViewMode"
                    @update:model-value="() => onDiagnosisGdrgEdited(props.row.index)"
                  />
                </div>
              </q-td>
            </template>
            <template v-slot:body-cell-is_chief="props">
              <q-td :props="props">
                <q-checkbox
                  :model-value="diagnosesList[props.row.index].is_chief"
                  :disable="claimStatus === 'finalized' || isViewMode"
                  @update:model-value="(checked) => setChiefDiagnosis(props.row.index, checked)"
                />
              </q-td>
            </template>
            <template v-slot:body-cell-actions="props">
              <q-td :props="props">
                <q-btn
                  v-if="diagnosesList[props.row.index].description && diagnosesList[props.row.index].description.trim() !== '' && (claimStatus !== 'finalized' || isViewMode)"
                  size="sm"
                  color="negative"
                  icon="delete"
                  flat
                  round
                  dense
                  @click="deleteDiagnosis(props.row.index)"
                >
                  <q-tooltip>Delete Diagnosis</q-tooltip>
                </q-btn>
              </q-td>
            </template>
          </q-table>
        </q-card-section>
      </q-card>

      <!-- Investigations -->
      <q-card>
        <q-card-section>
          <q-banner v-if="claimitErrors.by_section?.investigations?.length" class="bg-orange-1 q-mb-md" rounded dense>
            <template v-slot:avatar><q-icon name="warning" color="orange" /></template>
            <div class="text-subtitle2">ClaimIT reported:</div>
            <ul class="q-mt-xs q-mb-none q-pl-md">
              <li v-for="(msg, i) in claimitErrors.by_section.investigations" :key="i" class="text-body2">{{ msg }}</li>
            </ul>
          </q-banner>
          <div class="row items-center q-mb-md">
            <div class="text-h6">Investigations</div>
            <q-space />
            <q-btn
              v-if="claimStatus !== 'finalized' && !isViewMode"
              size="sm"
              color="primary"
              icon="add"
              label="Add Investigation"
              @click="addInvestigation"
            />
          </div>
          <q-table
            :rows="investigationsList"
            :columns="investigationColumns"
            row-key="index"
            flat
            dense
            :table-row-class-fn="claimLineRowClass"
          >
            <template v-slot:body-cell-description="props">
              <q-td :props="props">
                <q-select
                  :model-value="investigationsList[props.row.index].description"
                  :options="investigationSearchOptions"
                  option-label="service_name"
                  use-input
                  input-debounce="250"
                  fill-input
                  hide-selected
                  clearable
                  dense
                  filled
                  :disable="claimStatus === 'finalized' || isViewMode"
                  @filter="filterInvestigationProcedures"
                  @update:model-value="(val) => onInvestigationSelect(props.row.index, val)"
                >
                  <template v-slot:no-option>
                    <q-item>
                      <q-item-section class="text-grey">Type to search procedures (lab/scan/x-ray)</q-item-section>
                    </q-item>
                  </template>
                </q-select>
              </q-td>
            </template>
            <template v-slot:body-cell-date="props">
              <q-td :props="props">
                <q-input
                  v-model="investigationsList[props.row.index].date"
                  dense
                  filled
                  type="date"
                  :disable="claimStatus === 'finalized' || isViewMode"
                />
              </q-td>
            </template>
            <template v-slot:body-cell-gdrg="props">
              <q-td :props="props">
                <q-input
                  v-model="investigationsList[props.row.index].gdrg"
                  dense
                  filled
                  :disable="claimStatus === 'finalized' || isViewMode"
                />
              </q-td>
            </template>
            <template v-slot:body-cell-actions="props">
              <q-td :props="props">
                <q-btn
                  v-if="investigationsList[props.row.index].description && investigationsList[props.row.index].description.trim() !== '' && (claimStatus !== 'finalized' || isViewMode)"
                  size="sm"
                  color="negative"
                  icon="delete"
                  flat
                  round
                  dense
                  @click="deleteInvestigation(props.row.index)"
                >
                  <q-tooltip>Delete Investigation</q-tooltip>
                </q-btn>
              </q-td>
            </template>
          </q-table>
        </q-card-section>
      </q-card>

      <!-- Medicines -->
      <q-card>
        <q-card-section>
          <q-banner v-if="claimitErrors.by_section?.medicines?.length" class="bg-orange-1 q-mb-md" rounded dense>
            <template v-slot:avatar><q-icon name="warning" color="orange" /></template>
            <div class="text-subtitle2">ClaimIT reported:</div>
            <ul class="q-mt-xs q-mb-none q-pl-md">
              <li v-for="(msg, i) in claimitErrors.by_section.medicines" :key="i" class="text-body2">{{ msg }}</li>
            </ul>
          </q-banner>
          <div class="row items-center q-mb-md">
            <div class="text-h6">Medicines</div>
            <q-space />
            <q-btn
              v-if="claimStatus !== 'finalized' && !isViewMode"
              size="sm"
              color="primary"
              icon="add"
              label="Add Medicine"
              @click="addPrescription"
            />
          </div>
          <q-table
            :rows="prescriptionsList"
            :columns="prescriptionColumns"
            row-key="index"
            flat
            dense
            :table-row-class-fn="claimLineRowClass"
          >
            <template v-slot:body-cell-description="props">
              <q-td :props="props">
                <q-select
                  :model-value="prescriptionsList[props.row.index].description"
                  :options="productSearchOptions"
                  option-label="product_name"
                  use-input
                  input-debounce="250"
                  fill-input
                  hide-selected
                  clearable
                  dense
                  filled
                  :disable="claimStatus === 'finalized' || isViewMode"
                  @filter="filterProductSearch"
                  @update:model-value="(val) => onPrescriptionProductSelect(props.row.index, val)"
                >
                  <template v-slot:no-option>
                    <q-item>
                      <q-item-section class="text-grey">Type to search medicines</q-item-section>
                    </q-item>
                  </template>
                </q-select>
              </q-td>
            </template>
            <template v-slot:body-cell-price="props">
              <q-td :props="props">
                <q-input
                  v-model.number="prescriptionsList[props.row.index].price"
                  dense
                  filled
                  type="number"
                  step="0.01"
                  :disable="claimStatus === 'finalized' || isViewMode"
                  @update:model-value="updatePrescriptionTotal(props.row.index)"
                />
              </q-td>
            </template>
            <template v-slot:body-cell-quantity="props">
              <q-td :props="props">
                <q-input
                  v-model.number="prescriptionsList[props.row.index].quantity"
                  dense
                  filled
                  type="number"
                  :disable="claimStatus === 'finalized' || isViewMode"
                  @update:model-value="updatePrescriptionTotal(props.row.index)"
                />
              </q-td>
            </template>
            <template v-slot:body-cell-total_cost="props">
              <q-td :props="props">
                <q-input
                  v-model.number="prescriptionsList[props.row.index].total_cost"
                  dense
                  filled
                  type="number"
                  step="0.01"
                  readonly
                />
              </q-td>
            </template>
            <template v-slot:body-cell-date="props">
              <q-td :props="props">
                <q-input
                  v-model="prescriptionsList[props.row.index].date"
                  dense
                  filled
                  type="date"
                  :disable="claimStatus === 'finalized' || isViewMode"
                />
              </q-td>
            </template>
            <template v-slot:body-cell-code="props">
              <q-td :props="props">
                <q-input
                  v-model="prescriptionsList[props.row.index].code"
                  dense
                  filled
                  :disable="claimStatus === 'finalized' || isViewMode"
                />
              </q-td>
            </template>
            <template v-slot:body-cell-actions="props">
              <q-td :props="props">
                <div class="row q-gutter-xs">
                  <q-btn
                    v-if="prescriptionsList[props.row.index].description && prescriptionsList[props.row.index].description.trim() !== ''"
                    size="sm"
                    color="primary"
                    icon="edit"
                    flat
                    round
                    dense
                    @click="openPrescriptionDialog(props.row.index)"
                    :disable="claimStatus === 'finalized' || isViewMode"
                  >
                    <q-tooltip>Edit Dose, Frequency & Duration</q-tooltip>
                  </q-btn>
                  <q-btn
                    v-if="prescriptionsList[props.row.index].description && prescriptionsList[props.row.index].description.trim() !== '' && (claimStatus !== 'finalized' || isViewMode)"
                    size="sm"
                    color="negative"
                    icon="delete"
                    flat
                    round
                    dense
                    @click="deletePrescription(props.row.index)"
                  >
                    <q-tooltip>Delete Medicine</q-tooltip>
                  </q-btn>
                </div>
              </q-td>
            </template>
          </q-table>
        </q-card-section>
      </q-card>

      <!-- Client Claim Summary -->
      <q-card>
        <q-card-section>
          <div class="text-h6 q-mb-md">Client Claim Summary</div>
          <q-table
            :rows="claimSummary"
            :columns="summaryColumns"
            row-key="type"
            flat
            dense
          >
            <template v-slot:body-cell-gdrg_code="props">
              <q-td :props="props">
                <q-input
                  v-model="claimSummary[props.row.index].gdrg_code"
                  dense
                  filled
                  :disable="claimStatus === 'finalized' || props.row.type === 'TOTAL'"
                />
              </q-td>
            </template>
            <template v-slot:body-cell-tariff_amount="props">
              <q-td :props="props">
                <q-input
                  v-model.number="claimSummary[props.row.index].tariff_amount"
                  dense
                  filled
                  type="number"
                  step="0.01"
                  :disable="claimStatus === 'finalized' || props.row.type === 'TOTAL'"
                  readonly
                />
              </q-td>
            </template>
          </q-table>
          <div class="text-h6 q-mt-md text-right">
            Total: ₵{{ totalClaimAmount.toFixed(2) }}
          </div>
        </q-card-section>
      </q-card>

      <!-- Action Buttons -->
      <div class="row q-gutter-md q-mt-md">
        <q-btn
          v-if="claimStatus !== 'finalized' && canVetPharmacy"
          :color="vetting.pharmacy_vetted ? 'orange-9' : 'teal-7'"
          text-color="white"
          unelevated
          :icon="vetting.pharmacy_vetted ? 'undo' : 'local_pharmacy'"
          :label="vetting.pharmacy_vetted ? 'Revert pharmacy vet' : 'Vet by Pharmacy'"
          :loading="vettingPharmacy"
          class="col-12 col-md-3"
          @click="vetByPharmacy"
        />
        <q-btn
          v-if="claimStatus !== 'finalized' && canVetDoctor"
          :color="vetting.doctor_vetted ? 'orange-9' : 'indigo-7'"
          text-color="white"
          unelevated
          :icon="vetting.doctor_vetted ? 'undo' : 'medical_services'"
          :label="vetting.doctor_vetted ? 'Revert doctor vet' : 'Vet by Doctor'"
          :loading="vettingDoctor"
          class="col-12 col-md-3"
          @click="vetByDoctor"
        />
        <!-- Edit Mode Buttons -->
        <template v-if="!isViewMode">
          <q-btn
            type="submit"
            color="secondary"
            label="Save Draft"
            :loading="saving"
            :disable="claimStatus === 'finalized'"
            class="col-12 col-md-3"
          />
          <q-btn
            color="primary"
            label="Save & Finalize"
            :loading="saving"
            @click="saveAndFinalize"
            :disable="claimStatus === 'finalized'"
            class="col-12 col-md-3"
          />
        </template>
        <!-- View Mode Buttons (disabled when finalized — use Reopen claim first to edit) -->
        <template v-else>
          <q-btn
            color="primary"
            label="Save & Finalize"
            :loading="saving"
            @click="saveAndFinalize"
            :disable="claimStatus === 'finalized'"
            class="col-12 col-md-3"
          />
          <q-btn
            color="secondary"
            label="Save Changes"
            :loading="saving"
            @click.prevent="onSaveChangesInViewMode"
            :disable="claimStatus === 'finalized'"
            class="col-12 col-md-3"
          />
        </template>
      </div>
    </q-form>

    <!-- Fixed bottom bar: Reopen claim always visible when finalized (no need to scroll up) -->
    <div
      v-if="!loading && claimStatus === 'finalized'"
      class="reopen-claim-fixed-bar row items-center justify-center q-pa-sm shadow-6"
    >
      <span class="q-mr-md text-weight-medium">Claim is finalized.</span>
      <q-btn
        color="primary"
        label="Revert to draft"
        :loading="reopening"
        icon="undo"
        @click="reopenClaim"
      />
    </div>

    <!-- Add Diagnosis Dialog (same format as Consultation form) -->
    <q-dialog v-model="showDiagnosisDialog">
      <q-card style="min-width: 420px">
        <q-card-section>
          <div class="text-h6">Add Diagnosis</div>
        </q-card-section>
        <q-card-section>
          <q-form @submit="addDiagnosisFromDialog" class="q-gutter-md">
            <q-select
              v-model="selectedIcd10"
              filled
              :options="icd10Options"
              label="Search by ICD-10 Code"
              option-label="display"
              option-value="icd10_code"
              use-input
              input-debounce="300"
              @filter="filterIcd10Codes"
              @update:model-value="onIcd10Selected"
              hint="Search by ICD-10 code or description – diagnosis and G-DRG will be auto-filled"
              clearable
            />
            <q-select
              v-model="selectedDrgDiagnosis"
              filled
              :options="drgDiagnosisOptions"
              label="OR Search Diagnosis (from Unmapped DRG)"
              option-label="item_name"
              option-value="item_code"
              use-input
              input-debounce="300"
              @filter="filterDrgDiagnoses"
              @update:model-value="onDrgDiagnosisSelected"
              hint="Search by diagnosis name – G-DRG and description will be auto-filled"
              clearable
            />
            <q-input
              v-model="claimDiagnosisForm.icd10"
              filled
              label="ICD-10 Code *"
            />
            <q-input
              v-model="claimDiagnosisForm.description"
              filled
              label="Diagnosis (Description) *"
              lazy-rules
              :rules="[(val) => !!val || 'Required']"
            />
            <q-select
              v-if="(claimDiagnosisDrgOptions || []).length > 1"
              v-model="claimDiagnosisForm.gdrg"
              :options="claimDiagnosisDrgOptions"
              emit-value
              map-options
              filled
              clearable
              label="Mapped DRG options"
              hint="Pick a mapped DRG, or type your own below"
            />
            <q-input
              v-model="claimDiagnosisForm.gdrg"
              filled
              label="G-DRG Code"
              hint="Editable — type your own code if needed"
            />
            <q-checkbox
              v-model="claimDiagnosisForm.is_chief"
              label="Chief Diagnosis"
            />
            <q-card-actions align="right">
              <q-btn label="Cancel" flat v-close-popup @click="resetClaimDiagnosisForm" />
              <q-btn label="Add" type="submit" color="primary" />
            </q-card-actions>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- Prescription Details Dialog -->
    <q-dialog v-model="showPrescriptionDialog">
      <q-card style="min-width: 400px">
        <q-card-section>
          <div class="text-h6">Edit Prescription Details</div>
          <div class="text-subtitle2 text-grey-7 q-mt-xs">
            {{ currentPrescription?.description || 'Medicine' }}
          </div>
        </q-card-section>

        <q-card-section>
          <q-form @submit="savePrescriptionDetails" class="q-gutter-md">
            <q-input
              v-model="prescriptionForm.dose"
              filled
              label="Dose"
              placeholder="e.g., 500 MG"
              :disable="claimStatus === 'finalized'"
            />
            <q-input
              v-model="prescriptionForm.frequency"
              filled
              label="Frequency"
              placeholder="e.g., 2 DAILY"
              :disable="claimStatus === 'finalized'"
            />
            <q-input
              v-model="prescriptionForm.duration"
              filled
              label="Duration"
              placeholder="e.g., 7 DAYS"
              :disable="claimStatus === 'finalized'"
            />
            
            <q-card-actions align="right">
              <q-btn
                flat
                label="Cancel"
                color="secondary"
                v-close-popup
              />
              <q-btn
                type="submit"
                label="Save"
                color="primary"
                :disable="claimStatus === 'finalized'"
              />
            </q-card-actions>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- Pending surgeries: mark complete & add to claim -->
    <q-dialog v-model="showPendingSurgeriesDialog" persistent>
      <q-card style="min-width: 420px; max-width: 560px">
        <q-card-section>
          <div class="text-h6">Pending surgery(ies)</div>
          <div class="text-caption text-grey-7">
            Mark as completed and add to the claim. Changes will apply when you save or finalize (no regeneration).
          </div>
        </q-card-section>
        <q-card-section class="q-pt-none">
          <q-list v-if="pendingClaimSurgeries.length > 0" bordered separator>
            <q-item v-for="s in pendingClaimSurgeries" :key="s.id" class="q-py-sm">
              <q-item-section>
                <q-item-label>{{ s.surgery_name || 'Surgery' }}</q-item-label>
                <q-item-label caption>
                  {{ s.surgery_date ? (typeof s.surgery_date === 'string' ? s.surgery_date.split('T')[0] : s.surgery_date) : '—' }}
                  <span v-if="s.surgeon_name"> · {{ s.surgeon_name }}</span>
                  <span v-if="s.g_drg_code"> · {{ s.g_drg_code }}</span>
                </q-item-label>
              </q-item-section>
              <q-item-section side>
                <q-btn
                  flat
                  dense
                  color="primary"
                  label="Mark complete & add to claim"
                  :loading="completingSurgeryId === s.id"
                  :disable="completingSurgeryId !== null"
                  @click="markSurgeryCompleteAndAdd(s)"
                />
              </q-item-section>
            </q-item>
          </q-list>
          <p v-else class="text-grey-7 q-ma-none">No pending surgeries.</p>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Close" color="secondary" v-close-popup />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <q-dialog v-model="showApplyTemplateDialog" persistent>
      <q-card style="min-width: 520px; max-width: 720px">
        <q-card-section>
          <div class="text-h6">Apply diagnosis template</div>
          <div class="text-caption text-grey-7">{{ principalDiagnosisLabel }}</div>
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
            <q-item v-for="t in matchedTemplates" :key="t.id" clickable v-ripple @click="selectApplyTemplate(t)">
              <q-item-section>
                <q-item-label>{{ t.name }}</q-item-label>
                <q-item-label caption>
                  {{ (t.investigations || []).length }} inv · {{ (t.medicines || []).length }} meds
                  <span v-if="matchedTemplateIds.has(t.id)" class="text-positive"> · matched</span>
                  <span v-else class="text-orange-8"> · not mapped to this diagnosis</span>
                </q-item-label>
              </q-item-section>
            </q-item>
          </q-list>
        </q-card-section>
        <q-card-section v-else>
          <div class="text-subtitle2 q-mb-sm">{{ selectedApplyTemplate.name }} — tick items to apply</div>
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
          <q-btn v-if="selectedApplyTemplate" flat label="Back" @click="selectedApplyTemplate = null" />
          <q-btn v-if="selectedApplyTemplate" color="primary" label="Apply selected" @click="confirmApplyTemplate" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <q-dialog v-model="showSaveTemplateDialog" persistent>
      <q-card style="min-width: 520px; max-width: 720px">
        <q-card-section>
          <div class="text-h6">Save as diagnosis template</div>
          <div class="text-caption text-grey-7">{{ principalDiagnosisLabel }}</div>
        </q-card-section>
        <q-card-section class="q-gutter-md">
          <q-input v-model="saveTemplateForm.name" filled label="Template name *" />
          <q-input v-model="saveTemplateForm.match_keywords" filled dense label="Match keywords" />
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
import { ref, reactive, computed, watch, onMounted } from 'vue';
import HmsPageHeader from '../components/ui/HmsPageHeader.vue';
import HmsButton from '../components/ui/HmsButton.vue';
import { useRoute, useRouter } from 'vue-router';
import { useQuasar } from 'quasar';
import { claimsAPI, priceListAPI, consultationAPI } from '../services/api';
import { useAuthStore } from '../stores/auth';
import { useFacilityStore, DEFAULT_FACILITY_DISPLAY_NAME } from '../stores/facility';
import {
  confirmClaimGetCcc,
  applyClaimFetchCccToEditForm,
  applyServiceDateChangeToEditForm,
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
  isMedicineNotCovered,
  normalizeInsuranceCovered,
  claimLineRowClass,
} from '../utils/claimMedicineCoverage';
import { getClaimsNavPosition } from '../utils/claimNav';

const facilityStore = useFacilityStore();
const authStore = useAuthStore();
const $route = useRoute();
const $router = useRouter();
const $q = useQuasar();

const loading = ref(true);
const saving = ref(false);
const reopening = ref(false);
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
const canVetPharmacy = computed(() =>
  authStore.canAccess(['Pharmacy', 'Pharmacy Head', 'Claims', 'Admin'])
);
const canVetDoctor = computed(() =>
  authStore.canAccess(['Doctor', 'PA', 'Claims', 'Admin'])
);

function applyVettingFromClaim(claim = {}) {
  if (claim.status) claimStatus.value = claim.status;
  vetting.pharmacy_vetted = !!claim.pharmacy_vetted || !!claim.pharmacy_vetted_at;
  vetting.pharmacy_vetted_at = claim.pharmacy_vetted_at || null;
  vetting.pharmacy_vetted_by_name = claim.pharmacy_vetted_by_name || null;
  vetting.doctor_vetted = !!claim.doctor_vetted || !!claim.doctor_vetted_at;
  vetting.doctor_vetted_at = claim.doctor_vetted_at || null;
  vetting.doctor_vetted_by_name = claim.doctor_vetted_by_name || null;
}

async function vetByPharmacy() {
  if (!claimId.value || claimStatus.value === 'finalized') return;
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
    const res = await claimsAPI.vetClaim(claimId.value, 'pharmacy', clearing);
    applyVettingFromClaim(res.data || {});
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
  if (!claimId.value || claimStatus.value === 'finalized') return;
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
    const res = await claimsAPI.vetClaim(claimId.value, 'doctor', clearing);
    applyVettingFromClaim(res.data || {});
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
const patientNhiaMeta = ref({ insured: false, nhis_active: false });
const claimId = ref(null);
const claimStatus = ref('draft');
const isViewMode = ref(false);
/** Snapshot of last saved claim payload (JSON) for change detection in view mode */
const lastSavedClaimPayload = ref(null);

/** ClaimIT report errors for this claim, by section (from Correct Errors uploads) */
const claimitErrors = ref({ messages: [], by_section: {} });

// Pending surgeries (IPD): surgeries not yet completed – mark complete & add to claim without regenerating
const wardAdmissionId = ref(null);
const pendingClaimSurgeries = ref([]);
const showPendingSurgeriesDialog = ref(false);
const completingSurgeryId = ref(null);

// Prescription Dialog
const showPrescriptionDialog = ref(false);
const currentPrescriptionIndex = ref(null);
const currentPrescription = computed(() => {
  if (currentPrescriptionIndex.value !== null) {
    return prescriptionsList.value[currentPrescriptionIndex.value];
  }
  return null;
});

const prescriptionForm = reactive({
  dose: '',
  frequency: '',
  duration: '',
});

// Provider Information
const providerInfo = reactive({
  provider_name: DEFAULT_FACILITY_DISPLAY_NAME,
  scheme_code: '',
  month_of_claim: new Date().toISOString().split('T')[0],
});

const claimMeta = reactive({
  claim_check_code: '',
});

const canGetClaimCcc = computed(() => {
  const forCcc = memberNoForCcc({
    memberNo: patientInfo.member_number,
    ghanaCard: patientInfo.ghana_card,
  });
  if (!forCcc) return false;
  return !!(patientNhiaMeta.value.insured && patientNhiaMeta.value.nhis_active);
});

// Patient Information
const patientInfo = reactive({
  surname: '',
  other_names: '',
  date_of_birth: '',
  age: null,
  gender: 'M',
  member_number: '',
  ghana_card: '',
  hin: '',
  hospital_record_no: '',
  card_serial_no: '',
});

const isMemberNoGhanaCard = computed(() => isGhanaCard(patientInfo.member_number));
const showConvertToHin = computed(
  () => isMemberNoGhanaCard.value || (isGhanaCard(patientInfo.ghana_card) && !String(patientInfo.member_number || '').trim())
);

const genderOptions = [
  { label: 'Male', value: 'M' },
  { label: 'Female', value: 'F' },
];

// Services Provided
const services = reactive({
  type_of_service: 'OPD',
  includes_pharmacy: false,
  first_visit: '',
  second_visit: '',
  third_visit: '',
  fourth_visit: '',
  duration_of_spell: null,
  all_inclusive: true,
  outcome: 'DISC',
  type_of_attendance: 'EAE',
  specialty_code: '',
  principal_gdrg: '',
});

// OPD/IPD select options (export typeOfService = OPD | IPD)
const serviceTypeOptions = [
  { label: 'OPD', value: 'OPD' },
  { label: 'IPD', value: 'IPD' },
];

const serviceDateSnapshot = ref({ first_visit: '', second_visit: '' });
let skipServiceDateRebase = false;

function syncServiceDateSnapshot() {
  serviceDateSnapshot.value = {
    first_visit: services.first_visit || '',
    second_visit: services.second_visit || '',
  };
}

function onServiceDatesChanged() {
  if (skipServiceDateRebase || loading.value) return;

  const prev = serviceDateSnapshot.value;
  const isIpd = String(services.type_of_service || 'OPD').toUpperCase() === 'IPD';
  const firstChanged = (services.first_visit || '') !== (prev.first_visit || '');
  const secondChanged = (services.second_visit || '') !== (prev.second_visit || '');

  if (isIpd) {
    if (!firstChanged && !secondChanged) return;
    if (!services.first_visit) return;
  } else {
    if (!firstChanged) return;
    if (!services.first_visit) return;
  }

  skipServiceDateRebase = true;
  applyServiceDateChangeToEditForm(
    {
      services,
      investigationsList,
      prescriptionsList,
      proceduresList,
    },
    prev
  );
  syncServiceDateSnapshot();
  skipServiceDateRebase = false;
}

watch(
  () => [services.first_visit, services.second_visit, services.type_of_service],
  onServiceDatesChanged
);

const outcomeOptions = ['Discharged', 'Died', 'Transferred Out', 'Absconded/Discharged against Medical advice'];
const attendanceOptions = [
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
  const current = String(services.specialty_code || '').trim().toUpperCase();
  if (current && !SPECIALTY_ATTENDED_CODES.includes(current)) {
    return [{ label: current, value: current }, ...base];
  }
  return base;
});

// Procedures
const procedures = reactive({
  physician_name: '',
  physician_id: '',
});

const proceduresList = ref([
  { index: 0, description: '', diagnosis: '', date: '', gdrg: '', icd10: '', is_principal: false },
  { index: 1, description: '', diagnosis: '', date: '', gdrg: '', icd10: '', is_principal: false },
  { index: 2, description: '', diagnosis: '', date: '', gdrg: '', icd10: '', is_principal: false },
]);

const procedureColumns = [
  { name: 'number', label: '#', field: 'index', align: 'center' },
  { name: 'description', label: 'Description', field: 'description', align: 'left' },
  { name: 'diagnosis', label: 'Diagnosis', field: 'diagnosis', align: 'left' },
  { name: 'is_principal', label: 'Principal', field: 'is_principal', align: 'center' },
  { name: 'date', label: 'Date', field: 'date', align: 'center' },
  { name: 'icd10', label: 'ICD-10', field: 'icd10', align: 'center' },
  { name: 'gdrg', label: 'G-DRG', field: 'gdrg', align: 'left' },
  { name: 'actions', label: 'Actions', align: 'center' },
];

// Diagnoses
const diagnosesList = ref([
  { index: 0, id: null, description: '', icd10: '', gdrg: '', is_chief: false, _drgOptions: [] },
  { index: 1, id: null, description: '', icd10: '', gdrg: '', is_chief: false, _drgOptions: [] },
  { index: 2, id: null, description: '', icd10: '', gdrg: '', is_chief: false, _drgOptions: [] },
  { index: 3, id: null, description: '', icd10: '', gdrg: '', is_chief: false, _drgOptions: [] },
]);

const diagnosisColumns = [
  { name: 'number', label: '#', field: 'index', align: 'center' },
  { name: 'description', label: 'Description', field: 'description', align: 'left' },
  { name: 'icd10', label: 'ICD-10', field: 'icd10', align: 'center' },
  { name: 'gdrg', label: 'G-DRG', field: 'gdrg', align: 'left' },
  { name: 'is_chief', label: 'Chief', field: 'is_chief', align: 'center' },
  { name: 'actions', label: 'Actions', align: 'center' },
];

const diagnosisPagination = ref({ rowsPerPage: 5, sortBy: 'index', descending: false });

// Add Diagnosis dialog (same format as Consultation form)
const showDiagnosisDialog = ref(false);
const selectedIcd10 = ref(null);
const selectedDrgDiagnosis = ref(null);
const icd10Options = ref([]);
const drgDiagnosisOptions = ref([]);
const allIcd10Codes = ref([]);
const allDrgDiagnoses = ref([]);
const claimDiagnosisForm = reactive({
  description: '',
  icd10: '',
  gdrg: '',
  is_chief: false,
});
const claimDiagnosisDrgOptions = ref([]);

// Investigations
const investigationsList = ref([
  { index: 0, id: null, description: '', date: '', gdrg: '' },
  { index: 1, id: null, description: '', date: '', gdrg: '' },
  { index: 2, id: null, description: '', date: '', gdrg: '' },
  { index: 3, id: null, description: '', date: '', gdrg: '' },
  { index: 4, id: null, description: '', date: '', gdrg: '' },
]);

const investigationColumns = [
  { name: 'number', label: '#', field: 'index', align: 'center' },
  { name: 'description', label: 'Description', field: 'description', align: 'left' },
  { name: 'date', label: 'DATE', field: 'date', align: 'center' },
  { name: 'gdrg', label: 'G-DRG', field: 'gdrg', align: 'left' },
  { name: 'actions', label: 'Actions', align: 'center' },
];

const investigationSearchOptions = ref([]);
const productSearchOptions = ref([]);
const surgerySearchOptions = ref([]);
const diagnosisSearchOptions = ref([]);

// Prescriptions
const prescriptionsList = ref([
  { index: 0, id: null, description: '', code: '', price: 0, quantity: 0, total_cost: 0, date: '', dose: '', frequency: '', duration: '', unparsed: '' },
  { index: 1, id: null, description: '', code: '', price: 0, quantity: 0, total_cost: 0, date: '', dose: '', frequency: '', duration: '', unparsed: '' },
  { index: 2, id: null, description: '', code: '', price: 0, quantity: 0, total_cost: 0, date: '', dose: '', frequency: '', duration: '', unparsed: '' },
  { index: 3, id: null, description: '', code: '', price: 0, quantity: 0, total_cost: 0, date: '', dose: '', frequency: '', duration: '', unparsed: '' },
  { index: 4, id: null, description: '', code: '', price: 0, quantity: 0, total_cost: 0, date: '', dose: '', frequency: '', duration: '', unparsed: '' },
]);

const prescriptionColumns = [
  { name: 'number', label: '#', field: 'index', align: 'center' },
  { name: 'description', label: 'Description', field: 'description', align: 'left' },
  { name: 'price', label: 'Price', field: 'price', align: 'right', format: (val) => `₵${val?.toFixed(2) || '0.00'}` },
  { name: 'quantity', label: 'Qty', field: 'quantity', align: 'center' },
  { name: 'total_cost', label: 'Total Cost', field: 'total_cost', align: 'right', format: (val) => `₵${val?.toFixed(2) || '0.00'}` },
  { name: 'date', label: 'Date', field: 'date', align: 'center' },
  { name: 'code', label: 'Code', field: 'code', align: 'left' },
  { name: 'actions', label: 'Actions', align: 'center' },
];

// Auto-tick Pharmacy when officer adds a real drug (code/description + quantity > 0); empty placeholder rows don't count
watch(
  () => prescriptionsList.value.some(p => ((p.code && p.code.trim()) || (p.description && p.description.trim())) && (Number(p.quantity) || 0) > 0),
  (hasDrugs) => { if (hasDrugs) services.includes_pharmacy = true; },
  { immediate: false }
);

// Claim Summary
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
  { name: 'tariff_amount', label: 'Tariff Amount', field: 'tariff_amount', align: 'right', format: (val) => `₵${val?.toFixed(2) || '0.00'}` },
];

const totalClaimAmount = computed(() => {
  return claimSummary.value
    .filter(item => item.type !== 'TOTAL')
    .reduce((sum, item) => sum + (item.tariff_amount || 0), 0);
});

const getClaimPrice = (item) => {
  if (!item) return 0;
  return Number(item.claim_amount ?? item.nhia_app ?? item.base_rate ?? item.insured_price ?? 0) || 0;
};

const calculateClaimSummary = () => {
  const tos = String(services.type_of_service || 'OPD').toUpperCase();

  let procedureTotal = 0;
  for (const proc of proceduresList.value) {
    const code = String(proc.gdrg || '').trim();
    if (!code) continue;
    if (proc._selectedOption) {
      procedureTotal += getClaimPrice(proc._selectedOption);
    }
  }
  if (!procedureTotal && String(services.principal_gdrg || '').trim()) {
    // Principal GDRG line uses backend-loaded summary amounts when no procedure row price
  }

  claimSummary.value[0].tariff_amount = tos === 'IPD' ? procedureTotal : (claimSummary.value[0].tariff_amount || 0);
  claimSummary.value[1].tariff_amount = tos === 'OPD' ? procedureTotal : (claimSummary.value[1].tariff_amount || 0);
  if (procedureTotal > 0) {
    if (tos === 'IPD') claimSummary.value[0].tariff_amount = procedureTotal;
    if (tos === 'OPD') claimSummary.value[1].tariff_amount = procedureTotal;
  }

  let investigationsTotal = 0;
  for (const inv of investigationsList.value) {
    const code = String(inv.gdrg || '').trim();
    if (!code) continue;
    if (inv._selectedOption) {
      investigationsTotal += getClaimPrice(inv._selectedOption);
    }
  }

  let pharmacyTotal = 0;
  for (const presc of prescriptionsList.value) {
    pharmacyTotal += Number(presc.total_cost) || 0;
  }

  claimSummary.value[2].tariff_amount = investigationsTotal;
  claimSummary.value[3].tariff_amount = pharmacyTotal;
  claimSummary.value[4].tariff_amount = totalClaimAmount.value;
};

const updatePrescriptionTotal = (index) => {
  const presc = prescriptionsList.value[index];
  presc.total_cost = (presc.price || 0) * (presc.quantity || 0);
  calculateClaimSummary();
};

const openPrescriptionDialog = (index) => {
  currentPrescriptionIndex.value = index;
  const presc = prescriptionsList.value[index];
  
  // Populate form with existing values
  prescriptionForm.dose = presc.dose || '';
  prescriptionForm.frequency = presc.frequency || '';
  prescriptionForm.duration = presc.duration || '';
  
  showPrescriptionDialog.value = true;
};

const savePrescriptionDetails = () => {
  if (currentPrescriptionIndex.value === null) return;
  
  const presc = prescriptionsList.value[currentPrescriptionIndex.value];
  
  // Update prescription fields
  presc.dose = prescriptionForm.dose || '';
  presc.frequency = prescriptionForm.frequency || '';
  presc.duration = prescriptionForm.duration || '';
  
  // Combine as unparsed
  const parts = [];
  if (presc.dose) parts.push(presc.dose);
  if (presc.frequency) parts.push(presc.frequency);
  if (presc.duration) parts.push(presc.duration);
  presc.unparsed = parts.join(' ');
  
  showPrescriptionDialog.value = false;
  currentPrescriptionIndex.value = null;
  
  $q.notify({
    type: 'positive',
    message: 'Prescription details saved',
  });
};

const addInvestigation = () => {
  // Find first empty slot
  const emptyIndex = investigationsList.value.findIndex(inv => !inv.description || inv.description.trim() === '');
  if (emptyIndex !== -1) {
    // Focus on the empty slot (it already exists)
    $q.notify({
      type: 'info',
      message: 'Please fill in the empty investigation row',
      timeout: 2000,
    });
  } else if (investigationsList.value.length < 300) {
    // Add new row if we haven't reached the limit
    investigationsList.value.push({
      index: investigationsList.value.length,
      id: null,
      description: '',
      date: firstClaimServiceDate(),
      gdrg: ''
    });
    $q.notify({
      type: 'positive',
      message: 'New investigation row added',
      timeout: 2000,
    });
  } else {
    $q.notify({
      type: 'warning',
      message: 'Maximum of 10 investigations allowed',
      timeout: 2000,
    });
  }
};

const filterInvestigationProcedures = (val, update) => {
  update(async () => {
    if (!val || val.length < 1) {
      investigationSearchOptions.value = [];
      return;
    }
    try {
      const res = await priceListAPI.search(val, undefined, 'procedure');
      investigationSearchOptions.value = res.data || [];
    } catch (_) {
      investigationSearchOptions.value = [];
    }
  });
};

const onInvestigationSelect = (index, val) => {
  const row = investigationsList.value[index];
  if (val == null || val === '') {
    row.description = '';
    row.gdrg = '';
    return;
  }
  if (typeof val === 'object' && val !== null && (val.service_name != null || val.item_name != null)) {
    row.description = val.service_name || val.item_name || '';
    row.gdrg = val.g_drg_code || val.item_code || '';
    row._selectedOption = val;
    if (!row.date) {
      row.date = firstClaimServiceDate();
    }
    calculateClaimSummary();
    return;
  }
  row.description = typeof val === 'string' ? val : '';
  if (!row.date) {
    row.date = firstClaimServiceDate();
  }
};

const filterSurgerySearch = (val, update) => {
  update(async () => {
    if (!val || val.length < 1) {
      surgerySearchOptions.value = [];
      return;
    }
    try {
      const res = await priceListAPI.search(val, undefined, 'procedure');
      const surgeryRes = await priceListAPI.search(val, undefined, 'surgery');
      const combined = [...(res.data || []), ...(surgeryRes.data || [])];
      surgerySearchOptions.value = combined.map((item) => ({
        ...item,
        optionLabel: `${item.service_name || item.item_name || ''} (${item.g_drg_code || item.item_code || ''})`,
      }));
    } catch (_) {
      surgerySearchOptions.value = [];
    }
  });
};

const onProcedureSelect = async (index, val) => {
  const row = proceduresList.value[index];
  if (val == null || val === '') {
    row.description = '';
    row.gdrg = '';
    row.icd10 = '';
    row.diagnosis = '';
    row.is_principal = false;
    row._selectedOption = null;
    syncPrincipalFromProcedures({ syncSpecialty: true });
    return;
  }
  if (typeof val === 'object' && val !== null && (val.service_name != null || val.item_name != null)) {
    row.description = val.service_name || val.item_name || '';
    const gdrg = val.g_drg_code || val.item_code || '';
    row.gdrg = gdrg;
    row._selectedOption = val;
    if (!row.date) {
      row.date = firstClaimServiceDate();
    }
    // If diagnosis already chosen, keep ICD-10 but align diagnosis G-DRG to this procedure
    if (row.icd10 && gdrg) {
      upsertDiagnosisFromProcedure(row);
    }
    syncPrincipalFromProcedures({ syncSpecialty: true });
    return;
  }
  row.description = typeof val === 'string' ? val : '';
  if (!row.date) {
    row.date = firstClaimServiceDate();
  }
  syncPrincipalFromProcedures({ syncSpecialty: true });
};

function firstClaimServiceDate() {
  return String(services.first_visit || '').trim();
}

const filledProcedures = computed(() =>
  (proceduresList.value || []).filter((p) => String(p.description || '').trim())
);

const showProcedurePrincipalPicker = computed(() => filledProcedures.value.length >= 2);

function upsertDiagnosisFromProcedure(proc) {
  const icd10 = String(proc.icd10 || '').trim();
  const description = String(proc.diagnosis || '').trim();
  const gdrg = String(proc.gdrg || '').trim();
  if (!icd10 && !description) return;

  let row = (diagnosesList.value || []).find(
    (d) => String(d.icd10 || '').trim().toUpperCase() === icd10.toUpperCase() && icd10
  );
  if (!row) {
    row = (diagnosesList.value || []).find(
      (d) => !String(d.description || '').trim() && !String(d.icd10 || '').trim()
    );
  }
  if (!row) {
    if (diagnosesList.value.length >= 20) return;
    row = {
      index: diagnosesList.value.length,
      id: null,
      description: '',
      icd10: '',
      gdrg: '',
      is_chief: false,
      _drgOptions: [],
    };
    diagnosesList.value.push(row);
  }
  row.description = description || row.description;
  row.icd10 = icd10 || row.icd10;
  // Diagnosis G-DRG follows the procedure G-DRG
  if (gdrg) row.gdrg = gdrg;
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
  const chief = (diagnosesList.value || []).find((d) => d.is_chief);
  const gdrg = String(chief?.gdrg || services.principal_gdrg || '').trim();
  const specialty = specialtyFromGdrg(gdrg);
  if (specialty) {
    services.specialty_code = specialty;
  }
}

/** Align principal GDRG / chief diagnosis from procedures. Specialty sync is opt-in so load/save does not overwrite a manual selection. */
function syncPrincipalFromProcedures({ syncSpecialty = false } = {}) {
  const filled = filledProcedures.value;
  if (!filled.length) return;

  if (filled.length === 1) {
    proceduresList.value.forEach((p) => {
      p.is_principal = p === filled[0];
    });
  }

  let principal = filled.find((p) => p.is_principal);
  if (!principal && filled.length === 1) {
    principal = filled[0];
    principal.is_principal = true;
  }
  if (!principal) return;

  const gdrg = String(principal.gdrg || '').trim();
  if (gdrg) {
    services.principal_gdrg = gdrg;
  }
  if (principal.icd10 || principal.diagnosis) {
    upsertDiagnosisFromProcedure(principal);
  }
  const principalIcd = String(principal.icd10 || '').trim().toUpperCase();
  diagnosesList.value.forEach((d) => {
    const match = principalIcd && String(d.icd10 || '').trim().toUpperCase() === principalIcd;
    d.is_chief = !!match;
  });
  if (syncSpecialty) {
    syncSpecialtyFromPrincipalDiagnosis();
  } else if (String(services.specialty_code || '').trim().toUpperCase() === 'ZOOM') {
    // Legacy claims may still have ZOOM stored — normalize to OPDC
    services.specialty_code = 'OPDC';
  }
}

function setChiefDiagnosis(index, checked) {
  const row = diagnosesList.value[index];
  if (!row) return;
  if (!checked) {
    row.is_chief = false;
    return;
  }
  diagnosesList.value.forEach((d, i) => {
    d.is_chief = i === index;
  });
  const gdrg = String(row.gdrg || '').trim();
  if (gdrg) {
    services.principal_gdrg = gdrg;
  }
  syncSpecialtyFromPrincipalDiagnosis();
}

const hasChiefDiagnosis = computed(() => (diagnosesList.value || []).some((d) => d.is_chief));
const principalDiagnosisLabel = computed(() => {
  const row = (diagnosesList.value || []).find((d) => d.is_chief);
  if (!row) return '';
  return [row.description, row.icd10, row.gdrg].filter(Boolean).join(' · ');
});
const applyInvChoices = computed(() =>
  (selectedApplyTemplate.value?.investigations || []).map((item, i) => ({
    label: `${item.serviceName || 'Investigation'} (${item.gdrgCode || '—'})`,
    value: i,
  }))
);
const applyMedChoices = computed(() =>
  (selectedApplyTemplate.value?.medicines || []).map((item, i) => ({
    label: `${item.serviceName || 'Medicine'} (${item.medicineCode || '—'})`,
    value: i,
  }))
);
const saveInvChoices = computed(() =>
  (investigationsList.value || [])
    .map((inv, i) => ({ inv, i }))
    .filter(({ inv }) => String(inv?.description || inv?.gdrg || '').trim())
    .map(({ inv, i }) => ({
      label: `${inv.description || 'Investigation'} (${inv.gdrg || '—'})`,
      value: i,
    }))
);
const saveMedChoices = computed(() =>
  (prescriptionsList.value || [])
    .map((med, i) => ({ med, i }))
    .filter(({ med }) => String(med?.description || med?.code || '').trim())
    .map(({ med, i }) => ({
      label: `${med.description || 'Medicine'} (${med.code || '—'})`,
      value: i,
    }))
);

function getPrincipalDiagnosisSnapshot() {
  const row = (diagnosesList.value || []).find((d) => d.is_chief);
  if (!row) return null;
  return { icd10: row.icd10 || '', diagnosis: row.description || '', gdrg: row.gdrg || '' };
}

async function openApplyTemplate() {
  const snap = getPrincipalDiagnosisSnapshot();
  if (!snap) {
    $q.notify({ type: 'warning', message: 'Mark a chief diagnosis first' });
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
  const medCount = (t.medicines || []).length;
  selectedApplyInvIndexes.value = Array.from({ length: (t.investigations || []).length }, (_, i) => i);
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
    const item = (t.investigations || [])[i];
    if (!item) continue;
    const row = investigationFromTemplateItem(item, invServiceDate);
    const empty = (investigationsList.value || []).find((x) => !String(x.description || '').trim() && !String(x.gdrg || '').trim());
    const target = empty || {
      index: investigationsList.value.length,
      id: null,
      description: '',
      date: invServiceDate,
      gdrg: '',
    };
    target.description = row._serviceName || target.description;
    target.gdrg = row.gdrgCode || target.gdrg;
    target.date = invServiceDate;
    if (!empty) investigationsList.value.push(target);
  }
  for (const i of pickMed) {
    const item = (t.medicines || [])[i];
    if (!item) continue;
    const medDate = String(applyMedServiceDates.value?.[i] || '').trim();
    const row = medicineFromTemplateItem(item, medDate);
    const empty = (prescriptionsList.value || []).find((x) => !String(x.description || '').trim() && !String(x.code || '').trim());
    const target = empty || {
      index: prescriptionsList.value.length,
      id: null,
      description: '',
      code: '',
      price: 0,
      quantity: 0,
      total_cost: 0,
      date: medDate,
      dose: '',
      frequency: '',
      duration: '',
      unparsed: '',
    };
    target.description = row._serviceName || target.description;
    target.code = row.medicineCode || target.code;
    target.date = medDate;
    target.dose = row.prescription?.dose || target.dose;
    target.frequency = row.prescription?.frequency || target.frequency;
    target.duration = row.prescription?.duration || target.duration;
    target.quantity = Number(row.dispensedQty) || target.quantity || 1;
    const parts = [target.dose, target.frequency, target.duration].filter(Boolean);
    target.unparsed = parts.join(' ');
    if (!empty) prescriptionsList.value.push(target);
  }
  services.includes_pharmacy = true;
  calculateClaimSummary();
  closeApplyTemplate();
  $q.notify({ type: 'positive', message: 'Template items applied — review and edit as needed' });
}

function openSaveTemplate() {
  const snap = getPrincipalDiagnosisSnapshot();
  if (!snap) {
    $q.notify({ type: 'warning', message: 'Mark a chief diagnosis first' });
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
  const investigations = (investigationsList.value || [])
    .filter((_, i) => invPick.has(i))
    .map((inv) => serializeInvestigationForTemplate({
      gdrgCode: inv.gdrg,
      _serviceName: inv.description,
    }))
    .filter((x) => x.gdrgCode || x.serviceName);
  const medicines = (prescriptionsList.value || [])
    .filter((_, i) => medPick.has(i))
    .map((med) => serializeMedicineForTemplate({
      medicineCode: med.code,
      _serviceName: med.description,
      dispensedQty: med.quantity,
      prescription: { dose: med.dose, frequency: med.frequency, duration: med.duration, unparsed: med.unparsed },
    }))
    .filter((x) => x.medicineCode || x.serviceName);
  if (!investigations.length && !medicines.length) {
    $q.notify({ type: 'warning', message: 'Tick at least one investigation or medicine' });
    return;
  }
  savingTemplate.value = true;
  try {
    await claimsAPI.createDiagnosisTemplate({
      name,
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

function onDiagnosisMappedDrgSelect(index, val) {
  const row = diagnosesList.value[index];
  if (!row) return;
  row.gdrg = val || '';
  if (row.is_chief) {
    if (row.gdrg) services.principal_gdrg = row.gdrg;
    syncSpecialtyFromPrincipalDiagnosis();
  }
}

function onDiagnosisGdrgEdited(index) {
  const row = diagnosesList.value[index];
  if (!row?.is_chief) return;
  if (row.gdrg) services.principal_gdrg = String(row.gdrg).trim();
  syncSpecialtyFromPrincipalDiagnosis();
}

function setPrincipalProcedure(index, checked) {
  const row = proceduresList.value[index];
  if (!row || !(row.description || '').trim()) return;
  if (!checked) {
    row.is_principal = false;
    return;
  }
  proceduresList.value.forEach((p, i) => {
    p.is_principal = i === index;
  });
  syncPrincipalFromProcedures({ syncSpecialty: true });
}

function onProcedureGdrgChange(index) {
  const row = proceduresList.value[index];
  if (!row) return;
  if (row.icd10 || row.diagnosis) {
    upsertDiagnosisFromProcedure(row);
  }
  if (row.is_principal || filledProcedures.value.length === 1) {
    syncPrincipalFromProcedures({ syncSpecialty: true });
  }
}

const onProcedureDiagnosisSelect = (index, val) => {
  const row = proceduresList.value[index];
  if (!row) return;
  if (val == null || val === '') {
    row.diagnosis = '';
    row.icd10 = '';
    syncPrincipalFromProcedures({ syncSpecialty: true });
    return;
  }
  if (typeof val === 'object' && val !== null && (val.icd10_code != null || val.icd10_description != null)) {
    row.diagnosis = val.icd10_description || '';
    row.icd10 = val.icd10_code || '';
    // Diagnosis on the claim uses the procedure's G-DRG
    upsertDiagnosisFromProcedure(row);
    // If this is the only filled procedure (or already principal), it drives principal G-DRG
    const filled = filledProcedures.value;
    if (filled.length === 1 || row.is_principal || !filled.some((p) => p.is_principal)) {
      row.is_principal = true;
      proceduresList.value.forEach((p, i) => {
        if (i !== index) p.is_principal = false;
      });
    }
    syncPrincipalFromProcedures({ syncSpecialty: true });
    return;
  }
  row.diagnosis = typeof val === 'string' ? val : '';
};

const filterDiagnosisSearch = (val, update) => {
  update(async () => {
    if (!val || val.length < 1) {
      diagnosisSearchOptions.value = [];
      return;
    }
    try {
      const res = await priceListAPI.searchIcd10(val, 50);
      const results = res.data || [];
      diagnosisSearchOptions.value = results.map((item) => ({
        ...item,
        display: `${item.icd10_code || ''} - ${item.icd10_description || ''}`.trim(),
      }));
    } catch (_) {
      diagnosisSearchOptions.value = [];
    }
  });
};

const onDiagnosisSelect = async (index, val) => {
  const row = diagnosesList.value[index];
  if (val == null || val === '') {
    row.description = '';
    row.icd10 = '';
    row.gdrg = '';
    row._drgOptions = [];
    return;
  }
  if (typeof val === 'object' && val !== null && (val.icd10_code != null || val.icd10_description != null)) {
    row.description = val.icd10_description || '';
    row.icd10 = val.icd10_code || '';
    row._drgOptions = [];
    try {
      let drgCodes = [];
      if (Array.isArray(val.drg_codes) && val.drg_codes.length) {
        drgCodes = val.drg_codes
          .filter(Boolean)
          .map((code) => (typeof code === 'string' ? { drg_code: code, drg_description: '' } : code));
      }
      if (!drgCodes.length && val.icd10_code) {
        const res = await priceListAPI.getDrgCodesFromIcd10(val.icd10_code);
        drgCodes = res.data || [];
      }
      const options = (drgCodes || [])
        .map((d) => {
          const code = (d.drg_code || d || '').toString().trim();
          if (!code) return null;
          const desc = (d.drg_description || '').toString().trim();
          return { label: desc ? `${code} — ${desc}` : code, value: code };
        })
        .filter(Boolean);
      // de-dupe by value
      const seen = new Set();
      row._drgOptions = options.filter((o) => {
        if (seen.has(o.value)) return false;
        seen.add(o.value);
        return true;
      });
      if (row._drgOptions.length === 1) {
        row.gdrg = row._drgOptions[0].value;
      } else if (row._drgOptions.length > 1) {
        const existing = String(row.gdrg || '').trim();
        const stillValid = row._drgOptions.some((o) => o.value === existing);
        row.gdrg = stillValid ? existing : '';
        $q.notify({
          type: 'info',
          message: `This ICD-10 maps to ${row._drgOptions.length} DRGs — select one or type your own in G-DRG`,
          timeout: 3500,
        });
      } else {
        row.gdrg = '';
      }
      if (row.is_chief) {
        if (row.gdrg) services.principal_gdrg = row.gdrg;
        syncSpecialtyFromPrincipalDiagnosis();
      }
    } catch (_) {
      row._drgOptions = [];
      row.gdrg = '';
    }
    return;
  }
  row.description = typeof val === 'string' ? val : '';
};

const applyDrgOptionsForDiagnoses = async () => {
  const rows = diagnosesList.value || [];
  await Promise.all(
    rows.map(async (row) => {
      const code = String(row.icd10 || '').trim();
      if (!code) {
        row._drgOptions = [];
        return;
      }
      try {
        const res = await priceListAPI.getDrgCodesFromIcd10(code);
        const options = (res.data || [])
          .map((d) => {
            const drg = String(d.drg_code || '').trim();
            if (!drg) return null;
            const desc = String(d.drg_description || '').trim();
            return { label: desc ? `${drg} — ${desc}` : drg, value: drg };
          })
          .filter(Boolean);
        const seen = new Set();
        row._drgOptions = options.filter((o) => {
          if (seen.has(o.value)) return false;
          seen.add(o.value);
          return true;
        });
      } catch (_) {
        row._drgOptions = [];
      }
    })
  );
};

const addDiagnosis = () => {
  const emptyIndex = diagnosesList.value.findIndex(d => !d.description || d.description.trim() === '');
  if (emptyIndex !== -1) {
    $q.notify({
      type: 'info',
      message: 'Please fill in the empty diagnosis row first',
      timeout: 2000,
    });
    return;
  }
  if (diagnosesList.value.length >= 20) {
    $q.notify({
      type: 'warning',
      message: 'Maximum of 20 diagnoses allowed',
      timeout: 2000,
    });
    return;
  }
  const nextIndex = diagnosesList.value.length;
  diagnosesList.value.push({
    index: nextIndex,
    id: null,
    description: '',
    icd10: '',
    gdrg: '',
    is_chief: false,
    _drgOptions: [],
  });
  $q.notify({
    type: 'positive',
    message: 'New diagnosis row added',
    timeout: 2000,
  });
};

const filterProductSearch = (val, update) => {
  update(async () => {
    if (!val || val.length < 1) {
      productSearchOptions.value = [];
      return;
    }
    try {
      const res = await priceListAPI.search(val, undefined, 'product');
      productSearchOptions.value = res.data || [];
    } catch (_) {
      productSearchOptions.value = [];
    }
  });
};

const onPrescriptionProductSelect = (index, val) => {
  const row = prescriptionsList.value[index];
  if (val == null || val === '') {
    row.description = '';
    row.code = '';
    row.insurance_covered = null;
    row.price = 0;
    updatePrescriptionTotal(index);
    return;
  }
  if (typeof val === 'object' && val !== null && (val.product_name != null || val.service_name != null || val.medication_code != null)) {
    row.description = val.product_name || val.service_name || val.item_name || '';
    row.code = val.medication_code || val.item_code || '';
    row.insurance_covered = val.insurance_covered || 'yes';
    row._selectedOption = val;
    if (!row.date) {
      row.date = firstClaimServiceDate();
    }
    if (normalizeInsuranceCovered(row.insurance_covered) === 'no') {
      $q.notify({
        type: 'warning',
        message: 'This drug is not covered by insurance. It is highlighted in red and must be changed or removed before you can save.',
        position: 'top',
      });
    }
    const price = val.claim_amount ?? val.nhia_app ?? val.base_rate ?? val.insured_price ?? 0;
    row.price = Number(price) || 0;
    if (row.quantity == null || row.quantity === '') row.quantity = 0;
    row.total_cost = row.price * row.quantity;
    updatePrescriptionTotal(index);
    return;
  }
  row.description = typeof val === 'string' ? val : '';
  if (!row.date) {
    row.date = firstClaimServiceDate();
  }
};

async function resolvePrescriptionCoverage() {
  const lookups = [];
  for (const row of prescriptionsList.value) {
    const code = String(row.code || '').trim();
    if (!code) {
      row.insurance_covered = null;
      continue;
    }
    lookups.push(
      priceListAPI.search(code, undefined, 'product')
        .then((res) => {
          const items = res.data || [];
          const match = items.find(
            (p) => String(p.medication_code || p.item_code || '').trim() === code
          ) || items[0];
          if (match) {
            row.insurance_covered = match.insurance_covered || 'yes';
            if (!row._selectedOption) row._selectedOption = match;
          } else {
            row.insurance_covered = 'yes';
          }
        })
        .catch(() => {
          row.insurance_covered = row.insurance_covered || 'yes';
        })
    );
  }
  if (lookups.length) await Promise.all(lookups);
}

async function validateCoveredMedicinesOrThrow() {
  await resolvePrescriptionCoverage();
  const bad = [];
  for (let i = 0; i < prescriptionsList.value.length; i += 1) {
    const row = prescriptionsList.value[i];
    if (!row?.description?.trim() || !row?.code?.trim()) continue;
    if (normalizeInsuranceCovered(row.insurance_covered) === 'no') bad.push(i + 1);
  }
  if (bad.length) {
    throw new Error(`Medicine not covered by insurance. Change or remove medicine row(s): ${bad.join(', ')}`);
  }
}

const deleteInvestigation = (index) => {
  $q.dialog({
    title: 'Delete Investigation',
    message: 'Are you sure you want to delete this investigation?',
    cancel: true,
    persistent: true
  }).onOk(() => {
    investigationsList.value[index].description = '';
    investigationsList.value[index].date = '';
    investigationsList.value[index].gdrg = '';
    investigationsList.value[index].id = null;
    $q.notify({
      type: 'positive',
      message: 'Investigation deleted',
    });
  });
};

const addPrescription = () => {
  // Find first empty slot
  const emptyIndex = prescriptionsList.value.findIndex(presc => !presc.description || presc.description.trim() === '');
  if (emptyIndex !== -1) {
    // Focus on the empty slot (it already exists)
    $q.notify({
      type: 'info',
      message: 'Please fill in the empty medicine row',
      timeout: 2000,
    });
  } else if (prescriptionsList.value.length < 300) {
    // Add new row if we haven't reached the limit
    prescriptionsList.value.push({
      index: prescriptionsList.value.length,
      id: null,
      description: '',
      code: '',
      price: 0,
      quantity: 0,
      total_cost: 0,
      date: firstClaimServiceDate(),
      dose: '',
      frequency: '',
      duration: '',
      unparsed: ''
    });
    $q.notify({
      type: 'positive',
      message: 'New medicine row added',
      timeout: 2000,
    });
  } else {
    $q.notify({
      type: 'warning',
      message: 'Maximum of 10 medicines allowed',
      timeout: 2000,
    });
  }
};

const addProcedure = () => {
  const emptyIndex = proceduresList.value.findIndex(p => !p.description || p.description.trim() === '');
  if (emptyIndex !== -1) {
    $q.notify({
      type: 'info',
      message: 'Please fill in the empty surgery row first',
      timeout: 2000,
    });
    return;
  }
  if (proceduresList.value.length >= 10) {
    $q.notify({
      type: 'warning',
      message: 'Maximum of 10 surgeries allowed',
      timeout: 2000,
    });
    return;
  }
  proceduresList.value.push({
    index: proceduresList.value.length,
    description: '',
    diagnosis: '',
    date: firstClaimServiceDate(),
    gdrg: '',
    icd10: '',
    is_principal: false,
  });
  syncPrincipalFromProcedures();
  $q.notify({
    type: 'positive',
    message: 'New surgery row added',
    timeout: 2000,
  });
};

const markSurgeryCompleteAndAdd = async (surgery) => {
  const wid = wardAdmissionId.value;
  if (!wid) return;
  completingSurgeryId.value = surgery.id;
  try {
    await consultationAPI.updateInpatientSurgery(wid, surgery.id, { is_completed: true });
    const dateStr = surgery.surgery_date
      ? (typeof surgery.surgery_date === 'string' ? surgery.surgery_date.split('T')[0] : surgery.surgery_date)
      : '';
    const gdrg = surgery.g_drg_code || '';
    proceduresList.value.push({
      index: proceduresList.value.length,
      description: surgery.surgery_name || '',
      diagnosis: '',
      date: dateStr || firstClaimServiceDate(),
      gdrg,
      icd10: '',
      is_principal: false,
    });
    syncPrincipalFromProcedures();
    pendingClaimSurgeries.value = pendingClaimSurgeries.value.filter(s => s.id !== surgery.id);
    $q.notify({ type: 'positive', message: 'Surgery marked complete and added to claim', timeout: 2500 });
    if (pendingClaimSurgeries.value.length === 0) showPendingSurgeriesDialog.value = false;
  } catch (e) {
    $q.notify({
      type: 'negative',
      message: e?.response?.data?.detail || 'Failed to mark surgery complete',
      timeout: 3000,
    });
  } finally {
    completingSurgeryId.value = null;
  }
};

const deleteProcedure = (index) => {
  $q.dialog({
    title: 'Delete Surgery',
    message: 'Are you sure you want to delete this surgery?',
    cancel: true,
    persistent: true
  }).onOk(() => {
    proceduresList.value[index].description = '';
    proceduresList.value[index].diagnosis = '';
    proceduresList.value[index].date = '';
    proceduresList.value[index].gdrg = '';
    proceduresList.value[index].icd10 = '';
    proceduresList.value[index].is_principal = false;
    proceduresList.value[index]._selectedOption = null;
    syncPrincipalFromProcedures();
    $q.notify({
      type: 'positive',
      message: 'Surgery deleted',
    });
  });
};

const deleteDiagnosis = (index) => {
  $q.dialog({
    title: 'Delete Diagnosis',
    message: 'Are you sure you want to delete this diagnosis?',
    cancel: true,
    persistent: true
  }).onOk(() => {
    diagnosesList.value.splice(index, 1);
    diagnosesList.value.forEach((row, i) => { row.index = i; });
    $q.notify({
      type: 'positive',
      message: 'Diagnosis deleted',
    });
  });
};

function openAddDiagnosisDialog() {
  resetClaimDiagnosisForm();
  loadIcd10AndDrgOptions();
  showDiagnosisDialog.value = true;
}

function resetClaimDiagnosisForm() {
  selectedIcd10.value = null;
  selectedDrgDiagnosis.value = null;
  claimDiagnosisDrgOptions.value = [];
  Object.assign(claimDiagnosisForm, {
    description: '',
    icd10: '',
    gdrg: '',
    is_chief: false,
  });
}

async function loadIcd10AndDrgOptions() {
  try {
    const [icdRes, drgRes] = await Promise.all([
      priceListAPI.searchIcd10('', 100),
      priceListAPI.search('', undefined, 'unmapped_drg'),
    ]);
    const results = icdRes.data || [];
    allIcd10Codes.value = results;
    icd10Options.value = results.map((item) => ({
      ...item,
      display: `${item.icd10_code} - ${item.icd10_description || ''}`,
    }));
    allDrgDiagnoses.value = drgRes.data || [];
    drgDiagnosisOptions.value = allDrgDiagnoses.value;
  } catch (e) {
    icd10Options.value = [];
    drgDiagnosisOptions.value = [];
  }
}

const filterIcd10Codes = (val, update, abort) => {
  if (!val || val.length < 2) {
    update(() => {
      icd10Options.value = allIcd10Codes.value.map((item) => ({
        ...item,
        display: `${item.icd10_code} - ${item.icd10_description || ''}`,
      }));
    });
    return;
  }
  update(async () => {
    try {
      const res = await priceListAPI.searchIcd10(val, 50);
      const results = res.data || [];
      icd10Options.value = results.map((item) => ({
        ...item,
        display: `${item.icd10_code} - ${item.icd10_description || ''}`,
      }));
    } catch (_) {
      icd10Options.value = [];
    }
  });
};

const filterDrgDiagnoses = (val, update, abort) => {
  update(() => {
    if (!val) {
      drgDiagnosisOptions.value = allDrgDiagnoses.value;
      return;
    }
    const term = val.toLowerCase();
    drgDiagnosisOptions.value = allDrgDiagnoses.value.filter(
      (d) => (d.item_name || '').toLowerCase().includes(term) || (d.item_code || '').toLowerCase().includes(term)
    );
    if (drgDiagnosisOptions.value.length === 0) {
      priceListAPI.search(val, undefined, 'unmapped_drg').then((res) => {
        drgDiagnosisOptions.value = res.data || [];
      }).catch(() => { drgDiagnosisOptions.value = []; });
    }
  });
};

async function onIcd10Selected(icd10Item) {
  if (!icd10Item) {
    claimDiagnosisForm.icd10 = '';
    claimDiagnosisForm.gdrg = '';
    claimDiagnosisForm.description = '';
    selectedDrgDiagnosis.value = null;
    claimDiagnosisDrgOptions.value = [];
    return;
  }
  claimDiagnosisForm.icd10 = icd10Item.icd10_code || '';
  if (icd10Item.icd10_description && !claimDiagnosisForm.description) {
    claimDiagnosisForm.description = icd10Item.icd10_description;
  }
  selectedDrgDiagnosis.value = null;
  claimDiagnosisDrgOptions.value = [];
  try {
    let drgCodes = [];
    if (Array.isArray(icd10Item.drg_codes) && icd10Item.drg_codes.length) {
      drgCodes = icd10Item.drg_codes
        .filter(Boolean)
        .map((code) => (typeof code === 'string' ? { drg_code: code, drg_description: '' } : code));
    }
    if (!drgCodes.length && icd10Item.icd10_code) {
      const res = await priceListAPI.getDrgCodesFromIcd10(icd10Item.icd10_code);
      drgCodes = res.data || [];
    }
    const options = (drgCodes || [])
      .map((d) => {
        const code = String(d.drg_code || d || '').trim();
        if (!code) return null;
        const desc = String(d.drg_description || '').trim();
        return { label: desc ? `${code} — ${desc}` : code, value: code };
      })
      .filter(Boolean);
    const seen = new Set();
    claimDiagnosisDrgOptions.value = options.filter((o) => {
      if (seen.has(o.value)) return false;
      seen.add(o.value);
      return true;
    });
    if (claimDiagnosisDrgOptions.value.length === 1) {
      claimDiagnosisForm.gdrg = claimDiagnosisDrgOptions.value[0].value;
    } else if (claimDiagnosisDrgOptions.value.length > 1) {
      claimDiagnosisForm.gdrg = '';
      $q.notify({
        type: 'info',
        message: `This ICD-10 maps to ${claimDiagnosisDrgOptions.value.length} DRGs — select one`,
        timeout: 3500,
      });
    } else {
      claimDiagnosisForm.gdrg = '';
    }
  } catch (_) {
    claimDiagnosisDrgOptions.value = [];
    claimDiagnosisForm.gdrg = '';
  }
}

function onDrgDiagnosisSelected(drgItem) {
  if (!drgItem) {
    claimDiagnosisForm.gdrg = '';
    claimDiagnosisForm.description = '';
    selectedIcd10.value = null;
    return;
  }
  claimDiagnosisForm.gdrg = drgItem.item_code || drgItem.g_drg_code || '';
  claimDiagnosisForm.description = drgItem.item_name || '';
  if (drgItem.icd10_code && !claimDiagnosisForm.icd10) {
    claimDiagnosisForm.icd10 = drgItem.icd10_code;
  }
  selectedIcd10.value = null;
}

function addDiagnosisFromDialog() {
  const d = claimDiagnosisForm;
  if (!d.description || !d.description.trim()) {
    $q.notify({ type: 'warning', message: 'Please enter a diagnosis description.' });
    return;
  }
  const nextIndex = diagnosesList.value.length;
  const isChief = !!d.is_chief;
  if (isChief) {
    diagnosesList.value.forEach((row) => { row.is_chief = false; });
  }
  diagnosesList.value.push({
    index: nextIndex,
    id: null,
    description: (d.description || '').trim(),
    icd10: (d.icd10 || '').trim(),
    gdrg: (d.gdrg || '').trim(),
    is_chief: isChief,
    _drgOptions: [...(claimDiagnosisDrgOptions.value || [])],
  });
  if (isChief) {
    const gdrg = String(d.gdrg || '').trim();
    if (gdrg) services.principal_gdrg = gdrg;
    syncSpecialtyFromPrincipalDiagnosis();
  }
  resetClaimDiagnosisForm();
  showDiagnosisDialog.value = false;
  $q.notify({ type: 'positive', message: 'Diagnosis added', timeout: 2000 });
}

const deletePrescription = (index) => {
  $q.dialog({
    title: 'Delete Medicine',
    message: 'Are you sure you want to delete this medicine?',
    cancel: true,
    persistent: true
  }).onOk(() => {
    prescriptionsList.value[index].description = '';
    prescriptionsList.value[index].code = '';
    prescriptionsList.value[index].price = 0;
    prescriptionsList.value[index].quantity = 0;
    prescriptionsList.value[index].total_cost = 0;
    prescriptionsList.value[index].date = '';
    prescriptionsList.value[index].dose = '';
    prescriptionsList.value[index].frequency = '';
    prescriptionsList.value[index].duration = '';
    prescriptionsList.value[index].unparsed = '';
    prescriptionsList.value[index].id = null;
    calculateClaimSummary();
    $q.notify({
      type: 'positive',
      message: 'Medicine deleted',
    });
  });
};

const saveAndFinalize = async (e) => {
  if (e) {
    e.preventDefault();
  }
  saving.value = true;
  try {
    await validateCoveredMedicinesOrThrow();
    // Save claim data directly (do not reload after save to avoid overwriting with stale data)
    const claimData = buildClaimPayload();
    await claimsAPI.updateDetailed(claimId.value, claimData);
    await new Promise(resolve => setTimeout(resolve, 300));
    await claimsAPI.finalize(claimId.value);
    $q.notify({
      type: 'positive',
      message: 'Claim saved and finalized successfully',
    });
    $router.push('/claims');
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to save and finalize claim',
    });
  } finally {
    saving.value = false;
  }
};

const loadClaimData = async () => {
  loading.value = true;
  try {
    const response = await claimsAPI.getEditDetails(claimId.value);
    const data = response.data;
    
    // Debug: Log OPD encounter info if available
    if (data.debug) {
      console.log('OPD Encounter Debug Info:', data.debug);
      console.log('Diagnoses in response:', data.diagnoses?.length || 0);
      console.log('Prescriptions in response:', data.prescriptions?.length || 0);
      console.log('Investigations in response:', data.investigations?.length || 0);
    }
    
    // Set claim status
    claimStatus.value = data.claim.status;
    applyVettingFromClaim(data.claim || {});
    claimMeta.claim_check_code = data.claim.claim_check_code || '';
    patientNhiaMeta.value = {
      insured: !!data.patient?.insured,
      nhis_active: !!data.patient?.nhis_active,
    };

    // ClaimIT errors for this claim (from Correct Errors report uploads), grouped by section
    claimitErrors.value = data.claimit_errors || { messages: [], by_section: {} };
    
    // Populate patient info
    const insuranceId = data.patient.insurance_id || '';
    const patientHin = data.patient.hin || '';
    let memberNumber = insuranceId;
    let ghanaCard = '';
    // If insurance is Ghana Card and HIN exists, show HIN as member no (ClaimIT-ready)
    if (isGhanaCard(insuranceId) && patientHin && !isGhanaCard(patientHin)) {
      ghanaCard = normalizeGhanaCard(insuranceId);
      memberNumber = patientHin;
    } else if (isGhanaCard(insuranceId)) {
      ghanaCard = '';
      memberNumber = insuranceId;
    }
    Object.assign(patientInfo, {
      surname: data.patient.surname || '',
      other_names: `${data.patient.name} ${data.patient.other_names || ''}`.trim(),
      date_of_birth: data.patient.date_of_birth || '',
      age: data.patient.age,
      gender: data.patient.gender,
      member_number: memberNumber,
      ghana_card: ghanaCard,
      hin: patientHin,
      hospital_record_no: data.patient.card_number || '',
      card_serial_no: data.encounter.ccc_number || '',
    });
    
    // Populate services
    const hasDrugs = (data.prescriptions && data.prescriptions.length > 0) &&
      data.prescriptions.some(p => ((p.code && p.code.trim()) || (p.description && p.description.trim())) && (Number(p.quantity) || 0) > 0);
    Object.assign(services, {
      type_of_service: data.claim.type_of_service || 'OPD',
      includes_pharmacy: (data.claim.includes_pharmacy === true) || !!hasDrugs,
      first_visit: data.encounter.created_at ? data.encounter.created_at.split('T')[0] : '',
      second_visit: data.encounter.finalized_at ? data.encounter.finalized_at.split('T')[0] : '',
      type_of_attendance: data.claim.type_of_attendance || 'EAE',
      specialty_code: data.claim.specialty_attended || '',
      outcome: data.claim.service_outcome || 'DISC',
      all_inclusive: !data.claim.is_unbundled,
      principal_gdrg: data.claim.principal_gdrg || '',
    });
    
    // Reset and populate procedures (min 3 slots; use actual count if more)
    procedures.physician_id = data.claim.physician_id || '';
    const proceduresLength = Math.max(3, data.procedures?.length || 3);
    proceduresList.value = Array.from({ length: proceduresLength }, (_, idx) => {
      const proc = data.procedures && data.procedures[idx] ? data.procedures[idx] : null;
      const icd10 = (proc && (proc.icd10 ?? proc.icd_10)) ? String(proc.icd10 ?? proc.icd_10).trim() : '';
      return {
        index: idx,
        description: proc?.description || '',
        diagnosis: '',
        date: proc?.date ? proc.date.split('T')[0] : '',
        gdrg: proc?.gdrg || '',
        icd10,
        is_principal: false,
      };
    });
    
    // Determine if this is an IPD claim
    const isIPD = (data.claim.type_of_service || 'OPD').toUpperCase() === 'IPD';
    
    // For IPD claims with ward admission, load pending (incomplete) surgeries for "mark complete & add to claim"
    if (isIPD && data.debug?.ward_admission_id) {
      wardAdmissionId.value = data.debug.ward_admission_id;
      try {
        const surRes = await consultationAPI.getInpatientSurgeries(wardAdmissionId.value);
        const list = surRes.data || [];
        pendingClaimSurgeries.value = list.filter(s => !s.is_completed);
      } catch (e) {
        console.warn('Could not load inpatient surgeries for claim', e);
        pendingClaimSurgeries.value = [];
      }
    } else {
      wardAdmissionId.value = null;
      pendingClaimSurgeries.value = [];
    }
    
    // For IPD claims, use actual data length (OPD + IPD can have more items)
    // For OPD claims, pad to minimum required slots
    const diagnosesLength = Math.max(4, data.diagnoses ? data.diagnoses.length : 4);
    const investigationsLength = isIPD
      ? Math.max(5, data.investigations ? data.investigations.length : 5)
      : 5;
    const prescriptionsLength = isIPD
      ? Math.max(5, data.prescriptions ? data.prescriptions.length : 5)
      : 5;
    
    // Reset and populate diagnoses
    diagnosesList.value = Array.from({ length: diagnosesLength }, (_, idx) => {
      const diag = data.diagnoses && data.diagnoses[idx] ? data.diagnoses[idx] : null;
      return {
        index: idx,
        id: diag?.id || null,
        description: diag?.description || '',
        icd10: diag?.icd10 || '',
        gdrg: diag?.gdrg || '',
        is_chief: diag?.is_chief || false,
        _drgOptions: [],
      };
    });
    await applyDrgOptionsForDiagnoses();

    // After diagnoses load, align procedure diagnosis labels and principal G-DRG from procedures
    for (const proc of proceduresList.value) {
      const icd = String(proc.icd10 || '').trim().toUpperCase();
      if (!icd) continue;
      const match = diagnosesList.value.find(
        (d) => String(d.icd10 || '').trim().toUpperCase() === icd
      );
      if (match) {
        proc.diagnosis = match.description || '';
      }
    }
    const principalGdrg = String(services.principal_gdrg || '').trim();
    if (principalGdrg) {
      const matchProc = proceduresList.value.find(
        (p) => String(p.description || '').trim() && String(p.gdrg || '').trim() === principalGdrg
      );
      if (matchProc) matchProc.is_principal = true;
    }
    syncPrincipalFromProcedures();
    
    // Reset and populate investigations
    investigationsList.value = Array.from({ length: investigationsLength }, (_, idx) => {
      const inv = data.investigations && data.investigations[idx] ? data.investigations[idx] : null;
      return {
        index: idx,
        id: inv?.id || null,
        description: inv?.description || '',
        date: inv?.date ? inv.date.split('T')[0] : '',
        gdrg: inv?.gdrg || '',
      };
    });
    
    // Reset and populate prescriptions
    prescriptionsList.value = Array.from({ length: prescriptionsLength }, (_, idx) => {
      const presc = data.prescriptions && data.prescriptions[idx] ? data.prescriptions[idx] : null;
      return {
        index: idx,
        id: presc?.id || null,
        description: presc?.description || '',
        code: presc?.code || '',
        insurance_covered: null,
        price: presc?.price || 0,
        quantity: presc?.quantity || 0,
        total_cost: presc?.total_cost || 0,
        date: presc?.date ? presc.date.split('T')[0] : '',
        dose: presc?.dose || '',
        frequency: presc?.frequency || '',
        duration: presc?.duration || '',
        unparsed: presc?.unparsed || '',
      };
    });

    await resolvePrescriptionCoverage();
    
    // Populate claim summary
    if (data.claim_summary) {
      claimSummary.value[0].tariff_amount = data.claim_summary.inpatient_amount || 0;
      claimSummary.value[1].tariff_amount = data.claim_summary.outpatient_amount || 0;
      claimSummary.value[2].tariff_amount = data.claim_summary.investigations_amount || 0;
      claimSummary.value[3].tariff_amount = data.claim_summary.pharmacy_amount || 0;
      claimSummary.value[4].tariff_amount = data.claim_summary.total_amount ?? totalClaimAmount.value;
    } else {
      calculateClaimSummary();
    }
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to load claim data',
    });
    $router.back();
  } finally {
    skipServiceDateRebase = true;
    syncServiceDateSnapshot();
    skipServiceDateRebase = false;
    loading.value = false;
  }
};

async function onConvertGhanaCardToHin() {
  if (!claimId.value || claimStatus.value === 'finalized') return;
  const ghanaCard = normalizeGhanaCard(patientInfo.ghana_card || patientInfo.member_number);
  if (!isGhanaCard(ghanaCard)) {
    $q.notify({
      type: 'warning',
      message: 'Member number is not a Ghana Card (expected GHA-xxxxxxxx-x)',
      position: 'top',
    });
    return;
  }
  convertingGhanaCard.value = true;
  try {
    const res = await claimsAPI.convertGhanaCardToHin(claimId.value, ghanaCard);
    const data = res.data || {};
    const hin = (data.hin || data.member_no || '').trim();
    if (!hin) {
      throw new Error(data.message || 'No HIN returned from NHIA');
    }
    patientInfo.ghana_card = data.ghana_card || ghanaCard;
    patientInfo.hin = hin;
    patientInfo.member_number = hin;
    $q.notify({
      type: 'positive',
      message: 'Member No set to HIN. Ghana Card kept for CCC / ClaimIT export.',
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

async function onGetClaimCcc() {
  if (!claimId.value || !canGetClaimCcc.value) return;
  const confirmed = await confirmClaimGetCcc($q);
  if (!confirmed) return;

  fetchingClaimCcc.value = true;
  try {
    // HIN cannot generate CCC — use Ghana Card when present
    const memberNo = memberNoForCcc({
      memberNo: patientInfo.member_number,
      ghanaCard: patientInfo.ghana_card,
    });
    if (!memberNo) {
      $q.notify({
        type: 'warning',
        message: 'Enter an NHIA number or Ghana Card to fetch CCC (HIN cannot generate CCC)',
        position: 'top',
      });
      return;
    }
    const res = await claimsAPI.fetchCcc(claimId.value, memberNo);
    applyClaimFetchCccToEditForm(
      {
        patientInfo,
        claimMeta,
        services,
        investigationsList,
        prescriptionsList,
        proceduresList,
      },
      res.data
    );
    skipServiceDateRebase = true;
    syncServiceDateSnapshot();
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

/** Reopen a finalized claim so the user can edit (from view mode or Correct Errors) and save again */
async function reopenClaim() {
  if (!claimId.value || claimStatus.value !== 'finalized') return;
  reopening.value = true;
  try {
    await claimsAPI.reopen(claimId.value);
    $q.notify({
      type: 'positive',
      message: 'Claim reverted to draft. You can now edit and save.',
    });
    await loadClaimData();
    // If they were viewing (from main claims list), switch to edit mode so they can make changes and save
    if (isViewMode.value) {
      isViewMode.value = false;
    }
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to reopen claim',
    });
  } finally {
    reopening.value = false;
  }
}

/** Build the claim payload from current form state (for save and change detection) */
function buildClaimPayload() {
  const diagnosesToSave = diagnosesList.value
    .filter(d => d.description && d.description.trim() !== '');
  const investigationsToSave = investigationsList.value
    .filter(i => i.description && i.description.trim() !== '');
  const prescriptionsToSave = prescriptionsList.value
    .filter(p => p.description && p.description.trim() !== '');
  const proceduresToSave = proceduresList.value
    .filter(p => p.description && p.description.trim() !== '');
  const hasDrugs = prescriptionsToSave.some(p => ((p.code && p.code.trim()) || (p.description && p.description.trim())) && (Number(p.quantity) || 0) > 0);
  return {
    physician_id: procedures.physician_id || services.specialty_code || '',
    physician_name: procedures.physician_name || '',
    type_of_service: services.type_of_service,
    includes_pharmacy: hasDrugs || (services.includes_pharmacy === true),
    type_of_attendance: services.type_of_attendance,
    specialty_attended: services.specialty_code || '',
    service_outcome: services.outcome,
    is_unbundled: !services.all_inclusive,
    principal_gdrg: services.principal_gdrg || '',
    claim_check_code: (claimMeta.claim_check_code || '').trim() || null,
    first_visit: services.first_visit || null,
    second_visit: services.second_visit || null,
    third_visit: services.third_visit || null,
    fourth_visit: services.fourth_visit || null,
    duration_of_spell: services.duration_of_spell || null,
    diagnoses: diagnosesToSave.map(d => ({
      id: d.id,
      description: d.description || '',
      icd10: d.icd10 || '',
      gdrg: d.gdrg || '',
      is_chief: !!d.is_chief,
    })),
    investigations: investigationsToSave.map(i => ({
      id: i.id,
      description: i.description || '',
      date: i.date || '',
      gdrg: i.gdrg || '',
    })),
    prescriptions: prescriptionsToSave.map(p => ({
      id: p.id,
      description: p.description,
      code: p.code || '',
      price: Number(p.price) || 0,
      quantity: Number(p.quantity) || 0,
      total_cost: Number(p.total_cost) || 0,
      date: p.date || '',
      dose: p.dose || '',
      frequency: p.frequency || '',
      duration: p.duration || '',
      unparsed: p.unparsed || '',
    })),
    procedures: proceduresToSave.map(p => ({
      description: p.description || '',
      date: p.date || '',
      gdrg: p.gdrg || '',
      icd10: (p.icd10 != null && p.icd10 !== undefined) ? String(p.icd10).trim() : '',
    })),
  };
}

/** View mode: Save Changes = save edits and finalize (with confirm). If no edits, prompt to use Save & Finalize. */
const onSaveChangesInViewMode = async () => {
  const currentPayload = JSON.stringify(buildClaimPayload());
  if (lastSavedClaimPayload.value !== null && currentPayload === lastSavedClaimPayload.value) {
    $q.dialog({
      title: 'No Changes Made',
      message: 'No changes were made to the claim. To finalize without editing, please use the "Save & Finalize" button.',
      ok: 'OK',
    });
    return;
  }
  $q.dialog({
    title: 'Save Changes and Finalize',
    message: 'The claim will be updated with your changes and set as finalized. Do you want to continue?',
    cancel: true,
    persistent: true,
  }).onOk(async () => {
    saving.value = true;
    try {
      await validateCoveredMedicinesOrThrow();
      const claimData = buildClaimPayload();
      await claimsAPI.updateDetailed(claimId.value, claimData);
      await new Promise(resolve => setTimeout(resolve, 300));
      await claimsAPI.finalize(claimId.value);
      $q.notify({
        type: 'positive',
        message: 'Claim updated and finalized successfully',
      });
      $router.push('/claims');
    } catch (error) {
      $q.notify({
        type: 'negative',
        message: error.response?.data?.detail || 'Failed to save and finalize claim',
      });
    } finally {
      saving.value = false;
    }
  });
};

const saveClaim = async (e) => {
  if (e) {
    e.preventDefault();
  }
  saving.value = true;
  try {
    await validateCoveredMedicinesOrThrow();
    const claimData = buildClaimPayload();
    await claimsAPI.updateDetailed(claimId.value, claimData);
    $q.notify({
      type: 'positive',
      message: 'Claim updated successfully',
    });
    await loadClaimData();
    lastSavedClaimPayload.value = JSON.stringify(buildClaimPayload());
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to save claim',
    });
  } finally {
    saving.value = false;
  }
};

onMounted(async () => {
  await facilityStore.fetchPublic();
  providerInfo.provider_name = facilityStore.displayName;
});

const claimNav = computed(() => getClaimsNavPosition(claimId.value));

const claimDisplayName = computed(() => {
  const parts = [patientInfo.other_names, patientInfo.surname].map((x) => String(x || '').trim()).filter(Boolean);
  return parts.join(' ') || 'Claim patient';
});

const claimInitials = computed(() => {
  const bits = claimDisplayName.value.split(/\s+/).filter(Boolean);
  if (!bits.length) return 'CL';
  if (bits.length === 1) return bits[0].slice(0, 2).toUpperCase();
  return `${bits[0][0] || ''}${bits[bits.length - 1][0] || ''}`.toUpperCase();
});

function goToAdjacentClaim(targetId) {
  if (!targetId || loading.value) return;
  const query = { ...$route.query };
  $router.push({ path: `/claims/edit/${targetId}`, query });
}

watch(
  () => [$route.params.claimId, $route.query.view],
  async ([newClaimId]) => {
    claimId.value = parseInt(newClaimId, 10);
    if (!claimId.value) {
      $q.notify({
        type: 'negative',
        message: 'Invalid claim ID',
      });
      $router.push('/claims');
      return;
    }
    isViewMode.value = $route.query.view === 'true';
    await facilityStore.fetchPublic();
    providerInfo.provider_name = facilityStore.displayName;
    await loadClaimData();
    lastSavedClaimPayload.value = JSON.stringify(buildClaimPayload());
  },
  { immediate: true }
);
</script>

<style scoped>
.reopen-claim-fixed-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  background: var(--q-color-amber-2);
  border-top: 1px solid rgba(0, 0, 0, 0.12);
  z-index: 2000;
}
.q-page.reopen-bar-visible {
  padding-bottom: 64px;
}

.claim-nav-controls {
  margin-right: 8px;
}

.claim-nav-position {
  min-width: 4.5rem;
  text-align: center;
}

:deep(tr.medicine-not-covered-row) {
  background-color: rgba(244, 67, 54, 0.09);
}

:deep(tr.medicine-not-covered-row td) {
  box-shadow: inset 0 1px 0 rgba(244, 67, 54, 0.22), inset 0 -1px 0 rgba(244, 67, 54, 0.22);
}

:deep(tr.service-outside-span-row) {
  background-color: rgba(255, 193, 7, 0.12);
}

:deep(tr.service-outside-span-row td) {
  box-shadow: inset 0 1px 0 rgba(255, 193, 7, 0.28), inset 0 -1px 0 rgba(255, 193, 7, 0.28);
}
</style>
