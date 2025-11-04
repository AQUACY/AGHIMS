<template>
    <q-page class="q-pa-md">    
  <div class="upload-background" :class="themeStore.isDark ? 'dark-gradient' : 'light-gradient'">
    <div class="upload-container">
      <!-- Header -->
      <div class="upload-header">
        <div class="text-h5 text-weight-bold" style="color: rgba(255, 255, 255, 0.95);">
          Patient Data Import
        </div>
        <div class="text-subtitle2" style="color: rgba(255, 255, 255, 0.7);">
          Admin Only
        </div>
        <div class="q-mt-md">
          <q-btn
            flat
            icon="arrow_back"
            label="Back to Dashboard"
            color="white"
            @click="goToDashboard"
            class="q-mt-sm"
          />
        </div>
      </div>

      <q-card class="upload-card glass-card" flat>
      <q-card-section>
        <div class="text-h6 q-mb-md glass-text">Instructions</div>
        <q-banner rounded class=" q-mb-md">
          <div class="text-body2">
            <strong>CSV Template Format:</strong>
            <ul class="q-mt-sm q-ml-md">
              <li><strong>Required fields:</strong> name, gender (M or F)</li>
              <li><strong>Optional fields:</strong> surname, other_names, age, date_of_birth, card_number, insured, insurance_id, insurance_start_date, insurance_end_date, ccc_number, contact, address</li>
              <li><strong>Date formats:</strong> YYYY-MM-DD, DD/MM/YYYY, MM/DD/YYYY</li>
              <li><strong>Boolean values:</strong> TRUE, 1, YES, Y for true; FALSE, 0, NO, N for false</li>
              <li><strong>Card Number:</strong> Leave empty to auto-generate, or provide existing card number (must be unique)</li>
            </ul>
          </div>
        </q-banner>

        <div class="row q-gutter-md q-mb-md">
          <q-btn
            color="secondary"
            icon="download"
            label="Download Template"
            @click="downloadTemplate"
            class="glass-button"
          />
        </div>
      </q-card-section>

      <q-card-section>
        <div class="text-h6 q-mb-md glass-text">Upload CSV File</div>
        
        <q-file
          v-model="file"
          label="Select CSV File"
          accept=".csv"
          filled
          clearable
          class="q-mb-lg"
          :max-file-size="10485760"
          @rejected="onRejected"
        >
          <template v-slot:prepend>
            <q-icon name="attach_file" />
          </template>
        </q-file>

        <div class="row justify-center q-mt-md">
          <q-btn
            color="primary"
            icon="upload"
            label="Upload and Import"
            @click="uploadFile"
            :loading="uploading"
            :disable="!file"
            unelevated
            size="lg"
            class="upload-btn"
            style="min-width: 250px; font-weight: 600; padding: 12px 24px;"
          />
        </div>

        <div v-if="file" class="text-center q-mt-md">
          <q-chip color="positive" text-color="white" icon="check_circle">
            File selected: {{ file.name }}
          </q-chip>
        </div>
      </q-card-section>

      <!-- Upload Results -->
      <q-card-section v-if="uploadResults">
        <div class="text-h6 q-mb-md glass-text">Import Results</div>
        
        <q-banner 
          :class="uploadResults.imported > 0 ? 'bg-green-1' : 'bg-red-1'"
          rounded
          class="q-mb-md"
        >
          <div class="text-body1">
            <strong>Summary:</strong><br>
            Total rows: {{ uploadResults.total }}<br>
            Successfully imported: {{ uploadResults.imported }}<br>
            Failed: {{ uploadResults.failed }}
          </div>
        </q-banner>

        <!-- Success List -->
        <div v-if="uploadResults.success && uploadResults.success.length > 0" class="q-mb-md">
          <div class="text-subtitle1 q-mb-sm text-green">Successfully Imported ({{ uploadResults.success.length }})</div>
          <q-table
            :rows="uploadResults.success"
            :columns="successColumns"
            row-key="id"
            :rows-per-page-options="[10, 25, 50]"
            class="glass-card"
            flat
          />
        </div>

        <!-- Error List -->
        <div v-if="uploadResults.errors && uploadResults.errors.length > 0">
          <div class="text-subtitle1 q-mb-sm text-red">Errors ({{ uploadResults.errors.length }})</div>
          <q-table
            :rows="uploadResults.errors"
            :columns="errorColumns"
            row-key="row"
            :rows-per-page-options="[10, 25, 50]"
            class="glass-card"
            flat
          >
            <template v-slot:body-cell-error="props">
              <q-td :props="props">
                <div class="text-red">{{ props.value }}</div>
              </q-td>
            </template>
          </q-table>
        </div>

        <div class="row q-mt-md q-gutter-md">
          <q-btn
            color="primary"
            label="Import Another File"
            @click="resetForm"
            class="glass-button"
          />
        </div>
      </q-card-section>
      </q-card>
    </div>
  </div>
</q-page>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useQuasar } from 'quasar';
import { useThemeStore } from '../stores/theme';
import { patientsAPI } from '../services/api';

const $q = useQuasar();
const router = useRouter();
const themeStore = useThemeStore();

const file = ref(null);
const uploading = ref(false);
const uploadResults = ref(null);

const successColumns = [
  { name: 'row', label: 'Row', field: 'row', align: 'left' },
  { name: 'name', label: 'Name', field: 'name', align: 'left' },
  { name: 'card_number', label: 'Card Number', field: 'card_number', align: 'left' },
  { name: 'id', label: 'Patient ID', field: 'id', align: 'left' },
];

const errorColumns = [
  { name: 'row', label: 'Row', field: 'row', align: 'left' },
  { name: 'error', label: 'Error', field: 'error', align: 'left' },
];

const downloadTemplate = () => {
  // Create CSV template content
  const templateContent = `name,surname,other_names,gender,age,date_of_birth,card_number,insured,insurance_id,insurance_start_date,insurance_end_date,ccc_number,contact,address
John,Doe,Michael,M,35,1988-05-15,,TRUE,NHIS123456789,2020-01-01,2024-12-31,,0241234567,123 Main Street, Accra
Jane,Smith,,F,28,1995-08-20,,FALSE,,,,,0209876543,456 Oak Avenue, Kumasi
Kwame,Mensah,Kofi,M,,,ER-A25-AAA0001,FALSE,,,,,0501111111,789 High Street, Tamale`;

  // Create blob and download
  const blob = new Blob([templateContent], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  const url = URL.createObjectURL(blob);
  link.setAttribute('href', url);
  link.setAttribute('download', 'patient_import_template.csv');
  link.style.visibility = 'hidden';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
};

const onRejected = (rejectedEntries) => {
  const reasons = [];
  rejectedEntries.forEach((entry) => {
    if (entry.failedPropValidation === 'accept') {
      reasons.push('File must be a CSV file');
    }
    if (entry.failedPropValidation === 'max-file-size') {
      reasons.push('File size exceeds 10MB limit');
    }
  });
  
  $q.notify({
    type: 'negative',
    message: reasons.join(', ') || 'File rejected',
    position: 'top',
  });
};

const uploadFile = async () => {
  if (!file.value) {
    $q.notify({
      type: 'warning',
      message: 'Please select a CSV file',
      position: 'top',
    });
    return;
  }

  uploading.value = true;
  uploadResults.value = null;

  try {
    const response = await patientsAPI.import(file.value);
    const results = response.data;
    uploadResults.value = results;

    if (results.imported > 0) {
      $q.notify({
        type: 'positive',
        message: `Successfully imported ${results.imported} patient(s)`,
        position: 'top',
      });
    }

    if (results.failed > 0) {
      $q.notify({
        type: 'warning',
        message: `${results.failed} row(s) failed to import. Check the errors below.`,
        position: 'top',
      });
    }
  } catch (error) {
    console.error('Upload error:', error);
    $q.notify({
      type: 'negative',
      message: error.message || 'Failed to upload file',
      position: 'top',
    });
  } finally {
    uploading.value = false;
  }
};

const resetForm = () => {
  file.value = null;
  uploadResults.value = null;
};

const goToDashboard = () => {
  router.push('/');
};

onMounted(() => {
  themeStore.initTheme();
});
</script>

<style scoped>


.upload-container {
  min-height: 100vh;
  padding: 20px;
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  max-width: 1200px;
  margin: 0 auto;
}

.upload-header {
  width: 100%;
  text-align: center;
  margin-bottom: 30px;
  padding-top: 20px;
}

.upload-card {
  width: 100%;
  max-width: 1000px;
  padding: 24px;
}

.glass-text {
  color: rgba(255, 255, 255, 0.9);
}

.glass-card {
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.glass-button {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
}

.upload-btn {
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
}

.upload-btn:hover {
  box-shadow: 0 6px 12px rgba(0, 0, 0, 0.3);
}

:deep(.q-table) {
  background: rgba(255, 255, 255, 0.05) !important;
  color: rgba(255, 255, 255, 0.9) !important;
}

:deep(.q-table th) {
  background: rgba(255, 255, 255, 0.05) !important;
  color: rgba(255, 255, 255, 0.9) !important;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1) !important;
}

:deep(.q-table td) {
  border-bottom: 1px solid rgba(255, 255, 255, 0.1) !important;
  color: rgba(255, 255, 255, 0.9) !important;
}

:deep(.q-table tbody tr:hover) {
  background: rgba(255, 255, 255, 0.08) !important;
}

:deep(.q-field__control) {
  color: rgba(255, 255, 255, 0.9) !important;
}

:deep(.q-field__label) {
  color: rgba(255, 255, 255, 0.7) !important;
}

:deep(.q-file__input) {
  color: rgba(255, 255, 255, 0.9) !important;
}
</style>

