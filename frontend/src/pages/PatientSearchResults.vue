<template>
  <q-page class="hms-page">
    <HmsPageHeader title="Patient search results" :subtitle="subtitle">
      <template #actions>
        <HmsButton variant="secondary" size="sm" @click="$router.back()">
          <ArrowLeft :size="14" />
          Back
        </HmsButton>
        <HmsButton
          v-if="canRegister"
          variant="primary"
          size="sm"
          @click="$router.push({ name: 'PatientRegistration' })"
        >
          <UserPlus :size="14" />
          Add patient
        </HmsButton>
      </template>
    </HmsPageHeader>

    <div class="results-meta">
      <Users :size="15" class="meta-icon" />
      <span>{{ patients.length }} total patient{{ patients.length === 1 ? '' : 's' }}</span>
    </div>

    <HmsDataTable
      :rows="patients"
      :columns="patientColumns"
      row-key="id"
      searchable
      dense
      search-placeholder="Search for anything here…"
      empty-title="No patients found"
      :empty-description="`No matches for “${searchTerm}”`"
      @row-click="viewPatient"
    >
      <template #cell-card_number="{ value }">
        <span class="mono">{{ value }}</span>
      </template>

      <template #cell-name="{ row }">
        <div class="patient-cell">
          <div class="avatar">{{ initials(row) }}</div>
          <div class="patient-meta">
            <div class="name">{{ displayName(row) }}</div>
            <div v-if="row.contact" class="sub">{{ row.contact }}</div>
          </div>
        </div>
      </template>

      <template #cell-gender="{ value }">
        <HmsBadge :tone="value === 'M' || value === 'Male' ? 'info' : 'healthcare'">
          {{ genderLabel(value) }}
        </HmsBadge>
      </template>

      <template #cell-insured="{ value }">
        <HmsBadge :tone="value ? 'success' : 'warning'">
          {{ value ? 'Insured' : 'Cash' }}
        </HmsBadge>
      </template>

      <template #cell-actions="{ row }">
        <HmsButton variant="soft" size="sm" @click.stop="viewPatient(row)">Open</HmsButton>
      </template>

      <template #footer="{ count, total }">
        Showing {{ count }} of {{ total }} patient{{ total === 1 ? '' : 's' }}
      </template>
    </HmsDataTable>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useQuasar } from 'quasar';
import { ArrowLeft, UserPlus, Users } from 'lucide-vue-next';
import { useAuthStore } from '../stores/auth';
import HmsPageHeader from '../components/ui/HmsPageHeader.vue';
import HmsButton from '../components/ui/HmsButton.vue';
import HmsBadge from '../components/ui/HmsBadge.vue';
import HmsDataTable from '../components/ui/HmsDataTable.vue';

const route = useRoute();
const router = useRouter();
const $q = useQuasar();
const authStore = useAuthStore();

const searchTerm = ref('');
const searchType = ref('name');
const patients = ref([]);

const canRegister = computed(() => authStore.canAccess(['Records', 'Admin', 'PA', 'Doctor']));

const patientColumns = [
  { name: 'card_number', label: 'Card', field: 'card_number', align: 'left', width: '150px' },
  { name: 'name', label: 'Patient', field: 'name', align: 'left' },
  { name: 'gender', label: 'Sex', field: 'gender', align: 'center', width: '80px' },
  {
    name: 'date_of_birth',
    label: 'DOB',
    field: 'date_of_birth',
    align: 'left',
    width: '120px',
    format: (val) =>
      val
        ? new Date(val).toLocaleDateString(undefined, {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
          })
        : '—',
  },
  { name: 'insured', label: 'Cover', field: 'insured', align: 'center', width: '100px' },
  { name: 'actions', label: '', align: 'right', width: '96px' },
];

const subtitle = computed(() => {
  const labels = {
    name: 'name',
    card: 'card number',
    ccc: 'Ghana card / insurance number',
    contact: 'contact number',
  };
  const kind = labels[searchType.value] || 'query';
  if (!patients.value.length) return `No patients matching ${kind} “${searchTerm.value}”`;
  return `Matching ${kind} “${searchTerm.value}”`;
});

const titleCase = (value) => {
  if (!value) return '';
  return String(value)
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase());
};

const displayName = (row) =>
  [titleCase(row.name), titleCase(row.surname)].filter(Boolean).join(' ') || 'Unknown';

const initials = (row) => {
  const a = (row.name || '?')[0] || '?';
  const b = (row.surname || '')[0] || '';
  return `${a}${b}`.toUpperCase();
};

const genderLabel = (value) => {
  if (value === 'M' || value === 'Male') return 'Male';
  if (value === 'F' || value === 'Female') return 'Female';
  return value || '—';
};

const viewPatient = (patient) => {
  router.push({
    name: 'PatientProfile',
    params: { cardNumber: patient.card_number },
  });
};

const loadPatientsFromQuery = () => {
  searchTerm.value =
    route.query.searchTerm ||
    route.query.name ||
    route.query.cardNumber ||
    route.query.contactNumber ||
    '';

  if (route.query.searchType) {
    searchType.value = route.query.searchType;
  } else if (route.query.name) {
    searchType.value = 'name';
  } else if (route.query.cardNumber || route.query.card_number) {
    searchType.value = 'card';
  } else if (route.query.contactNumber || route.query.contact_number) {
    searchType.value = 'contact';
  } else if (route.query.cccNumber || route.query.ccc_number) {
    searchType.value = 'ccc';
  } else {
    searchType.value = 'name';
  }

  if (route.query.patients) {
    try {
      const parsedPatients = JSON.parse(route.query.patients);
      patients.value = Array.isArray(parsedPatients) ? parsedPatients : [];
      if (patients.value.length === 0) {
        $q.notify({
          type: 'info',
          message: `No patients found matching "${searchTerm.value}"`,
          position: 'top',
        });
      }
    } catch (e) {
      console.error('Failed to parse patients from query:', e);
      patients.value = [];
      $q.notify({
        type: 'negative',
        message: 'Failed to load search results',
        position: 'top',
      });
    }
  } else {
    patients.value = [];
  }
};

onMounted(() => {
  loadPatientsFromQuery();
});

watch(
  () => route.query,
  () => {
    loadPatientsFromQuery();
  },
  { deep: true }
);
</script>

<style scoped>
.results-meta {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  margin: -0.35rem 0 0.85rem;
  color: var(--hms-text-muted);
  font-size: var(--hms-text-sm);
  font-weight: 600;
}

.meta-icon {
  flex-shrink: 0;
}

.patient-cell {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  min-width: 0;
}

.avatar {
  width: 2.25rem;
  height: 2.25rem;
  border-radius: 9999px;
  background: linear-gradient(145deg, var(--hms-accent-muted), rgba(6, 182, 212, 0.18));
  color: var(--hms-accent);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 0.7rem;
  font-weight: 750;
  flex-shrink: 0;
}

.patient-meta {
  min-width: 0;
}

.name {
  font-weight: 700;
  color: var(--hms-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sub {
  margin-top: 0.1rem;
  font-size: var(--hms-text-xs);
  color: var(--hms-text-muted);
}

.mono {
  font-family: var(--hms-font-mono);
  font-size: 0.75rem;
  letter-spacing: 0.01em;
  color: var(--hms-text-secondary);
  font-weight: 600;
}

@media (max-width: 640px) {
  .results-meta {
    margin-bottom: 0.65rem;
  }
}
</style>
