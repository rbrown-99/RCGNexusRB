import { useEffect, useRef } from 'react';
import mermaid from 'mermaid';

mermaid.initialize({
  startOnLoad: false,
  theme: 'neutral',
  themeVariables: {
    primaryColor: '#fdf2f1',
    primaryTextColor: '#1f2330',
    primaryBorderColor: '#d52b1e',
    lineColor: '#7a7a7a',
    secondaryColor: '#fbf8f1',
    tertiaryColor: '#ffffff',
    fontFamily: "'Segoe UI', sans-serif",
    fontSize: '14px',
  },
  flowchart: { htmlLabels: true, curve: 'basis', padding: 14 },
  securityLevel: 'loose',
});

interface Props {
  chart: string;
  id: string;
}

export default function MermaidDiagram({ chart, id }: Props) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    if (!ref.current) return;
    mermaid
      .render(id, chart)
      .then(({ svg }) => {
        if (!cancelled && ref.current) ref.current.innerHTML = svg;
      })
      .catch((e) => {
        if (!cancelled && ref.current)
          ref.current.innerHTML = `<pre class="mermaid-err">Diagram error: ${e.message}</pre>`;
      });
    return () => { cancelled = true; };
  }, [chart, id]);

  return <div className="mermaid-host" ref={ref} />;
}
