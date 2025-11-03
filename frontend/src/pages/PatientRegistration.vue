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

             <q-input
               v-model="encounterCccNumber"
               filled
               :label="patientsStore.currentPatient?.insured ? 'CCC Number *' : 'CCC Number (Optional)'"
               :hint="patientsStore.currentPatient?.insured ? 'Required for insured patients' : 'Optional - leave empty if not needed'"
               lazy-rules
               :rules="patientsStore.currentPatient?.insured ? [(val) => !!val || 'CCC number is required for insured patients'] : []"
               maxlength="20"
             />

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

          <div v-if="form.insured" class="row q-gutter-md">
            <q-input
              v-model="form.insurance_id"
              filled
              label="Insurance ID / Member Number"
              class="col-12 col-md-6"
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

            <div v-if="editForm.insured" class="row q-gutter-md">
              <q-input
                v-model="editForm.insurance_id"
                filled
                label="Insurance ID / Member Number"
                class="col-12 col-md-6"
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
import { ref, reactive } from 'vue';
import { useRouter } from 'vue-router';
import { usePatientsStore } from '../stores/patients';
import { useQuasar } from 'quasar';
import { priceListAPI } from '../services/api';

const $q = useQuasar();
const router = useRouter();
const patientsStore = usePatientsStore();

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
    insurance_id: patient.insurance_id || '',
    insurance_start_date: patient.insurance_start_date 
      ? patient.insurance_start_date.split('T')[0] : '',
    insurance_end_date: patient.insurance_end_date 
      ? patient.insurance_end_date.split('T')[0] : '',
    contact: patient.contact || '',
    address: patient.address || '',
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
    
    await patientsStore.updatePatient(patientsStore.currentPatient.id, patientData);
    showEditDialog.value = false;
    // Reload patient data
    await patientsStore.getPatientByCard(patientsStore.currentPatient.card_number);
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

// Service Type and Procedure selection for encounter creation
const showEncounterDialog = ref(false);
const serviceTypeOptions = ref([]);
const encounterProcedures = ref([]);
const encounterProcedureOptions = ref([]);
const selectedEncounterServiceType = ref(null);
const selectedEncounterProcedure = ref(null);
const encounterCccNumber = ref('');

const form = reactive({
  name: '',
  surname: '',
  other_names: '',
  gender: '',
  age: null,
  date_of_birth: '',
  insured: false,
  insurance_id: '',
  insurance_start_date: '',
  insurance_end_date: '',
  contact: '',
  address: '',
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

const submitEncounterCreation = async () => {
  if (!patientsStore.currentPatient) return;
  
  const isInsured = patientsStore.currentPatient.insured;
  
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
  
  // Validate CCC for insured patients
  if (isInsured && !encounterCccNumber.value) {
    $q.notify({
      type: 'warning',
      message: 'CCC number is required for insured patients',
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
  loading.value = true;
  try {
    const patientData = { ...form };

    // Clean up empty date and string fields - send null instead of empty strings
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

    const patient = await patientsStore.createPatient(patientData);
    
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
</script>

