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
    const data = res.data || {};
    emit('refreshed', data);
    const info = data.ghims_refresh || {};
    let message = 'Latest GHIMS services loaded';
    if (info.note) {
      message = info.note;
    } else if (info.drug_qty_gt_one > 0) {
      message = `Updated ${info.drug_qty_gt_one} drug quantity(ies) from GHIMS`;
    }
    $q.notify({
      type: info.note && info.drug_qty_gt_one === 0 ? 'warning' : 'positive',
      message,
      position: 'top',
      timeout: info.note ? 8000 : 3500,
    });
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
