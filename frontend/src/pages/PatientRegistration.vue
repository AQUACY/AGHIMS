<template>
  <q-page class="q-pa-md">
    <div class="text-h4 q-mb-md text-weight-bold glass-text">Patient Registration</div>

    <q-card class="glass-card" flat>
      <q-card-section>
        <div class="text-h6 q-mb-md glass-text">Search Existing Patient</div>
        <div class="row q-gutter-md">
          <q-input
            v-model="cardNumber"
            filled
            label="Card Number"
            class="col-12 col-md-8"
            @keyup.enter="searchPatient"
          />
          <q-btn
            color="primary"
            label="Search"
            @click="searchPatient"
            class="col-12 col-md-4 glass-button"
            :loading="searching"
          />
        </div>
      </q-card-section>

      <q-card-section v-if="patientsStore.currentPatient">
        <div class="row items-center q-mb-md">
          <div class="text-h6 glass-text">Existing Patient Found</div>
          <q-space />
          <q-btn
            color="secondary"
            icon="edit"
            label="Edit Patient"
            @click="editPatient"
            class="q-mr-sm glass-button"
          />
          <q-btn
            color="primary"
            icon="visibility"
            label="View Profile"
            @click="viewPatientProfile"
            class="glass-button"
          />
        </div>
        <q-banner class="glass-card q-pa-md">
          <div class="text-body1 glass-text">
            <strong>Name:</strong> {{ patientsStore.currentPatient.name }}
            {{ patientsStore.currentPatient.surname }}
          </div>
          <div class="text-body1 glass-text">
            <strong>Card Number:</strong> {{ patientsStore.currentPatient.card_number }}
          </div>
          <div
            v-if="patientsStore.currentPatient.legacy_card_number"
            class="text-body1 glass-text"
          >
            <strong>Previous HMS Card:</strong> {{ patientsStore.currentPatient.legacy_card_number }}
          </div>
          <div class="text-body1 glass-text">
            <strong>Gender:</strong> {{ patientsStore.currentPatient.gender }}
          </div>
        </q-banner>
        <div class="row q-mt-md q-gutter-sm">
           <q-btn
             color="primary"
             icon="add"
             label="Create New Encounter"
             @click="createEncounterForExisting"
             class="glass-button"
           />
         </div>
       </q-card-section>
     </q-card>

     <!-- Create Encounter Dialog -->
     <q-dialog v-model="showEncounterDialog" persistent>
       <q-card style="min-width: 500px">
         <q-card-section>
           <div class="text-h6">Create Encounter</div>
         </q-card-section>

         <q-card-section>
           <q-form @submit="submitEncounterCreation" class="q-gutter-md">
             <q-select
               v-model="selectedEncounterServiceType"
               filled
               :options="serviceTypeOptions"
               label="Service Type (Department/Clinic) *"
               lazy-rules
               :rules="[(val) => !!val || 'Required']"
               @update:model-value="onEncounterServiceTypeSelected"
               hint="Select the department/clinic"
               clearable
             >
               <template v-slot:no-option>
                 <q-item>
                   <q-item-section class="text-grey">
                     No service types found. Admin should upload procedure prices.
                   </q-item-section>
                 </q-item>
               </template>
             </q-select>

             <q-select
               v-model="selectedEncounterProcedure"
               filled
               :options="encounterProcedureOptions"
               label="Procedure (Service Name) *"
               option-label="service_name"
               option-value="g_drg_code"
               lazy-rules
               :rules="[(val) => !!val || 'Required']"
               :disable="!selectedEncounterServiceType"
               hint="Select the procedure for this encounter"
               use-input
               input-debounce="300"
               @filter="filterEncounterProcedures"
               clearable
             >
               <template v-slot:no-option>
                 <q-item>
                   <q-item-section class="text-grey">
                     {{
                       selectedEncounterServiceType
                         ? 'No procedures found for this department. Select a different service type.'
                         : 'Please select a Service Type first'
                     }}
                   </q-item-section>
                 </q-item>
               </template>
             </q-select>

             <div class="row q-col-gutter-sm items-start">
               <q-input
                 v-model="encounterCccNumber"
                 filled
                 class="col"
                 :label="encounterRequiresCcc ? 'CCC Number *' : 'CCC Number (Optional)'"
                 :hint="encounterCccHint"
                 lazy-rules
                 :rules="encounterRequiresCcc ? [(val) => !!val || 'CCC number is required for active NHIS patients'] : []"
                 maxlength="20"
               />
               <q-btn
                 class="col-auto q-mt-xs"
                 color="secondary"
                 icon="cloud_download"
                 label="Get CCC"
                 :loading="generatingEncounterCcc"
                 :disable="!canGetEncounterCcc"
                 @click="fetchEncounterCcc"
               >
                 <q-tooltip v-if="!canGetEncounterCcc">
                   Requires active NHIS with a member number
                 </q-tooltip>
               </q-btn>
             </div>

             <div>
              <q-btn
                label="Create Encounter"
                type="submit"
                color="primary"
                class="glass-button"
              />
              <q-btn
                label="Cancel"
                flat
                color="grey"
                @click="showEncounterDialog = false"
                class="q-ml-sm glass-button"
              />
             </div>
           </q-form>
         </q-card-section>
       </q-card>
     </q-dialog>

    <q-card class="q-mt-md glass-card" flat>
      <q-card-section>
        <div class="text-h6 q-mb-md glass-text">New Patient Registration</div>
        <q-form @submit="onSubmit" class="q-gutter-md">
          <q-banner v-if="ghimsCardMode" rounded class="bg-blue-1 q-mb-sm">
            <template v-slot:avatar>
              <q-icon name="badge" color="primary" />
            </template>
            GHIMS mode is on — enter the client's GHIMS card number (e.g. E-0032-26xxxxxx). HMS will not auto-generate a card number.
          </q-banner>

          <q-input
            v-if="ghimsCardMode"
            v-model="form.card_number"
            filled
            label="GHIMS Card Number *"
            hint="Format: E-0032-26xxxxxx"
            lazy-rules
            :rules="[(val) => !!val?.trim() || 'GHIMS card number is required']"
            class="q-mb-sm"
          />

          <div class="row q-gutter-md">
            <q-input
              v-model="form.name"
              filled
              label="First Name *"
              class="col-12 col-md-6"
              lazy-rules
              :rules="[(val) => !!val || 'Required']"
            />
            <q-input
              v-model="form.surname"
              filled
              label="Surname"
              class="col-12 col-md-6"
            />
          </div>

          <q-input
            v-model="form.other_names"
            filled
            label="Other Names"
          />

          <div class="row q-gutter-md">
            <q-select
              v-model="form.gender"
              filled
              :options="genderOptions"
              label="Gender *"
              class="col-12 col-md-4"
              lazy-rules
              :rules="[(val) => !!val || 'Required']"
            />
            <q-input
              v-model.number="form.age"
              filled
              type="number"
              label="Age"
              class="col-12 col-md-4"
            />
            <q-input
              v-model="form.date_of_birth"
              filled
              type="date"
              label="Date of Birth"
              class="col-12 col-md-4"
            />
          </div>

          <q-toggle
            v-model="form.insured"
            label="Insured (NHIS)"
          />

          <div v-if="form.insured">
            <q-toggle
              v-model="form.nhis_active"
              label="NHIS card is active"
              class="q-mb-sm"
            />
            <q-banner v-if="form.insured && !form.nhis_active" rounded class="bg-orange-1 q-mb-md">
              Inactive NHIS card — patient will be treated as cash and carry (Get CCC disabled).
            </q-banner>

            <div class="row q-gutter-md items-start">
              <q-input
                v-model="form.insurance_id"
                filled
                label="Insurance ID / Member Number"
                class="col-12 col-md-6"
              />
              <q-btn
                color="secondary"
                icon="cloud_download"
                label="Import from NHIA"
                class="col-12 col-md-auto q-mt-xs"
                :loading="importingNhia"
                :disable="!form.insurance_id || !form.insurance_id.trim()"
                @click="importFromNhia"
              />
            </div>

            <div class="row q-gutter-md q-mt-sm">
              <q-input
                v-model="form.ccc_number"
                filled
                label="CCC Number"
                class="col-12 col-md-3"
                maxlength="20"
              />
              <q-input
                v-model="form.ccc_status"
                filled
                label="NHIS Status"
                class="col-12 col-md-3"
                readonly
              />
              <q-input
                v-model="form.insurance_start_date"
                filled
                type="date"
                label="Insurance Start Date"
                class="col-12 col-md-3"
              />
              <q-input
                v-model="form.insurance_end_date"
                filled
                type="date"
                label="Insurance End Date"
                class="col-12 col-md-3"
              />
            </div>
          </div>

          <q-input
            v-model="form.contact"
            filled
            label="Contact Number"
          />

          <q-input
            v-model="form.address"
            filled
            label="Address"
            type="textarea"
            rows="2"
          />

          <!-- Emergency Contact Details -->
          <div class="text-subtitle1 q-mt-md q-mb-sm glass-text">Emergency Contact Details</div>
          <div class="row q-gutter-md">
            <q-input
              v-model="form.emergency_contact_name"
              filled
              label="Emergency Contact Name"
              class="col-12 col-md-4"
            />
            <q-select
              v-model="form.emergency_contact_relationship"
              filled
              :options="relationshipOptions"
              label="Relationship"
              class="col-12 col-md-4"
              use-input
              input-debounce="0"
              @new-value="createRelationship"
            />
            <q-input
              v-model="form.emergency_contact_number"
              filled
              label="Emergency Contact Number"
              class="col-12 col-md-4"
            />
          </div>

          <!-- Additional Demographic Information -->
          <div class="text-subtitle1 q-mt-md q-mb-sm glass-text">Additional Information</div>
          <div class="row q-gutter-md">
            <q-select
              v-model="form.marital_status"
              filled
              :options="maritalStatusOptions"
              label="Marital Status"
              class="col-12 col-md-4"
              use-input
              input-debounce="0"
              @new-value="createMaritalStatus"
            />
            <q-select
              v-model="form.educational_level"
              filled
              :options="educationalLevelOptions"
              label="Educational Level"
              class="col-12 col-md-4"
              use-input
              input-debounce="0"
              @new-value="createEducationalLevel"
            />
            <q-input
              v-model="form.occupation"
              filled
              label="Occupation"
              class="col-12 col-md-4"
            />
          </div>

          <div>
            <q-btn
              label="Register Patient"
              type="submit"
              color="primary"
              :loading="loading"
              class="glass-button"
            />
          </div>
        </q-form>
      </q-card-section>
    </q-card>

    <!-- Edit Patient Dialog -->
    <q-dialog v-model="showEditDialog" persistent>
      <q-card style="min-width: 600px; max-width: 800px">
        <q-card-section>
          <div class="text-h6">Edit Patient Information</div>
        </q-card-section>

        <q-card-section>
          <q-form @submit="savePatientEdit" class="q-gutter-md">
            <q-banner v-if="ghimsCardMode" rounded class="bg-blue-1 q-mb-sm">
              <template v-slot:avatar>
                <q-icon name="badge" color="primary" />
              </template>
              Enter the client's GHIMS card number to replace the HMS card. The previous HMS card will be kept on the profile.
            </q-banner>

            <div v-if="ghimsCardMode" class="row q-gutter-md">
              <q-input
                v-model="editForm.card_number"
                filled
                label="GHIMS Card Number"
                hint="Format: E-0032-26xxxxxx. Leave unchanged to find patient by old card."
                class="col-12 col-md-6"
              />
              <q-input
                v-if="patientsStore.currentPatient?.legacy_card_number"
                :model-value="patientsStore.currentPatient.legacy_card_number"
                filled
                label="Previous HMS Card"
                readonly
                class="col-12 col-md-6"
              />
            </div>

            <div class="row q-gutter-md">
              <q-input
                v-model="editForm.name"
                filled
                label="First Name *"
                class="col-12 col-md-6"
                lazy-rules
                :rules="[(val) => !!val || 'Required']"
              />
              <q-input
                v-model="editForm.surname"
                filled
                label="Surname"
                class="col-12 col-md-6"
              />
            </div>

            <q-input
              v-model="editForm.other_names"
              filled
              label="Other Names"
            />

            <div class="row q-gutter-md">
              <q-select
                v-model="editForm.gender"
                filled
                :options="genderOptions"
                label="Gender *"
                class="col-12 col-md-4"
                lazy-rules
                :rules="[(val) => !!val || 'Required']"
              />
              <q-input
                v-model.number="editForm.age"
                filled
                type="number"
                label="Age"
                class="col-12 col-md-4"
              />
              <q-input
                v-model="editForm.date_of_birth"
                filled
                type="date"
                label="Date of Birth"
                class="col-12 col-md-4"
              />
            </div>

            <q-toggle
              v-model="editForm.insured"
              label="Insured (NHIS)"
            />

            <div v-if="editForm.insured">
              <q-toggle
                v-model="editForm.nhis_active"
                label="NHIS card is active"
                class="q-mb-sm"
              />
              <div class="row q-gutter-md items-start">
                <q-input
                  v-model="editForm.insurance_id"
                  filled
                  label="Insurance ID / Member Number"
                  class="col-12 col-md-6"
                />
                <q-btn
                  color="secondary"
                  icon="cloud_download"
                  label="Import from NHIA"
                  class="col-12 col-md-auto q-mt-xs"
                  :loading="importingNhiaEdit"
                  :disable="!editForm.insurance_id || !editForm.insurance_id.trim()"
                  @click="importFromNhiaEdit"
                />
              </div>
              <div class="row q-gutter-md q-mt-sm">
                <q-input
                  v-model="editForm.ccc_number"
                  filled
                  label="CCC Number"
                  class="col-12 col-md-3"
                />
                <q-input
                  v-model="editForm.ccc_status"
                  filled
                  label="NHIS Status"
                  class="col-12 col-md-3"
                  readonly
                />
                <q-input
                  v-model="editForm.insurance_start_date"
                  filled
                  type="date"
                  label="Insurance Start Date"
                  class="col-12 col-md-3"
                />
                <q-input
                  v-model="editForm.insurance_end_date"
                  filled
                  type="date"
                  label="Insurance End Date"
                  class="col-12 col-md-3"
                />
              </div>
            </div>

            <q-input
              v-model="editForm.contact"
              filled
              label="Contact Number"
            />

            <q-input
              v-model="editForm.address"
              filled
              label="Address"
              type="textarea"
              rows="2"
            />

            <!-- Emergency Contact Details -->
            <div class="text-subtitle1 q-mt-md q-mb-sm">Emergency Contact Details</div>
            <div class="row q-gutter-md">
              <q-input
                v-model="editForm.emergency_contact_name"
                filled
                label="Emergency Contact Name"
                class="col-12 col-md-4"
              />
              <q-select
                v-model="editForm.emergency_contact_relationship"
                filled
                :options="relationshipOptions"
                label="Relationship"
                class="col-12 col-md-4"
                use-input
                input-debounce="0"
                @new-value="createRelationship"
              />
              <q-input
                v-model="editForm.emergency_contact_number"
                filled
                label="Emergency Contact Number"
                class="col-12 col-md-4"
              />
            </div>

            <!-- Additional Demographic Information -->
            <div class="text-subtitle1 q-mt-md q-mb-sm">Additional Information</div>
            <div class="row q-gutter-md">
              <q-select
                v-model="editForm.marital_status"
                filled
                :options="maritalStatusOptions"
                label="Marital Status"
                class="col-12 col-md-4"
                use-input
                input-debounce="0"
                @new-value="createMaritalStatus"
              />
              <q-select
                v-model="editForm.educational_level"
                filled
                :options="educationalLevelOptions"
                label="Educational Level"
                class="col-12 col-md-4"
                use-input
                input-debounce="0"
                @new-value="createEducationalLevel"
              />
              <q-input
                v-model="editForm.occupation"
                filled
                label="Occupation"
                class="col-12 col-md-4"
              />
            </div>

            <div>
              <q-btn
                label="Save Changes"
                type="submit"
                color="primary"
                :loading="loading"
                class="glass-button"
              />
              <q-btn
                label="Cancel"
                flat
                color="grey"
                @click="showEditDialog = false"
                class="q-ml-sm glass-button"
              />
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, reactive, watch, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { usePatientsStore } from '../stores/patients';
import { useQuasar } from 'quasar';
import { priceListAPI } from '../services/api';
import { applyNhiaDataToForm, canFetchNhiaCcc, isWithinBabyWindow, firstNameFromFullName, babyNameFromFirstName } from '../utils/nhiaForm';
import { useModuleSettingsStore } from '../stores/moduleSettings';

const $q = useQuasar();
const router = useRouter();
const patientsStore = usePatientsStore();
const moduleSettingsStore = useModuleSettingsStore();

const ghimsCardMode = ref(false);
/** Parent first name from last NHIA import — used when DOB is changed to newborn range */
const nhiaParentFirstName = ref('');
const nhiaParentSurname = ref('');

const cardNumber = ref('');
const searching = ref(false);
const loading = ref(false);
const showEditDialog = ref(false);
const editForm = reactive({});

const editPatient = () => {
  if (!patientsStore.currentPatient) return;
  
  // Populate edit form with current patient data
  const patient = patientsStore.currentPatient;
  Object.assign(editForm, {
    name: patient.name || '',
    surname: patient.surname || '',
    other_names: patient.other_names || '',
    gender: patient.gender || '',
    age: patient.age || null,
    date_of_birth: patient.date_of_birth ? patient.date_of_birth.split('T')[0] : '',
    insured: patient.insured || false,
    nhis_active: patient.nhis_active || false,
    insurance_id: patient.insurance_id || '',
    ccc_number: patient.ccc_number || '',
    ccc_status: patient.ccc_status || '',
    insurance_start_date: patient.insurance_start_date 
      ? patient.insurance_start_date.split('T')[0] : '',
    insurance_end_date: patient.insurance_end_date 
      ? patient.insurance_end_date.split('T')[0] : '',
    contact: patient.contact || '',
    address: patient.address || '',
    emergency_contact_name: patient.emergency_contact_name || '',
    emergency_contact_relationship: patient.emergency_contact_relationship || '',
    emergency_contact_number: patient.emergency_contact_number || '',
    marital_status: patient.marital_status || '',
    educational_level: patient.educational_level || '',
    occupation: patient.occupation || '',
    card_number: patient.card_number || '',
  });
  
  showEditDialog.value = true;
};

const savePatientEdit = async () => {
  loading.value = true;
  try {
    const patientData = { ...editForm };
    
    // Clean up empty fields
    if (patientData.date_of_birth === '') {
      patientData.date_of_birth = null;
    }
    if (patientData.insurance_start_date === '') {
      patientData.insurance_start_date = null;
    }
    if (patientData.insurance_end_date === '') {
      patientData.insurance_end_date = null;
    }
    if (patientData.insurance_id === '') {
      patientData.insurance_id = null;
    }
    if (patientData.ccc_number === '') {
      patientData.ccc_number = null;
    }
    if (patientData.ccc_status === '') {
      patientData.ccc_status = null;
    }
    if (!patientData.insured) {
      patientData.nhis_active = false;
    }
    if (patientData.surname === '') {
      patientData.surname = null;
    }
    if (patientData.other_names === '') {
      patientData.other_names = null;
    }
    if (patientData.contact === '') {
      patientData.contact = null;
    }
    if (patientData.address === '') {
      patientData.address = null;
    }
    if (patientData.emergency_contact_name === '') {
      patientData.emergency_contact_name = null;
    }
    if (patientData.emergency_contact_relationship === '') {
      patientData.emergency_contact_relationship = null;
    }
    if (patientData.emergency_contact_number === '') {
      patientData.emergency_contact_number = null;
    }
    if (patientData.marital_status === '') {
      patientData.marital_status = null;
    }
    if (patientData.educational_level === '') {
      patientData.educational_level = null;
    }
    if (patientData.occupation === '') {
      patientData.occupation = null;
    }

    const currentCard = patientsStore.currentPatient?.card_number;
    if (!ghimsCardMode.value || patientData.card_number === currentCard) {
      delete patientData.card_number;
    } else if (patientData.card_number === '') {
      delete patientData.card_number;
    }
    
    const updated = await patientsStore.updatePatient(patientsStore.currentPatient.id, patientData);
    showEditDialog.value = false;
    // Reload patient data (card may have changed after GHIMS migration)
    const reloadCard = updated?.card_number || patientsStore.currentPatient.card_number;
    await patientsStore.getPatientByCard(reloadCard);
  } catch (error) {
    // Error handled in store
  } finally {
    loading.value = false;
  }
};

const viewPatientProfile = () => {
  if (patientsStore.currentPatient) {
    router.push(`/patients/${patientsStore.currentPatient.card_number}`);
  }
};

const genderOptions = ['M', 'F'];
const departmentOptions = ['General', 'Pediatrics', 'ENT', 'Eye', 'Emergency']; // Kept for backwards compatibility if needed

// Emergency contact relationship options
const relationshipOptions = ref([
  'Spouse', 'Parent', 'Child', 'Sibling', 'Friend', 'Relative', 'Other'
]);

// Marital status options
const maritalStatusOptions = ref([
  'Single', 'Married', 'Divorced', 'Widowed', 'Separated'
]);

// Educational level options
const educationalLevelOptions = ref([
  'None', 'Primary', 'Junior High School', 'Senior High School', 
  'Tertiary', 'University', 'Postgraduate', 'Other'
]);

// Functions to allow custom values
const createRelationship = (val, done) => {
  if (val.length > 0 && !relationshipOptions.value.includes(val)) {
    relationshipOptions.value.push(val);
  }
  done(val);
};

const createMaritalStatus = (val, done) => {
  if (val.length > 0 && !maritalStatusOptions.value.includes(val)) {
    maritalStatusOptions.value.push(val);
  }
  done(val);
};

const createEducationalLevel = (val, done) => {
  if (val.length > 0 && !educationalLevelOptions.value.includes(val)) {
    educationalLevelOptions.value.push(val);
  }
  done(val);
};

// Service Type and Procedure selection for encounter creation
const showEncounterDialog = ref(false);
const serviceTypeOptions = ref([]);
const encounterProcedures = ref([]);
const encounterProcedureOptions = ref([]);
const selectedEncounterServiceType = ref(null);
const selectedEncounterProcedure = ref(null);
const encounterCccNumber = ref('');
const importingNhia = ref(false);
const importingNhiaEdit = ref(false);
const generatingEncounterCcc = ref(false);

const encounterRequiresCcc = computed(() =>
  canFetchNhiaCcc(patientsStore.currentPatient)
);

const encounterCccHint = computed(() => {
  const p = patientsStore.currentPatient;
  if (!p?.insured) return 'Optional — cash patient';
  if (!p?.nhis_active) return 'Inactive NHIS — cash and carry for this visit';
  return 'Required for patients with active NHIS';
});

const canGetEncounterCcc = computed(() =>
  canFetchNhiaCcc(patientsStore.currentPatient)
);

const form = reactive({
  card_number: '',
  name: '',
  surname: '',
  other_names: '',
  gender: '',
  age: null,
  date_of_birth: '',
  insured: false,
  nhis_active: false,
  insurance_id: '',
  insurance_start_date: '',
  insurance_end_date: '',
  ccc_number: '',
  ccc_status: '',
  contact: '',
  address: '',
  emergency_contact_name: '',
  emergency_contact_relationship: '',
  emergency_contact_number: '',
  marital_status: '',
  educational_level: '',
  occupation: '',
});

// Helper function to calculate age from date of birth
const calculateAgeFromDateOfBirth = (dateOfBirth) => {
  if (!dateOfBirth) return null;
  
  const birthDate = new Date(dateOfBirth);
  if (isNaN(birthDate.getTime())) return null;
  
  const today = new Date();
  let age = today.getFullYear() - birthDate.getFullYear();
  const monthDiff = today.getMonth() - birthDate.getMonth();
  
  if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birthDate.getDate())) {
    age--;
  }
  
  return age >= 0 ? age : null;
};

// When DOB changes, update age (never derive DOB from age — that overwrote NHIA import dates)
watch(() => form.date_of_birth, (newDateOfBirth) => {
  if (!newDateOfBirth) return;
  const calculatedAge = calculateAgeFromDateOfBirth(newDateOfBirth);
  if (calculatedAge !== null) {
    form.age = calculatedAge;
  }
});

const searchPatient = async () => {
  if (!cardNumber.value) {
    $q.notify({
      type: 'warning',
      message: 'Please enter a card number',
    });
    return;
  }

  searching.value = true;
  try {
    await patientsStore.getPatientByCard(cardNumber.value);
  } finally {
    searching.value = false;
  }
};

// Load service types for encounter creation
const loadServiceTypesForEncounter = async () => {
  try {
    const response = await priceListAPI.getServiceTypes();
    serviceTypeOptions.value = response.data || [];
  } catch (error) {
    console.error('Failed to load service types:', error);
    serviceTypeOptions.value = [];
  }
};

// Load procedures when service type is selected for encounter
const onEncounterServiceTypeSelected = async (serviceType) => {
  if (!serviceType) {
    encounterProcedures.value = [];
    encounterProcedureOptions.value = [];
    selectedEncounterProcedure.value = null;
    return;
  }
  
  try {
    const response = await priceListAPI.getProceduresByServiceType(serviceType);
    encounterProcedures.value = response.data || [];
    encounterProcedureOptions.value = encounterProcedures.value;
    selectedEncounterProcedure.value = null;
  } catch (error) {
    console.error('Failed to load procedures:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to load procedures',
    });
    encounterProcedures.value = [];
    encounterProcedureOptions.value = [];
  }
};

// Filter procedures for autocomplete in encounter dialog
const filterEncounterProcedures = (val, update) => {
  if (val === '') {
    update(() => {
      encounterProcedureOptions.value = encounterProcedures.value;
    });
    return;
  }
  
  update(() => {
    const needle = val.toLowerCase();
    encounterProcedureOptions.value = encounterProcedures.value.filter(
      (p) => p.service_name.toLowerCase().indexOf(needle) > -1 ||
             p.g_drg_code.toLowerCase().indexOf(needle) > -1
    );
  });
};

const createEncounterForExisting = async () => {
  if (!patientsStore.currentPatient) return;
  
  // Load service types before showing dialog
  await loadServiceTypesForEncounter();
  
  // Reset form
  selectedEncounterServiceType.value = null;
  selectedEncounterProcedure.value = null;
  encounterCccNumber.value = '';
  encounterProcedures.value = [];
  encounterProcedureOptions.value = [];
  
  showEncounterDialog.value = true;
};

const importFromNhia = async () => {
  if (!form.insurance_id?.trim()) return;
  importingNhia.value = true;
  try {
    const result = await patientsStore.lookupNhia(form.insurance_id.trim());
    if (result.data?.name) {
      nhiaParentFirstName.value = firstNameFromFullName(result.data.name);
      const parts = result.data.name.trim().split(/\s+/);
      nhiaParentSurname.value = parts.length > 1 ? parts.slice(1).join(' ') : '';
    }
    applyNhiaDataToForm(form, result.data);
    await applyBabyNameWhenEligible();
    $q.notify({ type: 'positive', message: 'Patient details imported from NHIA' });
  } finally {
    importingNhia.value = false;
  }
};

const importFromNhiaEdit = async () => {
  if (!editForm.insurance_id?.trim()) return;
  importingNhiaEdit.value = true;
  try {
    const result = await patientsStore.lookupNhia(editForm.insurance_id.trim());
    applyNhiaDataToForm(editForm, result.data);
    $q.notify({ type: 'positive', message: 'Patient details imported from NHIA' });
  } finally {
    importingNhiaEdit.value = false;
  }
};

const fetchEncounterCcc = async () => {
  const patient = patientsStore.currentPatient;
  if (!patient?.id || !canGetEncounterCcc.value) return;
  generatingEncounterCcc.value = true;
  try {
    const result = await patientsStore.generateCcc(patient.id);
    if (result?.data?.ccc) {
      encounterCccNumber.value = result.data.ccc;
    }
    if (result?.patient) {
      patientsStore.currentPatient = result.patient;
    }
  } finally {
    generatingEncounterCcc.value = false;
  }
};

const submitEncounterCreation = async () => {
  if (!patientsStore.currentPatient) return;
  
  const isInsured = encounterRequiresCcc.value;
  
  // Validate service type
  if (!selectedEncounterServiceType.value) {
    $q.notify({
      type: 'warning',
      message: 'Please select a Service Type (Department/Clinic)',
    });
    return;
  }
  
  // Validate procedure
  if (!selectedEncounterProcedure.value) {
    $q.notify({
      type: 'warning',
      message: 'Please select a Procedure',
    });
    return;
  }
  
  // Validate CCC for NHIS-active insured patients
  if (isInsured && !encounterCccNumber.value) {
    $q.notify({
      type: 'warning',
      message: 'CCC number is required for patients with active NHIS',
    });
    return;
  }
  
  try {
    const procedure = selectedEncounterProcedure.value;
    const procedureObj = typeof procedure === 'object' ? procedure : encounterProcedures.value.find(p => p.g_drg_code === procedure);
    
    const result = await patientsStore.createEncounter(
      patientsStore.currentPatient.id,
      selectedEncounterServiceType.value,
      encounterCccNumber.value || null,
      procedureObj?.g_drg_code || null,
      procedureObj?.service_name || null
    );
    
    $q.notify({
      type: 'positive',
      message: `Encounter created!\nCard: ${patientsStore.currentPatient.card_number}\nEncounter ID: ${result.encounter_id}\nService: ${result.procedure_name || selectedEncounterServiceType.value}\nCCC: ${result.ccc_number || 'None'}`,
    });
    
    showEncounterDialog.value = false;
    
    // Reset new patient form if we just created a new patient
    if (loading.value) {
      Object.keys(form).forEach((key) => {
        if (key === 'insured') {
          form[key] = false;
        } else if (key === 'age') {
          form[key] = null;
        } else {
          form[key] = '';
        }
      });
      loading.value = false;
    }
    
    router.push(`/vitals`);
  } catch (error) {
    // Error handled in store
  }
};

const onSubmit = async () => {
  if (babyNameTimer) clearTimeout(babyNameTimer);
  loading.value = true;
  try {
    const patientData = buildPatientPayload();

    const validation = await patientsStore.validateRegistration({
      ...patientData,
      force_register: false,
    });

    let babyRegistrationSnapshot = null;
    if (validation?.status === 'insurance_baby_allowed') {
      babyRegistrationSnapshot = {
        name: patientData.name,
        surname: patientData.surname,
        date_of_birth: patientData.date_of_birth,
      };
    }

    const proceed = await handleRegistrationValidation(
      validation,
      patientData,
      babyRegistrationSnapshot,
    );
    if (!proceed?.continue) {
      loading.value = false;
      return;
    }

    const createPayload = {
      ...buildPatientPayload(),
      force_register: proceed.force_register || false,
    };
    if (proceed.isBabyRegistration || babyRegistrationSnapshot) {
      const fresh = buildPatientPayload();
      createPayload.name = fresh.name;
      createPayload.surname = fresh.surname;
      createPayload.date_of_birth = fresh.date_of_birth;
    }

    const patient = await patientsStore.createPatient(createPayload);
    
    // Set current patient so the encounter dialog can use it
    patientsStore.currentPatient = patient;

    // After patient is created, show encounter creation dialog
    await loadServiceTypesForEncounter();
    
    // Reset form
    selectedEncounterServiceType.value = null;
    selectedEncounterProcedure.value = null;
    encounterCccNumber.value = '';
    encounterProcedures.value = [];
    encounterProcedureOptions.value = [];
    
    showEncounterDialog.value = true;
  } catch (error) {
    // Error handled in store
    loading.value = false;
  }
  // Note: Loading will be set to false after encounter dialog is submitted or closed
};

const buildPatientPayload = () => {
  const patientData = { ...form };
  if (patientData.date_of_birth === '') patientData.date_of_birth = null;
  if (patientData.insurance_start_date === '') patientData.insurance_start_date = null;
  if (patientData.insurance_end_date === '') patientData.insurance_end_date = null;
  if (patientData.insurance_id === '') patientData.insurance_id = null;
  if (patientData.ccc_number === '') patientData.ccc_number = null;
  if (patientData.ccc_status === '') patientData.ccc_status = null;
  if (!patientData.insured) patientData.nhis_active = false;
  if (patientData.surname === '') patientData.surname = null;
  if (patientData.other_names === '') patientData.other_names = null;
  if (patientData.contact === '') patientData.contact = null;
  if (patientData.address === '') patientData.address = null;
  if (patientData.emergency_contact_name === '') patientData.emergency_contact_name = null;
  if (patientData.emergency_contact_relationship === '') patientData.emergency_contact_relationship = null;
  if (patientData.emergency_contact_number === '') patientData.emergency_contact_number = null;
  if (patientData.marital_status === '') patientData.marital_status = null;
  if (patientData.educational_level === '') patientData.educational_level = null;
  if (patientData.occupation === '') patientData.occupation = null;
  if (!ghimsCardMode.value) patientData.card_number = null;
  else if (patientData.card_number === '') patientData.card_number = null;
  return patientData;
};

let babyNameTimer = null;
const applyBabyNameWhenEligible = async () => {
  if (!form.insured || !form.date_of_birth || !form.insurance_id?.trim()) return;
  if (!isWithinBabyWindow(form.date_of_birth)) return;

  try {
    const response = await patientsStore.validateRegistration({
      ...buildPatientPayload(),
      force_register: false,
    });
    if (response?.status !== 'insurance_baby_allowed') return;

    const parentFirst = nhiaParentFirstName.value
      || firstNameFromFullName(response.existing_patient?.name);
    if (parentFirst) {
      form.name = babyNameFromFirstName(parentFirst);
    }
    if (response.suggested_surname) {
      form.surname = response.suggested_surname;
    } else if (nhiaParentSurname.value) {
      form.surname = nhiaParentSurname.value;
    }
  } catch {
    // Best-effort; submit validates again
  }
};

watch(
  () => [form.date_of_birth, form.insurance_id, form.insured],
  () => {
    if (babyNameTimer) clearTimeout(babyNameTimer);
    babyNameTimer = setTimeout(() => {
      applyBabyNameWhenEligible();
    }, 400);
  },
);

const openExistingPatientForService = async (existingPatient) => {
  if (!existingPatient?.card_number) return;
  await patientsStore.getPatientByCard(existingPatient.card_number);
  await createEncounterForExisting();
};

const handleRegistrationValidation = async (validation, patientData, babyRegistrationSnapshot = null) => {
  const status = validation?.status || 'ok';

  if (status === 'ok') {
    return { continue: true, force_register: false };
  }

  if (status === 'insurance_duplicate' || status === 'card_duplicate' || status === 'insurance_rejected') {
    const existing = validation.existing_patient;
    return new Promise((resolve) => {
      $q.dialog({
        title: 'Patient already registered',
        message: `${validation.message}\n\n${existing?.name || ''} ${existing?.surname || ''} — Card: ${existing?.card_number || 'N/A'}`,
        cancel: { label: 'Cancel', flat: true, color: 'grey' },
        ok: { label: 'Create service instead', color: 'primary' },
        persistent: true,
      })
        .onOk(() => {
          openExistingPatientForService(existing);
          resolve({ continue: false });
        })
        .onCancel(() => resolve({ continue: false }));
    });
  }

  if (status === 'insurance_rejected' || status === 'invalid_card') {
    $q.notify({ type: 'negative', message: validation.message });
    return { continue: false };
  }

  if (status === 'insurance_baby_allowed') {
    const existing = validation.existing_patient;
    const snapshot = babyRegistrationSnapshot || {
      name: patientData.name,
      surname: patientData.surname,
      date_of_birth: patientData.date_of_birth,
    };
    return new Promise((resolve) => {
      $q.dialog({
        title: 'Register as baby on existing insurance',
        message: `${validation.message}\n\nName will be registered as: ${snapshot.name || ''} ${snapshot.surname || ''}\nParent: ${existing?.name || ''} ${existing?.surname || ''} (${existing?.card_number})\nDate of birth: ${snapshot.date_of_birth || 'N/A'}`,
        cancel: { label: 'Cancel', flat: true, color: 'grey' },
        ok: { label: 'Register baby', color: 'primary' },
        persistent: true,
      })
        .onOk(() => {
          resolve({ continue: true, force_register: false, isBabyRegistration: true });
        })
        .onCancel(() => resolve({ continue: false }));
    });
  }

  if (status === 'profile_duplicate') {
    const existing = validation.existing_patient;
    return new Promise((resolve) => {
      $q.dialog({
        title: 'Similar patient found',
        message: `${validation.message}\n\nExisting: ${existing?.name || ''} ${existing?.surname || ''} — Card: ${existing?.card_number || 'N/A'}`,
        ok: { label: 'Register as new person', color: 'warning' },
        cancel: { label: 'Create service for existing', color: 'primary' },
        persistent: true,
      })
        .onOk(() => resolve({ continue: true, force_register: true }))
        .onCancel(() => {
          openExistingPatientForService(existing);
          resolve({ continue: false });
        });
    });
  }

  return { continue: true, force_register: false };
};

onMounted(async () => {
  try {
    const config = await patientsStore.fetchRegistrationConfig();
    ghimsCardMode.value = !!config?.ghims_card_mode;
    await moduleSettingsStore.fetchModuleStatus('ghims');
    ghimsCardMode.value = moduleSettingsStore.isModuleActive('ghims');
  } catch (e) {
    console.warn('Could not load GHIMS registration config', e);
  }
});
</script>

