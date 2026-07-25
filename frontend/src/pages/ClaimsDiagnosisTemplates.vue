<template>
  <q-page class="q-pa-md">
    <div class="row items-center q-mb-md">
      <div>
        <div class="text-h4 text-weight-bold glass-text">Diagnosis Templates</div>
        <div class="text-caption text-grey-7">
          Save investigations &amp; medicines for a principal diagnosis (e.g. Malaria → B/F + Artesunate). Apply them on claim sheets.
        </div>
      </div>
      <q-space />
      <q-btn flat color="secondary" icon="arrow_back" label="Claims home" @click="$router.push('/claims')" class="q-mr-sm" />
      <q-btn color="primary" icon="add" label="New template" @click="openCreate" />
    </div>

    <q-card flat bordered class="q-mb-md">
      <q-card-section class="row q-col-gutter-md items-center">
        <div class="col-12 col-md-6">
          <q-input v-model="search" filled dense debounce="300" clearable placeholder="Search templates..." @update:model-value="load">
            <template #append><q-icon name="search" /></template>
          </q-input>
        </div>
        <div class="col-12 col-md-3">
          <q-toggle v-model="activeOnly" label="Active only" @update:model-value="load" />
        </div>
      </q-card-section>
    </q-card>

    <q-card flat bordered>
      <q-table
        :rows="templates"
        :columns="columns"
        row-key="id"
        flat
        :loading="loading"
        :rows-per-page-options="[10, 25, 50]"
      >
        <template #body-cell-match="props">
          <q-td :props="props">
            <div class="text-caption">
              <div v-if="props.row.match_diagnosis"><strong>Dx:</strong> {{ props.row.match_diagnosis }}</div>
              <div v-if="props.row.match_icd10"><strong>ICD:</strong> {{ props.row.match_icd10 }}</div>
              <div v-if="props.row.match_gdrg_prefix"><strong>GDRG:</strong> {{ props.row.match_gdrg_prefix }}*</div>
              <div v-if="props.row.match_keywords"><strong>Keywords:</strong> {{ props.row.match_keywords }}</div>
            </div>
          </q-td>
        </template>
        <template #body-cell-counts="props">
          <q-td :props="props">
            {{ (props.row.investigations || []).length }} inv · {{ (props.row.medicines || []).length }} meds
          </q-td>
        </template>
        <template #body-cell-actions="props">
          <q-td :props="props">
            <q-btn flat dense size="sm" color="primary" icon="edit" label="Edit" @click="openEdit(props.row)" />
            <q-btn flat dense size="sm" color="negative" icon="delete" label="Delete" @click="confirmDelete(props.row)" />
          </q-td>
        </template>
      </q-table>
    </q-card>

    <q-dialog v-model="showDialog" persistent>
      <q-card style="min-width: 720px; max-width: 920px">
        <q-card-section>
          <div class="text-h6">{{ editingId ? 'Edit template' : 'New diagnosis template' }}</div>
        </q-card-section>
        <q-card-section class="q-gutter-md" style="max-height: 70vh; overflow: auto">
          <q-input v-model="form.name" filled label="Template name *" hint="e.g. Malaria OPD" />
          <q-input v-model="form.description" filled type="textarea" autogrow label="Description" />
          <div class="text-subtitle2">Match when principal diagnosis is…</div>
          <div class="row q-col-gutter-sm">
            <q-input v-model="form.match_diagnosis" filled dense label="Diagnosis contains" class="col-12 col-md-6" hint="e.g. Malaria" />
            <q-input v-model="form.match_icd10" filled dense label="ICD-10 exact" class="col-12 col-md-3" />
            <q-input v-model="form.match_gdrg_prefix" filled dense label="G-DRG prefix" class="col-12 col-md-3" hint="e.g. MALA or first 4" />
            <q-input v-model="form.match_keywords" filled dense label="Keywords (comma-separated)" class="col-12" hint="e.g. malaria, plasmodium" />
          </div>

          <div class="row items-center">
            <div class="text-subtitle2">Investigations</div>
            <q-space />
            <q-btn flat dense color="primary" icon="add" label="Add" @click="form.investigations.push({ gdrgCode: '', serviceName: '' })" />
          </div>
          <div v-for="(inv, i) in form.investigations" :key="`inv-${i}`" class="row q-col-gutter-sm q-mb-xs items-center">
            <q-input v-model="inv.gdrgCode" filled dense label="G-DRG" class="col-12 col-md-3" />
            <q-input v-model="inv.serviceName" filled dense label="Name" class="col-12 col-md-8" />
            <q-btn flat dense color="negative" icon="delete" @click="form.investigations.splice(i, 1)" />
          </div>

          <div class="row items-center q-mt-md">
            <div class="text-subtitle2">Medicines</div>
            <q-space />
            <q-btn flat dense color="primary" icon="add" label="Add" @click="form.medicines.push({ medicineCode: '', serviceName: '', dispensedQty: '1', dose: '', frequency: '', duration: '' })" />
          </div>
          <div v-for="(m, i) in form.medicines" :key="`med-${i}`" class="row q-col-gutter-sm q-mb-sm items-center">
            <q-input v-model="m.medicineCode" filled dense label="Code" class="col-12 col-md-2" />
            <q-input v-model="m.serviceName" filled dense label="Name" class="col-12 col-md-3" />
            <q-input v-model="m.dispensedQty" filled dense label="Qty" class="col-6 col-md-1" />
            <q-input v-model="m.dose" filled dense label="Dose" class="col-6 col-md-2" />
            <q-input v-model="m.frequency" filled dense label="Freq" class="col-6 col-md-2" />
            <q-input v-model="m.duration" filled dense label="Duration" class="col-6 col-md-1" />
            <q-btn flat dense color="negative" icon="delete" @click="form.medicines.splice(i, 1)" />
          </div>

          <q-toggle v-model="form.is_shared" label="Share with other claims users" />
          <q-toggle v-model="form.is_active" label="Active" />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Cancel" v-close-popup />
          <q-btn color="primary" label="Save" :loading="saving" @click="save" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useQuasar } from 'quasar';
import { claimsAPI } from '../services/api';

const $q = useQuasar();
const loading = ref(false);
const saving = ref(false);
const templates = ref([]);
const search = ref('');
const activeOnly = ref(true);
const showDialog = ref(false);
const editingId = ref(null);

const emptyForm = () => ({
  name: '',
  description: '',
  match_icd10: '',
  match_diagnosis: '',
  match_gdrg_prefix: '',
  match_keywords: '',
  investigations: [],
  medicines: [],
  is_shared: true,
  is_active: true,
});
const form = ref(emptyForm());

const columns = [
  { name: 'name', label: 'Name', field: 'name', align: 'left', sortable: true },
  { name: 'match', label: 'Matches', field: 'match_diagnosis', align: 'left' },
  { name: 'counts', label: 'Items', field: 'id', align: 'left' },
  { name: 'created_by_name', label: 'Created by', field: 'created_by_name', align: 'left' },
  { name: 'actions', label: 'Actions', field: 'id', align: 'right' },
];

function apiErrorMessage(e, fallback) {
  const detail = e?.response?.data?.detail;
  if (typeof detail === 'string' && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    const parts = detail.map((d) => d?.msg || d?.message || '').filter(Boolean);
    if (parts.length) return parts.join('; ');
  }
  return fallback;
}

async function load() {
  loading.value = true;
  try {
    const res = await claimsAPI.listDiagnosisTemplates({
      search: search.value || undefined,
      active_only: activeOnly.value,
      include_shared: true,
    });
    templates.value = res.data || [];
  } catch (e) {
    $q.notify({ type: 'negative', message: apiErrorMessage(e, 'Failed to load templates') });
  } finally {
    loading.value = false;
  }
}

function openCreate() {
  editingId.value = null;
  form.value = emptyForm();
  form.value.investigations.push({ gdrgCode: '', serviceName: '' });
  form.value.medicines.push({ medicineCode: '', serviceName: '', dispensedQty: '1', dose: '', frequency: '', duration: '' });
  showDialog.value = true;
}

function openEdit(row) {
  editingId.value = row.id;
  form.value = {
    name: row.name || '',
    description: row.description || '',
    match_icd10: row.match_icd10 || '',
    match_diagnosis: row.match_diagnosis || '',
    match_gdrg_prefix: row.match_gdrg_prefix || '',
    match_keywords: row.match_keywords || '',
    investigations: (row.investigations || []).map((x) => ({ ...x })),
    medicines: (row.medicines || []).map((x) => ({ ...x })),
    is_shared: row.is_shared !== false,
    is_active: row.is_active !== false,
  };
  showDialog.value = true;
}

async function save() {
  if (!String(form.value.name || '').trim()) {
    $q.notify({ type: 'warning', message: 'Template name is required' });
    return;
  }
  const inv = (form.value.investigations || []).filter((x) => String(x.gdrgCode || '').trim() || String(x.serviceName || '').trim());
  const med = (form.value.medicines || []).filter((x) => String(x.medicineCode || '').trim() || String(x.serviceName || '').trim());
  if (!inv.length && !med.length) {
    $q.notify({ type: 'warning', message: 'Add at least one investigation or medicine' });
    return;
  }
  saving.value = true;
  try {
    const payload = {
      ...form.value,
      investigations: inv,
      medicines: med,
    };
    if (editingId.value) {
      await claimsAPI.updateDiagnosisTemplate(editingId.value, payload);
    } else {
      await claimsAPI.createDiagnosisTemplate(payload);
    }
    $q.notify({ type: 'positive', message: 'Template saved' });
    showDialog.value = false;
    await load();
  } catch (e) {
    $q.notify({ type: 'negative', message: apiErrorMessage(e, 'Failed to save template') });
  } finally {
    saving.value = false;
  }
}

function confirmDelete(row) {
  $q.dialog({
    title: 'Delete template',
    message: `Delete “${row.name}”?`,
    cancel: true,
    persistent: true,
  }).onOk(async () => {
    try {
      await claimsAPI.deleteDiagnosisTemplate(row.id);
      $q.notify({ type: 'positive', message: 'Template deleted' });
      await load();
    } catch (e) {
      $q.notify({ type: 'negative', message: apiErrorMessage(e, 'Delete failed') });
    }
  });
}

onMounted(load);
</script>
