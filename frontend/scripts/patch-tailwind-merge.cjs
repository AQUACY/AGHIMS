/* eslint-env node */
/**
 * Quasar (Vite 2 / esbuild 0.14) follows package.json "source" into
 * TypeScript that uses `satisfies`, which those tools cannot parse.
 * Strip that field after install so resolution stays on dist/.
 */
const fs = require('fs');
const path = require('path');

const pkgPath = path.join(__dirname, '..', 'node_modules', 'tailwind-merge', 'package.json');
if (!fs.existsSync(pkgPath)) process.exit(0);

const pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf8'));
if (!Object.prototype.hasOwnProperty.call(pkg, 'source')) process.exit(0);

delete pkg.source;
fs.writeFileSync(pkgPath, `${JSON.stringify(pkg, null, 4)}\n`);
console.log('[patch-tailwind-merge] removed package.json "source" field');
