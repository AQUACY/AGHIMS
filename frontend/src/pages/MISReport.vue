<template>
  <q-page class="q-pa-md">
    <div class="text-h4 q-mb-md text-weight-bold glass-text">
      MIS Reports - DHIMS Platform
    </div>

    <div class="text-subtitle1 text-secondary q-mb-lg">
      Generate and export reports for the District Health Information Management System
    </div>

    <!-- Report Selection and Filters -->
    <q-card class="q-mb-md glass-card" flat>
      <q-card-section>
        <div class="text-h6 q-mb-md glass-text">Report Configuration</div>
        
        <!-- Report Type Selection -->
        <div class="row q-gutter-md q-mb-md">
          <div class="col-12 col-md-6">
            <q-select
              v-model="selectedReport"
              :options="reportOptions"
              filled
              label="Select Report Type"
              emit-value
              map-options
            >
              <template v-slot:prepend>
                <q-icon name="assessment" />
              </template>
            </q-select>
          </div>
        </div>

        <!-- Date Range and Filters -->
        <div class="row q-gutter-md q-mb-md">
          <q-input
            v-model="startDate"
            filled
            type="date"
            label="Start Date"
            class="col-12 col-md-3"
            :rules="[val => !!val || 'Start date is required']"
          >
            <template v-slot:prepend>
              <q-icon name="event" />
            </template>
          </q-input>
          
          <q-input
            v-model="endDate"
            filled
            type="date"
            label="End Date"
            class="col-12 col-md-3"
            :rules="[val => !!val || 'End date is required']"
          >
            <template v-slot:prepend>
              <q-icon name="event" />
            </template>
          </q-input>

          <q-select
            v-model="selectedDepartments"
            :options="filteredDepartmentOptions"
            filled
            label="Departments (Optional - Multi-select)"
            class="col-12 col-md-3"
            multiple
            clearable
            emit-value
            map-options
            use-chips
            use-input
            input-debounce="0"
            @filter="filterDepartments"
          >
            <template v-slot:prepend>
              <q-icon name="local_hospital" />
            </template>
            <template v-slot:no-option>
              <q-item>
                <q-item-section class="text-grey">
                  No departments found
                </q-item-section>
              </q-item>
            </template>
          </q-select>

          <div class="col-12 col-md-3 row q-gutter-sm">
            <q-btn
              color="primary"
              label="View Data"
              icon="visibility"
              @click="loadReportData"
              :loading="loading"
              :disable="!canLoadReport"
              class="col glass-button"
            />
            <q-btn
              color="positive"
              label="Export Excel"
              icon="download"
              @click="exportReport"
              :loading="exporting"
              :disable="!canExport"
              class="col glass-button"
            />
          </div>
        </div>

        <!-- Report Info -->
        <q-banner v-if="reportInfo" class="bg-info text-white q-mt-md">
          <template v-slot:avatar>
            <q-icon name="info" />
          </template>
          {{ reportInfo }}
        </q-banner>
      </q-card-section>
    </q-card>

    <!-- Report Data Preview -->
    <q-card v-if="reportData.length > 0" class="glass-card" flat>
      <q-card-section>
        <div class="row items-center q-mb-md">
          <div class="text-h6 glass-text">
            Report Preview ({{ reportData.length }} records)
          </div>
          <q-space />
          <q-btn
            flat
            icon="refresh"
            label="Refresh"
            @click="loadReportData"
            class="glass-button"
          />
        </div>

        <q-table
          :rows="reportData"
          :columns="tableColumns"
          row-key="sr_no"
          flat
          :loading="loading"
          :pagination="{ rowsPerPage: 25 }"
          class="glass-table"
          :rows-per-page-options="[10, 25, 50, 100]"
        >
          <template v-slot:body-cell-principal_diagnosis="props">
            <q-td :props="props">
              <div class="text-caption" style="max-width: 300px; overflow: hidden; text-overflow: ellipsis;">
                {{ props.value || 'N/A' }}
              </div>
            </q-td>
          </template>

          <template v-slot:body-cell-additional_diagnosis="props">
            <q-td :props="props">
              <div class="text-caption" style="max-width: 300px; overflow: hidden; text-overflow: ellipsis;">
                {{ props.value || 'N/A' }}
              </div>
            </q-td>
          </template>

          <template v-slot:body-cell-test_results="props">
            <q-td :props="props">
              <div class="text-caption" style="max-width: 200px; overflow: hidden; text-overflow: ellipsis;">
                {{ props.value || 'N/A' }}
              </div>
            </q-td>
          </template>
        </q-table>
      </q-card-section>
    </q-card>

    <!-- Empty State -->
    <q-card v-else-if="!loading && hasSearched" class="glass-card" flat>
      <q-card-section class="text-center">
        <q-icon name="assessment" size="64px" color="grey-6" />
        <div class="text-subtitle1 q-mt-md glass-text">
          No data found for the selected criteria
        </div>
        <div class="text-caption text-secondary q-mt-sm">
          Try adjusting your date range or filters
        </div>
      </q-card-section>
    </q-card>
  </q-page>
</template>

<script>
import { ref, computed, onMounted } from 'vue';
import { useQuasar } from 'quasar';
import { misReportsAPI } from '../services/api';
import { priceListAPI } from '../services/api';

export default {
  name: 'MISReport',
  setup() {
    const $q = useQuasar();

    // State
    const selectedReport = ref('consulting_room_register');
    const startDate = ref('');
    const endDate = ref('');
    const selectedDepartments = ref([]);
    const departmentFilter = ref('');
    const filteredDepartmentOptions = ref([]);
    const reportData = ref([]);
    const loading = ref(false);
    const exporting = ref(false);
    const hasSearched = ref(false);
    const departmentOptions = ref([]);
    const reportInfo = ref('');

    // Report options
    const reportOptions = [
      {
        label: 'Consulting Room Register',
        value: 'consulting_room_register',
        description: 'OPD consultation register for DHIMS'
      },
      {
        label: 'Statement of Outpatient',
        value: 'statement_of_outpatient',
        description: 'Age-grouped outpatient statistics for DHIMS'
      },
      {
        label: 'OPD Morbidity Report',
        value: 'opd_morbidity',
        description: 'Disease-specific morbidity statistics by age and gender for DHIMS'
      }
    ];

    // Table columns for different reports
    const tableColumns = computed(() => {
      if (selectedReport.value === 'consulting_room_register') {
        return [
          {
            name: 'sr_no',
            label: 'Sr.No.',
            field: 'sr_no',
            align: 'left',
            sortable: true
          },
          {
            name: 'schedule_date',
            label: 'Schedule Date',
            field: 'schedule_date',
            align: 'left',
            sortable: true
          },
          {
            name: 'patient_no',
            label: 'Patient No.',
            field: 'patient_no',
            align: 'left',
            sortable: true
          },
          {
            name: 'insurance_no',
            label: 'Insurance No.',
            field: 'insurance_no',
            align: 'left',
            sortable: true
          },
          {
            name: 'patient_name',
            label: 'Patient Name',
            field: 'patient_name',
            align: 'left',
            sortable: true
          },
          {
            name: 'address',
            label: 'Address',
            field: 'address',
            align: 'left',
            sortable: false
          },
          {
            name: 'telephone',
            label: 'Telephone',
            field: 'telephone',
            align: 'left',
            sortable: false
          },
          {
            name: 'age',
            label: 'Age',
            field: 'age',
            align: 'left',
            sortable: false
          },
          {
            name: 'sex',
            label: 'Sex',
            field: 'sex',
            align: 'left',
            sortable: true
          },
          {
            name: 'test_results',
            label: 'Test Results',
            field: 'test_results',
            align: 'left',
            sortable: false
          },
          {
            name: 'principal_diagnosis',
            label: 'Principal Diagnosis',
            field: 'principal_diagnosis',
            align: 'left',
            sortable: false
          },
          {
            name: 'additional_diagnosis',
            label: 'Additional Diagnosis',
            field: 'additional_diagnosis',
            align: 'left',
            sortable: false
          },
          {
            name: 'pregnant_patient',
            label: 'Pregnant',
            field: 'pregnant_patient',
            align: 'center',
            sortable: true
          },
          {
            name: 'nhia_patient',
            label: 'NHIA',
            field: 'nhia_patient',
            align: 'center',
            sortable: true
          }
        ];
      } else if (selectedReport.value === 'statement_of_outpatient') {
        return [
          {
            name: 'sr_no',
            label: 'Sr.No.',
            field: 'sr_no',
            align: 'left',
            sortable: true
          },
          {
            name: 'age_group',
            label: 'Age Groups (Yrs.)',
            field: 'age_group',
            align: 'left',
            sortable: true
          },
          {
            name: 'insured_new_male',
            label: 'Insured NEW - Male',
            field: 'insured_new_male',
            align: 'center',
            sortable: true
          },
          {
            name: 'insured_new_female',
            label: 'Insured NEW - Female',
            field: 'insured_new_female',
            align: 'center',
            sortable: true
          },
          {
            name: 'insured_old_male',
            label: 'Insured OLD - Male',
            field: 'insured_old_male',
            align: 'center',
            sortable: true
          },
          {
            name: 'insured_old_female',
            label: 'Insured OLD - Female',
            field: 'insured_old_female',
            align: 'center',
            sortable: true
          },
          {
            name: 'non_insured_new_male',
            label: 'Non-Insured NEW - Male',
            field: 'non_insured_new_male',
            align: 'center',
            sortable: true
          },
          {
            name: 'non_insured_new_female',
            label: 'Non-Insured NEW - Female',
            field: 'non_insured_new_female',
            align: 'center',
            sortable: true
          },
          {
            name: 'non_insured_old_male',
            label: 'Non-Insured OLD - Male',
            field: 'non_insured_old_male',
            align: 'center',
            sortable: true
          },
          {
            name: 'non_insured_old_female',
            label: 'Non-Insured OLD - Female',
            field: 'non_insured_old_female',
            align: 'center',
            sortable: true
          },
          {
            name: 'total_male',
            label: 'Total - Male',
            field: 'total_male',
            align: 'center',
            sortable: true
          },
          {
            name: 'total_female',
            label: 'Total - Female',
            field: 'total_female',
            align: 'center',
            sortable: true
          }
        ];
      } else if (selectedReport.value === 'opd_morbidity') {
        return [
          {
            name: 'sr_no',
            label: 'Sr.No.',
            field: 'sr_no',
            align: 'left',
            sortable: true
          },
          {
            name: 'disease',
            label: 'Disease',
            field: 'disease',
            align: 'left',
            sortable: true
          },
          {
            name: 'male_total',
            label: 'Male Total',
            field: 'male_total',
            align: 'center',
            sortable: true
          },
          {
            name: 'female_total',
            label: 'Female Total',
            field: 'female_total',
            align: 'center',
            sortable: true
          },
          {
            name: 'grand_total',
            label: 'Grand Total',
            field: 'grand_total',
            align: 'center',
            sortable: true
          }
        ];
      }
      return [];
    });

    // Computed
    const canLoadReport = computed(() => {
      return selectedReport.value && startDate.value && endDate.value;
    });

    const canExport = computed(() => {
      return canLoadReport.value;
    });

    // Methods
    const loadDepartmentOptions = async () => {
      try {
        const response = await priceListAPI.getServiceTypes();
        const serviceTypes = response.data || [];
        departmentOptions.value = serviceTypes.map(st => ({
          label: st,
          value: st
        }));
        filteredDepartmentOptions.value = departmentOptions.value;
      } catch (error) {
        console.error('Failed to load departments:', error);
        departmentOptions.value = [];
        filteredDepartmentOptions.value = [];
      }
    };

    const filterDepartments = (val, update) => {
      if (val === '') {
        update(() => {
          filteredDepartmentOptions.value = departmentOptions.value;
        });
        return;
      }
      update(() => {
        const needle = val.toLowerCase();
        filteredDepartmentOptions.value = departmentOptions.value.filter(
          dept => dept.label.toLowerCase().indexOf(needle) > -1
        );
      });
    };

    const loadReportData = async () => {
      if (!canLoadReport.value) {
        $q.notify({
          type: 'warning',
          message: 'Please select a report type and date range',
          position: 'top'
        });
        return;
      }

      loading.value = true;
      hasSearched.value = true;
      reportData.value = [];
      reportInfo.value = '';

      try {
        let response;
        // Convert selected departments array to comma-separated string
        const departmentsStr = selectedDepartments.value && selectedDepartments.value.length > 0
          ? selectedDepartments.value.join(',')
          : null;
        
        if (selectedReport.value === 'consulting_room_register') {
          response = await misReportsAPI.getConsultingRoomRegister(
            startDate.value,
            endDate.value,
            departmentsStr
          );
          const data = response.data || {};
          reportData.value = data.data || [];
          const deptInfo = departmentsStr ? ` (${selectedDepartments.value.length} department(s))` : ' (All departments)';
          reportInfo.value = `Found ${data.total_records || 0} records for ${data.start_date} to ${data.end_date}${deptInfo}`;
        } else if (selectedReport.value === 'statement_of_outpatient') {
          response = await misReportsAPI.getStatementOfOutpatient(
            startDate.value,
            endDate.value,
            departmentsStr
          );
          const data = response.data || {};
          reportData.value = data.data || [];
          const totals = data.totals || {};
          const deptInfo = departmentsStr ? ` (${selectedDepartments.value.length} department(s))` : ' (All departments)';
          reportInfo.value = `Total: ${totals.total_male || 0} Male, ${totals.total_female || 0} Female patients for ${data.start_date} to ${data.end_date}${deptInfo}`;
        } else if (selectedReport.value === 'opd_morbidity') {
          response = await misReportsAPI.getOPDMorbidity(
            startDate.value,
            endDate.value,
            departmentsStr
          );
          const data = response.data || {};
          reportData.value = data.data || [];
          const deptInfo = departmentsStr ? ` (${selectedDepartments.value.length} department(s))` : ' (All departments)';
          const grandTotal = reportData.value.reduce((sum, r) => sum + (r.grand_total || 0), 0);
          reportInfo.value = `Total: ${grandTotal} cases across ${reportData.value.length} disease categories for ${data.start_date} to ${data.end_date}${deptInfo}`;
        }
        
        if (reportData.value.length === 0) {
          $q.notify({
            type: 'info',
            message: 'No records found for the selected criteria',
            position: 'top'
          });
        }
      } catch (error) {
        console.error('Error loading report data:', error);
        $q.notify({
          type: 'negative',
          message: error.response?.data?.detail || 'Failed to load report data',
          position: 'top'
        });
        reportData.value = [];
      } finally {
        loading.value = false;
      }
    };

    const exportReport = async () => {
      if (!canExport.value) {
        $q.notify({
          type: 'warning',
          message: 'Please select a report type and date range',
          position: 'top'
        });
        return;
      }

      exporting.value = true;

      try {
        let response;
        let filename;
        
        // Convert selected departments array to comma-separated string
        const departmentsStr = selectedDepartments.value && selectedDepartments.value.length > 0
          ? selectedDepartments.value.join(',')
          : null;
        
        if (selectedReport.value === 'consulting_room_register') {
          response = await misReportsAPI.exportConsultingRoomRegister(
            startDate.value,
            endDate.value,
            departmentsStr
          );
          const startFormatted = startDate.value.replace(/-/g, '_');
          const endFormatted = endDate.value.replace(/-/g, '_');
          filename = `CR_REGISTER_${startFormatted}_TO_${endFormatted}.xlsx`;
        } else if (selectedReport.value === 'statement_of_outpatient') {
          response = await misReportsAPI.exportStatementOfOutpatient(
            startDate.value,
            endDate.value,
            departmentsStr
          );
          const startFormatted = startDate.value.replace(/-/g, '_');
          const endFormatted = endDate.value.replace(/-/g, '_');
          filename = `STATEMENT_OF_OUTPATIENT_${startFormatted}_TO_${endFormatted}.xlsx`;
        } else if (selectedReport.value === 'opd_morbidity') {
          response = await misReportsAPI.exportOPDMorbidity(
            startDate.value,
            endDate.value,
            departmentsStr
          );
          const startFormatted = startDate.value.replace(/-/g, '_');
          const endFormatted = endDate.value.replace(/-/g, '_');
          filename = `OPD_MORBIDITY_${startFormatted}_TO_${endFormatted}.xlsx`;
        }

        // Create blob and download
        const blob = new Blob([response.data], {
          type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        });
        
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);

        $q.notify({
          type: 'positive',
          message: 'Report exported successfully',
          position: 'top'
        });
      } catch (error) {
        console.error('Error exporting report:', error);
        $q.notify({
          type: 'negative',
          message: error.response?.data?.detail || 'Failed to export report',
          position: 'top'
        });
      } finally {
        exporting.value = false;
      }
    };

    // Initialize
    onMounted(() => {
      loadDepartmentOptions();
      
      // Set default dates (current month)
      const today = new Date();
      const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
      const lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0);
      
      startDate.value = firstDay.toISOString().split('T')[0];
      endDate.value = lastDay.toISOString().split('T')[0];
    });

    return {
      selectedReport,
      startDate,
      endDate,
      selectedDepartments,
      reportData,
      loading,
      exporting,
      hasSearched,
      departmentOptions,
      filteredDepartmentOptions,
      reportOptions,
      tableColumns,
      reportInfo,
      canLoadReport,
      canExport,
      filterDepartments,
      loadReportData,
      exportReport
    };
  }
};
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

.glass-button {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
}

.glass-table {
  background: rgba(255, 255, 255, 0.02);
}
</style>

