<template>
  <q-page class="hms-page">
    <HmsPageHeader
      title="Claims"
      subtitle="NHIS claims workspace — clear tools for daily submission, imports, and coding references."
    />

    <div class="claims-workspace">
      <section v-for="group in groups" :key="group.id" class="claims-group">
        <div class="group-bar">
          <div>
            <h2 class="group-title">{{ group.label }}</h2>
            <p class="group-note">{{ group.note }}</p>
          </div>
        </div>
        <div class="module-grid">
          <motion.div
            v-for="(mod, index) in group.modules"
            :key="mod.path"
            class="module-wrap"
            :initial="reduceMotion ? false : { opacity: 0, y: 12 }"
            :animate="{ opacity: 1, y: 0 }"
            :whileHover="reduceMotion ? undefined : { y: -4 }"
            :whilePress="reduceMotion ? undefined : { scale: 0.985 }"
            :transition="{ delay: index * 0.04, duration: 0.32, ease: [0.16, 1, 0.3, 1] }"
          >
            <HmsCard
              dense
              hoverable
              class="module-card"
              role="button"
              tabindex="0"
              @click="go(mod.path)"
              @keydown.enter="go(mod.path)"
              @keydown.space.prevent="go(mod.path)"
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
  LayoutDashboard,
  FileText,
  BarChart3,
  CircleAlert,
  Upload,
  ListChecks,
  GitCompareArrows,
  BadgeDollarSign,
  BookOpen,
} from 'lucide-vue-next';
import HmsPageHeader from '../components/ui/HmsPageHeader.vue';
import HmsCard from '../components/ui/HmsCard.vue';

const router = useRouter();
const preferredReducedMotion = usePreferredReducedMotion();
const reduceMotion = computed(() => preferredReducedMotion.value === 'reduce');

const go = (path) => router.push(path);

const groups = [
  {
    id: 'work',
    label: 'Daily work',
    note: 'Overview, generate, and export for ClaimIT',
    modules: [
      {
        title: 'Dashboard',
        hint: 'Monthly overview, submission advice, and duplicate checks',
        path: '/claims/dashboard',
        icon: LayoutDashboard,
        color: 'var(--hms-accent)',
        bg: 'var(--hms-accent-muted)',
      },
      {
        title: 'Claims list',
        hint: 'Finalized encounters, generate/edit claims, export XML',
        path: '/claims/list',
        icon: FileText,
        color: 'var(--hms-healthcare)',
        bg: 'var(--hms-healthcare-muted)',
      },
      {
        title: 'Reports',
        hint: 'Structured reports for claims analysis and auditing',
        path: '/claims/reports',
        icon: BarChart3,
        color: 'var(--hms-info)',
        bg: 'var(--hms-info-muted)',
      },
    ],
  },
  {
    id: 'fix',
    label: 'Import & fix',
    note: 'ClaimIT corrections, GHIMS XML, and CFX tools',
    modules: [
      {
        title: 'Correct errors',
        hint: 'Upload ClaimIT reports, fix errors, and re-export',
        path: '/claims/correct-errors',
        icon: CircleAlert,
        color: 'var(--hms-warning)',
        bg: 'var(--hms-warning-muted)',
      },
      {
        title: 'Import GHIMS XML',
        hint: 'Upload exported XML, review, finalize, and export again',
        path: '/claims/ghims-import',
        icon: Upload,
        color: 'var(--hms-healthcare)',
        bg: 'var(--hms-healthcare-muted)',
      },
      {
        title: 'CFX convert & diff',
        hint: 'Convert ClaimIT CFX to XML or find missing claims',
        path: '/claims/cxf-tools',
        icon: GitCompareArrows,
        color: 'var(--hms-accent)',
        bg: 'var(--hms-accent-muted)',
      },
    ],
  },
  {
    id: 'refs',
    label: 'References',
    note: 'Templates, tariffs, and ICD–DRG coding aids',
    modules: [
      {
        title: 'Diagnosis templates',
        hint: 'Save investigations & medicines for common diagnoses',
        path: '/claims/diagnosis-templates',
        icon: ListChecks,
        color: 'var(--hms-success)',
        bg: 'var(--hms-success-muted)',
      },
      {
        title: 'Price list',
        hint: 'Service tariffs and NHIA price list entries',
        path: '/claims/price-list',
        icon: BadgeDollarSign,
        color: 'var(--hms-accent)',
        bg: 'var(--hms-accent-muted)',
      },
      {
        title: 'ICD-10 DRG mapping',
        hint: 'Map ICD-10 diagnoses to G-DRG codes',
        path: '/claims/icd10-drg-mapping',
        icon: BookOpen,
        color: 'var(--hms-info)',
        bg: 'var(--hms-info-muted)',
      },
    ],
  },
];
</script>

<style scoped>
.claims-workspace {
  display: flex;
  flex-direction: column;
  gap: 1.15rem;
}

.claims-group {
  padding: 1.15rem 1.2rem 1.25rem;
  border-radius: 1.25rem;
  background: var(--hms-panel-bg);
  border: 1px solid var(--hms-border);
  box-shadow: var(--hms-shadow-md);
}

.group-bar {
  margin-bottom: 0.95rem;
  padding-bottom: 0.85rem;
  border-bottom: 1px solid var(--hms-border);
}

.group-title {
  margin: 0;
  font-size: var(--hms-text-lg);
  font-weight: 750;
  letter-spacing: var(--hms-tracking-tight);
  color: var(--hms-text-primary);
}

.group-note {
  margin: 0.2rem 0 0;
  font-size: var(--hms-text-sm);
  color: var(--hms-text-muted);
}

.module-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.8rem;
}

.module-wrap {
  min-width: 0;
}

.module-card {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 0.9rem;
  min-height: 92px;
  background: var(--hms-surface) !important;
  box-shadow: none !important;
}

.module-icon {
  width: 2.55rem;
  height: 2.55rem;
  border-radius: var(--hms-radius-lg);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.module-title {
  font-size: var(--hms-text-base);
  font-weight: 750;
  color: var(--hms-text-primary);
}

.module-hint {
  margin-top: 0.2rem;
  font-size: var(--hms-text-sm);
  color: var(--hms-text-secondary);
  line-height: 1.4;
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

  .claims-group {
    padding: 1rem;
  }
}
</style>
