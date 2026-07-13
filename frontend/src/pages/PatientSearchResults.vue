<template>
  <q-page class="q-pa-md">
    <div class="text-h4 q-mb-md text-weight-bold glass-text">Patient Search Results</div>

    <q-card class="q-mb-md glass-card" flat>
      <q-card-section>
        <div class="text-h6 glass-text q-mb-md">
          <span v-if="patients.length > 0">Found {{ patients.length }} patient(s) matching </span>
          <span v-else>No patients found matching </span>
          <span v-if="searchType === 'name'">name "{{ searchTerm }}"</span>
          <span v-else-if="searchType === 'card'">card number "{{ searchTerm }}"</span>
          <span v-else-if="searchType === 'ccc'">Ghana card/insurance number "{{ searchTerm }}"</span>
          <span v-else-if="searchType === 'contact'">contact number "{{ searchTerm }}"</span>
          <span v-else>"{{ searchTerm }}"</span>
        </div>

        <q-table
          :rows="patients"
          :columns="patientColumns"
          row-key="id"
          flat
          class="glass-table"
        >
          <template v-slot:body-cell-card_number="props">
            <q-td :props="props">
              <div class="text-weight-medium glass-text">{{ props.value }}</div>
            </q-td>
          </template>
          
          <template v-slot:body-cell-name="props">
            <q-td :props="props">
              <div class="glass-text">
                {{ props.row.name }} {{ props.row.surname || '' }}
              </div>
            </q-td>
          </template>
          
          <template v-slot:body-cell-gender="props">
            <q-td :props="props">
              <q-badge :color="props.value === 'M' ? 'blue' : 'pink'">
                {{ props.value }}
              </q-badge>
            </q-td>
          </template>
          
          <template v-slot:body-cell-insured="props">
            <q-td :props="props">
              <q-badge :color="props.value ? 'green' : 'orange'">
                {{ props.value ? 'Insured' : 'Cash' }}
              </q-badge>
            </q-td>
          </template>
          
          <template v-slot:body-cell-actions="props">
            <q-td :props="props">
              <q-btn
                size="sm"
                color="primary"
                icon="visibility"
                label="View"
                @click="viewPatient(props.row)"
                class="glass-button"
              />
            </q-td>
          </template>
        </q-table>
      </q-card-section>
    </q-card>
  </q-page>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useQuasar } from 'quasar';

const route = useRoute();
const router = useRouter();
const $q = useQuasar();

const searchTerm = ref('');
const searchType = ref('name'); // 'name' or 'card'
const patients = ref([]);

const patientColumns = [
  { name: 'card_number', label: 'Card Number', field: 'card_number', align: 'left' },
  { name: 'name', label: 'Name', field: 'name', align: 'left' },
  { name: 'gender', label: 'Gender', field: 'gender', align: 'center' },
  { name: 'date_of_birth', label: 'Date of Birth', field: 'date_of_birth', align: 'left', format: (val) => val ? new Date(val).toLocaleDateString() : 'N/A' },
  { name: 'insured', label: 'Insurance', field: 'insured', align: 'center' },
  { name: 'actions', label: 'Actions', align: 'center' },
];

const viewPatient = (patient) => {
  router.push({
    name: 'PatientProfile',
    params: { cardNumber: patient.card_number }
  });
};

const loadPatientsFromQuery = () => {
  console.log('Loading patients from query, route.query:', route.query);
  
  // Get search parameters from query
  searchTerm.value = route.query.searchTerm || route.query.name || route.query.cardNumber || route.query.contactNumber || '';
  
  // Determine search type from query
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
  
  // Try to get patients from query params
  if (route.query.patients) {
    try {
      const parsedPatients = JSON.parse(route.query.patients);
      console.log('Parsed patients:', parsedPatients);
      patients.value = Array.isArray(parsedPatients) ? parsedPatients : [];
      
      // Show notification if no patients found
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
    console.warn('No patients in query params');
    patients.value = [];
    $q.notify({
      type: 'warning',
      message: 'No search results available',
      position: 'top',
    });
  }
  
  console.log('Final patients:', patients.value);
};

onMounted(() => {
  loadPatientsFromQuery();
});

// Watch for route query changes (when navigating from search to search results)
watch(() => route.query, () => {
  console.log('Route query changed:', route.query);
  loadPatientsFromQuery();
}, { deep: true });
</script>

<style scoped>
/* Styles are now defined globally in App.vue */
</style>

