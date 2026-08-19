import { clsx } from 'clsx';
// Import the prebuilt bundle — Vite 2 / esbuild 0.14 cannot parse `satisfies`
// in tailwind-merge's TypeScript source (package.json "source" field).
import { twMerge } from '../../node_modules/tailwind-merge/dist/bundle-mjs.mjs';

/**
 * Merge class names with Tailwind conflict resolution.
 * @param {...import('clsx').ClassValue} inputs
 */
export function cn(...inputs) {
  return twMerge(clsx(inputs));
}
