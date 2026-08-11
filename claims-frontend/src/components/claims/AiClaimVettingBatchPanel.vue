<template>
  <q-card v-if="moduleActive" flat bordered class="ai-batch-panel q-mb-md">
    <q-card-section>
      <div class="row items-center q-gutter-sm q-mb-sm">
        <div class="text-h6">AI Claims Vetting</div>
        <q-space />
        <q-btn
          color="primary"
          icon="psychology"
          :label="runLabel"
          :loading="starting"
          :disable="!batchId || jobRunning"
          unelevated
          @click="startAnalyze"
        />
        <q-btn
          flat
          dense
          color="primary"
          icon="assessment"
          label="Refresh report"
          :loading="loadingReport"
          :disable="!batchId"
          @click="loadReport"
        />
      </div>
      <div class="text-caption text-grey-7 q-mb-md">
        Select claims in the table (or leave selection empty to scan all non-finalized), then run AI check in the background.
        Review the report by issue type and correct selected rows in one action.
      </div>

      <div v-if="job" class="q-mb-md">
        <div class="row items-center q-gutter-sm">
          <q-badge
            :color="jobBadgeColor"
            :label="`Job #${job.id}: ${job.status}`"
          />
          <span class="text-caption">
            {{ job.processed_items }}/{{ job.total_items }} claims
            <template v-if="job.findings_count != null"> · {{ job.findings_count }} finding(s)</template>
          </span>
        </div>
        <q-linear-progress
          v-if="jobRunning"
          :value="(job.progress_pct || 0) / 100"
          color="primary"
          class="q-mt-sm"
          size="8px"
        />
        <div v-if="job.error_message" class="text-negative text-caption q-mt-xs">{{ job.error_message }}</div>
        <div v-if="job.status === 'completed' && job.summary_by_rule" class="row q-gutter-xs q-mt-sm">
          <q-chip
            v-for="(count, code) in job.summary_by_rule"
            :key="code"
            dense
            outline
            color="deep-orange"
            clickable
            @click="activeRule = code"
          >
            {{ ruleLabel(code) }}: {{ count }}
          </q-chip>
        </div>
      </div>

      <q-banner v-if="error" class="bg-red-1 q-mb-sm" rounded dense>
        <template #avatar><q-icon name="error" color="negative" /></template>
        {{ error }}
      </q-banner>

      <div v-if="report && report.pending_total === 0 && !jobRunning" class="text-body2 text-grey-7">
        No pending AI findings for this batch.
        <template v-if="!job">Run AI check to scan claims.</template>
      </div>

      <div v-for="group in reportGroups" :key="group.rule_code" class="q-mb-lg">
        <div class="row items-center q-mb-sm">
          <div class="text-subtitle1 text-weight-medium">
            {{ group.label }}
            <q-badge color="orange" class="q-ml-sm" :label="`${group.pending_count}`" />
          </div>
          <q-space />
          <q-checkbox
            :model-value="isGroupFullySelected(group)"
            :indeterminate="isGroupPartiallySelected(group)"
            dense
            label="Select all"
            @update:model-value="(v) => toggleGroup(group, v)"
          />
          <q-btn
            color="positive"
            dense
            unelevated
            class="q-ml-sm"
            :label="correctLabel(group)"
            :disable="selectedInGroup(group).length === 0 || correcting"
            :loading="correcting && correctingRule === group.rule_code"
            @click="bulkCorrect(group.rule_code, selectedInGroup(group))"
          />
          <q-btn
            flat
            dense
            color="negative"
            class="q-ml-xs"
            label="Reject selected"
            :disable="selectedInGroup(group).length === 0 || correcting"
            @click="bulkReject(selectedInGroup(group))"
          />
        </div>

        <q-markup-table flat dense bordered separator="horizontal" wrap-cells>
          <thead>
            <tr>
              <th class="text-left" style="width: 48px">Sel</th>
              <th class="text-left">Claim ID</th>
              <th class="text-left">Client</th>
              <th class="text-left">Member No</th>
              <th class="text-left">Specialty</th>
              <th class="text-left">Finding</th>
              <th class="text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in group.findings" :key="row.id">
              <td>
                <q-checkbox
                  :model-value="selectedIds.includes(row.id)"
                  dense
                  @update:model-value="(v) => toggleFinding(row.id, v)"
                />
              </td>
              <td class="mono">{{ row.claim_claim_id || '—' }}</td>
              <td>{{ row.client_name || '—' }}</td>
              <td class="mono">{{ row.member_no || '—' }}</td>
              <td>{{ row.specialty_attended || '—' }}</td>
              <td>
                <div class="text-body2">{{ row.finding }}</div>
                <div class="text-caption text-grey-7">{{ row.recommendation }}</div>
              </td>
              <td class="text-right">
                <q-btn
                  flat
                  dense
                  color="primary"
                  label="Open"
                  :disable="!row.source_id"
                  @click="openClaim(row.source_id)"
                />
              </td>
            </tr>
          </tbody>
        </q-markup-table>
      </div>

      <div v-if="selectedIds.length" class="row items-center q-gutter-sm q-mt-md">
        <span class="text-body2">{{ selectedIds.length }} finding(s) selected across groups</span>
        <q-btn
          color="positive"
          unelevated
          dense
          label="Correct all selected"
          :loading="correcting && !correctingRule"
          :disable="correcting"
          @click="bulkCorrect(null, [...selectedIds])"
        />
        <q-btn
          outline
          color="negative"
          dense
          label="Reject all selected"
          :disable="correcting"
          @click="bulkReject([...selectedIds])"
        />
      </div>
    </q-card-section>
  </q-card>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue';
import { useQuasar } from 'quasar';
import { useRouter } from 'vue-router';
import { aiClaimVettingAPI, moduleSettingsAPI } from '../../services/api';

const props = defineProps({
  batchId: { type: Number, default: null },
  /** Selected GHIMS item ids from the batch table; empty = scan all non-finalized */
  selectedItemIds: { type: Array, default: () => [] },
});

const emit = defineEmits(['corrected', 'open-item']);

const $q = useQuasar();
const $router = useRouter();

const moduleActive = ref(false);
const starting = ref(false);
const loadingReport = ref(false);
const correcting = ref(false);
const correctingRule = ref(null);
const error = ref('');
const job = ref(null);
const report = ref(null);
const selectedIds = ref([]);
const activeRule = ref(null);
let pollTimer = null;

const jobRunning = computed(() => ['queued', 'running'].includes(job.value?.status));

const jobBadgeColor = computed(() => {
  const s = job.value?.status;
  if (s === 'completed') return 'positive';
  if (s === 'failed') return 'negative';
  if (s === 'running' || s === 'queued') return 'primary';
  return 'grey';
});

const runLabel = computed(() => {
  const n = (props.selectedItemIds || []).length;
  if (n > 0) return `AI check ${n} selected`;
  return 'AI check all (non-finalized)';
});

const reportGroups = computed(() => {
  const groups = report.value?.groups || [];
  if (!activeRule.value) return groups;
  return groups.filter((g) => g.rule_code === activeRule.value);
});

const RULE_LABELS = {
  specialty_zoom: 'ZOOM specialty → OPDC',
  ghana_card_member_no: 'Ghana Card Member No → HIN',
};

function ruleLabel(code) {
  return RULE_LABELS[code] || code;
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
  if (checked) {
    selectedIds.value = Array.from(new Set([...selectedIds.value, ...ids]));
  } else {
    const remove = new Set(ids);
    selectedIds.value = selectedIds.value.filter((id) => !remove.has(id));
  }
}

function toggleFinding(id, checked) {
  if (checked && !selectedIds.value.includes(id)) selectedIds.value.push(id);
  if (!checked) selectedIds.value = selectedIds.value.filter((x) => x !== id);
}

function correctLabel(group) {
  const n = selectedInGroup(group).length;
  return n ? `Correct ${n}` : 'Correct selected';
}

function openClaim(itemId) {
  if (!itemId) return;
  emit('open-item', itemId);
  $router.push({ path: `/claims/ghims-import/item/${itemId}` });
}

function stopPoll() {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
}

async function checkModule() {
  try {
    const res = await moduleSettingsAPI.getStatus('ai_claims_vetting');
    moduleActive.value = !!res.data?.is_active;
  } catch {
    moduleActive.value = false;
  }
}

async function loadReport() {
  if (!props.batchId || !moduleActive.value) return;
  loadingReport.value = true;
  error.value = '';
  try {
    const res = await aiClaimVettingAPI.getBatchReport(props.batchId);
    report.value = res.data || null;
    if (res.data?.latest_job) job.value = res.data.latest_job;
    // Drop selections that no longer exist
    const alive = new Set(
      (res.data?.groups || []).flatMap((g) => (g.findings || []).map((f) => f.id))
    );
    selectedIds.value = selectedIds.value.filter((id) => alive.has(id));
  } catch (e) {
    if (e.response?.status === 403) moduleActive.value = false;
    else error.value = e.response?.data?.detail || e.message || 'Failed to load AI report';
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
              ? `AI check done: ${res.data.findings_count} finding(s) to review`
              : 'AI check done: no Phase-1 issues found',
            position: 'top',
          });
        } else if (res.data?.status === 'failed') {
          $q.notify({ type: 'negative', message: res.data.error_message || 'AI check failed', position: 'top' });
        }
        emit('corrected');
      }
    } catch {
      stopPoll();
    }
  }, 1200);
}

async function startAnalyze() {
  if (!props.batchId) return;
  starting.value = true;
  error.value = '';
  activeRule.value = null;
  try {
    const itemIds = (props.selectedItemIds || []).map((x) => Number(x)).filter(Boolean);
    const res = await aiClaimVettingAPI.startBatchAnalyze(props.batchId, {
      item_ids: itemIds.length ? itemIds : null,
    });
    job.value = res.data;
    $q.notify({
      type: 'info',
      message: `AI check started on ${res.data.total_items} claim(s)…`,
      position: 'top',
    });
    await pollJob(res.data.id);
  } catch (e) {
    error.value = e.response?.data?.detail || e.message || 'Failed to start AI check';
    $q.notify({ type: 'negative', message: error.value, position: 'top' });
  } finally {
    starting.value = false;
  }
}

async function bulkCorrect(ruleCode, findingIds) {
  if (!findingIds?.length) return;
  const isHin = ruleCode === 'ghana_card_member_no'
    || (!ruleCode && (report.value?.groups || []).some(
      (g) => g.rule_code === 'ghana_card_member_no'
        && g.findings.some((f) => findingIds.includes(f.id))
    ));

  const ok = await new Promise((resolve) => {
    $q.dialog({
      title: 'Correct selected findings',
      message: isHin
        ? `Apply corrections to ${findingIds.length} finding(s)? Ghana Card rows will call NHIA for HIN (may take a while).`
        : `Apply corrections to ${findingIds.length} finding(s)?`,
      cancel: true,
      persistent: true,
    }).onOk(() => resolve(true)).onCancel(() => resolve(false)).onDismiss(() => resolve(false));
  });
  if (!ok) return;

  correcting.value = true;
  correctingRule.value = ruleCode;
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
    emit('corrected');
  } catch (e) {
    $q.notify({
      type: 'negative',
      message: e.response?.data?.detail || e.message || 'Bulk correct failed',
      position: 'top',
    });
  } finally {
    correcting.value = false;
    correctingRule.value = null;
  }
}

async function bulkReject(findingIds) {
  if (!findingIds?.length) return;
  correcting.value = true;
  try {
    const res = await aiClaimVettingAPI.bulkDecideFindings({
      finding_ids: findingIds,
      decision: 'reject',
      note: 'Rejected from batch AI report',
    });
    $q.notify({
      type: 'positive',
      message: res.data?.message || 'Rejected selected findings',
      position: 'top',
    });
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

onMounted(async () => {
  await checkModule();
  if (moduleActive.value && props.batchId) {
    await loadReport();
    if (jobRunning.value && job.value?.id) {
      await pollJob(job.value.id);
    }
  }
});

watch(
  () => props.batchId,
  async (id) => {
    stopPoll();
    report.value = null;
    job.value = null;
    selectedIds.value = [];
    activeRule.value = null;
    if (id && moduleActive.value) {
      await loadReport();
      if (jobRunning.value && job.value?.id) await pollJob(job.value.id);
    }
  }
);

onBeforeUnmount(stopPoll);
</script>

<style scoped>
.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.85em;
}
</style>
