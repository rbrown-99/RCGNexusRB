/**
 * Albertsons brand mark — stylistic placeholder.
 *
 * For production use, replace the inline SVG/wordmark with the licensed
 * Albertsons logo asset (SVG or PNG) provided by Albertsons brand team.
 *
 * Colors here approximate Albertsons corporate blue.
 */
interface Props {
  height?: number;
  variant?: 'full' | 'mark';   // full = mark + wordmark, mark = just the "A"
  onDark?: boolean;             // invert for use on a dark background
}

export default function BrandLogo({ height = 40, variant = 'full', onDark = false }: Props) {
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
