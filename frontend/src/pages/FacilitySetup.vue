<template>
  <q-page class="hms-page facility-branding-page">
    <HmsPageHeader title="Facility branding">
      <template #actions>
        <HmsButton variant="ghost" :disabled="loading || saving" @click="reload">
          Reset from server
        </HmsButton>
        <HmsButton variant="primary" :loading="saving" @click="onSubmit">Save facility</HmsButton>
      </template>
    </HmsPageHeader>

    <div class="facility-branding-layout">
      <aside class="diag-panel facility-branding-intro">
        <div class="facility-branding-intro__icon" aria-hidden="true">
          <q-icon name="business" size="28px" color="primary" />
        </div>
        <h2 class="facility-branding-intro__title">Facility identity</h2>
        <p class="facility-branding-intro__body">
          Name and code are shared for everyone — headers, login, and reports. Personal theme colors
          live under <strong>My theme colors</strong> in the sidebar.
        </p>
        <p class="facility-branding-intro__meta">
          Default name:
          <strong>{{ DEFAULT_FACILITY_DISPLAY_NAME }}</strong>
        </p>
      </aside>

      <q-card class="diag-panel facility-branding-card" flat>
        <q-card-section>
          <q-form @submit.prevent="onSubmit" class="q-gutter-md">
            <div class="text-subtitle2">Facility (shared)</div>
            <q-input
              v-model="form.displayName"
              label="Facility display name *"
              filled
              hint="Shown in toolbars, login, and reports for all users"
              :rules="[(v) => !!(v && v.trim()) || 'Required']"
            />
            <q-input
              v-model="form.facilityCode"
              label="Facility code"
              filled
              hint="Short code shown next to the name (optional)"
            />

            <div class="row q-gutter-sm items-center">
              <q-btn type="submit" color="primary" label="Save facility" :loading="saving" unelevated />
              <q-btn flat label="Reset from server" @click="reload" :loading="loading" />
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </div>
  </q-page>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue';
import { useQuasar } from 'quasar';
import HmsPageHeader from '../components/ui/HmsPageHeader.vue';
import HmsButton from '../components/ui/HmsButton.vue';
import { useFacilityStore, DEFAULT_FACILITY_DISPLAY_NAME } from '../stores/facility';

const $q = useQuasar();
const facilityStore = useFacilityStore();

const form = reactive({
  displayName: '',
  facilityCode: '',
});

const saving = ref(false);
const loading = ref(false);

function syncFormFromStore() {
  form.displayName = facilityStore.displayName;
  form.facilityCode = facilityStore.facilityCode || '';
}

async function reload() {
  loading.value = true;
  try {
    await facilityStore.fetchPublic();
    syncFormFromStore();
  } finally {
    loading.value = false;
  }
}

async function onSubmit() {
  saving.value = true;
  try {
    await facilityStore.saveIdentity({
      display_name: form.displayName.trim(),
      facility_code: form.facilityCode.trim() || null,
    });
    syncFormFromStore();
    $q.notify({
      type: 'positive',
      message: 'Facility name and code saved for everyone',
      position: 'top',
    });
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

onMounted(async () => {
  await reload();
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

@media (max-width: 900px) {
  .facility-branding-layout {
    grid-template-columns: 1fr;
  }

  .facility-branding-intro {
    position: static;
  }
}
</style>
