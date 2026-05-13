import { useState } from 'react';
import { ask } from '../services/agentClient';
import type { ChatMessage, OptimizeResponse } from '../types';

interface Props {
  sessionId?: string;
  result?: OptimizeResponse;
  onResult: (r: OptimizeResponse) => void;
}

export default function ChatInterface({ sessionId, result, onResult }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    { role: 'agent', content: 'Hi — I\'m the Albertsons routing copilot. Try "run optimization" or upload your files first.' },
  ]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);

  async function send() {
    if (!input.trim()) return;
    const next: ChatMessage[] = [...messages, { role: 'user', content: input }];
    setMessages(next);
    setInput('');
    setBusy(true);
    try {
      const reply = await ask(input, { sessionId, result });
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
      </div>
      <div className="input-row">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && send()}
          placeholder='e.g. "what if we lose 45-45 trailers?"'
          disabled={busy}
        />
        <button onClick={send} disabled={busy || !input.trim()}>Send</button>
      </div>
    </div>
  );
}
