import { useState } from 'react';

/**
 * Albertsons brand mark.
 *
 * Loads the official logo from `/albertsons-logo.svg` (preferred) or
 * `/albertsons-logo.png` if the SVG is missing. Drop the licensed asset
 * into `frontend/public/` and it will be picked up automatically.
 *
 * If neither file is present, falls back to a generic placeholder mark
 * + wordmark so the build still renders.
 */
interface Props {
  height?: number;
  variant?: 'full' | 'mark';   // full = mark + wordmark, mark = just the "A"
  onDark?: boolean;             // invert for use on a dark background
}

const SVG_SRC = '/albertsons-logo.svg';
const PNG_SRC = '/albertsons-logo.png';

export default function BrandLogo({ height = 40, variant = 'full', onDark = false }: Props) {
  // Try SVG first, then PNG, then fall back to the placeholder.
  const [src, setSrc] = useState<string | null>(SVG_SRC);
  const [failed, setFailed] = useState(false);

  if (!failed && src) {
    return (
      <img
        src={src}
        alt="Albertsons"
        height={height}
        style={{
          height,
          width: 'auto',
          display: 'block',
          ...(variant === 'mark'
            ? { width: height, objectFit: 'contain' as const, objectPosition: 'left center' as const }
            : {}),
          ...(onDark ? { filter: 'brightness(0) invert(1)' } : {}),
        }}
        onError={() => {
          if (src === SVG_SRC) {
            setSrc(PNG_SRC);
          } else {
            setFailed(true);
          }
        }}
      />
    );
  }

  // ── Fallback placeholder (used only when the licensed asset isn't present) ──
  const blue = onDark ? '#FFFFFF' : '#003DA5';
  const inner = onDark ? '#003DA5' : '#FFFFFF';
  const wordmarkColor = onDark ? '#FFFFFF' : '#003DA5';

  const Mark = (
    <svg
      width={height}
      height={height}
      viewBox="0 0 64 64"
      aria-hidden
      style={{ flexShrink: 0 }}
    >
      <circle cx="32" cy="32" r="30" fill={blue} />
      {/* Stylized A glyph */}
      <path
        d="M32 14 L50 52 H43 L39.4 43 H24.6 L21 52 H14 L32 14 Z M27.2 37.5 H36.8 L32 26 Z"
        fill={inner}
      />
    </svg>
  );

  if (variant === 'mark') return Mark;

  return (
    <span className="brand-logo" style={{ display: 'inline-flex', alignItems: 'center', gap: 12 }}>
      {Mark}
      <span
        className="brand-script"
        style={{
          color: wordmarkColor,
          fontSize: Math.round(height * 0.85),
          lineHeight: 1,
        }}
      >
        Albertsons
      </span>
    </span>
  );
}
