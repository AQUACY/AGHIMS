import { boot } from 'quasar/wrappers';
import { createPinia } from 'pinia';
import { useAuthStore } from '../stores/auth';

export default boot(({ app }) => {
  const pinia = createPinia();
  app.use(pinia);

  // Initialize auth after Pinia is set up
  const authStore = useAuthStore();
  authStore.initAuth();
});

