/* eslint-env node */

const { configure } = require('quasar/wrappers');

module.exports = configure(function (ctx) {
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
      env: {
        API_BASE_URL: ctx.dev
          ? 'http://localhost:8000/api'  // Development
          : '/backend/api'  // Production - relative path
      }
    },
    devServer: {
      port: 9000,
      open: false
    }
  };
});

