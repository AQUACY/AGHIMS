<template>
  <q-page class="q-pa-md">
    <div class="text-h4 q-mb-md text-weight-bold glass-text">
      Transactions
    </div>
    <div class="text-subtitle1 text-secondary q-mb-lg">
      Monetary transactions from OPD and Companion (copayment) applications. Filter by date, client, service type, or user.
    </div>

    <q-card class="q-mb-md glass-card" flat>
      <q-card-section>
        <div class="text-h6 q-mb-md glass-text">Filters</div>
        <div class="row q-col-gutter-md items-end">
          <q-input
            v-model="filters.start_date"
            filled
            dense
            type="date"
            label="From date"
            clearable
            class="col-12 col-sm-2"
          />
          <q-input
            v-model="filters.end_date"
            filled
            dense
            type="date"
            label="To date"
            clearable
            class="col-12 col-sm-2"
          />
          <q-input
            v-model="filters.client"
            filled
            dense
            label="Client (name or card)"
            clearable
            class="col-12 col-sm-2"
            @keyup.enter="loadTransactions"
          />
          <q-input
            v-model="filters.service_type"
            filled
            dense
            label="Service type"
            clearable
            class="col-12 col-sm-2"
            @keyup.enter="loadTransactions"
          />
          <q-select
            v-model="filters.user_id"
            :options="userOptions"
            filled
            dense
            label="User (who took transaction)"
            emit-value
            map-options
            clearable
            options-dense
            class="col-12 col-sm-2"
          />
          <q-btn
            unelevated
            label="Search"
            class="glass-button"
            icon="search"
            :loading="loading"
            @click="loadTransactions"
          />
        </div>
      </q-card-section>
    </q-card>

    <q-card class="glass-card" flat>
      <q-card-section>
        <div class="row items-center justify-between q-mb-md">
          <div class="text-h6 glass-text">
            Results
            <span v-if="totalAmount !== null" class="text-weight-normal text-secondary q-ml-sm">
              — Total: {{ formatPrice(totalAmount) }}
            </span>
          </div>
        </div>
        <q-table
          :rows="transactions"
          :columns="columns"
          :row-key="(row, index) => index"
          flat
          :loading="loading"
          :rows-per-page-options="[10, 25, 50, 100]"
          class="glass-table"
          no-data-label="No transactions found. Adjust filters or date range."
        >
          <template v-slot:body-cell-transaction_date="props">
            <q-td :props="props">{{ formatDate(props.row.transaction_date) }}</q-td>
          </template>
          <template v-slot:body-cell-amount="props">
            <q-td :props="props">{{ formatPrice(props.row.amount) }}</q-td>
          </template>
          <template v-slot:body-cell-source="props">
            <q-td :props="props">
              <q-badge :color="props.row.source === 'opd' ? 'primary' : 'teal'" :label="props.row.source.toUpperCase()" />
            </q-td>
          </template>
        </q-table>
      </q-card-section>
    </q-card>
  </q-page>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { managementAPI } from '../services/api';

const loading = ref(false);
const transactions = ref([]);
const totalAmount = ref(null);
const userOptions = ref([]);

const filters = ref({
  start_date: null,
  end_date: null,
  client: null,
  service_type: null,
  user_id: null,
});

const columns = [
  { name: 'transaction_date', label: 'Date', field: 'transaction_date', align: 'left', sortable: true },
  { name: 'source', label: 'Source', field: 'source', align: 'left' },
  { name: 'client_name', label: 'Client', field: 'client_name', align: 'left' },
  { name: 'client_identifier', label: 'Card / ID', field: 'client_identifier', align: 'left' },
  { name: 'service_type', label: 'Service type', field: 'service_type', align: 'left' },
  { name: 'amount', label: 'Amount', field: 'amount', align: 'right' },
  { name: 'user_name', label: 'User', field: 'user_name', align: 'left' },
  { name: 'receipt_number', label: 'Receipt', field: 'receipt_number', align: 'left' },
  { name: 'payment_method', label: 'Payment', field: 'payment_method', align: 'left' },
];

function formatPrice(val) {
  const n = Number(val);
  if (Number.isNaN(n)) return '0.00';
  return n.toFixed(2);
}

function formatDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString();
}

async function loadUsers() {
  try {
    const res = await managementAPI.getUsers();
    const list = res.data || [];
    userOptions.value = list.map((u) => ({
      label: u.full_name || u.username || `User ${u.id}`,
      value: u.id,
    }));
  } catch (e) {
    userOptions.value = [];
  }
}

async function loadTransactions() {
  loading.value = true;
  transactions.value = [];
  totalAmount.value = null;
  try {
    const params = {};
    if (filters.value.start_date) params.start_date = filters.value.start_date;
    if (filters.value.end_date) params.end_date = filters.value.end_date;
    if (filters.value.client && filters.value.client.trim()) params.client = filters.value.client.trim();
    if (filters.value.service_type && filters.value.service_type.trim()) params.service_type = filters.value.service_type.trim();
    if (filters.value.user_id != null) params.user_id = filters.value.user_id;
    const res = await managementAPI.getTransactions(params);
    transactions.value = (res.data && res.data.transactions) ? res.data.transactions : [];
    totalAmount.value = (res.data && res.data.total_amount != null) ? res.data.total_amount : 0;
  } catch (e) {
    console.error('Failed to load transactions', e);
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  loadUsers();
  loadTransactions();
});
</script>
