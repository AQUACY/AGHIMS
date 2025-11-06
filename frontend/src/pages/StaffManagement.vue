<template>
  <q-page class="q-pa-md">
    <div class="text-h4 q-mb-md text-weight-bold glass-text">Staff Management</div>
    <q-banner class="glass-card q-pa-md q-mb-md">
      <template v-slot:avatar>
        <q-icon name="info" color="primary" />
      </template>
      Create and manage staff accounts. You can create individual accounts or import multiple staff members from an Excel file.
    </q-banner>

    <!-- Create New Staff -->
    <q-card class="q-mb-md glass-card" flat>
      <q-card-section>
        <div class="text-h6 q-mb-md glass-text">Create New Staff</div>
        <q-form @submit="createStaff" ref="createForm">
          <div class="row q-gutter-md">
            <q-input
              v-model="staffForm.username"
              label="Username *"
              filled
              class="col-12 col-md-6"
              lazy-rules
              :rules="[(val) => !!val || 'Username is required']"
            />
            <q-input
              v-model="staffForm.email"
              label="Email"
              type="email"
              filled
              class="col-12 col-md-6"
            />
            <q-input
              v-model="staffForm.full_name"
              label="Full Name"
              filled
              class="col-12 col-md-6"
            />
            <q-input
              v-model="staffForm.password"
              label="Password *"
              type="password"
              filled
              class="col-12 col-md-6"
              lazy-rules
              :rules="[(val) => !!val || 'Password is required']"
            />
            <q-select
              v-model="staffForm.role"
              :options="roleOptions"
              label="Role *"
              filled
              class="col-12 col-md-6"
              lazy-rules
              :rules="[(val) => !!val || 'Role is required']"
            />
            <q-toggle
              v-model="staffForm.is_active"
              label="Active"
              class="col-12 col-md-6"
            />
            <div class="col-12">
              <q-btn
                type="submit"
                color="primary"
                label="Create Staff"
                :loading="creating"
                icon="person_add"
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

    <!-- Import Staff from Excel -->
    <q-card class="q-mb-md">
      <q-card-section>
        <div class="text-h6 q-mb-md">Import Staff from Excel</div>
        <div class="row q-gutter-md">
          <q-file
            v-model="importFile"
            label="Select Excel File (.xlsx, .xls)"
            accept=".xlsx,.xls"
            filled
            class="col-12 col-md-8"
          >
            <template v-slot:prepend>
              <q-icon name="attach_file" />
            </template>
          </q-file>
          <q-input
            v-model="defaultPassword"
            label="Default Password"
            type="password"
            filled
            class="col-12 col-md-4"
            hint="Password for imported staff"
          />
          <div class="col-12">
            <q-btn
              color="primary"
              label="Import Staff"
              @click="importStaff"
              :loading="importing"
              :disable="!importFile"
              icon="upload"
            />
          </div>
        </div>
        <div class="q-mt-md">
          <q-banner class="bg-grey-2">
            <div class="text-caption">
              <strong>Excel File Format:</strong><br/>
              Required columns: <strong>username</strong>, <strong>full_name</strong>, <strong>role</strong><br/>
              Optional columns: <strong>Email</strong>, <strong>is_active</strong> (1 or 0, default: 1)<br/>
              <br/>
              <strong>Roles:</strong> Records, Nurse, Doctor, Billing, Pharmacist, Lab, Claims, Admin<br/>
              <br/>
              <strong>Note:</strong> All imported staff will have the same default password (changeable after login).
            </div>
          </q-banner>
        </div>
      </q-card-section>
    </q-card>

    <!-- Staff List -->
    <q-card>
      <q-card-section>
        <div class="text-h6 q-mb-md">Staff Members</div>
        <div class="row q-gutter-md q-mb-md">
          <q-input
            v-model="searchTerm"
            filled
            label="Search by username, name, or email"
            class="col-12 col-md-6"
            clearable
            @keyup.enter="loadStaff"
            @clear="loadStaff"
          >
            <template v-slot:append>
              <q-icon name="search" />
            </template>
          </q-input>
          <div class="col-12 col-md-6 text-right">
            <q-btn
              color="primary"
              label="Refresh"
              @click="loadStaff"
              icon="refresh"
            />
          </div>
        </div>
        <q-table
          :rows="filteredStaff"
          :columns="columns"
          :loading="loading"
          row-key="id"
          :pagination="pagination"
        >
          <template v-slot:body-cell-role="props">
            <q-td :props="props">
              <q-badge :color="getRoleColor(props.value)" :label="props.value" />
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
                round
                icon="edit"
                color="primary"
                @click="openEditDialog(props.row)"
                size="sm"
              >
                <q-tooltip>Edit Staff</q-tooltip>
              </q-btn>
              <q-btn
                flat
                dense
                round
                icon="delete"
                color="negative"
                @click="confirmDelete(props.row)"
                size="sm"
                :disable="props.row.id === currentUser?.id"
              >
                <q-tooltip>Delete Staff</q-tooltip>
              </q-btn>
            </q-td>
          </template>
        </q-table>
      </q-card-section>
    </q-card>

    <!-- Edit Dialog -->
    <q-dialog v-model="showEditDialog">
      <q-card style="min-width: 500px">
        <q-card-section>
          <div class="text-h6">Edit Staff</div>
        </q-card-section>
        <q-card-section>
          <q-form @submit="updateStaff">
            <div class="row q-gutter-md">
              <q-input
                v-model="editForm.username"
                label="Username *"
                filled
                class="col-12"
                lazy-rules
                :rules="[(val) => !!val || 'Username is required']"
              />
              <q-input
                v-model="editForm.email"
                label="Email"
                type="email"
                filled
                class="col-12"
              />
              <q-input
                v-model="editForm.full_name"
                label="Full Name"
                filled
                class="col-12"
              />
              <q-input
                v-model="editForm.password"
                label="New Password (leave blank to keep current)"
                type="password"
                filled
                class="col-12"
              />
              <q-select
                v-model="editForm.role"
                :options="roleOptions"
                label="Role *"
                filled
                class="col-12"
                lazy-rules
                :rules="[(val) => !!val || 'Role is required']"
              />
              <q-toggle
                v-model="editForm.is_active"
                label="Active"
                class="col-12"
              />
            </div>
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
import { staffAPI } from '../services/api';
import { useAuthStore } from '../stores/auth';

export default {
  name: 'StaffManagement',
  setup() {
    const $q = useQuasar();
    const authStore = useAuthStore();
    const currentUser = computed(() => authStore.user);

    const loading = ref(false);
    const creating = ref(false);
    const updating = ref(false);
    const importing = ref(false);
    const staff = ref([]);
    const searchTerm = ref('');
    const importFile = ref(null);
    const defaultPassword = ref('password123');
    const showEditDialog = ref(false);
    const createForm = ref(null);

    const roleOptions = [
      'Records',
      'Nurse',
      'Doctor',
      'Billing',
      'Pharmacy',
      'Lab',
      'Claims',
      'Admin'
    ];

    const columns = [
      { name: 'id', label: 'ID', field: 'id', align: 'left', sortable: true },
      { name: 'username', label: 'Username', field: 'username', align: 'left', sortable: true },
      { name: 'full_name', label: 'Full Name', field: 'full_name', align: 'left', sortable: true },
      { name: 'email', label: 'Email', field: 'email', align: 'left', sortable: true },
      { name: 'role', label: 'Role', field: 'role', align: 'left', sortable: true },
      { name: 'is_active', label: 'Status', field: 'is_active', align: 'center', sortable: true },
      { name: 'actions', label: 'Actions', field: 'actions', align: 'center' },
    ];

    const pagination = {
      rowsPerPage: 20,
    };

    const staffForm = reactive({
      username: '',
      email: '',
      full_name: '',
      password: '',
      role: '',
      is_active: true,
    });

    const editForm = reactive({
      id: null,
      username: '',
      email: '',
      full_name: '',
      password: '',
      role: '',
      is_active: true,
    });

    const filteredStaff = computed(() => {
      if (!searchTerm.value) {
        return staff.value;
      }
      const search = searchTerm.value.toLowerCase();
      return staff.value.filter(
        (s) =>
          s.username?.toLowerCase().includes(search) ||
          s.full_name?.toLowerCase().includes(search) ||
          s.email?.toLowerCase().includes(search)
      );
    });

    const getRoleColor = (role) => {
      const colors = {
        Admin: 'red',
        Doctor: 'blue',
        Nurse: 'green',
        Lab: 'orange',
        Pharmacy: 'purple',
        Billing: 'teal',
        Claims: 'cyan',
        Records: 'grey',
      };
      return colors[role] || 'grey';
    };

    const loadStaff = async () => {
      loading.value = true;
      try {
        const response = await staffAPI.getAll();
        staff.value = response.data || [];
      } catch (error) {
        $q.notify({
          type: 'negative',
          message: 'Failed to load staff: ' + (error.response?.data?.detail || error.message),
        });
      } finally {
        loading.value = false;
      }
    };

    const createStaff = async () => {
      if (!createForm.value) return;
      const valid = await createForm.value.validate();
      if (!valid) return;

      creating.value = true;
      try {
        await staffAPI.create(staffForm);
        $q.notify({
          type: 'positive',
          message: 'Staff member created successfully',
        });
        resetForm();
        loadStaff();
      } catch (error) {
        $q.notify({
          type: 'negative',
          message: 'Failed to create staff: ' + (error.response?.data?.detail || error.message),
        });
      } finally {
        creating.value = false;
      }
    };

    const resetForm = () => {
      staffForm.username = '';
      staffForm.email = '';
      staffForm.full_name = '';
      staffForm.password = '';
      staffForm.role = '';
      staffForm.is_active = true;
      if (createForm.value) {
        createForm.value.resetValidation();
      }
    };

    const openEditDialog = (row) => {
      editForm.id = row.id;
      editForm.username = row.username || '';
      editForm.email = row.email || '';
      editForm.full_name = row.full_name || '';
      editForm.password = '';
      editForm.role = row.role || '';
      editForm.is_active = row.is_active ?? true;
      showEditDialog.value = true;
    };

    const updateStaff = async () => {
      updating.value = true;
      try {
        const updateData = {
          username: editForm.username,
          email: editForm.email,
          full_name: editForm.full_name,
          role: editForm.role,
          is_active: editForm.is_active,
        };
        if (editForm.password) {
          updateData.password = editForm.password;
        }
        await staffAPI.update(editForm.id, updateData);
        $q.notify({
          type: 'positive',
          message: 'Staff member updated successfully',
        });
        showEditDialog.value = false;
        loadStaff();
      } catch (error) {
        $q.notify({
          type: 'negative',
          message: 'Failed to update staff: ' + (error.response?.data?.detail || error.message),
        });
      } finally {
        updating.value = false;
      }
    };

    const confirmDelete = (row) => {
      if (row.id === currentUser.value?.id) {
        $q.notify({
          type: 'warning',
          message: 'You cannot delete your own account',
        });
        return;
      }
      $q.dialog({
        title: 'Confirm Delete',
        message: `Are you sure you want to deactivate ${row.username}?`,
        cancel: true,
        persistent: true,
      }).onOk(async () => {
        try {
          await staffAPI.delete(row.id);
          $q.notify({
            type: 'positive',
            message: 'Staff member deactivated successfully',
          });
          loadStaff();
        } catch (error) {
          $q.notify({
            type: 'negative',
            message: 'Failed to delete staff: ' + (error.response?.data?.detail || error.message),
          });
        }
      });
    };

    const importStaff = async () => {
      if (!importFile.value) {
        $q.notify({
          type: 'warning',
          message: 'Please select an Excel file',
        });
        return;
      }

      importing.value = true;
      try {
        const response = await staffAPI.import(importFile.value, defaultPassword.value);
        $q.dialog({
          title: 'Import Complete',
          message: `Successfully imported ${response.data.imported?.length || 0} staff member(s).${
            response.data.errors?.length > 0
              ? `\n\nErrors:\n${response.data.errors.join('\n')}`
              : ''
          }`,
          persistent: true,
        });
        importFile.value = null;
        loadStaff();
      } catch (error) {
        $q.notify({
          type: 'negative',
          message: 'Failed to import staff: ' + (error.response?.data?.detail || error.message),
        });
      } finally {
        importing.value = false;
      }
    };

    onMounted(() => {
      loadStaff();
    });

    return {
      loading,
      creating,
      updating,
      importing,
      staff,
      searchTerm,
      importFile,
      defaultPassword,
      showEditDialog,
      createForm,
      roleOptions,
      columns,
      pagination,
      staffForm,
      editForm,
      filteredStaff,
      currentUser,
      getRoleColor,
      loadStaff,
      createStaff,
      resetForm,
      openEditDialog,
      updateStaff,
      confirmDelete,
      importStaff,
    };
  },
};
</script>

<style scoped>
</style>

