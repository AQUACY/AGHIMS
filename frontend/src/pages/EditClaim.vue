<template>
  <q-page class="q-pa-md">
    <div class="row items-center q-mb-md">
      <div class="text-h4">{{ isViewMode ? 'View NHIS Claim Form' : 'Edit NHIS Claim Form' }}</div>
      <q-space />
      <q-btn
        color="secondary"
        label="Back to Claims"
        icon="arrow_back"
        @click="$router.push('/claims')"
        outline
      />
    </div>
    <q-banner
      v-if="isViewMode"
      class="bg-info text-white q-mb-md"
      rounded
    >
      <template v-slot:avatar>
        <q-icon name="info" />
      </template>
      <strong>View Mode</strong>
      <div class="text-caption q-mt-xs">
        You can edit this finalized claim and save changes or save and finalize again.
      </div>
    </q-banner>

    <q-card v-if="loading" class="q-pa-md">
      <q-inner-loading showing color="primary" />
    </q-card>

    <q-form v-else @submit="saveClaim" class="q-gutter-md">
      <!-- Provider Information -->
      <q-card>
        <q-card-section>
          <div class="text-h6 q-mb-md">Provider Information</div>
          <div class="row q-gutter-md">
            <q-input
              v-model="providerInfo.provider_name"
              filled
              label="Provider's Name"
              class="col-12"
              readonly
            />
            <q-input
              v-model="providerInfo.scheme_code"
              filled
              label="Scheme Code"
              class="col-12 col-md-6"
            />
            <q-input
              v-model="providerInfo.month_of_claim"
              filled
              type="date"
              label="Month of Claim"
              class="col-12 col-md-6"
            />
          </div>
        </q-card-section>
      </q-card>

      <!-- Client Information -->
      <q-card>
        <q-card-section>
          <div class="text-h6 q-mb-md">Client Information</div>
          <div class="row q-gutter-md">
            <q-input
              v-model="patientInfo.surname"
              filled
              label="Surname"
              class="col-12 col-md-4"
            />
            <q-input
              v-model="patientInfo.other_names"
              filled
              label="Other Names"
              class="col-12 col-md-4"
            />
            <q-input
              v-model="patientInfo.date_of_birth"
              filled
              type="date"
              label="Date of Birth"
              class="col-12 col-md-4"
            />
            <q-input
              v-model="patientInfo.age"
              filled
              type="number"
              label="Age"
              class="col-12 col-md-3"
            />
            <div class="col-12 col-md-4">
              <div class="text-subtitle2 q-mb-xs">Gender</div>
              <q-option-group
                v-model="patientInfo.gender"
                :options="genderOptions"
                type="radio"
              />
            </div>
            <q-input
              v-model="patientInfo.member_number"
              filled
              label="Member Number"
              class="col-12 col-md-5"
            />
            <q-input
              v-model="patientInfo.hospital_record_no"
              filled
              label="Hospital Record No."
              class="col-12 col-md-4"
            />
            <q-input
              v-model="patientInfo.card_serial_no"
              filled
              label="Card Serial No."
              class="col-12 col-md-3"
            />
          </div>
        </q-card-section>
      </q-card>

      <!-- Services Provided -->
      <q-card>
        <q-card-section>
          <div class="text-h6 q-mb-md">Services Provided</div>
          
          <div class="row q-gutter-md q-mb-md">
            <div class="col-12">
              <div class="text-subtitle2 q-mb-xs">Type of Services (select only one)</div>
              <q-option-group
                v-model="services.type_of_service"
                :options="typeOfServiceOptions"
                type="radio"
              />
            </div>
          </div>

          <div class="row q-gutter-md q-mb-md">
            <q-input
              v-model="services.first_visit"
              filled
              type="date"
              label="1st Visit/Admission"
              class="col-12 col-md-3"
            />
            <q-input
              v-model="services.second_visit"
              filled
              type="date"
              label="2nd Visit/Discharge"
              class="col-12 col-md-3"
            />
            <q-input
              v-model="services.third_visit"
              filled
              type="date"
              label="3rd Visit"
              class="col-12 col-md-3"
            />
            <q-input
              v-model="services.fourth_visit"
              filled
              type="date"
              label="4th Visit"
              class="col-12 col-md-3"
            />
            <q-input
              v-model="services.duration_of_spell"
              filled
              type="number"
              label="Duration of Spell (days)"
              class="col-12 col-md-4"
            />
          </div>

          <div class="row q-gutter-md q-mb-md">
            <div class="col-12 col-md-6">
              <div class="text-subtitle2 q-mb-xs">All Inclusive / Unbundled</div>
              <q-option-group
                v-model="services.all_inclusive"
                :options="[{label: 'All Inclusive', value: true}, {label: 'Unbundled', value: false}]"
                type="radio"
              />
            </div>
            <div class="col-12 col-md-6">
              <div class="text-subtitle2 q-mb-xs">Outcome</div>
              <q-select
                v-model="services.outcome"
                :options="outcomeOptions"
                filled
                label="Outcome"
              />
            </div>
            <div class="col-12 col-md-6">
              <div class="text-subtitle2 q-mb-xs">Type of Attendance</div>
              <q-option-group
                v-model="services.type_of_attendance"
                :options="attendanceOptions"
                type="radio"
              />
            </div>
            <q-input
              v-model="services.specialty_code"
              filled
              label="Specialty Code"
              class="col-12 col-md-6"
            />
          </div>
          
          <div class="row q-gutter-md">
            <q-input
              v-model="services.principal_gdrg"
              filled
              label="Principal G-DRG Code"
              class="col-12 col-md-6"
              :disable="claimStatus === 'finalized'"
              hint="Main diagnosis code for this claim"
            />
          </div>
        </q-card-section>
      </q-card>

      <!-- Procedures (Surgeries) -->
      <q-card>
        <q-card-section>
          <div class="text-h6 q-mb-md">Surgery(ies)</div>
          <div class="row q-gutter-md">
            <div class="col-12">
              <q-input
                v-model="procedures.physician_name"
                filled
                label="Physician/Clinician Name"
              />
            </div>
            <q-input
              v-model="procedures.physician_id"
              filled
              label="Physician/Clinician ID"
              class="col-12 col-md-6"
            />
          </div>
          
          <q-table
            :rows="proceduresList"
            :columns="procedureColumns"
            row-key="index"
            flat
            dense
            class="q-mt-md"
          >
            <template v-slot:body-cell-description="props">
              <q-td :props="props">
                <q-input
                  v-model="proceduresList[props.row.index].description"
                  dense
                  filled
                  :disable="claimStatus === 'finalized' && !isViewMode"
                />
              </q-td>
            </template>
            <template v-slot:body-cell-date="props">
              <q-td :props="props">
                <q-input
                  v-model="proceduresList[props.row.index].date"
                  dense
                  filled
                  type="date"
                  :disable="claimStatus === 'finalized' && !isViewMode"
                />
              </q-td>
            </template>
            <template v-slot:body-cell-gdrg="props">
              <q-td :props="props">
                <q-input
                  v-model="proceduresList[props.row.index].gdrg"
                  dense
                  filled
                  :disable="claimStatus === 'finalized' && !isViewMode"
                />
              </q-td>
            </template>
            <template v-slot:body-cell-actions="props">
              <q-td :props="props">
                <q-btn
                  v-if="proceduresList[props.row.index].description && proceduresList[props.row.index].description.trim() !== '' && (claimStatus !== 'finalized' || isViewMode)"
                  size="sm"
                  color="negative"
                  icon="delete"
                  flat
                  round
                  dense
                  @click="deleteProcedure(props.row.index)"
                >
                  <q-tooltip>Delete Surgery</q-tooltip>
                </q-btn>
              </q-td>
            </template>
          </q-table>
        </q-card-section>
      </q-card>

      <!-- Diagnoses -->
      <q-card>
        <q-card-section>
          <div class="text-h6 q-mb-md">Diagnosis(es)</div>
          <q-table
            :rows="diagnosesList"
            :columns="diagnosisColumns"
            row-key="index"
            flat
            dense
          >
            <template v-slot:body-cell-description="props">
              <q-td :props="props">
                <q-input
                  v-model="diagnosesList[props.row.index].description"
                  dense
                  filled
                  :disable="claimStatus === 'finalized' && !isViewMode"
                />
              </q-td>
            </template>
            <template v-slot:body-cell-icd10="props">
              <q-td :props="props">
                <q-input
                  v-model="diagnosesList[props.row.index].icd10"
                  dense
                  filled
                  :disable="claimStatus === 'finalized' && !isViewMode"
                />
              </q-td>
            </template>
            <template v-slot:body-cell-gdrg="props">
              <q-td :props="props">
                <q-input
                  v-model="diagnosesList[props.row.index].gdrg"
                  dense
                  filled
                  :disable="claimStatus === 'finalized' && !isViewMode"
                />
              </q-td>
            </template>
            <template v-slot:body-cell-is_chief="props">
              <q-td :props="props">
                <q-checkbox
                  v-model="diagnosesList[props.row.index].is_chief"
                  :disable="claimStatus === 'finalized' && !isViewMode"
                />
              </q-td>
            </template>
            <template v-slot:body-cell-actions="props">
              <q-td :props="props">
                <q-btn
                  v-if="diagnosesList[props.row.index].description && diagnosesList[props.row.index].description.trim() !== '' && (claimStatus !== 'finalized' || isViewMode)"
                  size="sm"
                  color="negative"
                  icon="delete"
                  flat
                  round
                  dense
                  @click="deleteDiagnosis(props.row.index)"
                >
                  <q-tooltip>Delete Diagnosis</q-tooltip>
                </q-btn>
              </q-td>
            </template>
          </q-table>
        </q-card-section>
      </q-card>

      <!-- Investigations -->
      <q-card>
        <q-card-section>
          <div class="row items-center q-mb-md">
            <div class="text-h6">Investigations</div>
            <q-space />
            <q-btn
              v-if="claimStatus !== 'finalized' || isViewMode"
              size="sm"
              color="primary"
              icon="add"
              label="Add Investigation"
              @click="addInvestigation"
            />
          </div>
          <q-table
            :rows="investigationsList"
            :columns="investigationColumns"
            row-key="index"
            flat
            dense
          >
            <template v-slot:body-cell-description="props">
              <q-td :props="props">
                <q-input
                  v-model="investigationsList[props.row.index].description"
                  dense
                  filled
                  :disable="claimStatus === 'finalized' && !isViewMode"
                />
              </q-td>
            </template>
            <template v-slot:body-cell-date="props">
              <q-td :props="props">
                <q-input
                  v-model="investigationsList[props.row.index].date"
                  dense
                  filled
                  type="date"
                  :disable="claimStatus === 'finalized' && !isViewMode"
                />
              </q-td>
            </template>
            <template v-slot:body-cell-gdrg="props">
              <q-td :props="props">
                <q-input
                  v-model="investigationsList[props.row.index].gdrg"
                  dense
                  filled
                  :disable="claimStatus === 'finalized' && !isViewMode"
                />
              </q-td>
            </template>
            <template v-slot:body-cell-actions="props">
              <q-td :props="props">
                <q-btn
                  v-if="investigationsList[props.row.index].description && investigationsList[props.row.index].description.trim() !== '' && (claimStatus !== 'finalized' || isViewMode)"
                  size="sm"
                  color="negative"
                  icon="delete"
                  flat
                  round
                  dense
                  @click="deleteInvestigation(props.row.index)"
                >
                  <q-tooltip>Delete Investigation</q-tooltip>
                </q-btn>
              </q-td>
            </template>
          </q-table>
        </q-card-section>
      </q-card>

      <!-- Medicines -->
      <q-card>
        <q-card-section>
          <div class="row items-center q-mb-md">
            <div class="text-h6">Medicines</div>
            <q-space />
            <q-btn
              v-if="claimStatus !== 'finalized' || isViewMode"
              size="sm"
              color="primary"
              icon="add"
              label="Add Medicine"
              @click="addPrescription"
            />
          </div>
          <q-table
            :rows="prescriptionsList"
            :columns="prescriptionColumns"
            row-key="index"
            flat
            dense
          >
            <template v-slot:body-cell-description="props">
              <q-td :props="props">
                <q-input
                  v-model="prescriptionsList[props.row.index].description"
                  dense
                  filled
                  :disable="claimStatus === 'finalized' && !isViewMode"
                />
              </q-td>
            </template>
            <template v-slot:body-cell-price="props">
              <q-td :props="props">
                <q-input
                  v-model.number="prescriptionsList[props.row.index].price"
                  dense
                  filled
                  type="number"
                  step="0.01"
                  :disable="claimStatus === 'finalized' && !isViewMode"
                  @update:model-value="updatePrescriptionTotal(props.row.index)"
                />
              </q-td>
            </template>
            <template v-slot:body-cell-quantity="props">
              <q-td :props="props">
                <q-input
                  v-model.number="prescriptionsList[props.row.index].quantity"
                  dense
                  filled
                  type="number"
                  :disable="claimStatus === 'finalized' && !isViewMode"
                  @update:model-value="updatePrescriptionTotal(props.row.index)"
                />
              </q-td>
            </template>
            <template v-slot:body-cell-total_cost="props">
              <q-td :props="props">
                <q-input
                  v-model.number="prescriptionsList[props.row.index].total_cost"
                  dense
                  filled
                  type="number"
                  step="0.01"
                  readonly
                />
              </q-td>
            </template>
            <template v-slot:body-cell-date="props">
              <q-td :props="props">
                <q-input
                  v-model="prescriptionsList[props.row.index].date"
                  dense
                  filled
                  type="date"
                  :disable="claimStatus === 'finalized' && !isViewMode"
                />
              </q-td>
            </template>
            <template v-slot:body-cell-code="props">
              <q-td :props="props">
                <q-input
                  v-model="prescriptionsList[props.row.index].code"
                  dense
                  filled
                  :disable="claimStatus === 'finalized' && !isViewMode"
                />
              </q-td>
            </template>
            <template v-slot:body-cell-actions="props">
              <q-td :props="props">
                <div class="row q-gutter-xs">
                  <q-btn
                    v-if="prescriptionsList[props.row.index].description && prescriptionsList[props.row.index].description.trim() !== ''"
                    size="sm"
                    color="primary"
                    icon="edit"
                    flat
                    round
                    dense
                    @click="openPrescriptionDialog(props.row.index)"
                    :disable="claimStatus === 'finalized' && !isViewMode"
                  >
                    <q-tooltip>Edit Dose, Frequency & Duration</q-tooltip>
                  </q-btn>
                  <q-btn
                    v-if="prescriptionsList[props.row.index].description && prescriptionsList[props.row.index].description.trim() !== '' && (claimStatus !== 'finalized' || isViewMode)"
                    size="sm"
                    color="negative"
                    icon="delete"
                    flat
                    round
                    dense
                    @click="deletePrescription(props.row.index)"
                  >
                    <q-tooltip>Delete Medicine</q-tooltip>
                  </q-btn>
                </div>
              </q-td>
            </template>
          </q-table>
        </q-card-section>
      </q-card>

      <!-- Client Claim Summary -->
      <q-card>
        <q-card-section>
          <div class="text-h6 q-mb-md">Client Claim Summary</div>
          <q-table
            :rows="claimSummary"
            :columns="summaryColumns"
            row-key="type"
            flat
            dense
          >
            <template v-slot:body-cell-gdrg_code="props">
              <q-td :props="props">
                <q-input
                  v-model="claimSummary[props.row.index].gdrg_code"
                  dense
                  filled
                  :disable="claimStatus === 'finalized' || props.row.type === 'TOTAL'"
                />
              </q-td>
            </template>
            <template v-slot:body-cell-tariff_amount="props">
              <q-td :props="props">
                <q-input
                  v-model.number="claimSummary[props.row.index].tariff_amount"
                  dense
                  filled
                  type="number"
                  step="0.01"
                  :disable="claimStatus === 'finalized' || props.row.type === 'TOTAL'"
                  readonly
                />
              </q-td>
            </template>
          </q-table>
          <div class="text-h6 q-mt-md text-right">
            Total: ₵{{ totalClaimAmount.toFixed(2) }}
          </div>
        </q-card-section>
      </q-card>

      <!-- Action Buttons -->
      <div class="row q-gutter-md q-mt-md">
        <!-- Edit Mode Buttons -->
        <template v-if="!isViewMode">
          <q-btn
            type="submit"
            color="secondary"
            label="Save Draft"
            :loading="saving"
            :disable="claimStatus === 'finalized'"
            class="col-12 col-md-3"
          />
          <q-btn
            color="primary"
            label="Save & Finalize"
            :loading="saving"
            @click="saveAndFinalize"
            :disable="claimStatus === 'finalized'"
            class="col-12 col-md-3"
          />
        </template>
        <!-- View Mode Buttons -->
        <template v-else>
          <q-btn
            color="primary"
            label="Save & Finalize"
            :loading="saving"
            @click="saveAndFinalize"
            class="col-12 col-md-3"
          />
          <q-btn
            type="submit"
            color="secondary"
            label="Save Changes"
            :loading="saving"
            class="col-12 col-md-3"
          />
        </template>
      </div>
    </q-form>

    <!-- Prescription Details Dialog -->
    <q-dialog v-model="showPrescriptionDialog">
      <q-card style="min-width: 400px">
        <q-card-section>
          <div class="text-h6">Edit Prescription Details</div>
          <div class="text-subtitle2 text-grey-7 q-mt-xs">
            {{ currentPrescription?.description || 'Medicine' }}
          </div>
        </q-card-section>

        <q-card-section>
          <q-form @submit="savePrescriptionDetails" class="q-gutter-md">
            <q-input
              v-model="prescriptionForm.dose"
              filled
              label="Dose"
              placeholder="e.g., 500 MG"
              :disable="claimStatus === 'finalized'"
            />
            <q-input
              v-model="prescriptionForm.frequency"
              filled
              label="Frequency"
              placeholder="e.g., 2 DAILY"
              :disable="claimStatus === 'finalized'"
            />
            <q-input
              v-model="prescriptionForm.duration"
              filled
              label="Duration"
              placeholder="e.g., 7 DAYS"
              :disable="claimStatus === 'finalized'"
            />
            
            <q-card-actions align="right">
              <q-btn
                flat
                label="Cancel"
                color="secondary"
                v-close-popup
              />
              <q-btn
                type="submit"
                label="Save"
                color="primary"
                :disable="claimStatus === 'finalized'"
              />
            </q-card-actions>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useQuasar } from 'quasar';
import { claimsAPI, priceListAPI } from '../services/api';

const $route = useRoute();
const $router = useRouter();
const $q = useQuasar();

const loading = ref(true);
const saving = ref(false);
const claimId = ref(null);
const claimStatus = ref('draft');
const isViewMode = ref(false);
const route = useRoute();

// Prescription Dialog
const showPrescriptionDialog = ref(false);
const currentPrescriptionIndex = ref(null);
const currentPrescription = computed(() => {
  if (currentPrescriptionIndex.value !== null) {
    return prescriptionsList.value[currentPrescriptionIndex.value];
  }
  return null;
});

const prescriptionForm = reactive({
  dose: '',
  frequency: '',
  duration: '',
});

// Provider Information
const providerInfo = reactive({
  provider_name: 'ASESEWA GOVERNMENT HOSPITAL, ASESEWA',
  scheme_code: '',
  month_of_claim: new Date().toISOString().split('T')[0],
});

// Patient Information
const patientInfo = reactive({
  surname: '',
  other_names: '',
  date_of_birth: '',
  age: null,
  gender: 'M',
  member_number: '',
  hospital_record_no: '',
  card_serial_no: '',
});

const genderOptions = [
  { label: 'Male', value: 'M' },
  { label: 'Female', value: 'F' },
];

// Services Provided
const services = reactive({
  type_of_service: 'OPD',
  first_visit: '',
  second_visit: '',
  third_visit: '',
  fourth_visit: '',
  duration_of_spell: null,
  all_inclusive: true,
  outcome: 'DISC',
  type_of_attendance: 'EAE',
  specialty_code: '',
  principal_gdrg: '',
});

const typeOfServiceOptions = [
  { label: 'Outpatients', value: 'OPD' },
  { label: 'In-patient', value: 'IPD' },
  { label: 'Pharmacy', value: 'Pharmacy' },
  { label: 'Diagnostic', value: 'Diagnostic' },
];

const outcomeOptions = ['Discharged', 'Died', 'Transferred Out', 'Absconded/Discharged against Medical advice'];
const attendanceOptions = [
  { label: 'Chronic Follow-up', value: 'CFU' },
  { label: 'Emergency/Acute Episode', value: 'EAE' },
  { label: 'Referral', value: 'Referral' },
  { label: 'Antenatal', value: 'Antenatal' },
  { label: 'Postnatal', value: 'Postnatal' },
];

// Procedures
const procedures = reactive({
  physician_name: '',
  physician_id: '',
});

const proceduresList = ref([
  { index: 0, description: '', date: '', gdrg: '' },
  { index: 1, description: '', date: '', gdrg: '' },
  { index: 2, description: '', date: '', gdrg: '' },
]);

const procedureColumns = [
  { name: 'number', label: '#', field: 'index', align: 'center' },
  { name: 'description', label: 'Description', field: 'description', align: 'left' },
  { name: 'date', label: 'Date', field: 'date', align: 'center' },
  { name: 'gdrg', label: 'G-DRG', field: 'gdrg', align: 'left' },
  { name: 'actions', label: 'Actions', align: 'center' },
];

// Diagnoses
const diagnosesList = ref([
  { index: 0, id: null, description: '', icd10: '', gdrg: '', is_chief: false },
  { index: 1, id: null, description: '', icd10: '', gdrg: '', is_chief: false },
  { index: 2, id: null, description: '', icd10: '', gdrg: '', is_chief: false },
  { index: 3, id: null, description: '', icd10: '', gdrg: '', is_chief: false },
]);

const diagnosisColumns = [
  { name: 'number', label: '#', field: 'index', align: 'center' },
  { name: 'description', label: 'Description', field: 'description', align: 'left' },
  { name: 'icd10', label: 'ICD-10', field: 'icd10', align: 'center' },
  { name: 'gdrg', label: 'G-DRG', field: 'gdrg', align: 'left' },
  { name: 'is_chief', label: 'Chief', field: 'is_chief', align: 'center' },
  { name: 'actions', label: 'Actions', align: 'center' },
];

// Investigations
const investigationsList = ref([
  { index: 0, id: null, description: '', date: '', gdrg: '' },
  { index: 1, id: null, description: '', date: '', gdrg: '' },
  { index: 2, id: null, description: '', date: '', gdrg: '' },
  { index: 3, id: null, description: '', date: '', gdrg: '' },
  { index: 4, id: null, description: '', date: '', gdrg: '' },
]);

const investigationColumns = [
  { name: 'number', label: '#', field: 'index', align: 'center' },
  { name: 'description', label: 'Description', field: 'description', align: 'left' },
  { name: 'date', label: 'DATE', field: 'date', align: 'center' },
  { name: 'gdrg', label: 'G-DRG', field: 'gdrg', align: 'left' },
  { name: 'actions', label: 'Actions', align: 'center' },
];

// Prescriptions
const prescriptionsList = ref([
  { index: 0, id: null, description: '', code: '', price: 0, quantity: 0, total_cost: 0, date: '', dose: '', frequency: '', duration: '', unparsed: '' },
  { index: 1, id: null, description: '', code: '', price: 0, quantity: 0, total_cost: 0, date: '', dose: '', frequency: '', duration: '', unparsed: '' },
  { index: 2, id: null, description: '', code: '', price: 0, quantity: 0, total_cost: 0, date: '', dose: '', frequency: '', duration: '', unparsed: '' },
  { index: 3, id: null, description: '', code: '', price: 0, quantity: 0, total_cost: 0, date: '', dose: '', frequency: '', duration: '', unparsed: '' },
  { index: 4, id: null, description: '', code: '', price: 0, quantity: 0, total_cost: 0, date: '', dose: '', frequency: '', duration: '', unparsed: '' },
]);

const prescriptionColumns = [
  { name: 'number', label: '#', field: 'index', align: 'center' },
  { name: 'description', label: 'Description', field: 'description', align: 'left' },
  { name: 'price', label: 'Price', field: 'price', align: 'right', format: (val) => `₵${val?.toFixed(2) || '0.00'}` },
  { name: 'quantity', label: 'Qty', field: 'quantity', align: 'center' },
  { name: 'total_cost', label: 'Total Cost', field: 'total_cost', align: 'right', format: (val) => `₵${val?.toFixed(2) || '0.00'}` },
  { name: 'date', label: 'Date', field: 'date', align: 'center' },
  { name: 'code', label: 'Code', field: 'code', align: 'left' },
  { name: 'actions', label: 'Actions', align: 'center' },
];

// Claim Summary
const claimSummary = ref([
  { index: 0, type: 'A In-Patient', gdrg_code: '', tariff_amount: 0 },
  { index: 1, type: 'B Out-Patient', gdrg_code: '', tariff_amount: 0 },
  { index: 2, type: 'C Investigations', gdrg_code: '', tariff_amount: 0 },
  { index: 3, type: 'D Pharmacy', gdrg_code: '', tariff_amount: 0 },
  { index: 4, type: 'TOTAL', gdrg_code: '', tariff_amount: 0 },
]);

const summaryColumns = [
  { name: 'type', label: 'Type of Service', field: 'type', align: 'left' },
  { name: 'gdrg_code', label: 'G-DRG/Code', field: 'gdrg_code', align: 'left' },
  { name: 'tariff_amount', label: 'Tariff Amount', field: 'tariff_amount', align: 'right', format: (val) => `₵${val?.toFixed(2) || '0.00'}` },
];

const totalClaimAmount = computed(() => {
  return claimSummary.value
    .filter(item => item.type !== 'TOTAL')
    .reduce((sum, item) => sum + (item.tariff_amount || 0), 0);
});

const updatePrescriptionTotal = (index) => {
  const presc = prescriptionsList.value[index];
  presc.total_cost = (presc.price || 0) * (presc.quantity || 0);
  calculateClaimSummary();
};

const openPrescriptionDialog = (index) => {
  currentPrescriptionIndex.value = index;
  const presc = prescriptionsList.value[index];
  
  // Populate form with existing values
  prescriptionForm.dose = presc.dose || '';
  prescriptionForm.frequency = presc.frequency || '';
  prescriptionForm.duration = presc.duration || '';
  
  showPrescriptionDialog.value = true;
};

const savePrescriptionDetails = () => {
  if (currentPrescriptionIndex.value === null) return;
  
  const presc = prescriptionsList.value[currentPrescriptionIndex.value];
  
  // Update prescription fields
  presc.dose = prescriptionForm.dose || '';
  presc.frequency = prescriptionForm.frequency || '';
  presc.duration = prescriptionForm.duration || '';
  
  // Combine as unparsed
  const parts = [];
  if (presc.dose) parts.push(presc.dose);
  if (presc.frequency) parts.push(presc.frequency);
  if (presc.duration) parts.push(presc.duration);
  presc.unparsed = parts.join(' ');
  
  showPrescriptionDialog.value = false;
  currentPrescriptionIndex.value = null;
  
  $q.notify({
    type: 'positive',
    message: 'Prescription details saved',
  });
};

const addInvestigation = () => {
  // Find first empty slot
  const emptyIndex = investigationsList.value.findIndex(inv => !inv.description || inv.description.trim() === '');
  if (emptyIndex !== -1) {
    // Focus on the empty slot (it already exists)
    $q.notify({
      type: 'info',
      message: 'Please fill in the empty investigation row',
      timeout: 2000,
    });
  } else if (investigationsList.value.length < 10) {
    // Add new row if we haven't reached the limit
    investigationsList.value.push({
      index: investigationsList.value.length,
      id: null,
      description: '',
      date: '',
      gdrg: ''
    });
    $q.notify({
      type: 'positive',
      message: 'New investigation row added',
      timeout: 2000,
    });
  } else {
    $q.notify({
      type: 'warning',
      message: 'Maximum of 10 investigations allowed',
      timeout: 2000,
    });
  }
};

const deleteInvestigation = (index) => {
  $q.dialog({
    title: 'Delete Investigation',
    message: 'Are you sure you want to delete this investigation?',
    cancel: true,
    persistent: true
  }).onOk(() => {
    investigationsList.value[index].description = '';
    investigationsList.value[index].date = '';
    investigationsList.value[index].gdrg = '';
    investigationsList.value[index].id = null;
    $q.notify({
      type: 'positive',
      message: 'Investigation deleted',
    });
  });
};

const addPrescription = () => {
  // Find first empty slot
  const emptyIndex = prescriptionsList.value.findIndex(presc => !presc.description || presc.description.trim() === '');
  if (emptyIndex !== -1) {
    // Focus on the empty slot (it already exists)
    $q.notify({
      type: 'info',
      message: 'Please fill in the empty medicine row',
      timeout: 2000,
    });
  } else if (prescriptionsList.value.length < 10) {
    // Add new row if we haven't reached the limit
    prescriptionsList.value.push({
      index: prescriptionsList.value.length,
      id: null,
      description: '',
      code: '',
      price: 0,
      quantity: 0,
      total_cost: 0,
      date: '',
      dose: '',
      frequency: '',
      duration: '',
      unparsed: ''
    });
    $q.notify({
      type: 'positive',
      message: 'New medicine row added',
      timeout: 2000,
    });
  } else {
    $q.notify({
      type: 'warning',
      message: 'Maximum of 10 medicines allowed',
      timeout: 2000,
    });
  }
};

const deleteProcedure = (index) => {
  $q.dialog({
    title: 'Delete Surgery',
    message: 'Are you sure you want to delete this surgery?',
    cancel: true,
    persistent: true
  }).onOk(() => {
    proceduresList.value[index].description = '';
    proceduresList.value[index].date = '';
    proceduresList.value[index].gdrg = '';
    $q.notify({
      type: 'positive',
      message: 'Surgery deleted',
    });
  });
};

const deleteDiagnosis = (index) => {
  $q.dialog({
    title: 'Delete Diagnosis',
    message: 'Are you sure you want to delete this diagnosis?',
    cancel: true,
    persistent: true
  }).onOk(() => {
    diagnosesList.value[index].description = '';
    diagnosesList.value[index].icd10 = '';
    diagnosesList.value[index].gdrg = '';
    diagnosesList.value[index].is_chief = false;
    diagnosesList.value[index].id = null;
    $q.notify({
      type: 'positive',
      message: 'Diagnosis deleted',
    });
  });
};

const deletePrescription = (index) => {
  $q.dialog({
    title: 'Delete Medicine',
    message: 'Are you sure you want to delete this medicine?',
    cancel: true,
    persistent: true
  }).onOk(() => {
    prescriptionsList.value[index].description = '';
    prescriptionsList.value[index].code = '';
    prescriptionsList.value[index].price = 0;
    prescriptionsList.value[index].quantity = 0;
    prescriptionsList.value[index].total_cost = 0;
    prescriptionsList.value[index].date = '';
    prescriptionsList.value[index].dose = '';
    prescriptionsList.value[index].frequency = '';
    prescriptionsList.value[index].duration = '';
    prescriptionsList.value[index].unparsed = '';
    prescriptionsList.value[index].id = null;
    calculateClaimSummary();
    $q.notify({
      type: 'positive',
      message: 'Medicine deleted',
    });
  });
};

const saveAndFinalize = async (e) => {
  if (e) {
    e.preventDefault();
  }
  saving.value = true;
  try {
    // First save the claim
    await saveClaim(e);
    // Wait a bit to ensure save completed
    await new Promise(resolve => setTimeout(resolve, 500));
    // Then finalize
    await claimsAPI.finalize(claimId.value);
    $q.notify({
      type: 'positive',
      message: 'Claim saved and finalized successfully',
    });
    // Navigate back to claims page
    $router.push('/claims');
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to save and finalize claim',
    });
  } finally {
    saving.value = false;
  }
};

const calculateClaimSummary = async () => {
  // Calculate amounts from price lists
  // This will be implemented to fetch prices from backend
  // For now, we'll sum up from the actual data
  
  // Sum investigations
  let investigationsTotal = 0;
  for (const inv of investigationsList.value) {
    if (inv.gdrg && inv.description) {
      // TODO: Get price from price list
      // For now, set a placeholder
      investigationsTotal += 0; // Will be calculated from price list
    }
  }
  
  // Sum prescriptions
  let pharmacyTotal = 0;
  for (const presc of prescriptionsList.value) {
    if (presc.total_cost) {
      pharmacyTotal += presc.total_cost;
    }
  }
  
  // Get procedure/diagnosis totals
  // TODO: Calculate from price lists based on G-DRG codes
  
  claimSummary.value[2].tariff_amount = investigationsTotal; // C Investigations
  claimSummary.value[3].tariff_amount = pharmacyTotal; // D Pharmacy
  
  // Calculate total
  claimSummary.value[4].tariff_amount = totalClaimAmount.value;
};

const loadClaimData = async () => {
  loading.value = true;
  try {
    const response = await claimsAPI.getEditDetails(claimId.value);
    const data = response.data;
    
    // Set claim status
    claimStatus.value = data.claim.status;
    
    // Populate patient info
    Object.assign(patientInfo, {
      surname: data.patient.surname || '',
      other_names: `${data.patient.name} ${data.patient.other_names || ''}`.trim(),
      date_of_birth: data.patient.date_of_birth || '',
      age: data.patient.age,
      gender: data.patient.gender,
      member_number: data.patient.insurance_id || '',
      hospital_record_no: data.patient.card_number || '',
      card_serial_no: data.encounter.ccc_number || '',
    });
    
    // Populate services
    Object.assign(services, {
      type_of_service: data.claim.type_of_service || 'OPD',
      first_visit: data.encounter.created_at ? data.encounter.created_at.split('T')[0] : '',
      second_visit: data.encounter.finalized_at ? data.encounter.finalized_at.split('T')[0] : '',
      type_of_attendance: data.claim.type_of_attendance || 'EAE',
      specialty_code: data.claim.specialty_attended || '',
      outcome: data.claim.service_outcome || 'DISC',
      all_inclusive: !data.claim.is_unbundled,
      principal_gdrg: data.claim.principal_gdrg || '',
    });
    
    // Reset and populate procedures (always populate all 3 slots)
    procedures.physician_id = data.claim.physician_id || '';
    proceduresList.value = Array.from({ length: 3 }, (_, idx) => {
      const proc = data.procedures && data.procedures[idx] ? data.procedures[idx] : null;
      return {
        index: idx,
        description: proc?.description || '',
        date: proc?.date ? proc.date.split('T')[0] : '',
        gdrg: proc?.gdrg || '',
      };
    });
    
    // Reset and populate diagnoses (always populate all 4 slots)
    diagnosesList.value = Array.from({ length: 4 }, (_, idx) => {
      const diag = data.diagnoses && data.diagnoses[idx] ? data.diagnoses[idx] : null;
      return {
        index: idx,
        id: diag?.id || null,
        description: diag?.description || '',
        icd10: diag?.icd10 || '',
        gdrg: diag?.gdrg || '',
        is_chief: diag?.is_chief || false,
      };
    });
    
    // Reset and populate investigations (always populate all 5 slots)
    investigationsList.value = Array.from({ length: 5 }, (_, idx) => {
      const inv = data.investigations && data.investigations[idx] ? data.investigations[idx] : null;
      return {
        index: idx,
        id: inv?.id || null,
        description: inv?.description || '',
        date: inv?.date ? inv.date.split('T')[0] : '',
        gdrg: inv?.gdrg || '',
      };
    });
    
    // Reset and populate prescriptions (always populate all 5 slots)
    prescriptionsList.value = Array.from({ length: 5 }, (_, idx) => {
      const presc = data.prescriptions && data.prescriptions[idx] ? data.prescriptions[idx] : null;
      return {
        index: idx,
        id: presc?.id || null,
        description: presc?.description || '',
        code: presc?.code || '',
        price: presc?.price || 0,
        quantity: presc?.quantity || 0,
        total_cost: presc?.total_cost || 0,
        date: presc?.date ? presc.date.split('T')[0] : '',
        dose: presc?.dose || '',
        frequency: presc?.frequency || '',
        duration: presc?.duration || '',
        unparsed: presc?.unparsed || '',
      };
    });
    
    // Populate claim summary
    if (data.claim_summary) {
      claimSummary.value[0].tariff_amount = data.claim_summary.inpatient_amount || 0; // A In-Patient
      claimSummary.value[1].tariff_amount = data.claim_summary.outpatient_amount || 0; // B Out-Patient
      claimSummary.value[2].tariff_amount = data.claim_summary.investigations_amount || 0; // C Investigations
      claimSummary.value[3].tariff_amount = data.claim_summary.pharmacy_amount || 0; // D Pharmacy
    } else {
      await calculateClaimSummary();
    }
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to load claim data',
    });
    $router.back();
  } finally {
    loading.value = false;
  }
};

const saveClaim = async (e) => {
  if (e) {
    e.preventDefault();
  }
  saving.value = true;
  try {
    // Don't navigate away - just save
    // Filter out empty entries
    const diagnosesToSave = diagnosesList.value
      .filter(d => d.description && d.description.trim() !== '');
    
    const investigationsToSave = investigationsList.value
      .filter(i => i.description && i.description.trim() !== '');
    
    const prescriptionsToSave = prescriptionsList.value
      .filter(p => p.description && p.description.trim() !== '');
    
    // Filter out empty procedures
    const proceduresToSave = proceduresList.value
      .filter(p => p.description && p.description.trim() !== '');
    
    const claimData = {
      physician_id: procedures.physician_id || services.specialty_code || '',
      physician_name: procedures.physician_name || '',
      type_of_service: services.type_of_service,
      type_of_attendance: services.type_of_attendance,
      specialty_attended: services.specialty_code || '',
      service_outcome: services.outcome,
      is_unbundled: !services.all_inclusive,
      principal_gdrg: services.principal_gdrg || '',
      first_visit: services.first_visit || null,
      second_visit: services.second_visit || null,
      third_visit: services.third_visit || null,
      fourth_visit: services.fourth_visit || null,
      duration_of_spell: services.duration_of_spell || null,
      diagnoses: diagnosesToSave.map(d => ({
        id: d.id,
        description: d.description,
        icd10: d.icd10,
        gdrg: d.gdrg,
        is_chief: d.is_chief,
      })),
      investigations: investigationsToSave.map(i => ({
        id: i.id,
        description: i.description,
        date: i.date,
        gdrg: i.gdrg,
      })),
      prescriptions: prescriptionsToSave.map(p => ({
        id: p.id,
        description: p.description,
        code: p.code,
        price: p.price,
        quantity: p.quantity,
        total_cost: p.total_cost,
        date: p.date,
        dose: p.dose || '',
        frequency: p.frequency || '',
        duration: p.duration || '',
        unparsed: p.unparsed || '',
      })),
      procedures: proceduresToSave.map(p => ({
        description: p.description,
        date: p.date,
        gdrg: p.gdrg,
      })),
    };
    
    await claimsAPI.updateDetailed(claimId.value, claimData);
    
    $q.notify({
      type: 'positive',
      message: 'Claim updated successfully',
    });
    
    // Reload the data to show updated values
    await loadClaimData();
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to save claim',
    });
  } finally {
    saving.value = false;
  }
};

onMounted(async () => {
  claimId.value = parseInt(route.params.claimId);
  if (!claimId.value) {
    $q.notify({
      type: 'negative',
      message: 'Invalid claim ID',
    });
    $router.push('/claims');
    return;
  }
  // Check if in view mode (from query parameter)
  isViewMode.value = route.query.view === 'true';
  
  // If in view mode and claim is finalized, automatically reopen it
  if (isViewMode.value) {
    try {
      const claimResponse = await claimsAPI.get(claimId.value);
      if (claimResponse.data.status === 'finalized') {
        await claimsAPI.reopen(claimId.value);
        $q.notify({
          type: 'info',
          message: 'Claim has been reopened for editing',
          timeout: 3000,
        });
      }
    } catch (error) {
      console.error('Error checking/reopening claim:', error);
    }
  }
  
  loadClaimData();
});
</script>

<style scoped>
</style>
