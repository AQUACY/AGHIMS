<template>
  <q-page class="hms-page">
    <HmsPageHeader
      :title="sheet ? 'Daily stocktaking sheet' : 'Stocktaking'"
      :subtitle="sheet
        ? 'Monday stocktake plus what this shift received, minus Friday closing balance, should match the GHIMS dispense report.'
        : 'One sheet per shift for the week. Dispensing stays in GHIMS.'"
    >
      <template #actions>
        <HmsButton v-if="sheet" variant="ghost" size="sm" @click="backToList">All sheets</HmsButton>
        <template v-else>
          <HmsButton variant="secondary" size="sm" :loading="syncing" @click="syncNames">Load GHIMS names</HmsButton>
          <HmsButton variant="primary" size="sm" @click="showCreate = true">New sheet</HmsButton>
        </template>
      </template>
    </HmsPageHeader>

    <section v-if="!sheet" class="diag-panel">
      <div class="panel-head">
        <div>
          <div class="panel-title">Sheets</div>
          <div class="panel-sub">Main pharmacy and any other unit that takes stock for a shift</div>
        </div>
      </div>
      <div class="panel-body">
        <q-table
          :rows="sheets"
          :columns="listColumns"
          row-key="id"
          flat
          :loading="loading"
          :pagination="{ rowsPerPage: 15 }"
          @row-click="(_evt, row) => openSheet(row.id)"
        >
          <template #body-cell-period="props">
            <q-td :props="props">{{ props.row.period_from }} → {{ props.row.period_to }}</q-td>
          </template>
          <template #body-cell-shift="props">
            <q-td :props="props" class="text-capitalize">{{ props.row.shift }}</q-td>
          </template>
          <template #no-data>
            <div class="q-pa-md text-grey-7">No sheets yet. Open one for this week’s shift.</div>
          </template>
        </q-table>
      </div>
    </section>

    <template v-else>
      <section class="diag-panel q-mb-md">
        <div class="panel-body">
          <div class="row q-col-gutter-md">
            <div class="col-12 col-md-4">
              <q-input :model-value="sheet.department_name" label="Department" filled readonly />
            </div>
            <div class="col-12 col-sm-4 col-md-2">
              <q-select v-model="sheet.shift" :options="shiftOptions" label="Shift" filled emit-value map-options />
            </div>
            <div class="col-6 col-sm-4 col-md-2">
              <q-input v-model="sheet.period_from" label="From" type="date" filled />
            </div>
            <div class="col-6 col-sm-4 col-md-2">
              <q-input v-model="sheet.period_to" label="To" type="date" filled />
            </div>
            <div class="col-12 col-sm-4 col-md-2">
              <q-select
                v-model="sheet.status"
                :options="[{ label: 'Open', value: 'open' }, { label: 'Closed', value: 'closed' }]"
                label="Status"
                filled
                emit-value
                map-options
              />
            </div>
            <div class="col-12 col-md-4">
              <q-input v-model="sheet.prepared_by" label="Prepared by" filled />
            </div>
            <div class="col-12 col-md-4">
              <q-input v-model="sheet.checked_by" label="Checked by" filled />
            </div>
            <div class="col-12 col-md-4 flex items-end q-gutter-sm">
              <HmsButton variant="primary" size="sm" :loading="saving" @click="saveSheet">Save sheet</HmsButton>
              <HmsButton variant="secondary" size="sm" :loading="filling" @click="fillReceived">
                Fill R from served requests
              </HmsButton>
            </div>
          </div>
        </div>
      </section>

      <section class="diag-panel q-mb-md">
        <div class="panel-head">
          <div>
            <div class="panel-title">Medicines</div>
            <div class="panel-sub">R = requisition received · ST = stocktaking · CB = closing balance</div>
          </div>
          <div class="row q-gutter-sm items-center">
            <q-select
              v-model="pickedDrug"
              :options="drugOptions"
              use-input
              input-debounce="300"
              filled
              dense
              clearable
              label="Add a GHIMS name"
              style="min-width: 280px"
              emit-value
              map-options
              @filter="filterDrugs"
              @update:model-value="addMedicine"
            />
          </div>
        </div>
        <div class="panel-body sheet-scroll">
          <table class="stock-sheet">
            <thead>
              <tr>
                <th rowspan="2">Medicines</th>
                <th colspan="2">Monday</th>
                <th>Tuesday</th>
                <th>Wednesday</th>
                <th>Thursday</th>
                <th colspan="3">Friday</th>
                <th rowspan="2"></th>
              </tr>
              <tr>
                <th>R</th>
                <th>ST</th>
                <th>R</th>
                <th>R</th>
                <th>R</th>
                <th>R</th>
                <th>AM ST</th>
                <th>CB</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="line in sheet.lines" :key="line.id">
                <td class="med-name">{{ line.medicine_name }}</td>
                <td v-for="field in quantityFields" :key="field">
                  <input v-model="line[field]" class="qty" inputmode="decimal" />
                </td>
                <td>
                  <q-btn flat dense round icon="close" size="sm" @click="removeLine(line)" />
                </td>
              </tr>
              <tr v-if="!sheet.lines.length">
                <td colspan="10" class="text-grey-7 q-pa-md">Add medicines from the GHIMS list.</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="diag-panel">
        <div class="panel-head">
          <div>
            <div class="panel-title">Dispense report</div>
            <div class="panel-sub">Upload the GHIMS Dispense Statistics By Drug file for this period</div>
          </div>
          <div class="row q-gutter-sm items-center">
            <q-select
              v-model="selectedReportId"
              :options="reportOptions"
              label="Report"
              filled
              dense
              emit-value
              map-options
              clearable
              style="min-width: 260px"
              @update:model-value="onReportPicked"
            />
            <HmsButton variant="secondary" size="sm" :loading="uploading" @click="fileInput?.click()">
              Upload report
            </HmsButton>
            <input ref="fileInput" type="file" accept=".xls,.html,.htm" class="hidden-file" @change="onReportFile" />
          </div>
        </div>
        <div class="panel-body">
          <q-banner v-if="reconciliation?.report && !reconciliation.report.covers_sheet" dense rounded class="soft-banner q-mb-md">
            This report is {{ reconciliation.report.period_from }} to {{ reconciliation.report.period_to }}.
            The sheet runs longer, so the quantities below are only for the report dates.
          </q-banner>
          <q-table
            :rows="reconciliation?.rows || []"
            :columns="balanceColumns"
            row-key="line_id"
            flat
            dense
            :pagination="{ rowsPerPage: 50 }"
            :loading="reconciling"
          >
            <template #body-cell-state="props">
              <q-td :props="props">
                <q-badge :color="stateColor(props.row.state)" :label="stateLabel(props.row.state)" />
              </q-td>
            </template>
          </q-table>

          <div v-if="reconciliation?.dispensed_not_on_sheet?.length" class="q-mt-lg">
            <div class="panel-title">Dispensed in GHIMS, not on this sheet</div>
            <q-list dense separator class="q-mt-sm">
              <q-item v-for="item in reconciliation.dispensed_not_on_sheet" :key="item.drug_id">
                <q-item-section>{{ item.drug_name }}</q-item-section>
                <q-item-section side>{{ item.quantity }}</q-item-section>
              </q-item>
            </q-list>
          </div>
        </div>
      </section>
    </template>

    <q-dialog v-model="showCreate">
      <q-card style="min-width: 420px">
        <q-card-section class="dialog-head">
          <div class="dialog-title">New stocktaking sheet</div>
        </q-card-section>
        <q-card-section class="q-gutter-md">
          <q-select
            v-model="draft.department_id"
            :options="departmentOptions"
            label="Department"
            filled
            emit-value
            map-options
          />
          <q-select v-model="draft.shift" :options="shiftOptions" label="Shift" filled emit-value map-options />
          <q-input v-model="draft.period_from" label="From" type="date" filled />
          <q-input v-model="draft.period_to" label="To" type="date" filled />
          <q-input v-model="draft.prepared_by" label="Prepared by" filled />
        </q-card-section>
        <q-card-actions align="right" class="dialog-actions">
          <HmsButton variant="ghost" size="sm" v-close-popup>Cancel</HmsButton>
          <HmsButton variant="primary" size="sm" :loading="saving" @click="createSheet">Create</HmsButton>
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { Notify } from 'quasar';
import HmsPageHeader from '../components/ui/HmsPageHeader.vue';
import HmsButton from '../components/ui/HmsButton.vue';
import { stockAccountabilityAPI, wardsAPI } from '../services/api';

const route = useRoute();
const router = useRouter();

const shiftOptions = [
  { label: 'Morning', value: 'morning' },
  { label: 'Afternoon', value: 'afternoon' },
  { label: 'Night', value: 'night' },
];
const quantityFields = ['mon_r', 'mon_st', 'tue_r', 'wed_r', 'thu_r', 'fri_r', 'fri_am_st', 'fri_cb'];
const listColumns = [
  { name: 'department_name', label: 'Department', field: 'department_name', align: 'left' },
  { name: 'shift', label: 'Shift', field: 'shift', align: 'left' },
  { name: 'period', label: 'Period', field: 'period_from', align: 'left' },
  { name: 'status', label: 'Status', field: 'status', align: 'left' },
  { name: 'checked_by', label: 'Checked by', field: 'checked_by', align: 'left' },
];
const balanceColumns = [
  { name: 'medicine_name', label: 'Medicine', field: 'medicine_name', align: 'left' },
  { name: 'taken', label: 'Taken', field: 'taken', align: 'right' },
  { name: 'closing_balance', label: 'Closing', field: 'closing_balance', align: 'right' },
  { name: 'expected_dispensed', label: 'Expected dispensed', field: 'expected_dispensed', align: 'right' },
  { name: 'dispensed', label: 'GHIMS dispensed', field: 'dispensed', align: 'right' },
  { name: 'difference', label: 'Difference', field: 'difference', align: 'right' },
  { name: 'state', label: 'Result', field: 'state', align: 'left' },
];

const loading = ref(false);
const syncing = ref(false);
const saving = ref(false);
const filling = ref(false);
const uploading = ref(false);
const reconciling = ref(false);
const showCreate = ref(false);
const sheets = ref([]);
const sheet = ref(null);
const reports = ref([]);
const reconciliation = ref(null);
const selectedReportId = ref(null);
const departmentOptions = ref([]);
const drugOptions = ref([]);
const pickedDrug = ref(null);
const fileInput = ref(null);
const draft = ref({
  department_id: null,
  shift: 'morning',
  period_from: '',
  period_to: '',
  prepared_by: '',
});

const reportOptions = computed(() =>
  reports.value.map((report) => ({
    label: `${report.period_from} → ${report.period_to}${report.source_filename ? ` · ${report.source_filename}` : ''}`,
    value: report.id,
  }))
);

const stateLabel = (state) => ({
  balanced: 'Balanced',
  report_higher: 'Report is higher',
  sheet_higher: 'Sheet is higher',
  needs_closing_balance: 'Needs closing balance',
  missing_from_report: 'Not on the report',
  no_movement: 'No movement',
  ambiguous: 'More than one name',
  no_report: 'No report yet',
}[state] || state);

const stateColor = (state) => ({
  balanced: 'positive',
  report_higher: 'warning',
  sheet_higher: 'warning',
  needs_closing_balance: 'grey',
  missing_from_report: 'negative',
  no_movement: 'grey',
  ambiguous: 'warning',
  no_report: 'grey',
}[state] || 'grey');

const notifyError = (error, fallback) => {
  Notify.create({
    type: 'negative',
    message: error.response?.data?.detail || fallback,
    position: 'top',
  });
};

const blankToNull = (value) => {
  if (value === '' || value === null || value === undefined) return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
};

const syncNames = async () => {
  syncing.value = true;
  try {
    const response = await stockAccountabilityAPI.syncCatalog();
    Notify.create({
      type: 'positive',
      message: `GHIMS names loaded. ${response.data.total} medicines are available to request.`,
      position: 'top',
    });
  } catch (error) {
    notifyError(error, 'Could not read the GHIMS drug list');
  } finally {
    syncing.value = false;
  }
};

const loadDepartments = async () => {
  const response = await wardsAPI.getAll(true);
  departmentOptions.value = (response.data || []).map((dept) => ({ label: dept.name, value: dept.id }));
};

const loadSheets = async () => {
  loading.value = true;
  try {
    const response = await stockAccountabilityAPI.listSheets();
    sheets.value = response.data || [];
  } catch (error) {
    notifyError(error, 'Failed to load sheets');
  } finally {
    loading.value = false;
  }
};

const loadReports = async () => {
  const response = await stockAccountabilityAPI.listReports();
  reports.value = response.data || [];
};

const onReportPicked = () => {
  loadReconciliation();
};

const loadReconciliation = async () => {
  if (!sheet.value) return;
  reconciling.value = true;
  try {
    const response = await stockAccountabilityAPI.reconcile(sheet.value.id, selectedReportId.value);
    reconciliation.value = response.data;
    const reportId = response.data?.report?.id;
    if (reportId && reportId !== selectedReportId.value) {
      selectedReportId.value = reportId;
    }
  } catch (error) {
    notifyError(error, 'Failed to compare with the dispense report');
  } finally {
    reconciling.value = false;
  }
};

const loadSheet = async (id) => {
  loading.value = true;
  try {
    const response = await stockAccountabilityAPI.getSheet(id);
    sheet.value = response.data;
    await loadReports();
    await loadReconciliation();
  } catch (error) {
    sheet.value = null;
    notifyError(error, 'Failed to open the sheet');
  } finally {
    loading.value = false;
  }
};

const openSheet = (id) => {
  router.push({ name: 'InventoryModeStocktakingSheet', params: { sheetId: id } });
};

const backToList = () => {
  sheet.value = null;
  reconciliation.value = null;
  router.push({ name: 'InventoryModeStocktaking' });
};

const createSheet = async () => {
  if (!draft.value.department_id || !draft.value.period_from || !draft.value.period_to) {
    Notify.create({ type: 'warning', message: 'Choose a department and the week.', position: 'top' });
    return;
  }
  saving.value = true;
  try {
    const response = await stockAccountabilityAPI.createSheet(draft.value);
    showCreate.value = false;
    openSheet(response.data.id);
  } catch (error) {
    notifyError(error, 'Failed to create the sheet');
  } finally {
    saving.value = false;
  }
};

const saveSheet = async () => {
  saving.value = true;
  try {
    const response = await stockAccountabilityAPI.updateSheet(sheet.value.id, {
      shift: sheet.value.shift,
      period_from: sheet.value.period_from,
      period_to: sheet.value.period_to,
      prepared_by: sheet.value.prepared_by,
      checked_by: sheet.value.checked_by,
      status: sheet.value.status,
      lines: sheet.value.lines.map((line) => ({
        id: line.id,
        mon_r: blankToNull(line.mon_r),
        mon_st: blankToNull(line.mon_st),
        tue_r: blankToNull(line.tue_r),
        wed_r: blankToNull(line.wed_r),
        thu_r: blankToNull(line.thu_r),
        fri_r: blankToNull(line.fri_r),
        fri_am_st: blankToNull(line.fri_am_st),
        fri_cb: blankToNull(line.fri_cb),
      })),
    });
    sheet.value = response.data;
    Notify.create({ type: 'positive', message: 'Sheet saved', position: 'top' });
    await loadReconciliation();
  } catch (error) {
    notifyError(error, 'Failed to save the sheet');
  } finally {
    saving.value = false;
  }
};

const filterDrugs = (val, update, abort) => {
  stockAccountabilityAPI
    .searchCatalog(val, 40)
    .then((res) => {
      const rows = Array.isArray(res.data) ? res.data : [];
      update(() => {
        drugOptions.value = rows.map((item) => ({
          label: item.drug_name,
          value: item.drug_id,
        }));
      });
    })
    .catch(() => abort());
};

const addMedicine = async (drugId) => {
  if (!drugId) return;
  try {
    const response = await stockAccountabilityAPI.addLine(sheet.value.id, drugId);
    sheet.value = response.data;
    pickedDrug.value = null;
  } catch (error) {
    notifyError(error, 'Could not add that medicine');
    pickedDrug.value = null;
  }
};

const removeLine = async (line) => {
  try {
    const response = await stockAccountabilityAPI.deleteLine(sheet.value.id, line.id);
    sheet.value = response.data;
    await loadReconciliation();
  } catch (error) {
    notifyError(error, 'Could not remove that row');
  }
};

const fillReceived = async () => {
  filling.value = true;
  try {
    const response = await stockAccountabilityAPI.fillFromRequisitions(sheet.value.id);
    sheet.value = response.data;
    Notify.create({
      type: 'positive',
      message: 'Received quantities were written into the R columns for this shift.',
      position: 'top',
    });
    await loadReconciliation();
  } catch (error) {
    notifyError(error, 'Could not read served requisitions');
  } finally {
    filling.value = false;
  }
};

const onReportFile = async (event) => {
  const file = event.target.files?.[0];
  event.target.value = '';
  if (!file) return;
  uploading.value = true;
  try {
    const response = await stockAccountabilityAPI.uploadReport(file);
    await loadReports();
    selectedReportId.value = response.data.id;
    await loadReconciliation();
    Notify.create({ type: 'positive', message: 'Dispense report uploaded', position: 'top' });
  } catch (error) {
    notifyError(error, 'Could not read that dispense report');
  } finally {
    uploading.value = false;
  }
};

watch(
  () => route.params.sheetId,
  (id) => {
    if (id) loadSheet(id);
    else {
      sheet.value = null;
      loadSheets();
    }
  },
  { immediate: true }
);

onMounted(loadDepartments);
</script>

<style scoped>
.sheet-scroll {
  overflow-x: auto;
}
.stock-sheet {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.stock-sheet th,
.stock-sheet td {
  border: 1px solid var(--hms-border);
  padding: 4px 6px;
  text-align: center;
  white-space: nowrap;
}
.stock-sheet th {
  background: var(--hms-surface-hover);
  font-weight: 650;
}
.med-name {
  text-align: left !important;
  min-width: 220px;
  white-space: normal !important;
}
.qty {
  width: 72px;
  border: 0;
  background: transparent;
  text-align: right;
  color: inherit;
  font: inherit;
}
.hidden-file {
  display: none;
}
.dialog-head {
  border-bottom: 1px solid var(--hms-border);
}
.dialog-title {
  font-size: var(--hms-text-lg);
  font-weight: 750;
}
</style>
