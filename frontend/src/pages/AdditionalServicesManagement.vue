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
        Additional Services Management
      </div>
    </div>

    <!-- Add Service Form -->
    <q-card class="glass-card q-mb-md" flat bordered>
      <q-card-section>
        <div class="text-h6 glass-text q-mb-md">
          <q-icon name="add_circle" color="primary" class="q-mr-sm" />
          {{ editingService ? 'Edit Service' : 'Add New Service' }}
        </div>
        <div class="row q-col-gutter-md">
          <div class="col-12 col-md-6">
            <q-input
              v-model="serviceForm.service_name"
              filled
              label="Service Name *"
              hint="e.g., Oxygen - Adult, Private Room, etc."
              :rules="[val => !!val || 'Service name is required']"
            />
          </div>
          <div class="col-12 col-md-6">
            <q-select
              v-model="serviceForm.unit_type"
              :options="unitTypeOptions"
              filled
              label="Unit Type *"
              hint="How is this service charged?"
              :rules="[val => !!val || 'Unit type is required']"
              emit-value
              map-options
            />
          </div>
          <div class="col-12 col-md-6">
            <q-input
              v-model.number="serviceForm.price_per_unit"
              filled
              type="number"
              step="0.01"
              min="0"
              label="Price Per Unit (GHS) *"
              hint="Price for one unit (hour/day/unit)"
              :rules="[
                val => !!val || 'Price is required',
                val => val >= 0 || 'Price must be positive'
              ]"
            />
          </div>
          <div class="col-12 col-md-6">
            <q-input
              v-model="serviceForm.description"
              filled
              type="textarea"
              label="Description (optional)"
              hint="Additional details about this service"
              rows="2"
            />
          </div>
          <div class="col-12 flex items-end q-gutter-sm">
            <q-btn
              v-if="editingService"
              flat
              icon="cancel"
              label="Cancel"
              color="grey"
              @click="cancelEdit"
            />
            <q-btn
              flat
              :icon="editingService ? 'save' : 'add'"
              :label="editingService ? 'Update Service' : 'Add Service'"
              color="primary"
              @click="saveService"
              :loading="saving"
            />
          </div>
        </div>
      </q-card-section>
    </q-card>

    <!-- Services Table -->
    <q-card class="glass-card" flat bordered>
      <q-card-section>
        <div class="row items-center q-mb-md">
          <div class="text-h6 glass-text">
            All Services ({{ services.length }})
          </div>
          <q-space />
          <q-toggle
            v-model="showActiveOnly"
            label="Active Only"
            color="primary"
            class="q-mr-md"
            @update:model-value="loadServices"
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
          :rows="filteredServices"
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

          <template v-slot:body-cell-price_per_unit="props">
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
                  @click="editService(props.row)"
                  :disable="!props.row.is_active && !editingService"
                >
                  <q-tooltip>Edit Service</q-tooltip>
                </q-btn>
                <q-btn
                  flat
                  dense
                  icon="delete"
                  color="negative"
                  size="sm"
                  @click="deleteService(props.row)"
                  :disable="!props.row.is_active"
                >
                  <q-tooltip>Deactivate Service</q-tooltip>
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
const services = ref([]);
const filter = ref('');
const showActiveOnly = ref(false);
const editingService = ref(null);

const serviceForm = ref({
  service_name: '',
  description: '',
  price_per_unit: null,
  unit_type: 'hour',
});

const unitTypeOptions = [
  { label: 'Hour', value: 'hour' },
  { label: 'Day', value: 'day' },
  { label: 'Unit', value: 'unit' },
];

const columns = [
  {
    name: 'service_name',
    required: true,
    label: 'Service Name',
    align: 'left',
    field: 'service_name',
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
    name: 'price_per_unit',
    label: 'Price',
    align: 'left',
    field: 'price_per_unit',
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
  sortBy: 'service_name',
  descending: false,
};

const filteredServices = computed(() => {
  if (!filter.value) return services.value;
  
  const searchTerm = filter.value.toLowerCase();
  return services.value.filter(service =>
    service.service_name.toLowerCase().includes(searchTerm) ||
    (service.description && service.description.toLowerCase().includes(searchTerm))
  );
});

const loadServices = async () => {
  loading.value = true;
  try {
    const res = await consultationAPI.getAdditionalServices(showActiveOnly.value);
    services.value = Array.isArray(res.data) ? res.data : [];
  } catch (error) {
    console.error('Error loading services:', error);
    $q.notify({
      type: 'negative',
      message: 'Failed to load additional services',
    });
  } finally {
    loading.value = false;
  }
};

const resetForm = () => {
  serviceForm.value = {
    service_name: '',
    description: '',
    price_per_unit: null,
    unit_type: 'hour',
  };
  editingService.value = null;
};

const saveService = async () => {
  if (!serviceForm.value.service_name || !serviceForm.value.price_per_unit || !serviceForm.value.unit_type) {
    $q.notify({
      type: 'warning',
      message: 'Please fill in all required fields',
    });
    return;
  }

  saving.value = true;
  try {
    if (editingService.value) {
      // Update existing service
      await consultationAPI.updateAdditionalService(editingService.value.id, serviceForm.value);
      $q.notify({
        type: 'positive',
        message: 'Service updated successfully',
      });
    } else {
      // Create new service
      await consultationAPI.createAdditionalService(serviceForm.value);
      $q.notify({
        type: 'positive',
        message: 'Service created successfully',
      });
    }
    
    resetForm();
    await loadServices();
  } catch (error) {
    console.error('Error saving service:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to save service',
    });
  } finally {
    saving.value = false;
  }
};

const editService = (service) => {
  editingService.value = service;
  serviceForm.value = {
    service_name: service.service_name,
    description: service.description || '',
    price_per_unit: service.price_per_unit,
    unit_type: service.unit_type,
  };
  
  // Scroll to top
  window.scrollTo({ top: 0, behavior: 'smooth' });
};

const cancelEdit = () => {
  resetForm();
};

const deleteService = async (service) => {
  $q.dialog({
    title: 'Deactivate Service',
    message: `Are you sure you want to deactivate "${service.service_name}"? This will prevent it from being used for new patients, but existing usage records will remain.`,
    cancel: true,
    persistent: true,
  }).onOk(async () => {
    try {
      await consultationAPI.deleteAdditionalService(service.id);
      $q.notify({
        type: 'positive',
        message: 'Service deactivated successfully',
      });
      await loadServices();
    } catch (error) {
      console.error('Error deleting service:', error);
      $q.notify({
        type: 'negative',
        message: error.response?.data?.detail || 'Failed to deactivate service',
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
  loadServices();
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

