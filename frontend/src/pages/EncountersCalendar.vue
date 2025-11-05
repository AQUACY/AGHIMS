<template>
  <q-page class="q-pa-md">
    <div class="text-h4 q-mb-md text-weight-bold glass-text">Appointment Calendar</div>

    <q-card class="q-mb-md glass-card" flat>
      <q-card-section>
        <div class="row items-center q-gutter-md">
          <q-input
            v-model="selectedDate"
            filled
            type="date"
            label="Select Date"
            class="col-12 col-md-3"
            @update:model-value="loadEncounters"
          />
          <q-select
            v-model="selectedDepartment"
            filled
            :options="departmentOptions"
            label="Filter by Department/Clinic"
            class="col-12 col-md-3"
            clearable
            emit-value
            map-options
          >
            <template v-slot:option="scope">
              <q-item v-bind="scope.itemProps">
                <q-item-section>
                  <q-item-label>{{ scope.opt.label || scope.opt }}</q-item-label>
                </q-item-section>
              </q-item>
            </template>
          </q-select>
          <q-input
            v-model="cardSearch"
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
          <q-badge color="primary" :label="`${filteredEncounters.length} / ${encounters.length} encounters`" />
        </div>
      </q-card-section>
    </q-card>

    <q-card class="glass-card" flat>
      <q-card-section>
        <div class="text-h6 q-mb-md glass-text">Appointments for {{ formattedDate }}</div>
        
        <q-table
          v-if="encounters.length > 0"
          :rows="filteredEncounters"
          :columns="columns"
          row-key="id"
          flat
          :loading="loading"
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
                @click="viewEncounter(props.row)"
                class="q-mr-xs"
              />
              <q-btn
                size="sm"
                color="secondary"
                icon="edit"
                flat
                :disable="props.row.status === 'finalized' && !isAdmin"
                @click="editEncounter(props.row)"
                class="q-mr-xs"
              />
              <q-btn
                v-if="isAdmin"
                size="sm"
                color="negative"
                icon="delete"
                flat
                @click="deleteEncounterConfirm(props.row)"
              />
            </q-td>
          </template>
        </q-table>

        <div v-else class="text-center q-pa-lg text-grey-6">
          <q-icon name="event_busy" size="64px" />
          <div class="text-h6 q-mt-md">No appointments found for this date</div>
        </div>
      </q-card-section>
    </q-card>

    <!-- Edit Encounter Dialog -->
    <q-dialog v-model="showEditDialog" persistent>
      <q-card style="min-width: 500px">
        <q-card-section>
          <div class="text-h6">Edit Appointment #{{ currentEncounter?.id }}</div>
        </q-card-section>

        <q-card-section>
          <q-form @submit="saveEncounterEdit" class="q-gutter-md">
            <q-select
              v-model="editForm.department"
              filled
              :options="departmentOptionsForEdit"
              label="Department *"
              lazy-rules
              :rules="[(val) => !!val || 'Required']"
              emit-value
              map-options
              @update:model-value="onDepartmentSelected"
            >
              <template v-slot:option="scope">
                <q-item v-bind="scope.itemProps">
                  <q-item-section>
                    <q-item-label>{{ scope.opt.label || scope.opt }}</q-item-label>
                  </q-item-section>
                </q-item>
              </template>
            </q-select>
            
            <q-select
              v-model="selectedProcedure"
              filled
              :options="procedureOptions"
              label="Procedure (Service Name)"
              option-label="service_name"
              option-value="g_drg_code"
              :disable="!editForm.department"
              @update:model-value="onProcedureSelected"
              hint="Select the procedure - GDRG code and name will be auto-filled"
              use-input
              input-debounce="300"
              @filter="filterProcedures"
              clearable
            >
              <template v-slot:no-option>
                <q-item>
                  <q-item-section class="text-grey">
                    {{ editForm.department
                      ? 'No procedures found. Try a different search term.'
                      : 'Please select a Department first'
                    }}
                  </q-item-section>
                </q-item>
              </template>
            </q-select>
            
            <q-input
              v-model="editForm.ccc_number"
              filled
              label="CCC Number"
            />
            <q-select
              v-model="editForm.status"
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
                @click="showEditDialog = false"
                class="q-ml-sm"
              />
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { encountersAPI, priceListAPI } from '../services/api';
import { useEncountersStore } from '../stores/encounters';
import { useAuthStore } from '../stores/auth';
import { useQuasar } from 'quasar';

const $q = useQuasar();
const router = useRouter();
const encountersStore = useEncountersStore();
const authStore = useAuthStore();

const selectedDate = ref('');
const encounters = ref([]);
const loading = ref(false);
const cardSearch = ref('');
const selectedDepartment = ref(null);
const departmentOptions = ref([]);
const loadingDepartments = ref(false);

const columns = [
  { name: 'time', label: 'Time', field: 'created_at', align: 'left', sortable: true },
  { name: 'id', label: 'Encounter ID', field: 'id', align: 'left' },
  { name: 'patient_name', label: 'Patient Name', field: 'patient_name', align: 'left' },
  { name: 'card_number', label: 'Card Number', field: 'patient_card_number', align: 'left' },
  { name: 'department', label: 'Department', field: 'department', align: 'left' },
  { name: 'status', label: 'Status', field: 'status', align: 'center' },
  { name: 'ccc_number', label: 'CCC Number', field: 'ccc_number', align: 'left' },
  { name: 'actions', label: 'Actions', align: 'center' },
];

const formattedDate = computed(() => {
  if (!selectedDate.value) return 'Select a date';
  const date = new Date(selectedDate.value);
  return date.toLocaleDateString('en-US', { 
    weekday: 'long', 
    year: 'numeric', 
    month: 'long', 
    day: 'numeric' 
  });
});

const filteredEncounters = computed(() => {
  let filtered = encounters.value;
  
  // Filter by department/clinic
  if (selectedDepartment.value) {
    filtered = filtered.filter(e => 
      (e.department || '').toLowerCase() === (selectedDepartment.value || '').toLowerCase()
    );
  }
  
  // Filter by card number
  const needle = (cardSearch.value || '').toLowerCase().trim();
  if (needle) {
    filtered = filtered.filter(e => 
      (e.patient_card_number || '').toLowerCase().includes(needle)
    );
  }
  
  return filtered;
});

const setToday = () => {
  const today = new Date();
  selectedDate.value = today.toISOString().split('T')[0];
  loadEncounters();
};

const formatTime = (dateString) => {
  if (!dateString) return '';
  const date = new Date(dateString);
  return date.toLocaleTimeString('en-US', { 
    hour: '2-digit', 
    minute: '2-digit',
    hour12: true 
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

const loadEncounters = async () => {
  if (!selectedDate.value) {
    encounters.value = [];
    return;
  }

  loading.value = true;
  try {
    const response = await encountersAPI.getByDate(selectedDate.value);
    encounters.value = response.data;
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to load encounters',
    });
    encounters.value = [];
  } finally {
    loading.value = false;
  }
};

const isAdmin = computed(() => authStore.userRole === 'Admin');

const viewEncounter = (encounter) => {
  // Non-admin viewing a finalized encounter -> open in read-only mode
  if (!isAdmin.value && encounter.status === 'finalized') {
    router.push({ path: `/consultation/${encounter.id}`, query: { readonly: '1' } });
  } else {
    router.push(`/consultation/${encounter.id}`);
  }
};

const editEncounter = async (encounter) => {
  showEditDialog.value = true;
  currentEncounter.value = encounter;
  editForm.department = encounter.department;
  editForm.ccc_number = encounter.ccc_number || '';
  editForm.status = encounter.status;
  editForm.procedure_g_drg_code = encounter.procedure_g_drg_code || '';
  editForm.procedure_name = encounter.procedure_name || '';
  
  // Reset procedure selection
  selectedProcedure.value = null;
  allProcedures.value = [];
  procedureOptions.value = [];
  
  // Load procedures for the current department
  if (encounter.department) {
    await loadProceduresForDepartment(encounter.department);
    
    // If encounter has a procedure, find and select it
    if (encounter.procedure_g_drg_code || encounter.procedure_name) {
      const matchingProcedure = allProcedures.value.find(p => 
        p.g_drg_code === encounter.procedure_g_drg_code ||
        p.service_name === encounter.procedure_name
      );
      if (matchingProcedure) {
        selectedProcedure.value = matchingProcedure;
      }
    }
  }
};

const deleteEncounterConfirm = (encounter) => {
  $q.dialog({
    title: 'Archive Appointment',
    message: `Are you sure you want to archive Appointment #${encounter.id} for ${encounter.patient_name}? This action cannot be undone.`,
    cancel: true,
    persistent: true,
    ok: {
      label: 'Archive',
      color: 'negative'
    }
  }).onOk(async () => {
    try {
      await encountersStore.deleteEncounter(encounter.id);
      await loadEncounters(); // Reload list
    } catch (error) {
      // Error handled in store
    }
  });
};

const showEditDialog = ref(false);
const currentEncounter = ref(null);
const editForm = reactive({
  department: '',
  ccc_number: '',
  status: '',
  procedure_g_drg_code: '',
  procedure_name: '',
});

// Procedure-related state
const allProcedures = ref([]);
const procedureOptions = ref([]);
const selectedProcedure = ref(null);

const statusOptions = ['draft', 'in_consultation', 'awaiting_services', 'finalized'];

// Department options for edit dialog (without "All" option)
const departmentOptionsForEdit = computed(() => {
  return departmentOptions.value.filter(opt => opt.value !== null);
});

const loadServiceTypes = async () => {
  loadingDepartments.value = true;
  try {
    const response = await priceListAPI.getServiceTypes();
    // Format options with "All" option first
    departmentOptions.value = [
      { label: 'All Departments', value: null },
      ...response.data.map(dept => ({ label: dept, value: dept }))
    ];
  } catch (error) {
    console.error('Failed to load service types:', error);
    // Fallback to default options
    departmentOptions.value = [
      { label: 'All Departments', value: null },
      { label: 'General', value: 'General' },
      { label: 'Pediatrics', value: 'Pediatrics' },
      { label: 'ENT', value: 'ENT' },
      { label: 'Eye', value: 'Eye' },
      { label: 'Emergency', value: 'Emergency' }
    ];
  } finally {
    loadingDepartments.value = false;
  }
};

const saveEncounterEdit = async () => {
  if (!currentEncounter.value) return;
  
  const updateData = {};
  if (editForm.department !== currentEncounter.value.department) {
    updateData.department = editForm.department;
  }
  if (editForm.ccc_number !== currentEncounter.value.ccc_number) {
    updateData.ccc_number = editForm.ccc_number || null;
  }
  if (editForm.status !== currentEncounter.value.status) {
    updateData.status = editForm.status;
  }
  if (editForm.procedure_g_drg_code !== (currentEncounter.value.procedure_g_drg_code || '')) {
    updateData.procedure_g_drg_code = editForm.procedure_g_drg_code || null;
  }
  if (editForm.procedure_name !== (currentEncounter.value.procedure_name || '')) {
    updateData.procedure_name = editForm.procedure_name || null;
  }
  
  if (Object.keys(updateData).length === 0) {
    $q.notify({
      type: 'info',
      message: 'No changes detected',
    });
    showEditDialog.value = false;
    return;
  }
  
  try {
    await encountersStore.updateEncounter(currentEncounter.value.id, updateData);
    showEditDialog.value = false;
    await loadEncounters(); // Reload list
  } catch (error) {
    // Error handled in store
  }
};

// Load procedures when department is selected
const onDepartmentSelected = async (department) => {
  if (!department) {
    allProcedures.value = [];
    procedureOptions.value = [];
    selectedProcedure.value = null;
    editForm.procedure_g_drg_code = '';
    editForm.procedure_name = '';
    return;
  }
  
  await loadProceduresForDepartment(department);
  
  // Clear procedure selection when department changes
  selectedProcedure.value = null;
  editForm.procedure_g_drg_code = '';
  editForm.procedure_name = '';
};

// Load procedures for a specific department
const loadProceduresForDepartment = async (department) => {
  try {
    const response = await priceListAPI.getProceduresByServiceType(department);
    console.log('Procedures response:', response.data);
    
    // Handle both array and grouped object formats
    let procedures = [];
    if (Array.isArray(response.data)) {
      procedures = response.data;
    } else if (response.data && typeof response.data === 'object') {
      // Old format: grouped object - extract procedures for the selected department
      procedures = response.data[department] || [];
    }
    
    allProcedures.value = procedures;
    procedureOptions.value = allProcedures.value;
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
             (p.g_drg_code && p.g_drg_code.toLowerCase().indexOf(needle) > -1)
    );
  });
};

// When procedure is selected, auto-fill GDRG code and procedure name
const onProcedureSelected = (procedure) => {
  if (procedure && typeof procedure === 'object') {
    editForm.procedure_g_drg_code = procedure.g_drg_code || '';
    editForm.procedure_name = procedure.service_name || '';
  } else if (procedure) {
    // If it's just the code, find the procedure object
    const proc = allProcedures.value.find(p => p.g_drg_code === procedure);
    if (proc) {
      editForm.procedure_g_drg_code = proc.g_drg_code || '';
      editForm.procedure_name = proc.service_name || '';
    }
  } else {
    editForm.procedure_g_drg_code = '';
    editForm.procedure_name = '';
  }
};

onMounted(async () => {
  await loadServiceTypes();
  setToday();
});
</script>

