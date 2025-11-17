<template>
  <q-page class="q-pa-md">
    <div class="row items-center q-mb-md">
      <q-btn
        flat
        icon="arrow_back"
        label="Back to Admission Manager"
        @click="goBack"
        class="q-mr-md"
      />
      <div class="text-h5 text-weight-bold glass-text">
        Clinical Review
      </div>
    </div>

    <q-card v-if="patientInfo" class="glass-card q-mb-md" flat bordered>
      <q-card-section>
        <div class="text-h6 text-weight-bold glass-text q-mb-sm">
          Patient Information
        </div>
        <div class="row q-col-gutter-md">
          <div class="col-12 col-md-6">
            <div class="text-body2">
              <strong>Name:</strong> {{ patientInfo.patient_name }} {{ patientInfo.patient_surname }}<span v-if="patientInfo.patient_other_names"> {{ patientInfo.patient_other_names }}</span>
            </div>
            <div class="text-body2">
              <strong>Card Number:</strong> {{ patientInfo.patient_card_number }}
            </div>
          </div>
          <div class="col-12 col-md-6">
            <div class="text-body2">
              <strong>Ward:</strong> {{ patientInfo.ward }}
            </div>
            <div class="text-body2" v-if="patientInfo.bed_number">
              <strong>Bed:</strong> {{ patientInfo.bed_number }}
            </div>
          </div>
        </div>
      </q-card-section>
    </q-card>

    <!-- Treatment Plan (Review Notes) -->
    <q-card class="glass-card q-mb-md" flat bordered>
      <q-card-section>
        <div class="text-h6 text-weight-bold glass-text q-mb-md">
          Treatment Plan
        </div>
        <q-input
          v-model="reviewNotes"
          filled
          type="textarea"
          placeholder="Enter treatment plan and clinical notes..."
          rows="6"
          hint="Auto-saved as draft"
          @update:model-value="autoSaveDraft"
        />
        <div class="row q-mt-md">
          <q-btn
            color="primary"
            label="Save Review"
            @click="saveClinicalReview"
            :loading="savingReview"
            class="glass-button"
          />
        </div>
      </q-card-section>
    </q-card>

    <!-- Diagnoses -->
    <q-card class="glass-card q-mb-md" flat bordered>
      <q-card-section>
        <div class="row items-center q-mb-md">
          <div class="text-h6 glass-text">Diagnoses</div>
          <q-space />
          <q-btn
            color="primary"
            label="Add Diagnosis"
            @click="resetDiagnosisForm(); showDiagnosisDialog = true"
            :disable="!currentClinicalReviewId"
            class="glass-button"
          />
        </div>

        <q-table
          :rows="diagnoses"
          :columns="diagnosisColumns"
          row-key="id"
          flat
          v-if="diagnoses.length > 0"
        >
          <template v-slot:body-cell-diagnosis_status="props">
            <q-td :props="props">
              <q-badge
                v-if="props.value"
                :color="props.value === 'new' ? 'blue' : props.value === 'old' ? 'grey' : 'purple'"
                :label="props.value === 'new' ? 'New' : props.value === 'old' ? 'Old' : 'Recurring'"
              />
            </q-td>
          </template>
          <template v-slot:body-cell-is_provisional="props">
            <q-td :props="props">
              <q-badge
                :color="props.value ? 'orange' : 'green'"
                :label="props.value ? 'Provisional' : 'Final'"
              />
            </q-td>
          </template>
          <template v-slot:body-cell-is_chief="props">
            <q-td :props="props">
              <q-icon
                v-if="props.value"
                name="star"
                color="primary"
                size="sm"
              />
            </q-td>
          </template>
          <template v-slot:body-cell-actions="props">
            <q-td :props="props">
              <q-btn
                flat
                dense
                round
                icon="delete"
                color="negative"
                size="sm"
                @click="deleteDiagnosis(props.row)"
              />
            </q-td>
          </template>
        </q-table>
        <div v-else class="text-center text-grey-6 q-pa-md">
          No diagnoses added yet. Click "Add Diagnosis" to add one.
        </div>
      </q-card-section>
    </q-card>

    <!-- Prescriptions -->
    <q-card class="glass-card q-mb-md" flat bordered>
      <q-card-section>
        <div class="row items-center q-mb-md">
          <div class="text-h6 glass-text">Prescriptions</div>
          <q-space />
          <q-btn
            color="primary"
            label="Add Prescription"
            @click="resetPrescriptionForm(); showPrescriptionDialog = true"
            :disable="!currentClinicalReviewId"
            class="glass-button"
          />
        </div>

        <q-table
          :rows="prescriptions"
          :columns="prescriptionColumns"
          row-key="id"
          flat
          v-if="prescriptions.length > 0"
        >
          <template v-slot:body-cell-actions="props">
            <q-td :props="props">
              <q-btn
                flat
                dense
                round
                icon="delete"
                color="negative"
                size="sm"
                @click="deletePrescription(props.row)"
              />
            </q-td>
          </template>
        </q-table>
        <div v-else class="text-center text-grey-6 q-pa-md">
          No prescriptions added yet. Click "Add Prescription" to add one.
        </div>
      </q-card-section>
    </q-card>

    <!-- Investigations -->
    <q-card class="glass-card q-mb-md" flat bordered>
      <q-card-section>
        <div class="row items-center q-mb-md">
          <div class="text-h6 glass-text">Investigations</div>
          <q-space />
          <q-btn
            color="primary"
            label="Add Investigation"
            @click="resetInvestigationForm(); showInvestigationDialog = true"
            :disable="!currentClinicalReviewId"
            class="glass-button"
          />
        </div>

        <q-table
          :rows="investigations"
          :columns="investigationColumns"
          row-key="id"
          flat
          v-if="investigations.length > 0"
        >
          <template v-slot:body-cell-actions="props">
            <q-td :props="props">
              <q-btn
                flat
                dense
                round
                icon="delete"
                color="negative"
                size="sm"
                @click="deleteInvestigation(props.row)"
              />
            </q-td>
          </template>
        </q-table>
        <div v-else class="text-center text-grey-6 q-pa-md">
          No investigations added yet. Click "Add Investigation" to add one.
        </div>
      </q-card-section>
    </q-card>

    <!-- Diagnosis Dialog -->
    <q-dialog v-model="showDiagnosisDialog">
      <q-card style="min-width: 500px">
        <q-card-section>
          <div class="text-h6">Add Diagnosis</div>
        </q-card-section>
        <q-card-section>
          <q-form @submit="saveDiagnosis" class="q-gutter-md">
            <q-select
              v-model="selectedIcd10"
              filled
              :options="icd10Options"
              label="Search by ICD-10 Code"
              option-label="display"
              use-input
              input-debounce="300"
              @filter="filterIcd10Codes"
              @update:model-value="onIcd10Selected"
              clearable
            />
            <q-input
              v-model="diagnosisForm.icd10"
              filled
              label="ICD-10 Code"
            />
            <q-input
              v-model="diagnosisForm.diagnosis"
              filled
              label="Diagnosis *"
              :rules="[val => !!val || 'Required']"
            />
            <q-input
              v-model="diagnosisForm.gdrg_code"
              filled
              label="GDRG Code"
              readonly
            />
            <q-select
              v-model="diagnosisForm.diagnosis_status"
              filled
              :options="[
                { label: 'New', value: 'new' },
                { label: 'Old', value: 'old' },
                { label: 'Recurring', value: 'recurring' }
              ]"
              emit-value
              map-options
              label="Diagnosis Status"
            />
            <q-toggle
              v-model="diagnosisForm.is_provisional"
              label="Provisional Diagnosis"
            />
            <q-toggle
              v-model="diagnosisForm.is_chief"
              label="Chief Diagnosis"
            />
            <div>
              <q-btn label="Add" type="submit" color="primary" />
              <q-btn label="Cancel" flat v-close-popup @click="resetDiagnosisForm" />
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- Prescription Dialog -->
    <q-dialog v-model="showPrescriptionDialog">
      <q-card style="min-width: 500px">
        <q-card-section>
          <div class="text-h6">Add Prescription</div>
        </q-card-section>
        <q-card-section>
          <q-form @submit="savePrescription" class="q-gutter-md">
            <q-select
              v-model="selectedMedication"
              filled
              :options="medicationOptions"
              label="Search Medication"
              option-label="item_name"
              use-input
              input-debounce="300"
              @filter="filterMedications"
              @update:model-value="onMedicationSelected"
              clearable
            />
            <q-input
              v-model="prescriptionForm.medicine_code"
              filled
              label="Medicine Code *"
              :rules="[val => !!val || 'Required']"
              readonly
            />
            <q-input
              v-model="prescriptionForm.medicine_name"
              filled
              label="Medicine Name *"
              :rules="[val => !!val || 'Required']"
              readonly
            />
            <div class="row q-gutter-md">
              <q-input
                v-model="prescriptionForm.dose"
                filled
                label="Dose"
                class="col-6"
              />
              <q-select
                v-model="prescriptionForm.unit"
                filled
                :options="unitOptions"
                label="Unit"
                class="col-6"
              />
            </div>
            <q-select
              v-model="prescriptionForm.frequency"
              filled
              :options="frequencyOptions"
              label="Frequency"
            />
            <q-input
              v-model="prescriptionForm.duration"
              filled
              label="Duration"
            />
            <q-input
              v-model="prescriptionForm.instructions"
              filled
              type="textarea"
              label="Instructions"
              rows="2"
            />
            <div>
              <q-btn label="Add" type="submit" color="primary" />
              <q-btn label="Cancel" flat v-close-popup @click="resetPrescriptionForm" />
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- Investigation Dialog -->
    <q-dialog v-model="showInvestigationDialog">
      <q-card style="min-width: 500px">
        <q-card-section>
          <div class="text-h6">Add Investigation</div>
        </q-card-section>
        <q-card-section>
          <q-form @submit="saveInvestigation" class="q-gutter-md">
            <q-select
              v-model="investigationForm.service_type"
              filled
              :options="serviceTypeOptions"
              label="Service Type"
              @update:model-value="onServiceTypeSelected"
            />
            <q-select
              v-model="selectedProcedure"
              filled
              :options="procedureOptions"
              label="Search Procedure"
              option-label="service_name"
              use-input
              input-debounce="300"
              @filter="filterProcedures"
              @update:model-value="onProcedureSelected"
              clearable
            />
            <q-input
              v-model="investigationForm.gdrg_code"
              filled
              label="GDRG Code *"
              :rules="[val => !!val || 'Required']"
              readonly
            />
            <q-input
              v-model="investigationForm.procedure_name"
              filled
              label="Procedure Name"
              readonly
            />
            <q-select
              v-model="investigationForm.investigation_type"
              filled
              :options="['lab', 'scan', 'xray']"
              label="Investigation Type *"
              :rules="[val => !!val || 'Required']"
            />
            <q-input
              v-model="investigationForm.notes"
              filled
              type="textarea"
              label="Notes"
              rows="2"
            />
            <q-input
              v-model="investigationForm.price"
              filled
              label="Price"
              readonly
            />
            <div>
              <q-btn label="Add" type="submit" color="primary" />
              <q-btn label="Cancel" flat v-close-popup @click="resetInvestigationForm" />
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { useQuasar } from 'quasar';
import { consultationAPI, priceListAPI } from '../services/api';

const $q = useQuasar();
const router = useRouter();
const route = useRoute();

const wardAdmissionId = computed(() => parseInt(route.params.id));
const clinicalReviewIdFromQuery = computed(() => {
  const reviewId = route.query.reviewId;
  return reviewId ? parseInt(reviewId) : null;
});
const patientInfo = ref(null);
const currentClinicalReviewId = ref(null);
const reviewNotes = ref('');
const savingReview = ref(false);

// Diagnoses
const diagnoses = ref([]);
const showDiagnosisDialog = ref(false);
const selectedIcd10 = ref(null);
const icd10Options = ref([]);
const allIcd10Codes = ref([]);
const diagnosisForm = ref({
  clinical_review_id: null,
  icd10: '',
  diagnosis: '',
  gdrg_code: '',
  diagnosis_status: null,
  is_provisional: false,
  is_chief: false,
});

// Prescriptions
const prescriptions = ref([]);
const showPrescriptionDialog = ref(false);
const selectedMedication = ref(null);
const medicationOptions = ref([]);
const allMedications = ref([]);
const prescriptionForm = ref({
  clinical_review_id: null,
  medicine_code: '',
  medicine_name: '',
  dose: '',
  unit: '',
  frequency: '',
  duration: '',
  instructions: '',
  quantity: 0,
});
const frequencyOptions = ['OD', 'BDS', 'TDS', 'QDS', 'Nocte', 'PRN', 'Stat'];
const unitOptions = ['MG', 'ML', 'TAB', 'CAP', 'G', 'MCG', 'IU', 'UNITS', 'DROPS', 'SACHET'];

// Investigations
const investigations = ref([]);
const showInvestigationDialog = ref(false);
const selectedProcedure = ref(null);
const procedureOptions = ref([]);
const allProcedures = ref([]);
const serviceTypeOptions = ref([]);
const investigationForm = ref({
  clinical_review_id: null,
  service_type: '',
  gdrg_code: '',
  procedure_name: '',
  investigation_type: '',
  notes: '',
  price: '',
});

// Auto-save draft
const draftSaveTimer = ref(null);
const DRAFT_SAVE_DELAY = 2000;

const autoSaveDraft = () => {
  if (draftSaveTimer.value) {
    clearTimeout(draftSaveTimer.value);
  }
  draftSaveTimer.value = setTimeout(() => {
    if (reviewNotes.value.trim()) {
      const key = `clinical_review_draft_${wardAdmissionId.value}`;
      localStorage.setItem(key, JSON.stringify({
        value: reviewNotes.value,
        timestamp: Date.now(),
      }));
    }
  }, DRAFT_SAVE_DELAY);
};

// Table columns
const diagnosisColumns = [
  { name: 'icd10', label: 'ICD-10', field: 'icd10', align: 'left' },
  { name: 'diagnosis', label: 'Diagnosis', field: 'diagnosis', align: 'left' },
  { name: 'gdrg_code', label: 'GDRG Code', field: 'gdrg_code', align: 'left' },
  { name: 'diagnosis_status', label: 'Status', field: 'diagnosis_status', align: 'center' },
  { name: 'is_provisional', label: 'Type', field: 'is_provisional', align: 'center' },
  { name: 'is_chief', label: 'Chief', field: 'is_chief', align: 'center' },
  { name: 'actions', label: 'Actions', field: 'actions', align: 'center' },
];

const prescriptionColumns = [
  { name: 'medicine_name', label: 'Medicine', field: 'medicine_name', align: 'left' },
  { name: 'dose', label: 'Dose', field: 'dose', align: 'left' },
  { name: 'unit', label: 'Unit', field: 'unit', align: 'left' },
  { name: 'frequency', label: 'Frequency', field: 'frequency', align: 'left' },
  { name: 'duration', label: 'Duration', field: 'duration', align: 'left' },
  { name: 'quantity', label: 'Quantity', field: 'quantity', align: 'left' },
  { name: 'actions', label: 'Actions', field: 'actions', align: 'center' },
];

const investigationColumns = [
  { name: 'procedure_name', label: 'Procedure', field: 'procedure_name', align: 'left' },
  { name: 'gdrg_code', label: 'GDRG Code', field: 'gdrg_code', align: 'left' },
  { name: 'investigation_type', label: 'Type', field: 'investigation_type', align: 'left' },
  { name: 'status', label: 'Status', field: 'status', align: 'left' },
  { name: 'price', label: 'Price', field: 'price', align: 'left' },
  { name: 'actions', label: 'Actions', field: 'actions', align: 'center' },
];

// Load patient info
const loadPatientInfo = async () => {
  try {
    const response = await consultationAPI.getWardAdmissions(null, false);
    const admissions = Array.isArray(response.data) ? response.data : [];
    const admission = admissions.find(a => a.id === wardAdmissionId.value);
    if (admission) {
      patientInfo.value = admission;
    }
  } catch (error) {
    console.error('Error loading patient info:', error);
  }
};

// Load or create clinical review
const loadClinicalReview = async () => {
  try {
    // If reviewId is provided in query, load that specific review
    if (clinicalReviewIdFromQuery.value) {
      const response = await consultationAPI.getInpatientClinicalReviews(wardAdmissionId.value);
      const reviews = Array.isArray(response.data) ? response.data : [];
      const review = reviews.find(r => r.id === clinicalReviewIdFromQuery.value);
      if (review) {
        currentClinicalReviewId.value = review.id;
        reviewNotes.value = review.review_notes || '';
        await loadReviewData();
        return;
      }
    }
    
    // Otherwise, try to load the most recent review
    const response = await consultationAPI.getInpatientClinicalReviews(wardAdmissionId.value);
    const reviews = Array.isArray(response.data) ? response.data : [];
    if (reviews.length > 0) {
      // Use the most recent review
      const latestReview = reviews[0];
      currentClinicalReviewId.value = latestReview.id;
      reviewNotes.value = latestReview.review_notes || '';
      await loadReviewData();
    } else {
      // Create a new review
      await createClinicalReview();
    }
  } catch (error) {
    console.error('Error loading clinical review:', error);
  }
};

const createClinicalReview = async () => {
  try {
    const response = await consultationAPI.createInpatientClinicalReview(wardAdmissionId.value, {
      review_notes: reviewNotes.value,
    });
    currentClinicalReviewId.value = response.data.id;
    reviewNotes.value = response.data.review_notes || '';
  } catch (error) {
    console.error('Error creating clinical review:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to create clinical review',
    });
  }
};

const saveClinicalReview = async () => {
  savingReview.value = true;
  try {
    if (!currentClinicalReviewId.value) {
      // Create new review
      await createClinicalReview();
      $q.notify({
        type: 'positive',
        message: 'Clinical review created successfully',
      });
    } else {
      // Update existing review
      await consultationAPI.updateInpatientClinicalReview(wardAdmissionId.value, currentClinicalReviewId.value, {
        review_notes: reviewNotes.value,
      });
      $q.notify({
        type: 'positive',
        message: 'Clinical review updated successfully',
      });
    }
    // Clear draft
    const key = `clinical_review_draft_${wardAdmissionId.value}`;
    localStorage.removeItem(key);
  } catch (error) {
    console.error('Error saving clinical review:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to save clinical review',
    });
  } finally {
    savingReview.value = false;
  }
};

const loadReviewData = async () => {
  if (!currentClinicalReviewId.value) return;
  
  try {
    // Load diagnoses
    const diagnosesRes = await consultationAPI.getInpatientDiagnoses(wardAdmissionId.value, currentClinicalReviewId.value);
    diagnoses.value = Array.isArray(diagnosesRes.data) ? diagnosesRes.data : [];
    
    // Load prescriptions
    const prescriptionsRes = await consultationAPI.getInpatientPrescriptions(wardAdmissionId.value, currentClinicalReviewId.value);
    prescriptions.value = Array.isArray(prescriptionsRes.data) ? prescriptionsRes.data : [];
    
    // Load investigations
    const investigationsRes = await consultationAPI.getInpatientInvestigations(wardAdmissionId.value, currentClinicalReviewId.value);
    investigations.value = Array.isArray(investigationsRes.data) ? investigationsRes.data : [];
  } catch (error) {
    console.error('Error loading review data:', error);
  }
};

// Diagnosis functions
const filterIcd10Codes = async (val, update) => {
  if (val === '') {
    update(() => {
      icd10Options.value = allIcd10Codes.value.map(item => ({
        ...item,
        display: `${item.icd10_code} - ${item.icd10_description}`
      }));
    });
    return;
  }
  update(async () => {
    try {
      const response = await priceListAPI.searchIcd10(val, 50);
      const results = response.data || [];
      icd10Options.value = results.map(item => ({
        ...item,
        display: `${item.icd10_code} - ${item.icd10_description}`
      }));
    } catch (error) {
      console.error('Failed to search ICD-10 codes:', error);
      icd10Options.value = [];
    }
  });
};

const onIcd10Selected = async (icd10Item) => {
  if (icd10Item) {
    diagnosisForm.value.icd10 = icd10Item.icd10_code || '';
    diagnosisForm.value.diagnosis = icd10Item.icd10_description || '';
    try {
      const response = await priceListAPI.getDrgCodesFromIcd10(icd10Item.icd10_code);
      const drgCodes = response.data || [];
      if (drgCodes.length > 0) {
        diagnosisForm.value.gdrg_code = drgCodes[0].drg_code || '';
      }
    } catch (error) {
      console.error('Failed to get DRG codes:', error);
    }
  }
};

const saveDiagnosis = async () => {
  if (!currentClinicalReviewId.value) {
    $q.notify({
      type: 'negative',
      message: 'Please save the clinical review first',
    });
    return;
  }
  
  try {
    diagnosisForm.value.clinical_review_id = currentClinicalReviewId.value;
    await consultationAPI.createInpatientDiagnosis(wardAdmissionId.value, currentClinicalReviewId.value, diagnosisForm.value);
    $q.notify({
      type: 'positive',
      message: 'Diagnosis added successfully',
    });
    resetDiagnosisForm();
    showDiagnosisDialog.value = false;
    await loadReviewData();
  } catch (error) {
    console.error('Error saving diagnosis:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to add diagnosis',
    });
  }
};

const deleteDiagnosis = async (diagnosis) => {
  $q.dialog({
    title: 'Confirm Delete',
    message: 'Are you sure you want to delete this diagnosis?',
    cancel: true,
    persistent: true,
  }).onOk(async () => {
    try {
      await consultationAPI.deleteInpatientDiagnosis(wardAdmissionId.value, currentClinicalReviewId.value, diagnosis.id);
      $q.notify({
        type: 'positive',
        message: 'Diagnosis deleted successfully',
      });
      await loadReviewData();
    } catch (error) {
      console.error('Error deleting diagnosis:', error);
      $q.notify({
        type: 'negative',
        message: error.response?.data?.detail || 'Failed to delete diagnosis',
      });
    }
  });
};

const resetDiagnosisForm = () => {
  diagnosisForm.value = {
    clinical_review_id: null,
    icd10: '',
    diagnosis: '',
    gdrg_code: '',
    diagnosis_status: null,
    is_provisional: false,
    is_chief: false,
  };
  selectedIcd10.value = null;
};

// Prescription functions
const filterMedications = (val, update) => {
  if (val === '') {
    update(() => {
      medicationOptions.value = allMedications.value;
    });
    return;
  }
  update(() => {
    const needle = val.toLowerCase();
    medicationOptions.value = allMedications.value.filter(
      m => (m.item_name || '').toLowerCase().includes(needle) ||
           (m.item_code || '').toLowerCase().includes(needle)
    );
  });
};

const onMedicationSelected = (medication) => {
  if (medication) {
    prescriptionForm.value.medicine_code = medication.item_code || '';
    prescriptionForm.value.medicine_name = medication.item_name || '';
  }
};

const savePrescription = async () => {
  if (!currentClinicalReviewId.value) {
    $q.notify({
      type: 'negative',
      message: 'Please save the clinical review first',
    });
    return;
  }
  
  try {
    prescriptionForm.value.clinical_review_id = currentClinicalReviewId.value;
    await consultationAPI.createInpatientPrescription(wardAdmissionId.value, currentClinicalReviewId.value, prescriptionForm.value);
    $q.notify({
      type: 'positive',
      message: 'Prescription added successfully',
    });
    resetPrescriptionForm();
    showPrescriptionDialog.value = false;
    await loadReviewData();
  } catch (error) {
    console.error('Error saving prescription:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to add prescription',
    });
  }
};

const deletePrescription = async (prescription) => {
  $q.dialog({
    title: 'Confirm Delete',
    message: 'Are you sure you want to delete this prescription?',
    cancel: true,
    persistent: true,
  }).onOk(async () => {
    try {
      await consultationAPI.deleteInpatientPrescription(wardAdmissionId.value, currentClinicalReviewId.value, prescription.id);
      $q.notify({
        type: 'positive',
        message: 'Prescription deleted successfully',
      });
      await loadReviewData();
    } catch (error) {
      console.error('Error deleting prescription:', error);
      $q.notify({
        type: 'negative',
        message: error.response?.data?.detail || 'Failed to delete prescription',
      });
    }
  });
};

const resetPrescriptionForm = () => {
  prescriptionForm.value = {
    clinical_review_id: null,
    medicine_code: '',
    medicine_name: '',
    dose: '',
    unit: '',
    frequency: '',
    duration: '',
    instructions: '',
    quantity: 0,
  };
  selectedMedication.value = null;
};

// Investigation functions
const onServiceTypeSelected = async (serviceType) => {
  if (!serviceType) {
    allProcedures.value = [];
    procedureOptions.value = [];
    return;
  }
  try {
    const response = await priceListAPI.getProceduresByServiceType(serviceType);
    let procedures = [];
    if (Array.isArray(response.data)) {
      procedures = response.data;
    } else if (response.data && typeof response.data === 'object') {
      procedures = response.data[serviceType] || [];
    }
    allProcedures.value = procedures;
    procedureOptions.value = procedures;
  } catch (error) {
    console.error('Failed to load procedures:', error);
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
      p => (p.service_name || '').toLowerCase().includes(needle) ||
           (p.g_drg_code || '').toLowerCase().includes(needle)
    );
  });
};

const onProcedureSelected = (procedure) => {
  if (procedure) {
    investigationForm.value.gdrg_code = procedure.g_drg_code || '';
    investigationForm.value.procedure_name = procedure.service_name || '';
    investigationForm.value.price = procedure.base_rate ? procedure.base_rate.toString() : '';
  }
};

const saveInvestigation = async () => {
  if (!currentClinicalReviewId.value) {
    $q.notify({
      type: 'negative',
      message: 'Please save the clinical review first',
    });
    return;
  }
  
  try {
    investigationForm.value.clinical_review_id = currentClinicalReviewId.value;
    await consultationAPI.createInpatientInvestigation(wardAdmissionId.value, currentClinicalReviewId.value, investigationForm.value);
    $q.notify({
      type: 'positive',
      message: 'Investigation added successfully',
    });
    resetInvestigationForm();
    showInvestigationDialog.value = false;
    await loadReviewData();
  } catch (error) {
    console.error('Error saving investigation:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to add investigation',
    });
  }
};

const deleteInvestigation = async (investigation) => {
  $q.dialog({
    title: 'Confirm Delete',
    message: 'Are you sure you want to delete this investigation?',
    cancel: true,
    persistent: true,
  }).onOk(async () => {
    try {
      await consultationAPI.deleteInpatientInvestigation(wardAdmissionId.value, currentClinicalReviewId.value, investigation.id);
      $q.notify({
        type: 'positive',
        message: 'Investigation deleted successfully',
      });
      await loadReviewData();
    } catch (error) {
      console.error('Error deleting investigation:', error);
      $q.notify({
        type: 'negative',
        message: error.response?.data?.detail || 'Failed to delete investigation',
      });
    }
  });
};

const resetInvestigationForm = () => {
  investigationForm.value = {
    clinical_review_id: null,
    service_type: '',
    gdrg_code: '',
    procedure_name: '',
    investigation_type: '',
    notes: '',
    price: '',
  };
  selectedProcedure.value = null;
};

// Load initial data
const loadInitialData = async () => {
  try {
    // Load ICD-10 codes
    const icd10Res = await priceListAPI.searchIcd10('', 100);
    allIcd10Codes.value = icd10Res.data || [];
    icd10Options.value = allIcd10Codes.value.map(item => ({
      ...item,
      display: `${item.icd10_code} - ${item.icd10_description}`
    }));
    
    // Load medications
    const medRes = await priceListAPI.search('', undefined, 'product');
    allMedications.value = medRes.data || [];
    medicationOptions.value = allMedications.value;
    
    // Load service types
    const serviceTypesRes = await priceListAPI.getServiceTypes();
    serviceTypeOptions.value = serviceTypesRes.data || [];
  } catch (error) {
    console.error('Error loading initial data:', error);
  }
};

const goBack = () => {
  router.push(`/ipd/admission-manager/${wardAdmissionId.value}`);
};

onMounted(async () => {
  if (!wardAdmissionId.value) {
    $q.notify({
      type: 'negative',
      message: 'Invalid ward admission ID',
    });
    goBack();
    return;
  }
  
  await loadPatientInfo();
  await loadInitialData();
  await loadClinicalReview();
  
  // Load draft
  const key = `clinical_review_draft_${wardAdmissionId.value}`;
  const draft = localStorage.getItem(key);
  if (draft && !reviewNotes.value) {
    try {
      const draftData = JSON.parse(draft);
      reviewNotes.value = draftData.value || '';
    } catch (error) {
      console.error('Error loading draft:', error);
    }
  }
});
</script>

<style scoped>
.body--light .glass-text {
  color: rgba(0, 0, 0, 0.87) !important;
}

.body--dark .glass-text {
  color: rgba(255, 255, 255, 0.9) !important;
}
</style>

