<template>
  <q-dialog v-model="open" maximized transition-show="slide-up" transition-hide="slide-down">
    <q-card>
      <q-bar class="bg-primary text-white">
        <q-icon name="history_edu" />
        <div class="q-ml-sm text-subtitle1">Recovered facility data — {{ claimId }}</div>
        <q-space />
        <q-btn v-close-popup dense flat icon="close" />
      </q-bar>

      <q-card-section v-if="loading" class="q-pa-xl text-center">
        <q-spinner color="primary" size="40px" />
        <div class="q-mt-md text-grey-7">Loading recovered visit data…</div>
      </q-card-section>

      <q-card-section v-else-if="error" class="q-pa-lg">
        <q-banner class="bg-orange-1" rounded>{{ error }}</q-banner>
      </q-card-section>

      <q-scroll-area v-else style="height: calc(100vh - 50px)" class="q-pa-md">
        <div class="row q-col-gutter-md q-mb-md">
          <div class="col-12 col-md-4">
            <div class="text-caption text-grey-7">Patient</div>
            <div class="text-body1">{{ data.patient_name || '—' }}</div>
          </div>
          <div class="col-12 col-md-2">
            <div class="text-caption text-grey-7">Member No</div>
            <div class="text-body1">{{ data.member_no || '—' }}</div>
          </div>
          <div class="col-12 col-md-2">
            <div class="text-caption text-grey-7">Visit date</div>
            <div class="text-body1">{{ data.service_date || '—' }}</div>
          </div>
          <div class="col-12 col-md-2">
            <div class="text-caption text-grey-7">Visit type</div>
            <div class="text-body1">{{ data.visit_type || parsed.visit_type || '—' }}</div>
          </div>
          <div class="col-12 col-md-2">
            <div class="text-caption text-grey-7">Source file</div>
            <div class="text-body2">{{ data.file_name || '—' }}</div>
          </div>
        </div>

        <q-expansion-item icon="medical_information" label="Clinical notes" header-class="text-weight-medium" default-opened>
          <q-card flat bordered class="q-pa-md q-mb-md">
            <div v-if="clinical.presenting_complaint" class="q-mb-sm"><strong>Presenting complaint:</strong> {{ clinical.presenting_complaint }}</div>
            <div v-if="clinical.odq" class="q-mb-sm"><strong>ODQ:</strong> {{ clinical.odq }}</div>
            <div v-if="clinical.on_examination" class="q-mb-sm"><strong>On examination:</strong> {{ clinical.on_examination }}</div>
            <div v-if="clinical.diagnosis" class="q-mb-sm"><strong>Diagnosis:</strong> {{ clinical.diagnosis }}</div>
            <div v-if="clinical.vitals" class="q-mb-sm"><strong>Vitals:</strong><pre class="clinical-pre">{{ clinical.vitals }}</pre></div>
            <div v-if="clinical.doctor_notes" class="q-mb-sm"><strong>Doctor notes:</strong> {{ clinical.doctor_notes }}</div>
            <div v-if="clinical.nurse_notes" class="q-mb-sm"><strong>Nurse notes:</strong> {{ clinical.nurse_notes }}</div>
            <div v-if="clinical.full_clinical_text"><strong>Full notes:</strong><pre class="clinical-pre">{{ clinical.full_clinical_text }}</pre></div>
          </q-card>
        </q-expansion-item>

        <div class="text-h6 q-mb-sm">Services billed (reference)</div>
        <q-table
          :rows="parsed.services || []"
          :columns="serviceColumns"
          row-key="raw"
          flat bordered dense hide-pagination :pagination="{ rowsPerPage: 0 }"
          class="q-mb-lg"
        >
          <template #body-cell-status="props">
            <q-td :props="props">
              <q-badge :color="procedureStatus(props.row).inClaim ? 'positive' : 'grey'" :label="procedureStatus(props.row).inClaim ? 'In claim' : 'Not in claim'" />
            </q-td>
          </template>
          <template #body-cell-actions="props">
            <q-td :props="props">
              <q-btn
                v-if="!procedureStatus(props.row).inClaim"
                dense flat color="primary" label="Add to claim" size="sm"
                :loading="actionKey === `proc-add-${props.rowIndex}`"
                @click="addProcedure(props.row, props.rowIndex)"
              />
              <q-btn
                v-else
                dense flat color="negative" label="Remove" size="sm"
                @click="removeProcedure(props.row)"
              />
            </q-td>
          </template>
        </q-table>

        <div class="text-h6 q-mb-sm">Investigations (reference)</div>
        <q-table
          :rows="parsed.investigations || []"
          :columns="invColumns"
          row-key="raw"
          flat bordered dense hide-pagination :pagination="{ rowsPerPage: 0 }"
          class="q-mb-lg"
        >
          <template #body-cell-status="props">
            <q-td :props="props">
              <q-badge :color="investigationStatus(props.row).inClaim ? 'positive' : 'grey'" :label="investigationStatus(props.row).inClaim ? 'In claim' : 'Not in claim'" />
            </q-td>
          </template>
          <template #body-cell-actions="props">
            <q-td :props="props">
              <q-btn
                v-if="!investigationStatus(props.row).inClaim"
                dense flat color="primary" label="Add to claim" size="sm"
                :loading="actionKey === `inv-add-${props.rowIndex}`"
                @click="addInvestigation(props.row, props.rowIndex)"
              />
              <q-btn
                v-else
                dense flat color="negative" label="Remove" size="sm"
                @click="removeInvestigation(props.row)"
              />
            </q-td>
          </template>
        </q-table>

        <div class="text-h6 q-mb-sm">Medicines dispensed (reference)</div>
        <q-table
          :rows="parsed.medicines || []"
          :columns="medColumns"
          row-key="raw"
          flat bordered dense hide-pagination :pagination="{ rowsPerPage: 0 }"
        >
          <template #body-cell-status="props">
            <q-td :props="props">
              <q-badge :color="medicineStatus(props.row).inClaim ? 'positive' : 'grey'" :label="medicineStatus(props.row).inClaim ? 'In claim' : 'Not in claim'" />
            </q-td>
          </template>
          <template #body-cell-actions="props">
            <q-td :props="props">
              <q-btn
                v-if="!medicineStatus(props.row).inClaim"
                dense flat color="primary" label="Add to claim" size="sm"
                :loading="actionKey === `med-add-${props.rowIndex}`"
                @click="addMedicine(props.row, props.rowIndex)"
              />
              <q-btn
                v-else
                dense flat color="negative" label="Remove" size="sm"
                @click="removeMedicine(props.row)"
              />
            </q-td>
          </template>
        </q-table>
      </q-scroll-area>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import { useQuasar } from 'quasar';
import { vettingGuideAPI, priceListAPI } from '../services/api';

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  claimId: { type: String, required: true },
  payload: { type: Object, required: true },
});

const emit = defineEmits(['update:modelValue', 'changed']);

const $q = useQuasar();
const open = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
});

const loading = ref(false);
const error = ref('');
const data = ref({});
const actionKey = ref('');

const parsed = computed(() => data.value?.parsed || {});
const clinical = computed(() => parsed.value?.clinical || {});

const serviceColumns = [
  { name: 'name', label: 'Service', field: 'name', align: 'left' },
  { name: 'suffix', label: 'Ref', field: 'suffix', align: 'left' },
  { name: 'status', label: 'Status', field: 'status', align: 'center' },
  { name: 'actions', label: 'Actions', field: 'actions', align: 'center' },
];
const invColumns = [
  { name: 'name', label: 'Investigation', field: 'name', align: 'left' },
  { name: 'status', label: 'Status', field: 'status', align: 'center' },
  { name: 'actions', label: 'Actions', field: 'actions', align: 'center' },
];
const medColumns = [
  { name: 'medicine_code', label: 'Code', field: 'medicine_code', align: 'left' },
  { name: 'quantity', label: 'Qty', field: 'quantity', align: 'left' },
  { name: 'dose', label: 'Dose', field: 'dose', align: 'left' },
  { name: 'frequency', label: 'Freq', field: 'frequency', align: 'left' },
  { name: 'duration', label: 'Duration', field: 'duration', align: 'left' },
  { name: 'status', label: 'Status', field: 'status', align: 'center' },
  { name: 'actions', label: 'Actions', field: 'actions', align: 'center' },
];

function defaultServiceDate() {
  return (
    data.value?.service_date
    || parsed.value?.service_date
    || (Array.isArray(props.payload.dateOfService) && props.payload.dateOfService[0])
    || ''
  );
}

function normalizeCode(v) {
  return String(v || '').trim().toUpperCase();
}

function procedureStatus(row) {
  const name = String(row.name || '').trim().toLowerCase();
  const idx = (props.payload.procedures || []).findIndex((p) => {
    const desc = String(p.description || p._serviceName || '').trim().toLowerCase();
    const code = normalizeCode(p.gdrgCode);
    return (name && desc.includes(name)) || (row.suffix && code === normalizeCode(row.suffix));
  });
  return { inClaim: idx >= 0, index: idx };
}

function investigationStatus(row) {
  const name = String(row.name || '').trim().toLowerCase();
  const idx = (props.payload.investigations || []).findIndex((inv) => {
    const code = normalizeCode(inv.gdrgCode);
    return name && (code === normalizeCode(row.name) || String(inv._serviceName || '').toLowerCase().includes(name));
  });
  return { inClaim: idx >= 0, index: idx };
}

function medicineStatus(row) {
  const code = normalizeCode(row.medicine_code);
  const idx = (props.payload.medicines || []).findIndex((m) => normalizeCode(m.medicineCode) === code);
  return { inClaim: idx >= 0 && !!code, index: idx };
}

async function searchProcedureByName(name) {
  const res = await priceListAPI.search(name, undefined, 'procedure');
  const items = res.data || [];
  const lower = name.toLowerCase();
  return items.find((x) => String(x.service_name || x.item_name || '').toLowerCase().includes(lower)) || items[0];
}

async function searchInvestigationByName(name) {
  let res = await priceListAPI.search(name, undefined, 'procedure');
  let items = res.data || [];
  if (!items.length) {
    res = await priceListAPI.search(name, undefined, 'unmapped_drg');
    items = res.data || [];
  }
  const lower = name.toLowerCase();
  return items.find((x) => String(x.service_name || x.item_name || '').toLowerCase().includes(lower)) || items[0];
}

async function addProcedure(row, rowIndex) {
  actionKey.value = `proc-add-${rowIndex}`;
  try {
    const match = await searchProcedureByName(row.name || row.raw);
    const code = match?.g_drg_code || match?.item_code || row.suffix || '';
    props.payload.procedures.push({
      serviceDate: defaultServiceDate(),
      gdrgCode: code,
      description: row.name || row.raw,
      icd10: '',
      diagnosis: '',
      _serviceName: row.name || '',
      _selectedOption: match ? { ...match, optionLabel: `${match.service_name || match.item_name || row.name} (${code})` } : null,
    });
    emit('changed');
    $q.notify({ type: 'positive', message: 'Procedure added from recovered data' });
  } catch (e) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Could not add procedure' });
  } finally {
    actionKey.value = '';
  }
}

function removeProcedure(row) {
  const { index } = procedureStatus(row);
  if (index >= 0) {
    props.payload.procedures.splice(index, 1);
    emit('changed');
  }
}

async function addInvestigation(row, rowIndex) {
  actionKey.value = `inv-add-${rowIndex}`;
  try {
    const match = await searchInvestigationByName(row.name || row.raw);
    const code = match?.g_drg_code || match?.item_code || '';
    props.payload.investigations.push({
      serviceDate: defaultServiceDate(),
      gdrgCode: code,
      _serviceName: row.name || '',
      _selectedOption: match ? { ...match, optionLabel: `${match.service_name || match.item_name || row.name} (${code})` } : null,
    });
    emit('changed');
    $q.notify({ type: 'positive', message: 'Investigation added from recovered data' });
  } catch (e) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Could not add investigation' });
  } finally {
    actionKey.value = '';
  }
}

function removeInvestigation(row) {
  const { index } = investigationStatus(row);
  if (index >= 0) {
    props.payload.investigations.splice(index, 1);
    emit('changed');
  }
}

async function addMedicine(row, rowIndex) {
  actionKey.value = `med-add-${rowIndex}`;
  try {
    const code = normalizeCode(row.medicine_code);
    let match = null;
    if (code) {
      const res = await priceListAPI.search(code, undefined, 'product');
      match = (res.data || []).find((p) => normalizeCode(p.medication_code || p.item_code) === code) || (res.data || [])[0];
    }
    props.payload.medicines.push({
      medicineCode: code,
      dispensedQty: row.quantity || '1',
      serviceDate: defaultServiceDate(),
      prescription: {
        dose: row.dose || '',
        frequency: row.frequency || '',
        duration: row.duration || '',
        unparsed: row.raw || '',
      },
      _serviceName: match?.product_name || match?.item_name || '',
      _selectedOption: match ? { ...match, optionLabel: `${match.product_name || match.item_name || code} (${code})` } : null,
      insurance_covered: match?.insurance_covered || 'yes',
    });
    emit('changed');
    $q.notify({ type: 'positive', message: 'Medicine added from recovered data' });
  } catch (e) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Could not add medicine' });
  } finally {
    actionKey.value = '';
  }
}

function removeMedicine(row) {
  const { index } = medicineStatus(row);
  if (index >= 0) {
    props.payload.medicines.splice(index, 1);
    emit('changed');
  }
}

async function load() {
  if (!props.claimId) return;
  loading.value = true;
  error.value = '';
  try {
    const res = await vettingGuideAPI.getForClaim(props.claimId);
    data.value = res.data || {};
  } catch (e) {
    data.value = {};
    error.value = e.response?.data?.detail || 'No recovered data found for this claim.';
  } finally {
    loading.value = false;
  }
}

watch(open, (v) => {
  if (v) load();
});
</script>

<style scoped>
.clinical-pre {
  white-space: pre-wrap;
  font-family: inherit;
  font-size: 0.9rem;
  margin: 0.25rem 0 0;
  background: rgba(0, 0, 0, 0.03);
  padding: 0.5rem;
  border-radius: 4px;
}
</style>
