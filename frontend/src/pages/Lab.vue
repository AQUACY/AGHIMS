<template>
  <q-page class="q-pa-md">
    <div class="text-h4 q-mb-md text-weight-bold glass-text">Lab Services</div>

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

        <!-- Age and Sex Section -->
        <div class="row q-gutter-md q-mb-md">
          <div class="col-12 col-md-3">
            <div class="text-caption text-grey-7">Age</div>
            <div class="text-body1 text-weight-medium">{{ patient.age || 'N/A' }}</div>
          </div>
          <div class="col-12 col-md-3">
            <div class="text-caption text-grey-7">Sex</div>
            <div class="text-body1 text-weight-medium">{{ patient.gender || 'N/A' }}</div>
          </div>
          <div class="col-12 col-md-3">
            <div class="text-caption text-grey-7">Date of Birth</div>
            <div class="text-body1 text-weight-medium">{{ formatDateOnly(patient.date_of_birth) }}</div>
          </div>
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

    <!-- Consultation Diagnoses -->
    <q-card v-if="selectedEncounterId && diagnoses.length > 0" class="q-mb-md glass-card" flat>
      <q-card-section>
        <div class="text-h6 q-mb-md glass-text">Consultation Diagnoses</div>
        <div class="q-gutter-sm">
          <q-chip
            v-for="diagnosis in diagnoses"
            :key="diagnosis.id"
            :color="diagnosis.is_chief ? 'primary' : 'secondary'"
            text-color="white"
            :label="diagnosis.is_chief ? `${diagnosis.icd10 || diagnosis.diagnosis} (Chief)` : (diagnosis.icd10 || diagnosis.diagnosis)"
            size="md"
          >
            <q-tooltip v-if="diagnosis.icd10">
              ICD-10: {{ diagnosis.icd10 }} - {{ diagnosis.diagnosis }}
            </q-tooltip>
            <q-tooltip v-else>
              {{ diagnosis.diagnosis }}
              {{ diagnosis }}
            </q-tooltip>
          </q-chip>
        </div>
      </q-card-section>
    </q-card>

    <!-- Investigations Table -->
    <q-card v-if="selectedEncounterId" class="q-mb-md">
          <q-card-section>
        <div class="row items-center q-mb-md">
          <div class="text-h6">Lab Investigations</div>
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
                  size="sm"
                  color="info"
                  icon="visibility"
                  flat
                  round
                  @click="viewRemarks(props.row)"
                >
                  <q-tooltip>View Remarks/Notes</q-tooltip>
                </q-btn>
                <q-btn
                  v-if="props.row.status !== 'confirmed' && props.row.status !== 'completed'"
                  size="sm"
                  color="primary"
                  label="Confirm"
                  @click="confirmInvestigation(props.row)"
                  :loading="confirmingId === props.row.id"
                  :disable="confirmingId !== null"
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
          No lab investigations found for this encounter
        </div>
      </q-card-section>
    </q-card>

    <!-- Lab Results Table -->
    <q-card v-if="selectedEncounterId && confirmedInvestigations.length > 0" class="q-mb-md">
      <q-card-section>
        <div class="text-h6 q-mb-md">Lab Results</div>
        <q-table
          :rows="labResults"
          :columns="labResultColumns"
          row-key="investigation_id"
          flat
          :loading="loadingResults"
        >
          <template v-slot:body-cell-actions="props">
            <q-td :props="props">
              <div class="row q-gutter-xs">
                <q-btn
                  size="sm"
                  color="info"
                  icon="visibility"
                  flat
                  round
                  @click="viewRemarksForLabResult(props.row)"
                >
                  <q-tooltip>View Remarks/Notes</q-tooltip>
                </q-btn>
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
                  round
                  @click="downloadAttachment(props.row)"
                >
                  <q-tooltip>Download Attachment</q-tooltip>
                </q-btn>
              </div>
            </q-td>
          </template>
        </q-table>
      </q-card-section>
    </q-card>

    <!-- Lab Result Dialog -->
    <q-dialog v-model="showResultDialog">
      <q-card style="min-width: 600px; max-width: 800px">
        <q-card-section>
          <div class="text-h6">
            {{ editingResult ? 'Edit Lab Result' : 'Add Lab Result' }}
          </div>
          <div class="text-subtitle2 text-grey-7 q-mt-xs" v-if="selectedInvestigation">
            {{ selectedInvestigation.procedure_name || 'Lab Investigation' }} ({{ selectedInvestigation.gdrg_code }})
          </div>
        </q-card-section>

        <q-card-section>
          <q-form @submit="saveLabResult" class="q-gutter-md">
            <q-input
              v-model="resultForm.results_text"
              filled
              type="textarea"
              rows="6"
              label="Results Text"
              hint="Enter lab results from analyzer"
            />
            <q-file
              v-model="resultForm.attachment"
              filled
              label="Upload PDF/Attachment"
              accept=".pdf,.jpg,.jpeg,.png"
              hint="Upload PDF or image file from analyzer"
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

    <!-- View Remarks Dialog -->
    <q-dialog v-model="showRemarksDialog">
      <q-card style="min-width: 400px; max-width: 600px">
        <q-card-section>
          <div class="text-h6">Remarks / Notes</div>
          <div class="text-subtitle2 text-grey-7 q-mt-xs" v-if="viewingRemarks">
            {{ viewingRemarks?.procedure_name || 'Investigation' }} ({{ viewingRemarks?.gdrg_code }})
          </div>
        </q-card-section>
        <q-card-section>
          <div v-if="viewingRemarks?.notes" class="text-body1 q-pa-md" style="background-color: #f5f5f5; border-radius: 4px; white-space: pre-wrap;">
            {{ viewingRemarks.notes }}
          </div>
          <div v-else class="text-grey-6 text-center q-pa-md">
            No remarks/notes provided for this investigation
          </div>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn label="Close" color="primary" flat v-close-popup />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue';
import { useRoute } from 'vue-router';
import { useQuasar } from 'quasar';
import { consultationAPI, patientsAPI, encountersAPI, billingAPI } from '../services/api';

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
const diagnoses = ref([]);
const loadingInvestigations = ref(false);
const confirmingId = ref(null);
const labResults = ref([]);
const loadingResults = ref(false);
const showResultDialog = ref(false);
const savingResult = ref(false);
const editingResult = ref(false);
const selectedInvestigation = ref(null);
const resultForm = ref({
  investigation_id: null,
  results_text: '',
  attachment: null,
  existingAttachment: null,
});
const showRemarksDialog = ref(false);
const viewingRemarks = ref(null);

const investigationColumns = [
  { name: 'procedure_name', label: 'Procedure', field: 'procedure_name', align: 'left' },
  { name: 'gdrg_code', label: 'G-DRG Code', field: 'gdrg_code', align: 'left' },
  { name: 'investigation_type', label: 'Type', field: 'investigation_type', align: 'left' },
  { name: 'status', label: 'Status', field: 'status', align: 'center' },
  { name: 'actions', label: 'Actions', align: 'center' },
];

const labResultColumns = [
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

const canAddResults = (row) => {
  // Guard clause: check if row exists
  if (!row) {
    console.log('canAddResults: Row is undefined');
    return false;
  }
  
  // If results already exist (row.id exists), always allow editing
  if (row.id) {
    console.log(`canAddResults: Results exist (id: ${row.id}), allowing edit`);
    return true;
  }
  
  // Handle both investigation objects (with id) and result objects (with investigation_id)
  const investigationId = row.id || row.investigation_id;
  if (!investigationId) {
    console.log('canAddResults: Row is missing id or investigation_id', row);
    return false;
  }
  
  // Find the actual investigation object from investigations array
  const investigation = investigations.value.find(inv => inv.id === investigationId);
  if (!investigation) {
    console.log(`canAddResults: Investigation ${investigationId} not found in investigations array`);
    return false;
  }
  
  // Must be confirmed before adding results
  if (investigation.status !== 'confirmed' && investigation.status !== 'completed') {
    console.log(`canAddResults: Investigation ${investigation.id} not confirmed/completed`);
    return false;
  }
  
  console.log(`canAddResults: Checking investigation ${investigation.id}`, {
    gdrg_code: investigation.gdrg_code,
    procedure_name: investigation.procedure_name,
    total_bills: bills.value.length
  });
  
  // Find bill item for this specific investigation
  // Check ALL bills (paid or unpaid) to find the specific item for this service
  for (const bill of bills.value) {
    console.log(`canAddResults: Checking bill ${bill.id}, items: ${bill.bill_items?.length || 0}`);
    for (const billItem of bill.bill_items || []) {
      // Match by gdrg_code or procedure name
      // Bill items for investigations are named like "Investigation: {procedure_name}"
      const matchesCode = billItem.item_code === investigation.gdrg_code;
      const investigationName = investigation.procedure_name || '';
      const investigationCode = investigation.gdrg_code || '';
      const matchesName = billItem.item_name && (
        billItem.item_name.includes(investigationName) ||
        billItem.item_name.includes(investigationCode) ||
        billItem.item_name.includes(`Investigation: ${investigationName}`) ||
        billItem.item_name.includes(`Investigation: ${investigationCode}`)
      );
      
      console.log(`canAddResults: Checking bill item`, {
        item_code: billItem.item_code,
        item_name: billItem.item_name,
        investigation_gdrg: investigation.gdrg_code,
        investigation_name: investigation.procedure_name,
        matchesCode,
        matchesName
      });
      
      if (matchesCode || matchesName) {
        // Found matching bill item - check if THIS SPECIFIC item is paid
        const totalPrice = billItem.total_price || 0;
        const remainingBalance = billItem.remaining_balance !== undefined && billItem.remaining_balance !== null
          ? billItem.remaining_balance 
          : (totalPrice - (billItem.amount_paid || 0));
        // Item is paid if is_paid flag is true OR remaining balance is 0 or less (allow small rounding differences)
        const isPaid = billItem.is_paid !== undefined 
          ? billItem.is_paid 
          : (remainingBalance <= 0.01); // Allow 0.01 tolerance for rounding
        
        console.log(`canAddResults: Found matching bill item for investigation ${investigation.id}:`, {
          totalPrice,
          amount_paid: billItem.amount_paid,
          remaining_balance: billItem.remaining_balance,
          calculated_remaining: remainingBalance,
          is_paid_flag: billItem.is_paid,
          calculated_is_paid: isPaid,
          final_decision: isPaid ? 'PAID' : 'UNPAID'
        });
        
        // Can add results if:
        // 1. Total price is 0 (free), OR
        // 2. Item is paid (remaining balance <= 0.01 or is_paid flag is true)
        if (totalPrice > 0 && !isPaid) {
          console.log(`canAddResults: Returning FALSE - unpaid balance for investigation ${investigation.id}`);
          return false; // This specific item has unpaid balance
        } else {
          console.log(`canAddResults: Returning TRUE - investigation ${investigation.id} is paid or free`);
          return true; // This specific item is paid or free
        }
      }
    }
  }
  
  console.log(`canAddResults: No bill item found for investigation ${investigation.id}, allowing results`);
  // If no bill item found for this investigation, allow adding results
  // (might be free or bill not created yet - backend will enforce)
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
    selectedEncounterId.value = null;
    investigations.value = [];
    diagnoses.value = [];
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
    
    // Load diagnoses for this encounter
    try {
      const diagnosesResponse = await consultationAPI.getDiagnoses(selectedEncounterId.value);
      diagnoses.value = diagnosesResponse.data || [];
    } catch (error) {
      console.error('Failed to load diagnoses:', error);
      diagnoses.value = [];
    }
    
    // Load investigations (filter by lab type)
    const response = await consultationAPI.getInvestigationsByPatientCard(
      patient.value.card_number,
      selectedEncounterId.value,
      'lab'
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
            // Use backend's remaining_balance directly, but also calculate as fallback
            const billItems = (billDetails.bill_items || []).map(item => {
              try {
                const amountPaid = (item.amount_paid !== undefined && item.amount_paid !== null) ? item.amount_paid : 0;
                const totalPrice = (item.total_price !== undefined && item.total_price !== null) ? item.total_price : 0;
                // Use backend's remaining_balance if available, otherwise calculate
                const remainingBalance = (item.remaining_balance !== undefined && item.remaining_balance !== null)
                  ? item.remaining_balance 
                  : (totalPrice - amountPaid);
                
                // Item is paid if remaining balance is 0 or less (allow small rounding differences)
                const isPaid = remainingBalance <= 0.01; // Allow 0.01 tolerance for rounding
                
                return {
                  ...item,
                  amount_paid: amountPaid,
                  remaining_balance: remainingBalance,
                  is_paid: isPaid,
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

    // Load lab results for confirmed investigations (after investigations are loaded)
    await loadLabResults();
  } catch (error) {
    investigations.value = [];
    labResults.value = [];
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to load investigations',
    });
  } finally {
    loadingInvestigations.value = false;
  }
};

const loadLabResults = async () => {
  if (!selectedEncounterId.value || confirmedInvestigations.value.length === 0) {
    labResults.value = [];
    return;
  }

  loadingResults.value = true;
  try {
    // Load lab results for confirmed investigations
    labResults.value = await Promise.all(
      confirmedInvestigations.value.map(async (inv) => {
        try {
          const resultResponse = await consultationAPI.getLabResult(inv.id);
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
    labResults.value = [];
    console.error('Failed to load lab results:', error);
  } finally {
    loadingResults.value = false;
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

const viewRemarks = (investigation) => {
  viewingRemarks.value = investigation;
  showRemarksDialog.value = true;
};

const viewRemarksForLabResult = (labResult) => {
  // Find the investigation from the investigations array using investigation_id
  const investigation = investigations.value.find(inv => inv.id === labResult.investigation_id);
  if (investigation) {
    viewingRemarks.value = investigation;
    showRemarksDialog.value = true;
  } else {
    $q.notify({
      type: 'warning',
      message: 'Investigation details not found',
    });
  }
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

const saveLabResult = async () => {
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

    await consultationAPI.createLabResult(formData);
    $q.notify({
      type: 'positive',
      message: 'Lab result saved successfully',
    });
    showResultDialog.value = false;
    // Reload investigations and results
    await loadInvestigations();
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to save lab result',
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
    const response = await consultationAPI.downloadLabResultAttachment(result.investigation_id);
    
    // Axios with responseType: 'blob' returns data as Blob directly
    const blob = response.data instanceof Blob 
      ? response.data 
      : new Blob([response.data], { 
          type: response.headers['content-type'] || 'application/pdf' 
        });
    
    // Get filename from Content-Disposition header or use attachment path
    const contentDisposition = response.headers['content-disposition'] || 
                                response.headers['Content-Disposition'];
    let filename = result.attachment_path.split('/').pop() || 'lab_result.pdf';
    
    if (contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
      if (filenameMatch && filenameMatch[1]) {
        filename = filenameMatch[1].replace(/['"]/g, '');
      }
    }
    
    // Create download link
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    
    // Clean up
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

const formatDateOnly = (dateString) => {
  if (!dateString) return 'N/A';
  const date = new Date(dateString);
  return date.toLocaleDateString('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric'
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
  
  // Fetch investigations asynchronously
  consultationAPI.getInvestigations(encounter.id)
    .then(response => {
      const investigations = response.data || [];
      const procedureNames = investigations
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
  currentEncounter.value = null;
  investigations.value = [];
  diagnoses.value = [];
  labResults.value = [];
  encounterProceduresCache.value.clear();
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

// Auto-load on mount
onMounted(() => {
  autoLoadFromRoute();
});
</script>
