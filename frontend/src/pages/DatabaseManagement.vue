<template>
  <q-page class="q-pa-md">
    <div class="text-h4 q-mb-md text-weight-bold glass-text">
      <q-icon name="storage" color="primary" class="q-mr-sm" />
      Database Management
    </div>

    <q-banner class="glass-card q-pa-md q-mb-md bg-info text-white">
      <template v-slot:avatar>
        <q-icon name="info" />
      </template>
      Manage database backups, schedule automatic backups, and sync to online database for disaster recovery.
    </q-banner>

    <!-- Database Information -->
    <q-card class="q-mb-md glass-card" flat bordered>
      <q-card-section>
        <div class="text-h6 q-mb-md glass-text">
          <q-icon name="info" color="primary" class="q-mr-sm" />
          Database Information
        </div>
        <div v-if="loadingInfo" class="text-center q-pa-md">
          <q-spinner color="primary" size="3em" />
        </div>
        <div v-else-if="dbInfo" class="row q-gutter-md">
          <div class="col-12 col-md-4">
            <div class="text-caption text-grey-7">Database Mode</div>
            <div class="text-body1 text-weight-medium">{{ dbInfo.database_mode.toUpperCase() }}</div>
          </div>
          <div class="col-12 col-md-4">
            <div class="text-caption text-grey-7">Table Count</div>
            <div class="text-body1 text-weight-medium">{{ dbInfo.table_count }}</div>
          </div>
          <div class="col-12 col-md-4">
            <div class="text-caption text-grey-7">Database Size</div>
            <div class="text-body1 text-weight-medium">{{ dbInfo.size_mb }} MB</div>
          </div>
        </div>
        <q-btn
          flat
          color="primary"
          icon="refresh"
          label="Refresh Info"
          @click="loadDatabaseInfo"
          :loading="loadingInfo"
          class="q-mt-md"
        />
      </q-card-section>
    </q-card>

    <!-- Backup Section -->
    <q-card class="q-mb-md glass-card" flat bordered>
      <q-card-section>
        <div class="text-h6 q-mb-md glass-text">
          <q-icon name="backup" color="primary" class="q-mr-sm" />
          Database Backup
        </div>

        <!-- Immediate Backup -->
        <div class="q-mb-md">
          <div class="text-subtitle2 q-mb-sm">Immediate Backup</div>
          <q-btn
            color="primary"
            icon="download"
            label="Export Backup Now"
            @click="exportBackup"
            :loading="exporting"
            class="q-mr-sm"
          />
          <q-btn
            color="secondary"
            icon="upload"
            label="Import Backup"
            @click="showImportDialog = true"
            class="q-mr-sm"
          />
        </div>

        <!-- Backup Schedule Configuration -->
        <q-separator class="q-my-md" />
        <div class="text-subtitle2 q-mb-sm">Scheduled Backups</div>
        <div class="row q-gutter-md items-center">
          <q-toggle
            v-model="backupSchedule.enabled"
            label="Enable Scheduled Backups"
            @update:model-value="updateBackupSchedule"
            color="primary"
          />
          <q-input
            v-if="backupSchedule.enabled"
            v-model="backupSchedule.time"
            label="Backup Time(s) (HH:MM)"
            filled
            hint="24-hour format. Multiple times: comma-separated (e.g., 07:00,19:00 for 7am and 7pm)"
            class="col-12 col-md-6"
            :disable="savingSchedule"
          >
            <template v-slot:prepend>
              <q-icon name="schedule" />
            </template>
          </q-input>
          <q-btn
            v-if="backupSchedule.enabled"
            flat
            color="primary"
            icon="save"
            label="Save Schedule"
            @click="updateBackupSchedule"
            :loading="savingSchedule"
            class="q-ml-md"
          />
        </div>

        <!-- Backup Status -->
        <div v-if="backupStatus" class="q-mt-md">
          <q-separator class="q-my-md" />
          <div class="text-subtitle2 q-mb-sm">Backup Status</div>
          <div class="row q-gutter-md">
            <div class="col-12 col-md-6">
              <div class="text-caption text-grey-7">Scheduled Backup</div>
              <div class="text-body2">
                <q-icon
                  :name="backupStatus.scheduled_backup_enabled ? 'check_circle' : 'cancel'"
                  :color="backupStatus.scheduled_backup_enabled ? 'positive' : 'negative'"
                  class="q-mr-xs"
                />
                {{ backupStatus.scheduled_backup_enabled ? 'Enabled' : 'Disabled' }}
              </div>
              <div v-if="backupStatus.scheduled_backup_enabled" class="text-caption text-grey-7 q-mt-xs">
                Time: {{ backupStatus.scheduled_backup_time }}
              </div>
            </div>
            <div class="col-12 col-md-6">
              <div class="text-caption text-grey-7">Next Scheduled Backup(s)</div>
              <div class="text-body2">
                <div v-if="backupStatus.scheduler?.jobs && backupStatus.scheduler.jobs.length > 0">
                  <div v-for="(job, idx) in backupStatus.scheduler.jobs.filter(j => j.name?.includes('Backup'))" :key="job.id" class="q-mb-xs">
                    <span v-if="job.next_run">
                      {{ job.name }}: {{ formatDateTime(job.next_run) }}
                    </span>
                  </div>
                </div>
                <span v-else class="text-grey-7">Not scheduled</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Backup List -->
        <q-separator class="q-my-md" />
        <div class="text-subtitle2 q-mb-sm">Available Backups</div>
        <q-table
          :rows="backups"
          :columns="backupColumns"
          row-key="filename"
          :loading="loadingBackups"
          :pagination="{ rowsPerPage: 10 }"
          flat
          bordered
        >
          <template v-slot:body-cell-size="props">
            <q-td :props="props">
              {{ formatFileSize(props.value) }}
            </q-td>
          </template>
          <template v-slot:body-cell-actions="props">
            <q-td :props="props">
              <q-btn
                flat
                dense
                icon="download"
                color="primary"
                @click="downloadBackup(props.row.filename)"
                class="q-mr-xs"
              >
                <q-tooltip>Download</q-tooltip>
              </q-btn>
              <q-btn
                flat
                dense
                icon="delete"
                color="negative"
                @click="confirmDeleteBackup(props.row)"
              >
                <q-tooltip>Delete</q-tooltip>
              </q-btn>
            </q-td>
          </template>
        </q-table>
        <q-btn
          flat
          color="primary"
          icon="refresh"
          label="Refresh List"
          @click="loadBackups"
          :loading="loadingBackups"
          class="q-mt-md"
        />
      </q-card-section>
    </q-card>

    <!-- Online Sync Section -->
    <q-card class="q-mb-md glass-card" flat bordered>
      <q-card-section>
        <div class="text-h6 q-mb-md glass-text">
          <q-icon name="cloud_sync" color="primary" class="q-mr-sm" />
          Online Database Sync
        </div>

        <!-- Sync Status -->
        <div v-if="syncStatus" class="q-mb-md">
          <div class="row q-gutter-md">
            <div class="col-12 col-md-6">
              <div class="text-caption text-grey-7">Sync Status</div>
              <div class="text-body2">
                <q-icon
                  :name="syncStatus.status?.connected ? 'cloud_done' : 'cloud_off'"
                  :color="syncStatus.status?.connected ? 'positive' : 'negative'"
                  class="q-mr-xs"
                />
                {{ syncStatus.status?.connected ? 'Connected' : 'Disconnected' }}
              </div>
              <div v-if="syncStatus.status?.connected" class="text-caption text-grey-7 q-mt-xs">
                Database: {{ syncStatus.status?.database || 'N/A' }}
              </div>
            </div>
            <div class="col-12 col-md-6">
              <div class="text-caption text-grey-7">Sync Interval</div>
              <div class="text-body2">
                Every {{ syncStatus.sync_interval_minutes }} minutes
              </div>
            </div>
          </div>
        </div>

        <!-- Sync Actions -->
        <div class="q-mb-md">
          <q-btn
            color="primary"
            icon="sync"
            label="Test Connection"
            @click="testSyncConnection"
            :loading="testingConnection"
            class="q-mr-sm"
          />
          <q-btn
            color="secondary"
            icon="cloud_upload"
            label="Sync Now"
            @click="runSync"
            :loading="syncing"
            :disable="!syncStatus?.status?.connected"
          />
        </div>

        <q-banner
          v-if="syncStatus && !syncStatus.sync_enabled"
          class="bg-warning text-white q-mt-md"
          rounded
        >
          <template v-slot:avatar>
            <q-icon name="warning" />
          </template>
          Online sync is disabled. Configure sync settings in your .env file to enable.
          <template v-slot:action>
            <q-btn flat label="View Setup Guide" @click="showSyncGuide = true" />
          </template>
        </q-banner>
      </q-card-section>
    </q-card>

    <!-- Import Backup Dialog -->
    <q-dialog v-model="showImportDialog" persistent>
      <q-card style="min-width: 400px">
        <q-card-section>
          <div class="text-h6">Import Database Backup</div>
          <div class="text-caption text-negative q-mt-sm">
            Warning: This will replace your current database with the backup. Make sure you have a current backup before proceeding.
          </div>
        </q-card-section>

        <q-card-section>
          <q-file
            v-model="importFile"
            label="Select Backup File"
            filled
            accept=".db,.sql,.sql.gz"
          >
            <template v-slot:prepend>
              <q-icon name="attach_file" />
            </template>
          </q-file>
        </q-card-section>

        <q-card-actions align="right">
          <q-btn flat label="Cancel" color="primary" v-close-popup />
          <q-btn
            flat
            label="Import"
            color="negative"
            @click="importBackup"
            :loading="importing"
            :disable="!importFile"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Sync Setup Guide Dialog -->
    <q-dialog v-model="showSyncGuide" maximized>
      <q-card>
        <q-card-section>
          <div class="text-h6">Online Database Sync Setup Guide</div>
        </q-card-section>
        <q-card-section>
          <div class="text-body2" style="white-space: pre-wrap;">{{ syncGuideText }}</div>
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Close" color="primary" v-close-popup />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useQuasar } from 'quasar';
import { databaseAPI } from '../services/api';

const $q = useQuasar();

// State
const loadingInfo = ref(false);
const dbInfo = ref(null);
const exporting = ref(false);
const importing = ref(false);
const loadingBackups = ref(false);
const backups = ref([]);
const backupStatus = ref(null);
const savingSchedule = ref(false);
const syncStatus = ref(null);
const testingConnection = ref(false);
const syncing = ref(false);
const showImportDialog = ref(false);
const importFile = ref(null);
const showSyncGuide = ref(false);

const backupSchedule = ref({
  enabled: false,
  time: '07:00,19:00', // Default: 7am and 7pm
});

const backupColumns = [
  { name: 'filename', label: 'Filename', field: 'filename', align: 'left', sortable: true },
  { name: 'size', label: 'Size', field: 'size', align: 'right', sortable: true },
  { name: 'created_at', label: 'Created', field: 'created_at', align: 'left', sortable: true },
  { name: 'actions', label: 'Actions', field: 'actions', align: 'center' },
];

const syncGuideText = `To enable online database sync, add the following to your .env file:

# Online Sync Settings
SYNC_ENABLED=true
SYNC_REMOTE_HOST=your-remote-mysql-host.com
SYNC_REMOTE_PORT=3306
SYNC_REMOTE_USER=your_username
SYNC_REMOTE_PASSWORD=your_password
SYNC_REMOTE_DATABASE=hms_backup
SYNC_INTERVAL_MINUTES=60

After adding these settings, restart the application server.

See DATABASE_SYNC_SETUP.md for detailed setup instructions.`;

// Methods
const loadDatabaseInfo = async () => {
  loadingInfo.value = true;
  try {
    const response = await databaseAPI.getDatabaseInfo();
    dbInfo.value = response.data;
  } catch (error) {
    console.error('Error loading database info:', error);
    $q.notify({
      type: 'negative',
      message: 'Failed to load database information',
      position: 'top',
    });
  } finally {
    loadingInfo.value = false;
  }
};

const exportBackup = async () => {
  exporting.value = true;
  try {
    const response = await databaseAPI.exportBackup();
    
    // Create download link
    const blob = new Blob([response.data], { type: 'application/octet-stream' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    
    // Get filename from Content-Disposition header
    const contentDisposition = response.headers['content-disposition'];
    let filename = 'backup.db';
    if (contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename="?(.+)"?/);
      if (filenameMatch) {
        filename = filenameMatch[1];
      }
    }
    
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
    
    $q.notify({
      type: 'positive',
      message: 'Backup exported successfully',
      position: 'top',
    });
    
    // Refresh backup list
    await loadBackups();
  } catch (error) {
    console.error('Error exporting backup:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to export backup',
      position: 'top',
    });
  } finally {
    exporting.value = false;
  }
};

const importBackup = async () => {
  if (!importFile.value) {
    $q.notify({
      type: 'warning',
      message: 'Please select a backup file',
      position: 'top',
    });
    return;
  }

  $q.dialog({
    title: 'Confirm Import',
    message: 'This will replace your current database with the backup. This action cannot be undone. Are you sure?',
    cancel: true,
    persistent: true,
  }).onOk(async () => {
    importing.value = true;
    try {
      await databaseAPI.importBackup(importFile.value);
      $q.notify({
        type: 'positive',
        message: 'Backup imported successfully. Please refresh the page.',
        position: 'top',
        timeout: 5000,
      });
      showImportDialog.value = false;
      importFile.value = null;
      
      // Reload database info
      await loadDatabaseInfo();
    } catch (error) {
      console.error('Error importing backup:', error);
      $q.notify({
        type: 'negative',
        message: error.response?.data?.detail || 'Failed to import backup',
        position: 'top',
      });
    } finally {
      importing.value = false;
    }
  });
};

const loadBackups = async () => {
  loadingBackups.value = true;
  try {
    const response = await databaseAPI.listBackups();
    backups.value = response.data.backups || [];
  } catch (error) {
    console.error('Error loading backups:', error);
    $q.notify({
      type: 'negative',
      message: 'Failed to load backups',
      position: 'top',
    });
  } finally {
    loadingBackups.value = false;
  }
};

const downloadBackup = async (filename) => {
  try {
    // The backup is already on the server, we can construct a download URL
    // Or we can use the export endpoint with a specific backup
    $q.notify({
      type: 'info',
      message: 'Use the Export Backup button to download backups',
      position: 'top',
    });
  } catch (error) {
    console.error('Error downloading backup:', error);
    $q.notify({
      type: 'negative',
      message: 'Failed to download backup',
      position: 'top',
    });
  }
};

const confirmDeleteBackup = (backup) => {
  $q.dialog({
    title: 'Confirm Delete',
    message: `Are you sure you want to delete backup "${backup.filename}"?`,
    cancel: true,
    persistent: true,
  }).onOk(async () => {
    try {
      await databaseAPI.deleteBackup(backup.filename);
      $q.notify({
        type: 'positive',
        message: 'Backup deleted successfully',
        position: 'top',
      });
      await loadBackups();
    } catch (error) {
      console.error('Error deleting backup:', error);
      $q.notify({
        type: 'negative',
        message: error.response?.data?.detail || 'Failed to delete backup',
        position: 'top',
      });
    }
  });
};

const loadBackupStatus = async () => {
  try {
    const response = await databaseAPI.getBackupStatus();
    backupStatus.value = response.data;
    backupSchedule.value.enabled = response.data.scheduled_backup_enabled;
    backupSchedule.value.time = response.data.scheduled_backup_time || '07:00,19:00';
  } catch (error) {
    console.error('Error loading backup status:', error);
  }
};

const updateBackupSchedule = async () => {
  savingSchedule.value = true;
  try {
    await databaseAPI.configureBackupSchedule(backupSchedule.value);
    $q.notify({
      type: 'positive',
      message: 'Backup schedule updated successfully',
      position: 'top',
    });
    await loadBackupStatus();
  } catch (error) {
    console.error('Error updating backup schedule:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to update backup schedule',
      position: 'top',
    });
  } finally {
    savingSchedule.value = false;
  }
};

const loadSyncStatus = async () => {
  try {
    const response = await databaseAPI.getSyncStatus();
    syncStatus.value = response.data;
  } catch (error) {
    console.error('Error loading sync status:', error);
  }
};

const testSyncConnection = async () => {
  testingConnection.value = true;
  try {
    const response = await databaseAPI.testSyncConnection();
    if (response.data.connected) {
      $q.notify({
        type: 'positive',
        message: 'Connection test successful',
        position: 'top',
      });
    } else {
      $q.notify({
        type: 'negative',
        message: response.data.message || 'Connection test failed',
        position: 'top',
      });
    }
    await loadSyncStatus();
  } catch (error) {
    console.error('Error testing sync connection:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to test connection',
      position: 'top',
    });
  } finally {
    testingConnection.value = false;
  }
};

const runSync = async () => {
  syncing.value = true;
  try {
    const response = await databaseAPI.runSync();
    $q.notify({
      type: 'positive',
      message: response.data.message || 'Sync completed successfully',
      position: 'top',
    });
    await loadSyncStatus();
  } catch (error) {
    console.error('Error running sync:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to sync database',
      position: 'top',
    });
  } finally {
    syncing.value = false;
  }
};

const formatFileSize = (bytes) => {
  if (!bytes) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
};

const formatDateTime = (dateString) => {
  if (!dateString) return 'N/A';
  const date = new Date(dateString);
  return date.toLocaleString();
};

// Lifecycle
onMounted(async () => {
  await Promise.all([
    loadDatabaseInfo(),
    loadBackups(),
    loadBackupStatus(),
    loadSyncStatus(),
  ]);
});
</script>

<style scoped>
.glass-text {
  color: rgba(0, 0, 0, 0.87);
}
</style>

