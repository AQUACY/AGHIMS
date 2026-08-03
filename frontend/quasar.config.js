/* eslint-env node */

const path = require('path');
const fs = require('fs');
const { configure } = require('quasar/wrappers');

/**
 * Load KEY=VALUE pairs from a .env file into process.env.
 * Does not override variables already set in the shell.
 */
function loadEnvFile(filePath) {
  if (!fs.existsSync(filePath)) return;
  const text = fs.readFileSync(filePath, 'utf8');
  for (const line of text.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const eq = trimmed.indexOf('=');
    if (eq <= 0) continue;
    const key = trimmed.slice(0, eq).trim();
    if (!key || process.env[key] !== undefined) continue;
    let val = trimmed.slice(eq + 1).trim();
    if (
      (val.startsWith('"') && val.endsWith('"')) ||
      (val.startsWith("'") && val.endsWith("'"))
    ) {
      val = val.slice(1, -1);
    }
    process.env[key] = val;
  }
}

// Prefer .env.local (machine-specific) over .env
loadEnvFile(path.join(__dirname, '.env'));
loadEnvFile(path.join(__dirname, '.env.local'));

module.exports = configure(function (ctx) {
  // Production is hosted at domain root (e.g. https://claims.aquacy.me/).
  // Do NOT default to /frontend/ — that causes /frontend/assets 404s on subdomain deploys.
  // Do not set PUBLIC_PATH=/ in Git Bash on Windows (path mangling); leave unset for "/".
  const publicPath =
    process.env.PUBLIC_PATH != null && String(process.env.PUBLIC_PATH).trim() !== ''
      ? String(process.env.PUBLIC_PATH).trim()
      : '/';

  // Set in frontend/.env (or .env.local), e.g. API_BASE_URL=http://10.10.16.40:8000/api
  // Must include the /api suffix used by the FastAPI app.
  const apiBaseUrl =
    process.env.API_BASE_URL != null && String(process.env.API_BASE_URL).trim() !== ''
      ? String(process.env.API_BASE_URL).trim().replace(/\/$/, '')
      : ctx.dev
        ? 'http://localhost:8000/api'
        : 'https://app.aquacy.me/api';

  return {
    css: [
      'app.css',
    ],
    framework: {
      config: {
        dark: true,
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
