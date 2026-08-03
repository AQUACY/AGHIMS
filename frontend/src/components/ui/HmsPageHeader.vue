<script setup>
import { cn } from '../../utils/cn';

defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
  class: { type: String, default: '' },
});
</script>

<template>
  <header :class="cn('hms-page-header', $props.class)">
    <div class="hms-page-header__text">
      <h1 class="hms-page-header__title">{{ title }}</h1>
      <p v-if="subtitle" class="hms-page-header__subtitle">{{ subtitle }}</p>
      <slot name="below" />
    </div>
    <div v-if="$slots.actions" class="hms-page-header__actions">
      <slot name="actions" />
    </div>
  </header>
</template>

<style scoped>
.hms-page-header {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: space-between;
  gap: 0.85rem 1rem;
  margin-bottom: 1.35rem;
}

.hms-page-header__text {
  min-width: 0;
  flex: 1;
}

.hms-page-header__title {
  margin: 0;
  font-size: var(--hms-text-2xl);
  font-weight: 750;
  letter-spacing: var(--hms-tracking-tight);
  line-height: var(--hms-leading-tight);
  color: var(--hms-text-primary);
}

.hms-page-header__subtitle {
  margin: 0.35rem 0 0;
  font-size: var(--hms-text-sm);
  color: var(--hms-text-secondary);
  max-width: 52ch;
}

.hms-page-header__actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}

@media (max-width: 640px) {
  .hms-page-header {
    align-items: stretch;
    flex-direction: column;
    gap: 0.85rem;
  }

  .hms-page-header__actions {
    width: 100%;
  }

  .hms-page-header__actions :deep(.hms-btn) {
    flex: 1;
  }
}
</style>
