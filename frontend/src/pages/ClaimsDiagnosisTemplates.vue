<template>
  <q-page class="hms-page">
    <HmsPageHeader
      title="Diagnosis templates"
      subtitle="Save investigations & medicines for a principal diagnosis (e.g. Malaria → B/F + Artesunate). Apply them on claim sheets."
    >
      <template #actions>
        <HmsButton variant="ghost" size="sm" @click="$router.push('/claims')">Back</HmsButton>
        <HmsButton variant="primary" size="sm" @click="openCreate">New template</HmsButton>
      </template>
    </HmsPageHeader>

    <section class="diag-panel">
      <div class="panel-head">
        <div>
          <div class="panel-title">Filters</div>
          <div class="panel-sub">Search and show active templates</div>
        </div>
      </div>
      <div class="panel-body filter-row">
        <q-input
          v-model="search"
          filled
          dense
          debounce="300"
          clearable
          placeholder="Search templates..."
          class="filter-search"
          @update:model-value="load"
        >
          <template #append><q-icon name="search" /></template>
        </q-input>
        <q-toggle v-model="activeOnly" label="Active only" @update:model-value="load" />
      </div>
    </section>

    <section class="diag-panel">
      <div class="panel-head">
        <div>
          <div class="panel-title">Templates</div>
          <div class="panel-sub">{{ templates.length }} template(s)</div>
        </div>
      </div>
      <div class="panel-body table-wrap">
        <q-table
          class="diag-table"
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
              <HmsButton variant="ghost" size="sm" @click="openEdit(props.row)">Edit</HmsButton>
              <HmsButton variant="danger" size="sm" @click="confirmDelete(props.row)">Delete</HmsButton>
            </q-td>
          </template>
        </q-table>
      </div>
    </section>

    <q-dialog v-model="showDialog" persistent>
      <q-card class="tpl-dialog">
        <q-card-section class="dialog-head">
          <div class="dialog-title">{{ editingId ? 'Edit template' : 'New diagnosis template' }}</div>
        </q-card-section>
        <q-card-section class="q-gutter-md dialog-body">
          <q-input v-model="form.name" filled label="Template name *" hint="e.g. Malaria OPD" />
          <q-input v-model="form.description" filled type="textarea" autogrow label="Description" />
          <div class="section-label">Match when principal diagnosis is…</div>
          <div class="row q-col-gutter-sm">
            <q-input v-model="form.match_diagnosis" filled dense label="Diagnosis contains" class="col-12 col-md-6" hint="e.g. Malaria" />
            <q-input v-model="form.match_icd10" filled dense label="ICD-10 exact" class="col-12 col-md-3" />
            <q-input v-model="form.match_gdrg_prefix" filled dense label="G-DRG prefix" class="col-12 col-md-3" hint="e.g. MALA or first 4" />
            <q-input v-model="form.match_keywords" filled dense label="Keywords (comma-separated)" class="col-12" hint="e.g. malaria, plasmodium" />
          </div>

          <div class="row items-center">
            <div class="section-label">Investigations</div>
            <q-space />
            <HmsButton variant="ghost" size="sm" @click="form.investigations.push({ gdrgCode: '', serviceName: '' })">Add</HmsButton>
          </div>
          <div v-for="(inv, i) in form.investigations" :key="`inv-${i}`" class="row q-col-gutter-sm q-mb-xs items-center">
            <q-input v-model="inv.gdrgCode" filled dense label="G-DRG" class="col-12 col-md-3" />
            <q-input v-model="inv.serviceName" filled dense label="Name" class="col-12 col-md-8" />
            <q-btn flat dense color="negative" icon="delete" @click="form.investigations.splice(i, 1)" />
          </div>

          <div class="row items-center q-mt-md">
            <div class="section-label">Medicines</div>
            <q-space />
            <HmsButton
              variant="ghost"
              size="sm"
              @click="form.medicines.push({ medicineCode: '', serviceName: '', dispensedQty: '1', dose: '', frequency: '', duration: '' })"
            >
              Add
            </HmsButton>
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
        <q-card-actions align="right" class="dialog-actions">
          <HmsButton variant="ghost" size="sm" v-close-popup>Cancel</HmsButton>
          <HmsButton variant="primary" size="sm" :loading="saving" @click="save">Save</HmsButton>
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useQuasar } from 'quasar';
import { claimsAPI } from '../services/api';
import HmsPageHeader from '../components/ui/HmsPageHeader.vue';
import HmsButton from '../components/ui/HmsButton.vue';

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

<style scoped>
.diag-panel {
  margin-bottom: 1rem;
  border: 1px solid var(--hms-border);
  border-radius: var(--hms-radius-xl);
  background: var(--hms-panel-bg);
  overflow: hidden;
}
.panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
  flex-wrap: wrap;
  padding: 0.85rem 1rem;
  border-bottom: 1px solid var(--hms-border);
}
.panel-title { font-size: var(--hms-text-base); font-weight: 750; color: var(--hms-text-primary); }
.panel-sub { margin-top: 0.15rem; font-size: var(--hms-text-xs); color: var(--hms-text-muted); }
.panel-body { padding: 1rem; }
.filter-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem 1rem;
}
.filter-search { flex: 1 1 16rem; max-width: 28rem; }
.table-wrap { padding: 0; overflow-x: auto; }
.tpl-dialog {
  min-width: min(920px, 96vw);
  max-width: 920px;
  border-radius: var(--hms-radius-xl);
}
.dialog-head { border-bottom: 1px solid var(--hms-border); }
.dialog-title { font-size: var(--hms-text-lg); font-weight: 750; color: var(--hms-text-primary); }
.dialog-body { max-height: 70vh; overflow: auto; }
.dialog-actions { padding: 0.75rem 1rem 1rem; gap: 0.5rem; }
.section-label { font-size: var(--hms-text-sm); font-weight: 650; color: var(--hms-text-primary); }
</style>
