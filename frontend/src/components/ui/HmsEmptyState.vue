<script setup>
import { Inbox } from 'lucide-vue-next';
import { cn } from '../../utils/cn';

defineProps({
  title: { type: String, default: 'Nothing here yet' },
  description: { type: String, default: '' },
  class: { type: String, default: '' },
});
</script>

<template>
  <div
    :class="
      cn(
        'flex flex-col items-center justify-center rounded-hms-2xl border border-dashed border-hms-border bg-hms-surface px-6 py-14 text-center',
        $props.class
      )
    "
  >
    <div
      class="mb-4 flex h-12 w-12 items-center justify-center rounded-hms-xl bg-hms-accent-muted text-hms-accent"
    >
      <slot name="icon">
        <Inbox :size="22" aria-hidden="true" />
      </slot>
    </div>
    <h3 class="text-hms-lg font-semibold text-hms-text-primary">{{ title }}</h3>
    <p v-if="description" class="mt-1 max-w-md text-hms-sm text-hms-text-secondary">
      {{ description }}
    </p>
    <div v-if="$slots.actions" class="mt-5">
      <slot name="actions" />
    </div>
  </div>
</template>
