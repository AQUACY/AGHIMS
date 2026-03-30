<template>
  <q-page class="q-pa-md">
    <div class="text-h4 q-mb-md text-weight-bold glass-text">Module Management</div>
    <q-banner class="glass-card q-pa-md q-mb-md">
      <template v-slot:avatar>
        <q-icon name="info" color="primary" />
      </template>
      Control which modules are active in the system. When a module is inactive, users can still view data they created but cannot create, edit, or delete records.
    </q-banner>

    <q-card v-if="isSuperAdmin" class="q-mb-md glass-card" flat>
      <q-card-section>
        <div class="text-h6 q-mb-sm glass-text">Facility Mode Setup</div>
        <div class="text-caption q-mb-md">
          Enable or disable app modes for this facility. Inactive modes are hidden for regular users on mode selection.
        </div>
        <div class="row q-col-gutter-md">
          <div class="col-12 col-md-4">
            <q-toggle
              :model-value="modeToggles.hms"
              label="HMS Mode Active"
              color="primary"
              :loading="togglingMode === 'hms'"
              @update:model-value="(value) => updateModeToggle('hms', value)"
            />
          </div>
          <div class="col-12 col-md-4">
            <q-toggle
              :model-value="modeToggles.companion"
              label="Companion Mode Active"
              color="primary"
              :loading="togglingMode === 'companion'"
              @update:model-value="(value) => updateModeToggle('companion', value)"
            />
          </div>
          <div class="col-12 col-md-4">
            <q-toggle
              :model-value="modeToggles.inventory"
              label="Inventory Mode Active"
              color="primary"
              :loading="togglingMode === 'inventory'"
              @update:model-value="(value) => updateModeToggle('inventory', value)"
            />
          </div>
        </div>
      </q-card-section>
    </q-card>

    <!-- Filter by Category -->
    <q-card class="q-mb-md glass-card" flat>
      <q-card-section>
        <q-select
          v-model="selectedCategory"
          :options="categoryOptions"
          label="Filter by Category"
          filled
          clearable
          class="col-12 col-md-4"
          @update:model-value="loadModules"
        />
      </q-card-section>
    </q-card>

    <!-- Modules Table -->
    <q-card class="glass-card" flat>
      <q-card-section>
        <div class="text-h6 q-mb-md glass-text">System Modules</div>
        
        <q-table
          :rows="modules"
          :columns="columns"
          :loading="loading"
          row-key="id"
          :pagination="{ rowsPerPage: 0 }"
          flat
          class="glass-table"
        >
          <template v-slot:body-cell-is_active="props">
            <q-td :props="props">
              <q-toggle
                :model-value="props.row.is_active"
                @update:model-value="toggleModule(props.row)"
                :loading="props.row.toggling"
                color="primary"
              />
            </q-td>
          </template>

          <template v-slot:body-cell-permissions="props">
            <q-td :props="props">
              <div class="row q-gutter-xs">
                <q-chip
                  :color="props.row.allow_read ? 'positive' : 'grey'"
                  text-color="white"
                  size="sm"
                  :label="props.row.allow_read ? 'Read' : 'No Read'"
                />
                <q-chip
                  :color="props.row.allow_create ? 'positive' : 'grey'"
                  text-color="white"
                  size="sm"
                  :label="props.row.allow_create ? 'Create' : 'No Create'"
                />
                <q-chip
                  :color="props.row.allow_update ? 'positive' : 'grey'"
                  text-color="white"
                  size="sm"
                  :label="props.row.allow_update ? 'Update' : 'No Update'"
                />
                <q-chip
                  :color="props.row.allow_delete ? 'positive' : 'grey'"
                  text-color="white"
                  size="sm"
                  :label="props.row.allow_delete ? 'Delete' : 'No Delete'"
                />
              </div>
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
                @click="editModule(props.row)"
                size="sm"
              >
                <q-tooltip>Edit Permissions</q-tooltip>
              </q-btn>
            </q-td>
          </template>
        </q-table>
      </q-card-section>
    </q-card>

    <!-- Edit Module Dialog -->
    <q-dialog v-model="showEditDialog" persistent>
      <q-card style="min-width: 500px">
        <q-card-section>
          <div class="text-h6">Edit Module: {{ editingModule?.module_name }}</div>
        </q-card-section>

        <q-card-section>
          <q-form @submit="saveModule" ref="editForm">
            <div class="q-gutter-md">
              <q-toggle
                v-model="editForm.is_active"
                label="Module Active"
                color="primary"
              />
              
              <q-separator />
              
              <div class="text-subtitle2 q-mt-md">Permissions</div>
              
              <q-toggle
                v-model="editForm.allow_read"
                label="Allow Read (View Data)"
                color="positive"
              />
              
              <q-toggle
                v-model="editForm.allow_create"
                label="Allow Create (Add New Records)"
                color="positive"
              />
              
              <q-toggle
                v-model="editForm.allow_update"
                label="Allow Update (Edit Records)"
                color="positive"
              />
              
              <q-toggle
                v-model="editForm.allow_delete"
                label="Allow Delete (Remove Records)"
                color="positive"
              />

              <q-input
                v-model.number="editForm.display_order"
                label="Display Order"
                type="number"
                filled
                hint="Lower numbers appear first"
              />
            </div>
          </q-form>
        </q-card-section>

        <q-card-actions align="right">
          <q-btn flat label="Cancel" color="negative" v-close-popup />
          <q-btn flat label="Save" color="primary" @click="saveModule" :loading="saving" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useQuasar } from 'quasar';
import { moduleSettingsAPI } from '../services/api';
import { useModuleSettingsStore } from '../stores/moduleSettings';
import { useAuthStore } from '../stores/auth';
import { APP_MODES, APP_MODE_MODULE_KEYS } from '../stores/appMode';

const $q = useQuasar();
const authStore = useAuthStore();
const moduleSettingsStore = useModuleSettingsStore();

const isSuperAdmin = computed(() => authStore.isSuperAdmin);
const togglingMode = ref(null);
const modeToggles = ref({
  hms: true,
  companion: true,
  inventory: true,
});

const modules = ref([]);
const loading = ref(false);
const saving = ref(false);
const selectedCategory = ref(null);
const showEditDialog = ref(false);
const editingModule = ref(null);
const editForm = ref({
  is_active: true,
  allow_read: true,
  allow_create: true,
  allow_update: true,
  allow_delete: true,
  display_order: 0,
});

const categoryOptions = [
  { label: 'All Categories', value: null },
  { label: 'Core', value: 'core' },
  { label: 'Clinical', value: 'clinical' },
  { label: 'Administrative', value: 'administrative' },
  { label: 'Reports', value: 'reports' },
];

const columns = [
  {
    name: 'module_name',
    label: 'Module Name',
    field: 'module_name',
    align: 'left',
    sortable: true,
  },
  {
    name: 'description',
    label: 'Description',
    field: 'description',
    align: 'left',
    sortable: false,
  },
  {
    name: 'category',
    label: 'Category',
    field: 'category',
    align: 'center',
    sortable: true,
  },
  {
    name: 'is_active',
    label: 'Active',
    field: 'is_active',
    align: 'center',
    sortable: true,
  },
  {
    name: 'permissions',
    label: 'Permissions',
    field: 'permissions',
    align: 'left',
    sortable: false,
  },
  {
    name: 'actions',
    label: 'Actions',
    field: 'actions',
    align: 'center',
    sortable: false,
  },
];

const loadModules = async () => {
  try {
    loading.value = true;
    const response = await moduleSettingsAPI.getAll(selectedCategory.value);
    modules.value = response.data.map((module) => ({
      ...module,
      toggling: false,
    }));
  } catch (error) {
    console.error('Error loading modules:', error);
    $q.notify({
      type: 'negative',
      message: 'Failed to load modules',
      position: 'top',
    });
  } finally {
    loading.value = false;
  }
};

const loadModeSetup = async () => {
  if (!isSuperAdmin.value) return;
  try {
    await moduleSettingsStore.fetchModuleStatus(Object.values(APP_MODE_MODULE_KEYS));
    modeToggles.value = {
      hms: moduleSettingsStore.isModuleActive(APP_MODE_MODULE_KEYS[APP_MODES.HMS]),
      companion: moduleSettingsStore.isModuleActive(APP_MODE_MODULE_KEYS[APP_MODES.COMPANION]),
      inventory: moduleSettingsStore.isModuleActive(APP_MODE_MODULE_KEYS[APP_MODES.INVENTORY]),
    };
  } catch (error) {
    console.error('Error loading facility mode setup:', error);
  }
};

const updateModeToggle = async (mode, value) => {
  const moduleKey = APP_MODE_MODULE_KEYS[mode];
  if (!moduleKey) return;
  const previousValue = modeToggles.value[mode];
  modeToggles.value[mode] = value;
  try {
    togglingMode.value = mode;
    await moduleSettingsAPI.update(moduleKey, { is_active: value });
    moduleSettingsStore.clearCache();
    await moduleSettingsStore.fetchModuleStatus([moduleKey]);
    $q.notify({
      type: 'positive',
      message: `${mode.charAt(0).toUpperCase() + mode.slice(1)} mode ${value ? 'activated' : 'deactivated'}`,
      position: 'top',
    });
  } catch (error) {
    modeToggles.value[mode] = previousValue;
    console.error('Error updating mode toggle:', error);
    $q.notify({
      type: 'negative',
      message: 'Failed to update mode setup. Ensure mode keys exist in Module Settings.',
      position: 'top',
    });
  } finally {
    togglingMode.value = null;
  }
};

const toggleModule = async (module) => {
  try {
    module.toggling = true;
    const response = await moduleSettingsAPI.toggle(module.module_key);
    module.is_active = response.data.is_active;
    $q.notify({
      type: 'positive',
      message: `${module.module_name} ${module.is_active ? 'activated' : 'deactivated'}`,
      position: 'top',
    });
    // Refresh module settings store cache
    const moduleSettingsStore = useModuleSettingsStore();
    moduleSettingsStore.clearCache();
  } catch (error) {
    console.error('Error toggling module:', error);
    $q.notify({
      type: 'negative',
      message: 'Failed to toggle module',
      position: 'top',
    });
    // Revert the toggle
    module.is_active = !module.is_active;
  } finally {
    module.toggling = false;
  }
};

const editModule = (module) => {
  editingModule.value = { ...module };
  // Create a new object to ensure reactivity
  editForm.value = {
    is_active: Boolean(module.is_active),
    allow_read: Boolean(module.allow_read),
    allow_create: Boolean(module.allow_create),
    allow_update: Boolean(module.allow_update),
    allow_delete: Boolean(module.allow_delete),
    display_order: Number(module.display_order) || 0,
  };
  showEditDialog.value = true;
};

const saveModule = async () => {
  try {
    saving.value = true;
    const response = await moduleSettingsAPI.update(editingModule.value.module_key, editForm.value);
    
    // Update local state
    const module = modules.value.find((m) => m.id === editingModule.value.id);
    if (module) {
      Object.assign(module, response.data);
    }
    
    $q.notify({
      type: 'positive',
      message: 'Module updated successfully',
      position: 'top',
    });
    
    showEditDialog.value = false;
    
    // Refresh module settings store cache
    const moduleSettingsStore = useModuleSettingsStore();
    moduleSettingsStore.clearCache();
  } catch (error) {
    console.error('Error saving module:', error);
    $q.notify({
      type: 'negative',
      message: 'Failed to save module',
      position: 'top',
    });
  } finally {
    saving.value = false;
  }
};

onMounted(() => {
  loadModules();
  loadModeSetup();
});
</script>

<script>
export default {
  name: 'ModuleManagement',
};
</script>

<style scoped>
.glass-text {
  color: rgba(255, 255, 255, 0.9);
}

.glass-card {
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.glass-table {
  background: transparent;
}
</style>
