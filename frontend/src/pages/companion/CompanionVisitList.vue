<template>
  <q-page class="hms-page">
    <HmsPageHeader
      title="Service list"
      subtitle="Visits created from the government system (card + visit number)."
    >
      <template #actions>
        <HmsButton variant="primary" size="sm" @click="$router.push({ name: 'CompanionCreateService' })">
          Create service
        </HmsButton>
        <HmsButton variant="ghost" size="sm" @click="$router.push('/companion')">
          Back
        </HmsButton>
      </template>
    </HmsPageHeader>

    <q-banner v-if="ghimsLiveSync" class="bg-blue-1 text-dark q-mb-md" rounded>
      Live GHIMS sync is on. Insured visits with a completed service or a dispensed medicine are added here. Excel upload and Create service stay available.
    </q-banner>

    <section class="diag-panel">
      <div class="panel-head">
        <div>
          <div class="panel-title">Filters</div>
          <div class="panel-sub">
            Defaults to today. Synced GHIMS visits use the GHIMS visit date, so older admissions stay off this list. Clear both dates to load every visit.
          </div>
        </div>
      </div>
      <div class="panel-body">
        <div class="row q-col-gutter-md items-end">
          <q-input
            v-model="filters.date_from"
            filled
            dense
            type="date"
            label="From (created)"
            clearable
            class="col-12 col-sm-6 col-md-3"
            hint="GHIMS visit date for synced visits. Otherwise the day the visit was created."
          />
          <q-input
            v-model="filters.date_to"
            filled
            dense
            type="date"
            label="To (created)"
            clearable
            class="col-12 col-sm-6 col-md-3"
            hint="GHIMS visit date for synced visits. Otherwise the day the visit was created."
          />
          <div class="col-12 col-sm-12 col-md-6 row q-gutter-sm items-center">
            <HmsButton variant="secondary" size="sm" @click="setTodayRange">Today only</HmsButton>
            <HmsButton variant="ghost" size="sm" @click="clearDateRange">Clear dates (all)</HmsButton>
          </div>
          <q-input
            v-model="filters.card_number"
            filled
            dense
            label="Card number"
            clearable
            class="col-12 col-sm-4"
            @keyup.enter="loadVisits"
          />
          <q-input
            v-model="filters.visit_number"
            filled
            dense
            label="Visit number"
            clearable
            class="col-12 col-sm-4"
            @keyup.enter="loadVisits"
          />
          <q-select
            v-model="filters.status"
            :options="statusOptions"
            filled
            dense
            label="Status"
            emit-value
            map-options
            clearable
            class="col-12 col-sm-2"
          />
          <div class="col-auto">
            <HmsButton variant="primary" size="sm" @click="loadVisits">Search</HmsButton>
          </div>
        </div>
      </div>
    </section>

    <section class="diag-panel">
      <div class="panel-head">
        <div>
          <div class="panel-title">Services</div>
          <div class="panel-sub">
            Tap Total bill for a receipt-style view (line items, receipts, and who recorded each payment).
          </div>
        </div>
      </div>
      <div class="panel-body table-wrap">
        <q-table
          :rows="visits"
          :columns="columns"
          row-key="id"
          flat
          :loading="loading"
          :rows-per-page-options="[10, 25, 50]"
          class="diag-table"
          no-data-label="No services found. Create one from the government system card and visit number."
        >
          <template v-slot:body-cell-bill_total="props">
            <q-td :props="props">
              <span
                class="receipt-amount-hit"
                tabindex="0"
                role="button"
                @click.stop="openReceiptForRow(props.row, 'total')"
                @keyup.enter.stop="openReceiptForRow(props.row, 'total')"
              >
                GH¢ {{ formatPrice(props.row.bill_total) }}
                <q-tooltip anchor="top middle" self="bottom middle">View bill &amp; payments</q-tooltip>
              </span>
            </q-td>
          </template>
          <template v-slot:body-cell-created_at="props">
            <q-td :props="props">{{ formatDate(props.row.created_at) }}</q-td>
          </template>
          <template v-slot:body-cell-actions="props">
            <q-td :props="props">
              <q-btn
                flat
                dense
                size="sm"
                icon="visibility"
                @click="viewVisit(props.row)"
              >
                <q-tooltip>View</q-tooltip>
              </q-btn>
              <q-btn
                flat
                dense
                size="sm"
                icon="edit"
                :disable="!canEdit(props.row)"
                @click="canEdit(props.row) && editVisit(props.row)"
              >
                <q-tooltip>{{ editDeleteTooltip(props.row, 'edit') }}</q-tooltip>
              </q-btn>
              <q-btn
                flat
                dense
                size="sm"
                icon="delete"
                color="negative"
                :disable="!canDelete(props.row)"
                @click="canDelete(props.row) && confirmDelete(props.row)"
              >
                <q-tooltip>{{ editDeleteTooltip(props.row, 'delete') }}</q-tooltip>
              </q-btn>
            </q-td>
          </template>
        </q-table>
      </div>
    </section>

    <CompanionBillingReceiptDialog
      v-model="receiptOpen"
      :visit="receiptVisit"
      :items="receiptItems"
      :loading="receiptLoading"
      :focus-hint="receiptFocus"
    />
  </q-page>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useQuasar } from 'quasar';
import { useAuthStore } from '../../stores/auth';
import { companionVisitsAPI, moduleSettingsAPI } from '../../services/api';
import CompanionBillingReceiptDialog from '../../components/companion/CompanionBillingReceiptDialog.vue';
import HmsPageHeader from '../../components/ui/HmsPageHeader.vue';
import HmsButton from '../../components/ui/HmsButton.vue';

const router = useRouter();
const $q = useQuasar();
const authStore = useAuthStore();
const loading = ref(false);
const ghimsLiveSync = ref(false);
const visits = ref([]);
let listLoadSeq = 0;
function localYmd(d = new Date()) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

const filters = reactive({
  card_number: '',
  visit_number: '',
  status: null,
  /** Default: today–today (visits created today, local calendar). */
  date_from: localYmd(),
  date_to: localYmd(),
});

function setTodayRange() {
  const t = localYmd();
  filters.date_from = t;
  filters.date_to = t;
  loadVisits();
}

function clearDateRange() {
  filters.date_from = null;
  filters.date_to = null;
  loadVisits();
}
const statusOptions = [
  { label: 'Open', value: 'open' },
  { label: 'Closed', value: 'closed' },
];

const columns = [
  { name: 'id', label: 'ID', field: 'id', align: 'left', sortable: true },
  { name: 'external_card_number', label: 'Card number', field: 'external_card_number', align: 'left' },
  { name: 'external_visit_number', label: 'Visit number', field: 'external_visit_number', align: 'left' },
  { name: 'client_name', label: 'Client name', field: 'client_name', align: 'left' },
  { name: 'bill_total', label: 'Total bill', field: 'bill_total', align: 'right', sortable: true },
  { name: 'status', label: 'Status', field: 'status', align: 'left' },
  { name: 'created_at', label: 'Created', field: 'created_at', align: 'left' },
  { name: 'actions', label: '', align: 'right' },
];

const receiptOpen = ref(false);
const receiptLoading = ref(false);
const receiptVisit = ref(null);
const receiptItems = ref([]);
const receiptFocus = ref('overview');

function formatPrice(val) {
  const n = Number(val);
  if (Number.isNaN(n)) return '0.00';
  return n.toFixed(2);
}

async function openReceiptForRow(row, focus) {
  receiptFocus.value = focus || 'overview';
  receiptOpen.value = true;
  receiptLoading.value = true;
  receiptVisit.value = row;
  receiptItems.value = [];
  try {
    const [vRes, iRes] = await Promise.all([companionVisitsAPI.get(row.id), companionVisitsAPI.getItems(row.id)]);
    receiptVisit.value = vRes.data;
    receiptItems.value = iRes.data || [];
  } catch (e) {
    receiptOpen.value = false;
    $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Could not load bill details', position: 'top' });
  } finally {
    receiptLoading.value = false;
  }
}

/** Edit: when closed only Admin; when open Records, Billing, or Admin. */
function canEdit(row) {
  if (row.status === 'closed') return authStore.canAccess(['Admin']);
  return authStore.canAccess(['Records', 'Admin', 'Billing']);
}

/** Delete: when closed only Admin; when open Records, Billing, or Admin. */
function canDelete(row) {
  if (row.status === 'closed') return authStore.canAccess(['Admin']);
  return authStore.canAccess(['Records', 'Admin', 'Billing']);
}

function editDeleteTooltip(row, action) {
  const label = action === 'edit' ? 'Edit' : 'Delete';
  if (row.status === 'closed' && !authStore.canAccess(['Admin'])) {
    return `Only Admin can ${action} a closed visit`;
  }
  return label;
}

function formatDate(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleString();
}

async function loadVisits() {
  const seq = ++listLoadSeq;
  loading.value = true;
  const card = (filters.card_number || '').trim();
  const visitNo = (filters.visit_number || '').trim();
  try {
    const res = await companionVisitsAPI.list(visitListParams());
    if (seq !== listLoadSeq) return;
    visits.value = res.data || [];
  } catch (e) {
    if (seq !== listLoadSeq) return;
    visits.value = [];
  } finally {
    if (seq === listLoadSeq) loading.value = false;
  }
  if (ghimsLiveSync.value && (card || visitNo)) {
    window.setTimeout(() => {
      if (seq === listLoadSeq) refreshVisitsQuietly(seq);
    }, 2000);
  }
}

function visitListParams() {
  const params = {};
  if (filters.card_number) params.card_number = filters.card_number;
  if (filters.visit_number) params.visit_number = filters.visit_number;
  if (filters.status) params.status_filter = filters.status;
  if (filters.date_from) params.date_from = filters.date_from;
  if (filters.date_to) params.date_to = filters.date_to;
  return params;
}

async function refreshVisitsQuietly(seq) {
  try {
    const res = await companionVisitsAPI.list(visitListParams());
    if (seq !== listLoadSeq) return;
    visits.value = res.data || [];
  } catch (e) {
    /* Keep the list already on screen. */
  }
}

function viewVisit(row) {
  router.push({ name: 'CompanionVisitDetail', params: { id: row.id } }).catch(() => {});
}

function editVisit(row) {
  router.push({ name: 'CompanionVisitDetail', params: { id: row.id } }).catch(() => {});
}

function confirmDelete(row) {
  $q.dialog({
    title: 'Delete service',
    message: 'Remove this visit? This cannot be undone.',
    cancel: true,
    persistent: true,
  }).onOk(async () => {
    try {
      await companionVisitsAPI.delete(row.id);
      $q.notify({ type: 'positive', message: 'Deleted', position: 'top' });
      loadVisits();
    } catch (e) {
      $q.notify({
        type: 'negative',
        message: e.response?.data?.detail || e.message || 'Delete failed',
        position: 'top',
      });
    }
  });
}

onMounted(async () => {
  try {
    const res = await moduleSettingsAPI.getStatus('companion_ghims_live');
    ghimsLiveSync.value = !!res.data?.is_active;
  } catch {
    ghimsLiveSync.value = false;
  }
  loadVisits();
});
</script>

<style scoped>
.receipt-amount-hit {
  cursor: pointer;
  border-bottom: 1px dashed currentColor;
  padding-bottom: 1px;
  outline-offset: 2px;
}
.receipt-amount-hit:focus {
  outline: 2px solid var(--q-primary);
  border-radius: 2px;
}
</style>
