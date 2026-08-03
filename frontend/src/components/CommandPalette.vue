<script setup>
import { computed, ref, watch, nextTick, onMounted, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
import { useDebounceFn, useMagicKeys, whenever } from '@vueuse/core';
import { motion, AnimatePresence } from 'motion-v';
import {
  Search,
  LayoutDashboard,
  UserPlus,
  Users,
  Stethoscope,
  HeartPulse,
  FlaskConical,
  Pill,
  Receipt,
  FileText,
  BedDouble,
  CalendarDays,
  Settings,
  Package,
  UserRound,
} from 'lucide-vue-next';
import { patientsAPI } from '../services/api';

const props = defineProps({
  modelValue: { type: Boolean, default: false },
});

const emit = defineEmits(['update:modelValue']);

const router = useRouter();
const query = ref('');
const activeIndex = ref(0);
const inputRef = ref(null);
const patientResults = ref([]);
const searchingPatients = ref(false);

const commands = [
  { id: 'dashboard', label: 'Dashboard', group: 'Navigate', icon: LayoutDashboard, to: { name: 'Dashboard' }, keywords: 'home overview' },
  { id: 'register', label: 'Register Patient', group: 'Patients', icon: UserPlus, to: { name: 'PatientRegistration' }, keywords: 'new patient registration' },
  { id: 'search-patients', label: 'Search Patients', group: 'Patients', icon: Users, to: { name: 'PatientSearchResults' }, keywords: 'find lookup' },
  { id: 'vitals', label: 'Vital Signs', group: 'Clinical', icon: HeartPulse, to: { name: 'Vitals' }, keywords: 'bp pulse temperature' },
  { id: 'consultation', label: 'Consultation', group: 'Clinical', icon: Stethoscope, to: { name: 'Consultation' }, keywords: 'opd doctor' },
  { id: 'calendar', label: 'Encounters Calendar', group: 'Clinical', icon: CalendarDays, to: { name: 'EncountersCalendar' }, keywords: 'appointments schedule' },
  { id: 'ipd', label: 'IPD / Admissions', group: 'Clinical', icon: BedDouble, to: { name: 'IPD' }, keywords: 'ward inpatient' },
  { id: 'lab', label: 'Laboratory', group: 'Diagnostics', icon: FlaskConical, to: { name: 'Lab' }, keywords: 'investigations results' },
  { id: 'pharmacy', label: 'Pharmacy', group: 'Pharmacy', icon: Pill, to: { name: 'Pharmacy' }, keywords: 'drugs dispense' },
  { id: 'billing', label: 'Billing', group: 'Finance', icon: Receipt, to: { name: 'Billing' }, keywords: 'invoice payment' },
  { id: 'claims', label: 'NHIS Claims', group: 'Finance', icon: FileText, to: { name: 'Claims' }, keywords: 'nhia insurance' },
  { id: 'inventory', label: 'Inventory', group: 'Stores', icon: Package, to: { name: 'InventoryManagement' }, keywords: 'stock stores' },
  { id: 'modules', label: 'Module Management', group: 'Settings', icon: Settings, to: { name: 'ModuleManagement' }, keywords: 'admin config' },
];

const open = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
});

function extractPatients(data) {
  if (Array.isArray(data)) return data;
  if (data?.data && Array.isArray(data.data)) return data.data;
  if (data?.results && Array.isArray(data.results)) return data.results;
  if (data && typeof data === 'object') return [data];
  return [];
}

const searchPatientsLive = useDebounceFn(async (q) => {
  if (!q || q.length < 2) {
    patientResults.value = [];
    searchingPatients.value = false;
    return;
  }
  searchingPatients.value = true;
  try {
    const looksLikeCard = /^[A-Za-z0-9-]{4,}$/.test(q) && !/\s/.test(q);
    const looksLikePhone = /^\+?\d{7,}$/.test(q.replace(/\s/g, ''));

    let response;
    if (looksLikePhone) {
      response = await patientsAPI.searchByContact(q);
    } else if (looksLikeCard) {
      try {
        response = await patientsAPI.getByCard(q);
      } catch {
        response = await patientsAPI.searchByName(q);
      }
    } else {
      response = await patientsAPI.searchByName(q);
    }
    patientResults.value = extractPatients(response.data).slice(0, 8);
  } catch {
    patientResults.value = [];
  } finally {
    searchingPatients.value = false;
  }
}, 320);

const filteredCommands = computed(() => {
  const q = query.value.trim().toLowerCase();
  if (!q) return commands;
  return commands.filter((c) => {
    const hay = `${c.label} ${c.group} ${c.keywords}`.toLowerCase();
    return hay.includes(q);
  });
});

const patientEntries = computed(() =>
  patientResults.value.map((p) => ({
    id: `patient-${p.id || p.card_number}`,
    type: 'patient',
    label: `${p.name || ''} ${p.surname || ''}`.trim() || p.card_number,
    meta: p.card_number,
    sub: [p.gender, p.insured ? 'Insured' : 'Cash', p.contact].filter(Boolean).join(' · '),
    patient: p,
    icon: UserRound,
  }))
);

const flatList = computed(() => {
  const list = [];
  if (patientEntries.value.length) {
    for (const p of patientEntries.value) list.push({ ...p, group: 'Patients' });
  }
  for (const c of filteredCommands.value) {
    list.push({ ...c, type: 'command', group: c.group });
  }
  return list;
});

const grouped = computed(() => {
  const map = new Map();
  for (const item of flatList.value) {
    if (!map.has(item.group)) map.set(item.group, []);
    map.get(item.group).push(item);
  }
  return [...map.entries()];
});

watch(open, async (isOpen) => {
  if (isOpen) {
    query.value = '';
    patientResults.value = [];
    activeIndex.value = 0;
    await nextTick();
    inputRef.value?.focus();
  }
});

watch(query, (q) => {
  activeIndex.value = 0;
  searchPatientsLive(q.trim());
});

watch(flatList, () => {
  activeIndex.value = 0;
});

function close() {
  open.value = false;
}

function runItem(item) {
  if (!item) return;
  if (item.type === 'patient' && item.patient?.card_number) {
    router.push({ name: 'PatientProfile', params: { cardNumber: item.patient.card_number } }).catch(() => {});
    close();
    return;
  }
  if (item.to) {
    router.push(item.to).catch(() => {});
    close();
  }
}

function onKeydown(e) {
  if (!open.value) return;
  if (e.key === 'Escape') {
    e.preventDefault();
    close();
    return;
  }
  if (e.key === 'ArrowDown') {
    e.preventDefault();
    activeIndex.value = Math.min(activeIndex.value + 1, Math.max(flatList.value.length - 1, 0));
  } else if (e.key === 'ArrowUp') {
    e.preventDefault();
    activeIndex.value = Math.max(activeIndex.value - 1, 0);
  } else if (e.key === 'Enter') {
    e.preventDefault();
    const item = flatList.value[activeIndex.value];
    if (item) runItem(item);
  }
}

function flatIndex(groupIndex, itemIndex) {
  let i = 0;
  for (let g = 0; g < grouped.value.length; g++) {
    const items = grouped.value[g][1];
    for (let j = 0; j < items.length; j++) {
      if (g === groupIndex && j === itemIndex) return i;
      i += 1;
    }
  }
  return 0;
}

const keys = useMagicKeys();
whenever(keys['ctrl_k'], () => {
  open.value = !open.value;
});
whenever(keys['meta_k'], () => {
  open.value = !open.value;
});

onMounted(() => window.addEventListener('keydown', onKeydown));
onUnmounted(() => window.removeEventListener('keydown', onKeydown));
</script>

<template>
  <AnimatePresence>
    <motion.div
      v-if="open"
      key="palette"
      class="palette-root"
      role="dialog"
      aria-modal="true"
      aria-label="Command palette"
      :initial="{ opacity: 0 }"
      :animate="{ opacity: 1 }"
      :exit="{ opacity: 0 }"
      :transition="{ duration: 0.15 }"
      @click.self="close"
    >
      <motion.div
        class="palette-panel hms-glass-strong"
        :initial="{ opacity: 0, y: -8, scale: 0.98 }"
        :animate="{ opacity: 1, y: 0, scale: 1 }"
        :exit="{ opacity: 0, y: -6, scale: 0.98 }"
        :transition="{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }"
      >
        <div class="palette-search">
          <Search :size="18" class="palette-search-icon" aria-hidden="true" />
          <input
            ref="inputRef"
            v-model="query"
            type="search"
            class="palette-input"
            placeholder="Search patients, modules, actions…"
            autocomplete="off"
            aria-autocomplete="list"
          />
          <span v-if="searchingPatients" class="palette-spinner" aria-hidden="true" />
          <kbd class="palette-kbd">Esc</kbd>
        </div>

        <div class="palette-results" role="listbox">
          <template v-if="flatList.length">
            <div v-for="([group, items], gi) in grouped" :key="group" class="palette-group">
              <div class="palette-group-label">{{ group }}</div>
              <button
                v-for="(item, ii) in items"
                :key="item.id"
                type="button"
                role="option"
                class="palette-item"
                :class="{ active: flatIndex(gi, ii) === activeIndex }"
                :aria-selected="flatIndex(gi, ii) === activeIndex"
                @mouseenter="activeIndex = flatIndex(gi, ii)"
                @click="runItem(item)"
              >
                <component :is="item.icon" :size="16" class="palette-item-icon" />
                <span class="palette-item-text">
                  <span>{{ item.label }}</span>
                  <span v-if="item.meta" class="palette-meta">{{ item.meta }}</span>
                  <span v-if="item.sub" class="palette-sub">{{ item.sub }}</span>
                </span>
              </button>
            </div>
          </template>
          <div v-else class="palette-empty">
            <template v-if="searchingPatients">Searching patients…</template>
            <template v-else-if="query">No matches for “{{ query }}”</template>
            <template v-else>Type to search modules or patients</template>
          </div>
        </div>

        <div class="palette-footer">
          <span><kbd>↑</kbd><kbd>↓</kbd> navigate</span>
          <span><kbd>↵</kbd> open</span>
          <span><kbd>⌘</kbd><kbd>K</kbd> toggle</span>
        </div>
      </motion.div>
    </motion.div>
  </AnimatePresence>
</template>

<style scoped>
.palette-root {
  position: fixed;
  inset: 0;
  z-index: 7000;
  display: flex;
  justify-content: center;
  padding-top: min(18vh, 140px);
  background: rgba(0, 0, 0, 0.45);
  backdrop-filter: blur(6px);
}

.palette-panel {
  width: min(560px, calc(100vw - 2rem));
  max-height: min(70vh, 520px);
  border-radius: var(--hms-radius-2xl);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.palette-search {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  padding: 0.9rem 1rem;
  border-bottom: 1px solid var(--hms-border);
}

.palette-search-icon {
  color: var(--hms-text-muted);
  flex-shrink: 0;
}

.palette-input {
  flex: 1;
  border: none;
  background: transparent;
  color: var(--hms-text-primary);
  font-size: var(--hms-text-lg);
  font-family: inherit;
  outline: none;
}

.palette-input::placeholder {
  color: var(--hms-text-muted);
}

.palette-spinner {
  width: 1rem;
  height: 1rem;
  border: 2px solid var(--hms-border);
  border-top-color: var(--hms-accent);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.palette-kbd {
  font-family: var(--hms-font-mono);
  font-size: 0.7rem;
  color: var(--hms-text-muted);
  border: 1px solid var(--hms-border);
  border-radius: 6px;
  padding: 0.15rem 0.4rem;
}

.palette-results {
  overflow-y: auto;
  padding: 0.5rem;
  flex: 1;
}

.palette-group-label {
  font-size: var(--hms-text-xs);
  font-weight: 600;
  letter-spacing: var(--hms-tracking-wide);
  text-transform: uppercase;
  color: var(--hms-text-muted);
  padding: 0.5rem 0.65rem 0.25rem;
}

.palette-item {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 0.65rem;
  padding: 0.65rem 0.75rem;
  border: none;
  border-radius: var(--hms-radius-lg);
  background: transparent;
  color: var(--hms-text-primary);
  font-size: var(--hms-text-base);
  font-family: inherit;
  text-align: left;
  cursor: pointer;
}

.palette-item:hover,
.palette-item.active {
  background: var(--hms-accent-muted);
  color: var(--hms-accent);
}

.palette-item-icon {
  flex-shrink: 0;
  opacity: 0.85;
}

.palette-item-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
  gap: 0.1rem;
}

.palette-meta {
  font-size: var(--hms-text-xs);
  font-family: var(--hms-font-mono);
  color: var(--hms-text-secondary);
}

.palette-sub {
  font-size: var(--hms-text-xs);
  color: var(--hms-text-muted);
}

.palette-empty {
  padding: 2rem 1rem;
  text-align: center;
  color: var(--hms-text-secondary);
  font-size: var(--hms-text-sm);
}

.palette-footer {
  display: flex;
  gap: 1rem;
  padding: 0.55rem 1rem;
  border-top: 1px solid var(--hms-border);
  font-size: var(--hms-text-xs);
  color: var(--hms-text-muted);
}

.palette-footer kbd {
  font-family: var(--hms-font-mono);
  border: 1px solid var(--hms-border);
  border-radius: 4px;
  padding: 0 0.3rem;
  margin-right: 0.15rem;
}

@media (prefers-reduced-motion: reduce) {
  .palette-spinner {
    animation: none;
  }
}
</style>
