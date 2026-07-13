<template>
  <div>
    <div class="row items-center q-mb-md">
      <div class="col">
        <div class="text-subtitle1">
          Notifications
          <q-badge v-if="unreadCount > 0" color="negative" :label="unreadCount" class="q-ml-sm" />
        </div>
      </div>
      <div class="col-auto">
        <q-btn
          v-if="unreadCount > 0"
          flat
          dense
          label="Mark All Read"
          @click="markAllRead"
          :loading="processing"
        />
        <q-btn
          flat
          dense
          round
          icon="refresh"
          @click="loadNotifications"
          :loading="loading"
        />
      </div>
    </div>

    <q-list v-if="notifications.length > 0" separator>
      <q-item
        v-for="notification in notifications"
        :key="notification.id"
        :class="{ 'bg-blue-1': !notification.is_read }"
        clickable
        @click="handleNotificationClick(notification)"
      >
        <q-item-section avatar>
          <q-icon
            :name="getNotificationIcon(notification.notification_type)"
            :color="getNotificationColor(notification.notification_type)"
            size="md"
          />
        </q-item-section>

        <q-item-section>
          <q-item-label :class="{ 'text-weight-bold': !notification.is_read }">
            {{ notification.title }}
          </q-item-label>
          <q-item-label caption lines="2">
            {{ notification.message }}
          </q-item-label>
          <q-item-label caption class="q-mt-xs">
            {{ formatDateTime(notification.created_at) }}
          </q-item-label>
        </q-item-section>

        <q-item-section side>
          <q-btn
            flat
            dense
            round
            icon="close"
            size="sm"
            @click.stop="deleteNotification(notification.id)"
          />
        </q-item-section>
      </q-item>
    </q-list>

    <div v-else class="text-center q-pa-lg text-grey-6">
      <q-icon name="notifications_off" size="3em" class="q-mb-md" />
      <div>No notifications</div>
    </div>

    <div v-if="hasMore" class="text-center q-mt-md">
      <q-btn
        flat
        label="Load More"
        @click="loadMore"
        :loading="loading"
      />
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { Notify } from 'quasar';
import { notificationsAPI } from '../services/api';

export default {
  name: 'NotificationsPanel',
  emits: ['close', 'count-updated'],
  setup(props, { emit }) {
    const router = useRouter();
    
    const notifications = ref([]);
    const loading = ref(false);
    const processing = ref(false);
    const page = ref(1);
    const pageSize = ref(20);
    const total = ref(0);
    const unreadCount = ref(0);

    const hasMore = computed(() => {
      return notifications.value.length < total.value;
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
        
        if (reset) {
          notifications.value = response.data.notifications || [];
        } else {
          notifications.value.push(...(response.data.notifications || []));
        }
        
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
      page.value++;
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

    const handleNotificationClick = async (notification) => {
      // Mark as read if unread
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

      // Navigate based on notification type
      if (notification.related_type === 'requisition' && notification.related_id) {
        emit('close');
        router.push({
          name: 'PharmacyRequisitions',
          query: { requisitionId: notification.related_id }
        });
      }
    };

    const deleteNotification = async (notificationId) => {
      try {
        await notificationsAPI.delete(notificationId);
        notifications.value = notifications.value.filter(n => n.id !== notificationId);
        if (notifications.value.find(n => n.id === notificationId && !n.is_read)) {
          unreadCount.value = Math.max(0, unreadCount.value - 1);
          emit('count-updated', unreadCount.value);
        }
        Notify.create({
          type: 'positive',
          message: 'Notification deleted',
          position: 'top',
        });
      } catch (error) {
        console.error('Error deleting notification:', error);
        Notify.create({
          type: 'negative',
          message: 'Failed to delete notification',
          position: 'top',
        });
      }
    };

    const getNotificationIcon = (type) => {
      const icons = {
        requisition_created: 'add_shopping_cart',
        requisition_approved: 'check_circle',
        requisition_rejected: 'cancel',
        requisition_fulfilled: 'inventory',
        requisition_partially_fulfilled: 'inventory_2',
      };
      return icons[type] || 'notifications';
    };

    const getNotificationColor = (type) => {
      const colors = {
        requisition_created: 'blue',
        requisition_approved: 'green',
        requisition_rejected: 'red',
        requisition_fulfilled: 'positive',
        requisition_partially_fulfilled: 'orange',
      };
      return colors[type] || 'grey';
    };

    const formatDateTime = (dateTime) => {
      if (!dateTime) return '-';
      const date = new Date(dateTime);
      const now = new Date();
      const diffMs = now - date;
      const diffMins = Math.floor(diffMs / 60000);
      const diffHours = Math.floor(diffMs / 3600000);
      const diffDays = Math.floor(diffMs / 86400000);

      if (diffMins < 1) return 'Just now';
      if (diffMins < 60) return `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`;
      if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
      if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
      return date.toLocaleDateString();
    };

    onMounted(() => {
      loadNotifications(true);
    });

    return {
      notifications,
      loading,
      processing,
      unreadCount,
      hasMore,
      loadNotifications,
      loadMore,
      markAllRead,
      handleNotificationClick,
      deleteNotification,
      getNotificationIcon,
      getNotificationColor,
      formatDateTime,
    };
  },
};
</script>

<style scoped>
</style>

