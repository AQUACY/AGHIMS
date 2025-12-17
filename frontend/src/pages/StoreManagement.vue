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
      <div class="text-h4 text-weight-bold glass-text">Store Management</div>
    </div>
    <q-banner class="glass-card q-pa-md q-mb-md">
      <template v-slot:avatar>
        <q-icon name="info" color="primary" />
      </template>
      Manage hospital stores (Main Store, Pharmacy Store, etc.). Stores are where departments request items from.
    </q-banner>

    <!-- Create New Store -->
    <q-card class="q-mb-md glass-card" flat>
      <q-card-section>
        <div class="text-h6 q-mb-md glass-text">Create New Store</div>
        <q-form @submit="createStore" ref="createForm">
          <div class="row q-gutter-md">
            <q-input
              v-model="storeForm.name"
              label="Store Name *"
              filled
              class="col-12 col-md-6"
              lazy-rules
              :rules="[(val) => !!val || 'Store name is required']"
            />
            <q-input
              v-model="storeForm.description"
              label="Description"
              filled
              type="textarea"
              class="col-12 col-md-6"
            />
            <q-toggle
              v-model="storeForm.is_active"
              label="Active"
              class="col-12 col-md-6"
            />
            <div class="col-12">
              <q-btn
                type="submit"
                color="primary"
                label="Create Store"
                :loading="creating"
                icon="add"
              />
              <q-btn
                flat
                label="Reset"
                @click="resetForm"
                class="q-ml-sm"
              />
            </div>
          </div>
        </q-form>
      </q-card-section>
    </q-card>

    <!-- Stores List -->
    <q-card class="glass-card" flat>
      <q-card-section>
        <div class="row items-center q-mb-md">
          <div class="text-h6 glass-text">Stores</div>
          <q-space />
          <q-input
            v-model="searchTerm"
            filled
            dense
            placeholder="Search stores..."
            class="col-12 col-md-4"
          >
            <template v-slot:prepend>
              <q-icon name="search" />
            </template>
          </q-input>
        </div>

        <q-table
          :rows="filteredStores"
          :columns="columns"
          :loading="loading"
          row-key="id"
          :pagination="pagination"
          flat
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
                flat
                dense
                icon="people"
                color="secondary"
                @click="openStaffAssignmentDialog(props.row)"
                class="q-mr-xs"
                :title="'Manage Store Managers/Department Heads'"
              />
              <q-btn
                flat
                dense
                icon="edit"
                color="primary"
                @click="openEditDialog(props.row)"
                class="q-mr-xs"
              />
              <q-btn
                flat
                dense
                icon="delete"
                color="negative"
                @click="confirmDelete(props.row)"
              />
            </q-td>
          </template>
        </q-table>
      </q-card-section>
    </q-card>

    <!-- Staff Assignment Dialog -->
    <q-dialog v-model="showStaffDialog" persistent>
      <q-card style="min-width: 600px" class="glass-card">
        <q-card-section>
          <div class="text-h6 glass-text">Manage Store Managers/Department Heads - {{ currentStore?.name }}</div>
        </q-card-section>

        <q-card-section>
          <div class="q-mb-md">
            <div class="text-subtitle2 q-mb-sm glass-text">Current Assignments</div>
            <q-list v-if="currentAssignments.length > 0" bordered separator>
              <q-item v-for="assignment in currentAssignments" :key="assignment.id">
                <q-item-section>
                  <q-item-label>{{ assignment.user_name }}</q-item-label>
                  <q-item-label caption>{{ assignment.role === 'store_manager' ? 'Store Manager' : 'Department Head' }}</q-item-label>
                </q-item-section>
                <q-item-section side>
                  <q-btn
                    flat
                    dense
                    icon="delete"
                    color="negative"
                    @click="removeAssignment(assignment)"
                    size="sm"
                  />
                </q-item-section>
              </q-item>
            </q-list>
            <q-banner v-else class="bg-grey-3">
              No Store Managers or Department Heads assigned yet.
            </q-banner>
          </div>

          <q-separator class="q-my-md" />

          <div class="text-subtitle2 q-mb-sm glass-text">Add New Assignment</div>
          <q-form @submit="addAssignment" ref="assignmentFormRef">
            <q-select
              v-model="newAssignment.user_id"
              :options="staffOptions"
              label="Select Staff *"
              filled
              class="q-mb-md"
              emit-value
              map-options
              :loading="loadingStaff"
              use-input
              input-debounce="300"
              @filter="filterStaff"
              lazy-rules
              :rules="[(val) => !!val || 'Staff selection is required']"
            >
              <template v-slot:no-option>
                <q-item>
                  <q-item-section class="text-grey">
                    No staff found
                  </q-item-section>
                </q-item>
              </template>
            </q-select>
            <q-select
              v-model="newAssignment.role"
              :options="roleOptions"
              label="Role *"
              filled
              class="q-mb-md"
              emit-value
              map-options
              lazy-rules
              :rules="[(val) => !!val || 'Role is required']"
            />
            <div class="q-mt-md">
              <q-btn
                type="submit"
                color="primary"
                label="Add Assignment"
                :loading="addingAssignment"
              />
              <q-btn
                flat
                label="Close"
                @click="showStaffDialog = false"
                class="q-ml-sm"
              />
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- Edit Dialog -->
    <q-dialog v-model="showEditDialog">
      <q-card style="min-width: 400px" class="glass-card">
        <q-card-section>
          <div class="text-h6 glass-text">Edit Store</div>
        </q-card-section>

        <q-card-section>
          <q-form @submit="updateStore" ref="editFormRef">
            <q-input
              v-model="editForm.name"
              label="Store Name *"
              filled
              class="q-mb-md"
              lazy-rules
              :rules="[(val) => !!val || 'Store name is required']"
            />
            <q-input
              v-model="editForm.description"
              label="Description"
              filled
              type="textarea"
              class="q-mb-md"
            />
            <q-toggle
              v-model="editForm.is_active"
              label="Active"
              class="q-mb-md"
            />
            <div class="q-mt-md">
              <q-btn
                type="submit"
                color="primary"
                label="Update"
                :loading="updating"
              />
              <q-btn
                flat
                label="Cancel"
                @click="showEditDialog = false"
                class="q-ml-sm"
              />
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script>
import { ref, reactive, computed, onMounted } from 'vue';
import { useQuasar } from 'quasar';
import { storesAPI, staffAPI, storeStaffAssignmentsAPI } from '../services/api';
import { useAuthStore } from '../stores/auth';

export default {
  name: 'StoreManagement',
  setup() {
    const $q = useQuasar();
    const authStore = useAuthStore();

    const loading = ref(false);
    const creating = ref(false);
    const updating = ref(false);
    const stores = ref([]);
    const searchTerm = ref('');
    const showEditDialog = ref(false);
    const showStaffDialog = ref(false);
    const createForm = ref(null);
    const editFormRef = ref(null);
    const assignmentFormRef = ref(null);
    const currentStore = ref(null);
    const currentAssignments = ref([]);
    const staffList = ref([]);
    const loadingStaff = ref(false);
    const addingAssignment = ref(false);

    const columns = [
      { name: 'id', label: 'ID', field: 'id', align: 'left', sortable: true },
      { name: 'name', label: 'Store Name', field: 'name', align: 'left', sortable: true },
      { name: 'description', label: 'Description', field: 'description', align: 'left', sortable: true },
      { name: 'is_active', label: 'Status', field: 'is_active', align: 'center', sortable: true },
      { name: 'created_at', label: 'Created', field: 'created_at', align: 'left', sortable: true },
      { name: 'actions', label: 'Actions', field: 'actions', align: 'center' },
    ];

    const pagination = {
      rowsPerPage: 20,
    };

    const storeForm = reactive({
      name: '',
      description: '',
      is_active: true,
    });

    const editForm = reactive({
      id: null,
      name: '',
      description: '',
      is_active: true,
    });

    const roleOptions = [
      { label: 'Store Manager', value: 'store_manager' },
      { label: 'Department Head', value: 'department_head' },
    ];

    const newAssignment = reactive({
      user_id: null,
      role: 'store_manager',
    });

    const staffOptions = ref([]);
    const allStaffOptions = computed(() => {
      // Filter out staff already assigned to this store
      const assignedIds = currentAssignments.value.map(a => a.user_id);
      return staffList.value.filter(s => !assignedIds.includes(s.value));
    });

    const filteredStores = computed(() => {
      if (!searchTerm.value) {
        return stores.value;
      }
      const search = searchTerm.value.toLowerCase();
      return stores.value.filter(
        (s) => s.name?.toLowerCase().includes(search) ||
               s.description?.toLowerCase().includes(search)
      );
    });

    const loadStores = async () => {
      loading.value = true;
      try {
        const response = await storesAPI.getAll(false); // Get all stores including inactive
        stores.value = response.data || [];
      } catch (error) {
        $q.notify({
          type: 'negative',
          message: 'Failed to load stores: ' + (error.response?.data?.detail || error.message),
        });
      } finally {
        loading.value = false;
      }
    };

    const createStore = async () => {
      if (!createForm.value) return;
      const valid = await createForm.value.validate();
      if (!valid) return;

      creating.value = true;
      try {
        await storesAPI.create(storeForm);
        $q.notify({
          type: 'positive',
          message: 'Store created successfully',
        });
        resetForm();
        loadStores();
      } catch (error) {
        $q.notify({
          type: 'negative',
          message: 'Failed to create store: ' + (error.response?.data?.detail || error.message),
        });
      } finally {
        creating.value = false;
      }
    };

    const resetForm = () => {
      storeForm.name = '';
      storeForm.description = '';
      storeForm.is_active = true;
      if (createForm.value) {
        createForm.value.resetValidation();
      }
    };

    const openEditDialog = (row) => {
      editForm.id = row.id;
      editForm.name = row.name;
      editForm.description = row.description || '';
      editForm.is_active = row.is_active;
      showEditDialog.value = true;
    };

    const updateStore = async () => {
      if (!editFormRef.value) return;
      const valid = await editFormRef.value.validate();
      if (!valid) return;

      updating.value = true;
      try {
        await storesAPI.update(editForm.id, {
          name: editForm.name,
          description: editForm.description,
          is_active: editForm.is_active,
        });
        $q.notify({
          type: 'positive',
          message: 'Store updated successfully',
        });
        showEditDialog.value = false;
        loadStores();
      } catch (error) {
        $q.notify({
          type: 'negative',
          message: 'Failed to update store: ' + (error.response?.data?.detail || error.message),
        });
      } finally {
        updating.value = false;
      }
    };

    const confirmDelete = (store) => {
      $q.dialog({
        title: 'Confirm Delete',
        message: `Are you sure you want to deactivate "${store.name}"? This will mark it as inactive.`,
        cancel: true,
        persistent: true,
      }).onOk(async () => {
        try {
          await storesAPI.delete(store.id);
          $q.notify({
            type: 'positive',
            message: 'Store deactivated successfully',
          });
          loadStores();
        } catch (error) {
          $q.notify({
            type: 'negative',
            message: 'Failed to deactivate store: ' + (error.response?.data?.detail || error.message),
          });
        }
      });
    };

    const formatDate = (dateString) => {
      if (!dateString) return '-';
      return new Date(dateString).toLocaleString();
    };

    const loadStaff = async () => {
      loadingStaff.value = true;
      try {
        const response = await staffAPI.getAll();
        staffList.value = (response.data || []).map(staff => {
          const name = staff.full_name || staff.username;
          const username = staff.username || '';
          // Format: "Full Name (username)" or just "username" if no full name
          const label = name && username && name !== username 
            ? `${name} (${username})` 
            : name || username;
          return {
            label: label,
            value: staff.id,
            fullName: name,
            username: username,
          };
        });
      } catch (error) {
        $q.notify({
          type: 'negative',
          message: 'Failed to load staff: ' + (error.response?.data?.detail || error.message),
        });
      } finally {
        loadingStaff.value = false;
      }
    };

    const filterStaff = (val, update) => {
      if (val === '') {
        update(() => {
          staffOptions.value = allStaffOptions.value;
        });
        return;
      }

      update(() => {
        const needle = val.toLowerCase();
        staffOptions.value = allStaffOptions.value.filter(
          staff => {
            // Search in label (which includes name and username)
            const labelMatch = staff.label.toLowerCase().indexOf(needle) > -1;
            // Also search in fullName and username separately for better matching
            const fullNameMatch = staff.fullName?.toLowerCase().indexOf(needle) > -1;
            const usernameMatch = staff.username?.toLowerCase().indexOf(needle) > -1;
            return labelMatch || fullNameMatch || usernameMatch;
          }
        );
      });
    };

    const openStaffAssignmentDialog = async (store) => {
      currentStore.value = store;
      newAssignment.user_id = null;
      newAssignment.role = 'store_manager';
      
      // Load staff if not already loaded
      if (staffList.value.length === 0) {
        await loadStaff();
      }
      
      // Load current assignments first (so allStaffOptions can filter correctly)
      await loadAssignments(store.id);
      
      // Initialize staff options with all available staff
      staffOptions.value = allStaffOptions.value;
      
      showStaffDialog.value = true;
    };

    const loadAssignments = async (storeId) => {
      try {
        const response = await storeStaffAssignmentsAPI.getAll({
          store_id: storeId,
          active_only: true,
        });
        currentAssignments.value = response.data || [];
      } catch (error) {
        $q.notify({
          type: 'negative',
          message: 'Failed to load assignments: ' + (error.response?.data?.detail || error.message),
        });
      }
    };

    const addAssignment = async () => {
      if (!assignmentFormRef.value) return;
      const valid = await assignmentFormRef.value.validate();
      if (!valid) return;

      addingAssignment.value = true;
      try {
        await storeStaffAssignmentsAPI.create({
          store_id: currentStore.value.id,
          user_id: newAssignment.user_id,
          role: newAssignment.role,
        });
        $q.notify({
          type: 'positive',
          message: 'Assignment added successfully',
        });
        newAssignment.user_id = null;
        newAssignment.role = 'store_manager';
        if (assignmentFormRef.value) {
          assignmentFormRef.value.resetValidation();
        }
        await loadAssignments(currentStore.value.id);
        // Update staff options after assignment is added
        staffOptions.value = allStaffOptions.value;
      } catch (error) {
        $q.notify({
          type: 'negative',
          message: 'Failed to add assignment: ' + (error.response?.data?.detail || error.message),
        });
      } finally {
        addingAssignment.value = false;
      }
    };

    const removeAssignment = async (assignment) => {
      $q.dialog({
        title: 'Confirm Removal',
        message: `Are you sure you want to remove ${assignment.user_name} as ${assignment.role === 'store_manager' ? 'Store Manager' : 'Department Head'}?`,
        cancel: true,
        persistent: true,
      }).onOk(async () => {
        try {
          await storeStaffAssignmentsAPI.delete(assignment.id);
          $q.notify({
            type: 'positive',
            message: 'Assignment removed successfully',
          });
          await loadAssignments(currentStore.value.id);
          // Update staff options after assignment is removed
          staffOptions.value = allStaffOptions.value;
        } catch (error) {
          $q.notify({
            type: 'negative',
            message: 'Failed to remove assignment: ' + (error.response?.data?.detail || error.message),
          });
        }
      });
    };

    onMounted(() => {
      loadStores();
      loadStaff();
    });

    return {
      loading,
      creating,
      updating,
      stores,
      searchTerm,
      showEditDialog,
      showStaffDialog,
      createForm,
      editFormRef,
      assignmentFormRef,
      storeForm,
      editForm,
      columns,
      pagination,
      filteredStores,
      loadStores,
      createStore,
      resetForm,
      openEditDialog,
      updateStore,
      confirmDelete,
      formatDate,
      currentStore,
      currentAssignments,
      staffList,
      loadingStaff,
      addingAssignment,
      staffOptions,
      allStaffOptions,
      filterStaff,
      roleOptions,
      newAssignment,
      openStaffAssignmentDialog,
      addAssignment,
      removeAssignment,
    };
  },
};
</script>

<style scoped>
.glass-text {
  color: rgba(255, 255, 255, 0.9);
}
</style>

