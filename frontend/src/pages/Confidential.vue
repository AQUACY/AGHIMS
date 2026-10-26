<template>
  <q-page class="hms-page confidential-page">
    <HmsPageHeader
      title="Confidential"
      subtitle="Visits are handled by code. The client’s name stays in the register."
    />

    <div class="tabs">
      <button
        v-for="tab in visibleTabs"
        :key="tab.id"
        type="button"
        class="tab"
        :class="{ on: activeTab === tab.id }"
        @click="activeTab = tab.id"
      >
        {{ tab.label }}
      </button>
    </div>

    <section v-if="activeTab === 'codes'" class="panel">
      <h2>Prepare codes</h2>
      <p class="hint">Records keeps this list and gives one code to the client when the visit is booked. Example: SCRN0001.</p>
      <div class="form-row">
        <label>Prefix <input v-model="pool.prefix" /></label>
        <label>Start <input v-model.number="pool.start" type="number" min="1" /></label>
        <label>How many <input v-model.number="pool.count" type="number" min="1" max="500" /></label>
        <label>Digits <input v-model.number="pool.pad" type="number" min="1" max="8" /></label>
        <HmsButton variant="primary" size="sm" :disabled="busy" @click="generateCodes">Prepare</HmsButton>
      </div>
      <p v-if="poolResult" class="result">Prepared {{ poolResult.created }} codes, {{ poolResult.first }} to {{ poolResult.last }}.</p>
      <p class="hint">{{ codeSummary.available }} available · {{ codeSummary.assigned }} assigned</p>
    </section>

    <section v-else-if="activeTab === 'issue'" class="panel">
      <h2>Give a code for this visit</h2>
      <p class="hint">Find the client, choose the priced service the claim will use, then hand them the code.</p>

      <div class="composer">
        <div class="step" :class="{ done: !!selectedPatient }">
          <div class="step-index">1</div>
          <div class="step-body">
            <div class="step-title">Client</div>
            <div v-if="selectedPatient" class="client-card">
              <div>
                <strong>{{ fullName(selectedPatient) }}</strong>
                <span>{{ selectedPatient.card_number }}</span>
                <span v-if="selectedPatient.insured">{{ selectedPatient.nhis_active ? 'NHIS active' : 'NHIS inactive' }}</span>
              </div>
              <HmsButton variant="ghost" size="sm" @click="clearClient">Change</HmsButton>
            </div>
            <div v-else>
              <q-input
                v-model="patientQuery"
                filled
                dense
                debounce="220"
                placeholder="Type a name or card number"
                :loading="searching"
                @update:model-value="onPatientType"
              >
                <template #prepend><q-icon name="search" /></template>
              </q-input>
              <div v-if="patientHits.length" class="hits">
                <button
                  v-for="person in patientHits"
                  :key="person.id"
                  type="button"
                  class="hit"
                  @click="chooseClient(person)"
                >
                  <strong>{{ fullName(person) }}</strong>
                  <span>{{ person.card_number }}</span>
                </button>
              </div>
              <p v-else-if="searched && !searching" class="hint">No client matches that.</p>
            </div>
          </div>
        </div>

        <div class="step" :class="{ locked: !selectedPatient, done: !!selectedProcedure }">
          <div class="step-index">2</div>
          <div class="step-body">
            <div class="step-title">Service</div>
            <p v-if="!selectedPatient" class="hint">The price list opens once a client is chosen.</p>
            <div v-else class="stack">
              <q-select
                v-model="selectedServiceType"
                filled
                dense
                use-input
                input-debounce="200"
                :options="serviceTypeOptions"
                label="Service type"
                hint="Department or clinic"
                clearable
                @filter="filterServiceTypes"
                @update:model-value="onServiceType"
              >
                <template #no-option>
                  <q-item><q-item-section class="text-grey">No service types in the price list.</q-item-section></q-item>
                </template>
              </q-select>
              <q-select
                v-model="selectedProcedure"
                filled
                dense
                use-input
                input-debounce="200"
                :options="procedureOptions"
                option-label="service_name"
                label="Service"
                :disable="!selectedServiceType"
                :hint="selectedServiceType ? 'Filter by name or G-DRG code' : 'Choose a service type first'"
                clearable
                @filter="filterProcedures"
              >
                <template #option="scope">
                  <q-item v-bind="scope.itemProps">
                    <q-item-section>
                      <q-item-label>{{ scope.opt.service_name }}</q-item-label>
                      <q-item-label caption>{{ scope.opt.g_drg_code }}</q-item-label>
                    </q-item-section>
                  </q-item>
                </template>
                <template #no-option>
                  <q-item><q-item-section class="text-grey">No service matches that.</q-item-section></q-item>
                </template>
              </q-select>
              <div v-if="selectedProcedure" class="claim-map">
                The claim will use <strong>{{ selectedProcedure.g_drg_code }}</strong>
                · {{ selectedProcedure.service_name }}
              </div>
            </div>
          </div>
        </div>

        <div class="step" :class="{ locked: !selectedPatient }">
          <div class="step-index">3</div>
          <div class="step-body">
            <div class="step-title">CCC</div>
            <p v-if="!selectedPatient" class="hint">Fetch it from NHIA, or type it.</p>
            <div v-else class="ccc-row">
              <q-input
                v-model="cccNumber"
                filled
                dense
                class="col"
                :label="cccRequired ? 'CCC number' : 'CCC number, if any'"
                :hint="cccHint"
                maxlength="20"
              />
              <q-btn
                color="secondary"
                icon="cloud_download"
                label="Get CCC"
                :loading="fetchingCcc"
                :disable="!canGetCcc"
                @click="fetchCcc"
              />
            </div>
          </div>
        </div>

        <div class="step" :class="{ locked: !selectedProcedure }">
          <div class="step-index">4</div>
          <div class="step-body">
            <div class="step-title">Code</div>
            <p v-if="!availableCodes.length" class="hint">Prepare a code list first. There is no code to give.</p>
            <p v-else-if="!selectedProcedure" class="hint">The code is given after the service is chosen.</p>
            <div v-else class="stack">
              <q-select
                v-model="chosenCodeId"
                filled
                dense
                use-input
                input-debounce="200"
                emit-value
                map-options
                :options="codeOptions"
                label="Code to give the client"
                @filter="filterCodes"
              />
              <HmsButton variant="primary" :disabled="busy || !canGive" @click="issueVisit">
                Give {{ chosenCodeLabel }}
              </HmsButton>
            </div>
          </div>
        </div>
      </div>

      <div v-if="issued" class="issued">
        <div class="code">{{ issued.code }}</div>
        <p>
          Tell {{ issued.patient_name }} this code.
          <template v-if="issued.procedure_name">
            {{ issued.procedure_name }}<template v-if="issued.procedure_g_drg_code"> · {{ issued.procedure_g_drg_code }}</template>
            is on today’s consultation list.
          </template>
        </p>
        <HmsButton variant="primary" size="sm" @click="openConsult(issued.encounter_id)">Open on the consultation list</HmsButton>
      </div>
    </section>

    <section v-else-if="activeTab === 'lookup'" class="panel">
      <h2>Find a visit by code</h2>
      <p class="hint">Service points use this code. The client’s name is not shown here.</p>
      <div class="form-row">
        <label class="grow">Code <input v-model="lookupCode" placeholder="SCRN0001" @keyup.enter="runLookup" /></label>
        <HmsButton variant="primary" size="sm" :disabled="busy" @click="runLookup">Look up</HmsButton>
      </div>
      <div v-if="lookupResult" class="visit-list">
        <article v-for="visit in lookupResult.encounters" :key="visit.id" class="visit">
          <div>
            <strong>{{ lookupResult.code }}</strong>
            <span>{{ visitLine(visit) }}</span>
          </div>
          <div class="visit-actions">
            <HmsButton variant="soft" size="sm" @click="openVitals">Vitals</HmsButton>
            <HmsButton variant="soft" size="sm" @click="openConsult(visit.id)">Consultation</HmsButton>
          </div>
        </article>
        <HmsButton v-if="canIssue" variant="secondary" size="sm" @click="openFollowUp({ code: lookupResult.code })">
          Start follow-up on this code
        </HmsButton>
      </div>
    </section>

    <section v-else class="panel">
      <h2>Register</h2>
      <p class="hint">Each code is listed with the client it belongs to. Print the chart from the profile. Claims are generated from the visit.</p>
      <div class="form-row">
        <label class="grow">Search <input v-model="registerSearch" placeholder="Code, name, or card" @keyup.enter="loadRegister" /></label>
        <HmsButton variant="secondary" size="sm" :disabled="busy" @click="loadRegister">Search</HmsButton>
      </div>
      <div v-if="!registerRows.length" class="hint">No assigned codes yet.</div>
      <article v-for="row in registerRows" :key="row.code_id" class="register-card">
        <header>
          <div class="code">{{ row.code }}</div>
          <div>
            <strong>{{ row.patient_name }}</strong>
            <span>{{ row.patient_card_number }}<template v-if="row.patient_insurance_id"> · {{ row.patient_insurance_id }}</template></span>
          </div>
          <HmsButton v-if="!claimsMode" variant="soft" size="sm" @click="openProfile(row)">Profile &amp; print</HmsButton>
        </header>
        <div v-for="visit in row.encounters" :key="visit.id" class="visit slim">
          <span>{{ visitLine(visit) }}</span>
          <div class="visit-actions">
            <HmsButton v-if="!claimsMode" variant="soft" size="sm" @click="openConsult(visit.id)">Open</HmsButton>
            <HmsButton v-if="visit.status === 'finalized'" variant="primary" size="sm" @click="openClaim(visit.id)">Generate claim</HmsButton>
          </div>
        </div>
        <HmsButton v-if="canIssue" variant="secondary" size="sm" @click="openFollowUp(row)">Follow-up</HmsButton>
      </article>
    </section>

    <q-dialog v-model="followUpOpen" persistent>
      <q-card class="follow-card">
        <q-card-section>
          <div class="text-h6">Follow-up on {{ followUpTarget?.code }}</div>
          <p class="hint">Choose the priced service. The claim uses that G-DRG code. The client keeps the same visit code.</p>
        </q-card-section>
        <q-card-section class="stack">
          <q-select
            v-model="followServiceType"
            filled
            dense
            use-input
            input-debounce="200"
            :options="followServiceOptions"
            label="Service type"
            clearable
            @filter="filterFollowServiceTypes"
            @update:model-value="onFollowServiceType"
          />
          <q-select
            v-model="followProcedure"
            filled
            dense
            use-input
            input-debounce="200"
            :options="followProcedureOptions"
            option-label="service_name"
            label="Service"
            :disable="!followServiceType"
            clearable
            @filter="filterFollowProcedures"
          >
            <template #option="scope">
              <q-item v-bind="scope.itemProps">
                <q-item-section>
                  <q-item-label>{{ scope.opt.service_name }}</q-item-label>
                  <q-item-label caption>{{ scope.opt.g_drg_code }}</q-item-label>
                </q-item-section>
              </q-item>
            </template>
          </q-select>
          <div v-if="followProcedure" class="claim-map">
            The claim will use <strong>{{ followProcedure.g_drg_code }}</strong>
          </div>
          <div class="ccc-row">
            <q-input v-model="followCcc" filled dense class="col" label="CCC number, if any" maxlength="20" />
            <q-btn
              v-if="followUpTarget?.patient_id"
              color="secondary"
              icon="cloud_download"
              label="Get CCC"
              :loading="fetchingCcc"
              :disable="!canGetFollowCcc"
              @click="fetchFollowCcc"
            />
          </div>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Cancel" @click="followUpOpen = false" />
          <q-btn color="primary" label="Open follow-up" :loading="busy" :disable="!followProcedure" @click="submitFollowUp" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useQuasar } from 'quasar';
import HmsPageHeader from '../components/ui/HmsPageHeader.vue';
import HmsButton from '../components/ui/HmsButton.vue';
import { confidentialAPI, patientsAPI, priceListAPI } from '../services/api';
import { useAuthStore } from '../stores/auth';
import { usePatientsStore } from '../stores/patients';
import { canFetchNhiaCcc } from '../utils/nhiaForm';

const $q = useQuasar();
const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();
const patientsStore = usePatientsStore();

const claimsMode = computed(() => route.name === 'ClaimsConfidential');
const canPool = computed(() => authStore.canAccess(['Admin', 'Records']));
const canIssue = computed(() => authStore.canAccess(['Admin', 'Records', 'Doctor', 'PA']));
const canRegister = computed(() => authStore.canAccess(['Admin', 'Doctor', 'PA', 'Claims']));

const visibleTabs = computed(() => {
  const tabs = [];
  if (!claimsMode.value && canPool.value) tabs.push({ id: 'codes', label: 'Code list' });
  if (!claimsMode.value && canIssue.value) tabs.push({ id: 'issue', label: 'Give a code' });
  if (!claimsMode.value) tabs.push({ id: 'lookup', label: 'Look up' });
  if (canRegister.value) tabs.push({ id: 'register', label: 'Register' });
  return tabs;
});

const activeTab = ref('lookup');
const busy = ref(false);
const pool = ref({ prefix: 'SCRN', start: 1, count: 50, pad: 4 });
const poolResult = ref(null);
const codeSummary = ref({ available: 0, assigned: 0 });
const availableCodes = ref([]);
const patientQuery = ref('');
const patientHits = ref([]);
const selectedPatient = ref(null);
const searching = ref(false);
const searched = ref(false);
const allServiceTypes = ref([]);
const serviceTypeOptions = ref([]);
const selectedServiceType = ref(null);
const allProcedures = ref([]);
const procedureOptions = ref([]);
const selectedProcedure = ref(null);
const cccNumber = ref('');
const fetchingCcc = ref(false);
const chosenCodeId = ref(null);
const codeOptions = ref([]);
const issued = ref(null);
const followUpOpen = ref(false);
const followUpTarget = ref(null);
const followServiceType = ref(null);
const followServiceOptions = ref([]);
const followProcedures = ref([]);
const followProcedureOptions = ref([]);
const followProcedure = ref(null);
const followCcc = ref('');
const lookupCode = ref('');
const lookupResult = ref(null);
const registerSearch = ref('');
const registerRows = ref([]);

const fullName = (person) => [person.name, person.surname, person.other_names].filter(Boolean).join(' ');

const cccRequired = computed(() => canFetchNhiaCcc(selectedPatient.value));
const canGetCcc = computed(() => canFetchNhiaCcc(selectedPatient.value));
const cccHint = computed(() => {
  const person = selectedPatient.value;
  if (!person?.insured) return 'Optional for a cash client. Type a CCC or leave it empty.';
  if (!person?.nhis_active) return 'Inactive NHIS. This visit is cash, and Get CCC stays off.';
  return 'Required for active NHIS. Get CCC, or type it.';
});
const chosenCodeLabel = computed(() => {
  const match = availableCodes.value.find((row) => row.id === chosenCodeId.value);
  return match?.code || availableCodes.value[0]?.code || 'code';
});
const canGive = computed(() => !!selectedPatient.value && !!selectedServiceType.value && !!selectedProcedure.value && !!chosenCodeId.value && (!cccRequired.value || !!cccNumber.value.trim()));
const canGetFollowCcc = computed(() => canFetchNhiaCcc(followUpTarget.value));

const visitLine = (visit) => {
  const service = visit.procedure_name || visit.department || 'General';
  const code = visit.procedure_g_drg_code ? ` · ${visit.procedure_g_drg_code}` : '';
  return `${service}${code} · ${visit.status} · ${formatWhen(visit.created_at)}`;
};

const formatWhen = (value) => {
  if (!value) return '';
  return new Date(value).toLocaleString('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit',
  });
};

const notifyError = (error, fallback) => {
  $q.notify({ type: 'negative', message: error.response?.data?.detail || fallback });
};

const loadCodeSummary = async () => {
  if (!canIssue.value) return;
  try {
    const response = await confidentialAPI.listCodes('available');
    codeSummary.value = { available: response.data.available, assigned: response.data.assigned };
    availableCodes.value = response.data.codes || [];
    codeOptions.value = availableCodes.value.map((row) => ({ label: row.code, value: row.id }));
    if (!chosenCodeId.value || !availableCodes.value.some((row) => row.id === chosenCodeId.value)) {
      chosenCodeId.value = availableCodes.value[0]?.id || null;
    }
  } catch (error) {
    notifyError(error, 'Could not load codes');
  }
};

const generateCodes = async () => {
  busy.value = true;
  try {
    const response = await confidentialAPI.generateCodes(pool.value);
    poolResult.value = response.data;
    pool.value.start = pool.value.start + pool.value.count;
    await loadCodeSummary();
  } catch (error) {
    notifyError(error, 'Could not prepare codes');
  } finally {
    busy.value = false;
  }
};

const onPatientType = (value) => {
  const term = String(value || '').trim();
  searched.value = false;
  if (term.length < 2) {
    patientHits.value = [];
    return;
  }
  searchPatients(term);
};

const searchPatients = async (term) => {
  searching.value = true;
  try {
    const byCard = await patientsAPI.getByCard(term).catch(() => null);
    const cardRows = Array.isArray(byCard?.data) ? byCard.data : (byCard?.data ? [byCard.data] : []);
    const byName = await patientsAPI.searchByName(term).catch(() => ({ data: [] }));
    const merged = [...cardRows, ...(byName.data || [])];
    const seen = new Set();
    patientHits.value = merged.filter((person) => {
      if (!person?.id || seen.has(person.id)) return false;
      seen.add(person.id);
      return true;
    });
    searched.value = true;
  } catch (error) {
    notifyError(error, 'Search failed');
  } finally {
    searching.value = false;
  }
};

const chooseClient = (person) => {
  selectedPatient.value = person;
  patientHits.value = [];
  patientQuery.value = '';
  searched.value = false;
  cccNumber.value = '';
};

const clearClient = () => {
  selectedPatient.value = null;
  selectedServiceType.value = null;
  selectedProcedure.value = null;
  allProcedures.value = [];
  procedureOptions.value = [];
  cccNumber.value = '';
  issued.value = null;
};

const loadServiceTypes = async () => {
  try {
    const response = await priceListAPI.getServiceTypes();
    allServiceTypes.value = response.data || [];
    serviceTypeOptions.value = allServiceTypes.value;
    followServiceOptions.value = allServiceTypes.value;
  } catch (error) {
    notifyError(error, 'Could not load the price list');
  }
};

const filterServiceTypes = (val, update) => {
  update(() => {
    const needle = String(val || '').toLowerCase();
    serviceTypeOptions.value = !needle
      ? allServiceTypes.value
      : allServiceTypes.value.filter((item) => String(item).toLowerCase().includes(needle));
  });
};

const filterFollowServiceTypes = (val, update) => {
  update(() => {
    const needle = String(val || '').toLowerCase();
    followServiceOptions.value = !needle
      ? allServiceTypes.value
      : allServiceTypes.value.filter((item) => String(item).toLowerCase().includes(needle));
  });
};

const loadProcedures = async (serviceType, target) => {
  if (!serviceType) {
    target.all.value = [];
    target.options.value = [];
    target.selected.value = null;
    return;
  }
  try {
    const response = await priceListAPI.getProceduresByServiceType(serviceType);
    target.all.value = response.data || [];
    target.options.value = target.all.value;
    target.selected.value = null;
  } catch (error) {
    notifyError(error, 'Could not load services');
    target.all.value = [];
    target.options.value = [];
  }
};

const onServiceType = (serviceType) => {
  loadProcedures(serviceType, { all: allProcedures, options: procedureOptions, selected: selectedProcedure });
};

const onFollowServiceType = (serviceType) => {
  loadProcedures(serviceType, { all: followProcedures, options: followProcedureOptions, selected: followProcedure });
};

const filterProcedureList = (val, update, source, target) => {
  update(() => {
    const needle = String(val || '').toLowerCase();
    target.value = !needle
      ? source.value
      : source.value.filter((item) =>
        String(item.service_name || '').toLowerCase().includes(needle)
        || String(item.g_drg_code || '').toLowerCase().includes(needle)
      );
  });
};

const filterProcedures = (val, update) => filterProcedureList(val, update, allProcedures, procedureOptions);
const filterFollowProcedures = (val, update) => filterProcedureList(val, update, followProcedures, followProcedureOptions);

const filterCodes = (val, update) => {
  update(() => {
    const needle = String(val || '').toLowerCase();
    const rows = !needle
      ? availableCodes.value
      : availableCodes.value.filter((row) => row.code.toLowerCase().includes(needle));
    codeOptions.value = rows.map((row) => ({ label: row.code, value: row.id }));
  });
};

const fetchCcc = async () => {
  if (!selectedPatient.value?.id || !canGetCcc.value) return;
  fetchingCcc.value = true;
  try {
    const result = await patientsStore.generateCcc(selectedPatient.value.id);
    if (result?.data?.ccc) cccNumber.value = result.data.ccc;
    if (result?.patient) selectedPatient.value = result.patient;
  } finally {
    fetchingCcc.value = false;
  }
};

const fetchFollowCcc = async () => {
  if (!followUpTarget.value?.patient_id || !canGetFollowCcc.value) return;
  fetchingCcc.value = true;
  try {
    const result = await patientsStore.generateCcc(followUpTarget.value.patient_id);
    if (result?.data?.ccc) followCcc.value = result.data.ccc;
  } finally {
    fetchingCcc.value = false;
  }
};

const issueVisit = async () => {
  if (!canGive.value) return;
  busy.value = true;
  try {
    const response = await confidentialAPI.issueVisit({
      patient_id: selectedPatient.value.id,
      service_type: selectedServiceType.value,
      procedure_g_drg_code: selectedProcedure.value.g_drg_code,
      procedure_name: selectedProcedure.value.service_name,
      ccc_number: cccNumber.value.trim() || null,
      code_id: chosenCodeId.value,
    });
    issued.value = response.data;
    await loadCodeSummary();
  } catch (error) {
    notifyError(error, 'Could not give a code');
  } finally {
    busy.value = false;
  }
};

const runLookup = async () => {
  busy.value = true;
  lookupResult.value = null;
  try {
    const response = await confidentialAPI.lookup(lookupCode.value.trim());
    lookupResult.value = response.data;
  } catch (error) {
    notifyError(error, 'Code not found');
  } finally {
    busy.value = false;
  }
};

const loadRegister = async () => {
  if (!canRegister.value) return;
  busy.value = true;
  try {
    const response = await confidentialAPI.register(registerSearch.value.trim());
    registerRows.value = response.data || [];
  } catch (error) {
    notifyError(error, 'Could not load the register');
  } finally {
    busy.value = false;
  }
};

const openFollowUp = (target) => {
  followUpTarget.value = {
    code: target.code,
    patient_id: target.patient_id || null,
    insured: target.patient_insured,
    nhis_active: target.patient_nhis_active,
    insurance_id: target.patient_insurance_id,
  };
  followServiceType.value = null;
  followProcedure.value = null;
  followProcedures.value = [];
  followProcedureOptions.value = [];
  followCcc.value = '';
  followUpOpen.value = true;
};

const submitFollowUp = async () => {
  if (!followUpTarget.value?.code || !followServiceType.value || !followProcedure.value) return;
  busy.value = true;
  try {
    const response = await confidentialAPI.followUp({
      code: followUpTarget.value.code,
      service_type: followServiceType.value,
      procedure_g_drg_code: followProcedure.value.g_drg_code,
      procedure_name: followProcedure.value.service_name,
      ccc_number: followCcc.value.trim() || null,
    });
    followUpOpen.value = false;
    $q.notify({ type: 'positive', message: response.data.message || 'Follow-up opened' });
    if (!claimsMode.value && response.data?.encounter_id) openConsult(response.data.encounter_id);
  } catch (error) {
    notifyError(error, 'Could not open the follow-up');
  } finally {
    busy.value = false;
  }
};

const openVitals = () => router.push({ name: 'Vitals' });
const openConsult = (encounterId) => router.push({ name: 'Consultation', params: { encounterId } });
const openClaim = (encounterId) => router.push({ name: 'GenerateClaim', params: { encounterId } });
const openProfile = (row) => {
  router.push({
    name: 'PatientProfile',
    params: { cardNumber: row.patient_card_number },
    query: { confidential: '1' },
  });
};

onMounted(async () => {
  activeTab.value = visibleTabs.value[0]?.id || 'lookup';
  if (claimsMode.value) activeTab.value = 'register';
  await Promise.all([
    loadCodeSummary(),
    canIssue.value ? loadServiceTypes() : Promise.resolve(),
    canRegister.value ? loadRegister() : Promise.resolve(),
  ]);
});
</script>

<style scoped>
.tabs { display: flex; gap: 0.4rem; margin: 0.5rem 0 1rem; flex-wrap: wrap; }
.tab { border: 1px solid var(--hms-border, #d7d5d0); background: transparent; border-radius: 999px; padding: 0.35rem 0.8rem; cursor: pointer; }
.tab.on { background: #1f3d36; color: white; border-color: #1f3d36; }
.panel { display: flex; flex-direction: column; gap: 0.75rem; }
.hint { color: var(--hms-text-muted, #667); margin: 0; }
.form-row { display: flex; flex-wrap: wrap; gap: 0.6rem; align-items: end; }
.form-row label { display: flex; flex-direction: column; gap: 0.25rem; font-size: 0.8rem; }
.form-row input, .form-row select { border: 1px solid var(--hms-border, #d7d5d0); border-radius: 8px; padding: 0.45rem 0.6rem; min-width: 8rem; }
.grow { flex: 1; }
.grow input { width: 100%; }
.hits { display: flex; flex-direction: column; gap: 0.35rem; }
.hit { text-align: left; border: 1px solid var(--hms-border, #d7d5d0); border-radius: 8px; padding: 0.5rem 0.7rem; background: white; cursor: pointer; display: flex; justify-content: space-between; gap: 1rem; }
.hit.on { border-color: #1f3d36; }
.issued, .register-card, .visit { border: 1px solid var(--hms-border, #d7d5d0); border-radius: 12px; padding: 0.8rem 1rem; background: white; }
.code { font-size: 1.6rem; font-weight: 700; letter-spacing: 0.04em; }
.visit, .register-card header { display: flex; justify-content: space-between; gap: 0.8rem; align-items: center; flex-wrap: wrap; }
.visit span, .register-card header span { display: block; color: var(--hms-text-muted, #667); font-size: 0.85rem; }
.visit-list, .register-card { display: flex; flex-direction: column; gap: 0.55rem; }
.visit.slim { background: transparent; border-style: dashed; }
.visit-actions { display: flex; gap: 0.35rem; }
.composer { display: flex; flex-direction: column; gap: 0.75rem; }
.step { display: grid; grid-template-columns: 2rem 1fr; gap: 0.75rem; padding: 0.9rem 1rem; border: 1px solid var(--hms-border, #d7d5d0); border-radius: 14px; background: white; }
.step.locked { opacity: 0.55; }
.step.done { border-color: #1f3d36; }
.step-index { width: 2rem; height: 2rem; border-radius: 999px; display: grid; place-items: center; background: #1f3d36; color: white; font-weight: 700; }
.step-title { font-weight: 700; margin-bottom: 0.45rem; }
.step-body { min-width: 0; }
.stack { display: flex; flex-direction: column; gap: 0.65rem; align-items: flex-start; }
.client-card, .ccc-row { display: flex; justify-content: space-between; gap: 0.8rem; align-items: center; flex-wrap: wrap; }
.client-card span, .claim-map { display: block; color: var(--hms-text-muted, #667); font-size: 0.85rem; }
.claim-map { padding: 0.45rem 0.7rem; border-radius: 8px; background: #f4f7f5; }
.ccc-row { width: 100%; align-items: flex-start; }
.ccc-row .col { flex: 1; min-width: 12rem; }
.follow-card { width: min(520px, 94vw); }
</style>
