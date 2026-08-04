<template>
  <q-page class="hms-page inventory-reports-page">
    <HmsPageHeader
      title="Inventory reports"
      subtitle="Requisition history and store stock snapshots with CSV and PDF export."
    >
      <template #actions>
        <HmsButton variant="ghost" size="sm" @click="$router.push('/inventory-mode')">Back</HmsButton>
      </template>
    </HmsPageHeader>

    <div class="soft-banner q-pa-md q-mb-md">
      <div class="row items-start no-wrap q-gutter-sm">
        <q-icon name="assessment" color="primary" size="20px" class="q-mt-xs" />
        <div class="panel-sub" style="margin-top: 0; max-width: none">
          Requisitions and store stock snapshots use the same access rules as the inventory dashboard (your store or department assignments, unless you have full filter access).
        </div>
      </div>
    </div>

    <section class="diag-panel">
      <div class="panel-head">
        <div>
          <div class="panel-title">Filters</div>
          <div class="panel-sub">Date range, store, department, and store type</div>
        </div>
      </div>
      <div class="panel-body">
        <div class="row q-col-gutter-md items-end">
          <div class="col-12 col-sm-6 col-md-3">
            <q-input v-model="filters.startDate" type="date" label="Start date" filled dense />
          </div>
          <div class="col-12 col-sm-6 col-md-3">
            <q-input v-model="filters.endDate" type="date" label="End date" filled dense />
          </div>
          <div class="col-12 col-sm-6 col-md-3">
            <q-select
              v-model="filters.storeId"
              :options="storeOptions"
              label="Store (optional)"
              clearable
              filled
              dense
              emit-value
              map-options
              :disable="!canFilterStores"
            />
          </div>
          <div class="col-12 col-sm-6 col-md-3">
            <q-select
              v-model="filters.department"
              :options="departmentOptions"
              label="Department (optional)"
              clearable
              filled
              dense
              emit-value
              map-options
              use-input
              input-debounce="200"
              :disable="!canFilterDepartments"
              @filter="filterDepartments"
            />
          </div>
          <div class="col-12 col-sm-6 col-md-3">
            <q-select
              v-model="filters.storeKind"
              :options="storeKindFilterOptions"
              label="Store type"
              filled
              dense
              emit-value
              map-options
            />
          </div>
        </div>
      </div>
    </section>

    <div class="tool-seg" role="tablist" aria-label="Report type">
      <button type="button" class="seg-btn" :class="{ active: tab === 'req' }" @click="tab = 'req'">
        Requisitions
      </button>
      <button type="button" class="seg-btn" :class="{ active: tab === 'stock' }" @click="tab = 'stock'">
        Store stock
      </button>
    </div>

    <template v-if="tab === 'req'">
      <section class="diag-panel">
        <div class="panel-head">
          <div>
            <div class="panel-title">Requisitions in date range</div>
            <div v-if="reqSummaryText" class="panel-sub">{{ reqSummaryText }}</div>
          </div>
          <div class="panel-actions">
            <HmsButton variant="primary" size="sm" :loading="loadingReq" @click="loadRequisitions">
              Run
            </HmsButton>
            <HmsButton variant="secondary" size="sm" :loading="exportingReq" @click="exportRequisitionsCsv">
              CSV
            </HmsButton>
            <HmsButton
              variant="ghost"
              size="sm"
              :disabled="!reqRows.length"
              :loading="exportingReqPdf"
              @click="exportPdfRequisitions"
            >
              PDF
            </HmsButton>
          </div>
        </div>
        <div class="panel-body table-wrap">
          <q-table
            class="diag-table"
            flat
            dense
            :rows="reqRows"
            :columns="reqColumns"
            row-key="requisition_id"
            :loading="loadingReq"
            :pagination="{ rowsPerPage: 25 }"
            :rows-per-page-options="[10, 25, 50, 100]"
          >
            <template v-slot:body-cell-line_count="props">
              <q-td :props="props">
                <span
                  class="text-primary text-weight-medium cursor-pointer text-underline"
                  role="button"
                  tabindex="0"
                  @click="openReqLineItems(props.row)"
                  @keyup.enter="openReqLineItems(props.row)"
                >
                  {{ props.row.line_count }}
                </span>
              </q-td>
            </template>
            <template v-slot:body-cell-total_requested_qty="props">
              <q-td :props="props">
                <span
                  class="text-primary text-weight-medium cursor-pointer text-underline"
                  role="button"
                  tabindex="0"
                  @click="openReqLineItems(props.row)"
                  @keyup.enter="openReqLineItems(props.row)"
                >
                  {{ formatQty(props.row.total_requested_qty) }}
                </span>
              </q-td>
            </template>
          </q-table>
        </div>
      </section>
    </template>

    <template v-else>
      <section class="diag-panel">
        <div class="panel-head">
          <div>
            <div class="panel-title">Current store stock (snapshot)</div>
            <div v-if="stockTotalsText" class="panel-sub">{{ stockTotalsText }}</div>
          </div>
          <div class="panel-actions">
            <HmsButton variant="primary" size="sm" :loading="loadingStock" @click="loadStoreStock">
              Run
            </HmsButton>
            <HmsButton variant="secondary" size="sm" :loading="exportingStock" @click="exportStoreStockCsv">
              CSV
            </HmsButton>
            <HmsButton
              variant="ghost"
              size="sm"
              :disabled="!stockRows.length"
              :loading="exportingStockPdf"
              @click="exportPdfStoreStock"
            >
              PDF
            </HmsButton>
          </div>
        </div>
        <div class="panel-body">
          <div class="row q-col-gutter-md items-end q-mb-md">
            <div class="col-12 col-sm-6 col-md-4">
              <q-select
                v-model="stockStatus"
                :options="stockStatusOptions"
                label="Stock status (optional)"
                clearable
                filled
                dense
                emit-value
                map-options
              />
            </div>
          </div>
          <div class="table-wrap">
            <q-table
              class="diag-table"
              flat
              dense
              :rows="stockRows"
              :columns="stockColumns"
              row-key="__key"
              :loading="loadingStock"
              :pagination="{ rowsPerPage: 25 }"
              :rows-per-page-options="[10, 25, 50, 100]"
            />
          </div>
        </div>
      </section>
    </template>

    <q-dialog v-model="reqItemsDialogOpen">
      <q-card class="diag-panel dialog-card" style="min-width: min(96vw, 920px); max-width: 920px">
        <q-card-section class="dialog-head row items-center">
          <div>
            <div class="dialog-title">Requisition line items</div>
            <div v-if="reqItemsDetail" class="dialog-sub">
              {{ reqItemsDetail.requisition_number }} · {{ reqItemsDetail.status }}
            </div>
          </div>
          <q-space />
          <q-btn flat round dense icon="close" v-close-popup />
        </q-card-section>
        <q-card-section v-if="reqItemsLoading" class="flex flex-center q-pa-xl">
          <q-spinner color="primary" size="40px" />
        </q-card-section>
        <template v-else>
          <q-card-section v-if="reqItemsDetail" class="q-pt-none">
            <div class="text-body2 q-gutter-xs">
              <div><strong>Number:</strong> {{ reqItemsDetail.requisition_number }}</div>
              <div><strong>Status:</strong> {{ reqItemsDetail.status }}</div>
              <div v-if="reqItemsDetail.department_name"><strong>Department:</strong> {{ reqItemsDetail.department_name }}</div>
              <div v-if="reqItemsDetail.store_name"><strong>Store:</strong> {{ reqItemsDetail.store_name }}</div>
            </div>
          </q-card-section>
          <q-card-section>
            <q-table
              class="diag-table"
              flat
              bordered
              :rows="reqItemsDetail?.items || []"
              :columns="reqItemColumns"
              row-key="id"
              :pagination="{ rowsPerPage: 0 }"
              hide-pagination
              no-data-label="No line items"
            />
          </q-card-section>
        </template>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useQuasar } from 'quasar';
import { storeToRefs } from 'pinia';
import { inventoryReportsAPI, storesAPI, wardsAPI, pharmacyRequisitionsAPI } from '../services/api';
import { useAuthStore } from '../stores/auth';
import { useFacilityStore } from '../stores/facility';
import { storeSelectLabel } from '../utils/storeKind';
import { downloadInventoryReportPdf } from '../utils/inventoryReportPdf';
import HmsPageHeader from '../components/ui/HmsPageHeader.vue';
import HmsButton from '../components/ui/HmsButton.vue';

const $q = useQuasar();
const authStore = useAuthStore();
const facilityStore = useFacilityStore();
const { displayName: facilityDisplayName } = storeToRefs(facilityStore);

const tab = ref('req');
const filters = ref({
  startDate: '',
  endDate: '',
  storeId: null,
  department: null,
  storeKind: null,
});

const storeKindFilterOptions = [
  { label: 'All types', value: null },
  { label: 'Pharmacy supply', value: 'pharmacy' },
  { label: 'General (main store)', value: 'general' },
];

const storeOptions = ref([]);
const allDepartmentOptions = ref([]);
const departmentOptions = ref([]);

const loadingReq = ref(false);
const exportingReq = ref(false);
const exportingReqPdf = ref(false);
const reqRows = ref([]);
const reqSummary = ref(null);

const reqItemsDialogOpen = ref(false);
const reqItemsLoading = ref(false);
const reqItemsDetail = ref(null);

const loadingStock = ref(false);
const exportingStock = ref(false);
const exportingStockPdf = ref(false);
const stockRows = ref([]);
const stockTotals = ref(null);
const stockStatus = ref(null);

const stockStatusOptions = [
  { label: 'All statuses', value: null },
  { label: 'Approved', value: 'APPROVED' },
  { label: 'Pending', value: 'PENDING' },
  { label: 'Rejected', value: 'REJECTED' },
  { label: 'Expired', value: 'EXPIRED' },
];

const canFilterStores = computed(() => Boolean(authStore.user?.inventory_dashboard_can_filter_stores));
const canFilterDepartments = computed(() => Boolean(authStore.user?.inventory_dashboard_can_filter_departments));

const reqColumns = [
  { name: 'requisition_number', label: 'Number', field: 'requisition_number', align: 'left', sortable: true },
  { name: 'created_at', label: 'Created', field: 'created_at', align: 'left', sortable: true },
  { name: 'status', label: 'Status', field: 'status', align: 'left', sortable: true },
  { name: 'department_name', label: 'Department', field: 'department_name', align: 'left' },
  { name: 'store_name', label: 'Store', field: 'store_name', align: 'left' },
  { name: 'store_kind', label: 'Type', field: 'store_kind', align: 'left' },
  { name: 'line_count', label: 'Lines', field: 'line_count', align: 'right', sortable: true },
  { name: 'total_requested_qty', label: 'Requested qty', field: 'total_requested_qty', align: 'right', sortable: true },
];

const reqItemColumns = [
  { name: 'product_code', label: 'Code', field: 'product_code', align: 'left' },
  { name: 'product_name', label: 'Product', field: 'product_name', align: 'left' },
  { name: 'requested_quantity', label: 'Requested', field: 'requested_quantity', align: 'right' },
  { name: 'approved_quantity', label: 'Approved', field: 'approved_quantity', align: 'right' },
  { name: 'fulfilled_quantity', label: 'Fulfilled', field: 'fulfilled_quantity', align: 'right' },
  { name: 'unit_price', label: 'Unit price', field: 'unit_price', align: 'right' },
  { name: 'notes', label: 'Notes', field: 'notes', align: 'left' },
];

const stockColumns = [
  { name: 'store_name', label: 'Store', field: 'store_name', align: 'left' },
  { name: 'store_kind', label: 'Type', field: 'store_kind', align: 'left' },
  { name: 'product_code', label: 'Code', field: 'product_code', align: 'left' },
  { name: 'product_name', label: 'Product', field: 'product_name', align: 'left' },
  { name: 'batch_number', label: 'Batch', field: 'batch_number', align: 'left' },
  { name: 'expiry_date', label: 'Expiry', field: 'expiry_date', align: 'left' },
  { name: 'quantity', label: 'Qty', field: 'quantity', align: 'right' },
  { name: 'status', label: 'Status', field: 'status', align: 'left' },
  { name: 'unit_price', label: 'Unit price', field: 'unit_price', align: 'right' },
  { name: 'line_value', label: 'Line value', field: 'line_value', align: 'right' },
];

const reqSummaryText = computed(() => {
  if (!reqSummary.value?.summary_by_status) return '';
  const parts = Object.entries(reqSummary.value.summary_by_status).map(([k, v]) => `${k}: ${v}`);
  return parts.length ? `By status — ${parts.join(' · ')}` : '';
});

const stockTotalsText = computed(() => {
  const t = stockTotals.value;
  if (!t?.totals) return '';
  const x = t.totals;
  const v = x.value != null ? ` · Estimated value: ${x.value}` : '';
  return `Lines: ${x.lines} · Total qty: ${x.quantity}${v}`;
});

function defaultDates() {
  const end = new Date();
  const start = new Date();
  start.setDate(start.getDate() - 30);
  const iso = (d) => d.toISOString().slice(0, 10);
  filters.value.endDate = iso(end);
  filters.value.startDate = iso(start);
}

function reportParams(extra = {}) {
  const p = {
    start_date: filters.value.startDate,
    end_date: filters.value.endDate,
    ...extra,
  };
  if (filters.value.storeId != null) p.store_id = filters.value.storeId;
  if (filters.value.department) p.department = filters.value.department;
  if (filters.value.storeKind) p.store_kind = filters.value.storeKind;
  return p;
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

function formatQty(v) {
  if (v == null || !Number.isFinite(Number(v))) return '0';
  const n = Number(v);
  return n % 1 === 0 ? String(n) : n.toFixed(2);
}

function formatReqCreatedForPdf(iso) {
  if (!iso) return '';
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return String(iso);
    return d.toLocaleString();
  } catch {
    return String(iso);
  }
}

async function ensureFacilityName() {
  if (!facilityStore.loaded) {
    try {
      await facilityStore.fetchPublic();
    } catch {
      void 0;
    }
  }
}

async function openReqLineItems(row) {
  if (!row?.requisition_id) return;
  reqItemsDialogOpen.value = true;
  reqItemsLoading.value = true;
  reqItemsDetail.value = null;
  try {
    const res = await pharmacyRequisitionsAPI.get(row.requisition_id);
    reqItemsDetail.value = res.data;
  } catch (e) {
    reqItemsDialogOpen.value = false;
    $q.notify({
      type: 'negative',
      message: e.response?.data?.detail || e.message || 'Could not load line items',
      position: 'top',
    });
  } finally {
    reqItemsLoading.value = false;
  }
}

function filterNoteForPdf() {
  const parts = [];
  if (filters.value.storeId != null) {
    const opt = storeOptions.value.find((o) => o.value === filters.value.storeId);
    parts.push(`Store: ${opt?.label || filters.value.storeId}`);
  }
  if (filters.value.department) parts.push(`Department: ${filters.value.department}`);
  if (filters.value.storeKind === 'pharmacy') parts.push('Store type: Pharmacy');
  if (filters.value.storeKind === 'general') parts.push('Store type: General');
  return parts.length ? parts.join(' · ') : '';
}

function stockPdfFilterNote() {
  const base = filterNoteForPdf();
  const st = stockStatus.value ? `Stock status: ${stockStatus.value}` : '';
  return [base, st].filter(Boolean).join(' · ') || '';
}

async function loadRequisitions() {
  if (!filters.value.startDate || !filters.value.endDate) {
    $q.notify({ type: 'warning', message: 'Choose start and end dates', position: 'top' });
    return;
  }
  loadingReq.value = true;
  try {
    const res = await inventoryReportsAPI.getRequisitions(reportParams());
    reqSummary.value = res.data;
    reqRows.value = (res.data?.rows || []).map((r) => ({
      ...r,
      created_at: r.created_at ? new Date(r.created_at).toLocaleString() : '',
      created_at_iso: r.created_at,
    }));
  } catch (e) {
    reqRows.value = [];
    reqSummary.value = null;
    $q.notify({
      type: 'negative',
      message: e.response?.data?.detail || e.message || 'Failed to load report',
      position: 'top',
    });
  } finally {
    loadingReq.value = false;
  }
}

function triggerDownload(blob, fallbackName) {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = fallbackName;
  a.click();
  window.URL.revokeObjectURL(url);
}

async function exportPdfRequisitions() {
  if (!reqRows.value.length) return;
  await ensureFacilityName();
  exportingReqPdf.value = true;
  try {
    const head = [
      [
        'Requisition #',
        'Created',
        'Status',
        'Department',
        'Store',
        'Type',
        'Lines',
        'Requested qty',
      ],
    ];
    const body = reqRows.value.map((r) => [
      r.requisition_number || '',
      formatReqCreatedForPdf(r.created_at_iso),
      String(r.status || ''),
      r.department_name || '',
      r.store_name || '',
      r.store_kind || '',
      String(r.line_count ?? ''),
      formatQty(r.total_requested_qty),
    ]);
    const summary = reqSummary.value?.summary_by_status
      ? Object.entries(reqSummary.value.summary_by_status)
          .map(([k, v]) => `${k}: ${v}`)
          .join(' · ')
      : '';
    await downloadInventoryReportPdf({
      facilityName: facilityDisplayName.value || 'Facility',
      reportTitle: 'Inventory — Requisitions',
      subtitle: 'Inventory management',
      periodLine: `${filters.value.startDate} – ${filters.value.endDate}`,
      filterNote: filterNoteForPdf() || undefined,
      summaryLine: summary ? `By status — ${summary}` : undefined,
      head,
      body,
      filename: `inventory_requisitions_${filters.value.startDate}_${filters.value.endDate}`,
      orientation: 'landscape',
    });
  } catch (e) {
    $q.notify({
      type: 'negative',
      message: e?.message || 'PDF export failed',
      position: 'top',
    });
  } finally {
    exportingReqPdf.value = false;
  }
}

async function exportRequisitionsCsv() {
  if (!filters.value.startDate || !filters.value.endDate) {
    $q.notify({ type: 'warning', message: 'Choose start and end dates', position: 'top' });
    return;
  }
  exportingReq.value = true;
  try {
    const res = await inventoryReportsAPI.downloadRequisitionsCsv(reportParams());
    const name = `inventory_requisitions_${filters.value.startDate}_${filters.value.endDate}.csv`;
    triggerDownload(res.data, name);
  } catch (e) {
    $q.notify({
      type: 'negative',
      message: e.response?.data?.detail || e.message || 'Export failed',
      position: 'top',
    });
  } finally {
    exportingReq.value = false;
  }
}

async function loadStoreStock() {
  loadingStock.value = true;
  try {
    const params = {};
    if (filters.value.storeId != null) params.store_id = filters.value.storeId;
    if (filters.value.department) params.department = filters.value.department;
    if (filters.value.storeKind) params.store_kind = filters.value.storeKind;
    if (stockStatus.value) params.stock_status = stockStatus.value;
    const res = await inventoryReportsAPI.getStoreStock(params);
    stockTotals.value = res.data;
    stockRows.value = (res.data?.rows || []).map((r, i) => ({
      ...r,
      __key: `${r.store_id}-${r.product_code}-${r.batch_number}-${i}`,
    }));
  } catch (e) {
    stockRows.value = [];
    stockTotals.value = null;
    $q.notify({
      type: 'negative',
      message: e.response?.data?.detail || e.message || 'Failed to load report',
      position: 'top',
    });
  } finally {
    loadingStock.value = false;
  }
}

async function exportPdfStoreStock() {
  if (!stockRows.value.length) return;
  await ensureFacilityName();
  exportingStockPdf.value = true;
  try {
    const head = [
      [
        'Store',
        'Type',
        'Code',
        'Product',
        'Batch',
        'Expiry',
        'Qty',
        'Status',
        'Unit price',
        'Line value',
      ],
    ];
    const body = stockRows.value.map((r) => [
      r.store_name || '',
      r.store_kind || '',
      r.product_code || '',
      r.product_name || '',
      r.batch_number || '',
      r.expiry_date || '',
      formatQty(r.quantity),
      r.status || '',
      r.unit_price != null ? formatQty(r.unit_price) : '',
      r.line_value != null ? formatQty(r.line_value) : '',
    ]);
    const t = stockTotals.value?.totals;
    const summaryLine = t
      ? `Lines: ${t.lines} · Total qty: ${t.quantity}${t.value != null ? ` · Est. value: ${t.value}` : ''}`
      : undefined;
    const asOf = stockTotals.value?.as_of
      ? new Date(stockTotals.value.as_of).toLocaleString()
      : new Date().toLocaleString();
    await downloadInventoryReportPdf({
      facilityName: facilityDisplayName.value || 'Facility',
      reportTitle: 'Inventory — Store stock snapshot',
      subtitle: 'Approved / pending stock lines (snapshot)',
      periodLine: `As of ${asOf}`,
      filterNote: stockPdfFilterNote() || undefined,
      summaryLine,
      head,
      body,
      filename: `inventory_store_stock_${new Date().toISOString().slice(0, 10)}`,
      orientation: 'landscape',
    });
  } catch (e) {
    $q.notify({
      type: 'negative',
      message: e?.message || 'PDF export failed',
      position: 'top',
    });
  } finally {
    exportingStockPdf.value = false;
  }
}

async function exportStoreStockCsv() {
  exportingStock.value = true;
  try {
    const params = {};
    if (filters.value.storeId != null) params.store_id = filters.value.storeId;
    if (filters.value.department) params.department = filters.value.department;
    if (filters.value.storeKind) params.store_kind = filters.value.storeKind;
    if (stockStatus.value) params.stock_status = stockStatus.value;
    const res = await inventoryReportsAPI.downloadStoreStockCsv(params);
    const name = `inventory_store_stock_${new Date().toISOString().slice(0, 10)}.csv`;
    triggerDownload(res.data, name);
  } catch (e) {
    $q.notify({
      type: 'negative',
      message: e.response?.data?.detail || e.message || 'Export failed',
      position: 'top',
    });
  } finally {
    exportingStock.value = false;
  }
}

onMounted(() => {
  defaultDates();
  loadStores();
  loadDepartments();
  void facilityStore.fetchPublic();
});
</script>

<style scoped>
.tool-seg {
  display: inline-flex;
  padding: 0.2rem;
  margin-bottom: 1rem;
  gap: 0.15rem;
  border-radius: var(--hms-radius-lg);
  background: var(--hms-surface);
  border: 1px solid var(--hms-border);
}
.seg-btn {
  appearance: none;
  border: none;
  background: transparent;
  color: var(--hms-text-secondary);
  font-size: var(--hms-text-sm);
  font-weight: 650;
  padding: 0.45rem 0.85rem;
  border-radius: calc(var(--hms-radius-lg) - 2px);
  cursor: pointer;
  transition: background var(--hms-duration-fast) var(--hms-ease-out), color var(--hms-duration-fast) var(--hms-ease-out);
}
.seg-btn.active {
  background: var(--hms-panel-bg);
  color: var(--hms-text-primary);
  box-shadow: var(--hms-shadow-sm);
}
.panel-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}
.table-wrap {
  padding: 0;
  overflow-x: auto;
}
.dialog-card {
  margin-bottom: 0;
}
.dialog-head {
  padding: 0.85rem 1rem;
  border-bottom: 1px solid var(--hms-border);
}
.dialog-title {
  font-size: var(--hms-text-lg);
  font-weight: 750;
  color: var(--hms-text-primary);
}
.dialog-sub {
  margin-top: 0.15rem;
  font-size: var(--hms-text-xs);
  color: var(--hms-text-muted);
}
.text-underline {
  text-decoration: underline;
}
.cursor-pointer {
  cursor: pointer;
}
</style>
