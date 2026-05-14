import { useCallback, useEffect, useRef, useState } from 'react';
import MermaidDiagram from './MermaidDiagram';

interface Props {
  chart: string;
  id: string;
  /** Min height of the viewport, in px. Defaults to 520. */
  minHeight?: number;
}

const MIN_SCALE = 0.4;
const MAX_SCALE = 3;
const SCALE_STEP = 1.2;

/**
 * Wraps a Mermaid diagram in a pan + zoom viewport with a small toolbar.
 *
 * - Drag to pan
 * - Mouse wheel (or Ctrl+wheel) to zoom around the cursor
 * - +/-/Reset/Fullscreen buttons
 * - Native Fullscreen API for "true" full-screen view
 */
export default function ZoomableDiagram({ chart, id, minHeight = 520 }: Props) {
  const frameRef = useRef<HTMLDivElement>(null);
  const viewportRef = useRef<HTMLDivElement>(null);

  const [scale, setScale] = useState(1);
  const [tx, setTx] = useState(0);
  const [ty, setTy] = useState(0);
  const [dragging, setDragging] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);

  // Drag state held in a ref so we don't re-render on every mousemove.
  const dragRef = useRef<{ startX: number; startY: number; baseTx: number; baseTy: number } | null>(null);

  const reset = useCallback(() => {
    setScale(1);
    setTx(0);
    setTy(0);
  }, []);

  const zoomBy = useCallback((factor: number, originX?: number, originY?: number) => {
    setScale((prev) => {
      const next = Math.max(MIN_SCALE, Math.min(MAX_SCALE, prev * factor));
      if (next === prev) return prev;
      // If a focal point was given, keep that point stationary on screen.
      if (originX !== undefined && originY !== undefined && viewportRef.current) {
        const rect = viewportRef.current.getBoundingClientRect();
        const cx = originX - rect.left;
        const cy = originY - rect.top;
        setTx((curTx) => cx - ((cx - curTx) * next) / prev);
        setTy((curTy) => cy - ((cy - curTy) * next) / prev);
      }
      return next;
    });
  }, []);

  // ---- Mouse drag to pan ----
  const onMouseDown = (e: React.MouseEvent) => {
    if (e.button !== 0) return;
    dragRef.current = { startX: e.clientX, startY: e.clientY, baseTx: tx, baseTy: ty };
    setDragging(true);
  };

  useEffect(() => {
    if (!dragging) return;
    const onMove = (e: MouseEvent) => {
      if (!dragRef.current) return;
      setTx(dragRef.current.baseTx + (e.clientX - dragRef.current.startX));
      setTy(dragRef.current.baseTy + (e.clientY - dragRef.current.startY));
    };
    const onUp = () => {
      dragRef.current = null;
      setDragging(false);
    };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    return () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };
  }, [dragging]);

  // ---- Wheel to zoom ----
  // Attached via a non-passive native listener so we can preventDefault reliably.
  useEffect(() => {
    const el = viewportRef.current;
    if (!el) return;
    const onWheel = (e: WheelEvent) => {
      // Only intercept when Ctrl/Meta is held OR pointer is inside the viewport
      // and we're inside fullscreen (where there's no page to scroll).
      const wantsZoom = e.ctrlKey || e.metaKey || isFullscreen;
      if (!wantsZoom) return;
      e.preventDefault();
      const factor = e.deltaY < 0 ? SCALE_STEP : 1 / SCALE_STEP;
      zoomBy(factor, e.clientX, e.clientY);
    };
    el.addEventListener('wheel', onWheel, { passive: false });
    return () => el.removeEventListener('wheel', onWheel);
  }, [zoomBy, isFullscreen]);

  // ---- Fullscreen ----
  const toggleFullscreen = useCallback(async () => {
    const el = frameRef.current;
    if (!el) return;
    try {
      if (!document.fullscreenElement) {
        await el.requestFullscreen();
      } else {
        await document.exitFullscreen();
      }
    } catch {
      /* ignore — some browsers reject silently */
    }
  }, []);

  useEffect(() => {
    const onFsChange = () => {
      const fs = document.fullscreenElement === frameRef.current;
      setIsFullscreen(fs);
      // Reset transform when entering fullscreen so the user starts from a known view.
      if (fs) reset();
    };
    document.addEventListener('fullscreenchange', onFsChange);
    return () => document.removeEventListener('fullscreenchange', onFsChange);
  }, [reset]);

  // ---- Keyboard shortcuts when frame is focused ----
  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === '+' || e.key === '=') {
      e.preventDefault();
      zoomBy(SCALE_STEP);
    } else if (e.key === '-' || e.key === '_') {
      e.preventDefault();
      zoomBy(1 / SCALE_STEP);
    } else if (e.key === '0') {
      e.preventDefault();
      reset();
    } else if (e.key === 'f' || e.key === 'F') {
      e.preventDefault();
      void toggleFullscreen();
    }
  };

  return (
    <div
      ref={frameRef}
      className={`zoom-frame${isFullscreen ? ' zoom-frame-fs' : ''}`}
      tabIndex={0}
      onKeyDown={onKeyDown}
    >
      <div className="zoom-toolbar" role="toolbar" aria-label="Diagram zoom controls">
        <span className="zoom-scale" aria-live="polite">{Math.round(scale * 100)}%</span>
        <button type="button" title="Zoom out (-)"     onClick={() => zoomBy(1 / SCALE_STEP)} className="zoom-btn">−</button>
        <button type="button" title="Reset view (0)"   onClick={reset} className="zoom-btn zoom-btn-text">Reset</button>
        <button type="button" title="Zoom in (+)"      onClick={() => zoomBy(SCALE_STEP)} className="zoom-btn">+</button>
        <button type="button" title="Fullscreen (F)"   onClick={() => void toggleFullscreen()} className="zoom-btn">
          {isFullscreen ? '⤢' : '⛶'}
        </button>
      </div>
      <div
        ref={viewportRef}
        className={`zoom-viewport${dragging ? ' is-dragging' : ''}`}
        style={{ minHeight: isFullscreen ? '100vh' : `${minHeight}px` }}
        onMouseDown={onMouseDown}
      >
        <div
          className="zoom-content"
          style={{
            transform: `translate(${tx}px, ${ty}px) scale(${scale})`,
            transformOrigin: '0 0',
          }}
        >
          <MermaidDiagram chart={chart} id={id} />
        </div>
      </div>
      <div className="zoom-hint">
        Drag to pan · Ctrl/⌘ + wheel to zoom · <kbd>+</kbd>/<kbd>−</kbd>/<kbd>0</kbd>/<kbd>F</kbd> when focused
      </div>
    </div>
  );
}
