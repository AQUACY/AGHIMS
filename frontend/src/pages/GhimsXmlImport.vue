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
          <div class="text-body2 text-primary">
            Showing {{ filteredClaims.length }} filtered claim(s)
          </div>
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
            v-model="serviceTypeFilter"
            :options="serviceTypeFilterOptions"
            emit-value
            map-options
            outlined
            dense
            label="Type of service"
            class="col-12 col-md-3"
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
          <q-select
            v-model="ageGroupFilter"
            :options="ageGroupFilterOptions"
            emit-value
            map-options
            outlined
            dense
            label="Age group"
            class="col-12 col-md-3"
          />
          <q-toggle
            v-model="missingSectionsOnly"
            color="deep-orange"
            label="Show only claims with missing sections"
            class="col-12 col-md-4"
          />
          <q-space />
          <q-btn
            color="secondary"
            icon="refresh"
            label="Refresh"
            :loading="refreshing"
            @click="refreshCurrentBatch"
          />
          <q-btn color="primary" icon="download" :label="selectedItemIds.length ? `Export ${selectedItemIds.length} selected` : 'Export selected'" :disable="selectedItemIds.length === 0" :loading="exporting" @click="exportSelected" />
        </q-card-section>
      </q-card>

      <q-card class="q-mb-sm glass-card" flat bordered>
        <q-card-section class="q-pa-none">
          <q-markup-table flat dense bordered separator="horizontal" wrap-cells>
            <thead>
              <tr>
                <th class="text-left">#</th>
                <th class="text-left">Claim ID</th>
                <th class="text-left">Client</th>
                <th class="text-left">Hosp Rec No</th>
                <th class="text-left">Age</th>
                <th class="text-left">Check Code</th>
                <th class="text-left">Status / Missing</th>
                <th class="text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, pageIndex) in pagedClaims" :key="row.id">
                <td>{{ ((currentPage - 1) * rowsPerPage) + pageIndex + 1 }}</td>
                <td>{{ row.claim_claim_id }}</td>
                <td>{{ claimClientName(row) || '-' }}</td>
                <td>{{ claimHospitalRecNo(row) || '-' }}</td>
                <td>{{ claimClientAge(row) }}</td>
                <td>{{ claimCheckCode(row) || '-' }}</td>
                <td>
                  <q-badge :color="claimStatusColor(row.status)" :label="row.status" />
                  <q-badge
                    v-if="row.has_missing_sections"
                    class="q-ml-sm q-mt-xs"
                    color="deep-orange"
                    :label="`Missing: ${(row.missing_sections || []).map(prettySectionName).join(', ')}`"
                  />
                  <q-badge
                    v-if="row.no_clinical_sections"
                    class="q-ml-sm q-mt-xs"
                    color="red-8"
                    label="No diagnosis/investigation/medicine/procedure"
                  />
                </td>
                <td class="text-right">
                  <div class="row q-gutter-xs justify-end">
                    <q-btn
                      size="sm"
                      color="primary"
                      label="Edit"
                      :disable="row.status === 'finalized' || row.status === 'flagged'"
                      @click="editImportedClaim(row)"
                    />
                    <q-btn
                      size="sm"
                      color="purple"
                      label="View"
                      @click="viewImportedClaim(row)"
                    />
                    <q-btn
                      v-if="row.status === 'finalized'"
                      size="sm"
                      color="teal"
                      label="Export"
                      :loading="exportingSingleItemId === row.id"
                      @click="exportSingleClaim(row)"
                    />
                    <q-btn v-if="row.status !== 'finalized'" size="sm" color="positive" label="Finalize" :disable="row.status === 'flagged'" :loading="statusLoadingItemId === row.id" outline @click="setClaimFinalized(row)" />
                    <q-btn
                      v-if="row.status !== 'finalized'"
                      size="sm"
                      color="negative"
                      :label="row.status === 'flagged' ? 'Flagged' : 'Flag claim'"
                      :disable="row.status === 'flagged'"
                      :loading="statusLoadingItemId === row.id"
                      outline
                      @click="flagClaim(row)"
                    />
                    <q-btn v-if="row.status === 'finalized'" size="sm" color="warning" label="Revert" :loading="statusLoadingItemId === row.id" outline @click="revertClaim(row)" />
                    <q-btn v-if="row.status === 'flagged'" size="sm" color="warning" label="Mark draft" :loading="statusLoadingItemId === row.id" outline @click="revertClaim(row)" />
                    <q-checkbox v-if="row.status === 'finalized'" :model-value="selectedItemIds.includes(row.id)" label="Export" @update:model-value="toggleExport(row.id, $event)" />
                  </div>
                </td>
              </tr>
              <tr v-if="pagedClaims.length === 0">
                <td colspan="8" class="text-center text-grey-7 q-pa-md">No claims match the current filters.</td>
              </tr>
            </tbody>
          </q-markup-table>
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
const refreshing = ref(false);
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
const serviceTypeFilter = ref('all');
const statusFilter = ref('all');
const ageGroupFilter = ref('all');
const missingSectionsOnly = ref(false);
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
  { label: 'Flagged', value: 'flagged' },
  { label: 'Finalized', value: 'finalized' },
];
const ageGroupFilterOptions = [
  { label: 'All', value: 'all' },
  { label: 'Kids (0-11)', value: 'kids' },
  { label: 'Adults (12+)', value: 'adults' },
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

function getServiceType(row) {
  return String(
    row?.type_of_service
      || row?.payload?.typeOfService
      || row?.payload?.type_of_service
      || ''
  )
    .trim()
    .toUpperCase();
}

const serviceTypeFilterOptions = computed(() => {
  const rows = currentBatch.value?.claims || [];
  const vals = Array.from(
    new Set(
      rows
        .map((r) => getServiceType(r))
        .filter((v) => v === 'IPD' || v === 'OPD')
    )
  );
  vals.sort((a, b) => a.localeCompare(b));
  return [{ label: 'All', value: 'all' }, ...vals.map((v) => ({ label: v, value: v }))];
});

const filteredClaims = computed(() => {
  const rows = currentBatch.value?.claims || [];
  const q = String(searchText.value || '').trim().toLowerCase();
  const out = rows.filter((r) => {
    if (missingSectionsOnly.value && !r.no_clinical_sections) return false;
    if (statusFilter.value !== 'all' && (r.status || '').toLowerCase() !== statusFilter.value) return false;
    if (serviceTypeFilter.value !== 'all' && getServiceType(r) !== serviceTypeFilter.value) return false;
    const age = claimClientAgeYears(r);
    if (ageGroupFilter.value === 'kids' && !(age !== null && age <= 11)) return false;
    if (ageGroupFilter.value === 'adults' && !(age !== null && age >= 12)) return false;
    if (attendanceFilter.value !== 'all' && String(r.type_of_attendance || '').trim() !== attendanceFilter.value) return false;
    if (specialtyFilter.value !== 'all' && String(r.specialty_attended || '').trim() !== specialtyFilter.value) return false;
    if (!q) return true;
    const hay = [
      r.client_name,
      r.hospital_rec_no,
      r.claim_claim_id,
      r.claim_check_code,
      getServiceType(r),
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

function claimClientAge(row) {
  const age = claimClientAgeYears(row);
  return age !== null ? String(age) : '-';
}

function claimClientAgeYears(row) {
  const dobRaw = row?.date_of_birth || row?.payload?.dateOfBirth || row?.payload?.date_of_birth || '';
  if (!dobRaw) return null;
  const dob = new Date(dobRaw);
  if (Number.isNaN(dob.getTime())) return null;

  const now = new Date();
  let age = now.getFullYear() - dob.getFullYear();
  const birthdayNotReachedYet = (
    now.getMonth() < dob.getMonth()
    || (now.getMonth() === dob.getMonth() && now.getDate() < dob.getDate())
  );
  if (birthdayNotReachedYet) age -= 1;
  return age >= 0 ? age : null;
}

function claimStatusColor(status) {
  if (status === 'finalized') return 'positive';
  if (status === 'flagged') return 'negative';
  return 'warning';
}

function prettySectionName(key) {
  return String(key || '').replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
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

async function refreshCurrentBatch() {
  if (!viewingBatchId.value) return;
  refreshing.value = true;
  try {
    await loadBatches();
    await openBatch(viewingBatchId.value);
    $q.notify({ type: 'positive', message: 'Imported claims refreshed' });
  } catch (e) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Failed to refresh imported claims' });
  } finally {
    refreshing.value = false;
  }
}

function editImportedClaim(row) {
  if (!row?.id) return;
  if (row.status === 'finalized') {
    $q.notify({ type: 'warning', message: 'Finalized imported claims cannot be edited' });
    return;
  }
  const route = $router.resolve({ path: `/claims/ghims-import/item/${row.id}` });
  window.open(route.href, '_blank');
}
function viewImportedClaim(row) {
  const route = $router.resolve({ path: `/claims/ghims-import/item/${row.id}` });
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

async function flagClaim(row) {
  statusLoadingItemId.value = row.id;
  try { await claimsAPI.flagGhimsImportItem(row.id); await openBatch(viewingBatchId.value); }
  catch (e) { $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Failed to flag imported claim' }); }
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
        serviceTypeFilter: serviceTypeFilter.value,
        ageGroupFilter: ageGroupFilter.value,
        attendanceFilter: attendanceFilter.value,
        specialtyFilter: specialtyFilter.value,
        statusFilter: statusFilter.value,
        missingSectionsOnly: missingSectionsOnly.value,
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
    serviceTypeFilter.value = s.serviceTypeFilter || 'all';
    ageGroupFilter.value = s.ageGroupFilter || 'all';
    attendanceFilter.value = s.attendanceFilter || 'all';
    specialtyFilter.value = s.specialtyFilter || 'all';
    statusFilter.value = s.statusFilter || 'all';
    missingSectionsOnly.value = Boolean(s.missingSectionsOnly);
    rowsPerPage.value = Number(s.rowsPerPage) > 0 ? Number(s.rowsPerPage) : 20;
  } catch (_) {}
}

watch([searchText, serviceTypeFilter, ageGroupFilter, attendanceFilter, specialtyFilter, statusFilter, missingSectionsOnly, rowsPerPage, filtersLocked], () => {
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
