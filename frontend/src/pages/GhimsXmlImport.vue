<template>
  <q-page class="q-pa-md">
    <div class="row items-center q-mb-md">
      <q-btn flat round dense icon="arrow_back" @click="goBack" />
      <div class="text-h4 q-ml-sm text-weight-bold glass-text">
        {{ viewingBatchId ? `Import Batch: ${currentBatch?.file_name || ''}` : 'Import GHIMS XML' }}
      </div>
    </div>

    <q-card v-if="!viewingBatchId" class="q-mb-lg glass-card" flat bordered>
      <q-card-section>
        <div class="text-h6 q-mb-md">Upload GHIMS XML Export</div>
        <div class="row q-gutter-md items-center">
          <q-file v-model="uploadFile" label="Select XML file" accept=".xml,text/xml,application/xml" outlined dense clearable class="col-12 col-md-5" />
          <q-btn color="primary" label="Import XML" :loading="uploading" :disable="!uploadFile" @click="uploadXml" />
        </div>
      </q-card-section>
    </q-card>

    <q-card v-if="!viewingBatchId" class="q-mb-lg glass-card" flat bordered>
      <q-card-section>
        <div class="text-h6 q-mb-md">Recent XML imports</div>
        <q-list v-if="batches.length" bordered separator>
          <q-item v-for="b in batches" :key="b.id">
            <q-item-section avatar><q-icon name="folder" color="primary" /></q-item-section>
            <q-item-section>
              <q-item-label>{{ b.file_name }}</q-item-label>
              <q-item-label caption>{{ formatDate(b.uploaded_at) }} · {{ b.claim_count }} claim(s) · {{ b.finalized_count || 0 }} finalized</q-item-label>
            </q-item-section>
            <q-item-section side class="row items-center q-gutter-sm">
              <q-btn flat dense round icon="chevron_right" @click="openBatch(b.id)" />
              <q-btn flat dense round color="negative" icon="delete" @click="deleteBatch(b)" />
            </q-item-section>
          </q-item>
        </q-list>
        <p v-else class="text-grey-7">No XML imports yet.</p>
      </q-card-section>
    </q-card>

    <template v-if="viewingBatchId && currentBatch">
      <q-card class="q-mb-md glass-card" flat bordered>
        <q-card-section class="row items-center q-gutter-md">
          <div class="text-body2 text-grey-8">{{ currentBatch.claims?.length || 0 }} claim(s) in this import</div>
          <q-checkbox
            :model-value="allFinalizedSelected"
            label="Select all finalized"
            @update:model-value="toggleSelectAllFinalized"
          />
          <q-toggle
            v-model="filtersLocked"
            color="primary"
            label="Lock filters"
            checked-icon="lock"
            unchecked-icon="lock_open"
            class="col-12 col-md-auto"
          />
          <q-input
            v-model="searchText"
            outlined
            dense
            clearable
            label="Search client / hospital rec no / claim IDs"
            class="col-12 col-md-4"
          />
          <q-select
            v-model="attendanceFilter"
            :options="attendanceFilterOptions"
            emit-value
            map-options
            outlined
            dense
            label="Type of attendance"
            class="col-12 col-md-3"
          />
          <q-select
            v-model="specialtyFilter"
            :options="specialtyFilterOptions"
            emit-value
            map-options
            outlined
            dense
            label="Specialty attended"
            class="col-12 col-md-3"
          />
          <q-select
            v-model="statusFilter"
            :options="statusFilterOptions"
            emit-value
            map-options
            outlined
            dense
            label="Filter by status"
            class="col-12 col-md-3"
          />
          <q-space />
          <q-btn color="primary" icon="download" :label="selectedItemIds.length ? `Export ${selectedItemIds.length} selected` : 'Export selected'" :disable="selectedItemIds.length === 0" :loading="exporting" @click="exportSelected" />
        </q-card-section>
      </q-card>

      <q-card v-for="row in pagedClaims" :key="row.id" class="q-mb-sm glass-card" flat bordered>
        <q-card-section class="row items-center q-col-gutter-sm">
          <div class="col-12 col-md-3"><strong>{{ row.claim_claim_id }}</strong></div>
          <div class="col-12 col-md-3 text-body2">
            <div><strong>Client:</strong> {{ claimClientName(row) || '-' }}</div>
            <div><strong>Hosp Rec No:</strong> {{ claimHospitalRecNo(row) || '-' }}</div>
          </div>
          <div class="col-12 col-md-2 text-body2">
            <strong>Check Code:</strong> {{ claimCheckCode(row) || '-' }}
          </div>
          <div class="col-12 col-md-2">
            <q-badge :color="row.status === 'finalized' ? 'positive' : 'warning'" :label="row.status" />
          </div>
          <div class="col-12 col-md-2 row q-gutter-sm justify-end">
            <q-btn size="sm" color="primary" label="Edit imported claim" @click="editImportedClaim(row.id)" />
            <q-btn
              v-if="row.status === 'finalized'"
              size="sm"
              color="teal"
              label="Export"
              :loading="exportingSingleItemId === row.id"
              @click="exportSingleClaim(row)"
            />
            <q-btn v-if="row.status !== 'finalized'" size="sm" color="positive" label="Finalize" :loading="statusLoadingItemId === row.id" outline @click="setClaimFinalized(row)" />
            <q-btn v-if="row.status === 'finalized'" size="sm" color="warning" label="Revert to draft" :loading="statusLoadingItemId === row.id" outline @click="revertClaim(row)" />
            <q-checkbox v-if="row.status === 'finalized'" :model-value="selectedItemIds.includes(row.id)" label="Export" @update:model-value="toggleExport(row.id, $event)" />
          </div>
        </q-card-section>
      </q-card>
      <div class="row items-center q-gutter-md q-mt-md">
        <q-select
          v-model="rowsPerPage"
          :options="rowsPerPageOptions"
          emit-value
          map-options
          outlined
          dense
          label="Rows per page"
          class="col-12 col-md-2"
        />
        <q-space />
        <q-pagination
          v-model="currentPage"
          :max="maxPages"
          direction-links
          boundary-links
          color="primary"
        />
      </div>
    </template>
  </q-page>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useQuasar } from 'quasar';
import { claimsAPI } from '../services/api';

const $route = useRoute();
const $router = useRouter();
const $q = useQuasar();
const uploadFile = ref(null);
const uploading = ref(false);
const exporting = ref(false);
const exportingSingleItemId = ref(null);
const statusLoadingItemId = ref(null);
const batches = ref([]);
const viewingBatchId = ref(null);
const currentBatch = ref(null);
const selectedItemIds = ref([]);
const filtersLocked = ref(false);
const searchText = ref('');
const attendanceFilter = ref('all');
const specialtyFilter = ref('all');
const statusFilter = ref('all');
const currentPage = ref(1);
const rowsPerPage = ref(20);
const rowsPerPageOptions = [
  { label: '10', value: 10 },
  { label: '20', value: 20 },
  { label: '50', value: 50 },
  { label: '100', value: 100 },
];
const FILTER_LOCK_KEY = 'ghimsImportFiltersLocked';
const FILTERS_KEY = 'ghimsImportFiltersState';
const statusFilterOptions = [
  { label: 'All', value: 'all' },
  { label: 'Draft', value: 'draft' },
  { label: 'Finalized', value: 'finalized' },
];

const attendanceFilterOptions = computed(() => {
  const rows = currentBatch.value?.claims || [];
  const vals = Array.from(new Set(rows.map((r) => String(r.type_of_attendance || '').trim()).filter(Boolean)));
  vals.sort((a, b) => a.localeCompare(b));
  return [{ label: 'All', value: 'all' }, ...vals.map((v) => ({ label: v, value: v }))];
});

const specialtyFilterOptions = computed(() => {
  const rows = currentBatch.value?.claims || [];
  const vals = Array.from(new Set(rows.map((r) => String(r.specialty_attended || '').trim()).filter(Boolean)));
  vals.sort((a, b) => a.localeCompare(b));
  return [{ label: 'All', value: 'all' }, ...vals.map((v) => ({ label: v, value: v }))];
});

const filteredClaims = computed(() => {
  const rows = currentBatch.value?.claims || [];
  const q = String(searchText.value || '').trim().toLowerCase();
  const out = rows.filter((r) => {
    if (statusFilter.value !== 'all' && (r.status || '').toLowerCase() !== statusFilter.value) return false;
    if (attendanceFilter.value !== 'all' && String(r.type_of_attendance || '').trim() !== attendanceFilter.value) return false;
    if (specialtyFilter.value !== 'all' && String(r.specialty_attended || '').trim() !== specialtyFilter.value) return false;
    if (!q) return true;
    const hay = [
      r.client_name,
      r.hospital_rec_no,
      r.claim_claim_id,
      r.claim_check_code,
      r.type_of_attendance,
      r.specialty_attended,
    ]
      .map((x) => String(x || '').toLowerCase())
      .join(' ');
    return hay.includes(q);
  });
  return out;
});

const allFinalizedSelected = computed(() => {
  const finalizedIds = (currentBatch.value?.claims || [])
    .filter((r) => r.status === 'finalized')
    .map((r) => Number(r.id));
  if (!finalizedIds.length) return false;
  return finalizedIds.every((id) => selectedItemIds.value.includes(id));
});

const maxPages = computed(() => {
  const total = filteredClaims.value.length;
  const per = Number(rowsPerPage.value) || 20;
  return Math.max(1, Math.ceil(total / per));
});

const pagedClaims = computed(() => {
  const per = Number(rowsPerPage.value) || 20;
  const start = (Math.max(1, currentPage.value) - 1) * per;
  return filteredClaims.value.slice(start, start + per);
});

function formatDate(iso) { try { return iso ? new Date(iso).toLocaleString() : ''; } catch { return iso || ''; } }

function claimClientName(row) {
  if (row?.client_name) return row.client_name;
  const p = row?.payload || {};
  return [p.surname, p.otherNames].filter(Boolean).join(' ').trim() || null;
}

function claimCheckCode(row) {
  return row?.claim_check_code || row?.payload?.claimCheckCode || null;
}

function claimHospitalRecNo(row) {
  return row?.hospital_rec_no || row?.payload?.hospitalRecNo || null;
}

function goBack() {
  if (viewingBatchId.value) {
    viewingBatchId.value = null; currentBatch.value = null; selectedItemIds.value = [];
    $router.replace('/claims/ghims-import').catch(() => {});
  } else $router.push('/claims');
}

async function loadBatches() { batches.value = (await claimsAPI.getGhimsImportBatches()).data || []; }

async function uploadXml() {
  if (!uploadFile.value) return;
  uploading.value = true;
  try {
    const fd = new FormData(); fd.append('file', uploadFile.value);
    const res = await claimsAPI.uploadGhimsXml(fd);
    uploadFile.value = null;
    $q.notify({ type: 'positive', message: `Imported ${res.data.claim_count} claim(s)` });
    await loadBatches(); await openBatch(res.data.batch_id);
  } catch (e) { $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Import failed' }); }
  finally { uploading.value = false; }
}

function syncSelectedExports() {
  selectedItemIds.value = (currentBatch.value?.claims || []).filter((r) => r.status === 'finalized').map((r) => r.id);
}

async function openBatch(id) {
  viewingBatchId.value = id;
  currentPage.value = 1;
  $router.replace({ path: `/claims/ghims-import/batch/${id}` }).catch(() => {});
  currentBatch.value = (await claimsAPI.getGhimsImportBatch(id)).data;
  syncSelectedExports();
}

function editImportedClaim(itemId) {
  const route = $router.resolve({ path: `/claims/ghims-import/item/${itemId}` });
  window.open(route.href, '_blank');
}

async function setClaimFinalized(row) {
  statusLoadingItemId.value = row.id;
  try { await claimsAPI.finalizeGhimsImportItem(row.id); await openBatch(viewingBatchId.value); }
  catch (e) { $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Failed to finalize imported claim' }); }
  finally { statusLoadingItemId.value = null; }
}

async function revertClaim(row) {
  statusLoadingItemId.value = row.id;
  try { await claimsAPI.reopenGhimsImportItem(row.id); await openBatch(viewingBatchId.value); }
  catch (e) { $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Failed to revert imported claim' }); }
  finally { statusLoadingItemId.value = null; }
}

function toggleExport(itemId, checked) {
  const id = Number(itemId);
  if (checked && !selectedItemIds.value.includes(id)) selectedItemIds.value.push(id);
  if (!checked) selectedItemIds.value = selectedItemIds.value.filter((x) => x !== id);
}

function toggleSelectAllFinalized(checked) {
  const finalizedIds = (currentBatch.value?.claims || [])
    .filter((r) => r.status === 'finalized')
    .map((r) => Number(r.id));
  if (checked) {
    const merged = new Set([...(selectedItemIds.value || []), ...finalizedIds]);
    selectedItemIds.value = Array.from(merged);
  } else {
    selectedItemIds.value = (selectedItemIds.value || []).filter((id) => !finalizedIds.includes(Number(id)));
  }
}

async function exportSelected() {
  if (!selectedItemIds.value.length) return;
  exporting.value = true;
  try {
    const res = await claimsAPI.exportGhimsImportItems(selectedItemIds.value);
    const blob = new Blob([res.data], { type: 'application/xml' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `NHIS_CLA_batch_${currentBatch.value?.file_name?.replace(/\.[^.]+$/, '') || 'export'}.xml`);
    document.body.appendChild(link); link.click(); link.remove(); window.URL.revokeObjectURL(url);
    $q.notify({ type: 'positive', message: 'Export complete' });
  } catch (e) { $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Export failed' }); }
  finally { exporting.value = false; }
}

async function exportSingleClaim(row) {
  if (!row?.id) return;
  exportingSingleItemId.value = row.id;
  try {
    const res = await claimsAPI.exportGhimsImportItems([Number(row.id)]);
    const blob = new Blob([res.data], { type: 'application/xml' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `NHIS_CLA_claim_${row.claim_claim_id || row.id}.xml`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
    $q.notify({ type: 'positive', message: `Exported claim ${row.claim_claim_id || row.id}` });
  } catch (e) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Single claim export failed' });
  } finally {
    exportingSingleItemId.value = null;
  }
}

function deleteBatch(batch) {
  $q.dialog({ title: 'Delete Imported XML', message: `Delete ${batch.file_name}?`, cancel: true, persistent: true }).onOk(async () => {
    try { await claimsAPI.deleteGhimsImportBatch(batch.id); await loadBatches(); $q.notify({ type: 'positive', message: 'Import deleted' }); }
    catch (e) { $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Failed to delete import' }); }
  });
}

function persistFilterState() {
  try {
    localStorage.setItem(FILTER_LOCK_KEY, filtersLocked.value ? '1' : '0');
    if (!filtersLocked.value) return;
    localStorage.setItem(
      FILTERS_KEY,
      JSON.stringify({
        searchText: searchText.value,
        attendanceFilter: attendanceFilter.value,
        specialtyFilter: specialtyFilter.value,
        statusFilter: statusFilter.value,
        rowsPerPage: rowsPerPage.value,
      })
    );
  } catch (_) {}
}

function restoreFilterState() {
  try {
    filtersLocked.value = localStorage.getItem(FILTER_LOCK_KEY) === '1';
    if (!filtersLocked.value) return;
    const raw = localStorage.getItem(FILTERS_KEY);
    if (!raw) return;
    const s = JSON.parse(raw);
    searchText.value = s.searchText || '';
    attendanceFilter.value = s.attendanceFilter || 'all';
    specialtyFilter.value = s.specialtyFilter || 'all';
    statusFilter.value = s.statusFilter || 'all';
    rowsPerPage.value = Number(s.rowsPerPage) > 0 ? Number(s.rowsPerPage) : 20;
  } catch (_) {}
}

watch([searchText, attendanceFilter, specialtyFilter, statusFilter, rowsPerPage, filtersLocked], () => {
  currentPage.value = 1;
  persistFilterState();
});

watch(maxPages, (m) => {
  if (currentPage.value > m) currentPage.value = m;
});

onMounted(async () => {
  restoreFilterState();
  try { await loadBatches(); const batchId = Number($route.params.batchId); if (batchId) await openBatch(batchId); }
  catch (e) { $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Failed to load imports' }); }
});
</script>
