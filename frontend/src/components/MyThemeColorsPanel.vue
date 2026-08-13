<template>
  <div class="my-theme-panel">
    <div class="text-subtitle2">{{ title }}</div>
    <p class="my-theme-hint">
      Colors apply only to your account. Other users keep their own theme. Leave a field empty for
      the default.
    </p>

    <div class="facility-color-grid">
      <div v-for="field in colorFields" :key="field.key" class="color-field">
        <div class="color-field__label">{{ field.label }}</div>
        <div class="color-field__row">
          <q-input
            v-model="form[field.key]"
            filled
            dense
            class="col"
            :placeholder="field.placeholder"
            :rules="[hexRule]"
            clearable
          >
            <template #append>
              <q-icon name="colorize" class="cursor-pointer">
                <q-popup-proxy cover transition-show="scale" transition-hide="scale">
                  <q-color
                    v-model="form[field.key]"
                    format-model="hex"
                    no-header-tabs
                    @update:model-value="onColorPicked(field.key, $event)"
                  />
                </q-popup-proxy>
              </q-icon>
            </template>
          </q-input>
          <div
            class="color-swatch"
            :style="{ background: swatch(form[field.key]) || field.fallback }"
          />
        </div>
      </div>
    </div>

    <div class="brand-preview q-mt-md">
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

    <div class="row q-gutter-sm items-center q-mt-md">
      <q-btn
        color="primary"
        label="Save my theme"
        :loading="saving"
        unelevated
        @click="save"
      />
      <q-btn flat label="Reload" :loading="loading" @click="reload" />
      <q-btn flat color="grey-7" label="Clear colors" @click="clearColors" />
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, watch, onMounted, onBeforeUnmount } from 'vue';
import { useQuasar } from 'quasar';
import { useFacilityStore } from '../stores/facility';
import { useThemeStore } from '../stores/theme';
import { applyFacilityBranding, normalizeBrandHex } from '../utils/facilityBranding';

defineProps({
  title: { type: String, default: 'My theme colors' },
});

const $q = useQuasar();
const facilityStore = useFacilityStore();
const themeStore = useThemeStore();

const form = reactive({
  bgColorLight: '',
  bgColorDark: '',
  accentColor: '',
  textColorLight: '',
  textColorDark: '',
});

const saving = ref(false);
const loading = ref(false);

const colorFields = [
  {
    key: 'bgColorLight',
    label: 'Light mode background',
    placeholder: '#f5f7fb',
    fallback: 'var(--hms-bg-primary)',
  },
  {
    key: 'textColorLight',
    label: 'Light mode text',
    placeholder: '#0f172a',
    fallback: '#0f172a',
  },
  {
    key: 'bgColorDark',
    label: 'Dark mode background',
    placeholder: '#09090b',
    fallback: '#09090b',
  },
  {
    key: 'textColorDark',
    label: 'Dark mode text',
    placeholder: '#fafafa',
    fallback: '#fafafa',
  },
  {
    key: 'accentColor',
    label: 'Accent',
    placeholder: '#3b82f6',
    fallback: 'var(--hms-accent)',
  },
];

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
    await facilityStore.fetchMyTheme();
    syncFormFromStore();
    previewBranding();
  } finally {
    loading.value = false;
  }
}

async function save() {
  saving.value = true;
  try {
    await facilityStore.saveMyTheme({
      bg_color_light: normalizeBrandHex(form.bgColorLight),
      bg_color_dark: normalizeBrandHex(form.bgColorDark),
      accent_color: normalizeBrandHex(form.accentColor),
      text_color_light: normalizeBrandHex(form.textColorLight),
      text_color_dark: normalizeBrandHex(form.textColorDark),
    });
    syncFormFromStore();
    facilityStore.applyBranding(themeStore.isDark);
    $q.notify({
      type: 'positive',
      message: 'Theme saved for your account only',
      position: 'top',
    });
  } catch (e) {
    const detail = e.response?.data?.detail;
    $q.notify({
      type: 'negative',
      message: typeof detail === 'string' ? detail : 'Failed to save theme',
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
.my-theme-hint {
  margin: 0.25rem 0 0.85rem;
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
  .facility-color-grid {
    grid-template-columns: 1fr;
  }
}
</style>
