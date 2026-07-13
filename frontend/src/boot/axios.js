import { boot } from 'quasar/wrappers';
import api from '../services/api';

export default boot(({ app }) => {
  // Make axios available globally
  app.config.globalProperties.$api = api;
});

