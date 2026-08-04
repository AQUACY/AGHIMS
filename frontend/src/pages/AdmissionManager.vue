<template>
  <q-page class="hms-page am-page">
    <HmsPageHeader
      title="Admission manager"
      subtitle="Inpatient clinical workspace for the selected ward admission."
    >
      <template #actions>
        <HmsButton variant="secondary" size="sm" @click="$router.push('/ipd/doctor-nursing-station')">
          Back to ward
        </HmsButton>
      </template>
    </HmsPageHeader>

    <div v-if="patientInfo" class="ipd-patient-hero">
      <div class="ipd-hero-main">
        <div class="ipd-hero-avatar">{{ amPatientInitials(patientInfo) }}</div>
        <div>
          <div style="display:flex;flex-wrap:wrap;align-items:center;gap:0.45rem;">
            <h1 class="ipd-hero-name">{{ amPatientDisplayName(patientInfo) }}</h1>
            <HmsBadge v-if="isInsured" tone="success">Insured</HmsBadge>
            <HmsBadge v-else tone="warning">Cash &amp; carry</HmsBadge>
          </div>
          <div class="ipd-hero-meta">
            <span class="mono">{{ patientInfo.patient_card_number }}</span>
            <span class="sep">·</span>
            <span>{{ patientInfo.patient_gender || '—' }}</span>
            <template v-if="patientInfo.patient_date_of_birth">
              <span class="sep">·</span>
              <span>{{ formatDate(patientInfo.patient_date_of_birth) }}</span>
            </template>
            <span class="sep">·</span>
            <span>{{ patientInfo.ward }}</span>
            <template v-if="patientInfo.bed_number">
              <span class="sep">·</span>
              <span>Bed {{ patientInfo.bed_number }}</span>
            </template>
            <span class="sep">·</span>
            <span>Admitted {{ formatDateTime(patientInfo.admitted_at) }}</span>
          </div>
        </div>
      </div>
      <div class="ipd-hero-actions">
        <button
          v-if="patientBillInfo.totalAmount !== null"
          type="button"
          class="balance-pill"
          :class="patientBillInfo.remainingBalance > 0 ? 'due' : (patientBillInfo.totalAmount > 0 ? 'ok' : 'neutral')"
          @click="openBillItemsDialog"
        >
          <span class="balance-label">Outstanding</span>
          <span class="balance-value">GHC {{ patientBillInfo.remainingBalance.toFixed(2) }}</span>
        </button>
      </div>
    </div>

    <div v-if="patientInfo" class="am-emergency-strip">
      <div class="am-emergency-label">Emergency contact</div>
      <template v-if="patientInfo.emergency_contact_name || patientInfo.emergency_contact_number">
        <span class="am-emergency-value">{{ patientInfo.emergency_contact_name || '—' }}</span>
        <span class="am-emergency-sep">·</span>
        <span class="am-emergency-value">{{ patientInfo.emergency_contact_relationship || '—' }}</span>
        <span class="am-emergency-sep">·</span>
        <a
          v-if="patientInfo.emergency_contact_number"
          :href="`tel:${patientInfo.emergency_contact_number}`"
          class="am-emergency-phone"
        >{{ patientInfo.emergency_contact_number }}</a>
        <span v-else class="am-emergency-value">No phone</span>
      </template>
      <span v-else class="am-emergency-muted">No emergency contact on file</span>
    </div>

    <div v-if="loading" class="am-loading">
      <q-spinner color="primary" size="2.5em" />
      <span>Loading patient information…</span>
    </div>

    <!-- Main Content Layout -->
    <div v-else class="am-workspace">
      <!-- Main Body - Middle Section -->
      <div class="am-main">
        <section class="am-panel">
            <div class="am-panel-head am-panel-head--board">
              <div>
                <h2 class="hms-section-title">Inpatient activities</h2>
                <p class="am-panel-sub">Clinical reviews, notes, surgeries, and services for this admission.</p>
              </div>
              <div class="am-activity-summary">
                <span>{{ activityTotalCount }} records</span>
              </div>
            </div>
            
            <div class="am-activity-board">
              <div class="am-activity-tabs" role="tablist">
                <button
                  v-for="tab in activitySections"
                  :key="tab.key"
                  type="button"
                  role="tab"
                  class="am-activity-tab"
                  :class="{ active: activeActivityTab === tab.key }"
                  :aria-selected="activeActivityTab === tab.key"
                  @click="activeActivityTab = tab.key"
                >
                  <span class="am-activity-tab-label">{{ tab.label }}</span>
                  <span class="am-activity-tab-count">{{ tab.count }}</span>
                </button>
              </div>

              <div class="am-activity-body">
                <div v-if="activeActivityTab === 'diagnoses'" class="am-activity-pane">
                  <div class="am-activity-pane-head">
                    <div>
                      <h3 class="am-activity-pane-title">Diagnoses</h3>
                      <p class="am-activity-pane-sub">IPD and carried-over OPD diagnoses for this admission.</p>
                    </div>
                  </div>
                  <div v-if="inpatientDiagnoses.length === 0" class="am-activity-empty">
                    No diagnoses recorded yet.
                  </div>
                  <div v-else class="am-activity-list">
                    <article
                      v-for="diagnosis in inpatientDiagnoses"
                      :key="diagnosis.id"
                      class="am-activity-item"
                    >
                      <div class="am-activity-item-main">
                        <div class="am-activity-item-title-row">
                          <h4 class="am-activity-item-title">{{ diagnosis.diagnosis }}</h4>
                          <div class="am-activity-item-badges">
                            <HmsBadge v-if="diagnosis.is_chief" tone="accent">Chief</HmsBadge>
                            <HmsBadge v-if="diagnosis.is_provisional" tone="warning">Provisional</HmsBadge>
                            <HmsBadge v-if="diagnosis.source === 'opd'" tone="info">OPD</HmsBadge>
                          </div>
                        </div>
                        <div class="am-activity-item-meta">
                          <span v-if="diagnosis.icd10" class="mono">ICD-10 {{ diagnosis.icd10 }}</span>
                          <span v-if="diagnosis.icd10 && diagnosis.gdrg_code" class="sep">·</span>
                          <span v-if="diagnosis.gdrg_code" class="mono">G-DRG {{ diagnosis.gdrg_code }}</span>
                          <template v-if="diagnosis.diagnosis_status">
                            <span class="sep">·</span>
                            <span>{{ diagnosis.diagnosis_status }}</span>
                          </template>
                        </div>
                        <div class="am-activity-item-foot">
                          Added {{ formatDateTime(diagnosis.created_at) }}
                          <span v-if="diagnosis.created_by_name"> by {{ diagnosis.created_by_name }}</span>
                        </div>
                      </div>
                    </article>
                  </div>
                </div>

                <div v-else-if="activeActivityTab === 'admission_notes'" class="am-activity-pane">
                  <div class="am-activity-pane-head">
                    <div>
                      <h3 class="am-activity-pane-title">Admission notes</h3>
                      <p class="am-activity-pane-sub">Narrative notes captured on ward admission.</p>
                    </div>
                    <HmsButton
                      variant="soft"
                      size="sm"
                      @click="openDocumentationDialog('admission_notes', patientInfo?.admission_notes || null)"
                    >
                      {{ patientInfo?.admission_notes ? 'Edit notes' : 'Add notes' }}
                    </HmsButton>
                  </div>
                  <div v-if="patientInfo?.admission_notes" class="am-note-card">
                    <pre class="am-note-text">{{ patientInfo.admission_notes }}</pre>
                  </div>
                  <div v-else class="am-activity-empty">
                    No admission notes yet.
                    <HmsButton
                      class="am-empty-cta"
                      variant="primary"
                      size="sm"
                      @click="openDocumentationDialog('admission_notes', null)"
                    >
                      Add notes
                    </HmsButton>
                  </div>
                </div>

                <div v-else-if="activeActivityTab === 'surgeries'" class="am-activity-pane">
                  <div class="am-activity-pane-head">
                    <div>
                      <h3 class="am-activity-pane-title">Surgeries</h3>
                      <p class="am-activity-pane-sub">Scheduled and completed theatre cases for this patient.</p>
                    </div>
                    <HmsButton
                      variant="soft"
                      size="sm"
                      :disabled="isDischarged"
                      @click="addOperation"
                    >
                      Add operation
                    </HmsButton>
                  </div>
                  <div v-if="surgeries.length === 0" class="am-activity-empty">
                    No surgeries recorded.
                  </div>
                  <div v-else class="am-activity-list">
                    <article
                      v-for="surgery in surgeries"
                      :key="surgery.id"
                      class="am-activity-item"
                    >
                      <div class="am-activity-item-main">
                        <div class="am-activity-item-title-row">
                          <h4 class="am-activity-item-title">{{ surgery.surgery_name }}</h4>
                          <HmsBadge :tone="surgery.is_completed ? 'success' : 'warning'">
                            {{ surgery.is_completed ? 'Completed' : 'Pending' }}
                          </HmsBadge>
                        </div>
                        <div class="am-activity-item-meta">
                          <span v-if="surgery.surgeon_name">{{ surgery.surgeon_name }}</span>
                          <template v-if="surgery.surgeon_name && surgery.surgery_date"><span class="sep">·</span></template>
                          <span v-if="surgery.surgery_date">{{ formatDateTime(surgery.surgery_date) }}</span>
                        </div>
                        <p v-if="surgery.surgery_notes" class="am-activity-item-note">{{ surgery.surgery_notes }}</p>
                      </div>
                      <div class="am-activity-item-actions">
                        <HmsButton
                          v-if="authStore.userRole === 'Doctor' || authStore.userRole === 'PA' || authStore.userRole === 'Admin'"
                          variant="ghost"
                          size="sm"
                          :disabled="isDischarged && surgery.is_completed"
                          @click="editSurgery(surgery)"
                        >
                          Edit
                        </HmsButton>
                        <HmsButton
                          v-if="authStore.userRole === 'Admin'"
                          variant="ghost"
                          size="sm"
                          :disabled="isDischarged && surgery.is_completed"
                          @click="deleteSurgery(surgery)"
                        >
                          Delete
                        </HmsButton>
                      </div>
                    </article>
                  </div>
                </div>

                <div v-else-if="activeActivityTab === 'clinical_review'" class="am-activity-pane">
                  <div class="am-activity-pane-head">
                    <div>
                      <h3 class="am-activity-pane-title">Clinical reviews</h3>
                      <p class="am-activity-pane-sub">Doctor reviews and treatment plans for this admission.</p>
                    </div>
                    <div class="am-activity-pane-actions">
                      <HmsButton variant="ghost" size="sm" @click="viewTableItems('clinical_review')">View all</HmsButton>
                      <HmsButton variant="soft" size="sm" @click="viewClinicalReview">New review</HmsButton>
                    </div>
                  </div>
                  <div v-if="clinicalReviews.length === 0" class="am-activity-empty">
                    No clinical reviews yet.
                  </div>
                  <div v-else class="am-activity-list">
                    <article
                      v-for="review in clinicalReviews"
                      :key="review.id"
                      class="am-activity-item"
                    >
                      <div class="am-activity-item-main">
                        <div class="am-activity-item-title-row">
                          <h4 class="am-activity-item-title">{{ review.reviewed_by_name || 'Unknown' }}</h4>
                          <span class="am-activity-item-when">{{ formatDateTime(review.reviewed_at) }}</span>
                        </div>
                        <p class="am-activity-item-note">{{ review.review_notes || 'No notes' }}</p>
                      </div>
                      <div class="am-activity-item-actions">
                        <HmsButton
                          v-if="authStore.user?.id === review.reviewed_by || authStore.userRole === 'Admin'"
                          variant="ghost"
                          size="sm"
                          :disabled="isDischarged"
                          @click="editClinicalReview(review)"
                        >
                          Edit
                        </HmsButton>
                        <HmsButton variant="soft" size="sm" @click="openClinicalReview(review.id)">Open</HmsButton>
                        <HmsButton
                          v-if="authStore.userRole === 'Admin'"
                          variant="ghost"
                          size="sm"
                          :disabled="isDischarged"
                          @click="deleteClinicalReview(review)"
                        >
                          Delete
                        </HmsButton>
                      </div>
                    </article>
                  </div>
                </div>

                <div v-else-if="activeActivityTab === 'additional_services'" class="am-activity-pane">
                  <div class="am-activity-pane-head">
                    <div>
                      <h3 class="am-activity-pane-title">Additional services</h3>
                      <p class="am-activity-pane-sub">Timed ward services such as oxygen and monitoring.</p>
                    </div>
                    <HmsButton
                      variant="soft"
                      size="sm"
                      :disabled="isDischarged"
                      @click="addAdditionalService"
                    >
                      Add service
                    </HmsButton>
                  </div>
                  <div v-if="patientAdditionalServices.length === 0" class="am-activity-empty">
                    No additional services recorded.
                  </div>
                  <div v-else class="am-activity-list">
                    <article
                      v-for="service in patientAdditionalServices"
                      :key="service.id"
                      class="am-activity-item"
                    >
                      <div class="am-activity-item-main">
                        <div class="am-activity-item-title-row">
                          <h4 class="am-activity-item-title">{{ service.service_name }}</h4>
                          <div class="am-activity-item-badges">
                            <HmsBadge :tone="service.end_time ? 'success' : 'warning'">
                              {{ service.end_time ? 'Stopped' : 'Active' }}
                            </HmsBadge>
                            <HmsBadge v-if="service.is_billed" tone="info">Billed</HmsBadge>
                          </div>
                        </div>
                        <div class="am-activity-item-meta">
                          <span>Started {{ formatDateTime(service.start_time) }}</span>
                          <span v-if="service.started_by_name"> by {{ service.started_by_name }}</span>
                          <template v-if="service.end_time">
                            <span class="sep">·</span>
                            <span>Stopped {{ formatDateTime(service.end_time) }}</span>
                            <span v-if="service.stopped_by_name"> by {{ service.stopped_by_name }}</span>
                          </template>
                        </div>
                        <div
                          v-if="service.units_used && service.total_cost"
                          class="am-activity-item-cost"
                        >
                          {{ service.units_used }} {{ service.service_unit_type }}(s)
                          × GHC {{ service.service_price_per_unit }}
                          = <strong>GHC {{ service.total_cost }}</strong>
                        </div>
                        <p v-if="service.notes" class="am-activity-item-note">{{ service.notes }}</p>
                      </div>
                      <div class="am-activity-item-actions" v-if="!service.end_time">
                        <HmsButton variant="danger" size="sm" @click="stopAdditionalService(service)">
                          Stop
                        </HmsButton>
                      </div>
                    </article>
                  </div>
                </div>
              </div>
            </div>

        </section>
      </div>

      <aside class="am-sidebar">
        <section class="am-panel am-actions-panel">
          <div class="am-panel-head">
            <h2 class="hms-section-title">Quick actions</h2>
          </div>

          <div class="am-action-group">
            <div class="am-action-label">Patient</div>
            <HmsButton variant="secondary" size="sm" class="am-action-btn" @click="viewPatient">Patient profile</HmsButton>
            <HmsButton variant="secondary" size="sm" class="am-action-btn" @click="viewEncounter">Encounter</HmsButton>
            <HmsButton variant="secondary" size="sm" class="am-action-btn" @click="viewBilling">Billing</HmsButton>
          </div>

          <div class="am-action-group">
            <div class="am-action-label">Clinical</div>
            <HmsButton variant="soft" size="sm" class="am-action-btn" :disabled="isDischarged" @click="addVitals">Vitals</HmsButton>
            <HmsButton variant="soft" size="sm" class="am-action-btn" :disabled="isDischarged" @click="viewPrescriptions">Prescriptions</HmsButton>
            <HmsButton variant="soft" size="sm" class="am-action-btn" :disabled="isDischarged" @click="viewInvestigations">Investigations</HmsButton>
            <HmsButton variant="soft" size="sm" class="am-action-btn" :disabled="isDischarged" @click="addOperation">Add operation</HmsButton>
            <HmsButton variant="soft" size="sm" class="am-action-btn" :disabled="isDischarged" @click="addAdditionalService">Additional service</HmsButton>
            <HmsButton variant="soft" size="sm" class="am-action-btn" :disabled="isDischarged" @click="addInventoryDebit">Inventory debit</HmsButton>
            <HmsButton variant="soft" size="sm" class="am-action-btn" :disabled="isDischarged" @click="requestBlood">Request blood</HmsButton>
          </div>

          <div class="am-action-group">
            <div class="am-action-label">Documentation</div>
            <HmsButton variant="ghost" size="sm" class="am-action-btn" @click="addNurseNote">Nurse note</HmsButton>
            <HmsButton variant="ghost" size="sm" class="am-action-btn" @click="viewNurseMidDocumentation">Nurse mid docs</HmsButton>
            <HmsButton variant="ghost" size="sm" class="am-action-btn" @click="viewClinicalReview">Clinical review</HmsButton>
            <HmsButton variant="ghost" size="sm" class="am-action-btn" @click="viewTreatmentSheet">Treatment sheet</HmsButton>
          </div>

          <div class="am-action-group am-action-group--danger">
            <div class="am-action-label">Discharge</div>
            <HmsButton
              v-if="!isDischarged"
              variant="danger"
              size="sm"
              class="am-action-btn"
              :loading="discharging"
              @click="dischargePatient"
            >
              {{ isPartiallyDischarged ? 'Final discharge' : 'Discharge patient' }}
            </HmsButton>
            <div v-if="isPartiallyDischarged && !isDischarged" class="am-partial-banner">
              Partially discharged — settle outstanding bills before final discharge.
            </div>
            <HmsButton
              v-if="isPartiallyDischarged && !isDischarged"
              variant="secondary"
              size="sm"
              class="am-action-btn"
              :loading="discharging"
              @click="revertPartialDischarge"
            >
              Revert partial discharge
            </HmsButton>
            <HmsButton
              v-if="!isDischarged"
              variant="outline"
              size="sm"
              class="am-action-btn"
              :loading="cancelling"
              @click="cancelAdmission"
            >
              Cancel admission
            </HmsButton>
            <div v-if="isDischarged" class="am-discharged-banner">
              Patient discharged — this record is read-only.
            </div>
          </div>
        </section>
      </aside>
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
                <!-- Draft Banner for Documentation -->
                <q-banner
                  v-if="hasDocumentationDraft(currentDocumentationType) && admissionNotes !== (getDocumentationDraftValue(currentDocumentationType) || '')"
                  class="bg-warning text-dark q-mb-md"
                  rounded
                >
                  <template v-slot:avatar>
                    <q-icon name="save" color="dark" />
                  </template>
                  <strong>Draft Available</strong>
                  <div class="text-caption q-mt-xs">
                    A draft was saved {{ formatDraftTime(getDocumentationDraftTime(currentDocumentationType)) }}. 
                    Would you like to restore it?
                  </div>
                  <template v-slot:action>
                    <q-btn
                      flat
                      label="Restore Draft"
                      color="dark"
                      @click="restoreDocumentationDraft(currentDocumentationType)"
                    />
                    <q-btn
                      flat
                      label="Discard"
                      color="dark"
                      @click="clearDocumentationDraft(currentDocumentationType); $q.notify({ type: 'info', message: 'Draft discarded', position: 'top', timeout: 2000 })"
                    />
                  </template>
                </q-banner>
                
                <q-input
                  v-model="admissionNotes"
                  filled
                  type="textarea"
                  label="Notes"
                  :hint="`Enter ${documentationTypeLabels[currentDocumentationType]?.toLowerCase() || 'notes'} for this patient (auto-saved as draft)`"
                  rows="10"
                  autofocus
                  @update:model-value="() => currentDocumentationType && autoSaveDocumentationDraft(currentDocumentationType)"
                />
              </q-card-section>

              <q-card-actions align="right">
                <q-btn 
                  flat 
                  label="Cancel" 
                  color="primary" 
                  @click="cancelDocumentationDialog" 
                />
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
              <q-card-section class="q-pb-none nn-dialog-head">
                <div class="text-h6 glass-text">
                  <template v-if="currentTableType === 'nurses_notes'">Nurse note</template>
                  <template v-else>Add {{ documentationTypeLabels[currentTableType] || 'Item' }}</template>
                </div>
                <p v-if="currentTableType === 'nurses_notes'" class="nn-dialog-sub">
                  Record dated ward observations for this admission.
                </p>
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
                <div v-else-if="currentTableType === 'nurses_notes'" class="nn-workspace">
                  <div class="nn-hero">
                    <div class="nn-hero-kicker">Ghana Health Service</div>
                    <h3 class="nn-hero-title">Nurse note</h3>
                    <p class="nn-hero-sub">Use red text for night notes. A nurse signature accompanies each entry.</p>
                  </div>

                  <div
                    v-if="(
                      (hasNurseNoteDraft('note_date') && tableItemData.note_date !== (getNurseNoteDraftValue('note_date') || '')) ||
                      (hasNurseNoteDraft('note_hour') && tableItemData.note_hour !== (getNurseNoteDraftValue('note_hour') || '')) ||
                      (hasNurseNoteDraft('notes') && tableItemData.notes !== (getNurseNoteDraftValue('notes') || ''))
                    )"
                    class="nn-draft"
                  >
                    <div>
                      <strong>Draft available</strong>
                      <div class="nn-draft-sub">
                        Saved
                        <span v-if="getNurseNoteDraftTime('notes')">{{ formatDraftTime(getNurseNoteDraftTime('notes')) }}</span>
                        <span v-else-if="getNurseNoteDraftTime('note_date')">{{ formatDraftTime(getNurseNoteDraftTime('note_date')) }}</span>
                        <span v-else-if="getNurseNoteDraftTime('note_hour')">{{ formatDraftTime(getNurseNoteDraftTime('note_hour')) }}</span>
                      </div>
                    </div>
                    <div class="nn-draft-actions">
                      <HmsButton
                        variant="secondary"
                        size="sm"
                        @click="restoreNurseNoteDraft('note_date'); restoreNurseNoteDraft('note_hour'); restoreNurseNoteDraft('notes')"
                      >
                        Restore
                      </HmsButton>
                      <HmsButton
                        variant="ghost"
                        size="sm"
                        @click="clearAllNurseNoteDrafts(); $q.notify({ type: 'info', message: 'Draft discarded', position: 'top', timeout: 2000 })"
                      >
                        Discard
                      </HmsButton>
                    </div>
                  </div>

                  <div class="nn-form-grid">
                    <q-input
                      v-model="tableItemData.note_date"
                      outlined
                      dense
                      type="date"
                      label="Date *"
                      :rules="[val => !!val || 'Date is required']"
                      @update:model-value="() => currentTableType === 'nurses_notes' && autoSaveNurseNoteDraft('note_date')"
                    />
                    <q-input
                      v-model="tableItemData.note_hour"
                      outlined
                      dense
                      type="time"
                      label="Hour *"
                      :rules="[val => !!val || 'Hour is required']"
                      @update:model-value="() => currentTableType === 'nurses_notes' && autoSaveNurseNoteDraft('note_hour')"
                    />
                  </div>

                  <div class="nn-toolbar">
                    <div class="nn-toolbar-label">Text color</div>
                    <q-btn
                      flat
                      dense
                      icon="format_color_text"
                      :style="`background-color: ${selectedTextColor}; color: ${getContrastColor(selectedTextColor)}; min-width: 42px;`"
                      size="sm"
                    >
                      <q-popup-proxy>
                        <q-color v-model="selectedTextColor" format-model="hex" />
                      </q-popup-proxy>
                    </q-btn>
                    <HmsButton variant="soft" size="sm" @click="applyTextColor">Apply color</HmsButton>
                    <span class="nn-toolbar-hint">Tip: red for night shift</span>
                  </div>

                  <q-editor
                    ref="nurseNoteEditor"
                    v-model="tableItemData.notes"
                    class="nn-editor"
                    :toolbar="[
                      ['bold', 'italic', 'strike', 'underline'],
                      ['left', 'center', 'right', 'justify'],
                      ['quote', 'unordered', 'ordered'],
                      ['undo', 'redo'],
                      ['viewsource']
                    ]"
                    min-height="180px"
                    :rules="[val => !!val || 'Notes are required']"
                    @update:model-value="() => currentTableType === 'nurses_notes' && autoSaveNurseNoteDraft('notes')"
                  />

                  <div class="nn-history">
                    <div class="nn-history-head">
                      <h4 class="nn-history-title">Previous notes</h4>
                      <span class="nn-history-count">{{ nurseNotes.length }}</span>
                    </div>
                    <div class="nn-history-list">
                      <article
                        v-for="note in nurseNotes"
                        :key="note.id"
                        class="nn-note-card"
                        :class="{ struck: note.strikethrough === 1 }"
                      >
                        <div
                          class="nn-note-body"
                          :class="getNoteClass(note)"
                          :style="getNoteStyle(note)"
                          v-html="processNoteHtml(note)"
                        />
                        <div class="nn-note-meta">
                          <span>{{ note.created_by_name || 'Unknown' }}</span>
                          <span class="sep">·</span>
                          <span>{{ formatDateTime(note.created_at) }}</span>
                          <template v-if="note.strikethrough === 1 && note.strikethrough_by_name">
                            <span class="sep">·</span>
                            <span>Struck by {{ note.strikethrough_by_name }}</span>
                          </template>
                        </div>
                        <div class="nn-note-actions" v-if="canStrikethroughNote(note)">
                          <HmsButton
                            variant="ghost"
                            size="sm"
                            @click="toggleStrikethrough(note)"
                          >
                            {{ note.strikethrough === 1 ? 'Restore' : 'Strikethrough' }}
                          </HmsButton>
                        </div>
                      </article>
                      <div v-if="nurseNotes.length === 0" class="nn-history-empty">
                        No previous nurse notes.
                      </div>
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
                <q-btn flat label="Cancel" color="primary" @click="cancelTableItemDialog" />
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

                <q-banner v-if="hasUnpaidBills && isPartiallyDischarged && !isDiedOrAbsconded" class="q-mt-md bg-negative text-white">
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
                  :disable="hasUnpaidBills && !isDiedOrAbsconded"
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
                    
                    <!-- Template-based Results (Lab with template) -->
                    <LabResultViewer
                      v-if="currentResult.template_id && currentResult.template_data && labResultTemplate && investigationDetails.investigation_type === 'lab'"
                      :template-structure="labResultTemplate.template_structure"
                      :template-data="typeof currentResult.template_data === 'string' ? JSON.parse(currentResult.template_data) : currentResult.template_data"
                      :results-text="currentResult.results_text"
                      :patient-info="patientInfo"
                      :procedure-name="investigationDetails?.procedure_name || ''"
                      :template-name="labResultTemplate?.template_name || ''"
                      :result-date="currentResult.created_at"
                      :entered-by="currentResult.entered_by_name"
                      :entered-at="currentResult.created_at"
                    />
                    
                    <!-- Non-template Results -->
                    <div v-else>
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
                    </div>

                    <!-- Attachments -->
                    <div v-if="parsedAttachments && parsedAttachments.length > 0" class="q-mt-md">
                      <q-separator class="q-my-md" />
                      <div class="text-subtitle2 q-mb-sm glass-text">
                        <q-icon name="attach_file" class="q-mr-xs" />
                        Attachment{{ parsedAttachments.length > 1 ? 's' : '' }} ({{ parsedAttachments.length }})
                      </div>
                      <div v-for="(attachmentPath, index) in parsedAttachments" :key="index" class="row items-center q-gutter-md q-mb-md" style="background-color: rgba(255, 255, 255, 0.05); border-radius: 4px; padding: 12px;">
                        <div class="col-auto">
                          <q-icon name="description" size="32px" color="primary" />
                        </div>
                        <div class="col">
                          <div class="text-body2 text-weight-medium">
                            {{ attachmentPath.split('/').pop() || `Attachment ${index + 1}` }}
                          </div>
                          <div class="text-caption text-grey-7">
                            Click to view the attached file
                          </div>
                        </div>
                        <div class="col-auto">
                          <q-btn
                            icon="visibility"
                            label="View"
                            color="primary"
                            outline
                            size="sm"
                            @click="viewResultAttachment(investigationDetails, attachmentPath)"
                          />
                        </div>
                      </div>
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

          <!-- Bill Items Dialog -->
          <q-dialog v-model="showBillItemsDialog" maximized>
            <q-card>
              <q-card-section class="row items-center q-pb-none">
                <div class="text-h6">Bill Items - {{ patientInfo?.patient_name }} {{ patientInfo?.patient_surname || '' }}</div>
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
import { ref, onMounted, computed, watch, nextTick } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { useQuasar } from 'quasar';
import HmsPageHeader from '../components/ui/HmsPageHeader.vue';
import HmsButton from '../components/ui/HmsButton.vue';
import HmsBadge from '../components/ui/HmsBadge.vue';
import { consultationAPI, priceListAPI, billingAPI, labTemplatesAPI, encountersAPI } from '../services/api';
import LabResultViewer from '../components/LabResultViewer.vue';
import { useAuthStore } from '../stores/auth';

const $q = useQuasar();
const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();

const amPatientInitials = (info) => {
  if (!info) return '?';
  const a = (info.patient_name || '').trim().charAt(0);
  const b = (info.patient_surname || '').trim().charAt(0);
  return ((a + b) || '?').toUpperCase();
};
const amPatientDisplayName = (info) => {
  if (!info) return '';
  return [info.patient_name, info.patient_surname, info.patient_other_names].filter(Boolean).join(' ');
};

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
const isDiedOrAbsconded = computed(() => {
  return dischargeForm.value.discharge_outcome === 'died' || 
         dischargeForm.value.discharge_outcome === 'absconded' ||
         dischargeForm.value.discharge_condition === 'died' || 
         dischargeForm.value.discharge_condition === 'absconded';
});
const patientBillInfo = ref({
  totalAmount: null,
  paidAmount: null,
  remainingBalance: null,
});
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

// Auto-save draft functionality for nurse notes
const draftSaveTimers = ref({});
const DRAFT_SAVE_DELAY = 2000; // Save after 2 seconds of no typing

// Get draft storage key
const getNurseNoteDraftKey = (field) => {
  const admissionId = wardAdmissionId.value;
  if (!admissionId) return null;
  return `nurse_note_draft_${admissionId}_${field}`;
};

// Auto-save draft (debounced)
const autoSaveNurseNoteDraft = (field) => {
  const admissionId = wardAdmissionId.value;
  if (!admissionId) {
    console.warn('No ward admission ID for draft save');
    return;
  }
  
  // Clear existing timer
  if (draftSaveTimers.value[field]) {
    clearTimeout(draftSaveTimers.value[field]);
  }
  
  // Set new timer
  draftSaveTimers.value[field] = setTimeout(() => {
    const key = getNurseNoteDraftKey(field);
    if (!key) {
      console.warn(`No draft key for field: ${field}`);
      return;
    }
    
    const value = tableItemData.value[field] || '';
    if (value && value.toString().trim()) {
      const draftData = {
        value: value,
        timestamp: Date.now(),
        admissionId: admissionId
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
const hasNurseNoteDraft = (field) => {
  const key = getNurseNoteDraftKey(field);
  if (!key) return false;
  const draft = localStorage.getItem(key);
  if (!draft) return false;
  
  try {
    const draftData = JSON.parse(draft);
    // Check if draft is for current admission
    return draftData.admissionId === wardAdmissionId.value;
  } catch {
    return false;
  }
};

// Get draft time
const getNurseNoteDraftTime = (field) => {
  const key = getNurseNoteDraftKey(field);
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
const getNurseNoteDraftValue = (field) => {
  const key = getNurseNoteDraftKey(field);
  if (!key) return null;
  const draft = localStorage.getItem(key);
  if (!draft) return null;
  
  try {
    const draftData = JSON.parse(draft);
    if (draftData.admissionId === wardAdmissionId.value) {
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
const restoreNurseNoteDraft = (field) => {
  const key = getNurseNoteDraftKey(field);
  if (!key) return;
  
  const draft = localStorage.getItem(key);
  if (!draft) return;
  
  try {
    const draftData = JSON.parse(draft);
    if (draftData.value) {
      tableItemData.value[field] = draftData.value;
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
const clearNurseNoteDraft = (field) => {
  const key = getNurseNoteDraftKey(field);
  if (key) {
    localStorage.removeItem(key);
  }
};

// Clear all nurse note drafts
const clearAllNurseNoteDrafts = () => {
  clearNurseNoteDraft('note_date');
  clearNurseNoteDraft('note_hour');
  clearNurseNoteDraft('notes');
};

// Auto-save draft functionality for documentation (doctor's notes, etc.)
const documentationDraftSaveTimers = ref({});
const DOCUMENTATION_DRAFT_SAVE_DELAY = 2000; // Save after 2 seconds of no typing

// Get draft storage key for documentation
const getDocumentationDraftKey = (type) => {
  const admissionId = wardAdmissionId.value;
  if (!admissionId || !type) return null;
  return `documentation_draft_${admissionId}_${type}`;
};

// Auto-save draft for documentation (debounced)
const autoSaveDocumentationDraft = (type) => {
  const admissionId = wardAdmissionId.value;
  if (!admissionId || !type) {
    console.warn('No ward admission ID or type for draft save');
    return;
  }
  
  // Clear existing timer
  if (documentationDraftSaveTimers.value[type]) {
    clearTimeout(documentationDraftSaveTimers.value[type]);
  }
  
  // Set new timer
  documentationDraftSaveTimers.value[type] = setTimeout(() => {
    const key = getDocumentationDraftKey(type);
    if (!key) {
      console.warn(`No draft key for type: ${type}`);
      return;
    }
    
    const value = admissionNotes.value || '';
    if (value && value.toString().trim()) {
      const draftData = {
        value: value,
        timestamp: Date.now(),
        admissionId: admissionId,
        type: type
      };
      localStorage.setItem(key, JSON.stringify(draftData));
      console.log(`Draft saved for ${type}:`, draftData);
    } else {
      // Remove draft if empty
      localStorage.removeItem(key);
    }
  }, DOCUMENTATION_DRAFT_SAVE_DELAY);
};

// Check if draft exists for documentation
const hasDocumentationDraft = (type) => {
  const key = getDocumentationDraftKey(type);
  if (!key) return false;
  const draft = localStorage.getItem(key);
  if (!draft) return false;
  
  try {
    const draftData = JSON.parse(draft);
    // Check if draft is for current admission and type
    return draftData.admissionId === wardAdmissionId.value && draftData.type === type;
  } catch {
    return false;
  }
};

// Get draft time for documentation
const getDocumentationDraftTime = (type) => {
  const key = getDocumentationDraftKey(type);
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

// Get draft value for documentation
const getDocumentationDraftValue = (type) => {
  const key = getDocumentationDraftKey(type);
  if (!key) return null;
  const draft = localStorage.getItem(key);
  if (!draft) return null;
  
  try {
    const draftData = JSON.parse(draft);
    if (draftData.admissionId === wardAdmissionId.value && draftData.type === type) {
      return draftData.value;
    }
    return null;
  } catch {
    return null;
  }
};

// Restore draft for documentation
const restoreDocumentationDraft = (type) => {
  const key = getDocumentationDraftKey(type);
  if (!key) return;
  
  const draft = localStorage.getItem(key);
  if (!draft) return;
  
  try {
    const draftData = JSON.parse(draft);
    if (draftData.value) {
      admissionNotes.value = draftData.value;
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

// Clear draft for documentation
const clearDocumentationDraft = (type) => {
  const key = getDocumentationDraftKey(type);
  if (key) {
    localStorage.removeItem(key);
  }
};

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


const activeActivityTab = ref('diagnoses');

const activitySections = computed(() => [
  { key: 'diagnoses', label: 'Diagnoses', count: inpatientDiagnoses.value.length },
  {
    key: 'admission_notes',
    label: 'Notes',
    count: patientInfo.value?.admission_notes ? 1 : 0,
  },
  { key: 'surgeries', label: 'Surgeries', count: surgeries.value.length },
  { key: 'clinical_review', label: 'Reviews', count: clinicalReviews.value.length },
  { key: 'additional_services', label: 'Services', count: patientAdditionalServices.value.length },
]);

const activityTotalCount = computed(() =>
  activitySections.value.reduce((sum, tab) => sum + (tab.count || 0), 0)
);

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

// Check if admission is insured (has CCC number)
const isInsured = computed(() => {
  if (!patientInfo.value) return false;
  // Check encounter_ccc_number from the encounter
  const cccNumber = patientInfo.value.encounter_ccc_number || null;
  return cccNumber && cccNumber.trim() !== '';
});

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

const openBillItemsDialog = async () => {
  if (!patientInfo.value || !patientInfo.value.encounter_id) {
    $q.notify({ type: 'warning', message: 'No patient information available', position: 'top' });
    return;
  }
  
  showBillItemsDialog.value = true;
  loadingBillItems.value = true;
  allBillItems.value = [];
  
  try {
    // For IPD, show only bill items for the specific ward admission encounter
    // The amount shown (e.g., GHC 120.00) is calculated from this specific encounter's bills
    const wardAdmissionEncounterId = patientInfo.value.encounter_id;
    
    // Load bills and bill items only for this specific encounter
    const billItemsList = [];
    
    try {
      const billsResponse = await billingAPI.getEncounterBills(wardAdmissionEncounterId);
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
              encounter_id: wardAdmissionEncounterId,
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
      console.error(`Failed to load bills for encounter ${wardAdmissionEncounterId}:`, error);
    }
    
    // Sort by item name
    billItemsList.sort((a, b) => {
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
const labResultTemplate = ref(null);

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
      
      // Load lab result template if this is a template-based lab result
      if (investigation.investigation_type === 'lab' && currentResult.value.template_id && currentResult.value.template_data) {
        try {
          const templateResponse = await labTemplatesAPI.get(currentResult.value.template_id);
          labResultTemplate.value = templateResponse.data;
        } catch (templateError) {
          console.error('Failed to load lab result template:', templateError);
          labResultTemplate.value = null;
        }
      } else {
        labResultTemplate.value = null;
      }
      
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

// Parse attachment_path to handle both single string and JSON array
const parsedAttachments = computed(() => {
  if (!currentResult.value?.attachment_path) {
    return [];
  }
  
  try {
    // Try to parse as JSON array
    const parsed = JSON.parse(currentResult.value.attachment_path);
    if (Array.isArray(parsed)) {
      return parsed;
    }
    // If not an array, treat as single string
    return [currentResult.value.attachment_path];
  } catch (e) {
    // If parsing fails, treat as single string
    return [currentResult.value.attachment_path];
  }
});

const viewResultAttachment = async (investigation, attachmentPath = null) => {
  if (!investigation || !currentResult.value?.attachment_path) {
    $q.notify({
      type: 'warning',
      message: 'No attachment available to view',
      position: 'top',
    });
    return;
  }

  try {
    let viewResponse = null;
    if (investigation.investigation_type === 'lab') {
      // Lab results only have a single attachment
      viewResponse = await consultationAPI.downloadLabResultAttachment(investigation.id, true);
    } else if (investigation.investigation_type === 'scan') {
      // For scan, pass the specific attachment path if provided
      viewResponse = await consultationAPI.downloadScanResultAttachment(investigation.id, attachmentPath, true);
    } else if (investigation.investigation_type === 'xray') {
      // For xray, pass the specific attachment path if provided
      viewResponse = await consultationAPI.downloadXrayResultAttachment(investigation.id, attachmentPath, true);
    } else {
      $q.notify({
        type: 'warning',
        message: 'Unknown investigation type',
        position: 'top',
      });
      return;
    }
    
    if (viewResponse && viewResponse.data) {
      // Handle blob response
      const blob = viewResponse.data instanceof Blob 
        ? viewResponse.data 
        : new Blob([viewResponse.data], { 
            type: viewResponse.headers?.['content-type'] || 
                  viewResponse.headers?.['Content-Type'] || 
                  'application/pdf' 
          });
      
      const url = window.URL.createObjectURL(blob);
      window.open(url, '_blank');
      
      // Cleanup after a delay
      setTimeout(() => {
        window.URL.revokeObjectURL(url);
      }, 1000);
    } else {
      throw new Error('No data received from server');
    }
  } catch (error) {
    console.error('Error viewing attachment:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to view attachment',
      position: 'top',
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

  // Check if patient died or absconded - skip bill check for these cases
  const isDiedOrAbsconded = 
    dischargeForm.value.discharge_outcome === 'died' || 
    dischargeForm.value.discharge_outcome === 'absconded' ||
    dischargeForm.value.discharge_condition === 'died' || 
    dischargeForm.value.discharge_condition === 'absconded';

  // Check bills again before final discharge (skip for died/absconded)
  if (!isDiedOrAbsconded) {
    await checkBills();
    
    if (hasUnpaidBills.value) {
      $q.notify({
        type: 'negative',
        message: `Cannot discharge patient. Outstanding bills amount to GHC ${unpaidBillAmount.value.toFixed(2)}. All bills must be paid before discharge.`,
        timeout: 5000,
      });
      return;
    }
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

const cancelDocumentationDialog = () => {
  // Clear any pending draft save timers
  Object.keys(documentationDraftSaveTimers.value).forEach(type => {
    if (documentationDraftSaveTimers.value[type]) {
      clearTimeout(documentationDraftSaveTimers.value[type]);
    }
  });
  documentationDraftSaveTimers.value = {};
  
  // Close dialog
  showAdmissionNotesDialog.value = false;
};

const openDocumentationDialog = (type, currentValue) => {
  currentDocumentationType.value = type;
  // Don't auto-restore drafts - let user choose via banner
  admissionNotes.value = currentValue || '';
  showAdmissionNotesDialog.value = true;
};

const saveDocumentation = async () => {
  if (!wardAdmissionId.value || !currentDocumentationType.value) return;
  
  savingNotes.value = true;
  try {
    await consultationAPI.updateAdmissionNotes(wardAdmissionId.value, admissionNotes.value);
    
    // Clear draft after successful save
    clearDocumentationDraft(currentDocumentationType.value);
    
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
      // Initialize with current date and time (don't auto-restore drafts - let user choose)
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

const cancelTableItemDialog = (event) => {
  // Prevent any default behavior
  if (event) {
    event.preventDefault();
    event.stopPropagation();
  }
  
  // Don't allow canceling while saving
  if (savingTableItem.value) {
    return;
  }
  
  // Clear any pending draft save timers
  Object.keys(draftSaveTimers.value).forEach(field => {
    if (draftSaveTimers.value[field]) {
      clearTimeout(draftSaveTimers.value[field]);
    }
  });
  draftSaveTimers.value = {};
  
  // Reset form data
  tableItemData.value = {};
  currentTableType.value = '';
  editingClinicalReviewId.value = null;
  editingVitalId.value = null;
  
  // Reset color pickers for nurse notes
  selectedTextColor.value = '#000000';
  selectedBgColor.value = '#FFFFFF';
  
  // Close dialog
  showTableItemDialog.value = false;
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
    
    // Clear drafts after successful save (only for nurse notes)
    if (currentTableType.value === 'nurses_notes') {
      clearAllNurseNoteDrafts();
    }
    
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
  if (isDischarged.value && surgery.is_completed) {
    $q.notify({
      type: 'negative',
      message: 'Cannot edit completed surgeries for a discharged patient',
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
.nn-dialog-sub {
  margin: 0.25rem 0 0;
  font-size: var(--hms-text-sm);
  color: var(--hms-text-muted);
}
.nn-workspace { display: flex; flex-direction: column; gap: 0.85rem; }
.nn-hero {
  padding: 0.85rem 1rem;
  border-radius: var(--hms-radius-lg);
  background: var(--hms-surface);
  border: 1px solid var(--hms-border);
}
.nn-hero-kicker {
  font-size: 0.65rem;
  font-weight: 750;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--hms-text-muted);
}
.nn-hero-title {
  margin: 0.2rem 0 0;
  font-size: var(--hms-text-lg);
  font-weight: 750;
  color: var(--hms-text-primary);
}
.nn-hero-sub {
  margin: 0.25rem 0 0;
  font-size: var(--hms-text-sm);
  color: var(--hms-text-secondary);
}
.nn-draft {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.65rem;
  padding: 0.7rem 0.85rem;
  border-radius: var(--hms-radius-md);
  background: var(--hms-warning-muted);
  border: 1px solid rgba(245, 158, 11, 0.28);
  color: #92400e;
}
.nn-draft-sub { margin-top: 0.15rem; font-size: 0.75rem; opacity: 0.9; }
.nn-draft-actions { display: flex; gap: 0.35rem; }
.nn-form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.65rem;
}
.nn-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.45rem;
}
.nn-toolbar-label {
  font-size: 0.72rem;
  font-weight: 750;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--hms-text-muted);
}
.nn-toolbar-hint {
  font-size: var(--hms-text-xs);
  color: var(--hms-text-muted);
  margin-left: auto;
}
.nn-editor {
  border-radius: var(--hms-radius-lg) !important;
  border: 1px solid var(--hms-border) !important;
}
.nn-history-head {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  margin-bottom: 0.55rem;
}
.nn-history-title {
  margin: 0;
  font-size: var(--hms-text-sm);
  font-weight: 750;
  color: var(--hms-text-primary);
}
.nn-history-count {
  min-width: 1.35rem;
  height: 1.35rem;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 0.68rem;
  font-weight: 750;
  background: var(--hms-accent-muted);
  color: var(--hms-accent);
}
.nn-history-list {
  max-height: 280px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.nn-note-card {
  padding: 0.75rem 0.85rem;
  border-radius: var(--hms-radius-md);
  border: 1px solid var(--hms-border);
  background: var(--hms-surface);
}
.nn-note-card.struck { opacity: 0.7; }
.nn-note-body { font-size: var(--hms-text-sm); color: var(--hms-text-primary); }
.nn-note-meta {
  margin-top: 0.4rem;
  font-size: 0.72rem;
  color: var(--hms-text-muted);
  display: flex;
  flex-wrap: wrap;
  align-items: center;
}
.nn-note-meta .sep { margin: 0 0.3rem; opacity: 0.45; }
.nn-note-actions { margin-top: 0.35rem; }
.nn-history-empty {
  padding: 1.25rem;
  text-align: center;
  color: var(--hms-text-muted);
  font-size: var(--hms-text-sm);
  border: 1px dashed var(--hms-border);
  border-radius: var(--hms-radius-md);
}
@media (max-width: 640px) {
  .nn-form-grid { grid-template-columns: 1fr; }
  .nn-toolbar-hint { margin-left: 0; width: 100%; }
}

.am-panel-head--board {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: space-between;
  gap: 0.75rem;
}
.am-activity-summary {
  font-size: var(--hms-text-sm);
  font-weight: 650;
  color: var(--hms-text-muted);
  font-variant-numeric: tabular-nums;
}
.am-activity-board {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}
.am-activity-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  padding: 0.3rem;
  border-radius: var(--hms-radius-lg);
  background: var(--hms-surface);
  border: 1px solid var(--hms-border);
}
.am-activity-tab {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  border: none;
  background: transparent;
  color: var(--hms-text-secondary);
  font-family: inherit;
  font-size: var(--hms-text-sm);
  font-weight: 650;
  padding: 0.45rem 0.7rem;
  border-radius: var(--hms-radius-md);
  cursor: pointer;
  transition: background var(--hms-duration-fast) var(--hms-ease-out), color var(--hms-duration-fast) var(--hms-ease-out);
}
.am-activity-tab:hover {
  background: var(--hms-panel-bg);
  color: var(--hms-text-primary);
}
.am-activity-tab.active {
  background: var(--hms-panel-bg);
  color: var(--hms-accent);
  box-shadow: var(--hms-shadow-sm);
}
.am-activity-tab-count {
  min-width: 1.35rem;
  height: 1.35rem;
  padding: 0 0.35rem;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 0.68rem;
  font-weight: 750;
  background: var(--hms-accent-muted);
  color: var(--hms-accent);
}
.am-activity-tab:not(.active) .am-activity-tab-count {
  background: rgba(148, 163, 184, 0.18);
  color: var(--hms-text-muted);
}
.am-activity-body {
  min-height: 280px;
}
.am-activity-pane-head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.85rem;
}
.am-activity-pane-title {
  margin: 0;
  font-size: var(--hms-text-md);
  font-weight: 750;
  color: var(--hms-text-primary);
  letter-spacing: -0.01em;
}
.am-activity-pane-sub {
  margin: 0.2rem 0 0;
  font-size: var(--hms-text-sm);
  color: var(--hms-text-muted);
}
.am-activity-pane-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}
.am-activity-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  padding: 2.5rem 1rem;
  text-align: center;
  color: var(--hms-text-muted);
  font-size: var(--hms-text-sm);
  border: 1px dashed var(--hms-border);
  border-radius: var(--hms-radius-lg);
  background: var(--hms-surface);
}
.am-empty-cta { margin-top: 0.15rem; }
.am-activity-list {
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
}
.am-activity-item {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.9rem 1rem;
  border-radius: var(--hms-radius-lg);
  background: var(--hms-surface);
  border: 1px solid var(--hms-border);
  transition: border-color var(--hms-duration-fast) var(--hms-ease-out), box-shadow var(--hms-duration-fast) var(--hms-ease-out);
}
.am-activity-item:hover {
  border-color: var(--hms-border-strong, var(--hms-border));
  box-shadow: var(--hms-shadow-sm);
}
.am-activity-item-main { flex: 1; min-width: 200px; }
.am-activity-item-title-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.45rem 0.65rem;
}
.am-activity-item-title {
  margin: 0;
  font-size: var(--hms-text-sm);
  font-weight: 750;
  color: var(--hms-text-primary);
}
.am-activity-item-badges {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 0.3rem;
}
.am-activity-item-when {
  font-size: 0.72rem;
  font-weight: 650;
  color: var(--hms-text-muted);
}
.am-activity-item-meta {
  margin-top: 0.3rem;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.15rem;
  font-size: var(--hms-text-sm);
  color: var(--hms-text-secondary);
}
.am-activity-item-meta .sep { margin: 0 0.3rem; opacity: 0.4; }
.am-activity-item-meta .mono,
.mono {
  font-variant-numeric: tabular-nums;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.92em;
}
.am-activity-item-foot {
  margin-top: 0.35rem;
  font-size: 0.72rem;
  color: var(--hms-text-muted);
}
.am-activity-item-note {
  margin: 0.45rem 0 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: var(--hms-text-sm);
  color: var(--hms-text-secondary);
  line-height: 1.45;
}
.am-activity-item-cost {
  margin-top: 0.4rem;
  font-size: var(--hms-text-sm);
  color: var(--hms-text-primary);
  font-variant-numeric: tabular-nums;
}
.am-activity-item-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  flex-shrink: 0;
}
.am-note-card {
  padding: 1rem 1.1rem;
  border-radius: var(--hms-radius-lg);
  background: var(--hms-surface);
  border: 1px solid var(--hms-border);
}
.am-note-text {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
  font-size: var(--hms-text-sm);
  line-height: 1.55;
  color: var(--hms-text-primary);
}
@media (max-width: 720px) {
  .am-activity-tabs { gap: 0.25rem; }
  .am-activity-tab { flex: 1 1 auto; justify-content: space-between; }
}


.am-emergency-strip {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.35rem 0.55rem;
  margin: -0.35rem 0 0.95rem;
  padding: 0.65rem 1rem;
  border-radius: var(--hms-radius-lg);
  background: var(--hms-surface);
  border: 1px solid var(--hms-border);
  font-size: var(--hms-text-sm);
}
.am-emergency-label {
  font-size: 0.65rem;
  font-weight: 750;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--hms-text-muted);
  margin-right: 0.35rem;
}
.am-emergency-value { color: var(--hms-text-secondary); font-weight: 600; }
.am-emergency-sep { opacity: 0.4; color: var(--hms-text-muted); }
.am-emergency-phone {
  color: var(--hms-accent);
  font-weight: 700;
  text-decoration: none;
}
.am-emergency-phone:hover { text-decoration: underline; }
.am-emergency-muted { color: var(--hms-text-muted); }
.am-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
  padding: 3rem 1rem;
  color: var(--hms-text-secondary);
  font-size: var(--hms-text-sm);
}
.am-workspace {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(240px, 280px);
  gap: 0.95rem;
  align-items: start;
}
.am-panel {
  padding: 1.05rem 1.15rem;
  border-radius: var(--hms-radius-xl);
  background: var(--hms-panel-bg);
  border: 1px solid var(--hms-border);
  box-shadow: var(--hms-shadow-md);
}
.am-panel-head { margin-bottom: 0.85rem; }
.am-panel-sub {
  margin: 0.2rem 0 0;
  font-size: var(--hms-text-sm);
  color: var(--hms-text-muted);
}
.am-sidebar { position: sticky; top: 5.5rem; }
.am-actions-panel { padding-bottom: 0.85rem; }
.am-action-group {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  padding: 0.75rem 0;
  border-top: 1px solid var(--hms-border);
}
.am-action-group:first-of-type { border-top: none; padding-top: 0; }
.am-action-label {
  font-size: 0.65rem;
  font-weight: 750;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--hms-text-muted);
  margin-bottom: 0.15rem;
}
.am-action-btn { width: 100%; justify-content: flex-start; }
.am-partial-banner,
.am-discharged-banner {
  margin-top: 0.25rem;
  padding: 0.55rem 0.65rem;
  border-radius: var(--hms-radius-md);
  font-size: var(--hms-text-xs);
  line-height: 1.4;
  font-weight: 600;
}
.am-partial-banner {
  background: var(--hms-warning-muted);
  color: #b45309;
  border: 1px solid rgba(245, 158, 11, 0.28);
}
.am-discharged-banner {
  background: var(--hms-surface);
  color: var(--hms-text-secondary);
  border: 1px solid var(--hms-border);
}
@media (max-width: 960px) {
  .am-workspace { grid-template-columns: 1fr; }
  .am-sidebar { position: static; }
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

