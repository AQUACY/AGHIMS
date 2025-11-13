<template>
  <q-page class="q-pa-md">
    <div class="row items-center q-mb-md">
      <q-btn
        flat
        icon="arrow_back"
        label="Back"
        @click="$router.back()"
        class="q-mr-md"
      />
      <div>
        <div class="text-h4 text-weight-bold glass-text">
          Inventory Debit - Add Products Used
        </div>
        <div v-if="patientInfo?.card_number" class="text-subtitle1 text-grey-4 q-mt-xs">
          Card Number: <span class="text-weight-bold">{{ patientInfo.card_number }}</span>
        </div>
      </div>
    </div>

    <!-- Patient Info Card -->
    <q-card v-if="patientInfo" class="glass-card q-mb-md" flat bordered>
      <q-card-section>
        <div class="text-h6 glass-text q-mb-sm">
          <q-icon name="person" color="primary" class="q-mr-sm" />
          Patient Information
        </div>
        <div class="row q-col-gutter-md">
          <div class="col-12 col-md-3">
            <div class="text-caption text-grey-7">Patient Name</div>
            <div class="text-body1 text-weight-bold">{{ patientInfo.patient_name }}</div>
          </div>
          <div class="col-12 col-md-3">
            <div class="text-caption text-grey-7">Card Number</div>
            <div class="text-body1 text-weight-bold text-primary">{{ patientInfo.card_number }}</div>
          </div>
          <div class="col-12 col-md-3">
            <div class="text-caption text-grey-7">Ward</div>
            <div class="text-body1 text-weight-bold">{{ patientInfo.ward }}</div>
          </div>
          <div class="col-12 col-md-3">
            <div class="text-caption text-grey-7">Total Products Used</div>
            <div class="text-body1 text-weight-bold text-positive">{{ inventoryDebits.length }}</div>
          </div>
        </div>
      </q-card-section>
    </q-card>

    <!-- Add Product Form -->
    <q-card class="glass-card q-mb-md" flat bordered>
      <q-card-section>
        <div class="text-h6 glass-text q-mb-md">
          <q-icon name="add_shopping_cart" color="primary" class="q-mr-sm" />
          Add Product Used
        </div>
        <div class="row q-col-gutter-md">
          <!-- Product Search with Auto-complete -->
          <div class="col-12">
            <q-select
              v-model="selectedProduct"
              :options="filteredProductOptions"
              filled
              use-input
              input-debounce="300"
              label="Search Product *"
              hint="Type to search for products (e.g., gloves, gauze, infusion set) - Select to auto-fill"
              :rules="[val => !!val || 'Product is required']"
              @filter="filterProducts"
              @update:model-value="onProductSelected"
              option-label="label"
              option-value="value"
              emit-value
              map-options
              clearable
            >
              <template v-slot:option="scope">
                <q-item v-bind="scope.itemProps">
                  <q-item-section>
                    <q-item-label>{{ scope.opt.label }}</q-item-label>
                    <q-item-label caption>
                      Code: {{ scope.opt.value.code }} | 
                      Price: GHS {{ scope.opt.value.price?.toFixed(2) || '0.00' }}
                    </q-item-label>
                  </q-item-section>
                </q-item>
              </template>
              <template v-slot:no-option>
                <q-item>
                  <q-item-section class="text-grey">
                    No products found. You can enter manually below.
                  </q-item-section>
                </q-item>
              </template>
            </q-select>
          </div>

          <!-- Manual Product Entry -->
          <div class="col-12 col-md-6">
            <q-input
              v-model="productForm.product_code"
              filled
              label="Product Code *"
              hint="Product/medication code"
              :rules="[val => !!val || 'Product code is required']"
            />
          </div>
          <div class="col-12 col-md-6">
            <q-input
              v-model="productForm.product_name"
              filled
              label="Product Name *"
              hint="e.g., Gloves, Gauze, Infusion Giving Set"
              :rules="[val => !!val || 'Product name is required']"
            />
          </div>
          <div class="col-12 col-md-4">
            <q-input
              v-model.number="productForm.quantity"
              filled
              type="number"
              step="0.01"
              min="0.01"
              label="Quantity *"
              hint="Number of units used"
              :rules="[
                val => !!val || 'Quantity is required',
                val => val > 0 || 'Quantity must be greater than 0'
              ]"
            />
          </div>
          <div class="col-12 col-md-4">
            <q-input
              v-model.number="productForm.unit_price"
              filled
              type="number"
              step="0.01"
              min="0"
              label="Unit Price (GHS)"
              hint="Leave empty to auto-fetch from price list"
            />
          </div>
          <div class="col-12 col-md-4">
            <q-input
              v-model="productForm.notes"
              filled
              type="textarea"
              label="Notes (optional)"
              hint="Additional notes about product usage"
              rows="2"
            />
          </div>
          <div class="col-12 flex items-end q-gutter-sm">
            <q-btn
              flat
              icon="add"
              label="Add Product"
              color="primary"
              @click="addProduct"
              :loading="adding"
              :disable="!productForm.product_code || !productForm.product_name || !productForm.quantity"
            />
            <q-btn
              flat
              icon="refresh"
              label="Clear"
              color="grey"
              @click="clearForm"
            />
          </div>
        </div>
      </q-card-section>
    </q-card>

    <!-- Products Used Table -->
    <q-card class="glass-card" flat bordered>
      <q-card-section>
        <div class="row items-center q-mb-md">
          <div class="text-h6 glass-text">
            Products Used ({{ inventoryDebits.length }})
          </div>
          <q-space />
          <q-btn
            flat
            icon="refresh"
            label="Refresh"
            color="primary"
            @click="loadInventoryDebits"
            :loading="loading"
          />
        </div>
        <q-table
          :rows="inventoryDebits"
          :columns="columns"
          row-key="id"
          :loading="loading"
          flat
          bordered
          :rows-per-page-options="[10, 20, 50]"
        >
          <template v-slot:body-cell-actions="props">
            <q-td :props="props">
              <q-btn
                flat
                dense
                icon="delete"
                color="negative"
                @click="deleteDebit(props.row)"
                :loading="deletingId === props.row.id"
                :label="props.row.is_billed ? 'Delete' : 'Delete'"
              />
              <q-chip
                v-if="props.row.is_billed"
                color="info"
                text-color="white"
                size="sm"
                label="Billed"
                class="q-ml-sm"
              />
            </q-td>
          </template>
        </q-table>
      </q-card-section>
    </q-card>
  </q-page>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useQuasar } from 'quasar';
import { consultationAPI, priceListAPI } from '../services/api';

const route = useRoute();
const router = useRouter();
const $q = useQuasar();

const wardAdmissionId = computed(() => parseInt(route.params.id));
const encounterId = computed(() => route.query.encounter_id ? parseInt(route.query.encounter_id) : null);

const patientInfo = ref(null);
const inventoryDebits = ref([]);
const loading = ref(false);
const adding = ref(false);
const deletingId = ref(null);

const selectedProduct = ref(null);
const allProducts = ref([]);
const filteredProductOptions = ref([]);
const productSearchQuery = ref('');

const productForm = ref({
  product_code: '',
  product_name: '',
  quantity: 1,
  unit_price: null,
  notes: ''
});

const columns = [
  {
    name: 'product_name',
    label: 'Product Name',
    field: 'product_name',
    align: 'left',
    sortable: true
  },
  {
    name: 'product_code',
    label: 'Code',
    field: 'product_code',
    align: 'left',
    sortable: true
  },
  {
    name: 'quantity',
    label: 'Quantity',
    field: 'quantity',
    align: 'center',
    sortable: true
  },
  {
    name: 'unit_price',
    label: 'Unit Price',
    field: 'unit_price',
    align: 'right',
    format: val => `GHS ${val?.toFixed(2) || '0.00'}`,
    sortable: true
  },
  {
    name: 'total_price',
    label: 'Total Price',
    field: 'total_price',
    align: 'right',
    format: val => `GHS ${val?.toFixed(2) || '0.00'}`,
    sortable: true
  },
  {
    name: 'used_by',
    label: 'Used By',
    field: 'used_by_name',
    align: 'left',
    sortable: true
  },
  {
    name: 'used_at',
    label: 'Date/Time',
    field: 'used_at',
    align: 'left',
    format: val => val ? new Date(val).toLocaleString() : '',
    sortable: true
  },
  {
    name: 'actions',
    label: 'Actions',
    align: 'center'
  }
];

const loadPatientInfo = async () => {
  if (!wardAdmissionId.value) return;
  
  try {
    const res = await consultationAPI.getWardAdmission(wardAdmissionId.value);
    if (res.data) {
      // Construct full name from surname, name, and other_names
      const parts = [];
      if (res.data.patient_surname) parts.push(res.data.patient_surname);
      if (res.data.patient_name) parts.push(res.data.patient_name);
      if (res.data.patient_other_names) parts.push(res.data.patient_other_names);
      const fullName = parts.length > 0 ? parts.join(' ') : res.data.patient_name || 'N/A';
      
      patientInfo.value = {
        patient_name: fullName,
        card_number: res.data.patient_card_number || res.data.card_number || 'N/A',
        ward: res.data.ward || 'N/A'
      };
    }
  } catch (error) {
    console.error('Error loading patient info:', error);
    $q.notify({
      type: 'negative',
      message: 'Failed to load patient information',
      position: 'top'
    });
  }
};

const loadInventoryDebits = async () => {
  if (!wardAdmissionId.value) return;
  
  loading.value = true;
  try {
    const res = await consultationAPI.getInpatientInventoryDebits(wardAdmissionId.value);
    inventoryDebits.value = res.data || [];
  } catch (error) {
    console.error('Error loading inventory debits:', error);
    $q.notify({
      type: 'negative',
      message: 'Failed to load inventory debits',
      position: 'top'
    });
  } finally {
    loading.value = false;
  }
};

const loadProducts = async () => {
  try {
    loading.value = true;
    console.log('Loading products from price list...');
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
        .filter(item => item.is_active !== false) // Only active products
        .map(item => {
          const productCode = item.medication_code || item.g_drg_code || item.item_code || '';
          const productName = item.product_name || item.service_name || 'Unknown Product';
          const price = item.cash_price || item.base_rate || item.insured_price || 0;
          
          return {
            label: `${productName} (${productCode})`,
            value: {
              code: productCode,
              name: productName,
              price: price,
              fullItem: item // Store full item for reference
            }
          };
        });
      
      console.log(`Mapped ${mappedProducts.length} active products`);
      allProducts.value = mappedProducts;
      filteredProductOptions.value = allProducts.value.slice(0, 50); // Show first 50 by default
      
      if (mappedProducts.length === 0) {
        $q.notify({
          type: 'warning',
          message: 'No active products found in price list',
          position: 'top'
        });
      }
    } else {
      console.warn('Products data is not an array:', productsData);
      $q.notify({
        type: 'warning',
        message: 'No products data received from server',
        position: 'top'
      });
      allProducts.value = [];
      filteredProductOptions.value = [];
    }
  } catch (error) {
    console.error('Error loading products:', error);
    console.error('Error details:', error.response);
    const errorMessage = error.response?.data?.detail || error.message || 'Failed to load products from price list';
    $q.notify({
      type: 'negative',
      message: `Failed to load products: ${errorMessage}`,
      position: 'top',
      timeout: 5000
    });
    // Set empty array to prevent further errors
    allProducts.value = [];
    filteredProductOptions.value = [];
  } finally {
    loading.value = false;
  }
};

const filterProducts = (val, update) => {
  productSearchQuery.value = val;
  
  if (val === '') {
    update(() => {
      filteredProductOptions.value = allProducts.value.slice(0, 50); // Show first 50 when empty
    });
    return;
  }

  update(() => {
    const needle = val.toLowerCase();
    filteredProductOptions.value = allProducts.value.filter(
      p => {
        const labelMatch = p.label.toLowerCase().indexOf(needle) > -1;
        const codeMatch = p.value.code?.toLowerCase().indexOf(needle) > -1;
        const nameMatch = p.value.name?.toLowerCase().indexOf(needle) > -1;
        return labelMatch || codeMatch || nameMatch;
      }
    ).slice(0, 100); // Limit to 100 results for performance
  });
};

const onProductSelected = (product) => {
  if (product && typeof product === 'object') {
    productForm.value.product_code = product.code;
    productForm.value.product_name = product.name;
    if (product.price && product.price > 0) {
      productForm.value.unit_price = product.price;
    }
    // Auto-focus quantity field for quick entry
    setTimeout(() => {
      const quantityInput = document.querySelector('input[type="number"][label="Quantity *"]');
      if (quantityInput) {
        quantityInput.focus();
        quantityInput.select();
      }
    }, 100);
  }
};

const addProduct = async () => {
  if (!productForm.value.product_code || !productForm.value.product_name || !productForm.value.quantity) {
    $q.notify({
      type: 'warning',
      message: 'Please fill in all required fields',
      position: 'top'
    });
    return;
  }

  adding.value = true;
  try {
    const data = {
      product_code: productForm.value.product_code,
      product_name: productForm.value.product_name,
      quantity: parseFloat(productForm.value.quantity),
      unit_price: productForm.value.unit_price ? parseFloat(productForm.value.unit_price) : null,
      notes: productForm.value.notes || null
    };

    await consultationAPI.createInpatientInventoryDebit(wardAdmissionId.value, data);
    
    $q.notify({
      type: 'positive',
      message: 'Product added successfully and billed to patient',
      position: 'top'
    });

    clearForm();
    loadInventoryDebits();
  } catch (error) {
    console.error('Error adding product:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to add product',
      position: 'top'
    });
  } finally {
    adding.value = false;
  }
};

const deleteDebit = async (debit) => {
  const message = debit.is_billed
    ? `Are you sure you want to delete "${debit.product_name}"? This will also remove it from the patient's bill (GHS ${debit.total_price?.toFixed(2) || '0.00'}). This action cannot be undone.`
    : `Are you sure you want to delete "${debit.product_name}"? This action cannot be undone.`;
  
  $q.dialog({
    title: 'Confirm Delete',
    message: message,
    cancel: true,
    persistent: true,
    ok: {
      label: 'Delete',
      color: 'negative',
      flat: false
    },
    cancel: {
      label: 'Cancel',
      color: 'grey',
      flat: true
    }
  }).onOk(async () => {
    deletingId.value = debit.id;
    try {
      await consultationAPI.deleteInpatientInventoryDebit(wardAdmissionId.value, debit.id);
      $q.notify({
        type: 'positive',
        message: debit.is_billed 
          ? 'Product deleted successfully and removed from bill'
          : 'Product deleted successfully',
        position: 'top'
      });
      loadInventoryDebits();
    } catch (error) {
      console.error('Error deleting product:', error);
      $q.notify({
        type: 'negative',
        message: error.response?.data?.detail || 'Failed to delete product',
        position: 'top'
      });
    } finally {
      deletingId.value = null;
    }
  });
};

const clearForm = () => {
  productForm.value = {
    product_code: '',
    product_name: '',
    quantity: 1,
    unit_price: null,
    notes: ''
  };
  selectedProduct.value = null;
  productSearchQuery.value = '';
  filteredProductOptions.value = allProducts.value.slice(0, 50);
};

onMounted(async () => {
  await Promise.all([
    loadPatientInfo(),
    loadInventoryDebits(),
    loadProducts()
  ]);
});
</script>

<style scoped>
.glass-card {
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(10px);
}

.glass-text {
  color: rgba(255, 255, 255, 0.9);
}
</style>

