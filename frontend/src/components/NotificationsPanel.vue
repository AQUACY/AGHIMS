<template>
  <aside class="notice-panel" aria-label="Notifications">
    <header class="notice-head">
      <div class="notice-brand">
        <span class="notice-bell" aria-hidden="true">
          <q-icon name="notifications" size="20px" />
        </span>
        <div>
          <h2>Notifications</h2>
          <p>{{ unreadCount }} unread</p>
        </div>
      </div>
      <div class="notice-head-actions">
        <button type="button" class="notice-icon-btn" aria-label="Refresh" :disabled="loading" @click="loadNotifications(true)">
          <q-icon name="refresh" size="18px" :class="{ spin: loading }" />
        </button>
        <button type="button" class="notice-icon-btn" aria-label="Close notifications" @click="emit('close')">
          <q-icon name="close" size="18px" />
        </button>
      </div>
    </header>

    <div class="notice-toolbar">
      <div class="notice-filters" role="tablist" aria-label="Filter notifications">
        <button
          v-for="filter in filters"
          :key="filter.id"
          type="button"
          role="tab"
          class="notice-chip"
          :class="{ 'is-active': activeFilter === filter.id }"
          :aria-selected="activeFilter === filter.id"
          @click="activeFilter = filter.id"
        >
          {{ filter.label }}
          <span v-if="filter.count">{{ filter.count }}</span>
        </button>
      </div>
      <button
        v-if="unreadCount > 0"
        type="button"
        class="notice-text-btn notice-mark"
        :disabled="processing"
        @click="markAllRead"
      >
        Mark all read
      </button>
    </div>

    <div class="notice-scroll">
      <div v-if="loading && notifications.length === 0" class="notice-skeleton" aria-hidden="true">
        <div v-for="n in 4" :key="n" class="notice-skel" />
      </div>

      <div v-else-if="visible.length === 0" class="notice-empty">
        <span class="notice-empty-icon" aria-hidden="true">
          <q-icon name="notifications_none" size="28px" />
        </span>
        <strong>{{ emptyTitle }}</strong>
        <p>{{ emptyCopy }}</p>
      </div>

      <ul v-else class="notice-list">
        <li v-for="notification in visible" :key="notification.id">
          <article
            class="notice-card"
            :class="[`tone-${kindOf(notification).tone}`, { 'is-unread': !notification.is_read }]"
          >
            <button type="button" class="notice-open" @click="handleNotificationClick(notification)">
              <span class="notice-glyph" aria-hidden="true">
                <q-icon :name="kindOf(notification).icon" size="18px" />
              </span>
              <span class="notice-body">
                <span class="notice-kicker">
                  <span class="notice-kind">{{ kindOf(notification).label }}</span>
                  <span class="notice-time">{{ formatDateTime(notification.created_at) }}</span>
                </span>
                <span class="notice-title">{{ notification.title }}</span>
                <span class="notice-message">{{ notification.message }}</span>
                <span v-if="kindOf(notification).action" class="notice-go">
                  {{ kindOf(notification).action }}
                  <q-icon name="arrow_forward" size="14px" />
                </span>
              </span>
              <span v-if="!notification.is_read" class="notice-dot" aria-label="Unread" />
            </button>
            <button
              type="button"
              class="notice-dismiss"
              aria-label="Remove notification"
              @click="deleteNotification(notification)"
            >
              <q-icon name="close" size="14px" />
            </button>
          </article>
        </li>
      </ul>

      <div v-if="hasMore" class="notice-more">
        <button type="button" class="notice-text-btn" :disabled="loading" @click="loadMore">
          {{ loading ? 'Loading…' : 'Load earlier' }}
        </button>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { Notify } from 'quasar';
import { notificationsAPI } from '../services/api';
import { useAppModeStore, APP_MODES } from '../stores/appMode';

const emit = defineEmits(['close', 'count-updated']);

const router = useRouter();
const appModeStore = useAppModeStore();

const KINDS = {
  requisition_created: {
    label: 'New requisition',
    icon: 'add_shopping_cart',
    tone: 'info',
    group: 'requisition',
    action: 'Open requisition',
  },
  requisition_approved: {
    label: 'Approved',
    icon: 'check_circle',
    tone: 'success',
    group: 'requisition',
    action: 'Open requisition',
  },
  requisition_rejected: {
    label: 'Rejected',
    icon: 'cancel',
    tone: 'critical',
    group: 'requisition',
    action: 'Open requisition',
  },
  requisition_fulfilled: {
    label: 'Fully fulfilled',
    icon: 'inventory',
    tone: 'healthcare',
    group: 'requisition',
    action: 'Open requisition',
  },
  requisition_partially_fulfilled: {
    label: 'Partly fulfilled',
    icon: 'inventory_2',
    tone: 'warning',
    group: 'requisition',
    action: 'Open requisition',
  },
  requisition_fulfillment_reverted: {
    label: 'Fulfillment reversed',
    icon: 'undo',
    tone: 'warning',
    group: 'requisition',
    action: 'Open requisition',
  },
  requisition_updated: {
    label: 'Requisition updated',
    icon: 'edit_note',
    tone: 'accent',
    group: 'requisition',
    action: 'Open requisition',
  },
  stock_pending_approval: {
    label: 'Stock waiting',
    icon: 'hourglass_top',
    tone: 'warning',
    group: 'stock',
    action: 'Open store stock',
  },
  stock_approved: {
    label: 'Stock approved',
    icon: 'verified',
    tone: 'success',
    group: 'stock',
    action: 'Open store stock',
  },
  stock_rejected: {
    label: 'Stock rejected',
    icon: 'block',
    tone: 'critical',
    group: 'stock',
    action: 'Open store stock',
  },
};

const FALLBACK_KIND = {
  label: 'Notice',
  icon: 'notifications',
  tone: 'accent',
  group: 'other',
  action: '',
};

const notifications = ref([]);
const loading = ref(false);
const processing = ref(false);
const page = ref(1);
const pageSize = ref(20);
const total = ref(0);
const unreadCount = ref(0);
const activeFilter = ref('all');

const hasMore = computed(() => notifications.value.length < total.value);

const kindOf = (notification) => KINDS[notification.notification_type] || FALLBACK_KIND;

const visible = computed(() => notifications.value.filter((notification) => {
  const kind = kindOf(notification);
  if (activeFilter.value === 'unread') return !notification.is_read;
  if (activeFilter.value === 'requisition') return kind.group === 'requisition';
  if (activeFilter.value === 'stock') return kind.group === 'stock';
  return true;
}));

const filters = computed(() => [
  { id: 'all', label: 'All', count: notifications.value.length },
  { id: 'unread', label: 'Unread', count: notifications.value.filter((n) => !n.is_read).length },
  { id: 'requisition', label: 'Requisitions', count: notifications.value.filter((n) => kindOf(n).group === 'requisition').length },
  { id: 'stock', label: 'Stock', count: notifications.value.filter((n) => kindOf(n).group === 'stock').length },
]);

const emptyTitle = computed(() => {
  if (activeFilter.value === 'unread') return 'You are caught up';
  if (activeFilter.value === 'requisition') return 'No requisition notices';
  if (activeFilter.value === 'stock') return 'No stock notices';
  return 'Nothing waiting';
});

const emptyCopy = computed(() => {
  if (activeFilter.value === 'unread') return 'New requisitions and stock decisions will land here.';
  if (activeFilter.value === 'requisition') return 'Approvals, rejections, and fulfillments show in this list.';
  if (activeFilter.value === 'stock') return 'Stock waiting for approval, and the decision that follows, show here.';
  return 'Requisition and store-stock activity for your account appears here.';
});

const loadNotifications = async (reset = false) => {
  if (reset) {
    page.value = 1;
    notifications.value = [];
  }

  loading.value = true;
  try {
    const response = await notificationsAPI.getAll({
      page: page.value,
      page_size: pageSize.value,
    });

    const incoming = response.data.notifications || [];
    notifications.value = reset ? incoming : notifications.value.concat(incoming);
    total.value = response.data.total || 0;
    unreadCount.value = response.data.unread_count || 0;
    emit('count-updated', unreadCount.value);
  } catch (error) {
    console.error('Error loading notifications:', error);
    Notify.create({
      type: 'negative',
      message: 'Failed to load notifications',
      position: 'top',
    });
  } finally {
    loading.value = false;
  }
};

const loadMore = () => {
  page.value += 1;
  loadNotifications(false);
};

const markAllRead = async () => {
  processing.value = true;
  try {
    await notificationsAPI.markAllRead();
    Notify.create({
      type: 'positive',
      message: 'All notifications marked as read',
      position: 'top',
    });
    loadNotifications(true);
  } catch (error) {
    console.error('Error marking all as read:', error);
    Notify.create({
      type: 'negative',
      message: 'Failed to mark all as read',
      position: 'top',
    });
  } finally {
    processing.value = false;
  }
};

const destinationFor = (notification) => {
  const kind = kindOf(notification);
  const inventory = appModeStore.currentMode === APP_MODES.INVENTORY;
  if (kind.group === 'requisition' && notification.related_id) {
    return {
      name: inventory ? 'InventoryModeRequisitions' : 'PharmacyRequisitions',
      query: { requisitionId: notification.related_id },
    };
  }
  if (kind.group === 'stock') {
    return {
      name: inventory ? 'InventoryModeStoreStock' : 'StoreStockManagement',
      query: notification.related_id ? { stockId: notification.related_id } : {},
    };
  }
  return null;
};

const handleNotificationClick = async (notification) => {
  if (!notification.is_read) {
    try {
      await notificationsAPI.markRead(notification.id);
      notification.is_read = true;
      unreadCount.value = Math.max(0, unreadCount.value - 1);
      emit('count-updated', unreadCount.value);
    } catch (error) {
      console.error('Error marking notification as read:', error);
    }
  }

  const destination = destinationFor(notification);
  if (!destination) return;
  emit('close');
  router.push(destination).catch(() => {});
};

const deleteNotification = async (notification) => {
  const wasUnread = !notification.is_read;
  try {
    await notificationsAPI.delete(notification.id);
    notifications.value = notifications.value.filter((n) => n.id !== notification.id);
    total.value = Math.max(0, total.value - 1);
    if (wasUnread) {
      unreadCount.value = Math.max(0, unreadCount.value - 1);
      emit('count-updated', unreadCount.value);
    }
  } catch (error) {
    console.error('Error deleting notification:', error);
    Notify.create({
      type: 'negative',
      message: 'Failed to delete notification',
      position: 'top',
    });
  }
};

const formatDateTime = (dateTime) => {
  if (!dateTime) return '';
  const date = new Date(dateTime);
  const now = new Date();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
};

onMounted(() => {
  loadNotifications(true);
});
</script>

<style scoped>
.notice-panel {
  width: min(440px, 100vw);
  height: 100vh;
  max-height: 100vh;
  pointer-events: auto;
  display: flex;
  flex-direction: column;
  background: var(--hms-glass-bg-strong);
  color: var(--hms-text-primary);
  border-left: 1px solid var(--hms-border-strong);
  box-shadow: var(--hms-shadow-lg);
  font-family: var(--hms-font-sans);
}

.notice-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--hms-space-3);
  padding: var(--hms-space-5) var(--hms-space-5) var(--hms-space-4);
}

.notice-brand {
  display: flex;
  align-items: center;
  gap: var(--hms-space-3);
  min-width: 0;
}

.notice-brand h2 {
  margin: 0;
  font-size: var(--hms-text-xl);
  font-weight: 700;
  letter-spacing: var(--hms-tracking-tight);
  line-height: var(--hms-leading-tight);
}

.notice-brand p {
  margin: 2px 0 0;
  font-size: var(--hms-text-sm);
  color: var(--hms-text-secondary);
}

.notice-bell {
  width: 40px;
  height: 40px;
  display: grid;
  place-items: center;
  border-radius: var(--hms-radius-lg);
  background: var(--hms-accent-muted);
  color: var(--hms-accent);
  box-shadow: var(--hms-shadow-inner);
}

.notice-toolbar {
  display: flex;
  flex-direction: column;
  gap: var(--hms-space-3);
  padding: 0 var(--hms-space-5) var(--hms-space-4);
  border-bottom: 1px solid var(--hms-border);
}

.notice-filters {
  display: flex;
  flex-wrap: wrap;
  gap: var(--hms-space-2);
}

.notice-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  height: 30px;
  padding: 0 0.7rem;
  border-radius: var(--hms-radius-full);
  border: 1px solid var(--hms-border);
  background: var(--hms-surface);
  color: var(--hms-text-secondary);
  font: inherit;
  font-size: var(--hms-text-xs);
  font-weight: 650;
  cursor: pointer;
  transition: background-color var(--hms-duration-fast) var(--hms-ease-out),
    color var(--hms-duration-fast) var(--hms-ease-out),
    border-color var(--hms-duration-fast) var(--hms-ease-out);
}

.notice-chip span {
  min-width: 1.1rem;
  padding: 0 0.28rem;
  border-radius: var(--hms-radius-full);
  background: var(--hms-surface-active);
  color: var(--hms-text-secondary);
  font-variant-numeric: tabular-nums;
  text-align: center;
}

.notice-chip.is-active {
  background: var(--hms-accent);
  border-color: var(--hms-accent);
  color: var(--hms-text-inverse);
  box-shadow: var(--hms-shadow-glow-accent);
}

.notice-chip.is-active span {
  background: color-mix(in srgb, white 22%, transparent);
  color: inherit;
}

.notice-head-actions {
  display: flex;
  align-items: center;
  gap: 0.15rem;
}

.notice-mark {
  align-self: flex-end;
}

.notice-text-btn,
.notice-icon-btn {
  border: 0;
  background: transparent;
  color: var(--hms-text-secondary);
  font: inherit;
  cursor: pointer;
}

.notice-text-btn {
  height: 32px;
  padding: 0 0.55rem;
  border-radius: var(--hms-radius-md);
  font-size: var(--hms-text-sm);
  font-weight: 650;
  color: var(--hms-accent);
}

.notice-text-btn:hover,
.notice-icon-btn:hover {
  background: var(--hms-surface-hover);
  color: var(--hms-text-primary);
}

.notice-text-btn:disabled,
.notice-icon-btn:disabled {
  opacity: 0.55;
  cursor: default;
}

.notice-icon-btn {
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
  border-radius: var(--hms-radius-md);
}

.notice-scroll {
  flex: 1;
  overflow: auto;
  padding: var(--hms-space-3) var(--hms-space-3) var(--hms-space-6);
}

.notice-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--hms-space-2);
}

.notice-card {
  position: relative;
  display: flex;
  align-items: stretch;
  border: 1px solid var(--hms-border);
  border-radius: var(--hms-radius-xl);
  background: var(--hms-bg-elevated);
  box-shadow: var(--hms-shadow-sm);
  overflow: hidden;
}

.notice-card.is-unread {
  background: color-mix(in srgb, var(--hms-accent) 7%, var(--hms-bg-elevated));
}

.notice-open {
  flex: 1;
  min-width: 0;
  display: flex;
  gap: var(--hms-space-3);
  align-items: flex-start;
  padding: var(--hms-space-3) 2.2rem var(--hms-space-3) var(--hms-space-3);
  border: 0;
  background: transparent;
  color: inherit;
  font: inherit;
  text-align: left;
  cursor: pointer;
}

.notice-open:hover {
  background: var(--hms-surface-hover);
}

.notice-glyph {
  width: 36px;
  height: 36px;
  flex: none;
  display: grid;
  place-items: center;
  border-radius: var(--hms-radius-md);
  background: var(--hms-accent-muted);
  color: var(--hms-accent);
}

.tone-success .notice-glyph { background: var(--hms-success-muted); color: var(--hms-success); }
.tone-warning .notice-glyph { background: var(--hms-warning-muted); color: var(--hms-warning); }
.tone-critical .notice-glyph { background: var(--hms-critical-muted); color: var(--hms-critical); }
.tone-info .notice-glyph { background: var(--hms-info-muted); color: var(--hms-info); }
.tone-healthcare .notice-glyph { background: var(--hms-healthcare-muted); color: var(--hms-healthcare); }
.tone-accent .notice-glyph { background: var(--hms-accent-muted); color: var(--hms-accent); }

.notice-body {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.notice-kicker {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--hms-space-3);
}

.notice-kind {
  font-size: var(--hms-text-xs);
  font-weight: 700;
  letter-spacing: var(--hms-tracking-wide);
  text-transform: uppercase;
  color: var(--hms-text-muted);
}

.notice-time {
  flex: none;
  font-size: var(--hms-text-xs);
  color: var(--hms-text-muted);
  font-variant-numeric: tabular-nums;
}

.notice-title {
  font-size: var(--hms-text-base);
  font-weight: 700;
  letter-spacing: -0.01em;
  line-height: var(--hms-leading-snug);
  color: var(--hms-text-primary);
}

.notice-card.is-unread .notice-title {
  color: var(--hms-text-primary);
}

.notice-message {
  font-size: var(--hms-text-sm);
  line-height: var(--hms-leading-normal);
  color: var(--hms-text-secondary);
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.notice-go {
  display: inline-flex;
  align-items: center;
  gap: 0.2rem;
  margin-top: 0.15rem;
  font-size: var(--hms-text-xs);
  font-weight: 700;
  color: var(--hms-accent);
}

.notice-dot {
  position: absolute;
  top: 0.85rem;
  right: 2.15rem;
  width: 8px;
  height: 8px;
  border-radius: var(--hms-radius-full);
  background: var(--hms-accent);
  box-shadow: 0 0 0 3px var(--hms-accent-muted);
}

.notice-dismiss {
  position: absolute;
  top: 0.35rem;
  right: 0.35rem;
  width: 26px;
  height: 26px;
  display: grid;
  place-items: center;
  border: 0;
  border-radius: var(--hms-radius-md);
  background: transparent;
  color: var(--hms-text-muted);
  cursor: pointer;
}

.notice-dismiss:hover {
  background: var(--hms-surface-active);
  color: var(--hms-text-primary);
}

.notice-empty {
  margin: var(--hms-space-8) var(--hms-space-4);
  text-align: center;
}

.notice-empty-icon {
  width: 56px;
  height: 56px;
  margin: 0 auto var(--hms-space-3);
  display: grid;
  place-items: center;
  border-radius: var(--hms-radius-xl);
  background: var(--hms-surface);
  color: var(--hms-text-muted);
  border: 1px solid var(--hms-border);
}

.notice-empty strong {
  display: block;
  font-size: var(--hms-text-lg);
  letter-spacing: var(--hms-tracking-tight);
}

.notice-empty p {
  margin: var(--hms-space-2) auto 0;
  max-width: 28ch;
  font-size: var(--hms-text-sm);
  line-height: var(--hms-leading-relaxed);
  color: var(--hms-text-secondary);
}

.notice-more {
  display: flex;
  justify-content: center;
  padding: var(--hms-space-3) 0 var(--hms-space-2);
}

.notice-skel {
  height: 92px;
  margin-bottom: var(--hms-space-2);
  border-radius: var(--hms-radius-xl);
  background: linear-gradient(
    90deg,
    var(--hms-surface) 0%,
    var(--hms-surface-hover) 50%,
    var(--hms-surface) 100%
  );
  background-size: 200% 100%;
  animation: notice-shimmer 1.2s ease-in-out infinite;
}

.spin {
  animation: notice-spin 0.8s linear infinite;
}

@keyframes notice-shimmer {
  from { background-position: 100% 0; }
  to { background-position: -100% 0; }
}

@keyframes notice-spin {
  to { transform: rotate(360deg); }
}

@media (prefers-reduced-motion: reduce) {
  .notice-skel,
  .spin {
    animation: none;
  }
}
</style>
