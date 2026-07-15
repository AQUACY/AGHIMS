<template>
  <q-page class="q-pa-md">
    <div class="row items-center q-mb-md">
      <q-btn flat round dense icon="arrow_back" @click="$router.push('/claims')" />
      <div class="text-h4 q-ml-sm text-weight-bold glass-text">CFX Convert &amp; Diff</div>
    </div>
    <p class="text-body2 text-grey-8 q-mb-md">
      Convert ClaimIT CFX packages to GHIMS XML, or compare a GHIMS XML export against a CFX to find claims missing from ClaimIT.
    </p>

    <q-tabs v-model="tab" dense class="text-primary q-mb-md" active-color="primary" indicator-color="primary" align="left">
      <q-tab name="convert" icon="transform" label="Convert CFX → XML" />
      <q-tab name="diff" icon="compare_arrows" label="Compare XML vs CFX" />
    </q-tabs>

    <q-tab-panels v-model="tab" animated class="bg-transparent">
      <!-- Convert -->
      <q-tab-panel name="convert" class="q-pa-none">
        <q-card flat bordered class="glass-card">
          <q-card-section>
            <div class="text-h6 q-mb-sm">Convert CFX to claims XML</div>
            <div class="text-caption text-grey-7 q-mb-md">
              Upload a ClaimIT .cxf file. The output follows the same &lt;claims&gt;/&lt;claim&gt; structure used by Import GHIMS XML.
            </div>
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
              <q-btn
                color="secondary"
                outline
                label="Preview"
                :loading="previewing"
                :disable="!convertFile"
                @click="previewCxf"
              />
              <q-btn
                color="primary"
                label="Download XML"
                icon="download"
                :loading="converting"
                :disable="!convertFile"
                @click="downloadConvertedXml"
              />
            </div>

            <div v-if="convertPreview" class="q-mt-lg">
              <div class="row q-gutter-sm q-mb-sm">
                <q-chip color="primary" text-color="white" icon="folder">
                  {{ convertPreview.claim_count }} claim(s)
                </q-chip>
                <q-chip
                  v-for="(count, status) in (convertPreview.status_counts || {})"
                  :key="status"
                  outline
                  color="positive"
                >
                  {{ status }}: {{ count }}
                </q-chip>
              </div>
              <div v-if="convertPreview.meta?.dateGenerated" class="text-caption text-grey-7">
                Generated: {{ convertPreview.meta.dateGenerated }}
                <span v-if="convertPreview.meta.signedByName"> · Signed by {{ convertPreview.meta.signedByName }}</span>
              </div>
            </div>
          </q-card-section>
        </q-card>
      </q-tab-panel>

      <!-- Diff -->
      <q-tab-panel name="diff" class="q-pa-none">
        <q-card flat bordered class="glass-card q-mb-md">
          <q-card-section>
            <div class="text-h6 q-mb-sm">Compare GHIMS XML vs ClaimIT CFX</div>
            <div class="text-caption text-grey-7 q-mb-md">
              Claims are matched primarily by claim check code (CCC), with hospital record number as a tie-break.
              Download the XML claims that exist in the GHIMS file but were not found in the CFX.
            </div>
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
              <q-btn
                color="primary"
                label="Compare"
                icon="compare_arrows"
                :loading="diffing"
                :disable="!diffXmlFile || !diffCxfFile"
                @click="runDiff"
              />
            </div>
          </q-card-section>
        </q-card>

        <template v-if="diffResult">
          <div class="row q-gutter-sm q-mb-md">
            <q-chip color="blue-grey" text-color="white">XML: {{ diffResult.summary.xml_total }}</q-chip>
            <q-chip color="blue-grey" text-color="white">CFX: {{ diffResult.summary.cxf_total }}</q-chip>
            <q-chip color="positive" text-color="white">Matched: {{ diffResult.summary.matched }}</q-chip>
            <q-chip color="orange" text-color="white">
              Matched with diffs: {{ diffResult.summary.matched_with_differences }}
            </q-chip>
            <q-chip color="negative" text-color="white">
              Missing from CFX: {{ diffResult.summary.xml_only }}
            </q-chip>
            <q-chip outline color="grey-8">
              Only in CFX: {{ diffResult.summary.cxf_only }}
            </q-chip>
          </div>

          <div class="row q-gutter-md q-mb-md">
            <q-btn
              color="negative"
              icon="download"
              :label="`Download ${diffResult.summary.xml_only} missing claim(s) as XML`"
              :loading="downloadingMissing"
              :disable="!diffResult.summary.xml_only"
              @click="downloadMissing"
            />
          </div>

          <q-card flat bordered class="glass-card q-mb-md">
            <q-card-section>
              <div class="text-subtitle1 q-mb-sm">Missing from CFX (in XML only)</div>
              <q-table
                flat
                dense
                :rows="diffResult.xml_only"
                :columns="missingColumns"
                row-key="claimID"
                :pagination="{ rowsPerPage: 25 }"
              />
            </q-card-section>
          </q-card>

          <q-card flat bordered class="glass-card q-mb-md">
            <q-card-section>
              <div class="row items-center q-mb-sm">
                <div class="text-subtitle1">Matched claims</div>
                <q-space />
                <q-toggle
                  v-model="showOnlyDiffs"
                  dense
                  label="Show only rows with differences"
                  color="orange"
                />
              </div>
              <q-table
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
                    <q-btn
                      v-if="props.row.has_differences"
                      flat
                      dense
                      size="sm"
                      color="primary"
                      label="View diffs"
                      @click="openDiffDetail(props.row)"
                    />
                  </q-td>
                </template>
              </q-table>
            </q-card-section>
          </q-card>

          <q-card flat bordered class="glass-card">
            <q-card-section>
              <div class="text-subtitle1 q-mb-sm">Only in CFX</div>
              <q-table
                flat
                dense
                :rows="diffResult.cxf_only"
                :columns="cxfOnlyColumns"
                row-key="guid"
                :pagination="{ rowsPerPage: 25 }"
              />
            </q-card-section>
          </q-card>
        </template>
      </q-tab-panel>
    </q-tab-panels>

    <q-dialog v-model="diffDetailOpen" maximized>
      <q-card>
        <q-card-section class="row items-center">
          <div class="text-h6">
            Differences — {{ diffDetailRow?.claimID }}
            <span class="text-caption text-grey-7 q-ml-sm">CCC {{ diffDetailRow?.claimCheckCode || '-' }}</span>
          </div>
          <q-space />
          <q-btn flat round dense icon="close" v-close-popup />
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
.diff-cell {
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 12px;
}
</style>
