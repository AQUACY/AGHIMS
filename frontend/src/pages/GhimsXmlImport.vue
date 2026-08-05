<template>
  <q-page class="hms-page">
    <HmsPageHeader
      :title="viewingBatchId ? `Import batch: ${currentBatch?.file_name || ''}` : 'Import GHIMS XML'"
      :subtitle="viewingBatchId ? 'Review, filter, vet, and export claims from this import.' : 'Upload exported XML, review batches, finalize, and export again.'"
    >
      <template #actions>
        <HmsButton variant="ghost" size="sm" @click="goBack">Back</HmsButton>
      </template>
    </HmsPageHeader>

    <section v-if="!viewingBatchId" class="diag-panel">
      <div class="panel-head">
        <div>
          <div class="panel-title">Upload GHIMS XML export</div>
          <div class="panel-sub">Select an XML file from GHIMS / ClaimIT export</div>
        </div>
      </div>
      <div class="panel-body upload-row">
        <q-file
          v-model="uploadFile"
          label="Select XML file"
          accept=".xml,text/xml,application/xml"
          outlined
          dense
          clearable
          class="upload-file"
        />
        <HmsButton
          variant="primary"
          size="sm"
          :loading="uploading"
          :disabled="!uploadFile"
          @click="uploadXml"
        >
          Import XML
        </HmsButton>
      </div>
    </section>

    <section v-if="!viewingBatchId" class="diag-panel">
      <div class="panel-head">
        <div>
          <div class="panel-title">Recent XML imports</div>
          <div class="panel-sub">Click a batch to review claims and export</div>
        </div>
      </div>
      <div class="panel-body">
        <div v-if="batches.length" class="batch-list">
          <div
            v-for="b in batches"
            :key="b.id"
            class="batch-row"
            role="button"
            tabindex="0"
            @click="openBatch(b.id)"
            @keydown.enter.prevent="openBatch(b.id)"
            @keydown.space.prevent="openBatch(b.id)"
          >
            <div class="batch-copy">
              <div class="batch-name">{{ b.file_name }}</div>
              <div class="batch-meta">
                {{ formatDate(b.uploaded_at) }} · {{ b.claim_count }} claim(s) · {{ b.finalized_count || 0 }} finalized
                · {{ b.pharmacy_vetted_count || 0 }} pharmacy-vetted · {{ b.doctor_vetted_count || 0 }} doctor-vetted
              </div>
            </div>
            <div v-if="canDeleteImportBatch" class="batch-actions" @click.stop>
              <button
                type="button"
                class="batch-delete-btn"
                aria-label="Delete import batch"
                @click="deleteBatch(b)"
              >
                <Trash2 :size="15" :stroke-width="2" />
                <q-tooltip anchor="top middle" self="bottom middle">Delete import (admin only)</q-tooltip>
              </button>
            </div>
          </div>
        </div>
        <p v-else class="empty-hint">No XML imports yet.</p>
      </div>
    </section>

    <template v-if="viewingBatchId && currentBatch">
      <div v-if="viewingBatchId && currentBatch" class="text-subtitle1 text-primary q-mb-md">
        <template v-if="totalsLoading">
          <q-spinner-dots size="20px" class="q-mr-sm" />
          Calculating claim revenue…
        </template>
        <template v-else-if="filteredRevenue != null">
          Total claim revenue ({{ filteredClaims.length }} filtered): {{ formatCurrency(filteredRevenue) }}
        </template>
      </div>
      <section class="diag-panel batch-toolbar">
        <q-card-section class="row items-center q-gutter-md">
          <div class="text-body2 text-grey-8">{{ currentBatch.claims?.length || 0 }} claim(s) in this import</div>
          <div class="text-body2 text-primary">
            Showing {{ filteredClaims.length }} filtered claim(s)
          </div>
          <div class="text-body2 text-teal">
            Pharmacy vetted: {{ batchPharmacyVettedCount }} · Doctor vetted: {{ batchDoctorVettedCount }}
          </div>
          <q-checkbox
            :model-value="allExportableSelected"
            label="Select all exportable"
            @update:model-value="toggleSelectAllExportable"
          />
          <q-toggle
            v-model="filtersLocked"
            color="primary"
            label="Lock filters"
            checked-icon="lock"
            unchecked-icon="lock_open"
            class="col-12 col-md-auto"
          />
          <q-input
            v-model="searchText"
            outlined
            dense
            clearable
            label="Search client / hospital rec no / claim IDs / CCC"
            class="col-12 col-md-4"
          />
          <q-select
            v-model="serviceTypeFilter"
            :options="serviceTypeFilterOptions"
            emit-value
            map-options
            outlined
            dense
            label="Type of service"
            class="col-12 col-md-3"
          />
          <q-select
            v-model="attendanceFilter"
            :options="attendanceFilterOptions"
            emit-value
            map-options
            outlined
            dense
            label="Type of attendance"
            class="col-12 col-md-3"
          />
          <q-select
            v-model="specialtyFilter"
            :options="specialtyFilterOptions"
            emit-value
            map-options
            outlined
            dense
            label="Specialty attended"
            class="col-12 col-md-3"
          />
          <q-select
            v-model="statusFilter"
            :options="statusFilterOptions"
            emit-value
            map-options
            outlined
            dense
            label="Filter by status"
            class="col-12 col-md-3"
          />
          <q-select
            v-model="ageGroupFilter"
            :options="ageGroupFilterOptions"
            emit-value
            map-options
            outlined
            dense
            label="Age group"
            class="col-12 col-md-3"
          />
          <q-toggle
            v-model="missingSectionsOnly"
            color="deep-orange"
            label="Show only claims with missing sections"
            class="col-12 col-md-4"
          />
          <q-toggle
            v-model="ghanaCardMemberOnly"
            color="orange"
            label="Show only Ghana Card Member No (need To HIN)"
            class="col-12 col-md-5"
          />
          <q-banner
            v-if="ghanaCardMemberCount > 0"
            dense
            rounded
            class="bg-orange-1 text-orange-10 col-12"
          >
            <template #avatar><q-icon name="badge" color="orange" /></template>
            {{ ghanaCardMemberCount }} claim(s) still have a Ghana Card as Member No.
            Use <strong>To HIN</strong> on each claim (or set HIN / insurance number) before exporting.
            <template #action>
              <q-btn
                flat
                dense
                color="orange-10"
                label="Filter them"
                @click="applyGhanaCardMemberFilter()"
              />
            </template>
          </q-banner>
          <q-space />
          <q-btn
            color="secondary"
            icon="refresh"
            label="Refresh"
            :loading="refreshing"
            @click="refreshCurrentBatch"
          />
          <q-btn
            color="negative"
            icon="flag"
            :disable="selectedBulkItemIds.length === 0"
            :label="selectedBulkItemIds.length ? `Flag ${selectedBulkItemIds.length}` : 'Flag selected'"
            :loading="bulkUpdating"
            outline
            @click="bulkSetStatus('flag')"
          />
          <q-btn
            color="warning"
            icon="undo"
            :disable="selectedBulkItemIds.length === 0"
            :label="selectedBulkItemIds.length ? `Revert ${selectedBulkItemIds.length}` : 'Revert selected'"
            :loading="bulkUpdating"
            outline
            @click="bulkSetStatus('reopen')"
          />
          <q-btn
            color="primary"
            icon="edit"
            :disable="selectedBulkItemIds.length === 0"
            :label="selectedBulkItemIds.length ? `Mark draft ${selectedBulkItemIds.length}` : 'Mark draft selected'"
            :loading="bulkUpdating"
            outline
            @click="bulkSetStatus('reopen')"
          />
          <q-btn color="primary" icon="download" :label="selectedItemIds.length ? `Export ${selectedItemIds.length} selected` : 'Export selected'" :disable="selectedItemIds.length === 0" :loading="exporting" @click="exportSelected" />
        </q-card-section>
      </section>

      <section class="diag-panel">
        <div class="panel-body table-wrap">
          <q-markup-table flat dense bordered separator="horizontal" wrap-cells>
            <thead>
              <tr>
                <th class="text-left">#</th>
                <th class="text-left">
                  <div class="row items-center q-gutter-xs no-wrap">
                    <span>Select</span>
                    <q-checkbox
                      :model-value="allFilteredSelected"
                      :indeterminate="someFilteredSelected"
                      dense
                      @update:model-value="toggleSelectAllFiltered"
                    />
                  </div>
                </th>
                <th class="text-left">Claim ID</th>
                <th class="text-left">Client</th>
                <th class="text-left">Hosp Rec No</th>
                <th class="text-left">Age</th>
                <th class="text-left">Visit Start Date</th>
                <th class="text-left">Check Code</th>
                <th class="text-right">Claim Total</th>
                <th class="text-left">Status / Missing</th>
                <th class="text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, pageIndex) in pagedClaims" :key="row.id">
                <td>{{ ((currentPage - 1) * rowsPerPage) + pageIndex + 1 }}</td>
                <td>
                  <q-checkbox
                    :model-value="selectedBulkItemIds.includes(row.id)"
                    @update:model-value="toggleBulkSelected(row.id, $event)"
                    dense
                  />
                </td>
                <td>{{ row.claim_claim_id }}</td>
                <td>{{ claimClientName(row) || '-' }}</td>
                <td>{{ claimHospitalRecNo(row) || '-' }}</td>
                <td>{{ claimClientAge(row) }}</td>
                <td>{{ formatVisitStartDate(row.visit_start_date) }}</td>
                <td>{{ claimCheckCode(row) || '-' }}</td>
                <td class="text-right">
                  <template v-if="totalsLoading && row.total_claim_amount == null">
                    <q-spinner-dots size="16px" color="primary" />
                  </template>
                  <template v-else>
                    {{ formatCurrency(row.total_claim_amount) }}
                  </template>
                </td>
                <td>
                  <q-badge :color="claimStatusColor(row.status)" :label="vetStatusLabel(row.status)" />
                  <q-badge v-if="row.pharmacy_vetted" class="q-ml-xs q-mt-xs" dense color="teal" label="Pharmacy" />
                  <q-badge v-if="row.doctor_vetted" class="q-ml-xs q-mt-xs" dense color="indigo" label="Doctor" />
                  <q-chip
                    v-if="row.status === 'flagged' && row.flag_comment"
                    class="q-ml-sm q-mt-xs"
                    dense
                    size="sm"
                    color="grey-3"
                    text-color="dark"
                    icon="comment"
                    :label="row.flag_comment"
                  />
                  <q-badge
                    v-if="row.needs_hin_conversion"
                    class="q-ml-sm q-mt-xs"
                    color="orange"
                    label="Ghana Card Member No — use To HIN"
                  />
                  <q-badge
                    v-if="row.has_missing_sections"
                    class="q-ml-sm q-mt-xs"
                    color="deep-orange"
                    :label="`Missing: ${(row.missing_sections || []).map(prettySectionName).join(', ')}`"
                  />
                  <q-badge
                    v-if="row.no_clinical_sections"
                    class="q-ml-sm q-mt-xs"
                    color="red-8"
                    label="No diagnosis/investigation/medicine/procedure"
                  />
                </td>
                <td class="text-right">
                  <div class="row q-gutter-xs justify-end">
                    <q-btn
                      size="sm"
                      color="primary"
                      label="Edit"
                      :disable="row.status === 'finalized'"
                      @click="editImportedClaim(row)"
                    />
                    <q-btn
                      size="sm"
                      color="purple"
                      label="View"
                      @click="viewImportedClaim(row)"
                    />
                    <q-btn
                      v-if="isClaimExportable(row)"
                      size="sm"
                      color="teal"
                      label="Export"
                      :loading="exportingSingleItemId === row.id"
                      @click="exportSingleClaim(row)"
                    />
                    <q-btn v-if="row.status !== 'finalized'" size="sm" color="positive" label="Finalize" :loading="statusLoadingItemId === row.id" outline @click="setClaimFinalized(row)" />
                    <q-btn
                      v-if="row.status !== 'finalized' && row.status !== 'flagged'"
                      size="sm"
                      color="negative"
                      label="Flag claim"
                      :loading="statusLoadingItemId === row.id"
                      outline
                      @click="flagClaim(row)"
                    />
                    <q-btn v-if="row.status === 'finalized' || row.status === 'pharmacy_vetted' || row.status === 'doctor_vetted' || row.status === 'vetted' || row.status === 'flagged'" size="sm" color="warning" :label="row.status === 'flagged' ? 'Mark draft' : 'Revert'" :loading="statusLoadingItemId === row.id" outline @click="revertClaim(row)" />
                    <q-checkbox v-if="isClaimExportable(row)" :model-value="selectedItemIds.includes(row.id)" label="Export" @update:model-value="toggleExport(row.id, $event)" />
                  </div>
                </td>
              </tr>
              <tr v-if="pagedClaims.length === 0">
                <td colspan="11" class="text-center text-grey-7 q-pa-md">No claims match the current filters.</td>
              </tr>
            </tbody>
          </q-markup-table>
        </div>
      </section>
      <div class="row items-center q-gutter-md q-mt-md">
        <q-select
          v-model="rowsPerPage"
          :options="rowsPerPageOptions"
          emit-value
          map-options
          outlined
          dense
          label="Rows per page"
          class="col-12 col-md-2"
        />
        <q-space />
        <q-pagination
          v-model="currentPage"
          :max="maxPages"
          direction-links
          boundary-links
          color="primary"
        />
      </div>
    </template>
  </q-page>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue';
import HmsPageHeader from '../components/ui/HmsPageHeader.vue';
import HmsButton from '../components/ui/HmsButton.vue';
import { useRoute, useRouter } from 'vue-router';
import { useQuasar } from 'quasar';
import { claimsAPI } from '../services/api';
import { useAuthStore } from '../stores/auth';
import { setGhimsNavIds } from '../utils/claimNav';
import { Trash2 } from 'lucide-vue-next';
import {
  isClaimExportable,
  confirmExportWithVettingWarning,
  statusColor as vetStatusColor,
  statusLabel as vetStatusLabel,
  isPharmacyVettedStatus,
  isDoctorVettedStatus,
  hasPharmacyVetted,
  hasDoctorVetted,
} from '../utils/claimVetting';
import {
  parseExportErrorDetail,
  exportErrorMessage,
  isGhanaCardMemberExportError,
} from '../utils/exportErrorDetail';

const $route = useRoute();
const $router = useRouter();
const $q = useQuasar();
const authStore = useAuthStore();
const canDeleteImportBatch = computed(() => {
  const roles = (authStore.allUserRoles || []).map((r) => String(r || '').trim());
  return roles.includes('Admin') || authStore.isSuperAdmin;
});
const uploadFile = ref(null);
const uploading = ref(false);
const exporting = ref(false);
const refreshing = ref(false);
const totalsLoading = ref(false);
const exportingSingleItemId = ref(null);
const statusLoadingItemId = ref(null);
const bulkUpdating = ref(false);
const batches = ref([]);
const viewingBatchId = ref(null);
const currentBatch = ref(null);
const selectedItemIds = ref([]);
const selectedBulkItemIds = ref([]);
const filtersLocked = ref(false);
const searchText = ref('');
const attendanceFilter = ref('all');
const specialtyFilter = ref('all');
const serviceTypeFilter = ref('all');
const statusFilter = ref('all');
const ageGroupFilter = ref('all');
const missingSectionsOnly = ref(false);
const ghanaCardMemberOnly = ref(false);
const currentPage = ref(1);
const rowsPerPage = ref(20);
const rowsPerPageOptions = [
  { label: '10', value: 10 },
  { label: '20', value: 20 },
  { label: '50', value: 50 },
  { label: '100', value: 100 },
];
const FILTER_LOCK_KEY = 'ghimsImportFiltersLocked';
const FILTERS_KEY = 'ghimsImportFiltersState';
const statusFilterOptions = [
  { label: 'All', value: 'all' },
  { label: 'Draft', value: 'draft' },
  { label: 'Flagged', value: 'flagged' },
  { label: 'Pharmacy vetted', value: 'pharmacy_vetted' },
  { label: 'Doctor vetted', value: 'doctor_vetted' },
  { label: 'Pharmacy + doctor vetted', value: 'vetted' },
  { label: 'Finalized', value: 'finalized' },
];
const ageGroupFilterOptions = [
  { label: 'All', value: 'all' },
  { label: 'Kids (0-11)', value: 'kids' },
  { label: 'Adults (12+)', value: 'adults' },
];

const STANDARD_ATTENDANCE_TYPES = ['EAE', 'CFU', 'ANC', 'PNC'];

const attendanceFilterOptions = computed(() => {
  const rows = currentBatch.value?.claims || [];
  const fromData = rows
    .map((r) => String(r.type_of_attendance || '').trim())
    .filter(Boolean);
  const vals = Array.from(new Set([...STANDARD_ATTENDANCE_TYPES, ...fromData]));
  vals.sort((a, b) => {
    const ia = STANDARD_ATTENDANCE_TYPES.indexOf(a);
    const ib = STANDARD_ATTENDANCE_TYPES.indexOf(b);
    if (ia !== -1 || ib !== -1) {
      return (ia === -1 ? 999 : ia) - (ib === -1 ? 999 : ib);
    }
    return a.localeCompare(b);
  });
  return [{ label: 'All', value: 'all' }, ...vals.map((v) => ({ label: v, value: v }))];
});

const specialtyFilterOptions = computed(() => {
  const rows = currentBatch.value?.claims || [];
  const vals = Array.from(new Set(rows.map((r) => String(r.specialty_attended || '').trim()).filter(Boolean)));
  vals.sort((a, b) => a.localeCompare(b));
  return [{ label: 'All', value: 'all' }, ...vals.map((v) => ({ label: v, value: v }))];
});

function getServiceType(row) {
  return String(
    row?.type_of_service
      || row?.payload?.typeOfService
      || row?.payload?.type_of_service
      || ''
  )
    .trim()
    .toUpperCase();
}

const serviceTypeFilterOptions = computed(() => {
  const rows = currentBatch.value?.claims || [];
  const vals = Array.from(
    new Set(
      rows
        .map((r) => getServiceType(r))
        .filter((v) => v === 'IPD' || v === 'OPD')
    )
  );
  vals.sort((a, b) => a.localeCompare(b));
  return [{ label: 'All', value: 'all' }, ...vals.map((v) => ({ label: v, value: v }))];
});

const filteredClaims = computed(() => {
  const rows = currentBatch.value?.claims || [];
  const q = String(searchText.value || '').trim().toLowerCase();
  const out = rows.filter((r) => {
    if (missingSectionsOnly.value && !r.no_clinical_sections) return false;
    if (ghanaCardMemberOnly.value && !r.needs_hin_conversion) return false;
    if (statusFilter.value !== 'all') {
      const sf = statusFilter.value;
      if (sf === 'pharmacy_vetted') {
        if (!hasPharmacyVetted(r)) return false;
      } else if (sf === 'doctor_vetted') {
        if (!hasDoctorVetted(r)) return false;
      } else if (sf === 'vetted') {
        if (!(hasPharmacyVetted(r) && hasDoctorVetted(r))) return false;
      } else if ((r.status || '').toLowerCase() !== sf) {
        return false;
      }
    }
    if (serviceTypeFilter.value !== 'all' && getServiceType(r) !== serviceTypeFilter.value) return false;
    const age = claimClientAgeYears(r);
    if (ageGroupFilter.value === 'kids' && !(age !== null && age <= 11)) return false;
    if (ageGroupFilter.value === 'adults' && !(age !== null && age >= 12)) return false;
    if (attendanceFilter.value !== 'all' && String(r.type_of_attendance || '').trim() !== attendanceFilter.value) return false;
    if (specialtyFilter.value !== 'all' && String(r.specialty_attended || '').trim() !== specialtyFilter.value) return false;
    if (!q) return true;
    const hay = [
      r.client_name,
      r.hospital_rec_no,
      r.claim_claim_id,
      r.claim_check_code,
      r.member_no,
      getServiceType(r),
      r.type_of_attendance,
      r.specialty_attended,
    ]
      .map((x) => String(x || '').toLowerCase())
      .join(' ');
    return hay.includes(q);
  });
  return out;
});

const ghanaCardMemberCount = computed(() =>
  (currentBatch.value?.claims || []).filter((r) => r.needs_hin_conversion).length
);

const filteredRevenue = computed(() => {
  return filteredClaims.value.reduce((sum, row) => sum + (Number(row.total_claim_amount) || 0), 0);
});

const formatCurrency = (amount) => {
  if (amount == null || Number.isNaN(Number(amount))) return 'N/A';
  return new Intl.NumberFormat('en-GH', { style: 'currency', currency: 'GHS' }).format(Number(amount));
};

const batchPharmacyVettedCount = computed(() =>
  (currentBatch.value?.claims || []).filter((r) => isPharmacyVettedStatus(r)).length
);
const batchDoctorVettedCount = computed(() =>
  (currentBatch.value?.claims || []).filter((r) => isDoctorVettedStatus(r)).length
);

const allExportableSelected = computed(() => {
  const ids = (currentBatch.value?.claims || [])
    .filter((r) => isClaimExportable(r))
    .map((r) => Number(r.id));
  if (!ids.length) return false;
  return ids.every((id) => selectedItemIds.value.includes(id));
});

const allFilteredSelected = computed(() => {
  const ids = filteredClaims.value.map((r) => Number(r.id));
  if (!ids.length) return false;
  const selected = new Set((selectedBulkItemIds.value || []).map((x) => Number(x)));
  return ids.every((id) => selected.has(id));
});

const someFilteredSelected = computed(() => {
  const ids = filteredClaims.value.map((r) => Number(r.id));
  if (!ids.length) return false;
  const selected = new Set((selectedBulkItemIds.value || []).map((x) => Number(x)));
  const selectedCount = ids.reduce((acc, id) => acc + (selected.has(id) ? 1 : 0), 0);
  return selectedCount > 0 && selectedCount < ids.length;
});

const maxPages = computed(() => {
  const total = filteredClaims.value.length;
  const per = Number(rowsPerPage.value) || 20;
  return Math.max(1, Math.ceil(total / per));
});

const pagedClaims = computed(() => {
  const per = Number(rowsPerPage.value) || 20;
  const start = (Math.max(1, currentPage.value) - 1) * per;
  return filteredClaims.value.slice(start, start + per);
});

function formatDate(iso) { try { return iso ? new Date(iso).toLocaleString() : ''; } catch { return iso || ''; } }

function formatVisitStartDate(val) {
  if (!val) return '-';
  try {
    // Keep YYYY-MM-DD as a calendar date (avoid timezone shifting)
    if (/^\d{4}-\d{2}-\d{2}$/.test(String(val))) {
      const [y, m, d] = String(val).split('-').map(Number);
      return new Date(y, m - 1, d).toLocaleDateString();
    }
    return new Date(val).toLocaleDateString();
  } catch {
    return String(val);
  }
}

function claimClientName(row) {
  if (row?.client_name) return row.client_name;
  const p = row?.payload || {};
  return [p.surname, p.otherNames].filter(Boolean).join(' ').trim() || null;
}

function claimCheckCode(row) {
  return row?.claim_check_code || row?.payload?.claimCheckCode || null;
}

function claimHospitalRecNo(row) {
  return row?.hospital_rec_no || row?.payload?.hospitalRecNo || null;
}

function claimClientAge(row) {
  const age = claimClientAgeYears(row);
  return age !== null ? String(age) : '-';
}

function claimClientAgeYears(row) {
  const dobRaw = row?.date_of_birth || row?.payload?.dateOfBirth || row?.payload?.date_of_birth || '';
  if (!dobRaw) return null;
  const dob = new Date(dobRaw);
  if (Number.isNaN(dob.getTime())) return null;

  const now = new Date();
  let age = now.getFullYear() - dob.getFullYear();
  const birthdayNotReachedYet = (
    now.getMonth() < dob.getMonth()
    || (now.getMonth() === dob.getMonth() && now.getDate() < dob.getDate())
  );
  if (birthdayNotReachedYet) age -= 1;
  return age >= 0 ? age : null;
}

function claimStatusColor(status) {
  return vetStatusColor(status);
}

function prettySectionName(key) {
  return String(key || '').replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

function goBack() {
  if (viewingBatchId.value) {
    viewingBatchId.value = null; currentBatch.value = null; selectedItemIds.value = []; selectedBulkItemIds.value = [];
    $router.replace('/claims/ghims-import').catch(() => {});
  } else $router.push('/claims');
}

async function loadBatches() { batches.value = (await claimsAPI.getGhimsImportBatches()).data || []; }

async function uploadXml() {
  if (!uploadFile.value) return;
  uploading.value = true;
  try {
    const fd = new FormData(); fd.append('file', uploadFile.value);
    const res = await claimsAPI.uploadGhimsXml(fd);
    uploadFile.value = null;
    $q.notify({ type: 'positive', message: `Imported ${res.data.claim_count} claim(s)` });
    await loadBatches(); await openBatch(res.data.batch_id);
  } catch (e) { $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Import failed' }); }
  finally { uploading.value = false; }
}

function syncSelectedExports() {
  selectedItemIds.value = (currentBatch.value?.claims || []).filter((r) => isClaimExportable(r)).map((r) => r.id);
}

function toggleBulkSelected(itemId, checked) {
  const id = Number(itemId);
  if (checked && !selectedBulkItemIds.value.includes(id)) selectedBulkItemIds.value.push(id);
  if (!checked) selectedBulkItemIds.value = selectedBulkItemIds.value.filter((x) => x !== id);
}

function toggleSelectAllFiltered(checked) {
  const ids = filteredClaims.value.map((r) => Number(r.id));
  if (!ids.length) return;
  if (checked) {
    const merged = new Set([...(selectedBulkItemIds.value || []).map((x) => Number(x)), ...ids]);
    selectedBulkItemIds.value = Array.from(merged);
  } else {
    const remove = new Set(ids);
    selectedBulkItemIds.value = (selectedBulkItemIds.value || []).filter((id) => !remove.has(Number(id)));
  }
}

async function promptFlagComment(title) {
  return new Promise((resolve) => {
    $q.dialog({
      title: title || 'Flag imported claim',
      message: 'Enter a short reason (required). This helps other staff understand why it was flagged.',
      prompt: {
        model: '',
        type: 'textarea',
        isValid: (val) => Boolean(String(val || '').trim()),
        autogrow: true,
      },
      cancel: true,
      persistent: true,
      ok: { label: 'Flag', color: 'negative' },
    })
      .onOk((val) => resolve(String(val || '').trim()))
      .onCancel(() => resolve(null))
      .onDismiss(() => resolve(null));
  });
}

async function bulkSetStatus(action) {
  if (!selectedBulkItemIds.value.length || !viewingBatchId.value) return;
  const label = action === 'flag' ? 'Flag' : (action === 'finalize' ? 'Finalize' : 'Revert/Mark draft');
  const ok = await new Promise((resolve) => {
    $q.dialog({
      title: `${label} imported claims`,
      message: `Apply "${label}" to ${selectedBulkItemIds.value.length} selected claim(s)?`,
      cancel: true,
      persistent: true,
    }).onOk(() => resolve(true)).onCancel(() => resolve(false)).onDismiss(() => resolve(false));
  });
  if (!ok) return;

  bulkUpdating.value = true;
  try {
    let comment = null;
    if (action === 'flag') {
      comment = await promptFlagComment(`Flag ${selectedBulkItemIds.value.length} imported claim(s)`);
      if (!comment) return;
    }
    await claimsAPI.bulkUpdateGhimsImportItemsStatus(selectedBulkItemIds.value, action, comment);
    await loadBatchClaims(viewingBatchId.value);
    $q.notify({ type: 'positive', message: `${label} complete` });
  } catch (e) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || `Failed to ${label.toLowerCase()} selected claims` });
  } finally {
    bulkUpdating.value = false;
  }
}

/** Reload batch claims from the server without resetting filters or pagination. */
async function loadBatchClaims(id) {
  if (!id) return;
  const res = await claimsAPI.getGhimsImportBatch(id, { include_totals: false });
  currentBatch.value = res.data;
  syncSelectedExports();
  loadBatchClaimTotals(id);
}

async function loadBatchClaimTotals(id) {
  if (!id || !currentBatch.value) return;
  totalsLoading.value = true;
  try {
    const res = await claimsAPI.getGhimsImportBatchClaimTotals(id);
    const totalsMap = new Map(
      (res.data?.totals || []).map((row) => [Number(row.id), Number(row.total_claim_amount) || 0])
    );
    if (currentBatch.value?.claims?.length) {
      currentBatch.value = {
        ...currentBatch.value,
        total_revenue: res.data?.total_revenue ?? null,
        claims: currentBatch.value.claims.map((claim) => ({
          ...claim,
          total_claim_amount: totalsMap.has(claim.id)
            ? totalsMap.get(claim.id)
            : claim.total_claim_amount,
        })),
      };
    }
  } catch (e) {
    console.error('Failed to load batch claim totals', e);
  } finally {
    totalsLoading.value = false;
  }
}

async function openBatch(id) {
  viewingBatchId.value = id;
  currentPage.value = 1;
  $router.replace({ path: `/claims/ghims-import/batch/${id}` }).catch(() => {});
  await loadBatchClaims(id);
}

async function refreshCurrentBatch() {
  if (!viewingBatchId.value) return;
  refreshing.value = true;
  try {
    await loadBatches();
    await loadBatchClaims(viewingBatchId.value);
    $q.notify({ type: 'positive', message: 'Imported claims refreshed' });
  } catch (e) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Failed to refresh imported claims' });
  } finally {
    refreshing.value = false;
  }
}

function storeGhimsFilteredNav() {
  // Always navigate the currently filtered set (never the full unfiltered batch).
  setGhimsNavIds(
    filteredClaims.value
      .map((r) => Number(r.id))
      .filter((id) => Number.isFinite(id) && id > 0)
  );
}

function editImportedClaim(row) {
  if (!row?.id) return;
  if (row.status === 'finalized') {
    $q.notify({ type: 'warning', message: 'Finalized imported claims cannot be edited' });
    return;
  }
  storeGhimsFilteredNav();
  const route = $router.resolve({ path: `/claims/ghims-import/item/${row.id}` });
  window.open(route.href, '_blank');
}
function viewImportedClaim(row) {
  storeGhimsFilteredNav();
  const route = $router.resolve({ path: `/claims/ghims-import/item/${row.id}` });
  window.open(route.href, '_blank');
}


async function setClaimFinalized(row) {
  statusLoadingItemId.value = row.id;
  try { await claimsAPI.finalizeGhimsImportItem(row.id); await loadBatchClaims(viewingBatchId.value); }
  catch (e) { $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Failed to finalize imported claim' }); }
  finally { statusLoadingItemId.value = null; }
}

async function revertClaim(row) {
  statusLoadingItemId.value = row.id;
  try { await claimsAPI.reopenGhimsImportItem(row.id); await loadBatchClaims(viewingBatchId.value); }
  catch (e) { $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Failed to revert imported claim' }); }
  finally { statusLoadingItemId.value = null; }
}

async function flagClaim(row) {
  statusLoadingItemId.value = row.id;
  try {
    const comment = await promptFlagComment('Flag imported claim');
    if (!comment) return;
    await claimsAPI.flagGhimsImportItem(row.id, comment);
    await loadBatchClaims(viewingBatchId.value);
  }
  catch (e) { $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Failed to flag imported claim' }); }
  finally { statusLoadingItemId.value = null; }
}

function toggleExport(itemId, checked) {
  const id = Number(itemId);
  if (checked && !selectedItemIds.value.includes(id)) selectedItemIds.value.push(id);
  if (!checked) selectedItemIds.value = selectedItemIds.value.filter((x) => x !== id);
}

function toggleSelectAllExportable(checked) {
  const exportableIds = (currentBatch.value?.claims || [])
    .filter((r) => isClaimExportable(r))
    .map((r) => Number(r.id));
  if (checked) {
    const merged = new Set([...(selectedItemIds.value || []), ...exportableIds]);
    selectedItemIds.value = Array.from(merged);
  } else {
    selectedItemIds.value = (selectedItemIds.value || []).filter((id) => !exportableIds.includes(Number(id)));
  }
}

async function exportSelected() {
  if (!selectedItemIds.value.length) return;
  const rows = (currentBatch.value?.claims || []).filter((r) => selectedItemIds.value.includes(r.id));
  const ok = await confirmExportWithVettingWarning($q, rows);
  if (!ok) return;
  exporting.value = true;
  try {
    const res = await claimsAPI.exportGhimsImportItems(selectedItemIds.value);
    const blob = new Blob([res.data], { type: 'application/xml' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `NHIS_CLA_batch_${currentBatch.value?.file_name?.replace(/\.[^.]+$/, '') || 'export'}.xml`);
    document.body.appendChild(link); link.click(); link.remove(); window.URL.revokeObjectURL(url);
    $q.notify({ type: 'positive', message: 'Export complete' });
  } catch (e) {
    await handleExportError(e);
  } finally {
    exporting.value = false;
  }
}

async function exportSingleClaim(row) {
  if (!row?.id) return;
  const ok = await confirmExportWithVettingWarning($q, [row]);
  if (!ok) return;
  exportingSingleItemId.value = row.id;
  try {
    const res = await claimsAPI.exportGhimsImportItems([Number(row.id)]);
    const blob = new Blob([res.data], { type: 'application/xml' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `NHIS_CLA_claim_${row.claim_claim_id || row.id}.xml`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
    $q.notify({ type: 'positive', message: `Exported claim ${row.claim_claim_id || row.id}` });
  } catch (e) {
    await handleExportError(e);
  } finally {
    exportingSingleItemId.value = null;
  }
}

function applyGhanaCardMemberFilter(claimItems) {
  ghanaCardMemberOnly.value = true;
  currentPage.value = 1;
  if (Array.isArray(claimItems) && claimItems.length) {
    const ids = claimItems.map((c) => Number(c.item_id)).filter((id) => Number.isFinite(id) && id > 0);
    if (ids.length) {
      selectedBulkItemIds.value = ids;
      // Keep export selection only if those rows are exportable — still useful to highlight
    }
  }
}

async function handleExportError(e) {
  const detail = await parseExportErrorDetail(e);
  if (isGhanaCardMemberExportError(detail)) {
    const lines = detail.claims
      .slice(0, 40)
      .map((c) => {
        const name = c.client_name ? ` — ${c.client_name}` : '';
        const member = c.member_no ? ` (${c.member_no})` : '';
        return `• ${c.claim_id}${name}${member}`;
      })
      .join('<br>');
    const more =
      detail.claims.length > 40
        ? `<br><em>…and ${detail.claims.length - 40} more</em>`
        : '';
    $q.dialog({
      title: 'Ghana Card as Member No',
      message:
        `<p>${exportErrorMessage(detail)}</p>` +
        `<p class="q-mb-none"><strong>Claims that need To HIN / insurance number:</strong></p>` +
        `<div style="max-height:280px;overflow:auto;margin-top:8px">${lines}${more}</div>`,
      html: true,
      ok: { label: 'Filter these claims', color: 'orange', unelevated: true },
      cancel: { label: 'Close', flat: true },
      persistent: true,
    }).onOk(() => {
      applyGhanaCardMemberFilter(detail.claims);
    });
    return;
  }
  $q.notify({
    type: 'negative',
    message: exportErrorMessage(detail) || 'Export failed',
    multiLine: true,
    timeout: 8000,
  });
}

function deleteBatch(batch) {
  if (!canDeleteImportBatch.value) {
    $q.notify({ type: 'negative', message: 'Only Admin can delete imports' });
    return;
  }
  $q.dialog({
    title: 'Delete imported XML?',
    message:
      `Permanently delete “${batch.file_name}” and all ${batch.claim_count || 0} claim(s) in this batch? This cannot be undone.`,
    cancel: { label: 'Keep batch', flat: true, color: 'primary' },
    ok: { label: 'Delete permanently', color: 'negative', unelevated: true },
    persistent: true,
  }).onOk(async () => {
    try {
      await claimsAPI.deleteGhimsImportBatch(batch.id);
      await loadBatches();
      $q.notify({ type: 'positive', message: 'Import deleted' });
    } catch (e) {
      $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Failed to delete import' });
    }
  });
}

function persistFilterState() {
  try {
    localStorage.setItem(FILTER_LOCK_KEY, filtersLocked.value ? '1' : '0');
    if (!filtersLocked.value) return;
    localStorage.setItem(
      FILTERS_KEY,
      JSON.stringify({
        searchText: searchText.value,
        serviceTypeFilter: serviceTypeFilter.value,
        ageGroupFilter: ageGroupFilter.value,
        attendanceFilter: attendanceFilter.value,
        specialtyFilter: specialtyFilter.value,
        statusFilter: statusFilter.value,
        missingSectionsOnly: missingSectionsOnly.value,
        ghanaCardMemberOnly: ghanaCardMemberOnly.value,
        rowsPerPage: rowsPerPage.value,
      })
    );
  } catch (_) {}
}

function restoreFilterState() {
  try {
    filtersLocked.value = localStorage.getItem(FILTER_LOCK_KEY) === '1';
    if (!filtersLocked.value) return;
    const raw = localStorage.getItem(FILTERS_KEY);
    if (!raw) return;
    const s = JSON.parse(raw);
    searchText.value = s.searchText || '';
    serviceTypeFilter.value = s.serviceTypeFilter || 'all';
    ageGroupFilter.value = s.ageGroupFilter || 'all';
    attendanceFilter.value = s.attendanceFilter || 'all';
    specialtyFilter.value = s.specialtyFilter || 'all';
    statusFilter.value = s.statusFilter || 'all';
    missingSectionsOnly.value = Boolean(s.missingSectionsOnly);
    ghanaCardMemberOnly.value = Boolean(s.ghanaCardMemberOnly);
    rowsPerPage.value = Number(s.rowsPerPage) > 0 ? Number(s.rowsPerPage) : 20;
  } catch (_) {}
}

watch([searchText, serviceTypeFilter, ageGroupFilter, attendanceFilter, specialtyFilter, statusFilter, missingSectionsOnly, ghanaCardMemberOnly, rowsPerPage, filtersLocked], () => {
  currentPage.value = 1;
  persistFilterState();
});

watch(maxPages, (m) => {
  if (currentPage.value > m) currentPage.value = m;
});

onMounted(async () => {
  restoreFilterState();
  try { await loadBatches(); const batchId = Number($route.params.batchId); if (batchId) await openBatch(batchId); }
  catch (e) { $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Failed to load imports' }); }
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
.panel-title { font-size: var(--hms-text-base); font-weight: 750; color: var(--hms-text-primary); }
.panel-sub { margin-top: 0.15rem; font-size: var(--hms-text-xs); color: var(--hms-text-muted); }
.panel-body { padding: 1rem; }
.upload-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem;
}
.upload-file { flex: 1 1 16rem; min-width: 12rem; max-width: 28rem; }
.batch-list { display: flex; flex-direction: column; gap: 0.5rem; }
.batch-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  flex-wrap: wrap;
  padding: 0.75rem 0.85rem;
  border: 1px solid var(--hms-border);
  border-radius: var(--hms-radius-lg);
  background: var(--hms-surface, transparent);
  cursor: pointer;
  transition:
    background-color var(--hms-duration-fast) var(--hms-ease-out),
    border-color var(--hms-duration-fast) var(--hms-ease-out);
}
.batch-row:hover,
.batch-row:focus-visible {
  background: var(--hms-surface-hover, var(--hms-surface));
  border-color: var(--hms-border-strong);
  outline: none;
}
.batch-name { font-weight: 650; color: var(--hms-text-primary); font-size: var(--hms-text-sm); }
.batch-meta { margin-top: 0.2rem; font-size: var(--hms-text-xs); color: var(--hms-text-muted); }
.batch-actions { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; }
.batch-delete-btn {
  width: 2rem;
  height: 2rem;
  border-radius: var(--hms-radius-md);
  border: 1px solid transparent;
  background: transparent;
  color: var(--hms-text-muted);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  opacity: 0.55;
  transition:
    opacity var(--hms-duration-fast) var(--hms-ease-out),
    color var(--hms-duration-fast) var(--hms-ease-out),
    background-color var(--hms-duration-fast) var(--hms-ease-out),
    border-color var(--hms-duration-fast) var(--hms-ease-out);
}
.batch-row:hover .batch-delete-btn,
.batch-row:focus-within .batch-delete-btn {
  opacity: 0.85;
}
.batch-delete-btn:hover,
.batch-delete-btn:focus-visible {
  opacity: 1;
  color: var(--hms-critical, #ef4444);
  background: var(--hms-critical-muted, rgba(239, 68, 68, 0.12));
  border-color: color-mix(in srgb, var(--hms-critical, #ef4444) 28%, transparent);
  outline: none;
}
.empty-hint { font-size: var(--hms-text-sm); color: var(--hms-text-muted); margin: 0; }
.batch-toolbar :deep(.q-card-section) { padding: 1rem; }
.table-wrap { padding: 0; overflow-x: auto; }
</style>
