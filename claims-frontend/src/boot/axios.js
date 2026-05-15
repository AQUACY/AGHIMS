import { boot } from 'quasar/wrappers';
import api from '../services/api';

export default boot(({ app }) => {
  app.config.globalProperties.$api = api;
});
