/* eslint-env node */

const { configure } = require('quasar/wrappers');

module.exports = configure(function (ctx) {
  const publicPath =
    process.env.PUBLIC_PATH != null && String(process.env.PUBLIC_PATH).trim() !== ''
      ? String(process.env.PUBLIC_PATH).trim()
      : '/';

  const apiBaseUrl =
    process.env.API_BASE_URL != null && String(process.env.API_BASE_URL).trim() !== ''
      ? String(process.env.API_BASE_URL).trim()
      : ctx.dev
        ? 'http://localhost:8000/api'
        : 'https://app.aquacy.me/api';

  return {
    framework: {
      config: {
        dark: 'auto',
      },
      plugins: ['Notify', 'Dialog', 'Loading'],
    },
    boot: ['icons', 'axios', 'pinia'],
    iconSet: 'material-icons',
    build: {
      target: {
        browser: ['es2019', 'edge88', 'firefox78', 'chrome87', 'safari13.1'],
        node: 'node20',
      },
      vueRouterMode: 'history',
      publicPath,
      env: {
        API_BASE_URL: apiBaseUrl,
      },
    },
    devServer: {
      port: 9001,
      open: false,
    },
  };
});
