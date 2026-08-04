<template>
  <q-page class="hms-page">
    <LicenseStatusBanner />

    <HmsPageHeader
      title="Companion"
      subtitle="Service requests and copayment billing from the government system. Lab, Scan, X-ray, and Pharmacy add line items for copayment."
    />

    <div class="companion-workspace">
      <section class="companion-group">
        <div class="group-bar">
          <div>
            <h2 class="group-title">Daily work</h2>
            <p class="group-note">Create visits, open the service list, and bill copayments</p>
          </div>
        </div>
        <div class="module-grid">
          <motion.div
            v-for="(mod, index) in modules"
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
import { ArrowRight, List, PlusCircle, Receipt } from 'lucide-vue-next';
import { useAuthStore } from '../stores/auth';
import LicenseStatusBanner from '../components/LicenseStatusBanner.vue';
import HmsPageHeader from '../components/ui/HmsPageHeader.vue';
import HmsCard from '../components/ui/HmsCard.vue';

const router = useRouter();
const authStore = useAuthStore();
const preferredReducedMotion = usePreferredReducedMotion();
const reduceMotion = computed(() => preferredReducedMotion.value === 'reduce');
const canAccessRecords = computed(() => authStore.canAccess(['Records', 'Admin']));

const go = (path) => router.push(path);

const modules = computed(() => {
  const items = [
    {
      title: 'Service list',
      hint: 'View visits created from card + visit number',
      path: '/companion/visits',
      icon: List,
      color: 'var(--hms-accent)',
      bg: 'var(--hms-accent-muted)',
    },
  ];
  if (canAccessRecords.value) {
    items.push({
      title: 'Create service',
      hint: 'Add a service using government card and visit number',
      path: '/companion/visits/create',
      icon: PlusCircle,
      color: 'var(--hms-healthcare)',
      bg: 'var(--hms-healthcare-muted)',
    });
  }
  items.push({
    title: 'Billing',
    hint: 'Copayment billing, deposits, and receipt breakdowns',
    path: '/companion/billing',
    icon: Receipt,
    color: 'var(--hms-success)',
    bg: 'var(--hms-success-muted)',
  });
  return items;
});
</script>

<style scoped>
.companion-workspace {
  display: flex;
  flex-direction: column;
  gap: 1.15rem;
}
.companion-group {
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
.module-wrap { min-width: 0; }
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
  .module-grid { grid-template-columns: 1fr; }
}
</style>
