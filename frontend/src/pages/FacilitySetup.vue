<template>
  <q-page class="q-pa-md">
    <div class="text-h4 q-mb-md text-weight-bold glass-text">Facility branding</div>
    <q-banner class="glass-card q-pa-md q-mb-md">
      <template v-slot:avatar>
        <q-icon name="business" color="primary" />
      </template>
      Set the facility name and code shown across the app (headers, prints, exports). Default display name before setup is
      <strong>{{ DEFAULT_FACILITY_DISPLAY_NAME }}</strong>.
    </q-banner>

    <q-card class="glass-card" flat style="max-width: 560px">
      <q-card-section>
        <q-form @submit.prevent="onSubmit" class="q-gutter-md">
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
          <div class="row q-gutter-sm">
            <q-btn type="submit" color="primary" label="Save" :loading="saving" unelevated />
            <q-btn flat label="Reset from server" @click="reload" :loading="loading" />
          </div>
        </q-form>
      </q-card-section>
    </q-card>
  </q-page>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue';
import { useQuasar } from 'quasar';
import { useFacilityStore, DEFAULT_FACILITY_DISPLAY_NAME } from '../stores/facility';

const $q = useQuasar();
const facilityStore = useFacilityStore();

const form = reactive({
  displayName: '',
  facilityCode: '',
});

const saving = ref(false);
const loading = ref(false);

async function reload() {
  loading.value = true;
  try {
    await facilityStore.fetchPublic();
    form.displayName = facilityStore.displayName;
    form.facilityCode = facilityStore.facilityCode || '';
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
    });
    $q.notify({ type: 'positive', message: 'Facility settings saved', position: 'top' });
  } catch (e) {
    $q.notify({
      type: 'negative',
      message: e.response?.data?.detail || 'Failed to save',
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
.glass-text {
  color: rgba(255, 255, 255, 0.95);
}
</style>
