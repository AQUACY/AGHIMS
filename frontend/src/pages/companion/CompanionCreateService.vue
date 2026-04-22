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

function parseOutstandingPayload(err) {
  const detail = err?.response?.data?.detail;
  if (!detail || typeof detail !== 'object') return null;
  if (detail.code !== 'OUTSTANDING_BALANCE') return null;
  return detail;
}

function outstandingPromptMessage(payload) {
  const visits = Array.isArray(payload?.outstanding_visits) ? payload.outstanding_visits : [];
  const total = Number(payload?.total_due || 0);
  const sample = visits.slice(0, 3).map((v) => {
    const u = (v?.undertaking_status || '').toString().trim();
    const undertakingPart = u ? `, undertaking ${u}` : '';
    return `Visit ${v.external_visit_number}: GH¢ ${(Number(v.balance_due || 0)).toFixed(2)} (${v.status}${undertakingPart})`;
  });
  const more = visits.length > 3 ? `\n...and ${visits.length - 3} more visit(s)` : '';
  return `This client has previous unpaid companion bill(s).\nOutstanding total: GH¢ ${total.toFixed(2)}\n\n${sample.join('\n')}${more}\n\nIgnore and continue creating this new service?`;
}

function askOutstandingOverride(payload) {
  return new Promise((resolve) => {
    $q.dialog({
      title: 'Outstanding previous bill found',
      message: outstandingPromptMessage(payload),
      cancel: { label: 'No, stop creation', flat: true },
      ok: { label: 'Yes, ignore and continue', color: 'warning' },
      persistent: true,
    }).onOk(() => resolve(true)).onCancel(() => resolve(false)).onDismiss(() => resolve(false));
  });
}

const onSubmit = async () => {
  const card = form.external_card_number.trim();
  const visit = form.external_visit_number.trim();
  const clientName = form.client_name.trim() || undefined;
  let ignoreOutstanding = false;
  loading.value = true;
  try {
    const checkRes = await companionVisitsAPI.checkOutstanding(card, visit);
    const check = checkRes?.data || {};
    if (check.has_outstanding) {
      const proceed = await askOutstandingOverride(check);
      if (!proceed) {
        $q.notify({ type: 'warning', message: 'Creation stopped. Ask billing to clear the previous bill first.', position: 'top' });
        return;
      }
      ignoreOutstanding = true;
    }
    await companionVisitsAPI.create(
      {
        external_card_number: card,
        external_visit_number: visit,
        client_name: clientName,
      },
      { ignore_outstanding: ignoreOutstanding },
    );
    $q.notify({ type: 'positive', message: 'Service created', position: 'top' });
    router.push({ name: 'CompanionVisitList' });
  } catch (e) {
    const outstanding = parseOutstandingPayload(e);
    if (outstanding) {
      const proceed = await askOutstandingOverride(outstanding);
      if (proceed) {
        try {
          await companionVisitsAPI.create(
            {
              external_card_number: card,
              external_visit_number: visit,
              client_name: clientName,
            },
            { ignore_outstanding: true },
          );
          $q.notify({ type: 'positive', message: 'Service created', position: 'top' });
          router.push({ name: 'CompanionVisitList' });
          return;
        } catch (e2) {
          const msg2 = e2.response?.data?.detail?.message || e2.response?.data?.detail || e2.message || 'Failed to create service';
          $q.notify({ type: 'negative', message: msg2, position: 'top' });
          return;
        }
      }
      $q.notify({ type: 'warning', message: 'Creation stopped. Ask billing to clear the previous bill first.', position: 'top' });
      return;
    }
    const msg = e.response?.data?.detail || e.message || 'Failed to create service';
    $q.notify({ type: 'negative', message: msg, position: 'top' });
  } finally {
    loading.value = false;
  }
};
</script>
