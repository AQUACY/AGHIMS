<template>
  <q-page class="hms-page aiv-page">
    <div class="aiv-atmosphere" aria-hidden="true" />

    <header
      class="aiv-hero"
    >
      <div class="aiv-hero__eyebrow">Claims intelligence</div>
      <h1 class="aiv-hero__title">AI Vetting</h1>
      <p class="aiv-hero__lede">
        Scan imported GHIMS claims for ClaimIT blockers, then approve corrections in one pass.
      </p>
      <div class="aiv-hero__actions">
        <button type="button" class="aiv-ghost" @click="$router.push('/claims')">← Claims home</button>
        <button
          v-if="moduleActive"
          type="button"
          class="aiv-ghost"
          @click="$router.push('/claims/ghims-import')"
        >
          Open imports
        </button>
      </div>
    </header>

    <section
      v-if="!moduleChecking && !moduleActive"
      class="aiv-panel aiv-panel--warn"
    >
      <div class="aiv-panel__kicker">Module inactive</div>
      <p class="aiv-copy">
        AI Claims Vetting is turned off for this facility. Enable it under Module Management → Claims.
      </p>
    </section>

    <template v-else-if="moduleActive">
      <div class="aiv-grid">
        <section
          class="aiv-panel"
        >
          <div class="aiv-panel__head">
            <div>
              <div class="aiv-panel__kicker">01 — Source</div>
              <h2 class="aiv-panel__title">Import batch</h2>
            </div>
            <button type="button" class="aiv-ghost aiv-ghost--sm" :disabled="loadingBatches" @click="loadBatches">
              Refresh
            </button>
          </div>

          <div v-if="loadingBatches" class="aiv-muted">Loading imports…</div>
          <div v-else-if="!batches.length" class="aiv-muted">
            No GHIMS imports yet. Upload XML under Import GHIMS XML first.
          </div>
          <div v-else class="aiv-batch-list">
            <button
              v-for="b in batches"
              :key="b.id"
              type="button"
              class="aiv-batch"
              :class="{ 'aiv-batch--active': selectedBatchId === b.id }"
              @click="selectBatch(b.id)"
            >
              <div class="aiv-batch__name">{{ b.file_name }}</div>
              <div class="aiv-batch__meta">
                {{ formatDate(b.uploaded_at) }} · {{ b.claim_count || 0 }} claims
                · {{ b.finalized_count || 0 }} finalized
              </div>
            </button>
          </div>
        </section>

        <section
          class="aiv-panel"
        >
          <div class="aiv-panel__head">
            <div>
              <div class="aiv-panel__kicker">02 — Scope</div>
              <h2 class="aiv-panel__title">What to scan</h2>
            </div>
          </div>

          <div v-if="!selectedBatchId" class="aiv-muted">Select an import batch to continue.</div>
          <template v-else>
            <div class="aiv-scope-row">
              <label class="aiv-radio">
                <input v-model="scopeMode" type="radio" value="all" />
                <span>All claims (including finalized)</span>
              </label>
              <label class="aiv-radio">
                <input v-model="scopeMode" type="radio" value="open" />
                <span>All non-finalized only</span>
              </label>
              <label class="aiv-radio">
                <input v-model="scopeMode" type="radio" value="selected" />
                <span>Selected claims only</span>
              </label>
            </div>
            <p v-if="scopeMode === 'all'" class="aiv-muted q-mt-sm">
              Finalized claims are scanned for the report. Applying corrections still requires reopening those claims first.
            </p>

            <div v-if="loadingClaims" class="aiv-muted q-mt-md">Loading claims…</div>
            <div v-else-if="scopeMode === 'selected'" class="aiv-claim-picker q-mt-md">
              <div class="aiv-picker-bar">
                <span class="aiv-muted">{{ selectedClaimIds.length }} selected</span>
                <button type="button" class="aiv-ghost aiv-ghost--sm" @click="selectAllClaims">Select all</button>
                <button type="button" class="aiv-ghost aiv-ghost--sm" @click="selectAllScannable">Non-finalized</button>
                <button type="button" class="aiv-ghost aiv-ghost--sm" @click="selectedClaimIds = []">Clear</button>
              </div>
              <div class="aiv-claim-scroll">
                <label
                  v-for="row in batchClaims"
                  :key="row.id"
                  class="aiv-claim-row"
                >
                  <input
                    type="checkbox"
                    :checked="selectedClaimIds.includes(row.id)"
                    @change="toggleClaim(row.id, $event.target.checked)"
                  />
                  <span class="mono">{{ row.claim_claim_id || row.id }}</span>
                  <span class="aiv-claim-row__name">{{ clientName(row) }}</span>
                  <span class="aiv-pill">{{ row.status }}</span>
                </label>
                <div v-if="!batchClaims.length" class="aiv-muted">No claims in this batch.</div>
              </div>
            </div>

            <div class="aiv-cta-row">
              <button
                type="button"
                class="aiv-primary"
                :disabled="starting || jobRunning || (scopeMode === 'selected' && !selectedClaimIds.length)"
                @click="startAnalyze"
              >
                <span v-if="starting || jobRunning" class="aiv-spinner" />
                {{ runLabel }}
              </button>
              <button
                type="button"
                class="aiv-ghost"
                :disabled="!selectedBatchId || loadingReport"
                @click="loadReport"
              >
                Refresh report
              </button>
            </div>
          </template>
        </section>
      </div>

      <section
        v-if="job"
        class="aiv-panel aiv-progress"
      >
        <div class="aiv-progress__top">
          <span class="aiv-status" :data-status="job.status">Job #{{ job.id }} · {{ job.status }}</span>
          <span class="aiv-muted">
            {{ job.processed_items }}/{{ job.total_items }}
            <template v-if="job.findings_count != null"> · {{ job.findings_count }} findings</template>
          </span>
        </div>
        <div class="aiv-progress__track">
          <div class="aiv-progress__fill" :style="{ width: `${job.progress_pct || 0}%` }" />
        </div>
        <p v-if="job.error_message" class="aiv-error">{{ job.error_message }}</p>
      </section>

      <p v-if="error" class="aiv-error aiv-error--banner">{{ error }}</p>

      <section
        class="aiv-panel aiv-report"
      >
        <div class="aiv-panel__head">
          <div>
            <div class="aiv-panel__kicker">03 — Report</div>
            <h2 class="aiv-panel__title">
              Findings
              <span v-if="report" class="aiv-count">{{ report.pending_total || 0 }}</span>
            </h2>
          </div>
          <div v-if="selectedIds.length" class="aiv-bulk-bar">
            <span>{{ selectedIds.length }} selected</span>
            <button type="button" class="aiv-primary aiv-primary--sm" :disabled="correcting" @click="bulkCorrect(null, [...selectedIds])">
              Correct selected
            </button>
            <button type="button" class="aiv-ghost aiv-ghost--sm" :disabled="correcting" @click="bulkReject([...selectedIds])">
              Reject
            </button>
          </div>
        </div>

        <div v-if="!selectedBatchId" class="aiv-muted">Choose a batch to load or generate a report.</div>
        <div v-else-if="loadingReport && !report" class="aiv-muted">Loading report…</div>
        <div v-else-if="report && report.pending_total === 0 && !jobRunning" class="aiv-empty">
          <div class="aiv-empty__mark">✓</div>
          <div>No pending Phase-1 issues for this batch.</div>
        </div>

        <div v-for="group in reportGroups" :key="group.rule_code" class="aiv-group">
          <div class="aiv-group__head">
            <div>
              <h3 class="aiv-group__title">{{ group.label }}</h3>
              <div class="aiv-muted">{{ group.pending_count }} claim(s)</div>
            </div>
            <div class="aiv-group__actions">
              <label class="aiv-check-all">
                <input
                  type="checkbox"
                  :checked="isGroupFullySelected(group)"
                  :indeterminate.prop="isGroupPartiallySelected(group)"
                  @change="toggleGroup(group, $event.target.checked)"
                />
                Select all
              </label>
              <button
                type="button"
                class="aiv-primary aiv-primary--sm"
                :disabled="!selectedInGroup(group).length || correcting"
                @click="bulkCorrect(group.rule_code, selectedInGroup(group))"
              >
                Correct {{ selectedInGroup(group).length || '' }}
              </button>
            </div>
          </div>

          <div class="aiv-table-wrap">
            <table class="aiv-table">
              <thead>
                <tr>
                  <th></th>
                  <th>Claim</th>
                  <th>Client</th>
                  <th>Member</th>
                  <th>Specialty</th>
                  <th>Finding</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in group.findings" :key="row.id">
                  <td>
                    <input
                      type="checkbox"
                      :checked="selectedIds.includes(row.id)"
                      @change="toggleFinding(row.id, $event.target.checked)"
                    />
                  </td>
                  <td class="mono">{{ row.claim_claim_id || '—' }}</td>
                  <td>{{ row.client_name || '—' }}</td>
                  <td class="mono">{{ row.member_no || '—' }}</td>
                  <td>{{ row.specialty_attended || '—' }}</td>
                  <td>
                    <div class="aiv-finding">{{ row.finding }}</div>
                    <div class="aiv-muted">{{ row.recommendation }}</div>
                  </td>
                  <td class="aiv-table__end">
                    <button
                      type="button"
                      class="aiv-ghost aiv-ghost--sm"
                      :disabled="!row.source_id"
                      @click="openClaim(row.source_id)"
                    >
                      Open
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </template>
  </q-page>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue';
import { useQuasar } from 'quasar';
import { useRouter } from 'vue-router';
import { claimsAPI, aiClaimVettingAPI, moduleSettingsAPI } from '../services/api';

const $q = useQuasar();
const $router = useRouter();

const moduleChecking = ref(true);
const moduleActive = ref(false);
const batches = ref([]);
const loadingBatches = ref(false);
const selectedBatchId = ref(null);
const batchClaims = ref([]);
const loadingClaims = ref(false);
const scopeMode = ref('all'); // all | open | selected
const selectedClaimIds = ref([]);

const starting = ref(false);
const loadingReport = ref(false);
const correcting = ref(false);
const error = ref('');
const job = ref(null);
const report = ref(null);
const selectedIds = ref([]);
let pollTimer = null;

const jobRunning = computed(() => ['queued', 'running'].includes(job.value?.status));

const scannableClaims = computed(() =>
  (batchClaims.value || []).filter((r) => String(r.status || '') !== 'finalized')
);

const runLabel = computed(() => {
  if (starting.value || jobRunning.value) return 'Scanning…';
  if (scopeMode.value === 'selected') {
    const n = selectedClaimIds.value.length;
    return n ? `Run AI on ${n} selected` : 'Select claims to scan';
  }
  if (scopeMode.value === 'open') return 'Run AI on non-finalized';
  return 'Run AI on all claims';
});

const reportGroups = computed(() => report.value?.groups || []);

const RULE_LABELS = {
  specialty_zoom: 'ZOOM specialty → OPDC',
  ghana_card_member_no: 'Ghana Card Member No → HIN',
};

function formatDate(value) {
  if (!value) return '—';
  try {
    return new Date(value).toLocaleString();
  } catch {
    return String(value);
  }
}

function clientName(row) {
  const p = row.payload || {};
  const parts = [p.otherNames, p.surname].map((x) => String(x || '').trim()).filter(Boolean);
  return parts.join(' ') || row.client_name || '—';
}

function stopPoll() {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
}

async function checkModule() {
  moduleChecking.value = true;
  try {
    const res = await moduleSettingsAPI.getStatus('ai_claims_vetting');
    moduleActive.value = !!res.data?.is_active;
  } catch {
    moduleActive.value = false;
  } finally {
    moduleChecking.value = false;
  }
}

async function loadBatches() {
  loadingBatches.value = true;
  try {
    const res = await claimsAPI.getGhimsImportBatches();
    batches.value = res.data || [];
  } catch (e) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Failed to load imports' });
  } finally {
    loadingBatches.value = false;
  }
}

async function selectBatch(id) {
  selectedBatchId.value = id;
  selectedClaimIds.value = [];
  selectedIds.value = [];
  report.value = null;
  job.value = null;
  stopPoll();
  await loadBatchClaims(id);
  await loadReport();
}

async function loadBatchClaims(id) {
  loadingClaims.value = true;
  try {
    const res = await claimsAPI.getGhimsImportBatch(id);
    batchClaims.value = res.data?.claims || [];
  } catch (e) {
    batchClaims.value = [];
    $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Failed to load batch claims' });
  } finally {
    loadingClaims.value = false;
  }
}

function toggleClaim(id, checked) {
  if (checked && !selectedClaimIds.value.includes(id)) selectedClaimIds.value.push(id);
  if (!checked) selectedClaimIds.value = selectedClaimIds.value.filter((x) => x !== id);
}

function selectAllScannable() {
  selectedClaimIds.value = scannableClaims.value.map((r) => r.id);
}

function selectAllClaims() {
  selectedClaimIds.value = (batchClaims.value || []).map((r) => r.id);
}

async function loadReport() {
  if (!selectedBatchId.value) return;
  loadingReport.value = true;
  error.value = '';
  try {
    const res = await aiClaimVettingAPI.getBatchReport(selectedBatchId.value);
    report.value = res.data || null;
    if (res.data?.latest_job) job.value = res.data.latest_job;
    const alive = new Set(
      (res.data?.groups || []).flatMap((g) => (g.findings || []).map((f) => f.id))
    );
    selectedIds.value = selectedIds.value.filter((id) => alive.has(id));
  } catch (e) {
    if (e.response?.status === 403) moduleActive.value = false;
    else error.value = e.response?.data?.detail || e.message || 'Failed to load report';
  } finally {
    loadingReport.value = false;
  }
}

async function pollJob(jobId) {
  stopPoll();
  pollTimer = setInterval(async () => {
    try {
      const res = await aiClaimVettingAPI.getJob(jobId);
      job.value = res.data;
      if (!['queued', 'running'].includes(res.data?.status)) {
        stopPoll();
        await loadReport();
        if (res.data?.status === 'completed') {
          $q.notify({
            type: res.data.findings_count ? 'warning' : 'positive',
            message: res.data.findings_count
              ? `Scan complete — ${res.data.findings_count} finding(s)`
              : 'Scan complete — no Phase-1 issues',
            position: 'top',
          });
        } else if (res.data?.status === 'failed') {
          $q.notify({ type: 'negative', message: res.data.error_message || 'Scan failed', position: 'top' });
        }
      }
    } catch {
      stopPoll();
    }
  }, 1200);
}

async function startAnalyze() {
  if (!selectedBatchId.value) return;
  starting.value = true;
  error.value = '';
  try {
    let itemIds = null;
    let includeFinalized = false;
    if (scopeMode.value === 'selected') {
      itemIds = selectedClaimIds.value.map((x) => Number(x)).filter(Boolean);
    } else if (scopeMode.value === 'all') {
      includeFinalized = true;
    }
    const res = await aiClaimVettingAPI.startBatchAnalyze(selectedBatchId.value, {
      item_ids: itemIds && itemIds.length ? itemIds : null,
      include_finalized: includeFinalized,
    });
    job.value = res.data;
    $q.notify({
      type: 'info',
      message: `Scanning ${res.data.total_items} claim(s) in the background…`,
      position: 'top',
    });
    await pollJob(res.data.id);
  } catch (e) {
    error.value = e.response?.data?.detail || e.message || 'Failed to start scan';
    $q.notify({ type: 'negative', message: error.value, position: 'top' });
  } finally {
    starting.value = false;
  }
}

function selectedInGroup(group) {
  const ids = new Set(selectedIds.value);
  return (group.findings || []).filter((f) => ids.has(f.id)).map((f) => f.id);
}

function isGroupFullySelected(group) {
  const rows = group.findings || [];
  return rows.length > 0 && rows.every((f) => selectedIds.value.includes(f.id));
}

function isGroupPartiallySelected(group) {
  const rows = group.findings || [];
  const n = rows.filter((f) => selectedIds.value.includes(f.id)).length;
  return n > 0 && n < rows.length;
}

function toggleGroup(group, checked) {
  const ids = (group.findings || []).map((f) => f.id);
  if (checked) selectedIds.value = Array.from(new Set([...selectedIds.value, ...ids]));
  else {
    const remove = new Set(ids);
    selectedIds.value = selectedIds.value.filter((id) => !remove.has(id));
  }
}

function toggleFinding(id, checked) {
  if (checked && !selectedIds.value.includes(id)) selectedIds.value.push(id);
  if (!checked) selectedIds.value = selectedIds.value.filter((x) => x !== id);
}

function openClaim(itemId) {
  if (!itemId) return;
  const route = $router.resolve({ path: `/claims/ghims-import/item/${itemId}` });
  window.open(route.href, '_blank');
}

async function bulkCorrect(ruleCode, findingIds) {
  if (!findingIds?.length) return;
  const isHin =
    ruleCode === 'ghana_card_member_no' ||
    (!ruleCode &&
      (report.value?.groups || []).some(
        (g) =>
          g.rule_code === 'ghana_card_member_no' &&
          g.findings.some((f) => findingIds.includes(f.id))
      ));

  const ok = await new Promise((resolve) => {
    $q.dialog({
      title: 'Apply corrections',
      message: isHin
        ? `Correct ${findingIds.length} finding(s)? Ghana Card rows call NHIA for HIN and may take a while.`
        : `Correct ${findingIds.length} finding(s)?`,
      cancel: true,
      persistent: true,
    })
      .onOk(() => resolve(true))
      .onCancel(() => resolve(false))
      .onDismiss(() => resolve(false));
  });
  if (!ok) return;

  correcting.value = true;
  try {
    const res = await aiClaimVettingAPI.bulkDecideFindings({
      finding_ids: findingIds,
      decision: 'accept',
    });
    const data = res.data || {};
    $q.notify({
      type: data.fail_count ? 'warning' : 'positive',
      message: data.message || `Corrected ${data.ok_count || 0}`,
      position: 'top',
      timeout: 5000,
    });
    selectedIds.value = selectedIds.value.filter((id) => !findingIds.includes(id));
    await loadReport();
  } catch (e) {
    $q.notify({
      type: 'negative',
      message: e.response?.data?.detail || e.message || 'Bulk correct failed',
      position: 'top',
    });
  } finally {
    correcting.value = false;
  }
}

async function bulkReject(findingIds) {
  if (!findingIds?.length) return;
  correcting.value = true;
  try {
    const res = await aiClaimVettingAPI.bulkDecideFindings({
      finding_ids: findingIds,
      decision: 'reject',
      note: 'Rejected from AI Vetting console',
    });
    $q.notify({ type: 'positive', message: res.data?.message || 'Rejected', position: 'top' });
    selectedIds.value = selectedIds.value.filter((id) => !findingIds.includes(id));
    await loadReport();
  } catch (e) {
    $q.notify({
      type: 'negative',
      message: e.response?.data?.detail || e.message || 'Bulk reject failed',
      position: 'top',
    });
  } finally {
    correcting.value = false;
  }
}

watch(scopeMode, () => {
  if (scopeMode.value !== 'selected') selectedClaimIds.value = [];
});

onMounted(async () => {
  await checkModule();
  if (moduleActive.value) await loadBatches();
});

onBeforeUnmount(stopPoll);
</script>

<style scoped>
.aiv-page {
  position: relative;
  isolation: isolate;
  color: var(--hms-text-primary);
  font-family: var(--hms-font-sans);
}

.aiv-atmosphere {
  pointer-events: none;
  position: absolute;
  inset: 0;
  z-index: -1;
  background:
    radial-gradient(820px 360px at 8% -8%, color-mix(in srgb, var(--hms-accent) 18%, transparent), transparent 58%),
    radial-gradient(640px 320px at 96% 0%, color-mix(in srgb, var(--hms-healthcare) 12%, transparent), transparent 52%);
}

.aiv-atmosphere::after {
  content: '';
  position: absolute;
  inset: 0;
  opacity: 0.28;
  background-image:
    linear-gradient(color-mix(in srgb, var(--hms-border-strong) 55%, transparent) 1px, transparent 1px),
    linear-gradient(90deg, color-mix(in srgb, var(--hms-border-strong) 55%, transparent) 1px, transparent 1px);
  background-size: 48px 48px;
  mask-image: linear-gradient(180deg, #000 0%, transparent 78%);
}

.aiv-hero {
  margin-bottom: 1.35rem;
  max-width: 42rem;
}

.aiv-hero__eyebrow {
  font-size: var(--hms-text-xs);
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--hms-accent);
  font-weight: 650;
}

.aiv-hero__title {
  margin: 0.3rem 0 0;
  font-size: clamp(1.85rem, 3.5vw, 2.55rem);
  font-weight: 750;
  letter-spacing: var(--hms-tracking-tight);
  line-height: var(--hms-leading-tight);
  color: var(--hms-text-primary);
}

.aiv-hero__lede {
  margin: 0.65rem 0 0;
  color: var(--hms-text-secondary);
  font-size: var(--hms-text-base);
  line-height: var(--hms-leading-relaxed);
  max-width: 34rem;
}

.aiv-hero__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.65rem;
  margin-top: 1rem;
}

.aiv-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
  margin-bottom: 1rem;
}

@media (max-width: 960px) {
  .aiv-grid { grid-template-columns: 1fr; }
}

.aiv-panel {
  border: 1px solid var(--hms-border);
  background: var(--hms-panel-bg);
  border-radius: var(--hms-radius-2xl);
  padding: 1.15rem 1.2rem 1.25rem;
  box-shadow: var(--hms-shadow-md);
}

.aiv-panel--warn {
  border-color: color-mix(in srgb, var(--hms-warning) 45%, var(--hms-border));
}

.aiv-panel__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1rem;
}

.aiv-panel__kicker {
  font-size: var(--hms-text-xs);
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--hms-text-muted);
  font-weight: 650;
}

.aiv-panel__title {
  margin: 0.25rem 0 0;
  font-size: var(--hms-text-xl);
  font-weight: 700;
  letter-spacing: var(--hms-tracking-tight);
  color: var(--hms-text-primary);
}

.aiv-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 1.55rem;
  height: 1.55rem;
  margin-left: 0.4rem;
  padding: 0 0.4rem;
  border-radius: var(--hms-radius-full);
  font-size: var(--hms-text-xs);
  background: var(--hms-accent-muted);
  color: var(--hms-accent);
  vertical-align: middle;
}

.aiv-copy,
.aiv-muted {
  color: var(--hms-text-muted);
  font-size: var(--hms-text-sm);
  line-height: var(--hms-leading-normal);
}

.aiv-batch-list {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  max-height: 320px;
  overflow: auto;
}

.aiv-batch {
  text-align: left;
  border: 1px solid transparent;
  background: var(--hms-surface);
  color: var(--hms-text-primary);
  border-radius: var(--hms-radius-lg);
  padding: 0.75rem 0.85rem;
  cursor: pointer;
  transition: border-color var(--hms-duration-fast) var(--hms-ease-out),
    background var(--hms-duration-fast) var(--hms-ease-out),
    transform var(--hms-duration-fast) var(--hms-ease-out);
}

.aiv-batch:hover {
  background: var(--hms-surface-hover);
  transform: translateY(-1px);
}

.aiv-batch--active {
  border-color: color-mix(in srgb, var(--hms-accent) 55%, var(--hms-border));
  background: var(--hms-accent-muted);
}

.aiv-batch__name {
  font-weight: 650;
  font-size: var(--hms-text-base);
}

.aiv-batch__meta {
  margin-top: 0.2rem;
  font-size: var(--hms-text-xs);
  color: var(--hms-text-muted);
}

.aiv-scope-row {
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
}

.aiv-radio,
.aiv-check-all {
  display: inline-flex;
  align-items: center;
  gap: 0.55rem;
  cursor: pointer;
  font-size: var(--hms-text-sm);
  color: var(--hms-text-primary);
}

.aiv-claim-picker {
  border: 1px solid var(--hms-border);
  border-radius: var(--hms-radius-xl);
  overflow: hidden;
  background: var(--hms-surface);
}

.aiv-picker-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
  padding: 0.55rem 0.7rem;
  border-bottom: 1px solid var(--hms-border);
  background: var(--hms-bg-elevated);
}

.aiv-claim-scroll {
  max-height: 220px;
  overflow: auto;
}

.aiv-claim-row {
  display: grid;
  grid-template-columns: auto auto 1fr auto;
  gap: 0.65rem;
  align-items: center;
  padding: 0.55rem 0.75rem;
  border-bottom: 1px solid var(--hms-border);
  cursor: pointer;
  font-size: var(--hms-text-sm);
  color: var(--hms-text-primary);
}

.aiv-claim-row__name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.aiv-pill {
  font-size: 0.68rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--hms-text-muted);
}

.aiv-cta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.65rem;
  margin-top: 1.15rem;
}

.aiv-primary,
.aiv-ghost {
  appearance: none;
  border: none;
  cursor: pointer;
  font: inherit;
  border-radius: var(--hms-radius-full);
  padding: 0.65rem 1.1rem;
  transition: transform var(--hms-duration-fast) var(--hms-ease-out),
    opacity var(--hms-duration-fast) ease,
    background var(--hms-duration-fast) ease;
}

.aiv-primary {
  background: var(--hms-accent);
  color: var(--hms-text-inverse);
  font-weight: 700;
  box-shadow: var(--hms-shadow-glow-accent);
}

.aiv-primary:hover:not(:disabled) {
  background: var(--hms-accent-hover);
  transform: translateY(-1px);
}

.aiv-primary:disabled,
.aiv-ghost:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.aiv-primary--sm,
.aiv-ghost--sm {
  padding: 0.38rem 0.75rem;
  font-size: var(--hms-text-sm);
}

.aiv-ghost {
  background: transparent;
  color: var(--hms-text-primary);
  border: 1px solid var(--hms-border-strong);
}

.aiv-ghost:hover:not(:disabled) {
  background: var(--hms-surface-hover);
}

.aiv-spinner {
  display: inline-block;
  width: 0.85rem;
  height: 0.85rem;
  margin-right: 0.45rem;
  border: 2px solid color-mix(in srgb, var(--hms-text-inverse) 28%, transparent);
  border-top-color: var(--hms-text-inverse);
  border-radius: 50%;
  animation: aiv-spin 0.7s linear infinite;
  vertical-align: -2px;
}

@keyframes aiv-spin {
  to { transform: rotate(360deg); }
}

.aiv-progress__top {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 0.65rem;
  flex-wrap: wrap;
}

.aiv-status {
  font-size: var(--hms-text-sm);
  font-weight: 650;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--hms-text-secondary);
}

.aiv-status[data-status='completed'] { color: var(--hms-success); }
.aiv-status[data-status='failed'] { color: var(--hms-critical); }
.aiv-status[data-status='running'],
.aiv-status[data-status='queued'] { color: var(--hms-warning); }

.aiv-progress__track {
  height: 6px;
  border-radius: var(--hms-radius-full);
  background: var(--hms-surface);
  overflow: hidden;
}

.aiv-progress__fill {
  height: 100%;
  background: var(--hms-accent);
  transition: width var(--hms-duration-slow) var(--hms-ease-out);
}

.aiv-error {
  color: var(--hms-critical);
  font-size: var(--hms-text-sm);
  margin: 0.55rem 0 0;
}

.aiv-error--banner {
  margin: 0 0 1rem;
  padding: 0.75rem 1rem;
  border-radius: var(--hms-radius-lg);
  border: 1px solid color-mix(in srgb, var(--hms-critical) 40%, var(--hms-border));
  background: var(--hms-critical-muted);
}

.aiv-report { margin-top: 1rem; }

.aiv-bulk-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
  font-size: var(--hms-text-sm);
  color: var(--hms-text-muted);
}

.aiv-empty {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1.5rem 0.25rem;
  color: var(--hms-text-muted);
}

.aiv-empty__mark {
  width: 2rem;
  height: 2rem;
  border-radius: var(--hms-radius-full);
  display: grid;
  place-items: center;
  background: var(--hms-success-muted);
  color: var(--hms-success);
  font-weight: 700;
}

.aiv-group {
  margin-top: 1.35rem;
  padding-top: 1.1rem;
  border-top: 1px solid var(--hms-border);
}

.aiv-group__head {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
  margin-bottom: 0.75rem;
}

.aiv-group__title {
  margin: 0;
  font-size: var(--hms-text-lg);
  font-weight: 700;
  letter-spacing: var(--hms-tracking-tight);
  color: var(--hms-text-primary);
}

.aiv-group__actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.aiv-table-wrap {
  overflow: auto;
  border: 1px solid var(--hms-border);
  border-radius: var(--hms-radius-xl);
  background: var(--hms-surface);
}

.aiv-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--hms-text-sm);
}

.aiv-table th {
  text-align: left;
  padding: 0.65rem 0.75rem;
  font-size: var(--hms-text-xs);
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--hms-text-muted);
  background: var(--hms-bg-elevated);
  border-bottom: 1px solid var(--hms-border);
  white-space: nowrap;
}

.aiv-table td {
  padding: 0.7rem 0.75rem;
  border-bottom: 1px solid var(--hms-border);
  vertical-align: top;
  color: var(--hms-text-primary);
}

.aiv-table__end {
  text-align: right;
  white-space: nowrap;
}

.aiv-finding {
  font-weight: 600;
  margin-bottom: 0.15rem;
}

.mono {
  font-family: var(--hms-font-mono);
  font-size: 0.82em;
}
</style>
