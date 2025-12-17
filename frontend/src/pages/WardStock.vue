<template>
  <q-page class="q-pa-md">
    <div class="row items-center q-mb-md">
      <q-btn
        flat
        icon="arrow_back"
        label="Back to Inventory"
        @click="$router.push('/inventory')"
        class="q-mr-md"
      />
      <div class="text-h4 text-weight-bold glass-text">Department/Unit Stock</div>
    </div>
    
    <q-banner class="glass-card q-pa-md q-mb-md">
      <template v-slot:avatar>
        <q-icon name="info" color="primary" />
      </template>
      View available inventory stock for each department/unit. Stock is updated when requisitions are fulfilled by Store Manager. Items can be filtered by store.
    </q-banner>

    <!-- Filters and Actions -->
    <div class="row q-gutter-md q-mb-md">
      <q-select
        v-model="selectedWard"
        :options="wardOptions"
        label="Select Department/Unit"
        filled
        class="col-12 col-md-3"
        @update:model-value="loadWardStock"
      />
      <q-select
        v-model="selectedStore"
        :options="storeOptions"
        label="Filter by Store"
        filled
        clearable
        emit-value
        map-options
        class="col-12 col-md-3"
        @update:model-value="loadWardStock"
        :disable="isStoreManagerOrDeptHead && userStoreIds.length > 0"
      >
        <template v-slot:prepend>
          <q-icon name="store" />
        </template>
      </q-select>
      <q-input
        v-model="productSearch"
        label="Search Product"
        filled
        clearable
        class="col-12 col-md-3"
        @input="loadWardStock"
      >
        <template v-slot:prepend>
          <q-icon name="search" />
        </template>
      </q-input>
      <q-btn
        flat
        icon="refresh"
        label="Refresh"
        @click="loadWardStock"
        :loading="loading"
        class="col-12 col-md-2"
      />
      <q-btn
        color="primary"
        icon="arrow_back"
        label="Back to Requisitions"
        @click="$router.push({ name: 'PharmacyRequisitions' })"
        class="col-12 col-md-3"
      />
    </div>

    <!-- Stock Summary -->
    <q-card class="q-mb-md glass-card" flat v-if="selectedWard">
      <q-card-section>
        <div class="row q-gutter-md">
          <q-card class="col-12 col-md-3">
            <q-card-section>
              <div class="text-caption text-grey-7">Total Items</div>
              <div class="text-h5 text-weight-bold">{{ stockItems.length }}</div>
            </q-card-section>
          </q-card>
          <q-card class="col-12 col-md-3">
            <q-card-section>
              <div class="text-caption text-grey-7">In Stock</div>
              <div class="text-h5 text-weight-bold text-positive">
                {{ stockItems.filter(item => item.quantity > 0).length }}
              </div>
            </q-card-section>
          </q-card>
          <q-card class="col-12 col-md-3">
            <q-card-section>
              <div class="text-caption text-grey-7">Out of Stock</div>
              <div class="text-h5 text-weight-bold text-negative">
                {{ stockItems.filter(item => item.quantity <= 0).length }}
              </div>
            </q-card-section>
          </q-card>
          <q-card class="col-12 col-md-3">
            <q-card-section>
              <div class="text-caption text-grey-7">Low Stock (< 10)</div>
              <div class="text-h5 text-weight-bold text-warning">
                {{ stockItems.filter(item => item.quantity > 0 && item.quantity < 10).length }}
              </div>
            </q-card-section>
          </q-card>
        </div>
      </q-card-section>
    </q-card>

    <!-- Stock Table -->
    <q-card class="glass-card" flat>
      <q-card-section>
        <div class="text-h6 glass-text q-mb-md">
          Stock Items
          <q-badge color="primary" class="q-ml-sm">{{ filteredStock.length }}</q-badge>
        </div>

        <q-table
          :rows="filteredStock"
          :columns="columns"
          :loading="loading"
          row-key="id"
          flat
          :pagination="{ rowsPerPage: 50 }"
        >
          <template v-slot:body-cell-quantity="props">
            <q-td :props="props">
              <q-badge
                :color="getQuantityColor(props.value)"
                :label="props.value.toFixed(2)"
              />
            </q-td>
          </template>

          <template v-slot:no-data>
            <div class="full-width row flex-center text-grey-6 q-gutter-sm">
              <q-icon name="inventory_2" size="2em" />
              <span v-if="!selectedWard">Please select a department/unit to view stock</span>
              <span v-else>No stock items found</span>
            </div>
          </template>
        </q-table>
      </q-card-section>
    </q-card>
  </q-page>
</template>

<script>
import { ref, computed, onMounted } from 'vue';
import { useAuthStore } from '../stores/auth';
import { Notify } from 'quasar';
import { pharmacyRequisitionsAPI, wardsAPI, storesAPI, storeStaffAssignmentsAPI } from '../services/api';

export default {
  name: 'WardStock',
  setup() {
    const authStore = useAuthStore();
    
    const stockItems = ref([]);
    const loading = ref(false);
    const selectedWard = ref(null);
    const selectedStore = ref(null);
    const productSearch = ref('');

    const wardOptions = ref([]);
    const storeOptions = ref([]);
    const userStoreIds = ref([]);
    
    const isStoreManagerOrDeptHead = computed(() => {
      return authStore.userRole === 'Store Manager' || authStore.userRole === 'Department Head';
    });

    const columns = [
      { name: 'product_code', label: 'Product Code', field: 'product_code', align: 'left', sortable: true },
      { name: 'product_name', label: 'Product Name', field: 'product_name', align: 'left', sortable: true },
      { name: 'store_name', label: 'Store', field: 'store_name', align: 'left', sortable: true },
      { name: 'quantity', label: 'Available Quantity', field: 'quantity', align: 'left', sortable: true },
      { name: 'updated_at', label: 'Last Updated', field: 'updated_at', align: 'left', sortable: true },
    ];

    const filteredStock = computed(() => {
      let filtered = stockItems.value;
      
      if (productSearch.value) {
        const search = productSearch.value.toLowerCase();
        filtered = filtered.filter(item =>
          item.product_name.toLowerCase().includes(search) ||
          item.product_code.toLowerCase().includes(search)
        );
      }
      
      return filtered;
    });

    const loadWardStock = async () => {
      if (!selectedWard.value) {
        stockItems.value = [];
        return;
      }

      loading.value = true;
      try {
        // Determine store_id to filter by
        let storeId = null;
        if (isStoreManagerOrDeptHead.value && userStoreIds.value.length > 0) {
          // Auto-filter by user's assigned store (use the selected store which is auto-set)
          storeId = selectedStore.value || userStoreIds.value[0];
        } else if (selectedStore.value) {
          storeId = selectedStore.value;
        }
        
        const response = await pharmacyRequisitionsAPI.getWardStock(selectedWard.value, null, storeId);
        stockItems.value = response.data || [];
      } catch (error) {
        console.error('Error loading department/unit stock:', error);
        Notify.create({
          type: 'negative',
          message: error.response?.data?.detail || 'Failed to load department/unit stock',
          position: 'top',
        });
        stockItems.value = [];
      } finally {
        loading.value = false;
      }
    };

    const getQuantityColor = (quantity) => {
      if (quantity <= 0) return 'negative';
      if (quantity < 10) return 'warning';
      return 'positive';
    };

    const loadWards = async () => {
      try {
        const response = await wardsAPI.getAll(true); // Get only active departments/units
        wardOptions.value = (response.data || []).map(ward => ward.name);
      } catch (error) {
        console.error('Error loading departments/units:', error);
        Notify.create({
          type: 'negative',
          message: 'Failed to load departments/units',
          position: 'top',
        });
      }
    };

    const loadStores = async () => {
      try {
        const response = await storesAPI.getAll(true); // Get only active stores
        storeOptions.value = (response.data || []).map(store => ({
          label: store.name,
          value: store.id,
        }));
      } catch (error) {
        console.error('Error loading stores:', error);
        Notify.create({
          type: 'negative',
          message: 'Failed to load stores',
          position: 'top',
        });
      }
    };

    const loadUserStoreAssignments = async () => {
      if (!isStoreManagerOrDeptHead.value) {
        return;
      }

      try {
        const response = await storeStaffAssignmentsAPI.getAll({
          user_id: authStore.user?.id,
          active_only: true,
        });
        userStoreIds.value = (response.data || []).map(assignment => assignment.store_id);
        
        // Auto-select first assigned store (always set for Store Managers/Department Heads)
        if (userStoreIds.value.length > 0) {
          selectedStore.value = userStoreIds.value[0];
        }
      } catch (error) {
        console.error('Error loading user store assignments:', error);
      }
    };

    onMounted(async () => {
      await loadWards();
      await loadStores();
      await loadUserStoreAssignments();
      
      if (selectedWard.value) {
        loadWardStock();
      }
    });

    return {
      stockItems,
      loading,
      selectedWard,
      selectedStore,
      productSearch,
      wardOptions,
      storeOptions,
      userStoreIds,
      isStoreManagerOrDeptHead,
      columns,
      filteredStock,
      loadWardStock,
      getQuantityColor,
    };
  },
};
</script>

<style scoped>
.glass-card {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
}
.glass-text {
  color: rgba(255, 255, 255, 0.9);
}
</style>

