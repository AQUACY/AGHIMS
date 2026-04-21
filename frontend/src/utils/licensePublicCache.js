let _licensePublicCache = { t: 0, v: null };

/**
 * @param {() => Promise<{ data: object }>} fetcher
 * @param {number} ttlMs
 */
export async function getCachedLicensePublic(fetcher, ttlMs = 8000) {
  const now = Date.now();
  if (_licensePublicCache.v && now - _licensePublicCache.t < ttlMs) {
    return _licensePublicCache.v;
  }
  const { data } = await fetcher();
  _licensePublicCache = { t: now, v: data };
  return data;
}

export function clearLicensePublicCache() {
  _licensePublicCache = { t: 0, v: null };
}
