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
      <div class="text-h4 text-weight-bold glass-text">Requisitions</div>
    </div>
    
    <q-banner class="glass-card q-pa-md q-mb-md">
      <template v-slot:avatar>
        <q-icon name="info" color="primary" />
      </template>
      <div v-if="isWardStaff">
        Request items from stores. Your requisitions must be approved by Pharmacy Head and fulfilled by Store Manager or Pharmacy Head before items are added to your department/unit stock.
      </div>
      <div v-else-if="isPharmacyHead">
        Review and approve/reject requisition requests from departments/units. You can also fulfill approved requisitions.
      </div>
      <div v-else-if="isStoreManager">
        Fulfill approved requisitions for your assigned stores. You can partially fulfill items if needed.
      </div>
    </q-banner>

    <!-- Action Buttons -->
    <div class="row q-gutter-md q-mb-md items-center">
      <q-btn
        v-if="isWardStaff || isAdmin"
        color="primary"
        icon="add"
        label="Create Requisition"
        @click="$router.push({ name: 'CreateRequisition' })"
        size="md"
        class="q-mr-sm"
      />
      <q-btn
        color="secondary"
        icon="inventory_2"
        label="View Department/Unit Stock"
        @click="$router.push({ name: 'WardStock' })"
        size="md"
      />
      <q-space />
      <q-btn
        flat
        icon="refresh"
        label="Refresh"
        @click="loadRequisitions"
        :loading="loading"
        size="md"
      />
    </div>

    <!-- Filters -->
    <q-card class="q-mb-md glass-card" flat>
      <q-card-section>
        <div class="row q-gutter-md">
          <q-select
            v-model="filters.department_id"
            :options="wardOptions"
            label="Department/Unit"
            filled
            clearable
            emit-value
            map-options
            class="col-12 col-md-2"
            @update:model-value="loadRequisitions"
          />
          <q-select
            v-model="filters.store_id"
            :options="storeOptions"
            label="Store"
            filled
            clearable
            emit-value
            map-options
            class="col-12 col-md-2"
            @update:model-value="loadRequisitions"
            :disable="isStoreManagerOrDeptHead && userStoreIds.length > 0"
          >
            <template v-slot:prepend>
              <q-icon name="store" />
            </template>
          </q-select>
          <q-select
            v-model="filters.status"
            :options="statusOptions"
            label="Status"
            filled
            clearable
            class="col-12 col-md-2"
            @update:model-value="loadRequisitions"
          />
          <q-input
            v-model="filters.start_date"
            label="Start Date"
            filled
            type="date"
            clearable
            class="col-12 col-md-2"
            @update:model-value="loadRequisitions"
          />
          <q-input
            v-model="filters.end_date"
            label="End Date"
            filled
            type="date"
            clearable
            class="col-12 col-md-2"
            @update:model-value="loadRequisitions"
          />
          <div class="col-12 col-md-4 flex items-center">
            <q-btn
              flat
              icon="clear"
              label="Clear Filters"
              @click="clearFilters"
              class="q-mr-sm"
            />
          </div>
        </div>
      </q-card-section>
    </q-card>

    <!-- Requisitions Table -->
    <q-card class="glass-card" flat>
      <q-card-section>
        <div class="text-h6 glass-text q-mb-md">
          Requisitions
          <q-badge color="primary" class="q-ml-sm">{{ requisitions.length }}</q-badge>
        </div>

        <q-table
          :rows="requisitions"
          :columns="columns"
          :loading="loading"
          row-key="id"
          flat
          :pagination="{ rowsPerPage: 20 }"
        >
          <template v-slot:body-cell-status="props">
            <q-td :props="props">
              <q-badge :color="getStatusColor(props.value)" :label="props.value" />
            </q-td>
          </template>

          <template v-slot:body-cell-actions="props">
            <q-td :props="props">
              <q-btn
                flat
                dense
                round
                icon="visibility"
                @click="viewRequisition(props.row)"
                size="sm"
              >
                <q-tooltip>View Details</q-tooltip>
              </q-btn>
              <q-btn
                v-if="(isWardStaff && props.row.status === 'pending' && props.row.requested_by === currentUserId) || (isAdmin && props.row.status === 'pending')"
                flat
                dense
                round
                icon="edit"
                color="primary"
                @click="openEditDialog(props.row)"
                size="sm"
              >
                <q-tooltip>Edit</q-tooltip>
              </q-btn>
              <q-btn
                v-if="isPharmacyHead && props.row.status === 'pending'"
                flat
                dense
                round
                icon="check"
                color="positive"
                @click="openApproveDialog(props.row)"
                size="sm"
              >
                <q-tooltip>Approve</q-tooltip>
              </q-btn>
              <q-btn
                v-if="isPharmacyHead && props.row.status === 'pending'"
                flat
                dense
                round
                icon="close"
                color="negative"
                @click="openRejectDialog(props.row)"
                size="sm"
              >
                <q-tooltip>Reject</q-tooltip>
              </q-btn>
              <q-btn
                v-if="isPharmacyHead && (props.row.status === 'approved' || props.row.status === 'partially_fulfilled')"
                flat
                dense
                round
                icon="undo"
                color="warning"
                @click="revertApproval(props.row.id)"
                size="sm"
              >
                <q-tooltip>Revert Approval</q-tooltip>
              </q-btn>
              <q-btn
                v-if="(isStoreManager || isPharmacyHead) && (props.row.status === 'approved' || props.row.status === 'partially_fulfilled')"
                flat
                dense
                round
                icon="inventory"
                color="primary"
                @click="openFulfillDialog(props.row)"
                size="sm"
              >
                <q-tooltip>Fulfill</q-tooltip>
              </q-btn>
              <!-- Revert Fulfillment: Only show for fulfilled or partially_fulfilled, NOT for approved -->
              <q-btn
                v-if="(isStoreManager || isPharmacyHead || isAdmin) && (props.row.status === 'fulfilled' || props.row.status === 'partially_fulfilled')"
                flat
                dense
                round
                icon="undo"
                color="warning"
                @click="revertFulfillment(props.row.id)"
                size="sm"
              >
                <q-tooltip>Revert Fulfillment</q-tooltip>
              </q-btn>
              <q-btn
                v-if="(isWardStaff && props.row.status === 'pending' && props.row.requested_by === currentUserId) || (isAdmin && props.row.status === 'pending')"
                flat
                dense
                round
                icon="cancel"
                color="orange"
                @click="cancelRequisition(props.row.id)"
                size="sm"
              >
                <q-tooltip>Cancel</q-tooltip>
              </q-btn>
            </q-td>
          </template>

          <template v-slot:no-data>
            <div class="full-width row flex-center text-grey-6 q-gutter-sm">
              <q-icon name="inbox" size="2em" />
              <span>No requisitions found</span>
            </div>
          </template>
        </q-table>
      </q-card-section>
    </q-card>

    <!-- Create Requisition Dialog -->
    <q-dialog v-model="showCreateDialog" persistent>
      <q-card style="min-width: 600px">
        <q-card-section>
          <div class="text-h6">Create Requisition</div>
        </q-card-section>

        <q-card-section>
          <q-input
            v-model="newRequisition.ward"
            label="Department/Unit"
            filled
            readonly
            class="q-mb-md"
          />
          <q-input
            v-model="newRequisition.notes"
            label="Notes (Optional)"
            filled
            type="textarea"
            rows="3"
            class="q-mb-md"
          />

          <div class="text-subtitle2 q-mb-sm">Items</div>
          <div v-for="(item, index) in newRequisition.items" :key="index" class="q-mb-md">
            <q-card>
              <q-card-section>
                <div class="row q-gutter-md">
                  <q-input
                    v-model="item.product_code"
                    label="Product Code"
                    filled
                    class="col-12 col-md-4"
                    readonly
                  />
                  <q-input
                    v-model="item.product_name"
                    label="Product Name"
                    filled
                    class="col-12 col-md-4"
                    readonly
                  />
                  <q-input
                    v-model.number="item.requested_quantity"
                    label="Quantity"
                    filled
                    type="number"
                    min="0.01"
                    step="0.01"
                    class="col-12 col-md-3"
                  />
                  <q-btn
                    flat
                    round
                    icon="delete"
                    color="negative"
                    @click="removeItem(index)"
                    class="col-12 col-md-1"
                  />
                </div>
              </q-card-section>
            </q-card>
          </div>

          <q-btn
            color="primary"
            icon="add"
            label="Add Item"
            @click="openAddItemDialog"
            class="q-mb-md"
          />
        </q-card-section>

        <q-card-actions align="right">
          <q-btn flat label="Cancel" v-close-popup />
          <q-btn color="primary" label="Create" @click="createRequisition" :loading="creating" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Add Item Dialog -->
    <q-dialog v-model="showAddItemDialog">
      <q-card style="min-width: 500px">
        <q-card-section>
          <div class="text-h6">Add Item</div>
        </q-card-section>

        <q-card-section>
          <q-input
            v-model="itemSearch"
            label="Search Product"
            filled
            @input="searchProducts"
            class="q-mb-md"
          />
          <q-list v-if="productResults.length > 0">
            <q-item
              v-for="product in productResults"
              :key="product.code"
              clickable
              @click="selectProduct(product)"
            >
              <q-item-section>
                <q-item-label>{{ product.name }}</q-item-label>
                <q-item-label caption>{{ product.code }}</q-item-label>
              </q-item-section>
            </q-item>
          </q-list>
        </q-card-section>

        <q-card-actions align="right">
          <q-btn flat label="Cancel" v-close-popup />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- View Requisition Dialog -->
    <q-dialog v-model="showViewDialog" style="min-width: 800px">
      <q-card>
        <q-card-section>
          <div class="text-h6">Requisition Details</div>
        </q-card-section>

        <q-card-section v-if="selectedRequisition">
          <div class="q-gutter-md">
            <div><strong>Requisition Number:</strong> {{ selectedRequisition.requisition_number }}</div>
            <div><strong>Department/Unit:</strong> {{ selectedRequisition.ward }}</div>
            <div><strong>Status:</strong> <q-badge :color="getStatusColor(selectedRequisition.status)" :label="selectedRequisition.status" /></div>
            <div><strong>Requested By:</strong> {{ selectedRequisition.requested_by_name }}</div>
            <div v-if="selectedRequisition.approved_by_name"><strong>Approved By:</strong> {{ selectedRequisition.approved_by_name }}</div>
            <div v-if="selectedRequisition.fulfilled_by_name"><strong>Fulfilled By:</strong> {{ selectedRequisition.fulfilled_by_name }}</div>
            <div v-if="selectedRequisition.rejection_reason"><strong>Rejection Reason:</strong> {{ selectedRequisition.rejection_reason }}</div>

            <div class="text-subtitle2 q-mt-md">Items</div>
            <q-table
              :rows="selectedRequisition.items || []"
              :columns="itemColumns"
              flat
            >
              <template v-slot:body-cell-fulfillment="props">
                <q-td :props="props">
                  <div>
                    {{ props.row.fulfilled_quantity }} / 
                    {{ props.row.approved_quantity !== null && props.row.approved_quantity !== undefined ? props.row.approved_quantity : props.row.requested_quantity }}
                    <q-badge v-if="props.row.approved_quantity !== null && props.row.approved_quantity !== undefined && props.row.approved_quantity < props.row.requested_quantity" 
                             color="warning" label="Partial Approval" class="q-ml-sm" />
                  </div>
                  <q-linear-progress
                    :value="props.row.fulfilled_quantity / (props.row.approved_quantity !== null && props.row.approved_quantity !== undefined ? props.row.approved_quantity : props.row.requested_quantity)"
                    :color="props.row.fulfilled_quantity >= (props.row.approved_quantity !== null && props.row.approved_quantity !== undefined ? props.row.approved_quantity : props.row.requested_quantity) ? 'positive' : 'warning'"
                  />
                </q-td>
              </template>
            </q-table>

            <div class="text-subtitle2 q-mt-md">History</div>
            <q-timeline v-if="selectedRequisition.history && selectedRequisition.history.length > 0">
              <q-timeline-entry
                v-for="(entry, index) in selectedRequisition.history"
                :key="index"
                :title="entry.action"
                :subtitle="entry.performed_by_name"
                :caption="formatDateTime(entry.timestamp)"
              >
                <div>{{ entry.notes }}</div>
              </q-timeline-entry>
            </q-timeline>
          </div>
        </q-card-section>

        <q-card-actions align="right">
          <q-btn flat label="Close" v-close-popup />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Reject Dialog -->
    <q-dialog v-model="showRejectDialog">
      <q-card style="min-width: 400px">
        <q-card-section>
          <div class="text-h6">Reject Requisition</div>
        </q-card-section>

        <q-card-section>
          <q-input
            v-model="rejectionReason"
            label="Rejection Reason (Optional)"
            filled
            type="textarea"
            rows="3"
          />
        </q-card-section>

        <q-card-actions align="right">
          <q-btn flat label="Cancel" v-close-popup />
          <q-btn color="negative" label="Reject" @click="rejectRequisition" :loading="processing" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Approve Dialog -->
    <q-dialog v-model="showApproveDialog" persistent style="min-width: 800px">
      <q-card>
        <q-card-section>
          <div class="text-h6">Approve Requisition</div>
        </q-card-section>

        <q-card-section v-if="selectedRequisition">
          <div class="text-caption q-mb-md">
            You can approve partial quantities for each item. Leave blank or set to requested quantity for full approval.
          </div>
          <div v-for="item in selectedRequisition.items" :key="item.id" class="q-mb-md">
            <q-card>
              <q-card-section>
                <div class="text-subtitle2">{{ item.product_name }}</div>
                <div class="text-caption">Requested: {{ item.requested_quantity }}</div>
                <q-input
                  v-model.number="approvalItems[item.id]"
                  label="Quantity to Approve"
                  filled
                  type="number"
                  :min="0"
                  :max="item.requested_quantity"
                  step="0.01"
                  class="q-mt-md"
                  hint="Leave blank or set to requested quantity for full approval"
                />
              </q-card-section>
            </q-card>
          </div>
          <q-input
            v-model="approvalNotes"
            label="Approval Notes (Optional)"
            filled
            type="textarea"
            rows="3"
          />
        </q-card-section>

        <q-card-actions align="right">
          <q-btn flat label="Cancel" v-close-popup />
          <q-btn color="positive" label="Approve" @click="approveRequisition" :loading="processing" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Edit Dialog -->
    <q-dialog v-model="showEditDialog" persistent style="min-width: 800px">
      <q-card>
        <q-card-section>
          <div class="text-h6">Edit Requisition</div>
        </q-card-section>

        <q-card-section v-if="editingRequisition">
          <q-select
            v-model="editingRequisition.department_id"
            :options="wardOptions"
            label="Department/Unit"
            filled
            emit-value
            map-options
            class="q-mb-md"
            :disable="!isAdmin"
          />
          <q-select
            v-model="editingRequisition.store_id"
            :options="storeOptions"
            label="Store"
            filled
            emit-value
            map-options
            class="q-mb-md"
            :disable="!isAdmin"
          />
          <q-input
            v-model="editingRequisition.notes"
            label="Notes"
            filled
            type="textarea"
            rows="3"
            class="q-mb-md"
          />
          <div class="text-subtitle2 q-mb-md">Items</div>
          
          <!-- Product Search Select -->
          <q-select
            v-model="selectedEditProduct"
            :options="filteredEditProductOptions"
            filled
            use-input
            input-debounce="300"
            label="Search Product to Add"
            hint="Type to search for products - Select to add"
            @filter="filterEditProducts"
            @update:model-value="onEditProductSelected"
            option-label="label"
            option-value="value"
            emit-value
            map-options
            clearable
            :loading="loadingEditProducts"
            class="q-mb-md"
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
          
          <div v-for="(item, index) in editingRequisition.items" :key="index" class="q-mb-md">
            <q-card>
              <q-card-section>
                <div class="row items-center q-gutter-md">
                  <div class="col">
                    <div class="text-subtitle2">{{ item.product_name }}</div>
                    <div class="text-caption">{{ item.product_code }}</div>
                  </div>
                  <q-input
                    v-model.number="item.requested_quantity"
                    label="Quantity"
                    filled
                    type="number"
                    :min="0"
                    step="0.01"
                    class="col-3"
                  />
                  <q-btn
                    flat
                    round
                    icon="delete"
                    color="negative"
                    @click="removeEditItem(index)"
                  />
                </div>
              </q-card-section>
            </q-card>
          </div>
        </q-card-section>

        <q-card-actions align="right">
          <q-btn flat label="Cancel" v-close-popup />
          <q-btn color="primary" label="Update" @click="updateRequisition" :loading="processing" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Fulfill Dialog -->
    <q-dialog v-model="showFulfillDialog" persistent style="min-width: 800px">
      <q-card>
        <q-card-section>
          <div class="text-h6">Fulfill Requisition</div>
        </q-card-section>

        <q-card-section v-if="selectedRequisition">
          <div v-for="item in selectedRequisition.items" :key="item.id" class="q-mb-md">
            <q-card>
              <q-card-section>
                <div class="text-subtitle2">{{ item.product_name }}</div>
                <div class="text-caption">Requested: {{ item.requested_quantity }}</div>
                <div class="text-caption" v-if="item.approved_quantity !== null && item.approved_quantity !== undefined">
                  Approved: {{ item.approved_quantity }} <q-badge color="positive" label="Partial" v-if="item.approved_quantity < item.requested_quantity" />
                </div>
                <div class="text-caption">Fulfilled: {{ item.fulfilled_quantity }}</div>
                <div class="text-caption">Remaining: {{ (item.approved_quantity !== null && item.approved_quantity !== undefined ? item.approved_quantity : item.requested_quantity) - item.fulfilled_quantity }}</div>
                <q-input
                  v-model.number="fulfillmentItems[item.id]"
                  label="Quantity to Fulfill"
                  filled
                  type="number"
                  :min="0"
                  :max="(item.approved_quantity !== null && item.approved_quantity !== undefined ? item.approved_quantity : item.requested_quantity) - item.fulfilled_quantity"
                  step="0.01"
                  class="q-mt-md"
                />
              </q-card-section>
            </q-card>
          </div>
          <q-input
            v-model="fulfillmentNotes"
            label="Notes (Optional)"
            filled
            type="textarea"
            rows="3"
          />
        </q-card-section>

        <q-card-actions align="right">
          <q-btn flat label="Cancel" v-close-popup />
          <q-btn color="primary" label="Fulfill" @click="fulfillRequisition" :loading="processing" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script>
import { ref, computed, onMounted, watch } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '../stores/auth';
import { useQuasar, Notify } from 'quasar';
import { pharmacyRequisitionsAPI, priceListAPI, wardsAPI, storesAPI, storeStaffAssignmentsAPI } from '../services/api';

export default {
  name: 'PharmacyRequisitions',
  setup() {
    const router = useRouter();
    const authStore = useAuthStore();
    const $q = useQuasar();
    
    const requisitions = ref([]);
    const loading = ref(false);
    const creating = ref(false);
    const processing = ref(false);
    const showCreateDialog = ref(false);
    const showAddItemDialog = ref(false);
    const showViewDialog = ref(false);
    const showRejectDialog = ref(false);
    const showApproveDialog = ref(false);
    const showEditDialog = ref(false);
    const showFulfillDialog = ref(false);
    const selectedRequisition = ref(null);
    const editingRequisition = ref(null);
    const rejectionReason = ref('');
    const approvalNotes = ref('');
    const approvalItems = ref({});
    const fulfillmentNotes = ref('');
    const fulfillmentItems = ref({});
    const itemSearch = ref('');
    const productResults = ref([]);
    const selectedEditProduct = ref(null);
    const allEditProducts = ref([]);
    const filteredEditProductOptions = ref([]);
    const loadingEditProducts = ref(false);

    const filters = ref({
      department_id: null,
      store_id: null,
      status: null,
      start_date: null,
      end_date: null,
    });

    const newRequisition = ref({
      department_id: (authStore.userRole && authStore.userRole !== 'Admin') ? authStore.userRole : '',
      notes: '',
      items: [],
    });

    const isWardStaff = computed(() => {
      const role = authStore.userRole;
      return role && ['Nurse', 'Doctor', 'PA', 'Admin'].includes(role);
    });

    const isPharmacyHead = computed(() => {
      const role = authStore.userRole;
      return role && ['Pharmacy Head', 'Admin'].includes(role);
    });

    const isStoreManager = computed(() => {
      const role = authStore.userRole;
      return role && ['Store Manager', 'Admin'].includes(role);
    });

    const isStoreManagerOrDeptHead = computed(() => {
      const role = authStore.userRole;
      return role && ['Store Manager', 'Department Head'].includes(role);
    });

    // Get current user ID safely
    const currentUserId = computed(() => {
      return authStore.user?.id || null;
    });

    // Check if user is Admin safely
    const isAdmin = computed(() => {
      return authStore.userRole && authStore.userRole === 'Admin';
    });

    const wardOptions = ref([]);
    const storeOptions = ref([]);
    const userStoreIds = ref([]);
    const statusOptions = ref([
      { label: 'Pending', value: 'pending' },
      { label: 'Approved', value: 'approved' },
      { label: 'Rejected', value: 'rejected' },
      { label: 'Partially Fulfilled', value: 'partially_fulfilled' },
      { label: 'Fulfilled', value: 'fulfilled' },
    ]);

    const columns = [
      { name: 'requisition_number', label: 'Requisition #', field: 'requisition_number', align: 'left', sortable: true },
      { name: 'ward', label: 'Department/Unit', field: 'ward', align: 'left', sortable: true },
      { name: 'status', label: 'Status', field: 'status', align: 'left', sortable: true },
      { name: 'requested_by_name', label: 'Requested By', field: 'requested_by_name', align: 'left', sortable: true },
      { name: 'created_at', label: 'Created', field: 'created_at', align: 'left', sortable: true },
      { name: 'actions', label: 'Actions', align: 'center' },
    ];

    const itemColumns = [
      { name: 'product_name', label: 'Product', field: 'product_name', align: 'left' },
      { name: 'product_code', label: 'Code', field: 'product_code', align: 'left' },
      { name: 'requested_quantity', label: 'Requested', field: 'requested_quantity', align: 'left' },
      { name: 'fulfillment', label: 'Fulfilled', align: 'left' },
    ];

    // Helper function to format date for API (YYYY-MM-DD)
    const formatDateForAPI = (dateString) => {
      if (!dateString) return null;
      // If it's already in YYYY-MM-DD format, return as is
      if (typeof dateString === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(dateString)) {
        return dateString;
      }
      // Otherwise, try to parse and format
      const date = new Date(dateString);
      if (isNaN(date.getTime())) return null;
      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const day = String(date.getDate()).padStart(2, '0');
      return `${year}-${month}-${day}`;
    };

    const clearFilters = () => {
      filters.value = {
        department_id: null,
        store_id: isStoreManagerOrDeptHead.value && userStoreIds.value.length > 0 ? userStoreIds.value[0] : null,
        status: null,
        start_date: null,
        end_date: null,
      };
      loadRequisitions();
    };

    const loadRequisitions = async () => {
      loading.value = true;
      try {
        // Build filter object
        const apiFilters = {
          ...filters.value,
          start_date: filters.value.start_date ? formatDateForAPI(filters.value.start_date) : null,
          end_date: filters.value.end_date ? formatDateForAPI(filters.value.end_date) : null,
        };
        
        // Auto-filter by store for Store Managers/Department Heads
        // The filter is already set in loadUserStoreAssignments, but ensure it's applied
        if (isStoreManagerOrDeptHead.value && userStoreIds.value.length > 0) {
          // Always use the filter value (which is auto-set to first assigned store)
          if (!apiFilters.store_id) {
            apiFilters.store_id = filters.value.store_id || userStoreIds.value[0];
          }
        }
        
        const response = await pharmacyRequisitionsAPI.getAll(apiFilters);
        requisitions.value = response.data || [];
      } catch (error) {
        console.error('Error loading requisitions:', error);
        Notify.create({
          type: 'negative',
          message: error.response?.data?.detail || 'Failed to load requisitions',
          position: 'top',
        });
      } finally {
        loading.value = false;
      }
    };

    const openCreateDialog = () => {
      newRequisition.value = {
        department_id: (authStore.userRole && authStore.userRole !== 'Admin') ? authStore.userRole : '',
        notes: '',
        items: [],
      };
      showCreateDialog.value = true;
    };

    const openAddItemDialog = () => {
      itemSearch.value = '';
      productResults.value = [];
      showAddItemDialog.value = true;
    };

    const searchProducts = async (val) => {
      if (!val || val.length < 2) {
        productResults.value = [];
        return;
      }
      try {
        const response = await priceListAPI.search(val, 'Pharmacy', 'product');
        productResults.value = response.data || [];
      } catch (error) {
        console.error('Error searching products:', error);
      }
    };

    const selectProduct = (product) => {
      // Check if we're in edit mode
      const targetItems = showEditDialog.value && editingRequisition.value 
        ? editingRequisition.value.items 
        : newRequisition.value.items;
      
      // Check if product is already in the list
      const existingItem = targetItems.find(
        item => item.product_code === product.code
      );
      
      if (existingItem) {
        Notify.create({
          type: 'warning',
          message: 'This product is already in the requisition',
          position: 'top',
        });
        return;
      }
      
      targetItems.push({
        product_code: product.code,
        product_name: product.name,
        requested_quantity: 1,
        notes: '',
      });
      
      showAddItemDialog.value = false;
      itemSearch.value = '';
      productResults.value = [];
      
      Notify.create({
        type: 'positive',
        message: 'Item added to requisition',
        position: 'top',
      });
    };

    const removeItem = (index) => {
      newRequisition.value.items.splice(index, 1);
    };

    const createRequisition = async () => {
      if (newRequisition.value.items.length === 0) {
        Notify.create({
          type: 'negative',
          message: 'Please add at least one item',
          position: 'top',
        });
        return;
      }

      creating.value = true;
      try {
        await pharmacyRequisitionsAPI.create(newRequisition.value);
        Notify.create({
          type: 'positive',
          message: 'Requisition created successfully',
          position: 'top',
        });
        showCreateDialog.value = false;
        loadRequisitions();
      } catch (error) {
        console.error('Error creating requisition:', error);
        const errorDetail = error.response?.data?.detail || 'Failed to create requisition';
        const errorItems = error.response?.data?.detail_items;
        
        if (errorItems && errorItems.length > 0) {
          // Show detailed error for duplicate requests
          let message = errorDetail + '\n\nPending items:\n';
          errorItems.forEach(item => {
            message += `• ${item.product_name} - ${item.requisition_number} (${item.status})\n`;
          });
          Notify.create({
            type: 'negative',
            message: message,
            position: 'top',
            timeout: 10000,
            multiLine: true,
          });
        } else {
          Notify.create({
            type: 'negative',
            message: errorDetail,
            position: 'top',
          });
        }
      } finally {
        creating.value = false;
      }
    };

    const viewRequisition = async (requisition) => {
      try {
        const response = await pharmacyRequisitionsAPI.get(requisition.id);
        console.log('Requisition details response:', response);
        selectedRequisition.value = response.data;
        console.log('Selected requisition:', selectedRequisition.value);
        showViewDialog.value = true;
      } catch (error) {
        console.error('Error loading requisition:', error);
        Notify.create({
          type: 'negative',
          message: error.response?.data?.detail || 'Failed to load requisition details',
          position: 'top',
        });
      }
    };

    const openApproveDialog = async (requisition) => {
      try {
        const response = await pharmacyRequisitionsAPI.get(requisition.id);
        selectedRequisition.value = response.data;
        approvalItems.value = {};
        approvalNotes.value = '';
        // Initialize approval quantities to requested quantities (full approval by default)
        selectedRequisition.value.items.forEach(item => {
          approvalItems.value[item.id] = item.requested_quantity;
        });
        showApproveDialog.value = true;
      } catch (error) {
        console.error('Error loading requisition:', error);
        Notify.create({
          type: 'negative',
          message: 'Failed to load requisition details',
          position: 'top',
        });
      }
    };

    const approveRequisition = async () => {
      if (!selectedRequisition.value) return;
      
      processing.value = true;
      try {
        // Build items array with approved quantities
        const items = selectedRequisition.value.items
          .filter(item => approvalItems.value[item.id] !== undefined && approvalItems.value[item.id] > 0)
          .map(item => ({
            item_id: item.id,
            approved_quantity: approvalItems.value[item.id] || item.requested_quantity,
          }));
        
        await pharmacyRequisitionsAPI.approve(selectedRequisition.value.id, {
          items: items.length > 0 ? items : undefined, // If no items specified, approve all
          notes: approvalNotes.value,
        });
        Notify.create({
          type: 'positive',
          message: 'Requisition approved successfully',
          position: 'top',
        });
        showApproveDialog.value = false;
        loadRequisitions();
      } catch (error) {
        console.error('Error approving requisition:', error);
        Notify.create({
          type: 'negative',
          message: error.response?.data?.detail || 'Failed to approve requisition',
          position: 'top',
        });
      } finally {
        processing.value = false;
      }
    };

    const openEditDialog = async (requisition) => {
      try {
        const response = await pharmacyRequisitionsAPI.get(requisition.id);
        editingRequisition.value = {
          id: response.data.id,
          department_id: response.data.department_id,
          store_id: response.data.store_id,
          notes: response.data.notes || '',
          items: response.data.items.map(item => ({
            product_code: item.product_code,
            product_name: item.product_name,
            requested_quantity: item.requested_quantity,
            notes: item.notes || '',
          })),
        };
        selectedEditProduct.value = null;
        // Load products if not already loaded
        if (allEditProducts.value.length === 0) {
          loadEditProducts();
        }
        showEditDialog.value = true;
      } catch (error) {
        console.error('Error loading requisition:', error);
        Notify.create({
          type: 'negative',
          message: 'Failed to load requisition details',
          position: 'top',
        });
      }
    };

    const loadEditProducts = async () => {
      try {
        loadingEditProducts.value = true;
        const res = await priceListAPI.searchPriceItems(null, null, 'product');
        
        let productsData = res.data;
        if (!Array.isArray(productsData) && res.data?.data) {
          productsData = res.data.data;
        }
        
        if (productsData && Array.isArray(productsData)) {
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
                  fullItem: item
                }
              };
            });
          
          allEditProducts.value = mappedProducts;
          filteredEditProductOptions.value = allEditProducts.value.slice(0, 50);
        } else {
          allEditProducts.value = [];
          filteredEditProductOptions.value = [];
        }
      } catch (error) {
        console.error('Error loading products:', error);
        Notify.create({
          type: 'negative',
          message: error.response?.data?.detail || 'Failed to load products',
          position: 'top',
        });
        allEditProducts.value = [];
        filteredEditProductOptions.value = [];
      } finally {
        loadingEditProducts.value = false;
      }
    };

    const filterEditProducts = (val, update) => {
      if (val === '') {
        update(() => {
          filteredEditProductOptions.value = allEditProducts.value.slice(0, 50);
        });
        return;
      }

      update(() => {
        const needle = val.toLowerCase();
        filteredEditProductOptions.value = allEditProducts.value.filter(
          v => v.label.toLowerCase().indexOf(needle) > -1
        );
      });
    };

    const onEditProductSelected = (productValue) => {
      if (!productValue || !editingRequisition.value) return;
      
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
      const existingItem = editingRequisition.value.items.find(
        item => item.product_code === productCode
      );
      
      if (existingItem) {
        Notify.create({
          type: 'warning',
          message: 'This product is already in the requisition',
          position: 'top',
        });
        selectedEditProduct.value = null;
        return;
      }

      editingRequisition.value.items.push({
        product_code: productCode,
        product_name: productName,
        requested_quantity: 1,
        notes: '',
      });
      
      selectedEditProduct.value = null;
      
      Notify.create({
        type: 'positive',
        message: 'Item added to requisition',
        position: 'top',
      });
    };

    const removeEditItem = (index) => {
      editingRequisition.value.items.splice(index, 1);
    };

    const updateRequisition = async () => {
      if (!editingRequisition.value) return;
      
      processing.value = true;
      try {
        await pharmacyRequisitionsAPI.update(editingRequisition.value.id, {
          department_id: editingRequisition.value.department_id,
          store_id: editingRequisition.value.store_id,
          items: editingRequisition.value.items,
          notes: editingRequisition.value.notes,
        });
        Notify.create({
          type: 'positive',
          message: 'Requisition updated successfully',
          position: 'top',
        });
        showEditDialog.value = false;
        loadRequisitions();
      } catch (error) {
        console.error('Error updating requisition:', error);
        Notify.create({
          type: 'negative',
          message: error.response?.data?.detail || 'Failed to update requisition',
          position: 'top',
        });
      } finally {
        processing.value = false;
      }
    };

    const revertApproval = async (requisitionId) => {
      // Get requisition to check status
      const requisition = requisitions.value.find(r => r.id === requisitionId);
      const hasFulfillment = requisition && (requisition.status === 'partially_fulfilled' || requisition.status === 'fulfilled');
      
      const message = hasFulfillment
        ? 'Are you sure you want to revert the approval? Any remaining fulfillment will be automatically reverted first (only unused quantities will be returned). This will set the requisition back to pending so the requester can make changes.'
        : 'Are you sure you want to revert the approval? This will set the requisition back to pending so the requester can make changes.';
      
      $q.dialog({
        title: 'Revert Approval',
        message: message,
        cancel: true,
        persistent: true,
      }).onOk(async () => {
        processing.value = true;
        try {
          await pharmacyRequisitionsAPI.revertApproval(requisitionId);
          Notify.create({
            type: 'positive',
            message: 'Approval reverted successfully',
            position: 'top',
          });
          loadRequisitions();
        } catch (error) {
          console.error('Error reverting approval:', error);
          Notify.create({
            type: 'negative',
            message: error.response?.data?.detail || 'Failed to revert approval',
            position: 'top',
          });
        } finally {
          processing.value = false;
        }
      });
    };

    const revertFulfillment = async (requisitionId) => {
      $q.dialog({
        title: 'Revert Fulfillment',
        message: 'Are you sure you want to revert the fulfillment? Only unused quantities will be returned. If items have been used (debited to patients), only the unused portion will be returned.',
        cancel: true,
        persistent: true,
      }).onOk(async () => {
        processing.value = true;
        try {
          await pharmacyRequisitionsAPI.revertFulfillment(requisitionId);
          Notify.create({
            type: 'positive',
            message: 'Fulfillment reverted successfully. Only unused quantities were returned.',
            position: 'top',
            timeout: 5000,
          });
          loadRequisitions();
        } catch (error) {
          console.error('Error reverting fulfillment:', error);
          Notify.create({
            type: 'negative',
            message: error.response?.data?.detail || 'Failed to revert fulfillment',
            position: 'top',
          });
        } finally {
          processing.value = false;
        }
      });
    };

    const openRejectDialog = (requisition) => {
      selectedRequisition.value = requisition;
      rejectionReason.value = '';
      showRejectDialog.value = true;
    };

    const rejectRequisition = async () => {
      processing.value = true;
      try {
        await pharmacyRequisitionsAPI.reject(selectedRequisition.value.id, {
          rejection_reason: rejectionReason.value,
        });
        Notify.create({
          type: 'positive',
          message: 'Requisition rejected',
          position: 'top',
        });
        showRejectDialog.value = false;
        loadRequisitions();
      } catch (error) {
        console.error('Error rejecting requisition:', error);
        Notify.create({
          type: 'negative',
          message: error.response?.data?.detail || 'Failed to reject requisition',
          position: 'top',
        });
      } finally {
        processing.value = false;
      }
    };

    const cancelRequisition = async (requisitionId) => {
      $q.dialog({
        title: 'Cancel Requisition',
        message: 'Are you sure you want to cancel this requisition? This action cannot be undone.',
        cancel: true,
        persistent: true,
      }).onOk(async () => {
        processing.value = true;
        try {
          await pharmacyRequisitionsAPI.cancel(requisitionId);
          Notify.create({
            type: 'positive',
            message: 'Requisition cancelled successfully',
            position: 'top',
          });
          await loadRequisitions();
        } catch (error) {
          console.error('Error cancelling requisition:', error);
          Notify.create({
            type: 'negative',
            message: error.response?.data?.detail || 'Failed to cancel requisition',
            position: 'top',
          });
        } finally {
          processing.value = false;
        }
      });
    };

    const openFulfillDialog = async (requisition) => {
      // Reset processing state when opening dialog
      processing.value = false;
      try {
        const response = await pharmacyRequisitionsAPI.get(requisition.id);
        selectedRequisition.value = response.data;
        fulfillmentItems.value = {};
        fulfillmentNotes.value = '';
        // Initialize fulfillment quantities (use approved_quantity if available, otherwise requested_quantity)
        selectedRequisition.value.items.forEach(item => {
          const maxQuantity = item.approved_quantity !== null && item.approved_quantity !== undefined 
            ? item.approved_quantity 
            : item.requested_quantity;
          fulfillmentItems.value[item.id] = maxQuantity - item.fulfilled_quantity;
        });
        showFulfillDialog.value = true;
      } catch (error) {
        console.error('Error loading requisition:', error);
        Notify.create({
          type: 'negative',
          message: 'Failed to load requisition details',
          position: 'top',
        });
      }
    };

    const fulfillRequisition = async () => {
      const items = selectedRequisition.value.items
        .filter(item => fulfillmentItems.value[item.id] > 0)
        .map(item => ({
          item_id: item.id,
          fulfilled_quantity: fulfillmentItems.value[item.id],
        }));

      if (items.length === 0) {
        Notify.create({
          type: 'negative',
          message: 'Please specify quantities to fulfill',
          position: 'top',
        });
        return;
      }

      processing.value = true;
      try {
        await pharmacyRequisitionsAPI.fulfill(selectedRequisition.value.id, {
          items: items,
          notes: fulfillmentNotes.value,
        });
        Notify.create({
          type: 'positive',
          message: 'Requisition fulfilled successfully',
          position: 'top',
        });
        showFulfillDialog.value = false;
        loadRequisitions();
      } catch (error) {
        console.error('Error fulfilling requisition:', error);
        // Don't show error notification for aborted requests (user cancellation or timeout)
        if (error.code === 'ECONNABORTED' || error.message === 'Request aborted' || error.name === 'AxiosError' && error.code === 'ECONNABORTED') {
          // Request was aborted, likely due to timeout or user action
          // Don't show error notification, but still reset state in finally block
          Notify.create({
            type: 'warning',
            message: 'Request was cancelled or timed out. Please try again.',
            position: 'top',
            timeout: 3000,
          });
        } else {
          Notify.create({
            type: 'negative',
            message: error.response?.data?.detail || 'Failed to fulfill requisition',
            position: 'top',
          });
        }
      } finally {
        processing.value = false;
      }
    };

    const getStatusColor = (status) => {
      const colors = {
        pending: 'orange',
        approved: 'blue',
        rejected: 'red',
        partially_fulfilled: 'warning',
        fulfilled: 'positive',
      };
      return colors[status] || 'grey';
    };

    const formatDateTime = (dateTime) => {
      if (!dateTime) return '-';
      return new Date(dateTime).toLocaleString();
    };

    const loadWards = async () => {
      try {
        const response = await wardsAPI.getAll(true); // Get only active departments/units
        wardOptions.value = (response.data || []).map(dept => ({
          label: dept.name,
          value: dept.id
        }));
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
        
        // Auto-set filter to first assigned store (always set for Store Managers/Department Heads)
        if (userStoreIds.value.length > 0) {
          filters.value.store_id = userStoreIds.value[0];
        }
      } catch (error) {
        console.error('Error loading user store assignments:', error);
      }
    };

    // Watch for dialog close to reset processing state
    watch(showFulfillDialog, (newVal) => {
      if (!newVal) {
        // Dialog closed - reset processing state
        processing.value = false;
      }
    });

    onMounted(async () => {
      await loadWards();
      await loadStores();
      await loadUserStoreAssignments();
      loadRequisitions();
    });

    return {
      requisitions,
      loading,
      creating,
      processing,
      filters,
      newRequisition,
      showCreateDialog,
      showAddItemDialog,
      showViewDialog,
      showRejectDialog,
      showApproveDialog,
      showEditDialog,
      showFulfillDialog,
      selectedRequisition,
      editingRequisition,
      rejectionReason,
      approvalNotes,
      approvalItems,
      fulfillmentNotes,
      fulfillmentItems,
      selectedEditProduct,
      filteredEditProductOptions,
      loadingEditProducts,
      itemSearch,
      productResults,
      isWardStaff,
      isPharmacyHead,
      isStoreManager,
      isAdmin,
      currentUserId,
      wardOptions,
      storeOptions,
      userStoreIds,
      isStoreManagerOrDeptHead,
      statusOptions,
      columns,
      itemColumns,
      loadRequisitions,
      clearFilters,
      openCreateDialog,
      openAddItemDialog,
      searchProducts,
      selectProduct,
      removeItem,
      createRequisition,
      viewRequisition,
      openApproveDialog,
      approveRequisition,
      openRejectDialog,
      rejectRequisition,
      openEditDialog,
      removeEditItem,
      updateRequisition,
      loadEditProducts,
      filterEditProducts,
      onEditProductSelected,
      revertApproval,
      revertFulfillment,
      openFulfillDialog,
      fulfillRequisition,
      cancelRequisition,
      getStatusColor,
      formatDateTime,
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

