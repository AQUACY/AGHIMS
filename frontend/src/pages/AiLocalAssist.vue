<template>
  <q-page class="hms-page aiv-page">
    <div class="aiv-atmosphere" aria-hidden="true" />

    <header class="aiv-hero">
      <div class="aiv-hero__eyebrow">Claims intelligence</div>
      <h1 class="aiv-hero__title">Local AI Assist</h1>
      <p class="aiv-hero__lede">
        Select a few imported claims and let the local model (Ollama) review them.
        You get recommendations only — nothing changes until you decide.
      </p>
      <div v-if="moduleActive" class="aiv-hero__status">
        <span class="aiv-chip" data-tone="ok">Human approval required</span>
        <span
          class="aiv-chip"
          :data-tone="aiStatus?.ollama_online ? 'ok' : 'warn'"
        >
          {{ aiEngineLabel }}
        </span>
        <span v-if="jobRunning" class="aiv-chip" data-tone="run">
          Reviewing… {{ job?.processed_items || 0 }}/{{ job?.total_items || 0 }}
        </span>
      </div>
      <div class="aiv-hero__actions">
        <button type="button" class="aiv-ghost" @click="$router.push('/claims')">← Claims home</button>
        <button type="button" class="aiv-ghost" @click="$router.push('/claims/ai-vetting')">
          Phase rules vetting
        </button>
        <button
          v-if="moduleActive"
          type="button"
          class="aiv-ghost"
          :disabled="loadingAiStatus"
          @click="loadAiStatus"
        >
          Refresh AI status
        </button>
      </div>
    </header>

    <section v-if="!moduleChecking && !moduleActive" class="aiv-panel aiv-panel--warn">
      <div class="aiv-panel__kicker">Module inactive</div>
      <p class="aiv-copy">
        AI Claims Vetting is turned off. Enable it under Module Management → Claims.
      </p>
    </section>

    <template v-else-if="moduleActive">
      <div class="aiv-grid">
        <section class="aiv-panel">
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
              </div>
            </button>
          </div>
        </section>

        <section class="aiv-panel">
          <div class="aiv-panel__head">
            <div>
              <div class="aiv-panel__kicker">02 — Assign</div>
              <h2 class="aiv-panel__title">Claims for local AI</h2>
            </div>
          </div>

          <div v-if="!selectedBatchId" class="aiv-muted">Select an import batch.</div>
          <template v-else>
            <p class="aiv-muted">
              Pick up to 10 claims. Each review can take ~30–90 seconds on the local model.
            </p>
            <div class="aiv-picker-bar">
              <span class="aiv-muted">{{ selectedClaimIds.length }} selected</span>
              <button type="button" class="aiv-ghost aiv-ghost--sm" @click="selectSample">Pick 3 open</button>
              <button type="button" class="aiv-ghost aiv-ghost--sm" @click="selectedClaimIds = []">Clear</button>
            </div>
            <div v-if="loadingClaims" class="aiv-muted">Loading claims…</div>
            <div v-else class="aiv-claim-scroll">
              <label v-for="row in batchClaims" :key="row.id" class="aiv-claim-row">
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

            <div class="aiv-cta-row">
              <button
                type="button"
                class="aiv-primary"
                :disabled="starting || jobRunning || !selectedClaimIds.length || !aiStatus?.ollama_online"
                @click="startAssist"
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
            <p v-if="aiStatus && !aiStatus.ollama_online" class="aiv-error q-mt-sm">
              Ollama is offline. Start Ollama on this machine, then refresh AI status.
            </p>
          </template>
        </section>
      </div>

      <section v-if="job" class="aiv-panel aiv-progress">
        <div class="aiv-progress__top">
          <span class="aiv-status" :data-status="job.status">
            Job #{{ job.id }} · {{ job.status }} · local AI
          </span>
          <span class="aiv-muted">
            {{ job.processed_items }}/{{ job.total_items }}
            <template v-if="job.findings_count != null"> · {{ job.findings_count }} findings</template>
          </span>
        </div>
        <div class="aiv-progress__track">
          <div class="aiv-progress__fill" :style="{ width: `${job.progress_pct || 0}%` }" />
        </div>
        <p v-if="jobRunning" class="aiv-muted q-mt-sm">
          Recommendations appear below as each claim finishes. Keep this page open.
        </p>
        <p v-if="job.error_message" class="aiv-error">{{ job.error_message }}</p>
      </section>

      <p v-if="error" class="aiv-error aiv-error--banner">{{ error }}</p>

      <section class="aiv-panel aiv-report">
        <div class="aiv-panel__head">
          <div>
            <div class="aiv-panel__kicker">03 — Recommendations</div>
            <h2 class="aiv-panel__title">
              Local AI report
              <span v-if="report" class="aiv-count">{{ report.pending_total || 0 }}</span>
            </h2>
          </div>
        </div>

        <div v-if="!selectedBatchId" class="aiv-muted">Choose a batch to begin.</div>
        <div v-else-if="loadingReport && !report" class="aiv-muted">Loading…</div>
        <div v-else-if="jobRunning && (!report || report.pending_total === 0)" class="aiv-muted">
          Local AI is reviewing claims
          ({{ job?.processed_items || 0 }}/{{ job?.total_items || 0 }})…
        </div>
        <div v-else-if="report && report.pending_total === 0 && !jobRunning" class="aiv-empty">
          <div class="aiv-empty__mark">✓</div>
          <div>No pending local-AI recommendations. Select claims and run a review.</div>
        </div>

        <div v-else-if="report && report.pending_total > 0" class="aiv-findings">
          <div v-for="group in report.groups" :key="group.rule_code" class="aiv-finding-group">
            <div class="aiv-finding-group__head">
              <h3>{{ group.label }}</h3>
              <span class="aiv-muted">{{ group.pending_count }} pending</span>
            </div>
            <article
              v-for="row in group.findings"
              :key="row.id"
              class="aiv-finding-card"
              :data-severity="row.severity"
            >
              <div class="aiv-finding-card__meta">
                <span class="mono">{{ row.claim_claim_id || row.source_id }}</span>
                <span>{{ row.client_name || '—' }}</span>
                <span class="aiv-pill">{{ row.severity }}</span>
              </div>
              <div class="aiv-finding-card__title">{{ row.finding }}</div>
              <p v-if="row.explanation" class="aiv-finding-card__body">{{ row.explanation }}</p>
              <p v-if="row.recommendation" class="aiv-finding-card__rec">
                Suggested: {{ row.recommendation }}
              </p>
              <div class="aiv-finding-card__actions">
                <button
                  type="button"
                  class="aiv-ghost aiv-ghost--sm"
                  :disabled="decidingId === row.id"
                  @click="decide(row, 'reject')"
                >
                  Dismiss
                </button>
                <button
                  type="button"
                  class="aiv-primary aiv-primary--sm"
                  :disabled="decidingId === row.id"
                  @click="decide(row, 'edited')"
                >
                  I'll edit manually
                </button>
                <button
                  type="button"
                  class="aiv-ghost aiv-ghost--sm"
                  @click="openClaim(row)"
                >
                  Open claim
                </button>
              </div>
            </article>
          </div>
        </div>
      </section>
    </template>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import { useQuasar } from 'quasar';
import { useRouter } from 'vue-router';
import { claimsAPI, aiClaimVettingAPI, moduleSettingsAPI } from '../services/api';

const $q = useQuasar();
const $router = useRouter();

const moduleChecking = ref(true);
const moduleActive = ref(false);
const aiStatus = ref(null);
const loadingAiStatus = ref(false);
const batches = ref([]);
const loadingBatches = ref(false);
const selectedBatchId = ref(null);
const batchClaims = ref([]);
const loadingClaims = ref(false);
const selectedClaimIds = ref([]);
const starting = ref(false);
const loadingReport = ref(false);
const report = ref(null);
const job = ref(null);
const error = ref('');
const decidingId = ref(null);
let pollTimer = null;

const jobRunning = computed(() => ['queued', 'running'].includes(job.value?.status));
const aiEngineLabel = computed(() => {
  const s = aiStatus.value;
  if (!s) return 'Checking local AI…';
  if (s.provider !== 'ollama') return 'Set AI_CLAIM_VETTING_PROVIDER=ollama in backend .env';
  const model = s.model || 'local model';
  return s.ollama_online ? `Online · ${model}` : `Offline · ${model}`;
});
const runLabel = computed(() => {
  if (starting.value || jobRunning.value) return 'Local AI reviewing…';
  const n = selectedClaimIds.value.length;
  if (!n) return 'Select claims to review';
  return `Run local AI on ${n} claim${n === 1 ? '' : 's'}`;
});

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

function toggleClaim(id, checked) {
  if (checked) {
    if (selectedClaimIds.value.length >= 10) {
      $q.notify({ type: 'warning', message: 'Max 10 claims for local AI assist', position: 'top' });
      return;
    }
    if (!selectedClaimIds.value.includes(id)) selectedClaimIds.value = [...selectedClaimIds.value, id];
  } else {
    selectedClaimIds.value = selectedClaimIds.value.filter((x) => x !== id);
  }
}

function selectSample() {
  const open = (batchClaims.value || [])
    .filter((r) => String(r.status || '') !== 'finalized')
    .slice(0, 3)
    .map((r) => r.id);
  selectedClaimIds.value = open;
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
  if (moduleActive.value) await loadAiStatus();
}

async function loadAiStatus() {
  loadingAiStatus.value = true;
  try {
    const res = await aiClaimVettingAPI.getStatus();
    aiStatus.value = res.data || null;
    if (typeof res.data?.module_active === 'boolean') moduleActive.value = res.data.module_active;
  } catch {
    aiStatus.value = null;
  } finally {
    loadingAiStatus.value = false;
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
  report.value = null;
  job.value = null;
  stopPoll();
  await Promise.all([loadClaims(), loadReport(), loadLatestJob()]);
}

async function loadClaims() {
  if (!selectedBatchId.value) return;
  loadingClaims.value = true;
  try {
    const res = await claimsAPI.getGhimsImportBatch(selectedBatchId.value);
    batchClaims.value = res.data?.claims || [];
  } catch (e) {
    batchClaims.value = [];
    $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Failed to load claims' });
  } finally {
    loadingClaims.value = false;
  }
}

async function loadLatestJob() {
  if (!selectedBatchId.value) return;
  try {
    const res = await aiClaimVettingAPI.getLatestBatchJob(selectedBatchId.value, { mode: 'llm' });
    if (res.data) {
      job.value = res.data;
      if (['queued', 'running'].includes(res.data.status)) await pollJob(res.data.id);
    }
  } catch {
    /* ignore */
  }
}

async function loadReport({ quiet = false } = {}) {
  if (!selectedBatchId.value) return;
  if (!quiet) {
    loadingReport.value = true;
    error.value = '';
  }
  try {
    const res = await aiClaimVettingAPI.getBatchReport(selectedBatchId.value, 'pending', {
      scope: 'llm',
    });
    report.value = res.data || null;
    if (res.data?.latest_job && (!job.value || job.value.id === res.data.latest_job.id || !jobRunning.value)) {
      job.value = res.data.latest_job;
    }
  } catch (e) {
    if (e.response?.status === 403) moduleActive.value = false;
    else if (!quiet) error.value = e.response?.data?.detail || e.message || 'Failed to load report';
  } finally {
    if (!quiet) loadingReport.value = false;
  }
}

async function pollJob(jobId) {
  stopPoll();
  let ticks = 0;
  pollTimer = setInterval(async () => {
    try {
      const res = await aiClaimVettingAPI.getJob(jobId);
      job.value = res.data;
      ticks += 1;
      if (ticks === 1 || ticks % 2 === 0) await loadReport({ quiet: true });
      if (!['queued', 'running'].includes(res.data?.status)) {
        stopPoll();
        await loadReport();
        if (res.data?.status === 'completed') {
          $q.notify({
            type: res.data.findings_count ? 'warning' : 'positive',
            message: res.data.findings_count
              ? `Local AI finished — ${res.data.findings_count} recommendation(s)`
              : 'Local AI finished — no issues flagged',
            position: 'top',
          });
        } else if (res.data?.status === 'failed') {
          $q.notify({ type: 'negative', message: res.data.error_message || 'Local AI failed', position: 'top' });
        }
      }
    } catch {
      stopPoll();
    }
  }, 1500);
}

async function startAssist() {
  if (!selectedBatchId.value || !selectedClaimIds.value.length) return;
  starting.value = true;
  error.value = '';
  try {
    const res = await aiClaimVettingAPI.startLlmAssist(selectedBatchId.value, {
      item_ids: selectedClaimIds.value.map(Number),
    });
    job.value = res.data;
    $q.notify({
      type: 'info',
      message: `Local AI reviewing ${res.data.total_items} claim(s)…`,
      position: 'top',
    });
    await pollJob(res.data.id);
  } catch (e) {
    error.value = e.response?.data?.detail || e.message || 'Failed to start local AI';
    $q.notify({ type: 'negative', message: error.value, position: 'top' });
  } finally {
    starting.value = false;
  }
}

async function decide(row, decision) {
  decidingId.value = row.id;
  try {
    await aiClaimVettingAPI.decideFinding(row.id, { decision });
    await loadReport();
    $q.notify({
      type: 'positive',
      message: decision === 'reject' ? 'Recommendation dismissed' : 'Marked for manual edit',
      position: 'top',
    });
  } catch (e) {
    $q.notify({
      type: 'negative',
      message: e.response?.data?.detail || e.message || 'Failed to record decision',
      position: 'top',
    });
  } finally {
    decidingId.value = null;
  }
}

function openClaim(row) {
  if (!row?.source_id) return;
  $router.push(`/claims/ghims-import/item/${row.source_id}`);
}

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
.aiv-hero { margin-bottom: 1.35rem; max-width: 42rem; }
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
}
.aiv-hero__lede {
  margin: 0.65rem 0 0;
  color: var(--hms-text-secondary);
  font-size: var(--hms-text-base);
  line-height: var(--hms-leading-relaxed);
  max-width: 34rem;
}
.aiv-hero__status { display: flex; flex-wrap: wrap; gap: 0.45rem; margin-top: 0.85rem; }
.aiv-chip {
  display: inline-flex;
  align-items: center;
  padding: 0.28rem 0.65rem;
  border-radius: 999px;
  font-size: var(--hms-text-xs);
  font-weight: 650;
  border: 1px solid var(--hms-border);
  background: var(--hms-panel-bg);
  color: var(--hms-text-secondary);
}
.aiv-chip[data-tone='ok'] {
  border-color: color-mix(in srgb, var(--hms-success) 35%, var(--hms-border));
  background: color-mix(in srgb, var(--hms-success) 12%, transparent);
  color: var(--hms-success);
}
.aiv-chip[data-tone='warn'] {
  border-color: color-mix(in srgb, var(--hms-warning) 40%, var(--hms-border));
  background: color-mix(in srgb, var(--hms-warning) 14%, transparent);
  color: var(--hms-warning);
}
.aiv-chip[data-tone='run'] {
  border-color: color-mix(in srgb, var(--hms-accent) 40%, var(--hms-border));
  background: color-mix(in srgb, var(--hms-accent) 12%, transparent);
  color: var(--hms-accent);
}
.aiv-hero__actions { display: flex; flex-wrap: wrap; gap: 0.65rem; margin-top: 1rem; }
.aiv-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
  margin-bottom: 1rem;
}
@media (max-width: 960px) {
  .aiv-grid { grid-template-columns: 1fr; }
}
.aiv-panel {
  padding: 1.1rem 1.15rem 1.2rem;
  border-radius: 1.25rem;
  background: var(--hms-panel-bg);
  border: 1px solid var(--hms-border);
  box-shadow: var(--hms-shadow-md);
}
.aiv-panel--warn {
  border-color: color-mix(in srgb, var(--hms-warning) 40%, var(--hms-border));
  background: color-mix(in srgb, var(--hms-warning) 8%, var(--hms-panel-bg));
}
.aiv-panel__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.85rem;
}
.aiv-panel__kicker {
  font-size: var(--hms-text-xs);
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--hms-text-muted);
  font-weight: 650;
}
.aiv-panel__title {
  margin: 0.2rem 0 0;
  font-size: var(--hms-text-lg);
  font-weight: 750;
}
.aiv-count {
  display: inline-flex;
  margin-left: 0.4rem;
  min-width: 1.5rem;
  justify-content: center;
  padding: 0.05rem 0.4rem;
  border-radius: 999px;
  background: color-mix(in srgb, var(--hms-accent) 14%, transparent);
  color: var(--hms-accent);
  font-size: var(--hms-text-sm);
}
.aiv-muted { color: var(--hms-text-muted); font-size: var(--hms-text-sm); }
.aiv-copy { margin: 0.4rem 0 0; color: var(--hms-text-secondary); }
.aiv-batch-list { display: flex; flex-direction: column; gap: 0.45rem; max-height: 22rem; overflow: auto; }
.aiv-batch {
  text-align: left;
  border: 1px solid var(--hms-border);
  background: transparent;
  border-radius: 0.85rem;
  padding: 0.7rem 0.8rem;
  cursor: pointer;
  color: inherit;
}
.aiv-batch--active {
  border-color: color-mix(in srgb, var(--hms-accent) 45%, var(--hms-border));
  background: color-mix(in srgb, var(--hms-accent) 10%, transparent);
}
.aiv-batch__name { font-weight: 650; }
.aiv-batch__meta { margin-top: 0.15rem; font-size: var(--hms-text-xs); color: var(--hms-text-muted); }
.aiv-picker-bar { display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: center; margin: 0.65rem 0; }
.aiv-claim-scroll { max-height: 16rem; overflow: auto; display: flex; flex-direction: column; gap: 0.35rem; }
.aiv-claim-row {
  display: grid;
  grid-template-columns: auto minmax(5rem, 7rem) 1fr auto;
  gap: 0.55rem;
  align-items: center;
  padding: 0.45rem 0.5rem;
  border-radius: 0.65rem;
  border: 1px solid transparent;
}
.aiv-claim-row:hover { background: color-mix(in srgb, var(--hms-text-primary) 4%, transparent); }
.aiv-claim-row__name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: var(--hms-text-sm); }
.aiv-pill {
  font-size: 0.7rem;
  padding: 0.12rem 0.4rem;
  border-radius: 999px;
  border: 1px solid var(--hms-border);
  color: var(--hms-text-muted);
}
.mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 0.8rem; }
.aiv-cta-row { display: flex; flex-wrap: wrap; gap: 0.55rem; margin-top: 0.9rem; }
.aiv-primary, .aiv-ghost {
  border-radius: 0.75rem;
  padding: 0.55rem 0.9rem;
  font-weight: 650;
  cursor: pointer;
  border: 1px solid transparent;
}
.aiv-primary {
  background: var(--hms-accent);
  color: white;
  border-color: var(--hms-accent);
}
.aiv-primary:disabled, .aiv-ghost:disabled { opacity: 0.5; cursor: not-allowed; }
.aiv-primary--sm, .aiv-ghost--sm { padding: 0.35rem 0.65rem; font-size: var(--hms-text-sm); }
.aiv-ghost {
  background: transparent;
  border-color: var(--hms-border);
  color: var(--hms-text-secondary);
}
.aiv-spinner {
  display: inline-block;
  width: 0.85rem;
  height: 0.85rem;
  margin-right: 0.4rem;
  border: 2px solid rgba(255,255,255,0.35);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  vertical-align: -0.15rem;
}
@keyframes spin { to { transform: rotate(360deg); } }
.aiv-progress { margin-bottom: 1rem; }
.aiv-progress__top { display: flex; justify-content: space-between; gap: 0.75rem; margin-bottom: 0.55rem; }
.aiv-progress__track {
  height: 0.45rem;
  border-radius: 999px;
  background: color-mix(in srgb, var(--hms-text-primary) 8%, transparent);
  overflow: hidden;
}
.aiv-progress__fill {
  height: 100%;
  background: var(--hms-accent);
  transition: width 0.35s ease;
}
.aiv-status[data-status='running'],
.aiv-status[data-status='queued'] { color: var(--hms-accent); font-weight: 650; }
.aiv-status[data-status='completed'] { color: var(--hms-success); font-weight: 650; }
.aiv-status[data-status='failed'] { color: var(--hms-danger, #c62828); font-weight: 650; }
.aiv-error { color: var(--hms-danger, #c62828); font-size: var(--hms-text-sm); }
.aiv-error--banner { margin: 0 0 1rem; }
.aiv-report { margin-bottom: 1.5rem; }
.aiv-empty { text-align: center; padding: 1.5rem 0.5rem; color: var(--hms-text-muted); }
.aiv-empty__mark { font-size: 1.6rem; margin-bottom: 0.35rem; color: var(--hms-success); }
.aiv-finding-group { margin-top: 1rem; }
.aiv-finding-group__head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 0.55rem;
}
.aiv-finding-group__head h3 { margin: 0; font-size: var(--hms-text-base); font-weight: 700; }
.aiv-finding-card {
  border: 1px solid var(--hms-border);
  border-left-width: 4px;
  border-radius: 0.9rem;
  padding: 0.85rem 0.95rem;
  margin-bottom: 0.55rem;
}
.aiv-finding-card[data-severity='critical'] { border-left-color: var(--hms-danger, #c62828); }
.aiv-finding-card[data-severity='warning'] { border-left-color: var(--hms-warning); }
.aiv-finding-card[data-severity='review_needed'] { border-left-color: #607d8b; }
.aiv-finding-card__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem;
  align-items: center;
  margin-bottom: 0.35rem;
  font-size: var(--hms-text-sm);
  color: var(--hms-text-muted);
}
.aiv-finding-card__title { font-weight: 650; }
.aiv-finding-card__body { margin: 0.35rem 0 0; color: var(--hms-text-secondary); font-size: var(--hms-text-sm); }
.aiv-finding-card__rec { margin: 0.45rem 0 0; font-weight: 600; font-size: var(--hms-text-sm); }
.aiv-finding-card__actions { display: flex; flex-wrap: wrap; gap: 0.45rem; margin-top: 0.75rem; }
</style>
