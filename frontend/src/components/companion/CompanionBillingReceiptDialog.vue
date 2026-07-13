<template>
  <q-dialog
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
    maximized
    transition-show="slide-up"
    transition-hide="slide-down"
  >
    <q-card class="receipt-dialog-card" style="max-width: 900px; width: 100%; margin: auto">
      <q-toolbar class="bg-primary text-white">
        <q-toolbar-title class="text-weight-medium">{{ titleText }}</q-toolbar-title>
        <q-btn flat round dense icon="close" aria-label="Close" @click="close" />
      </q-toolbar>

      <q-card-section v-if="visit" class="q-pb-none">
        <div class="text-caption text-grey-7">Client / visit</div>
        <div class="text-body1 text-weight-medium">
          {{ visit.client_name || '—' }}
          <span class="text-grey-7"> · Card {{ visit.external_card_number }} · Visit {{ visit.external_visit_number }}</span>
        </div>
        <div class="text-caption text-grey-7 q-mt-xs">
          Use the tabs below to verify totals, each paid line (receipt + who collected), part payments toward an undertaking, and the undertaking record.
        </div>
      </q-card-section>

      <q-card-section class="q-pt-sm relative-position">
        <q-inner-loading :showing="loading" label="Loading bill lines…" />

        <template v-if="!loading && visit">
          <q-tabs
            v-model="tab"
            dense
            class="text-grey-8"
            active-color="primary"
            indicator-color="primary"
            align="left"
            narrow-indicator
          >
            <q-tab name="overview" icon="summarize" label="Overview" />
            <q-tab name="lines" icon="receipt_long" label="Full bill" />
            <q-tab name="payments" icon="payments" label="Money received" />
            <q-tab name="undertaking" icon="handshake" label="Part payment &amp; undertaking" />
          </q-tabs>

          <q-separator />

          <q-tab-panels v-model="tab" animated class="receipt-panels">
            <q-tab-panel name="overview" class="q-px-none">
              <div class="row q-col-gutter-md q-mt-sm">
                <div class="col-12 col-sm-6 col-md-3">
                  <q-card flat bordered class="overview-tile">
                    <q-card-section class="q-py-md">
                      <div class="text-caption text-grey-7">Total bill</div>
                      <div class="text-h6 text-weight-bold">GH¢ {{ formatPrice(billTotal) }}</div>
                    </q-card-section>
                  </q-card>
                </div>
                <div class="col-12 col-sm-6 col-md-3">
                  <q-card flat bordered class="overview-tile">
                    <q-card-section class="q-py-md">
                      <div class="text-caption text-grey-7">Paid so far</div>
                      <div class="text-h6 text-positive">GH¢ {{ formatPrice(paidAmount) }}</div>
                    </q-card-section>
                  </q-card>
                </div>
                <div class="col-12 col-sm-6 col-md-3">
                  <q-card flat bordered class="overview-tile">
                    <q-card-section class="q-py-md">
                      <div class="text-caption text-grey-7">Part payment</div>
                      <div class="text-h6">GH¢ {{ formatPrice(depositAmount) }}</div>
                    </q-card-section>
                  </q-card>
                </div>
                <div class="col-12 col-sm-6 col-md-3">
                  <q-card flat bordered class="overview-tile overview-tile--balance">
                    <q-card-section class="q-py-md">
                      <div class="text-caption text-grey-7">Balance due</div>
                      <div class="text-h6 text-weight-bold text-primary">GH¢ {{ formatPrice(balanceDue) }}</div>
                    </q-card-section>
                  </q-card>
                </div>
              </div>
              <q-banner rounded class="bg-blue-1 text-dark q-mt-md" dense>
                <template v-slot:avatar>
                  <q-icon name="info" color="primary" />
                </template>
                <strong>Check:</strong> Compare “Money received” with physical receipts. Each paid line shows the receipt number and the officer who recorded payment.
              </q-banner>
            </q-tab-panel>

            <q-tab-panel name="lines" class="q-px-none">
              <div v-if="!activeLines.length" class="text-body2 text-grey-7 q-py-md">No bill lines (or all cancelled).</div>
              <div v-else class="receipt-paper q-pa-md rounded-borders q-mt-sm">
                <div class="text-center text-caption text-grey-7 q-mb-md">— Service lines —</div>
                <div
                  v-for="(row, idx) in activeLines"
                  :key="row.id"
                  class="receipt-row q-py-sm"
                  :class="{ 'receipt-row--cancelled': row.cancelled }"
                >
                  <div class="row items-start justify-between">
                    <div class="col">
                      <div class="text-body2" :class="{ 'text-strike text-grey-6': row.cancelled }">{{ row.item_name }}</div>
                      <div class="text-caption text-grey-7">{{ row.item_code }} · Qty {{ row.quantity }}</div>
                      <div v-if="row.cancelled" class="text-caption text-negative">Cancelled</div>
                      <div v-else-if="isPaidRow(row)" class="text-caption text-positive q-mt-xs">
                        Paid · Receipt <strong>{{ row.receipt_number || '—' }}</strong>
                        <span v-if="row.paid_by_name"> · Recorded by <strong>{{ row.paid_by_name }}</strong></span>
                        <span v-if="row.paid_at"> · {{ formatDate(row.paid_at) }}</span>
                        <span v-if="row.payment_method"> · {{ row.payment_method }}</span>
                      </div>
                      <div v-else class="text-caption text-warning q-mt-xs">Not paid</div>
                    </div>
                    <div class="col-auto text-right text-body2 text-weight-medium">
                      GH¢ {{ formatPrice(rowAmount(row)) }}
                    </div>
                  </div>
                  <q-separator v-if="idx < activeLines.length - 1" class="q-mt-sm" />
                </div>
                <q-separator class="q-my-md" />
                <div class="row justify-between text-body1 text-weight-bold">
                  <span>Total (excl. cancelled)</span>
                  <span>GH¢ {{ formatPrice(billTotal) }}</span>
                </div>
              </div>
            </q-tab-panel>

            <q-tab-panel name="payments" class="q-px-none">
              <div v-if="!paidLines.length" class="text-body2 text-grey-7 q-py-md">
                No payments recorded yet (no receipt numbers on lines). Free/zero lines count as paid but show here only if marked paid.
              </div>
              <q-table
                v-else
                flat
                dense
                :rows="paidLines"
                :columns="paymentColumns"
                row-key="id"
                class="q-mt-sm"
                hide-pagination
                :rows-per-page-options="[0]"
              >
                <template v-slot:body-cell-paid_by_name="props">
                  <q-td :props="props">{{ props.row.paid_by_name || '—' }}</q-td>
                </template>
                <template v-slot:body-cell-paid_at="props">
                  <q-td :props="props">{{ props.row.paid_at ? formatDate(props.row.paid_at) : '—' }}</q-td>
                </template>
                <template v-slot:body-cell-payment_method="props">
                  <q-td :props="props">{{ props.row.payment_method || '—' }}</q-td>
                </template>
                <template v-slot:body-cell-amount="props">
                  <q-td :props="props" class="text-right">GH¢ {{ formatPrice(rowAmount(props.row)) }}</q-td>
                </template>
              </q-table>
            </q-tab-panel>

            <q-tab-panel name="undertaking" class="q-px-none">
              <div v-if="!hasUndertakingInfo" class="text-body2 text-grey-7 q-py-md">No undertaking or part payment on file for this visit.</div>
              <q-list v-else bordered separator class="rounded-borders q-mt-sm">
                <q-item v-if="visit.undertaking_status">
                  <q-item-section>
                    <q-item-label caption>Status</q-item-label>
                    <q-item-label class="text-body1">{{ visit.undertaking_status }}</q-item-label>
                  </q-item-section>
                </q-item>
                <q-item v-if="visit.undertaking_deposit_amount != null && visit.undertaking_deposit_amount > 0">
                  <q-item-section>
                    <q-item-label caption>Part payment amount</q-item-label>
                    <q-item-label class="text-body1">GH¢ {{ formatPrice(visit.undertaking_deposit_amount) }}</q-item-label>
                  </q-item-section>
                </q-item>
                <q-item v-if="visit.undertaking_deposit_receipt_number">
                  <q-item-section>
                    <q-item-label caption>Part payment receipt number</q-item-label>
                    <q-item-label class="text-body1">{{ visit.undertaking_deposit_receipt_number }}</q-item-label>
                  </q-item-section>
                </q-item>
                <q-item v-if="visit.undertaking_requested_by_name">
                  <q-item-section>
                    <q-item-label caption>Requested by</q-item-label>
                    <q-item-label class="text-body1">{{ visit.undertaking_requested_by_name }}</q-item-label>
                    <q-item-label v-if="visit.undertaking_requested_at" caption>{{ formatDate(visit.undertaking_requested_at) }}</q-item-label>
                  </q-item-section>
                </q-item>
                <q-item v-if="visit.undertaking_approved_by_name">
                  <q-item-section>
                    <q-item-label caption>Approved by</q-item-label>
                    <q-item-label class="text-body1">{{ visit.undertaking_approved_by_name }}</q-item-label>
                    <q-item-label v-if="visit.undertaking_approved_at" caption>{{ formatDate(visit.undertaking_approved_at) }}</q-item-label>
                  </q-item-section>
                </q-item>
              </q-list>
            </q-tab-panel>
          </q-tab-panels>
        </template>
      </q-card-section>

      <q-card-actions align="right" class="q-pa-md receipt-footer">
        <q-btn flat icon="print" label="Print" color="primary" @click="printReceipt" />
        <q-btn flat label="Close" color="primary" @click="close" />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue';

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  visit: { type: Object, default: null },
  items: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  title: { type: String, default: 'Bill & payment receipt' },
  /** Hint which section user clicked: total | paid | deposit | balance */
  focusHint: { type: String, default: 'overview' },
});

const emit = defineEmits(['update:modelValue']);

const tab = ref('overview');

function close() {
  emit('update:modelValue', false);
}

function printReceipt() {
  window.print();
}

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      const h = (props.focusHint || 'overview').toLowerCase();
      if (h === 'paid') tab.value = 'payments';
      else if (h === 'deposit') tab.value = 'undertaking';
      else if (h === 'balance' || h === 'total') tab.value = 'overview';
      else tab.value = 'overview';
    }
  },
);

function formatPrice(val) {
  const n = Number(val);
  if (Number.isNaN(n)) return '0.00';
  return n.toFixed(2);
}

function formatDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString();
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

const activeLines = computed(() => props.items || []);
const titleText = computed(() => String(props.title || 'Bill & payment receipt'));

const billTotal = computed(() =>
  activeLines.value.reduce((sum, i) => (isCancelledRow(i) ? sum : sum + rowAmount(i)), 0),
);

const depositAmount = computed(() => {
  const v = props.visit;
  if (!v || v.undertaking_deposit_amount == null) return 0;
  const n = Number(v.undertaking_deposit_amount);
  return Number.isNaN(n) ? 0 : n;
});

const paidAmount = computed(() =>
  activeLines.value.reduce((sum, row) => {
    if (isCancelledRow(row)) return sum;
    if (!isPaidRow(row)) return sum;
    return sum + rowAmount(row);
  }, 0),
);

const balanceDue = computed(() => {
  const total = billTotal.value;
  const paid = paidAmount.value || 0;
  const deposit = depositAmount.value || 0;
  return Math.max(0, total - paid - deposit);
});

const paidLines = computed(() => (props.items || []).filter((row) => !isCancelledRow(row) && isPaidRow(row)));

const hasUndertakingInfo = computed(() => {
  const v = props.visit;
  if (!v) return false;
  return Boolean(
    v.undertaking_status ||
      (v.undertaking_deposit_amount != null && v.undertaking_deposit_amount > 0) ||
      v.undertaking_deposit_receipt_number ||
      v.undertaking_requested_by_name ||
      v.undertaking_approved_by_name,
  );
});

const paymentColumns = [
  { name: 'item_name', label: 'Service', field: 'item_name', align: 'left' },
  { name: 'receipt_number', label: 'Receipt #', field: 'receipt_number', align: 'left' },
  { name: 'paid_by_name', label: 'Recorded by (cashier)', field: 'paid_by_name', align: 'left' },
  { name: 'paid_at', label: 'When', field: 'paid_at', align: 'left' },
  { name: 'payment_method', label: 'Method', field: 'payment_method', align: 'left' },
  {
    name: 'amount',
    label: 'Amount',
    field: (row) => (Number(row.unit_price) || 0) * (Number(row.quantity) || 1),
    align: 'right',
  },
];
</script>

<style scoped>
.receipt-dialog-card {
  max-height: 100vh;
  display: flex;
  flex-direction: column;
}
.receipt-panels {
  min-height: 220px;
}
.receipt-paper {
  background: rgba(0, 0, 0, 0.03);
  border: 1px dashed rgba(0, 0, 0, 0.15);
}
.body--dark .receipt-paper {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(255, 255, 255, 0.12);
}
.receipt-row--cancelled {
  opacity: 0.75;
}
.overview-tile--balance {
  border-left: 3px solid var(--q-primary);
}
.receipt-footer {
  border-top: 1px solid rgba(0, 0, 0, 0.08);
}
.body--dark .receipt-footer {
  border-top-color: rgba(255, 255, 255, 0.12);
}
</style>
