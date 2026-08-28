<template>
  <q-layout view="hHh lpR fFf" class="license-setup-layout">
    <div class="app-background" :class="themeStore.isDark ? 'dark-gradient' : 'light-gradient'" />
    <q-page-container>
      <q-page class="license-setup-page q-pa-md">
        <div v-if="authStore.isAuthenticated" class="row items-center q-pa-sm q-mb-md rounded-borders text-white mini-license-bar">
          <q-btn flat dense round icon="arrow_back" color="white" @click="goBack" />
          <span class="text-subtitle1 q-ml-sm text-weight-medium">Installation license</span>
          <q-space />
          <q-btn
            flat
            dense
            round
            :icon="themeStore.isDark ? 'light_mode' : 'dark_mode'"
            color="white"
            @click="themeStore.toggleTheme()"
          />
        </div>
        <div class="q-mx-auto" style="max-width: 960px">
          <div v-if="!authStore.isAuthenticated" class="text-h5 text-weight-bold q-mb-md">Installation license</div>

          <q-banner v-if="!authStore.isAuthenticated" rounded class="bg-grey-3 text-dark q-mb-md">
            Sign in to manage licenses from the app toolbar. You can still activate a license below before first login if enforcement is on.
          </q-banner>

          <q-banner v-else-if="!canImport" rounded class="bg-info text-white q-mb-md">
            Only <strong>Admin</strong> or <strong>Management</strong> can import or replace a license file. Use the toolbar
            <strong>License</strong> link from any mode to open this page.
          </q-banner>

          <q-card flat bordered class="q-mb-md">
            <q-card-section class="text-h6">Current status</q-card-section>
            <q-separator />
            <q-card-section>
              <div v-if="statusLoading" class="text-grey">Loading…</div>
              <template v-else-if="publicStatus">
                <div class="row q-col-gutter-md">
                  <div class="col-12 col-sm-6">
                    <div class="text-caption text-grey-7">Enforcement</div>
                    <div>{{ publicStatus.enforcement_enabled ? 'On' : 'Off' }}</div>
                  </div>
                  <div class="col-12 col-sm-6">
                    <div class="text-caption text-grey-7">Valid for use</div>
                    <div :class="publicStatus.has_valid_license ? 'text-positive' : 'text-negative text-weight-medium'">
                      {{ publicStatus.has_valid_license ? 'Yes' : 'No' }}
                    </div>
                  </div>
                  <div class="col-12 col-sm-6" v-if="publicStatus.valid_until">
                    <div class="text-caption text-grey-7">Expires (claim)</div>
                    <div>{{ formatDt(publicStatus.valid_until) }}</div>
                  </div>
                  <div class="col-12" v-if="publicStatus.message">
                    <div class="text-caption text-grey-7">Message</div>
                    <div class="text-negative">{{ publicStatus.message }}</div>
                  </div>
                </div>
              </template>
              <div v-else class="text-grey">No status returned. Check that the HMS API is running.</div>
            </q-card-section>
          </q-card>

          <q-card v-if="summary && canImport" flat bordered class="q-mb-md">
            <q-card-section class="text-h6">Stored license file</q-card-section>
            <q-separator />
            <q-card-section>
              <div v-if="!summary.current_file?.has_file" class="text-grey">No license file has been imported yet.</div>
              <div v-else class="row q-col-gutter-md">
                <div class="col-12 col-sm-6">
                  <div class="text-caption text-grey-7">License ID</div>
                  <div class="ellipsis">{{ summary.current_file.license_id || '—' }}</div>
                </div>
                <div class="col-12 col-sm-6">
                  <div class="text-caption text-grey-7">Customer</div>
                  <div>{{ summary.current_file.customer_label || '—' }}</div>
                </div>
                <div class="col-12 col-sm-6">
                  <div class="text-caption text-grey-7">Expires (signed file)</div>
                  <div>{{ summary.current_file.valid_until ? formatDt(summary.current_file.valid_until) : '—' }}</div>
                </div>
                <div class="col-12 col-sm-6">
                  <div class="text-caption text-grey-7">Facility on license</div>
                  <div>{{ summary.current_file.facility_code_in_license || '(not bound)' }}</div>
                </div>
                <div class="col-12 col-sm-6">
                  <div class="text-caption text-grey-7">Facility in app</div>
                  <div>{{ summary.current_file.facility_code_installed || '(not set)' }}</div>
                </div>
                <div class="col-12 col-sm-6">
                  <div class="text-caption text-grey-7">Signature</div>
                  <div :class="summary.current_file.signature_valid ? 'text-positive' : 'text-negative'">
                    {{ summary.current_file.signature_valid ? 'Valid' : 'Invalid' }}
                  </div>
                </div>
                <div class="col-12" v-if="summary.current_file.verification_error">
                  <div class="text-caption text-grey-7">Verification</div>
                  <div class="text-negative">{{ summary.current_file.verification_error }}</div>
                </div>
                <div class="col-12" v-else-if="summary.current_file.signature_valid && summary.current_file.facility_matches === false">
                  <q-banner rounded class="bg-orange-2 text-dark q-mt-sm">
                    The license is bound to a different facility code than this installation. Import a new license file that
                    matches the current facility code, or change the facility back under Admin facility settings.
                  </q-banner>
                </div>
              </div>
            </q-card-section>
          </q-card>

          <q-card v-if="summary && canImport && historyRows.length" flat bordered class="q-mb-md">
            <q-card-section class="text-h6">Activation history</q-card-section>
            <q-separator />
            <q-markup-table flat dense wrap-cells>
              <thead>
                <tr>
                  <th>When</th>
                  <th>License ID</th>
                  <th>Customer</th>
                  <th>Valid until</th>
                  <th>Facility on file</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in historyRows" :key="row.id">
                  <td>{{ formatDt(row.activated_at) }}</td>
                  <td><code class="text-caption">{{ shortId(row.license_public_id) }}</code></td>
                  <td>{{ row.customer_label }}</td>
                  <td>{{ row.valid_until ? formatDt(row.valid_until) : '—' }}</td>
                  <td>{{ row.facility_code_in_license || '—' }}</td>
                </tr>
              </tbody>
            </q-markup-table>
            <q-card-section class="text-caption text-grey-7">
              Replacing a license: use <strong>Renew from portal</strong> after payment. Manual paste still works as a backup.
              History above keeps a record of each activation.
            </q-card-section>
          </q-card>

          <q-card v-if="canImport" flat bordered class="q-mb-md">
            <q-card-section class="text-h6">Security check (does not save)</q-card-section>
            <q-separator />
            <q-card-section>
              <p class="text-body2 q-mb-sm">
                Paste JSON and run checks: edited <code>claims</code>, wrong signature, wrong facility, or dates — each
                step reports pass/fail. Nothing is written to the server.
              </p>
              <q-input
                v-model="analyzeJsonText"
                filled
                type="textarea"
                rows="6"
                label="JSON to analyze (same format as activation file)"
                class="q-mb-md"
                :disable="!authStore.isAuthenticated"
              />
              <q-btn outline color="secondary" label="Run checks" :loading="analyzeLoading" @click="runAnalyze" />
              <q-list v-if="analyzeChecks.length" bordered separator class="rounded-borders q-mt-md">
                <q-item v-for="(c, idx) in analyzeChecks" :key="idx">
                  <q-item-section avatar>
                    <q-icon :name="c.pass ? 'check_circle' : 'cancel'" :color="c.pass ? 'positive' : 'negative'" />
                  </q-item-section>
                  <q-item-section>
                    <q-item-label>{{ c.label }}</q-item-label>
                    <q-item-label caption>{{ c.detail }}</q-item-label>
                  </q-item-section>
                </q-item>
              </q-list>
              <q-banner v-if="analyzePreview" rounded class="bg-grey-2 text-dark q-mt-md">
                <div class="text-caption text-weight-bold">Summary from file</div>
                <pre class="q-mt-xs text-caption" style="white-space: pre-wrap; margin: 0">{{ JSON.stringify(analyzePreview, null, 2) }}</pre>
              </q-banner>
            </q-card-section>
          </q-card>

          <q-card flat bordered class="q-mb-md">
            <q-card-section class="text-h6">Renew from the portal</q-card-section>
            <q-separator />
            <q-card-section>
              <p class="text-body2 q-mb-md">
                After the hospital pays on the license portal, HMS can collect the file itself. No JSON paste and no
                setup token. This applies the month that is paid <strong>and already started</strong> — not a future month.
              </p>
              <div class="row q-gutter-sm">
                <q-btn
                  color="primary"
                  unelevated
                  label="Renew from portal"
                  icon="cloud_download"
                  :loading="pullLoading"
                  :disable="authStore.isAuthenticated && !canImport"
                  @click="pullFromPortal"
                />
              </div>
              <p v-if="pullHint" class="text-caption q-mt-sm" :class="pullHintOk ? 'text-positive' : 'text-grey-7'">
                {{ pullHint }}
              </p>
            </q-card-section>
          </q-card>

          <q-card flat bordered class="q-mb-md q-mt-md">
            <q-card-section class="text-h6">Manual import (backup)</q-card-section>
            <q-separator />
            <q-card-section>
              <p class="text-body2 q-mb-md">
                Use this only if HMS cannot reach the portal. Paste the downloaded JSON and
                <strong>LICENSE_SETUP_TOKEN</strong> from the HMS server environment.
              </p>
              <q-input
                v-model="setupToken"
                filled
                label="Setup token"
                type="password"
                class="q-mb-md"
                :disable="!canImport && authStore.isAuthenticated"
              />
              <q-input
                v-model="jsonText"
                filled
                type="textarea"
                rows="10"
                label="Signed license JSON"
                class="q-mb-md"
                :disable="!canImport && authStore.isAuthenticated"
              />
              <div class="row q-gutter-sm">
                <q-btn
                  color="primary"
                  unelevated
                  label="Activate / replace"
                  :loading="loading"
                  :disable="(!canImport && authStore.isAuthenticated) || !setupToken.trim()"
                  @click="activate"
                />
                <q-btn flat label="Back" @click="goBack" />
              </div>
            </q-card-section>
          </q-card>
        </div>
      </q-page>
    </q-page-container>
  </q-layout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { Notify } from 'quasar';
import { licenseAPI } from '../services/api';
import { clearLicensePublicCache } from '../utils/licensePublicCache';
import { useThemeStore } from '../stores/theme';
import { useAuthStore } from '../stores/auth';

const router = useRouter();
const themeStore = useThemeStore();
const authStore = useAuthStore();
const setupToken = ref('');
const jsonText = ref('');
const loading = ref(false);
const pullLoading = ref(false);
const pullHint = ref('');
const pullHintOk = ref(false);
const statusLoading = ref(true);
const publicStatus = ref(null);
const summary = ref(null);

const analyzeJsonText = ref('');
const analyzeLoading = ref(false);
const analyzeChecks = ref([]);
const analyzePreview = ref(null);

const canImport = computed(() => authStore.canAccess(['Admin', 'Management']));

const historyRows = computed(() => summary.value?.activation_history || []);

function formatDt(iso) {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

function shortId(id) {
  if (!id) return '';
  return id.length > 12 ? `${id.slice(0, 8)}…` : id;
}

async function loadData() {
  statusLoading.value = true;
  try {
    const { data } = await licenseAPI.getPublicStatus();
    publicStatus.value = data;
    if (authStore.isAuthenticated && canImport.value) {
      try {
        const s = await licenseAPI.getActivationSummary();
        summary.value = s.data;
      } catch {
        summary.value = null;
      }
    } else {
      summary.value = null;
    }
  } catch (e) {
    publicStatus.value = null;
    Notify.create({ type: 'warning', message: 'Could not load license status.', position: 'top' });
  } finally {
    statusLoading.value = false;
  }
}

onMounted(() => {
  themeStore.initTheme();
  loadData();
});

const goBack = () => {
  if (authStore.isAuthenticated) {
    if (window.history.length > 1) {
      router.back();
    } else {
      router.push('/');
    }
  } else {
    router.push('/login');
  }
};

const runAnalyze = async () => {
  if (!authStore.isAuthenticated || !canImport.value) {
    Notify.create({ type: 'warning', message: 'Sign in as Admin or Management to run checks.', position: 'top' });
    return;
  }
  analyzeLoading.value = true;
  analyzeChecks.value = [];
  analyzePreview.value = null;
  try {
    const doc = JSON.parse(analyzeJsonText.value || '{}');
    const { data } = await licenseAPI.analyzeDocument(doc);
    analyzeChecks.value = Array.isArray(data.checks) ? data.checks : [];
    analyzePreview.value = data.claims_preview || null;
    Notify.create({
      type: data.ok ? 'positive' : 'warning',
      message: data.ok ? 'All checks passed (file still not saved until you activate).' : 'One or more checks failed.',
      position: 'top',
    });
  } catch (e) {
    if (e instanceof SyntaxError) {
      Notify.create({ type: 'negative', message: 'Invalid JSON syntax.', position: 'top' });
    } else {
      const msg = e.response?.data?.detail || e.message || 'Analyze failed';
      Notify.create({ type: 'negative', message: typeof msg === 'string' ? msg : JSON.stringify(msg), position: 'top' });
    }
  } finally {
    analyzeLoading.value = false;
  }
};

const pullFromPortal = async () => {
  if (authStore.isAuthenticated && !canImport.value) {
    Notify.create({ type: 'warning', message: 'Only Admin or Management can renew the license.', position: 'top' });
    return;
  }
  pullLoading.value = true;
  pullHint.value = '';
  try {
    const { data } = await licenseAPI.pullFromPortal();
    clearLicensePublicCache();
    pullHintOk.value = true;
    pullHint.value = data.detail || 'License updated from the portal.';
    Notify.create({ type: 'positive', message: pullHint.value, position: 'top' });
    await loadData();
    if (!authStore.isAuthenticated) {
      router.push('/login');
    }
  } catch (e) {
    pullHintOk.value = false;
    const msg = e.response?.data?.detail || e.message || 'Could not renew from the portal';
    pullHint.value = typeof msg === 'string' ? msg : JSON.stringify(msg);
    Notify.create({ type: 'negative', message: pullHint.value, position: 'top' });
  } finally {
    pullLoading.value = false;
  }
};

const activate = async () => {
  if (authStore.isAuthenticated && !canImport.value) {
    Notify.create({ type: 'warning', message: 'Only Admin or Management can activate.', position: 'top' });
    return;
  }
  loading.value = true;
  try {
    const doc = JSON.parse(jsonText.value);
    await licenseAPI.activate(doc, setupToken.value.trim());
    clearLicensePublicCache();
    jsonText.value = '';
    Notify.create({ type: 'positive', message: 'License saved. Replacing an older file overwrites the active license.', position: 'top' });
    await loadData();
    if (!authStore.isAuthenticated) {
      router.push('/login');
    }
  } catch (e) {
    const msg = e.response?.data?.detail || e.message || 'Activation failed';
    Notify.create({ type: 'negative', message: typeof msg === 'string' ? msg : JSON.stringify(msg), position: 'top' });
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
.license-setup-layout {
  min-height: 100vh;
}
.license-setup-layout .app-background {
  position: fixed;
  inset: 0;
  z-index: 0;
}
.license-setup-layout :deep(.q-page-container) {
  position: relative;
  z-index: 1;
}
.license-setup-page {
  min-height: 100%;
  background: rgba(0, 0, 0, 0.04);
}
.body--dark .license-setup-page {
  background: rgba(255, 255, 255, 0.06);
}
.mini-license-bar {
  background: linear-gradient(135deg, #1b5e20, #2e7d32);
}
.body--dark .mini-license-bar {
  background: linear-gradient(135deg, #0d2818, #1b5e20);
}
</style>
