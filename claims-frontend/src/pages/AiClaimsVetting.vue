<template>
  <q-page class="hms-page aiv-page">
    <div class="aiv-atmosphere" aria-hidden="true" />

    <header
      class="aiv-hero"
    >
      <div class="aiv-hero__eyebrow">Claims intelligence</div>
      <h1 class="aiv-hero__title">AI Vetting</h1>
      <p class="aiv-hero__lede">
        Run ClaimIT prep and coding checks in the background, then work findings here —
        nothing changes until a human approves.
      </p>
      <div v-if="moduleActive" class="aiv-hero__status">
        <span class="aiv-chip" data-tone="ok">Human approval required</span>
        <span
          class="aiv-chip"
          :data-tone="aiStatus?.provider === 'ollama' ? (aiStatus.ollama_online ? 'ok' : 'warn') : 'muted'"
        >
          {{ aiEngineLabel }}
        </span>
        <span v-if="jobRunning" class="aiv-chip" data-tone="run">
          Scanning… {{ job?.processed_items || 0 }}/{{ job?.total_items || 0 }}
        </span>
      </div>
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
              <div class="aiv-panel__kicker">02 — Scan lane</div>
              <h2 class="aiv-panel__title">What to run</h2>
            </div>
          </div>

          <div v-if="!selectedBatchId" class="aiv-muted">Select an import batch to continue.</div>
          <template v-else>
            <div class="aiv-lanes">
              <button
                type="button"
                class="aiv-lane"
                :class="{ 'aiv-lane--active': analysisMode === 'phase1' }"
                @click="analysisMode = 'phase1'"
              >
                <div class="aiv-lane__phase">Phase 1</div>
                <div class="aiv-lane__title">ClaimIT prep</div>
                <p class="aiv-lane__copy">ZOOM specialty → OPDC · Ghana Card Member No → HIN</p>
              </button>
              <button
                type="button"
                class="aiv-lane"
                :class="{ 'aiv-lane--active': analysisMode === 'coding' }"
                @click="analysisMode = 'coding'"
              >
                <div class="aiv-lane__phase">Coding</div>
                <div class="aiv-lane__title">Diagnosis GDRG</div>
                <p class="aiv-lane__copy">Phase 1 plus ICD-10 ↔ diagnosis GDRG mismatch checks</p>
              </button>
              <button
                type="button"
                class="aiv-lane"
                :class="{ 'aiv-lane--active': analysisMode === 'thorough' }"
                @click="setThoroughMode"
              >
                <div class="aiv-lane__phase">Thorough</div>
                <div class="aiv-lane__title">Assigned review</div>
                <p class="aiv-lane__copy">Pick 1–2 claims · procedures, medicines &amp; investigations</p>
              </button>
            </div>

            <div class="aiv-scope-block">
              <div class="aiv-scope-block__label">Claim set</div>
              <div class="aiv-scope-row">
                <label class="aiv-radio" :class="{ 'aiv-radio--disabled': analysisMode === 'thorough' }">
                  <input v-model="scopeMode" type="radio" value="all" :disabled="analysisMode === 'thorough'" />
                  <span>All claims (including finalized)</span>
                </label>
                <label class="aiv-radio" :class="{ 'aiv-radio--disabled': analysisMode === 'thorough' }">
                  <input v-model="scopeMode" type="radio" value="open" :disabled="analysisMode === 'thorough'" />
                  <span>All non-finalized only</span>
                </label>
                <label class="aiv-radio">
                  <input v-model="scopeMode" type="radio" value="selected" />
                  <span>{{ analysisMode === 'thorough' ? 'Assigned claims (required)' : 'Selected claims only' }}</span>
                </label>
              </div>
              <p v-if="scopeMode === 'all' && analysisMode !== 'thorough'" class="aiv-muted q-mt-sm">
                Finalized claims appear in the report; applying corrections still needs reopen first.
              </p>
              <p v-if="analysisMode === 'thorough'" class="aiv-muted q-mt-sm">
                Thorough is for validating AI on a small set before a full batch run. Max 10 claims.
              </p>
            </div>

            <div v-if="loadingClaims" class="aiv-muted q-mt-md">Loading claims…</div>
            <div v-else-if="scopeMode === 'selected'" class="aiv-claim-picker q-mt-md">
              <div class="aiv-picker-bar">
                <span class="aiv-muted">{{ selectedClaimIds.length }} selected</span>
                <button
                  v-if="analysisMode !== 'thorough'"
                  type="button"
                  class="aiv-ghost aiv-ghost--sm"
                  @click="selectAllClaims"
                >
                  Select all
                </button>
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
          <span class="aiv-status" :data-status="job.status">
            Job #{{ job.id }} · {{ job.status }}
            <template v-if="job.analysis_mode"> · {{ job.analysis_mode }}</template>
          </span>
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
              Intelligence workspace
              <span v-if="report" class="aiv-count">{{ report.pending_total || 0 }}</span>
            </h2>
          </div>
          <div v-if="selectedIds.length" class="aiv-bulk-bar">
            <span>{{ selectedIds.length }} selected</span>
            <button type="button" class="aiv-primary aiv-primary--sm" :disabled="correcting" @click="bulkCorrectSelected">
              Correct selected
            </button>
            <button type="button" class="aiv-ghost aiv-ghost--sm" :disabled="correcting" @click="bulkReject([...selectedIds])">
              Reject
            </button>
          </div>
        </div>

        <div v-if="!selectedBatchId" class="aiv-muted">Choose a batch to load or generate a report.</div>
        <div v-else-if="loadingReport && !report" class="aiv-muted">Loading report…</div>
        <div v-else-if="jobRunning && (!report || report.pending_total === 0)" class="aiv-muted">
          Scan in progress — findings will appear here as claims finish
          ({{ job?.processed_items || 0 }}/{{ job?.total_items || 0 }}).
        </div>
        <div v-else-if="report && report.pending_total === 0 && !jobRunning" class="aiv-empty">
          <div class="aiv-empty__mark">✓</div>
          <div>No pending issues for this batch.</div>
        </div>

        <template v-else-if="report && report.pending_total > 0">
          <div class="aiv-summary">
            <button
              v-for="lane in reportLanes"
              :key="lane.id"
              type="button"
              class="aiv-summary__tile"
              :class="{ 'aiv-summary__tile--active': activeLane === lane.id, 'aiv-summary__tile--empty': !lane.count }"
              :disabled="!lane.count"
              @click="selectLane(lane.id)"
            >
              <span class="aiv-summary__kicker">{{ lane.label }}</span>
              <span class="aiv-summary__value">{{ lane.count }}</span>
              <span class="aiv-summary__hint">{{ lane.hint }}</span>
            </button>
          </div>

          <div class="aiv-workspace">
            <aside class="aiv-nav">
              <div class="aiv-nav__search">
                <input
                  v-model="reportQuery"
                  type="search"
                  class="aiv-nav__input"
                  placeholder="Filter claim, client, member…"
                />
              </div>
              <div
                v-for="lane in reportLanes.filter((l) => l.count)"
                :key="`nav-${lane.id}`"
                class="aiv-nav__section"
              >
                <div class="aiv-nav__section-title">{{ lane.label }}</div>
                <button
                  v-for="cat in lane.categories"
                  :key="cat.rule_code"
                  type="button"
                  class="aiv-nav__item"
                  :class="{ 'aiv-nav__item--active': activeRuleCode === cat.rule_code }"
                  @click="selectCategory(lane.id, cat.rule_code)"
                >
                  <span class="aiv-nav__item-label">{{ cat.label }}</span>
                  <span class="aiv-nav__item-count">{{ cat.pending_count }}</span>
                </button>
              </div>
            </aside>

            <div class="aiv-detail">
              <div v-if="!activeGroup" class="aiv-muted">Select a category on the left.</div>
              <template v-else>
                <div class="aiv-detail__head">
                  <div>
                    <div class="aiv-detail__phase">{{ laneLabel(activeLane) }}</div>
                    <h3 class="aiv-detail__title">
                      {{ activeGroup.label || friendlyRuleLabel(activeGroup.rule_code) }}
                    </h3>
                    <p class="aiv-muted">
                      {{ filteredActiveFindings.length }} of {{ activeGroup.pending_count }} shown
                      <template v-if="reportQuery"> · filtered</template>
                    </p>
                  </div>
                  <div class="aiv-detail__actions">
                    <label class="aiv-check-all">
                      <input
                        type="checkbox"
                        :checked="isGroupFullySelected(activeGroup)"
                        :indeterminate.prop="isGroupPartiallySelected(activeGroup)"
                        @change="toggleGroup(activeGroup, $event.target.checked)"
                      />
                      Select all
                    </label>
                    <button
                      v-if="!isDrgChoiceGroup(activeGroup.rule_code) && !isReviewOnlyGroup(activeGroup.rule_code)"
                      type="button"
                      class="aiv-primary aiv-primary--sm"
                      :disabled="!selectedInGroup(activeGroup).length || correcting"
                      @click="bulkCorrect(activeGroup.rule_code, selectedInGroup(activeGroup))"
                    >
                      Correct {{ selectedInGroup(activeGroup).length || '' }}
                    </button>
                  </div>
                </div>

                <div v-if="!filteredActiveFindings.length" class="aiv-muted aiv-detail__empty">
                  No findings match this filter.
                </div>

                <div class="aiv-cards">
                  <article
                    v-for="(row, idx) in filteredActiveFindings"
                    :key="row.id"
                    class="aiv-card"
                    :class="{ 'aiv-card--selected': selectedIds.includes(row.id) }"
                  >
                    <div class="aiv-card__top">
                      <label class="aiv-card__check">
                        <input
                          type="checkbox"
                          :checked="selectedIds.includes(row.id)"
                          @change="toggleFinding(row.id, $event.target.checked)"
                        />
                        <span class="aiv-card__index">{{ idx + 1 }}</span>
                      </label>
                      <div class="aiv-card__identity">
                        <div class="aiv-card__claim mono">{{ row.claim_claim_id || '—' }}</div>
                        <div class="aiv-card__client">{{ row.client_name || '—' }}</div>
                      </div>
                      <div class="aiv-card__meta">
                        <span class="aiv-meta-chip" title="Member No">{{ row.member_no || '—' }}</span>
                        <span class="aiv-meta-chip" title="Specialty">{{ row.specialty_attended || '—' }}</span>
                        <span
                          v-if="row.severity"
                          class="aiv-sev"
                          :data-sev="row.severity"
                        >{{ row.severity.replace('_', ' ') }}</span>
                      </div>
                    </div>

                    <div class="aiv-card__body">
                      <div class="aiv-finding">{{ row.finding }}</div>
                      <div class="aiv-muted">{{ row.recommendation }}</div>
                      <details v-if="row.explanation" class="aiv-details">
                        <summary>Why this flagged</summary>
                        <p>{{ row.explanation }}</p>
                      </details>
                    </div>

                    <div class="aiv-card__foot">
                      <div v-if="isDrgChoiceGroup(activeGroup.rule_code)" class="aiv-card__drg">
                        <label class="aiv-card__drg-label">Correct GDRG</label>
                        <select
                          class="aiv-select"
                          :value="chosenDrg[row.id] || preferredDrg(row) || ''"
                          @change="setChosenDrg(row.id, $event.target.value)"
                        >
                          <option value="" disabled>Choose GDRG…</option>
                          <option
                            v-for="opt in allowedDrgs(row)"
                            :key="`${row.id}-${opt.drg_code}`"
                            :value="opt.drg_code"
                          >
                            {{ opt.drg_code }}{{ opt.drg_description ? ` — ${opt.drg_description}` : '' }}
                          </option>
                        </select>
                      </div>
                      <div class="aiv-card__btns">
                        <button
                          v-if="isDrgChoiceGroup(activeGroup.rule_code)"
                          type="button"
                          class="aiv-primary aiv-primary--sm"
                          :disabled="correcting || !(chosenDrg[row.id] || preferredDrg(row))"
                          @click="acceptDrgFinding(row)"
                        >
                          Apply
                        </button>
                    <button
                      v-else-if="isReviewOnlyFinding(row)"
                      type="button"
                      class="aiv-ghost aiv-ghost--sm"
                      :disabled="correcting"
                      @click="markEdited(row.id)"
                    >
                      Mark edited
                    </button>
                    <button
                      v-else
                      type="button"
                      class="aiv-primary aiv-primary--sm"
                      :disabled="correcting"
                      @click="acceptFinding(row)"
                    >
                      Apply
                    </button>
                    <button
                      type="button"
                      class="aiv-ghost aiv-ghost--sm"
                      :disabled="!row.source_id"
                      @click="openClaim(row.source_id)"
                    >
                      Open claim
                    </button>
                      </div>
                    </div>
                  </article>
                </div>
              </template>
            </div>
          </div>
        </template>
      </section>

      <section
        class="aiv-panel aiv-rules"
      >
        <div class="aiv-panel__head">
          <div>
            <div class="aiv-panel__kicker">04 — Facility rules</div>
            <h2 class="aiv-panel__title">Teach the scanner</h2>
            <p class="aiv-muted q-mt-xs">
              Add ClaimIT quirks here (leading hyphens, HIN shape, etc.). No developer script required —
              new rules run on the next Phase 1 / coding / thorough scan.
            </p>
          </div>
          <div class="aiv-bulk-bar">
            <button type="button" class="aiv-ghost aiv-ghost--sm" :disabled="loadingRules" @click="loadRules">
              Refresh
            </button>
            <button type="button" class="aiv-primary aiv-primary--sm" @click="openRuleForm()">
              Add rule
            </button>
          </div>
        </div>

        <div v-if="loadingRules" class="aiv-muted">Loading rules…</div>
        <div v-else-if="!facilityRules.length" class="aiv-muted">No facility rules yet.</div>
        <div v-else class="aiv-rules-list">
          <article
            v-for="rule in facilityRules"
            :key="rule.id"
            class="aiv-rule"
            :class="{ 'aiv-rule--off': !rule.enabled }"
          >
            <div class="aiv-rule__main">
              <div class="aiv-rule__top">
                <span class="aiv-rule__name">{{ rule.name }}</span>
                <span v-if="rule.is_system" class="aiv-pill">System</span>
                <span class="aiv-sev" :data-sev="rule.severity">{{ rule.severity }}</span>
                <span class="aiv-pill">{{ rule.enabled ? 'On' : 'Off' }}</span>
              </div>
              <div class="aiv-muted aiv-rule__cond">
                {{ rule.condition?.field }} · {{ rule.condition?.op }}
                <template v-if="rule.condition?.value != null && rule.condition?.value !== ''">
                  · {{ rule.condition.value }}
                </template>
              </div>
              <div v-if="rule.description" class="aiv-muted aiv-rule__desc">{{ rule.description }}</div>
            </div>
            <div class="aiv-rule__actions">
              <button type="button" class="aiv-ghost aiv-ghost--sm" @click="toggleRuleEnabled(rule)">
                {{ rule.enabled ? 'Disable' : 'Enable' }}
              </button>
              <button type="button" class="aiv-ghost aiv-ghost--sm" @click="openRuleForm(rule)">Edit</button>
              <button type="button" class="aiv-ghost aiv-ghost--sm" @click="removeRule(rule)">
                {{ rule.is_system ? 'Disable' : 'Delete' }}
              </button>
            </div>
          </article>
        </div>

        <div v-if="ruleFormOpen" class="aiv-rule-form">
          <h3 class="aiv-detail__title">{{ ruleForm.id ? 'Edit rule' : 'New rule' }}</h3>
          <div class="aiv-rule-form__grid">
            <label class="aiv-field">
              <span>Name</span>
              <input v-model="ruleForm.name" class="aiv-nav__input" />
            </label>
            <label class="aiv-field">
              <span>Severity</span>
              <select v-model="ruleForm.severity" class="aiv-select">
                <option v-for="s in (rulesMeta.severities || ['critical','warning','review_needed'])" :key="s" :value="s">
                  {{ s }}
                </option>
              </select>
            </label>
            <label class="aiv-field">
              <span>Field</span>
              <select v-model="ruleForm.condition.field" class="aiv-select">
                <option v-for="f in (rulesMeta.fields || [])" :key="f" :value="f">{{ f }}</option>
              </select>
            </label>
            <label class="aiv-field">
              <span>Operator</span>
              <select v-model="ruleForm.condition.op" class="aiv-select">
                <option v-for="op in (rulesMeta.ops || [])" :key="op" :value="op">{{ op }}</option>
              </select>
            </label>
            <label class="aiv-field">
              <span>Value</span>
              <input v-model="ruleForm.condition.value" class="aiv-nav__input" placeholder="e.g. - or 8" />
            </label>
            <label class="aiv-field">
              <span>Suggested fix</span>
              <select v-model="ruleForm.action_type" class="aiv-select">
                <option v-for="t in (rulesMeta.action_types || [])" :key="t" :value="t">{{ t }}</option>
              </select>
            </label>
            <label class="aiv-field aiv-field--wide">
              <span>Description</span>
              <input v-model="ruleForm.description" class="aiv-nav__input" />
            </label>
            <label class="aiv-field aiv-field--wide">
              <span>Finding text (optional, use {value})</span>
              <input v-model="ruleForm.finding_template" class="aiv-nav__input" />
            </label>
            <label class="aiv-field aiv-field--wide">
              <span>Recommendation (optional)</span>
              <input v-model="ruleForm.recommendation_template" class="aiv-nav__input" />
            </label>
          </div>
          <div class="aiv-cta-row">
            <button type="button" class="aiv-primary" :disabled="savingRule" @click="saveRuleForm">
              {{ savingRule ? 'Saving…' : 'Save rule' }}
            </button>
            <button type="button" class="aiv-ghost" @click="ruleFormOpen = false">Cancel</button>
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
const aiStatus = ref(null);
const loadingAiStatus = ref(false);
const batches = ref([]);
const loadingBatches = ref(false);
const selectedBatchId = ref(null);
const batchClaims = ref([]);
const loadingClaims = ref(false);
const scopeMode = ref('all'); // all | open | selected
const analysisMode = ref('phase1'); // phase1 | coding | thorough
const selectedClaimIds = ref([]);

const starting = ref(false);
const loadingReport = ref(false);
const correcting = ref(false);
const error = ref('');
const job = ref(null);
const report = ref(null);
const selectedIds = ref([]);
const chosenDrg = ref({});
const reportQuery = ref('');
const activeLane = ref('phase1');
const activeRuleCode = ref(null);
const facilityRules = ref([]);
const rulesMeta = ref({ fields: [], ops: [], severities: [], action_types: [] });
const loadingRules = ref(false);
const savingRule = ref(false);
const ruleFormOpen = ref(false);
const ruleForm = ref(emptyRuleForm());
let pollTimer = null;

function emptyRuleForm() {
  return {
    id: null,
    name: '',
    description: '',
    severity: 'warning',
    enabled: true,
    condition: { field: 'memberNo', op: 'starts_with', value: '' },
    action_type: 'review_only',
    finding_template: '',
    recommendation_template: '',
  };
}

const jobRunning = computed(() => ['queued', 'running'].includes(job.value?.status));

const scannableClaims = computed(() =>
  (batchClaims.value || []).filter((r) => String(r.status || '') !== 'finalized')
);

const runLabel = computed(() => {
  if (starting.value || jobRunning.value) return 'Scanning…';
  const mode = analysisMode.value;
  if (scopeMode.value === 'selected') {
    const n = selectedClaimIds.value.length;
    if (!n) {
      if (mode === 'thorough') return 'Select 1–2 claims for thorough review';
      if (mode === 'phase1') return 'Select claims for Phase 1';
      return 'Select claims for coding scan';
    }
    if (mode === 'thorough') return `Thorough review ${n} claim(s)`;
    if (mode === 'phase1') return `Run Phase 1 on ${n}`;
    return `Run coding scan on ${n}`;
  }
  const setLabel = scopeMode.value === 'open' ? 'non-finalized' : 'all claims';
  if (mode === 'phase1') return `Run Phase 1 on ${setLabel}`;
  if (mode === 'coding') return `Run coding scan on ${setLabel}`;
  return `Run AI on ${setLabel}`;
});

const reportGroups = computed(() => report.value?.groups || []);

const aiEngineLabel = computed(() => {
  const s = aiStatus.value;
  if (!s) return 'AI engine…';
  if (s.provider === 'ollama') {
    const model = s.model || 'local model';
    return s.ollama_online ? `Local AI · ${model}` : `Local AI offline · ${model}`;
  }
  return 'Rules engine (no LLM)';
});

const RULE_LABELS = {
  specialty_zoom: 'ZOOM specialty → OPDC',
  ghana_card_member_no: 'Ghana Card Member No → HIN',
  diagnosis_drg_mismatch: 'Diagnosis GDRG mismatch',
  diagnosis_icd_unmapped: 'Diagnosis ICD unmapped',
  procedure_drg_mismatch: 'Procedure GDRG mismatch',
  procedure_gdrg_unknown: 'Procedure GDRG unknown',
  medicine_code_unknown: 'Medicine code unknown',
  investigation_gdrg_unknown: 'Investigation GDRG unknown',
};

const PHASE1_RULES = new Set([
  'specialty_zoom',
  'ghana_card_member_no',
  'member_no_leading_hyphen',
  'member_no_length_not_8',
  'hin_format_check',
]);
const CODING_RULES = new Set(['diagnosis_drg_mismatch', 'diagnosis_icd_unmapped']);
const THOROUGH_RULES = new Set([
  'procedure_drg_mismatch',
  'procedure_gdrg_unknown',
  'medicine_code_unknown',
  'investigation_gdrg_unknown',
]);

const DRG_CHOICE_RULES = new Set(['diagnosis_drg_mismatch', 'procedure_drg_mismatch']);
const REVIEW_ONLY_RULES = new Set([
  'diagnosis_icd_unmapped',
  'procedure_gdrg_unknown',
  'medicine_code_unknown',
  'investigation_gdrg_unknown',
  'member_no_length_not_8',
  'hin_format_check',
]);

function friendlyRuleLabel(ruleCode) {
  if (RULE_LABELS[ruleCode]) return RULE_LABELS[ruleCode];
  if (String(ruleCode || '').startsWith('llm_')) {
    return String(ruleCode)
      .replace(/^llm_review_?/i, '')
      .replace(/^llm_/i, '')
      .replace(/_/g, ' ')
      .trim() || 'Local AI review';
  }
  return ruleCode;
}

function ruleLane(ruleCode) {
  if (String(ruleCode || '').startsWith('llm_')) return 'ai';
  if (PHASE1_RULES.has(ruleCode)) return 'phase1';
  if (CODING_RULES.has(ruleCode)) return 'coding';
  if (THOROUGH_RULES.has(ruleCode)) return 'thorough';
  return 'phase1';
}

function laneLabel(id) {
  if (id === 'phase1') return 'Phase 1 · ClaimIT';
  if (id === 'coding') return 'Coding intelligence';
  if (id === 'thorough') return 'Thorough review';
  if (id === 'ai') return 'Local AI assist';
  return id;
}

const reportLanes = computed(() => {
  const groups = reportGroups.value;
  const byLane = {
    phase1: [],
    coding: [],
    thorough: [],
    ai: [],
  };
  for (const g of groups) {
    byLane[ruleLane(g.rule_code)]?.push({
      ...g,
      label: g.label || friendlyRuleLabel(g.rule_code),
    });
  }
  return [
    {
      id: 'phase1',
      label: 'Phase 1',
      hint: 'ClaimIT prep',
      categories: byLane.phase1,
      count: byLane.phase1.reduce((n, g) => n + (g.pending_count || 0), 0),
    },
    {
      id: 'coding',
      label: 'Coding',
      hint: 'Diagnosis GDRG',
      categories: byLane.coding,
      count: byLane.coding.reduce((n, g) => n + (g.pending_count || 0), 0),
    },
    {
      id: 'thorough',
      label: 'Thorough',
      hint: 'Proc · med · inv',
      categories: byLane.thorough,
      count: byLane.thorough.reduce((n, g) => n + (g.pending_count || 0), 0),
    },
    {
      id: 'ai',
      label: 'AI assist',
      hint: 'Local model · review only',
      categories: byLane.ai,
      count: byLane.ai.reduce((n, g) => n + (g.pending_count || 0), 0),
    },
  ];
});

const activeGroup = computed(() => {
  if (!activeRuleCode.value) return null;
  return reportGroups.value.find((g) => g.rule_code === activeRuleCode.value) || null;
});

const filteredActiveFindings = computed(() => {
  const rows = activeGroup.value?.findings || [];
  const q = reportQuery.value.trim().toLowerCase();
  if (!q) return rows;
  return rows.filter((row) => {
    const hay = [
      row.claim_claim_id,
      row.client_name,
      row.member_no,
      row.specialty_attended,
      row.finding,
      row.recommendation,
    ]
      .map((x) => String(x || '').toLowerCase())
      .join(' ');
    return hay.includes(q);
  });
});

function selectLane(laneId) {
  activeLane.value = laneId;
  const lane = reportLanes.value.find((l) => l.id === laneId);
  const first = lane?.categories?.[0];
  activeRuleCode.value = first?.rule_code || null;
}

function selectCategory(laneId, ruleCode) {
  activeLane.value = laneId;
  activeRuleCode.value = ruleCode;
}

function syncReportSelection() {
  const lanes = reportLanes.value.filter((l) => l.count);
  if (!lanes.length) {
    activeRuleCode.value = null;
    return;
  }
  const currentOk = lanes.some((l) =>
    l.categories.some((c) => c.rule_code === activeRuleCode.value)
  );
  if (currentOk) return;
  const preferred = lanes.find((l) => l.id === activeLane.value) || lanes[0];
  activeLane.value = preferred.id;
  activeRuleCode.value = preferred.categories[0]?.rule_code || null;
}

function setThoroughMode() {
  analysisMode.value = 'thorough';
  scopeMode.value = 'selected';
}

function isDrgChoiceGroup(ruleCode) {
  return DRG_CHOICE_RULES.has(ruleCode);
}

function isReviewOnlyGroup(ruleCode) {
  if (REVIEW_ONLY_RULES.has(ruleCode)) return true;
  if (String(ruleCode || '').startsWith('llm_')) return true;
  return false;
}

function isReviewOnlyFinding(row) {
  const type = row?.suggested_action?.type || '';
  const code = row?.rule_code || '';
  if (String(type).startsWith('review_')) return true;
  if (String(code).startsWith('llm_')) return true;
  return isReviewOnlyGroup(code);
}

function isAutoApplyFinding(row) {
  if (isDrgChoiceGroup(row?.rule_code)) return false;
  if (isReviewOnlyFinding(row)) return false;
  return true;
}

function findingNeedsReopen(row) {
  return String(row?.item_status || '').toLowerCase() === 'finalized';
}

function allowedDrgs(row) {
  const details = row?.suggested_action?.details || {};
  return Array.isArray(details.allowed_drgs) ? details.allowed_drgs : [];
}

function preferredDrg(row) {
  const action = row?.suggested_action || {};
  const details = action.details || {};
  return (action.value || details.preferred || '').trim();
}

function setChosenDrg(findingId, value) {
  chosenDrg.value = { ...chosenDrg.value, [findingId]: value };
}
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
  if (moduleActive.value) {
    await loadAiStatus();
  }
}

async function loadAiStatus() {
  loadingAiStatus.value = true;
  try {
    const res = await aiClaimVettingAPI.getStatus();
    aiStatus.value = res.data || null;
    if (res.data && typeof res.data.module_active === 'boolean') {
      moduleActive.value = res.data.module_active;
    }
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

async function loadReport({ quiet = false } = {}) {
  if (!selectedBatchId.value) return;
  if (!quiet) {
    loadingReport.value = true;
    error.value = '';
  }
  try {
    const res = await aiClaimVettingAPI.getBatchReport(selectedBatchId.value);
    report.value = res.data || null;
    if (res.data?.latest_job && !jobRunning.value) {
      job.value = res.data.latest_job;
    } else if (res.data?.latest_job && job.value?.id === res.data.latest_job.id) {
      job.value = res.data.latest_job;
    }
    const alive = new Set(
      (res.data?.groups || []).flatMap((g) => (g.findings || []).map((f) => f.id))
    );
    selectedIds.value = selectedIds.value.filter((id) => alive.has(id));
    syncReportSelection();
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
      if (ticks === 1 || ticks % 3 === 0) {
        await loadReport({ quiet: true });
      }
      if (!['queued', 'running'].includes(res.data?.status)) {
        stopPoll();
        await loadReport();
        if (res.data?.status === 'completed') {
          $q.notify({
            type: res.data.findings_count ? 'warning' : 'positive',
            message: res.data.findings_count
              ? `Scan complete — ${res.data.findings_count} finding(s)`
              : 'Scan complete — no issues found',
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
  if (analysisMode.value === 'thorough') {
    if (scopeMode.value !== 'selected' || !selectedClaimIds.value.length) {
      $q.notify({
        type: 'warning',
        message: 'Thorough mode: select 1–2 claims to assign for careful review.',
        position: 'top',
      });
      return;
    }
    if (selectedClaimIds.value.length > 10) {
      $q.notify({
        type: 'warning',
        message: 'Thorough mode is limited to 10 claims. Deselect some first.',
        position: 'top',
      });
      return;
    }
  }
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
      mode: analysisMode.value,
    });
    job.value = res.data;
    $q.notify({
      type: 'info',
      message: `Scanning ${res.data.total_items} claim(s) (${analysisMode.value}) in the background…`,
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

async function acceptDrgFinding(row) {
  const value = (chosenDrg.value[row.id] || preferredDrg(row) || '').trim();
  if (!value) {
    $q.notify({ type: 'warning', message: 'Choose a GDRG before applying.', position: 'top' });
    return;
  }
  if (!(await confirmReopenIfNeeded(row))) return;
  correcting.value = true;
  try {
    const res = await aiClaimVettingAPI.decideFinding(row.id, {
      decision: 'accept',
      chosen_value: value,
    });
    $q.notify({
      type: 'positive',
      message: res.data?.message || `Applied GDRG ${value}`,
      position: 'top',
    });
    const next = { ...chosenDrg.value };
    delete next[row.id];
    chosenDrg.value = next;
    await loadReport();
  } catch (e) {
    $q.notify({
      type: 'negative',
      message: e.response?.data?.detail || e.message || 'Failed to apply GDRG',
      position: 'top',
    });
  } finally {
    correcting.value = false;
  }
}

async function confirmReopenIfNeeded(rowOrIds) {
  const rows = Array.isArray(rowOrIds)
    ? (reportGroups.value || [])
        .flatMap((g) => g.findings || [])
        .filter((f) => rowOrIds.includes(f.id))
    : [rowOrIds];
  const finalized = rows.filter((r) => findingNeedsReopen(r));
  if (!finalized.length) return true;
  return new Promise((resolve) => {
    $q.dialog({
      title: 'Reopen finalized claim?',
      message:
        finalized.length === 1
          ? `Claim ${finalized[0].claim_claim_id || finalized[0].source_id} is finalized. Accepting will reopen it, apply the correction, then you can re-finalize when ready.`
          : `${finalized.length} selected claim(s) are finalized. Accepting will reopen them, apply corrections, then you can re-finalize when ready.`,
      cancel: true,
      persistent: true,
      ok: { label: 'Reopen & apply', color: 'primary' },
    })
      .onOk(() => resolve(true))
      .onCancel(() => resolve(false))
      .onDismiss(() => resolve(false));
  });
}

async function acceptFinding(row) {
  if (!(await confirmReopenIfNeeded(row))) return;
  correcting.value = true;
  try {
    const res = await aiClaimVettingAPI.decideFinding(row.id, { decision: 'accept' });
    $q.notify({
      type: 'positive',
      message: res.data?.message || 'Applied',
      position: 'top',
    });
    await loadReport();
  } catch (e) {
    $q.notify({
      type: 'negative',
      message: e.response?.data?.detail || e.message || 'Failed to apply',
      position: 'top',
    });
  } finally {
    correcting.value = false;
  }
}

async function markEdited(findingId) {
  correcting.value = true;
  try {
    await aiClaimVettingAPI.decideFinding(findingId, {
      decision: 'edited',
      note: 'Reviewed / corrected manually from AI Vetting console',
    });
    $q.notify({ type: 'positive', message: 'Marked as edited', position: 'top' });
    await loadReport();
  } catch (e) {
    $q.notify({
      type: 'negative',
      message: e.response?.data?.detail || e.message || 'Failed to update finding',
      position: 'top',
    });
  } finally {
    correcting.value = false;
  }
}

async function bulkCorrectSelected() {
  const ids = [...selectedIds.value];
  if (!ids.length) return;
  const autoIds = [];
  let skippedChoice = 0;
  let skippedReview = 0;
  for (const group of reportGroups.value) {
    for (const f of group.findings || []) {
      if (!ids.includes(f.id)) continue;
      if (isDrgChoiceGroup(group.rule_code)) skippedChoice += 1;
      else if (isReviewOnlyFinding(f)) skippedReview += 1;
      else autoIds.push(f.id);
    }
  }
  if (skippedChoice || skippedReview) {
    $q.notify({
      type: 'info',
      message: [
        skippedChoice ? `${skippedChoice} DRG row(s) need a chosen code (use Apply).` : '',
        skippedReview ? `${skippedReview} review-only row(s) — open claim then Mark edited.` : '',
      ]
        .filter(Boolean)
        .join(' '),
      position: 'top',
    });
  }
  if (!autoIds.length) return;
  await bulkCorrect(null, autoIds);
}

async function bulkCorrect(ruleCode, findingIds) {
  if (!findingIds?.length) return;
  if (ruleCode && (isDrgChoiceGroup(ruleCode) || isReviewOnlyGroup(ruleCode))) {
    $q.notify({
      type: 'info',
      message: isDrgChoiceGroup(ruleCode)
        ? 'Choose the correct GDRG on each row, then Apply.'
        : 'Open the claim to fix the code, then Mark edited.',
      position: 'top',
    });
    return;
  }
  if (!(await confirmReopenIfNeeded(findingIds))) return;

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

watch(analysisMode, (mode) => {
  if (mode === 'thorough') scopeMode.value = 'selected';
});

watch(reportGroups, () => {
  syncReportSelection();
});

onMounted(async () => {
  await checkModule();
  if (moduleActive.value) {
    await loadBatches();
    await loadRules();
  }
});

onBeforeUnmount(stopPoll);

async function loadRules() {
  loadingRules.value = true;
  try {
    const [rulesRes, metaRes] = await Promise.all([
      aiClaimVettingAPI.listRules(),
      aiClaimVettingAPI.getRulesMeta(),
    ]);
    facilityRules.value = rulesRes.data || [];
    rulesMeta.value = metaRes.data || rulesMeta.value;
  } catch (e) {
    if (e.response?.status !== 403) {
      $q.notify({
        type: 'negative',
        message: e.response?.data?.detail || 'Failed to load facility rules',
        position: 'top',
      });
    }
  } finally {
    loadingRules.value = false;
  }
}

function openRuleForm(rule = null) {
  if (rule) {
    ruleForm.value = {
      id: rule.id,
      name: rule.name || '',
      description: rule.description || '',
      severity: rule.severity || 'warning',
      enabled: !!rule.enabled,
      condition: {
        field: rule.condition?.field || 'memberNo',
        op: rule.condition?.op || 'starts_with',
        value: rule.condition?.value ?? '',
        skip_if_ghana_card: !!rule.condition?.skip_if_ghana_card,
        skip_if_hin_shaped: !!rule.condition?.skip_if_hin_shaped,
      },
      action_type: rule.suggested_action?.type || 'review_only',
      finding_template: rule.finding_template || '',
      recommendation_template: rule.recommendation_template || '',
    };
  } else {
    ruleForm.value = emptyRuleForm();
    if (rulesMeta.value.fields?.length) {
      ruleForm.value.condition.field = rulesMeta.value.fields[0];
    }
  }
  ruleFormOpen.value = true;
}

async function saveRuleForm() {
  const form = ruleForm.value;
  if (!form.name?.trim()) {
    $q.notify({ type: 'warning', message: 'Name is required', position: 'top' });
    return;
  }
  const payload = {
    name: form.name.trim(),
    description: form.description || null,
    severity: form.severity,
    enabled: form.enabled !== false,
    analysis_modes: ['phase1', 'coding', 'thorough'],
    condition: {
      field: form.condition.field,
      op: form.condition.op,
      value: form.condition.value,
      ...(form.condition.skip_if_ghana_card ? { skip_if_ghana_card: true } : {}),
      ...(form.condition.skip_if_hin_shaped ? { skip_if_hin_shaped: true } : {}),
    },
    suggested_action: {
      type: form.action_type || 'review_only',
      field: form.condition.field,
      value: form.action_type === 'strip_prefix' ? form.condition.value : undefined,
      details:
        form.action_type === 'strip_prefix'
          ? { prefix: form.condition.value || '-' }
          : {},
    },
    finding_template: form.finding_template || null,
    recommendation_template: form.recommendation_template || null,
  };
  savingRule.value = true;
  try {
    if (form.id) {
      await aiClaimVettingAPI.updateRule(form.id, payload);
    } else {
      await aiClaimVettingAPI.createRule(payload);
    }
    ruleFormOpen.value = false;
    await loadRules();
    $q.notify({ type: 'positive', message: 'Rule saved', position: 'top' });
  } catch (e) {
    $q.notify({
      type: 'negative',
      message: e.response?.data?.detail || e.message || 'Failed to save rule',
      position: 'top',
    });
  } finally {
    savingRule.value = false;
  }
}

async function toggleRuleEnabled(rule) {
  try {
    await aiClaimVettingAPI.updateRule(rule.id, { enabled: !rule.enabled });
    await loadRules();
  } catch (e) {
    $q.notify({
      type: 'negative',
      message: e.response?.data?.detail || 'Failed to update rule',
      position: 'top',
    });
  }
}

async function removeRule(rule) {
  const ok = await new Promise((resolve) => {
    $q.dialog({
      title: rule.is_system ? 'Disable system rule?' : 'Delete rule?',
      message: rule.is_system
        ? 'System rules are disabled, not deleted, so you can turn them back on later.'
        : `Delete “${rule.name}”?`,
      cancel: true,
      persistent: true,
    })
      .onOk(() => resolve(true))
      .onCancel(() => resolve(false))
      .onDismiss(() => resolve(false));
  });
  if (!ok) return;
  try {
    await aiClaimVettingAPI.deleteRule(rule.id);
    await loadRules();
  } catch (e) {
    $q.notify({
      type: 'negative',
      message: e.response?.data?.detail || 'Failed to remove rule',
      position: 'top',
    });
  }
}
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

.aiv-hero__status {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
  margin-top: 0.85rem;
}

.aiv-chip {
  display: inline-flex;
  align-items: center;
  padding: 0.28rem 0.65rem;
  border-radius: 999px;
  font-size: var(--hms-text-xs);
  font-weight: 650;
  letter-spacing: 0.02em;
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

.aiv-chip[data-tone='muted'] {
  color: var(--hms-text-muted);
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

.aiv-radio--disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.aiv-select {
  max-width: 16rem;
  width: 100%;
  padding: 0.35rem 0.5rem;
  border-radius: var(--hms-radius-md, 8px);
  border: 1px solid var(--hms-border);
  background: var(--hms-panel-bg, var(--hms-surface));
  color: var(--hms-text-primary);
  font-size: var(--hms-text-sm);
}

.aiv-explain {
  margin-top: 0.25rem;
  font-size: var(--hms-text-xs);
  max-width: 28rem;
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

.aiv-lanes {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.65rem;
}

@media (max-width: 900px) {
  .aiv-lanes { grid-template-columns: 1fr; }
}

.aiv-lane {
  text-align: left;
  border: 1px solid var(--hms-border);
  background: var(--hms-surface);
  color: var(--hms-text-primary);
  border-radius: var(--hms-radius-xl);
  padding: 0.85rem 0.9rem;
  cursor: pointer;
  transition: border-color var(--hms-duration-fast) var(--hms-ease-out),
    background var(--hms-duration-fast) var(--hms-ease-out),
    transform var(--hms-duration-fast) var(--hms-ease-out);
}

.aiv-lane:hover {
  background: var(--hms-surface-hover);
  transform: translateY(-1px);
}

.aiv-lane--active {
  border-color: color-mix(in srgb, var(--hms-accent) 55%, var(--hms-border));
  background: var(--hms-accent-muted);
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--hms-accent) 25%, transparent);
}

.aiv-lane__phase {
  font-size: var(--hms-text-xs);
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--hms-accent);
  font-weight: 650;
}

.aiv-lane__title {
  margin-top: 0.35rem;
  font-weight: 700;
  font-size: var(--hms-text-base);
  letter-spacing: var(--hms-tracking-tight);
}

.aiv-lane__copy {
  margin: 0.35rem 0 0;
  font-size: var(--hms-text-xs);
  line-height: var(--hms-leading-normal);
  color: var(--hms-text-muted);
}

.aiv-scope-block {
  margin-top: 1.1rem;
  padding-top: 0.95rem;
  border-top: 1px solid var(--hms-border);
}

.aiv-scope-block__label {
  font-size: var(--hms-text-xs);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--hms-text-muted);
  font-weight: 650;
  margin-bottom: 0.55rem;
}

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

.aiv-summary {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.65rem;
  margin-bottom: 1rem;
}

@media (max-width: 720px) {
  .aiv-summary { grid-template-columns: 1fr; }
}

.aiv-summary__tile {
  text-align: left;
  border: 1px solid var(--hms-border);
  background: var(--hms-surface);
  border-radius: var(--hms-radius-xl);
  padding: 0.85rem 1rem;
  cursor: pointer;
  color: var(--hms-text-primary);
  transition: border-color var(--hms-duration-fast) var(--hms-ease-out),
    background var(--hms-duration-fast) var(--hms-ease-out);
}

.aiv-summary__tile:hover:not(:disabled) {
  background: var(--hms-surface-hover);
}

.aiv-summary__tile--active {
  border-color: color-mix(in srgb, var(--hms-accent) 50%, var(--hms-border));
  background: var(--hms-accent-muted);
}

.aiv-summary__tile--empty,
.aiv-summary__tile:disabled {
  opacity: 0.42;
  cursor: default;
}

.aiv-summary__kicker {
  display: block;
  font-size: var(--hms-text-xs);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--hms-text-muted);
  font-weight: 650;
}

.aiv-summary__value {
  display: block;
  margin-top: 0.2rem;
  font-size: clamp(1.5rem, 2.4vw, 1.9rem);
  font-weight: 750;
  letter-spacing: var(--hms-tracking-tight);
  line-height: 1.1;
}

.aiv-summary__hint {
  display: block;
  margin-top: 0.15rem;
  font-size: var(--hms-text-xs);
  color: var(--hms-text-muted);
}

.aiv-workspace {
  display: grid;
  grid-template-columns: minmax(200px, 260px) minmax(0, 1fr);
  gap: 0;
  border: 1px solid var(--hms-border);
  border-radius: var(--hms-radius-2xl);
  overflow: hidden;
  min-height: 420px;
  background: var(--hms-surface);
}

@media (max-width: 900px) {
  .aiv-workspace {
    grid-template-columns: 1fr;
  }
}

.aiv-nav {
  border-right: 1px solid var(--hms-border);
  background: var(--hms-bg-elevated);
  display: flex;
  flex-direction: column;
  min-height: 100%;
}

@media (max-width: 900px) {
  .aiv-nav {
    border-right: none;
    border-bottom: 1px solid var(--hms-border);
    max-height: 260px;
  }
}

.aiv-nav__search {
  padding: 0.75rem;
  border-bottom: 1px solid var(--hms-border);
}

.aiv-nav__input {
  width: 100%;
  border: 1px solid var(--hms-border);
  background: var(--hms-panel-bg);
  color: var(--hms-text-primary);
  border-radius: var(--hms-radius-lg);
  padding: 0.5rem 0.65rem;
  font: inherit;
  font-size: var(--hms-text-sm);
}

.aiv-nav__input:focus {
  outline: 2px solid color-mix(in srgb, var(--hms-accent) 45%, transparent);
  outline-offset: 1px;
}

.aiv-nav__section {
  padding: 0.75rem 0.55rem 0.35rem;
}

.aiv-nav__section-title {
  padding: 0 0.45rem 0.4rem;
  font-size: var(--hms-text-xs);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--hms-text-muted);
  font-weight: 650;
}

.aiv-nav__item {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  text-align: left;
  border: none;
  background: transparent;
  color: var(--hms-text-primary);
  border-radius: var(--hms-radius-lg);
  padding: 0.55rem 0.6rem;
  cursor: pointer;
  font: inherit;
  font-size: var(--hms-text-sm);
}

.aiv-nav__item:hover {
  background: var(--hms-surface-hover);
}

.aiv-nav__item--active {
  background: var(--hms-accent-muted);
  color: var(--hms-accent);
  font-weight: 650;
}

.aiv-nav__item-label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.aiv-nav__item-count {
  flex-shrink: 0;
  min-width: 1.4rem;
  text-align: center;
  font-size: var(--hms-text-xs);
  font-weight: 700;
  padding: 0.1rem 0.35rem;
  border-radius: var(--hms-radius-full);
  background: color-mix(in srgb, var(--hms-text-muted) 14%, transparent);
}

.aiv-detail {
  padding: 1rem 1.1rem 1.2rem;
  overflow: auto;
  max-height: 70vh;
}

.aiv-detail__head {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
  margin-bottom: 1rem;
  padding-bottom: 0.85rem;
  border-bottom: 1px solid var(--hms-border);
}

.aiv-detail__phase {
  font-size: var(--hms-text-xs);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--hms-accent);
  font-weight: 650;
}

.aiv-detail__title {
  margin: 0.2rem 0 0;
  font-size: var(--hms-text-lg);
  font-weight: 700;
  letter-spacing: var(--hms-tracking-tight);
  color: var(--hms-text-primary);
}

.aiv-detail__actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.aiv-detail__empty {
  padding: 1.5rem 0;
}

.aiv-cards {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.aiv-card {
  border: 1px solid var(--hms-border);
  border-radius: var(--hms-radius-xl);
  background: var(--hms-panel-bg);
  padding: 0.9rem 1rem;
  transition: border-color var(--hms-duration-fast) var(--hms-ease-out),
    box-shadow var(--hms-duration-fast) var(--hms-ease-out);
}

.aiv-card--selected {
  border-color: color-mix(in srgb, var(--hms-accent) 45%, var(--hms-border));
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--hms-accent) 20%, transparent);
}

.aiv-card__top {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 0.75rem;
  align-items: start;
}

@media (max-width: 720px) {
  .aiv-card__top {
    grid-template-columns: auto minmax(0, 1fr);
  }
  .aiv-card__meta {
    grid-column: 1 / -1;
  }
}

.aiv-card__check {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  cursor: pointer;
}

.aiv-card__index {
  width: 1.4rem;
  height: 1.4rem;
  display: grid;
  place-items: center;
  border-radius: var(--hms-radius-full);
  font-size: var(--hms-text-xs);
  font-weight: 700;
  color: var(--hms-text-muted);
  background: var(--hms-surface);
}

.aiv-card__claim {
  font-weight: 700;
  font-size: var(--hms-text-sm);
}

.aiv-card__client {
  margin-top: 0.15rem;
  font-size: var(--hms-text-sm);
  color: var(--hms-text-secondary);
}

.aiv-card__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  justify-content: flex-end;
}

.aiv-meta-chip {
  font-family: var(--hms-font-mono);
  font-size: 0.72rem;
  padding: 0.2rem 0.45rem;
  border-radius: var(--hms-radius-md, 8px);
  background: var(--hms-surface);
  color: var(--hms-text-muted);
  border: 1px solid var(--hms-border);
  max-width: 11rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.aiv-sev {
  font-size: 0.68rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  font-weight: 700;
  padding: 0.2rem 0.45rem;
  border-radius: var(--hms-radius-full);
  background: var(--hms-surface);
  color: var(--hms-text-muted);
}

.aiv-sev[data-sev='critical'] {
  color: var(--hms-critical);
  background: var(--hms-critical-muted);
}

.aiv-sev[data-sev='warning'] {
  color: var(--hms-warning);
  background: color-mix(in srgb, var(--hms-warning) 16%, transparent);
}

.aiv-card__body {
  margin-top: 0.75rem;
  padding-top: 0.7rem;
  border-top: 1px solid var(--hms-border);
}

.aiv-details {
  margin-top: 0.55rem;
  font-size: var(--hms-text-xs);
  color: var(--hms-text-muted);
}

.aiv-details summary {
  cursor: pointer;
  color: var(--hms-text-secondary);
  font-weight: 600;
}

.aiv-details p {
  margin: 0.4rem 0 0;
  line-height: var(--hms-leading-relaxed);
}

.aiv-card__foot {
  margin-top: 0.85rem;
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  align-items: flex-end;
  justify-content: space-between;
}

.aiv-card__drg {
  flex: 1 1 14rem;
  min-width: 0;
}

.aiv-card__drg-label {
  display: block;
  font-size: var(--hms-text-xs);
  color: var(--hms-text-muted);
  margin-bottom: 0.3rem;
  font-weight: 650;
}

.aiv-card__btns {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
  justify-content: flex-end;
}

.aiv-finding {
  font-weight: 600;
  margin-bottom: 0.15rem;
}

.mono {
  font-family: var(--hms-font-mono);
  font-size: 0.82em;
}

.aiv-rules {
  margin-top: 1rem;
}

.aiv-rules-list {
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
}

.aiv-rule {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
  padding: 0.85rem 1rem;
  border: 1px solid var(--hms-border);
  border-radius: var(--hms-radius-xl);
  background: var(--hms-surface);
}

.aiv-rule--off {
  opacity: 0.55;
}

.aiv-rule__top {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  align-items: center;
}

.aiv-rule__name {
  font-weight: 700;
  font-size: var(--hms-text-base);
}

.aiv-rule__cond {
  margin-top: 0.25rem;
  font-family: var(--hms-font-mono);
  font-size: 0.78rem;
}

.aiv-rule__desc {
  margin-top: 0.35rem;
  max-width: 40rem;
}

.aiv-rule__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  align-items: flex-start;
}

.aiv-rule-form {
  margin-top: 1.1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--hms-border);
}

.aiv-rule-form__grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.75rem;
  margin-top: 0.75rem;
}

@media (max-width: 720px) {
  .aiv-rule-form__grid { grid-template-columns: 1fr; }
}

.aiv-field {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  font-size: var(--hms-text-xs);
  color: var(--hms-text-muted);
  font-weight: 650;
}

.aiv-field--wide {
  grid-column: 1 / -1;
}
</style>
