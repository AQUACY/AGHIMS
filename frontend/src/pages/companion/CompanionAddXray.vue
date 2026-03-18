<template>
  <q-page class="q-pa-md">
    <div class="row items-center q-mb-md">
      <q-btn flat dense icon="arrow_back" :to="backLink" />
      <div class="text-h5 text-weight-bold glass-text q-ml-sm">Add X-ray</div>
    </div>

    <q-card v-if="visitClosed" class="glass-card q-mb-md" flat>
      <q-card-section>
        <q-banner class="bg-warning/20 text-warning rounded-borders">
          This visit is closed. You cannot add or remove X-rays.
        </q-banner>
      </q-card-section>
    </q-card>

    <!-- Added to bill -->
    <q-card v-if="addedItems.length > 0" class="glass-card q-mb-lg" flat>
      <q-card-section>
        <div class="text-h6 glass-text q-mb-md">Added to client's bill</div>
        <q-expansion-item
          v-for="group in addedGroups"
          :key="group.key"
          expand-separator
          :label="group.label"
          :caption="group.items.length === 1 ? '1 item' : group.items.length + ' items'"
          default-opened
        >
          <q-list bordered class="rounded-borders q-mt-sm">
            <q-item v-for="item in group.items" :key="item.id" class="q-pa-md">
              <q-item-section>
                <q-item-label class="text-weight-medium" :style="item.cancelled ? 'text-decoration: line-through; opacity: 0.75;' : ''">
                  {{ item.item_name }}
                </q-item-label>
                <q-item-label caption>{{ item.item_code }} · GH¢ {{ formatPrice(item.unit_price * item.quantity) }}</q-item-label>
                <q-item-label v-if="item.created_at" caption class="text-grey-7 q-mt-xs">Service date & time: {{ formatDateTime(item.created_at) }}</q-item-label>
                <q-item-label v-if="item.cancelled" caption class="text-negative q-mt-xs">
                  Cancelled {{ formatDateTime(item.cancelled_at) }} — {{ item.cancel_reason || '—' }}
                </q-item-label>
                <div v-if="item.receipt_number" class="receipt-badge q-mt-sm">
                  <q-icon name="receipt" size="18px" class="q-mr-xs" />
                  <span class="text-weight-medium">Receipt {{ item.receipt_number }}</span>
                  <span v-if="item.paid_at" class="q-ml-sm text-caption">· Paid {{ formatDateTime(item.paid_at) }}</span>
                </div>
                <div v-else class="unpaid-badge q-mt-sm">
                  <q-icon name="pending" size="18px" class="q-mr-xs" />
                  <span>Not paid</span>
                  <span class="text-caption q-ml-sm">— will be marked at central billing</span>
                </div>
              </q-item-section>
              <q-item-section side>
                <q-btn
                  v-if="!visitClosed && !item.receipt_number && !item.cancelled"
                  flat
                  dense
                  round
                  icon="delete"
                  color="negative"
                  @click="removeItem(item)"
                >
                  <q-tooltip>Remove from bill</q-tooltip>
                </q-btn>
                <q-tooltip v-else-if="item.receipt_number" content="Paid — cannot remove">
                  <q-icon name="check_circle" color="positive" size="24px" />
                </q-tooltip>
              </q-item-section>
            </q-item>
          </q-list>
        </q-expansion-item>
      </q-card-section>
    </q-card>

    <!-- Search and add (any X-ray) -->
    <q-card class="glass-card q-mb-lg" flat>
      <q-card-section>
        <div class="text-subtitle1 text-weight-medium glass-text q-mb-md">Search and add X-ray</div>
        <div class="text-caption glass-text-muted q-mb-sm">Type to search, then select to add to this visit.</div>
        <q-input
          v-model="searchText"
          filled
          dense
          placeholder="Type X-ray name or code..."
          class="q-mb-sm"
          clearable
        />
        <q-list v-if="searchText.trim() && filteredSearchOptions.length > 0" bordered class="rounded-borders" style="max-height: 280px; overflow-y: auto;">
          <q-item
            v-for="proc in filteredSearchOptions.slice(0, 20)"
            :key="proc.id"
            clickable
            v-ripple
            @click="selectSearchResult(proc)"
          >
            <q-item-section>
              <q-item-label>{{ proc.service_name }}</q-item-label>
              <q-item-label caption>{{ proc.g_drg_code }} · GH¢ {{ formatPrice(copaymentPrice(proc)) }} copay</q-item-label>
            </q-item-section>
            <q-item-section side>
              <q-btn flat dense size="sm" label="Add" class="glass-button" @click.stop="selectSearchResult(proc)" />
            </q-item-section>
          </q-item>
        </q-list>
        <div v-else-if="searchText.trim() && !loadingProcedures" class="text-caption text-grey-7">
          No matching X-rays.
        </div>
      </q-card-section>
    </q-card>

    <!-- Regularly requested (card list – Xray Head activates these) -->
    <div class="text-subtitle1 text-weight-medium glass-text q-mb-md">Regularly requested (cards)</div>
    <div v-if="loadingProcedures || loadingActive" class="row q-col-gutter-md">
      <q-card v-for="i in 4" :key="i" class="col-12 col-sm-6 col-md-4 glass-card" flat>
        <q-card-section class="text-center">
          <q-skeleton type="text" width="80%" class="q-mx-auto" />
          <q-skeleton type="text" width="50%" class="q-mx-auto q-mt-sm" />
        </q-card-section>
      </q-card>
    </div>
    <div v-else-if="procedures.length === 0" class="text-body2 glass-text-muted">
      No X-rays in the price list for service type "X RAY".
    </div>
    <div v-else-if="activeProcedures.length === 0" class="text-body2 glass-text-muted">
      No X-rays are on the card list yet. Xray Head can activate regularly requested ones below. Use "Search and add" above to add any X-ray to the visit.
    </div>
    <div v-else class="row q-col-gutter-lg q-ma-md">
      <q-card
        v-for="proc in activeProcedures"
        :key="proc.g_drg_code"
        class="procedure-card col-12 col-sm-6 col-md-4 col-lg-3 q-ma-sm"
        :class="{ 'procedure-card--added': addedCount(proc) > 0 }"
        flat
        :clickable="!visitClosed"
        @click="!visitClosed ? addProcedure(proc) : null"
      >
        <q-card-section class="text-center q-pa-md">
          <q-icon name="contrast" size="32px" class="text-primary" />
          <div class="text-subtitle2 q-mt-sm text-weight-medium glass-text">{{ proc.service_name }}</div>
          <div class="text-caption text-grey-7">{{ proc.g_drg_code }}</div>
          <div class="text-caption q-mt-xs">Copayment: GH¢ {{ formatPrice(copaymentPrice(proc)) }}</div>
          <q-btn
            v-if="!visitClosed"
            flat
            dense
            size="sm"
            label="Add to bill"
            class="glass-button q-mt-sm"
            @click.stop="addProcedure(proc)"
          />
          <q-badge v-else-if="addedCount(proc) > 0" color="positive" :label="addedCount(proc) > 1 ? `Added (${addedCount(proc)})` : 'Added'" class="q-mt-sm" />
        </q-card-section>
      </q-card>
    </div>

    <!-- Xray Head: manage card list -->
    <q-card v-if="canManageActive" class="glass-card q-mt-xl" flat>
      <q-card-section>
        <div class="text-h6 glass-text q-mb-md">Manage card list (Xray Head)</div>
        <div class="text-caption glass-text-muted q-mb-md">X-rays on the card list appear above. Add or remove them here.</div>
        <div class="row q-col-gutter-md q-mb-md">
          <div class="col-12 col-md-6">
            <q-select
              v-model="addActiveProc"
              :options="proceduresForActiveSelect"
              option-value="g_drg_code"
              option-label="label"
              emit-value
              map-options
              filled
              dense
              label="Add X-ray to card list"
              use-input
              input-debounce="200"
              @filter="filterProceduresForActive"
              @update:model-value="onAddToCardList"
            >
              <template v-slot:no-option>
                <q-item>
                  <q-item-section class="text-grey">Type to search X RAY</q-item-section>
                </q-item>
              </template>
            </q-select>
          </div>
        </div>
        <div v-if="activeList.length > 0" class="q-gutter-sm">
          <q-chip
            v-for="item in activeList"
            :key="item.g_drg_code"
            removable
            color="primary"
            text-color="white"
            @remove="removeActive(item.g_drg_code)"
          >
            {{ getProcedureName(item.g_drg_code) || item.g_drg_code }}
          </q-chip>
        </div>
        <div v-else class="text-caption text-grey-7">No X-rays on the card list yet.</div>
      </q-card-section>
    </q-card>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import { useQuasar } from 'quasar';
import { useAuthStore } from '../../stores/auth';
import { companionVisitsAPI, priceListAPI } from '../../services/api';

const route = useRoute();
const $q = useQuasar();
const authStore = useAuthStore();
const visitId = computed(() => route.params.id);
const backLink = computed(() => ({ name: 'CompanionVisitDetail', params: { id: visitId.value } }));

const visit = ref(null);
const visitClosed = computed(() => visit.value?.status === 'closed');
const procedures = ref([]);
const addedItems = ref([]);
const activeCodes = ref([]);
const loadingProcedures = ref(true);
const loadingActive = ref(true);
const searchText = ref('');
const addActiveProc = ref(null);
const proceduresForActiveSelect = ref([]);

const canManageActive = computed(() => authStore.canAccess(['Xray', 'Xray Head', 'Doctor', 'PA', 'Admin']));

const SERVICE_TYPE = 'X RAY';

// One card per active X-ray (price list can have multiple procedure rows per g_drg_code)
const activeProcedures = computed(() => {
  const codes = activeCodes.value.map((a) => a.g_drg_code);
  return codes.map((code) => procedures.value.find((p) => p.g_drg_code === code)).filter(Boolean);
});

const activeList = computed(() => activeCodes.value.map((a) => ({ g_drg_code: a.g_drg_code })));

const filteredSearchOptions = computed(() => {
  const t = (searchText.value || '').trim().toLowerCase();
  if (!t) return [];
  return procedures.value.filter(
    (p) =>
      (p.service_name && p.service_name.toLowerCase().includes(t)) ||
      (p.g_drg_code && p.g_drg_code.toLowerCase().includes(t))
  );
});

const addedGroups = computed(() => {
  const items = addedItems.value || [];
  const map = new Map();
  for (const item of items) {
    let key = 'no-date';
    let dateObj = null;
    if (item.created_at) {
      const d = new Date(item.created_at);
      if (!Number.isNaN(d.getTime())) {
        key = d.toISOString().slice(0, 10);
        dateObj = d;
      }
    }
    if (!map.has(key)) {
      map.set(key, { key, date: dateObj, items: [] });
    }
    map.get(key).items.push(item);
  }
  const groups = Array.from(map.values());
  groups.sort((a, b) => {
    const at = a.date ? a.date.getTime() : 0;
    const bt = b.date ? b.date.getTime() : 0;
    return bt - at;
  });
  const monthNames = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
  for (const g of groups) {
    if (g.date) {
      const d = g.date.getDate();
      const ord = d === 1 || d === 21 || d === 31 ? 'st' : d === 2 || d === 22 ? 'nd' : d === 3 || d === 23 ? 'rd' : 'th';
      g.label = `${d}${ord} ${monthNames[g.date.getMonth()]}, ${g.date.getFullYear()}`;
    } else {
      g.label = 'No service date';
    }
  }
  return groups;
});

function formatPrice(val) {
  const n = Number(val);
  if (Number.isNaN(n)) return '0.00';
  return n.toFixed(2);
}

function formatDateTime(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
}

function copaymentPrice(proc) {
  const co = proc.nhia_claim_co_payment;
  if (co != null && co !== '' && !Number.isNaN(Number(co))) return Number(co);
  const nhia = proc.nhia_app;
  if (nhia != null && nhia !== '' && !Number.isNaN(Number(nhia))) return Number(nhia);
  return Number(proc.base_rate) || 0;
}

function addedCount(proc) {
  return addedItems.value.filter((i) => i.item_code === proc.g_drg_code).length;
}

function getProcedureName(gDrgCode) {
  const p = procedures.value.find((x) => x.g_drg_code === gDrgCode);
  return p ? p.service_name : null;
}

function filterProceduresForActive(val, update) {
  const alreadyActive = new Set(activeCodes.value.map((a) => a.g_drg_code));
  let list = procedures.value.filter((p) => !alreadyActive.has(p.g_drg_code));
  if (val) {
    const v = val.toLowerCase();
    list = list.filter(
      (p) =>
        (p.service_name && p.service_name.toLowerCase().includes(v)) ||
        (p.g_drg_code && p.g_drg_code.toLowerCase().includes(v))
    );
  }
  update(() => {
    proceduresForActiveSelect.value = list.map((p) => ({
      g_drg_code: p.g_drg_code,
      label: `${p.service_name} (${p.g_drg_code})`,
    }));
  });
}

async function loadVisit() {
  try {
    const res = await companionVisitsAPI.get(visitId.value);
    visit.value = res.data;
  } catch {
    visit.value = null;
  }
}

async function loadAddedItems() {
  try {
    const res = await companionVisitsAPI.getItems(visitId.value, 'xray');
    addedItems.value = res.data || [];
  } catch {
    addedItems.value = [];
  }
}

async function loadProcedures() {
  loadingProcedures.value = true;
  try {
    const res = await priceListAPI.getProceduresByServiceType(SERVICE_TYPE);
    procedures.value = res.data || [];
  } catch {
    procedures.value = [];
  } finally {
    loadingProcedures.value = false;
  }
}

async function loadActiveXrays() {
  loadingActive.value = true;
  try {
    const res = await companionVisitsAPI.getActiveXrays();
    activeCodes.value = res.data || [];
  } catch {
    activeCodes.value = [];
  } finally {
    loadingActive.value = false;
  }
}

async function addProcedure(proc) {
  if (visitClosed.value) return;
  try {
    await companionVisitsAPI.addItem(visitId.value, {
      item_code: proc.g_drg_code,
      item_name: proc.service_name,
      category: 'xray',
      unit_price: copaymentPrice(proc),
      quantity: 1,
    });
    $q.notify({ type: 'positive', message: 'Added to bill', position: 'top' });
    await loadAddedItems();
  } catch (e) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Failed to add', position: 'top' });
  }
}

function selectSearchResult(proc) {
  addProcedure(proc);
  searchText.value = '';
}

async function removeItem(item) {
  if (visitClosed.value) return;
  $q.dialog({
    title: 'Cancel service',
    message: `Cancel "${item.item_name}"? It will be struck through and excluded from billing.`,
    prompt: {
      model: '',
      type: 'text',
      label: 'Reason for cancellation',
      isValid: (val) => String(val || '').trim().length >= 3,
    },
    cancel: true,
    persistent: true,
  }).onOk(async (reason) => {
    try {
      await companionVisitsAPI.cancelItem(visitId.value, item.id, String(reason || '').trim());
      $q.notify({ type: 'positive', message: 'Item cancelled', position: 'top' });
      await loadAddedItems();
    } catch (e) {
      $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Failed to cancel', position: 'top' });
    }
  });
}

async function onAddToCardList(gDrgCode) {
  const code = Array.isArray(gDrgCode) ? gDrgCode[0] : gDrgCode;
  if (!code) return;
  try {
    await companionVisitsAPI.addActiveXray({ g_drg_code: String(code) });
    $q.notify({ type: 'positive', message: 'Added to card list', position: 'top' });
    addActiveProc.value = null;
    await loadActiveXrays();
  } catch (e) {
    const detail = e.response?.data?.detail;
    const message = typeof detail === 'string' ? detail : Array.isArray(detail) ? detail.map((d) => d.msg || JSON.stringify(d)).join(', ') : 'Failed to add to card list';
    $q.notify({ type: 'negative', message, position: 'top' });
  }
}

async function removeActive(gDrgCode) {
  try {
    await companionVisitsAPI.removeActiveXray(gDrgCode);
    $q.notify({ type: 'positive', message: 'Removed from card list', position: 'top' });
    await loadActiveXrays();
  } catch (e) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Failed to remove', position: 'top' });
  }
}

onMounted(async () => {
  await loadVisit();
  await loadAddedItems();
  await loadProcedures();
  await loadActiveXrays();
});
</script>

<style scoped>
.procedure-card {
  transition: opacity 0.2s, transform 0.2s;
}
.procedure-card:not(.procedure-card--added) {
  cursor: pointer;
}
.procedure-card--added {
  opacity: 0.85;
  border: 1px solid rgba(46, 139, 87, 0.4);
}
.procedure-card:not(.procedure-card--added):hover {
  transform: translateY(-2px);
}

.receipt-badge {
  display: inline-flex;
  align-items: center;
  padding: 6px 12px;
  border-radius: 8px;
  background: rgba(46, 139, 87, 0.2);
  border: 1px solid rgba(46, 139, 87, 0.5);
  color: var(--q-primary);
}
.body--dark .receipt-badge {
  background: rgba(46, 139, 87, 0.15);
  border-color: rgba(46, 139, 87, 0.4);
}

.unpaid-badge {
  display: inline-flex;
  align-items: center;
  padding: 6px 12px;
  border-radius: 8px;
  background: rgba(255, 152, 0, 0.15);
  border: 1px solid rgba(255, 152, 0, 0.5);
  color: #e65100;
}
.body--dark .unpaid-badge {
  background: rgba(255, 152, 0, 0.1);
  border-color: rgba(255, 152, 0, 0.4);
  color: #ffb74d;
}
</style>
