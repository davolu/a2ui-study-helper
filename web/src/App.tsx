import {useEffect, useMemo, useRef, useState} from 'react';
import {A2uiSurface, MarkdownContext} from '@a2ui/react';
import {renderMarkdown} from '@a2ui/markdown-it';
import type {ActionPayload} from '@a2ui/web_core/v1_0';

import {StudySurfaces, actionMessage, type A2uiMessage} from './a2ui';
import {JsonPanel, type WireEntry} from './JsonPanel';

/** One line in the chat: what the student said, or what the agent answered. */
interface Turn {
  who: 'student' | 'agent';
  text: string;
  surfaceId?: string; // the UI the agent drew for this answer, if any
}

const EXAMPLES = [
  'Make me a 3-question fractions quiz',
  'List 5 topics to revise tonight',
  'Summarise photosynthesis',
];

export function App() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [wire, setWire] = useState<WireEntry[]>([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [showJson, setShowJson] = useState(true);
  const [textOnly, setTextOnly] = useState(false);
  const [mode, setMode] = useState('');
  // The app owns the look: 'study' applies theme.css, 'plain' shows A2UI's default theme.
  const [themed, setThemed] = useState(new URLSearchParams(location.search).get('theme') !== 'plain');
  const sessionId = useRef<string | null>(null);
  const bottom = useRef<HTMLDivElement>(null);

  // One processor for the whole conversation. A button press inside any
  // surface comes back here as an A2UI action, and we send it to the agent.
  const sendRef = useRef<(request: {message?: string; action?: ActionPayload}) => void>(() => {});
  const surfaces = useMemo(() => new StudySurfaces(action => sendRef.current({action})), []);

  useEffect(() => {
    fetch('/api/status').then(r => r.json()).then(s => setMode(s.mode));
  }, []);
  useEffect(() => {
    bottom.current?.scrollIntoView({behavior: 'smooth'});
  }, [turns]);

  async function send(request: {message?: string; action?: ActionPayload}) {
    const outgoing = request.action ? actionMessage(request.action) : undefined;
    if (outgoing) setWire(w => [...w, {direction: 'browser → agent', message: outgoing}]);
    if (request.message) setTurns(t => [...t, {who: 'student', text: request.message!}]);
    setBusy(true);
    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          sessionId: sessionId.current,
          message: request.message,
          action: outgoing?.action,
          textOnly,
          capabilities: surfaces.capabilities(), // "here is what I can draw"
        }),
      });
      const reply = await response.json();
      sessionId.current = reply.sessionId;
      if (reply.error) throw new Error(reply.error);

      const messages: A2uiMessage[] = reply.messages ?? [];
      surfaces.apply(messages); // the processor builds (or updates) the UI
      setWire(w => [...w, ...messages.map(message => ({direction: 'agent → browser' as const, message}))]);

      // A brand-new surface gets its own place in the chat.
      const created = messages.find(m => 'createSurface' in m) as
        | {createSurface: {surfaceId: string}}
        | undefined;
      setTurns(t => [...t, {who: 'agent', text: reply.text, surfaceId: created?.createSurface.surfaceId}]);
    } catch (error) {
      setTurns(t => [...t, {who: 'agent', text: `Something went wrong: ${String(error)}`}]);
    } finally {
      setBusy(false);
    }
  }

  sendRef.current = send; // always the latest send (it reads the latest toggles)

  function submit(text: string) {
    if (!text.trim() || busy) return;
    setInput('');
    send({message: text.trim()});
  }

  return (
    <MarkdownContext.Provider value={renderMarkdown}>
      <div className={`app a2ui-light ${showJson ? 'with-wire' : ''} ${themed ? 'theme-study' : 'theme-plain'}`}>
        <header>
          <div className="brand">
            <div className="logo">📚</div>
            <div>
              <h1>Study Helper</h1>
              <p className="sub">The agent decides the UI · A2UI v1.0 · <span className="mode">{mode || '…'}</span></p>
            </div>
          </div>
          <div className="toggles">
            <label><input type="checkbox" checked={themed} onChange={e => setThemed(e.target.checked)} /> App theme</label>
            <label><input type="checkbox" checked={textOnly} onChange={e => setTextOnly(e.target.checked)} /> Text-only replies</label>
            <label><input type="checkbox" checked={showJson} onChange={e => setShowJson(e.target.checked)} /> Show A2UI JSON</label>
          </div>
        </header>

        <main className="chat">
          {turns.length === 0 && (
            <div className="empty">
              <div className="big">✨</div>
              <p>Ask for something. The agent picks the best UI for the answer.</p>
            </div>
          )}
          {turns.map((turn, i) => (
            <div key={i} className={`turn ${turn.who}`}>
              {turn.text && <div className="bubble">{turn.text}</div>}
              {turn.surfaceId && surfaces.surface(turn.surfaceId) && (
                <div className="surface">
                  <A2uiSurface surface={surfaces.surface(turn.surfaceId)!} />
                </div>
              )}
            </div>
          ))}
          {busy && <div className="turn agent"><div className="bubble thinking">Thinking…</div></div>}
          <div ref={bottom} />
        </main>

        <footer>
          <div className="examples">
            {EXAMPLES.map(example => (
              <button key={example} onClick={() => submit(example)} disabled={busy}>{example}</button>
            ))}
          </div>
          <form onSubmit={e => { e.preventDefault(); submit(input); }}>
            <input value={input} onChange={e => setInput(e.target.value)} placeholder="Ask Study Helper…" />
            <button type="submit" disabled={busy}>Send</button>
          </form>
        </footer>

        {showJson && <JsonPanel entries={wire} />}
      </div>
    </MarkdownContext.Provider>
  );
}
