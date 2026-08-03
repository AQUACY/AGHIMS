<template>
  <q-page class="hms-page">
    <HmsPageHeader
      title="Inventory debit"
      subtitle="Build a list of products used on this companion visit, then save."
    >
      <template #actions>
        <HmsButton
          variant="secondary"
          size="sm"
          @click="$router.push({ name: 'CompanionVisitDetail', params: { id } })"
        >
          Back
        </HmsButton>
      </template>
    </HmsPageHeader>

    <q-banner
      v-if="visit && visit.status !== 'open'"
      class="soft-banner soft-banner--warn q-mb-md"
      rounded
    >
      <template #avatar>
        <q-icon name="lock" color="warning" />
      </template>
      This visit is closed — you cannot record new debits or change saved lines.
    </q-banner>

    <div v-if="visit" class="claim-hero">
      <div class="claim-hero__main">
        <div class="claim-hero__avatar" aria-hidden="true">{{ visitInitials }}</div>
        <div>
          <h2 class="claim-hero__name">{{ visit.client_name || 'Companion client' }}</h2>
          <div class="claim-hero__meta">
            <span class="mono">{{ visit.external_card_number }}</span>
            <span>Visit {{ visit.external_visit_number }}</span>
            <span v-if="debits.length">{{ debits.length }} debit{{ debits.length === 1 ? '' : 's' }}</span>
          </div>
        </div>
      </div>
      <div class="claim-hero__aside">
        <div class="claim-hero__badges">
          <HmsBadge :tone="visit.status === 'open' ? 'success' : 'muted'">
            {{ visit.status }}
          </HmsBadge>
        </div>
      </div>
    </div>

    <section v-if="canRecord && visit && visit.status === 'open'" class="diag-panel">
      <div class="panel-head">
        <div>
          <div class="panel-title">Build a list, then save</div>
          <div class="panel-sub">
            Add one or more lines below. Tick “On client bill” for lines that should appear on the copayment bill — no separate step.
          </div>
        </div>
      </div>
      <div class="panel-body">

        <div class="row q-col-gutter-md q-mb-md">
          <div class="col-12 col-md-6">
            <q-select
              v-model="form.requesting_department"
              :options="wardOptions"
              label="Department / unit"
              filled
              dense
              emit-value
              map-options
              use-input
              input-debounce="200"
              @filter="filterDepartments"
              :rules="[(v) => !!v || 'Required']"
              hint="Stock list and debits use this department"
            >
              <template v-slot:no-option>
                <q-item>
                  <q-item-section class="text-grey">No matching department</q-item-section>
                </q-item>
              </template>
            </q-select>
          </div>
        </div>

        <q-banner v-if="form.requesting_department && !stockLoading && stockRows.length === 0" rounded class="bg-grey-8 text-white q-mb-md">
          No stock lines are recorded for this department yet. Create a requisition so the store can supply items to this unit.
          <div class="q-mt-sm">
            <q-btn unelevated color="primary" label="How to request stock" @click="showRequestStockHelp" />
          </div>
        </q-banner>

        <div v-if="form.requesting_department" class="q-mb-md">
          <div class="text-body2 text-weight-medium q-mb-sm">Items in this department</div>
          <q-input
            v-model="stockFilter"
            dense
            filled
            clearable
            label="Search by name or code"
            class="q-mb-sm"
          >
            <template v-slot:prepend>
              <q-icon name="search" />
            </template>
          </q-input>
          <q-linear-progress v-if="stockLoading" indeterminate class="q-mb-sm" />
          <q-table
            v-else
            flat
            bordered
            dense
            :rows="filteredStockRows"
            :columns="stockColumns"
            row-key="product_code"
            selection="single"
            v-model:selected="stockSelected"
            @update:selected="onStockSelectionChange"
            :rows-per-page-options="[10, 15, 25]"
            :pagination="{ rowsPerPage: 10 }"
            class="stock-table diag-table"
          >
            <template v-slot:body-cell-quantity="props">
              <q-td :props="props">
                <span :class="props.row.quantity <= 0 ? 'text-negative text-weight-bold' : ''">
                  {{ formatQty(props.row.quantity) }}
                </span>
                <q-badge v-if="props.row.quantity <= 0" color="negative" label="Out of stock" class="q-ml-sm" />
              </q-td>
            </template>
            <template v-slot:body-cell-actions="props">
              <q-td :props="props">
                <q-btn flat dense no-caps color="primary" label="Use" @click.stop="selectStockRow(props.row)" />
              </q-td>
            </template>
          </q-table>
        </div>

        <q-banner v-if="selectedOutOfStock" rounded class="bg-negative text-white q-mb-md">
          This item is out of stock. Submit a pharmacy requisition before adding it.
          <div class="q-mt-sm">
            <q-btn outline color="white" label="What to do next" @click="showRequestStockHelp" />
          </div>
        </q-banner>

        <q-form @submit.prevent="addLineToPending" class="row q-col-gutter-md q-mb-md">
          <div class="col-12 col-md-3">
            <q-input v-model="form.product_code" filled dense label="Product code" :rules="[(v) => !!((v || '').trim()) || 'Required']" />
          </div>
          <div class="col-12 col-md-3">
            <q-input v-model="form.product_name" filled dense label="Product name" :rules="[(v) => !!((v || '').trim()) || 'Required']" />
          </div>
          <div class="col-12 col-sm-4 col-md-2">
            <q-input
              v-model.number="form.quantity"
              type="number"
              step="any"
              filled
              dense
              label="Quantity"
              min="0.01"
              :rules="[validateQtyRule]"
            />
          </div>
          <div class="col-12 col-sm-4 col-md-2">
            <q-input
              v-model.number="form.unit_price"
              type="number"
              step="any"
              filled
              dense
              label="Unit price (optional)"
            />
          </div>
          <div class="col-12 col-md-8">
            <q-input v-model="form.notes" filled dense label="Notes (optional)" />
          </div>
          <div class="col-12 col-sm-6 col-md-4 flex items-center">
            <q-checkbox v-model="form.charge_to_client" label="On client bill" color="primary" dense />
          </div>
          <div class="col-12">
            <q-btn type="submit" color="secondary" outline label="Add to list" :disable="selectedOutOfStock" />
          </div>
        </q-form>

        <div v-if="pendingLines.length > 0" class="q-mb-md">
          <div class="text-subtitle2 q-mb-sm">Ready to save ({{ pendingLines.length }})</div>
          <q-table
            flat
            bordered
            dense
            :rows="pendingLines"
            :columns="pendingColumns"
            row-key="_localId"
            :pagination="{ rowsPerPage: 15 }"
            :rows-per-page-options="[10, 15, 25]"
            class="diag-table"
          >
            <template v-slot:body-cell-quantity="props">
              <q-td :props="props">
                <q-input
                  v-model.number="props.row.quantity"
                  type="number"
                  step="any"
                  dense
                  filled
                  min="0.01"
                  style="max-width: 120px"
                />
              </q-td>
            </template>
            <template v-slot:body-cell-charge_to_client="props">
              <q-td :props="props">
                <q-checkbox v-model="props.row.charge_to_client" dense color="primary" />
              </q-td>
            </template>
            <template v-slot:body-cell-actions="props">
              <q-td :props="props">
                <q-btn flat dense round icon="delete" color="negative" @click="removePendingLine(props.row._localId)">
                  <q-tooltip>Remove from list</q-tooltip>
                </q-btn>
              </q-td>
            </template>
          </q-table>
          <div class="row q-gutter-sm q-mt-md">
            <q-btn color="primary" label="Save all" :loading="savingBatch" :disable="savingBatch || pendingLines.length === 0" @click="saveAllPending" />
            <q-btn flat label="Clear list" :disable="pendingLines.length === 0" @click="clearPendingLines" />
          </div>
        </div>

        <q-expansion-item
          v-if="form.requesting_department"
          label="Product not in the list above?"
          header-class="text-grey-7"
          class="q-mt-sm"
        >
          <div class="text-caption text-grey-7 q-pa-sm">
            Check the department name matches ward stock exactly. Add stock via a pharmacy requisition if needed.
          </div>
        </q-expansion-item>
      </div>
    </section>

    <section class="diag-panel">
      <div class="panel-head">
        <div>
          <div class="panel-title">Recorded debits for this visit</div>
          <div class="panel-sub">{{ debits.length }} line{{ debits.length === 1 ? '' : 's' }} on file</div>
        </div>
      </div>
      <div class="table-wrap">
        <q-table
          :rows="debits"
          :columns="columns"
          row-key="id"
          flat
          dense
          :loading="loading"
          :rows-per-page-options="[10, 25, 50]"
          class="diag-table"
        >
          <template v-slot:body-cell-charged="props">
            <q-td :props="props">
              <q-badge v-if="props.row.charged_to_client" color="positive" label="On bill" />
              <span v-else class="text-grey-6">Not on bill</span>
            </q-td>
          </template>
          <template v-slot:body-cell-released="props">
            <q-td :props="props">
              <q-badge v-if="props.row.is_released" color="info" label="Released" />
              <q-badge v-else color="warning" label="Pending release" />
            </q-td>
          </template>
          <template v-slot:body-cell-actions="props">
            <q-td :props="props">
              <div class="row q-gutter-xs no-wrap justify-end">
                <q-btn
                  v-if="visit && visit.status === 'open' && !props.row.is_released"
                  flat
                  dense
                  size="sm"
                  icon="edit"
                  color="primary"
                  @click="openEditDebit(props.row)"
                >
                  <q-tooltip>Edit</q-tooltip>
                </q-btn>
                <q-btn
                  v-if="visit && visit.status === 'open' && !props.row.is_released"
                  flat
                  dense
                  size="sm"
                  icon="delete"
                  color="negative"
                  @click="confirmDeleteDebit(props.row)"
                >
                  <q-tooltip>Delete</q-tooltip>
                </q-btn>
                <q-btn
                  v-if="canCharge && visit && visit.status === 'open' && !props.row.charged_to_client && !props.row.is_released"
                  flat
                  dense
                  size="sm"
                  color="primary"
                  label="Add to bill"
                  :loading="chargingId === props.row.id"
                  @click="chargeToBill(props.row)"
                />
                <span v-else-if="props.row.charged_to_client" class="text-caption text-grey-7">Line #{{ props.row.companion_visit_item_id }}</span>
              </div>
            </q-td>
          </template>
        </q-table>
      </div>
    </section>

    <q-dialog v-model="editDebitOpen">
      <q-card class="companion-dialog-card" style="min-width: 360px">
        <q-card-section class="companion-dialog-head">
          <div class="dialog-head-row">
            <div>
              <div class="dialog-title">Edit debit</div>
              <div class="dialog-sub">{{ editDebitRow?.product_name }}</div>
            </div>
            <q-btn icon="close" flat round dense v-close-popup />
          </div>
        </q-card-section>
        <q-card-section class="q-gutter-md">
          <q-input v-model.number="editForm.quantity" type="number" step="any" filled label="Quantity" min="0.01" />
          <q-input v-model="editForm.notes" filled label="Notes" type="textarea" rows="2" />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Cancel" v-close-popup />
          <q-btn color="primary" label="Save" :loading="editSaving" @click="submitEditDebit" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useQuasar } from 'quasar';
import { companionVisitsAPI, wardsAPI } from '../../services/api';
import { useAuthStore } from '../../stores/auth';
import { useAppModeStore } from '../../stores/appMode';
import HmsPageHeader from '../../components/ui/HmsPageHeader.vue';
import HmsButton from '../../components/ui/HmsButton.vue';
import HmsBadge from '../../components/ui/HmsBadge.vue';

const route = useRoute();
const router = useRouter();
const $q = useQuasar();
const authStore = useAuthStore();
const appModeStore = useAppModeStore();

const id = computed(() => route.params.id);
const visit = ref(null);
const debits = ref([]);
const loading = ref(true);
const savingBatch = ref(false);
const chargingId = ref(null);
const editDebitOpen = ref(false);
const editSaving = ref(false);
const editDebitRow = ref(null);
const editForm = ref({ quantity: 1, notes: '' });

const allWardOptions = ref([]);
const wardOptions = ref([]);
const stockRows = ref([]);
const stockLoading = ref(false);
const stockFilter = ref('');
const stockSelected = ref([]);
const pickedAvailability = ref(null);

let nextLocalId = 1;
const pendingLines = ref([]);

const form = ref({
  requesting_department: null,
  product_code: '',
  product_name: '',
  quantity: 1,
  unit_price: null,
  notes: '',
  charge_to_client: true,
});

const canRecord = computed(() => authStore.canAccess(['Nurse', 'Doctor', 'PA', 'Admin']));
const canCharge = computed(() =>
  authStore.canAccess(['Billing', 'Nurse', 'Doctor', 'PA', 'Pharmacy', 'Pharmacy Head', 'Admin'])
);

const visitInitials = computed(() => {
  const name = (visit.value?.client_name || '').trim();
  if (!name) return 'CV';
  const parts = name.split(/\s+/).filter(Boolean);
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
});

const selectedOutOfStock = computed(() => {
  if (pickedAvailability.value == null) return false;
  return Number(pickedAvailability.value) <= 0;
});

const filteredStockRows = computed(() => {
  const q = (stockFilter.value || '').trim().toLowerCase();
  if (!q) return stockRows.value;
  return stockRows.value.filter(
    (r) =>
      (r.product_name || '').toLowerCase().includes(q) || (r.product_code || '').toLowerCase().includes(q)
  );
});

const stockColumns = [
  { name: 'product_name', label: 'Product', field: 'product_name', align: 'left', sortable: true },
  { name: 'product_code', label: 'Code', field: 'product_code', align: 'left', sortable: true },
  { name: 'quantity', label: 'Available', field: 'quantity', align: 'right', sortable: true },
  { name: 'actions', label: '', field: 'product_code', align: 'right' },
];

const pendingColumns = [
  { name: 'requesting_department', label: 'Department', field: 'requesting_department', align: 'left' },
  { name: 'product_name', label: 'Product', field: 'product_name', align: 'left' },
  { name: 'product_code', label: 'Code', field: 'product_code', align: 'left' },
  { name: 'quantity', label: 'Qty', field: 'quantity', align: 'center' },
  {
    name: 'charge_to_client',
    label: 'On client bill',
    field: 'charge_to_client',
    align: 'center',
  },
  { name: 'notes', label: 'Notes', field: 'notes', align: 'left' },
  { name: 'actions', label: '', field: '_localId', align: 'right' },
];

const columns = [
  { name: 'dept', label: 'Department', field: 'requesting_department', align: 'left', sortable: true },
  { name: 'product_name', label: 'Product', field: 'product_name', align: 'left', sortable: true },
  { name: 'product_code', label: 'Code', field: 'product_code', align: 'left', sortable: true },
  { name: 'quantity', label: 'Qty', field: 'quantity', align: 'center', sortable: true },
  {
    name: 'total',
    label: 'Total',
    field: 'total_price',
    align: 'right',
    sortable: true,
    format: (v) => (v != null && Number.isFinite(Number(v)) ? `GH¢ ${Number(v).toFixed(2)}` : '—'),
  },
  { name: 'charged', label: 'Bill', field: 'charged_to_client', align: 'center', sortable: true },
  { name: 'released', label: 'Pharmacy release', field: 'is_released', align: 'center', sortable: true },
  { name: 'recorded', label: 'Recorded by', field: 'recorded_by_name', align: 'left', sortable: true },
  { name: 'actions', label: '', field: 'id', align: 'right' },
];

function deptLabel(w) {
  const t = (w.department_type || '').replace(/_/g, ' ');
  return `${w.name} (${t})`;
}

function filterDepartments(val, update) {
  if (val === '') {
    update(() => {
      wardOptions.value = allWardOptions.value;
    });
    return;
  }
  const needle = val.toLowerCase();
  update(() => {
    wardOptions.value = allWardOptions.value.filter((o) => o.label.toLowerCase().indexOf(needle) > -1);
  });
}

async function loadWards() {
  try {
    const res = await wardsAPI.getAll(true);
    const list = (res.data || []).slice().sort((a, b) => (a.name || '').localeCompare(b.name || ''));
    allWardOptions.value = list.map((w) => ({ label: deptLabel(w), value: w.name }));
    wardOptions.value = allWardOptions.value;
  } catch {
    allWardOptions.value = [];
    wardOptions.value = [];
  }
}

async function loadDepartmentStock(wardName) {
  stockRows.value = [];
  stockSelected.value = [];
  pickedAvailability.value = null;
  stockFilter.value = '';
  if (!wardName) return;
  stockLoading.value = true;
  try {
    const res = await companionVisitsAPI.getDepartmentStock(wardName);
    stockRows.value = res.data || [];
  } catch (e) {
    stockRows.value = [];
    $q.notify({
      type: 'negative',
      message: e.response?.data?.detail || 'Could not load department stock',
      position: 'top',
    });
  } finally {
    stockLoading.value = false;
  }
}

function formatQty(q) {
  if (q == null || !Number.isFinite(Number(q))) return '—';
  const n = Number(q);
  return n % 1 === 0 ? String(n) : n.toFixed(2);
}

function selectStockRow(row) {
  if (!row) return;
  form.value.product_code = row.product_code || '';
  form.value.product_name = row.product_name || '';
  pickedAvailability.value = row.quantity != null ? Number(row.quantity) : null;
  stockSelected.value = [row];
  if (selectedOutOfStock.value) {
    $q.notify({
      type: 'warning',
      message: 'This item is out of stock. Request stock via a pharmacy requisition before debiting.',
      position: 'top',
      timeout: 5000,
    });
  }
}

function onStockSelectionChange(rows) {
  if (rows && rows.length) {
    selectStockRow(rows[0]);
  } else {
    pickedAvailability.value = null;
  }
}

function validateQtyRule(val) {
  const n = Number(val);
  if (!Number.isFinite(n) || n <= 0) return 'Enter a positive quantity';
  if (pickedAvailability.value != null && Number(pickedAvailability.value) > 0 && n > Number(pickedAvailability.value)) {
    return `Not enough stock (available ${formatQty(pickedAvailability.value)})`;
  }
  return true;
}

function addLineToPending() {
  if (!form.value.requesting_department) {
    $q.notify({ type: 'warning', message: 'Select a department first', position: 'top' });
    return;
  }
  if (selectedOutOfStock.value) {
    promptInsufficientStock('This item is out of stock.');
    return;
  }
  const q = Number(form.value.quantity);
  if (pickedAvailability.value != null && Number(pickedAvailability.value) > 0 && q > Number(pickedAvailability.value)) {
    promptInsufficientStock(
      `Only ${formatQty(pickedAvailability.value)} available. Request more stock or reduce quantity.`
    );
    return;
  }
  pendingLines.value.push({
    _localId: nextLocalId++,
    requesting_department: form.value.requesting_department,
    product_code: (form.value.product_code || '').trim(),
    product_name: (form.value.product_name || '').trim(),
    quantity: q,
    unit_price:
      form.value.unit_price != null && form.value.unit_price !== '' ? Number(form.value.unit_price) : null,
    notes: (form.value.notes || '').trim() || undefined,
    charge_to_client: !!form.value.charge_to_client,
  });
  form.value.product_code = '';
  form.value.product_name = '';
  form.value.quantity = 1;
  form.value.unit_price = null;
  form.value.notes = '';
  form.value.charge_to_client = true;
  stockSelected.value = [];
  pickedAvailability.value = null;
  $q.notify({ type: 'positive', message: 'Line added — adjust in the table or save when ready', position: 'top' });
}

function removePendingLine(localId) {
  pendingLines.value = pendingLines.value.filter((l) => l._localId !== localId);
}

function clearPendingLines() {
  pendingLines.value = [];
}

async function saveAllPending() {
  if (!id.value || pendingLines.value.length === 0) return;
  for (const line of pendingLines.value) {
    const q = Number(line.quantity);
    if (!Number.isFinite(q) || q <= 0) {
      $q.notify({ type: 'negative', message: 'Each line needs a positive quantity', position: 'top' });
      return;
    }
  }
  savingBatch.value = true;
  try {
    const items = pendingLines.value.map((l) => ({
      requesting_department: l.requesting_department,
      product_code: l.product_code,
      product_name: l.product_name,
      quantity: Number(l.quantity),
      unit_price: l.unit_price != null && l.unit_price !== '' ? Number(l.unit_price) : undefined,
      notes: l.notes,
      charge_to_client: !!l.charge_to_client,
    }));
    await companionVisitsAPI.batchInventoryDebits(id.value, items);
    $q.notify({ type: 'positive', message: 'All lines saved', position: 'top' });
    pendingLines.value = [];
    await loadDepartmentStock(form.value.requesting_department);
    await loadDebits();
  } catch (e) {
    const detail = e.response?.data?.detail;
    const msg = typeof detail === 'string' ? detail : e.message || 'Save failed';
    if (msg.toLowerCase().includes('insufficient') || msg.toLowerCase().includes('requisition')) {
      promptInsufficientStock(msg);
    } else {
      $q.notify({ type: 'negative', message: msg, position: 'top' });
    }
  } finally {
    savingBatch.value = false;
  }
}

function showRequestStockHelp() {
  $q.dialog({
    title: 'Request stock from the store',
    message:
      'Use Pharmacy → Create requisition to request items for your department. After Pharmacy Head approval and Store fulfilment, stock will appear in this list.\n\n' +
      'If you are in Companion mode, switch to full HMS or Inventory mode from the app mode menu to open Pharmacy.',
    html: false,
    ok: { label: 'Open create requisition', color: 'primary', flat: false },
    cancel: { label: 'Close', flat: true },
  }).onOk(() => {
    goToCreateRequisition();
  });
}

function goToCreateRequisition() {
  if (appModeStore.isInventory) {
    router.push({ name: 'InventoryModeCreateRequisition' }).catch(() => {});
  } else {
    appModeStore.setHms();
    router.push({ name: 'CreateRequisition' }).catch(() => {});
  }
}

function promptInsufficientStock(detail) {
  $q.dialog({
    title: 'Insufficient stock',
    message:
      (detail || 'Not enough quantity in this department.') +
      ' Submit a pharmacy requisition to restock, then try again.',
    prompt: false,
    ok: { label: 'How to request stock', color: 'primary' },
    cancel: { label: 'OK', flat: true },
  }).onOk(() => {
    showRequestStockHelp();
  });
}

watch(
  () => form.value.requesting_department,
  (w) => {
    loadDepartmentStock(w);
  }
);

async function loadVisit() {
  if (!id.value) return;
  const res = await companionVisitsAPI.get(id.value);
  visit.value = res.data;
}

async function loadDebits() {
  if (!id.value) return;
  loading.value = true;
  try {
    const res = await companionVisitsAPI.listInventoryDebits(id.value);
    debits.value = res.data || [];
  } catch (e) {
    debits.value = [];
    $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Failed to load debits', position: 'top' });
  } finally {
    loading.value = false;
  }
}

function openEditDebit(row) {
  editDebitRow.value = row;
  editForm.value = {
    quantity: Number(row.quantity),
    notes: row.notes || '',
  };
  editDebitOpen.value = true;
}

async function submitEditDebit() {
  if (!id.value || !editDebitRow.value) return;
  const q = Number(editForm.value.quantity);
  if (!Number.isFinite(q) || q <= 0) {
    $q.notify({ type: 'negative', message: 'Invalid quantity', position: 'top' });
    return;
  }
  editSaving.value = true;
  try {
    await companionVisitsAPI.updateInventoryDebit(id.value, editDebitRow.value.id, {
      quantity: q,
      notes: (editForm.value.notes || '').trim() || null,
    });
    $q.notify({ type: 'positive', message: 'Updated', position: 'top' });
    editDebitOpen.value = false;
    await loadDepartmentStock(form.value.requesting_department);
    await loadDebits();
  } catch (e) {
    const d = e.response?.data?.detail;
    $q.notify({ type: 'negative', message: typeof d === 'string' ? d : e.message || 'Update failed', position: 'top' });
  } finally {
    editSaving.value = false;
  }
}

function confirmDeleteDebit(row) {
  $q.dialog({
    title: 'Remove debit',
    message: `Remove "${row.product_name}" from this visit and restore stock to ${row.requesting_department}?`,
    cancel: true,
    persistent: true,
    ok: { label: 'Delete', color: 'negative' },
  }).onOk(async () => {
    if (!id.value) return;
    try {
      await companionVisitsAPI.deleteInventoryDebit(id.value, row.id);
      $q.notify({ type: 'positive', message: 'Debit removed', position: 'top' });
      await loadDepartmentStock(form.value.requesting_department);
      await loadDebits();
    } catch (e) {
      const d = e.response?.data?.detail;
      $q.notify({ type: 'negative', message: typeof d === 'string' ? d : e.message || 'Delete failed', position: 'top' });
    }
  });
}

async function chargeToBill(row) {
  if (!id.value) return;
  chargingId.value = row.id;
  try {
    await companionVisitsAPI.chargeInventoryDebitToBill(id.value, row.id);
    $q.notify({ type: 'positive', message: 'Added to client bill', position: 'top' });
    await loadDebits();
  } catch (e) {
    $q.notify({
      type: 'negative',
      message: e.response?.data?.detail || e.message || 'Could not add to bill',
      position: 'top',
    });
  } finally {
    chargingId.value = null;
  }
}

onMounted(async () => {
  await loadWards();
  await loadVisit();
  await loadDebits();
  if (form.value.requesting_department) {
    await loadDepartmentStock(form.value.requesting_department);
  }
});
</script>

<style scoped>
.soft-banner--warn {
  border-color: color-mix(in srgb, var(--hms-warning, #d97706) 28%, var(--hms-border));
  background: color-mix(in srgb, var(--hms-warning, #d97706) 10%, var(--hms-surface));
}
.companion-dialog-card {
  border-radius: 1.25rem;
  border: 1px solid var(--hms-border);
  background: var(--hms-panel-bg);
  box-shadow: var(--hms-shadow-lg);
  overflow: hidden;
}
.companion-dialog-head {
  border-bottom: 1px solid var(--hms-border);
  background: linear-gradient(180deg, var(--hms-surface) 0%, transparent 100%);
}
.dialog-head-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
}
.dialog-title {
  font-size: var(--hms-text-base);
  font-weight: 750;
  letter-spacing: var(--hms-tracking-tight);
  color: var(--hms-text-primary);
}
.dialog-sub {
  margin-top: 0.2rem;
  font-size: var(--hms-text-xs);
  color: var(--hms-text-muted);
}
.stock-table :deep(.q-table__top) {
  padding: 0;
}
</style>
