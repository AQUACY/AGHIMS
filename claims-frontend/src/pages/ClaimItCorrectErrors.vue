<template>
  <q-page class="q-pa-md">
    <div class="row items-center q-mb-md">
      <q-btn flat round dense icon="arrow_back" @click="goBack" />
      <div class="text-h4 q-ml-sm text-weight-bold glass-text">
        {{ viewingBatchId ? `Batch: ${currentBatch?.file_name || ''}` : 'Correct Errors' }}
      </div>
      <q-space />
      <q-btn
        v-if="viewingBatchId && currentBatch"
        flat
        color="negative"
        icon="delete"
        label="Delete batch"
        :loading="deletingBatchId === viewingBatchId"
        @click="deleteBatch(currentBatch)"
      />
    </div>

    <!-- Upload (when not viewing a batch) -->
    <q-card v-if="!viewingBatchId" class="q-mb-lg glass-card" flat bordered>
      <q-card-section>
        <div class="text-h6 q-mb-md">Upload ClaimIT Import Report</div>
        <p class="text-caption text-grey-7 q-mb-md">
          Use <strong>Import GHIMS XML</strong> when the XML came from that screen; use <strong>main HMS claims only</strong> when the XML was exported from the normal claim registry (encounters) and ClaimIT errors should open <strong>Edit claim</strong>, not GHIMS import rows.
        </p>
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
        <div class="row q-gutter-md items-center">
          <q-file
            v-model="uploadFile"
            label="Select report (HTML)"
            accept=".html,.htm"
            outlined
            dense
            clearable
            class="col-12 col-md-5"
            @update:model-value="uploadFile = $event"
          />
          <q-btn
            color="primary"
            label="Upload"
            :loading="uploading"
            :disable="!uploadFile"
            @click="uploadReport"
          />
        </div>
      </q-card-section>
    </q-card>

    <!-- Batch list (when not viewing a batch) -->
    <q-card v-if="!viewingBatchId" class="q-mb-lg glass-card" flat bordered>
      <q-card-section>
        <div class="text-h6 q-mb-md">Recent report batches</div>
        <q-list v-if="batches.length" bordered separator>
          <q-item
            v-for="b in batches"
            :key="b.id"
            clickable
            @click="openBatch(b.id)"
          >
            <q-item-section avatar>
              <q-icon name="folder" color="primary" />
            </q-item-section>
            <q-item-section>
              <q-item-label>{{ b.file_name }}</q-item-label>
              <q-item-label caption>
                {{ formatDate(b.uploaded_at) }} · {{ b.error_count }} claim(s) with errors/warnings in this HTML
                <template v-if="claimItVolumeCaption(b.summary)">
                  · {{ claimItVolumeCaption(b.summary) }}
                </template>
                <template v-if="b.ghims_import_batch_file_name">
                  · GHIMS: {{ b.ghims_import_batch_file_name }}<template v-if="b.ghims_import_claim_count != null"> ({{ b.ghims_import_claim_count }} claims in HMS)</template>
                </template>
              </q-item-label>
            </q-item-section>
            <q-item-section side>
              <div class="row q-gutter-xs items-center no-wrap" @click.stop>
                <q-btn
                  flat
                  dense
                  round
                  color="negative"
                  icon="delete"
                  :loading="deletingBatchId === b.id"
                  @click="deleteBatch(b)"
                >
                  <q-tooltip>Delete this uploaded report</q-tooltip>
                </q-btn>
                <q-btn flat dense round icon="chevron_right" />
              </div>
            </q-item-section>
          </q-item>
        </q-list>
        <p v-else class="text-grey-7">No report batches yet. Upload a ClaimIT import report above.</p>
      </q-card-section>
    </q-card>

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
      <q-card class="q-mb-md glass-card" flat bordered>
        <q-card-section>
          <div class="row items-center justify-between q-mb-md">
            <div>
              <span class="text-caption text-grey-7">Errors / warnings in this batch: </span>
              <strong>{{ filteredErrors.length }}</strong>
              <span v-if="outcomeFilter !== 'all' || completedFilter !== 'all'" class="text-caption text-grey-7"> (filtered from {{ batchErrors.length }})</span>
            </div>
            <q-btn
              color="primary"
              :label="exportButtonLabel"
              icon="download"
              :disable="exportableTotal === 0"
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
            <q-btn-toggle
              v-model="completedFilter"
              no-caps
              dense
              toggle-color="teal"
              class="q-ml-sm"
              :options="[
                { label: 'Any status', value: 'all' },
                { label: 'Not completed', value: 'open' },
                { label: 'Completed only', value: 'completed' },
              ]"
              @update:model-value="paginationPage = 1"
            />
            <q-checkbox
              class="q-ml-md"
              dense
              :model-value="allFilteredExportSelected"
              :indeterminate="someFilteredExportSelected"
              :disable="filteredExportableTotal === 0"
              label="Select all in filter"
              @update:model-value="toggleSelectAllFiltered"
            />
            <q-btn
              flat
              dense
              no-caps
              color="teal"
              icon="done_all"
              label="Select all completed"
              :disable="completedExportableTotal === 0"
              @click="selectAllCompleted"
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
        </q-card-section>
      </q-card>

      <q-card v-for="err in paginatedErrors" :key="err.id" class="q-mb-md glass-card" flat bordered>
        <q-card-section>
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
              <span v-if="rowWorkflowStatus(err)" class="q-ml-sm text-caption">
                ({{ statusLabel(rowWorkflowStatus(err)) }})
                <span v-if="!rowIsExportReady(err)" class="text-orange-9"> · finalize before complete/export</span>
              </span>
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
                v-if="rowExportTarget(err)"
                :model-value="isRowExportSelected(err)"
                label="Export"
                @update:model-value="toggleRowExport(err, $event)"
              />
              <q-btn
                size="sm"
                :color="err.completed_at ? 'grey' : 'positive'"
                :label="err.completed_at ? 'Mark not completed' : 'Mark as completed'"
                :loading="completingErrorId === err.id"
                :disable="!err.completed_at && !rowIsExportReady(err)"
                outline
                @click="toggleCompleted(err)"
              />
            </div>
          </div>
        </q-card-section>
      </q-card>

      <q-card v-if="paginatedErrors.length && filteredErrors.length > rowsPerPage" class="q-mt-md glass-card" flat bordered>
        <q-card-section class="row justify-center">
          <q-pagination
            v-model="paginationPage"
            :max="paginationMaxPages"
            :max-pages="7"
            direction-links
            boundary-links
            color="primary"
          />
        </q-card-section>
      </q-card>
    </template>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useQuasar } from 'quasar';
import { claimsAPI } from '../services/api';
import { isClaimExportable, statusLabel } from '../utils/claimVetting';
import { parseExportErrorDetail, exportErrorMessage } from '../utils/exportErrorDetail';

const STORAGE_KEY = 'claimit_batch_selections';

const $route = useRoute();
const $router = useRouter();
const $q = useQuasar();

const uploading = ref(false);
const uploadFile = ref(null);
const batches = ref([]);
const deletingBatchId = ref(null);
const viewingBatchId = ref(null);
const currentBatch = ref(null);
const batchErrors = ref([]);
const selectedClaimIds = ref([]);
const selectedItemIds = ref([]);
const exportingBatch = ref(false);
const selectionsLocked = ref(false);
const outcomeFilter = ref('all');
const completedFilter = ref('all'); // all | open | completed
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

/** Prefer GHIMS import item for re-import export; otherwise HMS claim. */
function rowExportTarget(err) {
  if (err?.ghims_import_item_id != null) return { kind: 'item', id: Number(err.ghims_import_item_id) };
  if (err?.claim_id != null) return { kind: 'claim', id: Number(err.claim_id) };
  return null;
}

function collectExportTargets(errors) {
  const claimIds = [];
  const itemIds = [];
  const seenClaim = new Set();
  const seenItem = new Set();
  for (const e of errors || []) {
    const t = rowExportTarget(e);
    if (!t || Number.isNaN(t.id)) continue;
    if (t.kind === 'item') {
      if (!seenItem.has(t.id)) {
        seenItem.add(t.id);
        itemIds.push(t.id);
      }
    } else if (!seenClaim.has(t.id)) {
      seenClaim.add(t.id);
      claimIds.push(t.id);
    }
  }
  return { claimIds, itemIds };
}

function applySelectionsForBatch(batchId, errors) {
  const stored = getStoredSelections();
  const key = String(batchId);
  const entry = stored[key];
  const { claimIds: validClaimIds, itemIds: validItemIds } = collectExportTargets(errors);
  const validClaimSet = new Set(validClaimIds);
  const validItemSet = new Set(validItemIds);
  if (entry?.locked) {
    selectionsLocked.value = true;
    selectedClaimIds.value = Array.isArray(entry.claimIds)
      ? entry.claimIds.map((id) => Number(id)).filter((id) => !Number.isNaN(id) && validClaimSet.has(id))
      : [];
    selectedItemIds.value = Array.isArray(entry.itemIds)
      ? entry.itemIds.map((id) => Number(id)).filter((id) => !Number.isNaN(id) && validItemSet.has(id))
      : [];
  } else {
    selectionsLocked.value = entry?.locked ?? false;
    selectedClaimIds.value = [...validClaimIds];
    selectedItemIds.value = [...validItemIds];
  }
}

function persistSelectionsForCurrentBatch() {
  const id = viewingBatchId.value;
  if (id == null) return;
  const stored = getStoredSelections();
  stored[String(id)] = {
    locked: selectionsLocked.value,
    claimIds: selectedClaimIds.value.map((id) => Number(id)),
    itemIds: selectedItemIds.value.map((id) => Number(id)),
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
  if (completedFilter.value === 'open') list = list.filter((e) => !e.completed_at);
  if (completedFilter.value === 'completed') list = list.filter((e) => !!e.completed_at);
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
    selectedItemIds.value = [];
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

function deleteBatch(batch) {
  if (!batch?.id) return;
  $q.dialog({
    title: 'Delete error report?',
    message:
      `Permanently delete “${batch.file_name}” and its ${batch.error_count || 0} error/warning row(s)? This cannot be undone.`,
    cancel: { label: 'Keep', flat: true, color: 'primary' },
    ok: { label: 'Delete', color: 'negative', unelevated: true },
    persistent: true,
  }).onOk(async () => {
    deletingBatchId.value = batch.id;
    try {
      await claimsAPI.deleteClaimitBatch(batch.id);
      if (viewingBatchId.value === batch.id) {
        viewingBatchId.value = null;
        currentBatch.value = null;
        batchErrors.value = [];
        selectedClaimIds.value = [];
        selectedItemIds.value = [];
        $router.replace('/claims/correct-errors').catch(() => {});
      }
      await loadBatches();
      $q.notify({ type: 'positive', message: 'Error report deleted' });
    } catch (e) {
      $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Failed to delete report' });
    } finally {
      deletingBatchId.value = null;
    }
  });
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
  completedFilter.value = 'all';
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
  const route = $router.resolve({ path: `/claims/edit/${claimId}` });
  window.open(route.href, '_blank');
}

function editGhimsImportItem(itemId) {
  if (!itemId) return;
  const route = $router.resolve({ path: `/claims/ghims-import/item/${itemId}` });
  window.open(route.href, '_blank');
}

async function toggleCompleted(err) {
  const batchId = viewingBatchId.value;
  if (batchId == null) return;
  const markingComplete = !err.completed_at;
  if (markingComplete && !rowIsExportReady(err)) {
    const st = rowWorkflowStatus(err) || 'unknown';
    $q.notify({
      type: 'warning',
      multiLine: true,
      timeout: 10000,
      message:
        `${err.claim_claim_id} is not finalized for export (status: ${statusLabel(st)}). `
        + 'Finalize or pharmacy/doctor-vet the claim first, then mark completed.',
    });
    return;
  }
  completingErrorId.value = err.id;
  try {
    await claimsAPI.setClaimitErrorComplete(batchId, err.id, markingComplete);
    const res = await claimsAPI.getClaimitBatch(batchId);
    batchErrors.value = res.data?.errors || [];
  } catch (e) {
    $q.notify({
      type: 'negative',
      multiLine: true,
      timeout: 12000,
      message: e.response?.data?.detail || 'Failed to update',
    });
  } finally {
    completingErrorId.value = null;
  }
}

function rowWorkflowStatus(err) {
  return err?.ghims_import_item_status || err?.claim_status || '';
}

function rowIsExportReady(err) {
  if (err?.exportable === true) return true;
  if (err?.exportable === false) return false;
  const status = rowWorkflowStatus(err);
  if (!status && !err?.claim_id && !err?.ghims_import_item_id) return false;
  return isClaimExportable({ status, claim_status: status });
}

function isRowExportSelected(err) {
  const t = rowExportTarget(err);
  if (!t) return false;
  if (t.kind === 'item') return selectedItemIds.value.includes(t.id);
  return selectedClaimIds.value.includes(t.id);
}

function toggleRowExport(err, checked) {
  const t = rowExportTarget(err);
  if (!t) return;
  if (t.kind === 'item') {
    if (checked) {
      if (!selectedItemIds.value.includes(t.id)) selectedItemIds.value.push(t.id);
    } else {
      selectedItemIds.value = selectedItemIds.value.filter((i) => i !== t.id);
    }
  } else if (checked) {
    if (!selectedClaimIds.value.includes(t.id)) selectedClaimIds.value.push(t.id);
  } else {
    selectedClaimIds.value = selectedClaimIds.value.filter((i) => i !== t.id);
  }
  if (selectionsLocked.value) {
    nextTick(() => persistSelectionsForCurrentBatch());
  }
}

const filteredExportTargets = computed(() => collectExportTargets(filteredErrors.value));
const completedExportTargets = computed(() =>
  collectExportTargets((batchErrors.value || []).filter((e) => e.completed_at))
);

const filteredExportableTotal = computed(
  () => filteredExportTargets.value.claimIds.length + filteredExportTargets.value.itemIds.length
);
const completedExportableTotal = computed(
  () => completedExportTargets.value.claimIds.length + completedExportTargets.value.itemIds.length
);

const allFilteredExportSelected = computed(() => {
  const { claimIds, itemIds } = filteredExportTargets.value;
  if (!claimIds.length && !itemIds.length) return false;
  return (
    claimIds.every((id) => selectedClaimIds.value.includes(id))
    && itemIds.every((id) => selectedItemIds.value.includes(id))
  );
});

const someFilteredExportSelected = computed(() => {
  if (!filteredExportableTotal.value || allFilteredExportSelected.value) return false;
  const { claimIds, itemIds } = filteredExportTargets.value;
  return (
    claimIds.some((id) => selectedClaimIds.value.includes(id))
    || itemIds.some((id) => selectedItemIds.value.includes(id))
  );
});

function applyTargetSelection(claimIds, itemIds, mode) {
  if (mode === 'add') {
    const claimSet = new Set(selectedClaimIds.value.map(Number));
    const itemSet = new Set(selectedItemIds.value.map(Number));
    claimIds.forEach((id) => claimSet.add(id));
    itemIds.forEach((id) => itemSet.add(id));
    selectedClaimIds.value = [...claimSet];
    selectedItemIds.value = [...itemSet];
  } else if (mode === 'remove') {
    const removeClaim = new Set(claimIds);
    const removeItem = new Set(itemIds);
    selectedClaimIds.value = selectedClaimIds.value.filter((id) => !removeClaim.has(Number(id)));
    selectedItemIds.value = selectedItemIds.value.filter((id) => !removeItem.has(Number(id)));
  }
  if (selectionsLocked.value) {
    nextTick(() => persistSelectionsForCurrentBatch());
  }
}

function toggleSelectAllFiltered(checked) {
  const { claimIds, itemIds } = filteredExportTargets.value;
  applyTargetSelection(claimIds, itemIds, checked ? 'add' : 'remove');
}

function selectAllCompleted() {
  const { claimIds, itemIds } = completedExportTargets.value;
  if (!claimIds.length && !itemIds.length) {
    $q.notify({ type: 'warning', message: 'No completed claims available to select for export' });
    return;
  }
  applyTargetSelection(claimIds, itemIds, 'add');
  completedFilter.value = 'completed';
  paginationPage.value = 1;
  $q.notify({
    type: 'positive',
    message: `Selected ${claimIds.length + itemIds.length} completed claim(s). Click Export to download.`,
  });
}

const exportableClaimIds = computed(() => {
  const inFilter = new Set(filteredExportTargets.value.claimIds);
  return selectedClaimIds.value.filter((id) => inFilter.has(Number(id)));
});

const exportableItemIds = computed(() => {
  const inFilter = new Set(filteredExportTargets.value.itemIds);
  return selectedItemIds.value.filter((id) => inFilter.has(Number(id)));
});

const exportableTotal = computed(
  () => exportableClaimIds.value.length + exportableItemIds.value.length
);

const exportButtonLabel = computed(() => {
  const n = exportableTotal.value;
  const hasFilter = outcomeFilter.value !== 'all' || completedFilter.value !== 'all';
  if (hasFilter) {
    return n ? `Export ${n} selected (current filter) for re-import` : 'Export selected (current filter)';
  }
  return n ? `Export ${n} selected for re-import` : 'Export selected for re-import';
});

async function downloadXmlBlob(res, filename) {
  const blob = new Blob([res.data], { type: 'application/xml' });
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', filename);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

async function exportBatchClaims() {
  const claimIds = exportableClaimIds.value;
  const itemIds = exportableItemIds.value;
  if (!claimIds.length && !itemIds.length) return;
  exportingBatch.value = true;
  const base = currentBatch.value?.file_name?.replace(/\.[^.]+$/, '') || 'export';
  try {
    let total = 0;
    if (claimIds.length) {
      const res = await claimsAPI.exportBatch(claimIds);
      await downloadXmlBlob(res, `NHIS_CLA_batch_${base}${itemIds.length ? '_hms' : ''}.xml`);
      total += claimIds.length;
    }
    if (itemIds.length) {
      const res = await claimsAPI.exportGhimsImportItems(itemIds);
      await downloadXmlBlob(res, `NHIS_CLA_batch_${base}${claimIds.length ? '_ghims' : ''}.xml`);
      total += itemIds.length;
    }
    $q.notify({
      type: 'positive',
      message: `${total} claim(s) exported for re-import to ClaimIT`,
    });
  } catch (e) {
    const detail = await parseExportErrorDetail(e);
    const message = exportErrorMessage(detail) || 'Export failed';
    $q.notify({
      type: 'negative',
      multiLine: true,
      timeout: 0,
      actions: [{ label: 'Dismiss', color: 'white' }],
      message,
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
