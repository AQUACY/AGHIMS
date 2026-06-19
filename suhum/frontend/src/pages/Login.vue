<template>
  <div class="login-background" :class="themeStore.isDark ? 'dark-gradient' : 'light-gradient'">
    <div class="login-container">
      <q-card class="login-card glass-card" flat>
        <q-card-section>
          <div class="text-h5 text-center q-mb-md text-weight-bold">{{ facilityStore.displayName }}</div>
          <div class="text-subtitle2 text-center q-mb-lg">Suhum — sign in to continue</div>
        </q-card-section>
        <q-card-section>
          <q-form @submit="onSubmit" class="q-gutter-md">
            <q-input v-model="username" filled label="Username" :rules="[(v) => !!v || 'Required']" />
            <q-input v-model="password" filled type="password" label="Password" :rules="[(v) => !!v || 'Required']" />
            <q-btn unelevated label="Login" type="submit" class="full-width" color="primary" :loading="loading" />
          </q-form>
        </q-card-section>
      </q-card>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { useAuthStore } from '../stores/auth';
import { useThemeStore } from '../stores/theme';
import { useFacilityStore } from '../stores/facility';

const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();
const themeStore = useThemeStore();
const facilityStore = useFacilityStore();

const username = ref('');
const password = ref('');
const loading = ref(false);

onMounted(() => {
  themeStore.initTheme();
  facilityStore.fetchPublic();
  if (authStore.isAuthenticated) router.replace({ name: 'Home' });
});

async function onSubmit() {
  loading.value = true;
  const ok = await authStore.login(username.value, password.value);
  loading.value = false;
  if (!ok) return;
  const redirect = route.query.redirect || '/home';
  router.replace(redirect);
}
</script>

<style scoped>
.login-background {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
}
.light-gradient {
  background: linear-gradient(135deg, #e8f4f8 0%, #f5f7fa 100%);
}
.dark-gradient {
  background: linear-gradient(135deg, #1a1a2e 0%, #0f3460 100%);
}
.login-card {
  width: 100%;
  max-width: 400px;
  padding: 8px;
}
</style>
