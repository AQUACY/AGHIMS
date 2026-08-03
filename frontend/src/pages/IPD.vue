<template>
  <q-page class="hms-page">
    <HmsPageHeader
      title="Inpatient (IPD)"
      subtitle="Ward operations, admissions, transfers, and theatre scheduling."
    />

    <div class="ipd-groups">
      <section v-for="group in visibleGroups" :key="group.id" class="ipd-group">
        <div class="group-label">{{ group.label }}</div>
        <div class="module-grid">
          <motion.div
            v-for="(mod, index) in group.modules"
            :key="mod.path"
            :initial="reduceMotion ? false : { opacity: 0, y: 10 }"
            :animate="{ opacity: 1, y: 0 }"
            :whileHover="reduceMotion ? undefined : { y: -3 }"
            :whilePress="reduceMotion ? undefined : { scale: 0.985 }"
            :transition="{ delay: index * 0.03, duration: 0.28, ease: [0.16, 1, 0.3, 1] }"
          >
            <HmsCard
              dense
              hoverable
              class="module-card"
              role="button"
              tabindex="0"
              @click="navigateToModule(mod.path)"
              @keydown.enter="navigateToModule(mod.path)"
              @keydown.space.prevent="navigateToModule(mod.path)"
            >
              <div class="module-icon" :style="{ color: mod.color, background: mod.bg }">
                <component :is="mod.icon" :size="20" />
              </div>
              <div class="module-copy">
                <div class="module-title">{{ mod.title }}</div>
                <div class="module-hint">{{ mod.hint }}</div>
              </div>
              <ArrowRight :size="16" class="module-arrow" />
            </HmsCard>
          </motion.div>
        </div>
      </section>
    </div>
  </q-page>
</template>

<script setup>
import { computed } from 'vue';
import { useRouter } from 'vue-router';
import { motion } from 'motion-v';
import { usePreferredReducedMotion } from '@vueuse/core';
import {
  ArrowRight,
  Hospital,
  UserPlus,
  ArrowLeftRight,
  Stethoscope,
  BedDouble,
  ClipboardList,
  CalendarDays,
  BadgeCheck,
  CalendarRange,
} from 'lucide-vue-next';
import { useAuthStore } from '../stores/auth';
import HmsPageHeader from '../components/ui/HmsPageHeader.vue';
import HmsCard from '../components/ui/HmsCard.vue';

const router = useRouter();
const authStore = useAuthStore();
const preferredReducedMotion = usePreferredReducedMotion();
const reduceMotion = computed(() => preferredReducedMotion.value === 'reduce');

const canAccess = (roles) => authStore.canAccess(roles);

const groups = [
  {
    id: 'flow',
    label: 'Patient flow',
    modules: [
      {
        title: 'Admission recommendations',
        hint: 'Review patients recommended for admission',
        path: '/ipd/admission-recommendations',
        icon: Hospital,
        color: 'var(--hms-accent)',
        bg: 'var(--hms-accent-muted)',
        roles: null,
      },
      {
        title: 'Admit patient',
        hint: 'Admit a patient to a ward and bed',
        path: '/ipd/admit-patient',
        icon: UserPlus,
        color: 'var(--hms-healthcare)',
        bg: 'var(--hms-healthcare-muted)',
        roles: ['Nurse', 'Doctor', 'PA', 'Admin'],
      },
      {
        title: 'Transfer patient',
        hint: 'Move patients between wards or beds',
        path: '/ipd/transfer-patient',
        icon: ArrowLeftRight,
        color: '#7c3aed',
        bg: 'rgba(124, 58, 237, 0.12)',
        roles: ['Nurse', 'Doctor', 'PA', 'Admin'],
      },
      {
        title: 'Transfer acceptance',
        hint: 'Accept or reject pending transfers',
        path: '/ipd/transfer-acceptance',
        icon: BadgeCheck,
        color: '#d97706',
        bg: 'var(--hms-warning-muted)',
        roles: ['Nurse', 'Doctor', 'PA', 'Admin'],
      },
    ],
  },
  {
    id: 'ward',
    label: 'Ward operations',
    modules: [
      {
        title: 'Doctor / nursing station',
        hint: 'Manage active ward patients',
        path: '/ipd/doctor-nursing-station',
        icon: Stethoscope,
        color: 'var(--hms-accent)',
        bg: 'var(--hms-accent-muted)',
        roles: ['Nurse', 'Doctor', 'PA', 'Admin'],
      },
      {
        title: 'Bed management',
        hint: 'Configure beds for each ward',
        path: '/ipd/bed-management',
        icon: BedDouble,
        color: '#ea580c',
        bg: 'rgba(234, 88, 12, 0.12)',
        roles: ['Admin'],
      },
      {
        title: 'Daily ward state',
        hint: 'Occupancy and daily ward statistics',
        path: '/ipd/daily-ward-state',
        icon: CalendarDays,
        color: '#4f46e5',
        bg: 'rgba(79, 70, 229, 0.12)',
        roles: ['Nurse', 'Doctor', 'PA', 'Admin'],
      },
      {
        title: 'Registers',
        hint: 'Admission and discharge records',
        path: '/ipd/registers',
        icon: ClipboardList,
        color: '#0d9488',
        bg: 'rgba(13, 148, 136, 0.12)',
        roles: ['Nurse', 'Doctor', 'PA', 'Admin'],
      },
    ],
  },
  {
    id: 'theatre',
    label: 'Theatre',
    modules: [
      {
        title: 'Operation theatre calendar',
        hint: 'Schedule and review IPD operations',
        path: '/ipd/operation-theatre-calendar',
        icon: CalendarRange,
        color: 'var(--hms-critical)',
        bg: 'var(--hms-critical-muted)',
        roles: ['Nurse', 'Doctor', 'PA', 'Admin', 'Anaesthetist'],
      },
    ],
  },
];

const visibleGroups = computed(() =>
  groups
    .map((g) => ({
      ...g,
      modules: g.modules.filter((m) => !m.roles || canAccess(m.roles)),
    }))
    .filter((g) => g.modules.length > 0)
);

const navigateToModule = (path) => {
  router.push(path);
};
</script>

<style scoped>
.ipd-groups {
  display: flex;
  flex-direction: column;
  gap: 1.35rem;
}

.group-label {
  font-size: 0.68rem;
  font-weight: 750;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--hms-text-muted);
  margin-bottom: 0.65rem;
}

.module-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.75rem;
}

.module-card {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 0.85rem;
  min-height: 84px;
  background: var(--hms-panel-bg);
}

.module-icon {
  width: 2.5rem;
  height: 2.5rem;
  border-radius: var(--hms-radius-lg);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.module-title {
  font-size: var(--hms-text-base);
  font-weight: 700;
  color: var(--hms-text-primary);
}

.module-hint {
  margin-top: 0.2rem;
  font-size: var(--hms-text-sm);
  color: var(--hms-text-secondary);
}

.module-arrow {
  color: var(--hms-text-muted);
  transition: transform var(--hms-duration-fast) var(--hms-ease-out), color var(--hms-duration-fast) var(--hms-ease-out);
}

.module-card:hover .module-arrow {
  color: var(--hms-accent);
  transform: translateX(3px);
}

@media (max-width: 720px) {
  .module-grid {
    grid-template-columns: 1fr;
  }
}
</style>
