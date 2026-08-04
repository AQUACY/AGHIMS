<template>
  <q-page class="hms-page">
    <HmsPageHeader
      :title="viewingBatchId ? `Batch: ${currentBatch?.file_name || ''}` : 'Correct errors'"
      :subtitle="viewingBatchId ? 'Review ClaimIT errors and warnings for this report batch.' : 'Upload ClaimIT import reports and open batches to fix errors.'"
    >
      <template #actions>
        <HmsButton variant="ghost" size="sm" @click="goBack">Back</HmsButton>
      </template>
    </HmsPageHeader>

    <!-- Upload (when not viewing a batch) -->
    <section v-if="!viewingBatchId" class="diag-panel">
      <div class="panel-head">
        <div>
          <div class="panel-title">Upload ClaimIT Import Report</div>
          <div class="panel-sub">
            Use Import GHIMS XML when the XML came from that screen; use main HMS claims only when the XML was exported from the normal claim registry.
          </div>
        </div>
      </div>
      <div class="panel-body">
        <q-checkbox
          v-model="uploadMainHmsOnly"
          dense
          color="primary"
          class="q-mb-sm"
          label="Main HMS claims only — do not link this report to Import GHIMS XML"
        />
        <q-select
          v-model="uploadGhimsBatchId"
          :options="ghimsBatchSelectOptions"
          emit-value
          map-options
          clearable
          outlined
          dense
          label="GHIMS import this report belongs to (optional)"
          :hint="uploadMainHmsOnly ? 'Disabled: this upload is treated as main HMS claims.' : 'Leave empty to auto-detect from claim IDs in the report.'"
          class="q-mb-md col-12 col-md-8"
          :loading="ghimsBatchesLoading"
          :disable="uploadMainHmsOnly"
        />
        <div class="upload-row">
          <q-file
            v-model="uploadFile"
            label="Select report (HTML)"
            accept=".html,.htm"
            outlined
            dense
            clearable
            class="upload-file"
            @update:model-value="uploadFile = $event"
          />
          <HmsButton
            variant="primary"
            size="sm"
            :loading="uploading"
            :disabled="!uploadFile"
            @click="uploadReport"
          >
            Upload
          </HmsButton>
        </div>
      </div>
    </section>

    <!-- Batch list (when not viewing a batch) -->
    <section v-if="!viewingBatchId" class="diag-panel">
      <div class="panel-head">
        <div>
          <div class="panel-title">Recent report batches</div>
          <div class="panel-sub">Open a batch to review errors and warnings</div>
        </div>
      </div>
      <div class="panel-body">
        <div v-if="batches.length" class="batch-list">
          <div v-for="b in batches" :key="b.id" class="batch-row">
            <div class="batch-copy">
              <div class="batch-name">{{ b.file_name }}</div>
              <div class="batch-meta">
                {{ formatDate(b.uploaded_at) }} · {{ b.error_count }} claim(s) with errors/warnings in this HTML
                <template v-if="claimItVolumeCaption(b.summary)">
                  · {{ claimItVolumeCaption(b.summary) }}
                </template>
                <template v-if="b.ghims_import_batch_file_name">
                  · GHIMS: {{ b.ghims_import_batch_file_name }}<template v-if="b.ghims_import_claim_count != null"> ({{ b.ghims_import_claim_count }} claims in HMS)</template>
                </template>
              </div>
            </div>
            <div class="batch-actions">
              <HmsButton variant="secondary" size="sm" @click="openBatch(b.id)">
                Open
              </HmsButton>
            </div>
          </div>
        </div>
        <p v-else class="empty-hint">No report batches yet. Upload a ClaimIT import report above.</p>
      </div>
    </section>

    <!-- Batch detail: claims with errors -->
    <template v-if="viewingBatchId && currentBatch">
      <q-banner
        v-if="batchErrors.length === 0 && claimItVolumeCaption(currentBatch.summary)"
        rounded
        class="bg-cyan-1 text-dark q-mb-md"
      >
        <template #avatar>
          <q-icon name="check_circle" color="cyan-9" />
        </template>
        ClaimIT did not list any ERROR or WARNING rows in this file, so there is nothing to fix here. Overview for <strong>this</strong> ClaimIT import:
        {{ claimItVolumeCaption(currentBatch.summary) }}.
        That count is only what ClaimIT processed in that import, not necessarily every row in a large GHIMS XML batch.
      </q-banner>
      <q-banner v-if="claimitGhimsMismatchWarn" rounded class="bg-orange-2 text-dark q-mb-md">
        <template #avatar>
          <q-icon name="warning" color="deep-orange" />
        </template>
        {{ claimitGhimsMismatchWarn }}
      </q-banner>
      <q-banner v-if="currentBatch?.ghims_import_batch_id" rounded class="bg-teal-1 text-dark q-mb-md">
        <template #avatar>
          <q-icon name="link" color="teal" />
        </template>
        This report is linked to GHIMS import <strong>{{ currentBatch.ghims_import_batch_file_name || ('batch #' + currentBatch.ghims_import_batch_id) }}</strong>.
        Use <strong>Fix in GHIMS import</strong> on each row to edit that claim in Import GHIMS XML.
        <q-btn
          flat
          dense
          no-caps
          color="primary"
          class="q-ml-sm"
          label="Open batch"
          :to="{ path: `/claims/ghims-import/batch/${currentBatch.ghims_import_batch_id}` }"
        />
      </q-banner>
      <q-banner v-else-if="currentBatch?.summary?.ghims_resolution === 'skipped_main_hms'" rounded class="bg-indigo-1 text-dark q-mb-md">
        <template #avatar>
          <q-icon name="badge" color="indigo" />
        </template>
        This upload was marked as <strong>main HMS claims only</strong>. Rows use <strong>Edit claim</strong> for claims in this system; nothing is linked to Import GHIMS XML.
      </q-banner>
      <q-banner v-else rounded class="bg-blue-1 text-dark q-mb-md">
        <template #avatar>
          <q-icon name="info" color="primary" />
        </template>
        No GHIMS import batch was matched for this report. Use <strong>Edit claim</strong> if the claim exists in this system, or open
        <router-link to="/claims/ghims-import" class="text-primary">Import GHIMS XML</router-link> manually.
      </q-banner>

      <section class="diag-panel batch-toolbar">
        <div class="panel-body">
          <div class="row items-center justify-between q-mb-md">
            <div>
              <span class="text-caption text-grey-7">Errors / warnings in this batch: </span>
              <strong>{{ filteredErrors.length }}</strong>
              <span v-if="outcomeFilter !== 'all'" class="text-caption text-grey-7"> (filtered from {{ batchErrors.length }})</span>
            </div>
            <q-btn
              color="primary"
              :label="exportButtonLabel"
              icon="download"
              :disable="exportableClaimIds.length === 0"
              :loading="exportingBatch"
              @click="exportBatchClaims"
            />
          </div>
          <div class="row items-center q-gutter-md q-mb-sm">
            <q-checkbox
              v-model="selectionsLocked"
              label="Lock selections (keep on refresh)"
              dense
              @update:model-value="onLockToggled"
            />
          </div>
          <div class="row items-center q-gutter-md">
            <span class="text-caption text-grey-7">Show:</span>
            <q-btn-toggle
              v-model="outcomeFilter"
              no-caps
              dense
              toggle-color="primary"
              :options="[
                { label: 'All', value: 'all' },
                { label: 'Errors only', value: 'ERROR' },
                { label: 'Warnings only', value: 'WARNING' },
              ]"
              @update:model-value="paginationPage = 1"
            />
            <q-checkbox
              v-model="hideCompleted"
              label="Hide completed"
              dense
              class="q-ml-md"
              @update:model-value="paginationPage = 1"
            />
            <q-space />
            <div class="row items-center q-gutter-sm">
              <span class="text-caption text-grey-7">Rows per page:</span>
              <q-select
                v-model="rowsPerPage"
                :options="[10, 25, 50, 100]"
                dense
                outlined
                emit-value
                map-options
                options-dense
                class="col-auto"
                style="min-width: 70px"
                @update:model-value="paginationPage = 1"
              />
              <q-pagination
                v-model="paginationPage"
                :max="paginationMaxPages"
                :max-pages="7"
                direction-links
                boundary-links
                color="primary"
                dense
                input
              />
            </div>
          </div>
        </div>
      </section>

      <section v-for="err in paginatedErrors" :key="err.id" class="diag-panel">
        <div class="panel-body">
          <!-- Error messages above the claim block -->
          <div
            class="q-mb-md q-pa-md rounded-borders"
            :class="err.outcome === 'ERROR' ? 'bg-red-1' : 'bg-orange-1'"
          >
            <div class="text-weight-medium row items-center">
              <q-badge :color="err.outcome === 'ERROR' ? 'negative' : 'warning'" :label="err.outcome" class="q-mr-sm" />
              <template v-if="err.completed_at">
                <q-badge color="positive" label="Completed" class="q-mr-sm" />
                <span class="text-caption text-grey-7">
                  by {{ err.completed_by_name || 'Unknown' }} on {{ formatDate(err.completed_at) }}
                </span>
              </template>
              <span class="q-ml-sm">{{ err.claim_claim_id }}</span>
            </div>
            <ul class="q-mt-sm q-mb-none q-pl-md">
              <li v-for="(msg, i) in err.error_messages" :key="i" class="text-body2">{{ msg }}</li>
            </ul>
          </div>

          <div class="row items-center">
            <div class="col-grow">
              <span class="text-weight-medium">Claim {{ err.claim_claim_id }}</span>
              <span v-if="err.claim_status" class="q-ml-sm text-caption">({{ err.claim_status }})</span>
            </div>
            <div class="q-gutter-sm">
              <q-btn
                v-if="err.ghims_import_item_id"
                size="sm"
                color="secondary"
                icon="edit"
                label="Fix in GHIMS import"
                @click="editGhimsImportItem(err.ghims_import_item_id)"
              />
              <q-btn
                v-if="err.claim_id"
                size="sm"
                color="primary"
                label="Edit claim"
                @click="editClaim(err.claim_id)"
              />
              <q-btn
                v-if="!err.claim_id && !err.ghims_import_item_id"
                size="sm"
                color="grey"
                label="Claim not found"
                disable
              />
              <q-checkbox
                v-if="err.claim_id"
                :model-value="selectedClaimIds.includes(err.claim_id)"
                :label="'Export'"
                @update:model-value="toggleExport(err.claim_id, $event)"
              />
              <q-btn
                size="sm"
                :color="err.completed_at ? 'grey' : 'positive'"
                :label="err.completed_at ? 'Mark not completed' : 'Mark as completed'"
                :loading="completingErrorId === err.id"
                outline
                @click="toggleCompleted(err)"
              />
            </div>
          </div>
        </div>
      </section>

      <section v-if="paginatedErrors.length && filteredErrors.length > rowsPerPage" class="diag-panel">
        <div class="panel-body row justify-center">
          <q-pagination
            v-model="paginationPage"
            :max="paginationMaxPages"
            :max-pages="7"
            direction-links
            boundary-links
            color="primary"
          />
        </div>
      </section>
    </template>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useQuasar } from 'quasar';
import { claimsAPI } from '../services/api';
import { setClaimsNavIds, setGhimsNavIds } from '../utils/claimNav';
import HmsPageHeader from '../components/ui/HmsPageHeader.vue';
import HmsButton from '../components/ui/HmsButton.vue';

const STORAGE_KEY = 'claimit_batch_selections';

const $route = useRoute();
const $router = useRouter();
const $q = useQuasar();

const uploading = ref(false);
const uploadFile = ref(null);
const batches = ref([]);
const viewingBatchId = ref(null);
const currentBatch = ref(null);
const batchErrors = ref([]);
const selectedClaimIds = ref([]);
const exportingBatch = ref(false);
const selectionsLocked = ref(false);
const outcomeFilter = ref('all');
const hideCompleted = ref(false);
const rowsPerPage = ref(25);
const paginationPage = ref(1);
const completingErrorId = ref(null);
const uploadGhimsBatchId = ref(null);
const uploadMainHmsOnly = ref(false);

const ghimsBatches = ref([]);
const ghimsBatchesLoading = ref(false);

const ghimsBatchSelectOptions = computed(() =>
  (ghimsBatches.value || []).map((b) => ({
    label: `${b.file_name} — ${formatDate(b.uploaded_at)} (${b.claim_count} claims)`,
    value: b.id,
  })),
);

async function loadGhimsBatches() {
  ghimsBatchesLoading.value = true;
  try {
    const res = await claimsAPI.getGhimsImportBatches();
    ghimsBatches.value = res.data || [];
  } catch (e) {
    ghimsBatches.value = [];
    $q.notify({ type: 'warning', message: e.response?.data?.detail || 'Could not load GHIMS import batches' });
  } finally {
    ghimsBatchesLoading.value = false;
  }
}

watch(uploadMainHmsOnly, (on) => {
  if (on) uploadGhimsBatchId.value = null;
});

function getStoredSelections() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function saveStoredSelections(data) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  } catch (_) {}
}

function applySelectionsForBatch(batchId, errors) {
  const stored = getStoredSelections();
  const key = String(batchId);
  const entry = stored[key];
  const validIds = (errors || []).filter((e) => e.claim_id != null).map((e) => Number(e.claim_id));
  const validSet = new Set(validIds);
  if (entry?.locked && Array.isArray(entry.claimIds)) {
    selectionsLocked.value = true;
    // Normalize stored IDs (JSON may have numbers or strings) and keep only those still in batch
    selectedClaimIds.value = entry.claimIds
      .map((id) => Number(id))
      .filter((id) => !Number.isNaN(id) && validSet.has(id));
  } else {
    selectionsLocked.value = entry?.locked ?? false;
    selectedClaimIds.value = [...validIds];
  }
}

function persistSelectionsForCurrentBatch() {
  const id = viewingBatchId.value;
  if (id == null) return;
  const stored = getStoredSelections();
  stored[String(id)] = {
    locked: selectionsLocked.value,
    claimIds: selectedClaimIds.value.map((id) => Number(id)),
  };
  saveStoredSelections(stored);
}

function onLockToggled(locked) {
  selectionsLocked.value = locked;
  persistSelectionsForCurrentBatch();
}

const filteredErrors = computed(() => {
  let list = batchErrors.value;
  if (outcomeFilter.value !== 'all') list = list.filter((e) => e.outcome === outcomeFilter.value);
  if (hideCompleted.value) list = list.filter((e) => !e.completed_at);
  return list;
});

const paginationMaxPages = computed(() =>
  Math.max(1, Math.ceil(filteredErrors.value.length / rowsPerPage.value))
);

const paginatedErrors = computed(() => {
  const list = filteredErrors.value;
  const page = paginationPage.value;
  const per = rowsPerPage.value;
  const maxP = Math.max(1, Math.ceil(list.length / per));
  const safePage = Math.min(Math.max(1, page), maxP);
  const start = (safePage - 1) * per;
  return list.slice(start, start + per);
});

/** ClaimIT overview row(s) parsed from HTML — scope of this import, not the whole GHIMS batch. */
function claimItVolumeCaption(summary) {
  const s = summary || {};
  if (s.total != null && typeof s.passed === 'number') {
    const w = s.warning ?? 0;
    const f = s.failed ?? 0;
    return `ClaimIT import: ${s.total} claim(s) (${s.passed} passed, ${w} warnings, ${f} failed)`;
  }
  return '';
}

const claimitGhimsMismatchWarn = computed(() => {
  const c = currentBatch.value;
  if (!c?.ghims_import_batch_id || c.ghims_import_claim_count == null || c.summary?.total == null) {
    return '';
  }
  const g = Number(c.ghims_import_claim_count);
  const t = Number(c.summary.total);
  if (Number.isNaN(g) || Number.isNaN(t) || g === t) return '';
  const fname = c.ghims_import_batch_file_name || 'GHIMS batch';
  return (
    `This ClaimIT report reflects ${t} claim(s) in that import, but "${fname}" in HMS has ${g} claim(s). `
    + 'Pick the GHIMS batch that matches the XML you imported into ClaimIT, or use "Main HMS only" if this report is not from GHIMS export.'
  );
});

watch(paginationMaxPages, (max) => {
  if (paginationPage.value > max) paginationPage.value = Math.max(1, max);
});

function formatDate(iso) {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

function goBack() {
  if (viewingBatchId.value) {
    viewingBatchId.value = null;
    currentBatch.value = null;
    batchErrors.value = [];
    selectedClaimIds.value = [];
    $router.replace('/claims/correct-errors').catch(() => {});
    loadGhimsBatches();
  } else {
    $router.push('/claims');
  }
}

async function loadBatches() {
  try {
    const res = await claimsAPI.getClaimitBatches();
    batches.value = res.data || [];
  } catch (e) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Failed to load batches' });
  }
}

async function uploadReport() {
  if (!uploadFile.value) return;
  uploading.value = true;
  try {
    const formData = new FormData();
    formData.append('file', uploadFile.value);
    if (uploadMainHmsOnly.value) {
      formData.append('main_hms_only', 'true');
    } else if (uploadGhimsBatchId.value != null && uploadGhimsBatchId.value !== '') {
      formData.append('ghims_import_batch_id', String(uploadGhimsBatchId.value));
    }
    const res = await claimsAPI.uploadClaimitReport(formData);
    const data = res.data;
    uploadFile.value = null;
    uploadMainHmsOnly.value = false;
    let extra = '';
    if (data.ghims_match_reason === 'skipped_main_hms') {
      extra = ' Main HMS only — not linked to Import GHIMS XML.';
    } else if (data.ghims_import_batch_file_name) {
      extra = ` Linked to GHIMS: ${data.ghims_import_batch_file_name}.`;
    } else if (data.ghims_match_reason === 'none' && (data.error_count || 0) > 0) {
      extra = ' No GHIMS batch matched; pick the batch next time or check claim IDs.';
    }
    $q.notify({
      type: 'positive',
      message: `Report uploaded. ${data.error_count} claim(s) with errors/warnings.${extra}`,
    });
    await loadBatches();
    viewingBatchId.value = data.batch_id;
    await openBatch(data.batch_id);
  } catch (e) {
    $q.notify({
      type: 'negative',
      message: e.response?.data?.detail || 'Upload failed',
    });
  } finally {
    uploading.value = false;
  }
}

async function openBatch(id) {
  viewingBatchId.value = id;
  outcomeFilter.value = 'all';
  paginationPage.value = 1;
  $router.replace({ path: `/claims/correct-errors/batch/${id}` }).catch(() => {});
  try {
    const res = await claimsAPI.getClaimitBatch(id);
    currentBatch.value = res.data;
    batchErrors.value = res.data?.errors || [];
    applySelectionsForBatch(id, batchErrors.value);
  } catch (e) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Failed to load batch' });
  }
}

function editClaim(claimId) {
  setClaimsNavIds(
    (filteredErrors.value || [])
      .map((e) => e.claim_id)
      .filter(Boolean)
  );
  const route = $router.resolve({ path: `/claims/edit/${claimId}` });
  window.open(route.href, '_blank');
}

function editGhimsImportItem(itemId) {
  if (!itemId) return;
  setGhimsNavIds(
    (filteredErrors.value || [])
      .map((e) => e.ghims_import_item_id)
      .filter(Boolean)
  );
  const route = $router.resolve({ path: `/claims/ghims-import/item/${itemId}` });
  window.open(route.href, '_blank');
}

async function toggleCompleted(err) {
  const batchId = viewingBatchId.value;
  if (batchId == null) return;
  completingErrorId.value = err.id;
  try {
    const completed = !err.completed_at;
    await claimsAPI.setClaimitErrorComplete(batchId, err.id, completed);
    const res = await claimsAPI.getClaimitBatch(batchId);
    batchErrors.value = res.data?.errors || [];
  } catch (e) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Failed to update' });
  } finally {
    completingErrorId.value = null;
  }
}

function toggleExport(claimId, checked) {
  const id = Number(claimId);
  if (checked) {
    if (!selectedClaimIds.value.includes(id)) selectedClaimIds.value.push(id);
  } else {
    selectedClaimIds.value = selectedClaimIds.value.filter((i) => i !== id);
  }
  if (selectionsLocked.value) {
    nextTick(() => persistSelectionsForCurrentBatch());
  }
}

// Claim IDs to export: only those that are selected AND in the current filter (so filtering to "Errors only" exports only selected errors)
const exportableClaimIds = computed(() => {
  const selected = selectedClaimIds.value;
  const inFilter = new Set((filteredErrors.value || []).map((e) => e.claim_id).filter(Boolean));
  return selected.filter((id) => inFilter.has(id));
});

const exportButtonLabel = computed(() => {
  const n = exportableClaimIds.value.length;
  if (outcomeFilter.value !== 'all') {
    return n ? `Export ${n} selected (current filter) for re-import` : 'Export selected (current filter)';
  }
  return n ? `Export ${n} selected for re-import` : 'Export selected for re-import';
});

async function exportBatchClaims() {
  const ids = exportableClaimIds.value;
  if (ids.length === 0) return;
  exportingBatch.value = true;
  try {
    const res = await claimsAPI.exportBatch(ids);
    const blob = new Blob([res.data], { type: 'application/xml' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `NHIS_CLA_batch_${currentBatch.value?.file_name?.replace(/\.[^.]+$/, '') || 'export'}.xml`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
    $q.notify({
      type: 'positive',
      message: `${ids.length} claim(s) exported for re-import to ClaimIT`,
    });
  } catch (e) {
    $q.notify({
      type: 'negative',
      message: e.response?.data?.detail || 'Export failed',
    });
  } finally {
    exportingBatch.value = false;
  }
}

onMounted(async () => {
  await loadBatches();
  await loadGhimsBatches();
  const batchId = $route.params.batchId;
  if (batchId) {
    const id = parseInt(batchId, 10);
    if (id) {
      viewingBatchId.value = id;
      try {
        const res = await claimsAPI.getClaimitBatch(id);
        currentBatch.value = res.data;
        batchErrors.value = res.data?.errors || [];
        applySelectionsForBatch(id, batchErrors.value);
      } catch (e) {
        $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Failed to load batch' });
      }
    }
  }
});

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
.upload-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem;
}
.upload-file { flex: 1 1 16rem; min-width: 12rem; max-width: 28rem; }
.batch-list { display: flex; flex-direction: column; gap: 0.5rem; }
.batch-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  flex-wrap: wrap;
  padding: 0.75rem 0.85rem;
  border: 1px solid var(--hms-border);
  border-radius: var(--hms-radius-lg);
  background: var(--hms-surface, transparent);
}
.batch-name { font-weight: 650; color: var(--hms-text-primary); font-size: var(--hms-text-sm); }
.batch-meta { margin-top: 0.2rem; font-size: var(--hms-text-xs); color: var(--hms-text-muted); }
.batch-actions { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; }
.empty-hint { font-size: var(--hms-text-sm); color: var(--hms-text-muted); margin: 0; }
.batch-toolbar :deep(.q-card-section) { padding: 1rem; }
</style>
