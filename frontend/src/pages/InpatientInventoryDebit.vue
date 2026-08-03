<template>
  <q-page class="hms-page">
    <HmsPageHeader
      title="Inventory debit"
      subtitle="Record ward products used for this inpatient encounter."
    >
      <template #actions>
        <HmsButton variant="secondary" size="sm" @click="$router.back()">Back</HmsButton>
      </template>
    </HmsPageHeader>

    <div v-if="patientInfo" class="ipd-patient-hero">
      <div class="ipd-hero-main">
        <div class="ipd-hero-avatar">{{ iidPatientInitials(patientInfo) }}</div>
        <div>
          <h1 class="ipd-hero-name">{{ patientInfo.patient_name }}</h1>
          <div class="ipd-hero-meta">
            <span class="mono">{{ patientInfo.card_number }}</span>
            <span class="sep">·</span>
            <span>{{ patientInfo.ward || '—' }}</span>
            <span class="sep">·</span>
            <span>{{ inventoryDebits.length }} products used</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Ward Stock -->
    <section v-if="patientInfo?.ward" class="am-panel">
      <div class="am-panel-head">
        <h2 class="hms-section-title">Ward Stock — {{ patientInfo.ward }}</h2>
        <HmsButton variant="secondary" size="sm" :loading="stockLoading" @click="loadWardStock">
          Refresh
        </HmsButton>
      </div>
      <p class="am-panel-sub">
        Available items in this ward. Select an item to pre-fill the form below, or search by name or code.
      </p>

      <q-banner
        v-if="!stockLoading && stockRows.length === 0"
        rounded
        class="bg-grey-8 text-white q-mb-md"
      >
        No stock is recorded for this ward yet. Request items from pharmacy via a requisition.
      </q-banner>

      <template v-else>
        <q-input
          v-model="stockFilter"
          dense
          filled
          clearable
          label="Search by name or code"
          class="q-mb-sm"
        >
          <template v-slot:prepend>
            <q-icon name="search" />
          </template>
        </q-input>
        <q-linear-progress v-if="stockLoading" indeterminate class="q-mb-sm" />
        <q-table
          v-else
          flat
          bordered
          dense
          :rows="filteredStockRows"
          :columns="stockColumns"
          row-key="product_code"
          :rows-per-page-options="[10, 15, 25]"
          :pagination="{ rowsPerPage: 10 }"
          class="stock-table"
        >
          <template v-slot:body-cell-quantity="props">
            <q-td :props="props">
              <span :class="props.row.quantity <= 0 ? 'text-negative text-weight-bold' : ''">
                {{ formatQty(props.row.quantity) }}
              </span>
              <q-badge
                v-if="props.row.quantity <= 0"
                color="negative"
                label="Out of stock"
                class="q-ml-sm"
              />
            </q-td>
          </template>
          <template v-slot:body-cell-actions="props">
            <q-td :props="props">
              <q-btn
                flat
                dense
                no-caps
                color="primary"
                label="Use"
                @click="selectStockRow(props.row)"
              />
            </q-td>
          </template>
        </q-table>
      </template>
    </section>

    <!-- Add Product Form -->
    <section class="am-panel">
      <div class="am-panel-head">
        <h2 class="hms-section-title">Add Product Used</h2>
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
          <HmsButton
            variant="primary"
            :loading="adding"
            :disabled="!productForm.product_code || !productForm.product_name || !productForm.quantity"
            @click="addProduct"
          >
            Add Product
          </HmsButton>
          <HmsButton variant="secondary" @click="clearForm">
            Clear
          </HmsButton>
        </div>
      </div>
    </section>

    <!-- Products Used Table -->
    <section class="am-panel">
      <div class="am-panel-head">
        <h2 class="hms-section-title">Products Used ({{ inventoryDebits.length }})</h2>
        <HmsButton variant="secondary" size="sm" :loading="loading" @click="loadInventoryDebits">
          Refresh
        </HmsButton>
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
    </section>
  </q-page>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useQuasar } from 'quasar';
import HmsPageHeader from '../components/ui/HmsPageHeader.vue';
import HmsButton from '../components/ui/HmsButton.vue';
import { consultationAPI, priceListAPI, companionVisitsAPI } from '../services/api';

const route = useRoute();
const router = useRouter();
const $q = useQuasar();

const wardAdmissionId = computed(() => parseInt(route.params.id));
const encounterId = computed(() => route.query.encounter_id ? parseInt(route.query.encounter_id) : null);

const patientInfo = ref(null);

const iidPatientInitials = (info) => {
  if (!info?.patient_name) return '?';
  const parts = String(info.patient_name).trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return '?';
  if (parts.length === 1) return parts[0].charAt(0).toUpperCase();
  return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase();
};
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

const stockRows = ref([]);
const stockLoading = ref(false);
const stockFilter = ref('');
const pickedAvailability = ref(null);

const filteredStockRows = computed(() => {
  const q = (stockFilter.value || '').trim().toLowerCase();
  if (!q) return stockRows.value;
  return stockRows.value.filter(
    (r) =>
      (r.product_name || '').toLowerCase().includes(q) ||
      (r.product_code || '').toLowerCase().includes(q)
  );
});

const stockColumns = [
  { name: 'product_name', label: 'Product Name', field: 'product_name', align: 'left', sortable: true },
  { name: 'product_code', label: 'Code', field: 'product_code', align: 'left', sortable: true },
  { name: 'quantity', label: 'Available Stock', field: 'quantity', align: 'right', sortable: true },
  { name: 'actions', label: '', field: 'product_code', align: 'right' }
];

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

const formatQty = (q) => {
  if (q == null || !Number.isFinite(Number(q))) return '—';
  const n = Number(q);
  return n % 1 === 0 ? String(n) : n.toFixed(2);
};

const loadWardStock = async () => {
  const ward = patientInfo.value?.ward;
  if (!ward || ward === 'N/A') {
    stockRows.value = [];
    return;
  }

  stockLoading.value = true;
  try {
    const res = await companionVisitsAPI.getDepartmentStock(ward);
    stockRows.value = res.data || [];
  } catch (error) {
    console.error('Error loading ward stock:', error);
    stockRows.value = [];
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to load ward stock',
      position: 'top'
    });
  } finally {
    stockLoading.value = false;
  }
};

const selectStockRow = (row) => {
  if (!row) return;
  productForm.value.product_code = row.product_code || '';
  productForm.value.product_name = row.product_name || '';
  pickedAvailability.value = row.quantity != null ? Number(row.quantity) : null;

  const match = allProducts.value.find((p) => p.value.code === row.product_code);
  if (match) {
    selectedProduct.value = match.value;
    if (match.value.price && match.value.price > 0) {
      productForm.value.unit_price = match.value.price;
    }
  } else {
    selectedProduct.value = null;
  }

  if (pickedAvailability.value != null && pickedAvailability.value <= 0) {
    $q.notify({
      type: 'warning',
      message: 'This item is out of stock. Request stock via a Pharmacy/Main Stores requisition before debiting.',
      position: 'top',
      timeout: 5000
    });
  }
};

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
      await loadWardStock();
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
    await Promise.all([loadInventoryDebits(), loadWardStock()]);
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
      await Promise.all([loadInventoryDebits(), loadWardStock()]);
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
  pickedAvailability.value = null;
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
.am-panel {
  padding: 1.05rem 1.15rem;
  border-radius: var(--hms-radius-xl);
  background: var(--hms-panel-bg);
  border: 1px solid var(--hms-border);
  box-shadow: var(--hms-shadow-md);
  margin-bottom: 0.95rem;
}
.am-panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  flex-wrap: wrap;
  margin-bottom: 0.85rem;
}
.am-panel-sub {
  margin: 0 0 0.85rem;
  font-size: var(--hms-text-sm);
  color: var(--hms-text-muted);
}

.ipd-patient-hero {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.85rem;
  margin-bottom: 0.95rem;
  padding: 1rem 1.15rem;
  border-radius: var(--hms-radius-xl);
  background: var(--hms-panel-bg);
  border: 1px solid var(--hms-border);
  box-shadow: var(--hms-shadow-md);
  position: sticky;
  top: 0.55rem;
  z-index: 6;
}
.ipd-hero-main { display: flex; align-items: center; gap: 0.85rem; min-width: 0; }
.ipd-hero-avatar {
  width: 3rem; height: 3rem; border-radius: 999px;
  display: grid; place-items: center;
  font-weight: 700; font-size: 0.85rem;
  color: var(--hms-accent); background: var(--hms-accent-muted);
  flex-shrink: 0;
}
.ipd-hero-name {
  margin: 0;
  font-size: clamp(1.15rem, 2vw, 1.45rem);
  font-weight: 750;
  color: var(--hms-text-primary);
  letter-spacing: -0.02em;
}
.ipd-hero-meta {
  margin-top: 0.2rem;
  font-size: var(--hms-text-sm);
  color: var(--hms-text-secondary);
  display: flex; flex-wrap: wrap; align-items: center; gap: 0.15rem;
}
.ipd-hero-meta .sep { margin: 0 0.3rem; opacity: 0.4; }
.ipd-hero-meta .mono,
.mono { font-variant-numeric: tabular-nums; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }
.ipd-hero-actions { display: flex; flex-wrap: wrap; gap: 0.45rem; align-items: center; }
.balance-pill {
  display: inline-flex; flex-direction: column; align-items: flex-end;
  padding: 0.35rem 0.7rem; border-radius: var(--hms-radius-lg);
  border: 1px solid var(--hms-border); background: var(--hms-surface);
  cursor: pointer; font: inherit;
}
.balance-pill .balance-label {
  font-size: 0.62rem; font-weight: 700; letter-spacing: 0.05em;
  text-transform: uppercase; color: var(--hms-text-muted);
}
.balance-pill .balance-value { font-weight: 700; font-variant-numeric: tabular-nums; }
.balance-pill.due .balance-value { color: var(--hms-critical); }
.balance-pill.ok .balance-value { color: var(--hms-success); }
.balance-pill.neutral .balance-value { color: var(--hms-text-secondary); }
@media (max-width: 720px) {
  .ipd-patient-hero { position: static; }
}
:deep(.glass-card) {
  border-radius: var(--hms-radius-xl) !important;
  border: 1px solid var(--hms-border) !important;
  box-shadow: var(--hms-shadow-md) !important;
  background: var(--hms-panel-bg) !important;
}
:deep(.text-h6.glass-text),
:deep(.glass-text.text-h6) {
  font-size: var(--hms-text-lg) !important;
  font-weight: 700 !important;
  color: var(--hms-text-primary) !important;
}


.glass-card {
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(10px);
}

.glass-text {
  color: rgba(255, 255, 255, 0.9);
}
</style>

