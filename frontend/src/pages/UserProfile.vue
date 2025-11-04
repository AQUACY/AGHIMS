<template>
  <q-page class="q-pa-md">
    <div class="text-h4 q-mb-md text-weight-bold glass-text">User Profile</div>

    <q-card class="glass-card" flat>
      <q-card-section>
        <div class="text-h6 q-mb-md glass-text">Change Password</div>
        
        <q-form @submit="changePassword" class="q-gutter-md">
          <q-input
            v-model="passwordForm.currentPassword"
            filled
            type="password"
            label="Current Password *"
            :rules="[(val) => !!val || 'Current password is required']"
            lazy-rules
          />
          
          <q-input
            v-model="passwordForm.newPassword"
            filled
            type="password"
            label="New Password *"
            :rules="[
              (val) => !!val || 'New password is required',
              (val) => val.length >= 6 || 'Password must be at least 6 characters'
            ]"
            lazy-rules
          />
          
          <q-input
            v-model="passwordForm.confirmPassword"
            filled
            type="password"
            label="Confirm New Password *"
            :rules="[
              (val) => !!val || 'Please confirm your new password',
              (val) => val === passwordForm.newPassword || 'Passwords do not match'
            ]"
            lazy-rules
          />
          
          <div class="row q-gutter-md">
            <q-btn
              type="submit"
              color="primary"
              label="Change Password"
              :loading="changingPassword"
              :disable="!isFormValid"
              class="glass-button"
            />
            <q-btn
              flat
              label="Cancel"
              @click="goToDashboard"
              class="glass-button"
            />
          </div>
        </q-form>
      </q-card-section>
    </q-card>

    <!-- User Information Card -->
    <q-card class="q-mt-md glass-card" flat>
      <q-card-section>
        <div class="text-h6 q-mb-md glass-text">User Information</div>
        <div class="row q-gutter-md">
          <div class="col-12 col-md-6">
            <div class="text-body2 q-mb-xs" style="opacity: 0.7;">Username</div>
            <div class="text-body1 text-weight-medium glass-text">
              {{ authStore.user?.username || 'N/A' }}
            </div>
          </div>
          <div class="col-12 col-md-6">
            <div class="text-body2 q-mb-xs" style="opacity: 0.7;">Full Name</div>
            <div class="text-body1 text-weight-medium glass-text">
              {{ authStore.user?.full_name || 'N/A' }}
            </div>
          </div>
          <div class="col-12 col-md-6">
            <div class="text-body2 q-mb-xs" style="opacity: 0.7;">Email</div>
            <div class="text-body1 text-weight-medium glass-text">
              {{ authStore.user?.email || 'N/A' }}
            </div>
          </div>
          <div class="col-12 col-md-6">
            <div class="text-body2 q-mb-xs" style="opacity: 0.7;">Role</div>
            <div class="text-body1 text-weight-medium glass-text">
              {{ authStore.user?.role || 'N/A' }}
            </div>
          </div>
        </div>
      </q-card-section>
    </q-card>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useQuasar } from 'quasar';
import { useAuthStore } from '../stores/auth';
import { useThemeStore } from '../stores/theme';
import { authAPI } from '../services/api';

const $q = useQuasar();
const router = useRouter();
const authStore = useAuthStore();
const themeStore = useThemeStore();

const passwordForm = ref({
  currentPassword: '',
  newPassword: '',
  confirmPassword: '',
});

const changingPassword = ref(false);

const isFormValid = computed(() => {
  return (
    passwordForm.value.currentPassword &&
    passwordForm.value.newPassword &&
    passwordForm.value.confirmPassword &&
    passwordForm.value.newPassword.length >= 6 &&
    passwordForm.value.newPassword === passwordForm.value.confirmPassword
  );
});

const changePassword = async () => {
  if (!isFormValid.value) {
    $q.notify({
      type: 'warning',
      message: 'Please fill in all fields correctly',
      position: 'top',
    });
    return;
  }

  changingPassword.value = true;
  try {
    console.log('Attempting to change password...');
    const response = await authAPI.changePassword(
      passwordForm.value.currentPassword,
      passwordForm.value.newPassword
    );
    console.log('Password change response:', response);
    
    $q.notify({
      type: 'positive',
      message: 'Password changed successfully',
      position: 'top',
    });
    
    // Clear form
    passwordForm.value = {
      currentPassword: '',
      newPassword: '',
      confirmPassword: '',
    };
  } catch (error) {
    console.error('Password change error:', error);
    console.error('Error response:', error.response);
    console.error('Error URL:', error.config?.url);
    console.error('Error method:', error.config?.method);
    $q.notify({
      type: 'negative',
      message: error.response?.data?.detail || error.message || 'Failed to change password. Please ensure the backend server is running and has been restarted.',
      position: 'top',
    });
  } finally {
    changingPassword.value = false;
  }
};

const goToDashboard = () => {
  router.push('/');
};

onMounted(() => {
  themeStore.initTheme();
  // Refresh user data
  authStore.fetchUser();
});
</script>

<style scoped>
.glass-text {
  color: rgba(255, 255, 255, 0.9);
}

.glass-card {
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.glass-button {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
}
</style>

