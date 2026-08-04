<template>
  <q-page class="hms-page">
    <LicenseStatusBanner />

    <HmsPageHeader title="Dashboard" subtitle="Today’s operational pulse across clinical and billing workflows.">
      <template #actions>
        <HmsButton variant="secondary" size="sm" :loading="refreshing" @click="refresh">
          <RefreshCw :size="14" :class="{ spin: refreshing }" />
          Refresh
        </HmsButton>
      </template>
    </HmsPageHeader>

    <div class="dash-grid">
      <motion.div
        v-for="(stat, index) in stats"
        :key="stat.label"
        class="stat-wrap"
        :initial="reduceMotion ? false : { opacity: 0, y: 10 }"
        :animate="{ opacity: 1, y: 0 }"
        :whileHover="reduceMotion ? undefined : { y: -3 }"
        :transition="{ delay: index * 0.05, duration: 0.3, ease: [0.16, 1, 0.3, 1] }"
      >
        <HmsCard dense class="stat-card">
          <div class="stat-top">
            <div class="stat-icon" :style="{ color: stat.color, background: stat.bg }">
              <component :is="stat.icon" :size="18" />
            </div>
            <span class="stat-label">{{ stat.label }}</span>
          </div>
          <div class="stat-bottom">
            <div class="stat-value">{{ stat.value }}</div>
            <div class="stat-hint">{{ stat.hint }}</div>
          </div>
        </HmsCard>
      </motion.div>
    </div>

    <div class="workspace-panel">
      <div class="section-bar">
        <div>
          <h2 class="section-title">Quick actions</h2>
          <p class="section-note">Jump into high-frequency clinical workflows</p>
        </div>
      </div>

      <div v-if="visibleActions.length" class="action-grid">
        <motion.div
          v-for="(action, index) in visibleActions"
          :key="action.label"
          :initial="reduceMotion ? false : { opacity: 0, y: 10 }"
          :animate="{ opacity: 1, y: 0 }"
          :whileHover="reduceMotion ? undefined : { y: -2, scale: 1.01 }"
          :whilePress="reduceMotion ? undefined : { scale: 0.985 }"
          :transition="{ delay: 0.08 + index * 0.04, duration: 0.28, ease: [0.16, 1, 0.3, 1] }"
        >
          <HmsCard
            dense
            hoverable
            class="action-card"
            role="button"
            tabindex="0"
            @click="$router.push(action.to)"
            @keydown.enter="$router.push(action.to)"
            @keydown.space.prevent="$router.push(action.to)"
          >
            <div class="action-icon" :style="{ color: action.color, background: action.bg }">
              <component :is="action.icon" :size="18" />
            </div>
            <div class="action-copy">
              <div class="action-label">{{ action.label }}</div>
              <div class="action-hint">{{ action.hint }}</div>
            </div>
            <ArrowRight :size="16" class="action-arrow" />
          </HmsCard>
        </motion.div>
      </div>
      <HmsEmptyState
        v-else
        title="No quick actions available"
        description="Your role does not include common clinical shortcuts on this dashboard."
      />
    </div>
  </q-page>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import { motion } from 'motion-v';
import { usePreferredReducedMotion } from '@vueuse/core';
import {
  Users,
  ClipboardList,
  Receipt,
  UserPlus,
  HeartPulse,
  Stethoscope,
  RefreshCw,
  ArrowRight,
} from 'lucide-vue-next';
import { useDashboardStore } from '../stores/dashboard';
import { useAuthStore } from '../stores/auth';
import LicenseStatusBanner from '../components/LicenseStatusBanner.vue';
import HmsPageHeader from '../components/ui/HmsPageHeader.vue';
import HmsCard from '../components/ui/HmsCard.vue';
import HmsButton from '../components/ui/HmsButton.vue';
import HmsEmptyState from '../components/ui/HmsEmptyState.vue';

const dashboardStore = useDashboardStore();
const authStore = useAuthStore();
const preferredReducedMotion = usePreferredReducedMotion();
const reduceMotion = computed(() => preferredReducedMotion.value === 'reduce');
const refreshing = ref(false);

const canAccess = (roles) => authStore.canAccess(roles);

const stats = computed(() => [
  {
    label: "Today's patients",
    value: dashboardStore.stats.todayPatients ?? 0,
    hint: 'Registered / seen today',
    icon: Users,
    color: 'var(--hms-accent)',
    bg: 'var(--hms-accent-muted)',
  },
  {
    label: 'Pending encounters',
    value: dashboardStore.stats.pendingEncounters ?? 0,
    hint: 'Awaiting clinical action',
    icon: ClipboardList,
    color: 'var(--hms-healthcare)',
    bg: 'var(--hms-healthcare-muted)',
  },
  {
    label: 'Unpaid bills',
    value: dashboardStore.stats.unpaidBills ?? 0,
    hint: 'Outstanding balances',
    icon: Receipt,
    color: '#d97706',
    bg: 'var(--hms-warning-muted)',
  },
]);

const actions = [
  {
    label: 'Register patient',
    hint: 'Create a new patient record',
    icon: UserPlus,
    to: '/patients/register',
    roles: ['Records', 'Admin', 'PA', 'Doctor'],
    color: 'var(--hms-accent)',
    bg: 'var(--hms-accent-muted)',
  },
  {
    label: 'Record vitals',
    hint: 'Capture bedside measurements',
    icon: HeartPulse,
    to: '/vitals',
    roles: ['Nurse', 'Doctor', 'PA', 'Admin'],
    color: '#db2777',
    bg: 'rgba(219, 39, 119, 0.12)',
  },
  {
    label: 'Consultation',
    hint: 'Open the clinical workspace',
    icon: Stethoscope,
    to: '/consultation',
    roles: ['Doctor', 'PA', 'Admin'],
    color: 'var(--hms-healthcare)',
    bg: 'var(--hms-healthcare-muted)',
  },
  {
    label: 'Billing',
    hint: 'Review invoices and payments',
    icon: Receipt,
    to: '/billing',
    roles: ['Billing', 'Admin'],
    color: '#059669',
    bg: 'var(--hms-success-muted)',
  },
];

const visibleActions = computed(() => actions.filter((a) => canAccess(a.roles)));

async function refresh() {
  refreshing.value = true;
  try {
    await dashboardStore.fetchStats();
  } finally {
    refreshing.value = false;
  }
}

onMounted(() => {
  dashboardStore.fetchStats();
});
</script>

<style scoped>
.dash-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.85rem;
  margin-bottom: 1.25rem;
}

.stat-wrap {
  min-width: 0;
}

.stat-card {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
  min-height: 112px;
  transition: box-shadow var(--hms-duration-normal) var(--hms-ease-out);
}

.stat-wrap:hover .stat-card {
  box-shadow: var(--hms-shadow-lg);
}

.stat-top {
  display: flex;
  align-items: center;
  gap: 0.65rem;
}

.stat-icon {
  width: 2.25rem;
  height: 2.25rem;
  border-radius: var(--hms-radius-lg);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-label {
  font-size: var(--hms-text-sm);
  font-weight: 650;
  color: var(--hms-text-secondary);
}

.stat-bottom {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.75rem;
  margin-top: auto;
}

.stat-value {
  font-size: var(--hms-text-3xl);
  font-weight: 750;
  letter-spacing: var(--hms-tracking-tight);
  line-height: 1;
  font-variant-numeric: tabular-nums;
  color: var(--hms-text-primary);
}

.stat-hint {
  font-size: var(--hms-text-xs);
  color: var(--hms-text-muted);
  text-align: right;
  max-width: 9rem;
}

.workspace-panel {
  padding: 1.1rem 1.15rem 1.2rem;
  border-radius: var(--hms-radius-xl);
  background: var(--hms-panel-bg);
  border: 1px solid var(--hms-border);
  box-shadow: var(--hms-shadow-md);
}

.section-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: space-between;
  gap: 0.65rem;
  margin-bottom: 0.95rem;
  padding-bottom: 0.85rem;
  border-bottom: 1px solid var(--hms-border);
}

.section-title {
  margin: 0;
  font-size: var(--hms-text-lg);
  font-weight: 700;
  color: var(--hms-text-primary);
}

.section-note {
  margin: 0.2rem 0 0;
  font-size: var(--hms-text-sm);
  color: var(--hms-text-muted);
}

.action-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.75rem;
}

.action-card {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 0.85rem;
  min-height: 72px;
  background: var(--hms-surface) !important;
  box-shadow: none !important;
}

.action-icon {
  width: 2.4rem;
  height: 2.4rem;
  border-radius: var(--hms-radius-lg);
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.action-label {
  font-weight: 700;
  font-size: var(--hms-text-base);
  color: var(--hms-text-primary);
}

.action-hint {
  margin-top: 0.15rem;
  font-size: var(--hms-text-sm);
  color: var(--hms-text-secondary);
}

.action-arrow {
  color: var(--hms-text-muted);
  transition: transform var(--hms-duration-fast) var(--hms-ease-out), color var(--hms-duration-fast) var(--hms-ease-out);
}

.action-card:hover .action-arrow {
  color: var(--hms-accent);
  transform: translateX(3px);
}

.spin {
  animation: dash-spin 0.8s linear infinite;
}

@keyframes dash-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 960px) {
  .dash-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .action-grid {
    grid-template-columns: 1fr;
  }

  .workspace-panel {
    padding: 0.95rem;
  }

  .stat-hint {
    max-width: none;
    text-align: left;
  }

  .stat-bottom {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.35rem;
  }
}

@media (prefers-reduced-motion: reduce) {
  .spin {
    animation: none;
  }
}
</style>
