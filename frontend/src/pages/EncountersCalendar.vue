<template>
  <q-page class="hms-page calendar-page">
    <HmsPageHeader title="Reservations" :subtitle="formattedDate">
      <template #actions>
        <HmsButton variant="secondary" size="sm" @click="shiftDay(-1)">
          <ChevronLeft :size="14" />
        </HmsButton>
        <HmsButton variant="secondary" size="sm" @click="setToday">Today</HmsButton>
        <HmsButton variant="secondary" size="sm" @click="shiftDay(1)">
          <ChevronRight :size="14" />
        </HmsButton>
      </template>
    </HmsPageHeader>

    <div class="cal-tabs">
      <button type="button" class="cal-tab active">Calendar</button>
      <button type="button" class="cal-tab" disabled title="Coming soon">Log history</button>
    </div>

    <div class="cal-toolbar">
      <div class="toolbar-left">
        <CalendarDays :size="15" class="count-icon" />
        <span class="count-label">
          {{ filteredEncounters.length }} total appointment{{ filteredEncounters.length === 1 ? '' : 's' }}
        </span>
      </div>

      <div class="toolbar-controls">
        <input
          v-model="selectedDate"
          type="date"
          class="date-input"
          @change="loadEncounters"
        />

        <div class="view-toggle" role="group" aria-label="Calendar view">
          <button type="button" class="view-btn" :class="{ on: viewMode === 'day' }" @click="viewMode = 'day'">
            Day
          </button>
          <button type="button" class="view-btn" :class="{ on: viewMode === 'week' }" @click="viewMode = 'week'">
            Week
          </button>
        </div>

        <select v-model="selectedDepartment" class="dept-select">
          <option
            v-for="opt in departmentOptions"
            :key="String(opt.value ?? 'all')"
            :value="opt.value === null ? '' : opt.value"
          >
            {{ opt.label }}
          </option>
        </select>

        <input
          v-model="cardSearch"
          type="search"
          class="filter-input"
          placeholder="Filter by card…"
        />
      </div>
    </div>

    <!-- Day grid -->
    <div v-if="viewMode === 'day'" class="cal-board" :class="{ loading }">
      <div v-if="loading" class="board-loading">
        <HmsSkeleton :lines="8" />
      </div>

      <template v-else-if="departmentColumns.length">
        <div class="cal-grid" :style="gridStyle">
          <!-- Corner + time gutter header -->
          <div class="grid-corner">
            <span class="tz-label">Local</span>
          </div>

          <div
            v-for="col in departmentColumns"
            :key="col.key"
            class="col-header"
          >
            <div class="col-avatar">{{ col.initials }}</div>
            <div class="col-meta">
              <div class="col-name">{{ col.label }}</div>
              <div class="col-count">{{ col.items.length }} appointment{{ col.items.length === 1 ? '' : 's' }}</div>
            </div>
          </div>

          <!-- Time labels -->
          <div class="time-gutter" :style="{ gridRow: `2 / span ${hours.length}` }">
            <div
              v-for="hour in hours"
              :key="'t-' + hour"
              class="time-slot"
              :style="{ height: hourHeight + 'px' }"
            >
              {{ formatHourLabel(hour) }}
            </div>
          </div>

          <!-- Columns -->
          <div
            v-for="(col, colIndex) in departmentColumns"
            :key="'c-' + col.key"
            class="day-column"
            :style="{ gridColumn: colIndex + 2, gridRow: `2 / span ${hours.length}`, height: totalHeight + 'px' }"
          >
            <div
              v-for="hour in hours"
              :key="col.key + '-' + hour"
              class="hour-line"
              :style="{ top: (hour - dayStart) * hourHeight + 'px', height: hourHeight + 'px' }"
            />

            <button
              v-for="item in col.items"
              :key="item.id"
              type="button"
              class="appt-card"
              :class="statusTone(item.status)"
              :style="cardStyle(item)"
              @click="viewEncounter(item)"
            >
              <div class="appt-title">{{ displayPatient(item) }}</div>
              <div class="appt-time">{{ formatTime(item.created_at) }}</div>
              <div class="appt-meta">
                <span class="status-dot" />
                <span class="status-text">{{ statusLabel(item.status) }}</span>
              </div>
              <div v-if="item.procedure_name || item.department" class="appt-tag">
                {{ item.procedure_name || item.department }}
              </div>
              <div class="appt-actions" @click.stop>
                <button type="button" class="mini-btn" title="Edit" @click="editEncounter(item)">Edit</button>
                <button
                  v-if="isAdmin"
                  type="button"
                  class="mini-btn danger"
                  title="Archive"
                  @click="deleteEncounterConfirm(item)"
                >
                  Archive
                </button>
              </div>
            </button>

            <div
              v-if="showNowLine"
              class="now-line"
              :style="{ top: nowOffset + 'px' }"
            >
              <span class="now-label">{{ nowLabel }}</span>
            </div>
          </div>
        </div>
      </template>

      <HmsEmptyState
        v-else
        title="No appointments for this date"
        description="Try another day or clear your filters."
      />
    </div>

    <!-- Week list view -->
    <div v-else class="week-board">
      <div v-if="loading" class="board-loading"><HmsSkeleton :lines="6" /></div>
      <div v-else class="week-days">
        <div v-for="day in weekDays" :key="day.iso" class="week-day">
          <div class="week-day-head">
            <div class="week-day-title">{{ day.label }}</div>
            <div class="week-day-count">{{ day.items.length }}</div>
          </div>
          <button
            v-for="item in day.items"
            :key="item.id"
            type="button"
            class="week-appt"
            :class="statusTone(item.status)"
            @click="viewEncounter(item)"
          >
            <div class="week-appt-title">{{ displayPatient(item) }}</div>
            <div class="week-appt-sub">
              {{ formatTime(item.created_at) }} · {{ item.department || 'General' }}
            </div>
          </button>
          <div v-if="!day.items.length" class="week-empty">No appointments</div>
        </div>
      </div>
    </div>

    <!-- Edit Encounter Dialog -->
    <q-dialog v-model="showEditDialog" persistent>
      <q-card style="min-width: 500px">
        <q-card-section>
          <div class="text-h6">Edit Appointment #{{ currentEncounter?.id }}</div>
        </q-card-section>

        <q-card-section>
          <q-form @submit="saveEncounterEdit" class="q-gutter-md">
            <q-select
              v-model="editForm.department"
              filled
              :options="departmentOptionsForEdit"
              label="Department *"
              lazy-rules
              :rules="[(val) => !!val || 'Required']"
              emit-value
              map-options
              @update:model-value="onDepartmentSelected"
            >
              <template v-slot:option="scope">
                <q-item v-bind="scope.itemProps">
                  <q-item-section>
                    <q-item-label>{{ scope.opt.label || scope.opt }}</q-item-label>
                  </q-item-section>
                </q-item>
              </template>
            </q-select>

            <q-select
              v-model="selectedProcedure"
              filled
              :options="procedureOptions"
              label="Procedure (Service Name)"
              option-label="service_name"
              option-value="g_drg_code"
              :disable="!editForm.department"
              @update:model-value="onProcedureSelected"
              hint="Select the procedure - GDRG code and name will be auto-filled"
              use-input
              input-debounce="300"
              @filter="filterProcedures"
              clearable
            >
              <template v-slot:no-option>
                <q-item>
                  <q-item-section class="text-grey">
                    {{
                      editForm.department
                        ? 'No procedures found. Try a different search term.'
                        : 'Please select a Department first'
                    }}
                  </q-item-section>
                </q-item>
              </template>
            </q-select>

            <q-input v-model="editForm.ccc_number" filled label="CCC Number" />
            <q-select v-model="editForm.status" filled :options="statusOptions" label="Status" />
            <div>
              <q-btn label="Save Changes" type="submit" color="primary" />
              <q-btn
                label="Cancel"
                flat
                color="grey"
                class="q-ml-sm"
                @click="showEditDialog = false"
              />
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue';
import { useRouter } from 'vue-router';
import { ChevronLeft, ChevronRight, CalendarDays } from 'lucide-vue-next';
import { encountersAPI, priceListAPI } from '../services/api';
import { useEncountersStore } from '../stores/encounters';
import { useAuthStore } from '../stores/auth';
import { useQuasar } from 'quasar';
import HmsPageHeader from '../components/ui/HmsPageHeader.vue';
import HmsButton from '../components/ui/HmsButton.vue';
import HmsEmptyState from '../components/ui/HmsEmptyState.vue';
import HmsSkeleton from '../components/ui/HmsSkeleton.vue';

const $q = useQuasar();
const router = useRouter();
const encountersStore = useEncountersStore();
const authStore = useAuthStore();

const selectedDate = ref('');
const encounters = ref([]);
const loading = ref(false);
const cardSearch = ref('');
const selectedDepartment = ref('');
const departmentOptions = ref([]);
const loadingDepartments = ref(false);
const viewMode = ref('day');
const nowTick = ref(Date.now());
let nowTimer = null;

const dayStart = 7;
const dayEnd = 20;
const hourHeight = 76;
const hours = Array.from({ length: dayEnd - dayStart }, (_, i) => dayStart + i);
const totalHeight = hours.length * hourHeight;

const formattedDate = computed(() => {
  if (!selectedDate.value) return 'Select a date';
  const date = new Date(`${selectedDate.value}T12:00:00`);
  return date.toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
});

const filteredEncounters = computed(() => {
  let filtered = encounters.value;

  if (selectedDepartment.value) {
    filtered = filtered.filter(
      (e) => (e.department || '').toLowerCase() === (selectedDepartment.value || '').toLowerCase()
    );
  }

  const needle = (cardSearch.value || '').toLowerCase().trim();
  if (needle) {
    filtered = filtered.filter((e) =>
      (e.patient_card_number || '').toLowerCase().includes(needle)
    );
  }

  return filtered;
});

const departmentColumns = computed(() => {
  const map = new Map();
  for (const item of filteredEncounters.value) {
    const label = item.department || 'General';
    const key = label.toLowerCase();
    if (!map.has(key)) {
      map.set(key, {
        key,
        label,
        initials: label
          .split(/\s+/)
          .map((w) => w[0])
          .join('')
          .slice(0, 2)
          .toUpperCase(),
        items: [],
      });
    }
    map.get(key).items.push(item);
  }

  if (selectedDepartment.value && !map.size) {
    const label = selectedDepartment.value;
    return [
      {
        key: label.toLowerCase(),
        label,
        initials: label.slice(0, 2).toUpperCase(),
        items: [],
      },
    ];
  }

  return Array.from(map.values()).sort((a, b) => a.label.localeCompare(b.label));
});

const gridStyle = computed(() => ({
  gridTemplateColumns: `64px repeat(${Math.max(departmentColumns.value.length, 1)}, minmax(180px, 1fr))`,
}));

const isTodaySelected = computed(() => {
  const today = new Date().toISOString().split('T')[0];
  return selectedDate.value === today;
});

const showNowLine = computed(() => isTodaySelected.value && viewMode.value === 'day');

const nowOffset = computed(() => {
  void nowTick.value;
  const d = new Date();
  const minutes = d.getHours() * 60 + d.getMinutes() - dayStart * 60;
  return Math.min(Math.max(minutes * (hourHeight / 60), 0), totalHeight);
});

const nowLabel = computed(() => {
  void nowTick.value;
  return new Date().toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
});

const weekDays = computed(() => {
  if (!selectedDate.value) return [];
  const base = new Date(`${selectedDate.value}T12:00:00`);
  const day = base.getDay();
  const mondayOffset = day === 0 ? -6 : 1 - day;
  const monday = new Date(base);
  monday.setDate(base.getDate() + mondayOffset);

  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(monday);
    d.setDate(monday.getDate() + i);
    const iso = d.toISOString().split('T')[0];
    const items = filteredEncounters.value.filter((e) => {
      if (!e.created_at) return false;
      return new Date(e.created_at).toISOString().split('T')[0] === iso;
    });
    return {
      iso,
      label: d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' }),
      items,
    };
  });
});

watch(viewMode, async (mode) => {
  if (mode === 'week') {
    await loadWeekEncounters();
  } else {
    await loadEncounters();
  }
});

const setToday = () => {
  const today = new Date();
  selectedDate.value = today.toISOString().split('T')[0];
  if (viewMode.value === 'week') loadWeekEncounters();
  else loadEncounters();
};

const shiftDay = (delta) => {
  if (!selectedDate.value) {
    setToday();
    return;
  }
  const d = new Date(`${selectedDate.value}T12:00:00`);
  d.setDate(d.getDate() + delta);
  selectedDate.value = d.toISOString().split('T')[0];
  if (viewMode.value === 'week') loadWeekEncounters();
  else loadEncounters();
};

const formatHourLabel = (hour) => {
  const d = new Date();
  d.setHours(hour, 0, 0, 0);
  return d.toLocaleTimeString('en-US', { hour: 'numeric', hour12: true }).toLowerCase();
};

const formatTime = (dateString) => {
  if (!dateString) return '';
  const date = new Date(dateString);
  return date.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  });
};

const displayPatient = (item) => {
  const name = (item.patient_name || 'Patient').toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase());
  return name;
};

const statusLabel = (status) => {
  const map = {
    draft: 'Draft',
    in_consultation: 'In consult',
    awaiting_services: 'Awaiting',
    finalized: 'Finished',
  };
  return map[status] || status || 'Open';
};

const statusTone = (status) => {
  if (status === 'finalized') return 'tone-green';
  if (status === 'in_consultation') return 'tone-blue';
  if (status === 'awaiting_services') return 'tone-purple';
  if (status === 'draft') return 'tone-pink';
  return 'tone-slate';
};

const cardStyle = (item) => {
  const d = item.created_at ? new Date(item.created_at) : new Date(`${selectedDate.value}T09:00:00`);
  const minutes = d.getHours() * 60 + d.getMinutes() - dayStart * 60;
  const top = Math.min(Math.max(minutes * (hourHeight / 60), 4), totalHeight - 64);
  return {
    top: `${top}px`,
    height: '68px',
  };
};

const loadEncounters = async () => {
  if (!selectedDate.value) {
    encounters.value = [];
    return;
  }

  loading.value = true;
  try {
    const response = await encountersAPI.getByDate(selectedDate.value);
    encounters.value = response.data;
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to load encounters',
    });
    encounters.value = [];
  } finally {
    loading.value = false;
  }
};

const loadWeekEncounters = async () => {
  if (!selectedDate.value) return;
  loading.value = true;
  try {
    const base = new Date(`${selectedDate.value}T12:00:00`);
    const day = base.getDay();
    const mondayOffset = day === 0 ? -6 : 1 - day;
    const monday = new Date(base);
    monday.setDate(base.getDate() + mondayOffset);

    const days = Array.from({ length: 7 }, (_, i) => {
      const d = new Date(monday);
      d.setDate(monday.getDate() + i);
      return d.toISOString().split('T')[0];
    });

    const results = await Promise.all(
      days.map((iso) => encountersAPI.getByDate(iso).then((r) => r.data).catch(() => []))
    );
    encounters.value = results.flat();
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to load week',
    });
    encounters.value = [];
  } finally {
    loading.value = false;
  }
};

const isAdmin = computed(() => authStore.userRole === 'Admin');

const viewEncounter = (encounter) => {
  if (!isAdmin.value && encounter.status === 'finalized') {
    router.push({ path: `/consultation/${encounter.id}`, query: { readonly: '1' } });
  } else {
    router.push(`/consultation/${encounter.id}`);
  }
};

const editEncounter = async (encounter) => {
  showEditDialog.value = true;
  currentEncounter.value = encounter;
  editForm.department = encounter.department;
  editForm.ccc_number = encounter.ccc_number || '';
  editForm.status = encounter.status;
  editForm.procedure_g_drg_code = encounter.procedure_g_drg_code || '';
  editForm.procedure_name = encounter.procedure_name || '';

  selectedProcedure.value = null;
  allProcedures.value = [];
  procedureOptions.value = [];

  if (encounter.department) {
    await loadProceduresForDepartment(encounter.department);

    if (encounter.procedure_g_drg_code || encounter.procedure_name) {
      const matchingProcedure = allProcedures.value.find(
        (p) =>
          p.g_drg_code === encounter.procedure_g_drg_code ||
          p.service_name === encounter.procedure_name
      );
      if (matchingProcedure) {
        selectedProcedure.value = matchingProcedure;
      }
    }
  }
};

const deleteEncounterConfirm = (encounter) => {
  $q.dialog({
    title: 'Archive Appointment',
    message: `Are you sure you want to archive Appointment #${encounter.id} for ${encounter.patient_name}? This action cannot be undone.`,
    cancel: true,
    persistent: true,
    ok: {
      label: 'Archive',
      color: 'negative',
    },
  }).onOk(async () => {
    try {
      await encountersStore.deleteEncounter(encounter.id);
      if (viewMode.value === 'week') await loadWeekEncounters();
      else await loadEncounters();
    } catch (error) {
      // Error handled in store
    }
  });
};

const showEditDialog = ref(false);
const currentEncounter = ref(null);
const editForm = reactive({
  department: '',
  ccc_number: '',
  status: '',
  procedure_g_drg_code: '',
  procedure_name: '',
});

const allProcedures = ref([]);
const procedureOptions = ref([]);
const selectedProcedure = ref(null);

const statusOptions = ['draft', 'in_consultation', 'awaiting_services', 'finalized'];

const departmentOptionsForEdit = computed(() => {
  return departmentOptions.value.filter((opt) => opt.value !== null);
});

const loadServiceTypes = async () => {
  loadingDepartments.value = true;
  try {
    const response = await priceListAPI.getServiceTypes();
    departmentOptions.value = [
      { label: 'All Departments', value: null },
      ...response.data.map((dept) => ({ label: dept, value: dept })),
    ];
  } catch (error) {
    console.error('Failed to load service types:', error);
    departmentOptions.value = [
      { label: 'All Departments', value: null },
      { label: 'General', value: 'General' },
      { label: 'Pediatrics', value: 'Pediatrics' },
      { label: 'ENT', value: 'ENT' },
      { label: 'Eye', value: 'Eye' },
      { label: 'Emergency', value: 'Emergency' },
    ];
  } finally {
    loadingDepartments.value = false;
  }
};

const saveEncounterEdit = async () => {
  if (!currentEncounter.value) return;

  const updateData = {};
  if (editForm.department !== currentEncounter.value.department) {
    updateData.department = editForm.department;
  }
  if (editForm.ccc_number !== currentEncounter.value.ccc_number) {
    updateData.ccc_number = editForm.ccc_number || null;
  }
  if (editForm.status !== currentEncounter.value.status) {
    updateData.status = editForm.status;
  }
  if (editForm.procedure_g_drg_code !== (currentEncounter.value.procedure_g_drg_code || '')) {
    updateData.procedure_g_drg_code = editForm.procedure_g_drg_code || null;
  }
  if (editForm.procedure_name !== (currentEncounter.value.procedure_name || '')) {
    updateData.procedure_name = editForm.procedure_name || null;
  }

  if (Object.keys(updateData).length === 0) {
    $q.notify({
      type: 'info',
      message: 'No changes detected',
    });
    showEditDialog.value = false;
    return;
  }

  try {
    await encountersStore.updateEncounter(currentEncounter.value.id, updateData);
    showEditDialog.value = false;
    if (viewMode.value === 'week') await loadWeekEncounters();
    else await loadEncounters();
  } catch (error) {
    // Error handled in store
  }
};

const onDepartmentSelected = async (department) => {
  if (!department) {
    allProcedures.value = [];
    procedureOptions.value = [];
    selectedProcedure.value = null;
    editForm.procedure_g_drg_code = '';
    editForm.procedure_name = '';
    return;
  }

  await loadProceduresForDepartment(department);
  selectedProcedure.value = null;
  editForm.procedure_g_drg_code = '';
  editForm.procedure_name = '';
};

const loadProceduresForDepartment = async (department) => {
  try {
    const response = await priceListAPI.getProceduresByServiceType(department);
    let procedures = [];
    if (Array.isArray(response.data)) {
      procedures = response.data;
    } else if (response.data && typeof response.data === 'object') {
      procedures = response.data[department] || [];
    }
    allProcedures.value = procedures;
    procedureOptions.value = allProcedures.value;
  } catch (error) {
    console.error('Failed to load procedures:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to load procedures',
    });
    allProcedures.value = [];
    procedureOptions.value = [];
  }
};

const filterProcedures = (val, update) => {
  if (val === '') {
    update(() => {
      procedureOptions.value = allProcedures.value;
    });
    return;
  }

  update(() => {
    const needle = val.toLowerCase();
    procedureOptions.value = allProcedures.value.filter(
      (p) =>
        p.service_name.toLowerCase().indexOf(needle) > -1 ||
        (p.g_drg_code && p.g_drg_code.toLowerCase().indexOf(needle) > -1)
    );
  });
};

const onProcedureSelected = (procedure) => {
  if (procedure && typeof procedure === 'object') {
    editForm.procedure_g_drg_code = procedure.g_drg_code || '';
    editForm.procedure_name = procedure.service_name || '';
  } else if (procedure) {
    const proc = allProcedures.value.find((p) => p.g_drg_code === procedure);
    if (proc) {
      editForm.procedure_g_drg_code = proc.g_drg_code || '';
      editForm.procedure_name = proc.service_name || '';
    }
  } else {
    editForm.procedure_g_drg_code = '';
    editForm.procedure_name = '';
  }
};

onMounted(async () => {
  await loadServiceTypes();
  setToday();
  nowTimer = setInterval(() => {
    nowTick.value = Date.now();
  }, 60000);
});

onUnmounted(() => {
  if (nowTimer) clearInterval(nowTimer);
});
</script>

<style scoped>
.calendar-page {
  max-width: none;
}

.cal-tabs {
  display: flex;
  gap: 1.25rem;
  margin: -0.35rem 0 0.95rem;
  border-bottom: 1px solid var(--hms-border);
}

.cal-tab {
  border: none;
  background: transparent;
  padding: 0.55rem 0.1rem 0.7rem;
  font-family: inherit;
  font-size: var(--hms-text-sm);
  font-weight: 650;
  color: var(--hms-text-muted);
  cursor: pointer;
  position: relative;
}

.cal-tab.active {
  color: var(--hms-accent);
}

.cal-tab.active::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  bottom: -1px;
  height: 2px;
  background: var(--hms-accent);
  border-radius: 2px 2px 0 0;
}

.cal-tab:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.cal-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.95rem;
}

.toolbar-left {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  color: var(--hms-text-muted);
  font-size: var(--hms-text-sm);
  font-weight: 600;
}

.count-icon {
  flex-shrink: 0;
}

.toolbar-controls {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}

.date-input,
.dept-select,
.filter-input {
  height: 2.15rem;
  border-radius: var(--hms-radius-lg);
  border: 1px solid var(--hms-border);
  background: var(--hms-panel-bg);
  color: var(--hms-text-primary);
  font-family: inherit;
  font-size: var(--hms-text-sm);
  padding: 0 0.7rem;
}

.filter-input {
  min-width: 140px;
}

.view-toggle {
  display: inline-flex;
  padding: 0.15rem;
  border-radius: var(--hms-radius-lg);
  background: var(--hms-surface);
  border: 1px solid var(--hms-border);
}

.view-btn {
  border: none;
  background: transparent;
  color: var(--hms-text-secondary);
  font-family: inherit;
  font-size: var(--hms-text-sm);
  font-weight: 650;
  padding: 0.35rem 0.7rem;
  border-radius: var(--hms-radius-md);
  cursor: pointer;
}

.view-btn.on {
  background: var(--hms-panel-bg);
  color: var(--hms-accent);
  box-shadow: var(--hms-shadow-sm);
}

.cal-board,
.week-board {
  background: var(--hms-panel-bg);
  border: 1px solid var(--hms-border);
  border-radius: var(--hms-radius-xl);
  box-shadow: var(--hms-shadow-md);
  overflow: hidden;
  min-height: 420px;
}

.board-loading {
  padding: 1.25rem;
}

.cal-grid {
  display: grid;
  min-width: 720px;
  overflow-x: auto;
}

.grid-corner,
.col-header {
  position: sticky;
  top: 0;
  z-index: 3;
  background: var(--hms-panel-bg);
  border-bottom: 1px solid var(--hms-border);
  padding: 0.75rem 0.85rem;
}

.grid-corner {
  display: flex;
  align-items: flex-end;
}

.tz-label {
  font-size: 0.65rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--hms-text-muted);
}

.col-header {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  border-left: 1px solid var(--hms-border);
}

.col-avatar {
  width: 2.15rem;
  height: 2.15rem;
  border-radius: 9999px;
  background: var(--hms-accent-muted);
  color: var(--hms-accent);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 0.68rem;
  font-weight: 750;
  flex-shrink: 0;
}

.col-name {
  font-size: var(--hms-text-sm);
  font-weight: 700;
  color: var(--hms-text-primary);
}

.col-count {
  margin-top: 0.1rem;
  font-size: var(--hms-text-xs);
  color: var(--hms-text-muted);
}

.time-gutter {
  border-right: 1px solid var(--hms-border);
  background: var(--hms-panel-bg);
}

.time-slot {
  padding: 0.35rem 0.5rem 0 0;
  text-align: right;
  font-size: 0.68rem;
  font-weight: 650;
  color: var(--hms-text-muted);
  box-sizing: border-box;
}

.day-column {
  position: relative;
  border-left: 1px solid var(--hms-border);
  background:
    repeating-linear-gradient(
      to bottom,
      transparent,
      transparent calc(var(--hour-h, 76px) - 1px),
      var(--hms-border) calc(var(--hour-h, 76px) - 1px),
      var(--hms-border) var(--hour-h, 76px)
    );
}

.hour-line {
  position: absolute;
  left: 0;
  right: 0;
  pointer-events: none;
}

.appt-card {
  position: absolute;
  left: 0.4rem;
  right: 0.4rem;
  z-index: 2;
  border: 1px solid transparent;
  border-radius: 12px;
  padding: 0.45rem 0.55rem;
  text-align: left;
  cursor: pointer;
  font-family: inherit;
  overflow: hidden;
  box-shadow: var(--hms-shadow-sm);
  transition: transform var(--hms-duration-fast) var(--hms-ease-out), box-shadow var(--hms-duration-fast) var(--hms-ease-out);
}

.appt-card:hover {
  transform: translateY(-1px);
  box-shadow: var(--hms-shadow-md);
  z-index: 4;
}

.appt-title {
  font-size: var(--hms-text-sm);
  font-weight: 750;
  color: var(--hms-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.appt-time {
  margin-top: 0.1rem;
  font-size: 0.68rem;
  font-weight: 600;
  color: var(--hms-text-secondary);
}

.appt-meta {
  margin-top: 0.25rem;
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.65rem;
  font-weight: 700;
  color: var(--hms-text-secondary);
}

.status-dot {
  width: 0.4rem;
  height: 0.4rem;
  border-radius: 9999px;
  background: currentColor;
}

.appt-tag {
  margin-top: 0.25rem;
  display: inline-flex;
  padding: 0.12rem 0.4rem;
  border-radius: var(--hms-radius-full);
  background: rgba(255, 255, 255, 0.55);
  font-size: 0.62rem;
  font-weight: 700;
  color: var(--hms-text-secondary);
}

.appt-actions {
  display: none;
  gap: 0.25rem;
  margin-top: 0.3rem;
}

.appt-card:hover .appt-actions {
  display: flex;
}

.mini-btn {
  border: none;
  background: rgba(255, 255, 255, 0.7);
  color: var(--hms-text-primary);
  font-family: inherit;
  font-size: 0.62rem;
  font-weight: 700;
  padding: 0.15rem 0.4rem;
  border-radius: 6px;
  cursor: pointer;
}

.mini-btn.danger {
  color: var(--hms-critical);
}

.tone-pink {
  background: #fce7f3;
  border-color: #f9a8d4;
  color: #9d174d;
}

.tone-green {
  background: #dcfce7;
  border-color: #86efac;
  color: #166534;
}

.tone-blue {
  background: #dbeafe;
  border-color: #93c5fd;
  color: #1d4ed8;
}

.tone-purple {
  background: #ede9fe;
  border-color: #c4b5fd;
  color: #6d28d9;
}

.tone-slate {
  background: #f1f5f9;
  border-color: #cbd5e1;
  color: #334155;
}

.body--dark .tone-pink,
.body--dark .tone-green,
.body--dark .tone-blue,
.body--dark .tone-purple,
.body--dark .tone-slate {
  background: var(--hms-surface);
  border-color: var(--hms-border-strong);
  color: var(--hms-text-primary);
}

.now-line {
  position: absolute;
  left: 0;
  right: 0;
  height: 2px;
  background: #ef4444;
  z-index: 5;
  pointer-events: none;
}

.now-label {
  position: absolute;
  left: 0.35rem;
  top: -0.75rem;
  padding: 0.1rem 0.35rem;
  border-radius: 6px;
  background: #111827;
  color: #fff;
  font-size: 0.62rem;
  font-weight: 700;
}

.week-days {
  display: grid;
  grid-template-columns: repeat(7, minmax(140px, 1fr));
  gap: 0;
  overflow-x: auto;
}

.week-day {
  min-height: 320px;
  padding: 0.75rem;
  border-right: 1px solid var(--hms-border);
}

.week-day:last-child {
  border-right: none;
}

.week-day-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 0.65rem;
}

.week-day-title {
  font-size: var(--hms-text-sm);
  font-weight: 700;
  color: var(--hms-text-primary);
}

.week-day-count {
  font-size: var(--hms-text-xs);
  color: var(--hms-text-muted);
  font-weight: 650;
}

.week-appt {
  width: 100%;
  display: block;
  text-align: left;
  border: 1px solid transparent;
  border-radius: 10px;
  padding: 0.55rem 0.6rem;
  margin-bottom: 0.45rem;
  font-family: inherit;
  cursor: pointer;
}

.week-appt-title {
  font-size: var(--hms-text-sm);
  font-weight: 700;
}

.week-appt-sub {
  margin-top: 0.15rem;
  font-size: 0.68rem;
  opacity: 0.8;
}

.week-empty {
  font-size: var(--hms-text-xs);
  color: var(--hms-text-muted);
  padding: 0.5rem 0;
}

@media (max-width: 900px) {
  .cal-toolbar {
    align-items: stretch;
  }

  .toolbar-controls {
    width: 100%;
  }

  .date-input,
  .dept-select,
  .filter-input {
    flex: 1;
    min-width: 0;
  }

  .week-days {
    grid-template-columns: 1fr;
  }

  .week-day {
    min-height: 0;
    border-right: none;
    border-bottom: 1px solid var(--hms-border);
  }
}
</style>
