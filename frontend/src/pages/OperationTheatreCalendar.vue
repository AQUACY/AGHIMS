<template>
  <q-page class="hms-page calendar-page ot-calendar-page">
    <HmsPageHeader title="Operation theatre" :subtitle="formattedDate">
      <template #actions>
        <HmsButton variant="secondary" size="sm" @click="shiftDay(-1)">
          <ChevronLeft :size="14" />
        </HmsButton>
        <HmsButton variant="secondary" size="sm" @click="setToday">Today</HmsButton>
        <HmsButton variant="secondary" size="sm" @click="shiftDay(1)">
          <ChevronRight :size="14" />
        </HmsButton>
        <HmsButton variant="ghost" size="sm" @click="$router.push('/ipd')">Back to IPD</HmsButton>
      </template>
    </HmsPageHeader>

    <div class="cal-tabs">
      <button type="button" class="cal-tab active">Theatre schedule</button>
      <button type="button" class="cal-tab" disabled title="Coming soon">Log history</button>
    </div>

    <div class="cal-toolbar">
      <div class="toolbar-left">
        <CalendarDays :size="15" class="count-icon" />
        <span class="count-label">
          {{ filteredSurgeries.length }} operation{{ filteredSurgeries.length === 1 ? '' : 's' }}
        </span>
        <HmsBadge tone="warning">{{ pendingCount }} pending</HmsBadge>
        <HmsBadge tone="success">{{ completedCount }} done</HmsBadge>
      </div>

      <div class="toolbar-controls">
        <input
          v-model="selectedDate"
          type="date"
          class="date-input"
          :disabled="filtersLocked"
          @change="onDatePicked"
        />

        <div class="view-toggle" role="group" aria-label="Calendar view">
          <button type="button" class="view-btn" :class="{ on: viewMode === 'day' }" @click="setViewMode('day')">
            Day
          </button>
          <button type="button" class="view-btn" :class="{ on: viewMode === 'week' }" @click="setViewMode('week')">
            Week
          </button>
        </div>

        <select v-model="selectedWard" class="dept-select">
          <option value="">All wards</option>
          <option v-for="w in wardOptions" :key="w" :value="w">{{ w }}</option>
        </select>

        <input
          v-model="cardSearch"
          type="search"
          class="filter-input"
          placeholder="Filter by card…"
        />

        <HmsButton
          :variant="filtersLocked ? 'soft' : 'ghost'"
          size="sm"
          @click="toggleFiltersLock"
        >
          {{ filtersLocked ? 'Unlock' : 'Lock' }}
        </HmsButton>
      </div>
    </div>

    <div v-if="viewMode === 'day'" class="cal-board" :class="{ loading }">
      <div v-if="loading" class="board-loading">
        <HmsSkeleton :lines="8" />
      </div>

      <template v-else-if="wardColumns.length">
        <div class="cal-grid" :style="gridStyle">
          <div class="grid-corner">
            <span class="tz-label">Local</span>
          </div>

          <div v-for="col in wardColumns" :key="col.key" class="col-header">
            <div class="col-avatar">{{ col.initials }}</div>
            <div class="col-meta">
              <div class="col-name">{{ col.label }}</div>
              <div class="col-count">{{ col.items.length }} case{{ col.items.length === 1 ? '' : 's' }}</div>
            </div>
          </div>

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

          <div
            v-for="(col, colIndex) in wardColumns"
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
              :class="statusTone(item)"
              :style="cardStyle(item)"
              @click="editSurgery(item)"
            >
              <div class="appt-title">{{ displayPatient(item) }}</div>
              <div class="appt-time">{{ formatTime(item.surgery_date) }}</div>
              <div class="appt-meta">
                <span class="status-dot" />
                <span class="status-text">{{ item.is_completed ? 'Completed' : 'Pending' }}</span>
              </div>
              <div class="appt-tag">{{ item.surgery_name || 'Surgery' }}</div>
              <div class="appt-actions" @click.stop>
                <button type="button" class="mini-btn" @click="editSurgery(item)">Edit</button>
                <button type="button" class="mini-btn" @click="editAnaesthetistInfo(item)">Anaesthetist</button>
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
        title="No operations for this date"
        description="Try another day, clear filters, or schedule from Admission Manager."
      />
    </div>

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
            :class="statusTone(item)"
            @click="editSurgery(item)"
          >
            <div class="week-appt-title">{{ displayPatient(item) }}</div>
            <div class="week-appt-sub">
              {{ formatTime(item.surgery_date) }} · {{ item.surgery_name || 'Surgery' }}
              <span v-if="item.ward"> · {{ item.ward }}</span>
            </div>
          </button>
          <div v-if="!day.items.length" class="week-empty">No operations</div>
        </div>
      </div>
    </div>

    <!-- Surgery Form Dialog -->
    <q-dialog v-model="showSurgeryDialog" persistent>
      <q-card style="min-width: 700px; max-width: 900px">
        <q-card-section>
          <div class="text-h6 glass-text">
            {{ editingSurgery ? 'Edit Operation' : 'Add Operation' }}
          </div>
        </q-card-section>

        <q-card-section class="q-pt-none">
          <q-form @submit="saveSurgery" class="q-gutter-md">
            <!-- Surgery Search/Select -->
            <q-select
              v-model="selectedSurgery"
              :options="filteredSurgeryOptions"
              filled
              use-input
              input-debounce="300"
              :label="editingSurgery ? 'Search Surgery (optional)' : 'Search Surgery *'"
              hint="Type to search for surgeries from price list - Select to auto-fill"
              :rules="editingSurgery ? [] : [val => !!val || 'Surgery is required']"
              @filter="filterSurgeries"
              @update:model-value="onSurgerySelected"
              option-label="label"
              option-value="value"
              emit-value
              map-options
              clearable
              :loading="loadingSurgeries"
            >
              <template v-slot:option="scope">
                <q-item v-bind="scope.itemProps">
                  <q-item-section>
                    <q-item-label>{{ scope.opt.label }}</q-item-label>
                    <q-item-label caption>
                      Code: {{ scope.opt.value.code }} | 
                      Type: {{ scope.opt.value.service_type || 'N/A' }}
                    </q-item-label>
                  </q-item-section>
                </q-item>
              </template>
            </q-select>
            
            <!-- Manual Surgery Entry -->
            <q-input
              v-model="surgeryForm.surgery_name"
              filled
              label="Surgery Name *"
              hint="Name/description of the surgery"
              :rules="[val => !!val || 'Surgery name is required']"
            />
            
            <div class="row q-col-gutter-md">
              <div class="col-6">
                <q-input
                  v-model="surgeryForm.g_drg_code"
                  filled
                  label="G-DRG Code"
                  hint="Surgery code"
                />
              </div>
              <div class="col-6">
                <q-input
                  v-model="surgeryForm.surgery_type"
                  filled
                  label="Surgery Type"
                  hint="Type/category of surgery"
                />
              </div>
            </div>

            <div class="row q-col-gutter-md">
              <div class="col-6">
                <q-input
                  v-model="surgeryForm.surgeon_name"
                  filled
                  label="Surgeon Name"
                  hint="Name of the surgeon"
                />
              </div>
              <div class="col-6">
                <q-input
                  v-model="surgeryForm.assistant_surgeon"
                  filled
                  label="Assistant Surgeon"
                  hint="Assistant surgeon name (optional)"
                />
              </div>
            </div>

            <div class="row q-col-gutter-md">
              <div class="col-6">
                <q-input
                  v-model="surgeryForm.anesthesia_type"
                  filled
                  label="Anesthesia Type"
                  hint="Type of anesthesia (e.g., General, Local, Regional)"
                />
              </div>
              <div class="col-6">
                <q-input
                  v-model="surgeryForm.surgery_date"
                  filled
                  type="datetime-local"
                  label="Surgery Date"
                  hint="Scheduled/performed date"
                />
              </div>
            </div>

            <q-input
              v-model="surgeryForm.surgery_notes"
              filled
              type="textarea"
              label="Pre-operative Notes"
              hint="Pre-operative notes and observations"
              rows="4"
            />

            <div v-if="editingSurgery" class="q-mt-md">
              <q-separator class="q-my-md" />
              <div class="text-subtitle2 q-mb-sm">Post-operative Information</div>
              
              <q-input
                v-model="surgeryForm.operative_notes"
                filled
                type="textarea"
                label="Operative Notes"
                hint="Notes during the operation"
                rows="4"
              />

              <q-input
                v-model="surgeryForm.post_operative_notes"
                filled
                type="textarea"
                label="Post-operative Notes"
                hint="Post-operative observations and care instructions"
                rows="4"
                class="q-mt-md"
              />

              <q-input
                v-model="surgeryForm.complications"
                filled
                type="textarea"
                label="Complications"
                hint="Any complications encountered"
                rows="3"
                class="q-mt-md"
              />

              <q-checkbox
                v-model="surgeryForm.is_completed"
                label="Mark as Completed"
                class="q-mt-md"
              />
            </div>

            <q-card-actions align="right" class="q-pt-md">
              <q-btn flat label="Cancel" color="primary" @click="closeSurgeryDialog" />
              <q-btn
                type="submit"
                label="Save"
                color="positive"
                :loading="savingSurgery"
              />
            </q-card-actions>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>

    <!-- Anaesthetist Info Dialog -->
    <q-dialog v-model="showAnaesthetistDialog" persistent>
      <q-card style="min-width: 700px; max-width: 900px">
        <q-card-section>
          <div class="text-h6 glass-text">Anaesthetist Information</div>
          <div class="text-subtitle2 text-grey-7 q-mt-sm">
            Operation: <span class="text-weight-bold">{{ selectedSurgeryForAnaesthetist?.surgery_name }}</span>
          </div>
          <div class="text-subtitle2 text-grey-7">
            Patient: <span class="text-weight-bold">{{ selectedSurgeryForAnaesthetist?.patient_name }}</span>
          </div>
        </q-card-section>

        <q-card-section class="q-pt-none">
          <q-form @submit="saveAnaesthetistInfo" class="q-gutter-md">
            <q-input
              v-model="anaesthetistForm.anaesthetist_consultation"
              filled
              type="textarea"
              label="Anaesthetist Consultation"
              hint="Anaesthetist's consultation notes"
              rows="4"
            />

            <q-input
              v-model="anaesthetistForm.intra_operation_care"
              filled
              type="textarea"
              label="Intra-operation Care"
              hint="Care provided during the operation"
              rows="4"
            />

            <q-input
              v-model="anaesthetistForm.post_operation_care"
              filled
              type="textarea"
              label="Post-operation Care"
              hint="Post-operative care notes"
              rows="4"
            />

            <q-input
              v-model="anaesthetistForm.drugs_given"
              filled
              type="textarea"
              label="Drugs Given"
              hint="Drugs administered during operation"
              rows="4"
            />

            <q-input
              v-model="anaesthetistForm.anaesthesia_used"
              filled
              type="textarea"
              label="Anaesthesia Used"
              hint="Detailed anaesthesia information"
              rows="4"
            />

            <q-card-actions align="right" class="q-pt-md">
              <q-btn flat label="Cancel" color="primary" @click="closeAnaesthetistDialog" />
              <q-btn
                type="submit"
                label="Save"
                color="positive"
                :loading="savingAnaesthetist"
              />
            </q-card-actions>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>
    </q-page>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue';
import { useQuasar } from 'quasar';
import { ChevronLeft, ChevronRight, CalendarDays } from 'lucide-vue-next';
import HmsPageHeader from '../components/ui/HmsPageHeader.vue';
import HmsButton from '../components/ui/HmsButton.vue';
import HmsBadge from '../components/ui/HmsBadge.vue';
import HmsEmptyState from '../components/ui/HmsEmptyState.vue';
import HmsSkeleton from '../components/ui/HmsSkeleton.vue';
import { consultationAPI, priceListAPI } from '../services/api';

const $q = useQuasar();

const todayStr = () => new Date().toISOString().split('T')[0];
const addDays = (dateStr, days) => {
  const d = new Date(`${dateStr}T12:00:00`);
  d.setDate(d.getDate() + days);
  return d.toISOString().split('T')[0];
};

const mondayOf = (dateStr) => {
  const base = new Date(`${dateStr}T12:00:00`);
  const day = base.getDay();
  const mondayOffset = day === 0 ? -6 : 1 - day;
  const monday = new Date(base);
  monday.setDate(base.getDate() + mondayOffset);
  return monday.toISOString().split('T')[0];
};

const selectedDate = ref(todayStr());
const viewMode = ref('day');
const surgeries = ref([]);
const loading = ref(false);
const cardSearch = ref('');
const selectedWard = ref('');
const nowTick = ref(Date.now());
let nowTimer = null;

const dayStart = 7;
const dayEnd = 20;
const hourHeight = 76;
const hours = Array.from({ length: dayEnd - dayStart }, (_, i) => dayStart + i);
const totalHeight = hours.length * hourHeight;

const FILTERS_LOCK_KEY = 'ot_calendar_filters_locked';
const FILTERS_STORAGE_KEY = 'ot_calendar_filters';
const filtersLocked = ref(false);

function saveFiltersToStorage() {
  localStorage.setItem(FILTERS_STORAGE_KEY, JSON.stringify({
    selectedDate: selectedDate.value,
    viewMode: viewMode.value,
  }));
}

function loadFiltersFromStorage() {
  const raw = localStorage.getItem(FILTERS_STORAGE_KEY);
  if (!raw) return;
  try {
    const f = JSON.parse(raw);
    if (f.selectedDate) selectedDate.value = f.selectedDate;
    if (f.viewMode === 'day' || f.viewMode === 'week') viewMode.value = f.viewMode;
  } catch (_) {}
}

function toggleFiltersLock() {
  filtersLocked.value = !filtersLocked.value;
  if (filtersLocked.value) {
    saveFiltersToStorage();
    localStorage.setItem(FILTERS_LOCK_KEY, 'true');
    $q.notify({
      type: 'positive',
      message: 'Date view locked – it will persist when you leave and return',
      timeout: 2000,
    });
  } else {
    localStorage.removeItem(FILTERS_LOCK_KEY);
    localStorage.removeItem(FILTERS_STORAGE_KEY);
    $q.notify({ type: 'info', message: 'Date view unlocked', timeout: 2000 });
  }
}

const formatDateShort = (dateStr) => {
  const date = new Date(`${dateStr}T12:00:00`);
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
};

const formattedDate = computed(() => {
  if (!selectedDate.value) return 'Select a date';
  if (viewMode.value === 'week') {
    const mon = mondayOf(selectedDate.value);
    const sun = addDays(mon, 6);
    return `Week of ${formatDateShort(mon)} – ${formatDateShort(sun)}`;
  }
  const date = new Date(`${selectedDate.value}T12:00:00`);
  return date.toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
});

const surgeryIsoDate = (item) => {
  if (!item?.surgery_date) return selectedDate.value;
  return new Date(item.surgery_date).toISOString().split('T')[0];
};

const filteredSurgeries = computed(() => {
  let list = surgeries.value;
  if (selectedWard.value) {
    list = list.filter((s) => (s.ward || '') === selectedWard.value);
  }
  const needle = (cardSearch.value || '').toLowerCase().trim();
  if (needle) {
    list = list.filter((s) => (s.patient_card_number || '').toLowerCase().includes(needle));
  }
  if (viewMode.value === 'day') {
    list = list.filter((s) => surgeryIsoDate(s) === selectedDate.value);
  }
  return list;
});

const pendingCount = computed(() => filteredSurgeries.value.filter((s) => !s.is_completed).length);
const completedCount = computed(() => filteredSurgeries.value.filter((s) => s.is_completed).length);

const wardOptions = computed(() => {
  const set = new Set();
  surgeries.value.forEach((s) => {
    if (s.ward) set.add(s.ward);
  });
  return Array.from(set).sort();
});

const wardColumns = computed(() => {
  const map = new Map();
  for (const item of filteredSurgeries.value) {
    const label = item.ward || 'Unassigned';
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
  return Array.from(map.values()).sort((a, b) => a.label.localeCompare(b.label));
});

const gridStyle = computed(() => ({
  gridTemplateColumns: `64px repeat(${Math.max(wardColumns.value.length, 1)}, minmax(180px, 1fr))`,
}));

const isTodaySelected = computed(() => selectedDate.value === todayStr());
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
  const mon = mondayOf(selectedDate.value);
  return Array.from({ length: 7 }, (_, i) => {
    const iso = addDays(mon, i);
    const d = new Date(`${iso}T12:00:00`);
    const items = filteredSurgeries.value.filter((s) => surgeryIsoDate(s) === iso);
    return {
      iso,
      label: d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' }),
      items,
    };
  });
});

const setViewMode = (mode) => {
  viewMode.value = mode;
  loadSurgeries();
};

const onDatePicked = () => {
  loadSurgeries();
};

const setToday = () => {
  selectedDate.value = todayStr();
  loadSurgeries();
};

const shiftDay = (delta) => {
  const step = viewMode.value === 'week' ? delta * 7 : delta;
  selectedDate.value = addDays(selectedDate.value || todayStr(), step);
  loadSurgeries();
};

const formatHourLabel = (hour) => {
  const d = new Date();
  d.setHours(hour, 0, 0, 0);
  return d.toLocaleTimeString('en-US', { hour: 'numeric', hour12: true }).toLowerCase();
};

const formatTime = (dateString) => {
  if (!dateString) return 'TBD';
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

const statusTone = (item) => (item.is_completed ? 'tone-green' : 'tone-blue');

const cardStyle = (item) => {
  const d = item.surgery_date
    ? new Date(item.surgery_date)
    : new Date(`${selectedDate.value}T09:00:00`);
  const minutes = d.getHours() * 60 + d.getMinutes() - dayStart * 60;
  const top = Math.min(Math.max(minutes * (hourHeight / 60), 4), totalHeight - 72);
  return { top: `${top}px`, height: '76px' };
};

const loadSurgeries = async () => {
  loading.value = true;
  try {
    let start;
    let end;
    if (viewMode.value === 'week') {
      start = mondayOf(selectedDate.value);
      end = addDays(start, 6);
    } else {
      start = selectedDate.value;
      end = selectedDate.value;
    }
    const response = await consultationAPI.getSurgeriesCalendar(null, start, end);
    surgeries.value = Array.isArray(response.data) ? response.data : [];
  } catch (error) {
    console.error('Error loading surgeries:', error);
    $q.notify({ type: 'negative', message: 'Failed to load operations' });
    surgeries.value = [];
  } finally {
    loading.value = false;
  }
};

const showSurgeryDialog = ref(false);
const editingSurgery = ref(null);
const savingSurgery = ref(false);
const surgeryForm = ref({
  surgery_name: '',
  g_drg_code: '',
  surgery_type: '',
  surgeon_name: '',
  assistant_surgeon: '',
  anesthesia_type: '',
  surgery_date: '',
  surgery_notes: '',
  operative_notes: '',
  post_operative_notes: '',
  complications: '',
  is_completed: false,
});

const selectedSurgery = ref(null);
const allSurgeries = ref([]);
const filteredSurgeryOptions = ref([]);
const loadingSurgeries = ref(false);

const showAnaesthetistDialog = ref(false);
const selectedSurgeryForAnaesthetist = ref(null);
const savingAnaesthetist = ref(false);
const anaesthetistForm = ref({
  anaesthetist_consultation: '',
  intra_operation_care: '',
  post_operation_care: '',
  drugs_given: '',
  anaesthesia_used: '',
});

const loadSurgeriesFromPriceList = async () => {
  loadingSurgeries.value = true;
  try {
    const response = await priceListAPI.getProceduresByServiceType();
    let procedures = [];
    if (Array.isArray(response.data)) {
      procedures = response.data;
    } else if (response.data && typeof response.data === 'object') {
      for (const key in response.data) {
        if (Array.isArray(response.data[key])) {
          procedures = procedures.concat(response.data[key]);
        }
      }
    }
    allSurgeries.value = procedures
      .filter((p) => p && p.name)
      .map((p) => ({
        label: `${p.name}${p.code ? ` (${p.code})` : ''}`,
        value: {
          name: p.name,
          code: p.code || '',
          service_type: p.service_type || '',
        },
      }));
    filteredSurgeryOptions.value = allSurgeries.value.slice(0, 50);
  } catch (error) {
    console.error('Error loading surgeries from price list:', error);
  } finally {
    loadingSurgeries.value = false;
  }
};

const filterSurgeries = (val, update) => {
  if (val === '') {
    update(() => {
      filteredSurgeryOptions.value = allSurgeries.value.slice(0, 50);
    });
    return;
  }
  update(() => {
    const needle = val.toLowerCase();
    filteredSurgeryOptions.value = allSurgeries.value
      .filter((s) => {
        const labelMatch = s.label.toLowerCase().indexOf(needle) > -1;
        const codeMatch = s.value.code?.toLowerCase().indexOf(needle) > -1;
        const nameMatch = s.value.name?.toLowerCase().indexOf(needle) > -1;
        return labelMatch || codeMatch || nameMatch;
      })
      .slice(0, 100);
  });
};

const onSurgerySelected = (surgery) => {
  if (surgery && typeof surgery === 'object') {
    surgeryForm.value.surgery_name = surgery.name;
    surgeryForm.value.g_drg_code = surgery.code;
    if (surgery.service_type) {
      surgeryForm.value.surgery_type = surgery.service_type;
    }
  }
};

function toDateTimeLocal(isoStr) {
  if (!isoStr) return '';
  const d = new Date(isoStr);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  const h = String(d.getHours()).padStart(2, '0');
  const min = String(d.getMinutes()).padStart(2, '0');
  return `${y}-${m}-${day}T${h}:${min}`;
}

const editSurgery = (surgery) => {
  editingSurgery.value = surgery;
  surgeryForm.value = {
    surgery_name: surgery.surgery_name || '',
    g_drg_code: surgery.g_drg_code || '',
    surgery_type: surgery.surgery_type || '',
    surgeon_name: surgery.surgeon_name || '',
    assistant_surgeon: surgery.assistant_surgeon || '',
    anesthesia_type: surgery.anesthesia_type || '',
    surgery_date: toDateTimeLocal(surgery.surgery_date),
    surgery_notes: surgery.surgery_notes || '',
    operative_notes: surgery.operative_notes || '',
    post_operative_notes: surgery.post_operative_notes || '',
    complications: surgery.complications || '',
    is_completed: !!surgery.is_completed,
  };
  selectedSurgery.value = null;
  showSurgeryDialog.value = true;
};

const editAnaesthetistInfo = (surgery) => {
  selectedSurgeryForAnaesthetist.value = surgery;
  anaesthetistForm.value = {
    anaesthetist_consultation: surgery.anaesthetist_consultation || '',
    intra_operation_care: surgery.intra_operation_care || '',
    post_operation_care: surgery.post_operation_care || '',
    drugs_given: surgery.drugs_given || '',
    anaesthesia_used: surgery.anaesthesia_used || '',
  };
  showAnaesthetistDialog.value = true;
};

const saveAnaesthetistInfo = async () => {
  if (!selectedSurgeryForAnaesthetist.value) return;
  savingAnaesthetist.value = true;
  try {
    await consultationAPI.updateSurgeryAnaesthetistInfo(
      selectedSurgeryForAnaesthetist.value.id,
      anaesthetistForm.value
    );
    $q.notify({ type: 'positive', message: 'Anaesthetist information saved successfully' });
    closeAnaesthetistDialog();
    await loadSurgeries();
  } catch (error) {
    console.error('Error saving anaesthetist info:', error);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || 'Failed to save anaesthetist information',
    });
  } finally {
    savingAnaesthetist.value = false;
  }
};

const closeAnaesthetistDialog = () => {
  showAnaesthetistDialog.value = false;
  selectedSurgeryForAnaesthetist.value = null;
  anaesthetistForm.value = {
    anaesthetist_consultation: '',
    intra_operation_care: '',
    post_operation_care: '',
    drugs_given: '',
    anaesthesia_used: '',
  };
};

const saveSurgery = async () => {
  if (editingSurgery.value) {
    savingSurgery.value = true;
    try {
      const form = surgeryForm.value;
      const surgeryDate = form.surgery_date ? new Date(form.surgery_date).toISOString() : null;
      await consultationAPI.updateInpatientSurgery(
        editingSurgery.value.ward_admission_id,
        editingSurgery.value.id,
        {
          surgery_name: form.surgery_name || undefined,
          surgery_type: form.surgery_type || undefined,
          surgeon_name: form.surgeon_name || undefined,
          assistant_surgeon: form.assistant_surgeon || undefined,
          anesthesia_type: form.anesthesia_type || undefined,
          surgery_date: surgeryDate,
          surgery_notes: form.surgery_notes || undefined,
          operative_notes: form.operative_notes || undefined,
          post_operative_notes: form.post_operative_notes || undefined,
          complications: form.complications || undefined,
          is_completed: form.is_completed,
        }
      );
      $q.notify({ type: 'positive', message: 'Operation updated successfully' });
      closeSurgeryDialog();
      await loadSurgeries();
    } catch (error) {
      $q.notify({
        type: 'negative',
        message: error.response?.data?.detail || 'Failed to update operation',
      });
    } finally {
      savingSurgery.value = false;
    }
  } else {
    $q.notify({
      type: 'info',
      message: 'To add new operations, please use the Admission Manager page.',
    });
    closeSurgeryDialog();
  }
};

const closeSurgeryDialog = () => {
  showSurgeryDialog.value = false;
  editingSurgery.value = null;
  surgeryForm.value = {
    surgery_name: '',
    g_drg_code: '',
    surgery_type: '',
    surgeon_name: '',
    assistant_surgeon: '',
    anesthesia_type: '',
    surgery_date: '',
    surgery_notes: '',
    operative_notes: '',
    post_operative_notes: '',
    complications: '',
    is_completed: false,
  };
  selectedSurgery.value = null;
};

watch(filtersLocked, (locked) => {
  if (locked) saveFiltersToStorage();
});

onMounted(() => {
  const isLocked = localStorage.getItem(FILTERS_LOCK_KEY) === 'true';
  filtersLocked.value = isLocked;
  if (isLocked) loadFiltersFromStorage();
  loadSurgeries();
  loadSurgeriesFromPriceList();
  nowTimer = setInterval(() => {
    nowTick.value = Date.now();
  }, 60000);
});

onUnmounted(() => {
  if (nowTimer) clearInterval(nowTimer);
});
</script>

<style scoped>
.calendar-page,
.ot-calendar-page {
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
