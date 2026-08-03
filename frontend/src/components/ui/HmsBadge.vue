<script setup>
import { computed } from 'vue';
import { cn } from '../../utils/cn';

const props = defineProps({
  tone: {
    type: String,
    default: 'accent',
    validator: (v) =>
      ['accent', 'healthcare', 'success', 'warning', 'critical', 'info', 'muted', 'neutral'].includes(v),
  },
  class: { type: String, default: '' },
});

const classes = computed(() => cn('hms-badge', `hms-badge--${props.tone}`, props.class));
</script>

<template>
  <span :class="classes"><slot /></span>
</template>

<style scoped>
.hms-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.2rem 0.55rem;
  border-radius: var(--hms-radius-full);
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  line-height: 1.2;
  border: 1px solid transparent;
}

.hms-badge--accent {
  background: var(--hms-accent-muted);
  color: var(--hms-accent);
  border-color: rgba(59, 130, 246, 0.2);
}

.hms-badge--healthcare {
  background: var(--hms-healthcare-muted);
  color: var(--hms-healthcare);
  border-color: rgba(6, 182, 212, 0.22);
}

.hms-badge--success {
  background: var(--hms-success-muted);
  color: var(--hms-success);
  border-color: rgba(34, 197, 94, 0.22);
}

.hms-badge--warning {
  background: var(--hms-warning-muted);
  color: #d97706;
  border-color: rgba(245, 158, 11, 0.25);
}

.body--dark .hms-badge--warning {
  color: #fbbf24;
}

.hms-badge--critical {
  background: var(--hms-critical-muted);
  color: var(--hms-critical);
  border-color: rgba(239, 68, 68, 0.22);
}

.hms-badge--info {
  background: var(--hms-info-muted);
  color: var(--hms-info);
  border-color: rgba(56, 189, 248, 0.22);
}

.hms-badge--muted,
.hms-badge--neutral {
  background: var(--hms-surface);
  color: var(--hms-text-secondary);
  border-color: var(--hms-border);
}
</style>
