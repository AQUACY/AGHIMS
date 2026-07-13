/** Ordered claim IDs for Previous/Next navigation across tabs (lists open edit in new tabs). */

const CLAIMS_NAV_KEY = 'claims_nav_ids';
const GHIMS_NAV_KEY = 'ghims_nav_ids';

function cleanIds(ids) {
  const seen = new Set();
  const out = [];
  for (const raw of ids || []) {
    const n = Number(raw);
    if (!Number.isFinite(n) || n <= 0 || seen.has(n)) continue;
    seen.add(n);
    out.push(n);
  }
  return out;
}

function readIds(key) {
  try {
    const raw = JSON.parse(localStorage.getItem(key) || '[]');
    return Array.isArray(raw) ? cleanIds(raw) : [];
  } catch {
    return [];
  }
}

function writeIds(key, ids) {
  localStorage.setItem(key, JSON.stringify(cleanIds(ids)));
}

function navPosition(ids, currentId) {
  const id = Number(currentId);
  const index = ids.indexOf(id);
  return {
    ids,
    index,
    position: index >= 0 ? index + 1 : 0,
    total: ids.length,
    prevId: index > 0 ? ids[index - 1] : null,
    nextId: index >= 0 && index < ids.length - 1 ? ids[index + 1] : null,
    hasNav: index >= 0 && ids.length > 1,
  };
}

export function setClaimsNavIds(ids) {
  writeIds(CLAIMS_NAV_KEY, ids);
}

export function getClaimsNavPosition(currentId) {
  return navPosition(readIds(CLAIMS_NAV_KEY), currentId);
}

export function setGhimsNavIds(ids) {
  writeIds(GHIMS_NAV_KEY, ids);
}

export function getGhimsNavPosition(currentId) {
  return navPosition(readIds(GHIMS_NAV_KEY), currentId);
}
