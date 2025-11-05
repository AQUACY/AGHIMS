<template>
  <q-page class="q-pa-md">
    <div class="text-h4 q-mb-md text-weight-bold glass-text">X-ray Services</div>

    <!-- Patient Search -->
    <q-card class="q-mb-md glass-card" flat>
      <q-card-section>
        <div class="text-h6 q-mb-md glass-text">Search Patient</div>
        <div class="row q-gutter-md">
          <q-input
            v-model="cardNumber"
            filled
            label="Patient Card Number"
            class="col-12 col-md-8"
            @keyup.enter="searchPatient"
            :disable="loadingPatient"
          />
          <q-btn
            color="primary"
            label="Search"
            @click="searchPatient"
            class="col-12 col-md-4 glass-button"
            :loading="loadingPatient"
          />
        </div>
      </q-card-section>
    </q-card>

    <!-- Patient Info & Encounter Selection -->
    <q-card v-if="patient" class="q-mb-md glass-card" flat>
      <q-card-section>
        <div class="row items-center q-mb-md">
          <div>
            <div class="text-h6 glass-text">{{ patient.name }} {{ patient.surname || '' }}</div>
            <div class="text-grey-7">Card: {{ patient.card_number }}</div>
          </div>
          <q-space />
          <q-btn
            flat
            icon="refresh"
            label="Clear"
            @click="clearSearch"
          />
        </div>

        <!-- Today's Encounter -->
        <div v-if="todaysEncounter" class="q-mt-md">
          <div class="text-subtitle1 q-mb-sm glass-text">Today's Encounter:</div>
          <q-card class="q-mb-md" flat bordered style="background-color: rgba(46, 139, 87, 0.1);">
            <q-card-section>
              <div class="row items-center">
                <div class="col">
                  <div class="text-weight-bold">Encounter #{{ todaysEncounter.id }} - {{ getEncounterProcedures(todaysEncounter) }}</div>
                  <div class="text-caption text-grey-7 q-mt-xs">
                    {{ formatDate(todaysEncounter.created_at) }} - Status: {{ todaysEncounter.status }}
        </div>
                </div>
                <q-badge color="green" label="Today" />
              </div>
            </q-card-section>
          </q-card>
        </div>

        <!-- Old Encounters - Collapsible -->
        <div v-if="oldEncounters.length > 0" class="q-mt-md">
          <q-expansion-item
            v-model="oldEncountersExpanded"
            icon="history"
            :label="`Previous Services (${oldEncounters.length})`"
            header-class="text-subtitle1 glass-text"
            class="q-mb-sm"
          >
            <div class="q-gutter-sm q-pa-sm">
              <q-card
                v-for="encounter in oldEncounters"
                :key="encounter.id"
                flat
                bordered
                clickable
                :class="{ 'bg-blue-1': selectedEncounterId === encounter.id }"
                @click="selectOldEncounter(encounter.id)"
                style="cursor: pointer;"
              >
                <q-card-section class="q-pa-sm">
                  <div class="row items-center">
                    <div class="col">
                      <div class="text-weight-medium">Encounter #{{ encounter.id }} - {{ getEncounterProcedures(encounter) }}</div>
                      <div class="text-caption text-grey-7 q-mt-xs">
                        {{ formatDate(encounter.created_at) }} - Status: {{ encounter.status }}
                      </div>
                    </div>
                    <q-icon name="chevron_right" color="grey-6" />
                  </div>
                </q-card-section>
              </q-card>
            </div>
          </q-expansion-item>
        </div>

        <div v-if="!todaysEncounter && oldEncounters.length === 0" class="text-grey-7 q-mt-md">
          No active encounters found for this patient
        </div>
      </q-card-section>
    </q-card>

    <!-- Investigations Table -->
    <q-card v-if="selectedEncounterId" class="q-mb-md">
      <q-card-section>
        <div class="row items-center q-mb-md">
          <div class="text-h6">X-ray Investigations</div>
          <q-space />
          <q-badge v-if="isFinalized" color="orange" label="Encounter Finalized" />
        </div>
        <q-table
          v-if="investigations.length > 0"
          :rows="investigations"
          :columns="investigationColumns"
          row-key="id"
          flat
          :loading="loadingInvestigations"
        >
          <template v-slot:body-cell-status="props">
            <q-td :props="props">
              <q-badge
                :color="getStatusColor(props.value)"
                :label="props.value"
              />
            </q-td>
          </template>
          <template v-slot:body-cell-actions="props">
            <q-td :props="props">
              <div class="row q-gutter-xs">
                <q-btn
                  v-if="props.row.status !== 'confirmed' && props.row.status !== 'completed'"
                  size="sm"
                  color="secondary"
                  icon="edit"
                  label="Edit"
                  @click="openEditInvestigationDialog(props.row)"
                  :loading="updatingId === props.row.id"
                  :disable="confirmingId !== null"
                />
                <q-btn
                  v-if="props.row.status !== 'confirmed' && props.row.status !== 'completed'"
                  size="sm"
                  color="primary"
                  label="Confirm"
                  @click="confirmInvestigation(props.row)"
                  :loading="confirmingId === props.row.id"
                  :disable="confirmingId !== null || updatingId !== null"
                />
                <q-badge
                  v-else
                  color="positive"
                  label="Confirmed"
                />
              </div>
            </q-td>
          </template>
        </q-table>
        <div v-else-if="!loadingInvestigations" class="text-center text-grey-7 q-pa-md">
          No x-ray investigations found for this encounter
        </div>
      </q-card-section>
    </q-card>

    <!-- X-ray Results Table -->
    <q-card v-if="selectedEncounterId && confirmedInvestigations.length > 0" class="q-mb-md">
      <q-card-section>
        <div class="text-h6 q-mb-md">X-ray Results</div>
        <q-table
          :rows="xrayResults"
          :columns="xrayResultColumns"
          row-key="investigation_id"
          flat
          :loading="loadingResults"
        >
          <template v-slot:body-cell-actions="props">
            <q-td :props="props">
              <q-btn
                size="sm"
                color="primary"
                :label="props.row.id ? 'Edit' : 'Add Results'"
                @click="openResultDialog(props.row)"
                :disable="!canAddResults(props.row)"
              >
                <q-tooltip v-if="!canAddResults(props.row)">
                  Bill must be paid before adding results
                </q-tooltip>
                <q-tooltip v-else>
                  {{ props.row.id ? 'Edit results' : 'Add results' }}
                </q-tooltip>
              </q-btn>
              <q-btn
                v-if="props.row.attachment_path"
                size="sm"
                color="secondary"
                icon="download"
                flat
                @click="downloadAttachment(props.row)"
                class="q-ml-xs"
              />
            </q-td>
          </template>
        </q-table>
      </q-card-section>
    </q-card>

    <!-- Edit Investigation Dialog -->
    <q-dialog v-model="showEditInvestigationDialog">
      <q-card style="min-width: 600px; max-width: 800px">
        <q-card-section>
          <div class="text-h6">Edit Investigation Details</div>
          <div class="text-subtitle2 text-grey-7 q-mt-xs">
            You can change the procedure/service based on patient condition
          </div>
        </q-card-section>

        <q-card-section>
          <q-form @submit="updateInvestigation" class="q-gutter-md">
            <q-select
              v-model="editInvestigationForm.service_type"
              filled
              :options="serviceTypeOptions"
              label="Service Type (Department/Clinic) *"
              @update:model-value="onServiceTypeSelected"
              hint="Select the department/clinic"
              :loading="loadingServiceTypes"
            >
              <template v-slot:no-option>
                <q-item>
                  <q-item-section class="text-grey">
                    No service types found
                  </q-item-section>
                </q-item>
              </template>
            </q-select>
            
            <q-select
              v-model="selectedProcedure"
              filled
              :options="procedureOptions"
              label="Procedure (Service Name) *"
              option-label="service_name"
              option-value="g_drg_code"
              :disable="!editInvestigationForm.service_type"
              @update:model-value="onProcedureSelected"
              hint="Select the procedure - GDRG code and name will be auto-filled"
              use-input
              input-debounce="300"
              @filter="filterProcedures"
            >
              <template v-slot:no-option>
                <q-item>
                  <q-item-section class="text-grey">
                    {{ editInvestigationForm.service_type
                      ? 'No procedures found. Try a different search term.'
                      : 'Please select a Service Type first'
                    }}
                  </q-item-section>
                </q-item>
              </template>
            </q-select>
            
            <q-input
              v-model="editInvestigationForm.gdrg_code"
              filled
              label="G-DRG Code *"
              :rules="[(val) => !!val || 'G-DRG Code is required']"
            />
            <q-input
              v-model="editInvestigationForm.procedure_name"
              filled
              label="Procedure Name *"
              :rules="[(val) => !!val || 'Procedure name is required']"
            />
            
            <div class="row q-gutter-md q-mt-md">
              <q-btn label="Cancel" flat v-close-popup class="col" />
              <q-btn
                label="Update"
                type="submit"
                color="primary"
                class="col"
                :loading="updatingInvestigation"
              />
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- X-ray Result Dialog -->
    <q-dialog v-model="showResultDialog">
      <q-card style="min-width: 600px; max-width: 800px">
        <q-card-section>
          <div class="text-h6">
            {{ editingResult ? 'Edit X-ray Result' : 'Add X-ray Result' }}
          </div>
          <div class="text-subtitle2 text-grey-7 q-mt-xs" v-if="selectedInvestigation">
            {{ selectedInvestigation.procedure_name || 'X-ray Investigation' }} ({{ selectedInvestigation.gdrg_code }})
          </div>
        </q-card-section>

        <q-card-section>
          <q-form @submit="saveXrayResult" class="q-gutter-md">
            <q-input
              v-model="resultForm.results_text"
              filled
              type="textarea"
              rows="6"
              label="Results/Findings Text"
              hint="Enter x-ray results and findings"
            />
            <q-file
              v-model="resultForm.attachment"
              filled
              label="Upload PDF/Image Attachment"
              accept=".pdf,.jpg,.jpeg,.png"
              hint="Upload PDF or image file"
              @update:model-value="onFileSelected"
            >
              <template v-slot:prepend>
                <q-icon name="attach_file" />
              </template>
            </q-file>
            <div v-if="resultForm.existingAttachment" class="text-caption text-grey-7">
              Current attachment: {{ resultForm.existingAttachment.split('/').pop() }}
            </div>
            <div class="row q-gutter-md q-mt-md">
              <q-btn label="Cancel" flat v-close-popup class="col" />
              <q-btn
                label="Save"
                type="submit"
                color="primary"
                class="col"
                :loading="savingResult"
              />
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue';
import { useRoute } from 'vue-router';
import { useQuasar } from 'quasar';
import { consultationAPI, patientsAPI, encountersAPI, priceListAPI, billingAPI } from '../services/api';

const $q = useQuasar();
const route = useRoute();
const cardNumber = ref('');
const loadingPatient = ref(false);
const patient = ref(null);
const activeEncounters = ref([]);
const todaysEncounter = ref(null);
const oldEncounters = ref([]);
const oldEncountersExpanded = ref(false);
const selectedEncounterId = ref(null);
const currentEncounter = ref(null);
const investigations = ref([]);
const loadingInvestigations = ref(false);
const confirmingId = ref(null);
const updatingId = ref(null);
const xrayResults = ref([]);
const loadingResults = ref(false);
const showResultDialog = ref(false);
const savingResult = ref(false);
const editingResult = ref(false);
const selectedInvestigation = ref(null);
const showEditInvestigationDialog = ref(false);
const updatingInvestigation = ref(false);
const loadingServiceTypes = ref(false);
const serviceTypeOptions = ref([]);
const procedureOptions = ref([]);
const allProcedures = ref([]);
const selectedProcedure = ref(null);

const resultForm = ref({
  investigation_id: null,
  results_text: '',
  attachment: null,
  existingAttachment: null,
});

const editInvestigationForm = ref({
  investigation_id: null,
  gdrg_code: '',
  procedure_name: '',
  service_type: '',
});

const investigationColumns = [
  { name: 'procedure_name', label: 'Procedure', field: 'procedure_name', align: 'left' },
  { name: 'gdrg_code', label: 'G-DRG Code', field: 'gdrg_code', align: 'left' },
  { name: 'investigation_type', label: 'Type', field: 'investigation_type', align: 'left' },
  { name: 'status', label: 'Status', field: 'status', align: 'center' },
  { name: 'actions', label: 'Actions', align: 'center' },
];

const xrayResultColumns = [
  { name: 'procedure_name', label: 'Procedure', field: 'procedure_name', align: 'left' },
  { name: 'gdrg_code', label: 'G-DRG Code', field: 'gdrg_code', align: 'left' },
  { name: 'has_result', label: 'Has Results', field: 'has_result', align: 'center' },
  { name: 'has_attachment', label: 'Has Attachment', field: 'has_attachment', align: 'center' },
  { name: 'actions', label: 'Actions', align: 'center' },
];

const getStatusColor = (status) => {
  const colors = {
    requested: 'orange',
    confirmed: 'blue',
    completed: 'green',
  };
  return colors[status] || 'grey';
};

const confirmedInvestigations = computed(() => {
  return investigations.value.filter(inv => inv.status === 'confirmed' || inv.status === 'completed');
});

const isFinalized = computed(() => {
  return currentEncounter.value?.status === 'finalized';
});

const canAddResults = (investigation) => {
  // Must be confirmed before adding results
  if (investigation.status !== 'confirmed' && investigation.status !== 'completed') {
    return false;
  }
  
  // Find bill item for this investigation
  for (const bill of bills.value) {
    // Skip paid bills entirely
    if (bill.is_paid) continue;
    
    for (const billItem of bill.bill_items || []) {
      // Match by gdrg_code or procedure name
      const matchesCode = billItem.item_code === investigation.gdrg_code;
      const matchesName = billItem.item_name && (
        billItem.item_name.includes(investigation.procedure_name || '') ||
        billItem.item_name.includes(investigation.gdrg_code || '')
      );
      
      if (matchesCode || matchesName) {
        // If there's a bill item with a price > 0, check if it's paid
        const totalPrice = billItem.total_price || 0;
        const remainingBalance = billItem.remaining_balance !== undefined 
          ? billItem.remaining_balance 
          : (totalPrice - (billItem.amount_paid || 0));
        
        // Can only add results if:
        // 1. Total price is 0 (free), OR
        // 2. Remaining balance is 0 or less (fully paid)
        if (totalPrice > 0 && remainingBalance > 0) {
          return false; // Has unpaid balance
        }
      }
    }
  }
  
  // If no bill found, allow adding results (backend will enforce payment check)
  return true;
};

const searchPatient = async () => {
  if (!cardNumber.value || !cardNumber.value.trim()) {
    $q.notify({
      type: 'warning',
      message: 'Please enter a card number',
    });
    return;
  }

  loadingPatient.value = true;
  try {
    const patientResponse = await patientsAPI.getByCard(cardNumber.value.trim());
    
    // getByCard returns a list of patients
    let patients = [];
    if (Array.isArray(patientResponse.data)) {
      patients = patientResponse.data;
    } else if (patientResponse.data && typeof patientResponse.data === 'object' && !Array.isArray(patientResponse.data)) {
      patients = [patientResponse.data];
    }
    
    if (patients.length === 0) {
      $q.notify({
        type: 'info',
        message: 'No patients found with that card number',
      });
      return;
    }
    
    // Use the first patient (or exact match if available)
    patient.value = patients[0];

    const encountersResponse = await encountersAPI.getPatientEncounters(patient.value.id);
    const allEncounters = encountersResponse.data.filter(e => !e.archived);
    
    // Separate today's encounter from old encounters
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    
    const todaysEncounters = allEncounters.filter(e => {
      const encounterDate = new Date(e.created_at);
      encounterDate.setHours(0, 0, 0, 0);
      return encounterDate.getTime() === today.getTime();
    });
    
    const oldEncs = allEncounters.filter(e => {
      const encounterDate = new Date(e.created_at);
      encounterDate.setHours(0, 0, 0, 0);
      return encounterDate.getTime() !== today.getTime();
    }).sort((a, b) => new Date(b.created_at) - new Date(a.created_at)); // Sort newest first
    
    // Set today's encounter (use the most recent one if multiple)
    if (todaysEncounters.length > 0) {
      todaysEncounter.value = todaysEncounters.sort((a, b) => new Date(b.created_at) - new Date(a.created_at))[0];
      selectedEncounterId.value = todaysEncounter.value.id;
      // Pre-fetch procedure names for today's encounter
      getEncounterProcedures(todaysEncounter.value);
      await loadInvestigations();
    } else {
      todaysEncounter.value = null;
    }
    
    // Set old encounters and pre-fetch their procedure names
    oldEncounters.value = oldEncs;
    oldEncounters.value.forEach(encounter => {
      getEncounterProcedures(encounter);
    });
    
    // Keep for backward compatibility
    activeEncounters.value = allEncounters.map(e => ({
        id: e.id,
        label: `Encounter #${e.id} - ${e.department} (${new Date(e.created_at).toLocaleDateString()})`,
        value: e.id,
      }));

    if (allEncounters.length === 0) {
      $q.notify({
        type: 'info',
        message: 'No active encounters found for this patient',
      });
    }
  } catch (error) {
    patient.value = null;
    activeEncounters.value = [];
    todaysEncounter.value = null;
    oldEncounters.value = [];
    selectedEncounterId.value = null;
    investigations.value = [];
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Patient not found',
    });
  } finally {
    loadingPatient.value = false;
  }
};

const loadInvestigations = async () => {
  if (!selectedEncounterId.value || !patient.value) return;

  loadingInvestigations.value = true;
  try {
    // Load encounter details to check status
    const encounterResponse = await encountersAPI.get(selectedEncounterId.value);
    currentEncounter.value = encounterResponse.data;
    
    // Load investigations (filter by xray type)
    const response = await consultationAPI.getInvestigationsByPatientCard(
      patient.value.card_number,
      selectedEncounterId.value,
      'xray'
    );
    investigations.value = response.data || [];

    // Load bills for this encounter to check payment status
    try {
      const billsResponse = await billingAPI.getEncounterBills(selectedEncounterId.value);
      const billsList = billsResponse.data || [];
      
      // Load detailed bill information including bill items and payment status
      const detailedBills = await Promise.all(
        billsList.map(async (bill) => {
          try {
            const billDetailsResponse = await billingAPI.getBillDetails(bill.id);
            const billDetails = billDetailsResponse.data?.data || billDetailsResponse.data || {};
            
            // Calculate remaining balance for each bill item
            const billItems = (billDetails.bill_items || []).map(item => {
              try {
                const amountPaid = (item.amount_paid !== undefined && item.amount_paid !== null) ? item.amount_paid : 0;
                const totalPrice = (item.total_price !== undefined && item.total_price !== null) ? item.total_price : 0;
                const remainingBalance = (item.remaining_balance !== undefined && item.remaining_balance !== null)
                  ? item.remaining_balance 
                  : (totalPrice - amountPaid);
                
                return {
                  ...item,
                  amount_paid: amountPaid,
                  remaining_balance: remainingBalance,
                  is_paid: remainingBalance <= 0,
                };
              } catch (itemError) {
                console.error(`Error processing bill item:`, item, itemError);
                return {
                  ...item,
                  amount_paid: 0,
                  remaining_balance: item.total_price || 0,
                  is_paid: false,
                };
              }
            });
            
            return {
              ...bill,
              bill_items: billItems,
              is_paid: bill.is_paid || false,
              paid_amount: bill.paid_amount || 0,
              total_amount: bill.total_amount || 0,
            };
          } catch (error) {
            console.error(`Failed to load details for bill ${bill.id}:`, error);
            return {
              ...bill,
              bill_items: [],
              is_paid: bill.is_paid || false,
              paid_amount: bill.paid_amount || 0,
              total_amount: bill.total_amount || 0,
            };
          }
        })
      );
      
      bills.value = detailedBills;
    } catch (error) {
      console.error('Failed to load bills:', error);
      bills.value = [];
    }

    // Load xray results for confirmed investigations
    await loadXrayResults();
  } catch (error) {
    investigations.value = [];
    xrayResults.value = [];
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to load investigations',
    });
  } finally {
    loadingInvestigations.value = false;
  }
};

const loadXrayResults = async () => {
  if (!selectedEncounterId.value || confirmedInvestigations.value.length === 0) {
    xrayResults.value = [];
    return;
  }

  loadingResults.value = true;
  try {
    xrayResults.value = await Promise.all(
      confirmedInvestigations.value.map(async (inv) => {
        try {
          const resultResponse = await consultationAPI.getXrayResult(inv.id);
          const result = resultResponse.data || null;
          
          return {
            investigation_id: inv.id,
            procedure_name: inv.procedure_name,
            gdrg_code: inv.gdrg_code,
            has_result: result ? 'Yes' : 'No',
            has_attachment: result?.attachment_path ? 'Yes' : 'No',
            ...result,
          };
        } catch (error) {
          return {
            investigation_id: inv.id,
            procedure_name: inv.procedure_name,
            gdrg_code: inv.gdrg_code,
            has_result: 'No',
            has_attachment: 'No',
          };
        }
      })
    );
  } catch (error) {
    xrayResults.value = [];
    console.error('Failed to load xray results:', error);
  } finally {
    loadingResults.value = false;
  }
};

const loadServiceTypes = async () => {
  loadingServiceTypes.value = true;
  try {
    const response = await priceListAPI.getServiceTypes();
    serviceTypeOptions.value = response.data || [];
  } catch (error) {
    console.error('Failed to load service types:', error);
    serviceTypeOptions.value = [];
  } finally {
    loadingServiceTypes.value = false;
  }
};

const onServiceTypeSelected = async (serviceType) => {
  if (!serviceType) {
    procedureOptions.value = [];
    allProcedures.value = [];
    return;
  }

  try {
    const response = await priceListAPI.getProceduresByServiceType(serviceType);
    allProcedures.value = response.data || [];
    procedureOptions.value = allProcedures.value;
  } catch (error) {
    console.error('Failed to load procedures:', error);
    allProcedures.value = [];
    procedureOptions.value = [];
  }
};

const filterProcedures = (val, update) => {
  if (val === '') {
    update(() => {
      procedureOptions.value = allProcedures.value;
    });
    return;
  }
  update(() => {
    const needle = val.toLowerCase();
    procedureOptions.value = allProcedures.value.filter(
      (p) =>
        (p.service_name && p.service_name.toLowerCase().indexOf(needle) > -1) ||
        (p.g_drg_code && p.g_drg_code.toLowerCase().indexOf(needle) > -1)
    );
  });
};

const onProcedureSelected = (gdrgCode) => {
  if (!gdrgCode) {
    editInvestigationForm.value.gdrg_code = '';
    editInvestigationForm.value.procedure_name = '';
    return;
  }
  const selected = allProcedures.value.find(p => p.g_drg_code === gdrgCode);
  if (selected) {
    editInvestigationForm.value.gdrg_code = selected.g_drg_code;
    editInvestigationForm.value.procedure_name = selected.service_name;
  }
};

const openEditInvestigationDialog = async (investigation) => {
  editInvestigationForm.value = {
    investigation_id: investigation.id,
    gdrg_code: investigation.gdrg_code,
    procedure_name: investigation.procedure_name,
    service_type: '',
  };
  selectedProcedure.value = null;
  
  // Load service types if not loaded
  if (serviceTypeOptions.value.length === 0) {
    await loadServiceTypes();
  }
  
  showEditInvestigationDialog.value = true;
};

const updateInvestigation = async () => {
  if (!editInvestigationForm.value.investigation_id) return;

  updatingInvestigation.value = true;
  updatingId.value = editInvestigationForm.value.investigation_id;
  try {
    await consultationAPI.updateInvestigationDetails(
      editInvestigationForm.value.investigation_id,
      {
        gdrg_code: editInvestigationForm.value.gdrg_code,
        procedure_name: editInvestigationForm.value.procedure_name,
      }
    );
    $q.notify({
      type: 'positive',
      message: 'Investigation updated successfully',
    });
    showEditInvestigationDialog.value = false;
    await loadInvestigations();
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to update investigation',
    });
  } finally {
    updatingInvestigation.value = false;
    updatingId.value = null;
  }
};

const confirmInvestigation = async (investigation) => {
  $q.dialog({
    title: 'Confirm Investigation',
    message: `Confirm ${investigation.procedure_name || investigation.gdrg_code}?`,
    cancel: true,
    persistent: true,
  }).onOk(async () => {
    confirmingId.value = investigation.id;
    try {
      await consultationAPI.confirmInvestigation(investigation.id);
      $q.notify({
        type: 'positive',
        message: 'Investigation confirmed',
      });
      await loadInvestigations();
    } catch (error) {
      $q.notify({
        type: 'negative',
        message: error.response?.data?.detail || 'Failed to confirm investigation',
      });
    } finally {
      confirmingId.value = null;
    }
  });
};

const openResultDialog = (result) => {
  selectedInvestigation.value = investigations.value.find(inv => inv.id === result.investigation_id);
  editingResult.value = !!result.id;
  resultForm.value = {
    investigation_id: result.investigation_id,
    results_text: result.results_text || '',
    attachment: null,
    existingAttachment: result.attachment_path || null,
  };
  showResultDialog.value = true;
};

const onFileSelected = (file) => {
  // File is automatically set in resultForm.attachment
};

const saveXrayResult = async () => {
  if (!resultForm.value.investigation_id) return;

  savingResult.value = true;
  try {
    const formData = new FormData();
    formData.append('investigation_id', resultForm.value.investigation_id);
    if (resultForm.value.results_text) {
      formData.append('results_text', resultForm.value.results_text);
    }
    if (resultForm.value.attachment) {
      formData.append('attachment', resultForm.value.attachment);
    }

    await consultationAPI.createXrayResult(formData);
    $q.notify({
      type: 'positive',
      message: 'X-ray result saved successfully',
    });
    showResultDialog.value = false;
    await loadInvestigations();
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to save x-ray result',
    });
  } finally {
    savingResult.value = false;
  }
};

const downloadAttachment = async (result) => {
  if (!result.attachment_path || !result.investigation_id) {
    $q.notify({
      type: 'warning',
      message: 'No attachment available to download',
    });
    return;
  }

  try {
    const response = await consultationAPI.downloadXrayResultAttachment(result.investigation_id);
    
    const blob = response.data instanceof Blob 
      ? response.data 
      : new Blob([response.data], { 
          type: response.headers['content-type'] || 'application/pdf' 
        });
    
    const contentDisposition = response.headers['content-disposition'] || 
                                response.headers['Content-Disposition'];
    let filename = result.attachment_path.split('/').pop() || 'xray_result.pdf';
    
    if (contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
      if (filenameMatch && filenameMatch[1]) {
        filename = filenameMatch[1].replace(/['"]/g, '');
      }
    }
    
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    
    setTimeout(() => {
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    }, 100);
    
    $q.notify({
      type: 'positive',
      message: 'File downloaded successfully',
    });
  } catch (error) {
    console.error('Download error:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to download attachment',
    });
  }
};

const selectOldEncounter = async (encounterId) => {
  selectedEncounterId.value = encounterId;
  await loadInvestigations();
};

const formatDate = (dateString) => {
  if (!dateString) return 'N/A';
  const date = new Date(dateString);
  return date.toLocaleDateString('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
};

const encounterProceduresCache = ref(new Map());
const bills = ref([]);

const getEncounterProcedures = (encounter) => {
  if (!encounter || !encounter.id) return encounter?.department || 'N/A';
  
  // Check cache first
  if (encounterProceduresCache.value.has(encounter.id)) {
    const cached = encounterProceduresCache.value.get(encounter.id);
    return cached || encounter.department || 'N/A';
  }
  
  // Set loading placeholder
  encounterProceduresCache.value.set(encounter.id, 'Loading...');
  
  // Fetch xray investigations asynchronously
  consultationAPI.getInvestigations(encounter.id)
    .then(response => {
      const investigations = response.data || [];
      const xrayInvestigations = investigations.filter(inv => inv.investigation_type === 'xray');
      const procedureNames = xrayInvestigations
        .filter(inv => inv.procedure_name)
        .map(inv => inv.procedure_name)
        .filter((name, index, self) => self.indexOf(name) === index); // Remove duplicates
      
      const displayText = procedureNames.length > 0 
        ? (procedureNames.length > 3 
          ? `${procedureNames.slice(0, 3).join(', ')}... (+${procedureNames.length - 3} more)`
          : procedureNames.join(', '))
        : (encounter.department || 'N/A');
      
      encounterProceduresCache.value.set(encounter.id, displayText);
    })
    .catch(error => {
      console.error('Failed to fetch procedures for encounter:', error);
      encounterProceduresCache.value.set(encounter.id, encounter.department || 'N/A');
    });
  
  // Return department as fallback while loading
  return encounter.department || 'N/A';
};

const clearSearch = () => {
  cardNumber.value = '';
  patient.value = null;
  activeEncounters.value = [];
  todaysEncounter.value = null;
  oldEncounters.value = [];
  oldEncountersExpanded.value = false;
  selectedEncounterId.value = null;
  encounterProceduresCache.value.clear();
  currentEncounter.value = null;
  investigations.value = [];
  xrayResults.value = [];
};

// Auto-load from route query parameter
const autoLoadFromRoute = async () => {
  if (route.query.encounterId) {
    const encounterId = parseInt(route.query.encounterId);
    selectedEncounterId.value = encounterId;
    
    try {
      // Get encounter details to get patient info
      const encounterResponse = await encountersAPI.get(encounterId);
      const encounter = encounterResponse.data;
      currentEncounter.value = encounter;
      
      if (encounter && encounter.patient_id) {
        // Get patient info
        const patientResponse = await patientsAPI.get(encounter.patient_id);
        patient.value = patientResponse.data;
        cardNumber.value = patient.value.card_number;
        
        // Load all encounters for this patient
        const encountersResponse = await encountersAPI.getPatientEncounters(encounter.patient_id);
        const allEncounters = encountersResponse.data.filter(e => !e.archived);
        
        // Separate today's encounter from old encounters
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        
        const todaysEncounters = allEncounters.filter(e => {
          const encounterDate = new Date(e.created_at);
          encounterDate.setHours(0, 0, 0, 0);
          return encounterDate.getTime() === today.getTime();
        });
        
        const oldEncs = allEncounters.filter(e => {
          const encounterDate = new Date(e.created_at);
          encounterDate.setHours(0, 0, 0, 0);
          return encounterDate.getTime() !== today.getTime();
        }).sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
        
        if (todaysEncounters.length > 0) {
          todaysEncounter.value = todaysEncounters.sort((a, b) => new Date(b.created_at) - new Date(a.created_at))[0];
        } else {
          todaysEncounter.value = null;
        }
        
        oldEncounters.value = oldEncs;
        
        activeEncounters.value = allEncounters.map(e => ({
          id: e.id,
          label: `Encounter #${e.id} - ${e.department} (${new Date(e.created_at).toLocaleDateString()})`,
          value: e.id,
        }));
        
        // Load investigations for this encounter
        await loadInvestigations();
      }
    } catch (error) {
      console.error('Failed to auto-load from route:', error);
      $q.notify({
        type: 'warning',
        message: 'Failed to load encounter details',
      });
    }
  }
};

// Watch for route query changes
watch(() => route.query.encounterId, (newEncounterId) => {
  if (newEncounterId) {
    autoLoadFromRoute();
  }
});

onMounted(() => {
  loadServiceTypes();
  autoLoadFromRoute();
});
</script>

