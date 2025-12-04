<template>
  <q-page class="q-pa-md">
    <div class="text-h4 q-mb-md text-weight-bold glass-text">Ward Management</div>
    <q-banner class="glass-card q-pa-md q-mb-md">
      <template v-slot:avatar>
        <q-icon name="info" color="primary" />
      </template>
      Manage hospital wards. Create, edit, or deactivate wards as needed. Changes will be reflected across the system.
    </q-banner>

    <!-- Create New Ward -->
    <q-card class="q-mb-md glass-card" flat>
      <q-card-section>
        <div class="text-h6 q-mb-md glass-text">Create New Ward</div>
        <q-form @submit="createWard" ref="createForm">
          <div class="row q-gutter-md">
            <q-input
              v-model="wardForm.name"
              label="Ward Name *"
              filled
              class="col-12 col-md-6"
              lazy-rules
              :rules="[(val) => !!val || 'Ward name is required']"
            />
            <q-toggle
              v-model="wardForm.is_active"
              label="Active"
              class="col-12 col-md-6"
            />
            <div class="col-12">
              <q-btn
                type="submit"
                color="primary"
                label="Create Ward"
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
          <div class="text-h6 glass-text">Wards</div>
          <q-space />
          <q-input
            v-model="searchTerm"
            filled
            dense
            placeholder="Search wards..."
            class="col-12 col-md-4"
          >
            <template v-slot:prepend>
              <q-icon name="search" />
            </template>
          </q-input>
        </div>

        <q-table
          :rows="filteredWards"
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

    <!-- Edit Dialog -->
    <q-dialog v-model="showEditDialog">
      <q-card style="min-width: 400px" class="glass-card">
        <q-card-section>
          <div class="text-h6 glass-text">Edit Ward</div>
        </q-card-section>

        <q-card-section>
          <q-form @submit="updateWard" ref="editFormRef">
            <q-input
              v-model="editForm.name"
              label="Ward Name *"
              filled
              class="q-mb-md"
              lazy-rules
              :rules="[(val) => !!val || 'Ward name is required']"
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
import { wardsAPI } from '../services/api';
import { useAuthStore } from '../stores/auth';

export default {
  name: 'WardManagement',
  setup() {
    const $q = useQuasar();
    const authStore = useAuthStore();

    const loading = ref(false);
    const creating = ref(false);
    const updating = ref(false);
    const wards = ref([]);
    const searchTerm = ref('');
    const showEditDialog = ref(false);
    const createForm = ref(null);
    const editFormRef = ref(null);

    const columns = [
      { name: 'id', label: 'ID', field: 'id', align: 'left', sortable: true },
      { name: 'name', label: 'Ward Name', field: 'name', align: 'left', sortable: true },
      { name: 'is_active', label: 'Status', field: 'is_active', align: 'center', sortable: true },
      { name: 'created_at', label: 'Created', field: 'created_at', align: 'left', sortable: true },
      { name: 'actions', label: 'Actions', field: 'actions', align: 'center' },
    ];

    const pagination = {
      rowsPerPage: 20,
    };

    const wardForm = reactive({
      name: '',
      is_active: true,
    });

    const editForm = reactive({
      id: null,
      name: '',
      is_active: true,
    });

    const filteredWards = computed(() => {
      if (!searchTerm.value) {
        return wards.value;
      }
      const search = searchTerm.value.toLowerCase();
      return wards.value.filter(
        (w) => w.name?.toLowerCase().includes(search)
      );
    });

    const loadWards = async () => {
      loading.value = true;
      try {
        const response = await wardsAPI.getAll(false); // Get all wards including inactive
        wards.value = response.data || [];
      } catch (error) {
        $q.notify({
          type: 'negative',
          message: 'Failed to load wards: ' + (error.response?.data?.detail || error.message),
        });
      } finally {
        loading.value = false;
      }
    };

    const createWard = async () => {
      if (!createForm.value) return;
      const valid = await createForm.value.validate();
      if (!valid) return;

      creating.value = true;
      try {
        await wardsAPI.create(wardForm);
        $q.notify({
          type: 'positive',
          message: 'Ward created successfully',
        });
        resetForm();
        loadWards();
      } catch (error) {
        $q.notify({
          type: 'negative',
          message: 'Failed to create ward: ' + (error.response?.data?.detail || error.message),
        });
      } finally {
        creating.value = false;
      }
    };

    const resetForm = () => {
      wardForm.name = '';
      wardForm.is_active = true;
      if (createForm.value) {
        createForm.value.resetValidation();
      }
    };

    const openEditDialog = (row) => {
      editForm.id = row.id;
      editForm.name = row.name;
      editForm.is_active = row.is_active;
      showEditDialog.value = true;
    };

    const updateWard = async () => {
      if (!editFormRef.value) return;
      const valid = await editFormRef.value.validate();
      if (!valid) return;

      updating.value = true;
      try {
        await wardsAPI.update(editForm.id, {
          name: editForm.name,
          is_active: editForm.is_active,
        });
        $q.notify({
          type: 'positive',
          message: 'Ward updated successfully',
        });
        showEditDialog.value = false;
        loadWards();
      } catch (error) {
        $q.notify({
          type: 'negative',
          message: 'Failed to update ward: ' + (error.response?.data?.detail || error.message),
        });
      } finally {
        updating.value = false;
      }
    };

    const confirmDelete = (ward) => {
      $q.dialog({
        title: 'Confirm Delete',
        message: `Are you sure you want to deactivate "${ward.name}"? This will mark it as inactive.`,
        cancel: true,
        persistent: true,
      }).onOk(async () => {
        try {
          await wardsAPI.delete(ward.id);
          $q.notify({
            type: 'positive',
            message: 'Ward deactivated successfully',
          });
          loadWards();
        } catch (error) {
          $q.notify({
            type: 'negative',
            message: 'Failed to deactivate ward: ' + (error.response?.data?.detail || error.message),
          });
        }
      });
    };

    const formatDate = (dateString) => {
      if (!dateString) return '-';
      return new Date(dateString).toLocaleString();
    };

    onMounted(() => {
      loadWards();
    });

    return {
      loading,
      creating,
      updating,
      wards,
      searchTerm,
      showEditDialog,
      createForm,
      editFormRef,
      wardForm,
      editForm,
      columns,
      pagination,
      filteredWards,
      loadWards,
      createWard,
      resetForm,
      openEditDialog,
      updateWard,
      confirmDelete,
      formatDate,
    };
  },
};
</script>

<style scoped>
.glass-text {
  color: rgba(255, 255, 255, 0.9);
}
</style>

