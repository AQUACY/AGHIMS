<template>
  <q-page class="q-pa-md">
    <div class="text-h4 q-mb-md text-weight-bold glass-text">Pharmacy Services</div>

    <!-- Patient Search -->
    <q-card class="q-mb-md glass-card" flat>
      <q-card-section>
        <div class="text-h6 q-mb-md glass-text">Search Patient</div>
        <div class="row q-gutter-md">
          <q-input
            v-model="cardNumber"
            filled
            label="Patient Card Number"
            class="col-12 col-md-8"
            @keyup.enter="searchPatient"
            :disable="loadingPatient"
          />
          <q-btn
            color="primary"
            label="Search"
            @click="searchPatient"
            class="col-12 col-md-4 glass-button"
            :loading="loadingPatient"
          />
        </div>
      </q-card-section>
    </q-card>

    <!-- Patient Info & Encounter Selection -->
    <q-card v-if="patient" class="q-mb-md glass-card" flat>
      <q-card-section>
        <div class="row items-center q-mb-md">
          <div>
            <div class="text-h6 glass-text">{{ patient.name }} {{ patient.surname || '' }}<span v-if="patient.other_names"> {{ patient.other_names }}</span></div>
            <div class="text-grey-7">Card: {{ patient.card_number }}</div>
            <div class="text-grey-7" v-if="patient.insurance_id">
              Insurance: {{ patient.insurance_id }}
            </div>
          </div>
          <q-space />
          <q-btn
            flat
            icon="refresh"
            label="Clear"
            @click="clearSearch"
          />
        </div>

        <!-- Service Selection: OPD or IPD -->
        <div class="q-mt-md">
          <div class="text-subtitle1 q-mb-sm glass-text">Select Service Type:</div>
          
          <!-- OPD Section -->
          <div v-if="todaysEncounter || oldEncounters.length > 0" class="q-mb-md">
            <div class="text-weight-medium q-mb-sm">OPD Services</div>
            
        <!-- Today's Encounter -->
            <div v-if="todaysEncounter" class="q-mb-sm">
              <q-card 
                flat 
                bordered 
                clickable
                :class="{ 'bg-blue-1': serviceType === 'opd' && selectedEncounterId === todaysEncounter.id }"
                @click="selectOPDEncounter(todaysEncounter.id)"
                style="cursor: pointer; background-color: rgba(46, 139, 87, 0.1);"
              >
            <q-card-section>
              <div class="row items-center">
                <div class="col">
                  <div class="text-weight-bold">Encounter #{{ todaysEncounter.id }} - {{ getEncounterProcedures(todaysEncounter) }}</div>
                  <div class="text-caption text-grey-7 q-mt-xs">
                    {{ formatDate(todaysEncounter.created_at) }} - Status: {{ todaysEncounter.status }}
        </div>
                </div>
                <q-badge color="green" label="Today" />
              </div>
            </q-card-section>
          </q-card>
        </div>

        <!-- Old Encounters - Collapsible -->
            <div v-if="oldEncounters.length > 0">
          <q-expansion-item
            v-model="oldEncountersExpanded"
            icon="history"
                :label="`Previous OPD Services (${oldEncounters.length})`"
                header-class="text-subtitle2"
            class="q-mb-sm"
          >
            <div class="q-gutter-sm q-pa-sm">
              <q-card
                v-for="encounter in oldEncounters"
                :key="encounter.id"
                flat
                bordered
                clickable
                    :class="{ 'bg-blue-1': serviceType === 'opd' && selectedEncounterId === encounter.id }"
                    @click="selectOPDEncounter(encounter.id)"
                style="cursor: pointer;"
              >
                <q-card-section class="q-pa-sm">
                  <div class="row items-center">
                    <div class="col">
                      <div class="text-weight-medium">Encounter #{{ encounter.id }} - {{ getEncounterProcedures(encounter) }}</div>
                      <div class="text-caption text-grey-7 q-mt-xs">
                        {{ formatDate(encounter.created_at) }} - Status: {{ encounter.status }}
                      </div>
                    </div>
                    <q-icon name="chevron_right" color="grey-6" />
                  </div>
                </q-card-section>
              </q-card>
            </div>
          </q-expansion-item>
            </div>
        </div>

          <!-- IPD Section -->
          <div v-if="wardAdmissions.length > 0" class="q-mb-md">
            <div class="text-weight-medium q-mb-sm">IPD Services</div>
            <div class="q-gutter-sm">
              <q-card
                v-for="admission in wardAdmissions"
                :key="admission.id"
                flat
                bordered
                clickable
                :class="{ 'bg-purple-1': serviceType === 'ipd' && selectedWardAdmissionId === admission.id }"
                @click="selectIPDAdmission(admission.id)"
                style="cursor: pointer;"
              >
                <q-card-section class="q-pa-sm">
                  <div class="row items-center">
                    <div class="col">
                      <div class="text-weight-medium">Ward: {{ admission.ward }}</div>
                      <div class="text-caption text-grey-7 q-mt-xs">
                        <span v-if="admission.bed_number">Bed: {{ admission.bed_number }} | </span>
                        Admitted: {{ formatDate(admission.admitted_at) }}
                      </div>
                    </div>
                    <q-badge color="purple" label="IPD" />
                    <q-icon name="chevron_right" color="grey-6" />
                  </div>
                </q-card-section>
              </q-card>
            </div>
          </div>

          <div v-if="(!todaysEncounter && oldEncounters.length === 0) && wardAdmissions.length === 0" class="text-grey-7 q-mt-md">
            No active services found for this patient
          </div>
        </div>
      </q-card-section>
    </q-card>

    <!-- Diagnoses -->
    <q-card v-if="(selectedEncounterId || selectedWardAdmissionId) && diagnoses.length > 0" class="q-mb-md">
      <q-card-section>
        <div class="text-h6 q-mb-md">Diagnoses</div>
        <div class="row q-gutter-md">
          <div
            v-for="diagnosis in diagnoses"
            :key="diagnosis.id"
            class="col-12 col-md-6"
          >
            <q-card flat bordered>
              <q-card-section>
                <div class="row items-center">
                  <div class="col">
                    <div class="text-weight-bold">{{ diagnosis.diagnosis }}</div>
                    <div class="text-grey-7 text-caption q-mt-xs">
                      <span v-if="diagnosis.icd10">ICD-10: {{ diagnosis.icd10 }}</span>
                      <span v-if="diagnosis.gdrg_code"> | G-DRG: {{ diagnosis.gdrg_code }}</span>
                    </div>
                  </div>
                  <div class="col-auto">
                    <q-badge
                      v-if="diagnosis.is_chief"
                      color="primary"
                      label="Chief"
                    />
                    <q-badge
                      :color="diagnosis.is_provisional ? 'orange' : 'green'"
                      :label="diagnosis.is_provisional ? 'Provisional' : 'Final'"
                      class="q-ml-xs"
                    />
                  </div>
                </div>
              </q-card-section>
            </q-card>
          </div>
        </div>
      </q-card-section>
    </q-card>

    <!-- Vitals - OPD -->
    <q-card v-if="serviceType === 'opd' && selectedEncounterId && vitals" class="q-mb-md">
      <q-card-section>
        <div class="text-h6 q-mb-md">Vitals</div>
        <div class="row q-gutter-md">
          <div v-if="vitals.bp" class="col-12 col-md-3">
            <div class="text-grey-7 text-caption">Blood Pressure</div>
            <div class="text-body1 text-weight-medium">{{ vitals.bp }}</div>
          </div>
          <div v-if="vitals.temperature" class="col-12 col-md-3">
            <div class="text-grey-7 text-caption">Temperature</div>
            <div class="text-body1 text-weight-medium">{{ vitals.temperature }}°C</div>
          </div>
          <div v-if="vitals.pulse" class="col-12 col-md-3">
            <div class="text-grey-7 text-caption">Pulse</div>
            <div class="text-body1 text-weight-medium">{{ vitals.pulse }} bpm</div>
          </div>
          <div v-if="vitals.weight" class="col-12 col-md-3">
            <div class="text-grey-7 text-caption">Weight</div>
            <div class="text-body1 text-weight-medium">{{ vitals.weight }} kg</div>
          </div>
          <div v-if="vitals.height" class="col-12 col-md-3">
            <div class="text-grey-7 text-caption">Height</div>
            <div class="text-body1 text-weight-medium">{{ vitals.height }} cm</div>
          </div>
        </div>
        <div v-if="vitals.remarks" class="q-mt-md">
          <div class="text-grey-7 text-caption">Remarks</div>
          <div class="text-body2">{{ vitals.remarks }}</div>
        </div>
        <div v-if="vitals.recorded_by_name" class="q-mt-md">
          <div class="text-grey-7 text-caption">Recorded By</div>
          <div class="text-body2 text-weight-medium">{{ vitals.recorded_by_name }}</div>
        </div>
      </q-card-section>
    </q-card>

    <!-- Vitals - IPD (Most Recent) -->
    <q-card v-if="serviceType === 'ipd' && selectedWardAdmissionId && latestInpatientVital" class="q-mb-md">
      <q-card-section>
        <div class="text-h6 q-mb-md">Latest Vitals</div>
        <div class="row q-gutter-md">
          <div v-if="latestInpatientVital.blood_pressure_systolic || latestInpatientVital.blood_pressure_diastolic" class="col-12 col-md-3">
            <div class="text-grey-7 text-caption">Blood Pressure</div>
            <div class="text-body1 text-weight-medium">
              {{ latestInpatientVital.blood_pressure_systolic }}/{{ latestInpatientVital.blood_pressure_diastolic }} mmHg
            </div>
          </div>
          <div v-if="latestInpatientVital.temperature" class="col-12 col-md-3">
            <div class="text-grey-7 text-caption">Temperature</div>
            <div class="text-body1 text-weight-medium">{{ latestInpatientVital.temperature }}°C</div>
          </div>
          <div v-if="latestInpatientVital.pulse" class="col-12 col-md-3">
            <div class="text-grey-7 text-caption">Pulse</div>
            <div class="text-body1 text-weight-medium">{{ latestInpatientVital.pulse }} bpm</div>
          </div>
          <div v-if="latestInpatientVital.respiratory_rate" class="col-12 col-md-3">
            <div class="text-grey-7 text-caption">Respiratory Rate</div>
            <div class="text-body1 text-weight-medium">{{ latestInpatientVital.respiratory_rate }} /min</div>
          </div>
          <div v-if="latestInpatientVital.oxygen_saturation" class="col-12 col-md-3">
            <div class="text-grey-7 text-caption">Oxygen Saturation</div>
            <div class="text-body1 text-weight-medium">{{ latestInpatientVital.oxygen_saturation }}%</div>
          </div>
          <div v-if="latestInpatientVital.weight" class="col-12 col-md-3">
            <div class="text-grey-7 text-caption">Weight</div>
            <div class="text-body1 text-weight-medium">{{ latestInpatientVital.weight }} kg</div>
          </div>
          <div v-if="latestInpatientVital.height" class="col-12 col-md-3">
            <div class="text-grey-7 text-caption">Height</div>
            <div class="text-body1 text-weight-medium">{{ latestInpatientVital.height }} cm</div>
          </div>
          <div v-if="latestInpatientVital.bmi" class="col-12 col-md-3">
            <div class="text-grey-7 text-caption">BMI</div>
            <div class="text-body1 text-weight-medium">{{ latestInpatientVital.bmi }}</div>
          </div>
        </div>
        <div v-if="latestInpatientVital.notes" class="q-mt-md">
          <div class="text-grey-7 text-caption">Notes</div>
          <div class="text-body2">{{ latestInpatientVital.notes }}</div>
        </div>
        <div v-if="latestInpatientVital.recorded_by_name" class="q-mt-md">
          <div class="text-grey-7 text-caption">Recorded By</div>
          <div class="text-body2 text-weight-medium">{{ latestInpatientVital.recorded_by_name }}</div>
          <div class="text-caption text-grey-6">{{ formatDate(latestInpatientVital.recorded_at) }}</div>
        </div>
      </q-card-section>
    </q-card>

    <!-- No Diagnoses/Vitals Message -->
    <q-card v-if="(selectedEncounterId || selectedWardAdmissionId) && !loadingData && diagnoses.length === 0 && !vitals && !latestInpatientVital" class="q-mb-md">
      <q-card-section class="text-center text-grey-7">
        No diagnoses or vitals recorded yet
      </q-card-section>
    </q-card>

    <!-- Payment Information Section -->
    <q-card v-if="selectedEncounterId && currentEncounter" class="q-mb-md glass-card">
      <q-card-section>
        <div class="text-h6 q-mb-md glass-text">Payment Information</div>
        <div class="row q-gutter-md">
          <div class="col-12 col-md-6">
            <div class="text-subtitle2 q-mb-xs text-grey-7">Insurance Status</div>
            <div class="row items-center q-gutter-sm">
              <q-badge 
                :color="isInsuredEncounter ? 'green' : 'orange'" 
                :label="isInsuredEncounter ? 'Insured (NHIA)' : 'Cash/Carry'"
                class="text-weight-bold"
              />
              <span v-if="isInsuredEncounter && currentEncounter.ccc_number" class="text-body2 text-grey-7">
                CCC: {{ currentEncounter.ccc_number }}
              </span>
            </div>
          </div>
          <div class="col-12 col-md-6">
            <div class="text-subtitle2 q-mb-xs text-grey-7">Confirmed Prescriptions Summary</div>
            <div class="text-body1">
              <div v-if="loadingPrescriptionCosts" class="text-grey-6">
                <q-spinner size="sm" class="q-mr-xs" />
                Calculating costs...
              </div>
              <div v-else>
                <div class="text-weight-bold text-h6" :class="prescriptionTotalAmount > 0 ? 'text-primary' : 'text-grey-6'">
                  ₵{{ prescriptionTotalAmount.toFixed(2) }}
                </div>
                <div class="text-caption text-grey-7 q-mt-xs">
                  {{ confirmedPrescriptionsCount }} confirmed prescription(s)
                </div>
              </div>
            </div>
          </div>
        </div>
        <div v-if="prescriptionTotalAmount > 0" class="q-mt-md q-pt-md" style="border-top: 1px solid rgba(255,255,255,0.1);">
          <div class="text-subtitle2 q-mb-xs text-grey-7">Payment Note</div>
          <div class="text-body2">
            <span v-if="isInsuredEncounter" class="text-info">
              This is an insured encounter. The patient will pay the co-payment amount shown above.
            </span>
            <span v-else class="text-warning">
              This is a cash/carry encounter. The patient will pay the full amount shown above.
            </span>
          </div>
        </div>
      </q-card-section>
    </q-card>

    <!-- Prescriptions Table -->
    <q-card v-if="selectedEncounterId || selectedWardAdmissionId">
      <q-card-section>
        <div class="row items-center q-mb-md">
          <div class="text-h6">Prescriptions</div>
          <q-space />
          <q-badge v-if="isFinalized" color="orange" label="Encounter Finalized" />
          <q-btn
            color="secondary"
            icon="print"
            label="Print Bill Card"
            @click="printBillCard"
            :disable="(serviceType === 'opd' && !selectedEncounterId) || (serviceType === 'ipd' && !selectedWardAdmissionId) || !patient"
            class="q-mr-sm"
          />
          <q-btn
            v-if="serviceType === 'opd'"
            color="primary"
            icon="add"
            label="Add Prescription"
            @click="openAddPrescriptionDialog"
            :disable="!selectedEncounterId"
            class="q-mr-sm"
          />
          <q-btn
            v-if="serviceType === 'ipd'"
            color="primary"
            icon="add"
            label="Add Medication"
            @click="openAddPrescriptionDialog"
            :disable="!selectedWardAdmissionId"
            class="q-mr-sm"
          />
          <q-btn
            v-if="serviceType === 'opd'"
            color="secondary"
            icon="local_pharmacy"
            label="Add External Prescription"
            @click="openAddExternalPrescriptionDialog"
            :disable="!selectedEncounterId"
          />
          <q-btn
            v-if="serviceType === 'ipd'"
            color="secondary"
            icon="local_pharmacy"
            label="Add External Prescription"
            @click="openAddExternalPrescriptionDialog"
            :disable="!selectedWardAdmissionId"
          />
          <q-btn
            v-if="serviceType === 'opd' && externalPrescriptions.length > 0"
            color="accent"
            icon="print"
            label="Print External Prescriptions"
            @click="printExternalPrescriptions"
            :disable="!selectedEncounterId || !patient"
            class="q-ml-sm"
          />
        </div>
        <!-- OPD Prescriptions Section -->
        <div v-if="serviceType === 'opd' && prescriptions.length > 0" class="q-mb-md">
          <div class="text-h6 q-mb-sm">OPD Prescriptions</div>
          <q-table
            :rows="prescriptions"
            :columns="columns"
            row-key="id"
            flat
            :loading="loadingPrescriptions"
          >
          <template v-slot:top>
            <div class="row items-center q-pa-sm">
              <q-checkbox
                :model-value="allPendingSelected"
                :indeterminate="somePendingSelected"
                @update:model-value="toggleAllPending"
                label="Select all pending prescriptions"
                class="q-mr-md"
              />
              <q-btn
                v-if="selectedPrescriptions.length > 0"
                color="primary"
                icon="add"
                label="Add Selected to Confirmation"
                @click="addSelectedToConfirmation"
                class="q-mr-sm"
              />
            </div>
          </template>
          <template v-slot:body-cell-prescriber="props">
            <q-td :props="props">
              <div v-if="props.row.prescriber_name">
                <div class="text-weight-medium">{{ props.row.prescriber_name }}</div>
                <div class="text-caption text-grey-7" v-if="props.row.prescriber_role">
                  {{ props.row.prescriber_role }}
                </div>
              </div>
              <span v-else class="text-grey-6">N/A</span>
            </q-td>
          </template>
          <template v-slot:body-cell-medicine_name="props">
            <q-td :props="props">
              <div class="row items-center q-gutter-xs">
                <span>{{ props.value }}</span>
                <q-badge v-if="props.row.is_external" color="orange" label="External" />
                <q-badge v-if="props.row.prescription_type === 'inpatient' || props.row.source === 'inpatient'" color="purple" label="IPD" />
              </div>
            </q-td>
          </template>
          <template v-slot:body-cell-status="props">
            <q-td :props="props">
              <!-- Don't show status badge for external prescriptions (they're going outside) -->
              <q-badge
                v-if="!props.row.is_external && props.row.is_confirmed && props.row.is_dispensed"
                color="positive"
                label="Dispensed"
              />
              <q-badge
                v-else-if="!props.row.is_external && props.row.is_confirmed"
                color="blue"
                label="Confirmed"
              />
              <q-badge
                v-else-if="!props.row.is_external"
                color="orange"
                label="Pending"
              />
              <span v-else class="text-grey-6 text-caption">External</span>
            </q-td>
          </template>
          <template v-slot:body-cell-selection="props">
            <q-td :props="props">
              <q-checkbox
                v-if="!props.row.is_confirmed && !props.row.is_external"
                :model-value="isPrescriptionSelected(props.row)"
                @update:model-value="togglePrescriptionSelection(props.row, $event)"
              />
            </q-td>
          </template>
          <template v-slot:body-cell-amount="props">
            <q-td :props="props">
              <div v-if="prescriptionPrices.has(props.row.id)" class="text-weight-medium text-primary">
                ₵{{ prescriptionPrices.get(props.row.id).toFixed(2) }}
              </div>
              <div v-else-if="props.row.is_external" class="text-grey-6 text-caption">
                External
              </div>
              <div v-else class="text-grey-6 text-caption">
                Calculating...
              </div>
            </q-td>
          </template>
          <template v-slot:body-cell-actions="props">
            <q-td :props="props">
              <div class="row q-gutter-xs">
              <q-btn
                  v-if="props.row.instructions"
                  size="sm"
                  color="info"
                  icon="visibility"
                  flat
                  round
                  @click="viewInstructions(props.row)"
                  title="View Instructions"
                />
              <!-- Edit button for Admin (even if confirmed) - only for OPD prescriptions -->
              <q-btn
                  v-if="authStore.userRole === 'Admin' && props.row.prescription_type !== 'inpatient' && props.row.source !== 'inpatient'"
                  size="sm"
                  color="secondary"
                  icon="edit"
                  label="Edit"
                  @click="editPrescription(props.row)"
                  :loading="updatingPrescriptionId === props.row.id"
                  :disable="confirmingId !== null || dispensingId !== null || returningId !== null || confirmingMultiple || deletingId !== null"
                >
                  <q-tooltip>Edit prescription (Admin only)</q-tooltip>
                </q-btn>
              <q-btn
                  v-if="!props.row.is_confirmed && !props.row.is_external && !props.row.is_dispensed"
                  size="sm"
                  color="primary"
                  icon="check_circle"
                  label="Confirm"
                  @click="confirmPrescription(props.row)"
                  :loading="confirmingId === props.row.id || confirmingInpatient === props.row.id"
                  :disable="confirmingId !== null || dispensingId !== null || returningId !== null || confirmingMultiple || deletingId !== null || unconfirmingId !== null || dispensingInpatient !== null || unconfirmingInpatient !== null"
                />
              <q-btn
                  v-if="props.row.is_confirmed && !props.row.is_dispensed && !props.row.is_external"
                  size="sm"
                  color="warning"
                  icon="undo"
                  label="Revert"
                  @click="unconfirmPrescription(props.row)"
                  :loading="unconfirmingId === props.row.id || unconfirmingInpatient === props.row.id"
                  :disable="confirmingId !== null || dispensingId !== null || returningId !== null || confirmingMultiple || deletingId !== null || unconfirmingId !== null || confirmingInpatient !== null || dispensingInpatient !== null"
                >
                  <q-tooltip>Revert confirmation (set back to pending)</q-tooltip>
                </q-btn>
                <q-btn
                  v-if="!props.row.is_dispensed && !props.row.is_external && props.row.is_confirmed && (props.row.prescription_type === 'inpatient' || props.row.source === 'inpatient' || canDispense(props.row))"
                  size="sm"
                  color="positive"
                  label="Dispense"
                  @click="dispensePrescription(props.row)"
                  :loading="dispensingId === props.row.id || returningId === props.row.id || dispensingInpatient === props.row.id"
                  :disable="dispensingId !== null || returningId !== null || confirmingInpatient !== null || unconfirmingInpatient !== null || (props.row.prescription_type !== 'inpatient' && props.row.source !== 'inpatient' && !canDispense(props.row))"
                >
                  <q-tooltip v-if="props.row.prescription_type !== 'inpatient' && props.row.source !== 'inpatient' && !canDispense(props.row)">
                    Bill must be paid before dispense
                  </q-tooltip>
                  <q-tooltip v-else>
                    Dispense prescription
                  </q-tooltip>
                </q-btn>
                <q-btn
                  v-else-if="props.row.is_dispensed && !props.row.is_external"
                  size="sm"
                  color="negative"
                  icon="undo"
                  label="Return"
                  @click="returnPrescription(props.row)"
                  :loading="returningId === props.row.id"
                  :disable="dispensingId !== null || returningId !== null"
                />
                <!-- Delete button for external prescriptions -->
                <q-btn
                  v-if="props.row.is_external"
                  size="sm"
                  color="negative"
                  icon="delete"
                  label="Delete"
                  @click="deleteExternalPrescription(props.row)"
                  :loading="deletingId === props.row.id"
                  :disable="confirmingId !== null || dispensingId !== null || returningId !== null || confirmingMultiple"
                  flat
                >
                  <q-tooltip>Delete external prescription</q-tooltip>
                </q-btn>
              </div>
            </q-td>
          </template>
          </q-table>
        </div>

        <!-- IPD Prescriptions Section -->
        <div v-if="serviceType === 'ipd' && inpatientPrescriptions.length > 0" class="q-mb-md">
          <div class="text-h6 q-mb-sm">IPD Prescriptions</div>
          <div class="text-caption text-info q-mb-sm">
            IPD medications can be dispensed but must be added to IPD bill to be charged at discharge.
          </div>
          <q-table
            :rows="inpatientPrescriptions"
            :columns="inpatientColumns"
            row-key="id"
            flat
            :loading="loadingInpatientPrescriptions"
          >
            <template v-slot:top>
              <div class="row items-center q-pa-sm">
                <q-checkbox
                  :model-value="allPendingSelectedInpatient"
                  :indeterminate="somePendingSelectedInpatient"
                  @update:model-value="toggleAllPendingInpatient"
                  label="Select all pending prescriptions"
                  class="q-mr-md"
                />
                <q-btn
                  v-if="selectedInpatientPrescriptions.length > 0"
                  color="primary"
                  icon="add"
                  label="Add Selected to Confirmation"
                  @click="addSelectedToConfirmationInpatient"
                  class="q-mr-sm"
                />
              </div>
            </template>
            <template v-slot:body-cell-prescriber="props">
              <q-td :props="props">
                <div v-if="props.row.prescriber_name">
                  <div class="text-weight-medium">{{ props.row.prescriber_name }}</div>
                </div>
                <span v-else class="text-grey-6">N/A</span>
              </q-td>
            </template>
            <template v-slot:body-cell-medicine_name="props">
              <q-td :props="props">
                <div class="row items-center q-gutter-xs">
                  <span>{{ props.value }}</span>
                  <q-badge color="purple" label="IPD" />
                </div>
              </q-td>
            </template>
            <template v-slot:body-cell-status="props">
              <q-td :props="props">
                <q-badge
                  v-if="props.row.is_confirmed && props.row.is_dispensed"
                  color="positive"
                  label="Dispensed"
                />
                <q-badge
                  v-else-if="props.row.is_confirmed"
                  color="blue"
                  label="Confirmed"
                />
                <q-badge
                  v-else
                  color="orange"
                  label="Pending"
                />
              </q-td>
            </template>
            <template v-slot:body-cell-selection="props">
              <q-td :props="props">
                <q-checkbox
                  v-if="!props.row.is_confirmed && !props.row.is_dispensed"
                  :model-value="isInpatientPrescriptionSelected(props.row)"
                  @update:model-value="toggleInpatientPrescriptionSelection(props.row, $event)"
                />
              </q-td>
            </template>
            <template v-slot:body-cell-price="props">
              <q-td :props="props">
                <span v-if="props.row.calculated_price !== undefined" class="text-weight-medium text-primary">
                  {{ formatCurrency(props.row.calculated_price) }}
                </span>
                <span v-else class="text-grey-6 text-caption">Calculating...</span>
              </q-td>
            </template>
            <template v-slot:body-cell-actions="props">
              <q-td :props="props">
                <div class="row q-gutter-xs">
                  <q-btn
                    v-if="props.row.instructions"
                    size="sm"
                    color="info"
                    icon="visibility"
                    flat
                    round
                    @click="viewInstructions(props.row)"
                    title="View Instructions"
                  />
                  <q-btn
                    v-if="!props.row.is_confirmed && !props.row.is_dispensed"
                    size="sm"
                    color="primary"
                    icon="check_circle"
                    label="Confirm"
                    @click="confirmPrescription(props.row)"
                    :loading="confirmingInpatient === props.row.id"
                    :disable="confirmingInpatient !== null || dispensingInpatient !== null || unconfirmingInpatient !== null"
                  />
                  <q-btn
                    v-if="props.row.is_confirmed && !props.row.is_dispensed"
                    size="sm"
                    color="warning"
                    icon="undo"
                    label="Revert"
                    @click="unconfirmPrescription(props.row)"
                    :loading="unconfirmingInpatient === props.row.id"
                    :disable="confirmingInpatient !== null || dispensingInpatient !== null || unconfirmingInpatient !== null"
                  >
                    <q-tooltip>Revert confirmation (set back to pending)</q-tooltip>
                  </q-btn>
                  <q-btn
                    v-if="!props.row.is_dispensed && props.row.is_confirmed"
                    size="sm"
                    color="positive"
                    label="Dispense"
                    @click="dispensePrescription(props.row)"
                    :loading="dispensingInpatient === props.row.id"
                    :disable="dispensingInpatient !== null || confirmingInpatient !== null || unconfirmingInpatient !== null"
                  >
                    <q-tooltip>Dispense prescription</q-tooltip>
                  </q-btn>
                  <q-btn
                    v-if="props.row.is_dispensed"
                    size="sm"
                    color="negative"
                    icon="undo"
                    label="Return"
                    @click="returnPrescription(props.row)"
                    :loading="returningId === props.row.id"
                    :disable="dispensingInpatient !== null || returningId !== null"
                  >
                    <q-tooltip>Return dispensed prescription</q-tooltip>
                  </q-btn>
                </div>
              </q-td>
            </template>
          </q-table>
        </div>

        <!-- Empty State -->
        <div v-if="serviceType && ((serviceType === 'opd' && prescriptions.length === 0) || (serviceType === 'ipd' && inpatientPrescriptions.length === 0))" class="text-center q-pa-lg">
          <q-icon name="medication" size="4em" color="grey-6" />
          <div class="text-h6 q-mt-md text-grey-6">No prescriptions found</div>
          <div class="text-body2 text-grey-6">
            <span v-if="serviceType === 'opd'">Prescriptions will appear here once they are added for this encounter.</span>
            <span v-else>Prescriptions will appear here once they are added in a clinical review.</span>
          </div>
        </div>
      </q-card-section>
    </q-card>

    <!-- Itemized Confirmation Section -->
    <q-card v-if="itemizedPrescriptions.length > 0" class="q-mt-md glass-card">
      <q-card-section>
        <div class="text-h6 q-mb-md glass-text">Selected Prescriptions for Confirmation</div>
        <div class="q-gutter-md">
          <q-card
            v-for="prescription in itemizedPrescriptions"
            :key="prescription.id"
            flat
            bordered
            class="q-pa-md"
          >
            <div class="row q-gutter-md items-start">
              <!-- Drug Name Section - Left Side -->
              <div class="col-12 col-md-3">
                <div class="text-subtitle2 q-mb-xs text-grey-7">Drug Name</div>
                <div class="text-weight-bold" style="word-break: break-word; line-height: 1.4;">
                  {{ prescription.medicine_name }}
                </div>
                <div class="text-caption text-grey-6 q-mt-xs">{{ prescription.medicine_code }}</div>
              </div>
              
              <!-- Dose and Unit - Side by Side -->
              <div class="col-12 col-md-2">
                <div class="text-subtitle2 q-mb-xs text-grey-7">Dose</div>
                <q-input
                  v-model.number="prescription.editableDose"
                  type="number"
                  filled
                  dense
                  @update:model-value="calculateItemizedQuantity(prescription)"
                  hint="e.g., 500"
                />
              </div>
              
              <div class="col-12 col-md-2">
                <div class="text-subtitle2 q-mb-xs text-grey-7">Unit</div>
                <q-select
                  v-model="prescription.editableUnit"
                  :options="unitOptions"
                  filled
                  dense
                  use-input
                  input-debounce="0"
                  @new-value="createUnit"
                  @update:model-value="calculateItemizedQuantity(prescription)"
                />
              </div>
              
              <!-- Frequency -->
              <div class="col-12 col-md-2">
                <div class="text-subtitle2 q-mb-xs text-grey-7">Frequency</div>
                <q-select
                  v-model="prescription.editableFrequency"
                  :options="frequencyOptions"
                  filled
                  dense
                  @update:model-value="calculateItemizedQuantity(prescription)"
                />
              </div>
              
              <!-- Duration -->
              <div class="col-12 col-md-2">
                <div class="text-subtitle2 q-mb-xs text-grey-7">Duration</div>
                <q-input
                  v-model="prescription.editableDuration"
                  filled
                  dense
                  @update:model-value="calculateItemizedQuantity(prescription)"
                  hint="e.g., 7 DAYS"
                />
              </div>
              
              <!-- Quantity -->
              <div class="col-12 col-md-1">
                <div class="text-subtitle2 q-mb-xs text-grey-7">Quantity</div>
                <q-input
                  v-model.number="prescription.editableQuantity"
                  type="number"
                  filled
                  dense
                  hint="Auto-calc"
                  class="text-center"
                />
              </div>
              
              <!-- Remove Button -->
              <div class="col-12 col-md-auto">
                <q-btn
                  size="sm"
                  color="negative"
                  icon="delete"
                  flat
                  round
                  @click="removeFromItemized(prescription.id)"
                  class="q-mt-md"
                />
              </div>
            </div>
            <!-- Instructions Section -->
            <div class="row q-mt-md">
              <div class="col-12">
                <div class="text-subtitle2 q-mb-xs text-grey-7">Instructions / Remarks</div>
                <q-input
                  v-model="prescription.editableInstructions"
                  filled
                  type="textarea"
                  rows="2"
                  placeholder="Add instructions for taking this medication"
                />
              </div>
            </div>
          </q-card>
        </div>
        <div class="row q-mt-md justify-end">
          <q-btn
            color="primary"
            icon="check_circle"
            label="Confirm and Generate Bill"
            @click="confirmMultiplePrescriptions"
            :loading="confirmingMultiple"
            :disable="itemizedPrescriptions.length === 0"
            size="md"
          />
        </div>
      </q-card-section>
    </q-card>

    <!-- No Prescriptions Message -->
    <q-card v-if="patient && !loadingPrescriptions && !loadingInpatientPrescriptions && prescriptions.length === 0 && inpatientPrescriptions.length === 0" class="q-mt-md">
      <q-card-section class="text-center text-grey-7">
        <div v-if="selectedEncounterId">No prescriptions found for this encounter</div>
        <div v-else>No prescriptions found for this patient</div>
      </q-card-section>
    </q-card>

    <!-- Add External Prescription Dialog -->
    <q-dialog v-model="showAddExternalPrescriptionDialog">
      <q-card style="min-width: 600px; max-width: 800px">
        <q-card-section>
          <div class="text-h6">Add External Prescription</div>
          <div class="text-caption text-info q-mt-xs">
            External prescriptions are filled outside the hospital and will not be billed.
          </div>
        </q-card-section>
        <q-card-section>
          <q-form @submit="addExternalPrescription" class="q-gutter-md">
            <q-select
              v-model="selectedMedication"
              filled
              use-input
              input-debounce="300"
              label="Search Medication (from Pharmacy)"
              :options="medicationOptions"
              @filter="filterMedications"
              @update:model-value="onMedicationSelected"
              option-value="item_code"
              option-label="item_name"
              emit-value
              map-options
              hint="Start typing to search for medications"
              :rules="[(val) => !!val || 'Please select a medication']"
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
                    No medications found. Try a different search term.
                  </q-item-section>
                </q-item>
              </template>
            </q-select>
            <q-input
              v-model="externalPrescriptionForm.medicine_code"
              filled
              label="Medicine Code"
              readonly
              hint="Automatically populated"
            />
            <q-input
              v-model="externalPrescriptionForm.medicine_name"
              filled
              label="Medicine Name"
              readonly
              hint="Automatically populated"
            />
            <q-input
              v-model="externalPrescriptionForm.dose"
              filled
              label="Dose *"
              hint="e.g., 500 MG"
              :rules="[(val) => !!val || 'Dose is required']"
            />
            <q-input
              v-model="externalPrescriptionForm.frequency"
              filled
              label="Frequency *"
              hint="e.g., 2 DAILY"
              :rules="[(val) => !!val || 'Frequency is required']"
            />
            <q-input
              v-model="externalPrescriptionForm.duration"
              filled
              label="Duration *"
              hint="e.g., 7 DAYS"
              :rules="[(val) => !!val || 'Duration is required']"
            />
            <q-input
              v-model.number="externalPrescriptionForm.quantity"
              filled
              type="number"
              label="Quantity *"
              hint="Number of units"
              :rules="[
                (val) => !!val || 'Quantity is required',
                (val) => val > 0 || 'Quantity must be greater than 0'
              ]"
            />
            <q-input
              v-model="externalPrescriptionForm.instructions"
              filled
              type="textarea"
              label="Instructions (Optional)"
              hint="Special instructions for the patient"
              rows="3"
            />
            <div class="row q-gutter-md q-mt-md">
              <q-btn label="Cancel" flat v-close-popup class="col" />
              <q-btn label="Add External Prescription" type="submit" color="secondary" class="col" :loading="addingPrescription" />
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- Add Prescription Dialog -->
    <q-dialog v-model="showAddPrescriptionDialog">
      <q-card style="min-width: 600px; max-width: 800px">
        <q-card-section>
          <div class="text-h6">Add New Prescription</div>
        </q-card-section>
        <q-card-section>
          <q-form @submit="addPrescription" class="q-gutter-md">
            <q-select
              v-model="selectedMedication"
              filled
              use-input
              input-debounce="300"
              label="Search Medication (from Pharmacy)"
              :options="medicationOptions"
              @filter="filterMedications"
              @update:model-value="onMedicationSelected"
              option-value="item_code"
              option-label="item_name"
              emit-value
              map-options
              hint="Start typing to search for medications"
              :rules="[(val) => !!val || 'Please select a medication']"
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
                    No medications found. Try a different search term.
                  </q-item-section>
                </q-item>
              </template>
            </q-select>
            <q-input
              v-model="newPrescriptionForm.medicine_code"
              filled
              label="Medicine Code"
              readonly
              hint="Automatically populated"
            />
            <q-input
              v-model="newPrescriptionForm.medicine_name"
              filled
              label="Medicine Name"
              readonly
              hint="Automatically populated"
            />
            <q-input
              v-model="newPrescriptionForm.dose"
              filled
              label="Dose *"
              hint="e.g., 500 MG"
              :rules="[(val) => !!val || 'Dose is required']"
            />
            <q-input
              v-model="newPrescriptionForm.frequency"
              filled
              label="Frequency *"
              hint="e.g., 2 DAILY"
              :rules="[(val) => !!val || 'Frequency is required']"
            />
            <q-input
              v-model="newPrescriptionForm.duration"
              filled
              label="Duration *"
              hint="e.g., 7 DAYS"
              :rules="[(val) => !!val || 'Duration is required']"
            />
            <q-input
              v-model.number="newPrescriptionForm.quantity"
              filled
              type="number"
              label="Quantity *"
              hint="Number of units"
              :rules="[
                (val) => !!val || 'Quantity is required',
                (val) => val > 0 || 'Quantity must be greater than 0'
              ]"
            />
            <div class="row q-gutter-md q-mt-md">
              <q-btn label="Cancel" flat v-close-popup class="col" />
              <q-btn label="Add" type="submit" color="primary" class="col" :loading="addingPrescription" />
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- Confirm Prescription Dialog -->
    <q-dialog v-model="showConfirmDialog">
      <q-card style="min-width: 500px; max-width: 700px">
        <q-card-section>
          <div class="text-h6">Confirm Prescription</div>
          <div class="text-subtitle2 text-grey-7 q-mt-xs">
            {{ confirmForm.medicine_name }} ({{ confirmForm.medicine_code }})
          </div>
          <div class="text-caption text-warning q-mt-sm" v-if="!confirmForm.is_external">
            Review and update prescription details if needed, then confirm. This will generate a bill for the client.
          </div>
          <div class="text-caption text-info q-mt-sm" v-else>
            This prescription will be marked as external (to be filled outside). No bill will be generated.
          </div>
        </q-card-section>

        <q-card-section>
          <q-form @submit="confirmPrescriptionSubmit" class="q-gutter-md">
            <q-input
              v-model="confirmForm.dose"
              filled
              label="Dose *"
              hint="e.g., 500 MG"
              :rules="[(val) => !!val || 'Dose is required']"
            />
            <q-input
              v-model="confirmForm.frequency"
              filled
              label="Frequency *"
              hint="e.g., 2 DAILY"
              :rules="[(val) => !!val || 'Frequency is required']"
            />
            <q-input
              v-model="confirmForm.duration"
              filled
              label="Duration *"
              hint="e.g., 7 DAYS"
              :rules="[(val) => !!val || 'Duration is required']"
            />
            <q-input
              v-model.number="confirmForm.quantity"
              filled
              type="number"
              label="Quantity *"
              hint="Number of units"
              :rules="[
                (val) => !!val || 'Quantity is required',
                (val) => val > 0 || 'Quantity must be greater than 0'
              ]"
            />
            <q-input
              v-model="confirmForm.instructions"
              filled
              type="textarea"
              label="Instructions / Remarks"
              rows="3"
              hint="Instructions for taking this medication"
            />
            <q-checkbox
              v-model="confirmForm.is_external"
              label="Mark as External (Drug not in stock - to be filled outside)"
              color="orange"
              class="q-mt-md"
            />
            <div class="text-caption text-grey-7 q-ml-md" v-if="confirmForm.is_external">
              External prescriptions are filled outside the hospital and will not be billed.
            </div>
            <div class="row q-gutter-md q-mt-md">
              <q-btn
                label="Cancel"
                flat
                v-close-popup
                class="col"
              />
              <q-btn
                :label="confirmForm.is_external ? 'Mark as External' : 'Confirm & Generate Bill'"
                type="submit"
                :color="confirmForm.is_external ? 'orange' : 'primary'"
                class="col"
                :loading="confirmingId !== null"
              />
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- Confirm Inpatient Prescription Dialog -->
    <q-dialog v-model="showConfirmInpatientDialog">
      <q-card style="min-width: 500px; max-width: 700px">
        <q-card-section>
          <div class="text-h6">Confirm Inpatient Prescription</div>
          <div class="text-subtitle2 text-grey-7 q-mt-xs">
            {{ confirmInpatientForm.medicine_name }} ({{ confirmInpatientForm.medicine_code }})
          </div>
          <div class="text-caption text-info q-mt-sm">
            Review and update prescription details if needed. IPD medications can be dispensed but must be added to IPD bill to be charged at discharge.
          </div>
        </q-card-section>

        <q-card-section>
          <q-form @submit="confirmInpatientPrescriptionSubmit" class="q-gutter-md">
            <q-input
              v-model="confirmInpatientForm.dose"
              filled
              label="Dose *"
              hint="e.g., 500 MG"
              :rules="[(val) => !!val || 'Dose is required']"
            />
            <q-input
              v-model="confirmInpatientForm.frequency"
              filled
              label="Frequency *"
              hint="e.g., 2 DAILY"
              :rules="[(val) => !!val || 'Frequency is required']"
            />
            <q-input
              v-model="confirmInpatientForm.duration"
              filled
              label="Duration *"
              hint="e.g., 7 DAYS"
              :rules="[(val) => !!val || 'Duration is required']"
            />
            <q-input
              v-model.number="confirmInpatientForm.quantity"
              filled
              type="number"
              label="Quantity *"
              hint="Number of units"
              :rules="[
                (val) => !!val || 'Quantity is required',
                (val) => val > 0 || 'Quantity must be greater than 0'
              ]"
            />
            <q-input
              v-model="confirmInpatientForm.instructions"
              filled
              type="textarea"
              label="Instructions / Remarks"
              rows="3"
              hint="Instructions for taking this medication"
            />
            <q-checkbox
              v-model="confirmInpatientForm.add_to_ipd_bill"
              label="Add to IPD Bill"
              color="purple"
              class="q-mt-md"
            />
            <div class="text-caption text-grey-7 q-ml-md" v-if="confirmInpatientForm.add_to_ipd_bill">
              This medication will be added to the patient's IPD bill and charged at discharge.
            </div>
            <div class="text-caption text-warning q-ml-md" v-else>
              This medication will be confirmed but NOT added to the IPD bill. It can still be dispensed.
            </div>
            <div class="row q-gutter-md q-mt-md">
              <q-btn
                label="Cancel"
                flat
                v-close-popup
                class="col"
              />
              <q-btn
                label="Confirm"
                type="submit"
                color="purple"
                class="col"
                :loading="confirmingInpatient !== null"
              />
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- Edit Prescription Dialog -->
    <q-dialog v-model="showEditPrescriptionDialog">
      <q-card style="min-width: 600px; max-width: 800px">
        <q-card-section>
          <div class="text-h6">Edit Prescription</div>
          <div class="text-subtitle2 text-grey-7 q-mt-xs">
            {{ editPrescriptionForm.medicine_name }} ({{ editPrescriptionForm.medicine_code }})
          </div>
          <div class="text-caption text-warning q-mt-sm">
            Admin: You can edit confirmed prescriptions. Changes will update the prescription and may affect billing.
          </div>
        </q-card-section>

        <q-card-section>
          <q-form @submit="updatePrescriptionSubmit" class="q-gutter-md">
            <q-input
              v-model="editPrescriptionForm.medicine_code"
              filled
              label="Medicine Code"
              readonly
              hint="Cannot be changed"
            />
            <q-input
              v-model="editPrescriptionForm.medicine_name"
              filled
              label="Medicine Name"
              readonly
              hint="Cannot be changed"
            />
            <div class="row q-gutter-md">
              <q-input
                v-model="editPrescriptionForm.dose"
                filled
                label="Dose *"
                hint="e.g., 500"
                class="col-12 col-md-6"
                :rules="[(val) => !!val || 'Dose is required']"
              />
              <q-select
                v-model="editPrescriptionForm.unit"
                filled
                :options="unitOptions"
                label="Unit"
                class="col-12 col-md-6"
                use-input
                @filter="filterUnits"
                @new-value="createUnit"
                hint="e.g., MG, TAB, ML"
              />
            </div>
            <q-select
              v-model="editPrescriptionForm.frequency"
              filled
              :options="frequencyOptions"
              label="Frequency *"
              hint="e.g., BDS, TDS, OD"
              :rules="[(val) => !!val || 'Frequency is required']"
            />
            <q-input
              v-model="editPrescriptionForm.duration"
              filled
              label="Duration *"
              hint="e.g., 7 DAYS"
              :rules="[(val) => !!val || 'Duration is required']"
            />
            <q-input
              v-model.number="editPrescriptionForm.quantity"
              filled
              type="number"
              label="Quantity *"
              hint="Number of units"
              :rules="[
                (val) => !!val || 'Quantity is required',
                (val) => val > 0 || 'Quantity must be greater than 0'
              ]"
            />
            <q-input
              v-model="editPrescriptionForm.instructions"
              filled
              type="textarea"
              label="Instructions (Optional)"
              hint="Special instructions for the patient"
              rows="3"
            />
            <div class="row q-gutter-md q-mt-md">
              <q-btn
                label="Cancel"
                flat
                v-close-popup
                class="col"
              />
              <q-btn
                label="Update Prescription"
                type="submit"
                color="primary"
                class="col"
                :loading="updatingPrescriptionId !== null"
              />
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- View Instructions Dialog -->
    <q-dialog v-model="showInstructionsDialog">
      <q-card style="min-width: 400px; max-width: 600px">
        <q-card-section>
          <div class="text-h6">Instructions / Remarks</div>
          <div class="text-subtitle2  q-mt-xs" v-if="viewingInstructions">
            {{ viewingInstructions?.medicine_name }} ({{ viewingInstructions?.medicine_code }})
          </div>
        </q-card-section>
        <q-card-section>
          <div v-if="viewingInstructions?.instructions" class="text-body1 q-pa-md" style="border-radius: 4px; white-space: pre-wrap;">
            {{ viewingInstructions.instructions }}
          </div>
          <div v-else class="text-grey-6 text-center q-pa-md">
            No instructions provided for this prescription
          </div>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn label="Close" color="primary" flat v-close-popup />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Dispense Dialog -->
    <q-dialog v-model="showDispenseDialog">
      <q-card style="min-width: 500px; max-width: 700px">
        <q-card-section>
          <div class="text-h6">Dispense Prescription</div>
          <div class="text-subtitle2 text-grey-7 q-mt-xs">
            {{ dispenseForm.medicine_name }} ({{ dispenseForm.medicine_code }})
          </div>
        </q-card-section>

        <q-card-section>
          <q-form @submit="confirmDispense" class="q-gutter-md">
            <q-input
              v-model="dispenseForm.dose"
              filled
              label="Dose *"
              hint="e.g., 500 MG"
              :rules="[(val) => !!val || 'Dose is required']"
            />
            <q-input
              v-model="dispenseForm.frequency"
              filled
              label="Frequency *"
              hint="e.g., 2 DAILY"
              :rules="[(val) => !!val || 'Frequency is required']"
            />
            <q-input
              v-model="dispenseForm.duration"
              filled
              label="Duration *"
              hint="e.g., 7 DAYS"
              :rules="[(val) => !!val || 'Duration is required']"
            />
            <q-input
              v-model.number="dispenseForm.quantity"
              filled
              type="number"
              label="Quantity *"
              hint="Number of units to dispense"
              :rules="[
                (val) => !!val || 'Quantity is required',
                (val) => val > 0 || 'Quantity must be greater than 0'
              ]"
            />
            <div class="row q-gutter-md q-mt-md">
              <q-btn
                label="Cancel"
                flat
                v-close-popup
                class="col"
              />
              <q-btn
                label="Dispense"
                type="submit"
                color="positive"
                class="col"
                :loading="dispensingId !== null"
              />
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue';
import { useRoute } from 'vue-router';
import { useQuasar } from 'quasar';
import { consultationAPI, patientsAPI, encountersAPI, vitalsAPI, priceListAPI, staffAPI, billingAPI } from '../services/api';
import { useAuthStore } from '../stores/auth';

const $q = useQuasar();
const route = useRoute();
const authStore = useAuthStore();
const cardNumber = ref('');
const loadingPatient = ref(false);
const patient = ref(null);
const activeEncounters = ref([]);
const todaysEncounter = ref(null);
const oldEncounters = ref([]);
const oldEncountersExpanded = ref(false);
const selectedEncounterId = ref(null);
const prescriptions = ref([]);
const currentEncounter = ref(null);
const loadingPrescriptions = ref(false);
const dispensingId = ref(null);
const returningId = ref(null);
const confirmingId = ref(null);
const unconfirmingId = ref(null);
const deletingId = ref(null);
const confirmingMultiple = ref(false);
const updatingPrescriptionId = ref(null);
// Inpatient prescriptions
const wardAdmissions = ref([]);
const selectedWardAdmissionId = ref(null);
const inpatientPrescriptions = ref([]);
const loadingInpatientPrescriptions = ref(false);
const confirmingInpatient = ref(null);
const dispensingInpatient = ref(null);
const unconfirmingInpatient = ref(null);
const combinedPrescriptions = ref([]);
const serviceType = ref(null); // 'opd' or 'ipd'
const showEditPrescriptionDialog = ref(false);
const editPrescriptionForm = ref({
  id: null,
  encounter_id: null,
  medicine_code: '',
  medicine_name: '',
  dose: '',
  unit: '',
  frequency: '',
  duration: '',
  quantity: 1,
  instructions: '',
});
const selectedPrescriptions = ref([]);
const selectedInpatientPrescriptions = ref([]);
const itemizedPrescriptions = ref([]);
const diagnoses = ref([]);
const vitals = ref(null);
const inpatientVitals = ref([]); // Array of vitals for IPD (can have multiple)
const latestInpatientVital = ref(null); // Most recent vital for display
const loadingData = ref(false);
const showDispenseDialog = ref(false);
const showConfirmDialog = ref(false);
const showAddPrescriptionDialog = ref(false);
const showAddExternalPrescriptionDialog = ref(false);
const showInstructionsDialog = ref(false);
const viewingInstructions = ref(null);
const addingPrescription = ref(false);
const dispenseForm = ref({
  id: null,
  medicine_name: '',
  medicine_code: '',
  dose: '',
  frequency: '',
  duration: '',
  quantity: 1,
});
const confirmForm = ref({
  id: null,
  medicine_name: '',
  medicine_code: '',
  dose: '',
  frequency: '',
  duration: '',
  quantity: 1,
  instructions: '',
  is_external: false,
});
const showConfirmInpatientDialog = ref(false);
const confirmInpatientForm = ref({
  id: null,
  medicine_name: '',
  medicine_code: '',
  dose: '',
  frequency: '',
  duration: '',
  quantity: 1,
  instructions: '',
  add_to_ipd_bill: true,
});
const bills = ref([]);
const newPrescriptionForm = ref({
  encounter_id: null,
  medicine_code: '',
  medicine_name: '',
  dose: '',
  frequency: '',
  duration: '',
  quantity: 1,
});
const externalPrescriptionForm = ref({
  encounter_id: null,
  medicine_code: '',
  medicine_name: '',
  dose: '',
  frequency: '',
  duration: '',
  quantity: 1,
  instructions: '',
});
const selectedMedication = ref(null);
const medicationOptions = ref([]);
const allMedications = ref([]);
const staffMap = ref({}); // Map of user_id -> user info for getting prescriber/dispenser names
const prescriptionTotalAmount = ref(0);
const loadingPrescriptionCosts = ref(false);
const prescriptionPrices = ref(new Map()); // Map of prescription_id -> price

// Frequency mapping for prescriptions (same as Consultation.vue)
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

// Check if prescription is selected
const isPrescriptionSelected = (prescription) => {
  return selectedPrescriptions.value.some(p => p.id === prescription.id);
};

// Toggle prescription selection
const togglePrescriptionSelection = (prescription, selected) => {
  // Prevent selecting external prescriptions for confirmation
  if (selected && prescription.is_external) {
    $q.notify({
      type: 'warning',
      message: 'External prescriptions cannot be selected for confirmation. They are automatically confirmed and not billed.',
    });
    return;
  }
  
  if (selected && !isPrescriptionSelected(prescription)) {
    selectedPrescriptions.value.push(prescription);
  } else if (!selected) {
    selectedPrescriptions.value = selectedPrescriptions.value.filter(p => p.id !== prescription.id);
    // Also remove from itemized if it's there
    itemizedPrescriptions.value = itemizedPrescriptions.value.filter(p => p.id !== prescription.id);
  }
};

// Get pending prescriptions
const pendingPrescriptions = computed(() => {
  // Exclude external prescriptions from pending (they're auto-confirmed)
  return prescriptions.value.filter(p => !p.is_confirmed && !p.is_external);
});

// Check if all pending are selected
const allPendingSelected = computed(() => {
  return pendingPrescriptions.value.length > 0 && 
         pendingPrescriptions.value.every(p => isPrescriptionSelected(p));
});

// Check if some pending are selected
const somePendingSelected = computed(() => {
  return !allPendingSelected.value && 
         pendingPrescriptions.value.some(p => isPrescriptionSelected(p));
});

// Toggle all pending prescriptions
const toggleAllPending = (selected) => {
  if (selected) {
    pendingPrescriptions.value.forEach(p => {
      if (!isPrescriptionSelected(p)) {
        selectedPrescriptions.value.push(p);
      }
    });
  } else {
    selectedPrescriptions.value = selectedPrescriptions.value.filter(
      p => pendingPrescriptions.value.every(pending => pending.id !== p.id)
    );
    itemizedPrescriptions.value = [];
  }
};

// View instructions for a prescription
const viewInstructions = (prescription) => {
  viewingInstructions.value = prescription;
  showInstructionsDialog.value = true;
};

// Add selected prescriptions to itemized confirmation
const addSelectedToConfirmation = () => {
  // Filter out external prescriptions and already confirmed ones
  const pending = selectedPrescriptions.value.filter(p => !p.is_confirmed && !p.is_external);
  if (pending.length === 0) {
    $q.notify({
      type: 'warning',
      message: 'Please select at least one pending prescription (external prescriptions cannot be confirmed)',
    });
    return;
  }
  
  pending.forEach(prescription => {
    // Double check: skip external prescriptions
    if (prescription.is_external) {
      return;
    }
    
    // Check if already in itemized
    if (!itemizedPrescriptions.value.some(item => item.id === prescription.id)) {
      const newItem = {
        ...prescription,
        editableDose: parseFloat(prescription.dose) || 0,
        editableUnit: prescription.unit || 'TAB',
        editableFrequency: prescription.frequency || 'OD',
        editableDuration: prescription.duration || '1 DAY',
        editableQuantity: prescription.quantity || 1,
        editableInstructions: prescription.instructions || '',
      };
      itemizedPrescriptions.value.push(newItem);
      // Calculate quantity for this prescription after adding
      setTimeout(() => {
        calculateItemizedQuantity(newItem);
      }, 0);
    }
  });
};

// IPD Prescription Selection Functions
const isInpatientPrescriptionSelected = (prescription) => {
  return selectedInpatientPrescriptions.value.some(p => p.id === prescription.id);
};

const toggleInpatientPrescriptionSelection = (prescription, selected) => {
  if (selected && !isInpatientPrescriptionSelected(prescription)) {
    selectedInpatientPrescriptions.value.push(prescription);
  } else if (!selected) {
    selectedInpatientPrescriptions.value = selectedInpatientPrescriptions.value.filter(p => p.id !== prescription.id);
    itemizedPrescriptions.value = itemizedPrescriptions.value.filter(p => p.id !== prescription.id);
  }
};

const pendingInpatientPrescriptions = computed(() => {
  return inpatientPrescriptions.value.filter(p => !p.is_confirmed && !p.is_dispensed);
});

const allPendingSelectedInpatient = computed(() => {
  return pendingInpatientPrescriptions.value.length > 0 && 
         pendingInpatientPrescriptions.value.every(p => isInpatientPrescriptionSelected(p));
});

const somePendingSelectedInpatient = computed(() => {
  return !allPendingSelectedInpatient.value && 
         pendingInpatientPrescriptions.value.some(p => isInpatientPrescriptionSelected(p));
});

const toggleAllPendingInpatient = (selected) => {
  if (selected) {
    pendingInpatientPrescriptions.value.forEach(p => {
      if (!isInpatientPrescriptionSelected(p)) {
        selectedInpatientPrescriptions.value.push(p);
      }
    });
  } else {
    selectedInpatientPrescriptions.value = selectedInpatientPrescriptions.value.filter(
      p => pendingInpatientPrescriptions.value.every(pending => pending.id !== p.id)
    );
    itemizedPrescriptions.value = [];
  }
};

const addSelectedToConfirmationInpatient = () => {
  const pending = selectedInpatientPrescriptions.value.filter(p => !p.is_confirmed && !p.is_dispensed);
  if (pending.length === 0) {
    $q.notify({
      type: 'warning',
      message: 'Please select at least one pending prescription',
    });
    return;
  }
  
  pending.forEach(prescription => {
    if (!itemizedPrescriptions.value.some(item => item.id === prescription.id)) {
      const newItem = {
        ...prescription,
        editableDose: parseFloat(prescription.dose) || 0,
        editableUnit: prescription.unit || 'TAB',
        editableFrequency: prescription.frequency || 'OD',
        editableDuration: prescription.duration || '1 DAY',
        editableQuantity: prescription.quantity || 1,
        editableInstructions: prescription.instructions || '',
      };
      itemizedPrescriptions.value.push(newItem);
      setTimeout(() => {
        calculateItemizedQuantity(newItem);
      }, 0);
    }
  });
  
  $q.notify({
    type: 'positive',
    message: `Added ${pending.length} prescription(s) to confirmation list`,
  });
};

// Remove from itemized
const removeFromItemized = (prescriptionId) => {
  itemizedPrescriptions.value = itemizedPrescriptions.value.filter(p => p.id !== prescriptionId);
  selectedPrescriptions.value = selectedPrescriptions.value.filter(p => p.id !== prescriptionId);
};

// Calculate quantity for itemized prescription (same logic as Consultation.vue)
const calculateItemizedQuantity = (prescription) => {
  if (!prescription || !prescription.editableDose || !prescription.editableFrequency || !prescription.editableDuration) {
    return;
  }
  
  try {
    const doseNum = parseFloat(prescription.editableDose);
    const frequencyValue = frequencyMapping[prescription.editableFrequency];
    
    if (doseNum && frequencyValue && doseNum > 0) {
      // Extract duration number (e.g., "7 DAYS" -> 7, "2" -> 2)
      const durationStr = prescription.editableDuration.trim();
      let durationNum = 1;
      if (durationStr) {
        const directNum = parseFloat(durationStr);
        if (!isNaN(directNum) && directNum > 0) {
          durationNum = Math.floor(directNum);
        } else {
          const durationMatch = durationStr.match(/\d+/);
          if (durationMatch) {
            durationNum = parseInt(durationMatch[0]);
          }
        }
      }
      
      // Convert dose to units based on unit type
      let unitsPerDose = doseNum;
      if (prescription.editableUnit && prescription.editableUnit.toUpperCase() === 'MG') {
        // For MG: 100mg = 1 unit
        unitsPerDose = doseNum / 100;
      } else if (prescription.editableUnit && prescription.editableUnit.toUpperCase() === 'MCG') {
        // For MCG: 1000mcg = 1 unit
        unitsPerDose = doseNum / 1000;
      }
      // For other units (TAB, CAP, ML, etc.), use dose as-is (1 tablet = 1 unit)
      
      // Calculate: units per dose × frequency per day × number of days
      const calculatedQuantity = Math.floor(unitsPerDose * frequencyValue * durationNum);
      if (calculatedQuantity > 0) {
        prescription.editableQuantity = calculatedQuantity;
      }
    }
  } catch (error) {
    console.error('Error calculating quantity:', error);
  }
};

// Confirm multiple prescriptions and generate bills
const confirmMultiplePrescriptions = async () => {
  if (itemizedPrescriptions.value.length === 0) {
    $q.notify({
      type: 'warning',
      message: 'Please select at least one prescription to confirm',
    });
    return;
  }
  
  // Filter out external prescriptions
  const nonExternalPrescriptions = itemizedPrescriptions.value.filter(p => !p.is_external);
  
  if (nonExternalPrescriptions.length === 0) {
    $q.notify({
      type: 'warning',
      message: 'External prescriptions cannot be confirmed. They are automatically confirmed and not billed.',
    });
    return;
  }
  
  confirmingMultiple.value = true;
  let confirmedCount = 0;
  let failedCount = 0;
  const errors = [];
  
  try {
    // Separate OPD and IPD prescriptions
    const opdPrescriptions = nonExternalPrescriptions.filter(p => 
      p.prescription_type !== 'inpatient' && p.source !== 'inpatient'
    );
    const ipdPrescriptions = nonExternalPrescriptions.filter(p => 
      p.prescription_type === 'inpatient' || p.source === 'inpatient'
    );
    
    // Confirm OPD prescriptions
    for (const prescription of opdPrescriptions) {
      try {
        const confirmData = {
          dose: prescription.editableDose ? String(prescription.editableDose) : null,
          frequency: prescription.editableFrequency || null,
          duration: prescription.editableDuration || null,
          quantity: prescription.editableQuantity || null,
          instructions: prescription.editableInstructions || null,
        };
        
        await consultationAPI.confirmPrescription(prescription.id, confirmData);
        confirmedCount++;
      } catch (error) {
        console.error(`Failed to confirm OPD prescription ${prescription.id}:`, error);
        failedCount++;
        errors.push(`${prescription.medicine_name}: ${error.response?.data?.detail || error.message}`);
      }
    }
    
    // Confirm IPD prescriptions
    for (const prescription of ipdPrescriptions) {
      try {
        const confirmData = {
          dose: prescription.editableDose ? String(prescription.editableDose) : null,
          frequency: prescription.editableFrequency || null,
          duration: prescription.editableDuration || null,
          quantity: prescription.editableQuantity || null,
          instructions: prescription.editableInstructions || null,
          add_to_ipd_bill: true, // Default to adding to IPD bill
        };
        
        await consultationAPI.confirmInpatientPrescription(prescription.id, confirmData);
        confirmedCount++;
      } catch (error) {
        console.error(`Failed to confirm IPD prescription ${prescription.id}:`, error);
        failedCount++;
        errors.push(`${prescription.medicine_name}: ${error.response?.data?.detail || error.message}`);
      }
    }
    
    // Show notification based on results
    if (confirmedCount > 0 && failedCount === 0) {
      $q.notify({
        type: 'positive',
        message: `Successfully confirmed ${confirmedCount} prescription(s) and generated bills`,
      });
    } else if (confirmedCount > 0 && failedCount > 0) {
      $q.notify({
        type: 'warning',
        message: `Confirmed ${confirmedCount} prescription(s), but ${failedCount} failed. ${errors.join('; ')}`,
        timeout: 8000,
      });
    } else {
      $q.notify({
        type: 'negative',
        message: `Failed to confirm prescriptions. ${errors.join('; ')}`,
        timeout: 8000,
      });
    }
    
    // Clear selections
    selectedPrescriptions.value = [];
    selectedInpatientPrescriptions.value = [];
    itemizedPrescriptions.value = [];
    
    // Reload prescriptions based on current service type
    if (serviceType.value === 'ipd') {
      await loadInpatientPrescriptions();
    } else {
      await loadPrescriptions();
    }
  } catch (error) {
    console.error('Failed to confirm prescriptions:', error);
    const errorMessage = error.response?.data?.detail || error.message || 'Failed to confirm prescriptions';
    $q.notify({
      type: 'negative',
      message: typeof errorMessage === 'string' ? errorMessage : JSON.stringify(errorMessage),
      timeout: 5000,
    });
  } finally {
    confirmingMultiple.value = false;
  }
};

// Load all pharmacy medications
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

// Initialize medicationOptions when dialog opens
const openAddPrescriptionDialog = async () => {
  if (serviceType.value === 'ipd') {
    // For IPD, need ward admission
    if (!selectedWardAdmissionId.value) {
      $q.notify({
        type: 'warning',
        message: 'Please select an IPD admission first',
      });
      return;
    }
    
    // For IPD, we need a clinical review to add prescriptions
    // Get the latest clinical review for this ward admission
    try {
      const reviewsResponse = await consultationAPI.getInpatientClinicalReviews(selectedWardAdmissionId.value);
      const reviews = reviewsResponse.data || [];
      
      if (reviews.length === 0) {
        $q.notify({
          type: 'warning',
          message: 'No clinical review found for this admission. Please create a clinical review first.',
          timeout: 5000,
        });
        return;
      }
      
      // Use the most recent clinical review
      const latestReview = reviews[0]; // Already sorted by reviewed_at desc
      
      // Load medications if not already loaded
      if (allMedications.value.length === 0) {
        await loadPharmacyMedications();
      } else {
        medicationOptions.value = allMedications.value;
      }
      
      selectedMedication.value = null;
      newPrescriptionForm.value = {
        ward_admission_id: selectedWardAdmissionId.value,
        clinical_review_id: latestReview.id,
        medicine_code: '',
        medicine_name: '',
        dose: '',
        frequency: '',
        duration: '',
        quantity: 1,
      };
      showAddPrescriptionDialog.value = true;
    } catch (error) {
      console.error('Error loading clinical reviews:', error);
      $q.notify({
        type: 'negative',
        message: error.response?.data?.detail || 'Failed to load clinical reviews',
      });
    }
  } else {
    // For OPD, need encounter
    if (!selectedEncounterId.value) {
      $q.notify({
        type: 'warning',
        message: 'Please select an encounter first',
      });
      return;
    }
    
    // Load medications if not already loaded
    if (allMedications.value.length === 0) {
      await loadPharmacyMedications();
    } else {
      medicationOptions.value = allMedications.value;
    }
    
    selectedMedication.value = null;
    newPrescriptionForm.value = {
      encounter_id: selectedEncounterId.value,
      medicine_code: '',
      medicine_name: '',
      dose: '',
      frequency: '',
      duration: '',
      quantity: 1,
    };
    showAddPrescriptionDialog.value = true;
  }
};

const openAddExternalPrescriptionDialog = async () => {
  if (serviceType.value === 'ipd') {
    // For IPD, external prescriptions are not typically used, but we'll allow it
    if (!selectedWardAdmissionId.value) {
      $q.notify({
        type: 'warning',
        message: 'Please select an IPD admission first',
      });
      return;
    }
    
    // Get the latest clinical review
    try {
      const reviewsResponse = await consultationAPI.getInpatientClinicalReviews(selectedWardAdmissionId.value);
      const reviews = reviewsResponse.data || [];
      
      if (reviews.length === 0) {
        $q.notify({
          type: 'warning',
          message: 'No clinical review found for this admission. Please create a clinical review first.',
          timeout: 5000,
        });
        return;
      }
      
      const latestReview = reviews[0];
      
      // Load medications if not already loaded
      if (allMedications.value.length === 0) {
        await loadPharmacyMedications();
      } else {
        medicationOptions.value = allMedications.value;
      }
      
      selectedMedication.value = null;
      externalPrescriptionForm.value = {
        ward_admission_id: selectedWardAdmissionId.value,
        clinical_review_id: latestReview.id,
        medicine_code: '',
        medicine_name: '',
        dose: '',
        frequency: '',
        duration: '',
        quantity: 1,
        instructions: '',
      };
      showAddExternalPrescriptionDialog.value = true;
    } catch (error) {
      console.error('Error loading clinical reviews:', error);
      $q.notify({
        type: 'negative',
        message: error.response?.data?.detail || 'Failed to load clinical reviews',
      });
    }
  } else {
    // For OPD
    if (!selectedEncounterId.value) {
      $q.notify({
        type: 'warning',
        message: 'Please select an encounter first',
      });
      return;
    }
    
    // Load medications if not already loaded
    if (allMedications.value.length === 0) {
      await loadPharmacyMedications();
    } else {
      medicationOptions.value = allMedications.value;
    }
    
    selectedMedication.value = null;
    externalPrescriptionForm.value = {
      encounter_id: selectedEncounterId.value,
      medicine_code: '',
      medicine_name: '',
      dose: '',
      frequency: '',
      duration: '',
      quantity: 1,
      instructions: '',
    };
    showAddExternalPrescriptionDialog.value = true;
  }
};

// Computed property to get external prescriptions
const externalPrescriptions = computed(() => {
  return prescriptions.value.filter(p => p.is_external === true);
});

const columns = [
  { name: 'selection', label: '', field: 'selection', align: 'left', style: 'width: 50px' },
  { name: 'medicine_name', label: 'Medicine', field: 'medicine_name', align: 'left' },
  { name: 'medicine_code', label: 'Code', field: 'medicine_code', align: 'left' },
  { name: 'dose', label: 'Dose', field: 'dose', align: 'left' },
  { name: 'frequency', label: 'Frequency', field: 'frequency', align: 'left' },
  { name: 'duration', label: 'Duration', field: 'duration', align: 'left' },
  { name: 'quantity', label: 'Quantity', field: 'quantity', align: 'right' },
  { name: 'amount', label: 'Amount', field: 'amount', align: 'right' },
  { name: 'prescriber', label: 'Prescriber', field: 'prescriber_name', align: 'left' },
  { name: 'status', label: 'Status', field: 'is_confirmed', align: 'center' },
  { name: 'actions', label: 'Actions', align: 'center' },
];

const itemizedColumns = [
  { name: 'drug_name', label: 'Drug Name', field: 'medicine_name', align: 'left' },
  { name: 'dose', label: 'Dose', field: 'editableDose', align: 'left' },
  { name: 'unit', label: 'Unit', field: 'editableUnit', align: 'left' },
  { name: 'frequency', label: 'Frequency', field: 'editableFrequency', align: 'left' },
  { name: 'duration', label: 'Duration', field: 'editableDuration', align: 'left' },
  { name: 'quantity', label: 'Quantity', field: 'editableQuantity', align: 'right' },
  { name: 'actions', label: '', field: 'actions', align: 'center' },
];

const inpatientColumns = [
  { name: 'selection', label: '', field: 'selection', align: 'left', style: 'width: 50px' },
  { name: 'medicine_name', label: 'Medicine', field: 'medicine_name', align: 'left' },
  { name: 'medicine_code', label: 'Code', field: 'medicine_code', align: 'left' },
  { name: 'dose', label: 'Dose', field: 'dose', align: 'left' },
  { name: 'frequency', label: 'Frequency', field: 'frequency', align: 'left' },
  { name: 'duration', label: 'Duration', field: 'duration', align: 'left' },
  { name: 'quantity', label: 'Quantity', field: 'quantity', align: 'right' },
  { name: 'price', label: 'Amount', field: 'calculated_price', align: 'right' },
  { name: 'prescriber', label: 'Prescriber', field: 'prescriber_name', align: 'left' },
  { name: 'status', label: 'Status', field: 'is_confirmed', align: 'center' },
  { name: 'actions', label: 'Actions', align: 'center' },
];

const searchPatient = async () => {
  if (!cardNumber.value || !cardNumber.value.trim()) {
    $q.notify({
      type: 'warning',
      message: 'Please enter a card number',
    });
    return;
  }

  loadingPatient.value = true;
  try {
    // Get patient by card number (returns list)
    const patientResponse = await patientsAPI.getByCard(cardNumber.value.trim());
    
    // getByCard returns a list of patients
    let patients = [];
    if (Array.isArray(patientResponse.data)) {
      patients = patientResponse.data;
    } else if (patientResponse.data && typeof patientResponse.data === 'object' && !Array.isArray(patientResponse.data)) {
      patients = [patientResponse.data];
    }
    
    if (patients.length === 0) {
      $q.notify({
        type: 'info',
        message: 'No patients found with that card number',
      });
      return;
    }
    
    // Use the first patient (or exact match if available)
    patient.value = patients[0];

    // Load ward admissions for this patient
    await loadWardAdmissions();

    // Get patient's active encounters
    const encountersResponse = await encountersAPI.getPatientEncounters(patient.value.id);
    const allEncounters = encountersResponse.data.filter(e => !e.archived);
    
    // Separate today's encounter from old encounters
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    
    const todaysEncounters = allEncounters.filter(e => {
      const encounterDate = new Date(e.created_at);
      encounterDate.setHours(0, 0, 0, 0);
      return encounterDate.getTime() === today.getTime();
    });
    
    const oldEncs = allEncounters.filter(e => {
      const encounterDate = new Date(e.created_at);
      encounterDate.setHours(0, 0, 0, 0);
      return encounterDate.getTime() !== today.getTime();
    }).sort((a, b) => new Date(b.created_at) - new Date(a.created_at)); // Sort newest first
    
    // Set today's encounter (use the most recent one if multiple)
    if (todaysEncounters.length > 0) {
      todaysEncounter.value = todaysEncounters.sort((a, b) => new Date(b.created_at) - new Date(a.created_at))[0];
      // Don't auto-select - let user choose
      // Pre-fetch procedure names for today's encounter
      getEncounterProcedures(todaysEncounter.value);
    } else {
      todaysEncounter.value = null;
    }
    
    // Set old encounters and pre-fetch their procedure names
    oldEncounters.value = oldEncs;
    oldEncounters.value.forEach(encounter => {
      getEncounterProcedures(encounter);
    });
    
    // Keep for backward compatibility
    activeEncounters.value = allEncounters.map(e => ({
        id: e.id,
        label: `Encounter #${e.id} - ${e.department} (${new Date(e.created_at).toLocaleDateString()})`,
        value: e.id,
      }));

    if (allEncounters.length === 0) {
      $q.notify({
        type: 'info',
        message: 'No active encounters found for this patient',
      });
    }
  } catch (error) {
    patient.value = null;
    activeEncounters.value = [];
    todaysEncounter.value = null;
    oldEncounters.value = [];
    selectedEncounterId.value = null;
    prescriptions.value = [];
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Patient not found',
    });
  } finally {
    loadingPatient.value = false;
  }
};

const loadPrescriptions = async () => {
  if (!selectedEncounterId.value || !patient.value) {
    prescriptions.value = [];
    return;
  }

  loadingPrescriptions.value = true;
  loadingData.value = true;
  try {
    // Load OPD prescriptions only
    const prescriptionsResponse = await consultationAPI.getPrescriptionsByPatientCard(
      patient.value.card_number,
      selectedEncounterId.value
    );
    prescriptions.value = prescriptionsResponse.data || [];

    // Load encounter details (to get CCC and other fields)
    try {
      const encResp = await encountersAPI.get(selectedEncounterId.value);
      currentEncounter.value = encResp.data || null;
    } catch (e) {
      currentEncounter.value = null;
    }

    // Load diagnoses
    try {
      const diagnosesResponse = await consultationAPI.getDiagnoses(selectedEncounterId.value);
      diagnoses.value = diagnosesResponse.data || [];
    } catch (error) {
      console.error('Failed to load diagnoses:', error);
      diagnoses.value = [];
    }

    // Load vitals
    try {
      const vitalsResponse = await vitalsAPI.getByEncounter(selectedEncounterId.value);
      vitals.value = vitalsResponse.data || null;
    } catch (error) {
      console.error('Failed to load vitals:', error);
      vitals.value = null;
    }

    // Load bills for this encounter to check payment status
    try {
      const billsResponse = await billingAPI.getEncounterBills(selectedEncounterId.value);
      const billsList = billsResponse.data || [];
      
      // Load detailed bill information including bill items and payment status
      const detailedBills = await Promise.all(
        billsList.map(async (bill) => {
          try {
            const billDetailsResponse = await billingAPI.getBillDetails(bill.id);
            console.log(`Bill details response for bill ${bill.id}:`, billDetailsResponse);
            const billDetails = billDetailsResponse.data?.data || billDetailsResponse.data || {};
            console.log(`Bill details for bill ${bill.id}:`, billDetails);
            console.log(`Bill items from API for bill ${bill.id}:`, billDetails.bill_items);
            
            // Calculate remaining balance for each bill item
            // The API already returns amount_paid and remaining_balance, but we ensure they're set
            const billItems = (billDetails.bill_items || []).map(item => {
              try {
                // The API returns amount_paid and remaining_balance already calculated
                const amountPaid = (item.amount_paid !== undefined && item.amount_paid !== null) ? item.amount_paid : 0;
                const totalPrice = (item.total_price !== undefined && item.total_price !== null) ? item.total_price : 0;
                // Use the API's calculated remaining_balance if available, otherwise calculate it
                const remainingBalance = (item.remaining_balance !== undefined && item.remaining_balance !== null)
                  ? item.remaining_balance 
                  : (totalPrice - amountPaid);
                
                console.log(`Bill item mapping: ${item.item_name || 'Unknown'}`, {
                  item_code: item.item_code,
                  totalPrice,
                  amountPaid,
                  remainingBalance,
                  api_remaining_balance: item.remaining_balance,
                  api_amount_paid: item.amount_paid,
                });
                
                // Item is paid if remaining balance is 0 or less (allow small rounding differences)
                const isPaid = remainingBalance <= 0.01; // Allow 0.01 tolerance for rounding
                
                return {
                  ...item,
                  amount_paid: amountPaid,
                  remaining_balance: remainingBalance,
                  is_paid: isPaid,
                };
              } catch (itemError) {
                console.error(`Error processing bill item:`, item, itemError);
                return {
                  ...item,
                  amount_paid: 0,
                  remaining_balance: item.total_price || 0,
                  is_paid: false,
                };
              }
            });
            
            return {
              ...bill,
              bill_items: billItems,
              is_paid: bill.is_paid || false,
              paid_amount: bill.paid_amount || 0,
              total_amount: bill.total_amount || 0,
            };
          } catch (error) {
            console.error(`Failed to load details for bill ${bill.id}:`, error);
            console.error('Error details:', error.message, error.stack);
            return {
              ...bill,
              bill_items: [],
              is_paid: bill.is_paid || false,
              paid_amount: bill.paid_amount || 0,
              total_amount: bill.total_amount || 0,
            };
          }
        })
      );
      
      bills.value = detailedBills;
      console.log('Loaded bills for encounter:', selectedEncounterId.value, detailedBills);
      console.log('Total bills:', detailedBills.length);
      console.log('Bill items:', detailedBills.flatMap(b => b.bill_items || []));
      console.log('Bill items count:', detailedBills.flatMap(b => b.bill_items || []).length);
    } catch (error) {
      console.error('Failed to load bills:', error);
      bills.value = [];
    }

    // Set encounter_id for new prescription form
    newPrescriptionForm.value.encounter_id = selectedEncounterId.value;
    
    // Calculate prices for all prescriptions and total for confirmed ones
    await calculateAllPrescriptionPrices();
    await calculatePrescriptionCosts();
  } catch (error) {
    prescriptions.value = [];
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to load encounter data',
    });
  } finally {
    loadingPrescriptions.value = false;
    loadingData.value = false;
  }
};

const confirmPrescription = (prescription) => {
  // Check if this is an inpatient prescription
  if (prescription.prescription_type === 'inpatient' || prescription.source === 'inpatient') {
    // For inpatient, show confirmation dialog with "Add to IPD bill" checkbox
    const defaultQuantity = prescription.quantity && prescription.quantity > 0 ? prescription.quantity : 1;
    confirmInpatientForm.value = {
      id: prescription.id,
      medicine_name: prescription.medicine_name,
      medicine_code: prescription.medicine_code,
      dose: prescription.dose || '',
      frequency: prescription.frequency || '',
      duration: prescription.duration || '',
      quantity: defaultQuantity,
      instructions: prescription.instructions || '',
      add_to_ipd_bill: true, // Default to true
    };
    showConfirmInpatientDialog.value = true;
    return;
  }
  
  // Prevent confirming external prescriptions
  if (prescription.is_external) {
    $q.notify({
      type: 'warning',
      message: 'External prescriptions are automatically confirmed and cannot be confirmed again. They are filled outside and not billed.',
    });
    return;
  }
  
  // For OPD, show confirmation dialog
  // Populate form with current prescription data
  // If quantity is 0 (from doctor), set to 1 as default for pharmacy to edit
  const defaultQuantity = prescription.quantity && prescription.quantity > 0 ? prescription.quantity : 1;
  confirmForm.value = {
    id: prescription.id,
    medicine_name: prescription.medicine_name,
    medicine_code: prescription.medicine_code,
    dose: prescription.dose || '',
    frequency: prescription.frequency || '',
    duration: prescription.duration || '',
    quantity: defaultQuantity,
    instructions: prescription.instructions || '',
    is_external: false, // Reset to false when opening dialog
  };
  showConfirmDialog.value = true;
};

// Confirm inpatient prescription with dialog
const confirmInpatientPrescriptionSubmit = async () => {
  if (!confirmInpatientForm.value.id) return;

  confirmingInpatient.value = confirmInpatientForm.value.id;
  try {
    const confirmData = {
      dose: confirmInpatientForm.value.dose,
      frequency: confirmInpatientForm.value.frequency,
      duration: confirmInpatientForm.value.duration,
      quantity: confirmInpatientForm.value.quantity,
      instructions: confirmInpatientForm.value.instructions || null,
      add_to_ipd_bill: confirmInpatientForm.value.add_to_ipd_bill !== false, // Default to true
    };

    await consultationAPI.confirmInpatientPrescription(confirmInpatientForm.value.id, confirmData);
    $q.notify({
      type: 'positive',
      message: confirmInpatientForm.value.add_to_ipd_bill 
        ? 'Inpatient prescription confirmed and added to IPD bill' 
        : 'Inpatient prescription confirmed (not added to bill)',
    });
    showConfirmInpatientDialog.value = false;
    await loadInpatientPrescriptions();
  } catch (error) {
    console.error('Error confirming inpatient prescription:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to confirm prescription',
    });
  } finally {
    confirmingInpatient.value = null;
  }
};

const confirmPrescriptionSubmit = async () => {
  if (!confirmForm.value.id) return;

  confirmingId.value = confirmForm.value.id;
  try {
    const confirmData = {
      dose: confirmForm.value.dose,
      frequency: confirmForm.value.frequency,
      duration: confirmForm.value.duration,
      quantity: confirmForm.value.quantity,
      instructions: confirmForm.value.instructions || null,
      is_external: confirmForm.value.is_external || false,
    };

    await consultationAPI.confirmPrescription(confirmForm.value.id, confirmData);
    $q.notify({
      type: 'positive',
      message: confirmForm.value.is_external 
        ? 'Prescription marked as external successfully' 
        : 'Prescription confirmed and bill generated successfully',
    });
    showConfirmDialog.value = false;
    // Reload prescriptions and bills to update status
    await loadPrescriptions();
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to confirm prescription',
    });
  } finally {
    confirmingId.value = null;
  }
};

const canDispense = (prescription) => {
  // Inpatient prescriptions can always be dispensed (no payment check)
  if (prescription.prescription_type === 'inpatient' || prescription.source === 'inpatient') {
    return prescription.is_confirmed;
  }
  
  // Must be confirmed before dispense
  if (!prescription.is_confirmed) {
    console.log(`canDispense: Prescription ${prescription.id} not confirmed`);
    return false;
  }
  
  // Find bill item for this specific prescription
  // Check ALL bills (paid or unpaid) to find the specific item for this service
  for (const bill of bills.value) {
    for (const billItem of bill.bill_items || []) {
      // Match by medicine code or name
      const matchesCode = billItem.item_code === prescription.medicine_code;
      const matchesName = billItem.item_name && (
        billItem.item_name.includes(prescription.medicine_name) ||
        billItem.item_name.includes(`Prescription: ${prescription.medicine_name}`)
      );
      
      if (matchesCode || matchesName) {
        console.log(`canDispense: Found matching bill item for prescription ${prescription.id}:`, {
          prescription_code: prescription.medicine_code,
          prescription_name: prescription.medicine_name,
          billItem_name: billItem.item_name,
          billItem_code: billItem.item_code,
          totalPrice: billItem.total_price,
          amountPaid: billItem.amount_paid,
          remainingBalance: billItem.remaining_balance,
        });
        
        // Found matching bill item - check if THIS SPECIFIC item is paid
        const totalPrice = billItem.total_price || 0;
        const remainingBalance = billItem.remaining_balance !== undefined && billItem.remaining_balance !== null
          ? billItem.remaining_balance 
          : (totalPrice - (billItem.amount_paid || 0));
        // Item is paid if is_paid flag is true OR remaining balance is 0 or less (allow small rounding differences)
        const isPaid = billItem.is_paid !== undefined 
          ? billItem.is_paid 
          : (remainingBalance <= 0.01); // Allow 0.01 tolerance for rounding
        
        console.log(`canDispense: Calculated values - totalPrice=${totalPrice}, remainingBalance=${remainingBalance}, is_paid=${isPaid}`);
        
        // Can dispense if:
        // 1. Total price is 0 (free), OR
        // 2. Item is paid (remaining balance <= 0.01 or is_paid flag is true)
        if (totalPrice > 0 && !isPaid) {
          console.log(`canDispense: Returning FALSE - unpaid balance for THIS SPECIFIC prescription ${prescription.id}`);
          return false; // This specific item has unpaid balance
        } else {
          console.log(`canDispense: THIS SPECIFIC prescription ${prescription.id} is paid or free, allowing dispense`);
          return true; // This specific item is paid or free
        }
      } else {
        console.log(`canDispense: No match - prescription code: ${prescription.medicine_code}, bill item code: ${billItem.item_code}, prescription name: ${prescription.medicine_name}, bill item name: ${billItem.item_name}`);
      }
    }
  }
  
  console.log(`canDispense: No bill item found for prescription ${prescription.id}, allowing dispense`);
  // If no bill item found for this prescription, allow dispense
  // (might be free or bill not created yet - backend will enforce)
  return true;
};

const dispensePrescription = (prescription) => {
  // Check if this is an inpatient prescription
  if (prescription.prescription_type === 'inpatient' || prescription.source === 'inpatient') {
    // For inpatient, dispense directly without dialog (no payment check needed)
    dispenseInpatientPrescriptionDirect(prescription);
    return;
  }
  
  // For OPD, show dispense dialog
  dispenseForm.value = {
    id: prescription.id,
    medicine_name: prescription.medicine_name,
    medicine_code: prescription.medicine_code,
    dose: prescription.dose || '',
    frequency: prescription.frequency || '',
    duration: prescription.duration || '',
    quantity: prescription.quantity || 1,
  };
  showDispenseDialog.value = true;
};

// Direct dispense for inpatient prescriptions (no dialog needed)
const dispenseInpatientPrescriptionDirect = async (prescription) => {
  dispensingInpatient.value = prescription.id;
  try {
    await consultationAPI.dispenseInpatientPrescription(prescription.id);
    $q.notify({
      type: 'positive',
      message: 'Inpatient prescription dispensed successfully',
    });
    await loadInpatientPrescriptions();
    if (selectedEncounterId.value) {
      await loadPrescriptions();
    }
  } catch (error) {
    console.error('Error dispensing inpatient prescription:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to dispense prescription',
    });
  } finally {
    dispensingInpatient.value = null;
  }
};

const confirmDispense = async () => {
  if (!dispenseForm.value.id) return;

  dispensingId.value = dispenseForm.value.id;
  try {
    const dispenseData = {
      dose: dispenseForm.value.dose,
      frequency: dispenseForm.value.frequency,
      duration: dispenseForm.value.duration,
      quantity: dispenseForm.value.quantity,
    };

    await consultationAPI.dispensePrescription(dispenseForm.value.id, dispenseData);
    $q.notify({
      type: 'positive',
      message: 'Prescription marked as dispensed',
    });
    showDispenseDialog.value = false;
    // Reload prescriptions to update status
    await loadPrescriptions();
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to dispense prescription',
    });
  } finally {
    dispensingId.value = null;
  }
};

const unconfirmPrescription = async (prescription) => {
  $q.dialog({
    title: 'Revert Prescription',
    message: `Revert ${prescription.medicine_name} back to pending? This will undo the confirmation and remove it from the bill.`,
    cancel: true,
    persistent: true,
  }).onOk(async () => {
    // Check if this is an inpatient prescription
    if (prescription.prescription_type === 'inpatient' || prescription.source === 'inpatient') {
      unconfirmingInpatient.value = prescription.id;
      try {
        await consultationAPI.unconfirmInpatientPrescription(prescription.id);
        $q.notify({
          type: 'positive',
          message: 'Inpatient prescription reverted to pending successfully',
          position: 'top',
        });
        await loadInpatientPrescriptions();
        if (selectedEncounterId.value) {
          await loadPrescriptions();
        }
      } catch (error) {
        console.error('Unconfirm error:', error);
        $q.notify({
          type: 'negative',
          message: error.response?.data?.detail || error.message || 'Failed to revert prescription',
          position: 'top',
        });
      } finally {
        unconfirmingInpatient.value = null;
      }
    } else {
      // OPD prescription
    unconfirmingId.value = prescription.id;
    try {
      console.log('Unconfirming prescription:', prescription.id);
      const response = await consultationAPI.unconfirmPrescription(prescription.id);
      console.log('Unconfirm response:', response);
      $q.notify({
        type: 'positive',
        message: 'Prescription reverted to pending successfully',
        position: 'top',
      });
      // Reload prescriptions and recalculate costs
      await loadPrescriptions();
      await calculateAllPrescriptionPrices();
      await calculatePrescriptionCosts();
    } catch (error) {
      console.error('Unconfirm error:', error);
      console.error('Error response:', error.response);
      $q.notify({
        type: 'negative',
        message: error.response?.data?.detail || error.message || 'Failed to revert prescription',
        position: 'top',
      });
    } finally {
      unconfirmingId.value = null;
      }
    }
  });
};

const returnPrescription = async (prescription) => {
  $q.dialog({
    title: 'Return Prescription',
    message: `Return ${prescription.medicine_name}? This will undo the dispense action.`,
    cancel: true,
    persistent: true,
  }).onOk(async () => {
    returningId.value = prescription.id;
    try {
      // Check if this is an inpatient prescription
      if (prescription.prescription_type === 'inpatient' || prescription.source === 'inpatient') {
        // Use dedicated inpatient return endpoint
        await consultationAPI.returnInpatientPrescription(prescription.id);
        $q.notify({
          type: 'positive',
          message: 'Inpatient prescription returned successfully',
        });
        await loadInpatientPrescriptions();
      } else {
        await consultationAPI.returnPrescription(prescription.id);
        $q.notify({
          type: 'positive',
          message: 'Prescription returned successfully',
        });
        await loadPrescriptions();
      }
    } catch (error) {
      $q.notify({
        type: 'negative',
        message: error.response?.data?.detail || 'Failed to return prescription',
      });
    } finally {
      returningId.value = null;
    }
  });
};

const deleteExternalPrescription = async (prescription) => {
  $q.dialog({
    title: 'Delete External Prescription',
    message: `Are you sure you want to delete ${prescription.medicine_name}? This action cannot be undone.`,
    cancel: true,
    persistent: true,
    color: 'negative',
  }).onOk(async () => {
    deletingId.value = prescription.id;
    try {
      await consultationAPI.deletePrescription(prescription.id);
      $q.notify({
        type: 'positive',
        message: 'External prescription deleted successfully',
      });
      // Reload prescriptions to update list
      await loadPrescriptions();
    } catch (error) {
      $q.notify({
        type: 'negative',
        message: error.response?.data?.detail || 'Failed to delete external prescription',
      });
    } finally {
      deletingId.value = null;
    }
  });
};

const editPrescription = (prescription) => {
  // Populate form with current prescription data
  editPrescriptionForm.value = {
    id: prescription.id,
    encounter_id: prescription.encounter_id,
    medicine_code: prescription.medicine_code,
    medicine_name: prescription.medicine_name,
    dose: prescription.dose || '',
    unit: prescription.unit || '',
    frequency: prescription.frequency || '',
    duration: prescription.duration || '',
    quantity: prescription.quantity || 1,
    instructions: prescription.instructions || '',
  };
  showEditPrescriptionDialog.value = true;
};

const updatePrescriptionSubmit = async () => {
  if (!editPrescriptionForm.value.id) return;

  updatingPrescriptionId.value = editPrescriptionForm.value.id;
  try {
    const updateData = {
      encounter_id: editPrescriptionForm.value.encounter_id,
      medicine_code: editPrescriptionForm.value.medicine_code,
      medicine_name: editPrescriptionForm.value.medicine_name,
      dose: editPrescriptionForm.value.dose,
      unit: editPrescriptionForm.value.unit || null,
      frequency: editPrescriptionForm.value.frequency,
      duration: editPrescriptionForm.value.duration,
      quantity: editPrescriptionForm.value.quantity,
      instructions: editPrescriptionForm.value.instructions || null,
    };

    await consultationAPI.updatePrescription(editPrescriptionForm.value.id, updateData);
    $q.notify({
      type: 'positive',
      message: 'Prescription updated successfully',
    });
    showEditPrescriptionDialog.value = false;
    // Reload prescriptions to update status
    await loadPrescriptions();
    await loadInpatientPrescriptions();
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to update prescription',
    });
  } finally {
    updatingPrescriptionId.value = null;
  }
};

const filterUnits = (val, update, abort) => {
  update(() => {
    const needle = val.toLowerCase();
    // Filter units - show all if empty, otherwise filter
    if (needle === '') {
      // Show all units
    } else {
      // Filter units that match
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

  // Filter from pre-loaded medications
  update(() => {
    const needle = val.toLowerCase();
    medicationOptions.value = allMedications.value.filter(
      (m) => 
        (m.item_name && m.item_name.toLowerCase().indexOf(needle) > -1) ||
        (m.medication_name && m.medication_name.toLowerCase().indexOf(needle) > -1) ||
        (m.service_name && m.service_name.toLowerCase().indexOf(needle) > -1) ||
        (m.product_name && m.product_name.toLowerCase().indexOf(needle) > -1) ||
        (m.item_code && m.item_code.toLowerCase().indexOf(needle) > -1) ||
        (m.medication_code && m.medication_code.toLowerCase().indexOf(needle) > -1)
    );
  });
};

const onMedicationSelected = (medicationCode) => {
  if (!medicationCode) {
    newPrescriptionForm.value.medicine_code = '';
    newPrescriptionForm.value.medicine_name = '';
    externalPrescriptionForm.value.medicine_code = '';
    externalPrescriptionForm.value.medicine_name = '';
    return;
  }

  // Find medication from allMedications (full list) or medicationOptions (filtered)
  const selected = allMedications.value.find(
    m => (m.item_code || m.medication_code) === medicationCode
  ) || medicationOptions.value.find(
    m => (m.item_code || m.medication_code) === medicationCode
  );
  
  if (selected) {
    const code = selected.item_code || selected.medication_code || '';
    // Include formulation in the name if available
    let name = selected.item_name || selected.medication_name || selected.product_name || selected.service_name || '';
    if (selected.formulation) {
      name = `${name} (${selected.formulation})`;
    }
    
    // Update the active form (check which dialog is open)
    if (showAddPrescriptionDialog.value) {
      newPrescriptionForm.value.medicine_code = code;
      newPrescriptionForm.value.medicine_name = name;
    }
    if (showAddExternalPrescriptionDialog.value) {
      externalPrescriptionForm.value.medicine_code = code;
      externalPrescriptionForm.value.medicine_name = name;
    }
  }
};

const addPrescription = async () => {
  if (!selectedMedication.value) {
    $q.notify({
      type: 'warning',
      message: 'Please select a medication',
    });
    return;
  }

  addingPrescription.value = true;
  try {
    if (serviceType.value === 'ipd') {
      // For IPD, use inpatient prescription endpoint
      if (!newPrescriptionForm.value.ward_admission_id || !newPrescriptionForm.value.clinical_review_id) {
        $q.notify({
          type: 'warning',
          message: 'Missing ward admission or clinical review information',
        });
        return;
      }
      
      await consultationAPI.createInpatientPrescription(
        newPrescriptionForm.value.ward_admission_id,
        newPrescriptionForm.value.clinical_review_id,
        {
          medicine_code: newPrescriptionForm.value.medicine_code,
          medicine_name: newPrescriptionForm.value.medicine_name,
          dose: newPrescriptionForm.value.dose || null,
          unit: newPrescriptionForm.value.unit || null,
          frequency: newPrescriptionForm.value.frequency || null,
          duration: newPrescriptionForm.value.duration || null,
          quantity: newPrescriptionForm.value.quantity || 0,
        }
      );
      
      $q.notify({
        type: 'positive',
        message: 'Inpatient medication added successfully',
      });
      
      // Reload IPD prescriptions
      await loadInpatientPrescriptions();
    } else {
      // For OPD, use regular prescription endpoint
      await consultationAPI.createPrescription(newPrescriptionForm.value);
      $q.notify({
        type: 'positive',
        message: 'Prescription added successfully',
      });
      
      // Reload OPD prescriptions
      await loadPrescriptions();
    }
    
    showAddPrescriptionDialog.value = false;
    // Reset form
    selectedMedication.value = null;
    Object.assign(newPrescriptionForm.value, {
      encounter_id: serviceType.value === 'opd' ? selectedEncounterId.value : undefined,
      ward_admission_id: serviceType.value === 'ipd' ? selectedWardAdmissionId.value : undefined,
      clinical_review_id: serviceType.value === 'ipd' ? newPrescriptionForm.value.clinical_review_id : undefined,
      medicine_code: '',
      medicine_name: '',
      dose: '',
      frequency: '',
      duration: '',
      quantity: 1,
    });
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to add prescription',
    });
  } finally {
    addingPrescription.value = false;
  }
};

const addExternalPrescription = async () => {
  if (!selectedMedication.value) {
    $q.notify({
      type: 'warning',
      message: 'Please select a medication',
    });
    return;
  }

  addingPrescription.value = true;
  try {
    if (serviceType.value === 'ipd') {
      // For IPD, external prescriptions are not typically used
      // But if needed, we can add them as regular prescriptions with is_external flag
      // However, the inpatient prescription model doesn't have is_external in the same way
      // For now, show a message that external prescriptions for IPD are not supported
      $q.notify({
        type: 'warning',
        message: 'External prescriptions for IPD are not currently supported. Please add as a regular medication.',
      });
      showAddExternalPrescriptionDialog.value = false;
      return;
    } else {
      // For OPD, use regular prescription endpoint with is_external flag
      const prescriptionData = {
        ...externalPrescriptionForm.value,
        is_external: true,
      };
      await consultationAPI.createPrescription(prescriptionData);
      $q.notify({
        type: 'positive',
        message: 'External prescription added successfully',
      });
      
      // Reload OPD prescriptions
      await loadPrescriptions();
    }
    
    showAddExternalPrescriptionDialog.value = false;
    // Reset form
    selectedMedication.value = null;
    Object.assign(externalPrescriptionForm.value, {
      encounter_id: serviceType.value === 'opd' ? selectedEncounterId.value : undefined,
      ward_admission_id: serviceType.value === 'ipd' ? selectedWardAdmissionId.value : undefined,
      clinical_review_id: serviceType.value === 'ipd' ? externalPrescriptionForm.value.clinical_review_id : undefined,
      medicine_code: '',
      medicine_name: '',
      dose: '',
      frequency: '',
      duration: '',
      quantity: 1,
      instructions: '',
    });
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to add external prescription',
    });
  } finally {
    addingPrescription.value = false;
  }
};

const selectOldEncounter = async (encounterId) => {
  await selectOPDEncounter(encounterId);
};

const formatDate = (dateString) => {
  if (!dateString) return 'N/A';
  const date = new Date(dateString);
  return date.toLocaleDateString('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
};

const formatCurrency = (amount) => {
  if (amount === undefined || amount === null) return 'N/A';
  return new Intl.NumberFormat('en-GH', {
    style: 'currency',
    currency: 'GHS',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(amount);
};

const encounterProceduresCache = ref(new Map());

const getEncounterProcedures = (encounter) => {
  if (!encounter || !encounter.id) return encounter?.department || 'N/A';
  
  // Check cache first
  if (encounterProceduresCache.value.has(encounter.id)) {
    const cached = encounterProceduresCache.value.get(encounter.id);
    return cached || encounter.department || 'N/A';
  }
  
  // Set loading placeholder
  encounterProceduresCache.value.set(encounter.id, 'Loading...');
  
  // Fetch prescriptions asynchronously (Pharmacy page shows prescriptions)
  consultationAPI.getPrescriptions(encounter.id)
    .then(response => {
      const prescriptions = response.data || [];
      const medicationNames = prescriptions
        .filter(pres => pres.medication_name)
        .map(pres => pres.medication_name)
        .filter((name, index, self) => self.indexOf(name) === index); // Remove duplicates
      
      const displayText = medicationNames.length > 0 
        ? (medicationNames.length > 3 
          ? `${medicationNames.slice(0, 3).join(', ')}... (+${medicationNames.length - 3} more)`
          : medicationNames.join(', '))
        : (encounter.department || 'N/A');
      
      encounterProceduresCache.value.set(encounter.id, displayText);
    })
    .catch(error => {
      console.error('Failed to fetch procedures for encounter:', error);
      encounterProceduresCache.value.set(encounter.id, encounter.department || 'N/A');
    });
  
  // Return department as fallback while loading
  return encounter.department || 'N/A';
};

const clearSearch = () => {
  cardNumber.value = '';
  patient.value = null;
  serviceType.value = null;
  selectedWardAdmissionId.value = null;
  wardAdmissions.value = [];
  inpatientPrescriptions.value = [];
  activeEncounters.value = [];
  todaysEncounter.value = null;
  oldEncounters.value = [];
  oldEncountersExpanded.value = false;
  selectedEncounterId.value = null;
  encounterProceduresCache.value.clear();
  prescriptions.value = [];
  selectedPrescriptions.value = [];
  itemizedPrescriptions.value = [];
  diagnoses.value = [];
  vitals.value = null;
  selectedMedication.value = null;
  medicationOptions.value = [];
  allMedications.value = [];
};

// Load all staff for prescriber/dispenser names
const loadStaff = async () => {
  try {
    const response = await staffAPI.getAll();
    const staff = response.data || [];
    const map = {};
    staff.forEach(s => {
      map[s.id] = s.full_name || s.username || `User ${s.id}`;
    });
    staffMap.value = map;
  } catch (error) {
    console.error('Failed to load staff:', error);
    staffMap.value = {};
  }
};

// Get medication unit cost from price list
// Returns co-payment if insured (has CCC), otherwise base_rate
// If nhia_claim_co_payment is null for insured, returns 0 (free for patient)
const getMedicationPrice = async (medicineCode, isInsured = false) => {
  if (!medicineCode) {
    console.warn('getMedicationPrice: No medicine code provided');
    return 0;
  }
  
  try {
    console.log(`getMedicationPrice: Searching for code="${medicineCode}", isInsured=${isInsured}`);
    
    // Search for products without service_type filter (products aren't tied to service types)
    // Products are filtered by sub_category, but we want to search all products
    const response = await priceListAPI.search(medicineCode, null, 'product');
    const items = response.data || [];
    
    console.log(`getMedicationPrice: Found ${items.length} items for code="${medicineCode}"`);
    
    if (items.length > 0) {
      // Try to find exact match first (case-insensitive)
      let item = items.find(i => {
        const code = (i.item_code || i.medication_code || '').toString().toUpperCase().trim();
        const searchCode = medicineCode.toString().toUpperCase().trim();
        return code === searchCode || 
               (i.product_code && i.product_code.toString().toUpperCase().trim() === searchCode) ||
               (i.product_id && i.product_id.toString().toUpperCase().trim() === searchCode);
      });
      
      // If no exact match, use first item
      if (!item) {
        console.warn(`getMedicationPrice: No exact match for code="${medicineCode}", using first result`);
        item = items[0];
      }
      
      console.log(`getMedicationPrice: Using item:`, {
        medication_code: item.medication_code || item.item_code,
        product_name: item.product_name || item.item_name,
        base_rate: item.base_rate,
        nhia_claim_co_payment: item.nhia_claim_co_payment,
        insurance_covered: item.insurance_covered,
        isInsured
      });
      
      // Check if product is covered by insurance
      const insuranceCovered = item.insurance_covered && item.insurance_covered.toString().toLowerCase().trim() === 'no' ? false : true;
      
      // If product is NOT covered by insurance, always charge base_rate
      if (!insuranceCovered) {
        const price = parseFloat(item.base_rate) || parseFloat(item.unit_cost) || parseFloat(item.cash_price) || 0;
        console.log(`getMedicationPrice: Product not covered by insurance, returning base_rate: ${price}`);
        return price;
      }
      
      // If insured (has CCC), return co-payment (null means 0 - free for patient)
      if (isInsured) {
        if (item.nhia_claim_co_payment !== null && item.nhia_claim_co_payment !== undefined) {
          const price = parseFloat(item.nhia_claim_co_payment) || 0;
          console.log(`getMedicationPrice: Returning co-payment: ${price}`);
          return price;
        }
        // If co_payment field exists, use it
        if (item.co_payment !== null && item.co_payment !== undefined) {
          const price = parseFloat(item.co_payment) || 0;
          console.log(`getMedicationPrice: Returning co_payment: ${price}`);
          return price;
        }
        // If null/undefined, patient pays 0
        console.log('getMedicationPrice: No co-payment found, returning 0 for insured patient');
        return 0;
      } else {
        // Non-insured: use base_rate
        const price = parseFloat(item.base_rate) || parseFloat(item.unit_cost) || parseFloat(item.cash_price) || 0;
        console.log(`getMedicationPrice: Returning base_rate: ${price}`);
        return price;
      }
    }
    
    console.warn(`getMedicationPrice: No items found for code="${medicineCode}"`);
    return 0;
  } catch (error) {
    console.error('Failed to get medication price:', error);
    console.error('Error details:', error.response?.data || error.message);
    return 0;
  }
};

// Load pharmacy medications on component mount
// Auto-load from route query parameter
const autoLoadFromRoute = async () => {
  if (route.query.encounterId) {
    const encounterId = parseInt(route.query.encounterId);
    selectedEncounterId.value = encounterId;
    
    try {
      // Get encounter details to get patient info
      const encounterResponse = await encountersAPI.get(encounterId);
      const encounter = encounterResponse.data;
      currentEncounter.value = encounter;
      
      if (encounter && encounter.patient_id) {
        // Get patient info
        const patientResponse = await patientsAPI.get(encounter.patient_id);
        patient.value = patientResponse.data;
        cardNumber.value = patient.value.card_number;
        
        // Load all encounters for this patient
        const encountersResponse = await encountersAPI.getPatientEncounters(encounter.patient_id);
        const allEncounters = encountersResponse.data.filter(e => !e.archived);
        activeEncounters.value = allEncounters.map(e => ({
          id: e.id,
          label: `Encounter #${e.id} - ${e.department} (${new Date(e.created_at).toLocaleDateString()})`,
          value: e.id,
        }));
        
        // Load prescriptions for this encounter
        await loadPrescriptions();
      }
    } catch (error) {
      console.error('Failed to auto-load from route:', error);
      $q.notify({
        type: 'warning',
        message: 'Failed to load encounter details',
      });
    }
  }
};

// Watch for route query changes
watch(() => route.query.encounterId, (newEncounterId) => {
  if (newEncounterId) {
    autoLoadFromRoute();
  }
});

const dispensedPrescriptions = computed(() => (prescriptions.value || []).filter(p => p.is_dispensed));

const isFinalized = computed(() => {
  return currentEncounter.value?.status === 'finalized';
});

// Check if encounter is insured (has CCC number)
const isInsuredEncounter = computed(() => {
  return !!(currentEncounter.value?.ccc_number && currentEncounter.value.ccc_number.trim() !== '');
});

// Get confirmed prescriptions (excluding external ones)
const confirmedPrescriptions = computed(() => {
  return (prescriptions.value || []).filter(p => p.is_confirmed && !p.is_external);
});

// Count of confirmed prescriptions
const confirmedPrescriptionsCount = computed(() => {
  return confirmedPrescriptions.value.length;
});

// Calculate prices for all prescriptions (for display in table)
const calculateAllPrescriptionPrices = async () => {
  if (!currentEncounter.value || prescriptions.value.length === 0) {
    prescriptionPrices.value.clear();
    return;
  }

  try {
    const isInsured = isInsuredEncounter.value;
    const newPrices = new Map();

    // Calculate price for each prescription (excluding external ones)
    for (const prescription of prescriptions.value) {
      if (prescription.is_external) {
        // External prescriptions don't have prices
        continue;
      }
      
      if (prescription.medicine_code) {
        try {
          const unitPrice = await getMedicationPrice(prescription.medicine_code, isInsured);
          const quantity = prescription.quantity || 1;
          const totalPrice = unitPrice * quantity;
          newPrices.set(prescription.id, totalPrice);
        } catch (error) {
          console.error(`Failed to get price for prescription ${prescription.id}:`, error);
          newPrices.set(prescription.id, 0);
        }
      } else {
        newPrices.set(prescription.id, 0);
      }
    }

    prescriptionPrices.value = newPrices;
  } catch (error) {
    console.error('Failed to calculate prescription prices:', error);
    prescriptionPrices.value.clear();
  }
};

// Calculate total cost of confirmed prescriptions
const calculatePrescriptionCosts = async () => {
  if (!currentEncounter.value || confirmedPrescriptions.value.length === 0) {
    prescriptionTotalAmount.value = 0;
    return;
  }

  loadingPrescriptionCosts.value = true;
  try {
    const isInsured = isInsuredEncounter.value;
    let total = 0;

    // Calculate cost for each confirmed prescription
    for (const prescription of confirmedPrescriptions.value) {
      if (prescription.medicine_code) {
        const unitPrice = await getMedicationPrice(prescription.medicine_code, isInsured);
        const quantity = prescription.quantity || 1;
        total += unitPrice * quantity;
      }
    }

    prescriptionTotalAmount.value = total;
  } catch (error) {
    console.error('Failed to calculate prescription costs:', error);
    prescriptionTotalAmount.value = 0;
  } finally {
    loadingPrescriptionCosts.value = false;
  }
};

// Watch for changes in prescriptions or encounter to recalculate costs
// This must be after all computed properties and functions are defined
watch([() => prescriptions.value, () => currentEncounter.value], () => {
  if (currentEncounter.value) {
    calculateAllPrescriptionPrices();
    calculatePrescriptionCosts();
  } else {
    prescriptionTotalAmount.value = 0;
    prescriptionPrices.value.clear();
  }
}, { deep: true });

// Load ward admissions for the current patient
const loadWardAdmissions = async () => {
  if (!patient.value || !patient.value.card_number) {
    wardAdmissions.value = [];
    return;
  }
  
  try {
    const response = await consultationAPI.getWardAdmissionsByPatientCard(patient.value.card_number);
    wardAdmissions.value = response.data || [];
  } catch (error) {
    console.error('Error loading ward admissions:', error);
    if (error.response?.status !== 404) {
      $q.notify({
        type: 'negative',
        message: error.response?.data?.detail || 'Failed to load ward admissions',
      });
    }
    wardAdmissions.value = [];
  }
};

// Select OPD encounter
const selectOPDEncounter = async (encounterId) => {
  serviceType.value = 'opd';
  selectedEncounterId.value = encounterId;
  selectedWardAdmissionId.value = null;
  await loadPrescriptions();
};

// Select IPD admission
const selectIPDAdmission = async (wardAdmissionId) => {
  console.log('selectIPDAdmission: Selected ward admission ID:', wardAdmissionId);
  serviceType.value = 'ipd';
  selectedWardAdmissionId.value = wardAdmissionId;
  selectedEncounterId.value = null;
  prescriptions.value = []; // Clear OPD prescriptions
  await loadInpatientPrescriptions();
  console.log('selectIPDAdmission: After loading, serviceType:', serviceType.value);
  console.log('selectIPDAdmission: After loading, inpatientPrescriptions.length:', inpatientPrescriptions.value.length);
};

// Load inpatient prescriptions for selected ward admission
const loadInpatientPrescriptions = async () => {
  if (!selectedWardAdmissionId.value) {
    console.log('loadInpatientPrescriptions: No ward admission ID selected');
    inpatientPrescriptions.value = [];
    return;
  }
  
  console.log('loadInpatientPrescriptions: Loading prescriptions for ward admission:', selectedWardAdmissionId.value);
  loadingInpatientPrescriptions.value = true;
  try {
    const response = await consultationAPI.getInpatientPrescriptionsByWardAdmission(selectedWardAdmissionId.value);
    console.log('loadInpatientPrescriptions: API response:', response);
    const inpatientData = response.data || [];
    console.log('loadInpatientPrescriptions: Parsed data:', inpatientData);
    
    // Mark as inpatient
    inpatientPrescriptions.value = inpatientData.map(p => ({
      ...p,
      prescription_type: 'inpatient',
      source: 'inpatient'
    }));
    
    console.log('loadInpatientPrescriptions: Final prescriptions array:', inpatientPrescriptions.value);
    
    // Load diagnoses
    try {
      const diagnosesResponse = await consultationAPI.getAllInpatientDiagnoses(selectedWardAdmissionId.value);
      diagnoses.value = diagnosesResponse.data || [];
      console.log('loadInpatientPrescriptions: Loaded diagnoses:', diagnoses.value);
      
      // If no IPD diagnoses, try to get from OPD encounter
      if (diagnoses.value.length === 0) {
        const admission = wardAdmissions.value.find(wa => wa.id === selectedWardAdmissionId.value);
        if (admission?.encounter_id) {
          try {
            const opdDiagnosesResponse = await consultationAPI.getDiagnoses(admission.encounter_id);
            diagnoses.value = opdDiagnosesResponse.data || [];
            console.log('loadInpatientPrescriptions: Loaded OPD diagnoses as fallback:', diagnoses.value);
          } catch (e) {
            console.error('Failed to load OPD diagnoses:', e);
          }
        }
      }
    } catch (error) {
      console.error('Failed to load diagnoses:', error);
      diagnoses.value = [];
    }
    
    // Load vitals - try IPD first, then fallback to OPD
    try {
      const vitalsResponse = await consultationAPI.getInpatientVitals(selectedWardAdmissionId.value);
      inpatientVitals.value = vitalsResponse.data || [];
      // Get most recent vital
      if (inpatientVitals.value.length > 0) {
        latestInpatientVital.value = inpatientVitals.value[0]; // Already sorted by recorded_at desc
        console.log('loadInpatientPrescriptions: Loaded IPD vitals:', inpatientVitals.value);
        console.log('loadInpatientPrescriptions: Latest IPD vital:', latestInpatientVital.value);
      } else {
        // No IPD vitals - try to get from OPD encounter
        const admission = wardAdmissions.value.find(wa => wa.id === selectedWardAdmissionId.value);
        if (admission?.encounter_id) {
          try {
            const opdVitalsResponse = await vitalsAPI.getByEncounter(admission.encounter_id);
            const opdVital = opdVitalsResponse.data;
            if (opdVital) {
              // Convert OPD vital format to match IPD format for display
              latestInpatientVital.value = {
                temperature: opdVital.temperature,
                blood_pressure_systolic: opdVital.bp ? parseFloat(opdVital.bp.split('/')[0]) : null,
                blood_pressure_diastolic: opdVital.bp ? parseFloat(opdVital.bp.split('/')[1]) : null,
                pulse: opdVital.pulse,
                respiratory_rate: opdVital.respiration,
                oxygen_saturation: opdVital.spo2,
                weight: opdVital.weight,
                height: opdVital.height,
                bmi: opdVital.bmi,
                notes: opdVital.remarks,
                recorded_by_name: opdVital.recorded_by_name,
                recorded_at: opdVital.recorded_at || new Date().toISOString(),
              };
              console.log('loadInpatientPrescriptions: Loaded OPD vitals as fallback:', latestInpatientVital.value);
            } else {
              latestInpatientVital.value = null;
            }
          } catch (e) {
            console.error('Failed to load OPD vitals:', e);
            latestInpatientVital.value = null;
          }
        } else {
          latestInpatientVital.value = null;
        }
      }
    } catch (error) {
      console.error('Failed to load vitals:', error);
      inpatientVitals.value = [];
      // Try OPD vitals as fallback
      const admission = wardAdmissions.value.find(wa => wa.id === selectedWardAdmissionId.value);
      if (admission?.encounter_id) {
        try {
          const opdVitalsResponse = await vitalsAPI.getByEncounter(admission.encounter_id);
          const opdVital = opdVitalsResponse.data;
          if (opdVital) {
            latestInpatientVital.value = {
              temperature: opdVital.temperature,
              blood_pressure_systolic: opdVital.bp && opdVital.bp.includes('/') ? parseFloat(opdVital.bp.split('/')[0]) : null,
              blood_pressure_diastolic: opdVital.bp && opdVital.bp.includes('/') ? parseFloat(opdVital.bp.split('/')[1]) : null,
              pulse: opdVital.pulse,
              respiratory_rate: opdVital.respiration,
              oxygen_saturation: opdVital.spo2,
              weight: opdVital.weight,
              height: opdVital.height,
              bmi: opdVital.bmi,
              notes: opdVital.remarks,
              recorded_by_name: opdVital.recorded_by_name,
              recorded_at: opdVital.recorded_at || new Date().toISOString(),
            };
          } else {
            latestInpatientVital.value = null;
          }
        } catch (e) {
          console.error('Failed to load OPD vitals as fallback:', e);
          latestInpatientVital.value = null;
        }
      } else {
        latestInpatientVital.value = null;
      }
    }
    
    // Calculate prices for IPD prescriptions
    await calculateInpatientPrescriptionPrices();
  } catch (error) {
    console.error('Error loading inpatient prescriptions:', error);
    console.error('Error details:', {
      status: error.response?.status,
      statusText: error.response?.statusText,
      data: error.response?.data,
      message: error.message
    });
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to load inpatient prescriptions',
    });
    inpatientPrescriptions.value = [];
  } finally {
    loadingInpatientPrescriptions.value = false;
  }
};

// Calculate prices for inpatient prescriptions
const calculateInpatientPrescriptionPrices = async () => {
  if (!inpatientPrescriptions.value.length) {
    return;
  }
  
  try {
    // Get encounter for insurance status
    const admission = wardAdmissions.value.find(wa => wa.id === selectedWardAdmissionId.value);
    if (!admission) return;
    
    const encounterResponse = await encountersAPI.get(admission.encounter_id);
    const encounter = encounterResponse.data;
    const isInsured = encounter?.ccc_number && encounter.ccc_number.trim() !== '';
    
    // Calculate price for each prescription
    for (const prescription of inpatientPrescriptions.value) {
      if (prescription.medicine_code && !prescription.is_external) {
        try {
          const unitPrice = await getMedicationPrice(prescription.medicine_code, isInsured);
          const quantity = prescription.quantity || 1;
          prescription.calculated_price = unitPrice * quantity;
          prescription.unit_price = unitPrice;
        } catch (error) {
          console.error(`Failed to get price for prescription ${prescription.id}:`, error);
          prescription.calculated_price = 0;
          prescription.unit_price = 0;
        }
      } else {
        prescription.calculated_price = 0;
        prescription.unit_price = 0;
      }
    }
  } catch (error) {
    console.error('Failed to calculate inpatient prescription prices:', error);
  }
};

// Confirm inpatient prescription
const confirmInpatientPrescription = async (prescription) => {
  confirmingInpatient.value = prescription.id;
  try {
    await consultationAPI.confirmInpatientPrescription(prescription.id);
    $q.notify({
      type: 'positive',
      message: 'Inpatient prescription confirmed and added to IPD bill',
    });
    await loadInpatientPrescriptions();
  } catch (error) {
    console.error('Error confirming inpatient prescription:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to confirm prescription',
    });
  } finally {
    confirmingInpatient.value = null;
  }
};

// Dispense inpatient prescription
const dispenseInpatientPrescription = async (prescription) => {
  dispensingInpatient.value = prescription.id;
  try {
    await consultationAPI.dispenseInpatientPrescription(prescription.id);
    $q.notify({
      type: 'positive',
      message: 'Inpatient prescription dispensed successfully',
    });
    await loadInpatientPrescriptions();
  } catch (error) {
    console.error('Error dispensing inpatient prescription:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to dispense prescription',
    });
  } finally {
    dispensingInpatient.value = null;
  }
};

onMounted(() => {
  loadPharmacyMedications();
  loadStaff();
  autoLoadFromRoute();
});

const formatReceiptLine = (label, value) => {
  if (!value && value !== 0) return '';
  return `<div><span class=\"lbl\">${label}</span><span class=\"val\">${value}</span></div>`;
};

const buildReceiptHtml = async () => {
  // Ensure staff is loaded before building receipt
  if (Object.keys(staffMap.value).length === 0) {
    await loadStaff();
  }
  
  const now = new Date();
  const diagText = (diagnoses.value || []).map(d => d.diagnosis).filter(Boolean).join('; ');
  const vit = vitals.value || {};
  
  // Check if encounter is insured (has CCC number)
  const isInsured = !!(currentEncounter.value?.ccc_number);
  
  // Build items HTML with unit costs and total costs, and calculate grand total
  const itemsDataPromises = dispensedPrescriptions.value.map(async (p, idx) => {
    const unitCost = await getMedicationPrice(p.medicine_code, isInsured);
    const quantity = p.quantity || 0;
    const totalCost = unitCost * quantity;
    
    const line1 = `${idx + 1}. ${p.medicine_name || ''}`;
    const line2 = [
      p.dose ? `Dose: ${p.dose}` : '',
      p.frequency ? `Freq: ${p.frequency}` : '',
      p.duration ? `Dur: ${p.duration}` : '',
    ].filter(Boolean).join('  ');
    const line3 = `Qty: ${quantity}`;
    const line4 = `Unit Cost: ₵${unitCost.toFixed(2)}`;
    const line5 = `Total Cost: ₵${totalCost.toFixed(2)}`;
    
    const itemHtml = `
      <div class=\"item\">
        <div class=\"i1\">${line1}</div>
        ${line2 ? `<div class=\"i2\">${line2}</div>` : ''}
        <div class=\"i3\">${line3}</div>
        <div class=\"i4\">${line4}</div>
        <div class=\"i4\">${line5}</div>
      </div>`;
    
    return { html: itemHtml, totalCost };
  });
  
  const itemsData = await Promise.all(itemsDataPromises);
  const itemsHtmlStr = itemsData.map(item => item.html).join('');
  
  // Calculate grand total from all individual total costs
  const grandTotal = itemsData.reduce((sum, item) => sum + item.totalCost, 0);
  
  // Get prescriber name from first dispensed prescription
  const firstPrescription = dispensedPrescriptions.value[0];
  const prescriberId = firstPrescription?.prescribed_by;
  const prescriberName = firstPrescription?.prescriber_name || 
                         (prescriberId ? (staffMap.value[prescriberId] || 'N/A') : 'N/A');
  
  // Get dispenser name from first dispensed prescription
  const dispenserId = firstPrescription?.dispensed_by;
  const dispenserName = firstPrescription?.dispenser_name || 
                        (dispenserId ? (staffMap.value[dispenserId] || 'N/A') : 'N/A');
  
  return `<!doctype html>
  <html>
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>Pharmacy Bill Card</title>
    <style>
      /* Force 70mm thermal size for print & PDF */
      @page { size: 70mm auto; margin: 2mm; }
      html, body { width: 70mm; margin: 0; padding: 0; }
      body { font-family: monospace; font-size: 12px; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
      .center { text-align: center; }
      .hdr { border-bottom: 1px dashed #000; padding-bottom: 6px; margin-bottom: 6px; }
      .logo-container { display: flex; justify-content: center; align-items: center; gap: 8px; margin-bottom: 6px; }
      .logo { max-width: 25mm; max-height: 20mm; object-fit: contain; }
      .hospital-name { font-weight: bold; font-size: 14px; margin: 6px 0; }
      .dept-name { font-weight: bold; font-size: 13px; margin-bottom: 6px; }
      .sec { margin: 6px 0; }
      .lbl { display: inline-block; min-width: 30mm; }
      .val { float: right; max-width: 30mm; text-align: right; }
      .clearfix { clear: both; }
      .item { border-top: 1px dashed #000; padding: 4px 0; }
      .i1 { font-weight: bold; }
      .i2 { }
      .i3 { }
      .i4 { color: #333; }
      .grand-total { font-weight: bold; font-size: 13px; }
      .footer { border-top: 1px dashed #000; margin-top: 6px; padding-top: 6px; }
      .dispenser { margin-bottom: 4px; }
      /* On screen, center the receipt for a visual preview */
      @media screen { body { background: #f5f5f5; } .preview-wrap { width: 70mm; margin: 12px auto; background: #fff; padding: 2mm; box-shadow: 0 0 4px rgba(0,0,0,0.2); } }
      @media print { .preview-wrap { box-shadow: none; padding: 0; } }
    </style>
  </head>
  <body>
    <div class=\"preview-wrap\">
      <div class=\"logo-container\">
        <img src=\"/logos/ministry-of-health-logo.png\" alt=\"Ministry of Health\" class=\"logo\" onerror=\"this.style.display='none'\">
        <img src=\"/logos/ghana-health-service-logo.png\" alt=\"Ghana Health Service\" class=\"logo\" onerror=\"this.style.display='none'\">
      </div>
      <div class=\"center hospital-name\">ASESEWA GOVERNMENT HOSPITAL</div>
      <div class=\"hdr center\">
        <div class=\"dept-name\">PHARMACY DEPARTMENT BILL CARD</div>
      <div>${now.toLocaleString()}</div>
      </div>
    <div class=\"sec\">
      ${formatReceiptLine('Encounter ID', selectedEncounterId.value)}
      ${formatReceiptLine('Patient', `${patient.value?.name || ''} ${patient.value?.surname || ''}`.trim())}
      ${formatReceiptLine('Card', patient.value?.card_number || '')}
      ${formatReceiptLine('Insurance', patient.value?.insurance_id || 'N/A')}
      ${formatReceiptLine('CCC', currentEncounter.value?.ccc_number || '')}
      <div class=\"clearfix\"></div>
    </div>
    <div class=\"sec\">
      <div><strong>Diagnosis</strong></div>
      <div>${diagText || 'N/A'}</div>
    </div>
    <div class=\"sec\">
      <div><strong>Vitals</strong></div>
      ${formatReceiptLine('Weight (kg)', vit.weight || '')}
      <div class=\"clearfix\"></div>
    </div>
    <div class=\"sec\">
      ${formatReceiptLine('Prescriber', prescriberName)}
      <div class=\"clearfix\"></div>
    </div>
    <div class=\"sec\">
      <div class=\"center\"><strong>Dispensed Medicines</strong></div>
      ${itemsHtmlStr || '<div class=\"center\">No dispensed medicines</div>'}
    </div>
    <div class=\"sec\">
      <div class=\"clearfix\"></div>
      ${formatReceiptLine('Grand Total', `₵${grandTotal.toFixed(2)}`)}
      <div class=\"clearfix\"></div>
    </div>
    <div class=\"footer\">
      <div class=\"dispenser\">${formatReceiptLine('Dispenser', dispenserName)}</div>
      <div class=\"clearfix\"></div>
      <div class=\"center\">Thank you</div>
    </div>
    </div>
  </body>
  </html>`;
};

const buildIPDReceiptHtml = async () => {
  // Ensure staff is loaded before building receipt
  if (Object.keys(staffMap.value).length === 0) {
    await loadStaff();
  }
  
  const now = new Date();
  
  // Get ward admission details
  const admission = wardAdmissions.value.find(wa => wa.id === selectedWardAdmissionId.value);
  const encounterId = admission?.encounter_id;
  
  // Get diagnoses - use IPD diagnoses if available, otherwise try OPD diagnoses
  let diagText = (diagnoses.value || []).map(d => d.diagnosis).filter(Boolean).join('; ');
  
  // If no IPD diagnoses, try to get from OPD encounter
  if (!diagText || diagText.trim() === '') {
    if (encounterId) {
      try {
        const opdDiagnosesResponse = await consultationAPI.getDiagnoses(encounterId);
        const opdDiagnoses = opdDiagnosesResponse.data || [];
        diagText = opdDiagnoses.map(d => d.diagnosis).filter(Boolean).join('; ');
        console.log('buildIPDReceiptHtml: Loaded OPD diagnoses as fallback:', diagText);
      } catch (e) {
        console.error('Failed to load OPD diagnoses for print:', e);
      }
    }
  }
  
  // Get vitals - use IPD vitals if available, otherwise try OPD vitals
  let vit = latestInpatientVital.value || {};
  
  // If no IPD vitals, try to get from OPD encounter
  if (!vit || (!vit.weight && !vit.temperature && !vit.pulse)) {
    if (encounterId) {
      try {
        const opdVitalsResponse = await vitalsAPI.getByEncounter(encounterId);
        const opdVital = opdVitalsResponse.data;
        if (opdVital) {
          // Convert OPD vital format to match IPD format
          vit = {
            temperature: opdVital.temperature,
            blood_pressure_systolic: opdVital.bp ? parseFloat(opdVital.bp.split('/')[0]) : null,
            blood_pressure_diastolic: opdVital.bp ? parseFloat(opdVital.bp.split('/')[1]) : null,
            pulse: opdVital.pulse,
            respiratory_rate: opdVital.respiration,
            oxygen_saturation: opdVital.spo2,
            weight: opdVital.weight,
            height: opdVital.height,
            bmi: opdVital.bmi,
            notes: opdVital.remarks,
            recorded_by_name: opdVital.recorded_by_name,
            recorded_at: opdVital.recorded_at || new Date().toISOString(),
          };
        }
      } catch (e) {
        console.error('Failed to load OPD vitals for print:', e);
      }
    }
  }
  
  // Get encounter for insurance status
  let isInsured = false;
  let cccNumber = '';
  if (encounterId) {
    try {
      const encResp = await encountersAPI.get(encounterId);
      const encounter = encResp.data;
      isInsured = !!(encounter?.ccc_number && encounter.ccc_number.trim() !== '');
      cccNumber = encounter?.ccc_number || '';
    } catch (e) {
      console.error('Failed to get encounter:', e);
    }
  }
  
  // Get dispensed IPD prescriptions
  const dispensedIPD = inpatientPrescriptions.value.filter(p => p.is_dispensed);
  
  // Build items HTML with unit costs and total costs, and calculate grand total
  const itemsDataPromises = dispensedIPD.map(async (p, idx) => {
    const unitCost = p.unit_price || await getMedicationPrice(p.medicine_code, isInsured);
    const quantity = p.quantity || 0;
    const totalCost = unitCost * quantity;
    
    const line1 = `${idx + 1}. ${p.medicine_name || ''}`;
    const line2 = [
      p.dose ? `Dose: ${p.dose}` : '',
      p.frequency ? `Freq: ${p.frequency}` : '',
      p.duration ? `Dur: ${p.duration}` : '',
    ].filter(Boolean).join('  ');
    const line3 = `Qty: ${quantity}`;
    const line4 = `Unit Cost: ₵${unitCost.toFixed(2)}`;
    const line5 = `Total Cost: ₵${totalCost.toFixed(2)}`;
    
    const itemHtml = `
      <div class=\"item\">
        <div class=\"i1\">${line1}</div>
        ${line2 ? `<div class=\"i2\">${line2}</div>` : ''}
        <div class=\"i3\">${line3}</div>
        <div class=\"i4\">${line4}</div>
        <div class=\"i4\">${line5}</div>
      </div>`;
    
    return { html: itemHtml, totalCost };
  });
  
  const itemsData = await Promise.all(itemsDataPromises);
  const itemsHtmlStr = itemsData.map(item => item.html).join('');
  
  // Calculate grand total from all individual total costs
  const grandTotal = itemsData.reduce((sum, item) => sum + item.totalCost, 0);
  
  // Get prescriber name from first dispensed prescription
  const firstPrescription = dispensedIPD[0];
  const prescriberId = firstPrescription?.prescribed_by;
  const prescriberName = firstPrescription?.prescriber_name || 
                         (prescriberId ? (staffMap.value[prescriberId] || 'N/A') : 'N/A');
  
  // Get dispenser name from first dispensed prescription
  const dispenserId = firstPrescription?.dispensed_by;
  const dispenserName = firstPrescription?.dispenser_name || 
                        (dispenserId ? (staffMap.value[dispenserId] || 'N/A') : 'N/A');
  
  const formatReceiptLine = (label, value) => {
    return `<div class=\"lbl\">${label}:</div><div class=\"val\">${value || ''}</div><div class=\"clearfix\"></div>`;
  };
  
  return `<!doctype html>
  <html>
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>IPD Pharmacy Bill Card</title>
    <style>
      /* Force 70mm thermal size for print & PDF */
      @page { size: 70mm auto; margin: 2mm; }
      html, body { width: 70mm; margin: 0; padding: 0; }
      body { font-family: monospace; font-size: 12px; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
      .center { text-align: center; }
      .hdr { border-bottom: 1px dashed #000; padding-bottom: 6px; margin-bottom: 6px; }
      .logo-container { display: flex; justify-content: center; align-items: center; gap: 8px; margin-bottom: 6px; }
      .logo { max-width: 25mm; max-height: 20mm; object-fit: contain; }
      .hospital-name { font-weight: bold; font-size: 14px; margin: 6px 0; }
      .dept-name { font-weight: bold; font-size: 13px; margin-bottom: 6px; }
      .sec { margin: 6px 0; }
      .lbl { display: inline-block; min-width: 30mm; }
      .val { float: right; max-width: 30mm; text-align: right; }
      .clearfix { clear: both; }
      .item { border-top: 1px dashed #000; padding: 4px 0; }
      .i1 { font-weight: bold; }
      .i2 { }
      .i3 { }
      .i4 { color: #333; }
      .grand-total { font-weight: bold; font-size: 13px; }
      .footer { border-top: 1px dashed #000; margin-top: 6px; padding-top: 6px; }
      .dispenser { margin-bottom: 4px; }
      /* On screen, center the receipt for a visual preview */
      @media screen { body { background: #f5f5f5; } .preview-wrap { width: 70mm; margin: 12px auto; background: #fff; padding: 2mm; box-shadow: 0 0 4px rgba(0,0,0,0.2); } }
      @media print { .preview-wrap { box-shadow: none; padding: 0; } }
    </style>
  </head>
  <body>
    <div class=\"preview-wrap\">
      <div class=\"logo-container\">
        <img src=\"/logos/ministry-of-health-logo.png\" alt=\"Ministry of Health\" class=\"logo\" onerror=\"this.style.display='none'\">
        <img src=\"/logos/ghana-health-service-logo.png\" alt=\"Ghana Health Service\" class=\"logo\" onerror=\"this.style.display='none'\">
      </div>
      <div class=\"center hospital-name\">ASESEWA GOVERNMENT HOSPITAL</div>
      <div class=\"hdr center\">
        <div class=\"dept-name\">IPD PHARMACY DEPARTMENT BILL CARD</div>
        <div>${now.toLocaleString()}</div>
      </div>
      <div class=\"sec\">
        ${formatReceiptLine('Ward Admission ID', selectedWardAdmissionId.value)}
        ${formatReceiptLine('Encounter ID', encounterId || 'N/A')}
        ${formatReceiptLine('Patient', `${patient.value?.name || ''} ${patient.value?.surname || ''}`.trim())}
        ${formatReceiptLine('Card', patient.value?.card_number || '')}
        ${formatReceiptLine('Insurance', patient.value?.insurance_id || 'N/A')}
        ${formatReceiptLine('CCC', cccNumber || '')}
        ${admission ? formatReceiptLine('Ward', admission.ward || '') : ''}
        ${admission?.bed_number ? formatReceiptLine('Bed', admission.bed_number) : ''}
        <div class=\"clearfix\"></div>
      </div>
      <div class=\"sec\">
        <div><strong>Diagnosis</strong></div>
        <div>${diagText || 'N/A'}</div>
      </div>
      <div class=\"sec\">
        <div><strong>Latest Vitals</strong></div>
        ${vit.weight ? formatReceiptLine('Weight (kg)', vit.weight) : ''}
        ${vit.blood_pressure_systolic || vit.blood_pressure_diastolic ? formatReceiptLine('BP', `${vit.blood_pressure_systolic || ''}/${vit.blood_pressure_diastolic || ''} mmHg`) : ''}
        ${vit.temperature ? formatReceiptLine('Temp (°C)', vit.temperature) : ''}
        <div class=\"clearfix\"></div>
      </div>
      <div class=\"sec\">
        ${formatReceiptLine('Prescriber', prescriberName)}
        <div class=\"clearfix\"></div>
      </div>
      <div class=\"sec\">
        <div class=\"center\"><strong>Dispensed Medicines</strong></div>
        ${itemsHtmlStr || '<div class=\"center\">No dispensed medicines</div>'}
      </div>
      <div class=\"sec\">
        <div class=\"clearfix\"></div>
        ${formatReceiptLine('Grand Total', `₵${grandTotal.toFixed(2)}`)}
        <div class=\"clearfix\"></div>
      </div>
      <div class=\"footer\">
        <div class=\"dispenser\">${formatReceiptLine('Dispenser', dispenserName)}</div>
        <div class=\"clearfix\"></div>
        <div class=\"center\">Thank you</div>
      </div>
    </div>
  </body>
  </html>`;
};

const printBillCard = async () => {
  if (serviceType.value === 'ipd') {
    // Print IPD bill card
    if (!selectedWardAdmissionId.value || !patient.value) {
      $q.notify({ type: 'warning', message: 'Select IPD admission first' });
      return;
    }
    
    // Ensure staff is loaded
    if (Object.keys(staffMap.value).length === 0) {
      await loadStaff();
    }
    
    const receiptHtml = await buildIPDReceiptHtml();
    const w = window.open('', '_blank', 'width=420,height=800');
    if (!w) return;
    w.document.open();
    w.document.write(receiptHtml);
    w.document.close();
    setTimeout(() => { try { w.focus(); w.print(); } catch(e) {} }, 300);
  } else {
    // Print OPD bill card
    if (!selectedEncounterId.value || !patient.value) {
      $q.notify({ type: 'warning', message: 'Select encounter first' });
      return;
    }
    
    // Ensure staff is loaded
    if (Object.keys(staffMap.value).length === 0) {
      await loadStaff();
    }
    
    const receiptHtml = await buildReceiptHtml();
    const w = window.open('', '_blank', 'width=420,height=800');
    if (!w) return;
    w.document.open();
    w.document.write(receiptHtml);
    w.document.close();
    setTimeout(() => { try { w.focus(); w.print(); } catch(e) {} }, 300);
  }
};

const buildExternalPrescriptionHtml = async () => {
  // Ensure staff is loaded before building receipt
  if (Object.keys(staffMap.value).length === 0) {
    await loadStaff();
  }
  
  const now = new Date();
  
  // Get external prescriptions for this encounter
  const externalPrescs = externalPrescriptions.value;
  
  if (externalPrescs.length === 0) {
    $q.notify({ type: 'warning', message: 'No external prescriptions found' });
    return null;
  }
  
  // Get prescriber name from first prescription
  const firstPrescription = externalPrescs[0];
  const prescriberId = firstPrescription?.prescribed_by;
  const prescriberName = prescriberId ? (staffMap.value[prescriberId] || firstPrescription?.prescriber_name || 'N/A') : (firstPrescription?.prescriber_name || 'N/A');
  
  // Build medications list
  let itemsHtmlStr = '';
  externalPrescs.forEach((prescription, index) => {
    const dose = prescription.dose || '';
    const unit = prescription.unit || '';
    const frequency = prescription.frequency || '';
    const duration = prescription.duration || '';
    const quantity = prescription.quantity || '';
    const instructions = prescription.instructions || '';
    
    itemsHtmlStr += `
      <div class="item">
        <div class="i1">${prescription.medicine_name}</div>
        <div class="i2">Code: ${prescription.medicine_code}</div>
        <div class="i3">Dose: ${dose} ${unit} | Frequency: ${frequency} | Duration: ${duration}</div>
        <div class="i3">Quantity: ${quantity}</div>
        ${instructions ? `<div class="i4">Instructions: ${instructions}</div>` : ''}
      </div>
    `;
  });
  
  const formatReceiptLine = (label, value) => {
    return `<div class="lbl">${label}:</div><div class="val">${value || ''}</div><div class="clearfix"></div>`;
  };
  
  return `<!doctype html>
  <html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>External Prescription</title>
    <style>
      /* Force 70mm thermal size for print & PDF */
      @page { size: 70mm auto; margin: 2mm; }
      html, body { width: 70mm; margin: 0; padding: 0; }
      body { font-family: monospace; font-size: 12px; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
      .center { text-align: center; }
      .hdr { border-bottom: 1px dashed #000; padding-bottom: 6px; margin-bottom: 6px; }
      .logo-container { display: flex; justify-content: center; align-items: center; gap: 8px; margin-bottom: 6px; }
      .logo { max-width: 25mm; max-height: 20mm; object-fit: contain; }
      .hospital-name { font-weight: bold; font-size: 14px; margin: 6px 0; }
      .dept-name { font-weight: bold; font-size: 13px; margin-bottom: 6px; }
      .sec { margin: 6px 0; }
      .lbl { display: inline-block; min-width: 30mm; }
      .val { float: right; max-width: 30mm; text-align: right; }
      .clearfix { clear: both; }
      .item { border-top: 1px dashed #000; padding: 4px 0; }
      .i1 { font-weight: bold; }
      .i2 { }
      .i3 { }
      .i4 { color: #333; }
      .footer { border-top: 1px dashed #000; margin-top: 6px; padding-top: 6px; }
      .external-badge { background: #ff9800; color: white; padding: 2px 6px; border-radius: 3px; font-size: 10px; }
      /* On screen, center the receipt for a visual preview */
      @media screen { body { background: #f5f5f5; } .preview-wrap { width: 70mm; margin: 12px auto; background: #fff; padding: 2mm; box-shadow: 0 0 4px rgba(0,0,0,0.2); } }
      @media print { .preview-wrap { box-shadow: none; padding: 0; } }
    </style>
  </head>
  <body>
    <div class="preview-wrap">
      <div class="logo-container">
        <img src="/logos/ministry-of-health-logo.png" alt="Ministry of Health" class="logo" onerror="this.style.display='none'">
        <img src="/logos/ghana-health-service-logo.png" alt="Ghana Health Service" class="logo" onerror="this.style.display='none'">
      </div>
      <div class="center hospital-name">ASESEWA GOVERNMENT HOSPITAL</div>
      <div class="hdr center">
        <div class="dept-name">EXTERNAL PRESCRIPTION</div>
        <div><span class="external-badge">TO BE FILLED OUTSIDE</span></div>
        <div>${now.toLocaleString()}</div>
      </div>
      <div class="sec">
        ${formatReceiptLine('Encounter ID', selectedEncounterId.value)}
        ${formatReceiptLine('Patient', `${patient.value?.name || ''} ${patient.value?.surname || ''}`.trim())}
        ${formatReceiptLine('Card', patient.value?.card_number || '')}
        ${formatReceiptLine('Insurance', patient.value?.insurance_id || 'N/A')}
        ${formatReceiptLine('CCC', currentEncounter.value?.ccc_number || '')}
        <div class="clearfix"></div>
      </div>
      <div class="sec">
        ${formatReceiptLine('Prescriber', prescriberName)}
        <div class="clearfix"></div>
      </div>
      <div class="sec">
        <div class="center"><strong>Prescribed Medications</strong></div>
        ${itemsHtmlStr || '<div class="center">No prescriptions</div>'}
      </div>
      <div class="footer">
        <div class="center">
          <div class="external-badge">This prescription is to be filled at an external pharmacy</div>
          <div style="margin-top: 6px;">Thank you</div>
        </div>
      </div>
    </div>
  </body>
  </html>`;
};

const printExternalPrescriptions = async () => {
  if (!selectedEncounterId.value || !patient.value) {
    $q.notify({ type: 'warning', message: 'Select encounter first' });
    return;
  }
  
  if (externalPrescriptions.value.length === 0) {
    $q.notify({ type: 'warning', message: 'No external prescriptions found for this encounter' });
    return;
  }
  
  // Ensure staff is loaded
  if (Object.keys(staffMap.value).length === 0) {
    await loadStaff();
  }
  
  const receiptHtml = await buildExternalPrescriptionHtml();
  if (!receiptHtml) return;
  
  const w = window.open('', '_blank', 'width=420,height=800');
  if (!w) return;
  w.document.open();
  w.document.write(receiptHtml);
  w.document.close();
  setTimeout(() => { try { w.focus(); w.print(); } catch(e) {} }, 300);
};
</script>
