import { useMemo, useState } from 'react';
import { ask, getSuggestions } from '../services/agentClient';
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

  const suggestions = useMemo(
    () => getSuggestions({ scenario, hasResult: !!result }),
    [scenario, result],
  );

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
      if (reply.newResult) onResult(reply.newResult);
    } catch (e: any) {
      setMessages([...next, { role: 'agent', content: `Error: ${e.message || e}` }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="chat">
      <div className="messages">
        {messages.map((m, i) => (
          <div key={i} className={`msg ${m.role}`}>
            <pre>{m.content}</pre>
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
          placeholder='e.g. "what if we lose 45-45 trailers?"'
          disabled={busy}
        />
        <button onClick={() => send(input)} disabled={busy || !input.trim()}>Send</button>
      </div>
    </div>
  );
}
