<template>
  <q-page class="q-pa-md" :class="{ 'revert-bar-visible': !loading && status === 'finalized' }">
    <div class="row items-center q-mb-md">
      <q-btn flat round dense icon="arrow_back" @click="$router.back()" />
      <div class="text-h5 q-ml-sm">{{ status === 'finalized' ? 'View Imported Claim' : 'Edit Imported Claim' }}</div>
      <q-space />
      <q-badge :color="status === 'finalized' ? 'positive' : (status === 'flagged' ? 'negative' : 'warning')" :label="status" />
      <q-btn
        class="q-ml-sm"
        outline
        color="teal"
        icon="history_edu"
        label="See recovered data"
        :disable="loading || !payload.claimID"
        @click="showRecoveredData = true"
      />
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

    <q-form v-else @submit.prevent="saveAndFinalize" class="q-gutter-md" :inert="status === 'finalized' || undefined">
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
            <q-input v-model="payload.memberNo" label="Member No" filled class="col-12 col-md-3" />
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
            <q-input v-model="payload.typeOfService" label="Type of Service" filled class="col-12 col-md-3" />
            <q-input v-model="payload.typeOfAttendance" label="Type of Attendance" filled class="col-12 col-md-3" />
            <q-input v-model="payload.specialtyAttended" label="Specialty Attended" filled class="col-12 col-md-3" />
            <q-input v-model="payload.serviceOutcome" label="Service Outcome" filled class="col-12 col-md-3" />
            <q-input v-model="payload.principalGDRG" label="Principal GDRG" filled class="col-12 col-md-3" />
            <q-input v-model="payload.isDependant" label="Is Dependant (0/1)" filled class="col-12 col-md-3" />
            <q-input v-model="payload.isUnbundled" label="Is Unbundled (0/1)" filled class="col-12 col-md-3" />
            <q-input v-model="payload.includesPharmacy" label="Includes Pharmacy (0/1)" filled class="col-12 col-md-3" />
          </div>
          <div class="text-subtitle1 q-mb-sm">Date(s) of Service</div>
          <div v-for="(dt, i) in payload.dateOfService" :key="`date-${i}`" class="row q-col-gutter-sm q-mb-sm">
            <q-input v-model="payload.dateOfService[i]" type="date" filled dense class="col-12 col-md-4" />
            <q-btn flat dense color="negative" icon="delete" @click="payload.dateOfService.splice(i, 1)" />
          </div>
          <q-btn flat color="primary" icon="add" label="Add Service Date" @click="payload.dateOfService.push('')" />
        </q-card-section>
      </q-card>

      <q-card flat bordered>
        <q-card-section>
          <div class="text-h6 q-mb-sm">Diagnosis(es)</div>
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
            <q-input v-model="d.gdrgCode" label="GDRG" filled dense class="col-12 col-md-2" />
            <q-checkbox
              :model-value="principalDiagnosisIndex === i"
              label="Principal diagnosis"
              dense
              class="col-12 col-md-3"
              @update:model-value="(checked) => setPrincipalDiagnosis(i, checked)"
            />
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
              class="col-12 col-md-4"
              @update:model-value="(val) => { d.gdrgCode = val || ''; }"
            />
            <q-input v-model="d.icd10" label="ICD10" filled dense class="col-12 col-md-2" />
            <q-input v-model="d.diagnosis" label="Diagnosis" filled dense class="col-12 col-md-7" />
            <q-btn flat dense color="negative" icon="delete" @click="removeDiagnosis(i)" />
          </div>
          <q-btn flat color="primary" icon="add" label="Add Diagnosis" @click="payload.diagnoses.push({ icd10:'', gdrgCode:'', diagnosis:'' })" />
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
            <q-btn flat dense color="negative" icon="delete" @click="payload.investigations.splice(i,1)" />
          </div>
          <q-btn flat color="primary" icon="add" label="Add Investigation" @click="payload.investigations.push({ serviceDate:'', gdrgCode:'' })" />
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
              @update:model-value="() => syncPrescriptionUnparsed(m)"
            />
            <q-input v-model="m.prescription.unparsed" label="Unparsed" filled dense class="col-12 col-md-10" />
            <q-btn flat dense color="negative" icon="delete" @click="payload.medicines.splice(i,1)" />
          </div>
          <q-btn flat color="primary" icon="add" label="Add Medicine" @click="addMedicine" />
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
            <q-input v-model="p._serviceName" label="Procedure Name" filled dense class="col-12 col-md-5" />
            <q-input v-model="p.gdrgCode" label="GDRG Code" filled dense class="col-12 col-md-2" />
            <q-input v-model="p.icd10" label="ICD10" filled dense class="col-12 col-md-2" />
            <q-input v-model="p.description" label="Description" filled dense class="col-12 col-md-5" />
            <q-input v-model="p.diagnosis" label="Diagnosis" filled dense class="col-12 col-md-10" />
            <q-btn flat dense color="negative" icon="delete" @click="payload.procedures.splice(i,1)" />
          </div>
          <q-btn flat color="primary" icon="add" label="Add Procedure" @click="payload.procedures.push({ serviceDate:'', gdrgCode:'', description:'', icd10:'', diagnosis:'' })" />
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
        <q-btn v-if="status !== 'finalized'" type="submit" color="primary" label="Save and Finalize" :loading="saving" />
        <q-btn v-if="status !== 'finalized'" color="negative" :label="status === 'flagged' ? 'Flagged' : 'Flag claim'" :disable="status === 'flagged'" outline :loading="saving" @click="flagClaim" />
      </div>
    </q-form>

    <RecoveredDataDialog
      v-model="showRecoveredData"
      :claim-id="payload.claimID"
      :payload="payload"
    />

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
  </q-page>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue';
import { useRoute } from 'vue-router';
import { useQuasar } from 'quasar';
import { claimsAPI, priceListAPI } from '../services/api';
import RecoveredDataDialog from '../components/RecoveredDataDialog.vue';
import {
  confirmClaimGetCcc,
  canFetchClaimCcc,
  applyGhimsFetchCccToPayload,
  applyServiceDateChangeToGhimsPayload,
} from '../utils/claimGetCcc';
import {
  asMedicineList,
  isMedicineNotCovered,
  isOutsideServiceSpan,
  normalizeInsuranceCovered,
  claimLineSectionClass,
} from '../utils/claimMedicineCoverage';

const route = useRoute();
const $q = useQuasar();
const loading = ref(true);
const saving = ref(false);
const showRecoveredData = ref(false);
const reverting = ref(false);
const fetchingClaimCcc = ref(false);
const status = ref('draft');
const flagComment = ref('');
const principalDiagnosisIndex = ref(-1);
const itemId = Number(route.params.itemId);
const diagnosisSearchOptions = ref([]);
const investigationSearchOptions = ref([]);
const procedureSearchOptions = ref([]);
const medicineSearchOptions = ref([]);
const payload = reactive({
  claimID: '', claimCheckCode: '', memberNo: '', surname: '', otherNames: '', dateOfBirth: '',
  typeOfService: '', typeOfAttendance: '', specialtyAttended: '', diagnoses: [], medicines: [],
});

const canGetGhimsCcc = computed(() => canFetchClaimCcc({ memberNo: payload.memberNo }));

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

function addMedicine() {
  payload.medicines.push({
    medicineCode: '',
    dispensedQty: '',
    serviceDate: '',
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
    recalculateClaimSummary();
    return;
  }
}

function onDiagnosisSelect(index, val) {
  const row = payload.diagnoses[index];
  if (!row) return;
  if (!val) {
    row.icd10 = '';
    row.diagnosis = '';
    row._diagnosisName = '';
    row._drgOptions = [];
    row._selectedOption = null;
    return;
  }
  if (typeof val === 'object') {
    row.icd10 = val.icd10_code || row.icd10 || '';
    row.diagnosis = val.icd10_description || row.diagnosis || '';
    const drgCodes = Array.isArray(val.drg_codes) ? val.drg_codes.filter(Boolean) : [];
    row._drgOptions = drgCodes.map((code) => ({ label: code, value: code }));
    if (drgCodes.length === 1) {
      row.gdrgCode = drgCodes[0];
    } else if (drgCodes.length > 1) {
      const existing = String(row.gdrgCode || '').trim();
      if (!existing || !drgCodes.includes(existing)) row.gdrgCode = drgCodes[0];
    } else {
      row.gdrgCode = val.gdrg_code || val.g_drg_code || val.drg_code || val.gdrgCode || row.gdrgCode || '';
    }
    row._diagnosisName = val.icd10_description || row._diagnosisName || '';
    row._selectedOption = val;
    if (principalDiagnosisIndex.value === index) {
      payload.principalGDRG = row.gdrgCode || '';
    }
    return;
  }
}

function moveDiagnosisToFirst(index) {
  const list = payload.diagnoses || [];
  if (index <= 0 || index >= list.length) return;
  const [row] = list.splice(index, 1);
  list.unshift(row);
}

function reorderDiagnosesWithPrincipalFirst() {
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
    row._selectedOption = null;
    recalculateClaimSummary();
    return;
  }
  if (typeof val === 'object') {
    row.gdrgCode = val.g_drg_code || val.item_code || row.gdrgCode || '';
    row._serviceName = val.service_name || val.item_name || row._serviceName || '';
    if (!row.description) row.description = row._serviceName || '';
    row._selectedOption = withServiceOptionLabel(val);
    recalculateClaimSummary();
    return;
  }
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

function buildUnparsedFromPrescription(prescription) {
  const dose = String(prescription?.dose || '').trim();
  const frequency = String(prescription?.frequency || '').trim();
  const duration = normalizeDuration(prescription?.duration);
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
  med.prescription.duration = normalizeDuration(med.prescription.duration);
  med.prescription.unparsed = buildUnparsedFromPrescription(med.prescription);
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

function normalizeDuration(value) {
  const raw = String(value || '').trim();
  if (!raw) return '';
  const compact = raw.replace(/\s+/g, ' ');
  const numberOnly = compact.match(/^(\d+(?:\.\d+)?)$/);
  if (numberOnly) return `${numberOnly[1]} days`;
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
              } else if (!diag.gdrgCode) {
                diag.gdrgCode = first.gdrg_code || first.g_drg_code || first.drg_code || first.gdrgCode || '';
              }
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
  return {
    claimID: p.claimID || '',
    claimCheckCode: p.claimCheckCode || '',
    memberNo: p.memberNo || '',
    surname: p.surname || '',
    otherNames: p.otherNames || '',
    dateOfBirth: p.dateOfBirth || '',
    typeOfService: p.typeOfService || '',
    typeOfAttendance: p.typeOfAttendance || '',
    specialtyAttended: p.specialtyAttended || '',
    diagnoses: Array.isArray(p.diagnoses) ? p.diagnoses : [],
    medicines: Array.isArray(p.medicines) ? p.medicines : [],
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
    await claimsAPI.reopenGhimsImportItem(itemId);
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

async function onGetGhimsClaimCcc() {
  if (!canGetGhimsCcc.value) return;
  const confirmed = await confirmClaimGetCcc($q);
  if (!confirmed) return;

  fetchingClaimCcc.value = true;
  try {
    const memberNo = (payload.memberNo || '').trim();
    const res = await claimsAPI.fetchGhimsImportCcc(itemId, memberNo || null);
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
    const res = await claimsAPI.getGhimsImportItem(itemId);
    status.value = res.data.status || 'draft';
    flagComment.value = String(res.data.flag_comment || '').trim();
    Object.assign(payload, normalize(res.data.payload || {}));
    const ce = res.data.claimit_errors || {};
    claimitErrors.value = {
      messages: Array.isArray(ce.messages) ? ce.messages : [],
      by_section: { ...emptyClaimitBySection(), ...(ce.by_section || {}) },
    };
    reorderDiagnosesWithPrincipalFirst();
    await resolveServiceNames();
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
        duration: m.prescription?.duration || '',
        unparsed: m.prescription?.unparsed || '',
      },
    }));
    await claimsAPI.updateGhimsImportItem(itemId, clean);
    if (status.value !== 'finalized') {
      await claimsAPI.finalizeGhimsImportItem(itemId);
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
        duration: m.prescription?.duration || '',
        unparsed: m.prescription?.unparsed || '',
      },
    }));
    await claimsAPI.updateGhimsImportItem(itemId, clean);
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
    await claimsAPI.flagGhimsImportItem(itemId, comment);
    $q.notify({ type: 'positive', message: 'Imported claim flagged' });
    await load();
  } catch (e) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || e.message || 'Failed to flag imported claim' });
  } finally {
    saving.value = false;
  }
}

onMounted(load);

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
    payload.principalGDRG = row?.gdrgCode || '';
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
</style>
