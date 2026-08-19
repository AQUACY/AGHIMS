/**
 * Parse FastAPI error bodies from blob or JSON export responses.
 * Supports structured Ghana Card export errors:
 * { code, message, claims: [{ item_id, claim_id, member_no, client_name }] }
 */

export async function parseExportErrorDetail(errorOrData) {
  let raw = errorOrData;
  if (errorOrData?.response?.data !== undefined) {
    raw = errorOrData.response.data;
  }
  if (raw == null) return null;

  let parsed = raw;
  if (typeof Blob !== 'undefined' && raw instanceof Blob) {
    try {
      const text = await raw.text();
      try {
        parsed = JSON.parse(text);
      } catch {
        return text.slice(0, 400) || null;
      }
    } catch {
      return null;
    }
  } else if (typeof raw === 'string') {
    try {
      parsed = JSON.parse(raw);
    } catch {
      return raw;
    }
  }

  const detail = parsed?.detail !== undefined ? parsed.detail : parsed;
  if (detail == null) return null;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail.map((x) => x.msg || x.message || JSON.stringify(x)).join('; ');
  }
  if (typeof detail === 'object') {
    return detail;
  }
  return String(detail);
}

export function exportErrorMessage(detail) {
  if (detail == null) return 'Export failed';
  if (typeof detail === 'string') return detail;
  if (typeof detail === 'object' && detail.message) return detail.message;
  return 'Export failed';
}

export function isGhanaCardMemberExportError(detail) {
  return (
    detail &&
    typeof detail === 'object' &&
    detail.code === 'ghana_card_member_no' &&
    Array.isArray(detail.claims) &&
    detail.claims.length > 0
  );
}
