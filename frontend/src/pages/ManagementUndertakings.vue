<template>
  <q-page class="q-pa-md">
    <div class="text-h4 q-mb-md text-weight-bold glass-text">
      Undertakings
    </div>
    <div class="text-subtitle1 text-secondary q-mb-lg">
      Manage undertakings for Companion (copayment) visits: client total debt, part payment, remaining balance, and approver details.
      Billing can record undertakings; only Management/Admin can approve or reject.
    </div>

    <q-card class="q-mb-md glass-card" flat>
      <q-card-section>
        <div class="row items-center justify-between">
          <div class="text-h6 glass-text">Undertakings</div>
          <div class="row q-gutter-sm">
            <q-btn
              v-if="canCreateUndertaking"
              unelevated
              label="Add undertaking"
              class="glass-button"
              icon="add"
              @click="openAddDialog"
            />
            <q-btn
              outline
              color="primary"
              icon="picture_as_pdf"
              label="Debtors PDF"
              :disable="!debtorRows.length"
              :loading="exportingDebtorsPdf"
              @click="exportDebtorsPdf"
            />
            <q-btn
              unelevated
              label="Refresh"
              class="glass-button"
              icon="refresh"
              :loading="loading"
              @click="loadAll"
            />
          </div>
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
          <q-tab v-if="canApproveUndertaking" name="approved" icon="check_circle" label="My approvals" />
          <q-tab v-if="canApproveUndertaking" name="rejected" icon="cancel" label="My rejections" />
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
          <template v-slot:body-cell-bill_total="props">
            <q-td :props="props">{{ formatPrice(props.row.bill_total) }}</q-td>
          </template>
          <template v-slot:body-cell-balance_due="props">
            <q-td :props="props">{{ formatPrice(props.row.balance_due) }}</q-td>
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
                v-if="canApproveUndertaking && tab === 'approved'"
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
                v-if="canApproveUndertaking && tab === 'rejected'"
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
                v-if="canApproveUndertaking && tab === 'pending'"
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
                v-if="canApproveUndertaking && tab === 'pending'"
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
              Remaining after part payment:
              <q-btn
                flat
                dense
                no-caps
                color="primary"
                class="q-pa-none"
                style="min-height: auto;"
                @click="showRemainingBreakdown = true"
              >
                <strong>GH¢ {{ formatPrice(remainingToPay) }}</strong>
              </q-btn>
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

    <q-dialog v-model="showRemainingBreakdown">
      <q-card style="min-width: 380px; max-width: 520px;">
        <q-card-section class="row items-center justify-between">
          <div class="text-h6">Remaining Breakdown</div>
          <q-btn flat round dense icon="close" v-close-popup />
        </q-card-section>
        <q-card-section>
          <div class="text-body2 q-mb-xs">Remaining after part payment: <strong>GH¢ {{ formatPrice(remainingToPay) }}</strong></div>
          <div class="text-body2 q-mb-xs">
            Drug remaining:
            <q-btn
              flat
              dense
              no-caps
              color="primary"
              class="q-pa-none"
              style="min-height: auto;"
              @click="openRemainingItemsDialog('drug')"
            >
              <strong>GH¢ {{ formatPrice(remainingDrugAmount) }}</strong>
            </q-btn>
          </div>
          <div class="text-body2">
            Service remaining:
            <q-btn
              flat
              dense
              no-caps
              color="primary"
              class="q-pa-none"
              style="min-height: auto;"
              @click="openRemainingItemsDialog('service')"
            >
              <strong>GH¢ {{ formatPrice(remainingServiceAmount) }}</strong>
            </q-btn>
          </div>
          <div class="text-caption text-grey-7 q-mt-sm">
            Click an amount to see the individual unpaid items making it up.
          </div>
          <div class="text-caption text-grey-7 q-mt-xs">
            Part payment allocation rule: service first, then drug.
          </div>
        </q-card-section>
      </q-card>
    </q-dialog>

    <q-dialog v-model="showRemainingItemsDialog">
      <q-card style="min-width: 760px; max-width: 960px; width: 100%;">
        <q-card-section class="row items-center justify-between">
          <div class="text-h6">
            {{ remainingItemsType === 'drug' ? 'Drug' : 'Service' }} Remaining Items
          </div>
          <q-btn flat round dense icon="close" v-close-popup />
        </q-card-section>
        <q-card-section>
          <div class="text-body2 q-mb-sm">
            Total {{ remainingItemsType === 'drug' ? 'drug' : 'service' }} remaining:
            <strong>
              GH¢ {{
                formatPrice(remainingItemsType === 'drug' ? remainingDrugAmount : remainingServiceAmount)
              }}
            </strong>
          </div>
          <q-table
            :rows="remainingItemsRows"
            :columns="remainingItemsColumns"
            row-key="id"
            flat
            dense
            :rows-per-page-options="[10, 25, 50]"
          >
            <template v-slot:body-cell-unit_price="props">
              <q-td :props="props">GH¢ {{ formatPrice(props.row.unit_price) }}</q-td>
            </template>
            <template v-slot:body-cell-row_total="props">
              <q-td :props="props">GH¢ {{ formatPrice(props.row.row_total) }}</q-td>
            </template>
            <template v-slot:body-cell-remaining_amount="props">
              <q-td :props="props">
                <span>GH¢ {{ formatPrice(props.row.remaining_amount) }}</span>
                <q-icon name="info" size="xs" color="grey-7" class="q-ml-xs cursor-pointer">
                  <q-tooltip anchor="top middle" self="bottom middle" class="text-body2">
                    <div>Line total: GH¢ {{ formatPrice(props.row.row_total) }}</div>
                    <div>Deposit applied: GH¢ {{ formatPrice(props.row.deposit_applied) }}</div>
                    <div>Cash paid: GH¢ {{ formatPrice(props.row.cash_paid) }}</div>
                    <div>Outstanding on line: GH¢ {{ formatPrice(props.row.outstanding_on_line) }}</div>
                  </q-tooltip>
                </q-icon>
              </q-td>
            </template>
          </q-table>
        </q-card-section>
      </q-card>
    </q-dialog>

    <q-dialog v-model="showAddDialog" persistent>
      <q-card style="min-width: 720px; max-width: 900px; width: 100%;">
        <q-card-section class="row items-center justify-between">
          <div class="text-h6">Add Undertaking</div>
          <q-btn flat round dense icon="close" v-close-popup />
        </q-card-section>
        <q-card-section>
          <q-tabs
            v-model="addMode"
            dense
            active-color="primary"
            indicator-color="primary"
            align="left"
            class="q-mb-md"
          >
            <q-tab name="existing" icon="search" label="Existing visit" />
            <q-tab name="manual" icon="edit_note" label="Manual entry" />
          </q-tabs>

          <template v-if="addMode === 'existing'">
          <div class="row q-col-gutter-sm q-mb-sm">
            <q-input v-model="addSearch" filled dense label="Search by card, visit, or client name" class="col-12" clearable />
          </div>
          <q-table
            :rows="eligibleRowsFiltered"
            :columns="eligibleColumns"
            row-key="id"
            dense
            flat
            :rows-per-page-options="[5, 10, 20]"
            :pagination="{ rowsPerPage: 5 }"
          >
            <template v-slot:body-cell-balance_due="props">
              <q-td :props="props">GH¢ {{ formatPrice(props.row.balance_due) }}</q-td>
            </template>
            <template v-slot:body-cell-actions="props">
              <q-td :props="props">
                <q-btn
                  dense
                  flat
                  color="primary"
                  icon="check"
                  label="Select"
                  @click="selectVisitForUndertaking(props.row)"
                />
              </q-td>
            </template>
          </q-table>

          <q-separator class="q-my-md" />

          <div class="text-subtitle2 q-mb-sm">Selected visit</div>
          <div class="text-body2 q-mb-sm">
            <span v-if="selectedVisitForUndertaking">
              {{ selectedVisitForUndertaking.client_name || '—' }} (Card {{ selectedVisitForUndertaking.external_card_number }}, Visit {{ selectedVisitForUndertaking.external_visit_number }})
              - Total owed: <strong>GH¢ {{ formatPrice(selectedVisitForUndertaking.balance_due) }}</strong>
            </span>
            <span v-else>Select a visit above.</span>
          </div>

          <div class="row q-col-gutter-sm">
            <q-input
              v-model.number="newUndertaking.partPayment"
              type="number"
              filled
              dense
              min="0"
              step="0.01"
              label="Amount paid (part payment)"
              class="col-12 col-md-6"
            />
            <q-input
              v-model="newUndertaking.receiptNumber"
              filled
              dense
              label="Part payment receipt number (optional)"
              class="col-12 col-md-6"
            />
          </div>
          <div class="text-caption text-grey-7 q-mt-xs">
            Remaining amount will be computed automatically from total owed minus part payment.
          </div>
          </template>

          <template v-else>
            <div class="row q-col-gutter-sm">
              <q-input
                v-model="manualUndertaking.cardNumber"
                filled
                dense
                label="Card number"
                class="col-12 col-md-4"
              />
              <q-input
                v-model="manualUndertaking.clientName"
                filled
                dense
                label="Client name"
                class="col-12 col-md-4"
              />
              <q-input
                v-model.number="manualUndertaking.drugOwed"
                type="number"
                filled
                dense
                min="0"
                step="0.01"
                label="Drug amount owed"
                class="col-12 col-md-4"
              />
            </div>
            <div class="row q-col-gutter-sm q-mt-xs">
              <q-input
                v-model.number="manualUndertaking.serviceOwed"
                type="number"
                filled
                dense
                min="0"
                step="0.01"
                label="Service amount owed"
                class="col-12 col-md-4"
              />
              <q-input
                :model-value="formatPrice(manualManualTotalOwed)"
                filled
                dense
                label="Total owed (Drug + Service)"
                readonly
                class="col-12 col-md-4"
              />
            </div>
            <div class="row q-col-gutter-sm q-mt-xs">
              <q-input
                v-model.number="manualUndertaking.partPayment"
                type="number"
                filled
                dense
                min="0"
                step="0.01"
                label="Amount paid (part payment)"
                class="col-12 col-md-6"
              />
              <q-input
                v-model="manualUndertaking.receiptNumber"
                filled
                dense
                label="Part payment receipt number (optional)"
                class="col-12 col-md-6"
              />
            </div>
            <div class="text-caption text-grey-7 q-mt-sm">
              Visit number is auto-generated when manual undertaking is saved.
            </div>
            <div class="text-caption text-grey-7">
              Manual debt is saved as separate line items for drug and service.
            </div>
          </template>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Cancel" v-close-popup />
          <q-btn
            color="primary"
            unelevated
            label="Save undertaking"
            :loading="creatingUndertaking"
            :disable="addMode === 'existing' ? !selectedVisitForUndertaking : false"
            @click="addMode === 'existing' ? createUndertaking() : createManualUndertaking()"
          />
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
import { useFacilityStore } from '../stores/facility';

const LOGO_MOH = '/logos/ministry-of-health-logo.png';
const LOGO_GHS = '/logos/ghana-health-service-logo.png';

const $q = useQuasar();
const authStore = useAuthStore();
const facilityStore = useFacilityStore();

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
const showRemainingBreakdown = ref(false);
const showRemainingItemsDialog = ref(false);
const remainingItemsType = ref('drug');
const reversingId = ref(null);
const deletingId = ref(null);
const revertingRejectId = ref(null);
const exportingDebtorsPdf = ref(false);

const allCompanionVisits = ref([]);
const showAddDialog = ref(false);
const addSearch = ref('');
const addMode = ref('existing');
const selectedVisitForUndertaking = ref(null);
const creatingUndertaking = ref(false);
const newUndertaking = ref({
  partPayment: 0,
  receiptNumber: '',
});
const manualUndertaking = ref({
  cardNumber: '',
  clientName: '',
  drugOwed: 0,
  serviceOwed: 0,
  partPayment: 0,
  receiptNumber: '',
});
const manualManualTotalOwed = computed(() =>
  Math.max(0, Number(manualUndertaking.value.drugOwed || 0)) +
  Math.max(0, Number(manualUndertaking.value.serviceOwed || 0))
);

async function fetchLogoDataUrl(url) {
  try {
    const res = await fetch(url);
    if (!res.ok) return null;
    const blob = await res.blob();
    return await new Promise((resolve, reject) => {
      const fr = new FileReader();
      fr.onload = () => resolve(fr.result);
      fr.onerror = reject;
      fr.readAsDataURL(blob);
    });
  } catch {
    return null;
  }
}

function naturalSizeFromDataUrl(dataUrl) {
  return new Promise((resolve) => {
    if (!dataUrl) {
      resolve(null);
      return;
    }
    const img = new Image();
    img.onload = () => resolve({ w: img.naturalWidth, h: img.naturalHeight });
    img.onerror = () => resolve(null);
    img.src = dataUrl;
  });
}

const columns = [
  { name: 'id', label: 'ID', field: 'id', align: 'left', sortable: true },
  { name: 'external_card_number', label: 'Card', field: 'external_card_number', align: 'left' },
  { name: 'external_visit_number', label: 'Visit #', field: 'external_visit_number', align: 'left' },
  { name: 'client_name', label: 'Client', field: 'client_name', align: 'left' },
  { name: 'undertaking_requested_at', label: 'Requested at', field: 'undertaking_requested_at', align: 'left' },
  { name: 'undertaking_requested_by_name', label: 'Requested by', field: 'undertaking_requested_by_name', align: 'left' },
  { name: 'bill_total', label: 'Total owed', field: 'bill_total', align: 'right' },
  { name: 'undertaking_deposit_amount', label: 'Part payment', field: 'undertaking_deposit_amount', align: 'right' },
  { name: 'balance_due', label: 'Remaining', field: 'balance_due', align: 'right' },
  { name: 'undertaking_approved_by_name', label: 'Approved by', field: 'undertaking_approved_by_name', align: 'left' },
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
const canApproveUndertaking = computed(() => authStore.canAccess(['Management', 'Admin']));
const canCreateUndertaking = computed(() => authStore.canAccess(['Billing', 'Management', 'Admin']));

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

const paidItems = computed(() => (billingItems.value || []).filter((i) => itemOutstandingAmount(i) <= 0.005));
const pendingItems = computed(() => (billingItems.value || []).filter((i) => itemOutstandingAmount(i) > 0.005));

const itemsTotal = computed(() =>
  (billingItems.value || []).reduce((sum, r) => sum + (isCancelledItem(r) ? 0 : rowAmount(r)), 0)
);
const paidTotal = computed(() =>
  (billingItems.value || []).reduce((sum, r) => sum + (isCancelledItem(r) ? 0 : (rowAmount(r) - itemOutstandingAmount(r))), 0)
);
const depositAmount = computed(() => Number(billingVisit.value?.undertaking_deposit_amount || 0) || 0);
const remainingToPay = computed(() => Math.max(0, itemsTotal.value - paidTotal.value - depositAmount.value));
const pendingDrugRaw = computed(() =>
  pendingItems.value.reduce((sum, item) => {
    const cat = String(item.category || '').toLowerCase();
    return cat === 'drug' ? sum + itemOutstandingAmount(item) : sum;
  }, 0)
);
const pendingServiceRaw = computed(() =>
  pendingItems.value.reduce((sum, item) => {
    const cat = String(item.category || '').toLowerCase();
    return cat === 'drug' ? sum : sum + itemOutstandingAmount(item);
  }, 0)
);
const undertakingPartPayment = computed(() => Math.max(0, Number(depositAmount.value || 0)));
const serviceReductionFromPartPayment = computed(() =>
  Math.min(undertakingPartPayment.value, pendingServiceRaw.value)
);
const partPaymentLeftAfterService = computed(() =>
  Math.max(0, undertakingPartPayment.value - serviceReductionFromPartPayment.value)
);
const remainingDrugAmount = computed(() => {
  return Math.max(0, pendingDrugRaw.value - partPaymentLeftAfterService.value);
});
const remainingServiceAmount = computed(() =>
  Math.max(0, pendingServiceRaw.value - serviceReductionFromPartPayment.value)
);
const remainingItemsColumns = [
  { name: 'item_name', label: 'Item', field: 'item_name', align: 'left' },
  { name: 'category', label: 'Category', field: 'category', align: 'left' },
  { name: 'quantity', label: 'Qty', field: 'quantity', align: 'right' },
  { name: 'unit_price', label: 'Unit price', field: 'unit_price', align: 'right' },
  { name: 'row_total', label: 'Line total', field: 'row_total', align: 'right' },
  { name: 'remaining_amount', label: 'Remaining contribution', field: 'remaining_amount', align: 'right' },
];
const remainingItemsRows = computed(() => {
  const type = remainingItemsType.value;
  const sourceItems = pendingItems.value.filter((item) => {
    const cat = String(item.category || '').toLowerCase();
    if (type === 'drug') return cat === 'drug';
    return cat !== 'drug';
  });
  const rawTotal = sourceItems.reduce((sum, item) => sum + itemOutstandingAmount(item), 0);
  const targetTotal = type === 'drug' ? remainingDrugAmount.value : remainingServiceAmount.value;
  if (rawTotal <= 0) return [];
  return sourceItems.map((item, idx) => {
    const lineTotal = rowAmount(item);
    const lineOutstanding = itemOutstandingAmount(item);
    const depositApplied = itemDepositAppliedAmount(item);
    const cashPaid = itemCashPaidAmount(item);
    const proportionalRemaining = (lineOutstanding / rawTotal) * targetTotal;
    return {
      id: `${item.id || idx}-${type}`,
      item_name: item.item_name || '—',
      category: item.category || '—',
      quantity: Number(item.quantity || 0),
      unit_price: Number(item.unit_price || 0),
      row_total: lineTotal,
      deposit_applied: depositApplied,
      cash_paid: cashPaid,
      outstanding_on_line: lineOutstanding,
      remaining_amount: proportionalRemaining,
    };
  });
});

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

function openRemainingItemsDialog(type) {
  remainingItemsType.value = type === 'drug' ? 'drug' : 'service';
  showRemainingItemsDialog.value = true;
}

const debtorRows = computed(() =>
  (allVisits.value || []).filter((v) => Number(v.balance_due || 0) > 0)
);

const eligibleRows = computed(() =>
  (allCompanionVisits.value || []).filter((v) => {
    const status = String(v.undertaking_status || '').toLowerCase();
    const hasUndertaking = Boolean(v.undertaking_requested_at) || ['pending', 'approved', 'rejected'].includes(status);
    return v.status !== 'closed' && !hasUndertaking && Number(v.balance_due || 0) > 0;
  })
);

const eligibleRowsFiltered = computed(() => {
  const term = String(addSearch.value || '').trim().toLowerCase();
  if (!term) return eligibleRows.value;
  return eligibleRows.value.filter((v) =>
    [v.external_card_number, v.external_visit_number, v.client_name]
      .filter(Boolean)
      .some((s) => String(s).toLowerCase().includes(term))
  );
});

const eligibleColumns = [
  { name: 'external_card_number', label: 'Card', field: 'external_card_number', align: 'left' },
  { name: 'external_visit_number', label: 'Visit #', field: 'external_visit_number', align: 'left' },
  { name: 'client_name', label: 'Client', field: 'client_name', align: 'left' },
  { name: 'balance_due', label: 'Total owed', field: 'balance_due', align: 'right' },
  { name: 'actions', label: 'Actions', field: 'actions', align: 'left' },
];

async function loadAll() {
  loading.value = true;
  try {
    const res = await companionVisitsAPI.list();
    allCompanionVisits.value = res.data || [];
    allVisits.value = allCompanionVisits.value.filter(
      (v) => v.undertaking_requested_at // only visits that have an undertaking
    );
    if (!canApproveUndertaking.value && tab.value !== 'pending') {
      tab.value = 'pending';
    }
  } catch (e) {
    console.error('Failed to load undertakings', e);
    $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Failed to load' });
    allVisits.value = [];
  } finally {
    loading.value = false;
  }
}

function openAddDialog() {
  selectedVisitForUndertaking.value = null;
  addSearch.value = '';
  addMode.value = 'existing';
  newUndertaking.value = { partPayment: 0, receiptNumber: '' };
  manualUndertaking.value = {
    cardNumber: '',
    clientName: '',
    drugOwed: 0,
    serviceOwed: 0,
    partPayment: 0,
    receiptNumber: '',
  };
  showAddDialog.value = true;
}

function selectVisitForUndertaking(visit) {
  selectedVisitForUndertaking.value = visit;
  newUndertaking.value.partPayment = 0;
}

async function createUndertaking() {
  if (!selectedVisitForUndertaking.value) return;
  const totalOwed = Number(selectedVisitForUndertaking.value.balance_due || 0);
  const partPayment = Number(newUndertaking.value.partPayment || 0);
  if (Number.isNaN(partPayment) || partPayment < 0) {
    $q.notify({ type: 'warning', message: 'Part payment must be 0 or more.' });
    return;
  }
  if (partPayment > totalOwed) {
    $q.notify({ type: 'warning', message: 'Part payment cannot be greater than total owed.' });
    return;
  }
  creatingUndertaking.value = true;
  try {
    await companionVisitsAPI.requestUndertaking(selectedVisitForUndertaking.value.id, {
      deposit_amount: partPayment,
      deposit_receipt_number: (newUndertaking.value.receiptNumber || '').trim() || null,
    });
    $q.notify({ type: 'positive', message: 'Undertaking recorded successfully.' });
    showAddDialog.value = false;
    await loadAll();
  } catch (e) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Failed to create undertaking' });
  } finally {
    creatingUndertaking.value = false;
  }
}

function generateManualVisitNumber() {
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, '0');
  const d = String(now.getDate()).padStart(2, '0');
  const hh = String(now.getHours()).padStart(2, '0');
  const mm = String(now.getMinutes()).padStart(2, '0');
  const ss = String(now.getSeconds()).padStart(2, '0');
  const rand = Math.floor(Math.random() * 900 + 100);
  return `UTK-${y}${m}${d}-${hh}${mm}${ss}-${rand}`;
}

async function createManualUndertaking() {
  const card = String(manualUndertaking.value.cardNumber || '').trim();
  const name = String(manualUndertaking.value.clientName || '').trim();
  const drugOwed = Number(manualUndertaking.value.drugOwed || 0);
  const serviceOwed = Number(manualUndertaking.value.serviceOwed || 0);
  const totalOwed = Number(manualManualTotalOwed.value || 0);
  const partPayment = Number(manualUndertaking.value.partPayment || 0);

  if (!card) {
    $q.notify({ type: 'warning', message: 'Card number is required.' });
    return;
  }
  if (!name) {
    $q.notify({ type: 'warning', message: 'Client name is required.' });
    return;
  }
  if (Number.isNaN(drugOwed) || drugOwed < 0 || Number.isNaN(serviceOwed) || serviceOwed < 0) {
    $q.notify({ type: 'warning', message: 'Drug and service amounts must be 0 or more.' });
    return;
  }
  if (Number.isNaN(totalOwed) || totalOwed <= 0) {
    $q.notify({ type: 'warning', message: 'Total owed (drug + service) must be greater than 0.' });
    return;
  }
  if (Number.isNaN(partPayment) || partPayment < 0) {
    $q.notify({ type: 'warning', message: 'Part payment must be 0 or more.' });
    return;
  }
  if (partPayment > totalOwed) {
    $q.notify({ type: 'warning', message: 'Part payment cannot be greater than total owed.' });
    return;
  }

  creatingUndertaking.value = true;
  try {
    let createdVisit = null;
    let lastErr = null;
    // Retry visit creation in case generated visit number collides.
    for (let i = 0; i < 3; i += 1) {
      const visitNumber = generateManualVisitNumber();
      try {
        // eslint-disable-next-line no-await-in-loop
        const createRes = await companionVisitsAPI.create({
          external_card_number: card,
          external_visit_number: visitNumber,
          client_name: name,
        });
        createdVisit = createRes.data;
        break;
      } catch (e) {
        lastErr = e;
        if (e?.response?.status !== 409) throw e;
      }
    }
    if (!createdVisit) {
      throw lastErr || new Error('Failed to create manual visit');
    }

    if (serviceOwed > 0) {
      await companionVisitsAPI.addItem(createdVisit.id, {
        item_code: 'MANUAL_UNDERTAKING_SERVICE',
        item_name: 'Manual Undertaking Service Debt',
        category: 'inpatient',
        unit_price: serviceOwed,
        quantity: 1,
      });
    }
    if (drugOwed > 0) {
      await companionVisitsAPI.addItem(createdVisit.id, {
        item_code: 'MANUAL_UNDERTAKING_DRUG',
        item_name: 'Manual Undertaking Drug Debt',
        category: 'drug',
        unit_price: drugOwed,
        quantity: 1,
      });
    }

    await companionVisitsAPI.requestUndertaking(createdVisit.id, {
      deposit_amount: partPayment,
      deposit_receipt_number: (manualUndertaking.value.receiptNumber || '').trim() || null,
    });

    $q.notify({
      type: 'positive',
      message: `Manual undertaking saved. Auto visit number: ${createdVisit.external_visit_number}`,
    });
    showAddDialog.value = false;
    await loadAll();
  } catch (e) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Failed to create manual undertaking' });
  } finally {
    creatingUndertaking.value = false;
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

function isCancelledItem(item) {
  return Boolean(item?.cancelled);
}

function itemOutstandingAmount(item) {
  if (!item || isCancelledItem(item)) return 0;
  const total = rowAmount(item);
  if (total <= 0) return 0;

  const paidAt = Boolean(item.paid_at);
  const receipt = String(item.receipt_number || '').trim();
  const paymentMethod = String(item.payment_method || '').trim().toLowerCase();
  const depositLineReceipt = String(item.admission_deposit_line_receipt || '').trim();
  const rawDepositApplied = item.admission_deposit_applied;
  const hasDepositApplied = rawDepositApplied != null && !Number.isNaN(Number(rawDepositApplied));
  const depositApplied = hasDepositApplied ? Math.max(0, Number(rawDepositApplied)) : 0;

  // Legacy full-deposit flow.
  if (!hasDepositApplied && paymentMethod === 'admission_deposit') {
    return paidAt && receipt ? 0 : total;
  }

  // Split payment flow where admission_deposit_applied is persisted.
  if (hasDepositApplied) {
    const remAfterDeposit = Math.max(0, total - depositApplied);
    if (remAfterDeposit <= 0.005) {
      return paidAt && depositLineReceipt ? 0 : remAfterDeposit;
    }
    return paidAt && depositLineReceipt && receipt ? 0 : remAfterDeposit;
  }

  // Cash-only flow.
  return paidAt && receipt ? 0 : total;
}

function itemDepositAppliedAmount(item) {
  if (!item || isCancelledItem(item)) return 0;
  const total = rowAmount(item);
  if (total <= 0) return 0;
  const paymentMethod = String(item.payment_method || '').trim().toLowerCase();
  const rawDepositApplied = item.admission_deposit_applied;
  const hasDepositApplied = rawDepositApplied != null && !Number.isNaN(Number(rawDepositApplied));
  if (hasDepositApplied) {
    return Math.max(0, Math.min(total, Number(rawDepositApplied)));
  }
  // Legacy flow where full line is paid from deposit.
  if (paymentMethod === 'admission_deposit') {
    const paidAt = Boolean(item.paid_at);
    const receipt = String(item.receipt_number || '').trim();
    return paidAt && receipt ? total : 0;
  }
  return 0;
}

function itemCashPaidAmount(item) {
  if (!item || isCancelledItem(item)) return 0;
  const total = rowAmount(item);
  if (total <= 0) return 0;
  const outstanding = itemOutstandingAmount(item);
  const depositApplied = itemDepositAppliedAmount(item);
  return Math.max(0, Math.min(total, total - outstanding - depositApplied));
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

async function exportDebtorsPdf() {
  exportingDebtorsPdf.value = true;
  try {
    const [{ jsPDF }, autoMod] = await Promise.all([import('jspdf'), import('jspdf-autotable')]);
    const autoTable = autoMod.default;
    const doc = new jsPDF({ orientation: 'landscape', unit: 'mm', format: 'a4' });
    const pageW = doc.internal.pageSize.getWidth();
    let y = 7;
    const logoMaxH = 15;
    const [mohData, ghsData] = await Promise.all([
      fetchLogoDataUrl(LOGO_MOH),
      fetchLogoDataUrl(LOGO_GHS),
    ]);

    if (mohData && ghsData) {
      const [d1, d2] = await Promise.all([
        naturalSizeFromDataUrl(mohData),
        naturalSizeFromDataUrl(ghsData),
      ]);
      if (d1 && d2 && d1.h > 0 && d2.h > 0) {
        const w1 = (d1.w / d1.h) * logoMaxH;
        const w2 = (d2.w / d2.h) * logoMaxH;
        const gap = 6;
        const totalW = w1 + gap + w2;
        const x0 = (pageW - totalW) / 2;
        doc.addImage(mohData, 'PNG', x0, y, w1, logoMaxH);
        doc.addImage(ghsData, 'PNG', x0 + w1 + gap, y, w2, logoMaxH);
      }
    } else if (mohData) {
      const d1 = await naturalSizeFromDataUrl(mohData);
      if (d1 && d1.h > 0) {
        const w1 = (d1.w / d1.h) * logoMaxH;
        doc.addImage(mohData, 'PNG', (pageW - w1) / 2, y, w1, logoMaxH);
      }
    } else if (ghsData) {
      const d2 = await naturalSizeFromDataUrl(ghsData);
      if (d2 && d2.h > 0) {
        const w2 = (d2.w / d2.h) * logoMaxH;
        doc.addImage(ghsData, 'PNG', (pageW - w2) / 2, y, w2, logoMaxH);
      }
    }

    if (mohData || ghsData) {
      y += logoMaxH + 2;
    }

    doc.setFontSize(10);
    doc.setFont('helvetica', 'bold');
    doc.text('GHANA HEALTH SERVICE', pageW / 2, y, { align: 'center' });
    y += 6;
    const clinicName = (facilityStore.displayName || 'Facility').trim() || 'Facility';
    doc.setFontSize(14);
    doc.text(clinicName, pageW / 2, y, { align: 'center' });
    y += 6;
    doc.setFontSize(13);
    doc.text('Companion Undertaking Debtors Report', pageW / 2, y, { align: 'center' });
    y += 6;
    doc.setFontSize(9);
    doc.setFont('helvetica', 'normal');
    doc.text(`Generated: ${new Date().toLocaleString()}`, 14, y);
    y += 5;

    const systemRows = [];
    const manualRows = [];
    let systemDrugRemaining = 0;
    let systemServiceRemaining = 0;
    let systemPaidSoFar = 0;
    let manualDrugRemaining = 0;
    let manualServiceRemaining = 0;
    let manualPaidSoFar = 0;
    for (const visit of debtorRows.value) {
      // eslint-disable-next-line no-await-in-loop
      const itemsRes = await companionVisitsAPI.getItems(visit.id);
      const items = (itemsRes.data || []).filter((i) => !i.cancelled);
      const pending = items.filter((i) => itemOutstandingAmount(i) > 0.005);
      const hasItems = items.length > 0;
      const hasOnlyManualItems =
        hasItems &&
        items.every((i) => String(i.item_code || '').startsWith('MANUAL_UNDERTAKING_'));
      const rawDrug = pending.reduce(
        (sum, i) => (String(i.category || '').toLowerCase() === 'drug' ? sum + itemOutstandingAmount(i) : sum),
        0
      );
      const rawService = pending.reduce(
        (sum, i) => (String(i.category || '').toLowerCase() === 'drug' ? sum : sum + itemOutstandingAmount(i)),
        0
      );
      const partPayment = Math.max(0, Number(visit.undertaking_deposit_amount || 0));
      const serviceReduction = Math.min(partPayment, rawService);
      const partLeftAfterService = Math.max(0, partPayment - serviceReduction);
      const serviceRemain = Math.max(0, rawService - serviceReduction);
      const drugRemain = Math.max(0, rawDrug - partLeftAfterService);
      const remain = drugRemain + serviceRemain;
      const paidSoFar = Number(visit.bill_total || 0) - remain;
      const baseRow = [
        visit.external_card_number || '—',
        visit.external_visit_number || '—',
        visit.client_name || '—',
        Number(visit.bill_total || 0).toFixed(2),
        paidSoFar.toFixed(2),
        Number(visit.undertaking_deposit_amount || 0).toFixed(2),
        remain.toFixed(2),
        drugRemain.toFixed(2),
        serviceRemain.toFixed(2),
        visit.undertaking_approved_by_name || '—',
      ];
      if (hasOnlyManualItems) {
        manualDrugRemaining += drugRemain;
        manualServiceRemaining += serviceRemain;
        manualPaidSoFar += paidSoFar;
        manualRows.push([
          ...baseRow,
          'Manual entry: segregation between drug and service may not fully reflect original payment split.',
        ]);
      } else {
        systemDrugRemaining += drugRemain;
        systemServiceRemaining += serviceRemain;
        systemPaidSoFar += paidSoFar;
        systemRows.push(baseRow);
      }
    }
    const systemTotalOwed = systemDrugRemaining + systemServiceRemaining;
    const manualTotalOwed = manualDrugRemaining + manualServiceRemaining;

    doc.setFont('helvetica', 'bold');
    doc.text('System Undertakings (accurate segregation)', 14, y);
    y += 5;
    doc.text(`Total Service Remaining: GH¢ ${systemServiceRemaining.toFixed(2)}`, 14, y);
    y += 5;
    doc.text(`Total Drug Remaining: GH¢ ${systemDrugRemaining.toFixed(2)}`, 14, y);
    y += 5;
    doc.text(`Total Amount Owed (Service + Drug): GH¢ ${systemTotalOwed.toFixed(2)}`, 14, y);
    y += 5;
    doc.setFont('helvetica', 'normal');
    doc.text(`Total Paid So Far: GH¢ ${systemPaidSoFar.toFixed(2)}`, 14, y);
    y += 4;
    doc.setDrawColor(180);
    doc.line(14, y, pageW - 14, y);
    y += 6;

    autoTable(doc, {
      startY: y,
      head: [[
        'Card',
        'Visit #',
        'Client',
        'Total Owed',
        'Paid So Far',
        'Part Payment',
        'Remaining',
        'Drug Remaining',
        'Service Remaining',
        'Approved By',
      ]],
      body: systemRows,
      styles: { fontSize: 8, cellPadding: 1.5 },
      headStyles: { fillColor: [46, 125, 50] },
      margin: { left: 14, right: 14 },
    });

    if (manualRows.length > 0) {
      y = (doc.lastAutoTable?.finalY || y) + 8;
      doc.setFont('helvetica', 'bold');
      doc.text('Manual Undertakings', 14, y);
      y += 5;
      doc.setFont('helvetica', 'normal');
      doc.text(
        'Note: These were manual entries, so segregation between drug and service may not be a true reflection.',
        14,
        y
      );
      y += 5;
      doc.setFont('helvetica', 'bold');
      doc.text(`Total Service Remaining: GH¢ ${manualServiceRemaining.toFixed(2)}`, 14, y);
      y += 5;
      doc.text(`Total Drug Remaining: GH¢ ${manualDrugRemaining.toFixed(2)}`, 14, y);
      y += 5;
      doc.text(`Total Amount Owed (Service + Drug): GH¢ ${manualTotalOwed.toFixed(2)}`, 14, y);
      y += 5;
      doc.setFont('helvetica', 'normal');
      doc.text(`Total Paid So Far: GH¢ ${manualPaidSoFar.toFixed(2)}`, 14, y);
      y += 4;
      doc.setDrawColor(180);
      doc.line(14, y, pageW - 14, y);
      y += 6;

      autoTable(doc, {
        startY: y,
        head: [[
          'Card',
          'Visit #',
          'Client',
          'Total Owed',
          'Paid So Far',
          'Part Payment',
          'Remaining',
          'Drug Remaining',
          'Service Remaining',
          'Approved By',
          'Note',
        ]],
        body: manualRows,
        styles: { fontSize: 7, cellPadding: 1.5 },
        headStyles: { fillColor: [180, 120, 40] },
        margin: { left: 14, right: 14 },
      });
    }
    doc.save(`undertaking_debtors_${new Date().toISOString().slice(0, 10)}.pdf`);
  } catch (e) {
    console.error('Failed to export debtors report', e);
    $q.notify({ type: 'negative', message: 'Failed to export debtors PDF report.' });
  } finally {
    exportingDebtorsPdf.value = false;
  }
}

onMounted(() => {
  if (!facilityStore.loaded) {
    facilityStore.fetchPublic();
  }
  loadAll();
});
</script>
