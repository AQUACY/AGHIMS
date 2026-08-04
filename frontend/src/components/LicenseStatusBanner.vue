<template>
  <div v-if="eligible" class="license-status-banner-root">
    <div v-if="loading" class="license-banner muted">
      <q-spinner-dots size="sm" />
      <div class="license-body">Loading installation license…</div>
    </div>
    <div v-else-if="licenseBanner" class="license-banner" :class="licenseBanner.type">
      <q-icon :name="licenseBanner.icon || 'verified'" class="license-icon" />
      <div class="license-body">
        <div class="license-title">Installation license</div>
        <div class="license-line">
          <span class="label">Status</span>
          {{ licenseBanner.statusLabel }}
        </div>
        <div class="license-line">
          <span class="label">Expires</span>
          {{ licenseBanner.expiresLabel }}
        </div>
        <div v-if="licenseBanner.detail" class="license-detail">
          {{ licenseBanner.detail }}
        </div>
      </div>
    </div>
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
        detail:
          'Set LICENSE_ENFORCEMENT=true on the HMS server to show live expiry and validation here.',
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
        type: data.in_grace_period ? 'warning' : 'info',
        icon: data.in_grace_period ? 'schedule' : 'verified',
        statusLabel: data.in_grace_period ? 'Active (grace)' : 'Active',
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

watch(
  eligible,
  (ok) => {
    if (ok) loadBanner();
    else {
      loading.value = false;
      licenseBanner.value = null;
    }
  },
  { immediate: true }
);
</script>

<style scoped>
.license-status-banner-root {
  margin-bottom: 1rem;
  min-height: 48px;
}

.license-banner {
  display: flex;
  gap: 0.75rem;
  align-items: flex-start;
  padding: 0.9rem 1.1rem;
  border-radius: var(--hms-radius-xl);
  border: 1px solid var(--hms-border);
  background: var(--hms-glass-bg);
  backdrop-filter: blur(12px);
  color: var(--hms-text-primary);
}

.license-banner.info {
  border-color: rgba(59, 130, 246, 0.3);
  background: rgba(59, 130, 246, 0.08);
}

.license-banner.warning {
  border-color: rgba(245, 158, 11, 0.35);
  background: rgba(245, 158, 11, 0.1);
}

.license-banner.error {
  border-color: rgba(239, 68, 68, 0.35);
  background: rgba(239, 68, 68, 0.1);
}

.license-banner.muted {
  background: var(--hms-surface);
}

.license-icon {
  margin-top: 0.15rem;
  color: var(--hms-accent);
}

.license-banner.info .license-icon {
  color: var(--hms-accent);
}

.license-banner.warning .license-icon {
  color: var(--hms-warning);
}

.license-banner.error .license-icon {
  color: var(--hms-critical);
}

.license-body {
  min-width: 0;
}

.license-title {
  font-weight: 700;
  font-size: var(--hms-text-sm);
  margin-bottom: 0.25rem;
}

.license-line {
  font-size: var(--hms-text-sm);
  color: var(--hms-text-secondary);
}

.license-line .label {
  font-weight: 600;
  color: var(--hms-text-muted);
  margin-right: 0.35rem;
}

.license-detail {
  margin-top: 0.4rem;
  font-size: var(--hms-text-xs);
  color: var(--hms-text-muted);
}
</style>
