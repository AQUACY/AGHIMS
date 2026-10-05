<script setup>
import { computed, ref } from 'vue';
import { useQuasar } from 'quasar';
import { companionVisitsAPI } from '../../services/api';
import HmsButton from '../ui/HmsButton.vue';

const props = defineProps({
  visit: { type: Object, default: null },
});
const emit = defineEmits(['refreshed']);

const $q = useQuasar();
const loading = ref(false);
const show = computed(() => (props.visit?.source || '') === 'ghims_live' && props.visit?.id);

async function refresh() {
  if (!props.visit?.id || loading.value) return;
  loading.value = true;
  try {
    const res = await companionVisitsAPI.refreshFromGhims(props.visit.id);
    emit('refreshed', res.data);
    $q.notify({ type: 'positive', message: 'Latest GHIMS services loaded', position: 'top' });
  } catch (e) {
    const detail = e.response?.data?.detail;
    $q.notify({
      type: 'negative',
      message: typeof detail === 'string' ? detail : 'Could not refresh from GHIMS',
      position: 'top',
    });
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <HmsButton v-if="show" variant="secondary" size="sm" :loading="loading" @click="refresh">
    Refresh from GHIMS
  </HmsButton>
</template>
