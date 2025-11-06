<template>
  <q-page class="q-pa-md">
    <div class="text-h4 q-mb-md text-weight-bold glass-text">Consultation</div>

    <q-card class="q-mb-md glass-card" v-if="!encounterLoaded" flat>
      <q-card-section>
        <div class="text-h6 q-mb-md glass-text">Load Encounter</div>
        
        <!-- Filter Section -->
        <div class="row q-gutter-md q-mb-md">
          <q-input
            v-model="selectedDate"
            filled
            type="date"
            label="Select Date"
            class="col-12 col-md-3"
            @update:model-value="loadEncountersForDate"
          />
          <q-input
            v-model="cardNumberFilter"
            filled
            label="Filter by Card Number"
            class="col-12 col-md-3"
            clearable
          />
          <q-btn
            icon="today"
            label="Today"
            @click="setToday"
            color="primary"
            class="col-12 col-md-2 glass-button"
          />
          <q-space />
          <q-badge color="primary" :label="`${filteredEncounters.length} encounters`" />
        </div>

        <!-- Encounter ID Search (Alternative) -->
        <q-separator class="q-mb-md" />
        <div class="text-subtitle2 q-mb-sm glass-text">Or search by Encounter ID:</div>
        <div class="row q-gutter-md">
          <q-input
            v-model="searchEncounterId"
            filled
            type="number"
            label="Encounter ID"
            class="col-12 col-md-8"
            @keyup.enter="loadEncounter"
          />
          <q-btn
            color="primary"
            label="Load"
            @click="loadEncounter"
            class="col-12 col-md-4 glass-button"
            :loading="loadingEncounter"
          />
        </div>

        <!-- Encounters List -->
        <div v-if="filteredEncounters.length > 0" class="q-mt-md">
          <q-separator class="q-mb-md" />
          <div class="text-subtitle2 q-mb-sm glass-text">Select an encounter:</div>
          <q-table
            :rows="filteredEncounters"
            :columns="encounterColumns"
            row-key="id"
            flat
            :loading="loadingEncounters"
            :rows-per-page-options="[10, 20, 50]"
            @row-click="selectEncounter"
            class="cursor-pointer"
          >
            <template v-slot:body-cell-status="props">
              <q-td :props="props">
                <q-badge
                  :color="getStatusColor(props.value)"
                  :label="props.value"
                />
              </q-td>
            </template>
            <template v-slot:body-cell-time="props">
              <q-td :props="props">
                {{ formatTime(props.value) }}
              </q-td>
            </template>
            <template v-slot:body-cell-actions="props">
              <q-td :props="props">
                <q-btn
                  size="sm"
                  color="primary"
                  icon="visibility"
                  flat
                  @click.stop="selectEncounter(props.row)"
                  label="Select"
                />
              </q-td>
            </template>
          </q-table>
        </div>

        <!-- Empty State -->
        <div v-if="!loadingEncounters && filteredEncounters.length === 0 && selectedDate" class="text-center q-pa-lg text-grey-6">
          <q-icon name="event_busy" size="64px" />
          <div class="text-h6 q-mt-md">No encounters found for this date</div>
          <div class="text-caption q-mt-sm" v-if="cardNumberFilter">
            Try removing the card number filter or selecting a different date
          </div>
        </div>
      </q-card-section>
    </q-card>

    <div v-if="encounterLoaded">
      <!-- Patient Info -->
      <q-card class="q-mb-md glass-card" flat>
        <q-card-section>
          <div class="text-h6 q-mb-sm glass-text">
            {{ patientInfo?.name }} {{ patientInfo?.surname }}
            <span 
              v-if="remainingBalance > 0" 
              class="text-negative text-weight-bold q-ml-md cursor-pointer"
              style="text-decoration: underline;"
              @click="goToBilling"
            >
              Bill Amount: GHC {{ remainingBalance.toFixed(2) }} (Click to Pay)
            </span>
            <span 
              v-else-if="totalBillAmount > 0" 
              class="text-positive text-weight-bold q-ml-md"
            >
              Bill Fully Paid: GHC {{ totalBillAmount.toFixed(2) }}
            </span>
          </div>
          <div class="row q-gutter-md">
            <div class="col-12 col-md-3">
              <strong>Card Number:</strong> 
              <span class="text-weight-bold text-primary">{{ patientInfo?.card_number || 'N/A' }}</span>
            </div>
            <div class="col-12 col-md-3">
              <strong>Insurance No:</strong> {{ patientInfo?.insurance_id || 'N/A' }}
            </div>
            <div class="col-12 col-md-3">
              <strong>DOB:</strong> {{ formatDate(patientInfo?.date_of_birth) || 'N/A' }}
            </div>
            <div class="col-12 col-md-3">
              <strong>Encounter Date:</strong> {{ formatDate(encounterStore.currentEncounter?.created_at) || 'N/A' }}
            </div>
          </div>
          <div class="row q-gutter-md q-mt-sm">
            <div class="col-12 col-md-3">
              <strong>CCC Number:</strong> {{ encounterStore.currentEncounter?.ccc_number || 'N/A' }}
            </div>
          </div>
        </q-card-section>
      </q-card>

      <!-- Vitals Display -->
      <q-card class="q-mb-md glass-card" v-if="encounterStore.encounterVitals" flat>
        <q-card-section>
          <div class="row items-center q-mb-sm">
            <div class="text-h6 glass-text">Vitals</div>
            <q-space />
            <q-btn
              flat
              icon="history"
              label="Show Previous"
              color="secondary"
              size="sm"
              @click="showPreviousVitals"
            />
          </div>
          <div class="row q-gutter-md">
            <div v-if="encounterStore.encounterVitals.bp" class="col-12 col-md-3">
              <strong>BP:</strong> {{ encounterStore.encounterVitals.bp }} mmHg
            </div>
            <div v-if="encounterStore.encounterVitals.temperature" class="col-12 col-md-3">
              <strong>Temp:</strong> {{ encounterStore.encounterVitals.temperature }}°C
            </div>
            <div v-if="encounterStore.encounterVitals.pulse" class="col-12 col-md-3">
              <strong>Pulse:</strong> {{ encounterStore.encounterVitals.pulse }} bpm
            </div>
            <div v-if="encounterStore.encounterVitals.respiration" class="col-12 col-md-3">
              <strong>RR:</strong> {{ encounterStore.encounterVitals.respiration }} /min
            </div>
            <div v-if="encounterStore.encounterVitals.weight" class="col-12 col-md-3">
              <strong>Weight:</strong> {{ encounterStore.encounterVitals.weight }} kg
            </div>
            <div v-if="encounterStore.encounterVitals.height" class="col-12 col-md-3">
              <strong>Height:</strong> {{ encounterStore.encounterVitals.height }} cm
            </div>
            <div v-if="encounterStore.encounterVitals.bmi" class="col-12 col-md-3">
              <strong>BMI:</strong> {{ encounterStore.encounterVitals.bmi }}
            </div>
            <div v-if="encounterStore.encounterVitals.spo2" class="col-12 col-md-3">
              <strong>SpO2:</strong> {{ encounterStore.encounterVitals.spo2 }}%
            </div>
            <div v-if="encounterStore.encounterVitals.rbs" class="col-12 col-md-3">
              <strong>RBS:</strong> {{ encounterStore.encounterVitals.rbs }} mmol/L
            </div>
            <div v-if="encounterStore.encounterVitals.fbs" class="col-12 col-md-3">
              <strong>FBS:</strong> {{ encounterStore.encounterVitals.fbs }} mmol/L
            </div>
            <div v-if="encounterStore.encounterVitals.upt" class="col-12 col-md-3">
              <strong>UPT:</strong> {{ encounterStore.encounterVitals.upt }}
            </div>
            <div v-if="encounterStore.encounterVitals.rdt_malaria" class="col-12 col-md-3">
              <strong>Malaria RDT:</strong> {{ encounterStore.encounterVitals.rdt_malaria }}
            </div>
            <div v-if="encounterStore.encounterVitals.retro_rdt" class="col-12 col-md-3">
              <strong>Retro RDT:</strong> {{ encounterStore.encounterVitals.retro_rdt }}
            </div>
            <div v-if="encounterStore.encounterVitals.remarks" class="col-12">
              <strong>Remarks:</strong> {{ encounterStore.encounterVitals.remarks }}
            </div>
          </div>
        </q-card-section>
      </q-card>

      <!-- Presenting Complaints -->
      <q-card class="q-mb-md glass-card" flat>
        <q-card-section>
          <div class="row items-center q-mb-md">
            <div class="text-h6 glass-text">Presenting Complaints</div>
            <q-space />
            <q-btn
              flat
              icon="history"
              label="Show Previous"
              color="secondary"
              size="sm"
              @click="showPreviousComplaints"
              class="q-mr-sm"
            />
            <q-btn
              flat
              icon="edit"
              label="Edit"
              color="primary"
              @click="openEditPresentingComplaints"
              :disable="readonly"
            />
          </div>
          <div class="text-body1" style="white-space: pre-wrap;">
            {{ consultationNotes?.presenting_complaints || 'No presenting complaints recorded.' }}
          </div>
        </q-card-section>
      </q-card>

      <!-- Diagnoses -->
      <q-card class="q-mb-md glass-card" flat>
        <q-card-section>
          <div class="row items-center q-mb-md">
            <div class="text-h6 glass-text">Diagnoses</div>
            <q-space />
            <q-btn
              flat
              icon="history"
              label="Show Previous"
              color="secondary"
              size="sm"
              @click="showPreviousDiagnoses"
              class="q-mr-sm"
            />
            <q-btn
              color="primary"
              label="Add Diagnosis"
              @click="resetDiagnosisForm(); showDiagnosisDialog = true"
              class="glass-button"
            />
          </div>

          <q-table
            :rows="encounterStore.encounterDiagnoses"
            :columns="diagnosisColumns"
            row-key="id"
            flat
          >
            <template v-slot:body-cell-is_provisional="props">
              <q-td :props="props">
                <q-badge
                  :color="props.value ? 'orange' : 'green'"
                  :label="props.value ? 'Provisional' : 'Final'"
                />
              </q-td>
            </template>
            <template v-slot:body-cell-is_chief="props">
              <q-td :props="props">
                <q-icon
                  v-if="props.value"
                  name="star"
                  color="primary"
                  size="sm"
                />
              </q-td>
            </template>
            <template v-slot:body-cell-actions="props">
              <q-td :props="props">
                <q-btn
                  flat
                  dense
                  round
                  icon="edit"
                  color="primary"
                  size="sm"
                  @click="editDiagnosis(props.row)"
                >
                  <q-tooltip>Edit Diagnosis</q-tooltip>
                </q-btn>
                <q-btn
                  flat
                  dense
                  round
                  icon="delete"
                  color="negative"
                  size="sm"
                  @click="deleteDiagnosis(props.row)"
                  class="q-ml-xs"
                >
                  <q-tooltip>Delete Diagnosis</q-tooltip>
                </q-btn>
              </q-td>
            </template>
          </q-table>
        </q-card-section>
      </q-card>

      <!-- Prescriptions -->
      <q-card class="q-mb-md glass-card" flat>
        <q-card-section>
          <div class="row items-center q-mb-md">
            <div class="text-h6 glass-text">Prescriptions</div>
            <q-space />
            <q-btn
              flat
              icon="history"
              label="Show Previous"
              color="secondary"
              size="sm"
              @click="showPreviousPrescriptions"
              class="q-mr-sm"
            />
            <q-btn
              color="primary"
              label="Add Prescription"
              @click="resetPrescriptionForm(); showPrescriptionDialog = true"
              class="glass-button"
            />
          </div>

          <q-table
            :rows="encounterStore.encounterPrescriptions"
            :columns="prescriptionColumns"
            row-key="id"
            flat
          >
            <template v-slot:body-cell-status="props">
              <q-td :props="props">
                <q-badge
                  v-if="props.row.is_confirmed"
                  color="positive"
                  label="Confirmed"
                />
                <q-badge
                  v-else
                  color="warning"
                  label="Pending"
                />
              </q-td>
            </template>
            <template v-slot:body-cell-actions="props">
              <q-td :props="props">
                <q-btn
                  flat
                  dense
                  round
                  icon="edit"
                  color="primary"
                  size="sm"
                  @click="editPrescription(props.row)"
                  :disable="props.row.is_confirmed"
                >
                  <q-tooltip>
                    {{ props.row.is_confirmed ? 'Cannot edit confirmed prescription' : 'Edit Prescription' }}
                  </q-tooltip>
                </q-btn>
                <q-btn
                  flat
                  dense
                  round
                  icon="delete"
                  color="negative"
                  size="sm"
                  @click="deletePrescription(props.row)"
                  :disable="props.row.is_confirmed"
                  class="q-ml-xs"
                >
                  <q-tooltip>
                    {{ props.row.is_confirmed ? 'Cannot delete confirmed prescription' : 'Delete Prescription' }}
                  </q-tooltip>
                </q-btn>
              </q-td>
            </template>
          </q-table>
        </q-card-section>
      </q-card>

      <!-- Investigations -->
      <q-card class="q-mb-md glass-card" flat>
        <q-card-section>
          <div class="row items-center q-mb-md">
            <div class="text-h6 glass-text">Investigations</div>
            <q-space />
            <q-btn
              flat
              icon="history"
              label="Show Previous"
              color="secondary"
              size="sm"
              @click="showPreviousInvestigations"
              class="q-mr-sm"
            />
            <q-btn
              color="primary"
              label="Add Investigation"
              @click="resetInvestigationForm(); showInvestigationDialog = true"
              class="glass-button"
            />
          </div>

          <q-table
            :rows="encounterStore.encounterInvestigations"
            :columns="investigationColumns"
            row-key="id"
            flat
            :row-class="(row) => row.status === 'cancelled' ? 'bg-red-1 text-negative' : ''"
          >
            <template v-slot:body-cell-status="props">
              <q-td :props="props">
                <q-badge
                  v-if="props.row.status === 'cancelled'"
                  color="negative"
                  label="Cancelled"
                />
                <q-badge
                  v-else-if="props.row.status === 'completed'"
                  color="positive"
                  label="Completed"
                />
                <q-badge
                  v-else-if="props.row.status === 'confirmed'"
                  color="warning"
                  label="Confirmed"
                />
                <q-badge
                  v-else
                  color="grey"
                  label="Requested"
                />
              </q-td>
            </template>
            <template v-slot:body-cell-actions="props">
              <q-td :props="props">
                <q-btn
                  flat
                  dense
                  round
                  icon="edit"
                  color="primary"
                  size="sm"
                  @click="editInvestigation(props.row)"
                  :disable="props.row.confirmed_by || props.row.status === 'confirmed' || props.row.status === 'completed'"
                >
                  <q-tooltip>
                    {{ (props.row.confirmed_by || props.row.status === 'confirmed' || props.row.status === 'completed') 
                        ? 'Cannot edit confirmed investigation' 
                        : 'Edit Investigation' }}
                  </q-tooltip>
                </q-btn>
                <q-btn
                  v-if="props.row.status === 'confirmed'"
                  flat
                  dense
                  round
                  icon="cancel"
                  color="negative"
                  size="sm"
                  @click="cancelInvestigation(props.row)"
                  class="q-ml-xs"
                >
                  <q-tooltip>Cancel Investigation (Client cannot pay)</q-tooltip>
                </q-btn>
                <q-btn
                  v-if="props.row.status === 'confirmed' || props.row.status === 'completed'"
                  flat
                  dense
                  round
                  icon="visibility"
                  color="positive"
                  size="sm"
                  @click="viewInvestigationResults(props.row)"
                  class="q-ml-xs"
                >
                  <q-tooltip>View Results</q-tooltip>
                </q-btn>
                <q-btn
                  v-if="props.row.status !== 'cancelled'"
                  flat
                  dense
                  round
                  icon="delete"
                  color="negative"
                  size="sm"
                  @click="deleteInvestigation(props.row)"
                  :disable="props.row.confirmed_by || props.row.status === 'confirmed' || props.row.status === 'completed'"
                  class="q-ml-xs"
                >
                  <q-tooltip>
                    {{ (props.row.confirmed_by || props.row.status === 'confirmed' || props.row.status === 'completed') 
                        ? 'Cannot delete confirmed investigation' 
                        : 'Delete Investigation' }}
                  </q-tooltip>
                </q-btn>
                <q-chip
                  v-if="props.row.status === 'cancelled' && props.row.cancellation_reason"
                  color="negative"
                  text-color="white"
                  size="sm"
                  class="q-ml-xs"
                >
                  <q-tooltip>{{ props.row.cancellation_reason }}</q-tooltip>
                  Reason: {{ props.row.cancellation_reason.substring(0, 30) }}{{ props.row.cancellation_reason.length > 30 ? '...' : '' }}
                </q-chip>
              </q-td>
            </template>
          </q-table>
        </q-card-section>
      </q-card>

      <!-- Doctor Notes -->
      <q-card class="q-mb-md glass-card" flat>
        <q-card-section>
          <div class="row items-center q-mb-md">
            <div class="text-h6 glass-text">Doctor Notes</div>
            <q-space />
            <q-btn
              flat
              icon="edit"
              label="Edit"
              color="primary"
              @click="openEditDoctorNotes"
              :disable="readonly"
            />
          </div>
          <div class="text-body1" style="white-space: pre-wrap;">
            {{ consultationNotes?.doctor_notes || 'No doctor notes recorded.' }}
          </div>
        </q-card-section>
      </q-card>

      <!-- Follow-up Date -->
      <q-card class="q-mb-md glass-card" flat>
        <q-card-section>
          <div class="row items-center q-mb-md">
            <div class="text-h6 glass-text">Follow-up Date</div>
            <q-space />
          <q-btn
              flat
              icon="edit"
              label="Edit"
              color="primary"
            @click="openEditFollowUpDate"
            :disable="readonly"
            />
          </div>
          <div class="text-body1">
            <strong>Follow-up Date:</strong> 
            {{ consultationNotes?.follow_up_date ? formatDate(consultationNotes.follow_up_date) : 'No follow-up date set.' }}
          </div>
        </q-card-section>
      </q-card>

      <!-- Consultation Outcome -->
      <q-card class="q-mb-md glass-card" flat>
        <q-card-section>
          <div class="row items-center q-mb-md">
            <div class="text-h6 glass-text">Consultation Outcome</div>
          </div>
          <q-select
            v-model="notesForm.outcome"
            filled
            :options="[
              { label: 'Referred', value: 'referred' },
              { label: 'Discharged', value: 'discharged' },
              { label: 'Recommended for Admission', value: 'recommended_for_admission' }
            ]"
            emit-value
            map-options
            label="Outcome *"
            hint="Required to finalize consultation"
          />
          <q-input
            v-if="notesForm.outcome === 'recommended_for_admission'"
            v-model="notesForm.admission_ward"
            filled
            label="Admission Ward *"
          />
          <div class="row q-mt-md q-gutter-md">
            <q-btn label="Save Outcome" color="primary" @click="saveConsultationNotes" class="glass-button" />
          </div>
        </q-card-section>
      </q-card>

      <!-- Actions -->
      <div class="row q-gutter-md">
        <!-- Show "Save Draft & Wait for Service" only if NOT finalized -->
        <q-btn
          v-if="encounterStore.currentEncounter?.status !== 'finalized'"
          color="warning"
          label="Save Draft & Wait for Service"
          @click="saveDraftAndAwaitServices"
          :disable="readonly"
          class="glass-button"
        />
        <!-- Show "Update Consultation" only if finalized -->
        <q-btn
          v-if="encounterStore.currentEncounter?.status === 'finalized'"
          color="primary"
          label="Update Consultation"
          @click="updateConsultation"
          :disable="readonly"
          class="glass-button"
        />
        <!-- Show "Finalize Consultation" only if NOT finalized -->
        <q-btn
          v-if="encounterStore.currentEncounter?.status !== 'finalized'"
          color="positive"
          label="Finalize Consultation"
          @click="finalizeConsultation"
          :loading="finalizing"
          :disable="readonly"
          class="glass-button"
        />
        <q-btn
          flat
          color="grey"
          label="Cancel"
          @click="cancelConsultation"
          :disable="readonly"
          class="glass-button"
        />
      </div>
    </div>

    <!-- Diagnosis Dialog -->
    <q-dialog v-model="showDiagnosisDialog">
      <q-card style="min-width: 400px">
        <q-card-section>
          <div class="text-h6">{{ editingDiagnosisId ? 'Edit Diagnosis' : 'Add Diagnosis' }}</div>
        </q-card-section>

        <q-card-section>
          <q-form @submit="saveDiagnosis" class="q-gutter-md">
            <q-select
              v-model="selectedIcd10"
              filled
              :options="icd10Options"
              label="Search by ICD-10 Code"
              option-label="display"
              option-value="icd10_code"
              use-input
              input-debounce="300"
              @filter="filterIcd10Codes"
              @update:model-value="onIcd10Selected"
              hint="Search by ICD-10 code or description - DRG code and diagnosis will be auto-filled"
              clearable
              class="q-mb-md"
            >
              <template v-slot:option="scope">
                <q-item v-bind="scope.itemProps">
                  <q-item-section>
                    <q-item-label>{{ scope.opt.icd10_code }}</q-item-label>
                    <q-item-label caption>{{ scope.opt.icd10_description }}</q-item-label>
                  </q-item-section>
                </q-item>
              </template>
              <template v-slot:no-option>
                <q-item>
                  <q-item-section class="text-grey">
                    No ICD-10 codes found. Admin should upload ICD-10 mapping in Price List Management.
                  </q-item-section>
                </q-item>
              </template>
            </q-select>
            
            <q-select
              v-model="selectedDiagnosis"
              filled
              :options="drgDiagnosisOptions"
              label="OR Search Diagnosis (from Unmapped DRG)"
              option-label="item_name"
              option-value="item_code"
              use-input
              input-debounce="300"
              @filter="filterDrgDiagnoses"
              @update:model-value="onDiagnosisSelected"
              hint="Search by diagnosis name - GDRG code and diagnosis will be auto-filled"
              clearable
              class="q-mb-md"
            >
              <template v-slot:no-option>
                <q-item>
                  <q-item-section class="text-grey">
                    No diagnoses found. Admin should upload Unmapped DRG codes in Price List Management.
                  </q-item-section>
                </q-item>
              </template>
            </q-select>
            
            <q-input
              v-model="diagnosisForm.icd10"
              filled
              label="ICD-10 Code"
              hint="Auto-filled when ICD-10 is selected, or enter manually"
            />
            <q-input
              v-model="diagnosisForm.diagnosis"
              filled
              label="Diagnosis *"
              lazy-rules
              :rules="[(val) => !!val || 'Required']"
            />
            <q-input
              v-model="diagnosisForm.gdrg_code"
              filled
              label="GDRG Code (auto-filled from selection)"
              readonly
              hint="Automatically populated when you select a diagnosis above"
            />
            <q-toggle
              v-model="diagnosisForm.is_provisional"
              label="Provisional Diagnosis"
            />
            <q-toggle
              v-model="diagnosisForm.is_chief"
              label="Principal Complaint"
            />
            <div>
              <q-btn :label="editingDiagnosisId ? 'Update' : 'Add'" type="submit" color="primary" />
              <q-btn label="Cancel" flat v-close-popup @click="resetDiagnosisForm" />
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- Prescription Dialog -->
    <q-dialog v-model="showPrescriptionDialog">
      <q-card style="min-width: 500px">
        <q-card-section>
          <div class="text-h6">{{ editingPrescriptionId ? 'Edit Prescription' : 'Add Prescription' }}</div>
        </q-card-section>

        <q-card-section>
          <q-form @submit="savePrescription" class="q-gutter-md">
            <q-select
              v-model="selectedMedication"
              filled
              :options="medicationOptions"
              label="Search Medication (from Pharmacy)"
              option-label="item_name"
              option-value="item_code"
              use-input
              input-debounce="300"
              @filter="filterMedications"
              @update:model-value="onMedicationSelected"
              hint="Search by medication name or code - medicine code and name will be auto-filled"
              clearable
            >
              <template v-slot:option="scope">
                <q-item v-bind="scope.itemProps">
                  <q-item-section>
                    <q-item-label>{{ scope.opt.item_name || scope.opt.product_name || scope.opt.service_name }}</q-item-label>
                    <q-item-label v-if="scope.opt.formulation" caption class="text-grey-7">
                      Formulation: {{ scope.opt.formulation }}
                    </q-item-label>
                    <q-item-label v-if="scope.opt.item_code || scope.opt.medication_code" caption class="text-grey-6">
                      Code: {{ scope.opt.item_code || scope.opt.medication_code }}
                    </q-item-label>
                  </q-item-section>
                </q-item>
              </template>
              <template v-slot:no-option>
                <q-item>
                  <q-item-section class="text-grey">
                    No medications found. Admin should upload pharmacy products in Price List Management.
                  </q-item-section>
                </q-item>
              </template>
            </q-select>
            <q-input
              v-model="prescriptionForm.medicine_code"
              filled
              label="Medicine Code *"
              lazy-rules
              :rules="[(val) => !!val || 'Required']"
              readonly
              hint="Automatically populated when you select a medication above"
            />
            <q-input
              v-model="prescriptionForm.medicine_name"
              filled
              label="Medicine Name *"
              lazy-rules
              :rules="[(val) => !!val || 'Required']"
              readonly
              hint="Automatically populated when you select a medication above"
            />
            <div class="row q-gutter-md">
              <q-input
                v-model="prescriptionForm.dose"
                filled
                label="Dose"
                type="number"
                class="col-12 col-md-4"
                hint="e.g., 500 (for 500mg), 1 (for 1 tablet/capsule)"
                @update:model-value="calculateQuantity"
              />
              <q-select
                v-model="prescriptionForm.unit"
                filled
                :options="unitOptions"
                label="Unit"
                class="col-12 col-md-4"
                hint="e.g., MG, ML, TAB"
                use-input
                input-debounce="0"
                @new-value="createUnit"
                @update:model-value="calculateQuantity"
              />
              <q-select
                v-model="prescriptionForm.frequency"
                filled
                :options="frequencyOptions"
                label="Frequency *"
                class="col-12 col-md-4"
                lazy-rules
                :rules="[(val) => !!val || 'Required']"
                @update:model-value="calculateQuantity"
              />
            </div>
            <div class="row q-gutter-md">
              <q-input
                v-model="prescriptionForm.duration"
                filled
                label="Duration (e.g., 7 DAYS)"
                class="col-12 col-md-6"
                hint="e.g., 7 DAYS, 2 WEEKS"
                @update:model-value="calculateQuantity"
              />
            </div>
            <q-input
              v-model="prescriptionForm.instructions"
              filled
              type="textarea"
              label="Instructions"
              rows="3"
              hint="Add instructions for taking this medication"
            />
            <div>
              <q-btn :label="editingPrescriptionId ? 'Update' : 'Add'" type="submit" color="primary" />
              <q-btn label="Cancel" flat v-close-popup @click="resetPrescriptionForm" />
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- Investigation Dialog -->
    <q-dialog v-model="showInvestigationDialog">
      <q-card style="min-width: 400px">
        <q-card-section>
          <div class="text-h6">{{ editingInvestigationId ? 'Edit Investigation' : 'Add Investigation' }}</div>
        </q-card-section>

        <q-card-section>
          <q-form @submit="saveInvestigation" class="q-gutter-md">
            <q-select
              v-model="investigationForm.service_type"
              filled
              :options="serviceTypeOptions"
              label="Service Type (Department/Clinic) *"
              lazy-rules
              :rules="[(val) => !!val || 'Required']"
              @update:model-value="onServiceTypeSelected"
              hint="Select the department/clinic for the service request"
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
              v-model="selectedProcedure"
              filled
              :options="procedureOptions"
              label="Procedure (Service Name) *"
              option-label="service_name"
              option-value="g_drg_code"
              lazy-rules
              :rules="[(val) => !!val || 'Required']"
              :disable="!investigationForm.service_type"
              @update:model-value="onProcedureSelected"
              hint="Select the procedure - GDRG code will be auto-filled"
              use-input
              input-debounce="300"
              @filter="filterProcedures"
              clearable
            >
              <template v-slot:no-option>
                <q-item>
                  <q-item-section class="text-grey">
                    {{
                      investigationForm.service_type
                        ? 'No procedures found for this department. Select a different service type.'
                        : 'Please select a Service Type first'
                    }}
                  </q-item-section>
                </q-item>
              </template>
            </q-select>
            <q-input
              v-model="investigationForm.gdrg_code"
              filled
              label="GDRG Code (auto-filled)"
              readonly
              hint="Automatically populated when you select a procedure above"
            />
            <q-select
              v-model="investigationForm.investigation_type"
              filled
              :options="investigationTypes"
              label="Investigation Type *"
              lazy-rules
              :rules="[(val) => !!val || 'Required']"
            />
            <q-input
              v-model="investigationForm.notes"
              filled
              type="textarea"
              label="Notes/Remarks"
              rows="3"
              hint="Add any notes or remarks for this investigation request"
            />
            <q-input
              v-model="investigationForm.price"
              filled
              label="Price (Auto-fetched from price list)"
              readonly
              hint="Automatically fetched from price list based on patient insurance status"
              type="text"
            >
              <template v-slot:append>
                <q-icon name="info" color="primary">
                  <q-tooltip>
                    Price shown is based on patient's insurance status. Doctors can see this before confirming the investigation.
                  </q-tooltip>
                </q-icon>
              </template>
            </q-input>
            <div>
              <q-btn :label="editingInvestigationId ? 'Update' : 'Add'" type="submit" color="primary" />
              <q-btn label="Cancel" flat v-close-popup @click="resetInvestigationForm" />
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- Presenting Complaints Dialog -->
    <q-dialog v-model="editPresentingComplaints">
      <q-card style="min-width: 600px; max-width: 800px">
        <q-card-section>
          <div class="text-h6">Edit Presenting Complaints</div>
        </q-card-section>
        <q-card-section>
          <!-- Draft Banner for Presenting Complaints -->
          <q-banner
            v-if="hasDraft('presenting_complaints') && notesForm.presenting_complaints !== (getDraftValue('presenting_complaints') || '')"
            class="bg-warning text-dark q-mb-md"
            rounded
          >
            <template v-slot:avatar>
              <q-icon name="save" color="dark" />
            </template>
            <strong>Draft Available</strong>
            <div class="text-caption q-mt-xs">
              A draft was saved {{ formatDraftTime(getDraftTime('presenting_complaints')) }}. 
              Would you like to restore it?
            </div>
            <template v-slot:action>
              <q-btn
                flat
                label="Restore Draft"
                color="dark"
                @click="restoreDraft('presenting_complaints')"
              />
              <q-btn
                flat
                label="Discard"
                color="dark"
                @click="clearDraft('presenting_complaints')"
              />
            </template>
          </q-banner>
          
          <q-input
            v-model="notesForm.presenting_complaints"
            filled
            type="textarea"
            label="Presenting Complaints"
            rows="6"
            hint="Enter the patient's presenting complaints/history (auto-saved as draft)"
            @update:model-value="autoSaveDraft('presenting_complaints')"
          />
          <div class="row q-mt-md q-gutter-md">
            <q-btn label="Save" color="primary" @click="saveConsultationNotes" />
            <q-btn label="Cancel" flat @click="closePresentingComplaintsDialog" />
          </div>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- Doctor Notes Dialog -->
    <q-dialog v-model="editDoctorNotes">
      <q-card style="min-width: 600px; max-width: 800px">
        <q-card-section>
          <div class="text-h6">Edit Doctor Notes</div>
        </q-card-section>
        <q-card-section>
          <!-- Draft Banner for Doctor Notes -->
          <q-banner
            v-if="hasDraft('doctor_notes') && notesForm.doctor_notes !== (getDraftValue('doctor_notes') || '')"
            class="bg-warning text-dark q-mb-md"
            rounded
          >
            <template v-slot:avatar>
              <q-icon name="save" color="dark" />
            </template>
            <strong>Draft Available</strong>
            <div class="text-caption q-mt-xs">
              A draft was saved {{ formatDraftTime(getDraftTime('doctor_notes')) }}. 
              Would you like to restore it?
            </div>
            <template v-slot:action>
              <q-btn
                flat
                label="Restore Draft"
                color="dark"
                @click="restoreDraft('doctor_notes')"
              />
              <q-btn
                flat
                label="Discard"
                color="dark"
                @click="clearDraft('doctor_notes')"
              />
            </template>
          </q-banner>
          
          <q-input
            v-model="notesForm.doctor_notes"
            filled
            type="textarea"
            label="Doctor Notes"
            rows="8"
            hint="Enter clinical notes and observations (auto-saved as draft)"
            @update:model-value="autoSaveDraft('doctor_notes')"
          />
          <div class="row q-mt-md q-gutter-md">
            <q-btn label="Save" color="primary" @click="saveConsultationNotes" />
            <q-btn label="Cancel" flat @click="closeDoctorNotesDialog" />
          </div>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- Follow-up Date Dialog -->
    <q-dialog v-model="editFollowUpDate">
      <q-card style="min-width: 400px">
        <q-card-section>
          <div class="text-h6">Set Follow-up Date</div>
        </q-card-section>
        <q-card-section>
          <q-input
            v-model="notesForm.follow_up_date"
            filled
            type="date"
            label="Follow-up Date"
            hint="Select the follow-up appointment date"
          />
          <div class="row q-mt-md q-gutter-md">
            <q-btn label="Save" color="primary" @click="saveConsultationNotes" :disable="readonly" />
            <q-btn label="Cancel" flat v-close-popup />
            <q-btn label="Clear" flat color="negative" @click="clearFollowUpDate" :disable="readonly" />
          </div>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- Investigation Results Dialog -->
    <q-dialog v-model="showResultsDialog">
      <q-card style="min-width: 600px; max-width: 900px">
        <q-card-section>
          <div class="text-h6">Investigation Results</div>
          <div class="text-subtitle2 text-grey-7 q-mt-xs" v-if="selectedInvestigation">
            {{ selectedInvestigation.procedure_name || 'Investigation' }} ({{ selectedInvestigation.gdrg_code }})
          </div>
        </q-card-section>

        <q-card-section>
          <q-inner-loading :showing="loadingResults" />
          
          <div v-if="!loadingResults && investigationResult">
            <div class="q-mb-md">
              <div class="text-subtitle1 q-mb-sm">Results Text:</div>
              <div class="text-body1" style="white-space: pre-wrap; min-height: 100px; padding: 12px; background: #f5f5f5; border-radius: 4px;">
                {{ investigationResult.results_text || 'No text results available.' }}
              </div>
            </div>
            
            <div v-if="investigationResult.attachment_path" class="q-mt-md">
              <div class="text-subtitle1 q-mb-sm">Attachment:</div>
              <q-btn
                color="primary"
                icon="download"
                label="Download Attachment"
                @click="downloadInvestigationAttachment"
              />
              <div class="text-caption text-grey-7 q-mt-xs">
                {{ investigationResult.attachment_path.split('/').pop() }}
              </div>
            </div>
            <div v-else class="q-mt-md">
              <div class="text-body2 text-grey-7">No attachment available.</div>
            </div>
          </div>
          
          <div v-else-if="!loadingResults && !investigationResult" class="text-center text-grey-7 q-pa-md">
            Results not yet available for this investigation.
          </div>
        </q-card-section>

        <q-card-actions align="right">
          <q-btn label="Close" color="primary" v-close-popup />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Previous Vitals Dialog -->
    <q-dialog v-model="showPreviousVitalsDialog">
      <q-card style="min-width: 700px; max-width: 900px">
        <q-card-section>
          <div class="text-h6">Previous Vitals</div>
        </q-card-section>
        <q-card-section>
          <q-inner-loading :showing="loadingPreviousVitals" />
          <div v-if="!loadingPreviousVitals && previousVitals.length === 0" class="text-center text-grey-7 q-pa-md">
            No previous vitals found for this patient.
          </div>
          <div v-else-if="!loadingPreviousVitals" class="q-gutter-md">
            <q-card v-for="(vital, idx) in previousVitals" :key="idx" flat bordered class="q-mb-sm">
              <q-card-section>
                <div class="row items-center q-mb-sm">
                  <div class="text-subtitle2">
                    <strong>Encounter #{{ vital.encounter_id }}</strong> - {{ formatDate(vital.created_at) }}
                  </div>
                  <q-space />
                  <q-btn
                    flat
                    dense
                    icon="show_chart"
                    color="primary"
                    label="Plot Graph"
                    size="sm"
                    @click="plotVitalsGraph(vital)"
                  />
                </div>
                <div class="row q-gutter-md">
                  <div v-if="vital.weight"><strong>Weight:</strong> {{ vital.weight }} kg</div>
                  <div v-if="vital.height"><strong>Height:</strong> {{ vital.height }} cm</div>
                  <div v-if="vital.bp_systolic || vital.bp_diastolic">
                    <strong>BP:</strong> {{ vital.bp_systolic || '' }}/{{ vital.bp_diastolic || '' }} mmHg
                  </div>
                  <div v-if="vital.temperature"><strong>Temp:</strong> {{ vital.temperature }}°C</div>
                  <div v-if="vital.pulse"><strong>Pulse:</strong> {{ vital.pulse }} bpm</div>
                  <div v-if="vital.respiratory_rate"><strong>RR:</strong> {{ vital.respiratory_rate }} /min</div>
                  <div v-if="vital.spo2"><strong>SpO2:</strong> {{ vital.spo2 }}%</div>
                  <div v-if="vital.bmi"><strong>BMI:</strong> {{ vital.bmi }}</div>
                </div>
              </q-card-section>
            </q-card>
          </div>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn label="Plot All Vitals" color="secondary" @click="plotAllVitalsGraph" v-if="previousVitals.length > 0" class="q-mr-sm" />
          <q-btn label="Close" color="primary" v-close-popup />
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

    <!-- Previous Complaints Dialog -->
    <q-dialog v-model="showPreviousComplaintsDialog">
      <q-card style="min-width: 700px; max-width: 900px">
        <q-card-section>
          <div class="text-h6">Previous Presenting Complaints</div>
        </q-card-section>
        <q-card-section>
          <q-inner-loading :showing="loadingPreviousComplaints" />
          <div v-if="!loadingPreviousComplaints && previousComplaints.length === 0" class="text-center text-grey-7 q-pa-md">
            No previous complaints found for this patient.
          </div>
          <div v-else-if="!loadingPreviousComplaints" class="q-gutter-md">
            <q-card v-for="(complaint, idx) in previousComplaints" :key="idx" flat bordered class="q-mb-sm">
              <q-card-section>
                <div class="text-subtitle2 q-mb-sm">
                  <strong>Encounter #{{ complaint.encounter_id }}</strong> - {{ formatDate(complaint.created_at) }}
                </div>
                <div class="text-body1" style="white-space: pre-wrap;">
                  {{ complaint.presenting_complaints || 'No complaints recorded' }}
                </div>
              </q-card-section>
            </q-card>
          </div>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn label="Close" color="primary" v-close-popup />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Previous Diagnoses Dialog -->
    <q-dialog v-model="showPreviousDiagnosesDialog">
      <q-card style="min-width: 700px; max-width: 900px">
        <q-card-section>
          <div class="text-h6">Previous Diagnoses</div>
        </q-card-section>
        <q-card-section>
          <q-inner-loading :showing="loadingPreviousDiagnoses" />
          <div v-if="!loadingPreviousDiagnoses && previousDiagnoses.length === 0" class="text-center text-grey-7 q-pa-md">
            No previous diagnoses found for this patient.
          </div>
          <div v-else-if="!loadingPreviousDiagnoses">
            <q-list bordered>
              <q-item v-for="(diagnosis, idx) in previousDiagnoses" :key="idx">
                <q-item-section>
                  <q-item-label>
                    <strong>{{ diagnosis.diagnosis }}</strong>
                    <span v-if="diagnosis.icd10_code" class="text-grey-7 q-ml-sm">(ICD-10: {{ diagnosis.icd10_code }})</span>
                    <q-badge v-if="diagnosis.is_provisional" color="orange" label="Provisional" class="q-ml-sm" />
                    <q-badge v-if="diagnosis.is_chief" color="primary" label="Chief" class="q-ml-sm" />
                  </q-item-label>
                  <q-item-label caption>
                    Encounter #{{ diagnosis.encounter_id }} - {{ formatDate(diagnosis.created_at) }}
                  </q-item-label>
                </q-item-section>
                <q-item-section side>
                  <q-btn
                    flat
                    dense
                    icon="add"
                    color="primary"
                    label="Use This"
                    @click="usePreviousDiagnosis(diagnosis)"
                    :disable="!encounterStore.currentEncounter?.id"
                  />
                </q-item-section>
              </q-item>
            </q-list>
            <div v-if="Object.keys(recurringDiagnoses).length > 0" class="q-mt-md">
              <strong>Recurring Diagnoses:</strong>
              <q-chip 
                v-for="(count, diag) in recurringDiagnoses" 
                :key="diag" 
                color="primary" 
                text-color="white"
                class="q-ml-sm q-mt-sm"
              >
                {{ diag }} ({{ count }} times)
              </q-chip>
            </div>
          </div>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn label="Close" color="primary" v-close-popup />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Previous Prescriptions Dialog -->
    <q-dialog v-model="showPreviousPrescriptionsDialog">
      <q-card style="min-width: 800px; max-width: 1000px">
        <q-card-section>
          <div class="text-h6">Previous Prescriptions</div>
        </q-card-section>
        <q-card-section>
          <q-inner-loading :showing="loadingPreviousPrescriptions" />
          <div v-if="!loadingPreviousPrescriptions && previousPrescriptions.length === 0" class="text-center text-grey-7 q-pa-md">
            No previous prescriptions found for this patient.
          </div>
          <div v-else-if="!loadingPreviousPrescriptions">
            <q-table
              :rows="previousPrescriptions"
              :columns="previousPrescriptionColumns"
              row-key="id"
              flat
              :rows-per-page-options="[10, 20, 50]"
            >
              <template v-slot:body-cell-status="props">
                <q-td :props="props">
                  <q-badge v-if="props.row.is_dispensed" color="positive" label="Dispensed" />
                  <q-badge v-else-if="props.row.is_confirmed" color="warning" label="Confirmed" />
                  <q-badge v-else color="grey" label="Pending" />
                </q-td>
              </template>
              <template v-slot:body-cell-actions="props">
                <q-td :props="props">
                  <q-btn
                    flat
                    dense
                    icon="add"
                    color="primary"
                    label="Use This"
                    @click="usePreviousPrescription(props.row)"
                    :disable="!encounterStore.currentEncounter?.id"
                  />
                </q-td>
              </template>
            </q-table>
            <div v-if="Object.keys(recurringMedications).length > 0" class="q-mt-md">
              <strong>Recurring Medications:</strong>
              <q-chip 
                v-for="(count, med) in recurringMedications" 
                :key="med" 
                color="secondary" 
                text-color="white"
                class="q-ml-sm q-mt-sm"
              >
                {{ med }} ({{ count }} times)
              </q-chip>
            </div>
          </div>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn label="Close" color="primary" v-close-popup />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Previous Investigations Dialog -->
    <q-dialog v-model="showPreviousInvestigationsDialog">
      <q-card style="min-width: 800px; max-width: 1000px">
        <q-card-section>
          <div class="text-h6">Previous Investigations</div>
        </q-card-section>
        <q-card-section>
          <q-inner-loading :showing="loadingPreviousInvestigations" />
          <div v-if="!loadingPreviousInvestigations && previousInvestigations.length === 0" class="text-center text-grey-7 q-pa-md">
            No previous investigations found for this patient.
          </div>
          <div v-else-if="!loadingPreviousInvestigations">
            <q-table
              :rows="previousInvestigations"
              :columns="previousInvestigationColumns"
              row-key="id"
              flat
              :rows-per-page-options="[10, 20, 50]"
            >
              <template v-slot:body-cell-status="props">
                <q-td :props="props">
                  <q-badge v-if="props.row.is_confirmed" color="positive" label="Confirmed" />
                  <q-badge v-else color="warning" label="Pending" />
                </q-td>
              </template>
            </q-table>
          </div>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn label="Close" color="primary" v-close-popup />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, watch, nextTick } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { consultationAPI, priceListAPI, encountersAPI, patientsAPI, billingAPI, vitalsAPI } from '../services/api';
import { useEncountersStore } from '../stores/encounters';
import { usePatientsStore } from '../stores/patients';
import { useAuthStore } from '../stores/auth';
import { useQuasar } from 'quasar';

const $q = useQuasar();
const route = useRoute();
const router = useRouter();
const encounterStore = useEncountersStore();
const patientsStore = usePatientsStore();
const authStore = useAuthStore();
const isAdmin = computed(() => authStore.userRole === 'Admin');
const readonly = computed(() => !isAdmin.value && encounterStore.currentEncounter?.status === 'finalized');

const searchEncounterId = ref(route.params.encounterId || '');
const encounterLoaded = ref(false);
const loadingEncounter = ref(false);

// Date and card number filtering
const selectedDate = ref('');
const cardNumberFilter = ref('');
const encountersList = ref([]);
const loadingEncounters = ref(false);

// Encounter columns for the list
const encounterColumns = [
  { name: 'time', label: 'Time', field: 'created_at', align: 'left', sortable: true },
  { name: 'id', label: 'Encounter ID', field: 'id', align: 'left' },
  { name: 'patient_name', label: 'Patient Name', field: 'patient_name', align: 'left' },
  { name: 'card_number', label: 'Card Number', field: 'patient_card_number', align: 'left' },
  { name: 'department', label: 'Department', field: 'department', align: 'left' },
  { name: 'status', label: 'Status', field: 'status', align: 'center' },
  { name: 'actions', label: 'Actions', align: 'center' },
];

// Filtered encounters based on card number
const filteredEncounters = computed(() => {
  if (!cardNumberFilter.value) return encountersList.value;
  const needle = cardNumberFilter.value.toLowerCase().trim();
  return encountersList.value.filter(e => 
    (e.patient_card_number || '').toLowerCase().includes(needle)
  );
});

// Set today's date on mount
const setToday = () => {
  const today = new Date();
  selectedDate.value = today.toISOString().split('T')[0];
  loadEncountersForDate();
};

// Load encounters for selected date
const loadEncountersForDate = async () => {
  if (!selectedDate.value) {
    encountersList.value = [];
    return;
  }

  loadingEncounters.value = true;
  try {
    const response = await encountersAPI.getByDate(selectedDate.value);
    encountersList.value = response.data || [];
  } catch (error) {
    console.error('Failed to load encounters:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to load encounters',
    });
    encountersList.value = [];
  } finally {
    loadingEncounters.value = false;
  }
};

// Select encounter from list
const selectEncounter = async (encounter) => {
  searchEncounterId.value = encounter.id;
  await loadEncounter();
};

// Format time for display
const formatTime = (dateString) => {
  if (!dateString) return '';
  const date = new Date(dateString);
  return date.toLocaleTimeString('en-US', { 
    hour: '2-digit', 
    minute: '2-digit',
    hour12: true 
  });
};

// Get status color
const getStatusColor = (status) => {
  const colors = {
    draft: 'orange',
    in_consultation: 'blue',
    awaiting_services: 'purple',
    finalized: 'green',
  };
  return colors[status] || 'grey';
};
const finalizing = ref(false);

const showDiagnosisDialog = ref(false);
const showPrescriptionDialog = ref(false);
const showInvestigationDialog = ref(false);
const showResultsDialog = ref(false);
const selectedInvestigation = ref(null);
const investigationResult = ref(null);
const loadingResults = ref(false);

const diagnosisColumns = [
  { name: 'icd10', label: 'ICD-10', field: 'icd10', align: 'left' },
  { name: 'diagnosis', label: 'Diagnosis', field: 'diagnosis', align: 'left' },
  { name: 'gdrg_code', label: 'GDRG Code', field: 'gdrg_code', align: 'left' },
  { name: 'is_provisional', label: 'Type', field: 'is_provisional', align: 'center' },
  { name: 'is_chief', label: 'Chief', field: 'is_chief', align: 'center' },
  { name: 'actions', label: 'Actions', field: 'actions', align: 'center' },
];

const prescriptionColumns = [
  { name: 'medicine_name', label: 'Medicine', field: 'medicine_name', align: 'left' },
  { name: 'medicine_code', label: 'Code', field: 'medicine_code', align: 'left' },
  { name: 'dose', label: 'Dose', field: 'dose', align: 'left' },
  { name: 'frequency', label: 'Frequency', field: 'frequency', align: 'left' },
  { name: 'duration', label: 'Duration', field: 'duration', align: 'left' },
  { name: 'quantity', label: 'Quantity', field: 'quantity', align: 'right' },
  { name: 'status', label: 'Status', field: 'is_confirmed', align: 'center' },
  { name: 'actions', label: 'Actions', field: 'actions', align: 'center' },
];

const investigationColumns = [
  { name: 'procedure_name', label: 'Procedure Name', field: 'procedure_name', align: 'left' },
  { name: 'gdrg_code', label: 'GDRG Code', field: 'gdrg_code', align: 'left' },
  { name: 'investigation_type', label: 'Type', field: 'investigation_type', align: 'left' },
  { name: 'price', label: 'Price', field: 'price', align: 'right', format: (val) => val ? `₵${parseFloat(val).toFixed(2)}` : 'N/A' },
  { name: 'status', label: 'Status', field: 'status', align: 'left' },
  { name: 'actions', label: 'Actions', field: 'actions', align: 'center' },
];

const investigationTypes = ['lab', 'scan', 'xray'];

const selectedDiagnosis = ref(null);
const drgDiagnosisOptions = ref([]);
const allDrgDiagnoses = ref([]);
const editingDiagnosisId = ref(null);

const selectedIcd10 = ref(null);
const icd10Options = ref([]);
const allIcd10Codes = ref([]);

const selectedMedication = ref(null);
const medicationOptions = ref([]);
const allMedications = ref([]);
const editingPrescriptionId = ref(null);

const diagnosisForm = reactive({
  encounter_id: null,
  icd10: '',
  diagnosis: '',
  gdrg_code: '',
  is_provisional: false,
  is_chief: false,
});

const prescriptionForm = reactive({
  encounter_id: null,
  medicine_code: '',
  medicine_name: '',
  dose: '',
  unit: '',
  frequency: '',
  duration: '',
  instructions: '',
  quantity: 1,
});

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

const frequencyOptions = Object.keys(frequencyMapping);
const unitOptions = ref(['MG', 'ML', 'TAB', 'CAP', 'G', 'MCG', 'IU', 'UNITS']);

// Create unit if not in list
const createUnit = (val, done) => {
  if (val.length > 0 && !unitOptions.value.includes(val.toUpperCase())) {
    unitOptions.value.push(val.toUpperCase());
  }
  done(val.toUpperCase());
};

// Auto-calculate quantity based on pharmacist logic
// For MG: 100mg = 1 unit, so dose (in mg) / 100 = units per dose
// Then: (dose_mg / 100) × frequency_value × duration
// Example: 500mg, BDS (2), 2 days = (500/100) × 2 × 2 = 5 × 2 × 2 = 20
// Note: Doctors don't calculate quantity - it's set to 0 and pharmacy will set it during confirmation
const calculateQuantity = () => {
  // Don't calculate quantity for doctors - pharmacy will set it during confirmation
  if (authStore.userRole === 'Doctor') {
    prescriptionForm.quantity = 0;
    return;
  }
  if (prescriptionForm.dose && prescriptionForm.frequency && prescriptionForm.duration) {
    try {
      const doseNum = parseFloat(prescriptionForm.dose);
      const frequencyValue = frequencyMapping[prescriptionForm.frequency];
      
      if (doseNum && frequencyValue && doseNum > 0) {
        // Extract duration number (e.g., "7 DAYS" -> 7, "2" -> 2)
        const durationStr = prescriptionForm.duration.trim();
        let durationNum = 1;
        if (durationStr) {
          // First try to parse as a number directly
          const directNum = parseFloat(durationStr);
          if (!isNaN(directNum) && directNum > 0) {
            durationNum = Math.floor(directNum);
          } else {
            // Otherwise, extract number from string (e.g., "7 DAYS" -> 7)
            const durationMatch = durationStr.match(/\d+/);
            if (durationMatch) {
              durationNum = parseInt(durationMatch[0]);
            }
          }
        }
        
        // Convert dose to units based on unit type
        let unitsPerDose = doseNum;
        if (prescriptionForm.unit && prescriptionForm.unit.toUpperCase() === 'MG') {
          // For MG: 100mg = 1 unit
          unitsPerDose = doseNum / 100;
        } else if (prescriptionForm.unit && prescriptionForm.unit.toUpperCase() === 'MCG') {
          // For MCG: 1000mcg = 1 unit (or 100mcg = 0.1 unit, but typically 1000mcg = 1mg = 1 unit)
          unitsPerDose = doseNum / 1000;
        }
        // For other units (TAB, CAP, ML, etc.), use dose as-is (1 tablet = 1 unit)
        
        // Calculate: units per dose × frequency per day × number of days
        const calculatedQuantity = Math.floor(unitsPerDose * frequencyValue * durationNum);
        if (calculatedQuantity > 0) {
          prescriptionForm.quantity = calculatedQuantity;
        }
      }
    } catch (error) {
      console.error('Error calculating quantity:', error);
    }
  }
};

const investigationForm = reactive({
  encounter_id: null,
  service_type: '',  // New field for Service Type (Department/Clinic)
  gdrg_code: '',
  procedure_name: '',  // Procedure/service name
  investigation_type: '',
  notes: '',  // Notes/remarks from doctor
  price: '',  // Price of the investigation
});

const editingInvestigationId = ref(null);

// Consultation notes
const consultationNotes = ref(null);
const totalBillAmount = ref(0);
const paidAmount = ref(0);
const remainingBalance = computed(() => Math.max(0, totalBillAmount.value - paidAmount.value));
const editPresentingComplaints = ref(false);
const editDoctorNotes = ref(false);
const editFollowUpDate = ref(false);
const notesForm = reactive({
  encounter_id: null,
  presenting_complaints: '',
  doctor_notes: '',
  follow_up_date: '',
  outcome: '',
  admission_ward: ''
});

// Auto-save draft functionality
const draftSaveTimers = ref({});
const DRAFT_SAVE_DELAY = 2000; // Save after 2 seconds of no typing

// Get draft storage key
const getDraftKey = (field) => {
  const encounterId = encounterStore.currentEncounter?.id;
  if (!encounterId) return null;
  return `consultation_draft_${encounterId}_${field}`;
};

// Auto-save draft (debounced)
const autoSaveDraft = (field) => {
  const encounterId = encounterStore.currentEncounter?.id;
  if (!encounterId) {
    console.warn('No encounter ID for draft save');
    return;
  }
  
  // Clear existing timer
  if (draftSaveTimers.value[field]) {
    clearTimeout(draftSaveTimers.value[field]);
  }
  
  // Set new timer
  draftSaveTimers.value[field] = setTimeout(() => {
    const key = getDraftKey(field);
    if (!key) {
      console.warn(`No draft key for field: ${field}`);
      return;
    }
    
    const value = notesForm[field] || '';
    if (value.trim()) {
      const draftData = {
        value: value,
        timestamp: Date.now(),
        encounterId: encounterId
      };
      localStorage.setItem(key, JSON.stringify(draftData));
      console.log(`Draft saved for ${field}:`, draftData);
    } else {
      // Remove draft if empty
      localStorage.removeItem(key);
    }
  }, DRAFT_SAVE_DELAY);
};

// Check if draft exists
const hasDraft = (field) => {
  const key = getDraftKey(field);
  if (!key) return false;
  const draft = localStorage.getItem(key);
  if (!draft) return false;
  
  try {
    const draftData = JSON.parse(draft);
    // Check if draft is for current encounter
    return draftData.encounterId === encounterStore.currentEncounter?.id;
  } catch {
    return false;
  }
};

// Get draft time
const getDraftTime = (field) => {
  const key = getDraftKey(field);
  if (!key) return null;
  const draft = localStorage.getItem(key);
  if (!draft) return null;
  
  try {
    const draftData = JSON.parse(draft);
    return draftData.timestamp;
  } catch {
    return null;
  }
};

// Get draft value
const getDraftValue = (field) => {
  const key = getDraftKey(field);
  if (!key) return null;
  const draft = localStorage.getItem(key);
  if (!draft) return null;
  
  try {
    const draftData = JSON.parse(draft);
    if (draftData.encounterId === encounterStore.currentEncounter?.id) {
      return draftData.value;
    }
    return null;
  } catch {
    return null;
  }
};

// Format draft time
const formatDraftTime = (timestamp) => {
  if (!timestamp) return '';
  const now = Date.now();
  const diff = now - timestamp;
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(minutes / 60);
  
  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
  if (hours < 24) return `${hours} hour${hours > 1 ? 's' : ''} ago`;
  
  const date = new Date(timestamp);
  return date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
};

// Restore draft
const restoreDraft = (field) => {
  const key = getDraftKey(field);
  if (!key) return;
  
  const draft = localStorage.getItem(key);
  if (!draft) return;
  
  try {
    const draftData = JSON.parse(draft);
    if (draftData.value) {
      notesForm[field] = draftData.value;
      $q.notify({
        type: 'positive',
        message: 'Draft restored successfully',
        position: 'top',
        timeout: 2000
      });
    }
  } catch (error) {
    console.error('Failed to restore draft:', error);
  }
};

// Clear draft
const clearDraft = (field) => {
  const key = getDraftKey(field);
  if (key) {
    localStorage.removeItem(key);
  }
};

// Load drafts when dialog opens
const loadDraftsWhenDialogOpens = (field) => {
  if (hasDraft(field)) {
    // Don't auto-restore, just show the banner
    // User can choose to restore or discard
  }
};

// Previous data dialogs and state
const showPreviousVitalsDialog = ref(false);
const showPreviousComplaintsDialog = ref(false);
const showPreviousDiagnosesDialog = ref(false);
const showPreviousPrescriptionsDialog = ref(false);
const showPreviousInvestigationsDialog = ref(false);

const loadingPreviousVitals = ref(false);
const loadingPreviousComplaints = ref(false);
const loadingPreviousDiagnoses = ref(false);
const loadingPreviousPrescriptions = ref(false);
const loadingPreviousInvestigations = ref(false);

const previousVitals = ref([]);
const previousComplaints = ref([]);
const previousDiagnoses = ref([]);
const previousPrescriptions = ref([]);
const previousInvestigations = ref([]);

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

const recurringDiagnoses = computed(() => {
  const counts = {};
  previousDiagnoses.value.forEach(d => {
    const key = d.diagnosis?.toLowerCase() || '';
    if (key) counts[key] = (counts[key] || 0) + 1;
  });
  return Object.fromEntries(Object.entries(counts).filter(([_, count]) => count > 1));
});

const recurringMedications = computed(() => {
  const counts = {};
  previousPrescriptions.value.forEach(p => {
    const key = p.medicine_name?.toLowerCase() || '';
    if (key) counts[key] = (counts[key] || 0) + 1;
  });
  return Object.fromEntries(Object.entries(counts).filter(([_, count]) => count > 1));
});

const previousPrescriptionColumns = [
  { name: 'encounter_id', label: 'Encounter', field: 'encounter_id', align: 'left' },
  { name: 'created_at', label: 'Date', field: 'created_at', align: 'left', format: (val) => formatDate(val) },
  { name: 'medicine_name', label: 'Medicine', field: 'medicine_name', align: 'left' },
  { name: 'dose', label: 'Dose', field: 'dose', align: 'left' },
  { name: 'frequency', label: 'Frequency', field: 'frequency', align: 'left' },
  { name: 'duration', label: 'Duration', field: 'duration', align: 'left' },
  { name: 'quantity', label: 'Quantity', field: 'quantity', align: 'right' },
  { name: 'status', label: 'Status', field: 'status', align: 'center' },
  { name: 'actions', label: 'Action', field: 'actions', align: 'center' },
];

const previousInvestigationColumns = [
  { name: 'encounter_id', label: 'Encounter', field: 'encounter_id', align: 'left' },
  { name: 'created_at', label: 'Date', field: 'created_at', align: 'left', format: (val) => formatDate(val) },
  { name: 'procedure_name', label: 'Procedure Name', field: 'procedure_name', align: 'left' },
  { name: 'gdrg_code', label: 'GDRG Code', field: 'gdrg_code', align: 'left' },
  { name: 'investigation_type', label: 'Type', field: 'investigation_type', align: 'left' },
  { name: 'status', label: 'Status', field: 'status', align: 'center' },
];

// Service request (procedure) management
const serviceTypeOptions = ref([]);
const allProcedures = ref([]);  // All procedures for current service type
const procedureOptions = ref([]);  // Filtered procedures for autocomplete
const selectedProcedure = ref(null);

const patientInfo = computed(() => {
  if (encounterStore.currentEncounter?.patient_id) {
    return patientsStore.currentPatient;
  }
  return null;
});

const formatDate = (dateString) => {
  if (!dateString) return '';
  const date = new Date(dateString);
  return date.toLocaleDateString('en-GB', { 
    day: '2-digit', 
    month: '2-digit', 
    year: 'numeric' 
  });
};

const loadEncounter = async () => {
  if (!searchEncounterId.value) {
    $q.notify({
      type: 'warning',
      message: 'Please enter an encounter ID',
    });
    return;
  }

  loadingEncounter.value = true;
  try {
    await encounterStore.getEncounter(searchEncounterId.value);
    
    // Load patient info if needed  
    if (encounterStore.currentEncounter?.patient_id) {
      // Check if we need to load patient data
      // The patient might already be in the store if accessed from patient profile
      if (!patientsStore.currentPatient || patientsStore.currentPatient.id !== encounterStore.currentEncounter.patient_id) {
        try {
          // Try to load patient by ID from patients API
          const patientResponse = await patientsAPI.get(encounterStore.currentEncounter.patient_id);
          patientsStore.currentPatient = patientResponse.data;
        } catch (error) {
          console.error('Failed to load patient data:', error);
          // Continue without patient data - we'll show what we have
        }
      }
    }
    
    diagnosisForm.encounter_id = encounterStore.currentEncounter.id;
    prescriptionForm.encounter_id = encounterStore.currentEncounter.id;
    investigationForm.encounter_id = encounterStore.currentEncounter.id;
    notesForm.encounter_id = encounterStore.currentEncounter.id;
    
    // Load consultation notes
    await loadConsultationNotes();
    
    // Load bill total
    await loadBillTotal();
    
    encounterLoaded.value = true;
  } catch (error) {
    // Error handled in store
  } finally {
    loadingEncounter.value = false;
  }
};

const loadConsultationNotes = async () => {
  if (!encounterStore.currentEncounter?.id) return;
  
  try {
    const response = await consultationAPI.getConsultationNotes(encounterStore.currentEncounter.id);
    consultationNotes.value = response.data || null;
    if (consultationNotes.value) {
      notesForm.presenting_complaints = consultationNotes.value.presenting_complaints || '';
      notesForm.doctor_notes = consultationNotes.value.doctor_notes || '';
      notesForm.follow_up_date = consultationNotes.value.follow_up_date ? 
        consultationNotes.value.follow_up_date.split('T')[0] : '';
      notesForm.outcome = consultationNotes.value.outcome || '';
      notesForm.admission_ward = consultationNotes.value.admission_ward || '';
    }
  } catch (error) {
    console.error('Failed to load consultation notes:', error);
    consultationNotes.value = null;
  }
};

const loadBillTotal = async () => {
  if (!encounterStore.currentEncounter?.id) return;
  
  try {
    // Get all bills for this encounter
    const billsResponse = await billingAPI.getEncounterBills(encounterStore.currentEncounter.id);
    const bills = billsResponse.data || [];
    
    if (bills.length === 0) {
      // No bills exist yet - reset to 0
      totalBillAmount.value = 0;
      paidAmount.value = 0;
      return;
    }
    
    // Calculate total bill amount from all bills (sum of all bill total_amount)
    // This represents the total amount the patient owes from all bills
    totalBillAmount.value = bills.reduce((sum, bill) => {
      const billTotal = bill.total_amount || 0;
      return sum + billTotal;
    }, 0);
    
    // Calculate total paid amount from all bills (sum of all paid_amount)
    // This includes all payments made across all bills for this encounter
    // paid_amount already accounts for all receipts (non-refunded)
    paidAmount.value = bills.reduce((sum, bill) => {
      const paid = bill.paid_amount || 0;
      return sum + paid;
    }, 0);
    
    // Remaining balance is computed automatically (totalBillAmount - paidAmount)
    // This shows what the patient still owes
    // Initially when encounter starts: 0 (no bills yet)
    // After services are billed: Shows total bill amount
    // After payments: Shows remaining balance (total - paid)
  } catch (error) {
    console.error('Failed to load bill total:', error);
    totalBillAmount.value = 0;
    paidAmount.value = 0;
  }
};

// Navigate to billing page with encounter ID
const goToBilling = () => {
  if (encounterStore.currentEncounter?.id) {
    router.push({
      name: 'Billing',
      params: { encounterId: encounterStore.currentEncounter.id }
    });
  }
};

const saveConsultationNotes = async () => {
  try {
    // Prepare data - convert empty strings to null for optional fields
    const dataToSend = {
      encounter_id: notesForm.encounter_id,
      presenting_complaints: notesForm.presenting_complaints || null,
      doctor_notes: notesForm.doctor_notes || null,
      follow_up_date: notesForm.follow_up_date || null,
      outcome: notesForm.outcome || null,
      admission_ward: notesForm.outcome === 'recommended_for_admission' ? (notesForm.admission_ward || null) : null,
    };
    
    await consultationAPI.saveConsultationNotes(dataToSend);
    
    // Clear drafts after successful save
    clearDraft('presenting_complaints');
    clearDraft('doctor_notes');
    
    $q.notify({
      type: 'positive',
      message: 'Consultation notes saved successfully',
    });
    await loadConsultationNotes();
    editPresentingComplaints.value = false;
    editDoctorNotes.value = false;
    editFollowUpDate.value = false;
  } catch (error) {
    console.error('Error saving consultation notes:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to save consultation notes',
    });
  }
};

const clearFollowUpDate = () => {
  notesForm.follow_up_date = '';
  saveConsultationNotes();
};

const openEditPresentingComplaints = () => {
  // Load saved notes first
  notesForm.presenting_complaints = consultationNotes.value?.presenting_complaints || '';
  notesForm.doctor_notes = consultationNotes.value?.doctor_notes || '';
  notesForm.follow_up_date = consultationNotes.value?.follow_up_date ? 
    consultationNotes.value.follow_up_date.split('T')[0] : '';
  notesForm.outcome = consultationNotes.value?.outcome || '';
  notesForm.admission_ward = consultationNotes.value?.admission_ward || '';
  
  editPresentingComplaints.value = true;
  
  // Check for draft and restore if exists (only if saved notes are empty)
  nextTick(() => {
    if (hasDraft('presenting_complaints')) {
      const draft = localStorage.getItem(getDraftKey('presenting_complaints'));
      if (draft) {
        try {
          const draftData = JSON.parse(draft);
          if (draftData.value && draftData.encounterId === encounterStore.currentEncounter?.id) {
            // If there's no saved content, auto-restore draft
            if (!notesForm.presenting_complaints.trim()) {
              notesForm.presenting_complaints = draftData.value;
            }
            // Otherwise, the banner will show to let user choose
          }
        } catch (e) {
          console.error('Failed to restore draft:', e);
        }
      }
    }
  });
};

const openEditDoctorNotes = () => {
  // Load saved notes first
  notesForm.presenting_complaints = consultationNotes.value?.presenting_complaints || '';
  notesForm.doctor_notes = consultationNotes.value?.doctor_notes || '';
  notesForm.follow_up_date = consultationNotes.value?.follow_up_date ? 
    consultationNotes.value.follow_up_date.split('T')[0] : '';
  notesForm.outcome = consultationNotes.value?.outcome || '';
  notesForm.admission_ward = consultationNotes.value?.admission_ward || '';
  
  editDoctorNotes.value = true;
  
  // Check for draft and restore if exists (only if saved notes are empty)
  nextTick(() => {
    if (hasDraft('doctor_notes')) {
      const draft = localStorage.getItem(getDraftKey('doctor_notes'));
      if (draft) {
        try {
          const draftData = JSON.parse(draft);
          if (draftData.value && draftData.encounterId === encounterStore.currentEncounter?.id) {
            // If there's no saved content, auto-restore draft
            if (!notesForm.doctor_notes.trim()) {
              notesForm.doctor_notes = draftData.value;
            }
            // Otherwise, the banner will show to let user choose
          }
        } catch (e) {
          console.error('Failed to restore draft:', e);
        }
      }
    }
  });
};

// Close dialogs with auto-save
const closePresentingComplaintsDialog = () => {
  // Save draft immediately before closing
  const encounterId = encounterStore.currentEncounter?.id;
  if (encounterId && notesForm.presenting_complaints.trim()) {
    const key = getDraftKey('presenting_complaints');
    if (key) {
      const draftData = {
        value: notesForm.presenting_complaints,
        timestamp: Date.now(),
        encounterId: encounterId
      };
      localStorage.setItem(key, JSON.stringify(draftData));
      console.log('Draft saved on dialog close:', draftData);
    }
  }
  editPresentingComplaints.value = false;
};

const closeDoctorNotesDialog = () => {
  // Save draft immediately before closing
  const encounterId = encounterStore.currentEncounter?.id;
  if (encounterId && notesForm.doctor_notes.trim()) {
    const key = getDraftKey('doctor_notes');
    if (key) {
      const draftData = {
        value: notesForm.doctor_notes,
        timestamp: Date.now(),
        encounterId: encounterId
      };
      localStorage.setItem(key, JSON.stringify(draftData));
      console.log('Draft saved on dialog close:', draftData);
    }
  }
  editDoctorNotes.value = false;
};

const openEditFollowUpDate = () => {
  notesForm.presenting_complaints = consultationNotes.value?.presenting_complaints || '';
  notesForm.doctor_notes = consultationNotes.value?.doctor_notes || '';
  notesForm.follow_up_date = consultationNotes.value?.follow_up_date ? 
    consultationNotes.value.follow_up_date.split('T')[0] : '';
  notesForm.outcome = consultationNotes.value?.outcome || '';
  notesForm.admission_ward = consultationNotes.value?.admission_ward || '';
  editFollowUpDate.value = true;
};

const filterDrgDiagnoses = (val, update, abort) => {
  if (val === '') {
    update(() => {
      drgDiagnosisOptions.value = allDrgDiagnoses.value;
    });
    return;
  }

  // Perform server-side search on unmapped DRG for real-time results
  update(async () => {
    try {
      const response = await priceListAPI.search(val, undefined, 'unmapped_drg');
      drgDiagnosisOptions.value = response.data || [];
    } catch (error) {
      console.error('Failed to search diagnoses:', error);
      // Fallback to local filtering if API fails
    const needle = val.toLowerCase();
    drgDiagnosisOptions.value = allDrgDiagnoses.value.filter(
        (d) => d.item_name?.toLowerCase().indexOf(needle) > -1 || 
               d.item_code?.toLowerCase().indexOf(needle) > -1 ||
               d.g_drg_code?.toLowerCase().indexOf(needle) > -1 ||
               d.service_name?.toLowerCase().indexOf(needle) > -1
      );
    }
  });
};

const onDiagnosisSelected = (diagnosis) => {
  if (diagnosis) {
    // Auto-fill GDRG code from selected diagnosis
    diagnosisForm.gdrg_code = diagnosis.item_code || diagnosis.g_drg_code || '';
    
    // Get diagnosis name from unmapped DRG
    const diagnosisName = diagnosis.item_name || diagnosis.service_name || '';
    diagnosisForm.diagnosis = diagnosisName;
    
    // Try to extract ICD-10 code if it's embedded in the service name
    // Common patterns: "ICD10_CODE - Diagnosis Name" or "(ICD10_CODE)"
    const icd10Match = diagnosisName.match(/^([A-Z]\d{2}\.?\d*)\s*[-–—]\s*(.+)$/i) || 
                      diagnosisName.match(/\(([A-Z]\d{2}\.?\d*)\)/i);
    if (icd10Match && !diagnosisForm.icd10) {
      diagnosisForm.icd10 = icd10Match[1].toUpperCase().replace(/\./g, '');
      // If extracted from pattern like "ICD10 - Name", update diagnosis to just the name part
      if (diagnosisName.includes(' - ')) {
        diagnosisForm.diagnosis = diagnosisName.split(' - ').slice(1).join(' - ');
      }
    }
    
    // Clear ICD-10 selection when DRG diagnosis is selected
    selectedIcd10.value = null;
  } else {
    diagnosisForm.gdrg_code = '';
    diagnosisForm.diagnosis = '';
    // Don't clear ICD-10 if manually entered
  }
};

const loadDrgDiagnoses = async () => {
  try {
    // Search specifically in unmapped_drg for diagnoses
    const response = await priceListAPI.search('', undefined, 'unmapped_drg');
    allDrgDiagnoses.value = response.data || [];
    drgDiagnosisOptions.value = allDrgDiagnoses.value;
  } catch (error) {
    console.error('Failed to load unmapped DRG diagnoses:', error);
    allDrgDiagnoses.value = [];
    drgDiagnosisOptions.value = [];
  }
};

const loadIcd10Codes = async () => {
  try {
    // Load initial ICD-10 codes (empty search to get first batch)
    const response = await priceListAPI.searchIcd10('', 100);
    const results = response.data || [];
    allIcd10Codes.value = results;
    icd10Options.value = results.map(item => ({
      ...item,
      display: `${item.icd10_code} - ${item.icd10_description}`
    }));
  } catch (error) {
    console.error('Failed to load ICD-10 codes:', error);
    allIcd10Codes.value = [];
    icd10Options.value = [];
  }
};

const filterIcd10Codes = async (val, update, abort) => {
  if (val === '') {
    // If we have cached codes, use them, otherwise load them
    if (allIcd10Codes.value.length > 0) {
      update(() => {
        icd10Options.value = allIcd10Codes.value.map(item => ({
          ...item,
          display: `${item.icd10_code} - ${item.icd10_description}`
        }));
      });
    } else {
      // Load initial codes
      update(async () => {
        await loadIcd10Codes();
      });
    }
    return;
  }

  // Perform server-side search for ICD-10 codes
  update(async () => {
    try {
      const response = await priceListAPI.searchIcd10(val, 50);
      const results = response.data || [];
      icd10Options.value = results.map(item => ({
        ...item,
        display: `${item.icd10_code} - ${item.icd10_description}`
      }));
    } catch (error) {
      console.error('Failed to search ICD-10 codes:', error);
      icd10Options.value = [];
    }
  });
};

const onIcd10Selected = async (icd10Item) => {
  if (icd10Item) {
    // Auto-fill ICD-10 code and description
    diagnosisForm.icd10 = icd10Item.icd10_code || '';
    if (icd10Item.icd10_description && !diagnosisForm.diagnosis) {
      diagnosisForm.diagnosis = icd10Item.icd10_description;
    }
    
    // Get DRG codes for this ICD-10 code
    try {
      const response = await priceListAPI.getDrgCodesFromIcd10(icd10Item.icd10_code);
      const drgCodes = response.data || [];
      if (drgCodes.length > 0) {
        // Use first DRG code (or you could show a dialog to select if multiple)
        diagnosisForm.gdrg_code = drgCodes[0].drg_code || '';
        if (drgCodes.length > 1) {
          $q.notify({
            type: 'info',
            message: `This ICD-10 code maps to ${drgCodes.length} DRG code(s). Using first: ${drgCodes[0].drg_code}`,
            position: 'top'
          });
        }
      }
    } catch (error) {
      console.error('Failed to get DRG codes for ICD-10:', error);
    }
    
    // Clear DRG diagnosis selection when ICD-10 is selected
    selectedDiagnosis.value = null;
  } else {
    // Don't clear form fields if ICD-10 is deselected, allow manual entry
  }
};

const editDiagnosis = (diagnosis) => {
  editingDiagnosisId.value = diagnosis.id;
  diagnosisForm.encounter_id = diagnosis.encounter_id;
  diagnosisForm.icd10 = diagnosis.icd10 || '';
  diagnosisForm.diagnosis = diagnosis.diagnosis || '';
  diagnosisForm.gdrg_code = diagnosis.gdrg_code || '';
  diagnosisForm.is_provisional = diagnosis.is_provisional || false;
  diagnosisForm.is_chief = diagnosis.is_chief || false;
  selectedDiagnosis.value = null; // Clear selected diagnosis from search
  showDiagnosisDialog.value = true;
};

const resetDiagnosisForm = () => {
  editingDiagnosisId.value = null;
    selectedDiagnosis.value = null;
  selectedIcd10.value = null;
    Object.assign(diagnosisForm, {
    encounter_id: encounterStore.currentEncounter?.id || null,
      icd10: '',
      diagnosis: '',
      gdrg_code: '',
      is_provisional: false,
      is_chief: false,
    });
};

// Load ICD-10 codes when diagnosis dialog opens
watch(showDiagnosisDialog, (isOpen) => {
  if (isOpen) {
    // Load ICD-10 codes when dialog opens if not already loaded
    if (allIcd10Codes.value.length === 0) {
      loadIcd10Codes();
    }
    // Also load DRG diagnoses if not loaded
    if (allDrgDiagnoses.value.length === 0) {
      loadDrgDiagnoses();
    }
  }
});

const saveDiagnosis = async () => {
  try {
    if (editingDiagnosisId.value) {
      // Update existing diagnosis
      await consultationAPI.updateDiagnosis(editingDiagnosisId.value, diagnosisForm);
      $q.notify({
        type: 'positive',
        message: 'Diagnosis updated successfully',
      });
    } else {
      // Create new diagnosis
      await consultationAPI.createDiagnosis(diagnosisForm);
      $q.notify({
        type: 'positive',
        message: 'Diagnosis added successfully',
      });
    }
    
    await encounterStore.loadEncounterData(encounterStore.currentEncounter.id);
    showDiagnosisDialog.value = false;
    resetDiagnosisForm();
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || (editingDiagnosisId.value ? 'Failed to update diagnosis' : 'Failed to add diagnosis'),
    });
  }
};

const deleteDiagnosis = (diagnosis) => {
  $q.dialog({
    title: 'Delete Diagnosis',
    message: `Are you sure you want to delete this diagnosis: "${diagnosis.diagnosis}"?`,
    cancel: true,
    persistent: true,
  }).onOk(async () => {
    try {
      await consultationAPI.deleteDiagnosis(diagnosis.id);
      $q.notify({
        type: 'positive',
        message: 'Diagnosis deleted successfully',
      });
    await encounterStore.loadEncounterData(encounterStore.currentEncounter.id);
    } catch (error) {
      $q.notify({
        type: 'negative',
        message: error.response?.data?.detail || 'Failed to delete diagnosis',
      });
    }
  });
};

const filterMedications = (val, update, abort) => {
  if (val === '') {
    update(() => {
      medicationOptions.value = allMedications.value;
    });
    return;
  }

  // Perform server-side search on pharmacy products
  update(async () => {
    try {
      // Search products filtered by sub_category_2 = 'Pharmacy' using service_type parameter
      const response = await priceListAPI.search(val, 'Pharmacy', 'product');
      console.log('Search medications response:', response);
      // The API returns the data directly, not wrapped in .data
      medicationOptions.value = response.data || [];
      console.log('Filtered medications count:', medicationOptions.value.length);
    } catch (error) {
      console.error('Failed to search medications:', error);
      // Fallback to local filtering if API fails
      const needle = val.toLowerCase();
      medicationOptions.value = allMedications.value.filter(
        (m) => m.item_name?.toLowerCase().indexOf(needle) > -1 || 
               m.item_code?.toLowerCase().indexOf(needle) > -1 ||
               m.medication_code?.toLowerCase().indexOf(needle) > -1 ||
               m.product_name?.toLowerCase().indexOf(needle) > -1
      );
    }
  });
};

const onMedicationSelected = (medication) => {
  if (medication) {
    // Auto-fill medicine code and name from selected medication
    prescriptionForm.medicine_code = medication.item_code || medication.medication_code || '';
    // Include formulation in the name if available
    let medicineName = medication.item_name || medication.product_name || '';
    if (medication.formulation) {
      medicineName = `${medicineName} (${medication.formulation})`;
    }
    prescriptionForm.medicine_name = medicineName;
    // Set quantity to 0 for doctors (pharmacy will set it during confirmation)
    if (authStore.userRole === 'Doctor') {
      prescriptionForm.quantity = 0;
    }
  } else {
    prescriptionForm.medicine_code = '';
    prescriptionForm.medicine_name = '';
  }
};

const loadPharmacyMedications = async () => {
  try {
    // Load all products where sub_category_2 = 'Pharmacy' (case-insensitive)
    // Using service_type='Pharmacy' filters products by sub_category_2
    const response = await priceListAPI.search('', 'Pharmacy', 'product');
    console.log('Pharmacy medications response:', response);
    // The API returns the data directly, not wrapped in .data
    const medications = response.data || [];
    allMedications.value = medications;
    medicationOptions.value = medications;
    console.log('Loaded medications count:', medications.length);
  } catch (error) {
    console.error('Failed to load pharmacy medications:', error);
    allMedications.value = [];
    medicationOptions.value = [];
  }
};

const editPrescription = (prescription) => {
  // Prevent editing if prescription is confirmed
  if (prescription.is_confirmed) {
    $q.notify({
      type: 'warning',
      message: 'Cannot edit prescription that has been confirmed by pharmacy staff',
      position: 'top'
    });
    return;
  }
  editingPrescriptionId.value = prescription.id;
  prescriptionForm.encounter_id = prescription.encounter_id;
  prescriptionForm.medicine_code = prescription.medicine_code || '';
  prescriptionForm.medicine_name = prescription.medicine_name || '';
  prescriptionForm.dose = prescription.dose || '';
  prescriptionForm.unit = prescription.unit || '';
  prescriptionForm.frequency = prescription.frequency || '';
  prescriptionForm.duration = prescription.duration || '';
  prescriptionForm.instructions = prescription.instructions || '';
  prescriptionForm.quantity = prescription.quantity || 1;
  // Try to find the medication in the list to set selectedMedication
  selectedMedication.value = allMedications.value.find(
    m => (m.item_code || m.medication_code) === prescription.medicine_code
  ) || null;
  showPrescriptionDialog.value = true;
};

const resetPrescriptionForm = () => {
  editingPrescriptionId.value = null;
  selectedMedication.value = null;
    Object.assign(prescriptionForm, {
    encounter_id: encounterStore.currentEncounter?.id || null,
      medicine_code: '',
      medicine_name: '',
      dose: '',
      unit: '',
      frequency: '',
      duration: '',
      instructions: '',
      quantity: authStore.userRole === 'Doctor' ? 0 : 1, // Set to 0 for doctors, 1 for others
    });
};

const savePrescription = async () => {
  try {
    // For doctors, set quantity to 0 (pharmacy will set it during confirmation)
    const prescriptionData = { ...prescriptionForm };
    if (authStore.userRole === 'Doctor') {
      prescriptionData.quantity = 0;
    }
    
    if (editingPrescriptionId.value) {
      // Update existing prescription
      await consultationAPI.updatePrescription(editingPrescriptionId.value, prescriptionData);
      $q.notify({
        type: 'positive',
        message: 'Prescription updated successfully',
      });
    } else {
      // Create new prescription
      await consultationAPI.createPrescription(prescriptionData);
      $q.notify({
        type: 'positive',
        message: 'Prescription added successfully',
      });
    }
    
    await encounterStore.loadEncounterData(encounterStore.currentEncounter.id);
    showPrescriptionDialog.value = false;
    resetPrescriptionForm();
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || (editingPrescriptionId.value ? 'Failed to update prescription' : 'Failed to add prescription'),
    });
  }
};


const deletePrescription = (prescription) => {
  // Prevent deleting if prescription is confirmed
  if (prescription.is_confirmed) {
    $q.notify({
      type: 'warning',
      message: 'Cannot delete prescription that has been confirmed by pharmacy staff',
      position: 'top'
    });
    return;
  }
  
  $q.dialog({
    title: 'Delete Prescription',
    message: `Are you sure you want to delete this prescription: "${prescription.medicine_name}"?`,
    cancel: true,
    persistent: true,
  }).onOk(async () => {
    try {
      await consultationAPI.deletePrescription(prescription.id);
      $q.notify({
        type: 'positive',
        message: 'Prescription deleted successfully',
      });
      await encounterStore.loadEncounterData(encounterStore.currentEncounter.id);
    } catch (error) {
      $q.notify({
        type: 'negative',
        message: error.response?.data?.detail || 'Failed to delete prescription',
      });
    }
  });
};

// Load service types on mount
const loadServiceTypes = async () => {
  try {
    const response = await priceListAPI.getServiceTypes();
    serviceTypeOptions.value = response.data || [];
  } catch (error) {
    console.error('Failed to load service types:', error);
    serviceTypeOptions.value = [];
  }
};

// Load procedures when service type is selected
const onServiceTypeSelected = async (serviceType) => {
  if (!serviceType) {
    allProcedures.value = [];
    procedureOptions.value = [];
    selectedProcedure.value = null;
    investigationForm.gdrg_code = '';
    return;
  }
  
  try {
    const response = await priceListAPI.getProceduresByServiceType(serviceType);
    console.log('Procedures response:', response.data);
    
    // Handle both array and grouped object formats
    let procedures = [];
    if (Array.isArray(response.data)) {
      // New format: array
      procedures = response.data;
    } else if (response.data && typeof response.data === 'object') {
      // Old format: grouped object - extract procedures for the selected service type
      procedures = response.data[serviceType] || [];
    }
    
    allProcedures.value = procedures;
    procedureOptions.value = allProcedures.value;
    selectedProcedure.value = null;
    investigationForm.gdrg_code = '';
    
    console.log('Loaded procedures:', allProcedures.value.length);
  } catch (error) {
    console.error('Failed to load procedures:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to load procedures',
    });
    allProcedures.value = [];
    procedureOptions.value = [];
  }
};

// Filter procedures for autocomplete
const filterProcedures = (val, update) => {
  if (val === '') {
    update(() => {
      procedureOptions.value = allProcedures.value;
    });
    return;
  }
  
  update(() => {
    const needle = val.toLowerCase();
    procedureOptions.value = allProcedures.value.filter(
      (p) => p.service_name.toLowerCase().indexOf(needle) > -1 ||
             p.g_drg_code.toLowerCase().indexOf(needle) > -1
    );
  });
};

// When procedure is selected, auto-fill GDRG code, procedure name, and price
const onProcedureSelected = async (procedure) => {
  if (procedure && typeof procedure === 'object') {
    investigationForm.gdrg_code = procedure.g_drg_code;
    investigationForm.procedure_name = procedure.service_name || '';
    
    // Auto-fetch price from price list
    if (procedure.g_drg_code && encounterStore.currentEncounter) {
      try {
        // Check if patient is insured (has CCC number)
        const isInsured = !!encounterStore.currentEncounter.ccc_number;
        // Use base_rate for cash patients, nhia_claim_co_payment or base_rate for insured
        const price = isInsured && procedure.nhia_claim_co_payment 
          ? procedure.nhia_claim_co_payment 
          : procedure.base_rate;
        investigationForm.price = price ? price.toString() : '';
      } catch (error) {
        console.error('Error fetching price:', error);
        investigationForm.price = '';
      }
    }
  } else if (procedure) {
    // If it's just the code, find the procedure object
    const proc = allProcedures.value.find(p => p.g_drg_code === procedure);
    if (proc) {
      investigationForm.gdrg_code = proc.g_drg_code;
      investigationForm.procedure_name = proc.service_name || '';
      
      // Auto-fetch price
      if (encounterStore.currentEncounter) {
        const isInsured = !!encounterStore.currentEncounter.ccc_number;
        const price = isInsured && proc.nhia_claim_co_payment 
          ? proc.nhia_claim_co_payment 
          : proc.base_rate;
        investigationForm.price = price ? price.toString() : '';
      }
    }
  } else {
    investigationForm.gdrg_code = '';
    investigationForm.procedure_name = '';
    investigationForm.price = '';
  }
};

const editInvestigation = async (investigation) => {
  // Prevent editing if investigation is confirmed
  if (investigation.confirmed_by || investigation.status === 'confirmed' || investigation.status === 'completed') {
    $q.notify({
      type: 'warning',
      message: 'Cannot edit investigation that has been confirmed by staff',
      position: 'top'
    });
    return;
  }
  
  editingInvestigationId.value = investigation.id;
  investigationForm.encounter_id = investigation.encounter_id;
  investigationForm.gdrg_code = investigation.gdrg_code || '';
  investigationForm.procedure_name = investigation.procedure_name || '';
  investigationForm.investigation_type = investigation.investigation_type || '';
  investigationForm.notes = investigation.notes || '';
  investigationForm.price = investigation.price || '';
  
  // Try to find the procedure in existing procedures or load if needed
  let proc = allProcedures.value.find(p => p.g_drg_code === investigation.gdrg_code);
  
  // If not found, we'll need to load procedures. For now, set what we have
  // The user can manually select the service type and procedure
  if (proc) {
    investigationForm.service_type = proc.service_type || '';
    selectedProcedure.value = proc;
  } else {
    // If we don't have the procedure loaded, clear and let user select
    investigationForm.service_type = '';
    selectedProcedure.value = null;
  }
  
  showInvestigationDialog.value = true;
};

const resetInvestigationForm = () => {
  editingInvestigationId.value = null;
  selectedProcedure.value = null;
  Object.assign(investigationForm, {
    encounter_id: encounterStore.currentEncounter?.id || null,
    service_type: '',
    gdrg_code: '',
    procedure_name: '',
    investigation_type: '',
    notes: '',
    price: '',
  });
  allProcedures.value = [];
  procedureOptions.value = [];
};

const saveInvestigation = async () => {
  // Validate that procedure is selected
  if (!selectedProcedure.value || !investigationForm.gdrg_code) {
    $q.notify({
      type: 'warning',
      message: 'Please select a procedure',
    });
    return;
  }
  
  try {
    if (editingInvestigationId.value) {
      // Update existing investigation
      await consultationAPI.updateInvestigation(editingInvestigationId.value, investigationForm);
      $q.notify({
        type: 'positive',
        message: 'Investigation updated successfully',
      });
    } else {
      // Create new investigation
    await consultationAPI.createInvestigation(investigationForm);
      $q.notify({
        type: 'positive',
        message: 'Investigation added successfully',
      });
    }
    
    await encounterStore.loadEncounterData(encounterStore.currentEncounter.id);
    showInvestigationDialog.value = false;
    resetInvestigationForm();
  } catch (error) {
    console.error('Failed to save investigation:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || (editingInvestigationId.value ? 'Failed to update investigation' : 'Failed to add investigation'),
    });
  }
};

const cancelInvestigation = (investigation) => {
  // Only allow cancelling confirmed investigations
  if (investigation.status !== 'confirmed') {
    $q.notify({
      type: 'warning',
      message: 'Can only cancel confirmed investigations',
      position: 'top'
    });
    return;
  }
  
  if (investigation.status === 'cancelled') {
    $q.notify({
      type: 'warning',
      message: 'Investigation is already cancelled',
      position: 'top'
    });
    return;
  }
  
  $q.dialog({
    title: 'Cancel Investigation',
    message: `Cancel investigation: "${investigation.procedure_name || investigation.gdrg_code}"?`,
    prompt: {
      model: '',
      type: 'text',
      label: 'Reason for cancellation *',
      hint: 'Enter the reason for cancelling this investigation (e.g., Client cannot pay)',
      isValid: (val) => val && val.length > 0,
    },
    cancel: true,
    persistent: true,
  }).onOk(async (reason) => {
    try {
      await consultationAPI.cancelInvestigation(investigation.id, { reason });
      $q.notify({
        type: 'positive',
        message: 'Investigation cancelled successfully',
      });
      await encounterStore.loadEncounterData(encounterStore.currentEncounter.id);
    } catch (error) {
      $q.notify({
        type: 'negative',
        message: error.response?.data?.detail || 'Failed to cancel investigation',
      });
    }
  });
};

const deleteInvestigation = (investigation) => {
  // Prevent deleting if investigation is confirmed, completed, or cancelled
  if (investigation.confirmed_by || investigation.status === 'confirmed' || investigation.status === 'completed' || investigation.status === 'cancelled') {
    $q.notify({
      type: 'warning',
      message: 'Cannot delete investigation that has been confirmed, completed, or cancelled',
      position: 'top'
    });
    return;
  }
  
  $q.dialog({
    title: 'Delete Investigation',
    message: `Are you sure you want to delete this investigation: "${investigation.procedure_name || investigation.gdrg_code}"?`,
    cancel: true,
    persistent: true,
  }).onOk(async () => {
    try {
      await consultationAPI.deleteInvestigation(investigation.id);
      $q.notify({
        type: 'positive',
        message: 'Investigation deleted successfully',
      });
      await encounterStore.loadEncounterData(encounterStore.currentEncounter.id);
    } catch (error) {
      $q.notify({
        type: 'negative',
        message: error.response?.data?.detail || 'Failed to delete investigation',
      });
    }
  });
};

const viewInvestigationResults = async (investigation) => {
  selectedInvestigation.value = investigation;
  investigationResult.value = null;
  loadingResults.value = true;
  showResultsDialog.value = true;
  
  try {
    let response;
    
    // Fetch the appropriate result based on investigation type
    switch (investigation.investigation_type) {
      case 'lab':
        response = await consultationAPI.getLabResult(investigation.id);
        break;
      case 'scan':
        response = await consultationAPI.getScanResult(investigation.id);
        break;
      case 'xray':
        response = await consultationAPI.getXrayResult(investigation.id);
        break;
      default:
        $q.notify({
          type: 'warning',
          message: 'Unknown investigation type',
        });
        return;
    }
    
    investigationResult.value = response.data || null;
  } catch (error) {
    console.error('Failed to load investigation results:', error);
    // If result doesn't exist, investigationResult.value will remain null
    // This is okay - we'll show "Results not yet available" message
    if (error.response?.status !== 404) {
      $q.notify({
        type: 'warning',
        message: 'Failed to load results. Results may not be available yet.',
      });
    }
  } finally {
    loadingResults.value = false;
  }
};

const downloadInvestigationAttachment = async () => {
  if (!selectedInvestigation.value || !investigationResult.value?.attachment_path) {
    $q.notify({
      type: 'warning',
      message: 'No attachment available to download',
    });
    return;
  }

  try {
    let response;
    
    // Download the appropriate attachment based on investigation type
    switch (selectedInvestigation.value.investigation_type) {
      case 'lab':
        response = await consultationAPI.downloadLabResultAttachment(selectedInvestigation.value.id);
        break;
      case 'scan':
        response = await consultationAPI.downloadScanResultAttachment(selectedInvestigation.value.id);
        break;
      case 'xray':
        response = await consultationAPI.downloadXrayResultAttachment(selectedInvestigation.value.id);
        break;
      default:
        $q.notify({
          type: 'warning',
          message: 'Unknown investigation type',
        });
        return;
    }
    
    const blob = response.data instanceof Blob 
      ? response.data 
      : new Blob([response.data], { 
          type: response.headers['content-type'] || 'application/pdf' 
        });
    
    const contentDisposition = response.headers['content-disposition'] || 
                                response.headers['Content-Disposition'];
    let filename = investigationResult.value.attachment_path.split('/').pop() || 'result.pdf';
    
    if (contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
      if (filenameMatch && filenameMatch[1]) {
        filename = filenameMatch[1].replace(/['"]/g, '');
      }
    }
    
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    
    setTimeout(() => {
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    }, 100);
    
    $q.notify({
      type: 'positive',
      message: 'File downloaded successfully',
    });
  } catch (error) {
    console.error('Download error:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to download attachment',
    });
  }
};

const finalizeConsultation = () => {
  $q.dialog({
    title: 'Finalize Consultation',
    message: 'Are you sure you want to finalize this consultation? This action cannot be easily undone. Please ensure all required billing is confirmed.',
    cancel: true,
    persistent: true,
    ok: {
      label: 'Finalize',
      color: 'positive',
      flat: false
    },
    cancel: {
      label: 'Cancel',
      color: 'grey',
      flat: true
    }
  }).onOk(async () => {
    // Validate requirements before finalizing (frontend guard)
    // Check for diagnosis
    if (!encounterStore.encounterDiagnoses || encounterStore.encounterDiagnoses.length === 0) {
      $q.notify({ 
        type: 'negative', 
        message: 'Cannot finalize consultation. At least one diagnosis is required.' 
      });
      return;
    }
    
    // Check for outcome
    const outcomeVal = consultationNotes.value?.outcome || notesForm.outcome;
    if (!outcomeVal) {
      $q.notify({ 
        type: 'negative', 
        message: 'Cannot finalize consultation. Consultation outcome is required.' 
      });
      return;
    }
    
    // Check for follow-up date
    const followUpDate = consultationNotes.value?.follow_up_date || notesForm.follow_up_date;
    if (!followUpDate) {
      $q.notify({ 
        type: 'negative', 
        message: 'Cannot finalize consultation. Follow-up date is required.' 
      });
      return;
    }
    
    // Note: Payment validation is handled by backend
    // For insured clients, bills can be 0 (fully covered)
    // For non-insured clients, all bills must be paid
    
    finalizing.value = true;
    let finalizationSuccess = false;
    try {
      // Save notes first
      await saveConsultationNotes();
      // Then finalize (suppress store notification, we'll show our own)
      await encounterStore.updateStatus(encounterStore.currentEncounter.id, 'finalized', true);
      finalizationSuccess = true;
      
      // Update status locally to avoid reload issues
      if (encounterStore.currentEncounter?.id === encounterStore.currentEncounter.id) {
        encounterStore.currentEncounter.status = 'finalized';
      }
      
      // Clear all drafts after finalization
      clearDraft('presenting_complaints');
      clearDraft('doctor_notes');
      
      // Try to reload encounter data (but don't fail if this errors)
      try {
        await encounterStore.loadEncounterData(encounterStore.currentEncounter.id);
      } catch (reloadError) {
        console.warn('Failed to reload encounter data after finalization:', reloadError);
        // Don't show error - finalization succeeded
      }
      
      $q.notify({
        type: 'positive',
        message: 'Consultation finalized successfully',
        position: 'top'
      });
    } catch (error) {
      console.error('Failed to finalize consultation:', error);
      // Only show error if finalization actually failed
      if (!finalizationSuccess) {
        $q.notify({ 
          type: 'negative', 
          message: error.response?.data?.detail || 'Failed to finalize',
          position: 'top'
        });
      }
    } finally {
      finalizing.value = false;
    }
  });
};

const updateConsultation = async () => {
  try {
    // Just save consultation notes without changing status
    await saveConsultationNotes();
    $q.notify({
      type: 'positive',
      message: 'Consultation updated successfully',
    });
    await encounterStore.loadEncounter(encounterStore.currentEncounter.id);
  } catch (error) {
    console.error('Failed to update consultation:', error);
    $q.notify({ type: 'negative', message: error.response?.data?.detail || 'Failed to update consultation' });
  }
};

const saveDraftAndAwaitServices = async () => {
  try {
    // Save notes first (including outcome/ward if set)
    await saveConsultationNotes();
    // Move encounter to awaiting_services
    await encounterStore.updateStatus(encounterStore.currentEncounter.id, 'awaiting_services');
    $q.notify({ type: 'positive', message: 'Saved and moved to Awaiting Services' });
    await encounterStore.loadEncounter(encounterStore.currentEncounter.id);
  } catch (error) {
    console.error('Failed to move to awaiting services:', error);
    $q.notify({ type: 'negative', message: error.response?.data?.detail || 'Failed to update status' });
  }
};

const cancelConsultation = () => {
  // Clear any pending draft save timers
  Object.keys(draftSaveTimers.value).forEach(field => {
    if (draftSaveTimers.value[field]) {
      clearTimeout(draftSaveTimers.value[field]);
    }
  });
  draftSaveTimers.value = {};
  
  encounterStore.clearCurrent();
  encounterLoaded.value = false;
  searchEncounterId.value = '';
};

// Vitals graph functions
const plotVitalsGraph = (singleVital) => {
  // Include current vitals if available
  const allVitalsForGraph = [];
  
  if (encounterStore.encounterVitals) {
    allVitalsForGraph.push({
      ...encounterStore.encounterVitals,
      encounter_id: encounterStore.currentEncounter?.id || 0,
      created_at: encounterStore.currentEncounter?.created_at || new Date().toISOString()
    });
  }
  
  // Add selected vital and all previous vitals before it
  const selectedIndex = previousVitals.value.findIndex(v => 
    v.encounter_id === singleVital.encounter_id && v.created_at === singleVital.created_at
  );
  
  if (selectedIndex >= 0) {
    // Add all vitals up to and including the selected one
    previousVitals.value.slice(selectedIndex).forEach(v => {
      allVitalsForGraph.push(v);
    });
  } else {
    allVitalsForGraph.push(singleVital);
  }
  
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
  // Include current vitals if available
  const allVitalsForGraph = [];
  
  if (encounterStore.encounterVitals) {
    allVitalsForGraph.push({
      ...encounterStore.encounterVitals,
      encounter_id: encounterStore.currentEncounter?.id || 0,
      created_at: encounterStore.currentEncounter?.created_at || new Date().toISOString()
    });
  }
  
  // Add all previous vitals
  allVitalsForGraph.push(...previousVitals.value);
  
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
      ctx.fillText(formatDate(vitalsForGraph.value[i].created_at), x, height - padding + 10);
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
      // Ensure canvas is fully rendered before drawing
      setTimeout(() => {
        if (vitalsCanvas.value) {
          drawVitalsGraph();
        }
      }, 300);
    });
  }
});

// Functions to use previous data
const usePreviousDiagnosis = (previousDiagnosis) => {
  try {
    if (!encounterStore.currentEncounter?.id) {
      $q.notify({ type: 'warning', message: 'Please load an encounter first' });
      return;
    }
    
    // Prefill the diagnosis form
    diagnosisForm.encounter_id = encounterStore.currentEncounter.id;
    diagnosisForm.icd10 = previousDiagnosis.icd10 || previousDiagnosis.icd10_code || '';
    diagnosisForm.diagnosis = previousDiagnosis.diagnosis || '';
    diagnosisForm.gdrg_code = previousDiagnosis.gdrg_code || previousDiagnosis.g_drg_code || '';
    diagnosisForm.is_provisional = previousDiagnosis.is_provisional || false;
    diagnosisForm.is_chief = previousDiagnosis.is_chief || false;
    
    // Clear editing state (creating new diagnosis)
    editingDiagnosisId.value = null;
    
    // Close previous diagnoses dialog and open diagnosis dialog
    showPreviousDiagnosesDialog.value = false;
    showDiagnosisDialog.value = true;
    
    $q.notify({
      type: 'info',
      message: 'Diagnosis form prefilled from previous entry',
      timeout: 2000
    });
  } catch (error) {
    console.error('Error in usePreviousDiagnosis:', error);
    $q.notify({ type: 'negative', message: 'Failed to prefill diagnosis form' });
  }
};

const usePreviousPrescription = (previousPrescription) => {
  try {
    if (!encounterStore.currentEncounter?.id) {
      $q.notify({ type: 'warning', message: 'Please load an encounter first' });
      return;
    }
    
    // Prefill the prescription form
    prescriptionForm.encounter_id = encounterStore.currentEncounter.id;
    prescriptionForm.medicine_code = previousPrescription.medicine_code || '';
    prescriptionForm.medicine_name = previousPrescription.medicine_name || '';
    prescriptionForm.dose = previousPrescription.dose || '';
    prescriptionForm.unit = previousPrescription.unit || '';
    prescriptionForm.frequency = previousPrescription.frequency || '';
    prescriptionForm.duration = previousPrescription.duration || '';
    prescriptionForm.instructions = previousPrescription.instructions || '';
    prescriptionForm.quantity = previousPrescription.quantity || 1;
    
    // Try to find the medication in the list to set selectedMedication
    selectedMedication.value = allMedications.value.find(
      m => (m.item_code || m.medication_code) === previousPrescription.medicine_code
    ) || null;
    
    // Clear editing state (creating new prescription)
    editingPrescriptionId.value = null;
    
    // Close previous prescriptions dialog and open prescription dialog
    showPreviousPrescriptionsDialog.value = false;
    showPrescriptionDialog.value = true;
    
    $q.notify({
      type: 'info',
      message: 'Prescription form prefilled from previous entry',
      timeout: 2000
    });
  } catch (error) {
    console.error('Error in usePreviousPrescription:', error);
    $q.notify({ type: 'negative', message: 'Failed to prefill prescription form' });
  }
};

// Functions to load previous data
const showPreviousVitals = async () => {
  if (!encounterStore.currentEncounter?.patient_id) {
    $q.notify({ type: 'warning', message: 'Patient information not available' });
    return;
  }
  
  showPreviousVitalsDialog.value = true;
  loadingPreviousVitals.value = true;
  
  try {
    // Get all encounters for this patient
    const encountersResponse = await encountersAPI.getPatientEncounters(encounterStore.currentEncounter.patient_id);
    const allEncounters = encountersResponse.data.filter(e => !e.archived && e.id !== encounterStore.currentEncounter.id);
    
    // Load vitals for each encounter
    const vitalsPromises = allEncounters.map(async (encounter) => {
      try {
        const vitalsResponse = await vitalsAPI.getByEncounter(encounter.id);
        if (vitalsResponse.data) {
          return { ...vitalsResponse.data, encounter_id: encounter.id, created_at: encounter.created_at };
        }
      } catch (error) {
        // 404 is expected when an encounter doesn't have vitals - don't log it
        if (error.response?.status !== 404) {
          console.error(`Failed to load vitals for encounter ${encounter.id}:`, error);
        }
      }
      return null;
    });
    
    const vitalsResults = await Promise.all(vitalsPromises);
    previousVitals.value = vitalsResults.filter(v => v !== null).sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
  } catch (error) {
    console.error('Failed to load previous vitals:', error);
    $q.notify({ type: 'negative', message: 'Failed to load previous vitals' });
  } finally {
    loadingPreviousVitals.value = false;
  }
};

const showPreviousComplaints = async () => {
  if (!encounterStore.currentEncounter?.patient_id) {
    $q.notify({ type: 'warning', message: 'Patient information not available' });
    return;
  }
  
  showPreviousComplaintsDialog.value = true;
  loadingPreviousComplaints.value = true;
  
  try {
    const encountersResponse = await encountersAPI.getPatientEncounters(encounterStore.currentEncounter.patient_id);
    const allEncounters = encountersResponse.data.filter(e => !e.archived && e.id !== encounterStore.currentEncounter.id);
    
    const complaintsPromises = allEncounters.map(async (encounter) => {
      try {
        const notesResponse = await consultationAPI.getConsultationNotes(encounter.id);
        if (notesResponse.data?.presenting_complaints) {
          return {
            encounter_id: encounter.id,
            presenting_complaints: notesResponse.data.presenting_complaints,
            created_at: encounter.created_at
          };
        }
      } catch (error) {
        // 404 is expected when an encounter doesn't have consultation notes - don't log it
        if (error.response?.status !== 404) {
          console.error(`Failed to load complaints for encounter ${encounter.id}:`, error);
        }
      }
      return null;
    });
    
    const complaintsResults = await Promise.all(complaintsPromises);
    previousComplaints.value = complaintsResults.filter(c => c !== null).sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
  } catch (error) {
    console.error('Failed to load previous complaints:', error);
    $q.notify({ type: 'negative', message: 'Failed to load previous complaints' });
  } finally {
    loadingPreviousComplaints.value = false;
  }
};

const showPreviousDiagnoses = async () => {
  if (!encounterStore.currentEncounter?.patient_id) {
    $q.notify({ type: 'warning', message: 'Patient information not available' });
    return;
  }
  
  showPreviousDiagnosesDialog.value = true;
  loadingPreviousDiagnoses.value = true;
  
  try {
    const encountersResponse = await encountersAPI.getPatientEncounters(encounterStore.currentEncounter.patient_id);
    const allEncounters = encountersResponse.data.filter(e => !e.archived && e.id !== encounterStore.currentEncounter.id);
    
    const diagnosesPromises = allEncounters.map(async (encounter) => {
      try {
        const diagnosesResponse = await consultationAPI.getDiagnoses(encounter.id);
        if (diagnosesResponse.data && diagnosesResponse.data.length > 0) {
          return diagnosesResponse.data.map(d => ({
            ...d,
            encounter_id: encounter.id,
            created_at: encounter.created_at
          }));
        }
      } catch (error) {
        // 404 is expected when an encounter doesn't have diagnoses - don't log it
        if (error.response?.status !== 404) {
          console.error(`Failed to load diagnoses for encounter ${encounter.id}:`, error);
        }
      }
      return [];
    });
    
    const diagnosesResults = await Promise.all(diagnosesPromises);
    previousDiagnoses.value = diagnosesResults.flat().sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
  } catch (error) {
    console.error('Failed to load previous diagnoses:', error);
    $q.notify({ type: 'negative', message: 'Failed to load previous diagnoses' });
  } finally {
    loadingPreviousDiagnoses.value = false;
  }
};

const showPreviousPrescriptions = async () => {
  if (!encounterStore.currentEncounter?.patient_id) {
    $q.notify({ type: 'warning', message: 'Patient information not available' });
    return;
  }
  
  showPreviousPrescriptionsDialog.value = true;
  loadingPreviousPrescriptions.value = true;
  
  try {
    const encountersResponse = await encountersAPI.getPatientEncounters(encounterStore.currentEncounter.patient_id);
    const allEncounters = encountersResponse.data.filter(e => !e.archived && e.id !== encounterStore.currentEncounter.id);
    
    const prescriptionsPromises = allEncounters.map(async (encounter) => {
      try {
        const prescriptionsResponse = await consultationAPI.getPrescriptions(encounter.id);
        if (prescriptionsResponse.data && prescriptionsResponse.data.length > 0) {
          return prescriptionsResponse.data.map(p => ({
            ...p,
            encounter_id: encounter.id,
            created_at: encounter.created_at
          }));
        }
      } catch (error) {
        // 404 is expected when an encounter doesn't have prescriptions - don't log it
        if (error.response?.status !== 404) {
          console.error(`Failed to load prescriptions for encounter ${encounter.id}:`, error);
        }
      }
      return [];
    });
    
    const prescriptionsResults = await Promise.all(prescriptionsPromises);
    previousPrescriptions.value = prescriptionsResults.flat().sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
  } catch (error) {
    console.error('Failed to load previous prescriptions:', error);
    $q.notify({ type: 'negative', message: 'Failed to load previous prescriptions' });
  } finally {
    loadingPreviousPrescriptions.value = false;
  }
};

const showPreviousInvestigations = async () => {
  if (!encounterStore.currentEncounter?.patient_id) {
    $q.notify({ type: 'warning', message: 'Patient information not available' });
    return;
  }
  
  showPreviousInvestigationsDialog.value = true;
  loadingPreviousInvestigations.value = true;
  
  try {
    const encountersResponse = await encountersAPI.getPatientEncounters(encounterStore.currentEncounter.patient_id);
    const allEncounters = encountersResponse.data.filter(e => !e.archived && e.id !== encounterStore.currentEncounter.id);
    
    const investigationsPromises = allEncounters.map(async (encounter) => {
      try {
        const investigationsResponse = await consultationAPI.getInvestigations(encounter.id);
        if (investigationsResponse.data && investigationsResponse.data.length > 0) {
          return investigationsResponse.data.map(i => ({
            ...i,
            encounter_id: encounter.id,
            created_at: encounter.created_at
          }));
        }
      } catch (error) {
        // 404 is expected when an encounter doesn't have investigations - don't log it
        if (error.response?.status !== 404) {
          console.error(`Failed to load investigations for encounter ${encounter.id}:`, error);
        }
      }
      return [];
    });
    
    const investigationsResults = await Promise.all(investigationsPromises);
    previousInvestigations.value = investigationsResults.flat().sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
  } catch (error) {
    console.error('Failed to load previous investigations:', error);
    $q.notify({ type: 'negative', message: 'Failed to load previous investigations' });
  } finally {
    loadingPreviousInvestigations.value = false;
  }
};

onMounted(() => {
  loadServiceTypes();
  // Load DRG diagnoses when page mounts
  loadDrgDiagnoses();
  // Load pharmacy medications when page mounts
  loadPharmacyMedications();
  
  // If encounterId is in route, load it
  if (route.params.encounterId) {
    searchEncounterId.value = route.params.encounterId;
    loadEncounter();
  } else {
    // Otherwise, set today and load today's encounters
    setToday();
  }
});

// Cleanup on unmount
onUnmounted(() => {
  // Clear any pending draft save timers
  Object.keys(draftSaveTimers.value).forEach(field => {
    if (draftSaveTimers.value[field]) {
      clearTimeout(draftSaveTimers.value[field]);
    }
  });
  draftSaveTimers.value = {};
});
</script>

