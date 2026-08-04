<template>
  <q-page class="hms-page">
    <div v-if="loading && !patient" class="profile-loading">
      <HmsSkeleton :lines="6" />
      <div class="loading-label">Loading patient information…</div>
    </div>

    <div v-if="patient" class="profile-stack">
      <div class="patient-hero">
        <div class="hero-main">
          <div class="hero-avatar" aria-hidden="true">{{ patientInitials }}</div>
          <div class="hero-text">
            <div class="hero-name-row">
              <h1 class="hero-name">{{ displayPatientName }}</h1>
              <HmsBadge :tone="patient.insured ? 'success' : 'warning'">
                {{ patient.insured ? 'Insured' : 'Cash' }}
              </HmsBadge>
              <HmsBadge v-if="patient.insured" :tone="patient.nhis_active ? 'healthcare' : 'critical'">
                NHIS {{ patient.nhis_active ? 'Active' : 'Inactive' }}
              </HmsBadge>
            </div>
            <div class="hero-meta">
              <span class="meta-chip mono">{{ patient.card_number }}</span>
              <span v-if="patient.legacy_card_number" class="meta-sep">·</span>
              <span v-if="patient.legacy_card_number">Prev {{ patient.legacy_card_number }}</span>
              <span class="meta-sep">·</span>
              <span>{{ patient.gender === 'M' ? 'Male' : patient.gender === 'F' ? 'Female' : (patient.gender || '—') }}</span>
              <span class="meta-sep">·</span>
              <span>Age {{ patient.age ?? 'N/A' }}</span>
              <template v-if="patient.contact">
                <span class="meta-sep">·</span>
                <span>{{ patient.contact }}</span>
              </template>
            </div>
          </div>
        </div>
        <div class="hero-actions">
          <HmsButton
            v-if="canAccess(['Admin', 'Records'])"
            variant="primary"
            size="sm"
            @click="editPatient"
          >
            Edit profile
          </HmsButton>
          <HmsButton variant="secondary" size="sm" @click="printPatientRecords">Print records</HmsButton>
        </div>
      </div>

      <HmsCard class="profile-panel">
        <div class="panel-head">
          <h2 class="hms-section-title">Demographics & insurance</h2>
        </div>
        <div class="demo-grid">
          <div class="demo-item">
            <div class="hms-field-label">{{ patient.legacy_card_number ? 'GHIMS card' : 'Card number' }}</div>
            <div class="hms-field-value mono accent">{{ patient.card_number }}</div>
          </div>
          <div v-if="patient.legacy_card_number" class="demo-item">
            <div class="hms-field-label">Previous HMS card</div>
            <div class="hms-field-value mono">{{ patient.legacy_card_number }}</div>
          </div>
          <div class="demo-item">
            <div class="hms-field-label">Sex</div>
            <div class="hms-field-value">{{ patient.gender === 'M' ? 'Male' : patient.gender === 'F' ? 'Female' : patient.gender }}</div>
          </div>
          <div class="demo-item">
            <div class="hms-field-label">Age</div>
            <div class="hms-field-value">{{ patient.age ?? 'N/A' }}</div>
          </div>
          <div class="demo-item">
            <div class="hms-field-label">Date of birth</div>
            <div class="hms-field-value">{{ formatDate(patient.date_of_birth) }}</div>
          </div>
        </div>
        <div class="panel-divider" />
        <div class="info-columns">
          <div>
            <div class="hms-field-label">Insurance</div>
            <div class="q-mb-sm">
              <HmsBadge :tone="patient.insured ? 'success' : 'warning'">
                {{ patient.insured ? 'Insured patient' : 'Cash patient' }}
              </HmsBadge>
            </div>
            <template v-if="patient.insured">
              <div class="info-line"><span>NHIS active</span><strong>{{ patient.nhis_active ? 'Yes' : 'No (cash & carry)' }}</strong></div>
              <div class="info-line"><span>Member no.</span><strong>{{ patient.insurance_id || 'N/A' }}</strong></div>
              <div class="info-line"><span>HIN</span><strong>{{ patient.hin || 'N/A' }}</strong></div>
              <div v-if="patient.ccc_number" class="info-line"><span>CCC</span><strong>{{ patient.ccc_number }}<template v-if="patient.ccc_status"> ({{ patient.ccc_status }})</template></strong></div>
              <div class="info-line"><span>Valid from</span><strong>{{ formatDate(patient.insurance_start_date) }}</strong></div>
              <div class="info-line"><span>Valid to</span><strong>{{ formatDate(patient.insurance_end_date) }}</strong></div>
            </template>
          </div>
          <div>
            <div class="hms-field-label">Contact</div>
            <div class="info-line"><span>Phone</span><strong>{{ patient.contact || 'N/A' }}</strong></div>
            <div class="info-line"><span>Address</span><strong>{{ patient.address || 'N/A' }}</strong></div>
            <template v-if="patient.emergency_contact_name || patient.emergency_contact_relationship || patient.emergency_contact_number">
              <div class="hms-field-label q-mt-md">Emergency contact</div>
              <div v-if="patient.emergency_contact_name" class="info-line"><span>Name</span><strong>{{ patient.emergency_contact_name }}</strong></div>
              <div v-if="patient.emergency_contact_relationship" class="info-line"><span>Relationship</span><strong>{{ patient.emergency_contact_relationship }}</strong></div>
              <div v-if="patient.emergency_contact_number" class="info-line"><span>Phone</span><strong>{{ patient.emergency_contact_number }}</strong></div>
            </template>
            <template v-if="patient.marital_status || patient.educational_level || patient.occupation">
              <div class="hms-field-label q-mt-md">Additional</div>
              <div v-if="patient.marital_status" class="info-line"><span>Marital status</span><strong>{{ patient.marital_status }}</strong></div>
              <div v-if="patient.educational_level" class="info-line"><span>Education</span><strong>{{ patient.educational_level }}</strong></div>
              <div v-if="patient.occupation" class="info-line"><span>Occupation</span><strong>{{ patient.occupation }}</strong></div>
            </template>
          </div>
        </div>
      </HmsCard>

      <HmsCard v-if="patient" class="profile-panel">
        <div class="panel-head">
          <h2 class="hms-section-title">Bill summary</h2>
          <button type="button" class="balance-pill" :class="balanceTone" @click="openBillItemsDialog">
            <span class="balance-label">Total balance</span>
            <span class="balance-value">₵{{ totalRemainingBalance.toFixed(2) }}</span>
            <span class="balance-hint">View items</span>
          </button>
        </div>
        <div v-if="unpaidEncounters.length > 0" class="bill-list">
          <button
            v-for="encounter in unpaidEncounters"
            :key="encounter.id"
            type="button"
            class="bill-row"
            @click="viewEncounterBilling(encounter.id)"
          >
            <div class="bill-icon" :class="encounter.remaining_balance > 0 ? 'due' : 'ok'">
              <Receipt :size="16" />
            </div>
            <div class="bill-copy">
              <div class="bill-title">Encounter #{{ encounter.id }} · {{ encounter.department }}</div>
              <div class="bill-sub">{{ formatDateTime(encounter.created_at) }}</div>
            </div>
            <div class="bill-amount" :class="encounter.remaining_balance > 0 ? 'due' : 'ok'">
              ₵{{ encounter.remaining_balance.toFixed(2) }}
            </div>
          </button>
        </div>
        <div v-else-if="loadingBills" class="panel-empty"><HmsSkeleton :lines="3" /></div>
        <div v-else class="panel-empty muted">No unpaid services found</div>
      </HmsCard>

      <!-- IPD Information -->
      <HmsCard v-if="patient && wardAdmissions.length > 0" class="profile-panel">
        <div class="panel-head">
          <h2 class="hms-section-title">Inpatient (IPD)</h2>
        </div>
        <div class="ipd-list">
          <div v-for="admission in wardAdmissions" :key="admission.id" class="ipd-row">
            <div class="ipd-copy">
              <div class="ipd-title">
                Ward {{ admission.ward }}
                <HmsBadge :tone="admission.discharged_at ? 'neutral' : 'success'" class="q-ml-sm">
                  {{ admission.discharged_at ? 'Discharged' : 'Active' }}
                </HmsBadge>
              </div>
              <div class="ipd-meta">
                Admitted {{ formatDateTime(admission.admitted_at) }}
                <template v-if="admission.bed_number"> · Bed {{ admission.bed_number }}</template>
                <template v-if="admission.discharged_at"> · Discharged {{ formatDateTime(admission.discharged_at) }}</template>
                <template v-if="admission.encounter_department"> · {{ admission.encounter_department }}</template>
              </div>
            </div>
            <HmsButton
              v-if="!admission.discharged_at"
              variant="primary"
              size="sm"
              @click="goToIPD(admission.id)"
            >
              Go to IPD
            </HmsButton>
            <HmsButton
              v-else
              variant="secondary"
              size="sm"
              @click="viewIPDDetails(admission.id)"
            >
              View details
            </HmsButton>
          </div>
        </div>
      </HmsCard>

      <!-- Patient Encounters -->
      <HmsCard class="profile-panel encounters-panel">
        <div class="panel-head">
          <h2 class="hms-section-title">Encounters history</h2>
          <HmsButton variant="primary" size="sm" @click="createNewEncounter">
            <Plus :size="14" />
            New encounter
          </HmsButton>
        </div>

          <q-table
            :rows="patientEncounters"
            :columns="encounterColumns"
            row-key="id"
            flat
            :loading="loadingEncounters"
            class="glass-table profile-q-table"
          >
            <template v-slot:body-cell-status="props">
              <q-td :props="props">
                <HmsBadge :tone="encounterStatusTone(props.value)">{{ props.value }}</HmsBadge>
              </q-td>
            </template>
            <template v-slot:body-cell-created_at="props">
              <q-td :props="props">
                {{ formatDateTime(props.value) }}
              </q-td>
            </template>
            <template v-slot:body-cell-actions="props">
              <q-td :props="props">
                <div class="encounter-actions">
                  <HmsButton
                    v-if="canAccess(['Doctor', 'PA', 'Admin'])"
                    variant="soft"
                    size="sm"
                    @click="goToConsultation(props.row.id)"
                  >
                    Consult
                  </HmsButton>
                  <HmsButton
                    v-if="canAccess(['Nurse', 'Admin'])"
                    variant="soft"
                    size="sm"
                    @click="goToVitals(props.row.id)"
                  >
                    Vitals
                  </HmsButton>
                  <HmsButton
                    v-if="canAccess(['Pharmacy', 'Pharmacy Head', 'Store Manager', 'Admin'])"
                    variant="soft"
                    size="sm"
                    @click="goToPharmacy(props.row.id)"
                  >
                    Rx
                  </HmsButton>
                  <HmsButton
                    v-if="canAccess(['Lab', 'Admin'])"
                    variant="soft"
                    size="sm"
                    @click="goToLab(props.row.id)"
                  >
                    Lab
                  </HmsButton>
                  <HmsButton
                    v-if="canAccess(['Scan', 'Admin'])"
                    variant="soft"
                    size="sm"
                    @click="goToScan(props.row.id)"
                  >
                    Scan
                  </HmsButton>
                  <HmsButton
                    v-if="canAccess(['Xray', 'Admin'])"
                    variant="soft"
                    size="sm"
                    @click="goToXray(props.row.id)"
                  >
                    X-ray
                  </HmsButton>
                  <HmsButton
                    v-if="canAccess(['Billing', 'Admin'])"
                    variant="healthcare"
                    size="sm"
                    @click="viewEncounterBilling(props.row.id)"
                  >
                    Bill
                  </HmsButton>
                  <HmsButton
                    v-if="canAccess(['Admin', 'Records'])"
                    variant="ghost"
                    size="sm"
                    @click="viewEncounter(props.row.id)"
                  >
                    View
                  </HmsButton>
                  <HmsButton
                    v-if="canAccess(['Admin', 'Records'])"
                    variant="ghost"
                    size="sm"
                    @click="editEncounter(props.row)"
                  >
                    Edit
                  </HmsButton>
                  <HmsButton
                    v-if="isAdmin"
                    variant="danger"
                    size="sm"
                    @click="deleteEncounterConfirm(props.row)"
                  >
                    Delete
                  </HmsButton>
                </div>
              </q-td>
            </template>
          </q-table>
      </HmsCard>
    </div>

    <HmsCard v-if="!loading && !patient" class="profile-panel not-found">
      <HmsEmptyState title="Patient not found" description="No patient record matches this card number." />
    </HmsCard>

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
                hint="Format: E-0032-26050735. Leave unchanged to keep current card."
                class="col-12 col-md-6"
              />
              <q-input
                v-if="patient?.legacy_card_number"
                :model-value="patient.legacy_card_number"
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
                  label="NHIS Member Number"
                  hint="Used to fetch CCC from NHIA (not the HIN)"
                  class="col-12 col-md-4"
                />
                <q-input
                  v-model="editForm.hin"
                  filled
                  label="HIN"
                  hint="From NHIA import or manual entry"
                  class="col-12 col-md-3"
                />
                <q-input
                  v-model="nhiaOtac"
                  filled
                  label="OTAC (if required)"
                  hint="4-digit code from patient"
                  class="col-12 col-md-2"
                  maxlength="4"
                />
                <q-btn
                  color="secondary"
                  icon="cloud_download"
                  label="Import from NHIA"
                  class="col-12 col-md-auto q-mt-xs"
                  :loading="importingNhia"
                  :disable="!editForm.insurance_id || !editForm.insurance_id.trim()"
                  @click="importFromNhia"
                />
                <q-btn
                  v-if="patient?.id"
                  color="primary"
                  icon="verified"
                  label="Generate CCC"
                  class="col-12 col-md-auto q-mt-xs"
                  :loading="generatingCcc"
                  :disable="!canGenerateCcc"
                  @click="generateCccForPatient"
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
                :loading="saving"
              />
              <q-btn
                label="Cancel"
                flat
                color="grey"
                @click="showEditDialog = false"
                class="q-ml-sm"
              />
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- Edit Encounter Dialog -->
    <q-dialog v-model="showEditEncounterDialog" persistent>
      <q-card style="min-width: 500px">
        <q-card-section>
          <div class="text-h6">Edit Encounter #{{ currentEncounter?.id }}</div>
        </q-card-section>

        <q-card-section>
          <q-form @submit="saveEncounterEdit" class="q-gutter-md">
            <q-select
              v-model="encounterEditForm.department"
              filled
              :options="departmentOptions"
              option-label="service_type"
              option-value="service_type"
              emit-value
              map-options
              label="Department/Clinic *"
              lazy-rules
              :rules="[(val) => !!val || 'Required']"
            />
            <q-select
              v-model="encounterEditForm.procedure_g_drg_code"
              filled
              :options="procedureOptions"
              option-label="service_name"
              option-value="g_drg_code"
              emit-value
              map-options
              label="Procedure (optional)"
              @update:model-value="val => { const sel = (procedureOptions||[]).find(p=>p.g_drg_code===val); encounterEditForm.procedure_name = sel?.service_name || '' }"
              :disable="!encounterEditForm.department"
            />
            <div class="row q-col-gutter-sm items-start">
              <q-input
                v-model="encounterEditForm.ccc_number"
                filled
                class="col"
                label="CCC Number"
              />
              <q-btn
                class="col-auto q-mt-xs"
                color="secondary"
                icon="cloud_download"
                label="Get CCC"
                :loading="generatingEncounterCcc"
                :disable="!canGetEncounterCcc"
                @click="fetchEncounterCcc"
              />
            </div>
            <q-select
              v-model="encounterEditForm.status"
              filled
              :options="statusOptions"
              label="Status"
            />
            <div>
              <q-btn
                label="Save Changes"
                type="submit"
                color="primary"
              />
              <q-btn
                label="Cancel"
                flat
                color="grey"
                @click="showEditEncounterDialog = false"
                class="q-ml-sm"
              />
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>
    <!-- Bill Items Dialog -->
    <q-dialog v-model="showBillItemsDialog" maximized>
      <q-card>
        <q-card-section class="row items-center q-pb-none">
          <div class="text-h6">Bill Items - {{ patient?.name }} {{ patient?.surname || '' }}</div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>
        <q-card-section>
          <div v-if="loadingBillItems" class="text-center q-pa-md">
            <q-spinner color="primary" size="3em" />
            <div class="q-mt-md">Loading bill items...</div>
          </div>
          <div v-else-if="allBillItems.length === 0" class="text-center q-pa-md text-grey-7">
            No bill items found for this patient.
          </div>
          <q-table
            v-else
            :rows="allBillItems"
            :columns="billItemsColumns"
            row-key="id"
            :pagination="{ rowsPerPage: 50 }"
            class="bill-items-table"
            flat
            bordered
          >
            <template v-slot:body-cell-encounter_id="props">
              <q-td :props="props">
                <q-badge color="primary" :label="`Encounter #${props.value}`" />
              </q-td>
            </template>
            <template v-slot:body-cell-remaining_balance="props">
              <q-td :props="props" :class="props.value > 0.01 ? 'text-negative text-weight-bold' : 'text-positive'">
                GHC {{ props.value.toFixed(2) }}
              </q-td>
            </template>
            <template v-slot:body-cell-is_paid="props">
              <q-td :props="props">
                <q-badge :color="props.value ? 'positive' : 'negative'" :label="props.value ? 'Paid' : 'Unpaid'" />
              </q-td>
            </template>
          </q-table>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Close" color="primary" v-close-popup />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { patientsAPI, encountersAPI, billingAPI, consultationAPI, vitalsAPI } from '../services/api';
import { usePatientsStore } from '../stores/patients';
import { useEncountersStore } from '../stores/encounters';
import { useAuthStore } from '../stores/auth';
import { useFacilityStore } from '../stores/facility';
import { useQuasar } from 'quasar';
import { priceListAPI } from '../services/api';
import { applyNhiaDataToForm, applyNhiaCccToForm, canFetchNhiaCcc } from '../utils/nhiaForm';
import HmsButton from '../components/ui/HmsButton.vue';
import HmsBadge from '../components/ui/HmsBadge.vue';
import HmsSkeleton from '../components/ui/HmsSkeleton.vue';
import HmsCard from '../components/ui/HmsCard.vue';
import HmsEmptyState from '../components/ui/HmsEmptyState.vue';
import { Receipt, Plus } from 'lucide-vue-next';

const $q = useQuasar();
const route = useRoute();
const router = useRouter();
const patientsStore = usePatientsStore();
const encountersStore = useEncountersStore();
const authStore = useAuthStore();
const facilityStore = useFacilityStore();

const patient = ref(null);
const patientEncounters = ref([]);
const loading = ref(false);
const loadingEncounters = ref(false);
const loadingBills = ref(false);
const loadingIPD = ref(false);
const wardAdmissions = ref([]);
const totalBillAmount = ref(0);
const totalPaidAmount = ref(0);
const totalRemainingBalance = computed(() => Math.max(0, totalBillAmount.value - totalPaidAmount.value));
const showBillItemsDialog = ref(false);
const loadingBillItems = ref(false);
const allBillItems = ref([]);
const billItemsColumns = [
  { name: 'encounter_id', label: 'Encounter', field: 'encounter_id', align: 'center', sortable: true },
  { name: 'item_name', label: 'Service/Item', field: 'item_name', align: 'left', sortable: true },
  { name: 'category', label: 'Category', field: 'category', align: 'center', sortable: true },
  { name: 'quantity', label: 'Qty', field: 'quantity', align: 'center', sortable: true },
  { name: 'unit_price', label: 'Unit Price', field: 'unit_price', align: 'right', sortable: true, format: (val) => `GHC ${(val || 0).toFixed(2)}` },
  { name: 'total_price', label: 'Total Price', field: 'total_price', align: 'right', sortable: true, format: (val) => `GHC ${(val || 0).toFixed(2)}` },
  { name: 'amount_paid', label: 'Amount Paid', field: 'amount_paid', align: 'right', sortable: true, format: (val) => `GHC ${(val || 0).toFixed(2)}` },
  { name: 'remaining_balance', label: 'Outstanding', field: 'remaining_balance', align: 'right', sortable: true },
  { name: 'is_paid', label: 'Status', field: 'is_paid', align: 'center', sortable: true },
];
const unpaidEncounters = ref([]);
const saving = ref(false);
const importingNhia = ref(false);
const nhiaOtac = ref('');
const generatingCcc = ref(false);
const generatingEncounterCcc = ref(false);
const ghimsCardMode = ref(false);
const showEditDialog = ref(false);
const showEditEncounterDialog = ref(false);
const currentEncounter = ref(null);
const isAdmin = computed(() => authStore.userRole === 'Admin');

const encounterEditForm = reactive({
  department: '',
  ccc_number: '',
  status: '',
  procedure_g_drg_code: '',
  procedure_name: ''
});

const genderOptions = ['M', 'F'];

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

const editForm = reactive({
  name: '',
  surname: '',
  other_names: '',
  gender: '',
  age: null,
  date_of_birth: '',
  insured: false,
  nhis_active: false,
  insurance_id: '',
  hin: '',
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
  card_number: '',
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

// Watch date_of_birth in editForm and auto-calculate age
watch(() => editForm.date_of_birth, (newDateOfBirth) => {
  if (newDateOfBirth) {
    const calculatedAge = calculateAgeFromDateOfBirth(newDateOfBirth);
    if (calculatedAge !== null) {
      editForm.age = calculatedAge;
    }
  }
});

const encounterColumns = [
  { name: 'id', label: 'Encounter ID', field: 'id', align: 'left' },
  { name: 'created_at', label: 'Date & Time', field: 'created_at', align: 'left', sortable: true },
  { name: 'department', label: 'Department', field: 'department', align: 'left' },
  { name: 'status', label: 'Status', field: 'status', align: 'center' },
  { name: 'ccc_number', label: 'CCC Number', field: 'ccc_number', align: 'left' },
  { name: 'actions', label: 'Actions', align: 'center' },
];

const departmentOptions = ref([]);
const procedureOptions = ref([]);
const statusOptions = ['draft', 'in_consultation', 'awaiting_services', 'finalized'];

const loadServiceTypes = async () => {
  try {
    const resp = await priceListAPI.getServiceTypes();
    departmentOptions.value = resp.data || [];
  } catch (e) {
    departmentOptions.value = [];
  }
};

watch(() => encounterEditForm.department, async (newVal) => {
  if (!newVal) { procedureOptions.value = []; return; }
  try {
    const resp = await priceListAPI.getProceduresByServiceType(newVal);
    procedureOptions.value = resp.data || [];
  } catch (e) {
    procedureOptions.value = [];
  }
});

const formatDate = (dateString) => {
  if (!dateString) return 'N/A';
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', { 
    year: 'numeric', 
    month: 'long', 
    day: 'numeric' 
  });
};

const formatDateTime = (dateString) => {
  if (!dateString) return 'N/A';
  const date = new Date(dateString);
  return date.toLocaleString('en-US', { 
    year: 'numeric', 
    month: 'short', 
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
};

const getStatusColor = (status) => {
  const colors = {
    draft: 'orange',
    in_consultation: 'blue',
    awaiting_services: 'purple',
    finalized: 'green',
  };
  return colors[status] || 'grey';
};

const loadPatient = async () => {
  const cardNumber = route.params.cardNumber;
  if (!cardNumber) {
    $q.notify({
      type: 'warning',
      message: 'Card number not provided',
    });
    return;
  }

  loading.value = true;
  try {
    const response = await patientsAPI.getByCard(cardNumber);
    console.log('Profile card search response:', response);
    
    // FastAPI returns List[PatientResponse] which Axios wraps in response.data
    let patients = [];
    if (Array.isArray(response.data)) {
      patients = response.data;
    } else if (response.data?.data && Array.isArray(response.data.data)) {
      patients = response.data.data;
    } else if (response.data?.results && Array.isArray(response.data.results)) {
      patients = response.data.results;
    }
    
    if (patients.length === 0) {
      $q.notify({
        type: 'negative',
        message: 'Patient not found',
      });
      patient.value = null;
      return;
    }
    
    // If multiple matches, use the exact match if available, otherwise use first one
    // Try to find exact match first (case-insensitive)
    const normalizedCard = cardNumber.trim().toUpperCase();
    const exactMatch = patients.find(p => 
      p.card_number && p.card_number.toUpperCase() === normalizedCard
    );
    
    patient.value = exactMatch || patients[0];
    await loadEncounters(patient.value.id);
    await loadWardAdmissions(patient.value.card_number);
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Patient not found',
    });
    patient.value = null;
  } finally {
    loading.value = false;
  }
};

const loadEncounters = async (patientId) => {
  loadingEncounters.value = true;
  try {
    const response = await encountersAPI.getPatientEncounters(patientId);
    patientEncounters.value = response.data;
    
    // Load bill information for all encounters
    await loadBillSummary(patientId);
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to load encounters',
    });
    patientEncounters.value = [];
  } finally {
    loadingEncounters.value = false;
  }
};

const loadWardAdmissions = async (cardNumber) => {
  if (!cardNumber) return;
  
  loadingIPD.value = true;
  try {
    const response = await consultationAPI.getWardAdmissionsByPatientCard(cardNumber, true); // Include discharged
    wardAdmissions.value = response.data || [];
  } catch (error) {
    console.error('Failed to load ward admissions:', error);
    wardAdmissions.value = [];
  } finally {
    loadingIPD.value = false;
  }
};

const loadBillSummary = async (patientId) => {
  if (!patientId) return;
  
  loadingBills.value = true;
  try {
    // Get all encounters for this patient
    const encounters = patientEncounters.value.filter(e => !e.archived);
    
    // Load bills for each encounter
    const encounterBills = await Promise.all(
      encounters.map(async (encounter) => {
        try {
          const billsResponse = await billingAPI.getEncounterBills(encounter.id);
          const bills = billsResponse.data || [];
          
          const encounterTotal = bills.reduce((sum, bill) => sum + (bill.total_amount || 0), 0);
          const encounterPaid = bills.reduce((sum, bill) => sum + (bill.paid_amount || 0), 0);
          const encounterBalance = encounterTotal - encounterPaid;
          
          return {
            ...encounter,
            total_amount: encounterTotal,
            paid_amount: encounterPaid,
            remaining_balance: encounterBalance,
            has_bills: bills.length > 0,
          };
        } catch (error) {
          console.error(`Failed to load bills for encounter ${encounter.id}:`, error);
          return {
            ...encounter,
            total_amount: 0,
            paid_amount: 0,
            remaining_balance: 0,
            has_bills: false,
          };
        }
      })
    );
    
    // Calculate totals
    totalBillAmount.value = encounterBills.reduce((sum, e) => sum + e.total_amount, 0);
    totalPaidAmount.value = encounterBills.reduce((sum, e) => sum + e.paid_amount, 0);
    
    // Filter unpaid encounters (those with remaining balance > 0)
    unpaidEncounters.value = encounterBills.filter(e => e.remaining_balance > 0);
  } catch (error) {
    console.error('Failed to load bill summary:', error);
    totalBillAmount.value = 0;
    totalPaidAmount.value = 0;
    unpaidEncounters.value = [];
  } finally {
    loadingBills.value = false;
  }
};

const goToBilling = () => {
  if (unpaidEncounters.value.length > 0) {
    // Go to billing page with the first unpaid encounter
    router.push({
      name: 'Billing',
      params: { encounterId: unpaidEncounters.value[0].id }
    });
  }
};

const openBillItemsDialog = async () => {
  if (!patient.value || !patient.value.id) {
    $q.notify({ type: 'warning', message: 'No patient selected', position: 'top' });
    return;
  }
  
  showBillItemsDialog.value = true;
  loadingBillItems.value = true;
  allBillItems.value = [];
  
  try {
    // Get all active encounters for this patient
    const encountersResponse = await encountersAPI.getPatientEncounters(patient.value.id);
    const allEncounters = encountersResponse.data.filter(e => !e.archived);
    
    if (allEncounters.length === 0) {
      loadingBillItems.value = false;
      return;
    }
    
    // Load bills and bill items for all encounters
    const billItemsList = [];
    
    for (const encounter of allEncounters) {
      try {
        const billsResponse = await billingAPI.getEncounterBills(encounter.id);
        const bills = Array.isArray(billsResponse.data) ? billsResponse.data : [];
        
        for (const bill of bills) {
          try {
            const billDetailsResponse = await billingAPI.getBillDetails(bill.id);
            const billDetails = billDetailsResponse.data?.data || billDetailsResponse.data || {};
            const billItems = billDetails.bill_items || [];
            
            for (const item of billItems) {
              const amountPaid = (item.amount_paid !== undefined && item.amount_paid !== null) ? item.amount_paid : 0;
              const totalPrice = (item.total_price !== undefined && item.total_price !== null) ? item.total_price : 0;
              const remainingBalance = (item.remaining_balance !== undefined && item.remaining_balance !== null)
                ? item.remaining_balance 
                : (totalPrice - amountPaid);
              const isPaid = remainingBalance <= 0.01;
              
              billItemsList.push({
                id: item.id,
                encounter_id: encounter.id,
                item_name: item.item_name || 'N/A',
                category: item.category || 'N/A',
                quantity: item.quantity || 0,
                unit_price: item.unit_price || 0,
                total_price: totalPrice,
                amount_paid: amountPaid,
                remaining_balance: remainingBalance,
                is_paid: isPaid,
              });
            }
          } catch (error) {
            console.error(`Failed to load bill details for bill ${bill.id}:`, error);
          }
        }
      } catch (error) {
        console.error(`Failed to load bills for encounter ${encounter.id}:`, error);
      }
    }
    
    // Sort by encounter ID and then by item name
    billItemsList.sort((a, b) => {
      if (a.encounter_id !== b.encounter_id) {
        return b.encounter_id - a.encounter_id; // Newest encounters first
      }
      return (a.item_name || '').localeCompare(b.item_name || '');
    });
    
    allBillItems.value = billItemsList;
  } catch (error) {
    console.error('Error loading bill items:', error);
    $q.notify({ 
      type: 'negative', 
      message: 'Failed to load bill items', 
      position: 'top' 
    });
  } finally {
    loadingBillItems.value = false;
  }
};

const viewEncounterBilling = (encounterId) => {
  router.push({
    name: 'Billing',
    params: { encounterId: encounterId }
  });
};

// Navigation functions for different roles
const goToConsultation = (encounterId) => {
  router.push({
    name: 'Consultation',
    params: { encounterId: encounterId }
  });
};

const goToVitals = (encounterId) => {
  router.push({
    name: 'Vitals',
    query: { encounterId: encounterId }
  });
};

const goToPharmacy = (encounterId) => {
  router.push({
    name: 'Pharmacy',
    query: { encounterId: encounterId }
  });
};

const goToLab = (encounterId) => {
  router.push({
    name: 'Lab',
    query: { encounterId: encounterId }
  });
};

const goToScan = (encounterId) => {
  router.push({
    name: 'Scan',
    query: { encounterId: encounterId }
  });
};

const goToXray = (encounterId) => {
  router.push({
    name: 'Xray',
    query: { encounterId: encounterId }
  });
};

const goToIPD = (wardAdmissionId) => {
  router.push({
    name: 'AdmissionManager',
    params: { id: wardAdmissionId }
  });
};

const viewIPDDetails = (wardAdmissionId) => {
  router.push({
    name: 'AdmissionManager',
    params: { id: wardAdmissionId }
  });
};

const canAccess = (roles) => authStore.canAccess(roles);

const titleCase = (value) => {
  if (!value) return '';
  return String(value)
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase());
};

const displayPatientName = computed(() => {
  if (!patient.value) return '';
  return [titleCase(patient.value.name), titleCase(patient.value.surname), titleCase(patient.value.other_names)]
    .filter(Boolean)
    .join(' ');
});

const patientInitials = computed(() => {
  if (!patient.value) return '?';
  const a = (patient.value.name || '?')[0] || '?';
  const b = (patient.value.surname || '')[0] || '';
  return `${a}${b}`.toUpperCase();
});

const balanceTone = computed(() => {
  if (totalRemainingBalance.value > 0) return 'due';
  if (totalBillAmount.value > 0) return 'ok';
  return 'neutral';
});

const encounterStatusTone = (status) => {
  const s = String(status || '').toLowerCase();
  if (s.includes('complete') || s.includes('discharg') || s.includes('closed')) return 'success';
  if (s.includes('cancel') || s.includes('abort')) return 'critical';
  if (s.includes('progress') || s.includes('active') || s.includes('open')) return 'healthcare';
  if (s.includes('pending') || s.includes('wait')) return 'warning';
  return 'neutral';
};

const canGenerateCcc = computed(() => canFetchNhiaCcc(editForm));

const canGetEncounterCcc = computed(() => canFetchNhiaCcc(patient.value));

const importFromNhia = async () => {
  if (!editForm.insurance_id?.trim()) return;
  importingNhia.value = true;
  try {
    const result = await patientsStore.lookupNhia(editForm.insurance_id.trim(), nhiaOtac.value?.trim() || null);
    applyNhiaDataToForm(editForm, result.data);
    $q.notify({ type: 'positive', message: 'Patient details imported from NHIA' });
  } finally {
    importingNhia.value = false;
  }
};

const generateCccForPatient = async () => {
  if (!patient.value?.id || !canGenerateCcc.value) return;
  generatingCcc.value = true;
  try {
    const result = await patientsStore.generateCcc(patient.value.id, nhiaOtac.value?.trim() || null);
    if (result?.data?.ccc) {
      editForm.ccc_number = result.data.ccc;
    }
    if (result?.data) {
      applyNhiaCccToForm(editForm, result.data);
    }
    if (result?.patient) {
      patient.value = result.patient;
    }
  } finally {
    generatingCcc.value = false;
  }
};

const fetchEncounterCcc = async () => {
  if (!patient.value?.id || !canGetEncounterCcc.value) return;
  generatingEncounterCcc.value = true;
  try {
    const result = await patientsStore.generateCcc(patient.value.id, nhiaOtac.value?.trim() || null);
    if (result?.data?.ccc) {
      encounterEditForm.ccc_number = result.data.ccc;
    }
    if (result?.patient) {
      patient.value = result.patient;
    }
  } finally {
    generatingEncounterCcc.value = false;
  }
};

const editPatient = () => {
  if (!patient.value) return;
  
  Object.assign(editForm, {
    name: patient.value.name || '',
    surname: patient.value.surname || '',
    other_names: patient.value.other_names || '',
    gender: patient.value.gender || '',
    age: patient.value.age || null,
    date_of_birth: patient.value.date_of_birth ? patient.value.date_of_birth.split('T')[0] : '',
    insured: patient.value.insured || false,
    nhis_active: patient.value.nhis_active || false,
    insurance_id: patient.value.insurance_id || '',
    hin: patient.value.hin || '',
    insurance_start_date: patient.value.insurance_start_date 
      ? patient.value.insurance_start_date.split('T')[0] : '',
    insurance_end_date: patient.value.insurance_end_date 
      ? patient.value.insurance_end_date.split('T')[0] : '',
    ccc_number: patient.value.ccc_number || '',
    ccc_status: patient.value.ccc_status || '',
    contact: patient.value.contact || '',
    address: patient.value.address || '',
    emergency_contact_name: patient.value.emergency_contact_name || '',
    emergency_contact_relationship: patient.value.emergency_contact_relationship || '',
    emergency_contact_number: patient.value.emergency_contact_number || '',
    marital_status: patient.value.marital_status || '',
    educational_level: patient.value.educational_level || '',
    occupation: patient.value.occupation || '',
    card_number: patient.value.card_number || '',
  });
  
  showEditDialog.value = true;
};

const savePatientEdit = async () => {
  saving.value = true;
  try {
    const patientData = { ...editForm };
    
    // Clean up empty fields - send null instead of empty strings
    const fieldsToClean = [
      'date_of_birth', 'insurance_start_date', 'insurance_end_date',
      'insurance_id', 'hin', 'ccc_number', 'ccc_status', 'surname', 'other_names', 'contact', 'address',
      'emergency_contact_name', 'emergency_contact_relationship', 'emergency_contact_number',
      'marital_status', 'educational_level', 'occupation'
    ];
    
    fieldsToClean.forEach(field => {
      if (patientData[field] === '') {
        patientData[field] = null;
      }
    });
    if (!patientData.insured) {
      patientData.nhis_active = false;
    }

    if (!ghimsCardMode.value || patientData.card_number === patient.value.card_number) {
      delete patientData.card_number;
    } else if (patientData.card_number === '') {
      delete patientData.card_number;
    }
    
    await patientsStore.updatePatient(patient.value.id, patientData);
    await loadPatient(); // Reload patient data
    showEditDialog.value = false;
  } catch (error) {
    // Error handled in store
  } finally {
    saving.value = false;
  }
};

const viewEncounter = (encounterId) => {
  router.push(`/consultation/${encounterId}`);
};

const editEncounter = (encounter) => {
  showEditEncounterDialog.value = true;
  currentEncounter.value = encounter;
  encounterEditForm.department = encounter.department;
  encounterEditForm.ccc_number = encounter.ccc_number || '';
  encounterEditForm.status = encounter.status;
};

const saveEncounterEdit = async () => {
  if (!currentEncounter.value) return;
  
  const updateData = {};
  if (encounterEditForm.department !== currentEncounter.value.department) {
    updateData.department = encounterEditForm.department;
  }
  if (encounterEditForm.ccc_number !== currentEncounter.value.ccc_number) {
    updateData.ccc_number = encounterEditForm.ccc_number || null;
  }
  if (encounterEditForm.status !== currentEncounter.value.status) {
    updateData.status = encounterEditForm.status;
  }
  if (encounterEditForm.procedure_g_drg_code) {
    updateData.procedure_g_drg_code = encounterEditForm.procedure_g_drg_code;
    updateData.procedure_name = encounterEditForm.procedure_name || null;
  }
  
  if (Object.keys(updateData).length === 0) {
    $q.notify({
      type: 'info',
      message: 'No changes detected',
    });
    showEditEncounterDialog.value = false;
    return;
  }
  
  try {
    await encountersStore.updateEncounter(currentEncounter.value.id, updateData);
    showEditEncounterDialog.value = false;
    await loadEncounters(patient.value.id); // Reload encounters
  } catch (error) {
    // Error handled in store
  }
};

const deleteEncounterConfirm = (encounter) => {
  $q.dialog({
    title: 'Archive Encounter',
    message: `Are you sure you want to archive Encounter #${encounter.id}? This action cannot be undone.`,
    cancel: true,
    persistent: true,
    ok: {
      label: 'Archive',
      color: 'negative'
    }
  }).onOk(async () => {
    try {
      await encountersStore.deleteEncounter(encounter.id);
      await loadEncounters(patient.value.id); // Reload encounters
    } catch (error) {
      // Error handled in store
    }
  });
};

const createNewEncounter = () => {
  if (patient.value) {
    patientsStore.currentPatient = patient.value;
    router.push('/patients/register');
  }
};

const printPatientRecords = async () => {
  if (!patient.value) {
    $q.notify({
      type: 'warning',
      message: 'Patient information not loaded',
    });
    return;
  }

  try {
    $q.loading.show({
      message: 'Generating patient records...',
    });

    // Collect all encounter data - only finalized encounters
    const encounterData = [];
    
    for (const encounter of patientEncounters.value.filter(e => !e.archived && e.status === 'finalized')) {
      const encounterInfo = {
        ...encounter,
        vitals: null,
        consultationNotes: null,
        diagnoses: [],
        prescriptions: [],
        investigations: [],
        labResults: [],
        scanResults: [],
        xrayResults: [],
        bills: []
      };

      // Load vitals
      try {
        const vitalsResponse = await vitalsAPI.getByEncounter(encounter.id);
        encounterInfo.vitals = vitalsResponse.data || null;
      } catch (error) {
        console.error(`Failed to load vitals for encounter ${encounter.id}:`, error);
      }

      // Load consultation notes
      try {
        const notesResponse = await consultationAPI.getConsultationNotes(encounter.id);
        encounterInfo.consultationNotes = notesResponse.data || null;
      } catch (error) {
        console.error(`Failed to load consultation notes for encounter ${encounter.id}:`, error);
      }

      // Load diagnoses
      try {
        const diagnosesResponse = await consultationAPI.getDiagnoses(encounter.id);
        encounterInfo.diagnoses = diagnosesResponse.data || [];
      } catch (error) {
        console.error(`Failed to load diagnoses for encounter ${encounter.id}:`, error);
      }

      // Load prescriptions
      try {
        const prescriptionsResponse = await consultationAPI.getPrescriptions(encounter.id);
        encounterInfo.prescriptions = prescriptionsResponse.data || [];
      } catch (error) {
        console.error(`Failed to load prescriptions for encounter ${encounter.id}:`, error);
      }

      // Load investigations
      try {
        const investigationsResponse = await consultationAPI.getInvestigations(encounter.id);
        encounterInfo.investigations = investigationsResponse.data || [];
        
        // Load results for each investigation
        for (const investigation of encounterInfo.investigations) {
          if (investigation.investigation_type === 'Lab') {
            try {
              const labResultResponse = await consultationAPI.getLabResult(investigation.id);
              encounterInfo.labResults.push({
                investigation_id: investigation.id,
                result: labResultResponse.data
              });
            } catch (error) {
              console.error(`Failed to load lab result for investigation ${investigation.id}:`, error);
            }
          } else if (investigation.investigation_type === 'Scan') {
            try {
              const scanResultResponse = await consultationAPI.getScanResult(investigation.id);
              encounterInfo.scanResults.push({
                investigation_id: investigation.id,
                result: scanResultResponse.data
              });
            } catch (error) {
              console.error(`Failed to load scan result for investigation ${investigation.id}:`, error);
            }
          } else if (investigation.investigation_type === 'Xray') {
            try {
              const xrayResultResponse = await consultationAPI.getXrayResult(investigation.id);
              encounterInfo.xrayResults.push({
                investigation_id: investigation.id,
                result: xrayResultResponse.data
              });
            } catch (error) {
              console.error(`Failed to load xray result for investigation ${investigation.id}:`, error);
            }
          }
        }
      } catch (error) {
        console.error(`Failed to load investigations for encounter ${encounter.id}:`, error);
      }

      // Load bills
      try {
        const billsResponse = await billingAPI.getEncounterBills(encounter.id);
        encounterInfo.bills = billsResponse.data || [];
      } catch (error) {
        console.error(`Failed to load bills for encounter ${encounter.id}:`, error);
      }

      encounterData.push(encounterInfo);
    }

    // Sort encounters by date (newest first)
    encounterData.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

    // Collect IPD (ward admission) data
    const ipdData = [];
    
    // Load ward admissions if not already loaded
    if (wardAdmissions.value.length === 0) {
      await loadWardAdmissions(patient.value.card_number);
    }
    
    for (const admission of wardAdmissions.value) {
      const ipdInfo = {
        ...admission,
        clinicalReviews: [],
        diagnoses: [],
        investigations: [],
        prescriptions: [],
        surgeries: [],
        bills: [],
        nurseNotes: [],
        additionalServices: [],
        nurseMidDocumentations: []
      };

      // Load ward admission details
      try {
        const admissionResponse = await consultationAPI.getWardAdmission(admission.id);
        Object.assign(ipdInfo, admissionResponse.data);
      } catch (error) {
        console.error(`Failed to load ward admission ${admission.id}:`, error);
      }

      // Load clinical reviews
      try {
        const reviewsResponse = await consultationAPI.getInpatientClinicalReviews(admission.id);
        ipdInfo.clinicalReviews = reviewsResponse.data || [];
      } catch (error) {
        console.error(`Failed to load clinical reviews for admission ${admission.id}:`, error);
      }

      // Load all diagnoses
      try {
        const diagnosesResponse = await consultationAPI.getAllInpatientDiagnoses(admission.id);
        ipdInfo.diagnoses = diagnosesResponse.data || [];
      } catch (error) {
        console.error(`Failed to load diagnoses for admission ${admission.id}:`, error);
      }

      // Load all investigations
      try {
        const investigationsResponse = await consultationAPI.getAllInpatientInvestigations(admission.id);
        ipdInfo.investigations = investigationsResponse.data || [];
      } catch (error) {
        console.error(`Failed to load investigations for admission ${admission.id}:`, error);
      }

      // Load all prescriptions
      try {
        const prescriptionsResponse = await consultationAPI.getAllWardAdmissionPrescriptions(admission.id);
        ipdInfo.prescriptions = prescriptionsResponse.data || [];
      } catch (error) {
        console.error(`Failed to load prescriptions for admission ${admission.id}:`, error);
      }

      // Load surgeries
      try {
        const surgeriesResponse = await consultationAPI.getInpatientSurgeries(admission.id);
        ipdInfo.surgeries = surgeriesResponse.data || [];
      } catch (error) {
        console.error(`Failed to load surgeries for admission ${admission.id}:`, error);
      }

      // Load bills for the encounter
      if (ipdInfo.encounter_id) {
        try {
          const billsResponse = await billingAPI.getEncounterBills(ipdInfo.encounter_id);
          ipdInfo.bills = billsResponse.data || [];
        } catch (error) {
          console.error(`Failed to load bills for IPD encounter ${ipdInfo.encounter_id}:`, error);
        }
      }

      // Load nurse notes
      try {
        const nurseNotesResponse = await consultationAPI.getNurseNotes(admission.id);
        ipdInfo.nurseNotes = nurseNotesResponse.data || [];
      } catch (error) {
        console.error(`Failed to load nurse notes for admission ${admission.id}:`, error);
      }

      // Load additional services
      try {
        const additionalServicesResponse = await consultationAPI.getInpatientAdditionalServices(admission.id, false); // Include inactive
        ipdInfo.additionalServices = additionalServicesResponse.data || [];
      } catch (error) {
        console.error(`Failed to load additional services for admission ${admission.id}:`, error);
      }

      // Load nurse/mid documentation
      try {
        const nurseMidDocsResponse = await consultationAPI.getNurseMidDocumentations(admission.id);
        ipdInfo.nurseMidDocumentations = nurseMidDocsResponse.data || [];
      } catch (error) {
        console.error(`Failed to load nurse/mid documentation for admission ${admission.id}:`, error);
      }

      ipdData.push(ipdInfo);
    }

    // Sort IPD admissions by date (newest first)
    ipdData.sort((a, b) => new Date(b.admitted_at || b.created_at) - new Date(a.admitted_at || a.created_at));

    // Generate HTML
    const html = buildPatientRecordsHtml(patient.value, encounterData, ipdData);
    
    // Open in new window and print
    const w = window.open('', '_blank', 'width=1200,height=800');
    if (!w) {
      $q.loading.hide();
      $q.notify({
        type: 'negative',
        message: 'Please allow popups to print records',
      });
      return;
    }
    
    w.document.open();
    w.document.write(html);
    w.document.close();
    
    $q.loading.hide();
    
    setTimeout(() => {
      try {
        w.focus();
        w.print();
      } catch (e) {
        console.error('Print error:', e);
      }
    }, 500);
  } catch (error) {
    $q.loading.hide();
    console.error('Failed to generate patient records:', error);
    $q.notify({
      type: 'negative',
      message: 'Failed to generate patient records',
    });
  }
};

const buildPatientRecordsHtml = (patient, encounterData, ipdData = []) => {
  const now = new Date();

  // Build patient biostats section
  const biostatsHtml = `
    <div class="section">
      <h3 class="section-title">PATIENT BIOSTATISTICS</h3>
      <div class="two-column">
        <div><strong>Card Number:</strong> ${patient.card_number || 'N/A'}</div>
        ${patient.legacy_card_number ? `<div><strong>Previous HMS Card:</strong> ${patient.legacy_card_number}</div>` : ''}
        <div><strong>Name:</strong> ${patient.name || ''} ${patient.surname || ''} ${patient.other_names || ''}</div>
        <div><strong>Gender:</strong> ${patient.gender || 'N/A'}</div>
        <div><strong>Age:</strong> ${patient.age || 'N/A'}</div>
        <div><strong>Date of Birth:</strong> ${formatDate(patient.date_of_birth)}</div>
        <div><strong>Contact:</strong> ${patient.contact || 'N/A'}</div>
        <div><strong>Address:</strong> ${patient.address || 'N/A'}</div>
        <div><strong>Insurance Status:</strong> ${patient.insured ? 'Insured' : 'Cash Patient'}</div>
        ${patient.insured ? `
          <div><strong>NHIS Member Number:</strong> ${patient.insurance_id || 'N/A'}</div>
          <div><strong>HIN:</strong> ${patient.hin || 'N/A'}</div>
          <div><strong>Insurance Start:</strong> ${formatDate(patient.insurance_start_date)}</div>
          <div><strong>Insurance End:</strong> ${formatDate(patient.insurance_end_date)}</div>
        ` : ''}
      </div>
    </div>
  `;

  // Build encounters HTML
  let encountersHtml = '';
  
  if (encounterData.length === 0) {
    encountersHtml = '<div class="section"><p class="no-data">No encounters found</p></div>';
  } else {
    encounterData.forEach((encounter, idx) => {
      // Build vitals HTML
      let vitalsHtml = '<p class="no-data">No vitals recorded</p>';
      if (encounter.vitals) {
        const v = encounter.vitals;
        vitalsHtml = `
          <div class="two-column">
            ${v.weight ? `<div><strong>Weight:</strong> ${v.weight} kg</div>` : ''}
            ${v.height ? `<div><strong>Height:</strong> ${v.height} cm</div>` : ''}
            ${v.bp_systolic || v.bp_diastolic ? `<div><strong>Blood Pressure:</strong> ${v.bp_systolic || ''}/${v.bp_diastolic || ''} mmHg</div>` : ''}
            ${v.temperature ? `<div><strong>Temperature:</strong> ${v.temperature} °C</div>` : ''}
            ${v.pulse ? `<div><strong>Pulse:</strong> ${v.pulse} bpm</div>` : ''}
            ${v.respiratory_rate ? `<div><strong>Respiratory Rate:</strong> ${v.respiratory_rate} /min</div>` : ''}
            ${v.spo2 ? `<div><strong>SpO2:</strong> ${v.spo2}%</div>` : ''}
            ${v.bmi ? `<div><strong>BMI:</strong> ${v.bmi}</div>` : ''}
          </div>
        `;
      }

      // Build presenting complaints HTML
      let presentingComplaintsHtml = '<p class="no-data">No presenting complaints recorded</p>';
      if (encounter.consultationNotes?.presenting_complaints) {
        presentingComplaintsHtml = `<div style="white-space: pre-wrap;">${encounter.consultationNotes.presenting_complaints}</div>`;
      }
      
      // Build doctor notes HTML
      let doctorNotesHtml = '<p class="no-data">No doctor notes recorded</p>';
      if (encounter.consultationNotes?.doctor_notes) {
        doctorNotesHtml = `<div style="white-space: pre-wrap;">${encounter.consultationNotes.doctor_notes}</div>`;
      }
      
      // Build follow up date HTML
      let followUpDateHtml = '<p class="no-data">No follow-up date set</p>';
      if (encounter.consultationNotes?.follow_up_date) {
        followUpDateHtml = `<div><strong>Follow Up Date:</strong> ${formatDate(encounter.consultationNotes.follow_up_date)}</div>`;
      }
      
      // Build consultation outcome HTML
      let consultationOutcomeHtml = '<p class="no-data">No consultation outcome recorded</p>';
      if (encounter.consultationNotes?.outcome) {
        const outcomeLabels = {
          'discharged': 'Discharged',
          'referred': 'Referred',
          'recommended_for_admission': 'Recommended for Admission'
        };
        const outcomeLabel = outcomeLabels[encounter.consultationNotes.outcome] || encounter.consultationNotes.outcome;
        consultationOutcomeHtml = `<div><strong>Consultation Outcome:</strong> ${outcomeLabel}</div>`;
      }

      // Build diagnoses HTML
      let diagnosesHtml = '<p class="no-data">No diagnoses recorded</p>';
      if (encounter.diagnoses.length > 0) {
        diagnosesHtml = '<ul>';
        encounter.diagnoses.forEach(diag => {
          diagnosesHtml += `<li><strong>${diag.diagnosis || 'N/A'}</strong>${diag.icd10_code ? ` (ICD-10: ${diag.icd10_code})` : ''}</li>`;
        });
        diagnosesHtml += '</ul>';
      }

      // Build prescriptions HTML
      let prescriptionsHtml = '<p class="no-data">No prescriptions</p>';
      if (encounter.prescriptions.length > 0) {
        prescriptionsHtml = '<table class="data-table"><thead><tr><th>#</th><th>Medication</th><th>Dose</th><th>Frequency</th><th>Duration</th><th>Quantity</th><th>Status</th></tr></thead><tbody>';
        encounter.prescriptions.forEach((pres, pidx) => {
          prescriptionsHtml += `
            <tr>
              <td>${pidx + 1}</td>
              <td>${pres.medicine_name || 'N/A'}</td>
              <td>${pres.dose || 'N/A'}</td>
              <td>${pres.frequency || 'N/A'}</td>
              <td>${pres.duration || 'N/A'}</td>
              <td>${pres.quantity || 0}</td>
              <td>${pres.is_dispensed ? 'Dispensed' : pres.is_confirmed ? 'Confirmed' : 'Pending'}</td>
            </tr>
          `;
        });
        prescriptionsHtml += '</tbody></table>';
      }

      // Build investigations HTML
      let investigationsHtml = '<p class="no-data">No investigations</p>';
      if (encounter.investigations.length > 0) {
        investigationsHtml = '<table class="data-table"><thead><tr><th>#</th><th>Type</th><th>Investigation</th><th>Status</th></tr></thead><tbody>';
        encounter.investigations.forEach((inv, invidx) => {
          investigationsHtml += `
            <tr>
              <td>${invidx + 1}</td>
              <td>${inv.investigation_type || 'N/A'}</td>
              <td>${inv.procedure_name || inv.investigation_name || 'N/A'}</td>
              <td>${inv.is_confirmed ? 'Confirmed' : 'Pending'}</td>
            </tr>
          `;
        });
        investigationsHtml += '</tbody></table>';

        // Add results if available
        if (encounter.labResults.length > 0 || encounter.scanResults.length > 0 || encounter.xrayResults.length > 0) {
          investigationsHtml += '<h4 class="subsection-title">Investigation Results</h4>';
          
          encounter.labResults.forEach(lab => {
            investigationsHtml += `<div class="result-section"><strong>Lab Result:</strong><pre>${lab.result?.result || 'N/A'}</pre></div>`;
          });
          
          encounter.scanResults.forEach(scan => {
            investigationsHtml += `<div class="result-section"><strong>Scan Result:</strong><pre>${scan.result?.result || 'N/A'}</pre></div>`;
          });
          
          encounter.xrayResults.forEach(xray => {
            investigationsHtml += `<div class="result-section"><strong>X-ray Result:</strong><pre>${xray.result?.result || 'N/A'}</pre></div>`;
          });
        }
      }

      // Build bills HTML
      let billsHtml = '<p class="no-data">No bills</p>';
      if (encounter.bills.length > 0) {
        const encounterTotal = encounter.bills.reduce((sum, b) => sum + (b.total_amount || 0), 0);
        const encounterPaid = encounter.bills.reduce((sum, b) => sum + (b.paid_amount || 0), 0);
        const encounterBalance = encounterTotal - encounterPaid;
        
        billsHtml = `
          <table class="data-table"><thead><tr><th>Bill ID</th><th>Total Amount</th><th>Paid Amount</th><th>Balance</th></tr></thead><tbody>
          ${encounter.bills.map(bill => `
            <tr>
              <td>${bill.id}</td>
              <td>₵${(bill.total_amount || 0).toFixed(2)}</td>
              <td>₵${(bill.paid_amount || 0).toFixed(2)}</td>
              <td>₵${((bill.total_amount || 0) - (bill.paid_amount || 0)).toFixed(2)}</td>
            </tr>
          `).join('')}
          </tbody></table>
          <div class="bill-summary">
            <strong>Encounter Total:</strong> ₵${encounterTotal.toFixed(2)} | 
            <strong>Paid:</strong> ₵${encounterPaid.toFixed(2)} | 
            <strong>Balance:</strong> ₵${encounterBalance.toFixed(2)}
          </div>
        `;
      }

      encountersHtml += `
        <div class="encounter-section">
          <h3 class="encounter-title">ENCOUNTER #${encounter.id} - ${encounter.department || 'N/A'}</h3>
          <div class="encounter-meta">
            <strong>Date:</strong> ${formatDateTime(encounter.created_at)} | 
            <strong>Status:</strong> ${encounter.status || 'N/A'} | 
            ${encounter.ccc_number ? `<strong>CCC Number:</strong> ${encounter.ccc_number}` : ''}
          </div>
          
          <h4 class="subsection-title">Vitals</h4>
          ${vitalsHtml}
          
          <h4 class="subsection-title">Presenting Complaints</h4>
          ${presentingComplaintsHtml}
          
          <h4 class="subsection-title">Diagnoses</h4>
          ${diagnosesHtml}
          
          <h4 class="subsection-title">Prescriptions</h4>
          ${prescriptionsHtml}
          
          <h4 class="subsection-title">Investigations</h4>
          ${investigationsHtml}
          
          <h4 class="subsection-title">Doctor Note</h4>
          ${doctorNotesHtml}
          
          <h4 class="subsection-title">Follow Up Date</h4>
          ${followUpDateHtml}
          
          <h4 class="subsection-title">Consultation Outcome</h4>
          ${consultationOutcomeHtml}
          
          <h4 class="subsection-title">Billing</h4>
          ${billsHtml}
        </div>
      `;
    });
  }

  return `<!doctype html>
  <html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Patient Electronic Records - ${patient.card_number || patient.name}</title>
    <style>
      @page { size: A4; margin: 20mm; }
      * { margin: 0; padding: 0; box-sizing: border-box; }
      body { font-family: 'Arial', sans-serif; font-size: 11px; line-height: 1.6; color: #333; }
      
      .header { text-align: center; border-bottom: 3px solid #000; padding-bottom: 15px; margin-bottom: 20px; }
      .logo-container { display: flex; justify-content: center; align-items: center; gap: 20px; margin-bottom: 10px; }
      .logo { max-width: 80px; max-height: 80px; object-fit: contain; }
      .hospital-name { font-size: 18px; font-weight: bold; margin: 10px 0; }
      .document-title { font-size: 16px; font-weight: bold; text-transform: uppercase; }
      
      .section { margin-bottom: 25px; page-break-inside: avoid; }
      .section-title { font-size: 14px; font-weight: bold; text-transform: uppercase; border-bottom: 2px solid #333; padding-bottom: 5px; margin-bottom: 10px; }
      .subsection-title { font-size: 12px; font-weight: bold; margin-top: 15px; margin-bottom: 8px; color: #555; }
      
      .two-column { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
      
      .encounter-section { margin-bottom: 30px; padding: 15px; border: 1px solid #ddd; page-break-inside: avoid; }
      .encounter-title { font-size: 14px; font-weight: bold; color: #000; margin-bottom: 8px; }
      .encounter-meta { font-size: 10px; color: #666; margin-bottom: 15px; padding-bottom: 10px; border-bottom: 1px dashed #ccc; }
      
      table.data-table { width: 100%; border-collapse: collapse; margin: 10px 0; font-size: 10px; }
      table.data-table th, table.data-table td { border: 1px solid #ddd; padding: 6px; text-align: left; }
      table.data-table th { background-color: #f5f5f5; font-weight: bold; }
      
      ul { margin-left: 20px; }
      li { margin-bottom: 5px; }
      
      .no-data { color: #999; font-style: italic; }
      
      .result-section { margin: 10px 0; padding: 10px; background-color: #f9f9f9; border-left: 3px solid #333; }
      .result-section pre { white-space: pre-wrap; margin-top: 5px; }
      
      .bill-summary { margin-top: 10px; padding: 10px; background-color: #f0f0f0; font-weight: bold; }
      
      .review-section { margin: 10px 0; padding: 10px; background-color: #f9f9f9; border-left: 3px solid #0066cc; }
      .review-section h5 { margin-bottom: 5px; color: #0066cc; }
      
      @media print {
        .encounter-section { page-break-inside: avoid; }
        .section { page-break-inside: avoid; }
      }
    </style>
  </head>
  <body>
    <div class="header">
      <div class="logo-container">
        <img src="/logos/ministry-of-health-logo.png" alt="Ministry of Health" class="logo" onerror="this.style.display='none'">
        <img src="/logos/ghana-health-service-logo.png" alt="Ghana Health Service" class="logo" onerror="this.style.display='none'">
      </div>
      <div class="hospital-name">GHANA HEALTH SERVICE</div>
      <div class="hospital-name">${(facilityStore.displayName || '').replace(/</g, '&lt;').replace(/>/g, '&gt;')}</div>
      <div class="document-title">PATIENT ELECTRONIC RECORDS</div>
      <div style="margin-top: 10px; font-size: 10px;">Generated: ${now.toLocaleString('en-GB')}</div>
    </div>

    ${biostatsHtml}
    
    <div class="section">
      <h3 class="section-title">PATIENT ENCOUNTERS (OPD)</h3>
      ${encountersHtml}
    </div>
    
    ${ipdData.length > 0 ? `
    <div class="section">
      <h3 class="section-title">INPATIENT DEPARTMENT (IPD) ADMISSIONS</h3>
      ${ipdData.map((admission, idx) => {
        // Build admission details HTML
        const admissionDetailsHtml = `
          <div class="two-column">
            <div><strong>Ward:</strong> ${admission.ward || 'N/A'}</div>
            <div><strong>Bed:</strong> ${admission.bed_number || 'N/A'}</div>
            <div><strong>Admitted:</strong> ${formatDateTime(admission.admitted_at)}</div>
            <div><strong>Discharged:</strong> ${admission.discharged_at ? formatDateTime(admission.discharged_at) : 'Not discharged'}</div>
            ${admission.doctor_name ? `<div><strong>Doctor:</strong> ${admission.doctor_name}</div>` : ''}
            ${admission.discharge_outcome ? `<div><strong>Discharge Outcome:</strong> ${admission.discharge_outcome}</div>` : ''}
            ${admission.discharge_condition ? `<div><strong>Discharge Condition:</strong> ${admission.discharge_condition}</div>` : ''}
            ${admission.final_orders ? `<div><strong>Final Orders:</strong> ${admission.final_orders}</div>` : ''}
          </div>
        `;

        // Build clinical reviews HTML
        let clinicalReviewsHtml = '<p class="no-data">No clinical reviews</p>';
        if (admission.clinicalReviews && admission.clinicalReviews.length > 0) {
          clinicalReviewsHtml = '';
          admission.clinicalReviews.forEach((review, ridx) => {
            clinicalReviewsHtml += `
              <div class="review-section">
                <h5><strong>Clinical Review #${ridx + 1}</strong> - ${formatDateTime(review.created_at)}</h5>
                ${review.review_notes ? `<div style="white-space: pre-wrap; margin-top: 5px;">${review.review_notes}</div>` : '<p class="no-data">No notes</p>'}
              </div>
            `;
          });
        }

        // Build diagnoses HTML
        let diagnosesHtml = '<p class="no-data">No diagnoses recorded</p>';
        if (admission.diagnoses && admission.diagnoses.length > 0) {
          diagnosesHtml = '<ul>';
          admission.diagnoses.forEach(diag => {
            diagnosesHtml += `<li><strong>${diag.diagnosis || 'N/A'}</strong>${diag.icd10 ? ` (ICD-10: ${diag.icd10})` : ''}${diag.gdrg_code ? ` (GDRG: ${diag.gdrg_code})` : ''}${diag.is_chief ? ' <strong>[Chief]</strong>' : ''}</li>`;
          });
          diagnosesHtml += '</ul>';
        }

        // Build prescriptions HTML
        let prescriptionsHtml = '<p class="no-data">No prescriptions</p>';
        if (admission.prescriptions && admission.prescriptions.length > 0) {
          prescriptionsHtml = '<table class="data-table"><thead><tr><th>#</th><th>Medication</th><th>Dose</th><th>Frequency</th><th>Duration</th><th>Quantity</th><th>Status</th></tr></thead><tbody>';
          admission.prescriptions.forEach((pres, pidx) => {
            prescriptionsHtml += `
              <tr>
                <td>${pidx + 1}</td>
                <td>${pres.medicine_name || 'N/A'}</td>
                <td>${pres.dose || 'N/A'}</td>
                <td>${pres.frequency || 'N/A'}</td>
                <td>${pres.duration || 'N/A'}</td>
                <td>${pres.quantity || 0}</td>
                <td>${pres.dispensed_by ? 'Dispensed' : 'Pending'}</td>
              </tr>
            `;
          });
          prescriptionsHtml += '</tbody></table>';
        }

        // Build investigations HTML
        let investigationsHtml = '<p class="no-data">No investigations</p>';
        if (admission.investigations && admission.investigations.length > 0) {
          investigationsHtml = '<table class="data-table"><thead><tr><th>#</th><th>Type</th><th>Investigation</th><th>Status</th></tr></thead><tbody>';
          admission.investigations.forEach((inv, invidx) => {
            investigationsHtml += `
              <tr>
                <td>${invidx + 1}</td>
                <td>${inv.investigation_type || 'N/A'}</td>
                <td>${inv.procedure_name || 'N/A'}</td>
                <td>${inv.status || 'Pending'}</td>
              </tr>
            `;
          });
          investigationsHtml += '</tbody></table>';
        }

        // Build surgeries HTML
        let surgeriesHtml = '<p class="no-data">No surgeries recorded</p>';
        if (admission.surgeries && admission.surgeries.length > 0) {
          surgeriesHtml = '<table class="data-table"><thead><tr><th>#</th><th>Surgery Name</th><th>Type</th><th>Surgeon</th><th>Date</th><th>Status</th></tr></thead><tbody>';
          admission.surgeries.forEach((surgery, sidx) => {
            surgeriesHtml += `
              <tr>
                <td>${sidx + 1}</td>
                <td>${surgery.surgery_name || 'N/A'}</td>
                <td>${surgery.surgery_type || 'N/A'}</td>
                <td>${surgery.surgeon_name || 'N/A'}</td>
                <td>${surgery.surgery_date ? formatDate(surgery.surgery_date) : 'N/A'}</td>
                <td>${surgery.is_completed ? 'Completed' : 'Pending'}</td>
              </tr>
            `;
          });
          surgeriesHtml += '</tbody></table>';
        }

        // Build bills HTML
        let billsHtml = '<p class="no-data">No bills</p>';
        if (admission.bills && admission.bills.length > 0) {
          const ipdTotal = admission.bills.reduce((sum, b) => sum + (b.total_amount || 0), 0);
          const ipdPaid = admission.bills.reduce((sum, b) => sum + (b.paid_amount || 0), 0);
          const ipdBalance = ipdTotal - ipdPaid;
          
          billsHtml = `
            <table class="data-table"><thead><tr><th>Bill ID</th><th>Total Amount</th><th>Paid Amount</th><th>Balance</th></tr></thead><tbody>
            ${admission.bills.map(bill => `
              <tr>
                <td>${bill.id}</td>
                <td>₵${(bill.total_amount || 0).toFixed(2)}</td>
                <td>₵${(bill.paid_amount || 0).toFixed(2)}</td>
                <td>₵${((bill.total_amount || 0) - (bill.paid_amount || 0)).toFixed(2)}</td>
              </tr>
            `).join('')}
            </tbody></table>
            <div class="bill-summary">
              <strong>IPD Total:</strong> ₵${ipdTotal.toFixed(2)} | 
              <strong>Paid:</strong> ₵${ipdPaid.toFixed(2)} | 
              <strong>Balance:</strong> ₵${ipdBalance.toFixed(2)}
            </div>
          `;
        }

        return `
          <div class="encounter-section">
            <h3 class="encounter-title">IPD ADMISSION #${admission.id} - ${admission.ward || 'N/A'}</h3>
            <div class="encounter-meta">
              <strong>Admitted:</strong> ${formatDateTime(admission.admitted_at)} | 
              <strong>Discharged:</strong> ${admission.discharged_at ? formatDateTime(admission.discharged_at) : 'Not discharged'}
              ${admission.ccc_number ? ` | <strong>CCC Number:</strong> ${admission.ccc_number}` : ''}
            </div>
            
            <h4 class="subsection-title">Admission Details</h4>
            ${admissionDetailsHtml}
            ${admission.admission_notes ? `
              <div style="margin-top: 10px; padding: 10px; background-color: #f9f9f9; border-left: 3px solid #0066cc;">
                <strong>Admission Notes:</strong>
                <div style="white-space: pre-wrap; margin-top: 5px;">${admission.admission_notes}</div>
              </div>
            ` : ''}
            
            <h4 class="subsection-title">Nurse Notes</h4>
            ${(() => {
              let nurseNotesHtml = '<p class="no-data">No nurse notes</p>';
              if (admission.nurseNotes && admission.nurseNotes.length > 0) {
                nurseNotesHtml = '';
                admission.nurseNotes.forEach((note, nidx) => {
                  nurseNotesHtml += `
                    <div class="review-section" style="${note.strikethrough ? 'opacity: 0.6; text-decoration: line-through;' : ''}">
                      <h5><strong>Note #${nidx + 1}</strong> - ${formatDateTime(note.created_at)}${note.created_by_name ? ` by ${note.created_by_name}` : ''}</h5>
                      <div style="white-space: pre-wrap; margin-top: 5px;">${note.notes || 'No content'}</div>
                    </div>
                  `;
                });
              }
              return nurseNotesHtml;
            })()}
            
            <h4 class="subsection-title">Nurse/Mid Documentation</h4>
            ${(() => {
              let nurseMidDocsHtml = '<p class="no-data">No nurse/mid documentation</p>';
              if (admission.nurseMidDocumentations && admission.nurseMidDocumentations.length > 0) {
                nurseMidDocsHtml = '<table class="data-table"><thead><tr><th>#</th><th>Type</th><th>Date</th><th>Details</th></tr></thead><tbody>';
                admission.nurseMidDocumentations.forEach((doc, didx) => {
                  nurseMidDocsHtml += `
                    <tr>
                      <td>${didx + 1}</td>
                      <td>${doc.documentation_type || 'N/A'}</td>
                      <td>${formatDateTime(doc.created_at)}</td>
                      <td>${doc.details ? (doc.details.length > 100 ? doc.details.substring(0, 100) + '...' : doc.details) : 'N/A'}</td>
                    </tr>
                  `;
                });
                nurseMidDocsHtml += '</tbody></table>';
              }
              return nurseMidDocsHtml;
            })()}
            
            <h4 class="subsection-title">Additional Services</h4>
            ${(() => {
              let additionalServicesHtml = '<p class="no-data">No additional services</p>';
              if (admission.additionalServices && admission.additionalServices.length > 0) {
                additionalServicesHtml = '<table class="data-table"><thead><tr><th>#</th><th>Service Name</th><th>Started</th><th>Stopped</th><th>Status</th></tr></thead><tbody>';
                admission.additionalServices.forEach((service, sidx) => {
                  additionalServicesHtml += `
                    <tr>
                      <td>${sidx + 1}</td>
                      <td>${service.service_name || 'N/A'}</td>
                      <td>${service.started_at ? formatDateTime(service.started_at) : 'N/A'}</td>
                      <td>${service.stopped_at ? formatDateTime(service.stopped_at) : 'Active'}</td>
                      <td>${service.stopped_at ? 'Stopped' : 'Active'}</td>
                    </tr>
                  `;
                });
                additionalServicesHtml += '</tbody></table>';
              }
              return additionalServicesHtml;
            })()}
            
            <h4 class="subsection-title">Clinical Reviews</h4>
            ${clinicalReviewsHtml}
            
            <h4 class="subsection-title">Diagnoses</h4>
            ${diagnosesHtml}
            
            <h4 class="subsection-title">Prescriptions</h4>
            ${prescriptionsHtml}
            
            <h4 class="subsection-title">Investigations</h4>
            ${investigationsHtml}
            
            <h4 class="subsection-title">Surgeries</h4>
            ${surgeriesHtml}
            
            <h4 class="subsection-title">Billing</h4>
            ${billsHtml}
          </div>
        `;
      }).join('')}
    </div>
    ` : ''}
    
    <div style="margin-top: 40px; text-align: center; font-size: 10px; color: #666; border-top: 1px solid #ddd; padding-top: 15px;">
      <p>This document contains the complete electronic health records for the patient.</p>
      <p>Generated on ${now.toLocaleString('en-GB')}</p>
      <p>Generated by ${authStore.user?.name || 'System'}</p>
      <p>Made with ❤️ by IT Unit @ ${(facilityStore.displayName || '').replace(/</g, '&lt;').replace(/>/g, '&gt;')}</p>
    </div>

   
  </body>
  </html>`;
};

onMounted(async () => {
  try {
    const config = await patientsStore.fetchRegistrationConfig();
    ghimsCardMode.value = !!config?.ghims_card_mode;
  } catch {
    ghimsCardMode.value = false;
  }
  loadPatient();
  loadServiceTypes();
});
</script>

<style scoped>
.profile-stack { display:flex; flex-direction:column; gap:1.15rem; }
.profile-loading { padding:1.25rem; border-radius:var(--hms-radius-xl); background:var(--hms-panel-bg); border:1px solid var(--hms-border); }
.loading-label { margin-top:0.85rem; color:var(--hms-text-secondary); font-size:var(--hms-text-sm); }
.patient-hero { position:sticky; top:0.65rem; z-index:5; display:flex; flex-wrap:wrap; align-items:center; justify-content:space-between; gap:0.85rem; padding:1.05rem 1.2rem; border-radius:var(--hms-radius-xl); background:var(--hms-glass-bg-strong); border:1px solid var(--hms-border-strong); box-shadow:var(--hms-shadow-lg), var(--hms-shadow-inner); backdrop-filter:blur(18px); }
.hero-main { display:flex; align-items:center; gap:0.85rem; min-width:0; }
.hero-avatar { width:3.25rem; height:3.25rem; border-radius:9999px; background:linear-gradient(145deg, var(--hms-accent-muted), rgba(6, 182, 212, 0.18)); color:var(--hms-accent); display:inline-flex; align-items:center; justify-content:center; font-weight:750; font-size:var(--hms-text-base); flex-shrink:0; }
.hero-name-row { display:flex; flex-wrap:wrap; align-items:center; gap:0.45rem; }
.hero-name { font-size:var(--hms-text-2xl); font-weight:750; letter-spacing:var(--hms-tracking-tight); color:var(--hms-text-primary); margin:0; line-height:1.2; }
.hero-meta { margin-top:0.4rem; display:flex; flex-wrap:wrap; align-items:center; gap:0.25rem 0.15rem; color:var(--hms-text-secondary); font-size:var(--hms-text-sm); }
.meta-sep { color:var(--hms-text-muted); margin:0 0.2rem; }
.meta-chip { font-weight:650; }
.hero-actions { display:flex; flex-wrap:wrap; gap:0.45rem; }
.profile-panel { padding:1.25rem 1.35rem; }
.panel-head { display:flex; flex-wrap:wrap; align-items:center; justify-content:space-between; gap:0.75rem; margin-bottom:1.15rem; }
.panel-head .hms-section-title {
  font-size: var(--hms-text-lg);
  font-weight: 700;
  letter-spacing: var(--hms-tracking-tight);
  line-height: 1.3;
}
.demo-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:1rem 1.15rem; }
.demo-item .accent { color:var(--hms-accent); }
.panel-divider { height:1px; background:var(--hms-border); margin:1.15rem 0; }
.info-columns { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:1.4rem; }
.info-line { display:grid; grid-template-columns:7.5rem 1fr; gap:0.5rem; align-items:baseline; padding:0.32rem 0; font-size:var(--hms-text-sm); }
.info-line span { color:var(--hms-text-muted); font-weight:600; }
.info-line strong { color:var(--hms-text-primary); font-weight:650; }
.balance-pill { display:inline-flex; align-items:center; gap:0.55rem; padding:0.45rem 0.75rem; border-radius:var(--hms-radius-lg); border:1px solid var(--hms-border); background:var(--hms-surface); cursor:pointer; font-family:inherit; }
.balance-pill:hover { border-color:var(--hms-border-strong); background:var(--hms-surface-hover); }
.balance-label { font-size:0.68rem; font-weight:700; letter-spacing:0.04em; text-transform:uppercase; color:var(--hms-text-muted); }
.balance-value { font-size:var(--hms-text-lg); font-weight:750; font-variant-numeric:tabular-nums; }
.balance-hint { font-size:var(--hms-text-xs); color:var(--hms-accent); font-weight:650; }
.balance-pill.due .balance-value { color:var(--hms-critical); }
.balance-pill.ok .balance-value { color:var(--hms-success); }
.balance-pill.neutral .balance-value { color:var(--hms-text-primary); }
.bill-list { display:flex; flex-direction:column; gap:0.45rem; }
.bill-row { display:grid; grid-template-columns:auto 1fr auto; gap:0.75rem; align-items:center; width:100%; padding:0.7rem 0.75rem; border-radius:var(--hms-radius-lg); border:1px solid var(--hms-border); background:var(--hms-surface); text-align:left; cursor:pointer; font-family:inherit; color:inherit; }
.bill-row:hover { background:var(--hms-surface-hover); border-color:var(--hms-border-strong); }
.bill-icon { width:2rem; height:2rem; border-radius:var(--hms-radius-md); display:inline-flex; align-items:center; justify-content:center; }
.bill-icon.due { background:var(--hms-critical-muted); color:var(--hms-critical); }
.bill-icon.ok { background:var(--hms-success-muted); color:var(--hms-success); }
.bill-title { font-weight:700; font-size:var(--hms-text-sm); color:var(--hms-text-primary); }
.bill-sub { margin-top:0.1rem; font-size:var(--hms-text-xs); color:var(--hms-text-muted); }
.bill-amount { font-weight:750; font-variant-numeric:tabular-nums; }
.bill-amount.due { color:var(--hms-critical); }
.bill-amount.ok { color:var(--hms-success); }
.panel-empty { padding:0.85rem 0.25rem; }
.panel-empty.muted { text-align:center; color:var(--hms-text-muted); font-size:var(--hms-text-sm); padding:1.25rem 0.5rem; }
.mono { font-family:var(--hms-font-mono); font-size:0.8em; letter-spacing:0.01em; }
.ipd-list { display:flex; flex-direction:column; gap:0.55rem; }
.ipd-row { display:flex; flex-wrap:wrap; align-items:center; justify-content:space-between; gap:0.75rem; padding:0.75rem 0.85rem; border-radius:var(--hms-radius-lg); border:1px solid var(--hms-border); background:var(--hms-surface); }
.ipd-title { display:flex; flex-wrap:wrap; align-items:center; gap:0.35rem; font-weight:700; color:var(--hms-text-primary); }
.ipd-meta { margin-top:0.25rem; font-size:var(--hms-text-xs); color:var(--hms-text-muted); }
.encounters-panel :deep(.profile-q-table) { border:1px solid var(--hms-border); border-radius:var(--hms-radius-lg); overflow:hidden; background:var(--hms-surface) !important; }
.encounters-panel :deep(.q-table th) { font-size:0.68rem; letter-spacing:0.04em; text-transform:uppercase; color:var(--hms-text-muted); font-weight:700; }
.encounters-panel :deep(.q-table tbody td) { font-size:var(--hms-text-sm); }
.encounter-actions { display:flex; flex-wrap:wrap; gap:0.35rem; max-width:28rem; }
.not-found { padding:1.5rem; }
@media (max-width:960px){ .demo-grid,.info-columns{ grid-template-columns:1fr 1fr; } }
@media (max-width:720px){
  .patient-hero{ position:static; flex-direction:column; align-items:stretch; }
  .hero-actions{ width:100%; }
  .hero-actions :deep(.hms-btn){ flex:1; }
  .demo-grid,.info-columns{ grid-template-columns:1fr; }
  .info-line{ grid-template-columns:1fr; gap:0.1rem; }
  .panel-head{ flex-direction:column; align-items:stretch; }
  .balance-pill{ width:100%; justify-content:space-between; }
}
</style>

