<template>
  <q-page class="q-pa-md inventory-dashboard-page">
    <LicenseStatusBanner />

    <div class="row items-end q-col-gutter-md q-mb-lg">
      <div class="col-12 col-md-8">
        <div class="text-h4 text-weight-bold glass-text">Inventory dashboard</div>
        <div class="text-body2 text-secondary q-mt-xs">
          Stock levels, usage, requisitions, and trends.
          <template v-if="canFilterDashboardStores || canFilterDashboardDepartments">
            Use the filters below (Management / Admin / Pharmacy-wide roles).
          </template>
          <template v-else>
            Scoped to your assigned store or department; filters are fixed.
          </template>
        </div>
      </div>
      <div class="col-12 col-md-4 row justify-end">
        <q-btn
          flat
          icon="refresh"
          label="Refresh"
          :loading="loading"
          @click="loadDashboard"
          class="glass-button"
        />
      </div>
    </div>

    <!-- Filters -->
    <q-card class="glass-card q-mb-lg" flat bordered>
      <q-card-section>
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
        <div v-if="dash" class="text-caption text-grey-7 q-mt-sm">
          Showing
          <template v-if="dash.store_name"><strong>{{ dash.store_name }}</strong> store</template>
          <template v-else>all stores (approved stock)</template>
          ·
          <template v-if="dash.department"><strong>{{ dash.department }}</strong></template>
          <template v-else>all departments</template>
          · last <strong>{{ dash.period_days }}</strong> days
        </div>
      </q-card-section>
    </q-card>

    <q-banner v-if="loadError" class="bg-negative text-white q-mb-md" rounded>
      {{ loadError }}
    </q-banner>

    <!-- KPIs -->
    <div v-if="dash && !loading" class="row q-col-gutter-md q-mb-lg">
      <div v-if="showStoreStockKpi" class="col-6 col-sm-4 col-md-2">
        <q-card class="kpi-card glass-card" flat bordered>
          <q-card-section class="q-pa-sm">
            <div class="text-caption text-grey-7">Store stock (qty)</div>
            <div class="text-h6 text-weight-bold glass-text">{{ formatNum(dash.kpis.approved_store_stock_qty) }}</div>
            <div class="text-caption">{{ dash.kpis.approved_store_stock_lines }} lines</div>
          </q-card-section>
        </q-card>
      </div>
      <div class="col-6 col-sm-4 col-md-2" v-if="dash.kpis.ward_stock_total_qty != null">
        <q-card class="kpi-card glass-card" flat bordered>
          <q-card-section class="q-pa-sm">
            <div class="text-caption text-grey-7">Dept ward stock</div>
            <div class="text-h6 text-weight-bold glass-text">{{ formatNum(dash.kpis.ward_stock_total_qty) }}</div>
            <div class="text-caption">{{ dash.kpis.ward_stock_lines }} lines</div>
          </q-card-section>
        </q-card>
      </div>
      <div class="col-6 col-sm-4 col-md-2">
        <q-card class="kpi-card glass-card" flat bordered>
          <q-card-section class="q-pa-sm">
            <div class="text-caption text-grey-7">Req. pending</div>
            <div class="text-h6 text-weight-bold text-warning">{{ dash.kpis.requisitions_pending }}</div>
            <div class="text-caption">{{ dash.kpis.requisitions_in_flight }} in flight</div>
          </q-card-section>
        </q-card>
      </div>
      <div class="col-6 col-sm-4 col-md-2">
        <q-card class="kpi-card glass-card" flat bordered>
          <q-card-section class="q-pa-sm">
            <div class="text-caption text-grey-7">Req. (period)</div>
            <div class="text-h6 text-weight-bold glass-text">{{ dash.kpis.requisitions_created_period }}</div>
            <div class="text-caption">{{ dash.kpis.requisitions_fulfilled_period }} fulfilled</div>
          </q-card-section>
        </q-card>
      </div>
      <div class="col-6 col-sm-4 col-md-2">
        <q-card class="kpi-card glass-card" flat bordered>
          <q-card-section class="q-pa-sm">
            <div class="text-caption text-grey-7">Usage (units)</div>
            <div class="text-h6 text-weight-bold text-primary">{{ formatNum(dash.kpis.debit_units_period) }}</div>
            <div class="text-caption">{{ dash.kpis.debit_events_period }} debits</div>
          </q-card-section>
        </q-card>
      </div>
    </div>

    <!-- Charts -->
    <div v-if="dash && !loading" class="row q-col-gutter-md q-mb-lg">
      <div class="col-12 col-lg-6">
        <q-card class="glass-card chart-card" flat bordered>
          <q-card-section>
            <div class="text-subtitle1 text-weight-medium glass-text q-mb-md">Usage trend (inventory debits)</div>
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
            <div class="text-caption text-grey-7 q-mt-sm">Units debited per day (IPD + Companion)</div>
          </q-card-section>
        </q-card>
      </div>
      <div class="col-12 col-lg-6">
        <q-card class="glass-card chart-card" flat bordered>
          <q-card-section>
            <div class="text-subtitle1 text-weight-medium glass-text q-mb-md">Requisitions trend</div>
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
            <div class="row q-gutter-md text-caption q-mt-sm">
              <span><span class="legend-dot created" /> Created</span>
              <span><span class="legend-dot fulfilled" /> Fulfilled</span>
            </div>
          </q-card-section>
        </q-card>
      </div>
    </div>

    <!-- Top products + Activity -->
    <div v-if="dash && !loading" class="row q-col-gutter-md q-mb-lg">
      <div class="col-12 col-lg-6">
        <q-card class="glass-card" flat bordered>
          <q-card-section>
            <div class="text-subtitle1 text-weight-medium glass-text q-mb-md">Top products (period)</div>
            <div v-if="!dash.top_products.length" class="text-grey-7 text-caption">No product movement in this period.</div>
            <div v-for="tp in dash.top_products" :key="tp.product_code" class="top-product-row q-mb-sm">
              <div class="row items-center no-wrap q-gutter-sm">
                <div class="col ellipsis text-body2">{{ tp.product_name }}</div>
                <div class="col-auto text-caption text-grey-7">{{ tp.product_code }}</div>
              </div>
              <q-linear-progress
                :value="topProductRatio(tp)"
                color="primary"
                track-color="grey-8"
                size="8px"
                rounded
                class="q-mt-xs"
              />
              <div class="text-caption text-grey-7">
                Debits {{ formatNum(tp.debit_qty) }} · Req. {{ formatNum(tp.requisition_requested_qty) }}
              </div>
            </div>
          </q-card-section>
        </q-card>
      </div>
      <div class="col-12 col-lg-6">
        <q-card class="glass-card" flat bordered>
          <q-card-section>
            <div class="text-subtitle1 text-weight-medium glass-text q-mb-md">Recent activity</div>
            <q-list bordered separator class="rounded-borders">
              <q-item v-for="(ev, i) in dash.recent_events" :key="i" dense>
                <q-item-section avatar>
                  <q-icon :name="eventIcon(ev.kind)" :color="eventColor(ev.kind)" size="sm" />
                </q-item-section>
                <q-item-section>
                  <q-item-label class="text-weight-medium">{{ ev.label }}</q-item-label>
                  <q-item-label caption>{{ ev.detail }}</q-item-label>
                </q-item-section>
                <q-item-section side>
                  <span class="text-caption">{{ formatEventTime(ev.at) }}</span>
                </q-item-section>
              </q-item>
            </q-list>
          </q-card-section>
        </q-card>
      </div>
    </div>

    <q-inner-loading :showing="loading" color="primary" />

    <!-- Quick links -->
    <div class="text-h6 glass-text q-mb-md q-mt-xl">Quick links</div>
    <div class="text-subtitle2 text-secondary q-mb-md">Open a module to work with inventory</div>
    <div class="row q-col-gutter-md">
      <div v-if="canAccessRequisitions" class="col-12 col-md-6 col-lg-3">
        <q-card class="glass-card module-card cursor-pointer" flat bordered @click="navigateToModule('/inventory-mode/requisitions')">
          <q-card-section class="q-pa-lg">
            <div class="column items-center text-center">
              <q-icon name="shopping_cart" size="56px" color="primary" class="q-mb-md" />
              <div class="text-subtitle1 text-weight-bold glass-text q-mb-xs">Requisitions</div>
              <div class="text-caption text-secondary">Request and track store supplies</div>
            </div>
          </q-card-section>
        </q-card>
      </div>
      <div v-if="canAccessRequisitions" class="col-12 col-md-6 col-lg-3">
        <q-card class="glass-card module-card cursor-pointer" flat bordered @click="navigateToModule('/inventory-mode/reports')">
          <q-card-section class="q-pa-lg">
            <div class="column items-center text-center">
              <q-icon name="assessment" size="56px" color="cyan" class="q-mb-md" />
              <div class="text-subtitle1 text-weight-bold glass-text q-mb-xs">Reports</div>
              <div class="text-caption text-secondary">Requisitions &amp; store stock CSV</div>
            </div>
          </q-card-section>
        </q-card>
      </div>
      <div v-if="canAccessDepartmentStock" class="col-12 col-md-6 col-lg-3">
        <q-card class="glass-card module-card cursor-pointer" flat bordered @click="navigateToModule('/inventory-mode/ward-stock')">
          <q-card-section class="q-pa-lg">
            <div class="column items-center text-center">
              <q-icon name="warehouse" size="56px" color="secondary" class="q-mb-md" />
              <div class="text-subtitle1 text-weight-bold glass-text q-mb-xs">Department / ward stock</div>
              <div class="text-caption text-secondary">Unit-level stock</div>
            </div>
          </q-card-section>
        </q-card>
      </div>
      <div v-if="canAccessStoreStock" class="col-12 col-md-6 col-lg-3">
        <q-card class="glass-card module-card cursor-pointer" flat bordered @click="navigateToModule('/inventory-mode/store-stock')">
          <q-card-section class="q-pa-lg">
            <div class="column items-center text-center">
              <q-icon name="inventory" size="56px" color="purple" class="q-mb-md" />
              <div class="text-subtitle1 text-weight-bold glass-text q-mb-xs">Store stock</div>
              <div class="text-caption text-secondary">Central store batches &amp; approval</div>
            </div>
          </q-card-section>
        </q-card>
      </div>
      <div v-if="canAccessInventoryDebits" class="col-12 col-md-6 col-lg-3">
        <q-card class="glass-card module-card cursor-pointer" flat bordered @click="navigateToModule('/inventory-mode/inventory-debits')">
          <q-card-section class="q-pa-lg">
            <div class="column items-center text-center">
              <q-icon name="remove_shopping_cart" size="56px" color="teal" class="q-mb-md" />
              <div class="text-subtitle1 text-weight-bold glass-text q-mb-xs">Inventory debits</div>
              <div class="text-caption text-secondary">Release &amp; ward usage</div>
            </div>
          </q-card-section>
        </q-card>
      </div>
      <div v-if="canAccessStoreManagement" class="col-12 col-md-6 col-lg-3">
        <q-card class="glass-card module-card cursor-pointer" flat bordered @click="navigateToModule('/inventory-mode/store-management')">
          <q-card-section class="q-pa-lg">
            <div class="column items-center text-center">
              <q-icon name="store" size="56px" color="accent" class="q-mb-md" />
              <div class="text-subtitle1 text-weight-bold glass-text q-mb-xs">Store management</div>
            </div>
          </q-card-section>
        </q-card>
      </div>
      <div v-if="canAccessDepartmentManagement" class="col-12 col-md-6 col-lg-3">
        <q-card class="glass-card module-card cursor-pointer" flat bordered @click="navigateToModule('/inventory-mode/ward-management')">
          <q-card-section class="q-pa-lg">
            <div class="column items-center text-center">
              <q-icon name="meeting_room" size="56px" color="orange" class="q-mb-md" />
              <div class="text-subtitle1 text-weight-bold glass-text q-mb-xs">Department management</div>
            </div>
          </q-card-section>
        </q-card>
      </div>
    </div>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useAuthStore } from '../stores/auth';
import LicenseStatusBanner from '../components/LicenseStatusBanner.vue';
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
.glass-card {
  background: rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(10px);
}
.glass-text {
  color: rgba(255, 255, 255, 0.92);
}
.kpi-card {
  min-height: 88px;
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
  background: var(--q-primary);
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
  color: rgba(255, 255, 255, 0.5);
  transform: rotate(-45deg);
  transform-origin: top left;
  white-space: nowrap;
}
.top-product-row {
  max-width: 100%;
}
.module-card {
  transition: transform 0.2s, box-shadow 0.2s;
  height: 100%;
}
.module-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}
.body--light .glass-text {
  color: rgba(0, 0, 0, 0.87) !important;
}
</style>
