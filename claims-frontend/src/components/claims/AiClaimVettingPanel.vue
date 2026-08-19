<template>
  <q-card v-if="moduleActive" flat bordered class="ai-vet-panel">
    <q-card-section>
      <div class="row items-center q-mb-sm">
        <div class="text-h6">AI Claims Vetting</div>
        <q-space />
        <q-btn
          flat
          dense
          color="primary"
          icon="psychology"
          label="Run AI check"
          :loading="analyzing"
          :disable="disabled"
          @click="runAnalyze"
        />
      </div>
      <div class="text-caption text-grey-7 q-mb-md">
        Choose a scan lane. Phase 1 is ClaimIT prep only; Coding adds diagnosis GDRG;
        Thorough adds procedures / medicines / investigations. Nothing changes until you approve.
      </div>
      <div class="row q-gutter-sm q-mb-md items-center">
        <q-option-group
          v-model="analysisMode"
          :options="[
            { label: 'Phase 1', value: 'phase1' },
            { label: 'Coding', value: 'coding' },
            { label: 'Thorough', value: 'thorough' },
          ]"
          type="radio"
          dense
          inline
          color="primary"
        />
      </div>

      <q-banner v-if="summary && !findings.length && !analyzing" class="bg-green-1" rounded dense>
        <template #avatar><q-icon name="check_circle" color="positive" /></template>
        {{ summary }}
      </q-banner>

      <q-banner v-if="error" class="bg-red-1 q-mb-sm" rounded dense>
        <template #avatar><q-icon name="error" color="negative" /></template>
        {{ error }}
      </q-banner>

      <div v-if="pendingFindings.length" class="q-gutter-md">
        <q-card
          v-for="f in pendingFindings"
          :key="f.id"
          flat
          bordered
          class="ai-finding"
          :class="`ai-finding--${f.severity}`"
        >
          <q-card-section>
            <div class="row items-center q-mb-xs">
              <q-badge :color="severityColor(f.severity)" :label="severityLabel(f.severity)" />
              <q-badge outline color="grey-7" :label="f.rule_code" class="q-ml-sm" />
              <q-space />
            </div>
            <div class="text-subtitle2">{{ f.finding }}</div>
            <div class="text-body2 q-mt-xs">{{ f.explanation }}</div>
            <div class="text-body2 text-weight-medium q-mt-sm">Suggested: {{ f.recommendation }}</div>
            <div v-if="isDrgChoice(f)" class="q-mt-sm">
              <q-select
                dense
                outlined
                emit-value
                map-options
                label="Correct GDRG"
                :options="drgOptions(f)"
                v-model="chosenDrg[f.id]"
                style="max-width: 360px"
              />
            </div>
            <div class="row q-gutter-sm q-mt-md">
              <q-btn
                v-if="!isReviewOnly(f)"
                color="positive"
                unelevated
                dense
                :label="isDrgChoice(f) ? 'Apply GDRG' : 'Accept'"
                :loading="decidingId === f.id && decidingAction === 'accept'"
                :disable="disabled || decidingId === f.id || (isDrgChoice(f) && !chosenDrgValue(f))"
                @click="decide(f, 'accept')"
              />
              <q-btn
                color="negative"
                outline
                dense
                label="Reject"
                :loading="decidingId === f.id && decidingAction === 'reject'"
                :disable="disabled || decidingId === f.id"
                @click="decide(f, 'reject')"
              />
              <q-btn
                color="primary"
                flat
                dense
                label="I'll edit manually"
                :loading="decidingId === f.id && decidingAction === 'edited'"
                :disable="disabled || decidingId === f.id"
                @click="decide(f, 'edited')"
              />
            </div>
          </q-card-section>
        </q-card>
      </div>

      <div v-else-if="!analyzing && !summary && !error" class="text-caption text-grey-6">
        Click <strong>Run AI check</strong> to scan this imported claim.
      </div>

      <div v-if="resolvedFindings.length" class="q-mt-md">
        <div class="text-caption text-grey-7 q-mb-xs">Resolved ({{ resolvedFindings.length }})</div>
        <div
          v-for="f in resolvedFindings.slice(0, 5)"
          :key="`r-${f.id}`"
          class="text-caption text-grey-6"
        >
          {{ f.status }} · {{ f.finding }}
        </div>
      </div>
    </q-card-section>
  </q-card>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue';
import { useQuasar } from 'quasar';
import { aiClaimVettingAPI, moduleSettingsAPI } from '../../services/api';

const props = defineProps({
  itemId: { type: Number, required: true },
  disabled: { type: Boolean, default: false },
  autoRun: { type: Boolean, default: true },
});

const emit = defineEmits(['payload-updated']);

const $q = useQuasar();
const moduleActive = ref(false);
const analyzing = ref(false);
const findings = ref([]);
const summary = ref('');
const error = ref('');
const decidingId = ref(null);
const decidingAction = ref('');
const analysisMode = ref('phase1');
const chosenDrg = ref({});

const pendingFindings = computed(() => findings.value.filter((f) => f.status === 'pending'));
const resolvedFindings = computed(() => findings.value.filter((f) => f.status !== 'pending'));

const DRG_CHOICE = new Set(['diagnosis_drg_mismatch', 'procedure_drg_mismatch']);
const REVIEW_ONLY = new Set([
  'diagnosis_icd_unmapped',
  'procedure_gdrg_unknown',
  'medicine_code_unknown',
  'investigation_gdrg_unknown',
]);

function isDrgChoice(f) {
  return DRG_CHOICE.has(f?.rule_code);
}

function isReviewOnly(f) {
  const code = f?.rule_code || '';
  const actionType = f?.suggested_action?.type || '';
  if (REVIEW_ONLY.has(code)) return true;
  if (code.startsWith('llm_')) return true;
  if (String(actionType).startsWith('review_')) return true;
  return false;
}

function drgOptions(f) {
  const allowed = f?.suggested_action?.details?.allowed_drgs || [];
  return allowed.map((a) => ({
    label: a.drg_description ? `${a.drg_code} — ${a.drg_description}` : a.drg_code,
    value: a.drg_code,
  }));
}

function preferredDrg(f) {
  const action = f?.suggested_action || {};
  return (action.value || action.details?.preferred || '').trim();
}

function chosenDrgValue(f) {
  return (chosenDrg.value[f.id] || preferredDrg(f) || '').trim();
}

function severityColor(sev) {
  if (sev === 'critical') return 'negative';
  if (sev === 'warning') return 'orange';
  return 'blue-grey';
}

function severityLabel(sev) {
  if (sev === 'critical') return 'Critical';
  if (sev === 'warning') return 'Warning';
  return 'Review needed';
}

async function checkModule() {
  try {
    const res = await moduleSettingsAPI.getStatus('ai_claims_vetting');
    moduleActive.value = !!res.data?.is_active;
  } catch {
    moduleActive.value = false;
  }
}

async function loadFindings() {
  if (!moduleActive.value || !props.itemId) return;
  try {
    const res = await aiClaimVettingAPI.listGhimsFindings(props.itemId);
    findings.value = Array.isArray(res.data) ? res.data : [];
  } catch (e) {
    // Module may have been toggled off mid-session
    if (e.response?.status === 403) {
      moduleActive.value = false;
    }
  }
}

async function runAnalyze() {
  if (!props.itemId || props.disabled) return;
  analyzing.value = true;
  error.value = '';
  try {
    const res = await aiClaimVettingAPI.analyzeGhimsItem(props.itemId, {
      mode: analysisMode.value,
    });
    summary.value = res.data?.summary || '';
    findings.value = Array.isArray(res.data?.findings) ? res.data.findings : [];
    const nextChosen = { ...chosenDrg.value };
    for (const f of findings.value) {
      if (isDrgChoice(f) && preferredDrg(f) && !nextChosen[f.id]) {
        nextChosen[f.id] = preferredDrg(f);
      }
    }
    chosenDrg.value = nextChosen;
    if (!findings.value.length && Array.isArray(res.data?.preview_findings)) {
      // No persisted rows when clean — keep summary
    }
    $q.notify({
      type: findings.value.some((f) => f.status === 'pending') ? 'warning' : 'positive',
      message: summary.value || 'AI check complete',
      position: 'top',
    });
  } catch (e) {
    const detail = e.response?.data?.detail || e.message || 'AI check failed';
    error.value = detail;
    if (e.response?.status === 403) {
      moduleActive.value = false;
    }
    $q.notify({ type: 'negative', message: detail, position: 'top' });
  } finally {
    analyzing.value = false;
  }
}

async function decide(finding, decision) {
  decidingId.value = finding.id;
  decidingAction.value = decision;
  try {
    const payload = { decision };
    if (decision === 'accept' && isDrgChoice(finding)) {
      const value = chosenDrgValue(finding);
      if (!value) {
        $q.notify({ type: 'warning', message: 'Choose a GDRG first', position: 'top' });
        decidingId.value = null;
        decidingAction.value = '';
        return;
      }
      payload.chosen_value = value;
    }
    const res = await aiClaimVettingAPI.decideFinding(finding.id, payload);
    const updated = res.data?.finding;
    if (updated) {
      const idx = findings.value.findIndex((f) => f.id === updated.id);
      if (idx >= 0) findings.value.splice(idx, 1, updated);
    }
    if (res.data?.payload) {
      emit('payload-updated', res.data.payload);
    }
    $q.notify({
      type: 'positive',
      message: res.data?.message || `Marked as ${decision}`,
      position: 'top',
    });
  } catch (e) {
    const detail = e.response?.data?.detail || e.message || 'Failed to record decision';
    // Offer reopen path is now automatic — surface message only
    $q.notify({
      type: 'negative',
      message: detail,
      position: 'top',
    });
  } finally {
    decidingId.value = null;
    decidingAction.value = '';
  }
}

onMounted(async () => {
  await checkModule();
  if (moduleActive.value) {
    await loadFindings();
    if (props.autoRun && props.itemId && !props.disabled) {
      const hasPending = findings.value.some((f) => f.status === 'pending');
      if (!hasPending) {
        await runAnalyze();
      } else {
        summary.value = `${findings.value.filter((f) => f.status === 'pending').length} pending finding(s).`;
      }
    }
  }
});

watch(
  () => props.itemId,
  async (id) => {
    findings.value = [];
    summary.value = '';
    error.value = '';
    if (!id || !moduleActive.value) return;
    await loadFindings();
    if (props.autoRun && !props.disabled) {
      await runAnalyze();
    }
  }
);
</script>

<style scoped>
.ai-finding--critical {
  border-left: 4px solid var(--q-negative);
}
.ai-finding--warning {
  border-left: 4px solid #fb8c00;
}
.ai-finding--review_needed {
  border-left: 4px solid #607d8b;
}
</style>
