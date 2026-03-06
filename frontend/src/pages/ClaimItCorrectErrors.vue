<template>
  <q-page class="q-pa-md">
    <div class="row items-center q-mb-md">
      <q-btn flat round dense icon="arrow_back" @click="goBack" />
      <div class="text-h4 q-ml-sm text-weight-bold glass-text">
        {{ viewingBatchId ? `Batch: ${currentBatch?.file_name || ''}` : 'Correct Errors' }}
      </div>
    </div>

    <!-- Upload (when not viewing a batch) -->
    <q-card v-if="!viewingBatchId" class="q-mb-lg glass-card" flat bordered>
      <q-card-section>
        <div class="text-h6 q-mb-md">Upload ClaimIT Import Report</div>
        <p class="text-caption text-grey-7 q-mb-md">
          Upload the HTML report from ClaimIT after importing your XML. The system will extract claims with errors or warnings so you can fix them and re-export.
        </p>
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
                {{ formatDate(b.uploaded_at) }} · {{ b.error_count }} claim(s) with errors/warnings
              </q-item-label>
            </q-item-section>
            <q-item-section side>
              <q-btn flat dense round icon="chevron_right" />
            </q-item-section>
          </q-item>
        </q-list>
        <p v-else class="text-grey-7">No report batches yet. Upload a ClaimIT import report above.</p>
      </q-card-section>
    </q-card>

    <!-- Batch detail: claims with errors -->
    <template v-if="viewingBatchId && currentBatch">
      <q-card class="q-mb-md glass-card" flat bordered>
        <q-card-section>
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
              <span v-if="err.claim_status" class="q-ml-sm text-caption">({{ err.claim_status }})</span>
            </div>
            <div class="q-gutter-sm">
              <q-btn
                v-if="err.claim_id"
                size="sm"
                color="primary"
                label="Edit claim"
                @click="editClaim(err.claim_id)"
              />
              <q-btn
                v-else
                size="sm"
                color="grey"
                label="Claim not found in system"
                disable
              />
              <q-checkbox
                v-if="err.claim_id"
                :model-value="selectedClaimIds.includes(err.claim_id)"
                :label="'Export'"
                @update:model-value="toggleExport(err.claim_id, $event)"
              />
              <q-btn
                v-if="err.claim_id"
                size="sm"
                :color="err.completed_at ? 'grey' : 'positive'"
                :label="err.completed_at ? 'Mark not completed' : 'Mark as completed'"
                :loading="completingErrorId === err.id"
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
    const res = await claimsAPI.uploadClaimitReport(formData);
    const data = res.data;
    uploadFile.value = null;
    $q.notify({
      type: 'positive',
      message: `Report uploaded. ${data.error_count} claim(s) with errors/warnings.`,
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
  const route = $router.resolve({ path: `/claims/edit/${claimId}` });
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
