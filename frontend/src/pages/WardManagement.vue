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
      <div class="text-h4 text-weight-bold glass-text">Department/Unit Management</div>
    </div>
    <q-banner class="glass-card q-pa-md q-mb-md">
      <template v-slot:avatar>
        <q-icon name="info" color="primary" />
      </template>
      Manage hospital departments and units. Departments with type "Ward" will appear in IPD activities. Other departments can still request items from stores.
    </q-banner>

    <!-- Create New Department -->
    <q-card class="q-mb-md glass-card" flat>
      <q-card-section>
        <div class="text-h6 q-mb-md glass-text">Create New Department/Unit</div>
        <q-form @submit="createDepartment" ref="createForm">
          <div class="row q-gutter-md">
            <q-input
              v-model="departmentForm.name"
              label="Department/Unit Name *"
              filled
              class="col-12 col-md-6"
              lazy-rules
              :rules="[(val) => !!val || 'Department name is required']"
            />
            <q-select
              v-model="departmentForm.department_type"
              :options="departmentTypeOptions"
              label="Department Type *"
              filled
              class="col-12 col-md-6"
              emit-value
              map-options
              lazy-rules
              :rules="[(val) => !!val || 'Department type is required']"
            />
            <q-toggle
              v-model="departmentForm.is_active"
              label="Active"
              class="col-12 col-md-6"
            />
            <div class="col-12">
              <q-btn
                type="submit"
                color="primary"
                label="Create Department"
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

    <!-- Wards List -->
    <q-card class="glass-card" flat>
      <q-card-section>
        <div class="row items-center q-mb-md">
          <div class="text-h6 glass-text">Departments/Units</div>
          <q-space />
          <q-select
            v-model="filterType"
            :options="filterTypeOptions"
            label="Filter by Type"
            filled
            dense
            clearable
            emit-value
            map-options
            class="col-12 col-md-3 q-mr-md"
          />
          <q-input
            v-model="searchTerm"
            filled
            dense
            placeholder="Search departments..."
            class="col-12 col-md-4"
          >
            <template v-slot:prepend>
              <q-icon name="search" />
            </template>
          </q-input>
        </div>

        <q-table
          :rows="filteredDepartments"
          :columns="columns"
          :loading="loading"
          row-key="id"
          :pagination="pagination"
          flat
        >
          <template v-slot:body-cell-department_type="props">
            <q-td :props="props">
              <q-badge
                :color="getDepartmentTypeColor(props.value)"
                :label="getDepartmentTypeLabel(props.value)"
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
                :title="'Manage IC/Deputies'"
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
          <div class="text-h6 glass-text">Manage IC/Deputies - {{ currentDepartment?.name }}</div>
        </q-card-section>

        <q-card-section>
          <div class="q-mb-md">
            <div class="text-subtitle2 q-mb-sm glass-text">Current Assignments</div>
            <q-list v-if="currentAssignments.length > 0" bordered separator>
              <q-item v-for="assignment in currentAssignments" :key="assignment.id">
                <q-item-section>
                  <q-item-label>{{ assignment.user_name }}</q-item-label>
                  <q-item-label caption>{{ assignment.role === 'ic' ? 'In-Charge (IC)' : 'Deputy' }}</q-item-label>
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
              No IC or Deputies assigned yet.
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
          <div class="text-h6 glass-text">Edit Department/Unit</div>
        </q-card-section>

        <q-card-section>
          <q-form @submit="updateDepartment" ref="editFormRef">
            <q-input
              v-model="editForm.name"
              label="Department/Unit Name *"
              filled
              class="q-mb-md"
              lazy-rules
              :rules="[(val) => !!val || 'Department name is required']"
            />
            <q-select
              v-model="editForm.department_type"
              :options="departmentTypeOptions"
              label="Department Type *"
              filled
              class="q-mb-md"
              emit-value
              map-options
              lazy-rules
              :rules="[(val) => !!val || 'Department type is required']"
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
import { wardsAPI, staffAPI, departmentStaffAssignmentsAPI } from '../services/api';
import { useAuthStore } from '../stores/auth';

export default {
  name: 'DepartmentManagement',
  setup() {
    const $q = useQuasar();
    const authStore = useAuthStore();

    const loading = ref(false);
    const creating = ref(false);
    const updating = ref(false);
    const departments = ref([]);
    const searchTerm = ref('');
    const filterType = ref(null);
    const showEditDialog = ref(false);
    const showStaffDialog = ref(false);
    const createForm = ref(null);
    const editFormRef = ref(null);
    const assignmentFormRef = ref(null);
    const currentDepartment = ref(null);
    const currentAssignments = ref([]);
    const staffList = ref([]);
    const loadingStaff = ref(false);
    const addingAssignment = ref(false);

    const departmentTypeOptions = [
      { label: 'Ward', value: 'ward' },
      { label: 'OPD', value: 'opd' },
      { label: 'IT Unit', value: 'it' },
      { label: 'Administration', value: 'admin' },
      { label: 'Pharmacy', value: 'pharmacy' },
      { label: 'Other', value: 'other' },
    ];

    const filterTypeOptions = [
      { label: 'All Types', value: null },
      ...departmentTypeOptions,
    ];

    const roleOptions = [
      { label: 'In-Charge (IC)', value: 'ic' },
      { label: 'Deputy', value: 'deputy' },
    ];

    const columns = [
      { name: 'id', label: 'ID', field: 'id', align: 'left', sortable: true },
      { name: 'name', label: 'Department/Unit Name', field: 'name', align: 'left', sortable: true },
      { name: 'department_type', label: 'Type', field: 'department_type', align: 'center', sortable: true },
      { name: 'is_active', label: 'Status', field: 'is_active', align: 'center', sortable: true },
      { name: 'created_at', label: 'Created', field: 'created_at', align: 'left', sortable: true },
      { name: 'actions', label: 'Actions', field: 'actions', align: 'center' },
    ];

    const pagination = {
      rowsPerPage: 20,
    };

    const departmentForm = reactive({
      name: '',
      department_type: 'ward',
      is_active: true,
    });

    const editForm = reactive({
      id: null,
      name: '',
      department_type: 'ward',
      is_active: true,
    });

    const newAssignment = reactive({
      user_id: null,
      role: 'ic',
    });

    const filteredDepartments = computed(() => {
      let result = departments.value;
      
      // Filter by type
      if (filterType.value) {
        result = result.filter(d => d.department_type === filterType.value);
      }
      
      // Filter by search term
      if (searchTerm.value) {
        const search = searchTerm.value.toLowerCase();
        result = result.filter(
          (d) => d.name?.toLowerCase().includes(search)
        );
      }
      
      return result;
    });

    const getDepartmentTypeLabel = (type) => {
      const option = departmentTypeOptions.find(opt => opt.value === type);
      return option ? option.label : type;
    };

    const getDepartmentTypeColor = (type) => {
      const colors = {
        'ward': 'primary',
        'opd': 'info',
        'it': 'purple',
        'admin': 'orange',
        'other': 'grey',
      };
      return colors[type] || 'grey';
    };

    const loadDepartments = async () => {
      loading.value = true;
      try {
        const response = await wardsAPI.getAll(false); // Get all departments including inactive
        departments.value = response.data || [];
      } catch (error) {
        $q.notify({
          type: 'negative',
          message: 'Failed to load departments: ' + (error.response?.data?.detail || error.message),
        });
      } finally {
        loading.value = false;
      }
    };

    const createDepartment = async () => {
      if (!createForm.value) return;
      const valid = await createForm.value.validate();
      if (!valid) return;

      creating.value = true;
      try {
        await wardsAPI.create(departmentForm);
        $q.notify({
          type: 'positive',
          message: 'Department created successfully',
        });
        resetForm();
        loadDepartments();
      } catch (error) {
        $q.notify({
          type: 'negative',
          message: 'Failed to create department: ' + (error.response?.data?.detail || error.message),
        });
      } finally {
        creating.value = false;
      }
    };

    const resetForm = () => {
      departmentForm.name = '';
      departmentForm.department_type = 'ward';
      departmentForm.is_active = true;
      if (createForm.value) {
        createForm.value.resetValidation();
      }
    };

    const openEditDialog = (row) => {
      editForm.id = row.id;
      editForm.name = row.name;
      editForm.department_type = row.department_type || 'ward';
      editForm.is_active = row.is_active;
      showEditDialog.value = true;
    };

    const updateDepartment = async () => {
      if (!editFormRef.value) return;
      const valid = await editFormRef.value.validate();
      if (!valid) return;

      updating.value = true;
      try {
        await wardsAPI.update(editForm.id, {
          name: editForm.name,
          department_type: editForm.department_type,
          is_active: editForm.is_active,
        });
        $q.notify({
          type: 'positive',
          message: 'Department updated successfully',
        });
        showEditDialog.value = false;
        loadDepartments();
      } catch (error) {
        $q.notify({
          type: 'negative',
          message: 'Failed to update department: ' + (error.response?.data?.detail || error.message),
        });
      } finally {
        updating.value = false;
      }
    };

    const confirmDelete = (department) => {
      $q.dialog({
        title: 'Confirm Delete',
        message: `Are you sure you want to deactivate "${department.name}"? This will mark it as inactive.`,
        cancel: true,
        persistent: true,
      }).onOk(async () => {
        try {
          await wardsAPI.delete(department.id);
          $q.notify({
            type: 'positive',
            message: 'Department deactivated successfully',
          });
          loadDepartments();
        } catch (error) {
          $q.notify({
            type: 'negative',
            message: 'Failed to deactivate department: ' + (error.response?.data?.detail || error.message),
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

    const staffOptions = ref([]);
    const allStaffOptions = computed(() => {
      // Filter out staff already assigned to this department
      const assignedIds = currentAssignments.value.map(a => a.user_id);
      return staffList.value.filter(s => !assignedIds.includes(s.value));
    });

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

    const openStaffAssignmentDialog = async (department) => {
      currentDepartment.value = department;
      newAssignment.user_id = null;
      newAssignment.role = 'ic';
      
      // Load staff if not already loaded
      if (staffList.value.length === 0) {
        await loadStaff();
      }
      
      // Load current assignments first (so allStaffOptions can filter correctly)
      await loadAssignments(department.id);
      
      // Initialize staff options with all available staff
      staffOptions.value = allStaffOptions.value;
      
      showStaffDialog.value = true;
    };

    const loadAssignments = async (departmentId) => {
      try {
        const response = await departmentStaffAssignmentsAPI.getAll({
          department_id: departmentId,
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
        await departmentStaffAssignmentsAPI.create({
          department_id: currentDepartment.value.id,
          user_id: newAssignment.user_id,
          role: newAssignment.role,
        });
        $q.notify({
          type: 'positive',
          message: 'Assignment added successfully',
        });
        newAssignment.user_id = null;
        newAssignment.role = 'ic';
        if (assignmentFormRef.value) {
          assignmentFormRef.value.resetValidation();
        }
        await loadAssignments(currentDepartment.value.id);
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
        message: `Are you sure you want to remove ${assignment.user_name} as ${assignment.role === 'ic' ? 'IC' : 'Deputy'}?`,
        cancel: true,
        persistent: true,
      }).onOk(async () => {
        try {
          await departmentStaffAssignmentsAPI.delete(assignment.id);
          $q.notify({
            type: 'positive',
            message: 'Assignment removed successfully',
          });
          await loadAssignments(currentDepartment.value.id);
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
      loadDepartments();
      loadStaff();
    });

    return {
      loading,
      creating,
      updating,
      departments,
      searchTerm,
      filterType,
      showEditDialog,
      showStaffDialog,
      createForm,
      editFormRef,
      assignmentFormRef,
      departmentForm,
      editForm,
      columns,
      pagination,
      departmentTypeOptions,
      filterTypeOptions,
      filteredDepartments,
      getDepartmentTypeLabel,
      getDepartmentTypeColor,
      loadDepartments,
      createDepartment,
      resetForm,
      openEditDialog,
      updateDepartment,
      confirmDelete,
      formatDate,
      currentDepartment,
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



