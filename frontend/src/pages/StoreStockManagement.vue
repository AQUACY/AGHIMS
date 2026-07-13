<template>
  <q-page class="q-pa-md">
    <div class="row items-center q-mb-md">
      <q-btn
        flat
        icon="arrow_back"
        label="Back to Inventory"
        @click="$router.push('/inventory-mode')"
        class="q-mr-md"
      />
      <div class="text-h4 text-weight-bold glass-text">Store Stock Management</div>
    </div>
    <q-banner class="glass-card q-pa-md q-mb-md">
      <template v-slot:avatar>
        <q-icon name="info" color="primary" />
      </template>
      Manage stock for stores. Store Managers add stock with batch numbers and expiry dates. Department Heads approve stock before it becomes available for requisitions.
    </q-banner>

    <q-tabs v-model="activeTab" class="q-mb-md">
      <q-tab name="stock" label="Stock Management" icon="inventory" />
      <q-tab name="vendors" label="Vendors" icon="store" />
    </q-tabs>

    <!-- Stock Management Tab -->
    <q-tab-panels v-model="activeTab" animated>
      <q-tab-panel name="stock">
        <!-- Add Stock Form -->
        <q-card class="q-mb-md glass-card" flat v-if="canAddStock">
          <q-card-section>
            <div class="text-h6 q-mb-md glass-text">Add New Stock</div>
            <q-form @submit="addStock" ref="stockFormRef">
              <div class="row q-gutter-md">
                <q-select
                  v-model="stockForm.store_id"
                  :options="storeOptions"
                  option-value="value"
                  option-label="label"
                  emit-value
                  map-options
                  label="Store *"
                  filled
                  class="col-12 col-md-6"
                  lazy-rules
                  :rules="[(val) => !!val || 'Store is required']"
                  :disable="!canSelectStore"
                />
                <q-select
                  v-model="stockForm.product_code"
                  :options="productOptions"
                  option-value="value"
                  option-label="label"
                  emit-value
                  map-options
                  label="Product *"
                  filled
                  use-input
                  input-debounce="300"
                  @filter="filterProducts"
                  class="col-12 col-md-6"
                  lazy-rules
                  :rules="[(val) => !!val || 'Product is required']"
                  hint="Search by product name or code. Product must exist in Price List Management first."
                >
                  <template v-slot:no-option>
                    <q-item>
                      <q-item-section class="text-grey">
                        No products found. Add products in Price List Management first.
                      </q-item-section>
                    </q-item>
                  </template>
                </q-select>
                <q-select
                  v-model="stockForm.vendor_id"
                  :options="vendorOptions"
                  option-value="value"
                  option-label="label"
                  emit-value
                  map-options
                  label="Vendor *"
                  filled
                  use-input
                  input-debounce="300"
                  @filter="filterVendors"
                  class="col-12 col-md-6"
                  lazy-rules
                  :rules="[(val) => !!val || 'Vendor is required']"
                  hint="Select existing vendor or create new one in Vendors tab"
                >
                  <template v-slot:no-option>
                    <q-item>
                      <q-item-section class="text-grey">
                        No vendors found. Create a vendor in the Vendors tab first.
                      </q-item-section>
                    </q-item>
                  </template>
                </q-select>
                <q-input
                  v-model="stockForm.batch_number"
                  label="Batch Number *"
                  filled
                  class="col-12 col-md-6"
                  lazy-rules
                  :rules="[(val) => !!val || 'Batch number is required']"
                />
                <q-input
                  v-model="stockForm.expiry_date"
                  label="Expiry Date *"
                  filled
                  type="date"
                  class="col-12 col-md-6"
                  lazy-rules
                  :rules="[(val) => !!val || 'Expiry date is required']"
                />
                <q-input
                  v-model.number="stockForm.quantity"
                  label="Quantity *"
                  filled
                  type="number"
                  step="0.01"
                  min="0"
                  class="col-12 col-md-6"
                  lazy-rules
                  :rules="[(val) => val > 0 || 'Quantity must be greater than 0']"
                />
                <q-input
                  v-model.number="stockForm.unit_price"
                  label="Unit Price (Optional)"
                  filled
                  type="number"
                  step="0.01"
                  min="0"
                  class="col-12 col-md-6"
                  hint="Purchase price per unit"
                />
                <q-input
                  v-model="stockForm.receipt_number"
                  label="Receipt/Invoice Number (Optional)"
                  filled
                  class="col-12 col-md-6"
                />
                <q-input
                  v-model="stockForm.notes"
                  label="Notes (Optional)"
                  filled
                  type="textarea"
                  class="col-12"
                />
                <div class="col-12">
                  <q-btn
                    type="submit"
                    color="primary"
                    label="Add Stock"
                    :loading="addingStock"
                    icon="add"
                  />
                  <q-btn
                    flat
                    label="Reset"
                    @click="resetStockForm"
                    class="q-ml-sm"
                  />
                </div>
              </div>
            </q-form>
          </q-card-section>
        </q-card>

        <!-- Stock List -->
        <q-card class="glass-card" flat>
          <q-card-section>
            <div class="text-h6 q-mb-md glass-text">Stock List</div>
            <div class="row q-gutter-md q-mb-md">
              <q-select
                v-model="filters.store_id"
                :options="storeOptions"
                label="Filter by Store"
                filled
                clearable
                class="col-12 col-md-3"
                @update:model-value="loadStock"
              />
              <q-select
                v-model="filters.status"
                :options="statusOptions"
                label="Filter by Status"
                filled
                clearable
                class="col-12 col-md-3"
                @update:model-value="loadStock"
              />
              <q-input
                v-model="filters.product_code"
                label="Search by Product Code"
                filled
                clearable
                class="col-12 col-md-3"
                @update:model-value="loadStock"
              />
              <div class="col-12 col-md-3">
                <q-btn
                  color="primary"
                  label="Refresh"
                  @click="loadStock"
                  icon="refresh"
                  :loading="loading"
                />
              </div>
            </div>
            <q-table
              :rows="stockList"
              :columns="stockColumns"
              :loading="loading"
              row-key="id"
              :pagination="{ rowsPerPage: 20 }"
              class="glass-card"
            >
              <template v-slot:body-cell-status="props">
                <q-td :props="props">
                  <q-badge
                    :color="getStatusColor(props.value)"
                    :label="props.value"
                  />
                </q-td>
              </template>
              <template v-slot:body-cell-expiry_date="props">
                <q-td :props="props">
                  <span :class="getExpiryDateClass(props.value)">
                    {{ formatDate(props.value) }}
                  </span>
                </q-td>
              </template>
              <template v-slot:body-cell-actions="props">
                <q-td :props="props">
                  <q-btn
                    v-if="canApproveStock && (props.row.status === 'pending' || props.row.status === 'PENDING')"
                    size="sm"
                    color="positive"
                    label="Approve"
                    @click="openApproveDialog(props.row)"
                    class="q-mr-xs"
                  />
                  <q-btn
                    v-if="canApproveStock && (props.row.status === 'pending' || props.row.status === 'PENDING')"
                    size="sm"
                    color="negative"
                    label="Reject"
                    @click="openRejectDialog(props.row)"
                    class="q-mr-xs"
                  />
                  <q-btn
                    v-if="canEditStock(props.row)"
                    size="sm"
                    color="primary"
                    label="Edit"
                    @click="openEditStockDialog(props.row)"
                    class="q-mr-xs"
                  />
                  <q-btn
                    v-if="canDeleteStock(props.row)"
                    size="sm"
                    color="negative"
                    label="Delete"
                    @click="deleteStockItem(props.row)"
                  />
                </q-td>
              </template>
            </q-table>
          </q-card-section>
        </q-card>
      </q-tab-panel>

      <!-- Vendors Tab -->
      <q-tab-panel name="vendors">
        <!-- Add Vendor Form -->
        <q-card class="q-mb-md glass-card" flat>
          <q-card-section>
            <div class="text-h6 q-mb-md glass-text">Add New Vendor</div>
            <q-form @submit="createVendor" ref="vendorFormRef">
              <div class="row q-gutter-md">
                <q-input
                  v-model="vendorForm.name"
                  label="Vendor Name *"
                  filled
                  class="col-12 col-md-6"
                  lazy-rules
                  :rules="[(val) => !!val || 'Vendor name is required']"
                />
                <q-input
                  v-model="vendorForm.contact_person"
                  label="Contact Person"
                  filled
                  class="col-12 col-md-6"
                />
                <q-input
                  v-model="vendorForm.phone"
                  label="Phone"
                  filled
                  class="col-12 col-md-6"
                />
                <q-input
                  v-model="vendorForm.email"
                  label="Email"
                  filled
                  type="email"
                  class="col-12 col-md-6"
                />
                <q-input
                  v-model="vendorForm.address"
                  label="Address"
                  filled
                  type="textarea"
                  class="col-12"
                />
                <q-input
                  v-model="vendorForm.notes"
                  label="Notes"
                  filled
                  type="textarea"
                  class="col-12"
                />
                <q-toggle
                  v-model="vendorForm.is_active"
                  label="Active"
                  class="col-12"
                />
                <div class="col-12">
                  <q-btn
                    type="submit"
                    color="primary"
                    label="Create Vendor"
                    :loading="creatingVendor"
                    icon="add"
                  />
                  <q-btn
                    flat
                    label="Reset"
                    @click="resetVendorForm"
                    class="q-ml-sm"
                  />
                </div>
              </div>
            </q-form>
          </q-card-section>
        </q-card>

        <!-- Vendors List -->
        <q-card class="glass-card" flat>
          <q-card-section>
            <div class="text-h6 q-mb-md glass-text">Vendors List</div>
            <div class="row q-gutter-md q-mb-md">
              <q-input
                v-model="vendorSearch"
                label="Search Vendors"
                filled
                clearable
                class="col-12 col-md-6"
                @update:model-value="loadVendors"
              />
              <div class="col-12 col-md-6">
                <q-btn
                  color="primary"
                  label="Refresh"
                  @click="loadVendors"
                  icon="refresh"
                  :loading="loadingVendors"
                />
              </div>
            </div>
            <q-table
              :rows="vendorsList"
              :columns="vendorColumns"
              :loading="loadingVendors"
              row-key="id"
              :pagination="{ rowsPerPage: 20 }"
              class="glass-card"
            >
              <template v-slot:body-cell-is_active="props">
                <q-td :props="props">
                  <q-badge
                    :color="props.value ? 'positive' : 'negative'"
                    :label="props.value ? 'Active' : 'Inactive'"
                  />
                </q-td>
              </template>
              <template v-slot:body-cell-actions="props">
                <q-td :props="props">
                  <q-btn
                    size="sm"
                    color="primary"
                    label="Edit"
                    @click="openEditVendorDialog(props.row)"
                    class="q-mr-xs"
                  />
                  <q-btn
                    v-if="authStore.canAccess(['Admin'])"
                    size="sm"
                    color="negative"
                    label="Delete"
                    @click="deleteVendor(props.row)"
                  />
                </q-td>
              </template>
            </q-table>
          </q-card-section>
        </q-card>
      </q-tab-panel>
    </q-tab-panels>

    <!-- Approve Stock Dialog -->
    <q-dialog v-model="showApproveDialog">
      <q-card style="min-width: 400px">
        <q-card-section>
          <div class="text-h6">Approve Stock</div>
        </q-card-section>
        <q-card-section>
          <div class="q-mb-md">
            <strong>Product:</strong> {{ selectedStock?.product_name }}<br/>
            <strong>Batch:</strong> {{ selectedStock?.batch_number }}<br/>
            <strong>Quantity:</strong> {{ selectedStock?.quantity }}<br/>
            <strong>Expiry Date:</strong> {{ formatDate(selectedStock?.expiry_date) }}
          </div>
          <q-btn
            color="positive"
            label="Approve"
            @click="approveStock"
            :loading="approving"
            class="full-width"
          />
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- Reject Stock Dialog -->
    <q-dialog v-model="showRejectDialog">
      <q-card style="min-width: 400px">
        <q-card-section>
          <div class="text-h6">Reject Stock</div>
        </q-card-section>
        <q-card-section>
          <div class="q-mb-md">
            <strong>Product:</strong> {{ selectedStock?.product_name }}<br/>
            <strong>Batch:</strong> {{ selectedStock?.batch_number }}<br/>
            <strong>Quantity:</strong> {{ selectedStock?.quantity }}
          </div>
          <q-input
            v-model="rejectionReason"
            label="Rejection Reason *"
            filled
            type="textarea"
            class="q-mb-md"
            lazy-rules
            :rules="[(val) => !!val || 'Rejection reason is required']"
          />
          <q-btn
            color="negative"
            label="Reject"
            @click="rejectStock"
            :loading="approving"
            class="full-width"
          />
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- Edit Stock Dialog -->
    <q-dialog v-model="showEditStockDialog">
      <q-card style="min-width: 600px; max-width: 800px">
        <q-card-section>
          <div class="text-h6">Edit Stock</div>
        </q-card-section>
        <q-card-section>
          <q-form @submit="updateStock" ref="editStockFormRef">
            <div class="row q-gutter-md">
              <q-select
                v-model="editStockForm.product_code"
                :options="productOptions"
                option-value="value"
                option-label="label"
                emit-value
                map-options
                label="Product *"
                filled
                use-input
                input-debounce="300"
                @filter="filterProducts"
                class="col-12 col-md-6"
                lazy-rules
                :rules="[(val) => !!val || 'Product is required']"
              />
              <q-select
                v-model="editStockForm.vendor_id"
                :options="vendorOptions"
                option-value="value"
                option-label="label"
                emit-value
                map-options
                label="Vendor *"
                filled
                use-input
                input-debounce="300"
                @filter="filterVendors"
                class="col-12 col-md-6"
                lazy-rules
                :rules="[(val) => !!val || 'Vendor is required']"
              />
              <q-input
                v-model="editStockForm.batch_number"
                label="Batch Number *"
                filled
                class="col-12 col-md-6"
                lazy-rules
                :rules="[(val) => !!val || 'Batch number is required']"
              />
              <q-input
                v-model="editStockForm.expiry_date"
                label="Expiry Date *"
                filled
                type="date"
                class="col-12 col-md-6"
                lazy-rules
                :rules="[(val) => !!val || 'Expiry date is required']"
              />
              <q-input
                v-model.number="editStockForm.quantity"
                label="Quantity *"
                filled
                type="number"
                step="0.01"
                min="0"
                class="col-12 col-md-6"
                lazy-rules
                :rules="[(val) => val > 0 || 'Quantity must be greater than 0']"
              />
              <q-input
                v-model.number="editStockForm.unit_price"
                label="Unit Price (Optional)"
                filled
                type="number"
                step="0.01"
                min="0"
                class="col-12 col-md-6"
              />
              <q-input
                v-model="editStockForm.receipt_number"
                label="Receipt/Invoice Number (Optional)"
                filled
                class="col-12 col-md-6"
              />
              <q-input
                v-model="editStockForm.notes"
                label="Notes (Optional)"
                filled
                type="textarea"
                class="col-12"
              />
            </div>
            <q-card-actions align="right" class="q-mt-md">
              <q-btn flat label="Cancel" v-close-popup />
              <q-btn color="primary" label="Update" type="submit" :loading="updatingStock" />
            </q-card-actions>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- Edit Vendor Dialog -->
    <q-dialog v-model="showEditVendorDialog">
      <q-card style="min-width: 500px">
        <q-card-section>
          <div class="text-h6">Edit Vendor</div>
        </q-card-section>
        <q-card-section>
          <q-form @submit="updateVendor" ref="editVendorFormRef">
            <q-input
              v-model="editVendorForm.name"
              label="Vendor Name *"
              filled
              class="q-mb-md"
              lazy-rules
              :rules="[(val) => !!val || 'Vendor name is required']"
            />
            <q-input
              v-model="editVendorForm.contact_person"
              label="Contact Person"
              filled
              class="q-mb-md"
            />
            <q-input
              v-model="editVendorForm.phone"
              label="Phone"
              filled
              class="q-mb-md"
            />
            <q-input
              v-model="editVendorForm.email"
              label="Email"
              filled
              type="email"
              class="q-mb-md"
            />
            <q-input
              v-model="editVendorForm.address"
              label="Address"
              filled
              type="textarea"
              class="q-mb-md"
            />
            <q-input
              v-model="editVendorForm.notes"
              label="Notes"
              filled
              type="textarea"
              class="q-mb-md"
            />
            <q-toggle
              v-model="editVendorForm.is_active"
              label="Active"
              class="q-mb-md"
            />
            <q-card-actions align="right">
              <q-btn flat label="Cancel" v-close-popup />
              <q-btn color="primary" label="Update" type="submit" :loading="updatingVendor" />
            </q-card-actions>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useQuasar } from 'quasar';
import { useAuthStore } from '../stores/auth';
import { useRouter } from 'vue-router';
import { vendorsAPI, storeStockAPI, storesAPI, priceListAPI, storeStaffAssignmentsAPI } from '../services/api';
import { storeSelectLabel } from '../utils/storeKind';

const $q = useQuasar();
const router = useRouter();
const authStore = useAuthStore();

// Check permissions
if (!authStore.canAccess(['Admin', 'Store Manager', 'Department Head', 'Pharmacy Head'])) {
  router.push('/dashboard');
}

const activeTab = ref('stock');
const loading = ref(false);
const loadingVendors = ref(false);
const addingStock = ref(false);
const creatingVendor = ref(false);
const updatingVendor = ref(false);
const approving = ref(false);

// Form refs
const stockFormRef = ref(null);
const vendorFormRef = ref(null);
const editVendorFormRef = ref(null);

// Stock Management
const stockForm = ref({
  store_id: null,
  product_code: null,
  product_name: '',
  vendor_id: null,
  batch_number: '',
  expiry_date: '',
  quantity: 0,
  unit_price: null,
  receipt_number: '',
  notes: ''
});

const stockList = ref([]);
const filters = ref({
  store_id: null,
  status: null,
  product_code: ''
});

const statusOptions = [
  { label: 'Pending', value: 'PENDING' },
  { label: 'Approved', value: 'APPROVED' },
  { label: 'Rejected', value: 'REJECTED' },
  { label: 'Expired', value: 'EXPIRED' }
];

const stockColumns = [
  { name: 'product_name', label: 'Product', field: 'product_name', align: 'left', sortable: true },
  { name: 'product_code', label: 'Code', field: 'product_code', align: 'left', sortable: true },
  { name: 'batch_number', label: 'Batch Number', field: 'batch_number', align: 'left', sortable: true },
  { name: 'vendor_name', label: 'Vendor', field: 'vendor_name', align: 'left', sortable: true },
  { name: 'quantity', label: 'Quantity', field: 'quantity', align: 'right', sortable: true },
  { name: 'expiry_date', label: 'Expiry Date', field: 'expiry_date', align: 'left', sortable: true },
  { name: 'status', label: 'Status', field: 'status', align: 'center', sortable: true },
  { name: 'created_by_name', label: 'Added By', field: 'created_by_name', align: 'left' },
  { name: 'actions', label: 'Actions', field: 'actions', align: 'center' }
];

// Vendor Management
const vendorForm = ref({
  name: '',
  contact_person: '',
  phone: '',
  email: '',
  address: '',
  notes: '',
  is_active: true
});

const editVendorForm = ref({
  id: null,
  name: '',
  contact_person: '',
  phone: '',
  email: '',
  address: '',
  notes: '',
  is_active: true
});

const vendorsList = ref([]);
const vendorSearch = ref('');
const vendorOptions = ref([]);
const allVendors = ref([]);

const vendorColumns = [
  { name: 'name', label: 'Vendor Name', field: 'name', align: 'left', sortable: true },
  { name: 'contact_person', label: 'Contact Person', field: 'contact_person', align: 'left' },
  { name: 'phone', label: 'Phone', field: 'phone', align: 'left' },
  { name: 'email', label: 'Email', field: 'email', align: 'left' },
  { name: 'is_active', label: 'Status', field: 'is_active', align: 'center' },
  { name: 'actions', label: 'Actions', field: 'actions', align: 'center' }
];

// Store and Product Options
const storeOptions = ref([]);
const productOptions = ref([]);
const allProducts = ref([]);
const userStoreIds = ref([]);

// Approval Dialogs
const showApproveDialog = ref(false);
const showRejectDialog = ref(false);
const showEditStockDialog = ref(false);
const showEditVendorDialog = ref(false);
const selectedStock = ref(null);
const rejectionReason = ref('');
const updatingStock = ref(false);

// Edit Stock Form
const editStockForm = ref({
  id: null,
  product_code: null,
  vendor_id: null,
  batch_number: '',
  expiry_date: '',
  quantity: 0,
  unit_price: null,
  receipt_number: '',
  notes: ''
});
const editStockFormRef = ref(null);

// Computed properties
const canAddStock = computed(() => {
  return authStore.canAccess(['Admin', 'Store Manager']);
});

const canApproveStock = computed(() => {
  return authStore.canAccess(['Admin', 'Department Head']);
});

const canSelectStore = computed(() => {
  // Store Managers can only select from their assigned stores
  if (authStore.canAccess(['Store Manager']) && !authStore.canAccess(['Admin'])) {
    return false;
  }
  return true;
});

const canEditStock = (stock) => {
  // Store Managers can edit their own pending/rejected stock
  // Admin can edit any stock
  if (authStore.canAccess(['Admin'])) return true;
  if (authStore.canAccess(['Store Manager'])) {
    const status = stock.status?.toUpperCase() || stock.status;
    return status === 'PENDING' || status === 'REJECTED';
  }
  return false;
};

const canDeleteStock = (stock) => {
  // Store Managers can delete their own pending/rejected stock
  // Admin can delete any stock
  if (authStore.canAccess(['Admin'])) return true;
  if (authStore.canAccess(['Store Manager'])) {
    const status = stock.status?.toUpperCase() || stock.status;
    return status === 'PENDING' || status === 'REJECTED';
  }
  return false;
};

// Methods
const loadStores = async () => {
  try {
    const response = await storesAPI.getAll(true); // Get only active stores
    storeOptions.value = (response.data || []).map((store) => ({
      label: storeSelectLabel(store),
      value: store.id,
    }));
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: 'Failed to load stores: ' + (error.response?.data?.detail || error.message)
    });
  }
};

const loadUserStoreAssignments = async () => {
  if (!authStore.canAccess(['Store Manager']) || authStore.canAccess(['Admin'])) {
    return;
  }

  try {
    const response = await storeStaffAssignmentsAPI.getAll({
      user_id: authStore.user?.id,
      active_only: true
    });
    userStoreIds.value = (response.data || []).map(assignment => assignment.store_id);
    
    // Auto-select first assigned store for Store Managers
    if (userStoreIds.value.length > 0 && !stockForm.value.store_id) {
      stockForm.value.store_id = userStoreIds.value[0];
    }
  } catch (error) {
    console.error('Error loading user store assignments:', error);
  }
};

const loadProducts = async () => {
  try {
    const res = await priceListAPI.searchPriceItems(null, null, 'product');
    let productsData = res.data;
    if (!Array.isArray(productsData) && res.data?.data) {
      productsData = res.data.data;
    }
    
    if (productsData && Array.isArray(productsData)) {
      const mappedProducts = productsData
        .filter(item => item.is_active !== false)
        .map(item => {
          const productCode = item.medication_code || item.g_drg_code || item.item_code || '';
          const productName = item.product_name || item.service_name || 'Unknown Product';
          
          return {
            label: `${productName} (${productCode})`,
            value: productCode,
            name: productName
          };
        });
      
      allProducts.value = mappedProducts;
      productOptions.value = mappedProducts.slice(0, 50);
    }
  } catch (error) {
    console.error('Error loading products:', error);
  }
};

const filterProducts = (val, update) => {
  if (val === '') {
    update(() => {
      productOptions.value = allProducts.value.slice(0, 50);
    });
    return;
  }
  
  update(() => {
    const needle = val.toLowerCase();
    productOptions.value = allProducts.value.filter(v => 
      v.label.toLowerCase().indexOf(needle) > -1
    );
  });
};

const loadVendors = async () => {
  loadingVendors.value = true;
  try {
    const response = await vendorsAPI.getAll({
      search: vendorSearch.value || undefined,
      is_active: true
    });
    vendorsList.value = response.data || [];
    allVendors.value = vendorsList.value.map(v => ({
      label: v.name,
      value: v.id
    }));
    vendorOptions.value = allVendors.value;
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: 'Failed to load vendors: ' + (error.response?.data?.detail || error.message)
    });
  } finally {
    loadingVendors.value = false;
  }
};

const filterVendors = (val, update) => {
  if (val === '') {
    update(() => {
      vendorOptions.value = allVendors.value;
    });
    return;
  }
  
  update(() => {
    const needle = val.toLowerCase();
    vendorOptions.value = allVendors.value.filter(v => 
      v.label.toLowerCase().indexOf(needle) > -1
    );
  });
};

const loadStock = async () => {
  loading.value = true;
  try {
    const response = await storeStockAPI.getAll({
      store_id: filters.value.store_id || undefined,
      status: filters.value.status || undefined,
      product_code: filters.value.product_code || undefined
    });
    stockList.value = response.data || [];
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: 'Failed to load stock: ' + (error.response?.data?.detail || error.message)
    });
  } finally {
    loading.value = false;
  }
};

const addStock = async () => {
  if (!stockFormRef.value) return;
  const valid = await stockFormRef.value.validate();
  if (!valid) return;

  // Get product name from selected product
  const productCodeValue = stockForm.value.product_code;
  
  if (!productCodeValue) {
    $q.notify({
      type: 'negative',
      message: 'Please select a product'
    });
    return;
  }
  
  const selectedProduct = allProducts.value.find(p => p.value === productCodeValue);
  
  if (!selectedProduct) {
    $q.notify({
      type: 'negative',
      message: 'Please select a valid product from the list'
    });
    return;
  }

  addingStock.value = true;
  try {
    await storeStockAPI.create({
      ...stockForm.value,
      product_name: selectedProduct.name
    });
    $q.notify({
      type: 'positive',
      message: 'Stock added successfully. Waiting for Department Head approval.'
    });
    resetStockForm();
    loadStock();
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: 'Failed to add stock: ' + (error.response?.data?.detail || error.message)
    });
  } finally {
    addingStock.value = false;
  }
};

const resetStockForm = () => {
  stockForm.value = {
    store_id: userStoreIds.value.length > 0 ? userStoreIds.value[0] : null,
    product_code: null,
    product_name: '',
    vendor_id: null,
    batch_number: '',
    expiry_date: '',
    quantity: 0,
    unit_price: null,
    receipt_number: '',
    notes: ''
  };
  if (stockFormRef.value && typeof stockFormRef.value.resetValidation === 'function') {
    stockFormRef.value.resetValidation();
  }
};

const openApproveDialog = (stock) => {
  selectedStock.value = stock;
  showApproveDialog.value = true;
};

const openRejectDialog = (stock) => {
  selectedStock.value = stock;
  rejectionReason.value = '';
  showRejectDialog.value = true;
};

const approveStock = async () => {
  approving.value = true;
  try {
    await storeStockAPI.approve(selectedStock.value.id, { approval: true });
    $q.notify({
      type: 'positive',
      message: 'Stock approved successfully'
    });
    showApproveDialog.value = false;
    loadStock();
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: 'Failed to approve stock: ' + (error.response?.data?.detail || error.message)
    });
  } finally {
    approving.value = false;
  }
};

const rejectStock = async () => {
  if (!rejectionReason.value) {
    $q.notify({
      type: 'warning',
      message: 'Please provide a rejection reason'
    });
    return;
  }

  approving.value = true;
  try {
    await storeStockAPI.approve(selectedStock.value.id, {
      approval: false,
      rejection_reason: rejectionReason.value
    });
    $q.notify({
      type: 'positive',
      message: 'Stock rejected successfully'
    });
    showRejectDialog.value = false;
    loadStock();
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: 'Failed to reject stock: ' + (error.response?.data?.detail || error.message)
    });
  } finally {
    approving.value = false;
  }
};

const createVendor = async () => {
  if (!vendorFormRef.value) return;
  const valid = await vendorFormRef.value.validate();
  if (!valid) return;

  creatingVendor.value = true;
  try {
    await vendorsAPI.create(vendorForm.value);
    $q.notify({
      type: 'positive',
      message: 'Vendor created successfully'
    });
    resetVendorForm();
    loadVendors();
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: 'Failed to create vendor: ' + (error.response?.data?.detail || error.message)
    });
  } finally {
    creatingVendor.value = false;
  }
};

const resetVendorForm = () => {
  vendorForm.value = {
    name: '',
    contact_person: '',
    phone: '',
    email: '',
    address: '',
    notes: '',
    is_active: true
  };
  if (vendorFormRef.value && typeof vendorFormRef.value.resetValidation === 'function') {
    vendorFormRef.value.resetValidation();
  }
};

const openEditVendorDialog = (vendor) => {
  editVendorForm.value = {
    id: vendor.id,
    name: vendor.name,
    contact_person: vendor.contact_person || '',
    phone: vendor.phone || '',
    email: vendor.email || '',
    address: vendor.address || '',
    notes: vendor.notes || '',
    is_active: vendor.is_active
  };
  showEditVendorDialog.value = true;
};

const updateVendor = async () => {
  if (!editVendorFormRef.value) return;
  const valid = await editVendorFormRef.value.validate();
  if (!valid) return;

  updatingVendor.value = true;
  try {
    await vendorsAPI.update(editVendorForm.value.id, {
      name: editVendorForm.value.name,
      contact_person: editVendorForm.value.contact_person,
      phone: editVendorForm.value.phone,
      email: editVendorForm.value.email,
      address: editVendorForm.value.address,
      notes: editVendorForm.value.notes,
      is_active: editVendorForm.value.is_active
    });
    $q.notify({
      type: 'positive',
      message: 'Vendor updated successfully'
    });
    showEditVendorDialog.value = false;
    loadVendors();
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: 'Failed to update vendor: ' + (error.response?.data?.detail || error.message)
    });
  } finally {
    updatingVendor.value = false;
  }
};

const deleteVendor = async (vendor) => {
  $q.dialog({
    title: 'Confirm Delete',
    message: `Are you sure you want to delete vendor "${vendor.name}"?`,
    cancel: true,
    persistent: true
  }).onOk(async () => {
    try {
      await vendorsAPI.delete(vendor.id);
      $q.notify({
        type: 'positive',
        message: 'Vendor deleted successfully'
      });
      loadVendors();
    } catch (error) {
      $q.notify({
        type: 'negative',
        message: 'Failed to delete vendor: ' + (error.response?.data?.detail || error.message)
      });
    }
  });
};

const getStatusColor = (status) => {
  const colors = {
    PENDING: 'orange',
    APPROVED: 'green',
    REJECTED: 'red',
    EXPIRED: 'grey',
    // Support lowercase for backward compatibility
    pending: 'orange',
    approved: 'green',
    rejected: 'red',
    expired: 'grey'
  };
  return colors[status] || colors[status?.toUpperCase()] || 'grey';
};

const getExpiryDateClass = (expiryDate) => {
  if (!expiryDate) return '';
  const today = new Date();
  const expiry = new Date(expiryDate);
  const daysUntilExpiry = Math.ceil((expiry - today) / (1000 * 60 * 60 * 24));
  
  if (daysUntilExpiry < 0) return 'text-negative text-weight-bold';
  if (daysUntilExpiry <= 30) return 'text-warning text-weight-bold';
  return '';
};

const formatDate = (dateString) => {
  if (!dateString) return 'N/A';
  const date = new Date(dateString);
  return date.toLocaleDateString('en-GB');
};

const openEditStockDialog = (stock) => {
  editStockForm.value = {
    id: stock.id,
    product_code: stock.product_code,
    vendor_id: stock.vendor_id,
    batch_number: stock.batch_number,
    expiry_date: stock.expiry_date ? new Date(stock.expiry_date).toISOString().split('T')[0] : '',
    quantity: stock.quantity,
    unit_price: stock.unit_price,
    receipt_number: stock.receipt_number || '',
    notes: stock.notes || ''
  };
  showEditStockDialog.value = true;
};

const updateStock = async () => {
  if (!editStockFormRef.value) return;
  const valid = await editStockFormRef.value.validate();
  if (!valid) return;

  updatingStock.value = true;
  try {
    await storeStockAPI.update(editStockForm.value.id, editStockForm.value);
    $q.notify({
      type: 'positive',
      message: 'Stock updated successfully'
    });
    showEditStockDialog.value = false;
    loadStock();
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: 'Failed to update stock: ' + (error.response?.data?.detail || error.message)
    });
  } finally {
    updatingStock.value = false;
  }
};

const deleteStockItem = async (stock) => {
  $q.dialog({
    title: 'Confirm Delete',
    message: `Are you sure you want to delete stock for ${stock.product_name} (Batch: ${stock.batch_number})? This action cannot be undone.`,
    cancel: true,
    persistent: true
  }).onOk(async () => {
    try {
      await storeStockAPI.delete(stock.id);
      $q.notify({
        type: 'positive',
        message: 'Stock deleted successfully'
      });
      loadStock();
    } catch (error) {
      $q.notify({
        type: 'negative',
        message: 'Failed to delete stock: ' + (error.response?.data?.detail || error.message)
      });
    }
  });
};

onMounted(async () => {
  await loadStores();
  await loadProducts();
  await loadVendors();
  await loadUserStoreAssignments();
  await loadStock();
});
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

