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
          <div class="row q-col-gutter-lg items-center">
            <div class="col-12 col-sm-auto">
              <div class="text-caption text-grey-7">Total bill</div>
              <div class="text-h6 text-weight-bold">GH¢ {{ formatPrice(billTotal) }}</div>
            </div>
            <div class="col-12 col-sm-auto">
              <div class="text-caption text-grey-7">Paid so far</div>
              <div class="text-h6 text-positive">GH¢ {{ formatPrice(paidAmount) }}</div>
            </div>
            <div v-if="undertakingDepositAmount != null && undertakingDepositAmount > 0" class="col-12 col-sm-auto">
              <div class="text-caption text-grey-7">Deposit (undertaking)</div>
              <div class="text-body1">GH¢ {{ formatPrice(undertakingDepositAmount) }}</div>
            </div>
            <div class="col-12 col-sm">
              <div class="text-caption text-grey-7">Balance due (amount client owes)</div>
              <div class="balance-due" :class="balanceDue > 0 ? 'text-weight-bold text-primary' : 'text-positive'">
                GH¢ {{ formatPrice(balanceDue) }}
              </div>
            </div>
          </div>
        </q-card-section>
      </q-card>

      <!-- Services billed for client: grouped by category, then by date (visible to all roles when viewing service details) -->
      <div class="text-subtitle1 text-weight-medium glass-text q-mt-lg q-mb-sm">Services billed for client</div>
      <q-card class="glass-card q-mb-md" flat>
        <q-card-section v-if="loadingItems" class="text-center q-pa-md">
          <q-spinner size="32px" />
        </q-card-section>
        <q-card-section v-else-if="!groupedServicesByCategory.length" class="text-body2 glass-text-muted">
          No services added yet. Use the cards below to add lab, scan, X-ray, drugs, surgeries, dressing room, or oxygen services. When the visit is closed, you can still view all services that were billed here.
        </q-card-section>
        <q-card-section v-else class="q-pt-none">
          <q-expansion-item
            v-for="catGroup in groupedServicesByCategory"
            :key="catGroup.key"
            :label="catGroup.title"
            :caption="catGroup.caption"
            icon="folder"
            class="q-mb-sm"
            header-class="text-weight-medium"
            expand-icon-class="text-grey-7"
          >
            <q-expansion-item
              v-for="dateGroup in catGroup.dateGroups"
              :key="dateGroup.dateKey"
              :label="dateGroup.dateLabel"
              :caption="dateGroup.items.length === 1 ? '1 item' : dateGroup.items.length + ' items'"
              icon="event"
              class="q-ml-md q-mb-sm"
              dense
              expand-icon-class="text-grey-7"
            >
              <div class="receipt-block rounded-borders q-pa-sm">
                <div
                  v-for="(item, idx) in dateGroup.items"
                  :key="item.id"
                  class="receipt-line q-py-md q-px-sm"
                  :class="{ 'receipt-line--last': idx === dateGroup.items.length - 1 }"
                >
                  <div class="row items-start justify-between no-wrap receipt-line__row">
                    <div class="col receipt-line__main">
                      <div class="text-body2 text-weight-medium receipt-line__name" :style="item.cancelled ? 'text-decoration: line-through; opacity: 0.75;' : ''">
                        {{ item.item_name }}
                      </div>
                      <div class="text-caption text-grey-7 receipt-line__code">
                        <template v-if="item.category === 'oxygen' && item.start_time && item.end_time">
                          {{ formatOxygenPeriod(item) }}
                        </template>
                        <template v-else>{{ item.item_code }} · Qty {{ item.quantity }}</template>
                      </div>
                      <div v-if="item.created_by_name" class="text-caption text-grey-6 receipt-line__meta">Added by {{ item.created_by_name }}</div>
                      <div v-if="item.cancelled" class="text-caption text-negative receipt-line__meta">
                        Cancelled {{ item.cancelled_at ? formatDate(item.cancelled_at) : '' }} by {{ item.cancelled_by_name || '—' }} — {{ item.cancel_reason || '—' }}
                      </div>
                      <div v-if="item.receipt_number" class="text-caption text-positive receipt-line__meta">
                        Receipt {{ item.receipt_number }}{{ item.paid_at ? ' · Paid ' + formatDate(item.paid_at) : '' }}
                      </div>
                    </div>
                    <div class="col-auto text-right receipt-line__amount">
                      <span class="text-body2 text-weight-medium">GH¢ {{ formatPrice((item.unit_price || 0) * (item.quantity || 1)) }}</span>
                      <div class="text-caption text-grey-7">{{ item.quantity }} × GH¢ {{ formatPrice(item.unit_price) }}</div>
                    </div>
                  </div>
                </div>
              </div>
            </q-expansion-item>
          </q-expansion-item>
        </q-card-section>
      </q-card>

      <!-- Role-based action cards: active only for matching roles -->
      <div class="text-subtitle1 text-weight-medium glass-text q-mt-lg  q-mb-sm">Add services</div>
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

const route = useRoute();
const router = useRouter();
const $q = useQuasar();
const authStore = useAuthStore();
const loading = ref(true);
const visit = ref(null);
const billItems = ref([]);
const loadingItems = ref(false);
const showEditDialog = ref(false);
const saving = ref(false);
const editForm = ref({
  external_card_number: '',
  external_visit_number: '',
  client_name: '',
  status: 'open',
});

const statusOptions = [
  { label: 'Open', value: 'open' },
  { label: 'Closed', value: 'closed' },
];

const id = computed(() => route.params.id);

function normalizeCategory(cat) {
  const c = String(cat || '').trim().toLowerCase();
  if (!c) return 'other';
  if (c.includes('drug')) return 'drugs';
  if (c.includes('investigation') || c.includes('lab')) return 'investigations';
  if (c.includes('scan')) return 'scans';
  if (c.includes('xray') || c.includes('x-ray') || c.includes('x ray')) return 'xrays';
  if (c === 'day_surgery' || c === 'major_surgery') return 'surgeries';
  if (c === 'dressing' || c === 'dressing_room') return 'dressing';
  if (c === 'oxygen') return 'oxygen';
  if (c === 'inpatient') return 'inpatient';
  return c;
}

function categoryTitle(key) {
  if (key === 'drugs') return 'Drugs';
  if (key === 'investigations') return 'Investigations / Lab';
  if (key === 'scans') return 'Scans';
  if (key === 'xrays') return 'X-rays';
  if (key === 'surgeries') return 'Surgeries';
  if (key === 'dressing') return 'Dressing / Treatment room';
  if (key === 'oxygen') return 'Oxygen';
  if (key === 'inpatient') return 'Inpatient';
  if (key === 'other') return 'Other';
  return key.replace(/_/g, ' ').replace(/\b\w/g, (m) => m.toUpperCase());
}

const preferredCategoryOrder = ['drugs', 'investigations', 'scans', 'xrays', 'surgeries', 'dressing', 'oxygen', 'inpatient', 'other'];

const groupedServicesByCategory = computed(() => {
  const items = billItems.value || [];
  const byCategory = new Map();
  for (const item of items) {
    const key = normalizeCategory(item.category);
    if (!byCategory.has(key)) byCategory.set(key, []);
    byCategory.get(key).push(item);
  }
  const keys = Array.from(byCategory.keys());
  keys.sort((a, b) => {
    const ai = preferredCategoryOrder.indexOf(a);
    const bi = preferredCategoryOrder.indexOf(b);
    if (ai !== -1 || bi !== -1) return (ai === -1 ? 999 : ai) - (bi === -1 ? 999 : bi);
    return a.localeCompare(b);
  });
  const monthNames = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
  return keys.map((key) => {
    const catItems = byCategory.get(key) || [];
    const byDate = new Map();
    for (const item of catItems) {
      let dateKey = 'no-date';
      let dateObj = null;
      if (item.created_at) {
        const d = new Date(item.created_at);
        if (!Number.isNaN(d.getTime())) {
          dateKey = d.toISOString().slice(0, 10);
          dateObj = d;
        }
      }
      if (!byDate.has(dateKey)) byDate.set(dateKey, { dateKey, dateObj, items: [] });
      byDate.get(dateKey).items.push(item);
    }
    const dateGroups = Array.from(byDate.values());
    dateGroups.sort((a, b) => (b.dateObj ? b.dateObj.getTime() : 0) - (a.dateObj ? a.dateObj.getTime() : 0));
    for (const g of dateGroups) {
      if (g.dateObj) {
        const d = g.dateObj.getDate();
        const ord = d === 1 || d === 21 || d === 31 ? 'st' : d === 2 || d === 22 ? 'nd' : d === 3 || d === 23 ? 'rd' : 'th';
        g.dateLabel = `${d}${ord} ${monthNames[g.dateObj.getMonth()]}, ${g.dateObj.getFullYear()}`;
      } else {
        g.dateLabel = 'No service date';
      }
    }
    const totalItems = catItems.length;
    return {
      key,
      title: categoryTitle(key),
      caption: totalItems === 1 ? '1 item' : totalItems + ' items',
      dateGroups,
    };
  });
});

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
  return Boolean(row.receipt_number);
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
    { name: 'day_surgery', title: 'Add day surgery', icon: 'medical_services', routeName: 'CompanionAddDaySurgery', roles: ['Doctor', 'PA', 'Admin'] },
    { name: 'major_surgery', title: 'Add major surgery', icon: 'healing', routeName: 'CompanionAddMajorSurgery', roles: ['Doctor', 'PA', 'Admin'] },
    { name: 'dressing', title: 'Dressing room', icon: 'vaccines', routeName: 'CompanionAddDressing', roles: ['Nurse', 'Doctor', 'PA', 'Admin'] },
    { name: 'oxygen', title: 'Oxygen', icon: 'air', routeName: 'CompanionAddOxygen', roles: ['Nurse', 'Doctor', 'PA', 'Admin'] },
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

function formatOxygenPeriod(item) {
  if (!item?.start_time || !item?.end_time) return '';
  const start = new Date(item.start_time).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
  const end = new Date(item.end_time).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
  const qty = Number(item.quantity);
  const hours = Number.isNaN(qty) ? '' : (qty === 1 ? '1 hour' : `${qty.toFixed(1)} hours`);
  return hours ? `Start ${start} → End ${end} · ${hours}` : `Start ${start} → End ${end}`;
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
  loadingItems.value = true;
  try {
    const res = await companionVisitsAPI.getItems(id.value);
    billItems.value = res.data || [];
  } catch (e) {
    billItems.value = [];
  } finally {
    loadingItems.value = false;
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

/* Receipt-style service lines */
.receipt-block {
  background: rgba(0, 0, 0, 0.02);
  border: 1px solid rgba(0, 0, 0, 0.08);
}
.body--dark .receipt-block {
  background: rgba(255, 255, 255, 0.04);
  border-color: rgba(255, 255, 255, 0.08);
}
.receipt-line {
  border-bottom: 1px dashed rgba(0, 0, 0, 0.12);
}
.receipt-line--last {
  border-bottom: none;
}
.body--dark .receipt-line {
  border-bottom-color: rgba(255, 255, 255, 0.12);
}
.body--dark .receipt-line--last {
  border-bottom: none;
}
.receipt-line__row {
  gap: 1rem;
}
.receipt-line__name {
  line-height: 1.35;
  margin-bottom: 2px;
}
.receipt-line__code {
  margin-bottom: 2px;
}
.receipt-line__meta {
  margin-top: 4px;
}
.receipt-line__amount {
  min-width: 100px;
  white-space: nowrap;
}

/* Account summary: prominent so every account sees total vs paid and balance */
.account-summary-card {
  border-left: 4px solid var(--q-primary);
}
.account-summary-section .balance-due {
  font-size: 1.25rem;
}
.body--dark .account-summary-card {
  border-left-color: var(--q-primary);
}
</style>
