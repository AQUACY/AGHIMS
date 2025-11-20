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
              {{ patientInfo.patient_name }} {{ patientInfo.patient_surname }}<span v-if="patientInfo.patient_other_names"> {{ patientInfo.patient_other_names }}</span>
            </div>
            <div v-if="patientBillInfo.totalAmount !== null" class="text-body1 q-mt-xs" :class="patientBillInfo.remainingBalance > 0 ? 'text-negative text-weight-bold' : 'text-secondary'">
              <q-icon name="receipt" size="16px" class="q-mr-xs" />
              Total Bills: GHC {{ patientBillInfo.totalAmount.toFixed(2) }} 
              <span v-if="patientBillInfo.remainingBalance > 0" class="text-negative">
                | Outstanding: GHC {{ patientBillInfo.remainingBalance.toFixed(2) }}
              </span>
              <span v-else>
                | Outstanding: GHC 0.00
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
                <div v-if="patientInfo.bed_number" class="text-body2 text-secondary q-mt-xs">
                  <q-icon name="hotel" size="16px" class="q-mr-xs" />
                  Bed: <strong>{{ patientInfo.bed_number }}</strong>
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
                    </div>
                    <q-btn
                      v-if="props.row.type === 'transfers' || props.row.type === 'clinical_review'"
                      flat
                      dense
                      icon="visibility"
                      label="View All"
                      color="secondary"
                      size="sm"
                      @click="viewTableItems(props.row.type)"
                    />
                    <!-- Show clinical reviews list with edit buttons -->
                    <div v-if="props.row.type === 'clinical_review' && clinicalReviews.length > 0" class="q-mt-md">
                      <q-list bordered separator>
                        <q-item
                          v-for="review in clinicalReviews"
                          :key="review.id"
                          class="q-pa-sm"
                        >
                          <q-item-section>
                            <q-item-label class="text-weight-bold">
                              {{ review.reviewed_by_name || 'Unknown' }} - {{ formatDateTime(review.reviewed_at) }}
                            </q-item-label>
                            <q-item-label caption class="text-body2" style="white-space: pre-wrap; word-wrap: break-word;">
                              {{ review.review_notes || 'No notes' }}
                            </q-item-label>
                          </q-item-section>
                          <q-item-section side>
                            <div class="row q-gutter-xs">
                              <q-btn
                                v-if="authStore.user?.id === review.reviewed_by || authStore.userRole === 'Admin'"
                                flat
                                dense
                                icon="edit"
                                label="Edit"
                                color="primary"
                                size="sm"
                                @click="editClinicalReview(review)"
                                :disable="isDischarged"
                              />
                              <q-btn
                                flat
                                dense
                                icon="open_in_new"
                                label="Open"
                                color="secondary"
                                size="sm"
                                @click="openClinicalReview(review.id)"
                              />
                              <q-btn
                                v-if="authStore.userRole === 'Admin'"
                                flat
                                dense
                                icon="delete"
                                label="Delete"
                                color="negative"
                                size="sm"
                                @click="deleteClinicalReview(review)"
                                :disable="isDischarged"
                              />
                            </div>
                          </q-item-section>
                        </q-item>
                      </q-list>
                    </div>
                    <!-- Show surgeries list -->
                    <div v-if="props.row.type === 'surgeries' && surgeries.length > 0" class="q-mt-md">
                      <q-list bordered separator>
                        <q-item
                          v-for="surgery in surgeries"
                          :key="surgery.id"
                          class="q-pa-sm"
                        >
                          <q-item-section>
                            <q-item-label class="text-weight-bold">
                              {{ surgery.surgery_name }}
                              <q-badge 
                                :color="surgery.is_completed ? 'positive' : 'warning'" 
                                :label="surgery.is_completed ? 'Completed' : 'Pending'"
                                class="q-ml-sm"
                              />
                            </q-item-label>
                            <q-item-label caption>
                              <div v-if="surgery.surgeon_name" class="q-mt-xs">
                                Surgeon: {{ surgery.surgeon_name }}
                              </div>
                              <div v-if="surgery.surgery_date" class="q-mt-xs">
                                Date: {{ formatDateTime(surgery.surgery_date) }}
                              </div>
                              <div v-if="surgery.surgery_notes" class="q-mt-xs text-body2" style="white-space: pre-wrap; word-wrap: break-word;">
                                {{ surgery.surgery_notes }}
                              </div>
                            </q-item-label>
                          </q-item-section>
                          <q-item-section side>
                            <div class="row q-gutter-xs">
                              <q-btn
                                v-if="authStore.userRole === 'Doctor' || authStore.userRole === 'PA' || authStore.userRole === 'Admin'"
                                flat
                                dense
                                icon="edit"
                                label="Edit"
                                color="primary"
                                size="sm"
                                @click="editSurgery(surgery)"
                                :disable="isDischarged"
                              />
                              <q-btn
                                v-if="authStore.userRole === 'Admin'"
                                flat
                                dense
                                icon="delete"
                                label="Delete"
                                color="negative"
                                size="sm"
                                @click="deleteSurgery(surgery)"
                                :disable="isDischarged"
                              />
                            </div>
                          </q-item-section>
                        </q-item>
                      </q-list>
                    </div>
                    <div v-if="props.row.type === 'surgeries' && surgeries.length === 0" class="q-mt-sm text-center text-grey-7">
                      No surgeries recorded
                    </div>
                    <!-- Show additional services list -->
                    <div v-if="props.row.type === 'additional_services' && patientAdditionalServices.length > 0" class="q-mt-md">
                      <q-list bordered separator>
                        <q-item
                          v-for="service in patientAdditionalServices"
                          :key="service.id"
                          class="q-pa-sm"
                        >
                          <q-item-section>
                            <q-item-label class="text-weight-bold">
                              {{ service.service_name }}
                              <q-badge 
                                :color="service.end_time ? 'positive' : 'warning'" 
                                :label="service.end_time ? 'Stopped' : 'Active'"
                                class="q-ml-sm"
                              />
                              <q-badge 
                                v-if="service.is_billed"
                                color="info" 
                                label="Billed"
                                class="q-ml-sm"
                              />
                            </q-item-label>
                            <q-item-label caption>
                              <div class="q-mt-xs">
                                Started: {{ formatDateTime(service.start_time) }}
                                <span v-if="service.started_by_name"> by {{ service.started_by_name }}</span>
                              </div>
                              <div v-if="service.end_time" class="q-mt-xs">
                                Stopped: {{ formatDateTime(service.end_time) }}
                                <span v-if="service.stopped_by_name"> by {{ service.stopped_by_name }}</span>
                              </div>
                              <div v-if="service.units_used && service.total_cost" class="q-mt-xs text-weight-bold">
                                {{ service.units_used }} {{ service.service_unit_type }}(s) × {{ service.service_price_per_unit }} GHS = {{ service.total_cost }} GHS
                              </div>
                              <div v-if="service.notes" class="q-mt-xs text-body2" style="white-space: pre-wrap; word-wrap: break-word;">
                                {{ service.notes }}
                              </div>
                            </q-item-label>
                          </q-item-section>
                          <q-item-section side v-if="!service.end_time">
                            <q-btn
                              flat
                              dense
                              icon="stop"
                              label="Stop"
                              color="negative"
                              size="sm"
                              @click="stopAdditionalService(service)"
                            />
                          </q-item-section>
                        </q-item>
                      </q-list>
                    </div>
                    <div v-if="props.row.type === 'additional_services' && patientAdditionalServices.length === 0" class="q-mt-sm text-center text-grey-7">
                      No additional services recorded
                    </div>
                    <!-- Show diagnoses list -->
                    <div v-if="props.row.type === 'diagnoses' && inpatientDiagnoses.length > 0" class="q-mt-md">
                      <q-list bordered separator>
                        <q-item
                          v-for="diagnosis in inpatientDiagnoses"
                          :key="diagnosis.id"
                          class="q-pa-sm"
                        >
                          <q-item-section>
                            <q-item-label class="text-weight-bold">
                              {{ diagnosis.diagnosis }}
                              <q-badge 
                                v-if="diagnosis.is_chief"
                                color="primary" 
                                label="Chief"
                                class="q-ml-sm"
                              />
                              <q-badge 
                                v-if="diagnosis.is_provisional"
                                color="warning" 
                                label="Provisional"
                                class="q-ml-sm"
                              />
                              <q-badge 
                                v-if="diagnosis.source === 'opd'"
                                color="info" 
                                label="OPD"
                                class="q-ml-sm"
                              />
                            </q-item-label>
                            <q-item-label caption>
                              <div class="q-mt-xs">
                                <span v-if="diagnosis.icd10">
                                  ICD-10: <strong>{{ diagnosis.icd10 }}</strong>
                                </span>
                                <span v-if="diagnosis.gdrg_code" class="q-ml-md">
                                  G-DRG: <strong>{{ diagnosis.gdrg_code }}</strong>
                                </span>
                              </div>
                              <div v-if="diagnosis.diagnosis_status" class="q-mt-xs">
                                Status: <strong>{{ diagnosis.diagnosis_status }}</strong>
                              </div>
                              <div class="q-mt-xs text-caption text-grey-7">
                                Added: {{ formatDateTime(diagnosis.created_at) }}
                                <span v-if="diagnosis.created_by_name"> by {{ diagnosis.created_by_name }}</span>
                              </div>
                            </q-item-label>
                          </q-item-section>
                        </q-item>
                      </q-list>
                    </div>
                    <div v-if="props.row.type === 'diagnoses' && inpatientDiagnoses.length === 0" class="q-mt-sm text-center text-grey-7">
                      No diagnoses recorded
                    </div>
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
                    <!-- <q-icon name="edit" size="32px" color="grey-6" class="q-mb-sm" /> -->
                    <q-btn
                      v-if="props.row.type === 'admission_notes'"
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
                label="Vitals"
                color="info"
                @click="addVitals"
                :disable="isDischarged"
                class="full-width"
              />
              <q-btn
                flat
                icon="medication"
                label="Prescriptions"
                color="accent"
                @click="viewPrescriptions"
                :disable="isDischarged"
                class="full-width"
              />
              <q-btn
                flat
                icon="science"
                label="Investigations"
                color="purple"
                @click="viewInvestigations"
                :disable="isDischarged"
                class="full-width"
              />
              <q-btn
                flat
                icon="healing"
                label="Add Operation"
                color="red"
                @click="addOperation"
                :disable="isDischarged"
                class="full-width"
              />
              <q-btn
                flat
                icon="add_circle"
                label="Add Additional Service"
                color="deep-orange"
                @click="addAdditionalService"
                :disable="isDischarged"
                class="full-width"
              />
              <q-btn
                flat
                icon="inventory_2"
                label="Inventory Debit"
                color="teal"
                @click="addInventoryDebit"
                :disable="isDischarged"
                class="full-width"
              />
              <q-btn
                flat
                icon="bloodtype"
                label="Request Blood"
                color="red"
                @click="requestBlood"
                :disable="isDischarged"
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
                icon="medical_services"
                label="Clinical Review"
                color="purple"
                @click="viewClinicalReview"
                class="full-width"
              />
              <q-btn
                flat
                icon="medication_liquid"
                label="Treatment Sheet"
                color="indigo"
                @click="viewTreatmentSheet"
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
                v-if="!isDischarged"
                flat
                icon="exit_to_app"
                :label="isPartiallyDischarged ? 'Final Discharge' : 'Discharge Patient'"
                :color="isPartiallyDischarged ? 'warning' : 'negative'"
                @click="dischargePatient"
                :loading="discharging"
                class="full-width"
              />
              <q-banner
                v-if="isPartiallyDischarged && !isDischarged"
                class="bg-warning text-white q-mt-sm"
                rounded
              >
                <template v-slot:avatar>
                  <q-icon name="warning" />
                </template>
                <div class="text-weight-bold">Partially Discharged</div>
                <div class="text-caption">Please ensure all bills are paid before final discharge.</div>
              </q-banner>
              <q-btn
                v-if="isPartiallyDischarged && !isDischarged"
                flat
                icon="undo"
                label="Revert Partial Discharge"
                color="warning"
                @click="revertPartialDischarge"
                :loading="discharging"
                class="full-width q-mt-sm"
              />
              <q-btn
                v-if="!isDischarged"
                flat
                icon="cancel"
                label="Cancel Admission"
                color="negative"
                @click="cancelAdmission"
                :loading="cancelling"
                class="full-width"
              />
              <q-banner
                v-if="isDischarged"
                class="bg-grey-3 q-mt-sm"
                rounded
              >
                <template v-slot:avatar>
                  <q-icon name="info" color="grey" />
                </template>
                Patient has been discharged. This record is read-only.
              </q-banner>
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
                  
                  <q-separator class="q-my-md" />
                  
                  <!-- Previous Vitals Records -->
                  <div class="text-subtitle2 text-weight-bold glass-text q-mb-sm">
                    Previous Vitals Records
                  </div>
                  <div style="max-height: 400px; overflow-y: auto;" class="q-mb-md">
                    <q-list bordered separator v-if="inpatientVitals.length > 0">
                      <q-item
                        v-for="vital in inpatientVitals"
                        :key="vital.id"
                        class="q-pa-sm"
                      >
                        <q-item-section>
                          <q-item-label class="text-weight-bold">
                            {{ vital.recorded_by_name || 'Unknown' }} - {{ formatDateTime(vital.recorded_at) }}
                          </q-item-label>
                          <q-item-label caption>
                            <div class="row q-col-gutter-md">
                              <div v-if="vital.temperature" class="col-auto">
                                <strong>Temp:</strong> {{ vital.temperature }}°C
                              </div>
                              <div v-if="vital.pulse" class="col-auto">
                                <strong>Pulse:</strong> {{ vital.pulse }} bpm
                              </div>
                              <div v-if="vital.blood_pressure_systolic && vital.blood_pressure_diastolic" class="col-auto">
                                <strong>BP:</strong> {{ vital.blood_pressure_systolic }}/{{ vital.blood_pressure_diastolic }} mmHg
                              </div>
                              <div v-if="vital.respiratory_rate" class="col-auto">
                                <strong>RR:</strong> {{ vital.respiratory_rate }} /min
                              </div>
                              <div v-if="vital.oxygen_saturation" class="col-auto">
                                <strong>SpO2:</strong> {{ vital.oxygen_saturation }}%
                              </div>
                              <div v-if="vital.weight" class="col-auto">
                                <strong>Weight:</strong> {{ vital.weight }} kg
                              </div>
                              <div v-if="vital.height" class="col-auto">
                                <strong>Height:</strong> {{ vital.height }} cm
                              </div>
                              <div v-if="vital.bmi" class="col-auto">
                                <strong>BMI:</strong> {{ vital.bmi.toFixed(1) }}
                              </div>
                            </div>
                            <div v-if="vital.notes" class="q-mt-xs">
                              <strong>Notes:</strong> {{ vital.notes }}
                            </div>
                          </q-item-label>
                        </q-item-section>
                        <q-item-section side>
                          <div class="column q-gutter-xs">
                            <q-btn
                              v-if="authStore.user?.id === vital.recorded_by || authStore.userRole === 'Admin'"
                              flat
                              dense
                              icon="edit"
                              label="Edit"
                              color="primary"
                              size="sm"
                              @click="editVital(vital)"
                              :disable="isDischarged"
                            />
                            <q-btn
                              flat
                              dense
                              icon="show_chart"
                              label="Plot Graph"
                              color="secondary"
                              size="sm"
                              @click="plotVitalsGraph(vital)"
                            />
                          </div>
                        </q-item-section>
                      </q-item>
                    </q-list>
                    <div v-else class="text-center text-secondary q-pa-md">
                      No previous vitals records
                    </div>
                  </div>
                  <q-btn 
                    v-if="inpatientVitals.length > 0"
                    label="Plot All Vitals" 
                    color="secondary" 
                    icon="show_chart"
                    @click="plotAllVitalsGraph" 
                    class="q-mt-sm"
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
                                :class="getNoteClass(note)"
                                :style="getNoteStyle(note)"
                                v-html="processNoteHtml(note)"
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
                <q-btn 
                  v-if="currentTableType === 'vitals' && editingVitalId"
                  flat 
                  label="Clear" 
                  color="warning" 
                  @click="clearVitalForm" 
                />
                <q-btn flat label="Cancel" color="primary" @click="showTableItemDialog = false" />
                <q-btn
                  flat
                  :label="(currentTableType === 'vitals' && editingVitalId) ? 'Update' : 'Save'"
                  color="positive"
                  @click="saveTableItem"
                  :loading="savingTableItem"
                />
              </q-card-actions>
            </q-card>
          </q-dialog>

          <!-- Vitals Graph Dialog -->
          <q-dialog v-model="showVitalsGraphDialog">
            <q-card style="min-width: 900px; max-width: 1200px">
              <q-card-section>
                <div class="text-h6">Vitals Trend Graph</div>
              </q-card-section>
              <q-card-section>
                <div class="row q-gutter-sm q-mb-md">
                  <q-toggle v-model="showBP" label="Blood Pressure" color="red" />
                  <q-toggle v-model="showTemperature" label="Temperature" color="orange" />
                  <q-toggle v-model="showPulse" label="Pulse" color="blue" />
                  <q-toggle v-model="showWeight" label="Weight" color="green" />
                  <q-toggle v-model="showRR" label="Respiratory Rate" color="purple" />
                  <q-toggle v-model="showSpO2" label="SpO2" color="cyan" />
                </div>
                <div class="vitals-graph-container" style="position: relative; width: 100%; height: 500px; border: 1px solid #999; border-radius: 8px; background: #fafafa; box-shadow: inset 0 0 10px rgba(0,0,0,0.1);">
                  <canvas ref="vitalsCanvas" style="width: 100%; height: 100%;"></canvas>
                </div>
              </q-card-section>
              <q-card-actions align="right">
                <q-btn label="Close" color="primary" v-close-popup />
              </q-card-actions>
            </q-card>
          </q-dialog>

          <!-- Surgery Dialog -->
          <q-dialog v-model="showSurgeryDialog" persistent>
            <q-card style="min-width: 700px; max-width: 900px">
              <q-card-section>
                <div class="text-h6 glass-text">
                  {{ editingSurgery ? 'Edit Surgery' : 'Add Operation' }}
                </div>
              </q-card-section>

              <q-card-section class="q-pt-none">
                <q-form @submit="saveSurgery" class="q-gutter-md">
                  <!-- Surgery Search/Select -->
                  <q-select
                    v-model="selectedSurgery"
                    :options="filteredSurgeryOptions"
                    filled
                    use-input
                    input-debounce="300"
                    :label="editingSurgery ? 'Search Surgery (optional)' : 'Search Surgery *'"
                    hint="Type to search for surgeries from price list - Select to auto-fill"
                    :rules="editingSurgery ? [] : [val => !!val || 'Surgery is required']"
                    @filter="filterSurgeries"
                    @update:model-value="onSurgerySelected"
                    option-label="label"
                    option-value="value"
                    emit-value
                    map-options
                    clearable
                    :loading="loadingSurgeries"
                  >
                    <template v-slot:option="scope">
                      <q-item v-bind="scope.itemProps">
                        <q-item-section>
                          <q-item-label>{{ scope.opt.label }}</q-item-label>
                          <q-item-label caption>
                            Code: {{ scope.opt.value.code }} | 
                            Type: {{ scope.opt.value.service_type || 'N/A' }}
                          </q-item-label>
                        </q-item-section>
                      </q-item>
                    </template>
                    <template v-slot:no-option>
                      <q-item>
                        <q-item-section class="text-grey">
                          No surgeries found. You can enter manually below.
                        </q-item-section>
                      </q-item>
                    </template>
                  </q-select>
                  
                  <!-- Manual Surgery Entry (shown when editing or if no selection) -->
                  <q-input
                    v-model="surgeryForm.surgery_name"
                    filled
                    label="Surgery Name *"
                    hint="Name/description of the surgery (auto-filled from selection)"
                    :rules="[val => !!val || 'Surgery name is required']"
                  />
                  
                  <div class="row q-col-gutter-md">
                    <div class="col-6">
                      <q-input
                        v-model="surgeryForm.g_drg_code"
                        filled
                        label="G-DRG Code"
                        hint="Surgery code (auto-filled from selection)"
                      />
                    </div>
                    <div class="col-6">
                      <q-input
                        v-model="surgeryForm.surgery_type"
                        filled
                        label="Surgery Type"
                        hint="Type/category of surgery (auto-filled from selection)"
                      />
                    </div>
                  </div>

                  <div class="row q-col-gutter-md">
                    <div class="col-6">
                      <q-input
                        v-model="surgeryForm.surgeon_name"
                        filled
                        label="Surgeon Name"
                        hint="Name of the surgeon"
                      />
                    </div>
                    <div class="col-6">
                      <q-input
                        v-model="surgeryForm.assistant_surgeon"
                        filled
                        label="Assistant Surgeon"
                        hint="Assistant surgeon name (optional)"
                      />
                    </div>
                  </div>

                  <div class="row q-col-gutter-md">
                    <div class="col-6">
                      <q-input
                        v-model="surgeryForm.anesthesia_type"
                        filled
                        label="Anesthesia Type"
                        hint="Type of anesthesia (e.g., General, Local, Regional)"
                      />
                    </div>
                    <div class="col-6">
                      <q-input
                        v-model="surgeryForm.surgery_date"
                        filled
                        type="datetime-local"
                        label="Surgery Date"
                        hint="Scheduled/performed date"
                      />
                    </div>
                  </div>

                  <q-input
                    v-model="surgeryForm.surgery_notes"
                    filled
                    type="textarea"
                    label="Pre-operative Notes"
                    hint="Pre-operative notes and observations"
                    rows="4"
                  />

                  <div v-if="editingSurgery" class="q-mt-md">
                    <q-separator class="q-my-md" />
                    <div class="text-subtitle2 q-mb-sm">Post-operative Information</div>
                    
                    <q-input
                      v-model="surgeryForm.operative_notes"
                      filled
                      type="textarea"
                      label="Operative Notes"
                      hint="Notes during the operation"
                      rows="4"
                    />

                    <q-input
                      v-model="surgeryForm.post_operative_notes"
                      filled
                      type="textarea"
                      label="Post-operative Notes"
                      hint="Post-operative observations and care instructions"
                      rows="4"
                      class="q-mt-md"
                    />

                    <q-input
                      v-model="surgeryForm.complications"
                      filled
                      type="textarea"
                      label="Complications"
                      hint="Any complications encountered"
                      rows="3"
                      class="q-mt-md"
                    />

                    <q-checkbox
                      v-model="surgeryForm.is_completed"
                      label="Mark as Completed"
                      class="q-mt-md"
                    />
                  </div>

                  <q-card-actions align="right" class="q-pt-md">
                    <q-btn flat label="Cancel" color="primary" @click="closeSurgeryDialog" />
                    <q-btn
                      type="submit"
                      label="Save"
                      color="positive"
                      :loading="savingSurgery"
                    />
                  </q-card-actions>
                </q-form>
              </q-card-section>
            </q-card>
          </q-dialog>

          <!-- Stop Additional Service Dialog -->
          <q-dialog v-model="showStopServiceDialog" persistent>
            <q-card style="min-width: 500px; max-width: 700px;">
              <q-card-section>
                <div class="text-h6 glass-text">
                  Stop Additional Service
                </div>
                <div v-if="stoppingService" class="text-subtitle2 text-grey-7 q-mt-sm">
                  Service: <span class="text-weight-bold">{{ stoppingService.service_name }}</span>
                </div>
              </q-card-section>

              <q-card-section>
                <div class="row q-col-gutter-md">
                  <div class="col-12 col-md-6">
                    <q-input
                      v-model="stopServiceForm.end_date"
                      filled
                      label="Stop Date *"
                      hint="Select the date when the service stopped"
                      :rules="[val => !!val || 'Stop date is required']"
                    >
                      <template v-slot:append>
                        <q-icon name="event" class="cursor-pointer">
                          <q-popup-proxy cover transition-show="scale" transition-hide="scale">
                            <q-date v-model="stopServiceForm.end_date" mask="YYYY-MM-DD">
                              <div class="row items-center justify-end">
                                <q-btn v-close-popup label="Close" color="primary" flat />
                              </div>
                            </q-date>
                          </q-popup-proxy>
                        </q-icon>
                      </template>
                    </q-input>
                  </div>
                  <div class="col-12 col-md-6">
                    <q-input
                      v-model="stopServiceForm.end_time"
                      filled
                      label="Stop Time *"
                      hint="Select the time when the service stopped"
                      :rules="[val => !!val || 'Stop time is required']"
                    >
                      <template v-slot:append>
                        <q-icon name="access_time" class="cursor-pointer">
                          <q-popup-proxy cover transition-show="scale" transition-hide="scale">
                            <q-time v-model="stopServiceForm.end_time" mask="HH:mm" format24h>
                              <div class="row items-center justify-end">
                                <q-btn v-close-popup label="Close" color="primary" flat />
                              </div>
                            </q-time>
                          </q-popup-proxy>
                        </q-icon>
                      </template>
                    </q-input>
                  </div>
                </div>
                <q-input
                  v-model="stopServiceForm.notes"
                  filled
                  type="textarea"
                  label="Notes (optional)"
                  hint="Any additional notes about stopping this service"
                  rows="3"
                  class="q-mt-md"
                />
                <q-banner v-if="stoppingService" class="q-mt-md bg-info text-white">
                  <template v-slot:avatar>
                    <q-icon name="info" />
                  </template>
                  This will automatically bill the patient for the service usage period.
                </q-banner>
              </q-card-section>

              <q-card-actions align="right">
                <q-btn flat label="Cancel" color="primary" @click="showStopServiceDialog = false" />
                <q-btn
                  flat
                  label="Stop Service"
                  color="negative"
                  @click="confirmStopService"
                  :loading="savingAdditionalService"
                />
              </q-card-actions>
            </q-card>
          </q-dialog>

          <!-- Discharge Patient Dialog -->
          <q-dialog v-model="showDischargeDialog" persistent>
            <q-card style="min-width: 600px; max-width: 800px;">
              <q-card-section>
                <div class="text-h6 glass-text">
                  <q-icon name="exit_to_app" color="negative" class="q-mr-sm" />
                  Discharge Patient
                </div>
                <div v-if="patientInfo" class="text-subtitle2 text-grey-7 q-mt-sm">
                  Patient: <span class="text-weight-bold">{{ patientInfo.patient_name }} {{ patientInfo.patient_surname }}<span v-if="patientInfo.patient_other_names"> {{ patientInfo.patient_other_names }}</span></span>
                  <br />
                  Ward: <span class="text-weight-bold">{{ patientInfo.ward }}</span>
                </div>
              </q-card-section>

              <q-card-section>
                <div class="row q-col-gutter-md">
                  <div class="col-12 col-md-6">
                    <q-select
                      v-model="dischargeForm.discharge_outcome"
                      :options="dischargeOutcomeOptions"
                      filled
                      label="Discharge Outcome *"
                      :rules="[val => !!val || 'Discharge outcome is required']"
                      emit-value
                      map-options
                    >
                      <template v-slot:prepend>
                        <q-icon name="assignment" />
                      </template>
                    </q-select>
                  </div>
                  <div class="col-12 col-md-6">
                    <q-select
                      v-model="dischargeForm.discharge_condition"
                      :options="dischargeConditionOptions"
                      filled
                      label="Patient Condition *"
                      :rules="[val => !!val || 'Patient condition is required']"
                      emit-value
                      map-options
                    >
                      <template v-slot:prepend>
                        <q-icon name="healing" />
                      </template>
                    </q-select>
                  </div>
                </div>

                <q-input
                  v-model="dischargeForm.final_orders"
                  filled
                  type="textarea"
                  label="Final Orders / Doctor's Notes"
                  hint="Doctor's final orders and instructions for the patient"
                  rows="4"
                  class="q-mt-md"
                />

                <q-banner v-if="isPartiallyDischarged" class="q-mt-md bg-warning text-white">
                  <template v-slot:avatar>
                    <q-icon name="warning" />
                  </template>
                  <div class="text-weight-bold">Partial Discharge Already Initiated</div>
                  <div class="text-caption">You can now proceed with final discharge after ensuring all bills are paid.</div>
                </q-banner>

                <q-banner v-if="!isPartiallyDischarged" class="q-mt-md bg-info text-white">
                  <template v-slot:avatar>
                    <q-icon name="info" />
                  </template>
                  <div class="text-weight-bold">Partial Discharge</div>
                  <div class="text-caption">This will initiate partial discharge. You'll need to complete final discharge after all bills are paid.</div>
                </q-banner>

                <q-banner v-if="hasUnpaidBills && isPartiallyDischarged" class="q-mt-md bg-negative text-white">
                  <template v-slot:avatar>
                    <q-icon name="error" />
                  </template>
                  <div class="text-weight-bold">Outstanding Bills</div>
                  <div class="text-caption">Outstanding balance: <strong>GHC {{ unpaidBillAmount.toFixed(2) }}</strong></div>
                  <div class="text-caption q-mt-xs">All bills must be paid before final discharge can be completed.</div>
                  <q-btn
                    flat
                    dense
                    label="Go to Billing"
                    color="white"
                    @click="goToBillingFromDialog"
                    class="q-mt-sm"
                  />
                </q-banner>
              </q-card-section>

              <q-card-actions align="right">
                <q-btn flat label="Cancel" color="primary" @click="showDischargeDialog = false" />
                <q-btn
                  v-if="!isPartiallyDischarged"
                  flat
                  label="Initiate Partial Discharge"
                  color="warning"
                  @click="initiatePartialDischarge"
                  :loading="discharging"
                />
                <q-btn
                  v-if="isPartiallyDischarged"
                  flat
                  label="Final Discharge"
                  color="negative"
                  @click="completeFinalDischarge"
                  :loading="discharging"
                  :disable="hasUnpaidBills"
                />
              </q-card-actions>
            </q-card>
          </q-dialog>

          <!-- Investigations Dialog -->
          <q-dialog v-model="showInvestigationsDialog" maximized>
            <q-card>
              <q-card-section>
                <div class="row items-center">
                  <q-btn flat icon="close" @click="showInvestigationsDialog = false" />
                  <div class="text-h6 glass-text q-ml-md">
                    <q-icon name="science" color="purple" class="q-mr-sm" />
                    Investigations
                  </div>
                </div>
              </q-card-section>

              <q-card-section>
                <q-table
                  :rows="investigations"
                  :columns="[
                    { name: 'procedure_name', label: 'Investigation', field: 'procedure_name', align: 'left', sortable: true },
                    { name: 'investigation_type', label: 'Type', field: 'investigation_type', align: 'center', sortable: true },
                    { name: 'status', label: 'Status', field: 'status', align: 'center', sortable: true },
                    { name: 'requested_by_name', label: 'Requested By', field: 'requested_by_name', align: 'left', sortable: true },
                    { name: 'created_at', label: 'Requested Date', field: 'created_at', align: 'left', sortable: true },
                    { name: 'actions', label: 'Actions', field: 'actions', align: 'center' }
                  ]"
                  :loading="loadingInvestigations"
                  row-key="id"
                  :pagination="{ rowsPerPage: 20 }"
                  flat
                  bordered
                >
                  <template v-slot:body-cell-investigation_type="props">
                    <q-td :props="props">
                      {{ getInvestigationTypeLabel(props.value) }}
                    </q-td>
                  </template>

                  <template v-slot:body-cell-status="props">
                    <q-td :props="props">
                      <q-badge :color="getStatusColor(props.value)" :label="props.value" />
                    </q-td>
                  </template>

                  <template v-slot:body-cell-created_at="props">
                    <q-td :props="props">
                      {{ formatDateTime(props.value) }}
                    </q-td>
                  </template>

                  <template v-slot:body-cell-actions="props">
                    <q-td :props="props">
                      <q-btn
                        v-if="props.row.status === 'completed' && props.row.has_result"
                        flat
                        dense
                        icon="visibility"
                        label="View Result"
                        color="primary"
                        size="sm"
                        @click="viewInvestigationResult(props.row)"
                      />
                      <span v-else class="text-grey-6 text-caption">
                        {{ props.row.status === 'completed' ? 'No result yet' : 'Not completed' }}
                      </span>
                    </q-td>
                  </template>

                  <template v-slot:no-data>
                    <div class="full-width row justify-center items-center text-grey-6 q-pa-md">
                      <div class="text-center">
                        <q-icon name="science" size="48px" class="q-mb-sm" />
                        <div class="text-body1">No investigations found</div>
                      </div>
                    </div>
                  </template>
                </q-table>
              </q-card-section>

              <q-card-actions align="right">
                <q-btn flat label="Close" color="primary" @click="showInvestigationsDialog = false" />
              </q-card-actions>
            </q-card>
          </q-dialog>

          <!-- Investigation Result Dialog -->
          <q-dialog v-model="showResultDialog" maximized>
            <q-card>
              <q-card-section>
                <div class="row items-center">
                  <q-btn flat icon="close" @click="showResultDialog = false" />
                  <div class="text-h6 glass-text q-ml-md">
                    <q-icon name="science" color="purple" class="q-mr-sm" />
                    Investigation Result
                  </div>
                </div>
              </q-card-section>

              <q-card-section v-if="loadingResult" class="text-center q-pa-xl">
                <q-spinner color="primary" size="3em" />
                <div class="text-body1 q-mt-md">Loading result...</div>
              </q-card-section>

              <q-card-section v-else-if="currentResult && investigationDetails">
                <!-- Investigation Details -->
                <q-card class="q-mb-md glass-card" flat bordered>
                  <q-card-section>
                    <div class="text-h6 q-mb-md glass-text">Investigation Details</div>
                    <div class="row q-gutter-md">
                      <div class="col-12 col-md-6">
                        <div class="text-caption text-grey-7">Investigation</div>
                        <div class="text-body1 text-weight-medium">{{ investigationDetails.procedure_name || 'N/A' }}</div>
                      </div>
                      <div class="col-12 col-md-3">
                        <div class="text-caption text-grey-7">Type</div>
                        <div class="text-body1 text-weight-medium">{{ getInvestigationTypeLabel(investigationDetails.investigation_type) }}</div>
                      </div>
                      <div class="col-12 col-md-3">
                        <div class="text-caption text-grey-7">G-DRG Code</div>
                        <div class="text-body1 text-weight-medium">{{ investigationDetails.gdrg_code || 'N/A' }}</div>
                      </div>
                    </div>
                    <div v-if="investigationDetails.notes" class="row q-mt-md">
                      <div class="col-12">
                        <div class="text-caption text-grey-7">Doctor's Notes</div>
                        <div class="text-body2 q-pa-sm" style="background-color: rgba(255, 255, 255, 0.1); border-radius: 4px;">
                          {{ investigationDetails.notes }}
                        </div>
                      </div>
                    </div>
                  </q-card-section>
                </q-card>

                <!-- Result Details -->
                <q-card class="glass-card" flat bordered>
                  <q-card-section>
                    <div class="text-h6 q-mb-md glass-text">Result</div>
                    
                    <!-- Results Text -->
                    <div v-if="currentResult.results_text" class="q-mb-md">
                      <div class="text-caption text-grey-7 q-mb-sm">Results</div>
                      <div class="text-body1 q-pa-md" style="background-color: rgba(255, 255, 255, 0.1); border-radius: 4px; white-space: pre-wrap;">
                        {{ currentResult.results_text }}
                      </div>
                    </div>
                    <div v-else class="q-mb-md">
                      <q-banner class="bg-warning text-white">
                        <template v-slot:avatar>
                          <q-icon name="info" />
                        </template>
                        No text results available for this investigation.
                      </q-banner>
                    </div>

                    <!-- Attachment -->
                    <div v-if="currentResult.attachment_path" class="q-mt-md">
                      <div class="text-caption text-grey-7 q-mb-sm">Attachment</div>
                      <q-btn
                        icon="download"
                        label="Download Attachment"
                        color="primary"
                        @click="downloadResultAttachment(investigationDetails)"
                      />
                    </div>

                    <!-- Result Metadata -->
                    <q-separator class="q-my-md" />
                    <div class="row q-gutter-md">
                      <div class="col-12 col-md-4">
                        <div class="text-caption text-grey-7">Entered By</div>
                        <div class="text-body2 text-weight-medium">{{ currentResult.entered_by_name || 'N/A' }}</div>
                      </div>
                      <div class="col-12 col-md-4">
                        <div class="text-caption text-grey-7">Entered At</div>
                        <div class="text-body2 text-weight-medium">{{ formatDateTime(currentResult.created_at) }}</div>
                      </div>
                      <div v-if="currentResult.updated_by_name" class="col-12 col-md-4">
                        <div class="text-caption text-grey-7">Last Updated By</div>
                        <div class="text-body2 text-weight-medium">{{ currentResult.updated_by_name }}</div>
                        <div class="text-caption text-grey-7 q-mt-xs">Updated At</div>
                        <div class="text-body2">{{ formatDateTime(currentResult.updated_at) }}</div>
                      </div>
                    </div>
                  </q-card-section>
                </q-card>
              </q-card-section>

              <q-card-section v-else class="text-center q-pa-xl">
                <q-icon name="error_outline" size="48px" color="negative" />
                <div class="text-body1 q-mt-md">No result data available</div>
              </q-card-section>

              <q-card-actions align="right">
                <q-btn flat label="Close" color="primary" @click="showResultDialog = false" />
              </q-card-actions>
            </q-card>
          </q-dialog>

          <!-- Additional Service Dialog -->
          <q-dialog v-model="showAdditionalServiceDialog" persistent>
            <q-card style="min-width: 500px; max-width: 700px;">
              <q-card-section>
                <div class="text-h6 glass-text">
                  Start Additional Service
                </div>
              </q-card-section>

              <q-card-section>
                <q-select
                  v-model="additionalServiceForm.service_id"
                  :options="additionalServices.map(s => ({ label: `${s.service_name} - ${s.price_per_unit} GHS/${s.unit_type}`, value: s.id }))"
                  option-label="label"
                  option-value="value"
                  emit-value
                  map-options
                  filled
                  label="Select Service *"
                  hint="Choose an additional service to start"
                  :loading="additionalServices.length === 0"
                />
                <q-input
                  v-model="additionalServiceForm.start_time"
                  filled
                  type="datetime-local"
                  label="Start Time"
                  hint="When did the service start? (defaults to now)"
                  class="q-mt-md"
                />
                <q-input
                  v-model="additionalServiceForm.notes"
                  filled
                  type="textarea"
                  label="Notes (optional)"
                  hint="Any additional notes about this service"
                  rows="3"
                  class="q-mt-md"
                />
              </q-card-section>

              <q-card-actions align="right">
                <q-btn flat label="Cancel" color="primary" @click="showAdditionalServiceDialog = false" />
                <q-btn
                  flat
                  label="Start Service"
                  color="positive"
                  @click="startAdditionalService"
                  :loading="savingAdditionalService"
                />
              </q-card-actions>
            </q-card>
          </q-dialog>

          <!-- Additional sections can be added here for inpatient activities -->
          <!-- Examples: Daily notes, medication schedule, test results, etc. -->
        </q-page>
      </template>

<script setup>
import { ref, onMounted, computed, watch, nextTick } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { useQuasar } from 'quasar';
import { consultationAPI, priceListAPI, billingAPI } from '../services/api';
import { useAuthStore } from '../stores/auth';

const $q = useQuasar();
const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();

const loading = ref(false);
const patientInfo = ref(null);
const discharging = ref(false);
const showDischargeDialog = ref(false);
const dischargeForm = ref({
  discharge_outcome: '',
  discharge_condition: '',
  final_orders: '',
});
const dischargeOutcomeOptions = [
  { label: 'Discharged', value: 'discharged' },
  { label: 'Absconded', value: 'absconded' },
  { label: 'Referred', value: 'referred' },
  { label: 'Died', value: 'died' },
  { label: 'Discharged Against Medical Advice', value: 'discharged_against_medical_advice' },
];
const dischargeConditionOptions = [
  { label: 'Stable', value: 'stable' },
  { label: 'Cured', value: 'cured' },
  { label: 'Delivered', value: 'delivered' },
  { label: 'Improved', value: 'improved' },
  { label: 'Not Improved', value: 'not_improved' },
  { label: 'Died', value: 'died' },
  { label: 'Absconded', value: 'absconded' },
];
const unpaidBillAmount = ref(0);
const hasUnpaidBills = ref(false);
const isPartiallyDischarged = computed(() => patientInfo.value?.partially_discharged_at !== null && patientInfo.value?.partially_discharged_at !== undefined);
const patientBillInfo = ref({
  totalAmount: null,
  paidAmount: null,
  remainingBalance: null,
});
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
const surgeries = ref([]);
const inpatientDiagnoses = ref([]);
const loadingTableData = ref(false);

// Table item dialog
const showTableItemDialog = ref(false);
const currentTableType = ref('');
const tableItemData = ref({});
const savingTableItem = ref(false);
const editingClinicalReviewId = ref(null);
const editingVitalId = ref(null);
const nurseNoteEditor = ref(null);
const selectedTextColor = ref('#000000');
const selectedBgColor = ref('#FFFFFF');

// Vitals graph state
const showVitalsGraphDialog = ref(false);
const vitalsCanvas = ref(null);
const showBP = ref(true);
const showTemperature = ref(true);
const showPulse = ref(true);
const showWeight = ref(true);
const showRR = ref(true);
const showSpO2 = ref(true);
const vitalsForGraph = ref([]);

// Surgery dialog state
const showSurgeryDialog = ref(false);
const editingSurgery = ref(null);
const savingSurgery = ref(false);
const surgeryForm = ref({
  g_drg_code: '',
  surgery_name: '',
  surgery_type: '',
  surgeon_name: '',
  assistant_surgeon: '',
  anesthesia_type: '',
  surgery_date: '',
  surgery_notes: '',
  operative_notes: '',
  post_operative_notes: '',
  complications: '',
  is_completed: false,
});
const allSurgeries = ref([]);
const filteredSurgeryOptions = ref([]);
const selectedSurgery = ref(null);
const loadingSurgeries = ref(false);

// Additional Services state
const additionalServices = ref([]);  // Admin-defined services
const patientAdditionalServices = ref([]);  // Services used by this patient
const showAdditionalServiceDialog = ref(false);
const savingAdditionalService = ref(false);
const additionalServiceForm = ref({
  service_id: null,
  start_time: null,
  notes: '',
});
const stoppingService = ref(null);
const showStopServiceDialog = ref(false);
const stopServiceForm = ref({
  end_date: '',
  end_time: '',
  notes: '',
});

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
    // {
    //   label: 'Vitals',
    //   notes: null,
    //   type: 'vitals',
    //   isTable: true, // Multiple records in inpatient_vitals table
    // },
    {
      label: 'Diagnoses',
      notes: null,
      type: 'diagnoses',
      isTable: true, // Multiple records in inpatient_diagnoses table
    },
    {
      label: 'Admission Notes',
      notes: patientInfo.value?.admission_notes || null,
      type: 'admission_notes',
      isTable: false, // Single field in ward_admissions
    },
    {
      label: 'Surgeries',
      notes: null,
      type: 'surgeries',
      isTable: true, // Multiple records in inpatient_surgeries table
    },
    {
      label: 'Clinical Reviews',
      notes: null,
      type: 'clinical_review',
      isTable: true, // Multiple records in inpatient_clinical_reviews table
    },
    {
      label: 'Additional Services',
      notes: null,
      type: 'additional_services',
      isTable: true, // Multiple records in inpatient_additional_services table
    },
    // {
    //   label: 'Transfers',
    //   notes: null,
    //   type: 'transfers',
    //   isTable: true, // Multiple records in ward_transfers table
    // },
    
    // {
    //   label: 'Diagnoses',
    //   notes: null,
    //   type: 'diagnoses',
    //   isTable: true, // Multiple records in inpatient_diagnoses table
    // },
  ];
});

const wardAdmissionId = computed(() => parseInt(route.params.id));
const encounterId = computed(() => route.query.encounter_id ? parseInt(route.query.encounter_id) : null);
const cardNumber = computed(() => route.query.card_number || null);
const isDischarged = computed(() => patientInfo.value?.discharged_at !== null && patientInfo.value?.discharged_at !== undefined);

const loadPatientInfo = async () => {
  if (!wardAdmissionId.value) return;
  
  loading.value = true;
  try {
    // Load specific ward admission by ID (works for both active and discharged)
    const response = await consultationAPI.getWardAdmission(wardAdmissionId.value);
    console.log('Ward admission API response:', response);
    
    if (response.data) {
      patientInfo.value = response.data;
      console.log('Patient info loaded:', {
        id: patientInfo.value.id,
        card_number: patientInfo.value.patient_card_number,
        bed_id: patientInfo.value.bed_id,
        bed_number: patientInfo.value.bed_number,
        has_bed_number: !!patientInfo.value.bed_number,
        discharged_at: patientInfo.value.discharged_at,
        emergency_contact_name: patientInfo.value.emergency_contact_name,
        emergency_contact_relationship: patientInfo.value.emergency_contact_relationship,
        emergency_contact_number: patientInfo.value.emergency_contact_number,
      });
      
      // Load bill information
      await loadPatientBills();
    } else {
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

const loadPatientBills = async () => {
  if (!patientInfo.value?.encounter_id) {
    patientBillInfo.value = {
      totalAmount: 0,
      paidAmount: 0,
      remainingBalance: 0,
    };
    return;
  }

  try {
    const billsResponse = await billingAPI.getEncounterBills(patientInfo.value.encounter_id);
    const bills = Array.isArray(billsResponse.data) ? billsResponse.data : [];
    
    let totalAmount = 0;
    let paidAmount = 0;
    
    for (const bill of bills) {
      totalAmount += bill.total_amount || 0;
      paidAmount += bill.paid_amount || 0;
    }
    
    const remainingBalance = totalAmount - paidAmount;
    
    patientBillInfo.value = {
      totalAmount: totalAmount,
      paidAmount: paidAmount,
      remainingBalance: remainingBalance > 0.01 ? remainingBalance : 0, // Allow small rounding differences
    };
  } catch (error) {
    console.error('Error loading patient bills:', error);
    // Set to null to indicate error/not loaded
    patientBillInfo.value = {
      totalAmount: null,
      paidAmount: null,
      remainingBalance: null,
    };
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

const addVitals = async () => {
  if (isDischarged.value) {
    $q.notify({
      type: 'negative',
      message: 'Cannot add vitals for a discharged patient',
    });
    return;
  }
  // Ensure vitals are loaded
  if (inpatientVitals.value.length === 0) {
    await loadTableData();
  }
  openTableItemDialog('vitals', null);
};

const editVital = (vital) => {
  if (isDischarged.value) {
    $q.notify({
      type: 'negative',
      message: 'Cannot edit vitals for a discharged patient',
    });
    return;
  }
  // Check permissions
  const canEdit = authStore.user?.id === vital.recorded_by || authStore.userRole === 'Admin';
  if (!canEdit) {
    $q.notify({
      type: 'negative',
      message: 'You do not have permission to edit this vital record',
    });
    return;
  }
  
  // Open dialog for editing
  openTableItemDialog('vitals', {
    id: vital.id,
    temperature: vital.temperature,
    blood_pressure_systolic: vital.blood_pressure_systolic,
    blood_pressure_diastolic: vital.blood_pressure_diastolic,
    pulse: vital.pulse,
    respiratory_rate: vital.respiratory_rate,
    oxygen_saturation: vital.oxygen_saturation,
    weight: vital.weight,
    height: vital.height,
    notes: vital.notes || '',
  });
};

const clearVitalForm = () => {
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
  editingVitalId.value = null;
};

// Vitals graph functions
const formatDateForGraph = (dateString) => {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
};

const plotVitalsGraph = (singleVital) => {
  const allVitalsForGraph = [];
  
  if (singleVital) {
    allVitalsForGraph.push({
      ...singleVital,
      created_at: singleVital.recorded_at,
      bp_systolic: singleVital.blood_pressure_systolic,
      bp_diastolic: singleVital.blood_pressure_diastolic,
      spo2: singleVital.oxygen_saturation,
    });
  }
  
  // Add all previous vitals
  allVitalsForGraph.push(...inpatientVitals.value.map(v => ({
    ...v,
    created_at: v.recorded_at,
    bp_systolic: v.blood_pressure_systolic,
    bp_diastolic: v.blood_pressure_diastolic,
    spo2: v.oxygen_saturation,
  })));
  
  vitalsForGraph.value = allVitalsForGraph.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
  showVitalsGraphDialog.value = true;
  // Wait for dialog to open and canvas to be ready
  nextTick(() => {
    setTimeout(() => {
      drawVitalsGraph();
    }, 300);
  });
};

const plotAllVitalsGraph = () => {
  const allVitalsForGraph = inpatientVitals.value.map(v => ({
    ...v,
    created_at: v.recorded_at,
    bp_systolic: v.blood_pressure_systolic,
    bp_diastolic: v.blood_pressure_diastolic,
    spo2: v.oxygen_saturation,
  }));
  
  vitalsForGraph.value = allVitalsForGraph.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
  showVitalsGraphDialog.value = true;
  // Wait for dialog to open and canvas to be ready
  nextTick(() => {
    setTimeout(() => {
      drawVitalsGraph();
    }, 300);
  });
};

const drawVitalsGraph = () => {
  if (!vitalsCanvas.value || vitalsForGraph.value.length === 0) {
    // If canvas isn't ready yet, try again after a short delay
    if (showVitalsGraphDialog.value) {
      setTimeout(() => {
        drawVitalsGraph();
      }, 100);
    }
    return;
  }
  
  const canvas = vitalsCanvas.value;
  const ctx = canvas.getContext('2d');
  const container = canvas.parentElement;
  
  // Set canvas size
  const dpr = window.devicePixelRatio || 1;
  const rect = container.getBoundingClientRect();
  canvas.width = rect.width * dpr;
  canvas.height = rect.height * dpr;
  ctx.scale(dpr, dpr);
  canvas.style.width = rect.width + 'px';
  canvas.style.height = rect.height + 'px';
  
  // Clear canvas
  ctx.clearRect(0, 0, rect.width, rect.height);
  
  const width = rect.width;
  const height = rect.height;
  const padding = 60;
  const graphWidth = width - padding * 2;
  const graphHeight = height - padding * 2;
  
  // Prepare data - only include vitals that have values
  const dates = vitalsForGraph.value.map(v => new Date(v.created_at));
  const minDate = new Date(Math.min(...dates));
  const maxDate = new Date(Math.max(...dates));
  
  // Find min/max values for scaling
  const getValues = (field) => vitalsForGraph.value.filter(v => v[field] != null).map(v => v[field]);
  
  const minMax = {
    bp: {
      min: Math.min(...getValues('bp_systolic'), ...getValues('bp_diastolic'), 0),
      max: Math.max(...getValues('bp_systolic'), ...getValues('bp_diastolic'), 200)
    },
    temperature: {
      min: Math.min(...getValues('temperature'), 35),
      max: Math.max(...getValues('temperature'), 42)
    },
    pulse: {
      min: Math.min(...getValues('pulse'), 50),
      max: Math.max(...getValues('pulse'), 120)
    },
    weight: {
      min: Math.min(...getValues('weight'), 0),
      max: Math.max(...getValues('weight'), 150)
    },
    rr: {
      min: Math.min(...getValues('respiratory_rate'), 10),
      max: Math.max(...getValues('respiratory_rate'), 30)
    },
    spo2: {
      min: Math.min(...getValues('spo2'), 90),
      max: Math.max(...getValues('spo2'), 100)
    }
  };
  
  // Draw graph paper background (grid)
  ctx.fillStyle = '#f5f5f5';
  ctx.fillRect(0, 0, width, height);
  
  // Fine grid (like graph paper)
  ctx.strokeStyle = '#e0e0e0';
  ctx.lineWidth = 0.5;
  // Vertical lines
  for (let i = 0; i <= 20; i++) {
    const x = padding + (graphWidth / 20) * i;
    ctx.beginPath();
    ctx.moveTo(x, padding);
    ctx.lineTo(x, height - padding);
    ctx.stroke();
  }
  // Horizontal lines
  for (let i = 0; i <= 20; i++) {
    const y = padding + (graphHeight / 20) * i;
    ctx.beginPath();
    ctx.moveTo(padding, y);
    ctx.lineTo(width - padding, y);
    ctx.stroke();
  }
  
  // Major grid lines (bolder)
  ctx.strokeStyle = '#ccc';
  ctx.lineWidth = 1;
  for (let i = 0; i <= 10; i++) {
    const y = padding + (graphHeight / 10) * i;
    ctx.beginPath();
    ctx.moveTo(padding, y);
    ctx.lineTo(width - padding, y);
    ctx.stroke();
  }
  
  // Draw axes
  ctx.strokeStyle = '#333';
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(padding, padding);
  ctx.lineTo(padding, height - padding);
  ctx.lineTo(width - padding, height - padding);
  ctx.stroke();
  
  // Y-axis labels with actual values
  ctx.fillStyle = '#666';
  ctx.font = '11px Arial';
  ctx.textAlign = 'right';
  ctx.textBaseline = 'middle';
  
  // Calculate which vital signs to show Y-axis labels for
  const activeVitals = [];
  if (showBP.value && (getValues('bp_systolic').length > 0 || getValues('bp_diastolic').length > 0)) {
    activeVitals.push({ key: 'bp', min: minMax.bp.min, max: minMax.bp.max, label: 'BP (mmHg)' });
  }
  if (showTemperature.value && getValues('temperature').length > 0) {
    activeVitals.push({ key: 'temp', min: minMax.temperature.min, max: minMax.temperature.max, label: 'Temp (°C)' });
  }
  if (showPulse.value && getValues('pulse').length > 0) {
    activeVitals.push({ key: 'pulse', min: minMax.pulse.min, max: minMax.pulse.max, label: 'Pulse (bpm)' });
  }
  if (showWeight.value && getValues('weight').length > 0) {
    activeVitals.push({ key: 'weight', min: minMax.weight.min, max: minMax.weight.max, label: 'Weight (kg)' });
  }
  if (showRR.value && getValues('respiratory_rate').length > 0) {
    activeVitals.push({ key: 'rr', min: minMax.rr.min, max: minMax.rr.max, label: 'RR (/min)' });
  }
  if (showSpO2.value && getValues('spo2').length > 0) {
    activeVitals.push({ key: 'spo2', min: minMax.spo2.min, max: minMax.spo2.max, label: 'SpO2 (%)' });
  }
  
  // Draw Y-axis labels for the first active vital (primary scale)
  if (activeVitals.length > 0) {
    const primaryVital = activeVitals[0];
    for (let i = 0; i <= 10; i++) {
      const y = padding + (graphHeight / 10) * i;
      const value = primaryVital.max - ((primaryVital.max - primaryVital.min) / 10) * i;
      ctx.fillText(value.toFixed(primaryVital.key === 'temp' ? 1 : 0), padding - 10, y);
    }
  }
  
  // X-axis labels (dates)
  ctx.fillStyle = '#666';
  ctx.font = '10px Arial';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'top';
  const labelCount = Math.min(vitalsForGraph.value.length, 10);
  for (let i = 0; i < vitalsForGraph.value.length; i++) {
    if (i % Math.ceil(vitalsForGraph.value.length / labelCount) === 0 || i === vitalsForGraph.value.length - 1) {
      const x = padding + (graphWidth / (vitalsForGraph.value.length - 1 || 1)) * i;
      ctx.fillText(formatDateForGraph(vitalsForGraph.value[i].created_at), x, height - padding + 10);
    }
  }
  
  // Draw axis labels
  ctx.fillStyle = '#333';
  ctx.font = '12px Arial';
  ctx.textAlign = 'center';
  ctx.fillText('Date', width / 2, height - 15);
  ctx.save();
  ctx.translate(15, height / 2);
  ctx.rotate(-Math.PI / 2);
  ctx.fillText(activeVitals.length > 0 ? activeVitals[0].label : 'Values', 0, 0);
  ctx.restore();
  
  // Helper function to normalize value
  const normalize = (value, min, max) => {
    if (max === min) return 0.5;
    return (value - min) / (max - min);
  };
  
  // Plot data series
  const colors = {
    bp_systolic: '#ff4444',
    bp_diastolic: '#cc0000',
    temperature: '#ff8800',
    pulse: '#4488ff',
    weight: '#44aa44',
    rr: '#aa44aa',
    spo2: '#44aaaa'
  };
  
  const plotSeries = (field, color, minMaxKey) => {
    ctx.strokeStyle = color;
    ctx.lineWidth = 2.5;
    ctx.beginPath();
    let firstPoint = true;
    
    vitalsForGraph.value.forEach((vital, i) => {
      if (vital[field] != null) {
        const x = padding + (graphWidth / (vitalsForGraph.value.length - 1 || 1)) * i;
        const y = padding + graphHeight * (1 - normalize(vital[field], minMax[minMaxKey].min, minMax[minMaxKey].max));
        if (firstPoint) {
          ctx.moveTo(x, y);
          firstPoint = false;
        } else {
          ctx.lineTo(x, y);
        }
      }
    });
    ctx.stroke();
    
    // Draw points and values
    vitalsForGraph.value.forEach((vital, i) => {
      if (vital[field] != null) {
        const x = padding + (graphWidth / (vitalsForGraph.value.length - 1 || 1)) * i;
        const y = padding + graphHeight * (1 - normalize(vital[field], minMax[minMaxKey].min, minMax[minMaxKey].max));
        
        // Draw point
        ctx.fillStyle = color;
        ctx.strokeStyle = '#fff';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(x, y, 5, 0, 2 * Math.PI);
        ctx.fill();
        ctx.stroke();
        
        // Draw value label above point
        ctx.fillStyle = color;
        ctx.font = 'bold 10px Arial';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'bottom';
        const valueText = vital[field].toFixed(field === 'temperature' ? 1 : 0);
        // Add unit suffix
        let unit = '';
        if (field === 'bp_systolic' || field === 'bp_diastolic') unit = '';
        else if (field === 'temperature') unit = '°C';
        else if (field === 'pulse') unit = 'bpm';
        else if (field === 'weight') unit = 'kg';
        else if (field === 'respiratory_rate') unit = '/min';
        else if (field === 'spo2') unit = '%';
        
        // Draw text with background for readability
        const textY = y - 8;
        const metrics = ctx.measureText(valueText + unit);
        const textWidth = metrics.width;
        const textPadding = 4;
        
        // Background rectangle
        ctx.fillStyle = 'rgba(255, 255, 255, 0.9)';
        ctx.fillRect(x - textWidth / 2 - textPadding, textY - 12, textWidth + textPadding * 2, 14);
        
        // Text
        ctx.fillStyle = color;
        ctx.fillText(valueText + unit, x, textY);
      }
    });
  };
  
  // Plot each series
  if (showBP.value) {
    plotSeries('bp_systolic', colors.bp_systolic, 'bp');
    plotSeries('bp_diastolic', colors.bp_diastolic, 'bp');
  }
  if (showTemperature.value) plotSeries('temperature', colors.temperature, 'temperature');
  if (showPulse.value) plotSeries('pulse', colors.pulse, 'pulse');
  if (showWeight.value) plotSeries('weight', colors.weight, 'weight');
  if (showRR.value) plotSeries('respiratory_rate', colors.rr, 'rr');
  if (showSpO2.value) plotSeries('spo2', colors.spo2, 'spo2');
  
  // Legend
  ctx.font = '12px Arial';
  ctx.textAlign = 'left';
  ctx.textBaseline = 'top';
  let legendY = 20;
  if (showBP.value) {
    ctx.fillStyle = colors.bp_systolic;
    ctx.fillText('BP Systolic', width - padding - 200, legendY);
    legendY += 15;
    ctx.fillStyle = colors.bp_diastolic;
    ctx.fillText('BP Diastolic', width - padding - 200, legendY);
    legendY += 20;
  }
  if (showTemperature.value) {
    ctx.fillStyle = colors.temperature;
    ctx.fillText('Temperature (°C)', width - padding - 200, legendY);
    legendY += 20;
  }
  if (showPulse.value) {
    ctx.fillStyle = colors.pulse;
    ctx.fillText('Pulse (bpm)', width - padding - 200, legendY);
    legendY += 20;
  }
  if (showWeight.value) {
    ctx.fillStyle = colors.weight;
    ctx.fillText('Weight (kg)', width - padding - 200, legendY);
    legendY += 20;
  }
  if (showRR.value) {
    ctx.fillStyle = colors.rr;
    ctx.fillText('Respiratory Rate (/min)', width - padding - 200, legendY);
    legendY += 20;
  }
  if (showSpO2.value) {
    ctx.fillStyle = colors.spo2;
    ctx.fillText('SpO2 (%)', width - padding - 200, legendY);
  }
};

// Watch for toggle changes to redraw graph
watch([showBP, showTemperature, showPulse, showWeight, showRR, showSpO2], () => {
  if (showVitalsGraphDialog.value) {
    nextTick(() => {
      drawVitalsGraph();
    });
  }
});

// Watch for dialog opening to draw graph
watch(showVitalsGraphDialog, (isOpen) => {
  if (isOpen && vitalsForGraph.value.length > 0) {
    nextTick(() => {
      setTimeout(() => {
        drawVitalsGraph();
      }, 100);
    });
  }
});

const addNurseNote = () => {
  openTableItemDialog('nurses_notes', null);
};

const viewNurseMidDocumentation = () => {
  if (wardAdmissionId.value) {
    router.push(`/ipd/nurse-mid-documentation/${wardAdmissionId.value}`);
  }
};

const viewClinicalReview = async () => {
  if (!wardAdmissionId.value) return;
  
  $q.dialog({
    title: 'Create Clinical Review',
    message: 'Do you want to create a new clinical review? This will open in a new tab where you can add diagnoses, prescriptions, and investigations.',
    cancel: true,
    persistent: true,
  }).onOk(async () => {
    try {
      // Create a new clinical review
      const response = await consultationAPI.createInpatientClinicalReview(wardAdmissionId.value, {
        review_notes: '',
      });
      
      const clinicalReviewId = response.data.id;
      
      // Open in new tab
      const url = router.resolve({
        name: 'ClinicalReview',
        params: { id: wardAdmissionId.value },
        query: { reviewId: clinicalReviewId }
      }).href;
      
      window.open(url, '_blank');
      
      // Reload table data to show the new review
      await loadTableData();
      
      $q.notify({
        type: 'positive',
        message: 'Clinical review created successfully',
      });
    } catch (error) {
      console.error('Error creating clinical review:', error);
      $q.notify({
        type: 'negative',
        message: error.response?.data?.detail || 'Failed to create clinical review',
      });
    }
  });
};

const viewPrescriptions = () => {
  if (encounterId.value) {
    router.push(`/consultation/${encounterId.value}#prescriptions`);
  } else if (patientInfo.value?.encounter_id) {
    router.push(`/consultation/${patientInfo.value.encounter_id}#prescriptions`);
  }
};

const showInvestigationsDialog = ref(false);
const investigations = ref([]);
const loadingInvestigations = ref(false);
const showResultDialog = ref(false);
const currentResult = ref(null);
const loadingResult = ref(false);
const investigationDetails = ref(null);

const viewInvestigations = async () => {
  if (!wardAdmissionId.value) {
    $q.notify({
      type: 'negative',
      message: 'Ward admission ID not found',
    });
    return;
  }
  
  try {
    loadingInvestigations.value = true;
    const response = await consultationAPI.getAllInpatientInvestigations(wardAdmissionId.value);
    investigations.value = response.data || [];
    showInvestigationsDialog.value = true;
  } catch (error) {
    console.error('Error loading investigations:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to load investigations',
    });
  } finally {
    loadingInvestigations.value = false;
  }
};

const viewInvestigationResult = async (investigation) => {
  if (!investigation.has_result || investigation.status !== 'completed') {
    return;
  }
  
  try {
    loadingResult.value = true;
    investigationDetails.value = investigation;
    
    let resultResponse = null;
    if (investigation.investigation_type === 'lab') {
      resultResponse = await consultationAPI.getLabResult(investigation.id);
    } else if (investigation.investigation_type === 'scan') {
      resultResponse = await consultationAPI.getScanResult(investigation.id);
    } else if (investigation.investigation_type === 'xray') {
      resultResponse = await consultationAPI.getXrayResult(investigation.id);
    }
    
    if (resultResponse && resultResponse.data) {
      currentResult.value = resultResponse.data;
      showResultDialog.value = true;
    } else {
      $q.notify({
        type: 'warning',
        message: 'Result not found',
      });
    }
  } catch (error) {
    console.error('Error loading result:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to load result',
    });
  } finally {
    loadingResult.value = false;
  }
};

const downloadResultAttachment = async (investigation) => {
  try {
    let downloadResponse = null;
    if (investigation.investigation_type === 'lab') {
      downloadResponse = await consultationAPI.downloadLabResultAttachment(investigation.id);
    } else if (investigation.investigation_type === 'scan') {
      downloadResponse = await consultationAPI.downloadScanResultAttachment(investigation.id);
    } else if (investigation.investigation_type === 'xray') {
      downloadResponse = await consultationAPI.downloadXrayResultAttachment(investigation.id);
    }
    
    if (downloadResponse && downloadResponse.data) {
      // Create a blob URL and trigger download
      const contentType = downloadResponse.headers?.['content-type'] || downloadResponse.headers?.['Content-Type'] || 'application/octet-stream';
      const blob = new Blob([downloadResponse.data], { type: contentType });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      
      // Extract filename from Content-Disposition header or use default
      const contentDisposition = downloadResponse.headers?.['content-disposition'] || downloadResponse.headers?.['Content-Disposition'];
      let filename = `result_attachment_${investigation.id}`;
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/i);
        if (filenameMatch && filenameMatch[1]) {
          filename = filenameMatch[1].replace(/['"]/g, '');
        }
      }
      
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      $q.notify({
        type: 'positive',
        message: 'Download started',
      });
    }
  } catch (error) {
    console.error('Error downloading attachment:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to download attachment',
    });
  }
};

const getStatusColor = (status) => {
  switch (status) {
    case 'completed':
      return 'positive';
    case 'confirmed':
      return 'info';
    case 'requested':
      return 'warning';
    case 'cancelled':
      return 'negative';
    default:
      return 'grey';
  }
};

const getInvestigationTypeLabel = (type) => {
  switch (type) {
    case 'lab':
      return 'Lab';
    case 'scan':
      return 'Scan';
    case 'xray':
      return 'X-ray';
    default:
      return type;
  }
};


const viewBilling = () => {
  if (encounterId.value) {
    router.push(`/billing/${encounterId.value}`);
  } else if (patientInfo.value?.encounter_id) {
    router.push(`/billing/${patientInfo.value.encounter_id}`);
  }
};

const goToBillingFromDialog = () => {
  showDischargeDialog.value = false;
  viewBilling();
};

const checkBills = async () => {
  if (!patientInfo.value?.encounter_id) {
    hasUnpaidBills.value = false;
    unpaidBillAmount.value = 0;
    return;
  }

  try {
    const billsResponse = await billingAPI.getEncounterBills(patientInfo.value.encounter_id);
    const bills = Array.isArray(billsResponse.data) ? billsResponse.data : [];
    
    let totalUnpaid = 0;
    for (const bill of bills) {
      if (!bill.is_paid) {
        const remaining = (bill.total_amount || 0) - (bill.paid_amount || 0);
        if (remaining > 0.01) {
          totalUnpaid += remaining;
        }
      }
    }
    
    hasUnpaidBills.value = totalUnpaid > 0.01;
    unpaidBillAmount.value = totalUnpaid;
  } catch (error) {
    console.error('Error checking bills:', error);
    // Don't block discharge if bill check fails, but show warning
    hasUnpaidBills.value = false;
    unpaidBillAmount.value = 0;
  }
};

const viewTreatmentSheet = () => {
  if (wardAdmissionId.value) {
    router.push(`/ipd/treatment-sheet/${wardAdmissionId.value}`);
  }
};

const dischargePatient = async () => {
  if (!wardAdmissionId.value) return;
  
  // Reset form
  dischargeForm.value = {
    discharge_outcome: patientInfo.value?.discharge_outcome || '',
    discharge_condition: patientInfo.value?.discharge_condition || '',
    final_orders: patientInfo.value?.final_orders || '',
  };
  
  // Check bills if partially discharged
  if (isPartiallyDischarged.value) {
    await checkBills();
  }
  
  showDischargeDialog.value = true;
};

const initiatePartialDischarge = async () => {
  if (!dischargeForm.value.discharge_outcome || !dischargeForm.value.discharge_condition) {
    $q.notify({
      type: 'warning',
      message: 'Please select both discharge outcome and patient condition',
    });
    return;
  }

  discharging.value = true;
  try {
    await consultationAPI.partialDischargePatient(wardAdmissionId.value, {
      discharge_outcome: dischargeForm.value.discharge_outcome,
      discharge_condition: dischargeForm.value.discharge_condition,
      final_orders: dischargeForm.value.final_orders || null,
    });
    
    $q.notify({
      type: 'positive',
      message: 'Partial discharge initiated successfully. Please ensure all bills are paid before final discharge.',
      timeout: 5000,
    });
    
    // Reload patient info to get updated partial discharge status
    await loadPatientInfo();
    
    // Check bills now
    await checkBills();
    
    // Keep dialog open for final discharge
  } catch (error) {
    console.error('Error initiating partial discharge:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to initiate partial discharge',
    });
  } finally {
    discharging.value = false;
  }
};

const completeFinalDischarge = async () => {
  if (!dischargeForm.value.discharge_outcome || !dischargeForm.value.discharge_condition) {
    $q.notify({
      type: 'warning',
      message: 'Please select both discharge outcome and patient condition',
    });
    return;
  }

  // Check bills again before final discharge
  await checkBills();
  
  if (hasUnpaidBills.value) {
    $q.notify({
      type: 'negative',
      message: `Cannot discharge patient. Outstanding bills amount to GHC ${unpaidBillAmount.value.toFixed(2)}. All bills must be paid before discharge.`,
      timeout: 5000,
    });
    return;
  }

  discharging.value = true;
  try {
    await consultationAPI.dischargePatient(wardAdmissionId.value, {
      discharge_outcome: dischargeForm.value.discharge_outcome,
      discharge_condition: dischargeForm.value.discharge_condition,
      final_orders: dischargeForm.value.final_orders || null,
    });
    
    $q.notify({
      type: 'positive',
      message: 'Patient discharged successfully',
    });
    
    showDischargeDialog.value = false;
    // Redirect back to ward page
    router.push('/ipd/doctor-nursing-station');
  } catch (error) {
    console.error('Error discharging patient:', error);
    const errorMessage = error.response?.data?.detail || 'Failed to discharge patient';
    
    // If error mentions bills, check bills again
    if (errorMessage.includes('bill') || errorMessage.includes('paid')) {
      await checkBills();
    }
    
    $q.notify({
      type: 'negative',
      message: errorMessage,
      timeout: 5000,
    });
  } finally {
    discharging.value = false;
  }
};

const revertPartialDischarge = async () => {
  if (!wardAdmissionId.value) return;
  
  $q.dialog({
    title: 'Revert Partial Discharge',
    message: 'Are you sure you want to revert the partial discharge? This will allow you to add more services before discharging again.',
    cancel: true,
    persistent: true
  }).onOk(async () => {
    discharging.value = true;
    try {
      await consultationAPI.revertPartialDischarge(wardAdmissionId.value);
      
      $q.notify({
        type: 'positive',
        message: 'Partial discharge reverted successfully. You can now add services and discharge again when ready.',
        timeout: 5000,
      });
      
      // Reload patient info to update status
      await loadPatientInfo();
    } catch (error) {
      console.error('Error reverting partial discharge:', error);
      $q.notify({
        type: 'negative',
        message: error.response?.data?.detail || 'Failed to revert partial discharge',
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

// Determine if a note was created during night shift (8 PM to 7:29 AM)
const isNightShift = (dateString) => {
  if (!dateString) return false;
  const date = new Date(dateString);
  // Get local time (not UTC) - JavaScript Date automatically converts UTC to local
  const hours = date.getHours();
  const minutes = date.getMinutes();
  const timeInMinutes = hours * 60 + minutes;
  
  // Night shift: 8:00 PM (20:00) to 7:29 AM (7:29)
  // Day shift: 7:30 AM (7:30) to 8:00 PM (20:00)
  const nightShiftStart = 20 * 60; // 8:00 PM = 1200 minutes
  const dayShiftStart = 7 * 60 + 30; // 7:30 AM = 450 minutes
  
  // If time is between 8 PM (20:00) and midnight (00:00), it's night shift
  if (timeInMinutes >= nightShiftStart) {
    return true;
  }
  // If time is between midnight (00:00) and 7:29 AM, it's night shift
  if (timeInMinutes < dayShiftStart) {
    return true;
  }
  // Otherwise, it's day shift (7:30 AM to 8:00 PM)
  return false;
};

// Process HTML content to override inline color styles based on shift
const processNoteHtml = (note) => {
  if (!note.notes) return '';
  
  const nightShift = isNightShift(note.created_at);
  const textColor = nightShift ? '#d32f2f' : '#000000'; // Red for night, black for day
  
  // Remove or replace inline color styles in the HTML
  let processedHtml = note.notes;
  
  // Replace all inline color styles with our shift-based color
  // This regex matches style="..." and removes/replaces color properties
  processedHtml = processedHtml.replace(
    /style="([^"]*)"/gi,
    (match, styleContent) => {
      // Remove color property from style
      let newStyle = styleContent
        .replace(/color\s*:\s*[^;]+;?/gi, '')
        .replace(/;\s*;/g, ';')
        .trim();
      
      // Add our shift-based color
      newStyle = newStyle ? `${newStyle}; color: ${textColor} !important;` : `color: ${textColor} !important;`;
      
      return `style="${newStyle}"`;
    }
  );
  
  // Also add color to elements without style attributes
  // Wrap the entire content in a div with the shift color
  return `<div style="color: ${textColor} !important;">${processedHtml}</div>`;
};

// Get style for nurse note based on shift and strikethrough status
const getNoteStyle = (note) => {
  let style = '';
  
  // Build style string
  if (note.strikethrough === 1) {
    style += 'text-decoration: line-through; opacity: 0.6;';
  }
  
  return style;
};

// Get CSS class for nurse note based on shift
const getNoteClass = (note) => {
  const nightShift = isNightShift(note.created_at);
  return {
    'night-shift-note': nightShift,
    'day-shift-note': !nightShift,
    'strikethrough-note': note.strikethrough === 1
  };
};

// Debug function to check time calculation
const debugNoteTime = (note) => {
  if (!note.created_at) return;
  const date = new Date(note.created_at);
  const hours = date.getHours();
  const minutes = date.getMinutes();
  const nightShift = isNightShift(note.created_at);
  console.log('Note time:', date.toLocaleString(), 'Hours:', hours, 'Minutes:', minutes, 'Night shift:', nightShift);
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
    case 'surgeries':
      return surgeries.value.length;
    case 'additional_services':
      return patientAdditionalServices.value.length;
    case 'diagnoses':
      return inpatientDiagnoses.value.length;
    default:
      return 0;
  }
};

const loadTableData = async () => {
  if (!wardAdmissionId.value) return;
  
  loadingTableData.value = true;
  
  // Load each data source independently so one failure doesn't prevent others from loading
  const loadData = async (apiCall, defaultValue = []) => {
    try {
      const res = await apiCall();
      return Array.isArray(res.data) ? res.data : defaultValue;
    } catch (error) {
      console.error('Error loading data:', error);
      return defaultValue;
    }
  };
  
  try {
    const [notes, midDocs, vitals, reviews, transfersData, surgeriesData, patientServices, diagnoses] = await Promise.all([
      loadData(() => consultationAPI.getNurseNotes(wardAdmissionId.value)),
      loadData(() => consultationAPI.getNurseMidDocumentations(wardAdmissionId.value)),
      loadData(() => consultationAPI.getInpatientVitals(wardAdmissionId.value)),
      loadData(() => consultationAPI.getInpatientClinicalReviews(wardAdmissionId.value)),
      loadData(() => consultationAPI.getWardAdmissionTransfers(wardAdmissionId.value)),
      loadData(() => consultationAPI.getInpatientSurgeries(wardAdmissionId.value)),
      loadData(() => consultationAPI.getInpatientAdditionalServices(wardAdmissionId.value)),
      loadData(() => consultationAPI.getAllInpatientDiagnoses(wardAdmissionId.value)),
    ]);
    
    nurseNotes.value = notes;
    nurseMidDocumentations.value = midDocs;
    inpatientVitals.value = vitals;
    clinicalReviews.value = reviews;
    transfers.value = transfersData;
    surgeries.value = surgeriesData;
    patientAdditionalServices.value = patientServices;
    inpatientDiagnoses.value = diagnoses;
    
    // Debug logging
    console.log('Loaded surgeries:', surgeries.value);
    console.log('Surgeries count:', surgeries.value.length);
  } catch (error) {
    console.error('Error loading table data:', error);
    $q.notify({
      type: 'warning',
      message: 'Some data may not have loaded. Please refresh the page.',
    });
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
    // Store the item ID for editing
    if (type === 'clinical_review') {
      editingClinicalReviewId.value = item.id;
    } else if (type === 'vitals') {
      editingVitalId.value = item.id;
    }
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
        editingVitalId.value = null;
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
    // Reset editing ID for new items
    if (type === 'clinical_review') {
      editingClinicalReviewId.value = null;
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
        if (editingVitalId.value) {
          // Update existing vital
          response = await consultationAPI.updateInpatientVital(wardAdmissionId.value, editingVitalId.value, tableItemData.value);
        } else {
          // Create new vital
          response = await consultationAPI.createInpatientVital(wardAdmissionId.value, tableItemData.value);
        }
        break;
      case 'clinical_review':
        if (editingClinicalReviewId.value) {
          // Update existing review
          response = await consultationAPI.updateInpatientClinicalReview(wardAdmissionId.value, editingClinicalReviewId.value, { review_notes: tableItemData.value.notes });
        } else {
          // Create new review
          response = await consultationAPI.createInpatientClinicalReview(wardAdmissionId.value, { review_notes: tableItemData.value.notes });
        }
        break;
    }
    
    const isUpdating = (currentTableType.value === 'clinical_review' && editingClinicalReviewId.value) ||
                       (currentTableType.value === 'vitals' && editingVitalId.value);
    $q.notify({
      type: 'positive',
      message: `${documentationTypeLabels[currentTableType.value]} ${isUpdating ? 'updated' : 'saved'} successfully`,
    });
    showTableItemDialog.value = false;
    editingClinicalReviewId.value = null;
    editingVitalId.value = null;
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
  } else if (type === 'clinical_review') {
    // Show clinical reviews in a dialog with edit buttons
    if (clinicalReviews.value.length === 0) {
      $q.notify({
        type: 'info',
        message: 'No clinical reviews found',
      });
      return;
    }
    
    // Create a list of clinical reviews with edit buttons
    const reviewList = clinicalReviews.value.map(review => {
      const canEdit = authStore.user?.id === review.reviewed_by || authStore.userRole === 'Admin';
      return {
        id: review.id,
        notes: review.review_notes || 'No notes',
        reviewed_by: review.reviewed_by_name || 'Unknown',
        reviewed_at: review.reviewed_at,
        canEdit: canEdit,
      };
    });
    
    $q.dialog({
      title: 'Clinical Reviews',
      message: reviewList.map((r, idx) => 
        `${idx + 1}. Reviewed by: ${r.reviewed_by}\n` +
        `   Date: ${formatDateTime(r.reviewed_at)}\n` +
        `   Notes: ${r.notes.substring(0, 100)}${r.notes.length > 100 ? '...' : ''}`
      ).join('\n\n'),
      persistent: true,
      ok: {
        label: 'Close',
        flat: true,
      },
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

const editClinicalReview = (review) => {
  if (isDischarged.value) {
    $q.notify({
      type: 'negative',
      message: 'Cannot edit clinical reviews for a discharged patient',
    });
    return;
  }
  // Check permissions
  const canEdit = authStore.user?.id === review.reviewed_by || authStore.userRole === 'Admin';
  if (!canEdit) {
    $q.notify({
      type: 'negative',
      message: 'You do not have permission to edit this clinical review',
    });
    return;
  }
  
  // Open dialog for editing
  openTableItemDialog('clinical_review', {
    id: review.id,
    notes: review.review_notes || '',
    review_notes: review.review_notes || '',
  });
};

const openClinicalReview = (reviewId) => {
  // Open clinical review in new tab
  const url = router.resolve({
    name: 'ClinicalReview',
    params: { id: wardAdmissionId.value },
    query: { reviewId: reviewId }
  }).href;
  
  window.open(url, '_blank');
};

const deleteClinicalReview = async (review) => {
  // Only Admin can delete
  if (authStore.userRole !== 'Admin') {
    $q.notify({
      type: 'negative',
      message: 'Only Admin can delete clinical reviews',
    });
    return;
  }
  
  $q.dialog({
    title: 'Confirm Delete',
    message: `Are you sure you want to delete this clinical review? This action cannot be undone.`,
    cancel: true,
    persistent: true,
  }).onOk(async () => {
    try {
      await consultationAPI.deleteInpatientClinicalReview(wardAdmissionId.value, review.id);
      $q.notify({
        type: 'positive',
        message: 'Clinical review deleted successfully',
      });
      await loadTableData();
    } catch (error) {
      console.error('Error deleting clinical review:', error);
      $q.notify({
        type: 'negative',
        message: error.response?.data?.detail || 'Failed to delete clinical review',
      });
    }
  });
};

onMounted(() => {
  loadPatientInfo();
  loadTableData();
});

// Computed for isAdmin
const isAdmin = computed(() => authStore.userRole === 'Admin');

// Surgery functions
const loadSurgeries = async () => {
  try {
    loadingSurgeries.value = true;
    const res = await priceListAPI.searchPriceItems(null, null, 'surgery');
    
    // Handle both direct array response and nested data property
    let surgeriesData = res.data;
    if (!Array.isArray(surgeriesData) && res.data?.data) {
      surgeriesData = res.data.data;
    }
    
    if (surgeriesData && Array.isArray(surgeriesData)) {
      const mappedSurgeries = surgeriesData
        .filter(item => {
          // Only include active surgeries with file_type === 'surgery' (exclude day surgery)
          return item.is_active !== false && item.file_type === 'surgery';
        })
        .map(item => {
          const surgeryCode = item.g_drg_code || item.item_code || '';
          const surgeryName = item.service_name || 'Unknown Surgery';
          const serviceType = item.service_type || '';
          
          return {
            label: `${surgeryName} (${surgeryCode})`,
            value: {
              code: surgeryCode,
              name: surgeryName,
              service_type: serviceType,
              fullItem: item
            }
          };
        });
      
      allSurgeries.value = mappedSurgeries;
      filteredSurgeryOptions.value = allSurgeries.value.slice(0, 50); // Show first 50 by default
    } else {
      allSurgeries.value = [];
      filteredSurgeryOptions.value = [];
    }
  } catch (error) {
    console.error('Error loading surgeries:', error);
    allSurgeries.value = [];
    filteredSurgeryOptions.value = [];
  } finally {
    loadingSurgeries.value = false;
  }
};

const filterSurgeries = (val, update) => {
  if (val === '') {
    update(() => {
      filteredSurgeryOptions.value = allSurgeries.value.slice(0, 50);
    });
    return;
  }

  update(() => {
    const needle = val.toLowerCase();
    filteredSurgeryOptions.value = allSurgeries.value.filter(
      s => {
        const labelMatch = s.label.toLowerCase().indexOf(needle) > -1;
        const codeMatch = s.value.code?.toLowerCase().indexOf(needle) > -1;
        const nameMatch = s.value.name?.toLowerCase().indexOf(needle) > -1;
        return labelMatch || codeMatch || nameMatch;
      }
    ).slice(0, 100); // Limit to 100 results
  });
};

const onSurgerySelected = (surgery) => {
  if (surgery && typeof surgery === 'object') {
    surgeryForm.value.surgery_name = surgery.name;
    surgeryForm.value.g_drg_code = surgery.code;
    if (surgery.service_type) {
      surgeryForm.value.surgery_type = surgery.service_type;
    }
  }
};

const addOperation = async () => {
  if (isDischarged.value) {
    $q.notify({
      type: 'negative',
      message: 'Cannot add surgeries for a discharged patient',
    });
    return;
  }
  editingSurgery.value = null;
  resetSurgeryForm();
  // Load surgeries when opening dialog
  await loadSurgeries();
  showSurgeryDialog.value = true;
};

const editSurgery = async (surgery) => {
  if (isDischarged.value) {
    $q.notify({
      type: 'negative',
      message: 'Cannot edit surgeries for a discharged patient',
    });
    return;
  }
  editingSurgery.value = surgery;
  surgeryForm.value = {
    g_drg_code: surgery.g_drg_code || '',
    surgery_name: surgery.surgery_name || '',
    surgery_type: surgery.surgery_type || '',
    surgeon_name: surgery.surgeon_name || '',
    assistant_surgeon: surgery.assistant_surgeon || '',
    anesthesia_type: surgery.anesthesia_type || '',
    surgery_date: surgery.surgery_date ? new Date(surgery.surgery_date).toISOString().slice(0, 16) : '',
    surgery_notes: surgery.surgery_notes || '',
    operative_notes: surgery.operative_notes || '',
    post_operative_notes: surgery.post_operative_notes || '',
    complications: surgery.complications || '',
    is_completed: surgery.is_completed || false,
  };
  // Load surgeries and try to match selected surgery if editing
  await loadSurgeries();
  if (surgery.g_drg_code) {
    const matchedSurgery = allSurgeries.value.find(s => s.value.code === surgery.g_drg_code);
    if (matchedSurgery) {
      selectedSurgery.value = matchedSurgery.value;
    } else {
      selectedSurgery.value = null;
    }
  } else {
    selectedSurgery.value = null;
  }
  showSurgeryDialog.value = true;
};

const resetSurgeryForm = () => {
  surgeryForm.value = {
    g_drg_code: '',
    surgery_name: '',
    surgery_type: '',
    surgeon_name: '',
    assistant_surgeon: '',
    anesthesia_type: '',
    surgery_date: '',
    surgery_notes: '',
    operative_notes: '',
    post_operative_notes: '',
    complications: '',
    is_completed: false,
  };
  selectedSurgery.value = null;
  filteredSurgeryOptions.value = allSurgeries.value.slice(0, 50);
};

const closeSurgeryDialog = () => {
  showSurgeryDialog.value = false;
  editingSurgery.value = null;
  resetSurgeryForm();
};

// Additional Services functions
const addInventoryDebit = () => {
  if (isDischarged.value) {
    $q.notify({
      type: 'negative',
      message: 'Cannot add inventory debits for a discharged patient',
    });
    return;
  }
  // Open inventory debit page in new tab
  const routeData = router.resolve({
    name: 'InpatientInventoryDebit',
    params: { id: wardAdmissionId.value },
    query: { encounter_id: encounterId.value }
  });
  window.open(routeData.href, '_blank');
};

const requestBlood = () => {
  if (isDischarged.value) {
    $q.notify({
      type: 'negative',
      message: 'Cannot request blood for a discharged patient',
    });
    return;
  }
  // Open blood request page in new tab
  const routeData = router.resolve({
    name: 'BloodTransfusionRequest',
    params: { id: wardAdmissionId.value },
    query: { encounter_id: encounterId.value }
  });
  window.open(routeData.href, '_blank');
};

const addAdditionalService = async () => {
  if (isDischarged.value) {
    $q.notify({
      type: 'negative',
      message: 'Cannot add additional services for a discharged patient',
    });
    return;
  }
  try {
    // Load available services
    const res = await consultationAPI.getAdditionalServices(true); // active only
    additionalServices.value = Array.isArray(res.data) ? res.data : [];
    
    if (additionalServices.value.length === 0) {
      $q.notify({
        type: 'warning',
        message: 'No additional services available. Please contact admin to add services.',
      });
      return;
    }
    
    // Reset form
    additionalServiceForm.value = {
      service_id: null,
      start_time: new Date().toISOString().slice(0, 16),
      notes: '',
    };
    
    showAdditionalServiceDialog.value = true;
  } catch (error) {
    console.error('Error loading additional services:', error);
    $q.notify({
      type: 'negative',
      message: 'Failed to load additional services',
    });
  }
};

const startAdditionalService = async () => {
  if (!additionalServiceForm.value.service_id) {
    $q.notify({
      type: 'warning',
      message: 'Please select a service',
    });
    return;
  }
  
  savingAdditionalService.value = true;
  try {
    const serviceData = {
      service_id: additionalServiceForm.value.service_id,
      start_time: additionalServiceForm.value.start_time 
        ? new Date(additionalServiceForm.value.start_time).toISOString()
        : null,
      notes: additionalServiceForm.value.notes || null,
    };
    
    await consultationAPI.startAdditionalService(wardAdmissionId.value, serviceData);
    
    $q.notify({
      type: 'positive',
      message: 'Additional service started successfully',
    });
    
    showAdditionalServiceDialog.value = false;
    await loadTableData();
  } catch (error) {
    console.error('Error starting additional service:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to start additional service',
    });
  } finally {
    savingAdditionalService.value = false;
  }
};

const stopAdditionalService = async (serviceUsage) => {
  stoppingService.value = serviceUsage;
  // Set default end_date and end_time to current date and time
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  const hours = String(now.getHours()).padStart(2, '0');
  const minutes = String(now.getMinutes()).padStart(2, '0');
  stopServiceForm.value = {
    end_date: `${year}-${month}-${day}`,
    end_time: `${hours}:${minutes}`,
    notes: '',
  };
  showStopServiceDialog.value = true;
};

const confirmStopService = async () => {
  if (!stopServiceForm.value.end_date || !stopServiceForm.value.end_time) {
    $q.notify({
      type: 'warning',
      message: 'Please select both stop date and time',
    });
    return;
  }

  if (!stoppingService.value) return;

  const serviceUsage = stoppingService.value;
  savingAdditionalService.value = true;
  
  try {
    // Combine date and time into ISO string
    const dateTimeString = `${stopServiceForm.value.end_date}T${stopServiceForm.value.end_time}:00`;
    const stopData = {
      end_time: new Date(dateTimeString).toISOString(),
      notes: stopServiceForm.value.notes || null,
    };
    
    await consultationAPI.stopAdditionalService(
      wardAdmissionId.value,
      serviceUsage.id,
      stopData
    );
    
    $q.notify({
      type: 'positive',
      message: 'Service stopped and billed successfully',
    });
    
    showStopServiceDialog.value = false;
    await loadTableData();
  } catch (error) {
    console.error('Error stopping additional service:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to stop additional service',
    });
  } finally {
    savingAdditionalService.value = false;
    stoppingService.value = null;
    stopServiceForm.value = {
      end_date: '',
      end_time: '',
      notes: '',
    };
  }
};

const saveSurgery = async () => {
  if (!wardAdmissionId.value) return;
  
  if (!surgeryForm.value.surgery_name) {
    $q.notify({
      type: 'warning',
      message: 'Surgery name is required',
    });
    return;
  }
  
  savingSurgery.value = true;
  try {
    const surgeryData = {
      g_drg_code: surgeryForm.value.g_drg_code || null,
      surgery_name: surgeryForm.value.surgery_name,
      surgery_type: surgeryForm.value.surgery_type || null,
      surgeon_name: surgeryForm.value.surgeon_name || null,
      assistant_surgeon: surgeryForm.value.assistant_surgeon || null,
      anesthesia_type: surgeryForm.value.anesthesia_type || null,
      surgery_date: surgeryForm.value.surgery_date ? new Date(surgeryForm.value.surgery_date).toISOString() : null,
      surgery_notes: surgeryForm.value.surgery_notes || null,
    };
    
    if (editingSurgery.value) {
      // Update existing surgery
      const updateData = {
        ...surgeryData,
        operative_notes: surgeryForm.value.operative_notes || null,
        post_operative_notes: surgeryForm.value.post_operative_notes || null,
        complications: surgeryForm.value.complications || null,
        is_completed: surgeryForm.value.is_completed,
      };
      await consultationAPI.updateInpatientSurgery(wardAdmissionId.value, editingSurgery.value.id, updateData);
      $q.notify({
        type: 'positive',
        message: 'Surgery updated successfully',
      });
    } else {
      // Create new surgery
      await consultationAPI.createInpatientSurgery(wardAdmissionId.value, surgeryData);
      $q.notify({
        type: 'positive',
        message: 'Operation added successfully',
      });
    }
    
    closeSurgeryDialog();
    await loadTableData();
  } catch (error) {
    console.error('Error saving surgery:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to save surgery',
    });
  } finally {
    savingSurgery.value = false;
  }
};

const deleteSurgery = async (surgery) => {
  if (!wardAdmissionId.value) return;
  
  $q.dialog({
    title: 'Delete Surgery',
    message: `Are you sure you want to delete "${surgery.surgery_name}"? This action cannot be undone.`,
    cancel: true,
    persistent: true,
  }).onOk(async () => {
    try {
      await consultationAPI.deleteInpatientSurgery(wardAdmissionId.value, surgery.id);
      $q.notify({
        type: 'positive',
        message: 'Surgery deleted successfully',
      });
      await loadTableData();
    } catch (error) {
      console.error('Error deleting surgery:', error);
      $q.notify({
        type: 'negative',
        message: error.response?.data?.detail || 'Failed to delete surgery',
      });
    }
  });
};
</script>

<style scoped>
.body--light .glass-text {
  color: rgba(0, 0, 0, 0.87) !important;
}

/* Force color on nurse notes based on shift */
.night-shift-note,
.night-shift-note *,
.night-shift-note p,
.night-shift-note div,
.night-shift-note span {
  color: #d32f2f !important;
}

.day-shift-note,
.day-shift-note *,
.day-shift-note p,
.day-shift-note div,
.day-shift-note span {
  color: #000000 !important;
}

.body--dark .glass-text {
  color: rgba(255, 255, 255, 0.9) !important;
}

.strikethrough-note {
  opacity: 0.6;
}
</style>

