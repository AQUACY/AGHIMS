<template>
  <q-page class="hms-page ce-page">
    <div class="ce-atmosphere" aria-hidden="true" />

    <motion.div
      :initial="reduceMotion ? false : { opacity: 0, y: 14 }"
      :animate="{ opacity: 1, y: 0 }"
      :transition="{ duration: 0.42, ease: [0.16, 1, 0.3, 1] }"
    >
      <HmsPageHeader
        :title="viewingBatchId ? (currentBatch?.file_name || 'Report batch') : 'Correct errors'"
        :subtitle="viewingBatchId
          ? 'Resolve ClaimIT findings, mark complete, and export cleaned claims for re-import.'
          : 'Upload ClaimIT HTML reports, then work each batch until every finding is cleared.'"
      >
        <template #actions>
          <HmsButton
            v-if="viewingBatchId && currentBatch"
            variant="danger"
            size="sm"
            :loading="deletingBatchId === viewingBatchId"
            @click="deleteBatch(currentBatch)"
          >
            Delete batch
          </HmsButton>
          <HmsButton variant="ghost" size="sm" @click="goBack">Back</HmsButton>
        </template>
      </HmsPageHeader>
    </motion.div>

    <!-- Upload hub -->
    <motion.section
      v-if="!viewingBatchId"
      class="ce-panel"
      :initial="reduceMotion ? false : { opacity: 0, y: 16 }"
      :animate="{ opacity: 1, y: 0 }"
      :transition="{ delay: 0.04, duration: 0.42, ease: [0.16, 1, 0.3, 1] }"
    >
      <div class="ce-panel__head">
        <div>
          <div class="ce-kicker">01 — Ingest</div>
          <h2 class="ce-panel__title">Upload ClaimIT report</h2>
          <p class="ce-lede">
            Link to Import GHIMS XML when the file came from that screen. Use main HMS only when the XML was exported from the claim registry.
          </p>
        </div>
      </div>

      <div class="ce-upload-grid">
        <label class="ce-check">
          <q-checkbox v-model="uploadMainHmsOnly" dense color="primary" />
          <span>
            <strong>Main HMS claims only</strong>
            <span class="ce-muted"> — do not link this report to Import GHIMS XML</span>
          </span>
        </label>

        <q-select
          v-model="uploadGhimsBatchId"
          :options="ghimsBatchSelectOptions"
          emit-value
          map-options
          clearable
          outlined
          dense
          label="GHIMS import this report belongs to (optional)"
          :hint="uploadMainHmsOnly ? 'Disabled: treated as main HMS claims.' : 'Leave empty to auto-detect from claim IDs.'"
          class="ce-field"
          :loading="ghimsBatchesLoading"
          :disable="uploadMainHmsOnly"
        />

        <div class="ce-upload-row">
          <q-file
            v-model="uploadFile"
            label="Select report (HTML)"
            accept=".html,.htm"
            outlined
            dense
            clearable
            class="ce-field ce-field--file"
            @update:model-value="uploadFile = $event"
          >
            <template #prepend>
              <q-icon name="upload_file" />
            </template>
          </q-file>
          <HmsButton
            variant="primary"
            size="md"
            :loading="uploading"
            :disabled="!uploadFile"
            @click="uploadReport"
          >
            Upload report
          </HmsButton>
        </div>
      </div>
    </motion.section>

    <!-- Batch library -->
    <motion.section
      v-if="!viewingBatchId"
      class="ce-panel"
      :initial="reduceMotion ? false : { opacity: 0, y: 16 }"
      :animate="{ opacity: 1, y: 0 }"
      :transition="{ delay: 0.08, duration: 0.42, ease: [0.16, 1, 0.3, 1] }"
    >
      <div class="ce-panel__head">
        <div>
          <div class="ce-kicker">02 — Library</div>
          <h2 class="ce-panel__title">Recent report batches</h2>
          <p class="ce-lede">Open a batch to triage errors, mark completion, and export for ClaimIT re-import.</p>
        </div>
        <span v-if="batches.length" class="ce-count">{{ batches.length }}</span>
      </div>

      <div v-if="batches.length" class="ce-batch-list">
        <motion.article
          v-for="(b, idx) in batches"
          :key="b.id"
          class="ce-batch-row"
          :initial="reduceMotion ? false : { opacity: 0, y: 10 }"
          :animate="{ opacity: 1, y: 0 }"
          :transition="{ delay: Math.min(idx, 8) * 0.03, duration: 0.35, ease: [0.16, 1, 0.3, 1] }"
        >
          <div class="ce-batch-row__main">
            <div class="ce-batch-row__name">{{ b.file_name }}</div>
            <div class="ce-batch-row__meta">
              <span>{{ formatDate(b.uploaded_at) }}</span>
              <span class="ce-dot" aria-hidden="true" />
              <span>{{ b.error_count }} finding(s)</span>
              <template v-if="claimItVolumeCaption(b.summary)">
                <span class="ce-dot" aria-hidden="true" />
                <span>{{ claimItVolumeCaption(b.summary) }}</span>
              </template>
              <template v-if="b.ghims_import_batch_file_name">
                <span class="ce-dot" aria-hidden="true" />
                <span>GHIMS · {{ b.ghims_import_batch_file_name }}<template v-if="b.ghims_import_claim_count != null"> ({{ b.ghims_import_claim_count }})</template></span>
              </template>
            </div>
          </div>
          <div class="ce-batch-row__actions">
            <HmsButton variant="secondary" size="sm" @click="openBatch(b.id)">Open</HmsButton>
            <HmsButton
              variant="ghost"
              size="sm"
              :loading="deletingBatchId === b.id"
              @click="deleteBatch(b)"
            >
              Delete
            </HmsButton>
          </div>
        </motion.article>
      </div>
      <div v-else class="ce-empty">
        <div class="ce-empty__title">No reports yet</div>
        <p class="ce-muted">Upload a ClaimIT import HTML report to begin correcting findings.</p>
      </div>
    </motion.section>

    <!-- Batch workspace -->
    <template v-if="viewingBatchId && currentBatch">
      <motion.div
        class="ce-kpi-grid"
        :initial="reduceMotion ? false : { opacity: 0, y: 12 }"
        :animate="{ opacity: 1, y: 0 }"
        :transition="{ delay: 0.04, duration: 0.4, ease: [0.16, 1, 0.3, 1] }"
      >
        <div class="ce-kpi">
          <div class="ce-kpi__label">Findings</div>
          <div class="ce-kpi__value">{{ batchStats.total }}</div>
        </div>
        <div class="ce-kpi" data-tone="critical">
          <div class="ce-kpi__label">Errors</div>
          <div class="ce-kpi__value">{{ batchStats.errors }}</div>
        </div>
        <div class="ce-kpi" data-tone="warning">
          <div class="ce-kpi__label">Warnings</div>
          <div class="ce-kpi__value">{{ batchStats.warnings }}</div>
        </div>
        <div class="ce-kpi" data-tone="success">
          <div class="ce-kpi__label">Completed</div>
          <div class="ce-kpi__value">{{ batchStats.completed }}</div>
        </div>
        <div class="ce-kpi" data-tone="accent">
          <div class="ce-kpi__label">Ready to export</div>
          <div class="ce-kpi__value">{{ exportableTotal }}</div>
        </div>
      </motion.div>

      <div
        v-if="batchErrors.length === 0 && claimItVolumeCaption(currentBatch.summary)"
        class="ce-callout"
        data-tone="ok"
      >
        <q-icon name="verified" size="22px" />
        <div>
          <div class="ce-callout__title">Nothing to fix in this file</div>
          <p>
            ClaimIT listed no ERROR or WARNING rows.
            {{ claimItVolumeCaption(currentBatch.summary) }}.
            That count is only what ClaimIT processed in that import.
          </p>
        </div>
      </div>

      <div v-if="claimitGhimsMismatchWarn" class="ce-callout" data-tone="warn">
        <q-icon name="warning_amber" size="22px" />
        <div>
          <div class="ce-callout__title">Batch size mismatch</div>
          <p>{{ claimitGhimsMismatchWarn }}</p>
        </div>
      </div>

      <div v-if="currentBatch?.ghims_import_batch_id" class="ce-callout" data-tone="link">
        <q-icon name="link" size="22px" />
        <div class="ce-callout__body">
          <div>
            <div class="ce-callout__title">Linked GHIMS import</div>
            <p>
              {{ currentBatch.ghims_import_batch_file_name || ('batch #' + currentBatch.ghims_import_batch_id) }}.
              Use <strong>Fix in GHIMS import</strong> on each row.
            </p>
          </div>
          <HmsButton
            variant="secondary"
            size="sm"
            @click="$router.push(`/claims/ghims-import/batch/${currentBatch.ghims_import_batch_id}`)"
          >
            Open batch
          </HmsButton>
        </div>
      </div>
      <div
        v-else-if="currentBatch?.summary?.ghims_resolution === 'skipped_main_hms'"
        class="ce-callout"
        data-tone="info"
      >
        <q-icon name="badge" size="22px" />
        <div>
          <div class="ce-callout__title">Main HMS claims only</div>
          <p>Rows use <strong>Edit claim</strong> for claims in this system; nothing is linked to Import GHIMS XML.</p>
        </div>
      </div>
      <div v-else class="ce-callout" data-tone="info">
        <q-icon name="info" size="22px" />
        <div>
          <div class="ce-callout__title">No GHIMS batch matched</div>
          <p>
            Use <strong>Edit claim</strong> if the claim exists here, or open
            <router-link to="/claims/ghims-import" class="ce-inline-link">Import GHIMS XML</router-link> manually.
          </p>
        </div>
      </div>

      <motion.section
        class="ce-panel ce-toolbar"
        :initial="reduceMotion ? false : { opacity: 0, y: 12 }"
        :animate="{ opacity: 1, y: 0 }"
        :transition="{ delay: 0.08, duration: 0.4, ease: [0.16, 1, 0.3, 1] }"
      >
        <div class="ce-toolbar__top">
          <div>
            <div class="ce-kicker">Workspace</div>
            <div class="ce-toolbar__title">
              Showing <strong>{{ filteredErrors.length }}</strong>
              <span v-if="outcomeFilter !== 'all' || completedFilter !== 'all'" class="ce-muted">
                of {{ batchErrors.length }}
              </span>
            </div>
          </div>
          <HmsButton
            variant="primary"
            size="sm"
            :disabled="exportableTotal === 0"
            :loading="exportingBatch"
            @click="exportBatchClaims"
          >
            {{ exportButtonLabel }}
          </HmsButton>
        </div>

        <div class="ce-toolbar__filters">
          <div class="ce-filter-block">
            <span class="ce-filter-label">Severity</span>
            <q-btn-toggle
              v-model="outcomeFilter"
              no-caps
              dense
              unelevated
              toggle-color="primary"
              class="ce-seg"
              :options="[
                { label: 'All', value: 'all' },
                { label: 'Errors', value: 'ERROR' },
                { label: 'Warnings', value: 'WARNING' },
              ]"
              @update:model-value="paginationPage = 1"
            />
          </div>
          <div class="ce-filter-block">
            <span class="ce-filter-label">Status</span>
            <q-btn-toggle
              v-model="completedFilter"
              no-caps
              dense
              unelevated
              toggle-color="teal"
              class="ce-seg"
              :options="[
                { label: 'Any', value: 'all' },
                { label: 'Open', value: 'open' },
                { label: 'Completed', value: 'completed' },
              ]"
              @update:model-value="paginationPage = 1"
            />
          </div>
          <div class="ce-filter-block ce-filter-block--actions">
            <q-checkbox
              dense
              :model-value="allFilteredExportSelected"
              :indeterminate="someFilteredExportSelected"
              :disable="filteredExportableTotal === 0"
              label="Select all in filter"
              @update:model-value="toggleSelectAllFiltered"
            />
            <HmsButton
              variant="soft"
              size="sm"
              :disabled="completedExportableTotal === 0"
              @click="selectAllCompleted"
            >
              Select all completed
            </HmsButton>
            <q-checkbox
              v-model="selectionsLocked"
              dense
              label="Lock selections"
              @update:model-value="onLockToggled"
            />
          </div>
          <div class="ce-filter-block ce-filter-block--pager">
            <span class="ce-filter-label">Rows</span>
            <q-select
              v-model="rowsPerPage"
              :options="[10, 25, 50, 100]"
              dense
              outlined
              emit-value
              map-options
              options-dense
              class="ce-rows"
              @update:model-value="paginationPage = 1"
            />
            <q-pagination
              v-model="paginationPage"
              :max="paginationMaxPages"
              :max-pages="5"
              direction-links
              boundary-links
              color="primary"
              dense
            />
          </div>
        </div>
      </motion.section>

      <div v-if="!paginatedErrors.length" class="ce-empty ce-empty--panel">
        <div class="ce-empty__title">No findings in this view</div>
        <p class="ce-muted">Try changing severity or completion filters.</p>
      </div>

      <div class="ce-cards">
        <motion.article
          v-for="(err, idx) in paginatedErrors"
          :key="err.id"
          class="ce-card"
          :data-outcome="err.outcome"
          :data-done="err.completed_at ? '1' : '0'"
          :initial="reduceMotion ? false : { opacity: 0, y: 12 }"
          :animate="{ opacity: 1, y: 0 }"
          :transition="{ delay: Math.min(idx, 6) * 0.035, duration: 0.36, ease: [0.16, 1, 0.3, 1] }"
        >
          <div class="ce-card__rail" aria-hidden="true" />
          <div class="ce-card__body">
            <div class="ce-card__top">
              <div class="ce-card__identity">
                <span class="ce-index">{{ ((paginationPage - 1) * rowsPerPage) + idx + 1 }}</span>
                <div>
                  <div class="ce-claim-id">{{ err.claim_claim_id }}</div>
                  <div v-if="rowWorkflowStatus(err)" class="ce-muted">
                    Status: {{ statusLabel(rowWorkflowStatus(err)) }}
                    <span v-if="!rowIsExportReady(err)" class="ce-status-warn"> · finalize before complete/export</span>
                  </div>
                </div>
              </div>
              <div class="ce-card__chips">
                <span class="ce-sev" :data-sev="err.outcome === 'ERROR' ? 'critical' : 'warning'">
                  {{ err.outcome }}
                </span>
                <span v-if="err.completed_at" class="ce-sev" data-sev="ok">Completed</span>
              </div>
            </div>

            <ul v-if="err.error_messages?.length" class="ce-messages">
              <li v-for="(msg, i) in err.error_messages" :key="i">{{ msg }}</li>
            </ul>

            <div v-if="err.completed_at" class="ce-completed-meta">
              Marked complete by {{ err.completed_by_name || 'Unknown' }} · {{ formatDate(err.completed_at) }}
            </div>

            <div class="ce-card__actions">
              <HmsButton
                v-if="err.ghims_import_item_id"
                variant="secondary"
                size="sm"
                @click="editGhimsImportItem(err.ghims_import_item_id)"
              >
                Fix in GHIMS import
              </HmsButton>
              <HmsButton
                v-if="err.claim_id"
                variant="primary"
                size="sm"
                @click="editClaim(err.claim_id)"
              >
                Edit claim
              </HmsButton>
              <HmsButton
                v-if="!err.claim_id && !err.ghims_import_item_id"
                variant="ghost"
                size="sm"
                disabled
              >
                Claim not found
              </HmsButton>
              <label v-if="rowExportTarget(err)" class="ce-export-check">
                <q-checkbox
                  dense
                  :model-value="isRowExportSelected(err)"
                  @update:model-value="toggleRowExport(err, $event)"
                />
                <span>Export</span>
              </label>
              <HmsButton
                :variant="err.completed_at ? 'ghost' : 'healthcare'"
                size="sm"
                :loading="completingErrorId === err.id"
                :disabled="!err.completed_at && !rowIsExportReady(err)"
                @click="toggleCompleted(err)"
              >
                {{ err.completed_at ? 'Mark not completed' : 'Mark completed' }}
              </HmsButton>
            </div>
          </div>
        </motion.article>
      </div>

      <div v-if="paginatedErrors.length && filteredErrors.length > rowsPerPage" class="ce-pager-foot">
        <q-pagination
          v-model="paginationPage"
          :max="paginationMaxPages"
          :max-pages="7"
          direction-links
          boundary-links
          color="primary"
        />
      </div>
    </template>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useQuasar } from 'quasar';
import { motion } from 'motion-v';
import { usePreferredReducedMotion } from '@vueuse/core';
import { claimsAPI } from '../services/api';
import { setClaimsNavIds, setGhimsNavIds } from '../utils/claimNav';
import { isClaimExportable, statusLabel } from '../utils/claimVetting';
import { parseExportErrorDetail, exportErrorMessage } from '../utils/exportErrorDetail';
import HmsPageHeader from '../components/ui/HmsPageHeader.vue';
import HmsButton from '../components/ui/HmsButton.vue';

const STORAGE_KEY = 'claimit_batch_selections';

const $route = useRoute();
const $router = useRouter();
const $q = useQuasar();
const preferredReducedMotion = usePreferredReducedMotion();
const reduceMotion = computed(() => preferredReducedMotion.value === 'reduce');

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

const batchStats = computed(() => {
  const list = batchErrors.value || [];
  let errors = 0;
  let warnings = 0;
  let completed = 0;
  for (const e of list) {
    if (e.outcome === 'ERROR') errors += 1;
    else if (e.outcome === 'WARNING') warnings += 1;
    if (e.completed_at) completed += 1;
  }
  return { total: list.length, errors, warnings, completed };
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

<style scoped>
.ce-page {
  position: relative;
  isolation: isolate;
  color: var(--hms-text-primary);
  font-family: var(--hms-font-sans);
}

.ce-atmosphere {
  pointer-events: none;
  position: absolute;
  inset: 0;
  z-index: -1;
  background:
    radial-gradient(780px 320px at 6% -10%, color-mix(in srgb, var(--hms-accent) 16%, transparent), transparent 58%),
    radial-gradient(560px 280px at 100% 0%, color-mix(in srgb, var(--hms-healthcare) 11%, transparent), transparent 55%);
}

.ce-panel {
  margin-bottom: 1rem;
  border: 1px solid var(--hms-border);
  border-radius: var(--hms-radius-2xl, 1.15rem);
  background: var(--hms-panel-bg);
  box-shadow: var(--hms-shadow-md);
  padding: 1.15rem 1.25rem 1.3rem;
}

.ce-panel__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1.05rem;
}

.ce-kicker {
  font-size: var(--hms-text-xs);
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--hms-text-muted);
  font-weight: 650;
}

.ce-panel__title {
  margin: 0.28rem 0 0;
  font-size: var(--hms-text-xl);
  font-weight: 700;
  letter-spacing: var(--hms-tracking-tight, -0.02em);
  color: var(--hms-text-primary);
}

.ce-lede {
  margin: 0.4rem 0 0;
  max-width: 42rem;
  font-size: var(--hms-text-sm);
  color: var(--hms-text-secondary);
  line-height: 1.45;
}

.ce-muted { color: var(--hms-text-muted); }
.ce-count {
  flex-shrink: 0;
  min-width: 1.75rem;
  text-align: center;
  font-size: var(--hms-text-sm);
  font-weight: 700;
  padding: 0.25rem 0.55rem;
  border-radius: 999px;
  background: color-mix(in srgb, var(--hms-text-muted) 12%, transparent);
  color: var(--hms-text-secondary);
}

.ce-upload-grid {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}

.ce-check {
  display: flex;
  align-items: flex-start;
  gap: 0.45rem;
  font-size: var(--hms-text-sm);
  color: var(--hms-text-primary);
  cursor: pointer;
}

.ce-upload-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem;
}

.ce-field { max-width: 40rem; }
.ce-field--file { flex: 1 1 16rem; min-width: 14rem; max-width: 28rem; }

.ce-batch-list {
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
}

.ce-batch-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.85rem;
  flex-wrap: wrap;
  padding: 0.9rem 1rem;
  border: 1px solid var(--hms-border);
  border-radius: var(--hms-radius-xl);
  background: var(--hms-surface, transparent);
  transition: border-color var(--hms-duration-fast, 150ms) var(--hms-ease-out, ease),
    box-shadow var(--hms-duration-fast, 150ms) var(--hms-ease-out, ease),
    transform var(--hms-duration-fast, 150ms) var(--hms-ease-out, ease);
}

.ce-batch-row:hover {
  border-color: color-mix(in srgb, var(--hms-accent) 35%, var(--hms-border));
  box-shadow: var(--hms-shadow-sm, 0 1px 2px rgba(0, 0, 0, 0.04));
  transform: translateY(-1px);
}

.ce-batch-row__name {
  font-weight: 700;
  font-size: var(--hms-text-sm);
  color: var(--hms-text-primary);
}

.ce-batch-row__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.35rem;
  margin-top: 0.28rem;
  font-size: var(--hms-text-xs);
  color: var(--hms-text-muted);
}

.ce-dot {
  width: 3px;
  height: 3px;
  border-radius: 50%;
  background: var(--hms-text-muted);
  opacity: 0.7;
}

.ce-batch-row__actions {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  flex-wrap: wrap;
}

.ce-empty {
  padding: 1.5rem 0.25rem 0.5rem;
  text-align: left;
}

.ce-empty--panel {
  margin-bottom: 1rem;
  padding: 1.5rem 1.2rem;
  border: 1px dashed var(--hms-border);
  border-radius: var(--hms-radius-xl);
  background: color-mix(in srgb, var(--hms-surface) 70%, transparent);
}

.ce-empty__title {
  font-weight: 700;
  font-size: var(--hms-text-base);
  margin-bottom: 0.25rem;
}

.ce-kpi-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 0.65rem;
  margin-bottom: 1rem;
}

@media (max-width: 1100px) {
  .ce-kpi-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}
@media (max-width: 640px) {
  .ce-kpi-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

.ce-kpi {
  border: 1px solid var(--hms-border);
  border-radius: var(--hms-radius-xl);
  background: var(--hms-panel-bg);
  padding: 0.85rem 0.95rem;
  box-shadow: var(--hms-shadow-sm, none);
}

.ce-kpi__label {
  font-size: 0.7rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-weight: 650;
  color: var(--hms-text-muted);
}

.ce-kpi__value {
  margin-top: 0.35rem;
  font-size: 1.45rem;
  font-weight: 750;
  letter-spacing: var(--hms-tracking-tight, -0.02em);
  color: var(--hms-text-primary);
  font-variant-numeric: tabular-nums;
}

.ce-kpi[data-tone='critical'] .ce-kpi__value { color: var(--hms-critical); }
.ce-kpi[data-tone='warning'] .ce-kpi__value { color: var(--hms-warning); }
.ce-kpi[data-tone='success'] .ce-kpi__value { color: var(--hms-success); }
.ce-kpi[data-tone='accent'] .ce-kpi__value { color: var(--hms-accent); }

.ce-callout {
  display: flex;
  gap: 0.75rem;
  align-items: flex-start;
  margin-bottom: 0.85rem;
  padding: 0.95rem 1.05rem;
  border-radius: var(--hms-radius-xl);
  border: 1px solid var(--hms-border);
  background: var(--hms-panel-bg);
}

.ce-callout__title {
  font-weight: 700;
  font-size: var(--hms-text-sm);
  margin-bottom: 0.2rem;
}

.ce-callout p {
  margin: 0;
  font-size: var(--hms-text-sm);
  color: var(--hms-text-secondary);
  line-height: 1.45;
}

.ce-callout__body {
  display: flex;
  flex: 1;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
}

.ce-callout[data-tone='ok'] {
  border-color: color-mix(in srgb, var(--hms-success) 35%, var(--hms-border));
  background: color-mix(in srgb, var(--hms-success) 8%, var(--hms-panel-bg));
}
.ce-callout[data-tone='warn'] {
  border-color: color-mix(in srgb, var(--hms-warning) 40%, var(--hms-border));
  background: color-mix(in srgb, var(--hms-warning) 10%, var(--hms-panel-bg));
}
.ce-callout[data-tone='link'] {
  border-color: color-mix(in srgb, var(--hms-healthcare) 35%, var(--hms-border));
  background: color-mix(in srgb, var(--hms-healthcare) 8%, var(--hms-panel-bg));
}
.ce-callout[data-tone='info'] {
  border-color: color-mix(in srgb, var(--hms-info, var(--hms-accent)) 30%, var(--hms-border));
  background: color-mix(in srgb, var(--hms-info, var(--hms-accent)) 8%, var(--hms-panel-bg));
}

.ce-inline-link {
  color: var(--hms-accent);
  font-weight: 650;
  text-decoration: none;
}
.ce-inline-link:hover { text-decoration: underline; }

.ce-toolbar__top {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
  margin-bottom: 1rem;
}

.ce-toolbar__title {
  margin-top: 0.2rem;
  font-size: var(--hms-text-base);
  color: var(--hms-text-primary);
}

.ce-toolbar__filters {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 0.85rem 1.1rem;
}

.ce-filter-block {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.ce-filter-block--actions {
  flex-direction: row;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.65rem;
  padding-bottom: 0.15rem;
}

.ce-filter-block--pager {
  margin-left: auto;
  flex-direction: row;
  align-items: center;
  gap: 0.55rem;
}

.ce-filter-label {
  font-size: 0.68rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  font-weight: 650;
  color: var(--hms-text-muted);
}

.ce-seg :deep(.q-btn) {
  font-weight: 600;
  min-height: 2rem;
}

.ce-rows { min-width: 4.5rem; width: 4.5rem; }

.ce-cards {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.ce-card {
  position: relative;
  display: grid;
  grid-template-columns: 4px minmax(0, 1fr);
  border: 1px solid var(--hms-border);
  border-radius: var(--hms-radius-2xl, 1.15rem);
  background: var(--hms-panel-bg);
  box-shadow: var(--hms-shadow-md);
  overflow: hidden;
  transition: border-color var(--hms-duration-fast, 150ms) ease,
    box-shadow var(--hms-duration-fast, 150ms) ease;
}

.ce-card:hover {
  border-color: color-mix(in srgb, var(--hms-accent) 28%, var(--hms-border));
}

.ce-card__rail {
  background: var(--hms-text-muted);
}

.ce-card[data-outcome='ERROR'] .ce-card__rail {
  background: var(--hms-critical);
}

.ce-card[data-outcome='WARNING'] .ce-card__rail {
  background: var(--hms-warning);
}

.ce-card[data-done='1'] {
  background: color-mix(in srgb, var(--hms-success) 5%, var(--hms-panel-bg));
}

.ce-card__body { padding: 1rem 1.1rem 1.05rem; }

.ce-card__top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.85rem;
  flex-wrap: wrap;
}

.ce-card__identity {
  display: flex;
  align-items: flex-start;
  gap: 0.7rem;
}

.ce-index {
  width: 1.55rem;
  height: 1.55rem;
  display: grid;
  place-items: center;
  border-radius: 999px;
  font-size: var(--hms-text-xs);
  font-weight: 700;
  color: var(--hms-text-muted);
  background: var(--hms-surface);
  border: 1px solid var(--hms-border);
}

.ce-claim-id {
  font-family: var(--hms-font-mono, ui-monospace, monospace);
  font-weight: 700;
  font-size: var(--hms-text-sm);
  letter-spacing: 0.01em;
}

.ce-card__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
}

.ce-sev {
  font-size: 0.68rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  font-weight: 700;
  padding: 0.22rem 0.5rem;
  border-radius: 999px;
  background: var(--hms-surface);
  color: var(--hms-text-muted);
  border: 1px solid var(--hms-border);
}

.ce-sev[data-sev='critical'] {
  color: var(--hms-critical);
  background: var(--hms-critical-muted, color-mix(in srgb, var(--hms-critical) 14%, transparent));
  border-color: color-mix(in srgb, var(--hms-critical) 30%, var(--hms-border));
}

.ce-sev[data-sev='warning'] {
  color: var(--hms-warning);
  background: color-mix(in srgb, var(--hms-warning) 14%, transparent);
  border-color: color-mix(in srgb, var(--hms-warning) 30%, var(--hms-border));
}

.ce-sev[data-sev='ok'] {
  color: var(--hms-success);
  background: color-mix(in srgb, var(--hms-success) 12%, transparent);
  border-color: color-mix(in srgb, var(--hms-success) 30%, var(--hms-border));
}

.ce-messages {
  margin: 0.85rem 0 0;
  padding: 0.75rem 0.9rem 0.75rem 1.35rem;
  border-radius: var(--hms-radius-lg);
  background: var(--hms-surface);
  border: 1px solid var(--hms-border);
  list-style: disc;
}

.ce-messages li {
  font-size: var(--hms-text-sm);
  color: var(--hms-text-secondary);
  line-height: 1.45;
}

.ce-messages li + li { margin-top: 0.35rem; }

.ce-completed-meta {
  margin-top: 0.65rem;
  font-size: var(--hms-text-xs);
  color: var(--hms-text-muted);
}

.ce-card__actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.95rem;
  padding-top: 0.85rem;
  border-top: 1px solid var(--hms-border);
}

.ce-export-check {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  font-size: var(--hms-text-sm);
  color: var(--hms-text-secondary);
  cursor: pointer;
  padding: 0.15rem 0.35rem;
  border-radius: var(--hms-radius-md, 8px);
}

.ce-status-warn {
  color: var(--hms-warning);
  font-weight: 650;
}

.ce-pager-foot {
  display: flex;
  justify-content: center;
  padding: 0.5rem 0 1rem;
}
</style>
