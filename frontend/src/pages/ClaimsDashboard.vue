<template>
  <q-page class="hms-page claims-dashboard-page">
    <HmsPageHeader
      title="Claims dashboard"
      subtitle="Monthly overview and submission advice. Default is previous month; lock keeps your selection on next open."
    >
      <template #actions>
        <HmsButton variant="ghost" size="sm" @click="$router.push('/claims')">Back</HmsButton>
        <HmsButton :variant="filtersLocked ? 'healthcare' : 'secondary'" size="sm" @click="toggleLock">
          {{ filtersLocked ? 'Unlock' : 'Lock' }}
        </HmsButton>
        <HmsButton
          v-if="trendStartMonth || trendEndMonth"
          variant="ghost"
          size="sm"
          @click="resetTrendRange"
        >
          Reset trend
        </HmsButton>
        <HmsButton variant="secondary" size="sm" :loading="loading" @click="loadDashboard">
          Refresh
        </HmsButton>
      </template>
    </HmsPageHeader>

    <section class="diag-panel">
      <div class="panel-head">
        <div>
          <div class="panel-title">Filters</div>
          <div class="panel-sub">Source, month, and optional trend range</div>
        </div>
        <div class="panel-actions">
          <HmsButton variant="ghost" size="sm" @click="resetToPreviousMonth">
            Reset to previous month
          </HmsButton>
        </div>
      </div>
      <div class="panel-body">
        <div class="row q-col-gutter-md items-end">
          <div class="col-12 col-sm-6 col-md-3">
            <q-select
              v-model="source"
              :options="sourceOptions"
              label="Source"
              dense
              filled
              emit-value
              map-options
              @update:model-value="onFiltersChanged"
            />
          </div>
          <div class="col-12 col-sm-6 col-md-3">
            <q-input
              v-model="month"
              filled
              dense
              type="month"
              label="Month"
              @update:model-value="onFiltersChanged"
            />
          </div>
          <div class="col-12 col-sm-6 col-md-3">
            <q-input
              v-model="trendStartMonth"
              filled
              dense
              type="month"
              label="Trend start"
              hint="Affects trend chart only"
              @update:model-value="onTrendChanged"
              clearable
            />
          </div>
          <div class="col-12 col-sm-6 col-md-3">
            <q-input
              v-model="trendEndMonth"
              filled
              dense
              type="month"
              label="Trend end"
              hint="Affects trend chart only"
              @update:model-value="onTrendChanged"
              clearable
            />
          </div>
        </div>

        <div v-if="dash" class="filter-meta">
          Showing <strong>{{ dash.month }}</strong> · <strong>{{ dash.source }}</strong> claims
        </div>
      </div>
    </section>

    <div v-if="loadError" class="error-banner" role="alert">
      {{ loadError }}
    </div>

    <div v-if="dash && !loading" class="claim-kpi-grid">
      <div class="claim-kpi">
        <div class="stat-top">
          <div class="claim-kpi__icon" style="color: var(--hms-accent); background: var(--hms-accent-muted)">
            <FileStack :size="18" />
          </div>
          <div class="claim-kpi__label">Total volume</div>
        </div>
        <div class="claim-kpi__value">{{ formatInt(dash.kpis.total_volume) }}</div>
      </div>
      <div class="claim-kpi">
        <div class="stat-top">
          <div class="claim-kpi__icon" style="color: var(--hms-healthcare); background: var(--hms-healthcare-muted)">
            <BadgeDollarSign :size="18" />
          </div>
          <div class="claim-kpi__label">Total cost</div>
        </div>
        <div class="claim-kpi__value">{{ formatMoney(dash.kpis.total_cost) }}</div>
      </div>
      <div class="claim-kpi">
        <div class="stat-top">
          <div class="claim-kpi__icon" style="color: var(--hms-info); background: var(--hms-info-muted)">
            <ChartLine :size="18" />
          </div>
          <div class="claim-kpi__label">Avg. cost / claim</div>
        </div>
        <div class="claim-kpi__value">{{ formatMoney(dash.kpis.avg_cost_per_claim) }}</div>
      </div>
    </div>

    <div v-if="dash && !loading" class="row q-col-gutter-md q-mb-lg">
      <div class="col-12 col-lg-7">
        <section class="diag-panel chart-card">
          <div class="panel-head">
            <div>
              <div class="panel-title">Claims trend (6 months)</div>
              <div class="panel-sub">Hover for details</div>
            </div>
          </div>
          <div class="panel-body">
            <ApexChart
              v-if="trendSeries.length"
              type="line"
              height="260"
              :options="trendOptions"
              :series="trendSeries"
            />
            <div v-else class="empty-hint">No trend data available.</div>
          </div>
        </section>
      </div>

      <div class="col-12 col-lg-5">
        <section class="diag-panel chart-card">
          <div class="panel-head">
            <div>
              <div class="panel-title">Top diagnoses (month)</div>
            </div>
          </div>
          <div class="panel-body">
            <ApexChart
              v-if="dxSeries.length"
              type="bar"
              height="300"
              :options="dxOptions"
              :series="dxSeries"
            />
            <div v-else class="empty-hint">No diagnosis summary available for this source/month yet.</div>
          </div>
        </section>
      </div>
    </div>

    <div v-if="dash && !loading" class="row q-col-gutter-md q-mb-lg">
      <div class="col-12 col-lg-6">
        <section class="diag-panel">
          <div class="panel-head">
            <div>
              <div class="panel-title">Submission advice: multiple ANC/PNC attendance</div>
              <div class="panel-sub">
                Some clients may attend multiple times, but insurance may pay only once. Consider OPDC where applicable.
              </div>
            </div>
          </div>
          <div class="panel-body">
            <q-table
              v-if="dash.advice?.multiple_attendance?.length"
              class="diag-table"
              :rows="dash.advice.multiple_attendance"
              :columns="multiAttendanceColumns"
              row-key="member_no"
              flat
              dense
              :rows-per-page-options="[10, 20, 50]"
            >
              <template v-slot:body-cell-claim_ids="props">
                <q-td :props="props">
                  <div class="row q-gutter-xs">
                    <q-badge v-for="cid in props.value.slice(0, 6)" :key="cid" color="grey-8" :label="cid" />
                    <span v-if="props.value.length > 6" class="text-caption text-grey-7">
                      +{{ props.value.length - 6 }} more
                    </span>
                  </div>
                </q-td>
              </template>
            </q-table>
            <div v-else class="empty-hint">No multiple attendance candidates found for this month.</div>
          </div>
        </section>
      </div>

      <div class="col-12 col-lg-6">
        <section class="diag-panel">
          <div class="panel-head">
            <div>
              <div class="panel-title">Potential duplicates</div>
              <div class="panel-sub">Heuristic duplicate groups. Review and correct if needed, or leave as-is.</div>
            </div>
          </div>
          <div class="panel-body">
            <q-table
              v-if="dash.advice?.potential_duplicates?.length"
              class="diag-table"
              :rows="dash.advice.potential_duplicates"
              :columns="dupColumns"
              row-key="key"
              flat
              dense
              :rows-per-page-options="[10, 20, 50]"
            >
              <template v-slot:body-cell-claim_ids="props">
                <q-td :props="props">
                  <div class="row q-gutter-xs">
                    <q-badge v-for="cid in props.value.slice(0, 6)" :key="cid" color="grey-8" :label="cid" />
                    <span v-if="props.value.length > 6" class="text-caption text-grey-7">
                      +{{ props.value.length - 6 }} more
                    </span>
                  </div>
                </q-td>
              </template>
            </q-table>
            <div v-else class="empty-hint">No potential duplicates detected for this month.</div>
          </div>
        </section>
      </div>
    </div>

    <div v-if="dash && !loading" class="row q-col-gutter-md q-mb-lg">
      <div class="col-12">
        <section class="diag-panel">
          <div class="panel-head">
            <div>
              <div class="panel-title">Top prescribed medicines (month)</div>
            </div>
          </div>
          <div class="panel-body">
            <ApexChart
              v-if="medSeries.length"
              type="bar"
              height="320"
              :options="medOptions"
              :series="medSeries"
            />
            <div v-else class="empty-hint">No medicines summary available for this source/month yet.</div>
          </div>
        </section>
      </div>
    </div>
  </q-page>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import HmsPageHeader from '../components/ui/HmsPageHeader.vue';
import HmsButton from '../components/ui/HmsButton.vue';
import { FileStack, BadgeDollarSign, ChartLine } from 'lucide-vue-next';
import { claimsAnalyticsAPI } from '../services/api';
import { useQuasar } from 'quasar';
import VueApexCharts from 'vue3-apexcharts';

const $q = useQuasar();
const ApexChart = VueApexCharts;

const DASH_LOCK_KEY = 'claimsDashboardLocked';
const DASH_FILTERS_KEY = 'claimsDashboardFilters';

const loading = ref(false);
const loadError = ref('');
const dash = ref(null);

const sourceOptions = [
  { label: 'Main claims', value: 'main' },
  { label: 'Imported claims', value: 'import' },
];

const source = ref('main');
const month = ref(previousMonth());
const filtersLocked = ref(false);

const multiAttendanceColumns = [
  { name: 'member_no', label: 'Member #', field: 'member_no', align: 'left' },
  { name: 'patient_name', label: 'Client', field: 'patient_name', align: 'left' },
  { name: 'attendance_count', label: 'Visits', field: 'attendance_count', align: 'right' },
  { name: 'suggested_specialty_attended', label: 'Suggest', field: 'suggested_specialty_attended', align: 'left' },
  { name: 'claim_ids', label: 'Claim IDs', field: 'claim_ids', align: 'left' },
];

const dupColumns = [
  { name: 'member_no', label: 'Member #', field: 'member_no', align: 'left' },
  { name: 'patient_name', label: 'Client', field: 'patient_name', align: 'left' },
  { name: 'count', label: 'Count', field: 'count', align: 'right' },
  { name: 'claim_ids', label: 'Claim IDs', field: 'claim_ids', align: 'left' },
];

function previousMonth() {
  const d = new Date();
  d.setDate(1);
  d.setMonth(d.getMonth() - 1);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  return `${y}-${m}`;
}

function resetToPreviousMonth() {
  month.value = previousMonth();
  onFiltersChanged();
}

function toggleLock() {
  filtersLocked.value = !filtersLocked.value;
  localStorage.setItem(DASH_LOCK_KEY, filtersLocked.value ? '1' : '0');
  if (!filtersLocked.value) {
    localStorage.removeItem(DASH_FILTERS_KEY);
    $q.notify({ type: 'info', message: 'Dashboard filters unlocked', timeout: 1500 });
    return;
  }
  persistFilters();
  $q.notify({ type: 'positive', message: 'Dashboard filters locked', timeout: 1500 });
}

function persistFilters() {
  if (!filtersLocked.value) return;
  const payload = {
    source: source.value,
    month: month.value,
    trendStartMonth: trendStartMonth.value,
    trendEndMonth: trendEndMonth.value,
  };
  localStorage.setItem(DASH_FILTERS_KEY, JSON.stringify(payload));
}

function loadFiltersIfLocked() {
  filtersLocked.value = localStorage.getItem(DASH_LOCK_KEY) === '1';
  if (!filtersLocked.value) return;
  const raw = localStorage.getItem(DASH_FILTERS_KEY);
  if (!raw) return;
  try {
    const parsed = JSON.parse(raw);
    if (parsed?.source) source.value = parsed.source;
    if (parsed?.month) month.value = parsed.month;
    if (parsed?.trendStartMonth) trendStartMonth.value = parsed.trendStartMonth;
    if (parsed?.trendEndMonth) trendEndMonth.value = parsed.trendEndMonth;
  } catch {
    void 0;
  }
}

async function loadDashboard() {
  loadError.value = '';
  loading.value = true;
  try {
    const params = { month: month.value, source: source.value };
    if (trendStartMonth.value) params.trend_start = trendStartMonth.value;
    if (trendEndMonth.value) params.trend_end = trendEndMonth.value;
    const res = await claimsAnalyticsAPI.getDashboard(params);
    dash.value = res.data;
    persistFilters();
  } catch (e) {
    dash.value = null;
    loadError.value = e.response?.data?.detail || e.message || 'Could not load dashboard';
  } finally {
    loading.value = false;
  }
}

function onFiltersChanged() {
  if (filtersLocked.value) persistFilters();
  void loadDashboard();
}

watch([source, month], () => {
  // avoid double fetch if user is typing in month input; type=month changes atomically
  void loadDashboard();
  persistFilters();
});

function formatInt(n) {
  const x = Number(n || 0);
  return x.toLocaleString();
}

function formatMoney(n) {
  const x = Number(n || 0);
  return x.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function shortMonth(yyyyMm) {
  const [y, m] = String(yyyyMm || '').split('-');
  if (!y || !m) return yyyyMm;
  const dt = new Date(Number(y), Number(m) - 1, 1);
  return dt.toLocaleString(undefined, { month: 'short' });
}

const trendStartMonth = ref(null); // YYYY-MM
const trendEndMonth = ref(null); // YYYY-MM

function resetTrendRange() {
  trendStartMonth.value = null;
  trendEndMonth.value = null;
  void loadDashboard();
}

function onTrendChanged() {
  // If only one side is set, let backend infer the other.
  void loadDashboard();
}

function yyyyMmToTs(yyyyMm) {
  const [y, m] = String(yyyyMm || '').split('-');
  if (!y || !m) return null;
  return new Date(Number(y), Number(m) - 1, 1).getTime();
}

const trendCategories = computed(() => (dash.value?.trend || []).map((p) => p.month));
const trendSeries = computed(() => {
  const pts = dash.value?.trend || [];
  if (!pts.length) return [];
  return [
    {
      name: 'Volume',
      type: 'column',
      data: pts
        .map((p) => ({ x: yyyyMmToTs(p.month), y: Number(p.volume || 0) }))
        .filter((p) => p.x != null),
    },
    {
      name: 'Cost',
      type: 'line',
      data: pts
        .map((p) => ({ x: yyyyMmToTs(p.month), y: Number(p.cost || 0) }))
        .filter((p) => p.x != null),
    },
  ];
});

const trendOptions = computed(() => {
  return {
    chart: {
      type: 'line',
      toolbar: { show: false },
      foreColor: 'rgba(255,255,255,0.75)',
      zoom: { enabled: true, type: 'x', autoScaleYaxis: false },
    },
    theme: { mode: 'dark' },
    stroke: { width: [0, 3], curve: 'smooth' },
    dataLabels: { enabled: false },
    colors: ['#90caf9', '#ef5350'],
    xaxis: {
      type: 'datetime',
      labels: {
        rotate: 0,
        formatter: (val) => {
          const m = tsToYyyyMm(val);
          return m ? shortMonth(m) : '';
        },
      },
      tooltip: { enabled: false },
    },
    yaxis: [
      {
        title: { text: 'Volume' },
        labels: { formatter: (v) => Number(v || 0).toLocaleString() },
      },
      {
        opposite: true,
        title: { text: 'Cost' },
        labels: { formatter: (v) => Number(v || 0).toLocaleString() },
      },
    ],
    tooltip: {
      shared: true,
      intersect: false,
      y: {
        formatter: (val, { seriesIndex }) => (seriesIndex === 0 ? formatInt(val) : formatMoney(val)),
      },
    },
    plotOptions: {
      bar: {
        columnWidth: '45%',
        borderRadius: 4,
      },
    },
    legend: { show: true, position: 'top', horizontalAlign: 'right' },
    grid: { borderColor: 'rgba(255,255,255,0.08)' },
  };
});

const dxItems = computed(() => dash.value?.top_diagnoses || []);
const dxSeries = computed(() => {
  if (!dxItems.value.length) return [];
  return [{ name: 'Count', data: dxItems.value.map((x) => Number(x.count || 0)) }];
});
const dxOptions = computed(() => {
  const cats = dxItems.value.map((x) => String(x.name || '').slice(0, 60));
  return {
    chart: { type: 'bar', toolbar: { show: false }, foreColor: 'rgba(255,255,255,0.75)' },
    theme: { mode: 'dark' },
    plotOptions: { bar: { horizontal: true, barHeight: '70%', borderRadius: 4 } },
    dataLabels: { enabled: false },
    colors: ['#90caf9'],
    xaxis: { categories: cats, labels: { formatter: (v) => Number(v || 0).toLocaleString() } },
    tooltip: { y: { formatter: (v) => Number(v || 0).toLocaleString() } },
    grid: { borderColor: 'rgba(255,255,255,0.08)' },
  };
});

const medItems = computed(() => dash.value?.top_medicines || []);
const medSeries = computed(() => {
  if (!medItems.value.length) return [];
  return [{ name: 'Count', data: medItems.value.map((x) => Number(x.count || 0)) }];
});
const medOptions = computed(() => {
  const cats = medItems.value.map((x) => String(x.name || '').slice(0, 60));
  return {
    chart: { type: 'bar', toolbar: { show: false }, foreColor: 'rgba(255,255,255,0.75)' },
    theme: { mode: 'dark' },
    plotOptions: { bar: { horizontal: true, barHeight: '65%', borderRadius: 4 } },
    dataLabels: { enabled: false },
    colors: ['#4db6ac'],
    xaxis: { categories: cats, labels: { formatter: (v) => Number(v || 0).toLocaleString() } },
    tooltip: { y: { formatter: (v) => Number(v || 0).toLocaleString() } },
    grid: { borderColor: 'rgba(255,255,255,0.08)' },
  };
});

onMounted(async () => {
  loadFiltersIfLocked();
  await loadDashboard();
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
.panel-actions { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; }
.panel-body { padding: 1rem; }
.stat-top {
  display: flex;
  align-items: center;
  gap: 0.65rem;
}
.filter-meta {
  margin-top: 0.75rem;
  font-size: var(--hms-text-xs);
  color: var(--hms-text-muted);
}
.error-banner {
  margin-bottom: 1rem;
  padding: 0.75rem 1rem;
  border-radius: var(--hms-radius-lg);
  background: var(--hms-critical-muted);
  color: var(--hms-critical);
  font-size: var(--hms-text-sm);
}
.chart-card { min-height: 280px; }
.empty-hint {
  font-size: var(--hms-text-sm);
  color: var(--hms-text-muted);
  padding: 0.5rem 0;
}
</style>

