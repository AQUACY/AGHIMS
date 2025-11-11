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
        Nurse Mid Documentation
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
              <strong>Name:</strong> {{ patientInfo.patient_name }} {{ patientInfo.patient_surname }}
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

    <q-card class="glass-card" flat bordered>
      <q-card-section>
        <q-expansion-item
          v-model="formExpanded"
          expand-separator
          icon="description"
          label="Nurse Mid Documentation Form"
          header-class="text-h6 text-weight-bold glass-text"
        >
          <q-form @submit="saveDocumentation" class="q-gutter-md q-pa-md">
          <!-- Patient Problems / Diagnosis -->
          <div>
            <div class="text-subtitle2 text-weight-bold glass-text q-mb-sm">
              1. Patient Problems / Diagnosis *
            </div>
            <!-- Draft Banner -->
            <q-banner
              v-if="hasDraft('patient_problems_diagnosis') && formData.patient_problems_diagnosis !== (getDraftValue('patient_problems_diagnosis') || '')"
              class="bg-warning text-dark q-mb-md"
              rounded
            >
              <template v-slot:avatar>
                <q-icon name="save" color="dark" />
              </template>
              <strong>Draft Available</strong>
              <div class="text-caption q-mt-xs">
                A draft was saved {{ formatDraftTime(getDraftTime('patient_problems_diagnosis')) }}. 
                Would you like to restore it?
              </div>
              <template v-slot:action>
                <q-btn
                  flat
                  label="Restore Draft"
                  color="dark"
                  @click="restoreDraft('patient_problems_diagnosis')"
                />
                <q-btn
                  flat
                  label="Discard"
                  color="dark"
                  @click="clearDraft('patient_problems_diagnosis')"
                />
              </template>
            </q-banner>
            <q-input
              v-model="formData.patient_problems_diagnosis"
              filled
              type="textarea"
              placeholder="Enter patient problems and diagnosis..."
              rows="4"
              hint="Auto-saved as draft"
              :rules="[val => !!val || 'This field is required']"
              @update:model-value="autoSaveDraft('patient_problems_diagnosis')"
            />
          </div>

          <q-separator class="q-my-md" />

          <!-- Aim of Care / Objectives / Outcome Criteria -->
          <div>
            <div class="text-subtitle2 text-weight-bold glass-text q-mb-sm">
              2. Aim of Care / Objectives / Outcome Criteria *
            </div>
            <!-- Draft Banner -->
            <q-banner
              v-if="hasDraft('aim_of_care') && formData.aim_of_care !== (getDraftValue('aim_of_care') || '')"
              class="bg-warning text-dark q-mb-md"
              rounded
            >
              <template v-slot:avatar>
                <q-icon name="save" color="dark" />
              </template>
              <strong>Draft Available</strong>
              <div class="text-caption q-mt-xs">
                A draft was saved {{ formatDraftTime(getDraftTime('aim_of_care')) }}. 
                Would you like to restore it?
              </div>
              <template v-slot:action>
                <q-btn
                  flat
                  label="Restore Draft"
                  color="dark"
                  @click="restoreDraft('aim_of_care')"
                />
                <q-btn
                  flat
                  label="Discard"
                  color="dark"
                  @click="clearDraft('aim_of_care')"
                />
              </template>
            </q-banner>
            <q-input
              v-model="formData.aim_of_care"
              filled
              type="textarea"
              placeholder="Enter aim of care, objectives, and outcome criteria..."
              rows="4"
              hint="Auto-saved as draft"
              :rules="[val => !!val || 'This field is required']"
              @update:model-value="autoSaveDraft('aim_of_care')"
            />
          </div>

          <q-separator class="q-my-md" />

          <!-- Nursing Assessment -->
          <div>
            <div class="text-subtitle2 text-weight-bold glass-text q-mb-sm">
              3. Nursing Assessment *
            </div>
            <!-- Draft Banner -->
            <q-banner
              v-if="hasDraft('nursing_assessment') && formData.nursing_assessment !== (getDraftValue('nursing_assessment') || '')"
              class="bg-warning text-dark q-mb-md"
              rounded
            >
              <template v-slot:avatar>
                <q-icon name="save" color="dark" />
              </template>
              <strong>Draft Available</strong>
              <div class="text-caption q-mt-xs">
                A draft was saved {{ formatDraftTime(getDraftTime('nursing_assessment')) }}. 
                Would you like to restore it?
              </div>
              <template v-slot:action>
                <q-btn
                  flat
                  label="Restore Draft"
                  color="dark"
                  @click="restoreDraft('nursing_assessment')"
                />
                <q-btn
                  flat
                  label="Discard"
                  color="dark"
                  @click="clearDraft('nursing_assessment')"
                />
              </template>
            </q-banner>
            <q-input
              v-model="formData.nursing_assessment"
              filled
              type="textarea"
              placeholder="Enter nursing assessment..."
              rows="4"
              hint="Auto-saved as draft"
              :rules="[val => !!val || 'This field is required']"
              @update:model-value="autoSaveDraft('nursing_assessment')"
            />
          </div>

          <q-separator class="q-my-md" />

          <!-- Nursing Orders -->
          <div>
            <div class="text-subtitle2 text-weight-bold glass-text q-mb-sm">
              4. Nursing Orders *
            </div>
            <!-- Draft Banner -->
            <q-banner
              v-if="hasDraft('nursing_orders') && formData.nursing_orders !== (getDraftValue('nursing_orders') || '')"
              class="bg-warning text-dark q-mb-md"
              rounded
            >
              <template v-slot:avatar>
                <q-icon name="save" color="dark" />
              </template>
              <strong>Draft Available</strong>
              <div class="text-caption q-mt-xs">
                A draft was saved {{ formatDraftTime(getDraftTime('nursing_orders')) }}. 
                Would you like to restore it?
              </div>
              <template v-slot:action>
                <q-btn
                  flat
                  label="Restore Draft"
                  color="dark"
                  @click="restoreDraft('nursing_orders')"
                />
                <q-btn
                  flat
                  label="Discard"
                  color="dark"
                  @click="clearDraft('nursing_orders')"
                />
              </template>
            </q-banner>
            <q-input
              v-model="formData.nursing_orders"
              filled
              type="textarea"
              placeholder="Enter nursing orders..."
              rows="4"
              hint="Auto-saved as draft"
              :rules="[val => !!val || 'This field is required']"
              @update:model-value="autoSaveDraft('nursing_orders')"
            />
          </div>

          <q-separator class="q-my-md" />

          <!-- Nursing Intervention -->
          <div>
            <div class="text-subtitle2 text-weight-bold glass-text q-mb-sm">
              5. Nursing Intervention *
            </div>
            <!-- Draft Banner -->
            <q-banner
              v-if="hasDraft('nursing_intervention') && formData.nursing_intervention !== (getDraftValue('nursing_intervention') || '')"
              class="bg-warning text-dark q-mb-md"
              rounded
            >
              <template v-slot:avatar>
                <q-icon name="save" color="dark" />
              </template>
              <strong>Draft Available</strong>
              <div class="text-caption q-mt-xs">
                A draft was saved {{ formatDraftTime(getDraftTime('nursing_intervention')) }}. 
                Would you like to restore it?
              </div>
              <template v-slot:action>
                <q-btn
                  flat
                  label="Restore Draft"
                  color="dark"
                  @click="restoreDraft('nursing_intervention')"
                />
                <q-btn
                  flat
                  label="Discard"
                  color="dark"
                  @click="clearDraft('nursing_intervention')"
                />
              </template>
            </q-banner>
            <q-input
              v-model="formData.nursing_intervention"
              filled
              type="textarea"
              placeholder="Enter nursing intervention..."
              rows="4"
              hint="Auto-saved as draft"
              :rules="[val => !!val || 'This field is required']"
              @update:model-value="autoSaveDraft('nursing_intervention')"
            />
          </div>

          <q-separator class="q-my-md" />

          <!-- Evaluation -->
          <div>
            <div class="text-subtitle2 text-weight-bold glass-text q-mb-sm">
              6. Evaluation *
            </div>
            <!-- Draft Banner -->
            <q-banner
              v-if="hasDraft('evaluation') && formData.evaluation !== (getDraftValue('evaluation') || '')"
              class="bg-warning text-dark q-mb-md"
              rounded
            >
              <template v-slot:avatar>
                <q-icon name="save" color="dark" />
              </template>
              <strong>Draft Available</strong>
              <div class="text-caption q-mt-xs">
                A draft was saved {{ formatDraftTime(getDraftTime('evaluation')) }}. 
                Would you like to restore it?
              </div>
              <template v-slot:action>
                <q-btn
                  flat
                  label="Restore Draft"
                  color="dark"
                  @click="restoreDraft('evaluation')"
                />
                <q-btn
                  flat
                  label="Discard"
                  color="dark"
                  @click="clearDraft('evaluation')"
                />
              </template>
            </q-banner>
            <q-input
              v-model="formData.evaluation"
              filled
              type="textarea"
              placeholder="Enter evaluation..."
              rows="4"
              hint="Auto-saved as draft"
              :rules="[val => !!val || 'This field is required']"
              @update:model-value="autoSaveDraft('evaluation')"
            />
          </div>

          <q-separator class="q-my-md" />

            <q-card-actions align="right">
              <q-btn flat label="Cancel" color="primary" @click="resetForm" />
              <q-btn
                flat
                :label="editingDocId ? 'Update Documentation' : 'Save Documentation'"
                color="positive"
                type="submit"
                :loading="saving"
              />
            </q-card-actions>
          </q-form>
        </q-expansion-item>
      </q-card-section>
    </q-card>

    <!-- Previous Documentation List -->
    <q-card v-if="previousDocumentations.length > 0" class="glass-card q-mt-md" flat bordered>
      <q-card-section>
        <div class="text-h6 text-weight-bold glass-text q-mb-md">
          Previous Nurse Mid Documentations
        </div>
        <q-list bordered separator>
          <q-item
            v-for="doc in previousDocumentations"
            :key="doc.id"
            class="q-pa-md"
          >
            <q-item-section>
              <q-item-label class="text-weight-bold">
                <div class="row items-center justify-between">
                  <div>
                    Created by: {{ doc.created_by_name || 'Unknown' }} on {{ formatDateTime(doc.created_at) }}
                  </div>
                  <q-btn
                    v-if="canEditDocumentation(doc)"
                    flat
                    dense
                    icon="edit"
                    label="Edit"
                    color="primary"
                    size="sm"
                    @click="editDocumentation(doc)"
                  />
                </div>
              </q-item-label>
              <q-item-label caption>
                <div class="q-mt-sm">
                  <div v-if="doc.patient_problems_diagnosis" class="q-mb-sm">
                    <strong>Patient Problems / Diagnosis:</strong>
                    <div class="q-ml-md">{{ doc.patient_problems_diagnosis }}</div>
                  </div>
                  <div v-if="doc.aim_of_care" class="q-mb-sm">
                    <strong>Aim of Care / Objectives / Outcome Criteria:</strong>
                    <div class="q-ml-md">{{ doc.aim_of_care }}</div>
                  </div>
                  <div v-if="doc.nursing_assessment" class="q-mb-sm">
                    <strong>Nursing Assessment:</strong>
                    <div class="q-ml-md">{{ doc.nursing_assessment }}</div>
                  </div>
                  <div v-if="doc.nursing_orders" class="q-mb-sm">
                    <strong>Nursing Orders:</strong>
                    <div class="q-ml-md">{{ doc.nursing_orders }}</div>
                  </div>
                  <div v-if="doc.nursing_intervention" class="q-mb-sm">
                    <strong>Nursing Intervention:</strong>
                    <div class="q-ml-md">{{ doc.nursing_intervention }}</div>
                  </div>
                  <div v-if="doc.evaluation" class="q-mb-sm">
                    <strong>Evaluation:</strong>
                    <div class="q-ml-md">{{ doc.evaluation }}</div>
                  </div>
                  <!-- Backward compatibility: show old documentation field if new fields are empty -->
                  <div v-if="doc.documentation && !doc.patient_problems_diagnosis && !doc.aim_of_care" class="q-mb-sm">
                    <strong>Documentation:</strong>
                    <div class="q-ml-md">{{ doc.documentation }}</div>
                  </div>
                </div>
              </q-item-label>
            </q-item-section>
          </q-item>
        </q-list>
      </q-card-section>
    </q-card>
  </q-page>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { useQuasar } from 'quasar';
import { consultationAPI } from '../services/api';
import { useAuthStore } from '../stores/auth';

const $q = useQuasar();
const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();

const wardAdmissionId = computed(() => parseInt(route.params.id));
const patientInfo = ref(null);
const saving = ref(false);
const previousDocumentations = ref([]);
const formExpanded = ref(false);
const editingDocId = ref(null);

const formData = ref({
  patient_problems_diagnosis: '',
  aim_of_care: '',
  nursing_assessment: '',
  nursing_orders: '',
  nursing_intervention: '',
  evaluation: '',
});

// Auto-save draft functionality
const draftSaveTimers = ref({});
const DRAFT_SAVE_DELAY = 2000; // Save after 2 seconds of no typing

// Get draft storage key
const getDraftKey = (field) => {
  if (!wardAdmissionId.value) return null;
  const editSuffix = editingDocId.value ? `_edit_${editingDocId.value}` : '';
  return `nurse_mid_doc_draft_${wardAdmissionId.value}_${field}${editSuffix}`;
};

// Auto-save draft (debounced)
const autoSaveDraft = (field) => {
  if (!wardAdmissionId.value) {
    console.warn('No ward admission ID for draft save');
    return;
  }
  
  // Clear existing timer
  if (draftSaveTimers.value[field]) {
    clearTimeout(draftSaveTimers.value[field]);
  }
  
  // Set new timer
  draftSaveTimers.value[field] = setTimeout(() => {
    const key = getDraftKey(field);
    if (!key) {
      console.warn(`No draft key for field: ${field}`);
      return;
    }
    
    const value = formData.value[field] || '';
    if (value.trim()) {
      const draftData = {
        value: value,
        timestamp: Date.now(),
        wardAdmissionId: wardAdmissionId.value,
        editingDocId: editingDocId.value
      };
      localStorage.setItem(key, JSON.stringify(draftData));
      console.log(`Draft saved for ${field}:`, draftData);
    } else {
      // Remove draft if empty
      localStorage.removeItem(key);
    }
  }, DRAFT_SAVE_DELAY);
};

// Check if draft exists
const hasDraft = (field) => {
  const key = getDraftKey(field);
  if (!key) return false;
  const draft = localStorage.getItem(key);
  if (!draft) return false;
  
  try {
    const draftData = JSON.parse(draft);
    // Check if draft is for current ward admission and edit state
    return draftData.wardAdmissionId === wardAdmissionId.value &&
           draftData.editingDocId === editingDocId.value;
  } catch {
    return false;
  }
};

// Get draft time
const getDraftTime = (field) => {
  const key = getDraftKey(field);
  if (!key) return null;
  const draft = localStorage.getItem(key);
  if (!draft) return null;
  
  try {
    const draftData = JSON.parse(draft);
    return draftData.timestamp;
  } catch {
    return null;
  }
};

// Get draft value
const getDraftValue = (field) => {
  const key = getDraftKey(field);
  if (!key) return null;
  const draft = localStorage.getItem(key);
  if (!draft) return null;
  
  try {
    const draftData = JSON.parse(draft);
    if (draftData.wardAdmissionId === wardAdmissionId.value &&
        draftData.editingDocId === editingDocId.value) {
      return draftData.value;
    }
    return null;
  } catch {
    return null;
  }
};

// Format draft time
const formatDraftTime = (timestamp) => {
  if (!timestamp) return '';
  const now = Date.now();
  const diff = now - timestamp;
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(minutes / 60);
  
  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
  if (hours < 24) return `${hours} hour${hours > 1 ? 's' : ''} ago`;
  
  const date = new Date(timestamp);
  return date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
};

// Restore draft
const restoreDraft = (field) => {
  const key = getDraftKey(field);
  if (!key) return;
  
  const draft = localStorage.getItem(key);
  if (!draft) return;
  
  try {
    const draftData = JSON.parse(draft);
    if (draftData.value) {
      formData.value[field] = draftData.value;
      $q.notify({
        type: 'positive',
        message: 'Draft restored successfully',
        position: 'top',
        timeout: 2000
      });
    }
  } catch (error) {
    console.error('Failed to restore draft:', error);
  }
};

// Clear draft
const clearDraft = (field) => {
  const key = getDraftKey(field);
  if (key) {
    localStorage.removeItem(key);
  }
};

// Clear all drafts
const clearAllDrafts = () => {
  const fields = [
    'patient_problems_diagnosis',
    'aim_of_care',
    'nursing_assessment',
    'nursing_orders',
    'nursing_intervention',
    'evaluation'
  ];
  
  fields.forEach(field => {
    clearDraft(field);
  });
  
  // Also clear any pending timers
  Object.keys(draftSaveTimers.value).forEach(field => {
    if (draftSaveTimers.value[field]) {
      clearTimeout(draftSaveTimers.value[field]);
    }
  });
  draftSaveTimers.value = {};
};

// Load drafts on page mount
const loadDrafts = () => {
  if (!wardAdmissionId.value) return;
  
  const fields = [
    'patient_problems_diagnosis',
    'aim_of_care',
    'nursing_assessment',
    'nursing_orders',
    'nursing_intervention',
    'evaluation'
  ];
  
  fields.forEach(field => {
    if (hasDraft(field)) {
      const draftValue = getDraftValue(field);
      // Only auto-restore if form field is empty
      if (draftValue && !formData.value[field].trim()) {
        formData.value[field] = draftValue;
      }
    }
  });
};

const loadPatientInfo = async () => {
  try {
    const response = await consultationAPI.getWardAdmissions(null, false);
    const admissions = Array.isArray(response.data) ? response.data : [];
    const admission = admissions.find(a => a.id === wardAdmissionId.value);
    
    if (admission) {
      patientInfo.value = admission;
    } else {
      $q.notify({
        type: 'negative',
        message: 'Patient admission not found',
      });
      goBack();
    }
  } catch (error) {
    console.error('Error loading patient info:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to load patient information',
    });
    goBack();
  }
};

const loadPreviousDocumentations = async () => {
  try {
    const response = await consultationAPI.getNurseMidDocumentations(wardAdmissionId.value);
    previousDocumentations.value = Array.isArray(response.data) ? response.data : [];
  } catch (error) {
    console.error('Error loading previous documentations:', error);
  }
};

const canEditDocumentation = (doc) => {
  const currentUserId = authStore.user?.id;
  const isAdmin = authStore.userRole === 'Admin';
  const isOwner = doc.created_by === currentUserId;
  return isAdmin || isOwner;
};

const editDocumentation = (doc) => {
  editingDocId.value = doc.id;
  formData.value = {
    patient_problems_diagnosis: doc.patient_problems_diagnosis || '',
    aim_of_care: doc.aim_of_care || '',
    nursing_assessment: doc.nursing_assessment || '',
    nursing_orders: doc.nursing_orders || '',
    nursing_intervention: doc.nursing_intervention || '',
    evaluation: doc.evaluation || '',
  };
  formExpanded.value = true;
  // Scroll to form
  setTimeout(() => {
    const formElement = document.querySelector('.q-expansion-item');
    if (formElement) {
      formElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, 100);
};

const resetForm = () => {
  editingDocId.value = null;
  formData.value = {
    patient_problems_diagnosis: '',
    aim_of_care: '',
    nursing_assessment: '',
    nursing_orders: '',
    nursing_intervention: '',
    evaluation: '',
  };
  formExpanded.value = false;
  // Clear all drafts when resetting
  clearAllDrafts();
};

const saveDocumentation = async () => {
  if (!wardAdmissionId.value) return;

  saving.value = true;
  try {
    if (editingDocId.value) {
      // Update existing documentation
      await consultationAPI.updateNurseMidDocumentation(
        wardAdmissionId.value,
        editingDocId.value,
        formData.value
      );
      $q.notify({
        type: 'positive',
        message: 'Nurse mid documentation updated successfully',
      });
    } else {
      // Create new documentation
      await consultationAPI.createNurseMidDocumentation(wardAdmissionId.value, formData.value);
      $q.notify({
        type: 'positive',
        message: 'Nurse mid documentation saved successfully',
      });
    }
    
    // Clear all drafts after successful save
    clearAllDrafts();
    
    // Reset form
    resetForm();
    
    // Reload previous documentations
    await loadPreviousDocumentations();
  } catch (error) {
    console.error('Error saving documentation:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to save documentation',
    });
  } finally {
    saving.value = false;
  }
};

const goBack = () => {
  router.push(`/ipd/admission-manager/${wardAdmissionId.value}`);
};

const formatDateTime = (dateString) => {
  if (!dateString) return 'N/A';
  const date = new Date(dateString);
  return date.toLocaleString('en-GB');
};

onMounted(() => {
  if (!wardAdmissionId.value) {
    $q.notify({
      type: 'negative',
      message: 'Invalid ward admission ID',
    });
    goBack();
    return;
  }
  loadPatientInfo();
  loadPreviousDocumentations();
  // Load drafts after a short delay to ensure form is initialized
  setTimeout(() => {
    loadDrafts();
  }, 100);
});
</script>


<style scoped>
/* Light mode adjustments */
.body--light .glass-text {
  color: rgba(0, 0, 0, 0.87) !important;
}

/* Dark mode adjustments */
.body--dark .glass-text {
  color: rgba(255, 255, 255, 0.9) !important;
}
</style>

