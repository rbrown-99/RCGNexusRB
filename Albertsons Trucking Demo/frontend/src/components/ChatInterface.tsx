import { useEffect, useMemo, useRef, useState } from 'react';
import { ask, getSuggestions, summarize } from '../services/agentClient';
import type { ChatMessage, OptimizeResponse } from '../types';

interface Props {
  sessionId?: string;
  result?: OptimizeResponse;
  scenario?: string;
  onResult: (r: OptimizeResponse) => void;
}

export default function ChatInterface({ sessionId, result, scenario, onResult }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    { role: 'agent', content: 'Hi — I\'m the Albertsons routing copilot. Try a chip below or type your own question.' },
  ]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const messagesRef = useRef<HTMLDivElement>(null);
  // Tracks the last result we've already announced (either via a chat reply or
  // via the auto-summary effect below) so we don't double-post.
  const lastAnnouncedResultRef = useRef<OptimizeResponse | undefined>(undefined);

  const suggestions = useMemo(
    () => getSuggestions({ scenario, hasResult: !!result }),
    [scenario, result],
  );

  // Auto-scroll to the most recent message whenever a new one arrives or we
  // start/stop the typing indicator.
  useEffect(() => {
    const el = messagesRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' });
  }, [messages, busy]);

  // Esc collapses the expanded view.
  useEffect(() => {
    if (!expanded) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setExpanded(false);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [expanded]);

  // When a new optimization result arrives from outside the chat (e.g. the
  // "Run optimization" button at the top, file upload, or sample scenario),
  // post the same summary the agent would give if asked. Chat-initiated runs
  // pre-stamp the ref inside `send()` so they don't double-post.
  useEffect(() => {
    if (!result) return;
    if (result === lastAnnouncedResultRef.current) return;
    lastAnnouncedResultRef.current = result;
    const lead = scenario
      ? `**Plan ready** — loaded *${scenario}*.\n\n`
      : '**Plan ready.**\n\n';
    setMessages((prev) => [...prev, { role: 'agent', content: lead + summarize(result) }]);
  }, [result, scenario]);

  async function send(text: string) {
    const trimmed = text.trim();
    if (!trimmed) return;
    const next: ChatMessage[] = [...messages, { role: 'user', content: trimmed }];
    setMessages(next);
    setInput('');
    setBusy(true);
    try {
      const reply = await ask(trimmed, { sessionId, result });
      setMessages([...next, { role: 'agent', content: reply.text }]);
      if (reply.newResult) {
        // The reply already contains the summary, so flag this result as
        // announced before bubbling it up to the parent — prevents the effect
        // above from posting a duplicate when `result` flows back as a prop.
        lastAnnouncedResultRef.current = reply.newResult;
        onResult(reply.newResult);
      }
    } catch (e: any) {
      setMessages([...next, { role: 'agent', content: `Error: ${e.message || e}` }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      {expanded && (
        <div className="chat-backdrop" onClick={() => setExpanded(false)} aria-hidden />
      )}
      <div className={`chat${expanded ? ' chat-expanded' : ''}`}>
        <div className="chat-header">
          <span className="chat-title">
            <span className="chat-avatar" aria-hidden>◆</span>
            Routing copilot
          </span>
          <button
            type="button"
            className="chat-expand-btn"
            onClick={() => setExpanded((v) => !v)}
            title={expanded ? 'Collapse (Esc)' : 'Expand for more room'}
            aria-label={expanded ? 'Collapse chat' : 'Expand chat'}
          >
            {expanded ? '⤡ Collapse' : '⤢ Expand'}
          </button>
        </div>
        <div className="messages" ref={messagesRef}>
          {messages.map((m, i) => (
            <div key={i} className={`msg ${m.role}`}>
              <MessageBody content={m.content} />
            </div>
          ))}
          {busy && (
            <div className="msg agent typing-msg">
              <span className="typing-dot" /><span className="typing-dot" /><span className="typing-dot" />
            </div>
          )}
        </div>
        {suggestions.length > 0 && (
          <div className="chat-suggestions" role="group" aria-label="Suggested prompts">
            {suggestions.map((s) => (
              <button
                key={s.label}
                type="button"
                className="chip-suggest"
                onClick={() => send(s.prompt)}
                disabled={busy}
                title={s.prompt}
              >
                {s.label}
              </button>
            ))}
          </div>
        )}
        <div className="input-row">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && send(input)}
            placeholder='Ask anything — e.g. "what if we lose 45-45 trailers?"'
            disabled={busy}
          />
          <button onClick={() => send(input)} disabled={busy || !input.trim()}>Send</button>
        </div>
      </div>
    </>
  );
}

// ──────────────────────────────────────────────────────────────────────────
// Lightweight markdown-ish renderer for agent replies.
//
// Handles: paragraphs (blank-line separated), bullet lists (`- ` / `* ` / `• `),
// numbered lists (`1.`), inline **bold**, *italic*, and `code`. Plain enough to
// avoid pulling in react-markdown but enough to make agent output readable.
// ──────────────────────────────────────────────────────────────────────────

function MessageBody({ content }: { content: string }) {
  const blocks = content.replace(/\r\n/g, '\n').split(/\n\s*\n/);
  return <>{blocks.map((b, i) => renderBlock(b, i))}</>;
}

function renderBlock(block: string, key: number) {
  const lines = block.split('\n').filter((l) => l.trim().length > 0);
  if (lines.length === 0) return null;

  const isBullet = (l: string) => /^\s*[-*•]\s+/.test(l);
  const isNumbered = (l: string) => /^\s*\d+[.)]\s+/.test(l);

  if (lines.every(isBullet)) {
    return (
      <ul key={key} className="msg-list">
        {lines.map((l, j) => (
          <li key={j}>{renderInline(l.replace(/^\s*[-*•]\s+/, ''))}</li>
        ))}
      </ul>
    );
  }
  if (lines.every(isNumbered)) {
    return (
      <ol key={key} className="msg-list">
        {lines.map((l, j) => (
          <li key={j}>{renderInline(l.replace(/^\s*\d+[.)]\s+/, ''))}</li>
        ))}
      </ol>
    );
  }
  return (
    <p key={key} className="msg-para">
      {lines.map((l, j) => (
        <span key={j}>
          {renderInline(l)}
          {j < lines.length - 1 && <br />}
        </span>
      ))}
    </p>
  );
}

function renderInline(text: string): React.ReactNode {
  const parts: React.ReactNode[] = [];
  // Order matters: try `code`, then **bold**, then *italic*.
  const re = /(`[^`\n]+`)|(\*\*[^*\n]+\*\*)|(\*[^*\n]+\*)/g;
  let lastIndex = 0;
  let key = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(text))) {
    if (m.index > lastIndex) parts.push(text.slice(lastIndex, m.index));
    if (m[1]) parts.push(<code key={key++} className="msg-code">{m[1].slice(1, -1)}</code>);
    else if (m[2]) parts.push(<strong key={key++}>{m[2].slice(2, -2)}</strong>);
    else if (m[3]) parts.push(<em key={key++}>{m[3].slice(1, -1)}</em>);
    lastIndex = m.index + m[0].length;
  }
  if (lastIndex < text.length) parts.push(text.slice(lastIndex));
  return parts;
}
