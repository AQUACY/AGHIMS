<template>
  <q-page class="q-pa-md">
    <div class="text-h4 q-mb-md text-weight-bold glass-text">
      Undertakings
    </div>
    <div class="text-subtitle1 text-secondary q-mb-lg">
      Approve or unapprove undertakings for Companion (copayment) visits: clients may pay a part payment now and promise (undertaking) to pay the balance later.
      Once approved, Billing can close the visit even when line items are unpaid.
    </div>

    <q-card class="q-mb-md glass-card" flat>
      <q-card-section>
        <div class="row items-center justify-between">
          <div class="text-h6 glass-text">Undertakings</div>
          <q-btn
            unelevated
            label="Refresh"
            class="glass-button"
            icon="refresh"
            :loading="loading"
            @click="loadAll"
          />
        </div>
        <q-tabs
          v-model="tab"
          dense
          class="q-mt-md"
          active-color="primary"
          indicator-color="primary"
          align="left"
        >
          <q-tab name="pending" icon="hourglass_empty" label="Pending" />
          <q-tab name="approved" icon="check_circle" label="My approvals" />
          <q-tab name="rejected" icon="cancel" label="My rejections" />
        </q-tabs>
      </q-card-section>
    </q-card>

    <q-card class="glass-card" flat>
      <q-card-section>
        <q-table
          :rows="currentRows"
          :columns="columns"
          row-key="id"
          flat
          :loading="loading"
          :rows-per-page-options="[10, 25, 50]"
          class="glass-table"
          :no-data-label="noDataLabel"
        >
          <template v-slot:body-cell-undertaking_requested_at="props">
            <q-td :props="props">{{ formatDate(props.row.undertaking_requested_at) }}</q-td>
          </template>
          <template v-slot:body-cell-undertaking_deposit_amount="props">
            <q-td :props="props">{{ formatPrice(props.row.undertaking_deposit_amount) }}</q-td>
          </template>
          <template v-slot:body-cell-actions="props">
            <q-td :props="props">
              <q-btn
                flat
                dense
                size="sm"
                icon="receipt_long"
                class="q-mr-sm"
                @click="viewBilling(props.row)"
              >
                <q-tooltip>View billing</q-tooltip>
              </q-btn>
              <q-btn
                v-if="canAdmin"
                flat
                dense
                size="sm"
                color="negative"
                icon="delete"
                class="q-mr-sm"
                :loading="deletingId === props.row.id"
                @click="deleteUndertaking(props.row)"
              >
                <q-tooltip>Delete undertaking (Admin only)</q-tooltip>
              </q-btn>
              <q-btn
                v-if="tab === 'approved'"
                flat
                dense
                size="sm"
                color="warning"
                icon="undo"
                label="Reverse"
                :loading="reversingId === props.row.id"
                @click="reverseApproval(props.row)"
              >
                <q-tooltip>Reverse approval back to pending</q-tooltip>
              </q-btn>
              <q-btn
                v-if="tab === 'rejected'"
                flat
                dense
                size="sm"
                color="warning"
                icon="undo"
                label="Revert"
                :loading="revertingRejectId === props.row.id"
                @click="revertRejection(props.row)"
              >
                <q-tooltip>Revert rejection back to pending</q-tooltip>
              </q-btn>
              <q-btn
                v-if="tab === 'pending'"
                flat
                dense
                size="sm"
                color="positive"
                icon="check_circle"
                label="Approve"
                :loading="approvingId === props.row.id"
                @click="approve(props.row)"
              >
                <q-tooltip>Approve undertaking</q-tooltip>
              </q-btn>
              <q-btn
                v-if="tab === 'pending'"
                flat
                dense
                size="sm"
                color="negative"
                icon="cancel"
                label="Reject"
                :loading="rejectingId === props.row.id"
                @click="reject(props.row)"
              >
                <q-tooltip>Reject undertaking</q-tooltip>
              </q-btn>
            </q-td>
          </template>
        </q-table>
      </q-card-section>
    </q-card>

    <!-- Billing detail dialog -->
    <q-dialog v-model="showBillingDialog" persistent full-width>
      <q-card style="max-width: 900px; width: 100%;">
        <q-card-section>
          <div class="row items-center justify-between">
            <div>
              <div class="text-h6">Undertaking billing detail</div>
              <div class="text-caption text-grey-7 q-mt-xs">
                Card {{ billingVisit?.external_card_number }} &mdash; Visit {{ billingVisit?.external_visit_number }} &mdash;
                {{ billingVisit?.client_name }}
              </div>
            </div>
            <q-btn flat round dense icon="close" v-close-popup />
          </div>
        </q-card-section>
        <q-card-section>
          <div class="q-mb-md">
            <div class="text-subtitle2">Undertaking</div>
            <div class="text-body2">
              Status: <strong>{{ billingVisit?.undertaking_status || '—' }}</strong>,
              Part payment: <strong>GH¢ {{ formatPrice(billingVisit?.undertaking_deposit_amount) }}</strong>,
              Part payment receipt: <strong>{{ billingVisit?.undertaking_deposit_receipt_number || '—' }}</strong>
            </div>
            <div class="text-body2 q-mt-xs">
              Approved by: <strong>{{ billingVisit?.undertaking_approved_by_name || '—' }}</strong>,
              Rejected by: <strong>{{ billingVisit?.undertaking_unapproved_by_name || '—' }}</strong>
            </div>
            <div class="text-body2 q-mt-xs">
              Total items: <strong>GH¢ {{ formatPrice(itemsTotal) }}</strong>,
              Paid so far: <strong>GH¢ {{ formatPrice(paidTotal) }}</strong>,
              Remaining after part payment: <strong>GH¢ {{ formatPrice(remainingToPay) }}</strong>
            </div>
          </div>
          <q-tabs
            v-model="billingTab"
            dense
            active-color="primary"
            indicator-color="primary"
            align="left"
            class="q-mb-sm"
          >
            <q-tab name="pending" icon="hourglass_empty" label="Pending items" />
            <q-tab name="paid" icon="check_circle" label="Paid items" />
            <q-tab name="all" icon="list" label="All items" />
          </q-tabs>

          <q-table
            :rows="billingRows"
            :columns="billingColumns"
            row-key="id"
            flat
            hide-pagination
            class="glass-table"
            :loading="billingLoading"
            :no-data-label="billingNoDataLabel"
          >
            <template v-slot:body-cell-amount="props">
              <q-td :props="props">GH¢ {{ formatPrice(rowAmount(props.row)) }}</q-td>
            </template>
            <template v-slot:body-cell-receipt_number="props">
              <q-td :props="props">
                <div>{{ props.row.receipt_number || '—' }}</div>
                <div v-if="props.row.payment_method" class="text-caption text-grey-7">
                  {{ props.row.payment_method }}
                </div>
              </q-td>
            </template>
            <template v-slot:body-cell-paid_at="props">
              <q-td :props="props">{{ formatDate(props.row.paid_at) }}</q-td>
            </template>
          </q-table>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Close" v-close-popup />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue';
import { useQuasar } from 'quasar';
import { companionVisitsAPI } from '../services/api';
import { useAuthStore } from '../stores/auth';

const $q = useQuasar();
const authStore = useAuthStore();

const loading = ref(false);
const approvingId = ref(null);
const rejectingId = ref(null);
const allVisits = ref([]);
const tab = ref('pending');

const showBillingDialog = ref(false);
const billingVisit = ref(null);
const billingItems = ref([]);
const billingLoading = ref(false);
const billingTab = ref('pending');
const reversingId = ref(null);
const deletingId = ref(null);
const revertingRejectId = ref(null);

const columns = [
  { name: 'id', label: 'ID', field: 'id', align: 'left', sortable: true },
  { name: 'external_card_number', label: 'Card', field: 'external_card_number', align: 'left' },
  { name: 'external_visit_number', label: 'Visit #', field: 'external_visit_number', align: 'left' },
  { name: 'client_name', label: 'Client', field: 'client_name', align: 'left' },
  { name: 'undertaking_requested_at', label: 'Requested at', field: 'undertaking_requested_at', align: 'left' },
  { name: 'undertaking_requested_by_name', label: 'Requested by', field: 'undertaking_requested_by_name', align: 'left' },
  { name: 'undertaking_deposit_amount', label: 'Part payment', field: 'undertaking_deposit_amount', align: 'right' },
  { name: 'actions', label: 'Actions', field: 'actions', align: 'left' },
];

const billingColumns = [
  { name: 'item_name', label: 'Item', field: 'item_name', align: 'left' },
  { name: 'category', label: 'Category', field: 'category', align: 'left' },
  { name: 'unit_price', label: 'Unit price', field: 'unit_price', align: 'right' },
  { name: 'quantity', label: 'Qty', field: 'quantity', align: 'right' },
  { name: 'amount', label: 'Amount', field: 'amount', align: 'right' },
  { name: 'receipt_number', label: 'Receipt / Payment', field: 'receipt_number', align: 'left' },
  { name: 'paid_at', label: 'Paid at', field: 'paid_at', align: 'left' },
];

const currentUserId = computed(() => authStore.user?.id || null);
const canAdmin = computed(() => authStore.canAccess(['Admin']));

const pendingVisits = computed(() =>
  (allVisits.value || []).filter(
    (v) => (v.undertaking_status || '').toLowerCase() === 'pending'
  )
);

const myApprovedVisits = computed(() =>
  (allVisits.value || []).filter(
    (v) =>
      (v.undertaking_status || '').toLowerCase() === 'approved' &&
      v.undertaking_approved_by_id === currentUserId.value
  )
);

const myRejectedVisits = computed(() =>
  (allVisits.value || []).filter(
    (v) =>
      (v.undertaking_status || '').toLowerCase() === 'rejected' &&
      v.undertaking_unapproved_by_id === currentUserId.value
  )
);

const currentRows = computed(() => {
  if (tab.value === 'approved') return myApprovedVisits.value;
  if (tab.value === 'rejected') return myRejectedVisits.value;
  return pendingVisits.value;
});

const noDataLabel = computed(() => {
  if (tab.value === 'approved') return 'No undertakings you have approved yet.';
  if (tab.value === 'rejected') return 'No undertakings you have rejected yet.';
  return 'No pending undertakings.';
});

const paidItems = computed(() => (billingItems.value || []).filter((i) => Boolean(i.receipt_number)));
const pendingItems = computed(() => (billingItems.value || []).filter((i) => !i.receipt_number));

const itemsTotal = computed(() => (billingItems.value || []).reduce((sum, r) => sum + rowAmount(r), 0));
const paidTotal = computed(() => (paidItems.value || []).reduce((sum, r) => sum + rowAmount(r), 0));
const depositAmount = computed(() => Number(billingVisit.value?.undertaking_deposit_amount || 0) || 0);
const remainingToPay = computed(() => Math.max(0, itemsTotal.value - paidTotal.value - depositAmount.value));

const billingRows = computed(() => {
  if (billingTab.value === 'paid') return paidItems.value;
  if (billingTab.value === 'all') return billingItems.value || [];
  return pendingItems.value;
});

const billingNoDataLabel = computed(() => {
  if (billingTab.value === 'paid') return 'No paid items yet.';
  if (billingTab.value === 'all') return 'No items.';
  return 'No pending items.';
});

function formatPrice(val) {
  if (val == null) return '—';
  const n = Number(val);
  if (Number.isNaN(n)) return '—';
  return n.toFixed(2);
}

function formatDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString();
}

async function loadAll() {
  loading.value = true;
  try {
    const res = await companionVisitsAPI.list();
    allVisits.value = (res.data || []).filter(
      (v) => v.undertaking_requested_at // only visits that have an undertaking
    );
  } catch (e) {
    console.error('Failed to load undertakings', e);
    $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Failed to load' });
    allVisits.value = [];
  } finally {
    loading.value = false;
  }
}

async function approve(visit) {
  approvingId.value = visit.id;
  try {
    await companionVisitsAPI.approveUndertaking(visit.id);
    $q.notify({ type: 'positive', message: 'Undertaking approved.' });
    await loadAll();
  } catch (e) {
    $q.notify({
      type: 'negative',
      message: e.response?.data?.detail || 'Failed to approve',
    });
  } finally {
    approvingId.value = null;
  }
}

async function reject(visit) {
  $q.dialog({
    title: 'Reject undertaking',
    message: 'Provide a reason for rejecting this undertaking.',
    prompt: {
      model: '',
      type: 'text',
      isValid: (val) => Boolean((val || '').trim()),
    },
    cancel: true,
    persistent: true,
  }).onOk(async (reason) => {
    rejectingId.value = visit.id;
    try {
      await companionVisitsAPI.rejectUndertaking(visit.id, { reason: String(reason || '').trim() });
      $q.notify({ type: 'positive', message: 'Undertaking rejected.' });
      await loadAll();
      tab.value = 'rejected';
    } catch (e) {
      $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Failed to reject undertaking' });
    } finally {
      rejectingId.value = null;
    }
  });
}

function rowAmount(row) {
  const q = Number(row.quantity || 0);
  const u = Number(row.unit_price || 0);
  if (Number.isNaN(q) || Number.isNaN(u)) return 0;
  return q * u;
}

async function viewBilling(visit) {
  billingVisit.value = null;
  billingItems.value = [];
  showBillingDialog.value = true;
  billingTab.value = 'pending';
  billingLoading.value = true;
  try {
    const [visitRes, itemsRes] = await Promise.all([
      companionVisitsAPI.get(visit.id),
      companionVisitsAPI.getItems(visit.id),
    ]);
    billingVisit.value = visitRes.data || null;
    billingItems.value = itemsRes.data || [];
  } catch (e) {
    console.error('Failed to load billing detail', e);
    $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Failed to load billing detail' });
  } finally {
    billingLoading.value = false;
  }
}

async function reverseApproval(visit) {
  $q.dialog({
    title: 'Reverse approval',
    message: 'Provide a reason to reverse this undertaking back to pending.',
    prompt: {
      model: '',
      type: 'text',
      isValid: (val) => Boolean((val || '').trim()),
    },
    cancel: true,
    persistent: true,
  }).onOk(async (reason) => {
    reversingId.value = visit.id;
    try {
      await companionVisitsAPI.unapproveUndertaking(visit.id, { reason: String(reason || '').trim() });
      $q.notify({ type: 'positive', message: 'Approval reversed back to pending.' });
      await loadAll();
      tab.value = 'pending';
    } catch (e) {
      $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Failed to reverse approval' });
    } finally {
      reversingId.value = null;
    }
  });
}

async function deleteUndertaking(visit) {
  $q.dialog({
    title: 'Delete undertaking',
    message: 'Admin only. This will permanently remove the undertaking fields (status, deposit, approvals/rejections) for this visit. Continue?',
    cancel: true,
    persistent: true,
  }).onOk(async () => {
    deletingId.value = visit.id;
    try {
      await companionVisitsAPI.deleteUndertaking(visit.id);
      $q.notify({ type: 'positive', message: 'Undertaking deleted.' });
      if (showBillingDialog.value && billingVisit.value?.id === visit.id) {
        showBillingDialog.value = false;
      }
      await loadAll();
    } catch (e) {
      $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Failed to delete undertaking' });
    } finally {
      deletingId.value = null;
    }
  });
}

async function revertRejection(visit) {
  revertingRejectId.value = visit.id;
  try {
    await companionVisitsAPI.revertRejectedUndertaking(visit.id);
    $q.notify({ type: 'positive', message: 'Rejection reverted back to pending.' });
    await loadAll();
    tab.value = 'pending';
  } catch (e) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Failed to revert rejection' });
  } finally {
    revertingRejectId.value = null;
  }
}

onMounted(() => {
  loadAll();
});
</script>
