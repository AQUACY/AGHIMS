<template>
  <q-page class="q-pa-md">
    <div class="row items-center q-mb-md">
      <q-btn
        flat
        icon="arrow_back"
        label="Back to IPD"
        @click="$router.push('/ipd')"
        class="q-mr-md"
      />
      <div class="text-h4 text-weight-bold glass-text">
        Admit Patient
      </div>
    </div>

    <!-- Patient Search Section -->
    <q-card v-if="!selectedPatient" class="glass-card q-mb-md" flat bordered>
      <q-card-section>
        <div class="text-h6 glass-text q-mb-md">
          <q-icon name="search" color="primary" class="q-mr-sm" />
          Search Patient
        </div>
        <div class="row q-col-gutter-md">
          <div class="col-12 col-md-6">
            <q-input
              v-model="searchCardNumber"
              filled
              label="Search by Card Number"
              hint="Enter patient card number"
              @keyup.enter="searchPatientByCard"
            >
              <template v-slot:append>
                <q-btn
                  flat
                  dense
                  icon="search"
                  color="primary"
                  @click="searchPatientByCard"
                  :loading="searching"
                />
              </template>
            </q-input>
          </div>
          <div class="col-12 col-md-6">
            <q-input
              v-model="searchName"
              filled
              label="Search by Name"
              hint="Enter patient name"
              @keyup.enter="searchPatientByName"
            >
              <template v-slot:append>
                <q-btn
                  flat
                  dense
                  icon="search"
                  color="primary"
                  @click="searchPatientByName"
                  :loading="searching"
                />
              </template>
            </q-input>
          </div>
        </div>

        <!-- Search Results -->
        <div v-if="searchResults.length > 0" class="q-mt-md">
          <div class="text-subtitle2 glass-text q-mb-sm">Select Patient:</div>
          <q-list bordered separator>
            <q-item
              v-for="patient in searchResults"
              :key="patient.id"
              clickable
              @click="selectPatient(patient)"
              class="q-pa-md"
            >
              <q-item-section avatar>
                <q-avatar color="primary" text-color="white">
                  <q-icon name="person" />
                </q-avatar>
              </q-item-section>
              <q-item-section>
                <q-item-label class="text-weight-bold glass-text">
                  {{ patient.name }} {{ patient.surname }}
                  <span v-if="patient.other_names">{{ patient.other_names }}</span>
                </q-item-label>
                <q-item-label caption>
                  Card: {{ patient.card_number }} | 
                  {{ patient.gender }} | 
                  <span v-if="patient.date_of_birth">
                    DOB: {{ formatDate(patient.date_of_birth) }}
                  </span>
                </q-item-label>
              </q-item-section>
            </q-item>
          </q-list>
        </div>
      </q-card-section>
    </q-card>

    <!-- Admission Form -->
    <div v-if="selectedPatient">
      <q-card class="glass-card q-mb-md" flat bordered>
        <q-card-section class="row items-center">
          <div class="text-h6 glass-text">
            Admit Patient - {{ selectedPatient.name }} {{ selectedPatient.surname }}<span v-if="selectedPatient.other_names"> {{ selectedPatient.other_names }}</span>
          </div>
          <q-space />
          <q-btn
            flat
            icon="close"
            label="Change Patient"
            color="primary"
            @click="selectedPatient = null; searchResults = []; admissionForm = getInitialForm()"
          />
        </q-card-section>
      </q-card>

      <q-card class="glass-card" flat bordered>
        <q-card-section>
          <q-tabs v-model="currentTab" class="text-primary" align="left">
            <q-tab name="patient-info" label="Patient Info" icon="person" />
            <q-tab name="ward-selection" label="Ward Selection" icon="local_hospital" />
            <q-tab name="emergency-contact" label="Emergency Contact" icon="contact_phone" />
            <q-tab name="bed-selection" label="Bed Selection" icon="hotel" />
            <q-tab name="doctor-selection" label="Under Care Of" icon="medical_services" />
          </q-tabs>

          <q-separator />

          <q-tab-panels v-model="currentTab" animated>
            <!-- Tab 1: Patient Info -->
            <q-tab-panel name="patient-info">
              <div class="text-h6 q-mb-md glass-text">Patient Information</div>
              
              <!-- PROMINENT INSURANCE INFORMATION SECTION -->
              <q-card 
                v-if="selectedPatient && (selectedPatient.insured || selectedPatient.insurance_id)"
                :class="getInsuranceCardClass(selectedPatient)"
                flat 
                bordered
                class="q-mb-lg insurance-info-card"
                style="border-width: 3px !important;"
              >
                <q-card-section class="q-pa-lg">
                  <div class="row items-center q-mb-md">
                    <q-icon 
                      :name="selectedPatient.insured ? 'verified_user' : 'warning'" 
                      :color="selectedPatient.insured ? 'positive' : 'negative'"
                      size="48px" 
                      class="q-mr-md"
                    />
                    <div class="col">
                      <div class="text-h5 text-weight-bold" :class="selectedPatient.insured ? 'text-positive' : 'text-negative'">
                        <q-icon name="health_and_safety" size="32px" class="q-mr-sm" />
                        {{ selectedPatient.insured ? 'INSURED PATIENT' : 'INSURANCE INFORMATION' }}
                      </div>
                      <div class="text-subtitle1 q-mt-xs" :class="selectedPatient.insured ? 'text-positive' : 'text-grey-7'">
                        {{ selectedPatient.insured ? 'Active Insurance Coverage' : 'Insurance Status: Not Active' }}
                      </div>
                    </div>
                  </div>
                  
                  <q-separator class="q-mb-md" />
                  
                  <div class="row q-col-gutter-lg">
                    <div class="col-12 col-md-4">
                      <div class="text-subtitle2 text-weight-bold q-mb-xs" :class="selectedPatient.insured ? 'text-positive' : 'text-grey-7'">
                        <q-icon name="badge" size="20px" class="q-mr-xs" />
                        Insurance Number
                      </div>
                      <div class="text-h6 text-weight-bold glass-text" style="word-break: break-all;">
                        {{ selectedPatient.insurance_id || 'N/A' }}
                      </div>
                    </div>
                    <div class="col-12 col-md-4">
                      <div class="text-subtitle2 text-weight-bold q-mb-xs" :class="selectedPatient.insured ? 'text-positive' : 'text-grey-7'">
                        <q-icon name="event" size="20px" class="q-mr-xs" />
                        Start Date
                      </div>
                      <div class="text-h6 text-weight-bold glass-text">
                        {{ selectedPatient.insurance_start_date ? formatDate(selectedPatient.insurance_start_date) : 'N/A' }}
                      </div>
                    </div>
                    <div class="col-12 col-md-4">
                      <div class="text-subtitle2 text-weight-bold q-mb-xs" :class="getEndDateClass(selectedPatient)">
                        <q-icon name="event_available" size="20px" class="q-mr-xs" />
                        End Date
                      </div>
                      <div class="text-h6 text-weight-bold" :class="getEndDateTextClass(selectedPatient)">
                        {{ selectedPatient.insurance_end_date ? formatDate(selectedPatient.insurance_end_date) : 'N/A' }}
                        <q-icon 
                          v-if="isInsuranceExpired(selectedPatient)" 
                          name="error" 
                          color="negative" 
                          size="24px" 
                          class="q-ml-sm"
                        />
                      </div>
                      <div v-if="isInsuranceExpired(selectedPatient)" class="text-negative text-weight-bold q-mt-xs">
                        <q-icon name="warning" size="16px" class="q-mr-xs" />
                        EXPIRED - Cash and Carry
                      </div>
                      <div v-else-if="isInsuranceExpiringSoon(selectedPatient)" class="text-warning text-weight-bold q-mt-xs">
                        <q-icon name="schedule" size="16px" class="q-mr-xs" />
                        Expiring Soon
                      </div>
                    </div>
                  </div>
                  
                  <q-banner 
                    v-if="selectedPatient.insured && !isInsuranceExpired(selectedPatient)"
                    class="q-mt-md"
                    :class="selectedPatient.insured ? 'bg-positive' : 'bg-negative'"
                    rounded
                  >
                    <template v-slot:avatar>
                      <q-icon name="check_circle" color="white" size="32px" />
                    </template>
                    <div class="text-h6 text-white text-weight-bold">
                      CONFIRM CCC NUMBER - Patient has active insurance coverage
                    </div>
                    <div class="text-body1 text-white q-mt-xs">
                      Verify insurance dates and enter CCC number below if applicable.
                    </div>
                  </q-banner>
                  
                  <q-banner 
                    v-else
                    class="q-mt-md bg-negative"
                    rounded
                  >
                    <template v-slot:avatar>
                      <q-icon name="cancel" color="white" size="32px" />
                    </template>
                    <div class="text-h6 text-white text-weight-bold">
                      CASH AND CARRY - No active insurance coverage
                    </div>
                    <div class="text-body1 text-white q-mt-xs">
                      Do not enter CCC number. Patient will pay cash.
                    </div>
                  </q-banner>
                </q-card-section>
              </q-card>
              
              <!-- Insurance Not Available Warning -->
              <q-banner 
                v-if="selectedPatient && !selectedPatient.insured && !selectedPatient.insurance_id"
                class="q-mb-md bg-warning"
                rounded
              >
                <template v-slot:avatar>
                  <q-icon name="info" color="white" size="32px" />
                </template>
                <div class="text-h6 text-white text-weight-bold">
                  NO INSURANCE INFORMATION AVAILABLE
                </div>
                <div class="text-body1 text-white q-mt-xs">
                  Patient is not registered as insured. This is a cash and carry case.
                </div>
              </q-banner>
              
              <div class="row q-col-gutter-md">
                <div class="col-12">
                  <q-card flat bordered class="q-pa-md">
                    <div class="row q-col-gutter-md">
                      <div class="col-12 col-md-6">
                        <div class="text-body2 text-secondary">Patient Name</div>
                        <div class="text-body1 glass-text q-mb-md">
                          <strong>{{ selectedPatient.name }} {{ selectedPatient.surname }}</strong>
                          <span v-if="selectedPatient.other_names">{{ selectedPatient.other_names }}</span>
                        </div>
                        <div class="text-body2 text-secondary">Card Number</div>
                        <div class="text-body1 glass-text q-mb-md">
                          <strong>{{ selectedPatient.card_number }}</strong>
                        </div>
                        <div class="text-body2 text-secondary">Gender</div>
                        <div class="text-body1 glass-text q-mb-md">
                          <strong>{{ selectedPatient.gender }}</strong>
                        </div>
                        <div v-if="selectedPatient.date_of_birth" class="text-body2 text-secondary">Date of Birth</div>
                        <div v-if="selectedPatient.date_of_birth" class="text-body1 glass-text q-mb-md">
                          <strong>{{ formatDate(selectedPatient.date_of_birth) }}</strong>
                        </div>
                      </div>
                      <div class="col-12 col-md-6">
                        <q-input
                          v-model="admissionForm.ccc_number"
                          filled
                          label="CCC Number"
                          hint="Enter if patient has active insurance, otherwise leave blank (cash and carry)"
                          :rules="[val => !val || val.length === 5 || 'CCC number must be 5 digits']"
                          :class="selectedPatient.insured && !isInsuranceExpired(selectedPatient) ? 'bg-positive-1' : ''"
                        >
                          <template v-slot:append>
                            <q-btn
                              v-if="admissionForm.ccc_number"
                              flat
                              dense
                              icon="clear"
                              @click="admissionForm.ccc_number = ''"
                            />
                          </template>
                        </q-input>
                        <div class="text-caption text-secondary q-mt-xs">
                          <q-icon name="info" size="16px" class="q-mr-xs" />
                          For direct admissions, enter CCC number if patient has active insurance.
                        </div>
                      </div>
                    </div>
                  </q-card>
                </div>
              </div>
            </q-tab-panel>

            <!-- Tab 2: Ward Selection -->
            <q-tab-panel name="ward-selection">
              <div class="text-h6 q-mb-md glass-text">Ward Selection</div>
              <div class="text-body2 text-secondary q-mb-md">
                Select the ward where the patient will be admitted
              </div>
              <q-select
                v-model="admissionForm.ward"
                :options="wardOptions"
                filled
                label="Select Ward *"
                :rules="[val => !!val || 'Please select a ward']"
                emit-value
                map-options
                @update:model-value="onWardSelected"
                ref="wardSelectRef"
              >
                <template v-slot:option="scope">
                  <q-item v-bind="scope.itemProps">
                    <q-item-section>
                      <q-item-label>{{ scope.opt.label }}</q-item-label>
                    </q-item-section>
                  </q-item>
                </template>
              </q-select>
            </q-tab-panel>

            <!-- Tab 3: Emergency Contact -->
            <q-tab-panel name="emergency-contact">
              <div class="text-h6 q-mb-md glass-text">Emergency Contact Details</div>
              <div class="text-body2 text-secondary q-mb-md">
                Emergency contact information is required for admission. At least one person must be available to take care of the patient during admission.
                <br />
                <span v-if="admissionForm.emergency_contact_name || admissionForm.emergency_contact_relationship || admissionForm.emergency_contact_number">
                  <q-icon name="info" color="info" class="q-mr-xs" />
                  <strong>Contact information from patient registration has been pre-filled.</strong> You can edit if needed.
                </span>
                <span v-else>
                  <q-icon name="warning" color="warning" class="q-mr-xs" />
                  <strong>No emergency contact found in patient registration.</strong> Please provide emergency contact details below.
                </span>
              </div>
              <div class="row q-col-gutter-md">
                <div class="col-12 col-md-6">
                  <q-input
                    v-model="admissionForm.emergency_contact_name"
                    filled
                    label="Contact Name *"
                    :rules="[val => !!val || 'Contact name is required']"
                    ref="emergencyContactNameRef"
                  >
                    <template v-slot:append>
                      <q-btn
                        v-if="admissionForm.emergency_contact_name"
                        flat
                        dense
                        icon="clear"
                        @click="admissionForm.emergency_contact_name = ''"
                      />
                    </template>
                  </q-input>
                </div>
                <div class="col-12 col-md-6">
                  <q-input
                    v-model="admissionForm.emergency_contact_relationship"
                    filled
                    label="Relationship *"
                    hint="e.g., Spouse, Parent, Sibling, Friend"
                    :rules="[val => !!val || 'Relationship is required']"
                    ref="emergencyContactRelationshipRef"
                  >
                    <template v-slot:append>
                      <q-btn
                        v-if="admissionForm.emergency_contact_relationship"
                        flat
                        dense
                        icon="clear"
                        @click="admissionForm.emergency_contact_relationship = ''"
                      />
                    </template>
                  </q-input>
                </div>
                <div class="col-12">
                  <q-input
                    v-model="admissionForm.emergency_contact_number"
                    filled
                    label="Contact Number *"
                    hint="Phone number of emergency contact"
                    :rules="[val => !!val || 'Contact number is required']"
                    ref="emergencyContactNumberRef"
                  >
                    <template v-slot:append>
                      <q-btn
                        v-if="admissionForm.emergency_contact_number"
                        flat
                        dense
                        icon="clear"
                        @click="admissionForm.emergency_contact_number = ''"
                      />
                    </template>
                  </q-input>
                </div>
              </div>
            </q-tab-panel>

            <!-- Tab 4: Bed Selection -->
            <q-tab-panel name="bed-selection">
              <div class="text-h6 q-mb-md glass-text">Bed Selection</div>
              <div class="text-body2 text-secondary q-mb-md">
                Select an available bed for {{ admissionForm.ward || 'selected ward' }}
              </div>
              <q-select
                v-model="admissionForm.bed_id"
                :options="beds"
                option-label="bed_number"
                option-value="id"
                filled
                label="Select Bed *"
                :loading="loadingBeds"
                :rules="[val => !!val || 'Please select a bed']"
                :disable="!admissionForm.ward"
                emit-value
                map-options
                ref="bedSelectRef"
              >
                <template v-slot:option="scope">
                  <q-item v-bind="scope.itemProps">
                    <q-item-section>
                      <q-item-label>{{ scope.opt.bed_number }}</q-item-label>
                      <q-item-label caption>{{ scope.opt.ward }}</q-item-label>
                    </q-item-section>
                    <q-item-section side>
                      <q-chip color="positive" text-color="white" size="sm">Available</q-chip>
                    </q-item-section>
                  </q-item>
                </template>
                <template v-slot:no-option>
                  <q-item>
                    <q-item-section class="text-grey">
                      <span v-if="!admissionForm.ward">Please select a ward first</span>
                      <span v-else>No available beds found for this ward</span>
                    </q-item-section>
                  </q-item>
                </template>
              </q-select>
            </q-tab-panel>

            <!-- Tab 5: Doctor Selection -->
            <q-tab-panel name="doctor-selection">
              <div class="text-h6 q-mb-md glass-text">Under Care Of Doctor</div>
              <div class="text-body2 text-secondary q-mb-md">
                Select the doctor who will be responsible for this patient's care
              </div>
              <q-select
                v-model="admissionForm.doctor_id"
                :options="doctors"
                option-label="full_name"
                option-value="id"
                filled
                label="Select Doctor *"
                :loading="loadingDoctors"
                :rules="[val => !!val || 'Please select a doctor']"
                emit-value
                map-options
                ref="doctorSelectRef"
              >
                <template v-slot:option="scope">
                  <q-item v-bind="scope.itemProps">
                    <q-item-section>
                      <q-item-label>{{ scope.opt.full_name }}</q-item-label>
                      <q-item-label caption>{{ scope.opt.role }}</q-item-label>
                    </q-item-section>
                  </q-item>
                </template>
              </q-select>
            </q-tab-panel>
          </q-tab-panels>
        </q-card-section>

        <q-card-actions align="right">
          <q-btn flat label="Cancel" color="primary" @click="resetForm" />
          <q-btn
            v-if="currentTab !== 'patient-info'"
            flat
            label="Previous"
            color="primary"
            @click="previousTab"
          />
          <q-btn
            v-if="currentTab !== 'doctor-selection'"
            flat
            label="Next"
            color="primary"
            @click="nextTab"
            :disable="!canProceedToNextTab"
          />
          <q-btn
            v-if="currentTab === 'doctor-selection'"
            flat
            label="Admit Patient"
            color="positive"
            @click="submitAdmission"
            :loading="submitting"
            :disable="!isFormValid"
          />
        </q-card-actions>
      </q-card>
    </div>
  </q-page>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import { useQuasar } from 'quasar';
import { patientsAPI } from '../services/api';
import { consultationAPI } from '../services/api';

const $q = useQuasar();
const router = useRouter();

const searching = ref(false);
const searchCardNumber = ref('');
const searchName = ref('');
const searchResults = ref([]);
const selectedPatient = ref(null);
const currentTab = ref('patient-info');
const submitting = ref(false);
const loadingBeds = ref(false);
const loadingDoctors = ref(false);
const beds = ref([]);
const doctors = ref([]);

const wardOptions = [
  { label: 'Accident & Emergency Ward', value: 'Accident & Emergency Ward' },
  { label: 'Maternity Ward', value: 'Maternity Ward' },
  { label: 'Female Ward', value: 'Female Ward' },
  { label: 'Male Ward', value: 'Male Ward' },
  { label: 'Kids Ward', value: 'Kids Ward' },
  { label: 'Nicu', value: 'Nicu' },
  { label: 'Detention & Observation Ward', value: 'Detention & Observation Ward' },
];

const getInitialForm = () => ({
  ward: '',
  ccc_number: '',
  emergency_contact_name: '',
  emergency_contact_relationship: '',
  emergency_contact_number: '',
  bed_id: null,
  doctor_id: null,
  admission_notes: '',
});

const admissionForm = ref(getInitialForm());

const searchPatientByCard = async () => {
  if (!searchCardNumber.value || !searchCardNumber.value.trim()) {
    $q.notify({
      type: 'warning',
      message: 'Please enter a card number',
    });
    return;
  }

  searching.value = true;
  try {
    const response = await patientsAPI.getByCard(searchCardNumber.value.trim());
    let patients = [];
    if (Array.isArray(response.data)) {
      patients = response.data;
    } else if (response.data && typeof response.data === 'object' && !Array.isArray(response.data)) {
      patients = [response.data];
    }
    
    if (patients.length === 0) {
      $q.notify({
        type: 'info',
        message: 'No patients found with that card number',
      });
      searchResults.value = [];
    } else {
      searchResults.value = patients;
    }
  } catch (error) {
    console.error('Error searching patient:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to search patient',
    });
    searchResults.value = [];
  } finally {
    searching.value = false;
  }
};

const searchPatientByName = async () => {
  if (!searchName.value || !searchName.value.trim()) {
    $q.notify({
      type: 'warning',
      message: 'Please enter a patient name',
    });
    return;
  }

  searching.value = true;
  try {
    const response = await patientsAPI.searchByName(searchName.value.trim());
    let patients = [];
    if (Array.isArray(response.data)) {
      patients = response.data;
    } else if (response.data && typeof response.data === 'object' && !Array.isArray(response.data)) {
      patients = [response.data];
    }
    
    if (patients.length === 0) {
      $q.notify({
        type: 'info',
        message: 'No patients found with that name',
      });
      searchResults.value = [];
    } else {
      searchResults.value = patients;
    }
  } catch (error) {
    console.error('Error searching patient:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to search patient',
    });
    searchResults.value = [];
  } finally {
    searching.value = false;
  }
};

const selectPatient = (patient) => {
  selectedPatient.value = patient;
  searchResults.value = [];
  searchCardNumber.value = '';
  searchName.value = '';
  
  // Auto-populate emergency contact from patient registration
  admissionForm.value = {
    ward: '',
    ccc_number: '',
    emergency_contact_name: (patient.emergency_contact_name && typeof patient.emergency_contact_name === 'string') 
      ? patient.emergency_contact_name.trim() 
      : (patient.emergency_contact_name || ''),
    emergency_contact_relationship: (patient.emergency_contact_relationship && typeof patient.emergency_contact_relationship === 'string')
      ? patient.emergency_contact_relationship.trim()
      : (patient.emergency_contact_relationship || ''),
    emergency_contact_number: (patient.emergency_contact_number && typeof patient.emergency_contact_number === 'string')
      ? patient.emergency_contact_number.trim()
      : (patient.emergency_contact_number || ''),
    bed_id: null,
    doctor_id: null,
    admission_notes: '',
  };
  
  currentTab.value = 'patient-info';
  loadDoctors();
};

const onWardSelected = () => {
  if (admissionForm.value.ward) {
    loadBeds(admissionForm.value.ward);
  } else {
    beds.value = [];
    admissionForm.value.bed_id = null;
  }
};

const loadBeds = async (ward) => {
  loadingBeds.value = true;
  try {
    const bedsResponse = await consultationAPI.getBeds(ward, true);
    beds.value = Array.isArray(bedsResponse.data) ? bedsResponse.data : [];
  } catch (error) {
    console.error('Error loading beds:', error);
    $q.notify({
      type: 'negative',
      message: 'Failed to load beds',
    });
    beds.value = [];
  } finally {
    loadingBeds.value = false;
  }
};

const loadDoctors = async () => {
  loadingDoctors.value = true;
  try {
    const doctorsResponse = await consultationAPI.getDoctors();
    doctors.value = Array.isArray(doctorsResponse.data) ? doctorsResponse.data : [];
  } catch (error) {
    console.error('Error loading doctors:', error);
    $q.notify({
      type: 'negative',
      message: 'Failed to load doctors',
    });
    doctors.value = [];
  } finally {
    loadingDoctors.value = false;
  }
};

const canProceedToNextTab = computed(() => {
  if (currentTab.value === 'patient-info') {
    return true;
  } else if (currentTab.value === 'ward-selection') {
    return !!admissionForm.value.ward;
  } else if (currentTab.value === 'emergency-contact') {
    return !!(
      admissionForm.value.emergency_contact_name &&
      admissionForm.value.emergency_contact_relationship &&
      admissionForm.value.emergency_contact_number
    );
  } else if (currentTab.value === 'bed-selection') {
    return !!admissionForm.value.bed_id;
  } else if (currentTab.value === 'doctor-selection') {
    return !!admissionForm.value.doctor_id;
  }
  return false;
});

const isFormValid = computed(() => {
  const hasWard = !!admissionForm.value.ward;
  const hasEmergencyContact = !!(
    admissionForm.value.emergency_contact_name &&
    admissionForm.value.emergency_contact_relationship &&
    admissionForm.value.emergency_contact_number
  );
  const hasBed = !!admissionForm.value.bed_id;
  const hasDoctor = !!admissionForm.value.doctor_id;
  
  return hasWard && hasEmergencyContact && hasBed && hasDoctor;
});

const nextTab = () => {
  if (currentTab.value === 'patient-info') {
    currentTab.value = 'ward-selection';
  } else if (currentTab.value === 'ward-selection') {
    currentTab.value = 'emergency-contact';
  } else if (currentTab.value === 'emergency-contact') {
    currentTab.value = 'bed-selection';
  } else if (currentTab.value === 'bed-selection') {
    currentTab.value = 'doctor-selection';
  }
};

const previousTab = () => {
  if (currentTab.value === 'doctor-selection') {
    currentTab.value = 'bed-selection';
  } else if (currentTab.value === 'bed-selection') {
    currentTab.value = 'emergency-contact';
  } else if (currentTab.value === 'emergency-contact') {
    currentTab.value = 'ward-selection';
  } else if (currentTab.value === 'ward-selection') {
    currentTab.value = 'patient-info';
  }
};

const submitAdmission = async () => {
  if (!isFormValid.value) {
    const missingFields = [];
    
    if (!admissionForm.value.ward) {
      missingFields.push('Ward Selection');
    }
    if (!admissionForm.value.emergency_contact_name || 
        !admissionForm.value.emergency_contact_relationship || 
        !admissionForm.value.emergency_contact_number) {
      missingFields.push('Emergency Contact');
    }
    if (!admissionForm.value.bed_id) {
      missingFields.push('Bed Selection');
    }
    if (!admissionForm.value.doctor_id) {
      missingFields.push('Doctor Selection');
    }
    
    $q.notify({
      type: 'negative',
      message: `Cannot save admission. Please complete all required fields: ${missingFields.join(', ')}`,
      timeout: 5000,
      position: 'top',
    });
    
    // Navigate to the first tab with missing fields
    if (!admissionForm.value.ward) {
      currentTab.value = 'ward-selection';
    } else if (!admissionForm.value.emergency_contact_name || 
               !admissionForm.value.emergency_contact_relationship || 
               !admissionForm.value.emergency_contact_number) {
      currentTab.value = 'emergency-contact';
    } else if (!admissionForm.value.bed_id) {
      currentTab.value = 'bed-selection';
    } else if (!admissionForm.value.doctor_id) {
      currentTab.value = 'doctor-selection';
    }
    
    return;
  }

  submitting.value = true;
  try {
    await consultationAPI.createDirectAdmission({
      patient_id: selectedPatient.value.id,
      patient_card_number: selectedPatient.value.card_number,
      ward: admissionForm.value.ward,
      ccc_number: admissionForm.value.ccc_number || null,
      emergency_contact_name: admissionForm.value.emergency_contact_name,
      emergency_contact_relationship: admissionForm.value.emergency_contact_relationship,
      emergency_contact_number: admissionForm.value.emergency_contact_number,
      bed_id: admissionForm.value.bed_id,
      doctor_id: admissionForm.value.doctor_id,
      admission_notes: admissionForm.value.admission_notes || null,
    });
    
    $q.notify({
      type: 'positive',
      message: 'Patient admitted successfully',
    });
    
    // Reset form and redirect
    resetForm();
    router.push('/ipd/doctor-nursing-station');
  } catch (error) {
    console.error('Error admitting patient:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to admit patient',
    });
  } finally {
    submitting.value = false;
  }
};

const resetForm = () => {
  selectedPatient.value = null;
  searchResults.value = [];
  searchCardNumber.value = '';
  searchName.value = '';
  admissionForm.value = getInitialForm();
  currentTab.value = 'patient-info';
  beds.value = [];
  doctors.value = [];
};

const formatDate = (dateString) => {
  if (!dateString) return 'N/A';
  const date = new Date(dateString);
  return date.toLocaleDateString('en-GB');
};

const isInsuranceExpired = (patient) => {
  if (!patient || !patient.insurance_end_date) return false;
  const endDate = new Date(patient.insurance_end_date);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return endDate < today;
};

const isInsuranceExpiringSoon = (patient) => {
  if (!patient || !patient.insurance_end_date) return false;
  const endDate = new Date(patient.insurance_end_date);
  const today = new Date();
  const daysUntilExpiry = Math.ceil((endDate - today) / (1000 * 60 * 60 * 24));
  return daysUntilExpiry > 0 && daysUntilExpiry <= 30;
};

const getInsuranceCardClass = (patient) => {
  if (!patient) return '';
  if (patient.insured && !isInsuranceExpired(patient)) {
    return 'bg-positive-1 border-positive';
  } else if (isInsuranceExpired(patient)) {
    return 'bg-negative-1 border-negative';
  } else if (patient.insurance_id) {
    return 'bg-warning-1 border-warning';
  }
  return '';
};

const getEndDateClass = (patient) => {
  if (!patient) return 'text-grey-7';
  if (isInsuranceExpired(patient)) return 'text-negative';
  if (isInsuranceExpiringSoon(patient)) return 'text-warning';
  return 'text-positive';
};

const getEndDateTextClass = (patient) => {
  if (!patient) return 'glass-text';
  if (isInsuranceExpired(patient)) return 'text-negative';
  if (isInsuranceExpiringSoon(patient)) return 'text-warning';
  return 'glass-text';
};

onMounted(() => {
  loadDoctors();
});
</script>

<style scoped>
.body--light .glass-text {
  color: rgba(0, 0, 0, 0.87) !important;
}

.body--dark .glass-text {
  color: rgba(255, 255, 255, 0.9) !important;
}

.insurance-info-card {
  animation: pulse-border 2s ease-in-out infinite;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15) !important;
}

@keyframes pulse-border {
  0%, 100% {
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  }
  50% {
    box-shadow: 0 6px 30px rgba(76, 175, 80, 0.3);
  }
}

.insurance-info-card.bg-positive-1 {
  animation: pulse-border-positive 2s ease-in-out infinite;
}

@keyframes pulse-border-positive {
  0%, 100% {
    box-shadow: 0 4px 20px rgba(76, 175, 80, 0.2);
  }
  50% {
    box-shadow: 0 8px 40px rgba(76, 175, 80, 0.5);
  }
}

.insurance-info-card.bg-negative-1 {
  animation: pulse-border-negative 2s ease-in-out infinite;
}

@keyframes pulse-border-negative {
  0%, 100% {
    box-shadow: 0 4px 20px rgba(244, 67, 54, 0.2);
  }
  50% {
    box-shadow: 0 8px 40px rgba(244, 67, 54, 0.5);
  }
}
</style>
