<template>
  <q-page class="hms-page">
    <HmsPageHeader
      title="Nurse mid documentation"
      subtitle="Nursing and midwifery documentation for this admission."
    >
      <template #actions>
        <HmsButton variant="secondary" size="sm" @click="goBack">Back to manager</HmsButton>
      </template>
    </HmsPageHeader>

    <div v-if="patientInfo" class="ipd-patient-hero">
      <div class="ipd-hero-main">
        <div class="ipd-hero-avatar">{{ nmdPatientInitials(patientInfo) }}</div>
        <div>
          <h1 class="ipd-hero-name">{{ nmdPatientDisplayName(patientInfo) }}</h1>
          <div class="ipd-hero-meta">
            <span class="mono">{{ patientInfo.patient_card_number }}</span>
            <span class="sep">·</span>
            <span>{{ patientInfo.ward || '—' }}</span>
            <template v-if="patientInfo.bed_number">
              <span class="sep">·</span>
              <span>Bed {{ patientInfo.bed_number }}</span>
            </template>
            <template v-if="patientInfo.patient_gender">
              <span class="sep">·</span>
              <span>{{ patientInfo.patient_gender }}</span>
            </template>
          </div>
        </div>
      </div>
    </div>

    <section class="am-panel">
      <div class="am-panel-head">
        <h2 class="hms-section-title">Nurse Mid Documentation Form</h2>
      </div>
      <q-expansion-item
        v-model="formExpanded"
        expand-separator
        icon="description"
        label="Open form"
        header-class="text-weight-medium"
      >
        <q-form @submit="saveDocumentation" class="q-gutter-md q-pa-md">
          <!-- Patient Problems / Diagnosis -->
          <div>
            <div class="text-subtitle2 text-weight-bold glass-text q-mb-sm">
              1. Patient Problems / Diagnosis
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
              @update:model-value="autoSaveDraft('patient_problems_diagnosis')"
            />
          </div>

          <q-separator class="q-my-md" />

          <!-- Aim of Care / Objectives / Outcome Criteria -->
          <div>
            <div class="text-subtitle2 text-weight-bold glass-text q-mb-sm">
              2. Aim of Care / Objectives / Outcome Criteria
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
              @update:model-value="autoSaveDraft('aim_of_care')"
            />
          </div>

          <q-separator class="q-my-md" />

          <!-- Nursing Assessment -->
          <div>
            <div class="text-subtitle2 text-weight-bold glass-text q-mb-sm">
              3. Nursing Assessment
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
              @update:model-value="autoSaveDraft('nursing_assessment')"
            />
          </div>

          <q-separator class="q-my-md" />

          <!-- Nursing Orders -->
          <div>
            <div class="text-subtitle2 text-weight-bold glass-text q-mb-sm">
              4. Nursing Orders
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
              @update:model-value="autoSaveDraft('nursing_orders')"
            />
          </div>

          <q-separator class="q-my-md" />

          <!-- Nursing Intervention -->
          <div>
            <div class="text-subtitle2 text-weight-bold glass-text q-mb-sm">
              5. Nursing Intervention
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
              @update:model-value="autoSaveDraft('nursing_intervention')"
            />
          </div>

          <q-separator class="q-my-md" />

          <!-- Evaluation -->
          <div>
            <div class="text-subtitle2 text-weight-bold glass-text q-mb-sm">
              6. Evaluation
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
              @update:model-value="autoSaveDraft('evaluation')"
            />
          </div>

          <q-separator class="q-my-md" />

          <div class="row justify-end q-gutter-sm">
            <HmsButton variant="secondary" type="button" @click="resetForm">
              Cancel
            </HmsButton>
            <HmsButton variant="primary" type="submit" :loading="saving">
              {{ editingDocId ? 'Update Documentation' : 'Save Documentation' }}
            </HmsButton>
          </div>
        </q-form>
      </q-expansion-item>
    </section>

    <!-- Previous Documentation List -->
    <section v-if="previousDocumentations.length > 0" class="am-panel">
      <div class="am-panel-head">
        <h2 class="hms-section-title">Previous Nurse Mid Documentations</h2>
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
    </section>
  </q-page>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { useQuasar } from 'quasar';
import HmsPageHeader from '../components/ui/HmsPageHeader.vue';
import HmsButton from '../components/ui/HmsButton.vue';
import { consultationAPI } from '../services/api';
import { useAuthStore } from '../stores/auth';

const $q = useQuasar();
const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();

const nmdPatientInitials = (info) => {
  if (!info) return '?';
  const a = (info.patient_name || '').trim().charAt(0);
  const b = (info.patient_surname || '').trim().charAt(0);
  return ((a + b) || '?').toUpperCase();
};
const nmdPatientDisplayName = (info) => {
  if (!info) return '';
  return [info.patient_name, info.patient_surname, info.patient_other_names].filter(Boolean).join(' ');
};

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
  const userRole = authStore.userRole;
  const isAdmin = userRole === 'Admin';
  const isDoctor = userRole === 'Doctor';
  const isNurse = userRole === 'Nurse';
  const isOwner = doc.created_by === currentUserId;
  // Admin and Doctor can edit any documentation
  // Nurse can edit their own documentation
  return isAdmin || isDoctor || (isNurse && isOwner);
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
.am-panel {
  padding: 1.05rem 1.15rem;
  border-radius: var(--hms-radius-xl);
  background: var(--hms-panel-bg);
  border: 1px solid var(--hms-border);
  box-shadow: var(--hms-shadow-md);
  margin-bottom: 0.95rem;
}
.am-panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  flex-wrap: wrap;
  margin-bottom: 0.85rem;
}

.ipd-patient-hero {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.85rem;
  margin-bottom: 0.95rem;
  padding: 1rem 1.15rem;
  border-radius: var(--hms-radius-xl);
  background: var(--hms-panel-bg);
  border: 1px solid var(--hms-border);
  box-shadow: var(--hms-shadow-md);
  position: sticky;
  top: 0.55rem;
  z-index: 6;
}
.ipd-hero-main { display: flex; align-items: center; gap: 0.85rem; min-width: 0; }
.ipd-hero-avatar {
  width: 3rem; height: 3rem; border-radius: 999px;
  display: grid; place-items: center;
  font-weight: 700; font-size: 0.85rem;
  color: var(--hms-accent); background: var(--hms-accent-muted);
  flex-shrink: 0;
}
.ipd-hero-name {
  margin: 0;
  font-size: clamp(1.15rem, 2vw, 1.45rem);
  font-weight: 750;
  color: var(--hms-text-primary);
  letter-spacing: -0.02em;
}
.ipd-hero-meta {
  margin-top: 0.2rem;
  font-size: var(--hms-text-sm);
  color: var(--hms-text-secondary);
  display: flex; flex-wrap: wrap; align-items: center; gap: 0.15rem;
}
.ipd-hero-meta .sep { margin: 0 0.3rem; opacity: 0.4; }
.ipd-hero-meta .mono,
.mono { font-variant-numeric: tabular-nums; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }
.ipd-hero-actions { display: flex; flex-wrap: wrap; gap: 0.45rem; align-items: center; }
.balance-pill {
  display: inline-flex; flex-direction: column; align-items: flex-end;
  padding: 0.35rem 0.7rem; border-radius: var(--hms-radius-lg);
  border: 1px solid var(--hms-border); background: var(--hms-surface);
  cursor: pointer; font: inherit;
}
.balance-pill .balance-label {
  font-size: 0.62rem; font-weight: 700; letter-spacing: 0.05em;
  text-transform: uppercase; color: var(--hms-text-muted);
}
.balance-pill .balance-value { font-weight: 700; font-variant-numeric: tabular-nums; }
.balance-pill.due .balance-value { color: var(--hms-critical); }
.balance-pill.ok .balance-value { color: var(--hms-success); }
.balance-pill.neutral .balance-value { color: var(--hms-text-secondary); }
@media (max-width: 720px) {
  .ipd-patient-hero { position: static; }
}
:deep(.glass-card) {
  border-radius: var(--hms-radius-xl) !important;
  border: 1px solid var(--hms-border) !important;
  box-shadow: var(--hms-shadow-md) !important;
  background: var(--hms-panel-bg) !important;
}
:deep(.text-h6.glass-text),
:deep(.glass-text.text-h6) {
  font-size: var(--hms-text-lg) !important;
  font-weight: 700 !important;
  color: var(--hms-text-primary) !important;
}


/* Light mode adjustments */
.body--light .glass-text {
  color: rgba(0, 0, 0, 0.87) !important;
}

/* Dark mode adjustments */
.body--dark .glass-text {
  color: rgba(255, 255, 255, 0.9) !important;
}
</style>

