<template>
  <q-page class="hms-page inventory-dashboard-page">
    <LicenseStatusBanner />

    <HmsPageHeader
      title="Inventory"
      subtitle="Stock levels, usage, requisitions, and trends across stores and departments."
    >
      <template #actions>
        <HmsButton variant="secondary" size="sm" :loading="loading" @click="loadDashboard">
          Refresh
        </HmsButton>
      </template>
    </HmsPageHeader>

    <section class="diag-panel">
      <div class="panel-head">
        <div>
          <div class="panel-title">Filters</div>
          <div class="panel-sub">
            <template v-if="canFilterDashboardStores || canFilterDashboardDepartments">
              Scope by store, department, and period (Management / Admin / Pharmacy-wide roles).
            </template>
            <template v-else>
              Scoped to your assigned store or department; filters are fixed.
            </template>
          </div>
        </div>
      </div>
      <div class="panel-body">
        <div class="row q-col-gutter-md items-end">
          <div class="col-12 col-sm-6 col-md-3">
            <q-select
              v-model="filters.storeId"
              :options="storeOptions"
              label="Store"
              dense
              filled
              :clearable="canFilterDashboardStores"
              :disable="!canFilterDashboardStores"
              emit-value
              map-options
              @update:model-value="loadDashboard"
            />
          </div>
          <div class="col-12 col-sm-6 col-md-4">
            <q-select
              v-model="filters.department"
              :options="departmentOptions"
              label="Department / unit"
              dense
              filled
              :clearable="canFilterDashboardDepartments"
              :disable="!canFilterDashboardDepartments"
              emit-value
              map-options
              use-input
              input-debounce="200"
              @filter="filterDepartments"
              @update:model-value="loadDashboard"
            />
          </div>
          <div class="col-12 col-sm-6 col-md-2">
            <q-select
              v-model="filters.days"
              :options="periodOptions"
              label="Period"
              dense
              filled
              emit-value
              map-options
              @update:model-value="loadDashboard"
            />
          </div>
        </div>
        <div v-if="dash" class="filter-meta">
          Showing
          <template v-if="dash.store_name"><strong>{{ dash.store_name }}</strong> store</template>
          <template v-else>all stores (approved stock)</template>
          ·
          <template v-if="dash.department"><strong>{{ dash.department }}</strong></template>
          <template v-else>all departments</template>
          · last <strong>{{ dash.period_days }}</strong> days
        </div>
      </div>
    </section>

    <div v-if="loadError" class="error-banner" role="alert">
      {{ loadError }}
    </div>

    <div v-if="dash && !loading" class="claim-kpi-grid inv-kpi-grid">
      <div v-if="showStoreStockKpi" class="claim-kpi">
        <div class="stat-top">
          <div class="claim-kpi__icon" style="color: var(--hms-accent); background: var(--hms-accent-muted)">
            <Package :size="18" />
          </div>
          <div class="claim-kpi__label">Store stock (qty)</div>
        </div>
        <div class="claim-kpi__value">{{ formatNum(dash.kpis.approved_store_stock_qty) }}</div>
        <div class="claim-kpi__meta">{{ dash.kpis.approved_store_stock_lines }} lines</div>
      </div>
      <div v-if="dash.kpis.ward_stock_total_qty != null" class="claim-kpi">
        <div class="stat-top">
          <div class="claim-kpi__icon" style="color: var(--hms-healthcare); background: var(--hms-healthcare-muted)">
            <Warehouse :size="18" />
          </div>
          <div class="claim-kpi__label">Dept ward stock</div>
        </div>
        <div class="claim-kpi__value">{{ formatNum(dash.kpis.ward_stock_total_qty) }}</div>
        <div class="claim-kpi__meta">{{ dash.kpis.ward_stock_lines }} lines</div>
      </div>
      <div class="claim-kpi">
        <div class="stat-top">
          <div class="claim-kpi__icon" style="color: var(--hms-warning); background: var(--hms-warning-muted)">
            <Clock :size="18" />
          </div>
          <div class="claim-kpi__label">Req. pending</div>
        </div>
        <div class="claim-kpi__value">{{ dash.kpis.requisitions_pending }}</div>
        <div class="claim-kpi__meta">{{ dash.kpis.requisitions_in_flight }} in flight</div>
      </div>
      <div class="claim-kpi">
        <div class="stat-top">
          <div class="claim-kpi__icon" style="color: var(--hms-info); background: var(--hms-info-muted)">
            <ClipboardList :size="18" />
          </div>
          <div class="claim-kpi__label">Req. (period)</div>
        </div>
        <div class="claim-kpi__value">{{ dash.kpis.requisitions_created_period }}</div>
        <div class="claim-kpi__meta">{{ dash.kpis.requisitions_fulfilled_period }} fulfilled</div>
      </div>
      <div class="claim-kpi">
        <div class="stat-top">
          <div class="claim-kpi__icon" style="color: var(--hms-success); background: var(--hms-success-muted)">
            <Activity :size="18" />
          </div>
          <div class="claim-kpi__label">Usage (units)</div>
        </div>
        <div class="claim-kpi__value">{{ formatNum(dash.kpis.debit_units_period) }}</div>
        <div class="claim-kpi__meta">{{ dash.kpis.debit_events_period }} debits</div>
      </div>
    </div>

    <div v-if="dash && !loading" class="row q-col-gutter-md q-mb-lg">
      <div class="col-12 col-lg-6">
        <section class="diag-panel chart-card">
          <div class="panel-head">
            <div>
              <div class="panel-title">Usage trend (inventory debits)</div>
              <div class="panel-sub">Units debited per day (IPD + Companion)</div>
            </div>
          </div>
          <div class="panel-body">
            <div class="chart-area usage-chart">
              <div
                v-for="(p, idx) in dash.series"
                :key="'u-' + p.date"
                class="chart-bar"
                :title="p.date + ': ' + formatNum(p.usage_units)"
              >
                <div
                  class="chart-bar-fill usage"
                  :style="{ height: usageBarHeight(p) + '%' }"
                />
                <span v-if="idx % labelStep === 0" class="chart-label">{{ shortDate(p.date) }}</span>
              </div>
            </div>
          </div>
        </section>
      </div>
      <div class="col-12 col-lg-6">
        <section class="diag-panel chart-card">
          <div class="panel-head">
            <div>
              <div class="panel-title">Requisitions trend</div>
              <div class="panel-sub">Created vs fulfilled per day</div>
            </div>
          </div>
          <div class="panel-body">
            <div class="chart-area req-chart">
              <div
                v-for="(p, idx) in dash.series"
                :key="'r-' + p.date"
                class="chart-bar-group"
              >
                <div class="bar-pair">
                  <div
                    class="mini-bar created"
                    :style="{ height: rqBarHeight(p, 'created') + '%' }"
                    :title="'Created ' + p.date + ': ' + p.requisitions_created"
                  />
                  <div
                    class="mini-bar fulfilled"
                    :style="{ height: rqBarHeight(p, 'fulfilled') + '%' }"
                    :title="'Fulfilled ' + p.date + ': ' + p.requisitions_fulfilled"
                  />
                </div>
                <span v-if="idx % labelStep === 0" class="chart-label">{{ shortDate(p.date) }}</span>
              </div>
            </div>
            <div class="chart-legend">
              <span><span class="legend-dot created" /> Created</span>
              <span><span class="legend-dot fulfilled" /> Fulfilled</span>
            </div>
          </div>
        </section>
      </div>
    </div>

    <div v-if="dash && !loading" class="row q-col-gutter-md q-mb-lg">
      <div class="col-12 col-lg-6">
        <section class="diag-panel">
          <div class="panel-head">
            <div>
              <div class="panel-title">Top products (period)</div>
              <div class="panel-sub">Highest debit and requisition volume</div>
            </div>
          </div>
          <div class="panel-body">
            <div v-if="!dash.top_products.length" class="empty-hint">No product movement in this period.</div>
            <div v-for="tp in dash.top_products" :key="tp.product_code" class="top-product-row">
              <div class="top-product-head">
                <div class="top-product-name">{{ tp.product_name }}</div>
                <div class="top-product-code">{{ tp.product_code }}</div>
              </div>
              <q-linear-progress
                :value="topProductRatio(tp)"
                color="primary"
                track-color="grey-4"
                size="8px"
                rounded
                class="q-mt-xs"
              />
              <div class="top-product-meta">
                Debits {{ formatNum(tp.debit_qty) }} · Req. {{ formatNum(tp.requisition_requested_qty) }}
              </div>
            </div>
          </div>
        </section>
      </div>
      <div class="col-12 col-lg-6">
        <section class="diag-panel">
          <div class="panel-head">
            <div>
              <div class="panel-title">Recent activity</div>
              <div class="panel-sub">Latest requisitions and debits</div>
            </div>
          </div>
          <div class="panel-body">
            <q-list bordered separator class="activity-list">
              <q-item v-for="(ev, i) in dash.recent_events" :key="i" dense>
                <q-item-section avatar>
                  <q-icon :name="eventIcon(ev.kind)" :color="eventColor(ev.kind)" size="sm" />
                </q-item-section>
                <q-item-section>
                  <q-item-label class="text-weight-medium">{{ ev.label }}</q-item-label>
                  <q-item-label caption>{{ ev.detail }}</q-item-label>
                </q-item-section>
                <q-item-section side>
                  <span class="activity-time">{{ formatEventTime(ev.at) }}</span>
                </q-item-section>
              </q-item>
            </q-list>
          </div>
        </section>
      </div>
    </div>

    <q-inner-loading :showing="loading" color="primary" />

    <section class="inv-workspace">
      <div class="group-bar">
        <div>
          <h2 class="group-title">Quick links</h2>
          <p class="group-note">Open a module to work with inventory</p>
        </div>
      </div>
      <div class="module-grid">
        <HmsCard
          v-for="mod in quickLinkModules"
          :key="mod.path"
          dense
          hoverable
          class="module-card"
          role="button"
          tabindex="0"
          @click="navigateToModule(mod.path)"
          @keydown.enter="navigateToModule(mod.path)"
          @keydown.space.prevent="navigateToModule(mod.path)"
        >
          <div class="module-icon" :style="{ color: mod.color, background: mod.bg }">
            <component :is="mod.icon" :size="20" />
          </div>
          <div class="module-copy">
            <div class="module-title">{{ mod.title }}</div>
            <div v-if="mod.hint" class="module-hint">{{ mod.hint }}</div>
          </div>
          <ArrowRight :size="16" class="module-arrow" />
        </HmsCard>
      </div>
    </section>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useAuthStore } from '../stores/auth';
import LicenseStatusBanner from '../components/LicenseStatusBanner.vue';
import HmsPageHeader from '../components/ui/HmsPageHeader.vue';
import HmsButton from '../components/ui/HmsButton.vue';
import HmsCard from '../components/ui/HmsCard.vue';
import {
  Package,
  Warehouse,
  Clock,
  ClipboardList,
  Activity,
  ShoppingCart,
  BarChart3,
  Boxes,
  PackageMinus,
  Store,
  DoorOpen,
  ArrowRight,
} from 'lucide-vue-next';
import { useRouter } from 'vue-router';
import { inventoryAnalyticsAPI, storesAPI, wardsAPI } from '../services/api';
import { storeSelectLabel } from '../utils/storeKind';

const router = useRouter();
const authStore = useAuthStore();

const loading = ref(false);
const loadError = ref('');
const dash = ref(null);
const filters = ref({
  storeId: null,
  department: null,
  days: 30,
});
const storeOptions = ref([]);
const allDepartmentOptions = ref([]);
const departmentOptions = ref([]);

const periodOptions = [
  { label: '7 days', value: 7 },
  { label: '30 days', value: 30 },
  { label: '90 days', value: 90 },
];

const canAccessRequisitions = computed(() => authStore.canAccessInventoryMode);
const canAccessDepartmentStock = computed(() => authStore.canAccessInventoryMode);
const canAccessStoreStock = computed(() => {
  if (authStore.isSuperAdmin) return true;
  return (
    authStore.canAccess([
      'Admin',
      'Management',
      'Store Manager',
      'Department Head',
      'Pharmacy Head',
      'Pharmacy',
    ]) ||
    Boolean(authStore.user?.has_store_manager_assignment) ||
    Boolean(authStore.user?.has_store_department_head_assignment)
  );
});
const canAccessStoreManagement = computed(() => authStore.canAccess(['Admin']));
const canAccessDepartmentManagement = computed(() => authStore.canAccess(['Admin']));
const canAccessInventoryDebits = computed(() =>
  authStore.canAccess(['Pharmacy', 'Pharmacy Head', 'Store Manager', 'Management', 'Admin'])
);

const canFilterDashboardStores = computed(() =>
  Boolean(authStore.user?.inventory_dashboard_can_filter_stores)
);
const canFilterDashboardDepartments = computed(() =>
  Boolean(authStore.user?.inventory_dashboard_can_filter_departments)
);
/** Hide central store KPI for department IC/deputy-only (not store-assigned). */
const showStoreStockKpi = computed(() => {
  const u = authStore.user;
  if (!u) return true;
  const icOnly =
    (u.ic_managed_department_names?.length || 0) > 0 &&
    !(u.assigned_store_ids?.length || 0);
  return !icOnly;
});

const hasAnyAccess = computed(() => {
  return (
    canAccessRequisitions.value ||
    canAccessDepartmentStock.value ||
    canAccessStoreStock.value ||
    canAccessStoreManagement.value ||
    canAccessDepartmentManagement.value ||
    canAccessInventoryDebits.value
  );
});

const quickLinkModules = computed(() => {
  const all = [
    {
      show: canAccessRequisitions.value,
      title: 'Requisitions',
      hint: 'Request and track store supplies',
      path: '/inventory-mode/requisitions',
      icon: ShoppingCart,
      color: 'var(--hms-accent)',
      bg: 'var(--hms-accent-muted)',
    },
    {
      show: canAccessRequisitions.value,
      title: 'Reports',
      hint: 'Requisitions & store stock CSV',
      path: '/inventory-mode/reports',
      icon: BarChart3,
      color: 'var(--hms-info)',
      bg: 'var(--hms-info-muted)',
    },
    {
      show: canAccessDepartmentStock.value,
      title: 'Department / ward stock',
      hint: 'Unit-level stock',
      path: '/inventory-mode/ward-stock',
      icon: Warehouse,
      color: 'var(--hms-healthcare)',
      bg: 'var(--hms-healthcare-muted)',
    },
    {
      show: canAccessStoreStock.value,
      title: 'Store stock',
      hint: 'Central store batches & approval',
      path: '/inventory-mode/store-stock',
      icon: Boxes,
      color: 'var(--hms-accent)',
      bg: 'var(--hms-accent-muted)',
    },
    {
      show: canAccessInventoryDebits.value,
      title: 'Inventory debits',
      hint: 'Release & ward usage',
      path: '/inventory-mode/inventory-debits',
      icon: PackageMinus,
      color: 'var(--hms-success)',
      bg: 'var(--hms-success-muted)',
    },
    {
      show: canAccessStoreManagement.value,
      title: 'Store management',
      hint: 'Configure central stores',
      path: '/inventory-mode/store-management',
      icon: Store,
      color: 'var(--hms-warning)',
      bg: 'var(--hms-warning-muted)',
    },
    {
      show: canAccessDepartmentManagement.value,
      title: 'Department management',
      hint: 'Configure departments and wards',
      path: '/inventory-mode/ward-management',
      icon: DoorOpen,
      color: 'var(--hms-info)',
      bg: 'var(--hms-info-muted)',
    },
  ];
  return all.filter((m) => m.show);
});

const maxUsage = computed(() => {
  if (!dash.value?.series?.length) return 1;
  return Math.max(1, ...dash.value.series.map((p) => Number(p.usage_units) || 0));
});

const maxRq = computed(() => {
  if (!dash.value?.series?.length) return 1;
  let m = 1;
  for (const p of dash.value.series) {
    m = Math.max(m, Number(p.requisitions_created) || 0, Number(p.requisitions_fulfilled) || 0);
  }
  return m;
});

const maxTopProduct = computed(() => {
  if (!dash.value?.top_products?.length) return 1;
  return Math.max(
    1,
    ...dash.value.top_products.map((t) => (Number(t.debit_qty) || 0) + (Number(t.requisition_requested_qty) || 0))
  );
});

const labelStep = computed(() => {
  const n = dash.value?.series?.length || 0;
  if (n <= 14) return 2;
  if (n <= 35) return 5;
  return 7;
});

function formatNum(v) {
  if (v == null || !Number.isFinite(Number(v))) return '0';
  const n = Number(v);
  return n >= 1000 ? n.toLocaleString(undefined, { maximumFractionDigits: 1 }) : n.toFixed(n % 1 === 0 ? 0 : 2);
}

function shortDate(iso) {
  if (!iso) return '';
  const p = iso.split('-');
  return p.length === 3 ? `${p[1]}/${p[2]}` : iso;
}

function usageBarHeight(p) {
  const u = Number(p.usage_units) || 0;
  return Math.max(4, (u / maxUsage.value) * 100);
}

function rqBarHeight(p, kind) {
  const v = kind === 'created' ? Number(p.requisitions_created) : Number(p.requisitions_fulfilled);
  return Math.max(2, (v / maxRq.value) * 100);
}

function topProductRatio(tp) {
  const t = (Number(tp.debit_qty) || 0) + (Number(tp.requisition_requested_qty) || 0);
  return Math.min(1, t / maxTopProduct.value);
}

function eventIcon(kind) {
  if (kind === 'requisition') return 'shopping_cart';
  if (kind === 'companion_debit') return 'badge';
  return 'medical_services';
}

function eventColor(kind) {
  if (kind === 'requisition') return 'primary';
  if (kind === 'companion_debit') return 'accent';
  return 'secondary';
}

function formatEventTime(at) {
  if (!at) return '';
  try {
    return new Date(at).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  } catch {
    return '';
  }
}

async function loadStores() {
  try {
    const res = await storesAPI.getAll(true);
    storeOptions.value = (res.data || []).map((s) => ({ label: storeSelectLabel(s), value: s.id }));
  } catch {
    storeOptions.value = [];
  }
}

async function loadDepartments() {
  try {
    const res = await wardsAPI.getAll(true);
    const list = (res.data || []).slice().sort((a, b) => (a.name || '').localeCompare(b.name || ''));
    allDepartmentOptions.value = list.map((w) => ({
      label: `${w.name} (${(w.department_type || '').replace(/_/g, ' ')})`,
      value: w.name,
    }));
    departmentOptions.value = allDepartmentOptions.value;
  } catch {
    allDepartmentOptions.value = [];
    departmentOptions.value = [];
  }
}

function filterDepartments(val, update) {
  if (val === '') {
    update(() => {
      departmentOptions.value = allDepartmentOptions.value;
    });
    return;
  }
  const needle = val.toLowerCase();
  update(() => {
    departmentOptions.value = allDepartmentOptions.value.filter((o) => o.label.toLowerCase().indexOf(needle) > -1);
  });
}

async function loadDashboard() {
  loadError.value = '';
  loading.value = true;
  try {
    const params = { days: filters.value.days };
    if (filters.value.storeId != null) params.store_id = filters.value.storeId;
    if (filters.value.department) params.department = filters.value.department;
    const res = await inventoryAnalyticsAPI.getDashboard(params);
    dash.value = res.data;
  } catch (e) {
    dash.value = null;
    loadError.value = e.response?.data?.detail || e.message || 'Could not load dashboard';
  } finally {
    loading.value = false;
  }
}

const navigateToModule = (path) => {
  router.push(path);
};

onMounted(async () => {
  if (!hasAnyAccess.value) {
    router.push('/dashboard');
    return;
  }
  if (
    authStore.isAuthenticated &&
    authStore.user?.inventory_dashboard_can_filter_stores === undefined
  ) {
    try {
      await authStore.fetchUser();
    } catch (e) {
      void 0;
    }
  }
  await Promise.all([loadStores(), loadDepartments()]);
  const u = authStore.user;
  if (u) {
    if (!canFilterDashboardStores.value && u.assigned_store_ids?.length) {
      filters.value.storeId = u.assigned_store_ids[0];
    }
    if (!canFilterDashboardDepartments.value && u.ic_managed_department_names?.length) {
      filters.value.department = u.ic_managed_department_names[0];
    }
  }
  await loadDashboard();
});
</script>

<style scoped>
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
.inv-kpi-grid {
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
}
.claim-kpi__meta {
  margin-top: -0.35rem;
  font-size: var(--hms-text-xs);
  color: var(--hms-text-muted);
}
.chart-card {
  min-height: 280px;
}
.chart-area {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 2px;
  height: 160px;
  padding-bottom: 22px;
  position: relative;
}
.usage-chart .chart-bar {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-end;
  height: 100%;
  position: relative;
}
.chart-bar-fill.usage {
  width: 100%;
  max-width: 10px;
  border-radius: 4px 4px 0 0;
  background: var(--hms-accent, var(--q-primary));
  opacity: 0.95;
  min-height: 4px;
}
.req-chart .chart-bar-group {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-end;
  height: 100%;
  position: relative;
}
.bar-pair {
  display: flex;
  align-items: flex-end;
  gap: 2px;
  height: 100%;
  justify-content: center;
}
.mini-bar {
  width: 5px;
  border-radius: 2px 2px 0 0;
  min-height: 2px;
}
.mini-bar.created {
  background: #42a5f5;
}
.mini-bar.fulfilled {
  background: #66bb6a;
}
.chart-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  margin-top: 0.65rem;
  font-size: var(--hms-text-xs);
  color: var(--hms-text-muted);
}
.legend-dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 2px;
  margin-right: 4px;
  vertical-align: middle;
}
.legend-dot.created {
  background: #42a5f5;
}
.legend-dot.fulfilled {
  background: #66bb6a;
}
.chart-label {
  position: absolute;
  bottom: 0;
  font-size: 9px;
  color: var(--hms-text-muted);
  transform: rotate(-45deg);
  transform-origin: top left;
  white-space: nowrap;
}
.top-product-row {
  max-width: 100%;
  margin-bottom: 0.75rem;
}
.top-product-row:last-child {
  margin-bottom: 0;
}
.top-product-head {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 0;
}
.top-product-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: var(--hms-text-sm);
  color: var(--hms-text-primary);
}
.top-product-code {
  flex-shrink: 0;
  font-size: var(--hms-text-xs);
  color: var(--hms-text-muted);
  font-family: var(--hms-font-mono);
}
.top-product-meta {
  margin-top: 0.25rem;
  font-size: var(--hms-text-xs);
  color: var(--hms-text-muted);
}
.activity-list {
  border-radius: var(--hms-radius-lg);
  border-color: var(--hms-border) !important;
  background: var(--hms-surface);
}
.activity-time {
  font-size: var(--hms-text-xs);
  color: var(--hms-text-muted);
}
.inv-workspace {
  margin-top: 0.5rem;
  padding: 1.15rem 1.2rem 1.25rem;
  border-radius: 1.25rem;
  background: var(--hms-panel-bg);
  border: 1px solid var(--hms-border);
  box-shadow: var(--hms-shadow-md);
}
.group-bar {
  margin-bottom: 0.95rem;
  padding-bottom: 0.85rem;
  border-bottom: 1px solid var(--hms-border);
}
.group-title {
  margin: 0;
  font-size: var(--hms-text-lg);
  font-weight: 750;
  letter-spacing: var(--hms-tracking-tight);
  color: var(--hms-text-primary);
}
.group-note {
  margin: 0.2rem 0 0;
  font-size: var(--hms-text-sm);
  color: var(--hms-text-muted);
}
.module-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.8rem;
}
.module-card {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 0.9rem;
  min-height: 92px;
  background: var(--hms-surface) !important;
  box-shadow: none !important;
}
.module-icon {
  width: 2.55rem;
  height: 2.55rem;
  border-radius: var(--hms-radius-lg);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.module-title {
  font-size: var(--hms-text-base);
  font-weight: 750;
  color: var(--hms-text-primary);
}
.module-hint {
  margin-top: 0.2rem;
  font-size: var(--hms-text-sm);
  color: var(--hms-text-secondary);
  line-height: 1.4;
}
.module-arrow {
  color: var(--hms-text-muted);
  transition: transform var(--hms-duration-fast) var(--hms-ease-out), color var(--hms-duration-fast) var(--hms-ease-out);
}
.module-card:hover .module-arrow {
  color: var(--hms-accent);
  transform: translateX(3px);
}
@media (max-width: 720px) {
  .module-grid {
    grid-template-columns: 1fr;
  }
  .inv-workspace {
    padding: 1rem;
  }
}
</style>
