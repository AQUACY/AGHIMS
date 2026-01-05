<template>
  <q-page class="q-pa-md">
    <div class="text-h4 q-mb-md text-weight-bold glass-text">Operation Theatre Calendar</div>

    <!-- Filter Section -->
    <q-card class="q-mb-md glass-card" flat>
      <q-card-section>
        <div class="row q-gutter-md">
          <q-input
            v-model="selectedDate"
            filled
            type="date"
            label="Select Date"
            class="col-12 col-md-3"
            @update:model-value="loadSurgeries"
          />
          <q-btn
            icon="today"
            label="Today"
            @click="setToday"
            color="primary"
            class="col-12 col-md-2 glass-button"
          />
          <q-space />
          <q-badge color="primary" :label="`${surgeries.length} operations`" />
        </div>
      </q-card-section>
    </q-card>

    <!-- Operations List by Day -->
    <q-card class="glass-card" flat>
      <q-card-section>
        <div class="text-h6 q-mb-md glass-text">
          Operations for {{ formatDateDisplay(selectedDate) }}
        </div>

        <div v-if="loading" class="text-center q-pa-lg">
          <q-spinner color="primary" size="3em" />
          <div class="q-mt-md">Loading operations...</div>
        </div>

        <div v-else-if="surgeries.length === 0" class="text-center q-pa-lg text-grey-6">
          <q-icon name="event_busy" size="64px" />
          <div class="text-h6 q-mt-md">No operations found for this date</div>
        </div>

        <div v-else>
          <q-list separator>
            <q-item
              v-for="surgery in surgeries"
              :key="surgery.id"
              class="q-pa-md q-mb-sm"
              style="border: 1px solid rgba(0,0,0,0.12); border-radius: 8px;"
            >
              <q-item-section>
                <q-item-label class="text-h6 text-weight-bold">
                  {{ surgery.surgery_name }}
                </q-item-label>
                <q-item-label caption>
                  <div class="row q-gutter-md q-mt-sm">
                    <div><strong>Patient:</strong> {{ surgery.patient_name || 'N/A' }}</div>
                    <div><strong>Card:</strong> {{ surgery.patient_card_number || 'N/A' }}</div>
                    <div><strong>Ward:</strong> {{ surgery.ward || 'N/A' }}</div>
                    <div v-if="surgery.surgeon_name">
                      <strong>Surgeon:</strong> {{ surgery.surgeon_name }}
                    </div>
                    <div v-if="surgery.surgery_date">
                      <strong>Time:</strong> {{ formatDateTime(surgery.surgery_date) }}
                    </div>
                  </div>
                  <div class="row q-gutter-md q-mt-xs">
                    <q-badge
                      :color="surgery.is_completed ? 'positive' : 'orange'"
                      :label="surgery.is_completed ? 'Completed' : 'Pending'"
                    />
                    <q-badge
                      v-if="surgery.anaesthetist_consultation || surgery.intra_operation_care || surgery.post_operation_care"
                      color="info"
                      label="Anaesthetist Info Added"
                    />
                  </div>
                </q-item-label>
              </q-item-section>
              <q-item-section side>
                <div class="column q-gutter-xs">
                  <q-btn
                    flat
                    dense
                    icon="edit"
                    label="Edit"
                    color="primary"
                    @click="editSurgery(surgery)"
                  />
                  <q-btn
                    flat
                    dense
                    icon="local_hospital"
                    label="Anaesthetist Info"
                    color="secondary"
                    @click="editAnaesthetistInfo(surgery)"
                  />
                </div>
              </q-item-section>
            </q-item>
          </q-list>
        </div>
      </q-card-section>
    </q-card>

    <!-- Surgery Form Dialog -->
    <q-dialog v-model="showSurgeryDialog" persistent>
      <q-card style="min-width: 700px; max-width: 900px">
        <q-card-section>
          <div class="text-h6 glass-text">
            {{ editingSurgery ? 'Edit Operation' : 'Add Operation' }}
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
            </q-select>
            
            <!-- Manual Surgery Entry -->
            <q-input
              v-model="surgeryForm.surgery_name"
              filled
              label="Surgery Name *"
              hint="Name/description of the surgery"
              :rules="[val => !!val || 'Surgery name is required']"
            />
            
            <div class="row q-col-gutter-md">
              <div class="col-6">
                <q-input
                  v-model="surgeryForm.g_drg_code"
                  filled
                  label="G-DRG Code"
                  hint="Surgery code"
                />
              </div>
              <div class="col-6">
                <q-input
                  v-model="surgeryForm.surgery_type"
                  filled
                  label="Surgery Type"
                  hint="Type/category of surgery"
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

    <!-- Anaesthetist Info Dialog -->
    <q-dialog v-model="showAnaesthetistDialog" persistent>
      <q-card style="min-width: 700px; max-width: 900px">
        <q-card-section>
          <div class="text-h6 glass-text">Anaesthetist Information</div>
          <div class="text-subtitle2 text-grey-7 q-mt-sm">
            Operation: <span class="text-weight-bold">{{ selectedSurgeryForAnaesthetist?.surgery_name }}</span>
          </div>
          <div class="text-subtitle2 text-grey-7">
            Patient: <span class="text-weight-bold">{{ selectedSurgeryForAnaesthetist?.patient_name }}</span>
          </div>
        </q-card-section>

        <q-card-section class="q-pt-none">
          <q-form @submit="saveAnaesthetistInfo" class="q-gutter-md">
            <q-input
              v-model="anaesthetistForm.anaesthetist_consultation"
              filled
              type="textarea"
              label="Anaesthetist Consultation"
              hint="Anaesthetist's consultation notes"
              rows="4"
            />

            <q-input
              v-model="anaesthetistForm.intra_operation_care"
              filled
              type="textarea"
              label="Intra-operation Care"
              hint="Care provided during the operation"
              rows="4"
            />

            <q-input
              v-model="anaesthetistForm.post_operation_care"
              filled
              type="textarea"
              label="Post-operation Care"
              hint="Post-operative care notes"
              rows="4"
            />

            <q-input
              v-model="anaesthetistForm.drugs_given"
              filled
              type="textarea"
              label="Drugs Given"
              hint="Drugs administered during operation"
              rows="4"
            />

            <q-input
              v-model="anaesthetistForm.anaesthesia_used"
              filled
              type="textarea"
              label="Anaesthesia Used"
              hint="Detailed anaesthesia information"
              rows="4"
            />

            <q-card-actions align="right" class="q-pt-md">
              <q-btn flat label="Cancel" color="primary" @click="closeAnaesthetistDialog" />
              <q-btn
                type="submit"
                label="Save"
                color="positive"
                :loading="savingAnaesthetist"
              />
            </q-card-actions>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useQuasar } from 'quasar';
import { consultationAPI, priceListAPI } from '../services/api';

const $q = useQuasar();

const selectedDate = ref(new Date().toISOString().split('T')[0]);
const surgeries = ref([]);
const loading = ref(false);

// Surgery Dialog
const showSurgeryDialog = ref(false);
const editingSurgery = ref(null);
const savingSurgery = ref(false);
const surgeryForm = ref({
  surgery_name: '',
  g_drg_code: '',
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

// Surgery Search
const selectedSurgery = ref(null);
const allSurgeries = ref([]);
const filteredSurgeryOptions = ref([]);
const loadingSurgeries = ref(false);

// Anaesthetist Dialog
const showAnaesthetistDialog = ref(false);
const selectedSurgeryForAnaesthetist = ref(null);
const savingAnaesthetist = ref(false);
const anaesthetistForm = ref({
  anaesthetist_consultation: '',
  intra_operation_care: '',
  post_operation_care: '',
  drugs_given: '',
  anaesthesia_used: '',
});

const formatDateDisplay = (dateStr) => {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
};

const formatDateTime = (dateStr) => {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  return date.toLocaleString('en-US', { 
    year: 'numeric', 
    month: 'short', 
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
};

const setToday = () => {
  selectedDate.value = new Date().toISOString().split('T')[0];
  loadSurgeries();
};

const loadSurgeries = async () => {
  loading.value = true;
  try {
    const response = await consultationAPI.getSurgeriesCalendar(selectedDate.value);
    surgeries.value = Array.isArray(response.data) ? response.data : [];
  } catch (error) {
    console.error('Error loading surgeries:', error);
    $q.notify({
      type: 'negative',
      message: 'Failed to load operations',
    });
  } finally {
    loading.value = false;
  }
};

const loadSurgeriesFromPriceList = async () => {
  loadingSurgeries.value = true;
  try {
    const response = await priceListAPI.getProceduresByServiceType();
    let procedures = [];
    
    if (Array.isArray(response.data)) {
      procedures = response.data;
    } else if (response.data && typeof response.data === 'object') {
      for (const key in response.data) {
        if (Array.isArray(response.data[key])) {
          procedures = procedures.concat(response.data[key]);
        }
      }
    }
    
    allSurgeries.value = procedures
      .filter(p => p && p.name)
      .map(p => ({
        label: `${p.name}${p.code ? ` (${p.code})` : ''}`,
        value: {
          name: p.name,
          code: p.code || '',
          service_type: p.service_type || '',
        }
      }));
    
    filteredSurgeryOptions.value = allSurgeries.value.slice(0, 50);
  } catch (error) {
    console.error('Error loading surgeries from price list:', error);
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
    ).slice(0, 100);
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

const editSurgery = async (surgery) => {
  // For now, we can only view/edit operations that are already created
  // To add new operations, users should go to the Admission Manager
  $q.notify({
    type: 'info',
    message: 'To add new operations, please use the Admission Manager. This page is for viewing and adding anaesthetist information.',
  });
};

const editAnaesthetistInfo = (surgery) => {
  selectedSurgeryForAnaesthetist.value = surgery;
  anaesthetistForm.value = {
    anaesthetist_consultation: surgery.anaesthetist_consultation || '',
    intra_operation_care: surgery.intra_operation_care || '',
    post_operation_care: surgery.post_operation_care || '',
    drugs_given: surgery.drugs_given || '',
    anaesthesia_used: surgery.anaesthesia_used || '',
  };
  showAnaesthetistDialog.value = true;
};

const saveAnaesthetistInfo = async () => {
  if (!selectedSurgeryForAnaesthetist.value) return;

  savingAnaesthetist.value = true;
  try {
    await consultationAPI.updateSurgeryAnaesthetistInfo(
      selectedSurgeryForAnaesthetist.value.id,
      anaesthetistForm.value
    );
    
    $q.notify({
      type: 'positive',
      message: 'Anaesthetist information saved successfully',
    });
    
    closeAnaesthetistDialog();
    await loadSurgeries();
  } catch (error) {
    console.error('Error saving anaesthetist info:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to save anaesthetist information',
    });
  } finally {
    savingAnaesthetist.value = false;
  }
};

const closeAnaesthetistDialog = () => {
  showAnaesthetistDialog.value = false;
  selectedSurgeryForAnaesthetist.value = null;
  anaesthetistForm.value = {
    anaesthetist_consultation: '',
    intra_operation_care: '',
    post_operation_care: '',
    drugs_given: '',
    anaesthesia_used: '',
  };
};

const saveSurgery = async () => {
  // This is a placeholder - actual implementation would require ward_admission_id
  $q.notify({
    type: 'info',
    message: 'To add new operations, please use the Admission Manager page.',
  });
  closeSurgeryDialog();
};

const closeSurgeryDialog = () => {
  showSurgeryDialog.value = false;
  editingSurgery.value = null;
  surgeryForm.value = {
    surgery_name: '',
    g_drg_code: '',
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
};

onMounted(() => {
  loadSurgeries();
  loadSurgeriesFromPriceList();
});
</script>

<style scoped>
.glass-text {
  color: rgba(0, 0, 0, 0.87);
}

.body--dark .glass-text {
  color: rgba(255, 255, 255, 0.9);
}
</style>

