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
        Admission Recommendations
      </div>
    </div>

    <!-- Tabs for filtering by status -->
    <q-tabs v-model="activeTab" class="text-primary q-mb-md" align="left">
      <q-tab name="pending" label="Pending" icon="schedule" />
      <q-tab name="confirmed" label="Confirmed Admissions" icon="check_circle" />
      <q-tab name="rejected" label="Rejected/Cancelled" icon="cancel" />
    </q-tabs>

    <!-- Loading State -->
    <q-card v-if="loading" class="glass-card" flat>
      <q-card-section class="text-center">
        <q-spinner color="primary" size="3em" />
        <div class="text-subtitle1 q-mt-md glass-text">Loading admission recommendations...</div>
      </q-card-section>
    </q-card>

    <!-- Empty State -->
    <q-card v-else-if="!loading && filteredAdmissions.length === 0" class="glass-card" flat>
      <q-card-section class="text-center">
        <q-icon name="local_hospital" size="64px" color="grey-6" />
        <div class="text-subtitle1 q-mt-md glass-text">
          <span v-if="activeTab === 'pending'">No pending admission recommendations</span>
          <span v-else-if="activeTab === 'confirmed'">No confirmed admissions</span>
          <span v-else-if="activeTab === 'rejected'">No rejected or cancelled admissions</span>
        </div>
      </q-card-section>
    </q-card>

    <!-- Admissions Table -->
    <q-card v-else class="glass-card" flat>
      <q-card-section>
        <div class="row items-center q-mb-md">
          <div class="text-h6 glass-text">
            <span v-if="activeTab === 'pending'">Pending Admission Recommendations</span>
            <span v-else-if="activeTab === 'confirmed'">Confirmed Admissions</span>
            <span v-else-if="activeTab === 'rejected'">Rejected/Cancelled Admissions</span>
            <span v-if="selectedWard"> ({{ filteredAdmissions.length }} in {{ selectedWard }})</span>
            <span v-else> ({{ filteredAdmissions.length }} total)</span>
          </div>
          <q-space />
          <q-btn
            flat
            icon="refresh"
            label="Refresh"
            @click="loadAdmissions"
            class="glass-button"
          />
        </div>

        <q-table
          :rows="filteredAdmissions"
          :columns="columns"
          row-key="id"
          flat
          :loading="loading"
          :filter="filter"
          :pagination="{ rowsPerPage: 10 }"
          class="glass-table"
        >
          <template v-slot:top>
            <div class="row q-col-gutter-md q-mb-md" style="width: 100%;">
              <div class="col-12 col-md-4">
                <q-select
                  v-model="selectedWard"
                  :options="wardOptions"
                  filled
                  dense
                  label="Filter by Ward"
                  clearable
                  emit-value
                  map-options
                  @update:model-value="onWardFilterChange"
                >
                  <template v-slot:prepend>
                    <q-icon name="local_hospital" />
                  </template>
                </q-select>
              </div>
              <div class="col-12 col-md-4">
                <q-input
                  v-model="filter"
                  filled
                  dense
                  placeholder="Search by card number..."
                  @update:model-value="onSearchChange"
                >
                  <template v-slot:append>
                    <q-icon name="search" />
                  </template>
                </q-input>
              </div>
              <div class="col-12 col-md-4 flex items-center">
                <q-badge v-if="selectedWard" color="primary" :label="`Ward: ${selectedWard}`" class="q-mr-sm" />
                <q-badge color="info" :label="`Showing: ${filteredAdmissions.length} of ${allAdmissions.length}`" />
              </div>
            </div>
          </template>

          <template v-slot:body-cell-patient="props">
            <q-td :props="props">
              <div>
                <div class="text-weight-medium glass-text">
                  {{ props.row.patient_name }} {{ props.row.patient_surname }}
                  <span v-if="props.row.patient_other_names">
                    {{ props.row.patient_other_names }}
                  </span>
                </div>
                <div class="text-caption text-secondary">
                  Card: {{ props.row.patient_card_number }}
                </div>
                <div class="text-caption text-secondary">
                  {{ props.row.patient_gender }} | 
                  <span v-if="props.row.patient_date_of_birth">
                    DOB: {{ formatDate(props.row.patient_date_of_birth) }}
                  </span>
                </div>
              </div>
            </q-td>
          </template>

          <template v-slot:body-cell-ward="props">
            <q-td :props="props">
              <q-badge color="primary" :label="props.value" />
            </q-td>
          </template>

          <template v-slot:body-cell-date="props">
            <q-td :props="props">
              <div class="glass-text">{{ formatDateTime(props.value) }}</div>
              <div v-if="props.row.finalized_by_name" class="text-caption text-secondary q-mt-xs">
                Finalized by: <strong>{{ props.row.finalized_by_name }}</strong>
                <span v-if="props.row.finalized_by_role"> ({{ props.row.finalized_by_role }})</span>
              </div>
            </q-td>
          </template>

          <template v-slot:body-cell-actions="props">
            <q-td :props="props">
              <div class="row q-gutter-xs">
                <q-btn
                  flat
                  dense
                  icon="visibility"
                  label="View Patient"
                  color="primary"
                  size="sm"
                  @click="viewPatient(props.row.patient_card_number)"
                />
                <q-btn
                  flat
                  dense
                  icon="medical_services"
                  label="View Encounter"
                  color="secondary"
                  size="sm"
                  @click="viewEncounter(props.row.encounter_id)"
                />
                <template v-if="props.row.cancelled === 1">
                  <q-chip
                    color="negative"
                    text-color="white"
                    icon="cancel"
                    size="sm"
                  >
                    Cancelled
                  </q-chip>
                  <q-btn
                    flat
                    dense
                    icon="info"
                    label="View Reason"
                    color="info"
                    size="sm"
                    @click="showCancellationReason(props.row)"
                  />
                </template>
                <template v-else-if="!props.row.confirmed_by">
                  <!-- Confirm Admission button - Available to all staff (Nurse, Doctor, PA, Admin) -->
                  <q-btn
                    flat
                    dense
                    icon="check_circle"
                    label="Confirm Admission"
                    color="positive"
                    size="sm"
                    @click="confirmAdmission(props.row)"
                    :loading="confirmingId === props.row.id"
                  />
                  <q-btn
                    flat
                    dense
                    icon="cancel"
                    label="Cancel"
                    color="negative"
                    size="sm"
                    @click="cancelAdmission(props.row)"
                    :loading="cancellingId === props.row.id"
                  />
                </template>
                <template v-else>
                  <q-chip
                    color="positive"
                    text-color="white"
                    icon="check_circle"
                    size="sm"
                  >
                    Confirmed
                  </q-chip>
                  <q-btn
                    v-if="isAdmin"
                    flat
                    dense
                    icon="undo"
                    label="Revert"
                    color="warning"
                    size="sm"
                    @click="revertConfirmation(props.row)"
                    :loading="revertingId === props.row.id"
                  />
                  <q-btn
                    v-if="isAdmin"
                    flat
                    dense
                    icon="cancel"
                    label="Cancel"
                    color="negative"
                    size="sm"
                    @click="cancelAdmission(props.row)"
                    :loading="cancellingId === props.row.id"
                  />
                </template>
              </div>
            </q-td>
          </template>
        </q-table>
      </q-card-section>
    </q-card>

    <!-- Confirm Admission Dialog - Multi-step Form -->
    <q-dialog v-model="showConfirmDialog" persistent maximized>
      <q-card style="min-width: 800px; max-width: 1000px;">
        <q-card-section class="row items-center q-pb-none">
          <div class="text-h6 glass-text">
            Confirm Admission - {{ selectedAdmissionForConfirm?.patient_name }} {{ selectedAdmissionForConfirm?.patient_surname }}
          </div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>

        <q-card-section>
          <div v-if="loadingPatientInsurance" class="text-center q-pa-lg">
            <q-spinner color="primary" size="3em" />
            <div class="text-subtitle1 q-mt-md glass-text">Loading patient insurance information...</div>
          </div>
          
          <template v-else>
            <q-tabs v-model="currentTab" class="text-primary" align="left">
              <q-tab name="patient-info" label="Patient Info" icon="person" />
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
                v-if="selectedAdmissionForConfirm && (selectedAdmissionForConfirm.patient_insured || selectedAdmissionForConfirm.patient_insurance_id)"
                :class="getInsuranceCardClass(selectedAdmissionForConfirm)"
                flat 
                bordered
                class="q-mb-lg insurance-info-card"
                style="border-width: 3px !important;"
              >
                <q-card-section class="q-pa-lg">
                  <div class="row items-center q-mb-md">
                    <q-icon 
                      :name="selectedAdmissionForConfirm.patient_insured ? 'verified_user' : 'warning'" 
                      :color="selectedAdmissionForConfirm.patient_insured ? 'positive' : 'negative'"
                      size="48px" 
                      class="q-mr-md"
                    />
                    <div class="col">
                      <div class="text-h5 text-weight-bold" :class="selectedAdmissionForConfirm.patient_insured ? 'text-positive' : 'text-negative'">
                        <q-icon name="health_and_safety" size="32px" class="q-mr-sm" />
                        {{ selectedAdmissionForConfirm.patient_insured ? 'INSURED PATIENT' : 'INSURANCE INFORMATION' }}
                      </div>
                      <div class="text-subtitle1 q-mt-xs" :class="selectedAdmissionForConfirm.patient_insured ? 'text-positive' : 'text-grey-7'">
                        {{ selectedAdmissionForConfirm.patient_insured ? 'Active Insurance Coverage' : 'Insurance Status: Not Active' }}
                      </div>
                    </div>
                  </div>
                  
                  <q-separator class="q-mb-md" />
                  
                  <div class="row q-col-gutter-lg">
                    <div class="col-12 col-md-4">
                      <div class="text-subtitle2 text-weight-bold q-mb-xs" :class="selectedAdmissionForConfirm.patient_insured ? 'text-positive' : 'text-grey-7'">
                        <q-icon name="badge" size="20px" class="q-mr-xs" />
                        Insurance Number
                      </div>
                      <div class="text-h6 text-weight-bold glass-text" style="word-break: break-all;">
                        {{ selectedAdmissionForConfirm.patient_insurance_id || 'N/A' }}
                      </div>
                    </div>
                    <div class="col-12 col-md-4">
                      <div class="text-subtitle2 text-weight-bold q-mb-xs" :class="selectedAdmissionForConfirm.patient_insured ? 'text-positive' : 'text-grey-7'">
                        <q-icon name="event" size="20px" class="q-mr-xs" />
                        Start Date
                      </div>
                      <div class="text-h6 text-weight-bold glass-text">
                        {{ selectedAdmissionForConfirm.patient_insurance_start_date ? formatDate(selectedAdmissionForConfirm.patient_insurance_start_date) : 'N/A' }}
                      </div>
                    </div>
                    <div class="col-12 col-md-4">
                      <div class="text-subtitle2 text-weight-bold q-mb-xs" :class="getEndDateClass(selectedAdmissionForConfirm)">
                        <q-icon name="event_available" size="20px" class="q-mr-xs" />
                        End Date
                      </div>
                      <div class="text-h6 text-weight-bold" :class="getEndDateTextClass(selectedAdmissionForConfirm)">
                        {{ selectedAdmissionForConfirm.patient_insurance_end_date ? formatDate(selectedAdmissionForConfirm.patient_insurance_end_date) : 'N/A' }}
                        <q-icon 
                          v-if="isInsuranceExpired(selectedAdmissionForConfirm)" 
                          name="error" 
                          color="negative" 
                          size="24px" 
                          class="q-ml-sm"
                        />
                      </div>
                      <div v-if="isInsuranceExpired(selectedAdmissionForConfirm)" class="text-negative text-weight-bold q-mt-xs">
                        <q-icon name="warning" size="16px" class="q-mr-xs" />
                        EXPIRED - Cash and Carry
                      </div>
                      <div v-else-if="isInsuranceExpiringSoon(selectedAdmissionForConfirm)" class="text-warning text-weight-bold q-mt-xs">
                        <q-icon name="schedule" size="16px" class="q-mr-xs" />
                        Expiring Soon
                      </div>
                    </div>
                  </div>
                  
                  <q-banner 
                    v-if="selectedAdmissionForConfirm.patient_insured && !isInsuranceExpired(selectedAdmissionForConfirm)"
                    class="q-mt-md"
                    :class="selectedAdmissionForConfirm.patient_insured ? 'bg-positive' : 'bg-negative'"
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
                v-if="selectedAdmissionForConfirm && !selectedAdmissionForConfirm.patient_insured && !selectedAdmissionForConfirm.patient_insurance_id"
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
                          <strong>{{ selectedAdmissionForConfirm?.patient_name }} {{ selectedAdmissionForConfirm?.patient_surname }}</strong>
                        </div>
                        <div class="text-body2 text-secondary">Card Number</div>
                        <div class="text-body1 glass-text q-mb-md">
                          <strong>{{ selectedAdmissionForConfirm?.patient_card_number }}</strong>
                        </div>
                        <div class="text-body2 text-secondary">Ward</div>
                        <div class="text-body1 glass-text q-mb-md">
                          <strong>{{ selectedAdmissionForConfirm?.ward }}</strong>
                        </div>
                        <div v-if="selectedAdmissionForConfirm?.encounter_ccc_number" class="text-body2 text-secondary">
                          CCC from OPD Encounter
                        </div>
                        <div v-if="selectedAdmissionForConfirm?.encounter_ccc_number" class="text-body1 glass-text">
                          <strong>{{ selectedAdmissionForConfirm.encounter_ccc_number }}</strong>
                        </div>
                      </div>
                      <div class="col-12 col-md-6">
                        <q-input
                          v-model="admissionForm.ccc_number"
                          filled
                          label="CCC Number"
                          hint="Auto-populated from OPD encounter if available. For direct admissions, enter if patient has active insurance, otherwise leave blank (cash and carry)."
                          :rules="[val => !val || val.length === 5 || 'CCC number must be 5 digits']"
                          :class="selectedAdmissionForConfirm && selectedAdmissionForConfirm.patient_insured && !isInsuranceExpired(selectedAdmissionForConfirm) ? 'bg-positive-1' : ''"
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
                          If empty from OPD and patient has active insurance, enter CCC number here.
                        </div>
                      </div>
                    </div>
                  </q-card>
                </div>
              </div>
            </q-tab-panel>

            <!-- Tab 2: Emergency Contact -->
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

            <!-- Tab 3: Bed Selection -->
            <q-tab-panel name="bed-selection">
              <div class="text-h6 q-mb-md glass-text">Bed Selection</div>
              <div class="text-body2 text-secondary q-mb-md">
                Select an available bed for {{ selectedAdmissionForConfirm?.ward }}
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
                      No available beds found for this ward
                    </q-item-section>
                  </q-item>
                </template>
              </q-select>
            </q-tab-panel>

            <!-- Tab 4: Doctor Selection -->
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
          </template>
        </q-card-section>

        <q-card-actions align="right">
          <q-btn flat label="Cancel" color="primary" @click="showConfirmDialog = false" />
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
            label="Confirm Admission"
            color="positive"
            @click="submitAdmissionConfirmation"
            :loading="confirmingId !== null"
            :disable="!isFormValid"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Cancel Admission Dialog -->
    <q-dialog v-model="showCancelDialog" persistent>
      <q-card style="min-width: 400px">
        <q-card-section>
          <div class="text-h6">Cancel Admission</div>
        </q-card-section>

        <q-card-section>
          <div class="q-mb-md">
            <div class="text-body2 glass-text q-mb-sm">
              <strong>Patient:</strong> {{ selectedAdmissionForCancel?.patient_name }} {{ selectedAdmissionForCancel?.patient_surname }}
            </div>
            <div class="text-body2 glass-text">
              <strong>Ward:</strong> {{ selectedAdmissionForCancel?.ward }}
            </div>
          </div>
          <q-input
            v-model="cancelReason"
            filled
            type="textarea"
            label="Cancellation Reason *"
            hint="Please provide a reason for cancelling this admission"
            :rules="[val => !!val || 'Cancellation reason is required']"
            rows="4"
          />
        </q-card-section>

        <q-card-actions align="right">
          <q-btn flat label="Cancel" color="primary" @click="showCancelDialog = false" />
          <q-btn 
            flat 
            label="Confirm Cancel" 
            color="negative" 
            @click="submitCancelAdmission"
            :loading="cancellingId !== null"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import { useQuasar } from 'quasar';
import { consultationAPI, patientsAPI } from '../services/api';
import { useAuthStore } from '../stores/auth';

const $q = useQuasar();
const router = useRouter();
const authStore = useAuthStore();

const isAdmin = computed(() => {
  return authStore.user?.role === 'Admin';
});

const loading = ref(false);
const admissions = ref([]);
const allAdmissions = ref([]); // Store all admissions before filtering
const activeTab = ref('pending'); // 'pending', 'confirmed', 'rejected'
const filter = ref('');
const selectedWard = ref(null);
const confirmingId = ref(null);
const revertingId = ref(null);
const cancellingId = ref(null);
const cancelReason = ref('');
const showCancelDialog = ref(false);
const selectedAdmissionForCancel = ref(null);
const showConfirmDialog = ref(false);
const selectedAdmissionForConfirm = ref(null);
const currentTab = ref('patient-info'); // For multi-step form tabs
const beds = ref([]);
const doctors = ref([]);
const loadingBeds = ref(false);
const loadingDoctors = ref(false);
const loadingPatientInsurance = ref(false);

const admissionForm = ref({
  ccc_number: '',
  emergency_contact_name: '',
  emergency_contact_relationship: '',
  emergency_contact_number: '',
  bed_id: null,
  doctor_id: null,
});

// Get unique wards from admissions
const wardOptions = computed(() => {
  const wards = new Set();
  allAdmissions.value.forEach(admission => {
    if (admission.ward) {
      wards.add(admission.ward);
    }
  });
  return Array.from(wards).sort().map(ward => ({
    label: ward,
    value: ward
  }));
});

// Filter admissions based on tab, ward, and search
const filteredAdmissions = computed(() => {
  let filtered = [...allAdmissions.value];
  
  // Filter by active tab
  if (activeTab.value === 'pending') {
    // Pending: not confirmed and not cancelled
    filtered = filtered.filter(admission => 
      !admission.confirmed_by && admission.cancelled !== 1
    );
  } else if (activeTab.value === 'confirmed') {
    // Confirmed: has confirmed_by
    filtered = filtered.filter(admission => admission.confirmed_by !== null);
  } else if (activeTab.value === 'rejected') {
    // Rejected/Cancelled: cancelled === 1
    filtered = filtered.filter(admission => admission.cancelled === 1);
  }
  
  // Filter by ward
  if (selectedWard.value) {
    filtered = filtered.filter(admission => admission.ward === selectedWard.value);
  }
  
  // Filter by search (card number)
  if (filter.value) {
    const searchTerm = filter.value.toLowerCase();
    filtered = filtered.filter(admission => {
      const cardNumber = admission.patient_card_number?.toLowerCase() || '';
      return cardNumber.includes(searchTerm);
    });
  }
  
  return filtered;
});

const columns = [
  {
    name: 'patient',
    required: true,
    label: 'Patient',
    align: 'left',
    field: (row) => `${row.patient_name} ${row.patient_surname}`,
    sortable: true,
  },
  {
    name: 'ward',
    required: true,
    label: 'Ward',
    align: 'center',
    field: 'ward',
    sortable: true,
  },
  {
    name: 'encounter_type',
    label: 'Service Type',
    align: 'center',
    field: 'encounter_service_type',
    sortable: true,
  },
  {
    name: 'date',
    label: 'Recommended Date',
    align: 'center',
    field: 'created_at',
    sortable: true,
  },
  {
    name: 'actions',
    label: 'Actions',
    align: 'center',
    field: 'actions',
    sortable: false,
  },
];

const loadAdmissions = async () => {
  loading.value = true;
  try {
    const response = await consultationAPI.getAdmissionRecommendations();
    console.log('Admissions API response:', response);
    console.log('Response data:', response.data);
    
    // Handle both array and object responses
    let data = [];
    if (Array.isArray(response.data)) {
      data = response.data;
    } else if (response.data && Array.isArray(response.data.data)) {
      data = response.data.data;
    }
    
    // Load admissions quickly without fetching patient insurance data
    // Insurance data will be fetched only when a specific admission is selected
    allAdmissions.value = data;
    admissions.value = data;
    
    console.log('Loaded admissions:', allAdmissions.value.length);
  } catch (error) {
    console.error('Error loading admissions:', error);
    console.error('Error response:', error.response);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to load admission recommendations',
    });
    allAdmissions.value = [];
    admissions.value = [];
  } finally {
    loading.value = false;
  }
};

const onWardFilterChange = () => {
  // Filter change handled by computed property
};

const onSearchChange = () => {
  // Search change handled by computed property
};

// Confirm admission - Available to all staff (Nurse, Doctor, PA, Admin)
const confirmAdmission = async (admission) => {
  loadingPatientInsurance.value = true;
  try {
    // Fetch patient insurance information for the selected admission
    let admissionWithInsurance = { ...admission };
    
    if (admission.patient_card_number) {
      try {
        const patientResponse = await patientsAPI.getByCard(admission.patient_card_number);
        const patient = Array.isArray(patientResponse.data) 
          ? patientResponse.data[0] 
          : patientResponse.data;
        
        if (patient) {
          // Merge insurance information into admission object
          admissionWithInsurance = {
            ...admission,
            patient_insured: patient.insured || false,
            patient_insurance_id: patient.insurance_id || null,
            patient_insurance_start_date: patient.insurance_start_date || null,
            patient_insurance_end_date: patient.insurance_end_date || null,
          };
        }
      } catch (error) {
        console.warn(`Failed to fetch patient data for card ${admission.patient_card_number}:`, error);
        // Continue with admission data without insurance info if fetch fails
        admissionWithInsurance = {
          ...admission,
          patient_insured: false,
          patient_insurance_id: null,
          patient_insurance_start_date: null,
          patient_insurance_end_date: null,
        };
      }
    }
    
    // Set the admission with insurance data
    selectedAdmissionForConfirm.value = admissionWithInsurance;
    
    // Debug: Log the full admission object
    console.log('Full admission object with insurance:', JSON.stringify(admissionWithInsurance, null, 2));
    console.log('Emergency contact fields:', {
      name: admissionWithInsurance.patient_emergency_contact_name,
      relationship: admissionWithInsurance.patient_emergency_contact_relationship,
      number: admissionWithInsurance.patient_emergency_contact_number,
      nameType: typeof admissionWithInsurance.patient_emergency_contact_name,
      nameValue: admissionWithInsurance.patient_emergency_contact_name
    });
    
    // Auto-populate CCC from encounter if available
    // For OPD cases: use encounter CCC if exists, otherwise leave empty (can be filled if patient has insurance)
    // For direct admissions: leave empty (can be filled if patient has active insurance)
    
    // Auto-populate emergency contact from patient registration if available
    // Check if patient has emergency contact details from registration
    const hasEmergencyContactFromRegistration = !!(
      admissionWithInsurance.patient_emergency_contact_name ||
      admissionWithInsurance.patient_emergency_contact_relationship ||
      admissionWithInsurance.patient_emergency_contact_number
    );
    
    // Auto-populate emergency contact from patient registration if available
    // Handle null, undefined, and empty strings properly
    const emergencyContactName = (admissionWithInsurance.patient_emergency_contact_name && typeof admissionWithInsurance.patient_emergency_contact_name === 'string') 
      ? admissionWithInsurance.patient_emergency_contact_name.trim() 
      : (admissionWithInsurance.patient_emergency_contact_name || '');
    const emergencyContactRelationship = (admissionWithInsurance.patient_emergency_contact_relationship && typeof admissionWithInsurance.patient_emergency_contact_relationship === 'string')
      ? admissionWithInsurance.patient_emergency_contact_relationship.trim()
      : (admissionWithInsurance.patient_emergency_contact_relationship || '');
    const emergencyContactNumber = (admissionWithInsurance.patient_emergency_contact_number && typeof admissionWithInsurance.patient_emergency_contact_number === 'string')
      ? admissionWithInsurance.patient_emergency_contact_number.trim()
      : (admissionWithInsurance.patient_emergency_contact_number || '');
    
    admissionForm.value = {
      ccc_number: (admissionWithInsurance.encounter_ccc_number && typeof admissionWithInsurance.encounter_ccc_number === 'string') 
        ? admissionWithInsurance.encounter_ccc_number.trim() 
        : (admissionWithInsurance.encounter_ccc_number || ''), // Auto-populate from OPD encounter if exists
      emergency_contact_name: emergencyContactName, // Auto-populate from patient registration
      emergency_contact_relationship: emergencyContactRelationship, // Auto-populate from patient registration
      emergency_contact_number: emergencyContactNumber, // Auto-populate from patient registration
      bed_id: null,
      doctor_id: null,
    };
    
    // Log for debugging
    console.log('Admission data for card:', admissionWithInsurance.patient_card_number, {
      raw_emergency_contact_name: admissionWithInsurance.patient_emergency_contact_name,
      raw_emergency_contact_relationship: admissionWithInsurance.patient_emergency_contact_relationship,
      raw_emergency_contact_number: admissionWithInsurance.patient_emergency_contact_number,
      processed_emergency_contact_name: emergencyContactName,
      processed_emergency_contact_relationship: emergencyContactRelationship,
      processed_emergency_contact_number: emergencyContactNumber,
      hasEmergencyContactFromRegistration,
      patient_insured: admissionWithInsurance.patient_insured,
      patient_insurance_id: admissionWithInsurance.patient_insurance_id,
      formValues: admissionForm.value
    });
    
    currentTab.value = 'patient-info';
    showConfirmDialog.value = true;
    loadBedsAndDoctors(admissionWithInsurance.ward);
  } catch (error) {
    console.error('Error loading patient insurance data:', error);
    $q.notify({
      type: 'warning',
      message: 'Failed to load patient insurance information. Proceeding with available data.',
    });
    // Still show the dialog with available data
    selectedAdmissionForConfirm.value = admission;
    currentTab.value = 'patient-info';
    showConfirmDialog.value = true;
    loadBedsAndDoctors(admission.ward);
  } finally {
    loadingPatientInsurance.value = false;
  }
};

const revertConfirmation = async (admission) => {
  $q.dialog({
    title: 'Revert Confirmation',
    message: `Are you sure you want to revert the confirmation for ${admission.patient_name} ${admission.patient_surname}? This will remove them from the ward and return to recommendation status.`,
    cancel: true,
    persistent: true
  }).onOk(async () => {
    revertingId.value = admission.id;
    try {
      await consultationAPI.revertAdmissionConfirmation(admission.id);
      $q.notify({
        type: 'positive',
        message: 'Admission confirmation reverted successfully',
      });
      // Reload admissions to get updated status
      await loadAdmissions();
    } catch (error) {
      console.error('Error reverting confirmation:', error);
      $q.notify({
        type: 'negative',
        message: error.response?.data?.detail || 'Failed to revert confirmation',
      });
    } finally {
      revertingId.value = null;
    }
  });
};

const cancelAdmission = (admission) => {
  selectedAdmissionForCancel.value = admission;
  cancelReason.value = '';
  showCancelDialog.value = true;
};

const submitCancelAdmission = async () => {
  if (!cancelReason.value.trim()) {
    $q.notify({
      type: 'negative',
      message: 'Please provide a cancellation reason',
    });
    return;
  }

  const admission = selectedAdmissionForCancel.value;
  if (!admission) return;

  cancellingId.value = admission.id;
  try {
    await consultationAPI.cancelAdmission(admission.id, cancelReason.value);
    $q.notify({
      type: 'positive',
      message: 'Admission cancelled successfully',
    });
    showCancelDialog.value = false;
    selectedAdmissionForCancel.value = null;
    cancelReason.value = '';
    // Reload admissions to get updated status
    await loadAdmissions();
  } catch (error) {
    console.error('Error cancelling admission:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to cancel admission',
    });
  } finally {
    cancellingId.value = null;
  }
};

const showCancellationReason = (admission) => {
  $q.dialog({
    title: 'Cancellation Reason',
    message: `<strong>Patient:</strong> ${admission.patient_name} ${admission.patient_surname}<br/><strong>Ward:</strong> ${admission.ward}<br/><strong>Reason:</strong> ${admission.cancellation_reason || 'No reason provided'}`,
    html: true,
    persistent: true
  });
};

const loadBedsAndDoctors = async (ward) => {
  loadingBeds.value = true;
  loadingDoctors.value = true;
  try {
    // Load available beds for the ward
    const bedsResponse = await consultationAPI.getBeds(ward, true);
    beds.value = Array.isArray(bedsResponse.data) ? bedsResponse.data : [];
    
    // Load doctors
    const doctorsResponse = await consultationAPI.getDoctors();
    doctors.value = Array.isArray(doctorsResponse.data) ? doctorsResponse.data : [];
  } catch (error) {
    console.error('Error loading beds/doctors:', error);
    $q.notify({
      type: 'negative',
      message: 'Failed to load beds or doctors',
    });
  } finally {
    loadingBeds.value = false;
    loadingDoctors.value = false;
  }
};

const canProceedToNextTab = computed(() => {
  if (currentTab.value === 'patient-info') {
    // Can proceed if CCC is provided or not required
    return true;
  } else if (currentTab.value === 'emergency-contact') {
    // Must have all emergency contact fields
    return !!(
      admissionForm.value.emergency_contact_name &&
      admissionForm.value.emergency_contact_relationship &&
      admissionForm.value.emergency_contact_number
    );
  } else if (currentTab.value === 'bed-selection') {
    // Must select a bed
    return !!admissionForm.value.bed_id;
  } else if (currentTab.value === 'doctor-selection') {
    // Must select a doctor
    return !!admissionForm.value.doctor_id;
  }
  return false;
});

const isFormValid = computed(() => {
  // Check all mandatory fields are completed
  const hasEmergencyContact = !!(
    admissionForm.value.emergency_contact_name &&
    admissionForm.value.emergency_contact_relationship &&
    admissionForm.value.emergency_contact_number
  );
  const hasBed = !!admissionForm.value.bed_id;
  const hasDoctor = !!admissionForm.value.doctor_id;
  
  return hasEmergencyContact && hasBed && hasDoctor;
});

const nextTab = () => {
  if (currentTab.value === 'patient-info') {
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
    currentTab.value = 'patient-info';
  }
};

const submitAdmissionConfirmation = async () => {
  // Validate all mandatory fields before submission
  if (!isFormValid.value) {
    const missingFields = [];
    
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
    if (!admissionForm.value.emergency_contact_name || 
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

  const admission = selectedAdmissionForConfirm.value;
  if (!admission) return;

  confirmingId.value = admission.id;
  try {
    await consultationAPI.confirmAdmission(admission.id, admissionForm.value);
    $q.notify({
      type: 'positive',
      message: 'Admission confirmed successfully',
    });
    showConfirmDialog.value = false;
    selectedAdmissionForConfirm.value = null;
    currentTab.value = 'patient-info';
    // Reload admissions to get updated status
    await loadAdmissions();
    // Switch to confirmed tab to show the newly confirmed admission
    activeTab.value = 'confirmed';
  } catch (error) {
    console.error('Error confirming admission:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to confirm admission',
    });
  } finally {
    confirmingId.value = null;
  }
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

const isInsuranceExpired = (admission) => {
  if (!admission || !admission.patient_insurance_end_date) return false;
  const endDate = new Date(admission.patient_insurance_end_date);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return endDate < today;
};

const isInsuranceExpiringSoon = (admission) => {
  if (!admission || !admission.patient_insurance_end_date) return false;
  const endDate = new Date(admission.patient_insurance_end_date);
  const today = new Date();
  const daysUntilExpiry = Math.ceil((endDate - today) / (1000 * 60 * 60 * 24));
  return daysUntilExpiry > 0 && daysUntilExpiry <= 30;
};

const getInsuranceCardClass = (admission) => {
  if (!admission) return '';
  if (admission.patient_insured && !isInsuranceExpired(admission)) {
    return 'bg-positive-1 border-positive';
  } else if (isInsuranceExpired(admission)) {
    return 'bg-negative-1 border-negative';
  } else if (admission.patient_insurance_id) {
    return 'bg-warning-1 border-warning';
  }
  return '';
};

const getEndDateClass = (admission) => {
  if (!admission) return 'text-grey-7';
  if (isInsuranceExpired(admission)) return 'text-negative';
  if (isInsuranceExpiringSoon(admission)) return 'text-warning';
  return 'text-positive';
};

const getEndDateTextClass = (admission) => {
  if (!admission) return 'glass-text';
  if (isInsuranceExpired(admission)) return 'text-negative';
  if (isInsuranceExpiringSoon(admission)) return 'text-warning';
  return 'glass-text';
};

const viewPatient = (cardNumber) => {
  router.push(`/patients/${cardNumber}`);
};

const viewEncounter = (encounterId) => {
  router.push(`/consultation/${encounterId}`);
};

onMounted(() => {
  loadAdmissions();
});
</script>

<style scoped>
/* Table cell text styling for better visibility */
.glass-table :deep(.q-table__top),
.glass-table :deep(.q-table__bottom),
.glass-table :deep(.q-table tbody td),
.glass-table :deep(.q-table thead th) {
  color: inherit;
}

/* Light mode adjustments */
.body--light .glass-text {
  color: rgba(0, 0, 0, 0.87) !important;
}

.body--light .glass-table :deep(.q-table thead th) {
  color: rgba(0, 0, 0, 0.87);
  font-weight: 500;
}

.body--light .glass-table :deep(.q-table tbody td) {
  color: rgba(0, 0, 0, 0.87);
}

.body--light .glass-table :deep(.q-table tbody td .text-secondary) {
  color: rgba(0, 0, 0, 0.6) !important;
}

/* Dark mode adjustments */
.body--dark .glass-text {
  color: rgba(255, 255, 255, 0.9) !important;
}

.body--dark .glass-table :deep(.q-table thead th) {
  color: rgba(255, 255, 255, 0.9);
}

.body--dark .glass-table :deep(.q-table tbody td) {
  color: rgba(255, 255, 255, 0.9);
}

.body--dark .glass-table :deep(.q-table tbody td .text-secondary) {
  color: rgba(255, 255, 255, 0.6) !important;
}

.glass-button {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

/* Light mode button adjustments */
.body--light .glass-button {
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid rgba(0, 0, 0, 0.1);
  color: rgba(0, 0, 0, 0.87);
}

.body--light .glass-button:hover {
  background: rgba(255, 255, 255, 0.9);
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

