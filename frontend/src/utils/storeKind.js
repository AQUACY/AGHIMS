/**
 * Label for store dropdowns: distinguishes pharmacy supply vs general (main) store.
 * Requisitions and stock are always scoped by store_id; this is metadata for UX and reports.
 */
export function storeSelectLabel(store) {
  if (!store || !store.name) return '';
  const kind = store.store_kind || 'general';
  const tag = kind === 'pharmacy' ? 'Pharmacy' : 'General';
  return `${store.name} — ${tag}`;
}
