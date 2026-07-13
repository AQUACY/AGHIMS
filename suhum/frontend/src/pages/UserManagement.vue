<template>
  <q-page class="q-pa-md">
    <div class="text-h4 q-mb-md text-weight-bold glass-text">User Management</div>
    <q-banner class="glass-card q-mb-md" rounded>
      <template #avatar><q-icon name="info" color="primary" /></template>
      Create accounts for staff who will use Suhum. Admins can manage price lists, GHIMS imports, and other users.
    </q-banner>

    <q-card class="q-mb-lg glass-card" flat bordered>
      <q-card-section>
        <div class="text-h6 q-mb-md">{{ editingUser ? 'Edit user' : 'Create user' }}</div>
        <q-form @submit.prevent="saveUser" class="row q-col-gutter-md">
          <q-input
            v-model="form.username"
            label="Username *"
            filled
            class="col-12 col-md-4"
            :disable="!!editingUser"
            :rules="[(v) => !!v || 'Required']"
          />
          <q-input v-model="form.full_name" label="Full name" filled class="col-12 col-md-4" />
          <q-input
            v-model="form.password"
            :label="editingUser ? 'New password (leave blank to keep)' : 'Password *'"
            type="password"
            filled
            class="col-12 col-md-4"
            :rules="editingUser ? [] : [(v) => (v && v.length >= 6) || 'Min 6 characters']"
          />
          <div class="col-12 col-md-4 row items-center q-gutter-md">
            <q-toggle v-model="form.is_admin" label="Administrator" />
            <q-toggle v-model="form.is_active" label="Active" />
          </div>
          <div class="col-12">
            <q-btn type="submit" color="primary" :label="editingUser ? 'Save changes' : 'Create user'" :loading="saving" icon="person_add" />
            <q-btn v-if="editingUser" flat label="Cancel" class="q-ml-sm" @click="cancelEdit" />
          </div>
        </q-form>
      </q-card-section>
    </q-card>

    <q-card class="glass-card" flat bordered>
      <q-card-section>
        <div class="text-h6 q-mb-md">Users</div>
        <q-table
          :rows="users"
          :columns="columns"
          row-key="id"
          :loading="loading"
          flat
          bordered
          :pagination="{ rowsPerPage: 15 }"
        >
          <template #body-cell-is_admin="props">
            <q-td :props="props">
              <q-badge :color="props.row.is_admin ? 'primary' : 'grey'" :label="props.row.is_admin ? 'Admin' : 'User'" />
            </q-td>
          </template>
          <template #body-cell-is_active="props">
            <q-td :props="props">
              <q-badge :color="props.row.is_active ? 'positive' : 'negative'" :label="props.row.is_active ? 'Active' : 'Inactive'" />
            </q-td>
          </template>
          <template #body-cell-actions="props">
            <q-td :props="props">
              <q-btn flat dense round icon="edit" color="primary" @click="startEdit(props.row)">
                <q-tooltip>Edit</q-tooltip>
              </q-btn>
              <q-btn
                flat dense round icon="delete"
                color="negative"
                :disable="props.row.id === currentUserId"
                @click="confirmDelete(props.row)"
              >
                <q-tooltip>Delete</q-tooltip>
              </q-btn>
            </q-td>
          </template>
        </q-table>
      </q-card-section>
    </q-card>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useQuasar } from 'quasar';
import { useAuthStore } from '../stores/auth';
import { authAPI } from '../services/api';

const $q = useQuasar();
const authStore = useAuthStore();

const users = ref([]);
const loading = ref(false);
const saving = ref(false);
const editingUser = ref(null);

const form = ref({
  username: '',
  full_name: '',
  password: '',
  is_admin: false,
  is_active: true,
});

const currentUserId = computed(() => authStore.user?.id);

const columns = [
  { name: 'username', label: 'Username', field: 'username', align: 'left', sortable: true },
  { name: 'full_name', label: 'Full name', field: 'full_name', align: 'left', sortable: true },
  { name: 'is_admin', label: 'Role', field: 'is_admin', align: 'center' },
  { name: 'is_active', label: 'Status', field: 'is_active', align: 'center' },
  { name: 'created_at', label: 'Created', field: 'created_at', align: 'left', format: (v) => v ? new Date(v).toLocaleString() : '—' },
  { name: 'actions', label: 'Actions', field: 'actions', align: 'center' },
];

function resetForm() {
  form.value = { username: '', full_name: '', password: '', is_admin: false, is_active: true };
  editingUser.value = null;
}

async function loadUsers() {
  loading.value = true;
  try {
    const res = await authAPI.listUsers();
    users.value = res.data || [];
  } catch (e) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Failed to load users' });
  } finally {
    loading.value = false;
  }
}

function startEdit(row) {
  editingUser.value = row;
  form.value = {
    username: row.username,
    full_name: row.full_name || '',
    password: '',
    is_admin: !!row.is_admin,
    is_active: !!row.is_active,
  };
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function cancelEdit() {
  resetForm();
}

async function saveUser() {
  saving.value = true;
  try {
    if (editingUser.value) {
      const payload = {
        full_name: form.value.full_name || null,
        is_admin: form.value.is_admin,
        is_active: form.value.is_active,
      };
      if (form.value.password) payload.password = form.value.password;
      await authAPI.updateUser(editingUser.value.id, payload);
      $q.notify({ type: 'positive', message: 'User updated' });
    } else {
      if (!form.value.password || form.value.password.length < 6) {
        $q.notify({ type: 'negative', message: 'Password must be at least 6 characters' });
        return;
      }
      await authAPI.createUser({
        username: form.value.username,
        password: form.value.password,
        full_name: form.value.full_name || null,
        is_admin: form.value.is_admin,
      });
      $q.notify({ type: 'positive', message: 'User created' });
    }
    resetForm();
    await loadUsers();
  } catch (e) {
    $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Save failed' });
  } finally {
    saving.value = false;
  }
}

function confirmDelete(row) {
  $q.dialog({
    title: 'Delete user',
    message: `Remove account "${row.username}"? This cannot be undone.`,
    cancel: true,
    persistent: true,
  }).onOk(async () => {
    try {
      await authAPI.deleteUser(row.id);
      $q.notify({ type: 'positive', message: 'User deleted' });
      if (editingUser.value?.id === row.id) resetForm();
      await loadUsers();
    } catch (e) {
      $q.notify({ type: 'negative', message: e.response?.data?.detail || 'Delete failed' });
    }
  });
}

onMounted(loadUsers);
</script>
