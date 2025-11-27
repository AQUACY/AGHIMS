<template>
  <q-page class="q-pa-md">
    <div class="row items-center q-mb-md">
      <q-btn
        flat
        icon="arrow_back"
        label="Back to X-ray"
        @click="$router.push('/xray')"
        class="q-mr-md"
      />
      <div class="text-h4 text-weight-bold glass-text">X-ray Result Entry</div>
    </div>

    <!-- Patient Information -->
    <q-card v-if="investigation && patient" class="q-mb-md glass-card" flat>
      <q-card-section>
        <div class="text-h6 q-mb-md glass-text">Patient Information</div>
        <div class="row q-gutter-md">
          <div class="col-12 col-md-3">
            <div class="text-caption text-grey-7">Patient Name</div>
            <div class="text-body1 text-weight-medium">{{ patient.name }} {{ patient.surname || '' }}<span v-if="patient.other_names"> {{ patient.other_names }}</span></div>
          </div>
          <div class="col-12 col-md-3">
            <div class="text-caption text-grey-7">Card Number</div>
            <div class="text-body1 text-weight-medium">{{ patient.card_number || 'N/A' }}</div>
          </div>
          <div class="col-12 col-md-3">
            <div class="text-caption text-grey-7">CCC Number</div>
            <div class="text-body1 text-weight-medium">{{ patient.ccc_number || encounter?.ccc_number || 'N/A' }}</div>
          </div>
          <div class="col-12 col-md-3">
            <div class="text-caption text-grey-7">Insurance Status</div>
            <div class="text-body1 text-weight-medium">
              <q-badge :color="patient.insured ? 'positive' : 'grey'" :label="patient.insured ? 'Insured' : 'Not Insured'" />
            </div>
          </div>
        </div>
        <div class="row q-gutter-md q-mt-md">
          <div class="col-12 col-md-3">
            <div class="text-caption text-grey-7">Date of Birth</div>
            <div class="text-body1 text-weight-medium">{{ formatDateOnly(patient.date_of_birth) }}</div>
          </div>
          <div class="col-12 col-md-3">
            <div class="text-caption text-grey-7">Age</div>
            <div class="text-body1 text-weight-medium">{{ patient.age || 'N/A' }}</div>
          </div>
          <div class="col-12 col-md-3">
            <div class="text-caption text-grey-7">Sex</div>
            <div class="text-body1 text-weight-medium">{{ patient.gender || 'N/A' }}</div>
          </div>
          <div class="col-12 col-md-3">
            <div class="text-caption text-grey-7">Encounter Date</div>
            <div class="text-body1 text-weight-medium">{{ formatDate(encounter?.created_at) || 'N/A' }}</div>
          </div>
        </div>
        <div v-if="encounterBillInfo.totalAmount !== null" class="row q-gutter-md q-mt-md">
          <div class="col-12">
            <div class="text-body2" :class="encounterBillInfo.remainingBalance > 0 ? 'text-negative text-weight-bold' : 'text-secondary'">
              <q-icon name="receipt" size="14px" class="q-mr-xs" />
              <strong>Total Bills:</strong> GHC {{ encounterBillInfo.totalAmount.toFixed(2) }} 
              <span v-if="encounterBillInfo.remainingBalance > 0" class="text-negative">
                | Outstanding: GHC {{ encounterBillInfo.remainingBalance.toFixed(2) }}
              </span>
              <span v-else>
                | Outstanding: GHC 0.00
              </span>
            </div>
          </div>
        </div>
        <div v-if="patient.insured && patient.insurance_id" class="row q-gutter-md q-mt-md">
          <div class="col-12 col-md-3">
            <div class="text-caption text-grey-7">Insurance ID</div>
            <div class="text-body1 text-weight-medium">{{ patient.insurance_id || 'N/A' }}</div>
          </div>
          <div v-if="patient.insurance_start_date" class="col-12 col-md-3">
            <div class="text-caption text-grey-7">Insurance Start Date</div>
            <div class="text-body1 text-weight-medium">{{ formatDateOnly(patient.insurance_start_date) }}</div>
          </div>
          <div v-if="patient.insurance_end_date" class="col-12 col-md-3">
            <div class="text-caption text-grey-7">Insurance End Date</div>
            <div class="text-body1 text-weight-medium">{{ formatDateOnly(patient.insurance_end_date) }}</div>
          </div>
        </div>
      </q-card-section>
    </q-card>

    <!-- Investigation Details -->
    <q-card v-if="investigation" class="q-mb-md glass-card" flat>
      <q-card-section>
        <div class="text-h6 q-mb-md glass-text">Investigation Details</div>
        <div class="row q-gutter-md">
          <div class="col-12 col-md-6">
            <div class="text-caption text-grey-7">Procedure Name</div>
            <div class="text-body1 text-weight-medium">{{ investigation.procedure_name || 'N/A' }}</div>
          </div>
          <div class="col-12 col-md-6">
            <div class="text-caption text-grey-7">G-DRG Code</div>
            <div class="text-body1 text-weight-medium">{{ investigation.gdrg_code || 'N/A' }}</div>
          </div>
        </div>
        <div v-if="investigation.notes" class="row q-mt-md">
          <div class="col-12">
            <div class="text-caption text-grey-7">Doctor's Notes</div>
            <div class="text-body2 q-pa-sm" style="background-color: rgba(255, 255, 255, 0.1); border-radius: 4px;">
              {{ investigation.notes }}
            </div>
          </div>
        </div>
        <div class="row q-gutter-md q-mt-md">
          <div class="col-12 col-md-4">
            <div class="text-caption text-grey-7">Confirmed By</div>
            <div class="text-body1 text-weight-medium">{{ investigation.confirmed_by_name || 'N/A' }}</div>
          </div>
          <div class="col-12 col-md-4">
            <div class="text-caption text-grey-7">Completed By</div>
            <div class="text-body1 text-weight-medium">{{ investigation.completed_by_name || 'N/A' }}</div>
          </div>
          <div class="col-12 col-md-4">
            <div class="text-caption text-grey-7">Entered By</div>
            <div class="text-body1 text-weight-medium">{{ xrayResult?.entered_by_name || 'N/A' }}</div>
          </div>
          <div class="col-12 col-md-4">
            <div class="text-caption text-grey-7">Updated By</div>
            <div class="text-body1 text-weight-medium">{{ xrayResult?.updated_by_name || 'N/A' }}</div>
          </div>
        </div>
      </q-card-section>
    </q-card>

    <!-- X-ray Result Form -->
    <q-card class="q-mb-md glass-card" flat>
      <q-card-section>
        <div class="text-h6 q-mb-md glass-text">
          {{ editingResult ? 'Edit X-ray Result' : 'Add X-ray Result' }}
        </div>
        <q-banner
          v-if="investigation?.status === 'completed' && !canEditResult"
          class="bg-warning text-dark q-mb-md"
          rounded
        >
          <template v-slot:avatar>
            <q-icon name="warning" color="dark" />
          </template>
          This investigation is completed. Only Admin and Xray Head can edit completed investigations. Please contact Xray Head to revert the status if changes are needed.
        </q-banner>
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
          <div class="row q-gutter-md q-mt-md">
            <q-btn
              label="Cancel"
              flat
              @click="$router.push('/xray')"
              class="col"
            />
            <q-btn
              label="Save"
              type="submit"
              color="primary"
              class="col"
              :loading="savingResult"
              :disable="!canEditResult"
            />
          </div>
        </q-form>
      </q-card-section>
    </q-card>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useQuasar } from 'quasar';
import { consultationAPI, encountersAPI, patientsAPI, billingAPI } from '../services/api';
import { useAuthStore } from '../stores/auth';

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

