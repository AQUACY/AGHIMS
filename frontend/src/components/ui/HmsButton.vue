<script setup>
import { computed } from 'vue';
import { cn } from '../../utils/cn';

const props = defineProps({
  variant: {
    type: String,
    default: 'primary',
    validator: (v) =>
      ['primary', 'secondary', 'ghost', 'danger', 'healthcare', 'outline', 'soft'].includes(v),
  },
  size: {
    type: String,
    default: 'md',
    validator: (v) => ['sm', 'md', 'lg'].includes(v),
  },
  loading: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  block: { type: Boolean, default: false },
  type: { type: String, default: 'button' },
});

const emit = defineEmits(['click']);

const classes = computed(() =>
  cn(
    'hms-btn',
    `hms-btn--${props.variant}`,
    `hms-btn--${props.size}`,
    props.block && 'hms-btn--block',
    props.loading && 'hms-btn--loading'
  )
);

function onClick(e) {
  if (!props.loading && !props.disabled) emit('click', e);
}
</script>

<template>
  <button
    :type="type"
    :class="classes"
    :disabled="disabled || loading"
    :aria-busy="loading || undefined"
    @click="onClick"
  >
    <span
      v-if="loading"
      class="hms-btn__spinner"
      aria-hidden="true"
    />
    <span class="hms-btn__label"><slot /></span>
  </button>
</template>

<style scoped>
.hms-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.45rem;
  border: 1px solid transparent;
  font-family: var(--hms-font-sans);
  font-weight: 650;
  letter-spacing: -0.01em;
  line-height: 1;
  cursor: pointer;
  user-select: none;
  white-space: nowrap;
  transition:
    background-color var(--hms-duration-fast) var(--hms-ease-out),
    border-color var(--hms-duration-fast) var(--hms-ease-out),
    color var(--hms-duration-fast) var(--hms-ease-out),
    box-shadow var(--hms-duration-fast) var(--hms-ease-out),
    transform var(--hms-duration-fast) var(--hms-ease-out);
}

.hms-btn:focus-visible {
  outline: 2px solid var(--hms-accent);
  outline-offset: 2px;
}

.hms-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none !important;
  box-shadow: none !important;
}

.hms-btn--sm {
  height: 2rem;
  padding: 0 0.75rem;
  font-size: var(--hms-text-sm);
  border-radius: var(--hms-radius-md);
}

.hms-btn--md {
  height: 2.375rem;
  padding: 0 1rem;
  font-size: var(--hms-text-base);
  border-radius: var(--hms-radius-lg);
}

.hms-btn--lg {
  height: 2.75rem;
  padding: 0 1.25rem;
  font-size: var(--hms-text-lg);
  border-radius: var(--hms-radius-lg);
}

.hms-btn--block {
  width: 100%;
}

.hms-btn--primary {
  background: linear-gradient(180deg, #4b8ff7 0%, var(--hms-accent) 100%);
  color: #fff;
  box-shadow: var(--hms-shadow-sm), var(--hms-shadow-inner);
}

.hms-btn--primary:hover:not(:disabled) {
  background: linear-gradient(180deg, var(--hms-accent) 0%, var(--hms-accent-hover) 100%);
  box-shadow: var(--hms-shadow-glow-accent);
  transform: translateY(-1px);
}

.hms-btn--primary:active:not(:disabled) {
  transform: translateY(0);
}

.hms-btn--secondary {
  background: var(--hms-panel-bg);
  color: var(--hms-text-primary);
  border-color: var(--hms-border-strong);
  box-shadow: var(--hms-shadow-sm);
}

.hms-btn--secondary:hover:not(:disabled) {
  background: var(--hms-surface-hover);
  border-color: var(--hms-border-strong);
  transform: translateY(-1px);
}

.hms-btn--soft {
  background: var(--hms-accent-muted);
  color: var(--hms-accent);
  border-color: transparent;
}

.hms-btn--soft:hover:not(:disabled) {
  background: rgba(59, 130, 246, 0.22);
}

.hms-btn--outline {
  background: transparent;
  color: var(--hms-accent);
  border-color: rgba(59, 130, 246, 0.4);
}

.hms-btn--outline:hover:not(:disabled) {
  background: var(--hms-accent-muted);
}

.hms-btn--ghost {
  background: transparent;
  color: var(--hms-text-secondary);
}

.hms-btn--ghost:hover:not(:disabled) {
  background: var(--hms-surface);
  color: var(--hms-text-primary);
}

.hms-btn--healthcare {
  background: linear-gradient(180deg, #22d3ee 0%, var(--hms-healthcare) 100%);
  color: #042f2e;
  box-shadow: var(--hms-shadow-sm);
}

.hms-btn--danger {
  background: var(--hms-critical);
  color: #fff;
  box-shadow: var(--hms-shadow-sm);
}

.hms-btn--danger:hover:not(:disabled) {
  filter: brightness(1.05);
}

.hms-btn__spinner {
  width: 0.9rem;
  height: 0.9rem;
  border: 2px solid currentColor;
  border-right-color: transparent;
  border-radius: 50%;
  animation: hms-btn-spin 0.65s linear infinite;
}

.hms-btn__label {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
}

@keyframes hms-btn-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (prefers-reduced-motion: reduce) {
  .hms-btn,
  .hms-btn:hover:not(:disabled) {
    transform: none !important;
  }
  .hms-btn__spinner {
    animation: none;
  }
}
</style>
