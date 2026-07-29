/* eslint-env node */

const { configure } = require('quasar/wrappers');

module.exports = configure(function (ctx) {
  // Production is hosted at domain root (e.g. https://claims.aquacy.me/).
  // Do NOT default to /frontend/ — that causes /frontend/assets 404s on subdomain deploys.
  // Do not set PUBLIC_PATH=/ in Git Bash on Windows (path mangling); leave unset for "/".
  const publicPath =
    process.env.PUBLIC_PATH != null && String(process.env.PUBLIC_PATH).trim() !== ''
      ? String(process.env.PUBLIC_PATH).trim()
      : '/';

  // Live API is at app.aquacy.me. api.aquacy.me currently serves static HTML, not FastAPI.
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
      plugins: [
        'Notify',
        'Dialog',
        'Loading'
      ]
    },
    boot: [
      'icons',
      'axios',
      'pinia'
    ],
    iconSet: 'material-icons',
    build: {
      target: {
        browser: ['es2019', 'edge88', 'firefox78', 'chrome87', 'safari13.1'],
        node: 'node20'
      },
      vueRouterMode: 'history',
      // Override API: API_BASE_URL=https://app.aquacy.me/api npx quasar build
      publicPath,
      env: {
        API_BASE_URL: apiBaseUrl,
      }
    },
    devServer: {
      port: 9000,
      open: false
    },
  };
});
