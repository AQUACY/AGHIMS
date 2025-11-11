<template>
  <q-page class="q-pa-md">
    <div class="row items-center q-mb-md">
      <q-btn
        flat
        icon="arrow_back"
        label="Back to Ward"
        @click="$router.push('/ipd/doctor-nursing-station')"
        class="q-mr-md"
      />
      <div class="text-h4 text-weight-bold glass-text">
        Admission Manager
      </div>
    </div>

    <!-- Patient Info Card -->
    <q-card v-if="patientInfo" class="glass-card q-mb-md" flat bordered>
      <q-card-section>
        <div class="row items-center">
          <q-avatar size="64px" color="primary" text-color="white" class="q-mr-md">
            <q-icon name="person" size="40px" />
          </q-avatar>
          <div class="col">
            <div class="text-h5 text-weight-bold glass-text q-mb-xs">
              {{ patientInfo.patient_name }} {{ patientInfo.patient_surname }}
              <span v-if="patientInfo.patient_other_names">
                {{ patientInfo.patient_other_names }}
              </span>
            </div>
            <div class="row q-col-gutter-md q-mt-sm">
              <div class="col-12 col-md-6">
                <div class="text-body2 text-secondary">
                  <q-icon name="credit_card" size="16px" class="q-mr-xs" />
                  Card: {{ patientInfo.patient_card_number }}
                </div>
                <div class="text-body2 text-secondary q-mt-xs">
                  <q-icon name="person" size="16px" class="q-mr-xs" />
                  {{ patientInfo.patient_gender }}
                  <span v-if="patientInfo.patient_date_of_birth" class="q-ml-sm">
                    | DOB: {{ formatDate(patientInfo.patient_date_of_birth) }}
                  </span>
                </div>
              </div>
              <div class="col-12 col-md-6">
                <div class="text-body2 text-secondary">
                  <q-icon name="local_hospital" size="16px" class="q-mr-xs" />
                  Ward: <strong>{{ patientInfo.ward }}</strong>
                </div>
                <div class="text-body2 text-secondary q-mt-xs">
                  <q-icon name="schedule" size="16px" class="q-mr-xs" />
                  Admitted: {{ formatDateTime(patientInfo.admitted_at) }}
                </div>
                <div v-if="patientInfo.admitted_by_name" class="text-body2 text-secondary q-mt-xs">
                  <q-icon name="person" size="16px" class="q-mr-xs" />
                  Admitted by: <strong>{{ patientInfo.admitted_by_name }}</strong>
                  <span v-if="patientInfo.admitted_by_role"> ({{ patientInfo.admitted_by_role }})</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </q-card-section>
    </q-card>

    <!-- Emergency Contact Card -->
    <q-card v-if="patientInfo" class="glass-card q-mb-md" flat bordered>
      <q-card-section>
        <div class="text-h6 glass-text q-mb-md">
          <q-icon name="contact_phone" color="info" class="q-mr-sm" />
          Emergency Contact
        </div>
        <div v-if="patientInfo.emergency_contact_name || patientInfo.emergency_contact_number" class="row q-col-gutter-md">
          <div class="col-12 col-md-4">
            <div class="text-body2 text-secondary">Contact Name</div>
            <div class="text-body1 glass-text q-mt-xs">
              <strong>{{ patientInfo.emergency_contact_name || 'N/A' }}</strong>
            </div>
          </div>
          <div class="col-12 col-md-4">
            <div class="text-body2 text-secondary">Relationship</div>
            <div class="text-body1 glass-text q-mt-xs">
              <strong>{{ patientInfo.emergency_contact_relationship || 'N/A' }}</strong>
            </div>
          </div>
          <div class="col-12 col-md-4">
            <div class="text-body2 text-secondary">Contact Number</div>
            <div class="text-body1 glass-text q-mt-xs">
              <strong>
                <a 
                  v-if="patientInfo.emergency_contact_number" 
                  :href="`tel:${patientInfo.emergency_contact_number}`"
                  class="text-primary text-weight-bold"
                  style="text-decoration: none;"
                >
                  <q-icon name="phone" size="18px" class="q-mr-xs" />
                  {{ patientInfo.emergency_contact_number }}
                </a>
                <span v-else>N/A</span>
              </strong>
            </div>
          </div>
        </div>
        <div v-else class="text-body2 text-secondary text-center q-pa-md">
          <q-icon name="info" color="warning" size="24px" class="q-mb-sm" />
          <div>No emergency contact information available</div>
        </div>
      </q-card-section>
    </q-card>

    <!-- Loading State -->
    <q-card v-if="loading" class="glass-card" flat>
      <q-card-section class="text-center">
        <q-spinner color="primary" size="3em" />
        <div class="text-subtitle1 q-mt-md glass-text">Loading patient information...</div>
      </q-card-section>
    </q-card>

    <!-- Main Content Layout -->
    <div v-else class="row q-col-gutter-md">
      <!-- Main Body - Middle Section -->
      <div class="col-12 col-md-8 col-lg-9">
        <q-card class="glass-card" flat bordered>
          <q-card-section>
            <div class="text-h6 glass-text q-mb-md">
              Inpatient Activities
            </div>
            
            <!-- Admission Notes Table -->
            <q-table
              :rows="admissionNotesRows"
              :columns="admissionNotesColumns"
              row-key="label"
              flat
              hide-pagination
              class="glass-table"
            >
              <template v-slot:body-cell-notes="props">
                <q-td :props="props" class="q-pa-md">
                  <div v-if="props.row.isTable" class="column q-gutter-sm">
                    <div class="row items-center justify-between">
                      <div class="text-body2 text-secondary">
                        {{ getTableItemCount(props.row.type) }} record(s)
                      </div>
                      <q-btn
                        flat
                        dense
                        icon="add"
                        label="Add New"
                        color="primary"
                        size="sm"
                        @click="openTableItemDialog(props.row.type, null)"
                      />
                    </div>
                    <q-btn
                      v-if="props.row.type === 'transfers'"
                      flat
                      dense
                      icon="visibility"
                      label="View All"
                      color="secondary"
                      size="sm"
                      @click="viewTableItems(props.row.type)"
                    />
                  </div>
                  <!-- Show accepted transfers count for transfers type -->
                  <div v-if="props.row.type === 'transfers'" class="q-mt-sm">
                    <div class="text-caption text-secondary">
                      Showing {{ transfers.filter(t => t.status === 'accepted').length }} accepted transfer(s)
                    </div>
                  </div>
                  <div v-else-if="props.value" class="column q-gutter-sm">
                    <div class="text-body2 glass-text" style="white-space: pre-wrap; word-wrap: break-word;">
                      {{ props.value }}
                    </div>
                    <div class="row justify-end">
                      <q-btn
                        flat
                        dense
                        icon="edit"
                        label="Edit"
                        color="primary"
                        size="sm"
                        @click="openDocumentationDialog(props.row.type, props.value)"
                      />
                    </div>
                  </div>
                  <div v-else class="column items-center q-pa-md">
                    <q-icon name="edit" size="32px" color="grey-6" class="q-mb-sm" />
                    <q-btn
                      flat
                      dense
                      icon="edit"
                      label="Add Notes"
                      color="primary"
                      size="sm"
                      @click="openDocumentationDialog(props.row.type, null)"
                    />
                  </div>
                </q-td>
              </template>
            </q-table>
          </q-card-section>
        </q-card>
      </div>

      <!-- Right Sidebar - Quick Actions -->
      <div class="col-12 col-md-4 col-lg-3">
        <q-card class="glass-card" flat bordered>
          <q-card-section>
            <div class="text-h6 glass-text q-mb-md">
              <q-icon name="flash_on" color="primary" class="q-mr-sm" />
              Quick Actions
            </div>
            <div class="column q-gutter-sm">
              <q-btn
                flat
                icon="visibility"
                label="View Patient Profile"
                color="primary"
                @click="viewPatient"
                class="full-width"
              />
              <q-btn
                flat
                icon="medical_services"
                label="View Encounter"
                color="secondary"
                @click="viewEncounter"
                class="full-width"
              />
              <q-btn
                flat
                icon="monitor_heart"
                label="Add Vitals"
                color="info"
                @click="addVitals"
                class="full-width"
              />
              <q-btn
                flat
                icon="medication"
                label="Prescriptions"
                color="accent"
                @click="viewPrescriptions"
                class="full-width"
              />
              <q-btn
                flat
                icon="science"
                label="Investigations"
                color="purple"
                @click="viewInvestigations"
                class="full-width"
              />
              <q-separator class="q-my-sm" />
              <div class="text-subtitle2 text-weight-bold glass-text q-mb-sm">
                <q-icon name="link" color="primary" class="q-mr-sm" />
                Quick Links
              </div>
              <q-btn
                flat
                icon="note_add"
                label="Nurse Note"
                color="orange"
                @click="addNurseNote"
                class="full-width"
              />
              <q-btn
                flat
                icon="description"
                label="Nurse Mid Documentation"
                color="teal"
                @click="viewNurseMidDocumentation"
                class="full-width"
              />
              <q-btn
                flat
                icon="receipt"
                label="Billing"
                color="amber"
                @click="viewBilling"
                class="full-width"
              />
              <q-separator class="q-my-sm" />
              <q-btn
                flat
                icon="exit_to_app"
                label="Discharge Patient"
                color="negative"
                @click="dischargePatient"
                :loading="discharging"
                class="full-width"
              />
              <q-btn
                flat
                icon="cancel"
                label="Cancel Admission"
                color="negative"
                @click="cancelAdmission"
                :loading="cancelling"
                class="full-width"
              />
            </div>
          </q-card-section>
        </q-card>
      </div>
    </div>

          <!-- Documentation Dialog -->
          <q-dialog v-model="showAdmissionNotesDialog" persistent>
            <q-card style="min-width: 500px; max-width: 800px;">
              <q-card-section>
                <div class="text-h6 glass-text">
                  {{ documentationTypeLabels[currentDocumentationType] || 'Documentation' }}
                </div>
              </q-card-section>

              <q-card-section>
                <q-input
                  v-model="admissionNotes"
                  filled
                  type="textarea"
                  label="Notes"
                  :hint="`Enter ${documentationTypeLabels[currentDocumentationType]?.toLowerCase() || 'notes'} for this patient`"
                  rows="10"
                  autofocus
                />
              </q-card-section>

              <q-card-actions align="right">
                <q-btn flat label="Cancel" color="primary" @click="showAdmissionNotesDialog = false" />
                <q-btn
                  flat
                  label="Save"
                  color="positive"
                  @click="saveDocumentation"
                  :loading="savingNotes"
                />
              </q-card-actions>
            </q-card>
          </q-dialog>

          <!-- Table Item Dialog -->
          <q-dialog v-model="showTableItemDialog" persistent>
            <q-card style="min-width: 600px; max-width: 1000px; max-height: 90vh; display: flex; flex-direction: column;">
              <q-card-section class="q-pb-none">
                <div class="text-h6 glass-text">
                  Add {{ documentationTypeLabels[currentTableType] || 'Item' }}
                </div>
              </q-card-section>

              <q-card-section style="flex: 1; overflow-y: auto;" class="q-pt-md">
                <div v-if="currentTableType === 'vitals'" class="column q-gutter-md">
                  <div class="row q-col-gutter-md">
                    <div class="col-6">
                      <q-input
                        v-model.number="tableItemData.temperature"
                        filled
                        type="number"
                        label="Temperature (°C)"
                        hint="Body temperature"
                      />
                    </div>
                    <div class="col-6">
                      <q-input
                        v-model.number="tableItemData.pulse"
                        filled
                        type="number"
                        label="Pulse (bpm)"
                        hint="Heart rate"
                      />
                    </div>
                  </div>
                  <div class="row q-col-gutter-md">
                    <div class="col-6">
                      <q-input
                        v-model.number="tableItemData.blood_pressure_systolic"
                        filled
                        type="number"
                        label="BP Systolic (mmHg)"
                      />
                    </div>
                    <div class="col-6">
                      <q-input
                        v-model.number="tableItemData.blood_pressure_diastolic"
                        filled
                        type="number"
                        label="BP Diastolic (mmHg)"
                      />
                    </div>
                  </div>
                  <div class="row q-col-gutter-md">
                    <div class="col-6">
                      <q-input
                        v-model.number="tableItemData.respiratory_rate"
                        filled
                        type="number"
                        label="Respiratory Rate (bpm)"
                      />
                    </div>
                    <div class="col-6">
                      <q-input
                        v-model.number="tableItemData.oxygen_saturation"
                        filled
                        type="number"
                        label="O2 Saturation (%)"
                        step="0.1"
                      />
                    </div>
                  </div>
                  <div class="row q-col-gutter-md">
                    <div class="col-6">
                      <q-input
                        v-model.number="tableItemData.weight"
                        filled
                        type="number"
                        label="Weight (kg)"
                        step="0.1"
                      />
                    </div>
                    <div class="col-6">
                      <q-input
                        v-model.number="tableItemData.height"
                        filled
                        type="number"
                        label="Height (cm)"
                        step="0.1"
                      />
                    </div>
                  </div>
                  <q-input
                    v-model="tableItemData.notes"
                    filled
                    type="textarea"
                    label="Notes"
                    rows="3"
                  />
                </div>
                <div v-else-if="currentTableType === 'nurses_notes'" class="column q-gutter-md">
                  <!-- Nurses Note Form - Matching the attached image format -->
                  <div class="text-subtitle2 text-weight-bold glass-text q-mb-sm">
                    MOH / GHANA HEALTH SERVICE
                  </div>
                  <div class="text-h6 text-weight-bold glass-text q-mb-sm">
                    NURSES NOTE
                  </div>
                  <div class="text-caption text-warning q-mb-md">
                    USE RED INK FOR NIGHT NOTES
                  </div>
                  
                  <q-separator class="q-mb-md" />
                  
                  <div class="row q-col-gutter-md q-mb-md">
                    <div class="col-12 col-md-6">
                      <q-input
                        v-model="tableItemData.note_date"
                        filled
                        type="date"
                        label="Date *"
                        :rules="[val => !!val || 'Date is required']"
                      />
                    </div>
                    <div class="col-12 col-md-6">
                      <q-input
                        v-model="tableItemData.note_hour"
                        filled
                        type="time"
                        label="Hour *"
                        :rules="[val => !!val || 'Hour is required']"
                      />
                    </div>
                  </div>
                  
                  <q-separator class="q-mb-md" />
                  
                  <div class="text-body2 text-secondary q-mb-sm">
                    HOSPITAL REGULATIONS - The Signature of a nurse shall accompany each entry
                  </div>
                  
                  <q-separator class="q-mb-md" />
                  
                  <div class="text-body2 text-secondary q-mb-sm">
                    NOTES * (Use formatting tools to differentiate day/night shifts)
                  </div>
                  
                  <!-- Color Picker Controls (Only for Nurse Notes) -->
                  <div v-if="currentTableType === 'nurses_notes'" class="row q-col-gutter-sm q-mb-md">
                    <div class="col-12 col-md-6">
                      <div class="row items-center q-gutter-sm">
                        <q-icon name="format_color_text" size="20px" color="primary" />
                        <div class="text-body2 text-weight-medium">Text Color:</div>
                        <q-btn
                          flat
                          dense
                          icon="format_color_text"
                          :style="`background-color: ${selectedTextColor}; color: ${getContrastColor(selectedTextColor)}; min-width: 50px;`"
                          size="sm"
                        >
                          <q-popup-proxy>
                            <q-color
                              v-model="selectedTextColor"
                              format-model="hex"
                            />
                          </q-popup-proxy>
                        </q-btn>
                        <q-btn
                          flat
                          dense
                          icon="check"
                          label="Apply"
                          size="sm"
                          color="primary"
                          @click="applyTextColor"
                        />
                      </div>
                    </div>
                    <div class="col-12 col-md-6">
                      <div class="row items-center q-gutter-sm">
                        <!-- <q-icon name="format_color_fill" size="20px" color="secondary" /> -->
                        <!-- <div class="text-body2 text-weight-medium">Background Color:</div>
                        <q-btn
                          flat
                          dense
                          icon="format_color_fill"
                          :style="`background-color: ${selectedBgColor}; color: ${getContrastColor(selectedBgColor)}; min-width: 50px;`"
                          size="sm"
                        >
                          <q-popup-proxy>
                            <q-color
                              v-model="selectedBgColor"
                              format-model="hex"
                            />
                          </q-popup-proxy>
                        </q-btn> -->
                        <!-- <q-btn
                          flat
                          dense
                          icon="check"
                          label="Apply"
                          size="sm"
                          color="secondary"
                          @click="applyBgColor"
                        /> -->
                      </div>
                    </div>
                  </div>
                  
                  <q-editor
                    v-if="currentTableType === 'nurses_notes'"
                    ref="nurseNoteEditor"
                    v-model="tableItemData.notes"
                    :toolbar="[
                      ['bold', 'italic', 'strike', 'underline'],
                      ['left', 'center', 'right', 'justify'],
                      ['quote', 'unordered', 'ordered'],
                      ['undo', 'redo'],
                      ['viewsource']
                    ]"
                    :fonts="{
                      arial: 'Arial',
                      arial_black: 'Arial Black',
                      comic_sans: 'Comic Sans MS',
                      courier_new: 'Courier New',
                      impact: 'Impact',
                      lucida_grande: 'Lucida Grande',
                      times_new_roman: 'Times New Roman',
                      verdana: 'Verdana'
                    }"
                    min-height="200px"
                    :rules="[val => !!val || 'Notes are required']"
                  />
                  <q-input
                    v-else
                    v-model="tableItemData.notes"
                    filled
                    type="textarea"
                    label="Notes"
                    :hint="`Enter ${documentationTypeLabels[currentTableType]?.toLowerCase() || 'notes'}`"
                    rows="10"
                    autofocus
                  />
                  <div class="text-caption text-secondary q-mt-xs">
                    <q-icon name="info" size="14px" class="q-mr-xs" />
                    Tip: Use <strong>red text color</strong> for night shift notes to differentiate from day shift
                  </div>
                  
                  <q-separator class="q-mt-md q-mb-md" />
                  
                  <!-- Existing Nurse Notes List -->
                  <div class="text-subtitle2 text-weight-bold glass-text q-mb-sm">
                    Previous Nurse Notes
                  </div>
                  <div style="max-height: 300px; overflow-y: auto;" class="q-mb-md">
                    <q-list bordered separator v-if="nurseNotes.length > 0">
                      <q-item
                        v-for="note in nurseNotes"
                        :key="note.id"
                        :class="{ 'strikethrough-note': note.strikethrough === 1 }"
                      >
                        <q-item-section>
                          <q-item-label>
                            <div class="row items-center">
                              <div 
                                class="col"
                                :style="note.strikethrough === 1 ? 'text-decoration: line-through; opacity: 0.6;' : ''"
                                v-html="note.notes"
                              ></div>
                              <div class="col-auto q-ml-md">
                                <q-btn
                                  v-if="canStrikethroughNote(note)"
                                  flat
                                  dense
                                  :icon="note.strikethrough === 1 ? 'undo' : 'strikethrough_s'"
                                  :color="note.strikethrough === 1 ? 'positive' : 'negative'"
                                  size="sm"
                                  @click="toggleStrikethrough(note)"
                                  :label="note.strikethrough === 1 ? 'Restore' : 'Strikethrough'"
                                />
                              </div>
                            </div>
                          </q-item-label>
                          <q-item-label caption>
                            <div class="row items-center q-gutter-sm">
                              <div>
                                <q-icon name="person" size="14px" class="q-mr-xs" />
                                {{ note.created_by_name || 'Unknown' }}
                              </div>
                              <div>
                                <q-icon name="schedule" size="14px" class="q-mr-xs" />
                                {{ formatDateTime(note.created_at) }}
                              </div>
                              <div v-if="note.strikethrough === 1 && note.strikethrough_by_name">
                                <q-icon name="block" size="14px" class="q-mr-xs" />
                                Strikethrough by: {{ note.strikethrough_by_name }}
                                <span v-if="note.strikethrough_at">
                                  at {{ formatDateTime(note.strikethrough_at) }}
                                </span>
                              </div>
                            </div>
                          </q-item-label>
                        </q-item-section>
                      </q-item>
                    </q-list>
                    <div v-else class="text-center text-secondary q-pa-md">
                      No previous nurse notes
                    </div>
                  </div>
                </div>
                <div v-else>
                  <q-input
                    v-model="tableItemData.notes"
                    filled
                    type="textarea"
                    label="Notes"
                    :hint="`Enter ${documentationTypeLabels[currentTableType]?.toLowerCase() || 'notes'}`"
                    rows="10"
                    autofocus
                  />
                </div>
              </q-card-section>

              <q-card-actions align="right" class="q-pa-md">
                <q-btn flat label="Cancel" color="primary" @click="showTableItemDialog = false" />
                <q-btn
                  flat
                  label="Save"
                  color="positive"
                  @click="saveTableItem"
                  :loading="savingTableItem"
                />
              </q-card-actions>
            </q-card>
          </q-dialog>

          <!-- Additional sections can be added here for inpatient activities -->
          <!-- Examples: Daily notes, medication schedule, test results, etc. -->
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

const loading = ref(false);
const patientInfo = ref(null);
const discharging = ref(false);
const cancelling = ref(false);
const showAdmissionNotesDialog = ref(false);
const admissionNotes = ref('');
const savingNotes = ref(false);
const currentDocumentationType = ref('');
const documentationTypeLabels = {
  'admission_notes': 'Admission Notes',
  'clinical_review': 'Clinical Review',
  'nurses_notes': 'Nurses Notes',
  'nurses_mid_documentation': 'Nurses Mid Documentation',
  'vitals': 'Vitals',
};

// Table data
const nurseNotes = ref([]);
const nurseMidDocumentations = ref([]);
const inpatientVitals = ref([]);
const clinicalReviews = ref([]);
const transfers = ref([]);
const loadingTableData = ref(false);

// Table item dialog
const showTableItemDialog = ref(false);
const currentTableType = ref('');
const tableItemData = ref({});
const savingTableItem = ref(false);
const nurseNoteEditor = ref(null);
const selectedTextColor = ref('#000000');
const selectedBgColor = ref('#FFFFFF');

const admissionNotesColumns = [
  {
    name: 'label',
    required: true,
    label: 'Activity',
    align: 'left',
    field: 'label',
    sortable: false,
  },
  {
    name: 'notes',
    required: true,
    label: 'Notes',
    align: 'left',
    field: 'notes',
    sortable: false,
  },
];

const admissionNotesRows = computed(() => {
  if (!patientInfo.value) return [];
  
  return [
    {
      label: 'Vitals',
      notes: null,
      type: 'vitals',
      isTable: true, // Multiple records in inpatient_vitals table
    },
    {
      label: 'Admitted',
      notes: patientInfo.value?.admission_notes || null,
      type: 'admission_notes',
      isTable: false, // Single field in ward_admissions
    },
    {
      label: 'Transfers',
      notes: null,
      type: 'transfers',
      isTable: true, // Multiple records in ward_transfers table
    },
    {
      label: 'Clinical Reviews',
      notes: null,
      type: 'clinical_review',
      isTable: true, // Multiple records in inpatient_clinical_reviews table
    },
  ];
});

const wardAdmissionId = computed(() => parseInt(route.params.id));
const encounterId = computed(() => route.query.encounter_id ? parseInt(route.query.encounter_id) : null);
const cardNumber = computed(() => route.query.card_number || null);

const loadPatientInfo = async () => {
  if (!wardAdmissionId.value) return;
  
  loading.value = true;
  try {
    // Load all ward admissions to find this patient
    const response = await consultationAPI.getWardAdmissions();
    console.log('Ward admissions API response:', response);
    console.log('Response data:', response.data);
    
    let data = [];
    if (Array.isArray(response.data)) {
      data = response.data;
    } else if (response.data && Array.isArray(response.data.data)) {
      data = response.data.data;
    }
    
    console.log('Parsed data:', data);
    console.log('Looking for ward admission ID:', wardAdmissionId.value);
    
    // Find the specific patient
    const patient = data.find(p => p.id === wardAdmissionId.value);
    if (patient) {
      // Debug: Log emergency contact data
      console.log('Patient info loaded:', {
        id: patient.id,
        card_number: patient.patient_card_number,
        emergency_contact_name: patient.emergency_contact_name,
        emergency_contact_relationship: patient.emergency_contact_relationship,
        emergency_contact_number: patient.emergency_contact_number,
        allKeys: Object.keys(patient),
        fullPatient: patient
      });
      patientInfo.value = patient;
    } else {
      console.error('Patient not found. Available IDs:', data.map(p => p.id));
      $q.notify({
        type: 'negative',
        message: 'Patient not found in ward admissions',
      });
    }
  } catch (error) {
    console.error('Error loading patient info:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to load patient information',
    });
  } finally {
    loading.value = false;
  }
};

const viewPatient = () => {
  if (cardNumber.value) {
    router.push(`/patients/${cardNumber.value}`);
  } else if (patientInfo.value?.patient_card_number) {
    router.push(`/patients/${patientInfo.value.patient_card_number}`);
  }
};

const viewEncounter = () => {
  if (encounterId.value) {
    router.push(`/consultation/${encounterId.value}`);
  } else if (patientInfo.value?.encounter_id) {
    router.push(`/consultation/${patientInfo.value.encounter_id}`);
  }
};

const addVitals = () => {
  openTableItemDialog('vitals', null);
};

const addNurseNote = () => {
  openTableItemDialog('nurses_notes', null);
};

const viewNurseMidDocumentation = () => {
  if (wardAdmissionId.value) {
    router.push(`/ipd/nurse-mid-documentation/${wardAdmissionId.value}`);
  }
};

const viewPrescriptions = () => {
  if (encounterId.value) {
    router.push(`/consultation/${encounterId.value}#prescriptions`);
  } else if (patientInfo.value?.encounter_id) {
    router.push(`/consultation/${patientInfo.value.encounter_id}#prescriptions`);
  }
};

const viewInvestigations = () => {
  if (encounterId.value) {
    router.push(`/consultation/${encounterId.value}#investigations`);
  } else if (patientInfo.value?.encounter_id) {
    router.push(`/consultation/${patientInfo.value.encounter_id}#investigations`);
  }
};


const viewBilling = () => {
  if (encounterId.value) {
    router.push(`/billing/${encounterId.value}`);
  } else if (patientInfo.value?.encounter_id) {
    router.push(`/billing/${patientInfo.value.encounter_id}`);
  }
};

const dischargePatient = async () => {
  if (!wardAdmissionId.value) return;
  
  $q.dialog({
    title: 'Discharge Patient',
    message: `Are you sure you want to discharge ${patientInfo.value?.patient_name} ${patientInfo.value?.patient_surname} from ${patientInfo.value?.ward}?`,
    cancel: true,
    persistent: true
  }).onOk(async () => {
    discharging.value = true;
    try {
      await consultationAPI.dischargePatient(wardAdmissionId.value);
      $q.notify({
        type: 'positive',
        message: 'Patient discharged successfully',
      });
      // Redirect back to ward page
      router.push('/ipd/doctor-nursing-station');
    } catch (error) {
      console.error('Error discharging patient:', error);
      $q.notify({
        type: 'negative',
        message: error.response?.data?.detail || 'Failed to discharge patient',
      });
    } finally {
      discharging.value = false;
    }
  });
};

const cancelAdmission = async () => {
  if (!wardAdmissionId.value) return;
  
  $q.dialog({
    title: 'Cancel Admission',
    message: `Are you sure you want to cancel this admission? This will remove all admission records and free up the bed. This action cannot be undone.`,
    cancel: true,
    persistent: true
  }).onOk(async () => {
    cancelling.value = true;
    try {
      await consultationAPI.cancelWardAdmission(wardAdmissionId.value);
      $q.notify({
        type: 'positive',
        message: 'Admission cancelled successfully. All records have been removed.',
      });
      // Redirect back to ward page
      router.push('/ipd/doctor-nursing-station');
    } catch (error) {
      console.error('Error cancelling admission:', error);
      $q.notify({
        type: 'negative',
        message: error.response?.data?.detail || 'Failed to cancel admission',
      });
    } finally {
      cancelling.value = false;
    }
  });
};

const formatDate = (dateString) => {
  if (!dateString) return 'N/A';
  const date = new Date(dateString);
  return date.toLocaleDateString('en-GB');
};

const formatDateTime = (dateString) => {
  if (!dateString) return 'N/A';
  const date = new Date(dateString);
  return date.toLocaleString('en-GB');
};

const openDocumentationDialog = (type, currentValue) => {
  currentDocumentationType.value = type;
  admissionNotes.value = currentValue || '';
  showAdmissionNotesDialog.value = true;
};

const saveDocumentation = async () => {
  if (!wardAdmissionId.value || !currentDocumentationType.value) return;
  
  savingNotes.value = true;
  try {
    await consultationAPI.updateAdmissionNotes(wardAdmissionId.value, admissionNotes.value);
    $q.notify({
      type: 'positive',
      message: `${documentationTypeLabels[currentDocumentationType.value]} saved successfully`,
    });
    showAdmissionNotesDialog.value = false;
    // Reload patient info to get updated documentation
    await loadPatientInfo();
  } catch (error) {
    console.error('Error saving documentation:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to save documentation',
    });
  } finally {
    savingNotes.value = false;
  }
};

const getTableItemCount = (type) => {
  switch (type) {
    case 'nurses_notes':
      return nurseNotes.value.length;
    case 'nurses_mid_documentation':
      return nurseMidDocumentations.value.length;
    case 'vitals':
      return inpatientVitals.value.length;
    case 'clinical_review':
      return clinicalReviews.value.length;
    case 'transfers':
      // Only count accepted transfers
      return transfers.value.filter(t => t.status === 'accepted').length;
    default:
      return 0;
  }
};

const loadTableData = async () => {
  if (!wardAdmissionId.value) return;
  
  loadingTableData.value = true;
  try {
    const [notesRes, midDocRes, vitalsRes, reviewsRes, transfersRes] = await Promise.all([
      consultationAPI.getNurseNotes(wardAdmissionId.value),
      consultationAPI.getNurseMidDocumentations(wardAdmissionId.value),
      consultationAPI.getInpatientVitals(wardAdmissionId.value),
      consultationAPI.getInpatientClinicalReviews(wardAdmissionId.value),
      consultationAPI.getWardAdmissionTransfers(wardAdmissionId.value),
    ]);
    
    nurseNotes.value = Array.isArray(notesRes.data) ? notesRes.data : [];
    nurseMidDocumentations.value = Array.isArray(midDocRes.data) ? midDocRes.data : [];
    inpatientVitals.value = Array.isArray(vitalsRes.data) ? vitalsRes.data : [];
    clinicalReviews.value = Array.isArray(reviewsRes.data) ? reviewsRes.data : [];
    transfers.value = Array.isArray(transfersRes.data) ? transfersRes.data : [];
  } catch (error) {
    console.error('Error loading table data:', error);
  } finally {
    loadingTableData.value = false;
  }
};

const openTableItemDialog = async (type, item) => {
  currentTableType.value = type;
  
  // If opening nurse notes dialog, ensure nurse notes are loaded
  if (type === 'nurses_notes' && nurseNotes.value.length === 0) {
    await loadTableData();
  }
  
  if (item) {
    tableItemData.value = { ...item };
  } else {
    // Initialize empty data based on type
    if (type === 'vitals') {
      tableItemData.value = {
        temperature: null,
        blood_pressure_systolic: null,
        blood_pressure_diastolic: null,
        pulse: null,
        respiratory_rate: null,
        oxygen_saturation: null,
        weight: null,
        height: null,
        notes: null,
      };
    } else if (type === 'nurses_notes') {
      // Initialize with current date and time
      const now = new Date();
      const dateStr = now.toISOString().split('T')[0];
      const timeStr = now.toTimeString().split(' ')[0].substring(0, 5);
      tableItemData.value = {
        note_date: dateStr,
        note_hour: timeStr,
        notes: '',
      };
      // Reset color pickers
      selectedTextColor.value = '#000000';
      selectedBgColor.value = '#FFFFFF';
    } else {
      tableItemData.value = { notes: item?.notes || item?.documentation || item?.review_notes || '' };
    }
  }
  showTableItemDialog.value = true;
};

const getContrastColor = (hexColor) => {
  // Convert hex to RGB
  const r = parseInt(hexColor.slice(1, 3), 16);
  const g = parseInt(hexColor.slice(3, 5), 16);
  const b = parseInt(hexColor.slice(5, 7), 16);
  // Calculate luminance
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  // Return black or white based on luminance
  return luminance > 0.5 ? '#000000' : '#FFFFFF';
};

const applyTextColor = () => {
  if (nurseNoteEditor.value && selectedTextColor.value) {
    try {
      nurseNoteEditor.value.runCmd('foreColor', selectedTextColor.value);
    } catch (error) {
      console.error('Error applying text color:', error);
    }
  }
};

const applyBgColor = () => {
  if (nurseNoteEditor.value && selectedBgColor.value) {
    try {
      nurseNoteEditor.value.runCmd('backColor', selectedBgColor.value);
    } catch (error) {
      console.error('Error applying background color:', error);
    }
  }
};

const saveTableItem = async () => {
  if (!wardAdmissionId.value || !currentTableType.value) return;
  
  // Validate required fields for nurse notes
  if (currentTableType.value === 'nurses_notes') {
    if (!tableItemData.value.note_date || !tableItemData.value.note_hour || !tableItemData.value.notes) {
      $q.notify({
        type: 'warning',
        message: 'Please fill in all required fields (Date, Hour, and Notes)',
      });
      return;
    }
    // Format notes with date and hour (HTML is preserved from editor)
    const dateTimeHeader = `<p><strong>Date:</strong> ${tableItemData.value.note_date} | <strong>Hour:</strong> ${tableItemData.value.note_hour}</p>`;
    tableItemData.value.notes = dateTimeHeader + tableItemData.value.notes;
  }
  
  savingTableItem.value = true;
  try {
    let response;
    switch (currentTableType.value) {
      case 'nurses_notes':
        response = await consultationAPI.createNurseNote(wardAdmissionId.value, tableItemData.value.notes);
        break;
      case 'nurses_mid_documentation':
        response = await consultationAPI.createNurseMidDocumentation(wardAdmissionId.value, tableItemData.value.notes);
        break;
      case 'vitals':
        response = await consultationAPI.createInpatientVital(wardAdmissionId.value, tableItemData.value);
        break;
      case 'clinical_review':
        response = await consultationAPI.createInpatientClinicalReview(wardAdmissionId.value, { review_notes: tableItemData.value.notes });
        break;
    }
    
    $q.notify({
      type: 'positive',
      message: `${documentationTypeLabels[currentTableType.value]} saved successfully`,
    });
    showTableItemDialog.value = false;
    await loadTableData();
  } catch (error) {
    console.error('Error saving table item:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to save',
    });
  } finally {
    savingTableItem.value = false;
  }
};

const viewTableItems = (type) => {
  // For transfers, show only accepted ones
  if (type === 'transfers') {
    const acceptedTransfers = transfers.value.filter(t => t.status === 'accepted');
    if (acceptedTransfers.length === 0) {
      $q.notify({
        type: 'info',
        message: 'No accepted transfers found',
      });
      return;
    }
    // Show transfers in a dialog
    $q.dialog({
      title: 'Accepted Transfers',
      message: acceptedTransfers.map(t => 
        `From: ${t.from_ward} → To: ${t.to_ward}\n` +
        `Date: ${formatDateTime(t.transferred_at)}\n` +
        `By: ${t.transferred_by_name || 'Unknown'}\n` +
        (t.transfer_reason ? `Reason: ${t.transfer_reason}\n` : '')
      ).join('\n---\n'),
      persistent: true
    });
  } else {
    $q.notify({
      type: 'info',
      message: `View all ${documentationTypeLabels[type]} functionality will be implemented soon`,
    });
  }
};

const canStrikethroughNote = (note) => {
  const currentUserId = authStore.user?.id;
  const isAdmin = authStore.userRole === 'Admin';
  const isOwner = note.created_by === currentUserId;
  return isAdmin || isOwner;
};

const toggleStrikethrough = async (note) => {
  if (!wardAdmissionId.value) return;
  
  try {
    await consultationAPI.toggleNurseNoteStrikethrough(wardAdmissionId.value, note.id);
    // Reload nurse notes
    await loadTableData();
    $q.notify({
      type: 'positive',
      message: note.strikethrough === 1 ? 'Note restored successfully' : 'Note strikethrough successfully',
    });
  } catch (error) {
    console.error('Error toggling strikethrough:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to update note',
    });
  }
};

onMounted(() => {
  loadPatientInfo();
  loadTableData();
});

// Computed for isAdmin
const isAdmin = computed(() => authStore.userRole === 'Admin');
</script>

<style scoped>
.body--light .glass-text {
  color: rgba(0, 0, 0, 0.87) !important;
}

.body--dark .glass-text {
  color: rgba(255, 255, 255, 0.9) !important;
}

.strikethrough-note {
  opacity: 0.6;
}
</style>

