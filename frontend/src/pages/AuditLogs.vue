<template>
  <q-page class="q-pa-md">
    <div class="text-h4 q-mb-md text-weight-bold glass-text">Audit Trail Logs</div>
    
    <q-banner class="glass-card q-pa-md q-mb-md">
      <template v-slot:avatar>
        <q-icon name="info" color="primary" />
      </template>
      View and filter system activity logs. Track user actions, resource changes, and system events for security and compliance purposes.
    </q-banner>

    <!-- Filters -->
    <q-card class="q-mb-md glass-card" flat>
      <q-card-section>
        <div class="text-h6 q-mb-md glass-text">Filters</div>
        <q-form @submit="loadLogs" ref="filterForm">
          <div class="row q-gutter-md">
            <q-select
              v-model="filters.role"
              :options="roleOptions"
              label="Role"
              filled
              clearable
              class="col-12 col-md-3"
              @update:model-value="loadLogs"
            >
              <template v-slot:prepend>
                <q-icon name="badge" />
              </template>
            </q-select>

            <q-input
              v-model="filters.full_name"
              label="Full Name"
              filled
              clearable
              class="col-12 col-md-3"
              @keyup.enter="loadLogs"
              @clear="loadLogs"
            >
              <template v-slot:prepend>
                <q-icon name="person" />
              </template>
            </q-input>

            <q-input
              v-model="filters.username"
              label="Username"
              filled
              clearable
              class="col-12 col-md-3"
              @keyup.enter="loadLogs"
              @clear="loadLogs"
            >
              <template v-slot:prepend>
                <q-icon name="account_circle" />
              </template>
            </q-input>

            <q-select
              v-model="filters.action"
              :options="actionOptions"
              label="Action"
              filled
              clearable
              class="col-12 col-md-3"
              @update:model-value="loadLogs"
            >
              <template v-slot:prepend>
                <q-icon name="flash_on" />
              </template>
            </q-select>

            <q-select
              v-model="filters.resource_type"
              :options="resourceTypeOptions"
              label="Resource Type"
              filled
              clearable
              class="col-12 col-md-3"
              @update:model-value="loadLogs"
            >
              <template v-slot:prepend>
                <q-icon name="category" />
              </template>
            </q-select>

            <q-input
              v-model="filters.endpoint_path"
              label="Endpoint Path"
              filled
              clearable
              class="col-12 col-md-3"
              @keyup.enter="loadLogs"
              @clear="loadLogs"
            >
              <template v-slot:prepend>
                <q-icon name="link" />
              </template>
            </q-input>

            <q-select
              v-model="filters.http_method"
              :options="httpMethodOptions"
              label="HTTP Method"
              filled
              clearable
              class="col-12 col-md-3"
              @update:model-value="loadLogs"
            >
              <template v-slot:prepend>
                <q-icon name="http" />
              </template>
            </q-select>

            <q-input
              v-model="filters.start_date"
              label="Start Date"
              type="date"
              filled
              clearable
              class="col-12 col-md-3"
              @update:model-value="() => { pagination.page = 1; loadLogs(); }"
            >
              <template v-slot:prepend>
                <q-icon name="event" />
              </template>
            </q-input>

            <q-input
              v-model="filters.end_date"
              label="End Date"
              type="date"
              filled
              clearable
              class="col-12 col-md-3"
              @update:model-value="() => { pagination.page = 1; loadLogs(); }"
            >
              <template v-slot:prepend>
                <q-icon name="event" />
              </template>
            </q-input>

            <div class="col-12 col-md-3 flex items-center">
              <q-btn
                color="primary"
                label="Apply Filters"
                @click="() => { pagination.page = 1; loadLogs(); }"
                icon="filter_list"
                class="full-width"
              />
            </div>

            <div class="col-12 col-md-3 flex items-center">
              <q-btn
                flat
                label="Clear All"
                @click="clearFilters"
                icon="clear_all"
                class="full-width"
              />
            </div>
          </div>
        </q-form>
      </q-card-section>
    </q-card>

    <!-- Audit Logs Table -->
    <q-card class="glass-card" flat>
      <q-card-section>
        <div class="row items-center q-mb-md">
          <div class="col">
            <div class="text-h6 glass-text">
              Audit Logs
              <q-badge color="primary" class="q-ml-sm">{{ totalLogs }}</q-badge>
            </div>
            <div class="text-caption text-grey-7 q-mt-xs">
              Showing {{ paginationLabel }} · Page {{ pagination.page }} of {{ totalPages }}
            </div>
          </div>
          <div class="col-auto">
            <q-btn
              flat
              round
              icon="refresh"
              @click="loadLogs"
              :loading="loading"
            >
              <q-tooltip>Refresh</q-tooltip>
            </q-btn>
          </div>
        </div>

        <q-table
          v-model:pagination="pagination"
          :rows="logs"
          :columns="columns"
          :loading="loading"
          row-key="id"
          flat
          class="audit-logs-table"
          :rows-per-page-options="[25, 50, 100, 200]"
          @request="onRequest"
        >
          <template v-slot:body-cell-timestamp="props">
            <q-td :props="props">
              {{ formatDateTime(props.value) }}
            </q-td>
          </template>

          <template v-slot:body-cell-summary="props">
            <q-td :props="props">
              <span v-if="props.value" class="text-body2">{{ props.value }}</span>
              <span v-else class="text-grey-6 text-italic">—</span>
            </q-td>
          </template>
          <template v-slot:body-cell-details="props">
            <q-td :props="props">
              <q-btn
                v-if="props.value || props.row.summary"
                flat
                dense
                round
                icon="info"
                @click="showDetails(props.row)"
                size="sm"
              >
                <q-tooltip>View full details</q-tooltip>
              </q-btn>
              <span v-else class="text-grey-6">-</span>
            </q-td>
          </template>

          <template v-slot:body-cell-action="props">
            <q-td :props="props">
              <q-badge
                :color="getActionColor(props.value)"
                :label="props.value"
              />
            </q-td>
          </template>

          <template v-slot:body-cell-http_method="props">
            <q-td :props="props">
              <q-badge
                v-if="props.value"
                :color="getMethodColor(props.value)"
                :label="props.value"
              />
              <span v-else class="text-grey-6">-</span>
            </q-td>
          </template>

          <template v-slot:no-data>
            <div class="full-width row flex-center text-grey-6 q-gutter-sm">
              <q-icon name="inbox" size="2em" />
              <span>No audit logs found</span>
            </div>
          </template>
        </q-table>

        <div v-if="totalPages > 1" class="row justify-center q-mt-md">
          <q-pagination
            v-model="pagination.page"
            :max="totalPages"
            :max-pages="7"
            direction-links
            boundary-links
            color="primary"
            @update:model-value="loadLogs"
          />
        </div>
      </q-card-section>
    </q-card>

    <!-- Details Dialog -->
    <q-dialog v-model="showDetailsDialog">
      <q-card style="min-width: 500px">
        <q-card-section>
          <div class="text-h6">Audit Log Details</div>
        </q-card-section>

        <q-card-section>
          <div class="q-gutter-md">
            <div v-if="selectedLog?.summary" class="q-pa-md bg-primary-1 rounded-borders q-mb-md">
              <strong>What happened:</strong>
              <p class="q-mt-sm q-mb-none text-body1">{{ selectedLog.summary }}</p>
            </div>
            <div>
              <strong>User:</strong> {{ selectedLog?.full_name || selectedLog?.username }} ({{ selectedLog?.role }})
            </div>
            <div>
              <strong>Action:</strong> 
              <q-badge :color="getActionColor(selectedLog?.action)" :label="selectedLog?.action" />
            </div>
            <div v-if="selectedLog?.resource_type">
              <strong>Resource:</strong> {{ selectedLog.resource_type }}
            </div>
            <div v-if="selectedLog?.endpoint_path">
              <strong>Endpoint:</strong> {{ selectedLog.endpoint_path }}
            </div>
            <div v-if="selectedLog?.http_method">
              <strong>HTTP Method:</strong> 
              <q-badge :color="getMethodColor(selectedLog.http_method)" :label="selectedLog.http_method" />
            </div>
            <div>
              <strong>Timestamp:</strong> {{ formatDateTime(selectedLog?.timestamp) }}
            </div>
            <div v-if="selectedLog?.ip_address">
              <strong>IP Address:</strong> {{ selectedLog.ip_address }}
            </div>
            <div v-if="selectedLog?.details">
              <strong>Technical details (raw):</strong>
              <pre class="q-mt-sm q-pa-sm bg-grey-2 rounded-borders" style="max-height: 300px; overflow: auto;">{{ formatDetails(selectedLog.details) }}</pre>
            </div>
          </div>
        </q-card-section>

        <q-card-actions align="right">
          <q-btn flat label="Close" color="primary" v-close-popup />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script>
import { ref, computed, onMounted } from 'vue';
import { Notify } from 'quasar';
import { auditLogsAPI } from '../services/api';

function todayIsoDate() {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

export default {
  name: 'AuditLogs',
  setup() {
    const logs = ref([]);
    const loading = ref(false);
    const totalLogs = ref(0);
    const roleOptions = ref([]);
    const actionOptions = ref([]);
    const resourceTypeOptions = ref([]);
    const httpMethodOptions = ref(['GET', 'POST', 'PUT', 'PATCH', 'DELETE']);
    const showDetailsDialog = ref(false);
    const selectedLog = ref(null);

    const filters = ref({
      role: null,
      full_name: null,
      username: null,
      action: null,
      resource_type: null,
      endpoint_path: null,
      http_method: null,
      start_date: null,
      end_date: null,
    });

    const pagination = ref({
      sortBy: 'timestamp',
      descending: true,
      page: 1,
      rowsPerPage: 50,
      rowsNumber: 0,
    });

    const totalPages = computed(() => {
      const perPage = pagination.value.rowsPerPage || 50;
      return Math.max(1, Math.ceil((totalLogs.value || 0) / perPage));
    });

    const paginationLabel = computed(() => {
      const start = totalLogs.value === 0
        ? 0
        : (pagination.value.page - 1) * pagination.value.rowsPerPage + 1;
      const end = Math.min(
        pagination.value.page * pagination.value.rowsPerPage,
        totalLogs.value,
      );
      return `${start}-${end} of ${totalLogs.value}`;
    });

    const columns = [
      {
        name: 'timestamp',
        label: 'Timestamp',
        field: 'timestamp',
        align: 'left',
        sortable: true,
      },
      {
        name: 'username',
        label: 'Username',
        field: 'username',
        align: 'left',
        sortable: true,
      },
      {
        name: 'full_name',
        label: 'Full Name',
        field: 'full_name',
        align: 'left',
        sortable: true,
      },
      {
        name: 'role',
        label: 'Role',
        field: 'role',
        align: 'left',
        sortable: true,
      },
      {
        name: 'summary',
        label: 'What happened',
        field: 'summary',
        align: 'left',
        sortable: false,
        style: 'max-width: 360px; white-space: normal;',
      },
      {
        name: 'action',
        label: 'Action',
        field: 'action',
        align: 'left',
        sortable: true,
      },
      {
        name: 'resource_type',
        label: 'Resource',
        field: 'resource_type',
        align: 'left',
        sortable: true,
      },
      {
        name: 'endpoint_path',
        label: 'Endpoint',
        field: 'endpoint_path',
        align: 'left',
        sortable: true,
      },
      {
        name: 'http_method',
        label: 'Method',
        field: 'http_method',
        align: 'left',
        sortable: true,
      },
      {
        name: 'ip_address',
        label: 'IP Address',
        field: 'ip_address',
        align: 'left',
        sortable: false,
      },
      {
        name: 'details',
        label: 'Technical details',
        field: 'details',
        align: 'center',
        sortable: false,
      },
    ];

    const loadLogs = async () => {
      loading.value = true;
      try {
        const params = {
          page: pagination.value.page,
          page_size: pagination.value.rowsPerPage,
        };

        if (filters.value.role) params.role = filters.value.role;
        if (filters.value.full_name) params.full_name = filters.value.full_name;
        if (filters.value.username) params.username = filters.value.username;
        if (filters.value.action) params.action = filters.value.action;
        if (filters.value.resource_type) params.resource_type = filters.value.resource_type;
        if (filters.value.endpoint_path) params.endpoint_path = filters.value.endpoint_path;
        if (filters.value.http_method) params.http_method = filters.value.http_method;
        if (filters.value.start_date) params.start_date = filters.value.start_date;
        if (filters.value.end_date) params.end_date = filters.value.end_date;

        const response = await auditLogsAPI.getLogs(params);
        logs.value = response.data.logs;
        totalLogs.value = response.data.total;
        pagination.value.rowsNumber = response.data.total;
      } catch (error) {
        console.error('Error loading audit logs:', error);
        Notify.create({
          type: 'negative',
          message: 'Failed to load audit logs',
          position: 'top',
        });
      } finally {
        loading.value = false;
      }
    };

    const loadFilterOptions = async () => {
      try {
        const [rolesRes, actionsRes, resourceTypesRes] = await Promise.all([
          auditLogsAPI.getRoles(),
          auditLogsAPI.getActions(),
          auditLogsAPI.getResourceTypes(),
        ]);

        roleOptions.value = rolesRes.data || [];
        actionOptions.value = actionsRes.data || [];
        resourceTypeOptions.value = resourceTypesRes.data || [];
      } catch (error) {
        console.error('Error loading filter options:', error);
      }
    };

    const clearFilters = () => {
      const today = todayIsoDate();
      filters.value = {
        role: null,
        full_name: null,
        username: null,
        action: null,
        resource_type: null,
        endpoint_path: null,
        http_method: null,
        start_date: today,
        end_date: today,
      };
      pagination.value.page = 1;
      loadLogs();
    };

    const onRequest = (props) => {
      if (props?.pagination) {
        pagination.value = {
          ...pagination.value,
          ...props.pagination,
        };
      }
      loadLogs();
    };

    const showDetails = (log) => {
      selectedLog.value = log;
      showDetailsDialog.value = true;
    };

    const formatDateTime = (dateTime) => {
      if (!dateTime) return '-';
      const date = new Date(dateTime);
      return date.toLocaleString();
    };

    const formatDetails = (details) => {
      if (!details) return '';
      try {
        const parsed = JSON.parse(details);
        return JSON.stringify(parsed, null, 2);
      } catch {
        return details;
      }
    };

    const getActionColor = (action) => {
      if (!action) return 'grey';
      const actionUpper = action.toUpperCase();
      if (actionUpper.includes('CREATE') || actionUpper.includes('ADD')) return 'green';
      if (actionUpper.includes('UPDATE') || actionUpper.includes('EDIT') || actionUpper.includes('MODIFY')) return 'blue';
      if (actionUpper.includes('DELETE') || actionUpper.includes('REMOVE')) return 'red';
      if (actionUpper.includes('VIEW') || actionUpper.includes('GET') || actionUpper.includes('READ')) return 'grey';
      if (actionUpper.includes('LOGIN')) return 'positive';
      if (actionUpper.includes('LOGOUT')) return 'negative';
      return 'primary';
    };

    const getMethodColor = (method) => {
      if (!method) return 'grey';
      const methodUpper = method.toUpperCase();
      if (methodUpper === 'GET') return 'blue';
      if (methodUpper === 'POST') return 'green';
      if (methodUpper === 'PUT' || methodUpper === 'PATCH') return 'orange';
      if (methodUpper === 'DELETE') return 'red';
      return 'grey';
    };

    onMounted(() => {
      const today = todayIsoDate();
      filters.value.start_date = today;
      filters.value.end_date = today;
      loadFilterOptions();
      loadLogs();
    });

    return {
      logs,
      loading,
      totalLogs,
      totalPages,
      paginationLabel,
      filters,
      pagination,
      columns,
      roleOptions,
      actionOptions,
      resourceTypeOptions,
      httpMethodOptions,
      showDetailsDialog,
      selectedLog,
      loadLogs,
      clearFilters,
      onRequest,
      showDetails,
      formatDateTime,
      formatDetails,
      getActionColor,
      getMethodColor,
    };
  },
};
</script>

<style scoped>
.audit-logs-table {
  background: transparent;
}
</style>

