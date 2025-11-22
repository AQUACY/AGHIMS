<template>
  <div class="lab-result-viewer">
    <!-- Print Header (only visible when printing) -->
    <div class="print-header">
      <div class="logo-container">
        <img src="/logos/ministry-of-health-logo.png" alt="Ministry of Health" class="logo" onerror="this.style.display='none'">
        <img src="/logos/ghana-health-service-logo.png" alt="Ghana Health Service" class="logo" onerror="this.style.display='none'">
      </div>
      <div class="hospital-name">ASESEWA GOVERNMENT HOSPITAL</div>
      <div class="dept-name">LABORATORY DEPARTMENT</div>
      <div class="report-date">{{ formatDate(resultDate) }}</div>
    </div>
    
    <!-- Screen Header Section -->
    <div class="lab-result-header q-pa-md" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;">
      <div class="row items-center justify-between">
        <div class="col-auto">
          <div class="text-h5 text-weight-bold">{{ templateName || 'Lab Result' }}</div>
          <div class="text-subtitle2 q-mt-xs">{{ procedureName }}</div>
        </div>
        <div class="col-auto text-right">
          <div class="text-caption">Date: {{ formatDate(resultDate) }}</div>
          <div v-if="patientInfo" class="text-caption q-mt-xs">
            {{ patientInfo.name }} {{ patientInfo.surname }}
          </div>
        </div>
      </div>
    </div>

    <!-- Client Details Section -->
    <div v-if="patientInfo" class="q-pa-md" style="background: #f5f5f5; border-bottom: 2px solid #ddd;">
      <div class="text-subtitle1 q-mb-md text-weight-bold">Client Details</div>
      <div class="row q-gutter-md">
        <div class="col-12 col-md-3">
          <div class="text-caption text-grey-7">Name</div>
          <div class="text-body1 text-weight-medium">{{ patientInfo.name }} {{ patientInfo.surname || '' }}<span v-if="patientInfo.other_names"> {{ patientInfo.other_names }}</span></div>
        </div>
        <div class="col-12 col-md-3">
          <div class="text-caption text-grey-7">Card Number</div>
          <div class="text-body1 text-weight-medium">{{ patientInfo.card_number || 'N/A' }}</div>
        </div>
        <div class="col-12 col-md-3">
          <div class="text-caption text-grey-7">Age</div>
          <div class="text-body1 text-weight-medium">{{ patientInfo.age || 'N/A' }}</div>
        </div>
        <div class="col-12 col-md-3">
          <div class="text-caption text-grey-7">Sex</div>
          <div class="text-body1 text-weight-medium">{{ patientInfo.gender || 'N/A' }}</div>
        </div>
        <div class="col-12 col-md-3">
          <div class="text-caption text-grey-7">DOB</div>
          <div class="text-body1 text-weight-medium">{{ formatDateOnly(patientInfo.date_of_birth) || 'N/A' }}</div>
        </div>
        <div v-if="patientInfo.insurance_id" class="col-12 col-md-3">
          <div class="text-caption text-grey-7">Insurance ID</div>
          <div class="text-body1 text-weight-medium">{{ patientInfo.insurance_id }}</div>
        </div>
      </div>
    </div>

    <!-- Template Fields Section - Results with Reference Ranges -->
    <div v-if="templateStructure && templateData" class="q-pa-md">
      <div class="text-subtitle1 q-mb-md text-weight-bold">Test Results</div>
      <q-table
        :rows="formattedFields"
        :columns="fieldColumns"
        row-key="field_name"
        flat
        bordered
        :pagination="{ rowsPerPage: 0 }"
        class="lab-result-table"
      >
        <template v-slot:body-cell-value="props">
          <q-td :props="props">
            <span 
              :class="{
                'text-negative text-weight-bold': props.row.is_out_of_range,
                'text-primary': !props.row.is_out_of_range && props.row.value && props.row.value !== 'N/A'
              }"
              style="font-size: 1em;"
            >
              {{ props.row.display_value }}
            </span>
          </q-td>
        </template>
        <template v-slot:body-cell-reference="props">
          <q-td :props="props">
            <span class="text-grey-7" style="font-size: 0.9em;">{{ props.row.reference_range }}</span>
          </q-td>
        </template>
        <template v-slot:body-cell-unit="props">
          <q-td :props="props" class="text-center">
            <span class="text-grey-7" style="font-size: 0.9em;">{{ props.row.unit || '-' }}</span>
          </q-td>
        </template>
      </q-table>
    </div>

    <!-- Message Fields Section -->
    <div v-if="messageFields && messageFields.length > 0" class="q-pa-md" style="background: #f9f9f9;">
      <div class="text-subtitle1 q-mb-sm text-weight-bold">Additional Information</div>
      <div v-for="(msg, index) in messageFields" :key="index" class="q-mb-sm">
        <div class="text-caption text-grey-7">{{ msg.label || msg.field_name }}</div>
        <div class="text-body1 q-pa-sm" style="background: white; border-radius: 4px;">
          {{ getMessageValue(msg.field_name) || 'N/A' }}
        </div>
      </div>
    </div>

    <!-- Patient Fields Section -->
    <div v-if="patientFields && patientFields.length > 0" class="q-pa-md" style="background: #f9f9f9;">
      <div class="text-subtitle1 q-mb-sm text-weight-bold">Patient Details</div>
      <div class="row q-gutter-md">
        <div v-for="(field, index) in patientFields" :key="index" class="col-12 col-md-6">
          <div class="text-caption text-grey-7">{{ field.label || field.field_name }}</div>
          <div class="text-body1">{{ getPatientFieldValue(field.field_name) || 'N/A' }}</div>
        </div>
      </div>
    </div>

    <!-- Fallback: Non-template Results -->
    <div v-else-if="resultsText" class="q-pa-md">
      <div class="text-subtitle1 q-mb-sm">Results</div>
      <div class="text-body1 q-pa-md" style="background: #f5f5f5; border-radius: 4px; white-space: pre-wrap;">
        {{ resultsText }}
      </div>
    </div>

    <!-- Footer Section -->
    <div class="q-pa-md text-right" style="background: #f5f5f5; border-top: 2px solid #ddd;">
      <div class="text-caption text-grey-7">
        <span v-if="enteredBy">Entered by: {{ enteredBy }}</span>
        <span v-if="enteredBy && enteredAt"> | </span>
        <span v-if="enteredAt">Date: {{ formatDateTime(enteredAt) }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const formatDate = (dateString) => {
  if (!dateString) return '';
  const date = new Date(dateString);
  return date.toLocaleDateString('en-GB', { 
    day: '2-digit', 
    month: '2-digit', 
    year: 'numeric' 
  });
};

const formatDateOnly = (dateString) => {
  if (!dateString) return '';
  const date = new Date(dateString);
  return date.toLocaleDateString('en-GB', { 
    day: '2-digit', 
    month: '2-digit', 
    year: 'numeric' 
  });
};

const formatDateTime = (dateString) => {
  if (!dateString) return '';
  const date = new Date(dateString);
  return date.toLocaleString('en-GB', { 
    day: '2-digit', 
    month: '2-digit', 
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
};

const props = defineProps({
  templateStructure: {
    type: Object,
    default: null
  },
  templateData: {
    type: Object,
    default: null
  },
  resultsText: {
    type: String,
    default: null
  },
  patientInfo: {
    type: Object,
    default: null
  },
  procedureName: {
    type: String,
    default: ''
  },
  templateName: {
    type: String,
    default: ''
  },
  resultDate: {
    type: String,
    default: null
  },
  enteredBy: {
    type: String,
    default: null
  },
  enteredAt: {
    type: String,
    default: null
  }
});

const fieldColumns = [
  { name: 'field_name', label: 'Test', field: 'field_name', align: 'left', style: 'width: 35%' },
  { name: 'value', label: 'Result', field: 'display_value', align: 'left', style: 'width: 20%' },
  { name: 'unit', label: 'Unit', field: 'unit', align: 'center', style: 'width: 15%' },
  { name: 'reference', label: 'Reference Range', field: 'reference_range', align: 'left', style: 'width: 30%' }
];

const formattedFields = computed(() => {
  if (!props.templateStructure?.fields || !props.templateData) {
    return [];
  }

  return props.templateStructure.fields.map(field => {
    // Template uses 'name' as the field identifier, not 'field_name'
    const fieldName = field.name || field.field_name;
    
    // Get the actual value entered during result addition
    // Check both direct field name and field_values object structure
    let value = props.templateData[fieldName];
    if (value === undefined && props.templateData.field_values) {
      value = props.templateData.field_values[fieldName];
    }
    
    // Format the display value - show the actual entered value
    const displayValue = value !== null && value !== undefined && value !== '' ? String(value) : 'N/A';
    
    // Build reference range from reference_min and reference_max, or use reference_range if available
    let referenceRange = 'N/A';
    if (field.reference_range) {
      referenceRange = field.reference_range;
    } else if (field.reference_min !== undefined && field.reference_min !== null || 
               field.reference_max !== undefined && field.reference_max !== null) {
      const min = (field.reference_min !== undefined && field.reference_min !== null) ? field.reference_min : '';
      const max = (field.reference_max !== undefined && field.reference_max !== null) ? field.reference_max : '';
      if (min !== '' && max !== '') {
        referenceRange = `${min} - ${max}`;
      } else if (min !== '') {
        referenceRange = `≥ ${min}`;
      } else if (max !== '') {
        referenceRange = `≤ ${max}`;
      }
    }
    
    // Check if value is out of range for numeric fields
    let isOutOfRange = false;
    if ((field.type === 'number' || field.field_type === 'number' || field.type === 'numeric') && 
        value !== null && value !== undefined && value !== '') {
      const numValue = parseFloat(value);
      if (!isNaN(numValue)) {
        if (field.reference_min !== undefined && field.reference_min !== null && numValue < field.reference_min) {
          isOutOfRange = true;
        } else if (field.reference_max !== undefined && field.reference_max !== null && numValue > field.reference_max) {
          isOutOfRange = true;
        } else if (field.reference_range) {
          // Fallback: try parsing reference_range string
          const range = parseReferenceRange(field.reference_range);
          if (range) {
            if (range.min !== null && numValue < range.min) {
              isOutOfRange = true;
            } else if (range.max !== null && numValue > range.max) {
              isOutOfRange = true;
            }
          }
        }
      }
    }

    return {
      field_name: field.label || fieldName,
      display_value: displayValue,
      value: value,
      unit: field.unit || '',
      reference_range: referenceRange,
      is_out_of_range: isOutOfRange
    };
  });
});

const messageFields = computed(() => {
  return props.templateStructure?.message_fields || [];
});

const patientFields = computed(() => {
  return props.templateStructure?.patient_fields || [];
});

const parseReferenceRange = (rangeStr) => {
  if (!rangeStr) return null;
  
  // Try to parse formats like "3.5-5.5", ">10", "<5", "10-20"
  const match = rangeStr.match(/([<>]?)(\d+\.?\d*)\s*-\s*(\d+\.?\d*)|([<>])(\d+\.?\d*)/);
  if (match) {
    if (match[4]) {
      // Single bound (>10 or <5)
      return {
        min: match[4] === '>' ? parseFloat(match[5]) : null,
        max: match[4] === '<' ? parseFloat(match[5]) : null
      };
    } else {
      // Range (3.5-5.5)
      return {
        min: parseFloat(match[2]),
        max: parseFloat(match[3])
      };
    }
  }
  return null;
};

const getMessageValue = (fieldName) => {
  if (!props.templateData) return null;
  // Check both direct access and messages object
  if (props.templateData[fieldName] !== undefined) {
    return props.templateData[fieldName];
  }
  if (props.templateData.messages && props.templateData.messages[fieldName] !== undefined) {
    return props.templateData.messages[fieldName];
  }
  return null;
};

const getPatientFieldValue = (fieldName) => {
  if (!props.templateData) return null;
  // Check both direct access and patient_fields object
  if (props.templateData[fieldName] !== undefined) {
    return props.templateData[fieldName];
  }
  if (props.templateData.patient_fields && props.templateData.patient_fields[fieldName] !== undefined) {
    return props.templateData.patient_fields[fieldName];
  }
  return null;
};
</script>

<style scoped>
.lab-result-viewer {
  background: white;
  max-width: 210mm; /* A4 width */
  margin: 0 auto;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  padding: 20px;
}

.lab-result-header {
  border-radius: 4px 4px 0 0;
}

.lab-result-table :deep(.q-table__top) {
  display: none;
}

.lab-result-table :deep(.q-table tbody td) {
  padding: 12px 8px;
  border-bottom: 1px solid #e0e0e0;
}

.lab-result-table :deep(.q-table thead th) {
  background: #f5f5f5;
  font-weight: bold;
  border-bottom: 2px solid #ddd;
}

/* Print Header - Only visible when printing */
.print-header {
  display: none;
}

@media print {
  /* A4 Page setup - Standard margins */
  @page {
    size: A4;
    margin: 20mm 15mm;
  }
  
  html, body {
    width: 210mm;
    height: 297mm;
    margin: 0;
    padding: 0;
  }
  
  .lab-result-viewer {
    width: 180mm; /* 210mm - 30mm (left + right margins) */
    min-height: 257mm; /* 297mm - 40mm (top + bottom margins) */
    margin: 0 auto;
    padding: 0;
    box-shadow: none;
    background: white;
    position: relative;
  }
  
  /* Hide screen header when printing */
  .lab-result-header {
    display: none !important;
  }
  
  /* Show print header */
  .print-header {
    display: block !important;
    text-align: center;
    margin-bottom: 12mm;
    padding-bottom: 8mm;
    border-bottom: 2px solid #000;
  }
  
  .logo-container {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 12mm;
    margin-bottom: 6mm;
  }
  
  .logo {
    max-width: 45mm;
    max-height: 35mm;
    object-fit: contain;
  }
  
  .hospital-name {
    font-weight: bold;
    font-size: 14pt;
    margin: 4mm 0;
    text-transform: uppercase;
    letter-spacing: 0.5pt;
  }
  
  .dept-name {
    font-weight: bold;
    font-size: 12pt;
    margin-bottom: 4mm;
    text-transform: uppercase;
  }
  
  .report-date {
    font-size: 9pt;
    color: #666;
    margin-top: 2mm;
  }
  
  /* Client Details Section */
  .lab-result-viewer > div:nth-child(2) {
    margin-bottom: 8mm;
    padding: 4mm;
    font-size: 10pt;
  }
  
  /* Test Results Section */
  .lab-result-viewer > div:nth-child(3) {
    margin-bottom: 8mm;
    padding: 4mm;
  }
  
  /* Ensure proper page breaks */
  .lab-result-viewer {
    page-break-inside: avoid;
  }
  
  .lab-result-table {
    page-break-inside: auto;
    font-size: 9pt;
    width: 100%;
  }
  
  .lab-result-table :deep(tr) {
    page-break-inside: avoid;
    page-break-after: auto;
  }
  
  .lab-result-table :deep(td),
  .lab-result-table :deep(th) {
    padding: 2mm 3mm;
    font-size: 9pt;
  }
  
  /* Footer section */
  .lab-result-viewer > div:last-child {
    margin-top: 8mm;
    padding-top: 4mm;
    border-top: 1px solid #ddd;
    font-size: 8pt;
  }
  
  /* Text sizing for print */
  .lab-result-viewer .text-subtitle1 {
    font-size: 11pt;
  }
  
  .lab-result-viewer .text-body1 {
    font-size: 10pt;
  }
  
  .lab-result-viewer .text-caption {
    font-size: 8pt;
  }
}
</style>

