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
        NURSES TREATMENT SHEET
      </div>
    </div>

    <q-card v-if="patientInfo" class="glass-card q-mb-md" flat bordered>
      <q-card-section>
        <div class="text-h6 text-weight-bold glass-text q-mb-sm">
          Patient Information
        </div>
        <div class="row q-col-gutter-md">
          <div class="col-12 col-md-2">
            <div class="text-body2">
              <strong>NAME:</strong> {{ patientInfo.patient_name || '' }} {{ patientInfo.patient_surname || '' }}<span v-if="patientInfo.patient_other_names"> {{ patientInfo.patient_other_names }}</span>
            </div>
          </div>
          <div class="col-12 col-md-2">
            <div class="text-body2">
              <strong>SEX:</strong> {{ patientInfo.patient_gender || 'N/A' }}
            </div>
          </div>
          <div class="col-12 col-md-2">
            <div class="text-body2">
              <strong>AGED:</strong> {{ patientInfo.patient_age || 'N/A' }}
            </div>
          </div>
          <div class="col-12 col-md-2">
            <div class="text-body2">
              <strong>CARD NO:</strong> {{ patientInfo.patient_card_number || 'N/A' }}
            </div>
          </div>
          <div class="col-12 col-md-2">
            <div class="text-body2">
              <strong>WARD:</strong> {{ patientInfo.ward || 'N/A' }}
            </div>
          </div>
        </div>
      </q-card-section>
    </q-card>

    <q-card class="glass-card" flat bordered>
      <q-card-section>
        <div class="text-h6 text-weight-bold glass-text q-mb-md">
          Treatment Sheet
        </div>
        
        <div v-if="loading" class="text-center q-pa-lg">
          <q-spinner color="primary" size="3em" />
          <div class="q-mt-md">Loading prescriptions...</div>
        </div>

        <div v-else-if="!loading && prescriptions.length === 0" class="text-center q-pa-lg">
          <q-icon name="medication" size="4em" color="grey-6" />
          <div class="text-h6 q-mt-md text-grey-6">No prescriptions found</div>
          <div class="text-body2 text-grey-6">Prescriptions will appear here once they are added in a clinical review.</div>
        </div>

        <div v-else>
          <div v-for="prescription in prescriptions" :key="prescription.id" class="q-mb-md">
            <q-card class="glass-card" flat bordered>
              <q-card-section>
                <div class="text-weight-bold text-h6 q-mb-sm">{{ prescription.medicine_name }}</div>
                <div class="text-caption text-grey-7 q-mb-md">
                  {{ prescription.dose }} {{ prescription.unit }} - {{ prescription.frequency }}
                  <span v-if="prescription.instructions"> | {{ prescription.instructions }}</span>
                </div>
                
                <q-list>
                  <q-expansion-item
                    v-for="(day, dayIndex) in getDaysForPrescription(prescription)"
                    :key="`${prescription.id}-day-${dayIndex}`"
                    :label="formatDayLabel(day)"
                    :default-opened="dayIndex === 0"
                    header-class="text-weight-medium"
                    class="q-mb-xs"
                  >
                    <q-card flat>
                      <q-card-section class="q-pa-sm">
                        <q-table
                          :rows="getTimeSlotsForDay(prescription, day)"
                          :columns="dayColumns"
                          row-key="slotIndex"
                          flat
                          dense
                          :pagination="{ rowsPerPage: 0 }"
                          hide-header
                        >
                          <template v-slot:body-cell-time="props">
                            <q-td :props="props" class="q-pa-xs">
                              <div class="row items-center q-gutter-sm">
                                <div class="col-auto" style="min-width: 80px;">
                                  <span class="text-body2">
                                    <span v-if="props.row.administration">
                                      {{ formatTime(props.row.administration.administration_time) }}
                                    </span>
                                    <span v-else class="text-grey-6">Slot {{ props.row.slotIndex + 1 }}</span>
                                  </span>
                                </div>
                                <div class="col-auto">
                                  <q-checkbox
                                    :model-value="!!props.row.administration"
                                    @update:model-value="toggleAdministrationForDay(prescription, day, props.row.slotIndex, $event)"
                                    color="positive"
                                    size="sm"
                                    :disable="loading"
                                  />
                                </div>
                                <div class="col" v-if="props.row.administration">
                                  <div class="text-caption">
                                    <div><strong>Given by:</strong> {{ props.row.administration.given_by_name || 'Unknown' }}</div>
                                    <div v-if="props.row.administration.signature">
                                      <strong>Signature:</strong> {{ props.row.administration.signature }}
                                    </div>
                                    <div v-if="props.row.administration.notes">
                                      <strong>Notes:</strong> {{ props.row.administration.notes }}
                                    </div>
                                  </div>
                                </div>
                                <div class="col-auto" v-if="props.row.administration">
                                  <q-btn
                                    flat
                                    dense
                                    icon="info"
                                    size="xs"
                                    color="primary"
                                    @click="viewAdministrationDetailsForDay(prescription.id, day, props.row.slotIndex)"
                                  >
                                    <q-tooltip>View details</q-tooltip>
                                  </q-btn>
                                </div>
                              </div>
                            </q-td>
                          </template>
                        </q-table>
                      </q-card-section>
                    </q-card>
                  </q-expansion-item>
                </q-list>
              </q-card-section>
            </q-card>
          </div>
        </div>
      </q-card-section>
    </q-card>

    <!-- Administration Dialog -->
    <q-dialog v-model="showAdminDialog" persistent>
      <q-card style="min-width: 400px">
        <q-card-section>
          <div class="text-h6">Record Medication Administration</div>
        </q-card-section>

        <q-card-section>
          <q-form @submit="saveAdministration" class="q-gutter-md">
            <q-input
              v-model="adminForm.administration_date"
              filled
              type="date"
              label="Date *"
              :rules="[val => !!val || 'Date is required']"
            />

            <q-input
              v-model="adminForm.administration_time"
              filled
              type="time"
              label="Time *"
              :rules="[val => !!val || 'Time is required']"
            />

            <q-input
              v-model="adminForm.signature"
              filled
              label="Signature / Initials"
              hint="Enter your signature or initials"
            />

            <q-input
              v-model="adminForm.notes"
              filled
              type="textarea"
              label="Notes (Optional)"
              rows="3"
            />
          </q-form>
        </q-card-section>

        <q-card-actions align="right">
          <q-btn flat label="Cancel" color="primary" @click="showAdminDialog = false" />
          <q-btn
            flat
            label="Save"
            color="positive"
            @click="saveAdministration"
            :loading="saving"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Administration Details Dialog -->
    <q-dialog v-model="showDetailsDialog">
      <q-card style="min-width: 400px">
        <q-card-section>
          <div class="text-h6">Administration Details</div>
        </q-card-section>

        <q-card-section v-if="selectedAdministration">
          <div class="column q-gutter-sm">
            <div>
              <strong>Date:</strong> {{ formatDate(selectedAdministration.administration_date) }}
            </div>
            <div>
              <strong>Time:</strong> {{ selectedAdministration.administration_time }}
            </div>
            <div>
              <strong>Given By:</strong> {{ selectedAdministration.given_by_name || 'Unknown' }}
            </div>
            <div v-if="selectedAdministration.signature">
              <strong>Signature:</strong> {{ selectedAdministration.signature }}
            </div>
            <div v-if="selectedAdministration.notes">
              <strong>Notes:</strong> {{ selectedAdministration.notes }}
            </div>
          </div>
        </q-card-section>

        <q-card-actions align="right">
          <q-btn
            v-if="canDeleteAdministration"
            flat
            label="Delete"
            color="negative"
            @click="deleteAdministration"
            :loading="deleting"
          />
          <q-btn flat label="Close" color="primary" v-close-popup />
        </q-card-actions>
      </q-card>
    </q-dialog>
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

const loading = ref(false);
const saving = ref(false);
const deleting = ref(false);
const patientInfo = ref(null);
const prescriptions = ref([]);
const administrations = ref([]);

// Frequency mapping for prescriptions
const frequencyMapping = {
  "Nocte": 1,
  "Stat": 1,
  "OD": 1,
  "daily": 1,
  "PRN": 1,
  "BDS": 2,
  "BID": 2,
  "QDS": 4,
  "QID": 4,
  "TID": 3,
  "TDS": 3,
  "5X": 5,
  "EVERY OTHER DAY": 1,
  "AT BED TIME": 1,
  "6 TIMES": 6
};

// Administration dialog
const showAdminDialog = ref(false);
const showDetailsDialog = ref(false);
const selectedAdministration = ref(null);
const currentPrescription = ref(null);
const currentSlotIndex = ref(null);
const currentDay = ref(null);

const adminForm = ref({
  administration_date: new Date().toISOString().split('T')[0],
  administration_time: new Date().toTimeString().slice(0, 5),
  signature: '',
  notes: ''
});

const dayColumns = [
  {
    name: 'time',
    required: true,
    label: 'Time',
    align: 'left',
    field: 'time',
    sortable: false
  }
];

const canDeleteAdministration = computed(() => {
  if (!selectedAdministration.value) return false;
  return authStore.userRole === 'Admin' || 
         authStore.user?.id === selectedAdministration.value.given_by;
});

const loadPatientInfo = async () => {
  try {
    const response = await consultationAPI.getWardAdmission(wardAdmissionId.value);
    // Extract data from Axios response
    const admission = response.data || response;
    
    console.log('Admission data received:', admission);
    
    if (admission) {
      // Calculate age from date of birth
      let age = null;
      if (admission.patient_date_of_birth) {
        const birthDate = new Date(admission.patient_date_of_birth);
        const today = new Date();
        age = today.getFullYear() - birthDate.getFullYear();
        const monthDiff = today.getMonth() - birthDate.getMonth();
        if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birthDate.getDate())) {
          age--;
        }
      }
      
      patientInfo.value = {
        patient_name: admission.patient_name || '',
        patient_surname: admission.patient_surname || '',
        patient_other_names: admission.patient_other_names || '',
        patient_gender: admission.patient_gender || 'N/A',
        patient_age: age,
        patient_card_number: admission.patient_card_number || 'N/A',
        ward: admission.ward || 'N/A',
        bed_number: admission.bed_number || null
      };
      
      console.log('Patient info set:', patientInfo.value);
    }
  } catch (error) {
    console.error('Error loading patient info:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to load patient information',
    });
  }
};

const loadPrescriptions = async () => {
  loading.value = true;
  try {
    const response = await consultationAPI.getAllWardAdmissionPrescriptions(wardAdmissionId.value);
    // Extract data from Axios response
    const data = response.data || response;
    // Ensure response is an array
    prescriptions.value = Array.isArray(data) ? data : [];
    console.log('Prescriptions loaded:', prescriptions.value);
  } catch (error) {
    console.error('Error loading prescriptions:', error);
    prescriptions.value = []; // Set to empty array on error
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to load prescriptions',
    });
  } finally {
    loading.value = false;
  }
};

const loadAdministrations = async () => {
  try {
    const response = await consultationAPI.getTreatmentAdministrations(wardAdmissionId.value);
    // Extract data from Axios response
    const data = response.data || response;
    // Ensure response is an array
    administrations.value = Array.isArray(data) ? data : [];
    console.log('Administrations loaded:', administrations.value);
  } catch (error) {
    console.error('Error loading administrations:', error);
    administrations.value = []; // Set to empty array on error
  }
};

// Parse duration string to get number of days
const parseDuration = (durationStr) => {
  if (!durationStr) return 1;
  
  // Try to parse as a number directly
  try {
    const directNum = parseFloat(durationStr);
    if (directNum > 0) {
      return Math.floor(directNum);
    }
  } catch (e) {
    // Continue to regex parsing
  }
  
  // Extract number from string (e.g., "7 DAYS" -> 7, "4" -> 4)
  const durationMatch = durationStr.toString().match(/\d+/);
  if (durationMatch) {
    return parseInt(durationMatch[0]);
  }
  
  return 1; // Default to 1 day
};

// Get start date for prescription (use created_at or service_date)
const getPrescriptionStartDate = (prescription) => {
  if (prescription.service_date) {
    return new Date(prescription.service_date);
  }
  if (prescription.created_at) {
    return new Date(prescription.created_at);
  }
  // Default to today
  return new Date();
};

// Get array of days for a prescription
const getDaysForPrescription = (prescription) => {
  const duration = parseDuration(prescription.duration);
  const startDate = getPrescriptionStartDate(prescription);
  const days = [];
  
  for (let i = 0; i < duration; i++) {
    const dayDate = new Date(startDate);
    dayDate.setDate(startDate.getDate() + i);
    days.push(dayDate);
  }
  
  return days;
};

// Format day label for expansion item
const formatDayLabel = (day) => {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const dayDate = new Date(day);
  dayDate.setHours(0, 0, 0, 0);
  
  const isToday = dayDate.getTime() === today.getTime();
  const isTomorrow = dayDate.getTime() === today.getTime() + 86400000;
  const isYesterday = dayDate.getTime() === today.getTime() - 86400000;
  
  const dateStr = day.toLocaleDateString('en-GB', { 
    weekday: 'short', 
    day: 'numeric', 
    month: 'short', 
    year: 'numeric' 
  });
  
  if (isToday) return `Today - ${dateStr}`;
  if (isTomorrow) return `Tomorrow - ${dateStr}`;
  if (isYesterday) return `Yesterday - ${dateStr}`;
  return dateStr;
};

// Get number of times per day based on frequency
const getTimesPerDay = (prescription) => {
  // Use frequency_value if available, otherwise map from frequency string
  let timesPerDay = prescription.frequency_value;
  
  if (!timesPerDay && prescription.frequency) {
    timesPerDay = frequencyMapping[prescription.frequency] || 1;
  }
  
  // Default to 1 if still not set
  if (!timesPerDay || timesPerDay < 1) {
    timesPerDay = 1;
  }
  
  return timesPerDay;
};

// Get administrations for a specific day
const getAdministrationsForDay = (prescriptionId, day) => {
  const dayStr = day.toISOString().split('T')[0];
  return administrations.value
    .filter(admin => {
      if (admin.prescription_id !== prescriptionId) return false;
      const adminDate = new Date(admin.administration_date);
      const adminDateStr = adminDate.toISOString().split('T')[0];
      return adminDateStr === dayStr;
    })
    .sort((a, b) => {
      // Sort by time
      const timeA = a.administration_time;
      const timeB = b.administration_time;
      return timeA.localeCompare(timeB);
    });
};

// Get time slots for a specific day
const getTimeSlotsForDay = (prescription, day) => {
  const timesPerDay = getTimesPerDay(prescription);
  const dayAdministrations = getAdministrationsForDay(prescription.id, day);
  
  // Create slots array
  const slots = Array.from({ length: timesPerDay }, (_, i) => ({
    slotIndex: i,
    administration: dayAdministrations[i] || null
  }));
  
  return slots;
};

// Toggle administration for a specific day and slot
const toggleAdministrationForDay = (prescription, day, slotIndex, checked) => {
  if (checked) {
    // Open dialog to record administration
    currentPrescription.value = prescription;
    currentSlotIndex.value = slotIndex;
    currentDay.value = day;
    // Pre-fill with the day's date and current time
    const dayStr = day.toISOString().split('T')[0];
    const now = new Date();
    adminForm.value.administration_date = dayStr;
    adminForm.value.administration_time = now.toTimeString().slice(0, 5);
    showAdminDialog.value = true;
  } else {
    // Remove administration for this day and slot
    const dayAdministrations = getAdministrationsForDay(prescription.id, day);
    if (dayAdministrations[slotIndex]) {
      deleteAdministrationRecord(dayAdministrations[slotIndex].id);
    }
  }
};

const saveAdministration = async () => {
  if (!currentPrescription.value || currentSlotIndex.value === null) return;
  
  saving.value = true;
  try {
    // Use the day's date if currentDay is set, otherwise use form date
    let adminDate = adminForm.value.administration_date;
    if (currentDay.value) {
      adminDate = currentDay.value.toISOString().split('T')[0];
    }
    
    await consultationAPI.createTreatmentAdministration(wardAdmissionId.value, {
      prescription_id: currentPrescription.value.id,
      administration_date: adminDate,
      administration_time: adminForm.value.administration_time,
      signature: adminForm.value.signature || authStore.user?.full_name || '',
      notes: adminForm.value.notes || null
    });
    
    $q.notify({
      type: 'positive',
      message: 'Medication administration recorded successfully',
    });
    
    showAdminDialog.value = false;
    adminForm.value = {
      administration_date: new Date().toISOString().split('T')[0],
      administration_time: new Date().toTimeString().slice(0, 5),
      signature: '',
      notes: ''
    };
    currentPrescription.value = null;
    currentSlotIndex.value = null;
    currentDay.value = null;
    
    await loadAdministrations();
  } catch (error) {
    console.error('Error saving administration:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to record administration',
    });
  } finally {
    saving.value = false;
  }
};

const viewAdministrationDetailsForDay = (prescriptionId, day, slotIndex) => {
  const dayAdministrations = getAdministrationsForDay(prescriptionId, day);
  const admin = dayAdministrations[slotIndex];
  if (admin) {
    selectedAdministration.value = admin;
    showDetailsDialog.value = true;
  }
};

const deleteAdministration = async () => {
  if (!selectedAdministration.value) return;
  
  $q.dialog({
    title: 'Confirm Delete',
    message: 'Are you sure you want to delete this administration record?',
    cancel: true,
    persistent: true
  }).onOk(async () => {
    deleting.value = true;
    try {
      await consultationAPI.deleteTreatmentAdministration(wardAdmissionId.value, selectedAdministration.value.id);
      
      $q.notify({
        type: 'positive',
        message: 'Administration record deleted successfully',
      });
      
      showDetailsDialog.value = false;
      selectedAdministration.value = null;
      await loadAdministrations();
    } catch (error) {
      console.error('Error deleting administration:', error);
      $q.notify({
        type: 'negative',
        message: error.response?.data?.detail || 'Failed to delete administration',
      });
    } finally {
      deleting.value = false;
    }
  });
};

const deleteAdministrationRecord = async (administrationId) => {
  $q.dialog({
    title: 'Confirm Delete',
    message: 'Are you sure you want to remove this administration record?',
    cancel: true,
    persistent: true
  }).onOk(async () => {
    try {
      await consultationAPI.deleteTreatmentAdministration(wardAdmissionId.value, administrationId);
      await loadAdministrations();
    } catch (error) {
      console.error('Error deleting administration:', error);
      $q.notify({
        type: 'negative',
        message: error.response?.data?.detail || 'Failed to delete administration',
      });
    }
  });
};

const formatDate = (dateString) => {
  if (!dateString) return '';
  const date = new Date(dateString);
  return date.toLocaleDateString('en-GB');
};

const formatTime = (timeString) => {
  if (!timeString) return '';
  // timeString is in HH:MM format
  const [hours, minutes] = timeString.split(':');
  const hour = parseInt(hours);
  const ampm = hour >= 12 ? 'PM' : 'AM';
  const hour12 = hour % 12 || 12;
  return `${hour12}:${minutes} ${ampm}`;
};

const formatDateTime = (administration) => {
  if (!administration) return '';
  const date = new Date(`${administration.administration_date}T${administration.administration_time}`);
  return date.toLocaleString('en-GB', { 
    day: '2-digit', 
    month: '2-digit', 
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: true
  });
};

const goBack = () => {
  router.push(`/ipd/admission-manager/${wardAdmissionId.value}`);
};

onMounted(async () => {
  await loadPatientInfo();
  await loadPrescriptions();
  await loadAdministrations();
});
</script>

<style scoped>
.glass-table {
  background: transparent;
}
</style>

