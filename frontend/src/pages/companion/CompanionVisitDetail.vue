<template>
  <q-page class="q-pa-md">
    <div v-if="loading" class="text-center q-pa-xl">
      <q-spinner size="48px" />
    </div>
    <template v-else-if="visit">
      <div class="row items-center justify-between q-mb-md">
        <div class="row items-center">
          <q-btn flat dense icon="arrow_back" @click="$router.push({ name: 'CompanionVisitList' })" />
          <div class="text-h5 text-weight-bold glass-text q-ml-sm">Service details</div>
        </div>
        <div class="row q-gutter-sm">
          <q-btn
            v-if="canEdit"
            flat
            label="Edit"
            icon="edit"
            class="glass-button"
            @click="openEditDialog"
          />
          <q-btn
            v-if="canDelete"
            flat
            label="Delete"
            icon="delete"
            class="glass-button"
            color="negative"
            @click="confirmDelete"
          />
        </div>
      </div>
      <q-card class="glass-card" flat>
        <q-card-section>
          <div class="row q-col-gutter-md">
            <div class="col-12 col-sm-6">
              <div class="text-caption glass-text-muted">Card number</div>
              <div class="text-body1">{{ visit.external_card_number }}</div>
            </div>
            <div class="col-12 col-sm-6">
              <div class="text-caption glass-text-muted">Visit number</div>
              <div class="text-body1">{{ visit.external_visit_number }}</div>
            </div>
            <div class="col-12 col-sm-6">
              <div class="text-caption glass-text-muted">Client name</div>
              <div class="text-body1">{{ visit.client_name || '—' }}</div>
            </div>
            <div class="col-12 col-sm-6">
              <div class="text-caption glass-text-muted">Status</div>
              <div class="text-body1">{{ visit.status }}</div>
            </div>
            <div class="col-12 col-sm-6">
              <div class="text-caption glass-text-muted">Created</div>
              <div class="text-body1">{{ formatDate(visit.created_at) }}</div>
            </div>
          </div>
        </q-card-section>
      </q-card>

      <!-- Account summary: total bill vs paid amount and balance due (prominent for accounts) -->
      <div class="text-subtitle1 text-weight-medium glass-text q-mt-lg q-mb-sm">Account summary</div>
      <q-card class="glass-card account-summary-card q-mb-md" flat>
        <q-card-section class="account-summary-section">
          <p class="account-summary-hint text-caption text-grey-7">
            Tap any amount below for a receipt-style breakdown (lines, receipts, who recorded payment).
          </p>
          <div class="account-summary-grid">
            <div
              class="account-summary-cell receipt-amount-hit"
              tabindex="0"
              role="button"
              @click="openReceiptDialog('total')"
              @keyup.enter="openReceiptDialog('total')"
            >
              <div class="account-summary-label text-caption text-grey-7">Total bill</div>
              <div class="text-h6 text-weight-bold q-mt-xs">GH¢ {{ formatPrice(billTotal) }}</div>
              <q-tooltip anchor="top middle" self="bottom middle">Open bill &amp; payment viewer</q-tooltip>
            </div>
            <div
              class="account-summary-cell receipt-amount-hit"
              tabindex="0"
              role="button"
              @click="openReceiptDialog('paid')"
              @keyup.enter="openReceiptDialog('paid')"
            >
              <div class="account-summary-label text-caption text-grey-7">Paid so far</div>
              <div class="text-h6 text-positive q-mt-xs">GH¢ {{ formatPrice(paidAmount) }}</div>
              <q-tooltip anchor="top middle" self="bottom middle">Money received — receipts &amp; cashiers</q-tooltip>
            </div>
            <div
              class="account-summary-cell receipt-amount-hit"
              tabindex="0"
              role="button"
              @click="openReceiptDialog('deposit')"
              @keyup.enter="openReceiptDialog('deposit')"
            >
              <div class="account-summary-label text-caption text-grey-7">Part payment</div>
              <div class="text-h6 q-mt-xs">
                {{
                  undertakingDepositAmount != null && undertakingDepositAmount > 0
                    ? 'GH¢ ' + formatPrice(undertakingDepositAmount)
                    : '—'
                }}
              </div>
              <q-tooltip anchor="top middle" self="bottom middle">Amount paid on behalf of the client now; undertaking covers the agreement to pay the balance later</q-tooltip>
            </div>
            <div
              class="account-summary-cell account-summary-cell--balance receipt-amount-hit"
              tabindex="0"
              role="button"
              @click="openReceiptDialog('balance')"
              @keyup.enter="openReceiptDialog('balance')"
            >
              <div class="account-summary-label text-caption text-grey-7">Balance due</div>
              <div class="text-caption text-grey-7 q-mb-xs">Amount client owes</div>
              <div class="balance-due q-mt-xs" :class="balanceDue > 0 ? 'text-weight-bold text-primary' : 'text-positive'">
                GH¢ {{ formatPrice(balanceDue) }}
              </div>
              <q-tooltip anchor="top middle" self="bottom middle">Overview &amp; full bill</q-tooltip>
            </div>
          </div>
        </q-card-section>
      </q-card>

      <!-- Role-based action cards: active only for matching roles -->
      <div class="text-subtitle1 text-weight-medium glass-text q-mt-lg q-mb-sm">Add services</div>
      <div class="text-body2 glass-text-muted q-mb-sm">
        Full line-by-line bill (with receipts and payment details) is in Account summary — tap any amount above.
      </div>
      <div class="row q-col-gutter-md q-ma-md">
        <q-card
          v-for="card in actionCards"
          :key="card.name"
          class="action-card col-12 col-sm-6 col-md-3 q-ma-sm"
          :class="{ 'action-card--inactive': !card.active }"
          flat
          :clickable="card.active && visit.status === 'open'"
          @click="card.active && visit.status === 'open' ? goTo(card.routeName) : null"
        >
          <q-card-section class="text-center">
            <q-icon :name="card.icon" :size="card.active ? '40px' : '32px'" :class="card.active ? 'text-primary' : 'text-grey-5'" />
            <div class="text-subtitle1 q-mt-sm" :class="card.active ? 'glass-text' : 'text-grey-6'">{{ card.title }}</div>
            <q-btn
              v-if="card.active && visit.status === 'open'"
              flat
              dense
              size="sm"
              label="Open"
              class="glass-button q-mt-sm"
              @click.stop="goTo(card.routeName)"
            />
            <div v-else-if="!card.active" class="text-caption text-grey-6 q-mt-sm">Not available for your role</div>
            <div v-else class="text-caption text-grey-6 q-mt-sm">Visit is closed</div>
          </q-card-section>
        </q-card>
      </div>
    </template>
    <div v-else class="text-body1">Visit not found.</div>

    <CompanionBillingReceiptDialog
      v-model="receiptOpen"
      :visit="visit"
      :items="billItems"
      :loading="false"
      :focus-hint="receiptFocus"
    />

    <q-dialog v-model="showEditDialog" persistent>
      <q-card class="glass-card" style="min-width: 400px;">
        <q-card-section>
          <div class="text-h6">Edit service</div>
          <div class="text-caption glass-text-muted">Card and visit number can only be changed when the visit is open (to correct officer errors).</div>
        </q-card-section>
        <q-card-section>
          <q-form @submit="onSaveEdit" class="q-gutter-md">
            <q-input
              v-model="editForm.external_card_number"
              filled
              label="Card number (from government system)"
              :readonly="visit && visit.status === 'closed'"
              :rules="editForm.status === 'open' ? [(v) => !!((v || '').trim()) || 'Required when open'] : []"
              class="glass-text"
            />
            <q-input
              v-model="editForm.external_visit_number"
              filled
              label="Visit number (from government system)"
              :readonly="visit && visit.status === 'closed'"
              :rules="editForm.status === 'open' ? [(v) => !!((v || '').trim()) || 'Required when open'] : []"
              class="glass-text"
            />
            <q-input
              v-model="editForm.client_name"
              filled
              label="Client name (optional)"
              class="glass-text"
            />
            <q-select
              v-model="editForm.status"
              :options="statusOptions"
              filled
              label="Status"
              emit-value
              map-options
            />
            <div class="row q-gutter-sm justify-end">
              <q-btn flat label="Cancel" @click="showEditDialog = false" />
              <q-btn unelevated type="submit" label="Save" class="glass-button" :loading="saving" />
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useQuasar } from 'quasar';
import { useAuthStore } from '../../stores/auth';
import { companionVisitsAPI } from '../../services/api';
import CompanionBillingReceiptDialog from '../../components/companion/CompanionBillingReceiptDialog.vue';

const route = useRoute();
const router = useRouter();
const $q = useQuasar();
const authStore = useAuthStore();
const loading = ref(true);
const visit = ref(null);
const billItems = ref([]);
const showEditDialog = ref(false);
const saving = ref(false);
const editForm = ref({
  external_card_number: '',
  external_visit_number: '',
  client_name: '',
  status: 'open',
});
const receiptOpen = ref(false);
const receiptFocus = ref('overview');

function openReceiptDialog(hint) {
  receiptFocus.value = hint || 'overview';
  receiptOpen.value = true;
}

const statusOptions = [
  { label: 'Open', value: 'open' },
  { label: 'Closed', value: 'closed' },
];

const id = computed(() => route.params.id);

function formatPrice(val) {
  const n = Number(val);
  if (Number.isNaN(n)) return '0.00';
  return n.toFixed(2);
}

function rowAmount(row) {
  return (Number(row.unit_price) || 0) * (Number(row.quantity) || 1);
}
function isCancelledRow(row) {
  return Boolean(row.cancelled);
}
function isPaidRow(row) {
  if (rowAmount(row) === 0) return true;
  const T = rowAmount(row);
  const ln = String(row.admission_deposit_line_receipt || '').trim();
  const rn = String(row.receipt_number || '').trim();
  const rawApplied = row.admission_deposit_applied;
  const pm = (row.payment_method || '').trim();
  if (rawApplied == null && pm === 'admission_deposit') {
    return Boolean(rn);
  }
  if (rawApplied != null) {
    const rem = Math.round((T - Number(rawApplied)) * 100) / 100;
    if (rem <= 0.01) return Boolean(ln);
    return Boolean(ln && rn);
  }
  return Boolean(rn);
}

const billTotal = computed(() => {
  return (billItems.value || []).reduce((sum, i) => {
    if (isCancelledRow(i)) return sum;
    return sum + rowAmount(i);
  }, 0);
});
const undertakingDepositAmount = computed(() => {
  const v = visit.value;
  if (!v || v.undertaking_deposit_amount == null) return null;
  const n = Number(v.undertaking_deposit_amount);
  return Number.isNaN(n) ? null : n;
});
const paidAmount = computed(() => {
  return (billItems.value || []).reduce((sum, row) => {
    if (isCancelledRow(row)) return sum;
    if (!isPaidRow(row)) return sum;
    return sum + rowAmount(row);
  }, 0);
});
const balanceDue = computed(() => {
  const total = billTotal.value;
  const paid = paidAmount.value || 0;
  const deposit = undertakingDepositAmount.value || 0;
  return Math.max(0, total - paid - deposit);
});

const canEdit = computed(() => {
  if (!visit.value) return false;
  if (visit.value.status === 'closed') return authStore.canAccess(['Admin']);
  return authStore.canAccess(['Records', 'Admin', 'Billing']);
});

const canDelete = computed(() => {
  if (!visit.value) return false;
  if (visit.value.status === 'closed') return authStore.canAccess(['Admin']);
  return authStore.canAccess(['Records', 'Admin']);
});

const actionCards = computed(() => {
  const cards = [
    { name: 'investigation', title: 'Add investigation', icon: 'science', routeName: 'CompanionAddInvestigation', roles: ['Lab', 'Lab Head', 'Doctor', 'PA', 'Admin'] },
    { name: 'drugs', title: 'Add drugs', icon: 'medication', routeName: 'CompanionAddDrugs', roles: ['Pharmacy', 'Pharmacy Head', 'Doctor', 'PA', 'Admin'] },
    { name: 'scan', title: 'Add scan', icon: 'biotech', routeName: 'CompanionAddScan', roles: ['Scan', 'Scan Head', 'Doctor', 'PA', 'Admin'] },
    { name: 'xray', title: 'Add X-ray', icon: 'contrast', routeName: 'CompanionAddXray', roles: ['Xray', 'Xray Head', 'Doctor', 'PA', 'Admin'] },
    { name: 'day_surgery', title: 'Add day surgery', icon: 'medical_services', routeName: 'CompanionAddDaySurgery', roles: ['Nurse', 'Doctor', 'PA', 'Admin'] },
    { name: 'major_surgery', title: 'Add major surgery', icon: 'healing', routeName: 'CompanionAddMajorSurgery', roles: ['Nurse', 'Doctor', 'PA', 'Admin'] },
    { name: 'dressing', title: 'Dressing room', icon: 'vaccines', routeName: 'CompanionAddDressing', roles: ['Nurse', 'Doctor', 'PA', 'Admin'] },
    { name: 'oxygen', title: 'Oxygen', icon: 'air', routeName: 'CompanionAddOxygen', roles: ['Nurse', 'Doctor', 'PA', 'Admin'] },
    {
      name: 'inventory_debit',
      title: 'Inventory debit',
      icon: 'inventory_2',
      routeName: 'CompanionInventoryDebit',
      roles: ['Nurse', 'Doctor', 'PA', 'Pharmacy', 'Pharmacy Head', 'Billing', 'Admin'],
    },
  ];
  return cards.map((c) => ({ ...c, active: authStore.canAccess(c.roles) }));
});

function goTo(routeName) {
  router.push({ name: routeName, params: { id: id.value } }).catch(() => {});
}

function formatDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString();
}

function openEditDialog() {
  editForm.value = {
    external_card_number: visit.value?.external_card_number || '',
    external_visit_number: visit.value?.external_visit_number || '',
    client_name: visit.value?.client_name || '',
    status: visit.value?.status || 'open',
  };
  showEditDialog.value = true;
}

async function onSaveEdit() {
  saving.value = true;
  try {
    const payload = {
      client_name: editForm.value.client_name || undefined,
      status: editForm.value.status,
    };
    if (visit.value?.status === 'open') {
      payload.external_card_number = (editForm.value.external_card_number || '').trim() || undefined;
      payload.external_visit_number = (editForm.value.external_visit_number || '').trim() || undefined;
    }
    await companionVisitsAPI.update(id.value, payload);
    const res = await companionVisitsAPI.get(id.value);
    visit.value = res.data;
    showEditDialog.value = false;
    $q.notify({ type: 'positive', message: 'Updated', position: 'top' });
  } catch (e) {
    $q.notify({
      type: 'negative',
      message: e.response?.data?.detail || e.message || 'Update failed',
      position: 'top',
    });
  } finally {
    saving.value = false;
  }
}

function confirmDelete() {
  $q.dialog({
    title: 'Delete service',
    message: 'Remove this visit? This cannot be undone.',
    cancel: true,
    persistent: true,
  }).onOk(async () => {
    try {
      await companionVisitsAPI.delete(id.value);
      $q.notify({ type: 'positive', message: 'Deleted', position: 'top' });
      router.push({ name: 'CompanionVisitList' });
    } catch (e) {
      $q.notify({
        type: 'negative',
        message: e.response?.data?.detail || e.message || 'Delete failed',
        position: 'top',
      });
    }
  });
}

async function loadVisit() {
  if (!id.value) return;
  try {
    const res = await companionVisitsAPI.get(id.value);
    visit.value = res.data;
  } catch (e) {
    visit.value = null;
  } finally {
    loading.value = false;
  }
}

async function loadItems() {
  if (!id.value) return;
  try {
    const res = await companionVisitsAPI.getItems(id.value);
    billItems.value = res.data || [];
  } catch (e) {
    billItems.value = [];
  }
}

onMounted(async () => {
  await loadVisit();
  if (visit.value) await loadItems();
});
</script>

<style scoped>
.action-card {
  transition: opacity 0.2s, transform 0.2s;
}
.action-card:not(.action-card--inactive) {
  cursor: pointer;
}
.action-card--inactive {
  opacity: 0.6;
  pointer-events: none;
}
.action-card:not(.action-card--inactive):hover {
  transform: translateY(-2px);
}

/* Account summary: grid so columns never overlap; balance cell highlighted, not full-width */
.account-summary-card {
  border-left: 4px solid var(--q-primary);
}
.body--dark .account-summary-card {
  border-left-color: var(--q-primary);
}

.account-summary-hint {
  margin: 0 0 1rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid rgba(0, 0, 0, 0.08);
  line-height: 1.45;
  max-width: 100%;
}
.body--dark .account-summary-hint {
  border-bottom-color: rgba(255, 255, 255, 0.12);
}

.account-summary-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
  width: 100%;
}
@media (min-width: 600px) {
  .account-summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 14px;
  }
}
@media (min-width: 1024px) {
  .account-summary-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 16px;
  }
}

.account-summary-cell {
  min-width: 0;
  padding: 12px 14px;
  border-radius: 8px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  background: rgba(0, 0, 0, 0.02);
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: flex-start;
}
.body--dark .account-summary-cell {
  border-color: rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.04);
}

.account-summary-cell--balance {
  border-width: 2px;
  border-color: var(--q-primary);
  background: rgba(25, 118, 210, 0.06);
}
.body--dark .account-summary-cell--balance {
  background: rgba(100, 181, 246, 0.12);
}

.account-summary-label {
  line-height: 1.3;
  word-break: break-word;
}

.account-summary-section .balance-due {
  font-size: 1.25rem;
  line-height: 1.2;
}

/* Click targets: no negative margins inside summary (they caused overlap) */
.account-summary-section .receipt-amount-hit {
  cursor: pointer;
  outline-offset: 2px;
  transition: background 0.15s ease, box-shadow 0.15s ease;
  margin: 0;
}
.account-summary-section .receipt-amount-hit:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  background: rgba(0, 0, 0, 0.03);
}
.body--dark .account-summary-section .receipt-amount-hit:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.25);
  background: rgba(255, 255, 255, 0.06);
}
.account-summary-section .receipt-amount-hit:focus {
  outline: 2px solid var(--q-primary);
  outline-offset: 2px;
}
</style>
