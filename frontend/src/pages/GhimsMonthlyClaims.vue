<template>
  <q-page class="hms-page">
    <HmsPageHeader
      :title="monthKey ? (redirecting ? 'Opening month…' : monthTitle) : 'GHIMS monthly claims'"
      :subtitle="monthKey
        ? 'Syncing from GHIMS, then opening the claims workbench…'
        : 'Pick a month. GHIMS-approved claims fall into that folder — if it does not exist yet, it is created.'"
    >
      <template #actions>
        <HmsButton v-if="monthKey" variant="ghost" size="sm" @click="$router.push('/claims/ghims-months')">All months</HmsButton>
        <HmsButton variant="ghost" size="sm" @click="$router.push('/claims')">Back</HmsButton>
      </template>
    </HmsPageHeader>

    <div v-if="error" class="q-mb-md text-negative">{{ error }}</div>

    <template v-if="!monthKey">
      <div class="cal-year-bar">
        <q-btn round flat icon="chevron_left" @click="calendarYear -= 1" />
        <div class="cal-year">{{ calendarYear }}</div>
        <q-btn round flat icon="chevron_right" @click="calendarYear += 1" />
        <q-space />
        <HmsButton variant="primary" size="sm" :loading="loadingMonths" @click="loadMonths">Refresh from GHIMS</HmsButton>
      </div>
      <div v-if="loadingMonths" class="text-grey-7 q-pa-md">Loading months from GHIMS…</div>
      <div v-else class="year-grid">
        <button
          v-for="cell in yearCells"
          :key="cell.month_key"
          type="button"
          class="month-cell"
          :class="{
            'month-cell--current': cell.is_current,
            'month-cell--has': cell.ghims_count > 0 || cell.aghims_count > 0,
          }"
          @click="openMonth(cell.month_key)"
        >
          <div class="month-cell__name">{{ cell.name }}</div>
          <div class="month-cell__count">
            <template v-if="cell.ghims_count">{{ cell.ghims_count }} claims</template>
            <template v-else>No claims yet</template>
          </div>
          <div class="month-cell__hint">{{ cell.label }}</div>
        </button>
      </div>
    </template>

    <template v-else>
      <div class="text-grey-7 q-pa-md" v-if="!error">
        {{ redirecting ? 'Opening the XML-import-style claims workbench…' : 'Preparing month…' }}
      </div>
    </template>
  </q-page>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useQuasar } from 'quasar';
import HmsPageHeader from '../components/ui/HmsPageHeader.vue';
import HmsButton from '../components/ui/HmsButton.vue';
import { claimsAPI } from '../services/api';

const MONTH_NAMES = ['January','February','March','April','May','June','July','August','September','October','November','December'];

const $route = useRoute();
const $router = useRouter();
const $q = useQuasar();

const monthKey = computed(() => String($route.params.monthKey || '').trim());
const error = ref('');
const loadingMonths = ref(false);
const redirecting = ref(false);
const months = ref([]);
const calendarYear = ref(new Date().getFullYear());

function pad2(n) {
  return String(n).padStart(2, '0');
}
function labelForKey(key) {
  const [y, m] = String(key || '').split('-');
  const idx = Number(m) - 1;
  if (!y || idx < 0 || idx > 11) return `${key} claims`;
  return `${MONTH_NAMES[idx]} ${y} claims`;
}

const monthTitle = computed(() => labelForKey(monthKey.value));

const yearCells = computed(() => {
  const now = new Date();
  const currentKey = `${now.getFullYear()}-${pad2(now.getMonth() + 1)}`;
  return MONTH_NAMES.map((name, i) => {
    const key = `${calendarYear.value}-${pad2(i + 1)}`;
    const found = (months.value || []).find((m) => m.month_key === key);
    return {
      month_key: key,
      name,
      label: `${name} ${calendarYear.value} claims`,
      ghims_count: Number(found?.ghims_count || 0),
      aghims_count: Number(found?.aghims_count || 0),
      is_current: key === currentKey,
    };
  });
});

function openMonth(key) {
  $router.push(`/claims/ghims-months/${key}`);
}

async function loadMonths() {
  loadingMonths.value = true;
  error.value = '';
  try {
    const res = await claimsAPI.listGhimsMonths();
    months.value = res.data || [];
  } catch (e) {
    error.value = e?.response?.data?.detail || e?.message || 'Could not load GHIMS months';
  } finally {
    loadingMonths.value = false;
  }
}

async function openMonthWorkbench() {
  if (!monthKey.value) return;
  redirecting.value = true;
  error.value = '';
  try {
    const res = await claimsAPI.syncGhimsMonth(monthKey.value);
    const d = res.data || {};
    const batchId = d.batch_id;
    if (!batchId) {
      throw new Error('Sync did not return a batch_id');
    }
    if (d.created) {
      $q.notify({
        type: 'positive',
        message: `Pulled ${d.created} new GHIMS claim(s) into ${d.label || 'this month'}.`,
        position: 'top',
      });
    }
    await $router.replace(`/claims/ghims-import/batch/${batchId}?fromMonth=${encodeURIComponent(monthKey.value)}`);
  } catch (e) {
    error.value = e?.response?.data?.detail || e?.message || 'Could not open this month from GHIMS';
    redirecting.value = false;
  }
}

watch(monthKey, (key) => {
  if (key) openMonthWorkbench();
  else loadMonths();
});

onMounted(() => {
  if (monthKey.value) {
    const [y] = monthKey.value.split('-');
    if (y) calendarYear.value = Number(y);
    openMonthWorkbench();
  } else {
    loadMonths();
  }
});
</script>

<style scoped>
.cal-year-bar {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  margin-bottom: 1rem;
}
.cal-year {
  min-width: 5rem;
  text-align: center;
  font-size: 1.45rem;
  font-weight: 750;
}
.year-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.85rem;
}
.month-cell {
  text-align: left;
  border: 1px solid var(--hms-border);
  background: var(--hms-panel-bg);
  border-radius: 1.1rem;
  padding: 1rem 1.1rem 0.9rem;
  cursor: pointer;
  min-height: 7.2rem;
}
.month-cell:hover { transform: translateY(-2px); }
.month-cell--current { outline: 2px solid var(--hms-accent); }
.month-cell--has { border-color: color-mix(in srgb, var(--hms-healthcare) 55%, var(--hms-border)); }
.month-cell__name { font-weight: 750; font-size: 1.15rem; color: var(--hms-text-primary); }
.month-cell__count { margin-top: 0.35rem; font-size: 0.92rem; color: var(--hms-text-primary); }
.month-cell__hint { margin-top: 0.2rem; font-size: 0.78rem; color: var(--hms-text-muted); }
@media (max-width: 900px) {
  .year-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
</style>
