<template>
  <q-page class="hms-page">
    <HmsPageHeader
      title="ICD-10 DRG mapping"
      subtitle="Search, upload, and maintain ICD-10 to DRG code mappings for claims and consultations."
    >
      <template #actions>
        <HmsButton variant="ghost" size="sm" @click="$router.back()">Back</HmsButton>
        <HmsButton variant="secondary" size="sm" @click="downloadMappings">Download CSV</HmsButton>
        <HmsButton variant="secondary" size="sm" @click="triggerFileUpload">Upload File</HmsButton>
        <HmsButton variant="primary" size="sm" @click="openDialog(null)">Add New Mapping</HmsButton>
      </template>
    </HmsPageHeader>

    <!-- Hidden file input for upload -->
    <input
      ref="fileInput"
      type="file"
      accept=".csv,.xlsx,.xls"
      style="display: none"
      @change="handleFileUpload"
    />

    <!-- Search and Filters -->
    <section class="diag-panel">
      <div class="panel-head">
        <div>
          <div class="panel-title">Filters</div>
          <div class="panel-sub">Search codes and descriptions; toggle inactive or unmapped rows</div>
        </div>
      </div>
      <div class="panel-body">
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
          <div class="col-12 col-md-3 flex items-center">
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
      </div>
    </section>

    <!-- Mappings Table -->
    <section class="diag-panel">
      <div class="panel-head">
        <div>
          <div class="panel-title">Mappings</div>
          <div class="panel-sub">Edit or delete ICD-10 ↔ DRG rows</div>
        </div>
      </div>
      <div class="panel-body table-wrap">
        <q-table
          :rows="mappings"
          :columns="columns"
          row-key="id"
          flat
          :loading="loading"
          :pagination="pagination"
          @request="onRequest"
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
      </div>
    </section>

    <!-- Add/Edit Dialog -->
    <q-dialog v-model="showDialog" persistent>
      <q-card style="min-width: 600px; max-width: 800px;">
        <q-card-section class="dialog-head">
          <div class="text-h6">
            {{ editingMapping ? 'Edit ICD-10 DRG Mapping' : 'Add New ICD-10 DRG Mapping' }}
          </div>
          <div v-if="!editingMapping" class="text-caption text-grey-7 q-mt-xs">
            One ICD-10 code can map to multiple DRGs. Select all applicable DRGs below.
          </div>
        </q-card-section>

        <q-card-section class="q-pt-none">
          <q-form @submit="saveMapping" class="q-gutter-md">
            <div class="row q-col-gutter-md">
              <div class="col-12 col-md-6">
                <q-select
                  v-if="!editingMapping"
                  v-model="formData.drg_codes"
                  :options="drgCodeOptions"
                  option-value="drg_code"
                  option-label="drg_code"
                  emit-value
                  map-options
                  multiple
                  use-chips
                  filled
                  use-input
                  input-debounce="300"
                  @filter="filterDrgCodes"
                  @update:model-value="onDrgCodesSelected"
                  @new-value="createDrgCodeMulti"
                  label="DRG Code(s) *"
                  hint="Select one or more DRGs for this ICD-10. Type to search or enter manually."
                  :rules="[val => (Array.isArray(val) && val.length > 0) || 'At least one DRG code is required']"
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
                <q-select
                  v-else
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
                  :label="!editingMapping.drg_code ? 'DRG Code (Optional - Currently Unmapped)' : 'DRG Code *'"
                  hint="Type to search (e.g., ASUR) or enter manually. Leave empty for unmapped ICD-10."
                  :rules="!editingMapping.drg_code ? [] : [val => !!val || 'DRG code is required']"
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
              :hint="editingMapping ? 'Description of the DRG code' : 'Optional shared description; each selected DRG keeps its own description when available'"
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
import HmsPageHeader from '../components/ui/HmsPageHeader.vue';
import HmsButton from '../components/ui/HmsButton.vue';

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
  drg_codes: [],
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

// Handle DRG code selection (edit / single)
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

// Handle multi-DRG selection (create)
const onDrgCodesSelected = (codes) => {
  const list = Array.isArray(codes) ? codes : [];
  if (list.length === 1) {
    const selectedOption = drgCodeOptions.value.find(opt => opt.drg_code === list[0]);
    if (selectedOption?.drg_description) {
      formData.value.drg_description = selectedOption.drg_description;
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

const createDrgCodeMulti = (val, done) => {
  if (val.length > 0) {
    const newOption = { drg_code: val, drg_description: '' };
    if (!drgCodeOptions.value.find(opt => opt.drg_code === val)) {
      drgCodeOptions.value.push(newOption);
    }
    const current = Array.isArray(formData.value.drg_codes) ? [...formData.value.drg_codes] : [];
    if (!current.includes(val)) current.push(val);
    formData.value.drg_codes = current;
    done(val, 'add-unique');
  }
};

// Open dialog for add/edit
const openDialog = (mapping) => {
  editingMapping.value = mapping;
  if (mapping) {
    formData.value = {
      drg_code: mapping.drg_code || '',
      drg_codes: mapping.drg_code ? [mapping.drg_code] : [],
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
      drg_codes: [],
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
    drg_codes: [],
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
  
  // DRG code is optional for unmapped ICD-10 codes when editing
  // New mappings require at least one DRG
  if (!editingMapping.value) {
    const codes = Array.isArray(formData.value.drg_codes)
      ? formData.value.drg_codes.map((c) => String(c || '').trim()).filter(Boolean)
      : [];
    if (!codes.length) {
      $q.notify({
        type: 'negative',
        message: 'Select at least one DRG code',
      });
      return;
    }
  }

  saving.value = true;
  try {
    if (editingMapping.value) {
      await priceListAPI.updateIcd10DrgMapping(editingMapping.value.id, {
        drg_code: formData.value.drg_code,
        drg_description: formData.value.drg_description,
        icd10_code: formData.value.icd10_code,
        icd10_description: formData.value.icd10_description,
        notes: formData.value.notes,
        remarks: formData.value.remarks,
        is_active: formData.value.is_active,
      });
      $q.notify({
        type: 'positive',
        message: 'Mapping updated successfully',
      });
    } else {
      const codes = Array.isArray(formData.value.drg_codes)
        ? formData.value.drg_codes.map((c) => String(c || '').trim()).filter(Boolean)
        : [];
      const uniqueCodes = [...new Set(codes)];
      let created = 0;
      let skipped = 0;
      for (const code of uniqueCodes) {
        const opt = drgCodeOptions.value.find((o) => o.drg_code === code);
        try {
          await priceListAPI.createIcd10DrgMapping({
            drg_code: code,
            drg_description: opt?.drg_description || formData.value.drg_description || '',
            icd10_code: formData.value.icd10_code,
            icd10_description: formData.value.icd10_description,
            notes: formData.value.notes,
            remarks: formData.value.remarks,
            is_active: formData.value.is_active,
          });
          created += 1;
        } catch (err) {
          const detail = err.response?.data?.detail || '';
          if (String(detail).toLowerCase().includes('already exists')) {
            skipped += 1;
          } else {
            throw err;
          }
        }
      }
      $q.notify({
        type: created ? 'positive' : 'warning',
        message: skipped
          ? `Created ${created} mapping(s); ${skipped} already existed`
          : `Created ${created} mapping(s) for ${formData.value.icd10_code}`,
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
.diag-panel {
  margin-bottom: 1rem;
  border: 1px solid var(--hms-border);
  border-radius: var(--hms-radius-xl);
  background: var(--hms-panel-bg);
  overflow: hidden;
}
.panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
  flex-wrap: wrap;
  padding: 0.85rem 1rem;
  border-bottom: 1px solid var(--hms-border);
}
.panel-title {
  font-size: var(--hms-text-base);
  font-weight: 750;
  color: var(--hms-text-primary);
}
.panel-sub {
  margin-top: 0.15rem;
  font-size: var(--hms-text-xs);
  color: var(--hms-text-muted);
}
.panel-body {
  padding: 1rem;
}
.table-wrap {
  padding-top: 0.5rem;
  overflow-x: auto;
}
.dialog-head {
  border-bottom: 1px solid var(--hms-border);
}
</style>

