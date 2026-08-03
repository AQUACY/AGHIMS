<template>
  <q-page class="hms-page">
    <HmsPageHeader
      title="Department stock"
      subtitle="View available inventory stock for each department or unit."
    >
      <template #actions>
        <HmsButton variant="ghost" size="sm" @click="$router.push('/inventory-mode')">Back</HmsButton>
        <HmsButton
          variant="secondary"
          size="sm"
          @click="$router.push({ name: 'PharmacyRequisitions' })"
        >
          Requisitions
        </HmsButton>
        <HmsButton variant="secondary" size="sm" :loading="loading" @click="loadWardStock">
          Refresh
        </HmsButton>
      </template>
    </HmsPageHeader>

    <div class="soft-banner q-pa-md q-mb-md">
      <div class="row items-start no-wrap q-gutter-sm">
        <q-icon name="info" color="primary" size="20px" class="q-mt-xs" />
        <div class="panel-sub" style="margin-top: 0; max-width: none">
          <span v-if="isIcUnitOnly">You can only view stock for department(s) where you are in-charge or deputy.</span>
          <span v-else>View available inventory stock for each department/unit. Store managers and store department heads may review all units for their assigned stores.</span>
        </div>
      </div>
    </div>

    <section class="diag-panel">
      <div class="panel-head">
        <div>
          <div class="panel-title">Filters</div>
          <div class="panel-sub">Department, store, and product search</div>
        </div>
      </div>
      <div class="panel-body">
        <div class="row q-col-gutter-md items-end">
          <div class="col-12 col-md-3">
            <q-select
              v-model="selectedWard"
              :options="wardOptions"
              label="Select Department/Unit"
              filled
              dense
              :disable="isIcUnitOnly && wardOptions.length <= 1"
              @update:model-value="loadWardStock"
            />
          </div>
          <div class="col-12 col-md-3">
            <q-select
              v-model="selectedStore"
              :options="storeOptions"
              label="Filter by Store"
              filled
              dense
              clearable
              emit-value
              map-options
              @update:model-value="loadWardStock"
              :disable="hasStoreAssignment && userStoreIds.length > 0"
            >
              <template v-slot:prepend>
                <q-icon name="store" />
              </template>
            </q-select>
          </div>
          <div class="col-12 col-md-3">
            <q-input
              v-model="productSearch"
              label="Search Product"
              filled
              dense
              clearable
              @input="loadWardStock"
            >
              <template v-slot:prepend>
                <q-icon name="search" />
              </template>
            </q-input>
          </div>
        </div>
      </div>
    </section>

    <div v-if="selectedWard" class="claim-kpi-grid kpi-4">
      <div class="claim-kpi">
        <div class="stat-top">
          <div class="claim-kpi__label">Total items</div>
        </div>
        <div class="claim-kpi__value">{{ stockItems.length }}</div>
      </div>
      <div class="claim-kpi">
        <div class="stat-top">
          <div class="claim-kpi__label">In stock</div>
        </div>
        <div class="claim-kpi__value text-positive">
          {{ stockItems.filter(item => item.quantity > 0).length }}
        </div>
      </div>
      <div class="claim-kpi">
        <div class="stat-top">
          <div class="claim-kpi__label">Out of stock</div>
        </div>
        <div class="claim-kpi__value text-negative">
          {{ stockItems.filter(item => item.quantity <= 0).length }}
        </div>
      </div>
      <div class="claim-kpi">
        <div class="stat-top">
          <div class="claim-kpi__label">Low stock (&lt; 10)</div>
        </div>
        <div class="claim-kpi__value text-warning">
          {{ stockItems.filter(item => item.quantity > 0 && item.quantity < 10).length }}
        </div>
      </div>
    </div>

    <section class="diag-panel">
      <div class="panel-head">
        <div>
          <div class="panel-title">Stock items</div>
          <div class="panel-sub">{{ filteredStock.length }} matching item(s)</div>
        </div>
      </div>
      <div class="panel-body table-wrap">
        <q-table
          class="diag-table"
          :rows="filteredStock"
          :columns="columns"
          :loading="loading"
          row-key="id"
          flat
          dense
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
            <div class="full-width row flex-center text-grey-6 q-gutter-sm q-pa-md">
              <q-icon name="inventory_2" size="2em" />
              <span v-if="!selectedWard">Please select a department/unit to view stock</span>
              <span v-else>No stock items found</span>
            </div>
          </template>
        </q-table>
      </div>
    </section>
  </q-page>
</template>

<script>
import { ref, computed, onMounted } from 'vue';
import { useAuthStore } from '../stores/auth';
import { Notify } from 'quasar';
import { pharmacyRequisitionsAPI, wardsAPI, storesAPI, storeStaffAssignmentsAPI } from '../services/api';
import { storeSelectLabel } from '../utils/storeKind';
import HmsPageHeader from '../components/ui/HmsPageHeader.vue';
import HmsButton from '../components/ui/HmsButton.vue';

export default {
  name: 'WardStock',
  components: {
    HmsPageHeader,
    HmsButton,
  },
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
    
    const isIcUnitOnly = computed(() => {
      const u = authStore.user;
      if (!u) return false;
      return (
        !u.inventory_dashboard_can_filter_departments &&
        (u.ic_managed_department_names?.length || 0) > 0 &&
        !(u.assigned_store_ids?.length || 0)
      );
    });

    const hasStoreAssignment = computed(() => {
      return (authStore.user?.assigned_store_ids?.length || 0) > 0;
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
        if (hasStoreAssignment.value && userStoreIds.value.length > 0) {
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
        storeOptions.value = (response.data || []).map((store) => ({
          label: storeSelectLabel(store),
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
      try {
        const response = await storeStaffAssignmentsAPI.getAll({
          user_id: authStore.user?.id,
          active_only: true,
        });
        const ids = (response.data || []).map((assignment) => assignment.store_id);
        if (ids.length > 0) {
          userStoreIds.value = ids;
          if (selectedStore.value == null) {
            selectedStore.value = ids[0];
          }
        }
      } catch (error) {
        console.error('Error loading user store assignments:', error);
      }
    };

    onMounted(async () => {
      if (
        authStore.isAuthenticated &&
        authStore.user?.inventory_dashboard_can_filter_departments === undefined
      ) {
        try {
          await authStore.fetchUser();
        } catch (e) {
          void 0;
        }
      }

      if (isIcUnitOnly.value && authStore.user?.ic_managed_department_names?.length) {
        wardOptions.value = [...authStore.user.ic_managed_department_names];
        selectedWard.value = wardOptions.value[0] || null;
      } else {
        await loadWards();
      }
      await loadStores();

      if (authStore.user?.assigned_store_ids?.length) {
        userStoreIds.value = [...authStore.user.assigned_store_ids];
        selectedStore.value = userStoreIds.value[0];
      }
      if (!userStoreIds.value.length) {
        await loadUserStoreAssignments();
      }

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
      isIcUnitOnly,
      hasStoreAssignment,
      columns,
      filteredStock,
      loadWardStock,
      getQuantityColor,
    };
  },
};
</script>

<style scoped>
.stat-top {
  display: flex;
  align-items: center;
  gap: 0.65rem;
}
.kpi-4 {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}
@media (max-width: 960px) {
  .kpi-4 {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 520px) {
  .kpi-4 {
    grid-template-columns: 1fr;
  }
}
</style>
