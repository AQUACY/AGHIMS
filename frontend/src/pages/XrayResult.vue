<template>
  <q-page class="hms-page">
    <HmsPageHeader title="X-ray result" subtitle="Enter or review X-ray findings.">
      <template #actions>
        <HmsButton variant="secondary" size="sm" @click="$router.push('/xray')">
          Back
        </HmsButton>
      </template>
    </HmsPageHeader>

    <div v-if="investigation && patient" class="result-hero">
      <div class="result-hero-main">
        <div class="result-hero-avatar">{{ patientInitials }}</div>
        <div>
          <div class="result-hero-name-row">
            <h1 class="result-hero-name">{{ patientDisplayName }}</h1>
            <HmsBadge :tone="patient.insured ? 'success' : 'warning'">
              {{ patient.insured ? 'Insured' : 'Cash & carry' }}
            </HmsBadge>
            <HmsBadge v-if="investigation?.status" :tone="statusTone(investigation.status)">
              {{ investigation.status }}
            </HmsBadge>
          </div>
          <div class="result-hero-meta">
            <span class="mono">{{ patient.card_number || '—' }}</span>
            <span class="sep">·</span>
            <span>{{ patient.gender || '—' }}</span>
            <span class="sep">·</span>
            <span>{{ patient.age != null ? patient.age : '—' }}</span>
            <span class="sep">·</span>
            <span>CCC {{ patient.ccc_number || encounter?.ccc_number || '—' }}</span>
            <span class="sep">·</span>
            <span>{{ formatDate(encounter?.created_at) || '—' }}</span>
          </div>
        </div>
      </div>
      <div class="result-hero-actions">
        <div
          v-if="encounterBillInfo.totalAmount !== null"
          class="balance-pill"
          :class="encounterBillInfo.remainingBalance > 0 ? 'due' : (encounterBillInfo.totalAmount > 0 ? 'ok' : 'neutral')"
        >
          <span class="balance-label">Outstanding</span>
          <span class="balance-value">GHC {{ encounterBillInfo.remainingBalance.toFixed(2) }}</span>
        </div>
      </div>
    </div>

    <section v-if="investigation" class="result-panel">
      <div class="result-panel-head">
        <h2 class="hms-section-title">Investigation</h2>
      </div>
      <div class="result-meta-grid">
        <div class="result-meta-item">
          <div class="result-meta-label">Procedure</div>
          <div class="result-meta-value">{{ investigation.procedure_name || 'N/A' }}</div>
        </div>
        <div class="result-meta-item">
          <div class="result-meta-label">G-DRG</div>
          <div class="result-meta-value">{{ investigation.gdrg_code || 'N/A' }}</div>
        </div>
        <div class="result-meta-item">
          <div class="result-meta-label">Requested by</div>
          <div class="result-meta-value">{{ investigation.requested_by_name || 'N/A' }}</div>
        </div>
        <div class="result-meta-item">
          <div class="result-meta-label">Confirmed by</div>
          <div class="result-meta-value">{{ investigation.confirmed_by_name || 'N/A' }}</div>
        </div>
        <div class="result-meta-item">
          <div class="result-meta-label">Completed by</div>
          <div class="result-meta-value">{{ investigation.completed_by_name || 'N/A' }}</div>
        </div>
        <div class="result-meta-item">
          <div class="result-meta-label">Entered by</div>
          <div class="result-meta-value">{{ xrayResult?.entered_by_name || 'N/A' }}</div>
        </div>
        <div class="result-meta-item">
          <div class="result-meta-label">Updated by</div>
          <div class="result-meta-value">{{ xrayResult?.updated_by_name || 'N/A' }}</div>
        </div>
      </div>
      <div v-if="investigation.notes" class="result-note-callout">
        <div class="result-meta-label">Doctor's notes</div>
        <div class="result-note-body">{{ investigation.notes }}</div>
      </div>
    </section>

    <section class="result-panel result-form-panel">
      <div class="result-panel-head">
        <h2 class="hms-section-title">{{ editingResult ? 'Edit result' : 'Add result' }}</h2>
        <p class="result-panel-sub">Enter X-ray findings and attach supporting files.</p>
      </div>
      <div
        v-if="investigation?.status === 'completed' && !canEditResult"
        class="result-warn-banner"
        role="status"
      >
        <q-icon name="warning" size="20px" />
        <div>
          This investigation is completed. Only Admin and Xray Head can edit completed investigations. Please contact Xray Head to revert the status if changes are needed.
        </div>
      </div>
      <q-form @submit="saveXrayResult" class="q-gutter-md">
          <q-input
            v-model="resultForm.results_text"
            filled
            type="textarea"
            rows="10"
            label="Results Text"
            hint="Enter x-ray results/findings"
            :rules="[(val) => !!val || 'Results text is required']"
          />
          <q-file
            v-model="resultForm.attachments"
            filled
            multiple
            label="Upload PDF/Attachments"
            accept=".pdf,.jpg,.jpeg,.png,.doc,.docx"
            hint="Upload one or more PDF, Word document, or image files"
            @update:model-value="onFilesSelected"
          >
            <template v-slot:prepend>
              <q-icon name="attach_file" />
            </template>
          </q-file>
          <div v-if="resultForm.attachments && resultForm.attachments.length > 0" class="q-mt-sm">
            <div class="text-caption text-grey-7 q-mb-xs">Selected files:</div>
            <q-list dense bordered>
              <q-item v-for="(file, index) in resultForm.attachments" :key="index">
                <q-item-section>
                  <q-item-label>{{ file.name }}</q-item-label>
                  <q-item-label caption>{{ formatFileSize(file.size) }}</q-item-label>
                </q-item-section>
                <q-item-section side>
                  <q-btn
                    flat
                    dense
                    round
                    icon="close"
                    size="sm"
                    @click="removeFile(index)"
                  />
                </q-item-section>
              </q-item>
            </q-list>
          </div>
          <div v-if="existingAttachments && existingAttachments.length > 0" class="text-caption text-grey-7 q-mt-sm">
            <div class="q-mb-xs">Existing attachments:</div>
            <q-list dense bordered>
              <q-item v-for="(attachment, index) in existingAttachments" :key="index">
                <q-item-section>
                  <q-item-label>{{ attachment.split('/').pop() }}</q-item-label>
                </q-item-section>
                <q-item-section side>
                  <q-btn
                    flat
                    dense
                    size="sm"
                    icon="open_in_new"
                    label="Open"
                    @click="downloadExistingAttachment(attachment)"
                    class="q-mr-xs"
                  />
                  <q-btn
                    flat
                    dense
                    size="sm"
                    icon="delete"
                    color="negative"
                    @click="removeExistingAttachment(attachment, index)"
                  >
                    <q-tooltip>Remove attachment</q-tooltip>
                  </q-btn>
                </q-item-section>
              </q-item>
            </q-list>
          </div>
          <div class="result-form-actions">
            <HmsButton variant="secondary" @click="$router.push('/xray')">
              Cancel
            </HmsButton>
            <HmsButton
              variant="primary"
              type="submit"
              :loading="savingResult"
              :disabled="!canEditResult"
            >
              Save
            </HmsButton>
          </div>
        </q-form>
    </section>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useQuasar } from 'quasar';
import { consultationAPI, encountersAPI, patientsAPI, billingAPI } from '../services/api';
import { useAuthStore } from '../stores/auth';
import HmsPageHeader from '../components/ui/HmsPageHeader.vue';
import HmsButton from '../components/ui/HmsButton.vue';
import HmsBadge from '../components/ui/HmsBadge.vue';

const $q = useQuasar();
const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();

const investigation = ref(null);
const patient = ref(null);
const encounter = ref(null);
const xrayResult = ref(null);
const loading = ref(false);
const savingResult = ref(false);
const editingResult = ref(false);
const encounterBillInfo = ref({
  totalAmount: null,
  paidAmount: null,
  remainingBalance: null,
});

// Check if user can edit result (Admin and Xray Head can edit completed investigations)
const canEditResult = computed(() => {
  if (!investigation.value) return true;
  // If investigation is completed, only Admin and Xray Head can edit
  if (investigation.value.status === 'completed') {
    return authStore.userRole === 'Admin' || authStore.userRole === 'Xray Head';
  }
  // For non-completed investigations, all Xray staff can edit
  return true;
});

const patientDisplayName = computed(() => {
  if (!patient.value) return '';
  return [patient.value.name, patient.value.surname, patient.value.other_names].filter(Boolean).join(' ');
});

const patientInitials = computed(() => {
  if (!patient.value) return '?';
  const a = (patient.value.name || '').trim().charAt(0);
  const b = (patient.value.surname || '').trim().charAt(0);
  return ((a + b) || '?').toUpperCase();
});

const statusTone = (status) => {
  const s = String(status || '').toLowerCase();
  if (s === 'completed') return 'success';
  if (s === 'confirmed') return 'info';
  if (s === 'requested') return 'warning';
  return 'neutral';
};

const resultForm = ref({
  investigation_id: null,
  results_text: '',
  attachments: [],
});
const existingAttachments = ref([]);

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

const loadInvestigation = async () => {
  const investigationId = route.params.investigationId;
  if (!investigationId) {
    $q.notify({
      type: 'negative',
      message: 'Investigation ID is required',
    });
    router.push('/xray');
    return;
  }

  const source = route.query.source; // 'opd' or 'inpatient' from query param
  const expectedCardNumber = route.query.card_number; // Expected patient card number
  
  loading.value = true;
  try {
    let invResponse;
    let isInpatient = false;
    
    // If source is specified in query params, use it to determine which API to call first
    if (source === 'inpatient') {
      // Try IPD first if source indicates inpatient
      try {
        invResponse = await consultationAPI.getInpatientInvestigation(parseInt(investigationId));
        investigation.value = invResponse.data;
        isInpatient = true;
        
        // Verify patient card number matches if provided
        if (expectedCardNumber && investigation.value.patient_card_number !== expectedCardNumber) {
          throw new Error('Patient mismatch');
        }
      } catch (ipdError) {
        if (ipdError.message === 'Patient mismatch' || (expectedCardNumber && ipdError.response?.status !== 404)) {
          // Patient doesn't match or other error - try OPD
          try {
            invResponse = await consultationAPI.getInvestigation(parseInt(investigationId));
            investigation.value = invResponse.data;
            isInpatient = false;
            
            // Verify patient card number matches
            if (expectedCardNumber && investigation.value.patient_card_number !== expectedCardNumber) {
              throw new Error('Investigation not found for this patient');
            }
          } catch (opdError) {
            $q.notify({
              type: 'negative',
              message: 'Investigation not found or patient mismatch',
            });
            router.push('/xray');
            return;
          }
        } else {
          throw ipdError;
        }
      }
    } else if (source === 'opd') {
      // Explicitly OPD - try OPD first
      try {
        invResponse = await consultationAPI.getInvestigation(parseInt(investigationId));
        investigation.value = invResponse.data;
        isInpatient = false;
        
        // Verify patient card number matches if provided
        if (expectedCardNumber && investigation.value.patient_card_number !== expectedCardNumber) {
          throw new Error('Patient mismatch');
        }
      } catch (opdError) {
        // If OPD fails with 404 or patient mismatch, try IPD as fallback
        if (opdError.response?.status === 404 || opdError.message === 'Patient mismatch') {
          try {
            invResponse = await consultationAPI.getInpatientInvestigation(parseInt(investigationId));
            investigation.value = invResponse.data;
            isInpatient = true;
            
            // Verify patient card number matches
            if (expectedCardNumber && investigation.value.patient_card_number !== expectedCardNumber) {
              throw new Error('Investigation not found for this patient');
            }
          } catch (ipdError) {
            $q.notify({
              type: 'negative',
              message: 'Investigation not found or patient mismatch',
            });
            router.push('/xray');
            return;
          }
        } else {
          throw opdError;
        }
      }
    } else {
      // Source not specified: Try IPD first, then OPD (to handle IPD investigations correctly)
      // This ensures IPD investigations are found even if source parameter is missing
      let found = false;
      
      // Try IPD first
      try {
        invResponse = await consultationAPI.getInpatientInvestigation(parseInt(investigationId));
        investigation.value = invResponse.data;
        isInpatient = true;
        found = true;
        
        // Verify patient card number matches if provided
        if (expectedCardNumber && investigation.value.patient_card_number !== expectedCardNumber) {
          throw new Error('Patient mismatch');
        }
      } catch (ipdError) {
        // IPD not found or mismatch - try OPD
        if (ipdError.response?.status === 404 || ipdError.message === 'Patient mismatch') {
          try {
            invResponse = await consultationAPI.getInvestigation(parseInt(investigationId));
            investigation.value = invResponse.data;
            isInpatient = false;
            found = true;
            
            // Verify patient card number matches
            if (expectedCardNumber && investigation.value.patient_card_number !== expectedCardNumber) {
              throw new Error('Investigation not found for this patient');
            }
          } catch (opdError) {
            $q.notify({
              type: 'negative',
              message: 'Investigation not found or patient mismatch',
            });
            router.push('/xray');
            return;
          }
        } else {
          // Other error from IPD call - rethrow
          throw ipdError;
        }
      }
      
      if (!found) {
        $q.notify({
          type: 'negative',
          message: 'Investigation not found',
        });
        router.push('/xray');
        return;
      }
    }
    
    // Store investigation source for reference
    investigation.value.source = isInpatient ? 'inpatient' : 'opd';
    
    if (!investigation.value) {
      $q.notify({
        type: 'negative',
        message: 'Investigation not found',
      });
      router.push('/xray');
      return;
    }

    // For IPD investigations, use patient_id directly from investigation response if available
    // This ensures we get the correct patient even if encounter_id points to a different encounter
    if (isInpatient) {
      if (investigation.value.patient_id) {
        // Use patient_id directly from investigation response (most reliable)
        try {
          const patientResponse = await patientsAPI.get(investigation.value.patient_id);
          patient.value = patientResponse.data;
        } catch (error) {
          console.error('Failed to load patient by ID from investigation:', error);
          // Fallback to card number if patient_id lookup fails
          if (investigation.value.patient_card_number) {
            try {
              const patientResponse = await patientsAPI.getByCard(investigation.value.patient_card_number);
              const patients = patientResponse.data || [];
              if (patients.length > 0) {
                // Find patient that matches the patient_id if available, otherwise use first
                patient.value = investigation.value.patient_id 
                  ? patients.find(p => p.id === investigation.value.patient_id) || patients[0]
                  : patients[0];
              }
            } catch (cardError) {
              console.error('Failed to load patient by card from investigation:', cardError);
            }
          }
        }
      } else if (investigation.value.patient_card_number) {
        // Fallback: use card number if patient_id not available
        try {
          const patientResponse = await patientsAPI.getByCard(investigation.value.patient_card_number);
          const patients = patientResponse.data || [];
          if (patients.length > 0) {
            patient.value = patients[0];
          }
        } catch (error) {
          console.error('Failed to load patient by card from investigation:', error);
        }
      }
    }
    
    // Load encounter details (for both OPD and IPD)
    if (investigation.value.encounter_id) {
      try {
        const encounterResponse = await encountersAPI.get(investigation.value.encounter_id);
        encounter.value = encounterResponse.data;
        
        // Load bills for this encounter
        await loadEncounterBills(encounter.value.id);
        
        // Verify encounter matches investigation's patient_card_number if available
        if (investigation.value.patient_card_number && encounter.value.patient_card_number) {
          if (investigation.value.patient_card_number !== encounter.value.patient_card_number) {
            console.warn(`Mismatch: Investigation patient card (${investigation.value.patient_card_number}) != Encounter patient card (${encounter.value.patient_card_number})`);
            $q.notify({
              type: 'warning',
              message: 'Warning: Patient information mismatch detected. Please verify the investigation belongs to this patient.',
            });
          }
        }
        
        // Load patient from encounter to ensure correct patient
        // For IPD, we already loaded patient from investigation above, so only load for OPD
        if (!isInpatient && encounter.value && encounter.value.patient_id) {
          try {
            const patientResponse = await patientsAPI.get(encounter.value.patient_id);
            patient.value = patientResponse.data;
            
            // Double-check: verify patient card number matches investigation
            if (investigation.value.patient_card_number && patient.value.card_number) {
              if (investigation.value.patient_card_number !== patient.value.card_number) {
                console.error(`CRITICAL: Patient card mismatch! Investigation: ${investigation.value.patient_card_number}, Patient: ${patient.value.card_number}`);
                $q.notify({
                  type: 'negative',
                  message: `Error: Patient mismatch detected. Investigation is for ${investigation.value.patient_card_number} but encounter is for ${patient.value.card_number}`,
                });
              }
            }
          } catch (error) {
            console.error('Failed to load patient by ID:', error);
            // Fallback: try loading by card number from investigation
            if (investigation.value.patient_card_number) {
              try {
                const patientResponse = await patientsAPI.getByCard(investigation.value.patient_card_number);
                const patients = patientResponse.data || [];
                if (patients.length > 0) {
                  // For IPD, prefer the patient that matches the encounter's patient_id if available
                  let correctPatient = patients[0];
                  if (encounter.value && encounter.value.patient_id) {
                    const matchingPatient = patients.find(p => p.id === encounter.value.patient_id);
                    if (matchingPatient) {
                      correctPatient = matchingPatient;
                    } else {
                      console.warn(`Patient from card lookup doesn't match encounter patient_id. Using first match.`);
                    }
                  }
                  patient.value = correctPatient;
                } else {
                  throw new Error('Patient not found');
                }
              } catch (cardError) {
                console.error('Failed to load patient by card:', cardError);
                // Final fallback: use patient info from investigation response
                if (investigation.value.patient_name) {
                  const nameParts = investigation.value.patient_name.split(' ');
                  patient.value = {
                    id: encounter.value?.patient_id || null,
                    card_number: investigation.value.patient_card_number,
                    name: nameParts[0] || 'N/A',
                    surname: nameParts.slice(1).join(' ') || '',
                    ccc_number: encounter.value?.ccc_number || null,
                    date_of_birth: null,
                    age: null,
                    gender: null,
                    insured: false,
                    insurance_id: null,
                  };
                }
              }
            }
          }
        } else if (!isInpatient && !patient.value && investigation.value.patient_card_number) {
          // For OPD, if patient not loaded, try by card number
          try {
            const patientResponse = await patientsAPI.getByCard(investigation.value.patient_card_number);
            const patients = patientResponse.data || [];
            if (patients.length > 0) {
              patient.value = patients[0];
            }
          } catch (cardError) {
            console.error('Failed to load patient by card:', cardError);
          }
        }
        
        // For IPD, verify patient matches if we have both - but don't override patient from investigation
        if (isInpatient && patient.value && encounter.value && encounter.value.patient_id) {
          if (patient.value.id !== encounter.value.patient_id) {
            console.warn('Patient ID mismatch between investigation and encounter. Using patient from investigation.');
            // Keep the patient from investigation (already loaded above) - don't override
          }
        }
      } catch (error) {
        console.error('Failed to load encounter:', error);
        // If encounter fails but we have patient from investigation, that's okay
        if (!patient.value && investigation.value.patient_card_number) {
          try {
            const patientResponse = await patientsAPI.getByCard(investigation.value.patient_card_number);
            const patients = patientResponse.data || [];
            if (patients.length > 0) {
              patient.value = patients[0];
            }
          } catch (cardError) {
            console.error('Failed to load patient:', cardError);
          }
        }
      }
    } else {
      // No encounter_id - load patient by card number from investigation
      if (!patient.value && investigation.value.patient_card_number) {
        try {
          const patientResponse = await patientsAPI.getByCard(investigation.value.patient_card_number);
          const patients = patientResponse.data || [];
          if (patients.length > 0) {
            patient.value = patients[0];
          }
        } catch (error) {
          console.error('Failed to load patient:', error);
        }
      }
    }

    // Check if result already exists
    // IMPORTANT: Backend will check IPD first to prevent ID collisions
    // Since we've already loaded the correct investigation (IPD or OPD),
    // the backend should return the matching result
    try {
      const resultResponse = await consultationAPI.getXrayResult(investigation.value.id);
      const existingResult = resultResponse.data;
      
      // Verify the result belongs to this investigation
      // Backend handles IPD/OPD separation, but verify ID matches
      if (existingResult && existingResult.investigation_id === investigation.value.id) {
        xrayResult.value = existingResult;
        editingResult.value = true;
        resultForm.value = {
          investigation_id: investigation.value.id,
          results_text: existingResult.results_text || '',
          attachments: [],
        };
        // Parse existing attachments (can be JSON array or single string)
        if (existingResult.attachment_path) {
          try {
            const parsed = JSON.parse(existingResult.attachment_path);
            existingAttachments.value = Array.isArray(parsed) ? parsed : [existingResult.attachment_path];
          } catch {
            // If not JSON, treat as single attachment
            existingAttachments.value = [existingResult.attachment_path];
          }
        } else {
          existingAttachments.value = [];
        }
      } else {
        // No result exists or mismatch - start fresh
        console.log('No matching xray result found for investigation:', investigation.value.id, 'Source:', investigation.value.source);
        xrayResult.value = null;
        editingResult.value = false;
        resultForm.value = {
          investigation_id: investigation.value?.id || parseInt(route.params.investigationId),
          results_text: '',
          attachments: [],
        };
        existingAttachments.value = [];
      }
    } catch (error) {
      // No result exists yet or error loading
      console.log('No xray result found for investigation:', investigation.value?.id || route.params.investigationId, 'Source:', investigation.value?.source || 'unknown', error);
      xrayResult.value = null;
      editingResult.value = false;
      resultForm.value = {
        investigation_id: investigation.value?.id || parseInt(route.params.investigationId),
        results_text: '',
        attachments: [],
      };
      existingAttachments.value = [];
    }
  } catch (error) {
    console.error('Failed to load investigation:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to load investigation details',
    });
    router.push('/xray');
  } finally {
    loading.value = false;
  }
};

const onFilesSelected = (files) => {
  // Files are automatically set in resultForm.attachments
};

const removeFile = (index) => {
  resultForm.value.attachments.splice(index, 1);
};

const formatFileSize = (bytes) => {
  if (!bytes) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
};

const removeExistingAttachment = async (attachmentPath, index) => {
  if (!attachmentPath || !resultForm.value.investigation_id) {
    return;
  }

  $q.dialog({
    title: 'Confirm Removal',
    message: `Are you sure you want to remove "${attachmentPath.split('/').pop()}"?`,
    cancel: true,
    persistent: true
  }).onOk(async () => {
    try {
      await consultationAPI.deleteXrayResultAttachment(resultForm.value.investigation_id, attachmentPath);
      
      // Remove from local array
      existingAttachments.value.splice(index, 1);
      
      $q.notify({
        type: 'positive',
        message: 'Attachment removed successfully',
      });
      
      // Reload the investigation to refresh data
      await loadInvestigation();
    } catch (error) {
      console.error('Remove attachment error:', error);
      $q.notify({
        type: 'negative',
        message: error.response?.data?.detail || 'Failed to remove attachment',
      });
    }
  });
};

const saveXrayResult = async () => {
  // Ensure we have a valid investigation_id
  const investigationId = resultForm.value.investigation_id || investigation.value?.id || parseInt(route.params.investigationId);
  
  if (!investigationId) {
    $q.notify({
      type: 'negative',
      message: 'Investigation ID is missing. Please reload the page.',
    });
    return;
  }

  savingResult.value = true;
  try {
    const formData = new FormData();
    // Ensure investigation_id is sent as a number
    formData.append('investigation_id', String(investigationId));
    if (resultForm.value.results_text) {
      formData.append('results_text', resultForm.value.results_text);
    }
    // Append all attachments
    if (resultForm.value.attachments && resultForm.value.attachments.length > 0) {
      resultForm.value.attachments.forEach((file) => {
        formData.append('attachments', file);
      });
    }

    await consultationAPI.createXrayResult(formData);
    $q.notify({
      type: 'positive',
      message: 'X-ray result saved successfully',
    });
    
    // Clear the form attachments (they've been saved)
    resultForm.value.attachments = [];
    
    // Reload the investigation to show updated results
    await loadInvestigation();
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to save x-ray result',
    });
  } finally {
    savingResult.value = false;
  }
};

const downloadExistingAttachment = async (attachmentPath) => {
  if (!attachmentPath || !resultForm.value.investigation_id) {
    $q.notify({
      type: 'warning',
      message: 'No attachment available to open',
    });
    return;
  }

  try {
    const response = await consultationAPI.downloadXrayResultAttachment(resultForm.value.investigation_id, attachmentPath);
    
    const contentType = response.headers['content-type'] || response.headers['Content-Type'] || 'application/pdf';
    const blob = response.data instanceof Blob 
      ? response.data 
      : new Blob([response.data], { type: contentType });
    
    const contentDisposition = response.headers['content-disposition'] || 
                                response.headers['Content-Disposition'];
    let filename = attachmentPath.split('/').pop() || 'xray_result.pdf';
    
    if (contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
      if (filenameMatch && filenameMatch[1]) {
        filename = filenameMatch[1].replace(/['"]/g, '');
      }
    }
    
    // Check if file is PDF or image (can be opened in browser)
    const fileExt = filename.toLowerCase().split('.').pop();
    const isPDF = fileExt === 'pdf' || contentType.includes('application/pdf');
    const isImage = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp'].includes(fileExt) || 
                    contentType.startsWith('image/');
    
    const url = window.URL.createObjectURL(blob);
    
    if (isPDF || isImage) {
      // Open in new tab for PDFs and images
      window.open(url, '_blank');
      // Revoke URL after a delay to allow browser to load it
      setTimeout(() => {
        window.URL.revokeObjectURL(url);
      }, 1000);
      
      $q.notify({
        type: 'positive',
        message: 'File opened in new tab',
      });
    } else {
      // Download other file types (doc, docx, etc.)
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
    }
  } catch (error) {
    console.error('Download error:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to open attachment',
    });
  }
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

onMounted(() => {
  loadInvestigation();
});
</script>

<style scoped>
.result-hero {
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
.result-hero-main { display: flex; align-items: center; gap: 0.85rem; min-width: 0; }
.result-hero-avatar {
  width: 3rem; height: 3rem; border-radius: 999px;
  display: grid; place-items: center;
  font-weight: 700; font-size: 0.85rem;
  color: var(--hms-accent); background: var(--hms-accent-muted);
  flex-shrink: 0;
}
.result-hero-name-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.45rem;
}
.result-hero-name {
  margin: 0;
  font-size: clamp(1.15rem, 2vw, 1.45rem);
  font-weight: 750;
  color: var(--hms-text-primary);
  letter-spacing: -0.02em;
}
.result-hero-meta {
  margin-top: 0.2rem;
  font-size: var(--hms-text-sm);
  color: var(--hms-text-secondary);
  display: flex; flex-wrap: wrap; align-items: center; gap: 0.15rem;
}
.result-hero-meta .sep { margin: 0 0.3rem; opacity: 0.4; }
.result-hero-meta .mono,
.mono { font-variant-numeric: tabular-nums; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }
.result-hero-actions { display: flex; flex-wrap: wrap; gap: 0.45rem; align-items: center; }
.balance-pill {
  display: inline-flex; flex-direction: column; align-items: flex-end;
  padding: 0.35rem 0.7rem; border-radius: var(--hms-radius-lg);
  border: 1px solid var(--hms-border); background: var(--hms-surface);
  font: inherit;
}
.balance-pill .balance-label {
  font-size: 0.62rem; font-weight: 700; letter-spacing: 0.05em;
  text-transform: uppercase; color: var(--hms-text-muted);
}
.balance-pill .balance-value { font-weight: 700; font-variant-numeric: tabular-nums; }
.balance-pill.due .balance-value { color: var(--hms-critical); }
.balance-pill.ok .balance-value { color: var(--hms-success); }
.balance-pill.neutral .balance-value { color: var(--hms-text-secondary); }

.result-panel {
  padding: 1.05rem 1.15rem;
  border-radius: var(--hms-radius-xl);
  background: var(--hms-panel-bg);
  border: 1px solid var(--hms-border);
  box-shadow: var(--hms-shadow-md);
  margin-bottom: 0.95rem;
}
.result-panel-head { margin-bottom: 0.85rem; }
.result-panel-sub {
  margin: 0.2rem 0 0;
  font-size: var(--hms-text-sm);
  color: var(--hms-text-muted);
}
.result-meta-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 0.85rem 1rem;
}
.result-meta-label {
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--hms-text-muted);
  margin-bottom: 0.2rem;
}
.result-meta-value {
  font-size: var(--hms-text-sm);
  font-weight: 600;
  color: var(--hms-text-primary);
}
.result-note-callout {
  margin-top: 0.95rem;
  padding: 0.75rem 0.9rem;
  border-radius: var(--hms-radius-lg);
  background: var(--hms-surface);
  border: 1px solid var(--hms-border);
}
.result-note-body {
  margin-top: 0.25rem;
  font-size: var(--hms-text-sm);
  color: var(--hms-text-secondary);
  line-height: 1.45;
  white-space: pre-wrap;
}
.result-form-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem;
  justify-content: flex-end;
  margin-top: 1rem;
  padding-top: 0.85rem;
  border-top: 1px solid var(--hms-border);
}
.result-warn-banner {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: 0.65rem;
  margin-bottom: 0.95rem;
  padding: 0.75rem 0.9rem;
  border-radius: var(--hms-radius-lg);
  background: var(--hms-warning-muted, rgba(245, 158, 11, 0.12));
  border: 1px solid rgba(245, 158, 11, 0.28);
  color: var(--hms-text-primary);
  font-size: var(--hms-text-sm);
  line-height: 1.4;
}
@media (max-width: 720px) {
  .result-hero { position: static; }
}
</style>

