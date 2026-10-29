<template>
  <q-page class="hms-page">
    <HmsPageHeader
      title="GHIMS drugs"
      :subtitle="branchName
        ? `Drugs on ${branchName}. MapBranchItems only searches the category selected in its dropdown.`
        : 'Drugs on the GHIMS store for this hospital.'"
    />

    <section class="diag-panel q-mb-md">
      <div class="panel-body">
        <div class="row q-col-gutter-md items-end">
          <div class="col-12 col-md-6">
            <q-input
              v-model="query"
              filled
              label="Search name or drug ID"
              @keyup.enter="load"
            />
          </div>
          <div class="col-auto">
            <HmsButton variant="primary" size="sm" :loading="loading" @click="load">Search</HmsButton>
          </div>
        </div>
      </div>
    </section>

    <section class="diag-panel q-mb-md">
      <div class="panel-head">
        <div>
          <div class="panel-title">Hospital drug list</div>
          <div class="panel-sub">A drug with no store row cannot take a branch price yet</div>
        </div>
      </div>
      <div class="panel-body">
        <q-table
          :rows="drugs"
          :columns="columns"
          row-key="drug_id"
          flat
          :loading="loading"
          :pagination="{ rowsPerPage: 25 }"
        >
          <template #body-cell-on_store="props">
            <q-td :props="props">
              <q-badge :color="props.row.on_store ? 'positive' : 'warning'" :label="props.row.on_store ? 'On a store' : 'Not on a store'" />
            </q-td>
          </template>
          <template #no-data>
            <div class="q-pa-md text-grey-7">No drugs matched.</div>
          </template>
        </q-table>
      </div>
    </section>

    <section v-if="exchange.length" class="diag-panel">
      <div class="panel-head">
        <div>
          <div class="panel-title">MapBranchItems catalog</div>
          <div class="panel-sub">This is the list that screen searches. The category has to match the dropdown.</div>
        </div>
      </div>
      <div class="panel-body">
        <q-table
          :rows="exchange"
          :columns="exchangeColumns"
          row-key="exchange_item_code"
          flat
          :pagination="{ rowsPerPage: 15 }"
        />
      </div>
    </section>
  </q-page>
</template>

<script setup>
import { onMounted, ref } from 'vue';
import { Notify } from 'quasar';
import HmsPageHeader from '../components/ui/HmsPageHeader.vue';
import HmsButton from '../components/ui/HmsButton.vue';
import { stockAccountabilityAPI } from '../services/api';

const query = ref('');
const loading = ref(false);
const drugs = ref([]);
const exchange = ref([]);
const branchName = ref('');

const columns = [
  { name: 'drug_id', label: 'Drug ID', field: 'drug_id', align: 'left' },
  { name: 'drug_name', label: 'Name', field: 'drug_name', align: 'left' },
  { name: 'drug_type', label: 'Type', field: 'drug_type', align: 'left' },
  { name: 'unit', label: 'Unit', field: 'unit', align: 'left' },
  { name: 'bill_group', label: 'Bill group', field: 'bill_group', align: 'left' },
  { name: 'on_store', label: 'Store', field: 'on_store', align: 'left' },
  { name: 'created_at', label: 'Created', field: 'created_at', align: 'left' },
];
const exchangeColumns = [
  { name: 'item_name', label: 'Name', field: 'item_name', align: 'left' },
  { name: 'exchange_item_code', label: 'Code', field: 'exchange_item_code', align: 'left' },
  { name: 'service_type', label: 'Category', field: 'service_type', align: 'left' },
];

const load = async () => {
  loading.value = true;
  try {
    const response = await stockAccountabilityAPI.listGhimsDrugs(query.value.trim());
    drugs.value = response.data?.drugs || [];
    exchange.value = response.data?.exchange || [];
    branchName.value = response.data?.branch_name || '';
  } catch (error) {
    Notify.create({
      type: 'negative',
      message: error.response?.data?.detail || 'Could not read the GHIMS drug list',
      position: 'top',
    });
  } finally {
    loading.value = false;
  }
};

onMounted(load);
</script>
