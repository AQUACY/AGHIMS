<script setup>
import { computed } from 'vue';
import { cn } from '../../utils/cn';

const props = defineProps({
  padding: { type: Boolean, default: true },
  hoverable: { type: Boolean, default: false },
  strong: { type: Boolean, default: false },
  dense: { type: Boolean, default: false },
  class: { type: String, default: '' },
});

const classes = computed(() =>
  cn(
    'hms-card',
    props.strong && 'hms-card--strong',
    props.hoverable && 'hms-card--hoverable',
    props.padding && (props.dense ? 'hms-card--pad-sm' : 'hms-card--pad'),
    props.class
  )
);
</script>

<template>
  <div :class="classes">
    <slot />
  </div>
</template>

<style scoped>
.hms-card {
  background: var(--hms-panel-bg);
  border: 1px solid var(--hms-border);
  border-radius: var(--hms-radius-xl);
  box-shadow: var(--hms-shadow-md);
  color: var(--hms-text-primary);
}

.hms-card--strong {
  background: var(--hms-glass-bg-strong);
  backdrop-filter: blur(var(--hms-glass-blur)) saturate(var(--hms-glass-saturate));
  -webkit-backdrop-filter: blur(var(--hms-glass-blur)) saturate(var(--hms-glass-saturate));
  border-color: var(--hms-border-strong);
  box-shadow: var(--hms-shadow-lg), var(--hms-shadow-inner);
}

.hms-card--pad {
  padding: 1.15rem 1.25rem;
}

.hms-card--pad-sm {
  padding: 0.85rem 1rem;
}

.hms-card--hoverable {
  cursor: pointer;
  transition:
    transform var(--hms-duration-normal) var(--hms-ease-out),
    box-shadow var(--hms-duration-normal) var(--hms-ease-out),
    border-color var(--hms-duration-normal) var(--hms-ease-out);
}

.hms-card--hoverable:hover {
  transform: translateY(-2px);
  border-color: var(--hms-border-strong);
  box-shadow: var(--hms-shadow-lg);
}

.hms-card--hoverable:focus-visible {
  outline: 2px solid var(--hms-accent);
  outline-offset: 2px;
}

@media (prefers-reduced-motion: reduce) {
  .hms-card--hoverable:hover {
    transform: none;
  }
}
</style>
