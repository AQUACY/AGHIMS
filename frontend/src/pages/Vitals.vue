<template>
  <q-page class="hms-page">
    <HmsPageHeader title="Record vitals" :subtitle="formattedDate">
      <template #actions>
        <HmsButton variant="secondary" size="sm" @click="shiftDay(-1)">Prev</HmsButton>
        <HmsButton variant="secondary" size="sm" @click="setToday">Today</HmsButton>
        <HmsButton variant="secondary" size="sm" @click="shiftDay(1)">Next</HmsButton>
      </template>
    </HmsPageHeader>

    <div class="vitals-toolbar">
      <div class="toolbar-meta">
        <HeartPulse :size="15" />
        <span>{{ filteredEncounters.length }} encounter{{ filteredEncounters.length === 1 ? '' : 's' }}</span>
      </div>
      <div class="toolbar-controls">
        <input v-model="selectedDate" type="date" class="tool-input" @change="loadEncounters" />
        <input v-model="cardSearch" type="search" class="tool-input" placeholder="Filter by card…" />
      </div>
    </div>

    <HmsDataTable
      :rows="filteredEncounters"
      :columns="vitalsTableColumns"
      row-key="id"
      :loading="loading"
      dense
      searchable
      search-placeholder="Search patient, card, department…"
      empty-title="No encounters for this date"
      empty-description="Try another day or clear the card filter."
      @row-click="recordVitals"
    >
      <template #cell-time="{ value }">{{ formatTime(value) }}</template>
      <template #cell-patient_name="{ row }">
        <div class="patient-cell">
          <div class="avatar">{{ patientInitials(row) }}</div>
          <div>
            <div class="name">{{ titleCaseName(row.patient_name) }}</div>
            <div class="sub mono">{{ row.patient_card_number }}</div>
          </div>
        </div>
      </template>
      <template #cell-status="{ value }">
        <HmsBadge :tone="statusTone(value)">{{ value }}</HmsBadge>
      </template>
      <template #cell-has_vitals="{ value }">
        <HmsBadge :tone="value ? 'success' : 'muted'">{{ value ? 'Recorded' : 'Pending' }}</HmsBadge>
      </template>
      <template #cell-actions="{ row }">
        <HmsButton
          :variant="row.has_vitals ? 'secondary' : 'primary'"
          size="sm"
          @click.stop="recordVitals(row)"
        >
          {{ row.has_vitals ? 'Edit' : 'Record' }}
        </HmsButton>
      </template>
    </HmsDataTable>

    <!-- Vitals Form Dialog -->
    <q-dialog v-model="showVitalsDialog" persistent>
      <q-card class="vitals-dialog-card" style="min-width: min(900px, 96vw); max-width: 960px">
      <q-card-section class="vitals-dialog-head">
          <div class="dialog-title">Record vitals</div>
          <div class="dialog-sub">Encounter #{{ selectedEncounter?.id }}</div>
          <div class="row q-gutter-md q-mt-md">
            <div class="col-12 col-md-6">
              <div class="text-body2"><strong>Patient:</strong> {{ selectedEncounter?.patient_name || 'N/A' }}</div>
              <div class="text-body2"><strong>Card Number:</strong> {{ selectedEncounter?.patient_card_number || 'N/A' }}</div>
            </div>
            <div class="col-12 col-md-6">
              <div class="text-body2"><strong>Age:</strong> {{ selectedEncounter?.patient_age ? `${selectedEncounter.patient_age} years` : 'N/A' }}</div>
              <div class="text-body2"><strong>Sex:</strong> {{ selectedEncounter?.patient_gender === 'M' ? 'Male' : selectedEncounter?.patient_gender === 'F' ? 'Female' : selectedEncounter?.patient_gender || 'N/A' }}</div>
            </div>
          </div>
          <div class="row q-gutter-md q-mt-xs">
            <div class="col-12 col-md-6">
              <div class="text-body2"><strong>Insurance Number:</strong> {{ selectedEncounter?.patient_insurance_id || 'N/A' }}</div>
            </div>
            <div class="col-12 col-md-6">
              <div class="text-body2"><strong>Address:</strong> {{ selectedEncounter?.patient_address || 'N/A' }}</div>
            </div>
          </div>
          <div v-if="encounterBillInfo.totalAmount !== null" class="row q-gutter-md q-mt-xs">
            <div class="col-12">
              <div class="text-body2" :class="encounterBillInfo.remainingBalance > 0 ? 'text-negative text-weight-bold' : 'text-secondary'">
                <q-icon name="receipt" size="14px" class="q-mr-xs" />
                <span 
                  @click="openBillItemsDialog" 
                  style="cursor: pointer; text-decoration: underline;"
                  class="text-primary"
                >
                  <strong>Total Bills:</strong> GHC {{ encounterBillInfo.totalAmount.toFixed(2) }} 
                  <span v-if="encounterBillInfo.remainingBalance > 0" class="text-negative">
                    | Outstanding: GHC {{ encounterBillInfo.remainingBalance.toFixed(2) }}
                  </span>
                  <span v-else>
                    | Outstanding: GHC 0.00
                  </span>
                </span>
                <q-tooltip>Click to view all bill items</q-tooltip>
              </div>
            </div>
          </div>
        </q-card-section>

        <q-card-section class="q-pt-none">
        <q-form @submit="onSubmit" class="q-gutter-md">
          <div class="row q-gutter-md">
              <q-input 
                v-model="vitalsForm.bp" 
                filled 
                label="Blood Pressure (e.g., 120/80)" 
                class="col-12 col-md-6" 
                hint="e.g., 120/80"
              />
              <q-input 
                v-model.number="vitalsForm.temperature" 
                filled 
                type="number" 
                label="Temperature (°C)" 
                class="col-12 col-md-6" 
                step="0.1"
              />
          </div>

          <div class="row q-gutter-md">
              <q-input 
                v-model.number="vitalsForm.pulse" 
                filled 
                type="number" 
                label="Pulse (bpm)" 
                class="col-12 col-md-3" 
              />
              <q-input 
                v-model.number="vitalsForm.respiration" 
                filled 
                type="number" 
                label="Respiration (breaths/min)" 
                class="col-12 col-md-3" 
              />
              <q-input 
                v-model.number="vitalsForm.weight" 
                filled 
                type="number" 
                label="Weight (kg)" 
                class="col-12 col-md-3" 
                step="0.1"
              />
              <q-input 
                v-model.number="vitalsForm.height" 
                filled 
                type="number" 
                label="Height (cm)" 
                class="col-12 col-md-3" 
                step="0.1"
              />
          </div>

          <div class="row q-gutter-md">
              <q-input 
                v-model.number="vitalsForm.bmi" 
                filled 
                type="number" 
                label="BMI" 
                class="col-12 col-md-3" 
                step="0.1"
              />
              <q-input 
                v-model.number="vitalsForm.spo2" 
                filled 
                type="number" 
                label="SPO2 (%)" 
                class="col-12 col-md-3" 
              />
              <q-input 
                v-model.number="vitalsForm.rbs" 
                filled 
                type="number" 
                label="Random Blood Sugar (mmol/L)" 
                class="col-12 col-md-3" 
                step="0.1"
              />
              <q-input 
                v-model.number="vitalsForm.fbs" 
                filled 
                type="number" 
                label="Fasting Blood Sugar (mmol/L)" 
                class="col-12 col-md-3" 
                step="0.1"
              />
          </div>

          <div class="row q-gutter-md">
              <q-select 
                v-model="vitalsForm.upt" 
                filled 
                :options="testOptions" 
                emit-value 
                map-options 
                label="UPT" 
                class="col-12 col-md-4" 
                clearable 
              />
              <q-select 
                v-model="vitalsForm.rdt_malaria" 
                filled 
                :options="testOptions" 
                emit-value 
                map-options 
                label="RDT for Malaria" 
                class="col-12 col-md-4" 
                clearable
                @update:model-value="onRDTSelected"
              />
              <q-select 
                v-model="vitalsForm.retro_rdt" 
                filled 
                :options="testOptions" 
                emit-value 
                map-options 
                label="Retro RDT" 
                class="col-12 col-md-4" 
                clearable 
              />
          </div>

          <q-input
            v-model="vitalsForm.remarks"
            filled
            label="Remarks"
            type="textarea"
            rows="3"
          />

            <div class="row justify-end q-gutter-sm q-mt-md">
              <HmsButton variant="ghost" size="sm" @click="closeVitalsDialog">Cancel</HmsButton>
              <HmsButton variant="primary" size="sm" type="submit" :loading="saving">
                Save vitals
              </HmsButton>
          </div>
        </q-form>
      </q-card-section>

      <!-- Inventory Debit Section -->
      <q-card-section v-if="selectedEncounter" class="vitals-debit-section">
        <div class="debit-title">Inventory debits</div>
        <div class="debit-sub">Stock management only — items are not billed to the patient.</div>
        
        <!-- Reminder to debit when RDT is selected -->
        <div
          v-if="vitalsForm.rdt_malaria && !hasMalariaRDTDebit"
          class="debit-banner debit-banner--warn"
        >
          <strong>RDT result recorded.</strong> Debit Malaria RDT inventory before saving vitals.
        </div>
        
        <div class="debit-banner debit-banner--info">
          OPD inventory debits are for stock accountability only.
        </div>
        
        <!-- Stock Levels -->
        <q-card flat bordered class="q-mb-md">
          <q-card-section>
            <div class="text-subtitle2 q-mb-sm">
              Available Stock 
              <span v-if="selectedEncounter?.department">
                ({{ selectedEncounter.department }}
                <span v-if="canUseGeneralOPDStock && selectedEncounter.department.toLowerCase() !== 'general opd' && selectedEncounter.department.toLowerCase() !== 'general'">
                  + General OPD (Malaria RDT only)
                </span>
                <span v-else-if="selectedEncounter.department.toLowerCase() === 'general opd' || selectedEncounter.department.toLowerCase() === 'general'">
                  - All Items
                </span>
                )
              </span>
              <span v-else>N/A</span>
            </div>
            <div v-if="loadingStock" class="text-center q-pa-md">
              <q-spinner color="primary" size="sm" />
              <div class="text-caption q-mt-sm">Loading stock...</div>
            </div>
            <div v-else-if="departmentStock.length === 0" class="text-grey-6 text-center q-pa-md">
              No stock available for this department
            </div>
            <div v-else class="row q-gutter-sm">
              <q-chip
                v-for="stock in filteredStock"
                :key="`${stock.product_code}-${stock.ward || 'dept'}`"
                :color="getStockColor(stock.quantity)"
                text-color="white"
                :label="`${stock.product_name}: ${stock.quantity.toFixed(0)}`"
                size="sm"
              />
            </div>
          </q-card-section>
        </q-card>

        <!-- Existing Inventory Debits -->
        <div v-if="inventoryDebits.length > 0" class="q-mb-md">
          <div class="text-subtitle2 q-mb-sm">Debited Items</div>
          <q-table
            :rows="inventoryDebits"
            :columns="inventoryDebitColumns"
            row-key="id"
            flat
            dense
            :loading="loadingDebits"
          >
            <template v-slot:body-cell-actions="props">
              <q-td :props="props">
                <q-btn
                  size="xs"
                  color="negative"
                  icon="delete"
                  flat
                  @click="deleteInventoryDebit(props.row.id)"
                  :loading="deletingDebit === props.row.id"
                />
              </q-td>
            </template>
          </q-table>
        </div>

        <!-- Add Inventory Debit -->
        <q-card flat bordered>
          <q-card-section>
            <div class="text-subtitle2 q-mb-sm">Debit Item</div>
            <div class="row q-gutter-md">
              <q-select
                v-model="newDebit.product_code"
                :options="stockProductOptions"
                option-label="label"
                option-value="value"
                emit-value
                map-options
                label="Product"
                filled
                class="col-12 col-md-6"
                @update:model-value="onProductSelected"
              />
              <q-input
                v-model.number="newDebit.quantity"
                filled
                type="number"
                label="Quantity"
                class="col-12 col-md-3"
                min="0.1"
                step="0.1"
              />
              <q-btn
                label="Debit"
                color="primary"
                icon="add"
                class="col-12 col-md-3"
                @click="addInventoryDebit"
                :loading="addingDebit"
                :disable="!newDebit.product_code || !newDebit.quantity || newDebit.quantity <= 0"
              />
            </div>
            <q-input
              v-model="newDebit.notes"
              filled
              label="Notes (optional)"
              class="q-mt-md"
            />
          </q-card-section>
        </q-card>
      </q-card-section>
    </q-card>
    </q-dialog>

    <!-- Bill Items Dialog -->
    <q-dialog v-model="showBillItemsDialog" maximized>
      <q-card>
        <q-card-section class="row items-center q-pb-none">
          <div class="text-h6">Bill Items - {{ selectedEncounter?.patient_name || 'Patient' }}</div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>
        <q-card-section>
          <div v-if="loadingBillItems" class="text-center q-pa-md">
            <q-spinner color="primary" size="3em" />
            <div class="q-mt-md">Loading bill items...</div>
          </div>
          <div v-else-if="allBillItems.length === 0" class="text-center q-pa-md text-grey-7">
            No bill items found.
          </div>
          <q-table
            v-else
            :rows="allBillItems"
            :columns="billItemsColumns"
            row-key="id"
            :pagination="{ rowsPerPage: 50 }"
            class="bill-items-table"
            flat
            bordered
          >
            <template v-slot:body-cell-encounter_id="props">
              <q-td :props="props">
                <q-badge color="primary" :label="`Encounter #${props.value}`" />
              </q-td>
            </template>
            <template v-slot:body-cell-remaining_balance="props">
              <q-td :props="props" :class="props.value > 0.01 ? 'text-negative text-weight-bold' : 'text-positive'">
                GHC {{ props.value.toFixed(2) }}
              </q-td>
            </template>
            <template v-slot:body-cell-is_paid="props">
              <q-td :props="props">
                <q-badge :color="props.value ? 'positive' : 'negative'" :label="props.value ? 'Paid' : 'Unpaid'" />
              </q-td>
            </template>
          </q-table>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Close" color="primary" v-close-popup />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { vitalsAPI, encountersAPI, patientsAPI, billingAPI, consultationAPI, pharmacyRequisitionsAPI, wardsAPI } from '../services/api';
import { useQuasar } from 'quasar';
import { HeartPulse } from 'lucide-vue-next';
import HmsPageHeader from '../components/ui/HmsPageHeader.vue';
import HmsButton from '../components/ui/HmsButton.vue';
import HmsBadge from '../components/ui/HmsBadge.vue';
import HmsDataTable from '../components/ui/HmsDataTable.vue';

const $q = useQuasar();
const router = useRouter();
const route = useRoute();

const selectedDate = ref('');
const encounters = ref([]);
const loading = ref(false);
const cardSearch = ref('');

const vitalsTableColumns = [
  { name: 'time', label: 'Time', field: 'created_at', align: 'left', width: '100px' },
  { name: 'patient_name', label: 'Patient', field: 'patient_name', align: 'left' },
  { name: 'department', label: 'Department', field: 'department', align: 'left', width: '140px' },
  { name: 'status', label: 'Status', field: 'status', align: 'center', width: '120px' },
  { name: 'has_vitals', label: 'Vitals', field: 'has_vitals', align: 'center', width: '110px' },
  { name: 'actions', label: '', align: 'right', width: '110px' },
];

const titleCaseName = (value) => {
  if (!value) return 'Unknown';
  return String(value)
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase());
};

const patientInitials = (row) => {
  const parts = String(row.patient_name || '?').trim().split(/\s+/);
  const a = (parts[0] || '?')[0] || '?';
  const b = (parts[1] || '')[0] || '';
  return `${a}${b}`.toUpperCase();
};

const statusTone = (status) => {
  const s = String(status || '').toLowerCase();
  if (s.includes('final')) return 'success';
  if (s.includes('consult') || s.includes('progress')) return 'healthcare';
  if (s.includes('await') || s.includes('draft') || s.includes('pending')) return 'warning';
  return 'neutral';
};

const shiftDay = (delta) => {
  if (!selectedDate.value) {
    setToday();
    return;
  }
  const d = new Date(`${selectedDate.value}T12:00:00`);
  d.setDate(d.getDate() + delta);
  selectedDate.value = d.toISOString().split('T')[0];
  loadEncounters();
};

const showVitalsDialog = ref(false);
const selectedEncounter = ref(null);
const saving = ref(false);
const encounterBillInfo = ref({
  totalAmount: null,
  paidAmount: null,
  remainingBalance: null,
});
const showBillItemsDialog = ref(false);
const loadingBillItems = ref(false);
const allBillItems = ref([]);
const billItemsColumns = [
  { name: 'encounter_id', label: 'Encounter', field: 'encounter_id', align: 'center', sortable: true },
  { name: 'item_name', label: 'Service/Item', field: 'item_name', align: 'left', sortable: true },
  { name: 'category', label: 'Category', field: 'category', align: 'center', sortable: true },
  { name: 'quantity', label: 'Qty', field: 'quantity', align: 'center', sortable: true },
  { name: 'unit_price', label: 'Unit Price', field: 'unit_price', align: 'right', sortable: true, format: (val) => `GHC ${(val || 0).toFixed(2)}` },
  { name: 'total_price', label: 'Total Price', field: 'total_price', align: 'right', sortable: true, format: (val) => `GHC ${(val || 0).toFixed(2)}` },
  { name: 'amount_paid', label: 'Amount Paid', field: 'amount_paid', align: 'right', sortable: true, format: (val) => `GHC ${(val || 0).toFixed(2)}` },
  { name: 'remaining_balance', label: 'Outstanding', field: 'remaining_balance', align: 'right', sortable: true },
  { name: 'is_paid', label: 'Status', field: 'is_paid', align: 'center', sortable: true },
];

const inventoryDebits = ref([]);
const loadingDebits = ref(false);
const departmentStock = ref([]);
const loadingStock = ref(false);
const addingDebit = ref(false);
const deletingDebit = ref(null);

const newDebit = reactive({
  product_code: null,
  product_name: '',
  quantity: 1,
  notes: '',
});

const inventoryDebitColumns = [
  { name: 'product_name', label: 'Product', field: 'product_name', align: 'left' },
  { name: 'quantity', label: 'Quantity', field: 'quantity', align: 'center' },
  { name: 'used_at', label: 'Date', field: 'used_at', align: 'left', format: (val) => val ? new Date(val).toLocaleString() : '' },
  { name: 'actions', label: 'Actions', align: 'center' },
];

const stockProductOptions = computed(() => {
  return departmentStock.value.map(stock => ({
    label: `${stock.product_name} (Stock: ${stock.quantity.toFixed(0)})`,
    value: stock.product_code,
    product_name: stock.product_name,
    stock_quantity: stock.quantity,
  }));
});

const filteredStock = computed(() => {
  // Show all items with stock > 0 (including from General OPD)
  return departmentStock.value.filter(stock => (stock.quantity || 0) > 0);
});

// Computed property to check if Malaria RDT has been debited
const hasMalariaRDTDebit = computed(() => {
  if (!vitalsForm.rdt_malaria) return false;
  return inventoryDebits.value.some(debit => 
    debit.product_name.toLowerCase().includes('malaria') && 
    (debit.product_name.toLowerCase().includes('rdt') || debit.product_code.toLowerCase().includes('rdt'))
  );
});

// Load departments to check their type
const departments = ref([]);
const departmentTypeMap = computed(() => {
  const map = {};
  departments.value.forEach(dept => {
    map[dept.name] = dept.department_type;
  });
  return map;
});

const canUseGeneralOPDStock = computed(() => {
  if (!selectedEncounter.value?.department) return false;
  const department = selectedEncounter.value.department;
  
  // Check if department is OPD type from the database
  const deptType = departmentTypeMap.value[department];
  if (deptType === 'opd') {
    return true;
  }
  
  // Fallback: check legacy department name patterns if not found in database
  const departmentsUsingGeneralOPD = [
    'Paediatric', 'Pediatrics', 'Paediatric Clinic',
    'ENT', 'ENT Clinic',
    'Eye', 'Eye Clinic',
    'Diabetic & Hypertension Clinic', 'Diabetic', 'Hypertension', 'DIABETIC & HYPERTENSION CLINIC'
  ];
  const deptLower = department.toLowerCase();
  return departmentsUsingGeneralOPD.some(
    dept => deptLower.includes(dept.toLowerCase()) || (deptLower.includes('diabetic') && deptLower.includes('hypertension'))
  );
});

const columns = [
  { name: 'time', label: 'Time', field: 'created_at', align: 'left', sortable: true },
  { name: 'id', label: 'Encounter ID', field: 'id', align: 'left' },
  { name: 'patient_name', label: 'Patient Name', field: 'patient_name', align: 'left' },
  { name: 'card_number', label: 'Card Number', field: 'patient_card_number', align: 'left' },
  { name: 'department', label: 'Department', field: 'department', align: 'left' },
  { name: 'status', label: 'Status', field: 'status', align: 'center' },
  { name: 'has_vitals', label: 'Vitals', field: 'has_vitals', align: 'center' },
  { name: 'actions', label: 'Actions', align: 'center' },
];

const testOptions = [
  { label: 'Negative', value: 'negative' },
  { label: 'Positive', value: 'positive' }
];

const formattedDate = computed(() => {
  if (!selectedDate.value) return 'Select a date';
  const date = new Date(selectedDate.value);
  return date.toLocaleDateString('en-US', { 
    weekday: 'long', 
    year: 'numeric', 
    month: 'long', 
    day: 'numeric' 
  });
});

const filteredEncounters = computed(() => {
  const needle = (cardSearch.value || '').toLowerCase().trim();
  if (!needle) return encounters.value;
  return encounters.value.filter(e => (e.patient_card_number || '').toLowerCase().includes(needle));
});

const setToday = () => {
  const today = new Date();
  selectedDate.value = today.toISOString().split('T')[0];
  loadEncounters();
};

const formatTime = (dateString) => {
  if (!dateString) return '';
  const date = new Date(dateString);
  return date.toLocaleTimeString('en-US', { 
    hour: '2-digit', 
    minute: '2-digit',
    hour12: true 
  });
};

const getStatusColor = (status) => {
  const colors = {
    draft: 'orange',
    in_consultation: 'blue',
    awaiting_services: 'purple',
    finalized: 'green',
  };
  return colors[status] || 'grey';
};

const loadEncounters = async () => {
  if (!selectedDate.value) {
    encounters.value = [];
    return;
  }

  loading.value = true;
  try {
    // Load encounters for the date using encounters API
    const response = await encountersAPI.getByDate(selectedDate.value);
    const encountersList = response.data || [];
    
    // Check vitals status for each encounter
    const encountersWithVitals = await Promise.all(
      encountersList.map(async (encounter) => {
        try {
          // Try to get vitals for this encounter
          const vitalsResponse = await vitalsAPI.getByEncounter(encounter.id);
          return {
            ...encounter,
            has_vitals: true,
            vitals_id: vitalsResponse.data?.id || null,
          };
        } catch (error) {
          // If 404, vitals don't exist for this encounter
          return {
            ...encounter,
            has_vitals: false,
            vitals_id: null,
          };
        }
      })
    );
    
    encounters.value = encountersWithVitals;
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to load encounters',
    });
    encounters.value = [];
  } finally {
    loading.value = false;
  }
};

const loadEncounterBills = async (encounterId) => {
  if (!encounterId) {
    encounterBillInfo.value = {
      totalAmount: null,
      paidAmount: null,
      remainingBalance: null,
    };
    return;
  }

  try {
    const billsResponse = await billingAPI.getEncounterBills(encounterId);
    const bills = Array.isArray(billsResponse.data) ? billsResponse.data : [];
    
    let totalAmount = 0;
    let paidAmount = 0;
    
    for (const bill of bills) {
      totalAmount += bill.total_amount || 0;
      paidAmount += bill.paid_amount || 0;
    }
    
    const remainingBalance = totalAmount - paidAmount;
    
    encounterBillInfo.value = {
      totalAmount: totalAmount,
      paidAmount: paidAmount,
      remainingBalance: remainingBalance > 0.01 ? remainingBalance : 0, // Allow small rounding differences
    };
  } catch (error) {
    console.error('Error loading encounter bills:', error);
    // Set to null to indicate error/not loaded
    encounterBillInfo.value = {
      totalAmount: null,
      paidAmount: null,
      remainingBalance: null,
    };
  }
};

const recordVitals = async (encounter) => {
  selectedEncounter.value = encounter;
  
  // Load bills for this encounter
  await loadEncounterBills(encounter.id);
  
  // Load inventory debits and stock
  await loadInventoryDebits(encounter.id);
  await loadDepartmentStock(encounter.department);
  
  try {
    // Always fetch full patient details to ensure we have the latest data
    if (encounter.patient_card_number) {
      try {
        const patientResponse = await patientsAPI.getByCard(encounter.patient_card_number);
        let patients = [];
        if (Array.isArray(patientResponse.data)) {
          patients = patientResponse.data;
        } else if (patientResponse.data && typeof patientResponse.data === 'object' && !Array.isArray(patientResponse.data)) {
          patients = [patientResponse.data];
        }
        
        if (patients.length > 0) {
          const patient = patients[0];
          // Update encounter with full patient details
          selectedEncounter.value = {
            ...encounter,
            patient_name: patient.name + (patient.surname ? ' ' + patient.surname : '') + (patient.other_names ? ' ' + patient.other_names : ''),
            patient_card_number: patient.card_number,
            patient_age: patient.age,
            patient_gender: patient.gender,
            patient_insurance_id: patient.insurance_id,
            patient_address: patient.address,
          };
        }
      } catch (patientError) {
        console.warn('Failed to fetch patient details:', patientError);
        // Continue even if patient fetch fails - use data from encounter
      }
    }
    
    // Load existing vitals if available
    if (encounter.has_vitals) {
      const vitalsResponse = await vitalsAPI.getByEncounter(encounter.id);
      const vitals = vitalsResponse.data;
      Object.assign(vitalsForm, {
        encounter_id: encounter.id,
        vitals_id: vitals.id,
        bp: vitals.bp || '',
        temperature: vitals.temperature || null,
        pulse: vitals.pulse || null,
        respiration: vitals.respiration || null,
        weight: vitals.weight || null,
        height: vitals.height || null,
        bmi: vitals.bmi || null,
        spo2: vitals.spo2 || null,
        rbs: vitals.rbs || null,
        fbs: vitals.fbs || null,
        upt: vitals.upt || null,
        rdt_malaria: vitals.rdt_malaria || null,
        retro_rdt: vitals.retro_rdt || null,
        remarks: vitals.remarks || '',
      });
    } else {
      // Reset form for new vitals
      Object.assign(vitalsForm, {
        encounter_id: encounter.id,
        vitals_id: null,
        bp: '',
        temperature: null,
        pulse: null,
        respiration: null,
        weight: null,
        height: null,
        bmi: null,
        spo2: null,
        rbs: null,
        fbs: null,
        upt: null,
        rdt_malaria: null,
        retro_rdt: null,
        remarks: '',
      });
    }
    
    showVitalsDialog.value = true;
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to load vitals',
    });
  }
};

const closeVitalsDialog = () => {
  showVitalsDialog.value = false;
  selectedEncounter.value = null;
  inventoryDebits.value = [];
  departmentStock.value = [];
  Object.assign(newDebit, {
    product_code: null,
    product_name: '',
    quantity: 1,
    notes: '',
  });
};

const loadInventoryDebits = async (encounterId) => {
  if (!encounterId) return;
  
  loadingDebits.value = true;
  try {
    const response = await consultationAPI.getEncounterInventoryDebits(encounterId);
    inventoryDebits.value = response.data || [];
  } catch (error) {
    console.error('Error loading inventory debits:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to load inventory debits',
    });
    inventoryDebits.value = [];
  } finally {
    loadingDebits.value = false;
  }
};

const loadDepartmentStock = async (department) => {
  if (!department) return;
  
  loadingStock.value = true;
  try {
    // Load department stock
    const response = await pharmacyRequisitionsAPI.getWardStock(department);
    let stock = response.data || [];
    
    // Check if department can use General OPD stock
    // First check if department is OPD type from database
    const deptType = departmentTypeMap.value[department];
    let canUseGeneralOPD = deptType === 'opd';
    
    // Fallback: check legacy department name patterns if not found in database
    if (!canUseGeneralOPD) {
      const departmentsUsingGeneralOPD = [
        'Paediatric', 'Pediatrics', 'Paediatric Clinic',
        'ENT', 'ENT Clinic',
        'Eye', 'Eye Clinic',
        'Diabetic & Hypertension Clinic', 'Diabetic', 'Hypertension', 'DIABETIC & HYPERTENSION CLINIC'
      ];
      const deptLower = department.toLowerCase();
      canUseGeneralOPD = departmentsUsingGeneralOPD.some(
        dept => deptLower.includes(dept.toLowerCase()) || (deptLower.includes('diabetic') && deptLower.includes('hypertension'))
      );
    }
    
    // Check if this is General OPD department itself
    const isGeneralOPD = department.toLowerCase() === 'general opd' || department.toLowerCase() === 'general';
    
    if (canUseGeneralOPD && !isGeneralOPD) {
      // For non-General OPD departments, only load Malaria RDT from General OPD
      try {
        const generalOPDResponse = await pharmacyRequisitionsAPI.getWardStock('General OPD');
        const generalOPDStock = generalOPDResponse.data || [];
        
        // Filter to only Malaria RDT items
        const malariaRDTStock = generalOPDStock.filter(item => {
          const productName = (item.product_name || '').toLowerCase();
          const productCode = (item.product_code || '').toLowerCase();
          return productName.includes('malaria') && (productName.includes('rdt') || productCode.includes('rdt'));
        });
        
        // Merge stocks - if same product exists in both, combine quantities
        const stockMap = new Map();
        
        // Add department stock first (even if 0, to show it exists)
        stock.forEach(item => {
          stockMap.set(item.product_code, {
            ...item,
            source: department,
            combined_quantity: item.quantity || 0,
            dept_quantity: item.quantity || 0
          });
        });
        
        // Add or merge General OPD Malaria RDT stock only
        malariaRDTStock.forEach(item => {
          const productCode = item.product_code;
          if (stockMap.has(productCode)) {
            // Merge quantities - add General OPD to existing department stock
            const existing = stockMap.get(productCode);
            existing.combined_quantity = (existing.dept_quantity || 0) + (item.quantity || 0);
            existing.source = `${department} + General OPD`;
            existing.general_opd_quantity = item.quantity || 0;
          } else {
            // Add General OPD Malaria RDT stock item (not in department)
            stockMap.set(productCode, {
              ...item,
              source: 'General OPD',
              combined_quantity: item.quantity || 0,
              dept_quantity: 0,
              general_opd_quantity: item.quantity || 0
            });
          }
        });
        
        // Convert back to array and update quantities to show combined
        stock = Array.from(stockMap.values()).map(item => {
          // Ensure all required fields are present
          // Use General OPD id if source is General OPD, otherwise use department id
          const stockId = item.source === 'General OPD' ? item.id : (item.id || `dept-${item.product_code}`);
          return {
            id: stockId,
            ward: item.ward || (item.source === 'General OPD' ? 'General' : department),
            store_id: item.store_id,
            store_name: item.store_name,
            product_code: item.product_code,
            product_name: item.product_name,
            quantity: item.combined_quantity || 0,
            created_at: item.created_at,
            updated_at: item.updated_at,
            source_info: item.source,
            dept_quantity: item.dept_quantity || 0,
            general_opd_quantity: item.general_opd_quantity || 0
          };
        });
      } catch (error) {
        console.warn('Could not load General OPD stock:', error);
        // Continue with department stock only
      }
    }
    
    departmentStock.value = stock;
  } catch (error) {
    console.error('Error loading department stock:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to load department stock',
    });
    departmentStock.value = [];
  } finally {
    loadingStock.value = false;
  }
};

const onProductSelected = (productCode) => {
  const selected = stockProductOptions.value.find(opt => opt.value === productCode);
  if (selected) {
    newDebit.product_name = selected.product_name;
  }
};

const onRDTSelected = (value) => {
  // When RDT is selected, auto-select Malaria RDT product and remind user to debit
  if (value && !hasMalariaRDTDebit.value) {
    // Auto-select Malaria RDT in the product dropdown if available
    const malariaRDTProduct = stockProductOptions.value.find(opt => {
      const name = opt.product_name?.toLowerCase() || '';
      const code = opt.value?.toLowerCase() || '';
      return name.includes('malaria') && (name.includes('rdt') || code.includes('rdt'));
    });
    
    if (malariaRDTProduct) {
      // Auto-select the Malaria RDT product
      newDebit.product_code = malariaRDTProduct.value;
      newDebit.product_name = malariaRDTProduct.product_name;
      
      $q.notify({
        type: 'info',
        message: 'Malaria RDT product auto-selected. Please debit inventory before saving vitals.',
        position: 'top',
        timeout: 3000,
        icon: 'info'
      });
    } else {
      $q.notify({
        type: 'info',
        message: 'Please debit Malaria RDT inventory before saving vitals.',
        position: 'top',
        timeout: 3000,
        icon: 'info'
      });
    }
  }
};

const addInventoryDebit = async () => {
  if (!selectedEncounter.value || !newDebit.product_code || !newDebit.quantity || newDebit.quantity <= 0) {
    return;
  }

  // Validation: Check if Malaria RDT is being debited
  const isMalariaRDT = newDebit.product_name.toLowerCase().includes('malaria') && 
                       (newDebit.product_name.toLowerCase().includes('rdt') || 
                        newDebit.product_code.toLowerCase().includes('rdt'));
  
  if (isMalariaRDT && !vitalsForm.rdt_malaria) {
    $q.notify({
      type: 'negative',
      message: 'Cannot debit Malaria RDT without recording RDT result in vitals. Please record the RDT result first.',
      position: 'top',
      timeout: 5000,
    });
    return;
  }

  addingDebit.value = true;
  try {
    const debitData = {
      product_code: newDebit.product_code,
      product_name: newDebit.product_name,
      quantity: newDebit.quantity,
      notes: newDebit.notes || null,
      // Include RDT value from form if available (for validation when vitals not saved yet)
      rdt_malaria_value: vitalsForm.rdt_malaria || null,
    };

    await consultationAPI.createEncounterInventoryDebit(selectedEncounter.value.id, debitData);
    
    $q.notify({
      type: 'positive',
      message: 'Inventory debited successfully',
      position: 'top',
    });

    // Reload debits and stock
    await loadInventoryDebits(selectedEncounter.value.id);
    await loadDepartmentStock(selectedEncounter.value.department);
    
    // Note: OPD inventory debits are not billed, so no need to reload bills

    // Reset form
    Object.assign(newDebit, {
      product_code: null,
      product_name: '',
      quantity: 1,
      notes: '',
    });
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to debit inventory',
      position: 'top',
    });
  } finally {
    addingDebit.value = false;
  }
};

const deleteInventoryDebit = async (debitId) => {
  if (!selectedEncounter.value || !debitId) return;

  $q.dialog({
    title: 'Confirm Delete',
    message: 'Are you sure you want to delete this inventory debit? Stock will be restored.',
    cancel: true,
    persistent: true,
  }).onOk(async () => {
    deletingDebit.value = debitId;
    try {
      await consultationAPI.deleteEncounterInventoryDebit(selectedEncounter.value.id, debitId);
      
      $q.notify({
        type: 'positive',
        message: 'Inventory debit deleted successfully',
        position: 'top',
      });

      // Reload debits and stock
      await loadInventoryDebits(selectedEncounter.value.id);
      await loadDepartmentStock(selectedEncounter.value.department);
      
      // Note: OPD inventory debits are not billed, so no need to reload bills
    } catch (error) {
      $q.notify({
        type: 'negative',
        message: error.response?.data?.detail || 'Failed to delete inventory debit',
        position: 'top',
      });
    } finally {
      deletingDebit.value = null;
    }
  });
};

const getStockColor = (quantity) => {
  if (quantity <= 0) return 'negative';
  if (quantity < 10) return 'warning';
  return 'positive';
};

const vitalsForm = reactive({
  encounter_id: null,
  vitals_id: null, // ID of existing vitals if updating
  bp: '',
  temperature: null,
  pulse: null,
  respiration: null,
  weight: null,
  height: null,
  bmi: null,
  spo2: null,
  rbs: null,
  fbs: null,
  upt: null,
  rdt_malaria: null,
  retro_rdt: null,
  remarks: '',
});

const onSubmit = async () => {
  if (!vitalsForm.encounter_id) {
    $q.notify({
      type: 'warning',
      message: 'Please select an encounter first',
    });
    return;
  }

  // No validation check - allow saving even if RDT is recorded but not debited
  // The visual banner and auto-selection will remind users to debit before saving

  saving.value = true;
  try {
    // Prepare form data (exclude vitals_id from payload - backend handles create/update automatically)
    const { vitals_id, ...createData } = vitalsForm;
    
    // Backend create endpoint handles both create and update automatically
    await vitalsAPI.create(createData);
    
    $q.notify({ 
      type: 'positive', 
      message: vitals_id ? 'Vitals updated successfully' : 'Vitals recorded successfully',
      position: 'top'
    });
    
    closeVitalsDialog();
    await loadEncounters(); // Reload encounters to update vitals status
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to save vitals',
      position: 'top'
    });
  } finally {
    saving.value = false;
  }
};

// Auto-load encounter from route query parameter
const autoLoadFromRoute = async () => {
  if (route.query.encounterId) {
    const encounterId = parseInt(route.query.encounterId);
    
    try {
      // Get encounter details
      const encounterResponse = await encountersAPI.get(encounterId);
      const encounter = encounterResponse.data;
      
      if (encounter) {
        // Set the date to the encounter's date
        const encounterDate = new Date(encounter.created_at);
        const dateStr = encounterDate.toISOString().split('T')[0];
        selectedDate.value = dateStr;
        
        // Load encounters for that date
        await loadEncounters();
        
        // Find the specific encounter in the loaded list
        const foundEncounter = encounters.value.find(e => e.id === encounterId);
        
        if (foundEncounter) {
          // Automatically open the vitals dialog for this encounter
          await recordVitals(foundEncounter);
        } else {
          $q.notify({
            type: 'warning',
            message: 'Encounter found but not in the encounters list for that date',
          });
        }
      }
    } catch (error) {
      console.error('Failed to auto-load from route:', error);
      $q.notify({
        type: 'warning',
        message: 'Failed to load encounter details',
      });
      // Still set today's date so the page is usable
      setToday();
    }
  } else {
    // No encounterId in route, set today's date normally
    setToday();
  }
};

// Watch for route query changes
watch(() => route.query.encounterId, (newEncounterId) => {
  if (newEncounterId) {
    autoLoadFromRoute();
  }
});

const openBillItemsDialog = async () => {
  if (!selectedEncounter.value || !selectedEncounter.value.id) {
    $q.notify({ type: 'warning', message: 'No encounter selected', position: 'top' });
    return;
  }
  
  showBillItemsDialog.value = true;
  loadingBillItems.value = true;
  allBillItems.value = [];
  
  try {
    // Show only bill items for the selected encounter (the amount shown is for this encounter)
    const selectedEncounterId = selectedEncounter.value.id;
    
    // Load bills and bill items for this specific encounter only
    const billItemsList = [];
    
    try {
      const billsResponse = await billingAPI.getEncounterBills(selectedEncounterId);
      const bills = Array.isArray(billsResponse.data) ? billsResponse.data : [];
      
      for (const bill of bills) {
        try {
          const billDetailsResponse = await billingAPI.getBillDetails(bill.id);
          const billDetails = billDetailsResponse.data?.data || billDetailsResponse.data || {};
          const billItems = billDetails.bill_items || [];
          
          for (const item of billItems) {
            const amountPaid = (item.amount_paid !== undefined && item.amount_paid !== null) ? item.amount_paid : 0;
            const totalPrice = (item.total_price !== undefined && item.total_price !== null) ? item.total_price : 0;
            const remainingBalance = (item.remaining_balance !== undefined && item.remaining_balance !== null)
              ? item.remaining_balance 
              : (totalPrice - amountPaid);
            const isPaid = remainingBalance <= 0.01;
            
            billItemsList.push({
              id: item.id,
              encounter_id: selectedEncounterId,
              item_name: item.item_name || 'N/A',
              category: item.category || 'N/A',
              quantity: item.quantity || 0,
              unit_price: item.unit_price || 0,
              total_price: totalPrice,
              amount_paid: amountPaid,
              remaining_balance: remainingBalance,
              is_paid: isPaid,
            });
          }
        } catch (error) {
          console.error(`Failed to load bill details for bill ${bill.id}:`, error);
        }
      }
    } catch (error) {
      console.error(`Failed to load bills for encounter ${selectedEncounterId}:`, error);
    }
    
    // Sort by item name
    billItemsList.sort((a, b) => {
      return (a.item_name || '').localeCompare(b.item_name || '');
    });
    
    allBillItems.value = billItemsList;
  } catch (error) {
    console.error('Error loading bill items:', error);
    $q.notify({ 
      type: 'negative', 
      message: 'Failed to load bill items', 
      position: 'top' 
    });
  } finally {
    loadingBillItems.value = false;
  }
};

// Load departments to check their type
const loadDepartments = async () => {
  try {
    const response = await wardsAPI.getAll(false); // Get all departments including inactive
    departments.value = response.data || [];
  } catch (error) {
    console.warn('Failed to load departments:', error);
    departments.value = [];
  }
};

onMounted(() => {
  loadDepartments();
  autoLoadFromRoute();
});
</script>

<style scoped>
.vitals-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.95rem;
}
.toolbar-meta {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  color: var(--hms-text-muted);
  font-size: var(--hms-text-sm);
  font-weight: 600;
}
.toolbar-controls {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}
.tool-input {
  height: 2.15rem;
  border-radius: var(--hms-radius-lg);
  border: 1px solid var(--hms-border);
  background: var(--hms-panel-bg);
  color: var(--hms-text-primary);
  font-family: inherit;
  font-size: var(--hms-text-sm);
  padding: 0 0.7rem;
}
.patient-cell { display: flex; align-items: center; gap: 0.7rem; min-width: 0; }
.avatar {
  width: 2.15rem; height: 2.15rem; border-radius: 9999px;
  background: linear-gradient(145deg, var(--hms-accent-muted), rgba(219, 39, 119, 0.14));
  color: var(--hms-accent); display: inline-flex; align-items: center; justify-content: center;
  font-size: 0.68rem; font-weight: 750; flex-shrink: 0;
}
.name { font-weight: 700; color: var(--hms-text-primary); }
.sub { margin-top: 0.1rem; font-size: var(--hms-text-xs); color: var(--hms-text-muted); }
.mono { font-family: var(--hms-font-mono); font-size: 0.75rem; }
.vitals-dialog-head { border-bottom: 1px solid var(--hms-border); }
.dialog-title { font-size: var(--hms-text-xl); font-weight: 750; color: var(--hms-text-primary); }
.dialog-sub { margin-top: 0.2rem; font-size: var(--hms-text-sm); color: var(--hms-text-muted); }
.vitals-debit-section {
  border-top: 1px solid var(--hms-border);
  padding-top: 1rem;
}
.debit-title { font-size: var(--hms-text-base); font-weight: 750; color: var(--hms-text-primary); }
.debit-sub { margin: 0.2rem 0 0.75rem; font-size: var(--hms-text-xs); color: var(--hms-text-muted); }
.debit-banner {
  margin-bottom: 0.65rem;
  padding: 0.65rem 0.8rem;
  border-radius: var(--hms-radius-lg);
  font-size: var(--hms-text-sm);
  border: 1px solid var(--hms-border);
}
.debit-banner--warn {
  background: var(--hms-warning-muted);
  border-color: rgba(245, 158, 11, 0.3);
  color: var(--hms-text-primary);
}
.debit-banner--info {
  background: var(--hms-accent-muted);
  border-color: rgba(59, 130, 246, 0.22);
  color: var(--hms-text-secondary);
}
@media (max-width: 720px) {
  .toolbar-controls { width: 100%; }
  .tool-input { flex: 1; min-width: 0; }
}
</style>
