<template>
  <q-page class="q-pa-md">
    <div class="row items-center q-mb-md">
      <div class="text-h4 text-weight-bold glass-text">Lab Result Templates</div>
      <q-space />
      <q-btn
        color="primary"
        icon="add"
        label="Create Template"
        @click="openCreateDialog"
        :disable="!canManageTemplates"
      />
    </div>

    <q-banner
      v-if="!canManageTemplates"
      class="bg-warning text-dark q-mb-md"
      rounded
    >
      <template v-slot:avatar>
        <q-icon name="warning" color="dark" />
      </template>
      Only Admin and Lab Head can manage templates.
    </q-banner>

    <!-- Templates List -->
    <q-card class="glass-card" flat>
      <q-card-section>
        <q-table
          :rows="templates"
          :columns="columns"
          row-key="id"
          :loading="loading"
          :filter="filter"
          flat
        >
          <template v-slot:top>
            <div class="text-h6">Templates</div>
            <q-space />
            <q-input
              v-model="filter"
              filled
              dense
              placeholder="Search templates..."
              class="q-mr-md"
              style="min-width: 300px"
            >
              <template v-slot:prepend>
                <q-icon name="search" />
              </template>
            </q-input>
          </template>

          <template v-slot:body-cell-is_active="props">
            <q-td :props="props">
              <q-badge :color="props.value === 1 ? 'positive' : 'grey'" 
                       :label="props.value === 1 ? 'Active' : 'Inactive'" />
            </q-td>
          </template>

          <template v-slot:body-cell-actions="props">
            <q-td :props="props">
              <div class="row q-gutter-xs">
                <q-btn
                  size="sm"
                  color="primary"
                  icon="edit"
                  flat
                  round
                  @click="openEditDialog(props.row)"
                  :disable="!canManageTemplates"
                >
                  <q-tooltip>Edit Template</q-tooltip>
                </q-btn>
                <q-btn
                  size="sm"
                  color="negative"
                  icon="delete"
                  flat
                  round
                  @click="confirmDelete(props.row)"
                  :disable="!canManageTemplates"
                >
                  <q-tooltip>Delete Template</q-tooltip>
                </q-btn>
              </div>
            </q-td>
          </template>
        </q-table>
      </q-card-section>
    </q-card>

    <!-- Create/Edit Template Dialog -->
    <q-dialog v-model="showTemplateDialog" persistent>
      <q-card style="min-width: 800px; max-width: 1200px">
        <q-card-section>
          <div class="text-h6">
            {{ editingTemplate ? 'Edit Template' : 'Create Template' }}
          </div>
        </q-card-section>

        <q-card-section>
          <q-form @submit="saveTemplate" class="q-gutter-md">
            <q-select
              v-model="selectedProcedure"
              filled
              label="Select Lab Procedure *"
              :hint="editingTemplate ? 'Change procedure to remap this template to a different procedure' : 'Choose a lab procedure from the system'"
              :options="labProcedureOptions"
              option-label="service_name"
              option-value="service_name"
              use-input
              input-debounce="300"
              @filter="filterLabProcedures"
              @update:model-value="onProcedureSelected"
              :rules="[val => !!val || 'Please select a lab procedure']"
            >
              <template v-slot:no-option>
                <q-item>
                  <q-item-section class="text-grey">
                    No lab procedures found
                  </q-item-section>
                </q-item>
              </template>
              <template v-slot:option="scope">
                <q-item v-bind="scope.itemProps">
                  <q-item-section>
                    <q-item-label>{{ scope.opt.service_name }}</q-item-label>
                    <q-item-label caption>G-DRG: {{ scope.opt.g_drg_code }}</q-item-label>
                  </q-item-section>
                </q-item>
              </template>
            </q-select>
            
            <q-input
              v-model="templateForm.g_drg_code"
              filled
              label="G-DRG Code"
              hint="Auto-filled from selected procedure"
              :disable="true"
            />
            <q-input
              v-model="templateForm.procedure_name"
              filled
              label="Procedure Name"
              :hint="editingTemplate ? 'This is used to match templates. Changing it will remap the template to the new procedure name.' : 'Auto-filled from selected procedure - This is used to match templates'"
              :disable="true"
            />
            <q-banner
              v-if="editingTemplate"
              class="bg-info text-white q-mt-sm"
              rounded
              dense
            >
              <template v-slot:avatar>
                <q-icon name="info" />
              </template>
              <strong>Note:</strong> Changing the procedure will remap this template. Make sure the procedure name matches exactly with the procedure name used in lab investigations.
            </q-banner>
            <q-input
              v-model="templateForm.template_name"
              filled
              label="Template Name"
              hint="Short template identifier (e.g., FBC)"
              :rules="[val => !!val || 'Template name is required']"
            />

            <div class="text-subtitle1 q-mt-md">Template Structure (JSON)</div>
            <q-editor
              v-model="templateForm.template_structure_json"
              :toolbar="[
                ['bold', 'italic', 'underline'],
                ['code', 'codeblock'],
                ['fullscreen']
              ]"
              min-height="400px"
              :rules="[val => validateTemplateStructure(val) || 'Invalid template structure']"
            />

            <div class="row q-gutter-md q-mt-md">
              <q-btn label="Cancel" flat v-close-popup class="col" />
              <q-btn
                label="Save"
                type="submit"
                color="primary"
                class="col"
                :loading="saving"
              />
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useQuasar } from 'quasar';
import { labTemplatesAPI, priceListAPI } from '../services/api';
import { useAuthStore } from '../stores/auth';

const $q = useQuasar();
const authStore = useAuthStore();

const templates = ref([]);
const loading = ref(false);
const saving = ref(false);
const filter = ref('');
const showTemplateDialog = ref(false);
const editingTemplate = ref(false);
const editingTemplateId = ref(null);
const labProcedures = ref([]);
const labProcedureOptions = ref([]);
const selectedProcedure = ref(null);
const loadingProcedures = ref(false);

const canManageTemplates = computed(() => {
  return authStore.userRole === 'Admin' || authStore.userRole === 'Lab Head';
});

const columns = [
  { name: 'template_name', label: 'Template Name', field: 'template_name', align: 'left', sortable: true },
  { name: 'procedure_name', label: 'Procedure Name', field: 'procedure_name', align: 'left', sortable: true },
  { name: 'g_drg_code', label: 'G-DRG Code', field: 'g_drg_code', align: 'left', sortable: true, format: (val) => val || 'N/A' },
  { name: 'is_active', label: 'Status', field: 'is_active', align: 'center' },
  { name: 'created_at', label: 'Created', field: 'created_at', align: 'left', format: (val) => formatDate(val) },
  { name: 'actions', label: 'Actions', field: 'actions', align: 'center' },
];

const templateForm = ref({
  g_drg_code: '',
  procedure_name: '',
  template_name: '',
  template_structure_json: '',
});

const loadTemplates = async () => {
  loading.value = true;
  try {
    const response = await labTemplatesAPI.getAll();
    templates.value = response.data || [];
  } catch (error) {
    console.error('Failed to load templates:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to load templates',
    });
  } finally {
    loading.value = false;
  }
};

const openCreateDialog = async () => {
  editingTemplate.value = false;
  editingTemplateId.value = null;
  selectedProcedure.value = null;
  templateForm.value = {
    g_drg_code: '',
    procedure_name: '',
    template_name: '',
    template_structure_json: JSON.stringify({
      fields: [],
      message_fields: [],
      patient_fields: [],
    }, null, 2),
  };
  
  // Load lab procedures if not already loaded
  if (labProcedures.value.length === 0) {
    await loadLabProcedures();
  }
  
  showTemplateDialog.value = true;
};

const openEditDialog = async (template) => {
  editingTemplate.value = true;
  editingTemplateId.value = template.id;  // Store the template ID for update
  selectedProcedure.value = null;
  
  // Try to find the procedure in the list
  if (labProcedures.value.length === 0) {
    await loadLabProcedures();
  }
  
  const matchingProcedure = labProcedures.value.find(
    p => p.service_name === template.procedure_name
  );
  if (matchingProcedure) {
    selectedProcedure.value = matchingProcedure;
  }
  
  templateForm.value = {
    g_drg_code: template.g_drg_code || '',
    procedure_name: template.procedure_name,
    template_name: template.template_name,
    template_structure_json: JSON.stringify(template.template_structure, null, 2),
  };
  showTemplateDialog.value = true;
};

const validateTemplateStructure = (jsonString) => {
  try {
    const parsed = JSON.parse(jsonString);
    if (!parsed.fields || !Array.isArray(parsed.fields)) {
      return false;
    }
    return true;
  } catch {
    return false;
  }
};

const saveTemplate = async () => {
  if (!validateTemplateStructure(templateForm.value.template_structure_json)) {
    $q.notify({
      type: 'negative',
      message: 'Invalid template structure JSON',
    });
    return;
  }

  saving.value = true;
  try {
    const templateData = {
      g_drg_code: templateForm.value.g_drg_code,
      procedure_name: templateForm.value.procedure_name,
      template_name: templateForm.value.template_name,
      template_structure: JSON.parse(templateForm.value.template_structure_json),
    };

    if (editingTemplate.value) {
      // Use the stored template ID
      if (!editingTemplateId.value) {
        $q.notify({
          type: 'negative',
          message: 'Template ID not found for update',
        });
        return;
      }
      await labTemplatesAPI.update(editingTemplateId.value, templateData);
      $q.notify({
        type: 'positive',
        message: 'Template updated successfully',
      });
    } else {
      await labTemplatesAPI.create(templateData);
      $q.notify({
        type: 'positive',
        message: 'Template created successfully',
      });
    }

    showTemplateDialog.value = false;
    await loadTemplates();
  } catch (error) {
    console.error('Failed to save template:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to save template',
    });
  } finally {
    saving.value = false;
  }
};

const confirmDelete = (template) => {
  $q.dialog({
    title: 'Confirm Delete',
    message: `Are you sure you want to delete template "${template.template_name}"?`,
    cancel: true,
    persistent: true,
  }).onOk(async () => {
    try {
      await labTemplatesAPI.delete(template.id);
      $q.notify({
        type: 'positive',
        message: 'Template deleted successfully',
      });
      await loadTemplates();
    } catch (error) {
      console.error('Failed to delete template:', error);
      $q.notify({
        type: 'negative',
        message: error.response?.data?.detail || 'Failed to delete template',
      });
    }
  });
};

const loadLabProcedures = async () => {
  loadingProcedures.value = true;
  try {
    // Use the new endpoint that gets lab procedures from investigations and price list
    const response = await labTemplatesAPI.getAvailableProcedures();
    labProcedures.value = response.data || [];
    labProcedureOptions.value = labProcedures.value;
  } catch (error) {
    console.error('Failed to load lab procedures:', error);
    // Fallback: try price list API
    try {
      const priceListResponse = await priceListAPI.getProceduresByServiceType('Lab');
      if (Array.isArray(priceListResponse.data)) {
        labProcedures.value = priceListResponse.data;
        labProcedureOptions.value = labProcedures.value;
      }
    } catch (e) {
      $q.notify({
        type: 'warning',
        message: 'Could not load lab procedures. You can still type the procedure name manually.',
      });
      labProcedures.value = [];
      labProcedureOptions.value = [];
    }
  } finally {
    loadingProcedures.value = false;
  }
};

const filterLabProcedures = (val, update) => {
  if (val === '') {
    update(() => {
      labProcedureOptions.value = labProcedures.value;
    });
    return;
  }
  
  update(() => {
    const needle = val.toLowerCase();
    labProcedureOptions.value = labProcedures.value.filter(
      (p) => p.service_name.toLowerCase().indexOf(needle) > -1 ||
             (p.g_drg_code && p.g_drg_code.toLowerCase().indexOf(needle) > -1)
    );
  });
};

const onProcedureSelected = (procedure) => {
  if (procedure && typeof procedure === 'object') {
    templateForm.value.procedure_name = procedure.service_name || '';
    templateForm.value.g_drg_code = procedure.g_drg_code || '';
  }
};

const formatDate = (dateString) => {
  if (!dateString) return 'N/A';
  const date = new Date(dateString);
  return date.toLocaleDateString('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  });
};

onMounted(() => {
  loadTemplates();
  loadLabProcedures();
});
</script>

