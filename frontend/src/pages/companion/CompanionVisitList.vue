<template>
  <q-page class="q-pa-md">
    <div class="row items-center justify-between q-mb-md">
      <div>
        <div class="text-h5 text-weight-bold glass-text">Service list</div>
        <div class="text-body2 glass-text-muted">Visits created from the government system (card + visit number)</div>
      </div>
      <q-btn
        unelevated
        label="Create service"
        class="glass-button"
        icon="add"
        :to="{ name: 'CompanionCreateService' }"
      />
    </div>

    <q-card class="glass-card q-mb-md" flat>
      <q-card-section>
        <div class="row q-col-gutter-md items-end">
          <q-input
            v-model="filters.card_number"
            filled
            dense
            label="Card number"
            clearable
            class="col-12 col-sm-4"
            @keyup.enter="loadVisits"
          />
          <q-input
            v-model="filters.visit_number"
            filled
            dense
            label="Visit number"
            clearable
            class="col-12 col-sm-4"
            @keyup.enter="loadVisits"
          />
          <q-select
            v-model="filters.status"
            :options="statusOptions"
            filled
            dense
            label="Status"
            emit-value
            map-options
            clearable
            class="col-12 col-sm-2"
          />
          <q-btn unelevated label="Search" class="glass-button" @click="loadVisits" />
        </div>
      </q-card-section>
    </q-card>

    <q-card class="glass-card" flat>
      <q-card-section>
        <q-table
          :rows="visits"
          :columns="columns"
          row-key="id"
          flat
          :loading="loading"
          :rows-per-page-options="[10, 25, 50]"
          class="glass-table"
          no-data-label="No services found. Create one from the government system card and visit number."
        >
          <template v-slot:body-cell-created_at="props">
            <q-td :props="props">{{ formatDate(props.row.created_at) }}</q-td>
          </template>
          <template v-slot:body-cell-actions="props">
            <q-td :props="props">
              <q-btn
                flat
                dense
                size="sm"
                icon="visibility"
                @click="viewVisit(props.row)"
              >
                <q-tooltip>View</q-tooltip>
              </q-btn>
              <q-btn
                flat
                dense
                size="sm"
                icon="edit"
                :disable="!canEdit(props.row)"
                @click="canEdit(props.row) && editVisit(props.row)"
              >
                <q-tooltip>{{ editDeleteTooltip(props.row, 'edit') }}</q-tooltip>
              </q-btn>
              <q-btn
                flat
                dense
                size="sm"
                icon="delete"
                color="negative"
                :disable="!canDelete(props.row)"
                @click="canDelete(props.row) && confirmDelete(props.row)"
              >
                <q-tooltip>{{ editDeleteTooltip(props.row, 'delete') }}</q-tooltip>
              </q-btn>
            </q-td>
          </template>
        </q-table>
      </q-card-section>
    </q-card>
  </q-page>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useQuasar } from 'quasar';
import { useAuthStore } from '../../stores/auth';
import { companionVisitsAPI } from '../../services/api';

const router = useRouter();
const $q = useQuasar();
const authStore = useAuthStore();
const loading = ref(false);
const visits = ref([]);
const filters = reactive({
  card_number: '',
  visit_number: '',
  status: null,
});
const statusOptions = [
  { label: 'Open', value: 'open' },
  { label: 'Closed', value: 'closed' },
];

const columns = [
  { name: 'id', label: 'ID', field: 'id', align: 'left', sortable: true },
  { name: 'external_card_number', label: 'Card number', field: 'external_card_number', align: 'left' },
  { name: 'external_visit_number', label: 'Visit number', field: 'external_visit_number', align: 'left' },
  { name: 'client_name', label: 'Client name', field: 'client_name', align: 'left' },
  { name: 'status', label: 'Status', field: 'status', align: 'left' },
  { name: 'created_at', label: 'Created', field: 'created_at', align: 'left' },
  { name: 'actions', label: '', align: 'right' },
];

/** Edit: when closed only Admin; when open Records, Billing, or Admin. */
function canEdit(row) {
  if (row.status === 'closed') return authStore.canAccess(['Admin']);
  return authStore.canAccess(['Records', 'Admin', 'Billing']);
}

/** Delete: when closed only Admin; when open Records or Admin. */
function canDelete(row) {
  if (row.status === 'closed') return authStore.canAccess(['Admin']);
  return authStore.canAccess(['Records', 'Admin']);
}

function editDeleteTooltip(row, action) {
  const label = action === 'edit' ? 'Edit' : 'Delete';
  if (row.status === 'closed' && !authStore.canAccess(['Admin'])) {
    return `Only Admin can ${action} a closed visit`;
  }
  return label;
}

function formatDate(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleString();
}

async function loadVisits() {
  loading.value = true;
  try {
    const params = {};
    if (filters.card_number) params.card_number = filters.card_number;
    if (filters.visit_number) params.visit_number = filters.visit_number;
    if (filters.status) params.status_filter = filters.status;
    const res = await companionVisitsAPI.list(params);
    visits.value = res.data || [];
  } catch (e) {
    visits.value = [];
  } finally {
    loading.value = false;
  }
}

function viewVisit(row) {
  router.push({ name: 'CompanionVisitDetail', params: { id: row.id } }).catch(() => {});
}

function editVisit(row) {
  router.push({ name: 'CompanionVisitDetail', params: { id: row.id } }).catch(() => {});
}

function confirmDelete(row) {
  $q.dialog({
    title: 'Delete service',
    message: 'Remove this visit? This cannot be undone.',
    cancel: true,
    persistent: true,
  }).onOk(async () => {
    try {
      await companionVisitsAPI.delete(row.id);
      $q.notify({ type: 'positive', message: 'Deleted', position: 'top' });
      loadVisits();
    } catch (e) {
      $q.notify({
        type: 'negative',
        message: e.response?.data?.detail || e.message || 'Delete failed',
        position: 'top',
      });
    }
  });
}

onMounted(loadVisits);
</script>
