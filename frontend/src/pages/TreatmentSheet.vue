<template>
  <q-page class="hms-page">
    <HmsPageHeader
      title="Treatment sheet"
      subtitle="Nurses treatment sheet and prescribed medications for this admission."
    >
      <template #actions>
        <HmsButton variant="secondary" size="sm" @click="goBack">Back to manager</HmsButton>
      </template>
    </HmsPageHeader>

    <div v-if="patientInfo" class="ipd-patient-hero">
      <div class="ipd-hero-main">
        <div class="ipd-hero-avatar">{{ tsPatientInitials(patientInfo) }}</div>
        <div>
          <h1 class="ipd-hero-name">{{ tsPatientDisplayName(patientInfo) }}</h1>
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

    <section class="am-panel ts-board">
      <div class="am-panel-head ts-board-head">
        <div>
          <h2 class="hms-section-title">Medication chart</h2>
          <p class="ts-board-sub">Pick a day, then tick each dose slot as medication is given.</p>
        </div>
        <div class="ts-day-nav">
          <HmsButton variant="secondary" size="sm" @click="shiftSheetDay(-1)">
            <ChevronLeft :size="14" />
          </HmsButton>
          <HmsButton variant="secondary" size="sm" @click="setSheetToday">Today</HmsButton>
          <HmsButton variant="secondary" size="sm" @click="shiftSheetDay(1)">
            <ChevronRight :size="14" />
          </HmsButton>
        </div>
      </div>

      <div v-if="loading" class="ts-loading">
        <q-spinner color="primary" size="2.5em" />
        <span>Loading prescriptions…</span>
      </div>

      <div v-else-if="prescriptions.length === 0" class="ts-empty">
        No prescriptions found. They appear here after a clinical review.
      </div>

      <template v-else>
        <div class="ts-calendar-strip" role="tablist" aria-label="Treatment days">
          <button
            v-for="day in courseDayStrip"
            :key="day.iso"
            type="button"
            role="tab"
            class="ts-day-chip"
            :class="{
              active: selectedSheetDate === day.iso,
              today: day.isToday,
              complete: day.allComplete,
              partial: day.hasAny && !day.allComplete,
            }"
            @click="selectedSheetDate = day.iso"
          >
            <span class="ts-day-chip-week">{{ day.weekday }}</span>
            <span class="ts-day-chip-num">{{ day.dayNum }}</span>
            <span class="ts-day-chip-dots">
              <span
                v-for="n in Math.min(day.medCount, 4)"
                :key="n"
                class="ts-dot"
                :class="{ on: day.givenCount >= n }"
              />
            </span>
          </button>
        </div>

        <div class="ts-selected-meta">
          <strong>{{ selectedDayLabel }}</strong>
          <span>{{ prescriptionsForSelectedDay.length }} medicine{{ prescriptionsForSelectedDay.length === 1 ? '' : 's' }}</span>
          <span>{{ selectedDayProgress.given }}/{{ selectedDayProgress.total }} doses given</span>
        </div>

        <div v-if="prescriptionsForSelectedDay.length === 0" class="ts-empty">
          No medications scheduled for this day.
        </div>

        <div v-else class="ts-med-list">
          <article
            v-for="prescription in prescriptionsForSelectedDay"
            :key="prescription.id"
            class="ts-med-card"
          >
            <div class="ts-med-top">
              <div>
                <h3 class="ts-med-name">{{ prescription.medicine_name }}</h3>
                <div class="ts-med-meta">
                  <span>{{ prescription.dose }} {{ prescription.unit }}</span>
                  <span class="sep">·</span>
                  <span>{{ prescription.frequency }}</span>
                  <template v-if="prescription.duration">
                    <span class="sep">·</span>
                    <span>{{ prescription.duration }}</span>
                  </template>
                </div>
                <div v-if="prescription.instructions" class="ts-med-instructions">
                  {{ prescription.instructions }}
                </div>
              </div>
              <div class="ts-med-progress" :class="progressTone(prescription)">
                {{ dayGivenCount(prescription) }}/{{ getTimesPerDay(prescription) }}
              </div>
            </div>

            <div class="ts-slot-ticker" role="group" :aria-label="`Dose slots for ${prescription.medicine_name}`">
              <button
                v-for="slot in getTimeSlotsForDay(prescription, selectedDayDate)"
                :key="slot.slotIndex"
                type="button"
                class="ts-slot"
                :class="{ given: !!slot.administration }"
                :disabled="loading"
                @click="onSlotClick(prescription, slot)"
              >
                <span class="ts-slot-check" aria-hidden="true">
                  <Check v-if="slot.administration" :size="14" />
                </span>
                <span class="ts-slot-label">
                  <template v-if="slot.administration">
                    {{ formatTime(slot.administration.administration_time) }}
                  </template>
                  <template v-else>
                    Slot {{ slot.slotIndex + 1 }}
                  </template>
                </span>
                <span v-if="slot.administration" class="ts-slot-by">
                  {{ slot.administration.given_by_name || 'Given' }}
                </span>
              </button>
            </div>
          </article>
        </div>
      </template>
    </section>

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

        <q-card-actions align="right" class="q-gutter-sm">
          <q-btn flat label="Cancel" color="primary" @click="showAdminDialog = false" />
          <HmsButton variant="primary" :loading="saving" @click="saveAdministration">
            Save
          </HmsButton>
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
import { ChevronLeft, ChevronRight, Check } from 'lucide-vue-next';
import HmsPageHeader from '../components/ui/HmsPageHeader.vue';
import HmsButton from '../components/ui/HmsButton.vue';
import { consultationAPI } from '../services/api';
import { useAuthStore } from '../stores/auth';
import { getApplicationTodaySync } from '../utils/dateUtils';

const $q = useQuasar();
const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();

const tsPatientInitials = (info) => {
  if (!info) return '?';
  const a = (info.patient_name || '').trim().charAt(0);
  const b = (info.patient_surname || '').trim().charAt(0);
  return ((a + b) || '?').toUpperCase();
};
const tsPatientDisplayName = (info) => {
  if (!info) return '';
  return [info.patient_name, info.patient_surname, info.patient_other_names].filter(Boolean).join(' ');
};

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
  // Use application date (from reference date if configured) instead of system date
  const today = getApplicationTodaySync();
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


const selectedSheetDate = ref(getApplicationTodaySync().toISOString().split('T')[0]);

const toIsoDay = (d) => {
  const x = new Date(d);
  x.setHours(12, 0, 0, 0);
  return x.toISOString().split('T')[0];
};

const selectedDayDate = computed(() => new Date(`${selectedSheetDate.value}T12:00:00`));

const isPrescriptionActiveOn = (prescription, day) => {
  const days = getDaysForPrescription(prescription);
  const iso = toIsoDay(day);
  return days.some((d) => toIsoDay(d) === iso);
};

const prescriptionsForSelectedDay = computed(() =>
  prescriptions.value.filter((p) => isPrescriptionActiveOn(p, selectedDayDate.value))
);

const courseDayStrip = computed(() => {
  const map = new Map();
  const todayIso = toIsoDay(getApplicationTodaySync());

  for (const p of prescriptions.value) {
    for (const day of getDaysForPrescription(p)) {
      const iso = toIsoDay(day);
      if (!map.has(iso)) {
        const d = new Date(`${iso}T12:00:00`);
        map.set(iso, {
          iso,
          date: d,
          weekday: d.toLocaleDateString('en-GB', { weekday: 'short' }),
          dayNum: d.getDate(),
          isToday: iso === todayIso,
          medCount: 0,
          givenCount: 0,
          totalSlots: 0,
          hasAny: false,
          allComplete: false,
        });
      }
      const entry = map.get(iso);
      entry.medCount += 1;
      const slots = getTimesPerDay(p);
      entry.totalSlots += slots;
      const given = getAdministrationsForDay(p.id, day).length;
      entry.givenCount += Math.min(given, slots);
    }
  }

  const list = Array.from(map.values()).sort((a, b) => a.iso.localeCompare(b.iso));
  for (const entry of list) {
    entry.hasAny = entry.givenCount > 0;
    entry.allComplete = entry.totalSlots > 0 && entry.givenCount >= entry.totalSlots;
  }
  return list;
});

const selectedDayLabel = computed(() => formatDayLabel(selectedDayDate.value));

const selectedDayProgress = computed(() => {
  let total = 0;
  let given = 0;
  for (const p of prescriptionsForSelectedDay.value) {
    const slots = getTimesPerDay(p);
    total += slots;
    given += Math.min(getAdministrationsForDay(p.id, selectedDayDate.value).length, slots);
  }
  return { total, given };
});

const dayGivenCount = (prescription) =>
  Math.min(
    getAdministrationsForDay(prescription.id, selectedDayDate.value).length,
    getTimesPerDay(prescription)
  );

const progressTone = (prescription) => {
  const total = getTimesPerDay(prescription);
  const given = dayGivenCount(prescription);
  if (given >= total) return 'done';
  if (given > 0) return 'partial';
  return 'pending';
};

const shiftSheetDay = (delta) => {
  const strip = courseDayStrip.value;
  if (!strip.length) {
    const d = new Date(`${selectedSheetDate.value}T12:00:00`);
    d.setDate(d.getDate() + delta);
    selectedSheetDate.value = toIsoDay(d);
    return;
  }
  const idx = strip.findIndex((d) => d.iso === selectedSheetDate.value);
  const next = strip[Math.min(Math.max((idx < 0 ? 0 : idx) + delta, 0), strip.length - 1)];
  if (next) selectedSheetDate.value = next.iso;
};

const setSheetToday = () => {
  const todayIso = toIsoDay(getApplicationTodaySync());
  const strip = courseDayStrip.value;
  if (strip.some((d) => d.iso === todayIso)) {
    selectedSheetDate.value = todayIso;
  } else if (strip.length) {
    selectedSheetDate.value = strip.reduce((best, d) => {
      const bd = Math.abs(new Date(best).getTime() - new Date(todayIso).getTime());
      const dd = Math.abs(new Date(d.iso).getTime() - new Date(todayIso).getTime());
      return dd < bd ? d.iso : best;
    }, strip[0].iso);
  } else {
    selectedSheetDate.value = todayIso;
  }
};

const onSlotClick = (prescription, slot) => {
  if (slot.administration) {
    viewAdministrationDetailsForDay(prescription.id, selectedDayDate.value, slot.slotIndex);
    return;
  }
  toggleAdministrationForDay(prescription, selectedDayDate.value, slot.slotIndex, true);
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
  setSheetToday();
});
</script>

<style scoped>

.ts-board-sub {
  margin: 0.2rem 0 0;
  font-size: var(--hms-text-sm);
  color: var(--hms-text-muted);
}
.ts-board-head { align-items: flex-end; }
.ts-day-nav { display: inline-flex; gap: 0.4rem; }
.ts-loading, .ts-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.65rem;
  padding: 2.5rem 1rem;
  color: var(--hms-text-muted);
  font-size: var(--hms-text-sm);
  text-align: center;
}
.ts-calendar-strip {
  display: flex;
  gap: 0.45rem;
  overflow-x: auto;
  padding: 0.35rem 0.15rem 0.65rem;
  margin-bottom: 0.55rem;
  scrollbar-width: thin;
}
.ts-day-chip {
  flex: 0 0 auto;
  width: 3.55rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.15rem;
  padding: 0.55rem 0.35rem 0.45rem;
  border-radius: var(--hms-radius-lg);
  border: 1px solid var(--hms-border);
  background: var(--hms-surface);
  color: var(--hms-text-secondary);
  font-family: inherit;
  cursor: pointer;
  transition: border-color var(--hms-duration-fast) var(--hms-ease-out),
    box-shadow var(--hms-duration-fast) var(--hms-ease-out),
    background var(--hms-duration-fast) var(--hms-ease-out);
}
.ts-day-chip:hover { border-color: var(--hms-accent); }
.ts-day-chip.active {
  background: var(--hms-accent-muted);
  border-color: rgba(59, 130, 246, 0.35);
  color: var(--hms-accent);
  box-shadow: var(--hms-shadow-sm);
}
.ts-day-chip.today:not(.active) {
  border-color: rgba(59, 130, 246, 0.35);
}
.ts-day-chip-week {
  font-size: 0.62rem;
  font-weight: 750;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.ts-day-chip-num {
  font-size: 1.05rem;
  font-weight: 750;
  line-height: 1;
  color: var(--hms-text-primary);
}
.ts-day-chip.active .ts-day-chip-num { color: var(--hms-accent); }
.ts-day-chip-dots { display: flex; gap: 0.15rem; min-height: 0.35rem; }
.ts-dot {
  width: 0.28rem; height: 0.28rem; border-radius: 999px;
  background: rgba(148, 163, 184, 0.45);
}
.ts-dot.on { background: var(--hms-success); }
.ts-day-chip.complete { box-shadow: inset 0 -2px 0 var(--hms-success); }
.ts-day-chip.partial { box-shadow: inset 0 -2px 0 #f59e0b; }
.ts-selected-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem 1rem;
  margin-bottom: 0.85rem;
  font-size: var(--hms-text-sm);
  color: var(--hms-text-secondary);
  font-weight: 600;
}
.ts-selected-meta strong { color: var(--hms-text-primary); }
.ts-med-list { display: flex; flex-direction: column; gap: 0.65rem; }
.ts-med-card {
  padding: 0.95rem 1rem;
  border-radius: var(--hms-radius-lg);
  border: 1px solid var(--hms-border);
  background: var(--hms-surface);
}
.ts-med-top {
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
  align-items: flex-start;
  margin-bottom: 0.75rem;
}
.ts-med-name {
  margin: 0;
  font-size: var(--hms-text-md);
  font-weight: 750;
  color: var(--hms-text-primary);
}
.ts-med-meta {
  margin-top: 0.25rem;
  font-size: var(--hms-text-sm);
  color: var(--hms-text-secondary);
  display: flex; flex-wrap: wrap; align-items: center;
}
.ts-med-meta .sep { margin: 0 0.3rem; opacity: 0.4; }
.ts-med-instructions {
  margin-top: 0.3rem;
  font-size: var(--hms-text-sm);
  color: var(--hms-text-muted);
}
.ts-med-progress {
  flex-shrink: 0;
  min-width: 2.75rem;
  text-align: center;
  padding: 0.3rem 0.5rem;
  border-radius: var(--hms-radius-md);
  font-size: 0.78rem;
  font-weight: 750;
  font-variant-numeric: tabular-nums;
  background: var(--hms-panel-bg);
  border: 1px solid var(--hms-border);
  color: var(--hms-text-secondary);
}
.ts-med-progress.partial {
  background: var(--hms-warning-muted);
  color: #b45309;
  border-color: rgba(245, 158, 11, 0.28);
}
.ts-med-progress.done {
  background: var(--hms-success-muted);
  color: var(--hms-success);
  border-color: rgba(34, 197, 94, 0.28);
}
.ts-slot-ticker {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
}
.ts-slot {
  display: inline-flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.15rem;
  min-width: 5.5rem;
  padding: 0.55rem 0.65rem;
  border-radius: var(--hms-radius-md);
  border: 1px dashed var(--hms-border);
  background: var(--hms-panel-bg);
  color: var(--hms-text-secondary);
  font-family: inherit;
  cursor: pointer;
  text-align: left;
  transition: border-color var(--hms-duration-fast) var(--hms-ease-out),
    background var(--hms-duration-fast) var(--hms-ease-out),
    transform var(--hms-duration-fast) var(--hms-ease-out);
}
.ts-slot:hover:not(:disabled) {
  border-color: var(--hms-accent);
  transform: translateY(-1px);
}
.ts-slot:disabled { opacity: 0.6; cursor: not-allowed; }
.ts-slot.given {
  border-style: solid;
  border-color: rgba(34, 197, 94, 0.35);
  background: var(--hms-success-muted);
  color: var(--hms-success);
}
.ts-slot-check {
  width: 1.15rem; height: 1.15rem;
  border-radius: 999px;
  border: 1.5px solid currentColor;
  display: grid; place-items: center;
  opacity: 0.55;
}
.ts-slot.given .ts-slot-check {
  opacity: 1;
  background: var(--hms-success);
  border-color: var(--hms-success);
  color: #fff;
}
.ts-slot-label { font-size: 0.78rem; font-weight: 750; }
.ts-slot-by { font-size: 0.65rem; opacity: 0.85; max-width: 7rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
@media (max-width: 640px) {
  .ts-slot { flex: 1 1 calc(50% - 0.45rem); }
}

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
.am-panel--nested {
  margin-bottom: 0.75rem;
  box-shadow: var(--hms-shadow-sm, var(--hms-shadow-md));
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


.glass-table {
  background: transparent;
}
</style>

