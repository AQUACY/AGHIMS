<template>
  <q-page class="hms-page">
    <HmsPageHeader
      title="Bed management"
      subtitle="Add and manage beds across consultation wards."
    >
      <template #actions>
        <HmsButton variant="secondary" size="sm" @click="$router.push('/ipd')">
          Back to IPD
        </HmsButton>
      </template>
    </HmsPageHeader>


    <!-- Add Bed Form -->
    <q-card class="glass-card q-mb-md" flat bordered>
      <q-card-section>
        <div class="text-h6 glass-text q-mb-md">
          <q-icon name="add" color="primary" class="q-mr-sm" />
          Add New Bed
        </div>
        <div class="row q-col-gutter-md">
          <div class="col-12 col-md-4">
            <q-select
              v-model="newBed.ward"
              :options="wardOptions"
              filled
              label="Ward *"
              hint="Select ward from consultation wards"
              :rules="[val => !!val || 'Ward is required']"
              use-input
              input-debounce="0"
              @filter="filterWards"
              @new-value="createWard"
              emit-value
              map-options
            >
              <template v-slot:no-option>
                <q-item>
                  <q-item-section class="text-grey">
                    No wards found. Type to add a new ward.
                  </q-item-section>
                </q-item>
              </template>
            </q-select>
          </div>
          <div class="col-12 col-md-4">
            <q-input
              v-model="newBed.bed_number"
              filled
              label="Bed Number *"
              hint="e.g., Bed 1, A1, 101"
              :rules="[val => !!val || 'Bed number is required']"
            />
          </div>
          <div class="col-12 col-md-4 flex items-end">
            <q-btn
              flat
              icon="add"
              label="Add Bed"
              color="primary"
              @click="addBed"
              :loading="addingBed"
              class="full-width"
            />
          </div>
        </div>
      </q-card-section>
    </q-card>

    <!-- Beds Table -->
    <q-card class="glass-card" flat bordered>
      <q-card-section>
        <div class="row items-center q-mb-md">
          <div class="text-h6 glass-text">
            All Beds ({{ beds.length }})
          </div>
          <q-space />
          <q-input
            v-model="filter"
            filled
            dense
            placeholder="Search by ward or bed number..."
            class="col-12 col-md-4"
          >
            <template v-slot:append>
              <q-icon name="search" />
            </template>
          </q-input>
        </div>

        <q-table
          :rows="filteredBeds"
          :columns="columns"
          row-key="id"
          flat
          :loading="loading"
          :filter="filter"
          :pagination="pagination"
          class="glass-table"
        >
          <template v-slot:body-cell-ward="props">
            <q-td :props="props">
              <q-badge color="primary" :label="props.value" />
            </q-td>
          </template>

          <template v-slot:body-cell-status="props">
            <q-td :props="props">
              <q-chip
                :color="props.row.is_occupied ? 'negative' : 'positive'"
                text-color="white"
                :icon="props.row.is_occupied ? 'person' : 'check_circle'"
                size="sm"
              >
                {{ props.row.is_occupied ? 'Occupied' : 'Available' }}
              </q-chip>
            </q-td>
          </template>

          <template v-slot:body-cell-actions="props">
            <q-td :props="props">
              <div class="row q-gutter-xs">
                <q-btn
                  flat
                  dense
                  icon="edit"
                  label="Edit"
                  color="primary"
                  size="sm"
                  @click="editBed(props.row)"
                />
                <q-btn
                  v-if="!props.row.is_occupied"
                  flat
                  dense
                  icon="delete"
                  label="Delete"
                  color="negative"
                  size="sm"
                  @click="deleteBed(props.row)"
                  :loading="deletingId === props.row.id"
                />
              </div>
            </q-td>
          </template>
        </q-table>
      </q-card-section>
    </q-card>

    <!-- Edit Bed Dialog -->
    <q-dialog v-model="showEditDialog" persistent>
      <q-card style="min-width: 400px">
        <q-card-section>
          <div class="text-h6">Edit Bed</div>
        </q-card-section>

        <q-card-section>
          <q-select
            v-model="editingBed.ward"
            :options="wardOptions"
            filled
            label="Ward *"
            :rules="[val => !!val || 'Ward is required']"
            use-input
            input-debounce="0"
            @filter="filterWards"
            @new-value="createWard"
            emit-value
            map-options
          />
          <q-input
            v-model="editingBed.bed_number"
            filled
            label="Bed Number *"
            :rules="[val => !!val || 'Bed number is required']"
            class="q-mt-md"
          />
        </q-card-section>

        <q-card-actions align="right">
          <q-btn flat label="Cancel" color="primary" @click="showEditDialog = false" />
          <q-btn
            flat
            label="Update"
            color="positive"
            @click="updateBed"
            :loading="updatingBed"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useQuasar } from 'quasar';
import HmsPageHeader from '../components/ui/HmsPageHeader.vue';
import HmsButton from '../components/ui/HmsButton.vue';
import { consultationAPI, wardsAPI } from '../services/api';

const $q = useQuasar();

const loading = ref(false);
const beds = ref([]);
const filter = ref('');
const addingBed = ref(false);
const updatingBed = ref(false);
const deletingId = ref(null);
const showEditDialog = ref(false);
const wards = ref([]);
const wardOptions = ref([]);
const editingBed = ref({
  id: null,
  ward: '',
  bed_number: '',
});

const newBed = ref({
  ward: '',
  bed_number: '',
});

const pagination = ref({
  sortBy: 'ward',
  descending: false,
  page: 1,
  rowsPerPage: 10,
  rowsNumber: 0,
});

const columns = [
  {
    name: 'ward',
    required: true,
    label: 'Ward',
    align: 'left',
    field: 'ward',
    sortable: true,
  },
  {
    name: 'bed_number',
    required: true,
    label: 'Bed Number',
    align: 'left',
    field: 'bed_number',
    sortable: true,
  },
  {
    name: 'status',
    label: 'Status',
    align: 'center',
    field: 'status',
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

const filteredBeds = computed(() => {
  if (!filter.value) return beds.value;
  
  const searchTerm = filter.value.toLowerCase();
  return beds.value.filter(bed => {
    return (
      bed.ward.toLowerCase().includes(searchTerm) ||
      bed.bed_number.toLowerCase().includes(searchTerm)
    );
  });
});

const loadBeds = async () => {
  loading.value = true;
  try {
    const response = await consultationAPI.getBeds();
    beds.value = Array.isArray(response.data) ? response.data : [];
    pagination.value.rowsNumber = beds.value.length;
  } catch (error) {
    console.error('Error loading beds:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to load beds',
    });
    beds.value = [];
  } finally {
    loading.value = false;
  }
};

const loadWards = async () => {
  try {
    const response = await wardsAPI.getAll(true, 'ward'); // Get only active wards (department type = ward)
    const wardNames = (response.data || []).map(ward => ward.name);
    wards.value = wardNames;
    wardOptions.value = wardNames.map(ward => ({
      label: ward,
      value: ward
    }));
  } catch (error) {
    console.error('Error loading wards:', error);
    $q.notify({
      type: 'negative',
      message: 'Failed to load wards',
    });
  }
};

const filterWards = (val, update) => {
  if (val === '') {
    update(() => {
      wardOptions.value = wards.value.map(ward => ({
        label: ward,
        value: ward
      }));
    });
    return;
  }

  update(() => {
    const needle = val.toLowerCase();
    wardOptions.value = wards.value
      .filter(ward => ward.toLowerCase().includes(needle))
      .map(ward => ({
        label: ward,
        value: ward
      }));
  });
};

const createWard = (val, done) => {
  // Allow creating new ward if it doesn't exist
  if (val.length > 0 && !wards.value.includes(val)) {
    wards.value.push(val);
    wardOptions.value = wards.value.map(ward => ({
      label: ward,
      value: ward
    }));
    done(val, 'add');
  } else {
    done(false);
  }
};

const addBed = async () => {
  if (!newBed.value.ward || !newBed.value.bed_number) {
    $q.notify({
      type: 'negative',
      message: 'Please fill in all required fields',
    });
    return;
  }

  addingBed.value = true;
  try {
    await consultationAPI.createBed({
      ward: newBed.value.ward,
      bed_number: newBed.value.bed_number,
      is_active: true,
    });
    $q.notify({
      type: 'positive',
      message: 'Bed added successfully',
    });
    newBed.value = { ward: '', bed_number: '' };
    await loadBeds();
  } catch (error) {
    console.error('Error adding bed:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to add bed',
    });
  } finally {
    addingBed.value = false;
  }
};

const editBed = (bed) => {
  editingBed.value = {
    id: bed.id,
    ward: bed.ward,
    bed_number: bed.bed_number,
  };
  showEditDialog.value = true;
};

const updateBed = async () => {
  if (!editingBed.value.ward || !editingBed.value.bed_number) {
    $q.notify({
      type: 'negative',
      message: 'Please fill in all required fields',
    });
    return;
  }

  updatingBed.value = true;
  try {
    await consultationAPI.updateBed(editingBed.value.id, {
      ward: editingBed.value.ward,
      bed_number: editingBed.value.bed_number,
      is_active: true,
    });
    $q.notify({
      type: 'positive',
      message: 'Bed updated successfully',
    });
    showEditDialog.value = false;
    await loadBeds();
  } catch (error) {
    console.error('Error updating bed:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to update bed',
    });
  } finally {
    updatingBed.value = false;
  }
};

const deleteBed = async (bed) => {
  $q.dialog({
    title: 'Delete Bed',
    message: `Are you sure you want to delete ${bed.bed_number} from ${bed.ward}?`,
    cancel: true,
    persistent: true
  }).onOk(async () => {
    deletingId.value = bed.id;
    try {
      await consultationAPI.deleteBed(bed.id);
      $q.notify({
        type: 'positive',
        message: 'Bed deleted successfully',
      });
      await loadBeds();
    } catch (error) {
      console.error('Error deleting bed:', error);
      $q.notify({
        type: 'negative',
        message: error.response?.data?.detail || 'Failed to delete bed',
      });
    } finally {
      deletingId.value = null;
    }
  });
};

onMounted(() => {
  loadWards();
  loadBeds();
});
</script>

<style scoped>

.ipd-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  align-items: flex-end;
  margin-bottom: 0.95rem;
  padding: 0.95rem 1.05rem;
  border-radius: var(--hms-radius-xl);
  background: var(--hms-panel-bg);
  border: 1px solid var(--hms-border);
  box-shadow: var(--hms-shadow-md);
}
.ipd-panel {
  padding: 1.05rem 1.15rem;
  border-radius: var(--hms-radius-xl);
  background: var(--hms-panel-bg);
  border: 1px solid var(--hms-border);
  box-shadow: var(--hms-shadow-md);
  margin-bottom: 0.95rem;
}
.ipd-tabs {
  display: flex;
  gap: 1.1rem;
  margin-bottom: 0.95rem;
  border-bottom: 1px solid var(--hms-border);
}
.ipd-tab {
  border: none;
  background: transparent;
  padding: 0.55rem 0.1rem 0.7rem;
  font-family: inherit;
  font-size: var(--hms-text-sm);
  font-weight: 650;
  color: var(--hms-text-muted);
  cursor: pointer;
  position: relative;
}
.ipd-tab.active { color: var(--hms-accent); }
.ipd-tab.active::after {
  content: '';
  position: absolute; left: 0; right: 0; bottom: -1px; height: 2px;
  background: var(--hms-accent); border-radius: 2px 2px 0 0;
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

.body--dark .glass-text {
  color: rgba(255, 255, 255, 0.9) !important;
}
</style>

