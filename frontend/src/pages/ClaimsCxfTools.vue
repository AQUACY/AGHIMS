<template>
  <q-page class="hms-page">
    <HmsPageHeader
      title="CFX convert & diff"
      subtitle="Convert ClaimIT CFX packages to GHIMS XML, or compare a GHIMS XML export against a CFX to find claims missing from ClaimIT."
    >
      <template #actions>
        <HmsButton variant="ghost" size="sm" @click="$router.push('/claims')">Back</HmsButton>
      </template>
    </HmsPageHeader>

    <div class="tool-seg" role="tablist" aria-label="CFX tools">
      <button type="button" class="seg-btn" :class="{ active: tab === 'convert' }" @click="tab = 'convert'">
        Convert CFX → XML
      </button>
      <button type="button" class="seg-btn" :class="{ active: tab === 'diff' }" @click="tab = 'diff'">
        Compare XML vs CFX
      </button>
    </div>

    <template v-if="tab === 'convert'">
      <section class="diag-panel">
        <div class="panel-head">
          <div>
            <div class="panel-title">Convert CFX to claims XML</div>
            <div class="panel-sub">
              Upload a ClaimIT .cxf file. Output follows the same claims structure used by Import GHIMS XML.
            </div>
          </div>
        </div>
        <div class="panel-body">
          <div class="row q-col-gutter-md items-center">
            <q-file
              v-model="convertFile"
              label="Select CFX file"
              accept=".cxf,application/octet-stream"
              outlined
              dense
              clearable
              class="col-12 col-md-6"
              @update:model-value="onConvertFileChange"
            />
            <div class="col-12 col-md-6 action-row">
              <HmsButton
                variant="secondary"
                size="sm"
                :loading="previewing"
                :disabled="!convertFile"
                @click="previewCxf"
              >
                Preview
              </HmsButton>
              <HmsButton
                variant="primary"
                size="sm"
                :loading="converting"
                :disabled="!convertFile"
                @click="downloadConvertedXml"
              >
                Download XML
              </HmsButton>
            </div>
          </div>

          <div v-if="convertPreview" class="preview-block">
            <div class="chip-row">
              <span class="meta-chip">{{ convertPreview.claim_count }} claim(s)</span>
              <span
                v-for="(count, status) in (convertPreview.status_counts || {})"
                :key="status"
                class="meta-chip soft"
              >
                {{ status }}: {{ count }}
              </span>
            </div>
            <div v-if="convertPreview.meta?.dateGenerated" class="preview-meta">
              Generated: {{ convertPreview.meta.dateGenerated }}
              <span v-if="convertPreview.meta.signedByName"> · Signed by {{ convertPreview.meta.signedByName }}</span>
            </div>
          </div>
        </div>
      </section>
    </template>

    <template v-else>
      <section class="diag-panel">
        <div class="panel-head">
          <div>
            <div class="panel-title">Compare GHIMS XML vs ClaimIT CFX</div>
            <div class="panel-sub">
              Matched primarily by claim check code (CCC), with hospital record number as a tie-break.
            </div>
          </div>
        </div>
        <div class="panel-body">
          <div class="row q-col-gutter-md items-end">
            <q-file
              v-model="diffXmlFile"
              label="GHIMS / claims XML"
              accept=".xml,text/xml,application/xml"
              outlined
              dense
              clearable
              class="col-12 col-md-5"
            />
            <q-file
              v-model="diffCxfFile"
              label="ClaimIT CFX"
              accept=".cxf,application/octet-stream"
              outlined
              dense
              clearable
              class="col-12 col-md-5"
            />
            <div class="col-12 col-md-2">
              <HmsButton
                variant="primary"
                size="sm"
                :loading="diffing"
                :disabled="!diffXmlFile || !diffCxfFile"
                @click="runDiff"
              >
                Compare
              </HmsButton>
            </div>
          </div>
        </div>
      </section>

      <template v-if="diffResult">
        <div class="chip-row q-mb-md">
          <span class="meta-chip">XML: {{ diffResult.summary.xml_total }}</span>
          <span class="meta-chip">CFX: {{ diffResult.summary.cxf_total }}</span>
          <span class="meta-chip ok">Matched: {{ diffResult.summary.matched }}</span>
          <span class="meta-chip warn">Matched with diffs: {{ diffResult.summary.matched_with_differences }}</span>
          <span class="meta-chip bad">Missing from CFX: {{ diffResult.summary.xml_only }}</span>
          <span class="meta-chip soft">Only in CFX: {{ diffResult.summary.cxf_only }}</span>
        </div>

        <div class="q-mb-md">
          <HmsButton
            variant="danger"
            size="sm"
            :loading="downloadingMissing"
            :disabled="!diffResult.summary.xml_only"
            @click="downloadMissing"
          >
            Download {{ diffResult.summary.xml_only }} missing claim(s) as XML
          </HmsButton>
        </div>

        <section class="diag-panel">
          <div class="panel-head">
            <div>
              <div class="panel-title">Missing from CFX (in XML only)</div>
            </div>
          </div>
          <div class="panel-body table-wrap">
            <q-table
              class="diag-table"
              flat
              dense
              :rows="diffResult.xml_only"
              :columns="missingColumns"
              row-key="claimID"
              :pagination="{ rowsPerPage: 25 }"
            />
          </div>
        </section>

        <section class="diag-panel">
          <div class="panel-head">
            <div>
              <div class="panel-title">Matched claims</div>
            </div>
            <div class="panel-actions">
              <q-toggle
                v-model="showOnlyDiffs"
                dense
                label="Show only rows with differences"
                color="orange"
              />
            </div>
          </div>
          <div class="panel-body table-wrap">
            <q-table
              class="diag-table"
              flat
              dense
              :rows="filteredMatched"
              :columns="matchedColumns"
              row-key="claimID"
              :pagination="{ rowsPerPage: 25 }"
            >
              <template #body-cell-has_differences="props">
                <q-td :props="props">
                  <q-badge
                    :color="props.row.has_differences ? 'orange' : 'positive'"
                    :label="props.row.has_differences ? `${props.row.difference_count} diff(s)` : 'Identical'"
                  />
                </q-td>
              </template>
              <template #body-cell-actions="props">
                <q-td :props="props">
                  <HmsButton
                    v-if="props.row.has_differences"
                    variant="ghost"
                    size="sm"
                    @click="openDiffDetail(props.row)"
                  >
                    View diffs
                  </HmsButton>
                </q-td>
              </template>
            </q-table>
          </div>
        </section>

        <section class="diag-panel">
          <div class="panel-head">
            <div>
              <div class="panel-title">Only in CFX</div>
            </div>
          </div>
          <div class="panel-body table-wrap">
            <q-table
              class="diag-table"
              flat
              dense
              :rows="diffResult.cxf_only"
              :columns="cxfOnlyColumns"
              row-key="guid"
              :pagination="{ rowsPerPage: 25 }"
            />
          </div>
        </section>
      </template>
    </template>

    <q-dialog v-model="diffDetailOpen" maximized>
      <q-card class="diff-dialog">
        <q-card-section class="dialog-head row items-center">
          <div>
            <div class="dialog-title">Differences — {{ diffDetailRow?.claimID }}</div>
            <div class="dialog-sub">CCC {{ diffDetailRow?.claimCheckCode || '-' }}</div>
          </div>
          <q-space />
          <HmsButton variant="ghost" size="sm" v-close-popup>Close</HmsButton>
        </q-card-section>
        <q-separator />
        <q-card-section>
          <q-markup-table flat dense bordered>
            <thead>
              <tr>
                <th class="text-left">Field</th>
                <th class="text-left">XML</th>
                <th class="text-left">CFX</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(d, i) in (diffDetailRow?.differences || [])" :key="i">
                <td>{{ d.field }}</td>
                <td><code class="diff-cell">{{ formatDiffValue(d.xml) }}</code></td>
                <td><code class="diff-cell">{{ formatDiffValue(d.cxf) }}</code></td>
              </tr>
            </tbody>
          </q-markup-table>
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, computed } from 'vue';
import { useQuasar } from 'quasar';
import { claimsAPI } from '../services/api';
import HmsPageHeader from '../components/ui/HmsPageHeader.vue';
import HmsButton from '../components/ui/HmsButton.vue';

const $q = useQuasar();

const tab = ref('convert');

const convertFile = ref(null);
const convertPreview = ref(null);
const previewing = ref(false);
const converting = ref(false);

const diffXmlFile = ref(null);
const diffCxfFile = ref(null);
const diffing = ref(false);
const downloadingMissing = ref(false);
const diffResult = ref(null);
const showOnlyDiffs = ref(false);

const diffDetailOpen = ref(false);
const diffDetailRow = ref(null);

const missingColumns = [
  { name: 'claimID', label: 'Claim ID', field: 'claimID', align: 'left' },
  { name: 'client_name', label: 'Client', field: 'client_name', align: 'left' },
  { name: 'hospitalRecNo', label: 'Hosp Rec No', field: 'hospitalRecNo', align: 'left' },
  { name: 'claimCheckCode', label: 'CCC', field: 'claimCheckCode', align: 'left' },
  { name: 'memberNo', label: 'Member No', field: 'memberNo', align: 'left' },
  { name: 'typeOfService', label: 'Service', field: 'typeOfService', align: 'left' },
  { name: 'visit_start_date', label: 'Visit Start', field: 'visit_start_date', align: 'left' },
];

const matchedColumns = [
  { name: 'claimID', label: 'Claim ID', field: 'claimID', align: 'left' },
  { name: 'client_name', label: 'Client', field: 'client_name', align: 'left' },
  { name: 'claimCheckCode', label: 'CCC', field: 'claimCheckCode', align: 'left' },
  { name: 'hospitalRecNo', label: 'Hosp Rec No', field: 'hospitalRecNo', align: 'left' },
  { name: 'has_differences', label: 'Status', field: 'has_differences', align: 'center' },
  { name: 'actions', label: '', field: 'actions', align: 'right' },
];

const cxfOnlyColumns = [
  { name: 'guid', label: 'CFX GUID', field: 'guid', align: 'left' },
  { name: 'client_name', label: 'Client', field: 'client_name', align: 'left' },
  { name: 'claimCheckCode', label: 'CCC', field: 'claimCheckCode', align: 'left' },
  { name: 'hospitalRecNo', label: 'Hosp Rec No', field: 'hospitalRecNo', align: 'left' },
  { name: 'memberNo', label: 'Member No', field: 'memberNo', align: 'left' },
  { name: 'status', label: 'Status', field: 'status', align: 'left' },
  { name: 'visit_start_date', label: 'Visit Start', field: 'visit_start_date', align: 'left' },
];

const filteredMatched = computed(() => {
  const rows = diffResult.value?.matched || [];
  if (!showOnlyDiffs.value) return rows;
  return rows.filter((r) => r.has_differences);
});

function onConvertFileChange() {
  convertPreview.value = null;
}

function errorDetail(err) {
  return err?.response?.data?.detail || err?.message || 'Request failed';
}

async function blobErrorDetail(blobOrData) {
  if (!blobOrData) return null;
  if (typeof blobOrData === 'string') return blobOrData;
  if (blobOrData instanceof Blob) {
    try {
      const text = await blobOrData.text();
      const parsed = JSON.parse(text);
      return parsed?.detail || text;
    } catch {
      return null;
    }
  }
  if (typeof blobOrData === 'object' && blobOrData.detail) return blobOrData.detail;
  return null;
}

function triggerDownload(blob, filename) {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', filename);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

function filenameFromDisposition(header, fallback) {
  if (!header) return fallback;
  const m = /filename\*?=(?:UTF-8''|")?([^\";]+)/i.exec(header);
  if (!m) return fallback;
  try {
    return decodeURIComponent(m[1].replace(/"/g, ''));
  } catch {
    return m[1].replace(/"/g, '') || fallback;
  }
}

async function previewCxf() {
  if (!convertFile.value) return;
  previewing.value = true;
  try {
    const formData = new FormData();
    formData.append('file', convertFile.value);
    const res = await claimsAPI.previewCxf(formData);
    convertPreview.value = res.data;
    $q.notify({ type: 'positive', message: `Parsed ${res.data.claim_count} claim(s) from CFX` });
  } catch (e) {
    $q.notify({ type: 'negative', message: errorDetail(e) });
  } finally {
    previewing.value = false;
  }
}

async function downloadConvertedXml() {
  if (!convertFile.value) return;
  converting.value = true;
  try {
    const formData = new FormData();
    formData.append('file', convertFile.value);
    const res = await claimsAPI.convertCxfToXml(formData);
    if (res.status >= 400) {
      const msg = await blobErrorDetail(res.data);
      throw new Error(msg || 'Conversion failed');
    }
    const filename = filenameFromDisposition(
      res.headers?.['content-disposition'],
      `CFX_converted_${new Date().toISOString().slice(0, 10)}.xml`
    );
    triggerDownload(new Blob([res.data], { type: 'application/xml' }), filename);
    $q.notify({ type: 'positive', message: 'XML downloaded' });
  } catch (e) {
    const msg = (await blobErrorDetail(e?.response?.data)) || errorDetail(e);
    $q.notify({ type: 'negative', message: msg });
  } finally {
    converting.value = false;
  }
}

async function runDiff() {
  if (!diffXmlFile.value || !diffCxfFile.value) return;
  diffing.value = true;
  diffResult.value = null;
  try {
    const formData = new FormData();
    formData.append('xml_file', diffXmlFile.value);
    formData.append('cxf_file', diffCxfFile.value);
    const res = await claimsAPI.diffXmlVsCxf(formData);
    diffResult.value = res.data;
    $q.notify({
      type: 'positive',
      message: `Compared: ${res.data.summary.xml_only} missing from CFX, ${res.data.summary.matched} matched`,
    });
  } catch (e) {
    $q.notify({ type: 'negative', message: errorDetail(e) });
  } finally {
    diffing.value = false;
  }
}

async function downloadMissing() {
  if (!diffXmlFile.value || !diffCxfFile.value) return;
  downloadingMissing.value = true;
  try {
    const formData = new FormData();
    formData.append('xml_file', diffXmlFile.value);
    formData.append('cxf_file', diffCxfFile.value);
    const res = await claimsAPI.downloadXmlMissingFromCxf(formData);
    if (res.status >= 400) {
      const msg = await blobErrorDetail(res.data);
      throw new Error(msg || 'Download failed');
    }
    const filename = filenameFromDisposition(
      res.headers?.['content-disposition'],
      `XML_missing_from_CFX_${new Date().toISOString().slice(0, 10)}.xml`
    );
    triggerDownload(new Blob([res.data], { type: 'application/xml' }), filename);
    $q.notify({ type: 'positive', message: 'Missing claims XML downloaded' });
  } catch (e) {
    const msg = (await blobErrorDetail(e?.response?.data)) || errorDetail(e);
    $q.notify({ type: 'negative', message: msg });
  } finally {
    downloadingMissing.value = false;
  }
}

function openDiffDetail(row) {
  diffDetailRow.value = row;
  diffDetailOpen.value = true;
}

function formatDiffValue(val) {
  if (val == null) return '-';
  if (Array.isArray(val)) return val.join(', ') || '-';
  if (typeof val === 'object') return JSON.stringify(val);
  return String(val);
}
</script>

<style scoped>
.tool-seg {
  display: inline-flex;
  padding: 0.2rem;
  margin-bottom: 1rem;
  border: 1px solid var(--hms-border);
  border-radius: 999px;
  background: var(--hms-panel-bg);
  gap: 0.15rem;
}
.seg-btn {
  border: 0;
  background: transparent;
  color: var(--hms-text-secondary);
  font-size: var(--hms-text-sm);
  font-weight: 600;
  padding: 0.4rem 0.9rem;
  border-radius: 999px;
  cursor: pointer;
}
.seg-btn.active {
  background: var(--hms-accent-muted);
  color: var(--hms-accent);
}
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
.panel-actions { display: flex; align-items: center; gap: 0.5rem; }
.panel-body { padding: 1rem; }
.table-wrap { padding: 0; overflow-x: auto; }
.action-row { display: flex; flex-wrap: wrap; gap: 0.5rem; }
.preview-block { margin-top: 1rem; }
.chip-row { display: flex; flex-wrap: wrap; gap: 0.4rem; }
.meta-chip {
  display: inline-flex;
  align-items: center;
  padding: 0.25rem 0.65rem;
  border-radius: 999px;
  font-size: var(--hms-text-xs);
  font-weight: 650;
  background: var(--hms-accent-muted);
  color: var(--hms-accent);
}
.meta-chip.soft { background: rgba(100, 116, 139, 0.12); color: var(--hms-text-secondary); }
.meta-chip.ok { background: var(--hms-success-muted); color: var(--hms-success); }
.meta-chip.warn { background: var(--hms-warning-muted); color: var(--hms-warning); }
.meta-chip.bad { background: var(--hms-danger-muted, rgba(220, 38, 38, 0.12)); color: var(--hms-danger, #b91c1c); }
.preview-meta { margin-top: 0.5rem; font-size: var(--hms-text-xs); color: var(--hms-text-muted); }
.diff-dialog { border-radius: 0; }
.dialog-head { padding: 0.85rem 1rem; }
.dialog-title { font-size: var(--hms-text-lg); font-weight: 750; color: var(--hms-text-primary); }
.dialog-sub { margin-top: 0.15rem; font-size: var(--hms-text-xs); color: var(--hms-text-muted); }
.diff-cell {
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 12px;
}
</style>
