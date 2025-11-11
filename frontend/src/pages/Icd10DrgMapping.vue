<template>
  <q-page class="q-pa-md">
    <div class="row items-center q-mb-md">
      <div class="text-h4 text-weight-bold glass-text">
        ICD-10 DRG Mapping Management
      </div>
      <q-space />
      <q-btn
        flat
        icon="download"
        label="Download CSV"
        color="secondary"
        @click="downloadMappings"
        class="q-mr-sm"
      />
      <q-btn
        flat
        icon="upload"
        label="Upload File"
        color="secondary"
        @click="triggerFileUpload"
        class="q-mr-sm"
      />
      <q-btn
        flat
        icon="add"
        label="Add New Mapping"
        color="primary"
        @click="openDialog(null)"
      />
    </div>
    
    <!-- Hidden file input for upload -->
    <input
      ref="fileInput"
      type="file"
      accept=".csv,.xlsx,.xls"
      style="display: none"
      @change="handleFileUpload"
    />

    <!-- Search and Filters -->
    <q-card class="glass-card q-mb-md" flat bordered>
      <q-card-section>
        <div class="row q-col-gutter-md">
          <div class="col-12 col-md-5">
            <q-input
              v-model="searchTerm"
              filled
              dense
              placeholder="Search by DRG code, ICD-10 code, or description..."
              debounce="300"
              @update:model-value="loadMappings"
            >
              <template v-slot:append>
                <q-icon name="search" />
              </template>
            </q-input>
          </div>
          <div class="col-12 col-md-2 flex items-center">
            <q-toggle
              v-model="showInactive"
              label="Show Inactive Mappings"
              @update:model-value="loadMappings"
            />
          </div>
          <div class="col-12 col-md-2 flex items-center">
            <q-toggle
              v-model="showUnmappedOnly"
              label="Show Unmapped Only"
              @update:model-value="loadMappings"
            />
          </div>
          <div class="col-12 col-md-4 flex items-center">
            <q-select
              v-model="pagination.rowsPerPage"
              :options="rowsPerPageOptions"
              option-value="value"
              option-label="label"
              emit-value
              map-options
              label="Records per page"
              filled
              dense
              @update:model-value="loadMappings"
              style="min-width: 150px"
            />
          </div>
        </div>
      </q-card-section>
    </q-card>

    <!-- Mappings Table -->
    <q-card class="glass-card" flat bordered>
      <q-card-section>
        <q-table
          :rows="mappings"
          :columns="columns"
          row-key="id"
          flat
          :loading="loading"
          :pagination="pagination"
          @request="onRequest"
          class="glass-table"
          :rows-per-page-options="[25, 50, 100, 200, 500, 0]"
        >
          <template v-slot:body-cell-drg_code="props">
            <q-td :props="props">
              <q-badge 
                v-if="props.value && props.value.trim() !== ''" 
                color="primary" 
                :label="props.value" 
              />
              <q-badge 
                v-else 
                color="orange" 
                label="Unmapped" 
                class="text-white"
              />
            </q-td>
          </template>

          <template v-slot:body-cell-icd10_code="props">
            <q-td :props="props">
              <q-badge color="secondary" :label="props.value" />
            </q-td>
          </template>

          <template v-slot:body-cell-is_active="props">
            <q-td :props="props">
              <q-chip
                :color="props.value ? 'positive' : 'negative'"
                text-color="white"
                :icon="props.value ? 'check_circle' : 'cancel'"
                size="sm"
              >
                {{ props.value ? 'Active' : 'Inactive' }}
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
                  @click="openDialog(props.row)"
                />
                <q-btn
                  flat
                  dense
                  icon="delete"
                  label="Delete"
                  color="negative"
                  size="sm"
                  @click="confirmDelete(props.row)"
                  :loading="deletingId === props.row.id"
                />
              </div>
            </q-td>
          </template>
        </q-table>
      </q-card-section>
    </q-card>

    <!-- Add/Edit Dialog -->
    <q-dialog v-model="showDialog" persistent>
      <q-card style="min-width: 600px; max-width: 800px;">
        <q-card-section>
          <div class="text-h6 glass-text">
            {{ editingMapping ? 'Edit ICD-10 DRG Mapping' : 'Add New ICD-10 DRG Mapping' }}
          </div>
        </q-card-section>

        <q-card-section class="q-pt-none">
          <q-form @submit="saveMapping" class="q-gutter-md">
            <div class="row q-col-gutter-md">
              <div class="col-12 col-md-6">
                <q-select
                  v-model="formData.drg_code"
                  :options="drgCodeOptions"
                  option-value="drg_code"
                  option-label="drg_code"
                  emit-value
                  map-options
                  filled
                  use-input
                  input-debounce="300"
                  @filter="filterDrgCodes"
                  @update:model-value="onDrgCodeSelected"
                  @new-value="createDrgCode"
                  :label="editingMapping && !editingMapping.drg_code ? 'DRG Code (Optional - Currently Unmapped)' : 'DRG Code *'"
                  hint="Type to search (e.g., ASUR) or enter manually. Leave empty for unmapped ICD-10."
                  :rules="editingMapping && !editingMapping.drg_code ? [] : [val => !!val || 'DRG code is required']"
                  :loading="loadingDrgCodes"
                  clearable
                >
                  <template v-slot:option="scope">
                    <q-item v-bind="scope.itemProps">
                      <q-item-section>
                        <q-item-label>{{ scope.opt.drg_code }}</q-item-label>
                        <q-item-label caption v-if="scope.opt.drg_description">
                          {{ scope.opt.drg_description }}
                        </q-item-label>
                      </q-item-section>
                    </q-item>
                  </template>
                  <template v-slot:no-option>
                    <q-item>
                      <q-item-section class="text-grey">
                        No DRG codes found
                      </q-item-section>
                    </q-item>
                  </template>
                </q-select>
              </div>
              <div class="col-12 col-md-6">
                <q-input
                  v-model="formData.icd10_code"
                  filled
                  label="ICD-10 Code *"
                  hint="e.g., D34.00"
                  :rules="[val => !!val || 'ICD-10 code is required']"
                />
              </div>
            </div>

            <q-input
              v-model="formData.drg_description"
              filled
              label="DRG Description"
              hint="Description of the DRG code"
              type="textarea"
              rows="2"
            />

            <q-input
              v-model="formData.icd10_description"
              filled
              label="ICD-10 Description"
              hint="Description of the ICD-10 code"
              type="textarea"
              rows="2"
            />

            <q-input
              v-model="formData.notes"
              filled
              label="Notes"
              hint="Additional notes"
              type="textarea"
              rows="2"
            />

            <q-input
              v-model="formData.remarks"
              filled
              label="Remarks"
              hint="Additional remarks"
              type="textarea"
              rows="2"
            />

            <q-toggle
              v-model="formData.is_active"
              label="Active"
            />
          </q-form>
        </q-card-section>

        <q-card-actions align="right" class="q-pa-md">
          <q-btn flat label="Cancel" color="primary" @click="closeDialog" />
          <q-btn
            flat
            label="Save"
            color="positive"
            @click="saveMapping"
            :loading="saving"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useQuasar } from 'quasar';
import { priceListAPI } from '../services/api';

const $q = useQuasar();

// State
const loading = ref(false);
const mappings = ref([]);
const searchTerm = ref('');
const showInactive = ref(false);
const showUnmappedOnly = ref(false);
const showDialog = ref(false);
const editingMapping = ref(null);
const saving = ref(false);
const deletingId = ref(null);
const fileInput = ref(null);
const uploading = ref(false);
const drgCodeOptions = ref([]);
const loadingDrgCodes = ref(false);

// Form data
const formData = ref({
  drg_code: '',
  drg_description: '',
  icd10_code: '',
  icd10_description: '',
  notes: '',
  remarks: '',
  is_active: true,
});

// Table columns
const columns = [
  {
    name: 'drg_code',
    label: 'DRG Code',
    field: 'drg_code',
    align: 'left',
    sortable: true,
  },
  {
    name: 'drg_description',
    label: 'DRG Description',
    field: 'drg_description',
    align: 'left',
    sortable: true,
    style: 'max-width: 200px; white-space: normal;',
  },
  {
    name: 'icd10_code',
    label: 'ICD-10 Code',
    field: 'icd10_code',
    align: 'left',
    sortable: true,
  },
  {
    name: 'icd10_description',
    label: 'ICD-10 Description',
    field: 'icd10_description',
    align: 'left',
    sortable: true,
    style: 'max-width: 200px; white-space: normal;',
  },
  {
    name: 'notes',
    label: 'Notes',
    field: 'notes',
    align: 'left',
    sortable: false,
    style: 'max-width: 150px; white-space: normal;',
  },
  {
    name: 'is_active',
    label: 'Status',
    field: 'is_active',
    align: 'center',
    sortable: true,
  },
  {
    name: 'actions',
    label: 'Actions',
    field: 'actions',
    align: 'center',
    sortable: false,
  },
];

// Pagination options
const rowsPerPageOptions = [
  { label: '25', value: 25 },
  { label: '50', value: 50 },
  { label: '100', value: 100 },
  { label: '200', value: 200 },
  { label: '500', value: 500 },
  { label: 'All', value: 0 }, // 0 means show all
];

// Pagination
const pagination = ref({
  sortBy: 'icd10_code',
  descending: false,
  page: 1,
  rowsPerPage: 100, // Increased default from 25 to 100
  rowsNumber: 0,
});

// Load mappings
const loadMappings = async (props = {}) => {
  loading.value = true;
  try {
    const page = props.pagination?.page || pagination.value.page;
    let rowsPerPage = props.pagination?.rowsPerPage || pagination.value.rowsPerPage;
    
    // If rowsPerPage is 0, fetch a large number (show all)
    const limit = rowsPerPage === 0 ? 10000 : rowsPerPage;
    const skip = rowsPerPage === 0 ? 0 : (page - 1) * rowsPerPage;

    // Pass is_active filter to backend (true = only active, null = all)
    const isActiveFilter = showInactive.value ? null : true;
    
    // Pass unmapped_only filter
    const unmappedOnly = showUnmappedOnly.value;

    const response = await priceListAPI.getIcd10DrgMappings(
      skip,
      limit,
      searchTerm.value || null,
      isActiveFilter,
      unmappedOnly
    );

    const items = response.data.items || [];
    const total = response.data.total || 0;

    mappings.value = items;
    pagination.value.rowsNumber = total;
    pagination.value.page = rowsPerPage === 0 ? 1 : page;
    pagination.value.rowsPerPage = rowsPerPage;
  } catch (error) {
    console.error('Error loading mappings:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to load mappings',
    });
  } finally {
    loading.value = false;
  }
};

// Handle table request (pagination, sorting)
const onRequest = (props) => {
  pagination.value = props.pagination;
  loadMappings(props);
};

// Filter DRG codes
const filterDrgCodes = async (val, update) => {
  if (val === '') {
    update(() => {
      drgCodeOptions.value = [];
    });
    return;
  }
  
  loadingDrgCodes.value = true;
  try {
    const response = await priceListAPI.searchDrgCodes(val, 50);
    update(() => {
      drgCodeOptions.value = response.data || [];
    });
  } catch (error) {
    console.error('Error searching DRG codes:', error);
    update(() => {
      drgCodeOptions.value = [];
    });
  } finally {
    loadingDrgCodes.value = false;
  }
};

// Handle DRG code selection
const onDrgCodeSelected = (drgCode) => {
  if (!drgCode) return;
  
  // Find the selected DRG code option to get its description
  const selectedOption = drgCodeOptions.value.find(opt => opt.drg_code === drgCode);
  if (selectedOption && selectedOption.drg_description) {
    formData.value.drg_description = selectedOption.drg_description;
  } else {
    // If manually entered, clear description so user can enter it
    if (!selectedOption) {
      formData.value.drg_description = '';
    }
  }
};

// Handle manual DRG code entry
const createDrgCode = (val, done) => {
  if (val.length > 0) {
    // Add the manually entered value as an option
    const newOption = {
      drg_code: val,
      drg_description: ''
    };
    if (!drgCodeOptions.value.find(opt => opt.drg_code === val)) {
      drgCodeOptions.value.push(newOption);
    }
    done(val, 'add-unique');
  }
};

// Open dialog for add/edit
const openDialog = (mapping) => {
  editingMapping.value = mapping;
  if (mapping) {
    formData.value = {
      drg_code: mapping.drg_code || '',
      drg_description: mapping.drg_description || '',
      icd10_code: mapping.icd10_code || '',
      icd10_description: mapping.icd10_description || '',
      notes: mapping.notes || '',
      remarks: mapping.remarks || '',
      is_active: mapping.is_active !== undefined ? mapping.is_active : true,
    };
    // Pre-populate DRG code options if editing
    if (mapping.drg_code) {
      drgCodeOptions.value = [{
        drg_code: mapping.drg_code,
        drg_description: mapping.drg_description || ''
      }];
    }
  } else {
    formData.value = {
      drg_code: '',
      drg_description: '',
      icd10_code: '',
      icd10_description: '',
      notes: '',
      remarks: '',
      is_active: true,
    };
    drgCodeOptions.value = [];
  }
  showDialog.value = true;
};

// Close dialog
const closeDialog = () => {
  showDialog.value = false;
  editingMapping.value = null;
  formData.value = {
    drg_code: '',
    drg_description: '',
    icd10_code: '',
    icd10_description: '',
    notes: '',
    remarks: '',
    is_active: true,
  };
};

// Save mapping
const saveMapping = async () => {
  if (!formData.value.icd10_code) {
    $q.notify({
      type: 'negative',
      message: 'ICD-10 code is required',
    });
    return;
  }
  
  // DRG code is optional for unmapped ICD-10 codes
  // But if it's a new mapping (not editing an unmapped one), require DRG code
  if (!editingMapping && !formData.value.drg_code) {
    $q.notify({
      type: 'negative',
      message: 'DRG code is required for new mappings',
    });
    return;
  }

  saving.value = true;
  try {
    if (editingMapping.value) {
      await priceListAPI.updateIcd10DrgMapping(editingMapping.value.id, formData.value);
      $q.notify({
        type: 'positive',
        message: 'Mapping updated successfully',
      });
    } else {
      await priceListAPI.createIcd10DrgMapping(formData.value);
      $q.notify({
        type: 'positive',
        message: 'Mapping created successfully',
      });
    }
    closeDialog();
    await loadMappings();
  } catch (error) {
    console.error('Error saving mapping:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to save mapping',
    });
  } finally {
    saving.value = false;
  }
};

// Confirm delete
const confirmDelete = (mapping) => {
  $q.dialog({
    title: 'Confirm Delete',
    message: `Are you sure you want to delete the mapping between DRG code "${mapping.drg_code}" and ICD-10 code "${mapping.icd10_code}"?`,
    cancel: true,
    persistent: true,
  }).onOk(() => {
    deleteMapping(mapping);
  });
};

// Delete mapping
const deleteMapping = async (mapping) => {
  deletingId.value = mapping.id;
  try {
    await priceListAPI.deleteIcd10DrgMapping(mapping.id);
    $q.notify({
      type: 'positive',
      message: 'Mapping deleted successfully',
    });
    await loadMappings();
  } catch (error) {
    console.error('Error deleting mapping:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to delete mapping',
    });
  } finally {
    deletingId.value = null;
  }
};

// Download mappings as CSV
const downloadMappings = async () => {
  try {
    const isActiveFilter = showInactive.value ? null : true;
    const params = {};
    if (isActiveFilter !== null) {
      params.is_active = isActiveFilter;
    }
    
    const response = await priceListAPI.exportIcd10DrgMapping(params);
    
    // Create blob and download
    const blob = new Blob([response.data], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'icd10_drg_mapping.csv';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
    
    $q.notify({
      type: 'positive',
      message: 'Mappings downloaded successfully',
    });
  } catch (error) {
    console.error('Error downloading mappings:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to download mappings',
    });
  }
};

// Trigger file upload
const triggerFileUpload = () => {
  fileInput.value?.click();
};

// Handle file upload
const handleFileUpload = async (event) => {
  const file = event.target.files?.[0];
  if (!file) return;
  
  uploading.value = true;
  try {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await priceListAPI.uploadIcd10Mapping(file);
    
    $q.notify({
      type: 'positive',
      message: response.data.summary || 'File uploaded successfully',
      timeout: 5000,
    });
    
    // Reload mappings
    await loadMappings();
    
    // Reset file input
    if (fileInput.value) {
      fileInput.value.value = '';
    }
  } catch (error) {
    console.error('Error uploading file:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to upload file',
      timeout: 5000,
    });
  } finally {
    uploading.value = false;
  }
};

// Initialize
onMounted(() => {
  loadMappings();
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

