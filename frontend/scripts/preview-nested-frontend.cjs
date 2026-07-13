'use strict';

/**
 * After `quasar build` with publicPath `/frontend/`, static servers that
 * serve dist/spa at URL `/` break asset URLs (`/frontend/assets/...`).
 * This copies dist/spa into `.preview-frontend/frontend/` and runs `serve`
 * on the parent so http://localhost:4000/frontend/ matches production layout.
 */

const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const root = path.join(__dirname, '..');
const dist = path.join(root, 'dist', 'spa');
const previewRoot = path.join(root, '.preview-frontend');
const nested = path.join(previewRoot, 'frontend');

if (!fs.existsSync(dist)) {
  console.error('dist/spa not found. Run: npm run build');
  process.exit(1);
}

fs.rmSync(previewRoot, { recursive: true, force: true });
fs.mkdirSync(nested, { recursive: true });

for (const name of fs.readdirSync(dist)) {
  fs.cpSync(path.join(dist, name), path.join(nested, name), { recursive: true });
}

console.log('Open http://localhost:4000/frontend/ (Ctrl+C to stop)\n');

const npx = process.platform === 'win32' ? 'npx.cmd' : 'npx';
const r = spawnSync(npx, ['--yes', 'serve', previewRoot, '-l', '4000'], {
  stdio: 'inherit',
  cwd: root,
  shell: true,
});
process.exit(r.status === null ? 1 : r.status);
