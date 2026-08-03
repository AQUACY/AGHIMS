<template>
  <q-btn
    v-if="showLink"
    flat
    dense
    no-caps
    icon="verified_user"
    label="License"
    class="header-ghost-btn"
    :to="{ name: 'LicenseSetup' }"
  >
    <q-tooltip>Installation license status and activation</q-tooltip>
  </q-btn>
</template>

<script setup>
import { computed } from 'vue';
import { useAuthStore } from '../stores/auth';

const authStore = useAuthStore();

const showLink = computed(
  () => authStore.isAuthenticated && authStore.canAccess(['Admin', 'Management']),
);
</script>
