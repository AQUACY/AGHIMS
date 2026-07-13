<template>
  <div v-if="eligible" class="license-status-banner-root q-mb-md">
    <q-banner v-if="loading" rounded dense class="bg-grey-4 text-dark">
      <q-spinner-dots size="sm" class="q-mr-sm" />
      Loading installation license…
    </q-banner>
    <q-banner v-else-if="licenseBanner" rounded :class="bannerClass">
      <template #avatar>
        <q-icon :name="licenseBanner.icon || 'verified'" />
      </template>
      <div class="text-subtitle2 text-weight-bold">Installation license</div>
      <div class="text-body1 q-mt-xs">
        <span class="text-weight-medium">Status:</span>
        {{ licenseBanner.statusLabel }}
      </div>
      <div class="text-body1 q-mt-xs">
        <span class="text-weight-medium">Expires:</span>
        {{ licenseBanner.expiresLabel }}
      </div>
      <div v-if="licenseBanner.detail" class="text-caption q-mt-sm">
        {{ licenseBanner.detail }}
      </div>
    </q-banner>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue';
import { useAuthStore } from '../stores/auth';
import { licenseAPI } from '../services/api';

const authStore = useAuthStore();
const loading = ref(true);
const licenseBanner = ref(null);

/** Admin, Management, or Super Admin — same as toolbar License link audience */
const eligible = computed(() => {
  const u = authStore.user;
  if (!authStore.isAuthenticated || !u) return false;
  if (Boolean(u.is_super_admin)) return true;
  return authStore.canAccess(['Admin', 'Management']);
});

function formatExpiry(iso) {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

async function loadBanner() {
  await nextTick();
  if (!eligible.value) {
    licenseBanner.value = null;
    loading.value = false;
    return;
  }

  loading.value = true;
  licenseBanner.value = null;

  const applyFromPayload = (data) => {
    if (!data.enforcement_enabled) {
      licenseBanner.value = {
        type: 'muted',
        icon: 'info',
        statusLabel: 'Enforcement off',
        expiresLabel: '—',
        detail: 'Set LICENSE_ENFORCEMENT=true on the HMS server to show live expiry and validation here.',
      };
      return;
    }

    const expiresLabel = formatExpiry(data.valid_until);

    if (data.has_valid_license) {
      const grace = data.in_grace_period
        ? 'Operating on connectivity grace until the next successful online check.'
        : '';
      const boot =
        data.awaiting_first_online_verify && data.online_bootstrap_deadline
          ? `Complete first online license verification by ${new Date(data.online_bootstrap_deadline).toLocaleString()}.`
          : '';
      const detail = [grace, boot].filter(Boolean).join(' ');
      licenseBanner.value = {
        type: 'info',
        icon: 'verified',
        statusLabel: 'Active',
        expiresLabel,
        detail: detail || null,
      };
    } else {
      licenseBanner.value = {
        type: 'warning',
        icon: 'schedule',
        statusLabel: 'Not valid',
        expiresLabel,
        detail: data.message || 'Users may be unable to sign in until the license is fixed.',
      };
    }
  };

  try {
    const { data } = await licenseAPI.getStatus();
    applyFromPayload(data);
  } catch {
    try {
      const { data } = await licenseAPI.getPublicStatus();
      applyFromPayload(data);
    } catch {
      licenseBanner.value = {
        type: 'error',
        icon: 'cloud_off',
        statusLabel: 'Could not load',
        expiresLabel: '—',
        detail: 'Check that the HMS API is running and you are still signed in.',
      };
    }
  } finally {
    loading.value = false;
  }
}

const bannerClass = computed(() => {
  const t = licenseBanner.value?.type;
  if (t === 'warning') return 'bg-orange-2 text-dark';
  if (t === 'error') return 'bg-red-2 text-dark';
  if (t === 'muted') return 'bg-grey-5 text-dark';
  return 'bg-blue-1 text-dark';
});

watch(eligible, (ok) => {
  if (ok) loadBanner();
  else {
    loading.value = false;
    licenseBanner.value = null;
  }
}, { immediate: true });
</script>

<style scoped>
.license-status-banner-root {
  min-height: 48px;
}
</style>
