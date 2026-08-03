<script setup>
import { cn } from '../../utils/cn';

defineProps({
  lines: { type: Number, default: 3 },
  class: { type: String, default: '' },
});
</script>

<template>
  <div :class="cn('space-y-3', $props.class)" role="status" aria-label="Loading">
    <div
      v-for="n in lines"
      :key="n"
      class="hms-skeleton h-4"
      :style="{ width: n === lines ? '66%' : '100%' }"
    />
  </div>
</template>
