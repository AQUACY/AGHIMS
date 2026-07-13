import { boot } from 'quasar/wrappers';
// Import Material Icons CSS
import '@quasar/extras/material-icons/material-icons.css';

function assetHref(relativePath) {
  const base = import.meta.env.BASE_URL || '/';
  const path = relativePath.replace(/^\//, '');
  if (base === '/' || base === './') {
    return `/${path}`;
  }
  const normalized = base.endsWith('/') ? base : `${base}/`;
  return `${normalized}${path}`;
}

export default boot(() => {
  const head = document.head;
  const marker = 'data-hms-asset-link';

  if (!head.querySelector(`link[rel="icon"][${marker}]`)) {
    const link = document.createElement('link');
    link.rel = 'icon';
    link.type = 'image/png';
    link.href = assetHref('icons/favicon-128x128.png');
    link.setAttribute(marker, '1');
    head.appendChild(link);
  }

  if (!head.querySelector(`link[rel="manifest"][${marker}]`)) {
    const manifest = document.createElement('link');
    manifest.rel = 'manifest';
    manifest.href = assetHref('manifest.json');
    manifest.setAttribute(marker, '1');
    head.appendChild(manifest);
  }
});

