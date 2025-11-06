<template>
  <q-page class="q-pa-md">
    <div class="text-h4 q-mb-md text-weight-bold glass-text">Price List Management</div>
    <q-banner class="glass-card q-pa-md q-mb-md">
      <template v-slot:avatar>
        <q-icon name="info" color="primary" />
      </template>
      Upload and manage services, products, medications, and surgery codes with their prices.
      DRG codes can be uploaded here for diagnoses selection in consultations.
    </q-banner>

    <!-- Upload Price List -->
    <q-card class="q-mb-md glass-card" flat>
      <q-card-section>
        <div class="text-h6 q-mb-md glass-text">Upload Price List</div>
        <div class="row q-gutter-md">
          <q-select
            v-model="uploadFileType"
            :options="fileTypes"
            label="File Type *"
            class="col-12 col-md-3"
            filled
            lazy-rules
            :rules="[(val) => !!val || 'Required']"
            hint="Select the type of file being uploaded"
          />
          <q-file
            v-model="priceListFile"
            label="Select Excel File (.xlsx, .xls)"
            accept=".xlsx,.xls"
            class="col-12 col-md-6"
            filled
          >
            <template v-slot:prepend>
              <q-icon name="attach_file" />
            </template>
          </q-file>
          <q-btn
            v-if="uploadFileType !== 'product'"
            color="primary"
            label="Upload"
            @click="uploadPriceList"
            :loading="uploading"
            :disable="!priceListFile || !uploadFileType"
            class="col-12 col-md-3"
            icon="upload"
          />
          <div v-if="uploadFileType === 'product'" class="col-12 col-md-3 q-gutter-sm">
            <q-btn
              color="primary"
              label="Upload"
              @click="uploadPriceList"
              :loading="uploading"
              :disable="!priceListFile || !uploadFileType"
              icon="upload"
            />
            <q-btn
              color="secondary"
              label="Download CSV"
              @click="downloadProductCSV"
              :loading="downloadingCSV"
              icon="download"
            />
          </div>
        </div>
        <div class="q-mt-md">
          <q-banner class="bg-grey-2">
            <div class="text-caption">
              <strong>Excel File Format:</strong><br/>
              <strong>For Procedure/Surgery/Unmapped DRG files:</strong><br/>
              • <strong>G-DRG Code:</strong> Service code (required)<br/>
              • <strong>Service Type:</strong> Department/Clinic (e.g., General, Pediatrics, ENT) - This is used as the category<br/>
              • <strong>Service Name:</strong> Procedure/service name (required)<br/>
              • <strong>Base Rate:</strong> What cash patients pay<br/>
              • <strong>NHIA App:</strong> Amount NHIA covers/approves<br/>
              • <strong>NHIA Claim Co-Payment:</strong> Top-up amount that insured patients pay (in addition to what NHIA covers)<br/>
              <br/>
              <strong>For Product (Medication) files:</strong><br/>
              • <strong>Product N:</strong> Product name with embedded medication code, e.g., "Allopurinol (300 mg) (ALLOPUTA2 | Allopurinol )"<br/>
              • The medication code (e.g., ALLOPUTA2) is automatically extracted from the Product Name column<br/>
              • <strong>Sub Categ:</strong> Sub category columns (may appear twice)<br/>
              • <strong>Product ID:</strong> Product identifier<br/>
              • <strong>Formulati:</strong> Formulation type<br/>
              • <strong>Strength:</strong> Medication strength<br/>
              • <strong>Base Rate:</strong> What cash patients pay<br/>
              • <strong>NHIA App:</strong> Amount NHIA covers/approves<br/>
              • <strong>Claim Am, NHIA Clain, Bill Effecti:</strong> Additional claim and billing fields<br/>
              • <strong>Insurance Covered:</strong> "yes" or "no" - If "no", product will always charge base_rate regardless of patient insurance status<br/>
              <br/>
              <strong>Note:</strong> For insured patients on procedures/surgeries, they pay the Co-Payment amount, and NHIA covers the NHIA App amount.<br/>
              For products (medications) with insurance_covered="yes", insured patients pay the Co-Payment (if available) or 0. Products with insurance_covered="no" always charge base_rate to all patients.<br/>
              • <strong>All other columns:</strong> Will be preserved in the database<br/>
              <br/>
              <strong>File Types:</strong><br/>
              • <strong>procedure:</strong> Procedure price Excel file<br/>
              • <strong>surgery:</strong> Surgery price Excel file<br/>
              • <strong>product:</strong> Product/Medication price Excel file (with embedded medication codes)<br/>
              • <strong>unmapped_drg:</strong> Unmapped DRG price Excel file<br/>
              <br/>
              <strong>Note:</strong> Each file type is stored in a separate table. The "Service Type" column from your Excel file will be used as the category/department.
            </div>
          </q-banner>
        </div>
      </q-card-section>
    </q-card>

    <!-- Upload ICD-10 Mapping -->
    <q-card class="q-mb-md glass-card" flat>
      <q-card-section>
        <div class="text-h6 q-mb-md glass-text">Upload ICD-10 to DRG Code Mapping</div>
        <q-banner rounded class="bg-blue-1 q-mb-md">
          <div class="text-body2">
            <strong>CSV Format:</strong> Upload a CSV file mapping ICD-10 codes to DRG codes.<br/>
            <strong>Columns:</strong> DRG Code, DRG Description, ICD-10 Code, ICD-10 Description, Notes, Remarks<br/>
            <strong>Note:</strong> This will create mappings between ICD-10 codes and existing DRG codes without modifying any prices.
          </div>
        </q-banner>
        <div class="row q-gutter-md">
          <q-file
            v-model="icd10MappingFile"
            label="Select CSV File"
            accept=".csv"
            class="col-12 col-md-8"
            filled
            clearable
          >
            <template v-slot:prepend>
              <q-icon name="attach_file" />
            </template>
          </q-file>
          <q-btn
            color="secondary"
            label="Upload ICD-10 Mapping"
            @click="uploadIcd10Mapping"
            :loading="uploadingIcd10"
            :disable="!icd10MappingFile"
            class="col-12 col-md-4"
            icon="upload"
          />
        </div>
        
        <!-- ICD-10 Upload Results -->
        <div v-if="icd10UploadResults" class="q-mt-md">
          <q-banner 
            :class="icd10UploadResults.imported > 0 ? 'bg-green-1' : 'bg-red-1'"
            rounded
            class="q-mb-md"
          >
            <div class="text-body1">
              <strong>Summary:</strong><br>
              Total rows: {{ icd10UploadResults.total }}<br>
              Successfully imported: {{ icd10UploadResults.imported }}<br>
              Failed: {{ icd10UploadResults.failed }}<br>
              <span v-if="icd10UploadResults.skipped_no_drg">Skipped (no DRG code): {{ icd10UploadResults.skipped_no_drg }}<br></span>
              <span v-if="icd10UploadResults.skipped_no_icd10">Skipped (no ICD-10 code): {{ icd10UploadResults.skipped_no_icd10 }}</span>
            </div>
          </q-banner>
        </div>
      </q-card-section>
    </q-card>

    <!-- Search and View Price List -->
    <q-card>
      <q-card-section>
        <div class="text-h6 q-mb-md">Price List Items</div>
        <div class="row q-gutter-md q-mb-md">
          <q-input
            v-model="searchTerm"
            filled
            label="Search by G-DRG Code or Service Name"
            class="col-12 col-md-4"
            clearable
            @keyup.enter="searchItems"
            @clear="searchItems"
          />
          <q-select
            v-model="searchServiceType"
            :options="serviceTypeOptions"
            label="Filter by Service Type (Department/Clinic)"
            class="col-12 col-md-3"
            filled
            clearable
            use-input
            input-debounce="300"
            @filter="filterServiceTypes"
            @update:model-value="searchItems"
            hint="Filter by department/clinic from Excel"
          />
          <q-select
            v-model="searchFileType"
            :options="['All', ...fileTypes]"
            label="Filter by File Type"
            class="col-12 col-md-3"
            filled
            clearable
            @update:model-value="searchItems"
          />
          <q-btn
            color="primary"
            label="Search"
            @click="searchItems"
            icon="search"
            class="col-12 col-md-2"
          />
        </div>

        <q-table
          :rows="priceListItems"
          :columns="priceColumns"
          row-key="id"
          flat
          :loading="loading"
          :pagination="{ rowsPerPage: 20 }"
        >
          <template v-slot:body-cell-actions="props">
            <q-td :props="props">
              <q-btn size="sm" color="primary" icon="edit" flat @click="openEditItem(props.row)" />
            </q-td>
          </template>
          <template v-slot:body-cell-file_type="props">
            <q-td :props="props">
              <q-badge :color="getFileTypeColor(props.value)" :label="props.value" />
            </q-td>
          </template>
          <template v-slot:body-cell-service_type="props">
            <q-td :props="props">
              <q-badge v-if="props.value" color="blue" :label="props.value" />
              <span v-else class="text-grey">N/A</span>
            </q-td>
          </template>
          <template v-slot:body-cell-base_rate="props">
            <q-td :props="props">
              {{ formatCurrency(props.value) }}
            </q-td>
          </template>
          <template v-slot:body-cell-nhia_app="props">
            <q-td :props="props">
              {{ props.value ? formatCurrency(props.value) : 'N/A' }}
            </q-td>
          </template>
          <template v-slot:body-cell-nhia_claim_co_payment="props">
            <q-td :props="props">
              {{ props.value ? formatCurrency(props.value) : 'N/A' }}
            </q-td>
          </template>
          <template v-slot:body-cell-insurance_covered="props">
            <q-td :props="props">
              <q-badge 
                v-if="props.row.file_type === 'product'"
                :color="props.value && props.value.toLowerCase() === 'no' ? 'negative' : 'positive'"
                :label="props.value && props.value.toLowerCase() === 'no' ? 'No' : 'Yes'"
              />
              <span v-else class="text-grey">N/A</span>
            </q-td>
          </template>
          <template v-slot:no-data>
            <div class="full-width row justify-center items-center text-grey q-gutter-sm q-pa-md">
              <q-icon name="inbox" size="2em" />
              <span>No price list items found. Upload a price list file to get started.</span>
            </div>
          </template>
        </q-table>
      </q-card-section>
    </q-card>
    <q-dialog v-model="showEditDialog">
      <q-card style="min-width: 500px">
        <q-card-section>
          <div class="text-h6">Edit Price Item</div>
        </q-card-section>
        <q-card-section>
          <div class="q-gutter-md">
            <q-input v-if="editingItem?.file_type === 'product'" v-model="editForm.product_name" filled label="Product Name" />
            <q-input v-else v-model="editForm.service_name" filled label="Service Name" />
            <q-input v-if="editingItem?.file_type !== 'product'" v-model="editForm.service_type" filled label="Service Type (Department)" />
            <q-input v-model.number="editForm.base_rate" type="number" filled label="Base Rate" />
            <q-input v-model.number="editForm.nhia_app" type="number" filled label="NHIA App" />
            <q-input v-model.number="editForm.nhia_claim_co_payment" type="number" filled label="Co-Payment" hint="For insured patients (with CCC). If null, patient pays 0 (free)." />
            <q-input v-if="editingItem?.file_type === 'product'" v-model.number="editForm.claim_amount" type="number" filled label="Claim Amount (Products)" />
            <q-select 
              v-if="editingItem?.file_type === 'product'"
              v-model="editForm.insurance_covered"
              :options="insuranceCoveredOptions"
              filled
              label="Insurance Covered"
              hint="If 'No', product will always charge base_rate regardless of patient insurance status"
            />
            <q-toggle v-model="editForm.is_active" label="Active" />
          </div>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Cancel" v-close-popup />
          <q-btn color="primary" label="Save" @click="saveEditItem" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useBillingStore } from '../stores/billing';
import { useQuasar } from 'quasar';
import { useAuthStore } from '../stores/auth';
import { useRouter } from 'vue-router';
import { priceListAPI } from '../services/api';

const $q = useQuasar();
const router = useRouter();
const billingStore = useBillingStore();
const authStore = useAuthStore();

// Check if user is admin or pharmacy head
if (!authStore.canAccess(['Admin', 'Pharmacy Head'])) {
  router.push('/dashboard');
}

const uploadFileType = ref('');
const priceListFile = ref(null);
const uploading = ref(false);
const icd10MappingFile = ref(null);
const uploadingIcd10 = ref(false);
const icd10UploadResults = ref(null);
const searchTerm = ref('');
const searchServiceType = ref(null);
const searchFileType = ref(null);
const loading = ref(false);
const serviceTypeOptions = ref([]);

const fileTypes = ['procedure', 'surgery', 'product', 'unmapped_drg'];
const priceListItems = ref([]);

const priceColumns = [
  { name: 'file_type', label: 'File Type', field: 'file_type', align: 'left', sortable: true },
  { name: 'g_drg_code', label: 'Code (G-DRG/Medication)', field: 'g_drg_code', align: 'left', sortable: true },
  { name: 'service_name', label: 'Name (Service/Product)', field: 'service_name', align: 'left', sortable: true },
  { name: 'service_type', label: 'Category/Dept', field: 'service_type', align: 'left', sortable: true },
  { name: 'base_rate', label: 'Base Rate (Cash)', field: 'base_rate', align: 'right', sortable: true },
  { name: 'nhia_app', label: 'NHIA App', field: 'nhia_app', align: 'right', sortable: true },
  { name: 'nhia_claim_co_payment', label: 'Co-Payment', field: 'nhia_claim_co_payment', align: 'right', sortable: true },
  { name: 'insurance_covered', label: 'Insurance Covered', field: 'insurance_covered', align: 'center', sortable: true },
  { name: 'actions', label: 'Actions', field: 'actions', align: 'center' },
];

const getFileTypeColor = (fileType) => {
  const colors = {
    procedure: 'blue',
    surgery: 'red',
    product: 'green',
    unmapped_drg: 'purple',
  };
  return colors[fileType] || 'grey';
};

const filterServiceTypes = (val, update) => {
  // Extract unique service types from loaded items
  const allServiceTypes = [...new Set(priceListItems.value.map(item => item.service_type).filter(Boolean))];
  update(() => {
    if (val === '') {
      serviceTypeOptions.value = allServiceTypes;
    } else {
      serviceTypeOptions.value = allServiceTypes.filter(v => 
        v.toLowerCase().includes(val.toLowerCase())
      );
    }
  });
};

const formatCurrency = (amount) => {
  if (!amount && amount !== 0) return 'N/A';
  return new Intl.NumberFormat('en-GH', {
    style: 'currency',
    currency: 'GHS',
  }).format(amount);
};

const uploadPriceList = async () => {
  if (!priceListFile.value || !uploadFileType.value) {
    $q.notify({
      type: 'warning',
      message: 'Please select a file and file type',
    });
    return;
  }

  uploading.value = true;
  try {
    const result = await billingStore.uploadPriceList(uploadFileType.value, priceListFile.value);
    priceListFile.value = null;
    uploadFileType.value = '';
    // Reload price list items
    await searchItems();
  } catch (error) {
    // Error handled in store
  } finally {
    uploading.value = false;
  }
};

const searchItems = async () => {
  loading.value = true;
  try {
    const serviceType = searchServiceType.value || null;
    const fileType = searchFileType.value === 'All' || !searchFileType.value ? null : searchFileType.value;
    const items = await billingStore.searchPriceItems(searchTerm.value || '', serviceType, fileType);
    priceListItems.value = items;
    // Update service type options for autocomplete
    const allServiceTypes = [...new Set(items.map(item => item.service_type).filter(Boolean))];
    serviceTypeOptions.value = allServiceTypes;
  } catch (error) {
    // Error handled in store
    priceListItems.value = [];
  } finally {
    loading.value = false;
  }
};

const downloadProductCSV = async () => {
  downloadingCSV.value = true;
  try {
    const response = await priceListAPI.exportProductCSV();
    
    // Create blob from response
    const blob = response.data instanceof Blob 
      ? response.data 
      : new Blob([response.data], { type: 'text/csv' });
    
    // Create download link
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'product_price_list.csv';
    document.body.appendChild(a);
    a.click();
    
    // Clean up
    setTimeout(() => {
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    }, 100);
    
    $q.notify({
      type: 'positive',
      message: 'Product price list downloaded successfully',
    });
  } catch (error) {
    console.error('Download error:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to download product price list',
    });
  } finally {
    downloadingCSV.value = false;
  }
};

onMounted(() => {
  searchItems(); // Load all items initially
});

// Edit dialog
const showEditDialog = ref(false);
const editingItem = ref(null);
const editForm = ref({});

const insuranceCoveredOptions = ['yes', 'no'];

const openEditItem = (row) => {
  editingItem.value = row;
  // Prime editForm with allowed fields by type
  if (row.file_type === 'product') {
    editForm.value = {
      product_name: row.service_name,
      base_rate: row.base_rate,
      nhia_app: row.nhia_app,
      nhia_claim_co_payment: row.nhia_claim_co_payment || null,
      claim_amount: row.claim_amount || null,
      insurance_covered: row.insurance_covered || 'yes',
      is_active: row.is_active ?? true,
    };
  } else {
    editForm.value = {
      service_name: row.service_name,
      service_type: row.service_type,
      base_rate: row.base_rate,
      nhia_app: row.nhia_app,
      nhia_claim_co_payment: row.nhia_claim_co_payment || null,
      is_active: row.is_active ?? true,
    };
  }
  showEditDialog.value = true;
};

const saveEditItem = async () => {
  try {
    await billingStore.updatePriceItem(editingItem.value.file_type, editingItem.value.id, editForm.value);
    showEditDialog.value = false;
    await searchItems();
  } catch (e) {}
};

const uploadIcd10Mapping = async () => {
  if (!icd10MappingFile.value) {
    $q.notify({
      type: 'warning',
      message: 'Please select a CSV file',
    });
    return;
  }

  uploadingIcd10.value = true;
  icd10UploadResults.value = null;

  try {
    const response = await priceListAPI.uploadIcd10Mapping(icd10MappingFile.value);
    icd10UploadResults.value = response.data;

    if (response.data.imported > 0) {
      $q.notify({
        type: 'positive',
        message: `Successfully imported ${response.data.imported} ICD-10 mapping(s)`,
        position: 'top',
      });
    }

    if (response.data.failed > 0) {
      $q.notify({
        type: 'warning',
        message: `${response.data.failed} row(s) failed to import. Check the errors in the results.`,
        position: 'top',
      });
    }
  } catch (error) {
    console.error('ICD-10 upload error:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || error.message || 'Failed to upload ICD-10 mapping file',
      position: 'top',
    });
  } finally {
    uploadingIcd10.value = false;
  }
};
</script>

