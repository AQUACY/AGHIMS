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
              v-model="filters.start_date"
              label="Start Date"
              type="date"
              filled
              clearable
              class="col-12 col-md-3"
              @update:model-value="loadLogs"
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
              @update:model-value="loadLogs"
            >
              <template v-slot:prepend>
                <q-icon name="event" />
              </template>
            </q-input>

            <div class="col-12 col-md-3 flex items-center">
              <q-btn
                color="primary"
                label="Apply Filters"
                @click="loadLogs"
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
          :rows="logs"
          :columns="columns"
          :loading="loading"
          :pagination="pagination"
          @request="onRequest"
          row-key="id"
          flat
          class="audit-logs-table"
        >
          <template v-slot:body-cell-timestamp="props">
            <q-td :props="props">
              {{ formatDateTime(props.value) }}
            </q-td>
          </template>

          <template v-slot:body-cell-details="props">
            <q-td :props="props">
              <q-btn
                v-if="props.value"
                flat
                dense
                round
                icon="info"
                @click="showDetails(props.row)"
                size="sm"
              >
                <q-tooltip>View Details</q-tooltip>
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

          <template v-slot:no-data>
            <div class="full-width row flex-center text-grey-6 q-gutter-sm">
              <q-icon name="inbox" size="2em" />
              <span>No audit logs found</span>
            </div>
          </template>
        </q-table>
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
            <div>
              <strong>ID:</strong> {{ selectedLog?.id }}
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
              <span v-if="selectedLog.resource_id"> (ID: {{ selectedLog.resource_id }})</span>
            </div>
            <div>
              <strong>Timestamp:</strong> {{ formatDateTime(selectedLog?.timestamp) }}
            </div>
            <div v-if="selectedLog?.ip_address">
              <strong>IP Address:</strong> {{ selectedLog.ip_address }}
            </div>
            <div v-if="selectedLog?.details">
              <strong>Details:</strong>
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
import { ref, onMounted } from 'vue';
import { Notify } from 'quasar';
import { auditLogsAPI } from '../services/api';

export default {
  name: 'AuditLogs',
  setup() {
    const logs = ref([]);
    const loading = ref(false);
    const totalLogs = ref(0);
    const roleOptions = ref([]);
    const actionOptions = ref([]);
    const resourceTypeOptions = ref([]);
    const showDetailsDialog = ref(false);
    const selectedLog = ref(null);

    const filters = ref({
      role: null,
      full_name: null,
      username: null,
      action: null,
      resource_type: null,
      start_date: null,
      end_date: null,
    });

    const pagination = ref({
      page: 1,
      rowsPerPage: 50,
      rowsNumber: 0,
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
        name: 'resource_id',
        label: 'Resource ID',
        field: 'resource_id',
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
        label: 'Details',
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
      filters.value = {
        role: null,
        full_name: null,
        username: null,
        action: null,
        resource_type: null,
        start_date: null,
        end_date: null,
      };
      pagination.value.page = 1;
      loadLogs();
    };

    const onRequest = (props) => {
      pagination.value = props.pagination;
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

    onMounted(() => {
      loadFilterOptions();
      loadLogs();
    });

    return {
      logs,
      loading,
      totalLogs,
      filters,
      pagination,
      columns,
      roleOptions,
      actionOptions,
      resourceTypeOptions,
      showDetailsDialog,
      selectedLog,
      loadLogs,
      clearFilters,
      onRequest,
      showDetails,
      formatDateTime,
      formatDetails,
      getActionColor,
    };
  },
};
</script>

<style scoped>
.audit-logs-table {
  background: transparent;
}
</style>

