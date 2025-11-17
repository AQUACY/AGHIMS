<template>
  <q-page class="q-pa-md">
    <div class="row items-center q-mb-md">
      <q-btn
        flat
        icon="arrow_back"
        label="Back"
        @click="$router.push('/')"
        class="q-mr-md"
      />
      <div class="text-h4 text-weight-bold glass-text">
        Blood Transfusion Types Management
      </div>
    </div>

    <!-- Add Type Form -->
    <q-card class="glass-card q-mb-md" flat bordered>
      <q-card-section>
        <div class="text-h6 glass-text q-mb-md">
          <q-icon name="add_circle" color="primary" class="q-mr-sm" />
          {{ editingType ? 'Edit Type' : 'Add New Blood Transfusion Type' }}
        </div>
        <div class="row q-col-gutter-md">
          <div class="col-12 col-md-6">
            <q-input
              v-model="typeForm.type_name"
              filled
              label="Type Name *"
              hint="e.g., Packed Cells, Whole Blood, Platelets, etc."
              :rules="[val => !!val || 'Type name is required']"
            />
          </div>
          <div class="col-12 col-md-6">
            <q-select
              v-model="typeForm.unit_type"
              :options="unitTypeOptions"
              filled
              label="Unit Type *"
              hint="How is this charged?"
              :rules="[val => !!val || 'Unit type is required']"
              emit-value
              map-options
            />
          </div>
          <div class="col-12 col-md-6">
            <q-input
              v-model.number="typeForm.unit_price"
              filled
              type="number"
              step="0.01"
              min="0"
              label="Unit Price (GHS) *"
              hint="Price for one unit"
              :rules="[
                val => !!val || 'Price is required',
                val => val >= 0 || 'Price must be positive'
              ]"
            />
          </div>
          <div class="col-12 col-md-6">
            <q-input
              v-model="typeForm.description"
              filled
              type="textarea"
              label="Description (optional)"
              hint="Additional details about this blood type"
              rows="2"
            />
          </div>
          <div class="col-12 flex items-end q-gutter-sm">
            <q-btn
              v-if="editingType"
              flat
              icon="cancel"
              label="Cancel"
              color="grey"
              @click="cancelEdit"
            />
            <q-btn
              flat
              :icon="editingType ? 'save' : 'add'"
              :label="editingType ? 'Update Type' : 'Add Type'"
              color="primary"
              @click="saveType"
              :loading="saving"
            />
          </div>
        </div>
      </q-card-section>
    </q-card>

    <!-- Types Table -->
    <q-card class="glass-card" flat bordered>
      <q-card-section>
        <div class="row items-center q-mb-md">
          <div class="text-h6 glass-text">
            All Blood Transfusion Types ({{ types.length }})
          </div>
          <q-space />
          <q-toggle
            v-model="showActiveOnly"
            label="Active Only"
            color="primary"
            class="q-mr-md"
            @update:model-value="loadTypes"
          />
          <q-input
            v-model="filter"
            filled
            dense
            placeholder="Search by name..."
            class="col-12 col-md-4"
          >
            <template v-slot:append>
              <q-icon name="search" />
            </template>
          </q-input>
        </div>

        <q-table
          :rows="filteredTypes"
          :columns="columns"
          row-key="id"
          flat
          :loading="loading"
          :filter="filter"
          :pagination="pagination"
          class="glass-table"
        >
          <template v-slot:body-cell-is_active="props">
            <q-td :props="props">
              <q-badge
                :color="props.value ? 'positive' : 'grey'"
                :label="props.value ? 'Active' : 'Inactive'"
              />
            </q-td>
          </template>

          <template v-slot:body-cell-unit_price="props">
            <q-td :props="props">
              <span class="text-weight-bold">{{ props.value }} GHS</span>
              <span class="text-caption text-grey-7 q-ml-xs">/ {{ props.row.unit_type }}</span>
            </q-td>
          </template>

          <template v-slot:body-cell-actions="props">
            <q-td :props="props">
              <div class="row q-gutter-xs">
                <q-btn
                  flat
                  dense
                  icon="edit"
                  color="primary"
                  size="sm"
                  @click="editType(props.row)"
                  :disable="!props.row.is_active && !editingType"
                >
                  <q-tooltip>Edit Type</q-tooltip>
                </q-btn>
                <q-btn
                  flat
                  dense
                  icon="delete"
                  color="negative"
                  size="sm"
                  @click="deleteType(props.row)"
                  :disable="!props.row.is_active"
                >
                  <q-tooltip>Deactivate Type</q-tooltip>
                </q-btn>
              </div>
            </q-td>
          </template>
        </q-table>
      </q-card-section>
    </q-card>
  </q-page>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useQuasar } from 'quasar';
import { consultationAPI } from '../services/api';

const $q = useQuasar();

const loading = ref(false);
const saving = ref(false);
const types = ref([]);
const filter = ref('');
const showActiveOnly = ref(false);
const editingType = ref(null);

const typeForm = ref({
  type_name: '',
  description: '',
  unit_price: null,
  unit_type: 'unit',
});

const unitTypeOptions = [
  { label: 'Unit', value: 'unit' },
  { label: 'Pack', value: 'pack' },
  { label: 'Bag', value: 'bag' },
];

const columns = [
  {
    name: 'type_name',
    required: true,
    label: 'Type Name',
    align: 'left',
    field: 'type_name',
    sortable: true,
  },
  {
    name: 'description',
    label: 'Description',
    align: 'left',
    field: 'description',
    sortable: false,
  },
  {
    name: 'unit_price',
    label: 'Price',
    align: 'left',
    field: 'unit_price',
    sortable: true,
  },
  {
    name: 'unit_type',
    label: 'Unit Type',
    align: 'center',
    field: 'unit_type',
    sortable: true,
  },
  {
    name: 'is_active',
    label: 'Status',
    align: 'center',
    field: 'is_active',
    sortable: true,
  },
  {
    name: 'created_at',
    label: 'Created',
    align: 'left',
    field: 'created_at',
    format: (val) => formatDate(val),
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

const pagination = {
  rowsPerPage: 25,
  sortBy: 'type_name',
  descending: false,
};

const filteredTypes = computed(() => {
  if (!filter.value) return types.value;
  
  const searchTerm = filter.value.toLowerCase();
  return types.value.filter(type =>
    type.type_name.toLowerCase().includes(searchTerm) ||
    (type.description && type.description.toLowerCase().includes(searchTerm))
  );
});

const loadTypes = async () => {
  loading.value = true;
  try {
    const res = await consultationAPI.getBloodTransfusionTypes(showActiveOnly.value);
    types.value = Array.isArray(res.data) ? res.data : [];
  } catch (error) {
    console.error('Error loading types:', error);
    $q.notify({
      type: 'negative',
      message: 'Failed to load blood transfusion types',
    });
  } finally {
    loading.value = false;
  }
};

const resetForm = () => {
  typeForm.value = {
    type_name: '',
    description: '',
    unit_price: null,
    unit_type: 'unit',
  };
  editingType.value = null;
};

const saveType = async () => {
  if (!typeForm.value.type_name || typeForm.value.unit_price === null || !typeForm.value.unit_type) {
    $q.notify({
      type: 'warning',
      message: 'Please fill in all required fields',
    });
    return;
  }

  saving.value = true;
  try {
    if (editingType.value) {
      // Update existing type
      await consultationAPI.updateBloodTransfusionType(editingType.value.id, typeForm.value);
      $q.notify({
        type: 'positive',
        message: 'Blood transfusion type updated successfully',
      });
    } else {
      // Create new type
      await consultationAPI.createBloodTransfusionType(typeForm.value);
      $q.notify({
        type: 'positive',
        message: 'Blood transfusion type created successfully',
      });
    }
    
    resetForm();
    await loadTypes();
  } catch (error) {
    console.error('Error saving type:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to save blood transfusion type',
    });
  } finally {
    saving.value = false;
  }
};

const editType = (type) => {
  editingType.value = type;
  typeForm.value = {
    type_name: type.type_name,
    description: type.description || '',
    unit_price: type.unit_price,
    unit_type: type.unit_type,
  };
  
  // Scroll to top
  window.scrollTo({ top: 0, behavior: 'smooth' });
};

const cancelEdit = () => {
  resetForm();
};

const deleteType = async (type) => {
  $q.dialog({
    title: 'Deactivate Type',
    message: `Are you sure you want to deactivate "${type.type_name}"? This will prevent it from being used for new requests, but existing request records will remain.`,
    cancel: true,
    persistent: true,
  }).onOk(async () => {
    try {
      await consultationAPI.deleteBloodTransfusionType(type.id);
      $q.notify({
        type: 'positive',
        message: 'Blood transfusion type deactivated successfully',
      });
      await loadTypes();
    } catch (error) {
      console.error('Error deleting type:', error);
      $q.notify({
        type: 'negative',
        message: error.response?.data?.detail || 'Failed to deactivate type',
      });
    }
  });
};

const formatDate = (dateString) => {
  if (!dateString) return '';
  const date = new Date(dateString);
  return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
};

onMounted(() => {
  loadTypes();
});
</script>

<style scoped>
.glass-text {
  color: rgba(255, 255, 255, 0.9);
}

.glass-card {
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.glass-table {
  background: transparent;
}
</style>

