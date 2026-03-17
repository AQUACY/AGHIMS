<template>
  <q-page class="q-pa-md">
    <div class="text-h5 q-mb-md text-weight-bold glass-text">
      Create service (Records)
    </div>
    <div class="text-body2 glass-text-muted q-mb-lg">
      Enter the card number and visit number from the government system. The client has no generated ID in our system — everything comes from the external application.
    </div>
    <q-card class="glass-card" flat style="max-width: 520px;">
      <q-card-section>
        <q-form @submit="onSubmit" class="q-gutter-md">
          <q-input
            v-model="form.external_card_number"
            filled
            label="Card number (from government system)"
            :rules="[(v) => !!((v || '').trim()) || 'Required']"
            class="glass-text"
          />
          <q-input
            v-model="form.external_visit_number"
            filled
            label="Visit number (from government system)"
            :rules="[(v) => !!((v || '').trim()) || 'Required']"
            class="glass-text"
          />
          <q-input
            v-model="form.client_name"
            filled
            label="Client name (optional)"
            hint="For display only; identity is by card + visit number"
            class="glass-text"
          />
          <div class="row q-gutter-sm q-mt-md">
            <q-btn
              unelevated
              type="submit"
              label="Create service"
              class="glass-button"
              :loading="loading"
            />
            <q-btn
              flat
              label="Cancel"
              class="glass-button"
              :to="{ name: 'CompanionVisitList' }"
            />
          </div>
        </q-form>
      </q-card-section>
    </q-card>
  </q-page>
</template>

<script setup>
import { ref, reactive } from 'vue';
import { useRouter } from 'vue-router';
import { useQuasar } from 'quasar';
import { companionVisitsAPI } from '../../services/api';

const $q = useQuasar();
const router = useRouter();
const loading = ref(false);
const form = reactive({
  external_card_number: '',
  external_visit_number: '',
  client_name: '',
});

const onSubmit = async () => {
  loading.value = true;
  try {
    await companionVisitsAPI.create({
      external_card_number: form.external_card_number.trim(),
      external_visit_number: form.external_visit_number.trim(),
      client_name: form.client_name.trim() || undefined,
    });
    $q.notify({ type: 'positive', message: 'Service created', position: 'top' });
    router.push({ name: 'CompanionVisitList' });
  } catch (e) {
    const msg = e.response?.data?.detail || e.message || 'Failed to create service';
    $q.notify({ type: 'negative', message: msg, position: 'top' });
  } finally {
    loading.value = false;
  }
};
</script>
