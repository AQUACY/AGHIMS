<template>
  <q-page class="hms-page">
    <HmsPageHeader
      title="Store Management"
      subtitle="Define supply stores, mark Pharmacy vs General, and assign managers."
    >
      <template #actions>
        <HmsButton variant="ghost" size="sm" @click="$router.back()">Back</HmsButton>
      </template>
    </HmsPageHeader>

    <q-banner dense rounded class="soft-banner q-mb-md">
      <template v-slot:avatar>
        <q-icon name="info" color="primary" />
      </template>
      Each store is a supply source for requisitions. Mark a row as <strong>Pharmacy</strong> (drug/pharmacy items) or <strong>General</strong> (main store / consumables) so lists and dashboards stay clear; requests stay tied to the store you pick when creating a requisition.
    </q-banner>

    <!-- Create New Store -->
    <section class="diag-panel">
      <div class="panel-head">
        <div>
          <div class="panel-title">Create New Store</div>
          <div class="panel-sub">Name, type, and active status</div>
        </div>
      </div>
      <div class="panel-body">
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
            <q-select
              v-model="storeForm.store_kind"
              :options="storeKindOptions"
              label="Store type *"
              filled
              class="col-12 col-md-6"
              emit-value
              map-options
            />
            <q-toggle
              v-model="storeForm.is_active"
              label="Active"
              class="col-12 col-md-6"
            />
            <div class="col-12 row q-gutter-sm">
              <HmsButton type="submit" variant="primary" size="sm" :loading="creating">
                Create Store
              </HmsButton>
              <HmsButton variant="ghost" size="sm" @click="resetForm">Reset</HmsButton>
            </div>
          </div>
        </q-form>
      </div>
    </section>

    <!-- Stores List -->
    <section class="diag-panel">
      <div class="panel-head">
        <div>
          <div class="panel-title">Stores</div>
          <div class="panel-sub">Search, edit, and manage staff assignments</div>
        </div>
        <q-input
          v-model="searchTerm"
          filled
          dense
          placeholder="Search stores..."
          style="min-width: 220px"
        >
          <template v-slot:prepend>
            <q-icon name="search" />
          </template>
        </q-input>
      </div>
      <div class="panel-body">
        <q-table
          :rows="filteredStores"
          :columns="columns"
          :loading="loading"
          row-key="id"
          :pagination="pagination"
          flat
        >
          <template v-slot:body-cell-store_kind="props">
            <q-td :props="props">
              <q-badge
                :color="props.row.store_kind === 'pharmacy' ? 'deep-purple' : 'grey-8'"
                :label="props.row.store_kind === 'pharmacy' ? 'Pharmacy' : 'General'"
              />
            </q-td>
          </template>

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
      </div>
    </section>

    <!-- Staff Assignment Dialog -->
    <q-dialog v-model="showStaffDialog" persistent>
      <q-card style="min-width: 600px">
        <q-card-section class="dialog-head">
          <div class="dialog-title">Manage Store Managers/Department Heads — {{ currentStore?.name }}</div>
        </q-card-section>

        <q-card-section>
          <div class="q-mb-md">
            <div class="text-subtitle2 q-mb-sm">Current Assignments</div>
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
            <q-banner v-else dense rounded class="soft-banner">
              No Store Managers or Department Heads assigned yet.
            </q-banner>
          </div>

          <q-separator class="q-my-md" />

          <div class="text-subtitle2 q-mb-sm">Add New Assignment</div>
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
            <q-card-actions align="right" class="dialog-actions">
              <HmsButton variant="ghost" size="sm" @click="showStaffDialog = false">Close</HmsButton>
              <HmsButton type="submit" variant="primary" size="sm" :loading="addingAssignment">
                Add Assignment
              </HmsButton>
            </q-card-actions>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- Edit Dialog -->
    <q-dialog v-model="showEditDialog">
      <q-card style="min-width: 400px">
        <q-card-section class="dialog-head">
          <div class="dialog-title">Edit Store</div>
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
            <q-select
              v-model="editForm.store_kind"
              :options="storeKindOptions"
              label="Store type *"
              filled
              class="q-mb-md"
              emit-value
              map-options
            />
            <q-toggle
              v-model="editForm.is_active"
              label="Active"
              class="q-mb-md"
            />
            <q-card-actions align="right" class="dialog-actions">
              <HmsButton variant="ghost" size="sm" @click="showEditDialog = false">Cancel</HmsButton>
              <HmsButton type="submit" variant="primary" size="sm" :loading="updating">Update</HmsButton>
            </q-card-actions>
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
import HmsPageHeader from '../components/ui/HmsPageHeader.vue';
import HmsButton from '../components/ui/HmsButton.vue';

export default {
  name: 'StoreManagement',
  components: { HmsPageHeader, HmsButton },
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

    const storeKindOptions = [
      { label: 'General (main store / consumables)', value: 'general' },
      { label: 'Pharmacy supply (drugs & pharmacy items)', value: 'pharmacy' },
    ];

    const columns = [
      { name: 'id', label: 'ID', field: 'id', align: 'left', sortable: true },
      { name: 'name', label: 'Store Name', field: 'name', align: 'left', sortable: true },
      { name: 'store_kind', label: 'Type', field: 'store_kind', align: 'center', sortable: true },
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
      store_kind: 'general',
      is_active: true,
    });

    const editForm = reactive({
      id: null,
      name: '',
      description: '',
      store_kind: 'general',
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
      editForm.store_kind = row.store_kind === 'pharmacy' ? 'pharmacy' : 'general';
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
          store_kind: editForm.store_kind,
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
      storeKindOptions,
      newAssignment,
      openStaffAssignmentDialog,
      addAssignment,
      removeAssignment,
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
  padding: 0;
}
</style>
