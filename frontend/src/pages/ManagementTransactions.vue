<template>
  <q-page class="q-pa-md">
    <div class="text-h4 q-mb-md text-weight-bold glass-text">
      Transactions
    </div>
    <div class="text-subtitle1 text-secondary q-mb-lg">
      Choose a payment board below. Confirmed payments shows saved transactions; Pending payments shows bills that still need to be saved/paid.
    </div>

    <div class="row q-col-gutter-md q-mb-md">
      <div class="col-12 col-md-6">
        <q-card
          flat
          class="glass-card cursor-pointer"
          :class="activeBoard === 'confirmed' ? 'board-card-active' : ''"
          @click="switchBoard('confirmed')"
        >
          <q-card-section class="row items-center justify-between">
            <div>
              <div class="text-h6 glass-text">Confirmed payments</div>
              <div class="text-caption text-grey-7">Saved OPD + Companion transactions</div>
            </div>
            <q-badge color="positive" :label="String(confirmedCount)" />
          </q-card-section>
        </q-card>
      </div>
      <div class="col-12 col-md-6">
        <q-card
          flat
          class="glass-card cursor-pointer"
          :class="activeBoard === 'pending' ? 'board-card-active' : ''"
          @click="switchBoard('pending')"
        >
          <q-card-section class="row items-center justify-between">
            <div>
              <div class="text-h6 glass-text">Pending payments</div>
              <div class="text-caption text-grey-7">Incoming bills not fully paid/saved yet</div>
            </div>
            <q-badge color="orange" :label="String(pendingCount)" />
          </q-card-section>
        </q-card>
      </div>
    </div>

    <q-card class="q-mb-md glass-card" flat>
      <q-card-section>
        <div class="row items-center justify-between q-mb-md">
          <div class="text-h6 glass-text">Filters</div>
          <span class="row items-center no-wrap">
            <q-toggle
              v-model="rememberFilters"
              color="primary"
              dense
              label="Remember filters & board"
            />
            <q-icon name="info" size="xs" color="grey-6" class="q-ml-xs cursor-pointer">
              <q-tooltip anchor="top middle" self="bottom middle">
                When on, your filters and which board is selected are saved in this browser
                until you turn this off or clear site data.
              </q-tooltip>
            </q-icon>
          </span>
        </div>
        <div class="row q-col-gutter-md items-end">
          <q-input
            v-model="filters.start_date"
            filled
            dense
            type="date"
            label="From date"
            clearable
            class="col-12 col-sm-6 col-md-2"
          />
          <q-input
            v-model="filters.end_date"
            filled
            dense
            type="date"
            label="To date"
            clearable
            class="col-12 col-sm-6 col-md-2"
          />
          <q-input
            v-model="filters.client"
            filled
            dense
            label="Client (name or card)"
            clearable
            class="col-12 col-md-3"
            @keyup.enter="loadActiveBoard"
          />
          <q-select
            v-model="filters.service_group"
            :options="chargeServiceOptions"
            filled
            dense
            label="Charged service"
            emit-value
            map-options
            option-label="label"
            option-value="value"
            clearable
            options-dense
            class="col-12 col-md-3"
          >
            <template #append>
              <q-icon name="info" size="xs" class="self-center" style="opacity: 0.55">
                <q-tooltip anchor="top middle" self="bottom middle">
                  Groups what the client was billed for (OPD procedures and copayment lines): labs, scans, surgery, pharmacy, etc.
                </q-tooltip>
              </q-icon>
            </template>
          </q-select>
          <q-select
            v-model="filters.user_id"
            :options="userOptions"
            filled
            dense
            label="User (who took transaction)"
            emit-value
            map-options
            clearable
            options-dense
            class="col-12 col-md-2"
            :disable="activeBoard === 'pending'"
          />
        </div>
        <div class="row justify-end q-mt-md">
          <q-btn
            unelevated
            label="Search / refresh"
            class="glass-button q-px-lg"
            icon="search"
            size="md"
            :loading="loading"
            @click="loadActiveBoard"
          />
        </div>
      </q-card-section>
    </q-card>

    <q-card class="glass-card" flat>
      <q-card-section>
        <div class="row items-center justify-between q-mb-md">
          <div class="text-h6 glass-text">
            {{ activeBoard === 'confirmed' ? 'Confirmed payments' : 'Pending payments' }}
            <span v-if="summaryAmount !== null" class="text-weight-normal text-secondary q-ml-sm">
              — {{ activeBoard === 'confirmed' ? 'Total confirmed' : 'Total pending' }}: {{ formatPrice(summaryAmount) }}
            </span>
          </div>
          <div class="row q-gutter-sm">
            <q-btn
              outline
              dense
              color="primary"
              icon="table_chart"
              label="Excel"
              :disable="!tableRows.length"
              @click="exportExcel"
            />
            <q-btn
              outline
              dense
              color="primary"
              icon="picture_as_pdf"
              label="PDF"
              :disable="!tableRows.length"
              @click="exportPdf"
            />
          </div>
        </div>
        <q-table
          :rows="tableRows"
          :columns="tableColumns"
          :row-key="(row, index) => index"
          flat
          :loading="loading"
          :rows-per-page-options="[10, 25, 50, 100]"
          class="glass-table"
          :no-data-label="activeBoard === 'confirmed' ? 'No transactions found. Adjust filters or date range.' : 'No pending payments found. Adjust filters or date range.'"
        >
          <template v-slot:body-cell-transaction_date="props">
            <q-td :props="props">{{ formatDate(props.row.transaction_date) }}</q-td>
          </template>
          <template v-slot:body-cell-pending_date="props">
            <q-td :props="props">{{ formatDate(props.row.pending_date) }}</q-td>
          </template>
          <template v-slot:body-cell-amount="props">
            <q-td :props="props">{{ formatPrice(props.row.amount) }}</q-td>
          </template>
          <template v-slot:body-cell-amount_due="props">
            <q-td :props="props">{{ formatPrice(props.row.amount_due) }}</q-td>
          </template>
          <template v-slot:body-cell-source="props">
            <q-td :props="props">
              <q-badge :color="props.row.source === 'opd' ? 'primary' : 'teal'" :label="props.row.source.toUpperCase()" />
            </q-td>
          </template>
        </q-table>
      </q-card-section>
    </q-card>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue';
import { storeToRefs } from 'pinia';
import { managementAPI } from '../services/api';
import { useFacilityStore } from '../stores/facility';

const PREFS_KEY = 'hms.managementTransactions.v1';

/** Same paths as Pharmacy / Patient profile PDF prints (public/). */
const LOGO_MOH = '/logos/ministry-of-health-logo.png';
const LOGO_GHS = '/logos/ghana-health-service-logo.png';

async function fetchLogoDataUrl(url) {
  try {
    const res = await fetch(url);
    if (!res.ok) return null;
    const blob = await res.blob();
    return await new Promise((resolve, reject) => {
      const fr = new FileReader();
      fr.onload = () => resolve(fr.result);
      fr.onerror = reject;
      fr.readAsDataURL(blob);
    });
  } catch {
    return null;
  }
}

function dataUrlToBase64(dataUrl) {
  if (!dataUrl || typeof dataUrl !== 'string') return null;
  const i = dataUrl.indexOf(',');
  return i >= 0 ? dataUrl.slice(i + 1) : dataUrl;
}

function naturalSizeFromDataUrl(dataUrl) {
  return new Promise((resolve) => {
    if (!dataUrl) {
      resolve(null);
      return;
    }
    const img = new Image();
    img.onload = () => resolve({ w: img.naturalWidth, h: img.naturalHeight });
    img.onerror = () => resolve(null);
    img.src = dataUrl;
  });
}

/** 0-based column index → Excel column letters (A, B, …, Z, AA). */
function colNameFromZeroBased(zeroBased) {
  let n = zeroBased + 1;
  let s = '';
  while (n > 0) {
    const rem = (n - 1) % 26;
    s = String.fromCharCode(65 + rem) + s;
    n = Math.floor((n - 1) / 26);
  }
  return s;
}

function todayStr() {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

function defaultFilters() {
  return {
    start_date: todayStr(),
    end_date: todayStr(),
    client: null,
    service_group: null,
    user_id: null,
  };
}

const loading = ref(false);
const activeBoard = ref('confirmed');
const transactions = ref([]);
const totalAmount = ref(null);
const pendingPayments = ref([]);
const totalPending = ref(null);
const userOptions = ref([]);
const rememberFilters = ref(false);

const facilityStore = useFacilityStore();
const { displayName: facilityDisplayName } = storeToRefs(facilityStore);

const filters = ref(defaultFilters());

/** Matches backend /management `service_group`: how the client was charged (OPD + copayment lines). */
const chargeServiceOptions = [
  { label: 'All charged services', value: null },
  { label: 'Laboratory / investigations', value: 'labs' },
  { label: 'Ultrasound & scans', value: 'scans' },
  { label: 'X-ray & radiology', value: 'xray' },
  { label: 'Pharmacy & drugs', value: 'pharmacy' },
  { label: 'Day surgery', value: 'day_surgery' },
  { label: 'Major / adult surgery', value: 'major_surgery' },
  { label: 'Dressing & treatment room', value: 'dressing' },
  { label: 'Oxygen', value: 'oxygen' },
  { label: 'Inpatient', value: 'inpatient' },
];

const columns = [
  { name: 'transaction_date', label: 'Date', field: 'transaction_date', align: 'left', sortable: true },
  { name: 'source', label: 'Source', field: 'source', align: 'left' },
  { name: 'client_name', label: 'Client', field: 'client_name', align: 'left' },
  { name: 'client_identifier', label: 'Card / ID', field: 'client_identifier', align: 'left' },
  { name: 'service_type', label: 'Service type', field: 'service_type', align: 'left' },
  { name: 'amount', label: 'Amount', field: 'amount', align: 'right' },
  { name: 'user_name', label: 'User', field: 'user_name', align: 'left' },
  { name: 'receipt_number', label: 'Receipt', field: 'receipt_number', align: 'left' },
  { name: 'payment_method', label: 'Payment', field: 'payment_method', align: 'left' },
];

const pendingColumns = [
  { name: 'pending_date', label: 'Date', field: 'pending_date', align: 'left', sortable: true },
  { name: 'source', label: 'Source', field: 'source', align: 'left' },
  { name: 'client_name', label: 'Client', field: 'client_name', align: 'left' },
  { name: 'client_identifier', label: 'Card / ID', field: 'client_identifier', align: 'left' },
  { name: 'service_type', label: 'Service type', field: 'service_type', align: 'left' },
  { name: 'amount_due', label: 'Amount due', field: 'amount_due', align: 'right' },
];

const tableRows = computed(() => (activeBoard.value === 'confirmed' ? transactions.value : pendingPayments.value));
const tableColumns = computed(() => (activeBoard.value === 'confirmed' ? columns : pendingColumns));
const summaryAmount = computed(() => (activeBoard.value === 'confirmed' ? totalAmount.value : totalPending.value));
const confirmedCount = computed(() => transactions.value.length);
const pendingCount = computed(() => pendingPayments.value.length);

function formatPrice(val) {
  const n = Number(val);
  if (Number.isNaN(n)) return '0.00';
  return n.toFixed(2);
}

function formatDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString();
}

function loadPrefsFromStorage() {
  try {
    const raw = localStorage.getItem(PREFS_KEY);
    if (!raw) return;
    const p = JSON.parse(raw);
    if (!p || !p.remember) return;
    rememberFilters.value = true;
    if (p.activeBoard === 'confirmed' || p.activeBoard === 'pending') {
      activeBoard.value = p.activeBoard;
    }
    if (p.filters && typeof p.filters === 'object') {
      const merged = { ...defaultFilters(), ...p.filters };
      delete merged.service_type;
      filters.value = merged;
    }
  } catch (e) {
    /* ignore */
  }
}

function savePrefsToStorage() {
  if (!rememberFilters.value) return;
  try {
    localStorage.setItem(
      PREFS_KEY,
      JSON.stringify({
        remember: true,
        activeBoard: activeBoard.value,
        filters: { ...filters.value },
      }),
    );
  } catch (e) {
    /* ignore */
  }
}

watch(
  [filters, activeBoard],
  () => {
    if (rememberFilters.value) savePrefsToStorage();
  },
  { deep: true },
);

watch(rememberFilters, (on) => {
  if (on) savePrefsToStorage();
  else localStorage.removeItem(PREFS_KEY);
});

function cellDisplay(col, row) {
  const f = col.field;
  const v = row[f];
  if (f === 'transaction_date' || f === 'pending_date') return formatDate(v);
  if (f === 'amount' || f === 'amount_due') return formatPrice(v);
  if (f === 'source') return (v || '').toString().toUpperCase();
  if (v == null) return '';
  return String(v);
}

function exportFileSlug() {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}_${pad(d.getHours())}${pad(d.getMinutes())}`;
}

function reportMeta() {
  const clinic = (facilityDisplayName.value || 'Facility').trim() || 'Facility';
  const isConfirmed = activeBoard.value === 'confirmed';
  const reportTitle = isConfirmed ? 'Confirmed payments' : 'Pending payments';
  const subtitle = isConfirmed
    ? 'Saved OPD receipts and paid copayment lines'
    : 'Outstanding OPD bills and unpaid copayment lines';
  const generated = new Date().toLocaleString();
  const periodFrom = filters.value.start_date || '—';
  const periodTo = filters.value.end_date || '—';
  const totalLabel = isConfirmed ? 'Total confirmed' : 'Total pending';
  const totalVal = formatPrice(summaryAmount.value ?? 0);
  const sg = filters.value.service_group;
  const filterNote =
    sg != null && String(sg).trim()
      ? (chargeServiceOptions.find((o) => o.value === sg)?.label || `Charged service: ${sg}`)
      : null;
  return { clinic, reportTitle, subtitle, generated, periodFrom, periodTo, totalLabel, totalVal, filterNote };
}

async function exportExcel() {
  const ExcelJS = (await import('exceljs')).default;
  const m = reportMeta();
  const cols = tableColumns.value;
  const headerRow = cols.map((c) => c.label);
  const bodyRows = tableRows.value.map((row) => cols.map((c) => cellDisplay(c, row)));
  const lastColIdx = Math.max(headerRow.length, 10) - 1;
  const lastCol = colNameFromZeroBased(lastColIdx);

  const wb = new ExcelJS.Workbook();
  const sheetName = activeBoard.value === 'confirmed' ? 'Confirmed' : 'Pending';
  const ws = wb.addWorksheet(sheetName.slice(0, 31), { views: [{ showGridLines: true }] });

  const [mohUrl, ghsUrl] = await Promise.all([
    fetchLogoDataUrl(LOGO_MOH),
    fetchLogoDataUrl(LOGO_GHS),
  ]);

  ws.getRow(1).height = 78;
  if (mohUrl) {
    const b64 = dataUrlToBase64(mohUrl);
    if (b64) {
      const id = wb.addImage({ base64: b64, extension: 'png' });
      ws.addImage(id, {
        tl: { col: 0.25, row: 0.05 },
        ext: { width: 132, height: 99 },
      });
    }
  }
  if (ghsUrl) {
    const b64 = dataUrlToBase64(ghsUrl);
    if (b64) {
      const id = wb.addImage({ base64: b64, extension: 'png' });
      ws.addImage(id, {
        tl: { col: 2.65, row: 0.05 },
        ext: { width: 132, height: 99 },
      });
    }
  }

  let r = 6;
  const mergeCenter = (text, font = {}) => {
    ws.mergeCells(`A${r}:${lastCol}${r}`);
    const cell = ws.getCell(`A${r}`);
    cell.value = text;
    cell.alignment = { horizontal: 'center', vertical: 'middle', wrapText: true };
    if (Object.keys(font).length) cell.font = font;
    r += 1;
  };

  mergeCenter('GHANA HEALTH SERVICE', { bold: true, size: 11 });
  mergeCenter(m.clinic, { bold: true, size: 14 });
  mergeCenter(m.reportTitle, { bold: true, size: 12 });
  mergeCenter(m.subtitle, { size: 10 });
  mergeCenter(`Generated: ${m.generated}`, { size: 10 });
  mergeCenter(`Period: ${m.periodFrom} – ${m.periodTo}`, { size: 10 });
  if (m.filterNote) mergeCenter(`Filter: ${m.filterNote}`, { size: 10 });
  mergeCenter(`${m.totalLabel}: ${m.totalVal}`, { bold: true, size: 11 });
  r += 1;
  mergeCenter('Detail', { bold: true, size: 10 });
  r += 1;

  const hdr = ws.getRow(r);
  headerRow.forEach((val, i) => {
    const c = hdr.getCell(i + 1);
    c.value = val;
    c.font = { bold: true, color: { argb: 'FFFFFFFF' } };
    c.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FF2E7D32' } };
    c.alignment = { horizontal: 'left', vertical: 'middle', wrapText: true };
  });
  r += 1;

  bodyRows.forEach((row) => {
    const xr = ws.getRow(r);
    row.forEach((val, i) => {
      xr.getCell(i + 1).value = val;
    });
    r += 1;
  });

  for (let c = 1; c <= lastColIdx + 1; c += 1) {
    ws.getColumn(c).width = 14;
  }

  const buf = await wb.xlsx.writeBuffer();
  const blob = new Blob([buf], {
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  });
  const href = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = href;
  const board = activeBoard.value === 'confirmed' ? 'confirmed' : 'pending';
  a.download = `transactions_${board}_${exportFileSlug()}.xlsx`;
  a.click();
  URL.revokeObjectURL(href);
}

async function exportPdf() {
  const [{ jsPDF }, autoMod] = await Promise.all([import('jspdf'), import('jspdf-autotable')]);
  const autoTable = autoMod.default;
  const m = reportMeta();
  const cols = tableColumns.value;
  const head = [cols.map((c) => c.label)];
  const body = tableRows.value.map((row) => cols.map((c) => cellDisplay(c, row)));
  const doc = new jsPDF({ orientation: 'landscape', unit: 'mm', format: 'a4' });
  const pageW = doc.internal.pageSize.getWidth();
  let y = 7;

  const logoMaxH = 15;
  const [mohData, ghsData] = await Promise.all([
    fetchLogoDataUrl(LOGO_MOH),
    fetchLogoDataUrl(LOGO_GHS),
  ]);

  if (mohData && ghsData) {
    const [d1, d2] = await Promise.all([
      naturalSizeFromDataUrl(mohData),
      naturalSizeFromDataUrl(ghsData),
    ]);
    if (d1 && d2 && d1.h > 0 && d2.h > 0) {
      const w1 = (d1.w / d1.h) * logoMaxH;
      const w2 = (d2.w / d2.h) * logoMaxH;
      const gap = 6;
      const totalW = w1 + gap + w2;
      const x0 = (pageW - totalW) / 2;
      doc.addImage(mohData, 'PNG', x0, y, w1, logoMaxH);
      doc.addImage(ghsData, 'PNG', x0 + w1 + gap, y, w2, logoMaxH);
    }
  } else if (mohData) {
    const d1 = await naturalSizeFromDataUrl(mohData);
    if (d1 && d1.h > 0) {
      const w1 = (d1.w / d1.h) * logoMaxH;
      doc.addImage(mohData, 'PNG', (pageW - w1) / 2, y, w1, logoMaxH);
    }
  } else if (ghsData) {
    const d2 = await naturalSizeFromDataUrl(ghsData);
    if (d2 && d2.h > 0) {
      const w2 = (d2.w / d2.h) * logoMaxH;
      doc.addImage(ghsData, 'PNG', (pageW - w2) / 2, y, w2, logoMaxH);
    }
  }

  if (mohData || ghsData) {
    y += logoMaxH + 2;
  }

  doc.setFontSize(10);
  doc.setFont('helvetica', 'bold');
  doc.text('GHANA HEALTH SERVICE', pageW / 2, y, { align: 'center' });
  y += 5;
  doc.setFontSize(16);
  doc.text(m.clinic, pageW / 2, y, { align: 'center' });
  y += 7;
  doc.setFontSize(12);
  doc.text(m.reportTitle, pageW / 2, y, { align: 'center' });
  y += 6;
  doc.setFontSize(9);
  doc.setFont('helvetica', 'normal');
  doc.text(m.subtitle, pageW / 2, y, { align: 'center' });
  y += 6;
  doc.setFontSize(9);
  doc.text(`Generated: ${m.generated}`, 14, y);
  y += 5;
  doc.text(`Period: ${m.periodFrom} – ${m.periodTo}`, 14, y);
  y += 5;
  if (m.filterNote) {
    doc.setFont('helvetica', 'normal');
    doc.text(`Filter: ${m.filterNote}`, 14, y);
    y += 5;
  }
  doc.setFont('helvetica', 'bold');
  doc.text(`${m.totalLabel}: ${m.totalVal}`, 14, y);
  doc.setFont('helvetica', 'normal');
  y += 4;
  doc.setDrawColor(180);
  doc.line(14, y, pageW - 14, y);
  y += 6;
  autoTable(doc, {
    startY: y,
    head,
    body,
    styles: { fontSize: 7, cellPadding: 1.5 },
    headStyles: { fillColor: [46, 125, 50] },
    margin: { left: 14, right: 14 },
    didDrawPage: (data) => {
      if (data.pageNumber > 1) {
        doc.setFontSize(8);
        doc.setTextColor(100);
        doc.text(`${m.clinic} — ${m.reportTitle}`, 14, 8);
        doc.setTextColor(0);
      }
    },
  });
  const board = activeBoard.value === 'confirmed' ? 'confirmed' : 'pending';
  doc.save(`transactions_${board}_${exportFileSlug()}.pdf`);
}

async function loadUsers() {
  try {
    const res = await managementAPI.getUsers();
    const list = res.data || [];
    userOptions.value = list.map((u) => ({
      label: u.full_name || u.username || `User ${u.id}`,
      value: u.id,
    }));
  } catch (e) {
    userOptions.value = [];
  }
}

async function loadTransactions() {
  loading.value = true;
  transactions.value = [];
  totalAmount.value = null;
  try {
    const params = {};
    if (filters.value.start_date) params.start_date = filters.value.start_date;
    if (filters.value.end_date) params.end_date = filters.value.end_date;
    if (filters.value.client && filters.value.client.trim()) params.client = filters.value.client.trim();
    const sg = filters.value.service_group;
    if (sg != null && String(sg).trim()) params.service_group = String(sg).trim();
    if (filters.value.user_id != null) params.user_id = filters.value.user_id;
    const res = await managementAPI.getTransactions(params);
    transactions.value = (res.data && res.data.transactions) ? res.data.transactions : [];
    totalAmount.value = (res.data && res.data.total_amount != null) ? res.data.total_amount : 0;
  } catch (e) {
    console.error('Failed to load transactions', e);
  } finally {
    loading.value = false;
  }
}

async function loadPendingPayments() {
  loading.value = true;
  pendingPayments.value = [];
  totalPending.value = null;
  try {
    const params = {};
    if (filters.value.start_date) params.start_date = filters.value.start_date;
    if (filters.value.end_date) params.end_date = filters.value.end_date;
    if (filters.value.client && filters.value.client.trim()) params.client = filters.value.client.trim();
    const sg = filters.value.service_group;
    if (sg != null && String(sg).trim()) params.service_group = String(sg).trim();
    const res = await managementAPI.getPendingPayments(params);
    pendingPayments.value = (res.data && res.data.pending) ? res.data.pending : [];
    totalPending.value = (res.data && res.data.total_due != null) ? res.data.total_due : 0;
  } catch (e) {
    console.error('Failed to load pending payments', e);
  } finally {
    loading.value = false;
  }
}

function switchBoard(board) {
  if (activeBoard.value === board) return;
  activeBoard.value = board;
  loadActiveBoard();
}

function loadActiveBoard() {
  if (activeBoard.value === 'confirmed') {
    return loadTransactions();
  }
  return loadPendingPayments();
}

onMounted(() => {
  loadPrefsFromStorage();
  if (!facilityStore.loaded) {
    facilityStore.fetchPublic();
  }
  loadUsers();
  loadActiveBoard();
});
</script>

<style scoped>
.board-card-active {
  border: 1px solid rgba(76, 175, 80, 0.35);
  box-shadow: 0 0 0 1px rgba(76, 175, 80, 0.2) inset;
}
</style>
