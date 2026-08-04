<template>
  <q-page class="hms-page">
    <HmsPageHeader
      title="Create requisition"
      subtitle="Request store items for your department or unit."
    >
      <template #actions>
        <HmsButton variant="ghost" size="sm" @click="$router.back()">Back</HmsButton>
      </template>
    </HmsPageHeader>

    <q-banner dense rounded class="soft-banner q-mb-md">
      <template v-slot:avatar>
        <q-icon name="info" color="primary" />
      </template>
      Request items from stores. Your requisition will be reviewed by Pharmacy Head and fulfilled by Store Manager before items are added to your department/unit stock.
    </q-banner>

    <section class="diag-panel">
      <div class="panel-head">
        <div>
          <div class="panel-title">Requisition details</div>
          <div class="panel-sub">Choose department, store, and the items you need</div>
        </div>
      </div>
      <div class="panel-body">
        <q-form @submit="createRequisition" ref="requisitionForm">
          <!-- Department/Unit Selection -->
          <q-select
            v-model="requisition.department_id"
            :options="departmentOptions"
            label="Department/Unit *"
            filled
            required
            class="q-mb-md"
            emit-value
            map-options
            :rules="[val => !!val || 'Please select a department/unit']"
          >
            <template v-slot:prepend>
              <q-icon name="local_hospital" />
            </template>
          </q-select>

          <!-- Store Selection -->
          <q-select
            v-model="requisition.store_id"
            :options="storeOptions"
            label="Store *"
            filled
            required
            class="q-mb-md"
            emit-value
            map-options
            :rules="[val => !!val || 'Please select a store']"
          >
            <template v-slot:prepend>
              <q-icon name="store" />
            </template>
          </q-select>

          <!-- Notes -->
          <q-input
            v-model="requisition.notes"
            label="Notes (Optional)"
            filled
            type="textarea"
            rows="3"
            class="q-mb-md"
          >
            <template v-slot:prepend>
              <q-icon name="notes" />
            </template>
          </q-input>

          <!-- Items Section -->
          <div class="panel-title q-mb-md">Items</div>
          
          <q-card
            v-for="(item, index) in requisition.items"
            :key="index"
            class="q-mb-md"
            flat
            bordered
          >
            <q-card-section>
              <div class="row q-gutter-md items-center">
                <q-input
                  v-model="item.product_code"
                  label="Product Code"
                  filled
                  readonly
                  class="col-12 col-md-4"
                />
                <q-input
                  v-model="item.product_name"
                  label="Product Name"
                  filled
                  readonly
                  class="col-12 col-md-4"
                />
                <q-input
                  v-model.number="item.requested_quantity"
                  label="Quantity *"
                  filled
                  type="number"
                  min="0.01"
                  step="0.01"
                  class="col-12 col-md-3"
                  :rules="[val => val > 0 || 'Quantity must be greater than 0']"
                />
                <q-btn
                  flat
                  round
                  icon="delete"
                  color="negative"
                  @click="removeItem(index)"
                  class="col-12 col-md-1"
                >
                  <q-tooltip>Remove Item</q-tooltip>
                </q-btn>
              </div>
            </q-card-section>
          </q-card>

          <HmsButton variant="secondary" size="sm" class="q-mb-md" @click="openAddItemDialog">
            Add Item
          </HmsButton>

          <!-- Action Buttons -->
          <div class="row q-gutter-md q-mt-lg items-center">
            <HmsButton
              type="submit"
              variant="primary"
              size="sm"
              :loading="creating"
              :disabled="requisition.items.length === 0"
            >
              Create Requisition
            </HmsButton>
            <HmsButton variant="ghost" size="sm" @click="$router.back()">Cancel</HmsButton>
          </div>
        </q-form>
      </div>
    </section>

    <!-- Add Item Dialog -->
    <q-dialog v-model="showAddItemDialog">
      <q-card style="min-width: 600px">
        <q-card-section class="dialog-head">
          <div class="dialog-title">Add item</div>
        </q-card-section>

        <q-card-section>
          <q-select
            v-model="selectedProduct"
            :options="filteredProductOptions"
            filled
            use-input
            input-debounce="300"
            label="Search Product *"
            hint="Type to search for products - Select to add"
            @filter="filterProducts"
            @update:model-value="onProductSelected"
            option-label="label"
            option-value="value"
            emit-value
            map-options
            clearable
            :loading="loadingProducts"
          >
            <template v-slot:option="scope">
              <q-item v-bind="scope.itemProps">
                <q-item-section>
                  <q-item-label>{{ scope.opt.label }}</q-item-label>
                  <q-item-label caption>
                    Code: {{ scope.opt.value.code }}
                    <span v-if="scope.opt.value.formulation"> | {{ scope.opt.value.formulation }}</span>
                  </q-item-label>
                </q-item-section>
              </q-item>
            </template>
            <template v-slot:no-option>
              <q-item>
                <q-item-section class="text-grey">
                  No products found. Type to search.
                </q-item-section>
              </q-item>
            </template>
          </q-select>
        </q-card-section>

        <q-card-actions align="right" class="dialog-actions">
          <HmsButton variant="ghost" size="sm" v-close-popup>Cancel</HmsButton>
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '../stores/auth';
import { useQuasar, Notify } from 'quasar';
import { pharmacyRequisitionsAPI, priceListAPI, wardsAPI, storesAPI, departmentStaffAssignmentsAPI } from '../services/api';
import { storeSelectLabel } from '../utils/storeKind';
import HmsPageHeader from '../components/ui/HmsPageHeader.vue';
import HmsButton from '../components/ui/HmsButton.vue';

export default {
  name: 'CreateRequisition',
  components: { HmsPageHeader, HmsButton },
  setup() {
    const router = useRouter();
    const authStore = useAuthStore();
    const $q = useQuasar();
    
    const requisitionForm = ref(null);
    const creating = ref(false);
    const showAddItemDialog = ref(false);
    const loadingProducts = ref(false);
    const selectedProduct = ref(null);
    const allProducts = ref([]);
    const filteredProductOptions = ref([]);

    const departmentOptions = ref([]);
    const storeOptions = ref([]);

    const requisition = ref({
      department_id: null,
      store_id: null,
      notes: '',
      items: [],
    });

    const loadDepartments = async () => {
      try {
        // Load all active departments
        const response = await wardsAPI.getAll(true);
        const allDepartments = response.data || [];
        
        // If user is Admin, show all departments
        // Otherwise, only show departments where user is IC or Deputy
        if (authStore.userRole === 'Admin') {
          departmentOptions.value = allDepartments.map(dept => ({
            label: dept.name,
            value: dept.id,
          }));
        } else {
          // Get user's department assignments
          const assignmentsResponse = await departmentStaffAssignmentsAPI.getAll({
            user_id: authStore.user?.id,
            active_only: true,
          });
          const assignments = assignmentsResponse.data || [];
          const assignedDepartmentIds = assignments.map(a => a.department_id);
          
          // Filter departments to only those where user is IC or Deputy
          departmentOptions.value = allDepartments
            .filter(dept => assignedDepartmentIds.includes(dept.id))
            .map(dept => ({
              label: dept.name,
              value: dept.id,
            }));
        }
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

    const loadProducts = async () => {
      try {
        loadingProducts.value = true;
        console.log('Loading products from price list...');
        // Load all products without filtering by service_type (like inventory debit page)
        const res = await priceListAPI.searchPriceItems(null, null, 'product');
        console.log('Products API response:', res);
        
        // Handle both direct array response and nested data property
        let productsData = res.data;
        if (!Array.isArray(productsData) && res.data?.data) {
          productsData = res.data.data;
        }
        
        if (productsData && Array.isArray(productsData)) {
          console.log(`Found ${productsData.length} products`);
          
          // Filter only active products and map them
          const mappedProducts = productsData
            .filter(item => item.is_active !== false && item.file_type === 'product')
            .map(item => {
              const productCode = item.medication_code || item.product_id || item.item_code || item.g_drg_code || '';
              const productName = item.product_name || item.service_name || 'Unknown Product';
              const formulation = item.formulation || '';
              
              return {
                label: `${productName}${formulation ? ` (${formulation})` : ''} (${productCode})`,
                value: {
                  code: productCode,
                  name: productName,
                  formulation: formulation,
                  fullItem: item // Store full item for reference
                }
              };
            });
          
          console.log(`Mapped ${mappedProducts.length} active products`);
          allProducts.value = mappedProducts;
          filteredProductOptions.value = allProducts.value.slice(0, 50); // Show first 50 by default
        } else {
          console.warn('Products data is not an array:', productsData);
          allProducts.value = [];
          filteredProductOptions.value = [];
        }
      } catch (error) {
        console.error('Error loading products:', error);
        Notify.create({
          type: 'negative',
          message: error.response?.data?.detail || 'Failed to load products from price list',
          position: 'top',
        });
        allProducts.value = [];
        filteredProductOptions.value = [];
      } finally {
        loadingProducts.value = false;
      }
    };

    const filterProducts = (val, update) => {
      if (val === '') {
        update(() => {
          filteredProductOptions.value = allProducts.value.slice(0, 50);
        });
        return;
      }

      update(() => {
        const needle = val.toLowerCase();
        filteredProductOptions.value = allProducts.value.filter(
          v => v.label.toLowerCase().indexOf(needle) > -1
        );
      });
    };

    const openAddItemDialog = () => {
      selectedProduct.value = null;
      if (allProducts.value.length === 0) {
        loadProducts();
      }
      showAddItemDialog.value = true;
    };

    const onProductSelected = (productValue) => {
      if (!productValue) return;
      
      const productCode = productValue.code;
      const productName = productValue.name;
      
      if (!productCode || !productName) {
        Notify.create({
          type: 'negative',
          message: 'Invalid product data',
          position: 'top',
        });
        return;
      }
      
      // Check if product is already in the list
      const existingItem = requisition.value.items.find(
        item => item.product_code === productCode
      );
      
      if (existingItem) {
        Notify.create({
          type: 'warning',
          message: 'This product is already in the requisition',
          position: 'top',
        });
        selectedProduct.value = null;
        return;
      }

      requisition.value.items.push({
        product_code: productCode,
        product_name: productName,
        requested_quantity: 1,
        notes: '',
      });
      
      showAddItemDialog.value = false;
      selectedProduct.value = null;
      
      Notify.create({
        type: 'positive',
        message: 'Item added to requisition',
        position: 'top',
      });
    };

    const removeItem = (index) => {
      requisition.value.items.splice(index, 1);
    };

    const createRequisition = async () => {
      if (!requisition.value.department_id) {
        Notify.create({
          type: 'negative',
          message: 'Please select a department/unit',
          position: 'top',
        });
        return;
      }

      if (!requisition.value.store_id) {
        Notify.create({
          type: 'negative',
          message: 'Please select a store',
          position: 'top',
        });
        return;
      }

      if (requisition.value.items.length === 0) {
        Notify.create({
          type: 'negative',
          message: 'Please add at least one item to the requisition',
          position: 'top',
        });
        return;
      }

      // Validate all items have quantity > 0
      const invalidItems = requisition.value.items.filter(item => !item.requested_quantity || item.requested_quantity <= 0);
      if (invalidItems.length > 0) {
        Notify.create({
          type: 'negative',
          message: 'All items must have a quantity greater than 0',
          position: 'top',
        });
        return;
      }

      creating.value = true;
      try {
        await pharmacyRequisitionsAPI.create(requisition.value);
        Notify.create({
          type: 'positive',
          message: 'Requisition created successfully! It will be reviewed by Pharmacy Head.',
          position: 'top',
          timeout: 5000,
        });
        // Navigate to requisitions page
        router.push({ name: 'PharmacyRequisitions' });
      } catch (error) {
        console.error('Error creating requisition:', error);
        const errorData = error.response?.data;
        const errorMessage = errorData?.message || errorData?.detail || 'Failed to create requisition';
        const pendingItems = errorData?.pending_items || [];
        
        if (pendingItems && pendingItems.length > 0) {
          // Show dialog with pending items and option to cancel
          $q.dialog({
            title: 'Pending Requisitions Found',
            message: `Cannot create requisition. The following items already have pending requisitions:\n\n${pendingItems.map(item => `• ${item.product_name} (${item.product_code})\n  Requisition: ${item.requisition_number} - Status: ${item.status}`).join('\n\n')}\n\nPlease follow up on the existing requests or cancel them before creating a new requisition.`,
            html: true,
            persistent: true,
            ok: {
              label: 'View Requisitions',
              color: 'primary',
              flat: false
            },
            cancel: {
              label: 'Close',
              flat: true
            }
          }).onOk(() => {
            router.push({ name: 'PharmacyRequisitions' });
          });
        } else {
          Notify.create({
            type: 'negative',
            message: errorMessage,
            position: 'top',
          });
        }
      } finally {
        creating.value = false;
      }
    };

    // Load departments and stores on component mount
    onMounted(() => {
      loadDepartments();
      loadStores();
    });

    return {
      requisitionForm,
      requisition,
      creating,
      showAddItemDialog,
      departmentOptions,
      storeOptions,
      loadProducts,
      filterProducts,
      openAddItemDialog,
      onProductSelected,
      selectedProduct,
      filteredProductOptions,
      loadingProducts,
      removeItem,
      createRequisition,
      loadDepartments,
      loadStores,
    };
  },
};
</script>

<style scoped>
.dialog-head {
  border-bottom: 1px solid var(--hms-border);
}
.dialog-title {
  font-size: var(--hms-text-lg);
  font-weight: 750;
  color: var(--hms-text-primary);
}
.dialog-actions {
  gap: 0.5rem;
}
</style>

