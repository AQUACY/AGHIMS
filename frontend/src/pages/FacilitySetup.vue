<template>
  <q-page class="hms-page facility-branding-page">
    <HmsPageHeader title="Facility branding">
      <template #actions>
        <HmsButton variant="ghost" :disabled="loading || saving" @click="reload">
          Reset from server
        </HmsButton>
        <HmsButton variant="primary" :loading="saving" @click="onSubmit">Save</HmsButton>
      </template>
    </HmsPageHeader>

    <div class="facility-branding-layout">
      <aside class="diag-panel facility-branding-intro">
        <div class="facility-branding-intro__icon" aria-hidden="true">
          <q-icon name="business" size="28px" color="primary" />
        </div>
        <h2 class="facility-branding-intro__title">Identity & theme</h2>
        <p class="facility-branding-intro__body">
          Name and code appear in headers, login, and reports. Brand colors tint the page canvas,
          header, and sidebar; text colors keep labels readable on those backgrounds. Leave a color
          empty to keep the default for that slot.
        </p>
        <p class="facility-branding-intro__meta">
          Default name:
          <strong>{{ DEFAULT_FACILITY_DISPLAY_NAME }}</strong>
        </p>
      </aside>

      <q-card class="diag-panel facility-branding-card" flat>
        <q-card-section>
          <q-form @submit.prevent="onSubmit" class="q-gutter-md">
            <div class="text-subtitle2">Facility</div>
            <q-input
              v-model="form.displayName"
              label="Facility display name *"
              filled
              hint="Shown in toolbars, login, and reports"
              :rules="[(v) => !!(v && v.trim()) || 'Required']"
            />
            <q-input
              v-model="form.facilityCode"
              label="Facility code"
              filled
              hint="Short code shown next to the name (optional)"
            />

            <div class="text-subtitle2 q-mt-md">Brand colors</div>
            <p class="facility-branding-hint">
              Backgrounds and text apply per theme. Accent applies in both. Leave empty to keep
              defaults so text never clashes with a custom background.
            </p>

            <div class="facility-color-grid">
              <div class="color-field">
                <div class="color-field__label">Light mode background</div>
                <div class="color-field__row">
                  <q-input
                    v-model="form.bgColorLight"
                    filled
                    dense
                    class="col"
                    placeholder="#f5f7fb"
                    :rules="[hexRule]"
                    clearable
                  >
                    <template #append>
                      <q-icon name="colorize" class="cursor-pointer">
                        <q-popup-proxy cover transition-show="scale" transition-hide="scale">
                          <q-color
                            v-model="form.bgColorLight"
                            format-model="hex"
                            no-header-tabs
                            @update:model-value="onColorPicked('bgColorLight', $event)"
                          />
                        </q-popup-proxy>
                      </q-icon>
                    </template>
                  </q-input>
                  <div
                    class="color-swatch"
                    :style="{ background: swatch(form.bgColorLight) || 'var(--hms-bg-primary)' }"
                  />
                </div>
              </div>

              <div class="color-field">
                <div class="color-field__label">Light mode text</div>
                <div class="color-field__row">
                  <q-input
                    v-model="form.textColorLight"
                    filled
                    dense
                    class="col"
                    placeholder="#0f172a"
                    :rules="[hexRule]"
                    clearable
                  >
                    <template #append>
                      <q-icon name="colorize" class="cursor-pointer">
                        <q-popup-proxy cover transition-show="scale" transition-hide="scale">
                          <q-color
                            v-model="form.textColorLight"
                            format-model="hex"
                            no-header-tabs
                            @update:model-value="onColorPicked('textColorLight', $event)"
                          />
                        </q-popup-proxy>
                      </q-icon>
                    </template>
                  </q-input>
                  <div
                    class="color-swatch"
                    :style="{ background: swatch(form.textColorLight) || '#0f172a' }"
                  />
                </div>
              </div>

              <div class="color-field">
                <div class="color-field__label">Dark mode background</div>
                <div class="color-field__row">
                  <q-input
                    v-model="form.bgColorDark"
                    filled
                    dense
                    class="col"
                    placeholder="#09090b"
                    :rules="[hexRule]"
                    clearable
                  >
                    <template #append>
                      <q-icon name="colorize" class="cursor-pointer">
                        <q-popup-proxy cover transition-show="scale" transition-hide="scale">
                          <q-color
                            v-model="form.bgColorDark"
                            format-model="hex"
                            no-header-tabs
                            @update:model-value="onColorPicked('bgColorDark', $event)"
                          />
                        </q-popup-proxy>
                      </q-icon>
                    </template>
                  </q-input>
                  <div
                    class="color-swatch"
                    :style="{ background: swatch(form.bgColorDark) || '#09090b' }"
                  />
                </div>
              </div>

              <div class="color-field">
                <div class="color-field__label">Dark mode text</div>
                <div class="color-field__row">
                  <q-input
                    v-model="form.textColorDark"
                    filled
                    dense
                    class="col"
                    placeholder="#fafafa"
                    :rules="[hexRule]"
                    clearable
                  >
                    <template #append>
                      <q-icon name="colorize" class="cursor-pointer">
                        <q-popup-proxy cover transition-show="scale" transition-hide="scale">
                          <q-color
                            v-model="form.textColorDark"
                            format-model="hex"
                            no-header-tabs
                            @update:model-value="onColorPicked('textColorDark', $event)"
                          />
                        </q-popup-proxy>
                      </q-icon>
                    </template>
                  </q-input>
                  <div
                    class="color-swatch"
                    :style="{ background: swatch(form.textColorDark) || '#fafafa' }"
                  />
                </div>
              </div>

              <div class="color-field">
                <div class="color-field__label">Accent</div>
                <div class="color-field__row">
                  <q-input
                    v-model="form.accentColor"
                    filled
                    dense
                    class="col"
                    placeholder="#3b82f6"
                    :rules="[hexRule]"
                    clearable
                  >
                    <template #append>
                      <q-icon name="colorize" class="cursor-pointer">
                        <q-popup-proxy cover transition-show="scale" transition-hide="scale">
                          <q-color
                            v-model="form.accentColor"
                            format-model="hex"
                            no-header-tabs
                            @update:model-value="onColorPicked('accentColor', $event)"
                          />
                        </q-popup-proxy>
                      </q-icon>
                    </template>
                  </q-input>
                  <div
                    class="color-swatch"
                    :style="{ background: swatch(form.accentColor) || 'var(--hms-accent)' }"
                  />
                </div>
              </div>
            </div>

            <div class="brand-preview">
              <div class="brand-preview__label">Live preview (current theme)</div>
              <div class="brand-preview__canvas">
                <div class="brand-preview__chrome">
                  <span>Header / sidebar</span>
                  <span class="brand-preview__accent">Accent</span>
                </div>
                <div class="brand-preview__page">
                  <div class="brand-preview__page-title">Sample heading</div>
                  <div class="brand-preview__page-body">Secondary text on page background</div>
                </div>
              </div>
            </div>

            <div class="row q-gutter-sm items-center">
              <q-btn type="submit" color="primary" label="Save" :loading="saving" unelevated />
              <q-btn flat label="Reset from server" @click="reload" :loading="loading" />
              <q-btn flat color="grey-7" label="Clear brand colors" @click="clearColors" />
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </div>
  </q-page>
</template>

<script setup>
import { reactive, ref, watch, onMounted, onBeforeUnmount } from 'vue';
import { useQuasar } from 'quasar';
import HmsPageHeader from '../components/ui/HmsPageHeader.vue';
import HmsButton from '../components/ui/HmsButton.vue';
import { useFacilityStore, DEFAULT_FACILITY_DISPLAY_NAME } from '../stores/facility';
import { useThemeStore } from '../stores/theme';
import { applyFacilityBranding, normalizeBrandHex } from '../utils/facilityBranding';

const $q = useQuasar();
const facilityStore = useFacilityStore();
const themeStore = useThemeStore();

const form = reactive({
  displayName: '',
  facilityCode: '',
  bgColorLight: '',
  bgColorDark: '',
  accentColor: '',
  textColorLight: '',
  textColorDark: '',
});

const saving = ref(false);
const loading = ref(false);

function hexRule(v) {
  if (v == null || String(v).trim() === '') return true;
  return !!normalizeBrandHex(v) || 'Use a 6-digit hex color like #3b82f6';
}

function swatch(v) {
  return normalizeBrandHex(v) || '';
}

function onColorPicked(key, value) {
  form[key] = normalizeBrandHex(value) || '';
}

function syncFormFromStore() {
  form.displayName = facilityStore.displayName;
  form.facilityCode = facilityStore.facilityCode || '';
  form.bgColorLight = facilityStore.bgColorLight || '';
  form.bgColorDark = facilityStore.bgColorDark || '';
  form.accentColor = facilityStore.accentColor || '';
  form.textColorLight = facilityStore.textColorLight || '';
  form.textColorDark = facilityStore.textColorDark || '';
}

function previewBranding() {
  applyFacilityBranding({
    bgColorLight: normalizeBrandHex(form.bgColorLight),
    bgColorDark: normalizeBrandHex(form.bgColorDark),
    accentColor: normalizeBrandHex(form.accentColor),
    textColorLight: normalizeBrandHex(form.textColorLight),
    textColorDark: normalizeBrandHex(form.textColorDark),
    isDark: themeStore.isDark,
  });
}

function clearColors() {
  form.bgColorLight = '';
  form.bgColorDark = '';
  form.accentColor = '';
  form.textColorLight = '';
  form.textColorDark = '';
  previewBranding();
}

async function reload() {
  loading.value = true;
  try {
    await facilityStore.fetchPublic();
    syncFormFromStore();
    previewBranding();
  } finally {
    loading.value = false;
  }
}

async function onSubmit() {
  saving.value = true;
  try {
    await facilityStore.save({
      display_name: form.displayName.trim(),
      facility_code: form.facilityCode.trim() || null,
      bg_color_light: normalizeBrandHex(form.bgColorLight),
      bg_color_dark: normalizeBrandHex(form.bgColorDark),
      accent_color: normalizeBrandHex(form.accentColor),
      text_color_light: normalizeBrandHex(form.textColorLight),
      text_color_dark: normalizeBrandHex(form.textColorDark),
    });
    syncFormFromStore();
    facilityStore.applyBranding(themeStore.isDark);
    $q.notify({ type: 'positive', message: 'Facility settings saved', position: 'top' });
  } catch (e) {
    const detail = e.response?.data?.detail;
    $q.notify({
      type: 'negative',
      message: typeof detail === 'string' ? detail : 'Failed to save',
      position: 'top',
    });
  } finally {
    saving.value = false;
  }
}

watch(
  () => [
    form.bgColorLight,
    form.bgColorDark,
    form.accentColor,
    form.textColorLight,
    form.textColorDark,
    themeStore.isDark,
  ],
  () => {
    previewBranding();
  },
);

onMounted(async () => {
  await reload();
});

onBeforeUnmount(() => {
  facilityStore.applyBranding(themeStore.isDark);
});
</script>

<style scoped>
.facility-branding-layout {
  display: grid;
  grid-template-columns: minmax(220px, 280px) minmax(0, 1fr);
  gap: 1.25rem;
  align-items: start;
  max-width: 1100px;
}

.facility-branding-intro {
  padding: 1.25rem 1.15rem;
  position: sticky;
  top: calc(var(--hms-header-height) + 0.75rem);
}

.facility-branding-intro__icon {
  width: 2.75rem;
  height: 2.75rem;
  border-radius: var(--hms-radius-lg);
  background: var(--hms-accent-muted);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 0.85rem;
}

.facility-branding-intro__title {
  margin: 0 0 0.45rem;
  font-size: 1.05rem;
  font-weight: 750;
  color: var(--hms-text-primary);
}

.facility-branding-intro__body {
  margin: 0;
  font-size: 0.875rem;
  line-height: 1.5;
  color: var(--hms-text-secondary);
}

.facility-branding-intro__meta {
  margin: 0.9rem 0 0;
  font-size: 0.8125rem;
  color: var(--hms-text-muted);
}

.facility-branding-card {
  max-width: 720px;
}

.facility-branding-hint {
  margin: -0.35rem 0 0.25rem;
  font-size: 0.8125rem;
  color: var(--hms-text-muted);
}

.facility-color-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem 1.25rem;
}

.color-field__label {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--hms-text-secondary);
  margin-bottom: 0.35rem;
}

.color-field__row {
  display: flex;
  align-items: center;
  gap: 0.55rem;
}

.color-swatch {
  width: 2.25rem;
  height: 2.25rem;
  border-radius: var(--hms-radius-md);
  border: 1px solid var(--hms-border-strong);
  flex-shrink: 0;
}

.brand-preview {
  margin-top: 0.35rem;
}

.brand-preview__label {
  font-size: 0.75rem;
  color: var(--hms-text-muted);
  margin-bottom: 0.5rem;
}

.brand-preview__canvas {
  border-radius: var(--hms-radius-lg);
  border: 1px dashed var(--hms-border-strong);
  overflow: hidden;
  background: var(--hms-bg-primary);
}

.brand-preview__chrome {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.7rem 0.9rem;
  background: var(--hms-panel-bg);
  border-bottom: 1px solid var(--hms-border);
  color: var(--hms-text-primary);
  font-size: 0.8125rem;
  font-weight: 650;
}

.brand-preview__page {
  padding: 1.1rem 0.9rem;
}

.brand-preview__page-title {
  font-size: 0.9rem;
  font-weight: 700;
  color: var(--hms-text-primary);
  margin-bottom: 0.25rem;
}

.brand-preview__page-body {
  font-size: 0.8125rem;
  color: var(--hms-text-secondary);
}

.brand-preview__accent {
  color: #fff;
  background: var(--hms-accent);
  padding: 0.2rem 0.55rem;
  border-radius: var(--hms-radius-sm);
  font-size: 0.75rem;
}

@media (max-width: 900px) {
  .facility-branding-layout {
    grid-template-columns: 1fr;
  }

  .facility-branding-intro {
    position: static;
  }

  .facility-color-grid {
    grid-template-columns: 1fr;
  }
}
</style>
