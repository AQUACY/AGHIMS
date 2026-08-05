/**
 * Apply / clear facility brand colors as CSS custom properties.
 * Unset colors leave design-token defaults in place.
 *
 * IMPORTANT: Light-theme tokens are defined on `body.body--light` / `html.body--light`,
 * so overrides must be written to both `html` and `body` or body wins and branding
 * appears to do nothing.
 */

const BG_VARS = [
  '--hms-bg-primary',
  '--hms-bg-secondary',
  '--hms-bg-elevated',
  '--hms-panel-bg',
  '--hms-glass-bg',
  '--hms-glass-bg-strong',
  '--hms-surface',
  '--hms-surface-hover',
  '--hms-surface-active',
];

const TEXT_VARS = [
  '--hms-text-primary',
  '--hms-text-secondary',
  '--hms-text-muted',
  '--hms-text-inverse',
  '--hms-border',
  '--hms-border-strong',
];

const ACCENT_VARS = [
  '--hms-accent',
  '--hms-accent-hover',
  '--hms-accent-muted',
  '--hms-shadow-glow-accent',
  '--q-primary',
];

const HEX_RE = /^#([0-9a-fA-F]{6})$/;

export function normalizeBrandHex(value) {
  if (value == null) return null;
  const raw = String(value).trim();
  if (!raw) return null;
  // Quasar color picker sometimes emits #rrggbbaa — keep first 6 digits
  const short = raw.length >= 7 && raw.startsWith('#') ? raw.slice(0, 7) : raw;
  if (!HEX_RE.test(short)) return null;
  return short.toLowerCase();
}

function targets() {
  return [document.documentElement, document.body].filter(Boolean);
}

function clearVars(el, names) {
  names.forEach((name) => el.style.removeProperty(name));
}

function setVar(el, name, value) {
  el.style.setProperty(name, value);
}

function applyBackground(els, hex, isDark) {
  if (!hex) {
    els.forEach((el) => clearVars(el, BG_VARS));
    return;
  }

  els.forEach((el) => {
    if (isDark) {
      setVar(el, '--hms-bg-primary', hex);
      setVar(el, '--hms-bg-secondary', `color-mix(in srgb, ${hex} 86%, white)`);
      setVar(el, '--hms-bg-elevated', `color-mix(in srgb, ${hex} 76%, white)`);
      setVar(el, '--hms-panel-bg', `color-mix(in srgb, ${hex} 80%, white)`);
      setVar(el, '--hms-glass-bg', `color-mix(in srgb, ${hex} 86%, transparent)`);
      setVar(el, '--hms-glass-bg-strong', `color-mix(in srgb, ${hex} 90%, white)`);
      setVar(el, '--hms-surface', `color-mix(in srgb, white 7%, transparent)`);
      setVar(el, '--hms-surface-hover', `color-mix(in srgb, white 11%, transparent)`);
      setVar(el, '--hms-surface-active', `color-mix(in srgb, white 15%, transparent)`);
    } else {
      setVar(el, '--hms-bg-primary', hex);
      setVar(el, '--hms-bg-secondary', `color-mix(in srgb, ${hex} 88%, black)`);
      setVar(el, '--hms-bg-elevated', `color-mix(in srgb, ${hex} 28%, white)`);
      setVar(el, '--hms-panel-bg', `color-mix(in srgb, ${hex} 78%, white)`);
      setVar(el, '--hms-glass-bg', `color-mix(in srgb, ${hex} 82%, white)`);
      setVar(el, '--hms-glass-bg-strong', `color-mix(in srgb, ${hex} 88%, white)`);
      setVar(el, '--hms-surface', `color-mix(in srgb, ${hex} 55%, white)`);
      setVar(el, '--hms-surface-hover', `color-mix(in srgb, ${hex} 48%, white)`);
      setVar(el, '--hms-surface-active', `color-mix(in srgb, ${hex} 40%, white)`);
    }
  });
}

function applyText(els, hex, isDark) {
  if (!hex) {
    els.forEach((el) => {
      clearVars(el, TEXT_VARS);
      el.style.removeProperty('color');
    });
    return;
  }

  // Fade primary toward black (dark UI) or white (light UI) for secondary/muted
  const fadeToward = isDark ? 'black' : 'white';
  const inverse = isDark ? '#09090b' : '#ffffff';

  els.forEach((el) => {
    setVar(el, '--hms-text-primary', hex);
    setVar(el, '--hms-text-secondary', `color-mix(in srgb, ${hex} 62%, ${fadeToward})`);
    setVar(el, '--hms-text-muted', `color-mix(in srgb, ${hex} 40%, ${fadeToward})`);
    setVar(el, '--hms-text-inverse', inverse);
    setVar(el, '--hms-border', `color-mix(in srgb, ${hex} 14%, transparent)`);
    setVar(el, '--hms-border-strong', `color-mix(in srgb, ${hex} 24%, transparent)`);
    setVar(el, 'color', hex);
  });
}

function applyAccent(els, hex, isDark) {
  if (!hex) {
    els.forEach((el) => clearVars(el, ACCENT_VARS));
    return;
  }

  const mutedAmount = isDark ? '18%' : '12%';
  els.forEach((el) => {
    setVar(el, '--hms-accent', hex);
    setVar(el, '--hms-accent-hover', `color-mix(in srgb, ${hex} 78%, black)`);
    setVar(el, '--hms-accent-muted', `color-mix(in srgb, ${hex} ${mutedAmount}, transparent)`);
    setVar(
      el,
      '--hms-shadow-glow-accent',
      `0 4px 20px color-mix(in srgb, ${hex} ${isDark ? '28%' : '20%'}, transparent)`,
    );
    setVar(el, '--q-primary', hex);
  });
}

/**
 * @param {{
 *   bgColorLight?: string|null,
 *   bgColorDark?: string|null,
 *   accentColor?: string|null,
 *   textColorLight?: string|null,
 *   textColorDark?: string|null,
 *   isDark?: boolean
 * }} opts
 */
export function applyFacilityBranding(opts = {}) {
  if (typeof document === 'undefined') return;

  const els = targets();
  const root = document.documentElement;
  const isDark =
    typeof opts.isDark === 'boolean'
      ? opts.isDark
      : root.classList.contains('body--dark') ||
        document.body?.classList?.contains('body--dark');

  const light = normalizeBrandHex(opts.bgColorLight);
  const dark = normalizeBrandHex(opts.bgColorDark);
  const accent = normalizeBrandHex(opts.accentColor);
  const textLight = normalizeBrandHex(opts.textColorLight);
  const textDark = normalizeBrandHex(opts.textColorDark);

  applyBackground(els, isDark ? dark : light, isDark);
  applyText(els, isDark ? textDark : textLight, isDark);
  applyAccent(els, accent, isDark);
}

export function clearFacilityBranding() {
  if (typeof document === 'undefined') return;
  targets().forEach((el) => {
    clearVars(el, BG_VARS);
    clearVars(el, TEXT_VARS);
    clearVars(el, ACCENT_VARS);
    el.style.removeProperty('color');
  });
}
