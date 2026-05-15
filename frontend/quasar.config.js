/* eslint-env node */

const { configure } = require('quasar/wrappers');

module.exports = configure(function (ctx) {
  const publicPath =
    process.env.PUBLIC_PATH != null && String(process.env.PUBLIC_PATH).trim() !== ''
      ? String(process.env.PUBLIC_PATH).trim()
      : ctx.dev
        ? '/'
        : '/frontend/';

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
      // Production default: SPA under https://api.aquacy.me/frontend/ (same folder as this .htaccess).
      // Override: PUBLIC_PATH=/other/ quasar build   (must start/end with /; then edit public/.htaccess if needed)
      publicPath,
      env: {
        API_BASE_URL: ctx.dev
          ? 'http://localhost:8000/api'  // Development
          : 'https://app.aquacy.me/api'  // Production - will be overridden by dynamic detection in api.js
      }
    },
    devServer: {
      port: 9000,
      open: false
    },
  };
});