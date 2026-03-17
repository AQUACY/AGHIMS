<template>
  <q-page class="q-pa-md">
    <div v-if="loading" class="text-center q-pa-xl">
      <q-spinner size="48px" />
    </div>
    <template v-else-if="visit">
      <div class="row items-center justify-between q-mb-md">
        <div class="row items-center">
          <q-btn flat dense icon="arrow_back" @click="$router.push({ name: 'CompanionVisitList' })" />
          <div class="text-h5 text-weight-bold glass-text q-ml-sm">Service details</div>
        </div>
        <div class="row q-gutter-sm">
          <q-btn
            v-if="canEdit"
            flat
            label="Edit"
            icon="edit"
            class="glass-button"
            @click="openEditDialog"
          />
          <q-btn
            v-if="canDelete"
            flat
            label="Delete"
            icon="delete"
            class="glass-button"
            color="negative"
            @click="confirmDelete"
          />
        </div>
      </div>
      <q-card class="glass-card" flat>
        <q-card-section>
          <div class="row q-col-gutter-md">
            <div class="col-12 col-sm-6">
              <div class="text-caption glass-text-muted">Card number</div>
              <div class="text-body1">{{ visit.external_card_number }}</div>
            </div>
            <div class="col-12 col-sm-6">
              <div class="text-caption glass-text-muted">Visit number</div>
              <div class="text-body1">{{ visit.external_visit_number }}</div>
            </div>
            <div class="col-12 col-sm-6">
              <div class="text-caption glass-text-muted">Client name</div>
              <div class="text-body1">{{ visit.client_name || '—' }}</div>
            </div>
            <div class="col-12 col-sm-6">
              <div class="text-caption glass-text-muted">Status</div>
              <div class="text-body1">{{ visit.status }}</div>
            </div>
            <div class="col-12 col-sm-6">
              <div class="text-caption glass-text-muted">Created</div>
              <div class="text-body1">{{ formatDate(visit.created_at) }}</div>
            </div>
          </div>
          <div class="q-mt-lg text-body2 glass-text-muted">
            Billing and line items (lab, scan, xray, medication) will be added in the next steps.
          </div>
        </q-card-section>
      </q-card>

      <!-- Role-based action cards: active only for matching roles -->
      <div class="text-subtitle1 text-weight-medium glass-text q-mt-lg  q-mb-sm">Add services</div>
      <div class="row q-col-gutter-md q-ma-md">
        <q-card
          v-for="card in actionCards"
          :key="card.name"
          class="action-card col-12 col-sm-6 col-md-3 q-ma-sm"
          :class="{ 'action-card--inactive': !card.active }"
          flat
          :clickable="card.active && visit.status === 'open'"
          @click="card.active && visit.status === 'open' ? goTo(card.routeName) : null"
        >
          <q-card-section class="text-center">
            <q-icon :name="card.icon" :size="card.active ? '40px' : '32px'" :class="card.active ? 'text-primary' : 'text-grey-5'" />
            <div class="text-subtitle1 q-mt-sm" :class="card.active ? 'glass-text' : 'text-grey-6'">{{ card.title }}</div>
            <q-btn
              v-if="card.active && visit.status === 'open'"
              flat
              dense
              size="sm"
              label="Open"
              class="glass-button q-mt-sm"
              @click.stop="goTo(card.routeName)"
            />
            <div v-else-if="!card.active" class="text-caption text-grey-6 q-mt-sm">Not available for your role</div>
            <div v-else class="text-caption text-grey-6 q-mt-sm">Visit is closed</div>
          </q-card-section>
        </q-card>
      </div>
    </template>
    <div v-else class="text-body1">Visit not found.</div>

    <q-dialog v-model="showEditDialog" persistent>
      <q-card class="glass-card" style="min-width: 400px;">
        <q-card-section>
          <div class="text-h6">Edit service</div>
          <div class="text-caption glass-text-muted">Card and visit number can only be changed when the visit is open (to correct officer errors).</div>
        </q-card-section>
        <q-card-section>
          <q-form @submit="onSaveEdit" class="q-gutter-md">
            <q-input
              v-model="editForm.external_card_number"
              filled
              label="Card number (from government system)"
              :readonly="visit && visit.status === 'closed'"
              :rules="editForm.status === 'open' ? [(v) => !!((v || '').trim()) || 'Required when open'] : []"
              class="glass-text"
            />
            <q-input
              v-model="editForm.external_visit_number"
              filled
              label="Visit number (from government system)"
              :readonly="visit && visit.status === 'closed'"
              :rules="editForm.status === 'open' ? [(v) => !!((v || '').trim()) || 'Required when open'] : []"
              class="glass-text"
            />
            <q-input
              v-model="editForm.client_name"
              filled
              label="Client name (optional)"
              class="glass-text"
            />
            <q-select
              v-model="editForm.status"
              :options="statusOptions"
              filled
              label="Status"
              emit-value
              map-options
            />
            <div class="row q-gutter-sm justify-end">
              <q-btn flat label="Cancel" @click="showEditDialog = false" />
              <q-btn unelevated type="submit" label="Save" class="glass-button" :loading="saving" />
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useQuasar } from 'quasar';
import { useAuthStore } from '../../stores/auth';
import { companionVisitsAPI } from '../../services/api';

const route = useRoute();
const router = useRouter();
const $q = useQuasar();
const authStore = useAuthStore();
const loading = ref(true);
const visit = ref(null);
const showEditDialog = ref(false);
const saving = ref(false);
const editForm = ref({
  external_card_number: '',
  external_visit_number: '',
  client_name: '',
  status: 'open',
});

const statusOptions = [
  { label: 'Open', value: 'open' },
  { label: 'Closed', value: 'closed' },
];

const id = computed(() => route.params.id);

const canEdit = computed(() => {
  if (!visit.value) return false;
  if (visit.value.status === 'closed') return authStore.canAccess(['Admin']);
  return authStore.canAccess(['Records', 'Admin', 'Billing']);
});

const canDelete = computed(() => {
  if (!visit.value) return false;
  if (visit.value.status === 'closed') return authStore.canAccess(['Admin']);
  return authStore.canAccess(['Records', 'Admin']);
});

const actionCards = computed(() => {
  const cards = [
    { name: 'investigation', title: 'Add investigation', icon: 'science', routeName: 'CompanionAddInvestigation', roles: ['Lab', 'Lab Head', 'Admin'] },
    { name: 'drugs', title: 'Add drugs', icon: 'medication', routeName: 'CompanionAddDrugs', roles: ['Pharmacy', 'Pharmacy Head', 'Admin'] },
    { name: 'scan', title: 'Add scan', icon: 'biotech', routeName: 'CompanionAddScan', roles: ['Scan', 'Scan Head', 'Admin'] },
    { name: 'xray', title: 'Add X-ray', icon: 'contrast', routeName: 'CompanionAddXray', roles: ['Xray', 'Xray Head', 'Admin'] },
  ];
  return cards.map((c) => ({ ...c, active: authStore.canAccess(c.roles) }));
});

function goTo(routeName) {
  router.push({ name: routeName, params: { id: id.value } }).catch(() => {});
}

function formatDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString();
}

function openEditDialog() {
  editForm.value = {
    external_card_number: visit.value?.external_card_number || '',
    external_visit_number: visit.value?.external_visit_number || '',
    client_name: visit.value?.client_name || '',
    status: visit.value?.status || 'open',
  };
  showEditDialog.value = true;
}

async function onSaveEdit() {
  saving.value = true;
  try {
    const payload = {
      client_name: editForm.value.client_name || undefined,
      status: editForm.value.status,
    };
    if (visit.value?.status === 'open') {
      payload.external_card_number = (editForm.value.external_card_number || '').trim() || undefined;
      payload.external_visit_number = (editForm.value.external_visit_number || '').trim() || undefined;
    }
    await companionVisitsAPI.update(id.value, payload);
    const res = await companionVisitsAPI.get(id.value);
    visit.value = res.data;
    showEditDialog.value = false;
    $q.notify({ type: 'positive', message: 'Updated', position: 'top' });
  } catch (e) {
    $q.notify({
      type: 'negative',
      message: e.response?.data?.detail || e.message || 'Update failed',
      position: 'top',
    });
  } finally {
    saving.value = false;
  }
}

function confirmDelete() {
  $q.dialog({
    title: 'Delete service',
    message: 'Remove this visit? This cannot be undone.',
    cancel: true,
    persistent: true,
  }).onOk(async () => {
    try {
      await companionVisitsAPI.delete(id.value);
      $q.notify({ type: 'positive', message: 'Deleted', position: 'top' });
      router.push({ name: 'CompanionVisitList' });
    } catch (e) {
      $q.notify({
        type: 'negative',
        message: e.response?.data?.detail || e.message || 'Delete failed',
        position: 'top',
      });
    }
  });
}

async function loadVisit() {
  if (!id.value) return;
  try {
    const res = await companionVisitsAPI.get(id.value);
    visit.value = res.data;
  } catch (e) {
    visit.value = null;
  } finally {
    loading.value = false;
  }
}

onMounted(loadVisit);
</script>

<style scoped>
.action-card {
  transition: opacity 0.2s, transform 0.2s;
}
.action-card:not(.action-card--inactive) {
  cursor: pointer;
}
.action-card--inactive {
  opacity: 0.6;
  pointer-events: none;
}
.action-card:not(.action-card--inactive):hover {
  transform: translateY(-2px);
}
</style>
