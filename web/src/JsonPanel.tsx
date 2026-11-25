import {useEffect, useRef} from 'react';

/** The "Wire" panel: every A2UI message, in the order it travelled. */
export interface WireEntry {
  direction: 'agent → browser' | 'browser → agent';
  message: Record<string, unknown>;
}

/** The message type is the key next to "version", e.g. createSurface. */
function kindOf(message: Record<string, unknown>): string {
  return Object.keys(message).find(key => key !== 'version') ?? 'message';
}

/** Tiny JSON colouring for the panel: keys, strings and numbers. */
function highlight(json: string): string {
  const escaped = json.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  return escaped.replace(/("(?:\\.|[^"\\])*")(\s*:)?|\b(-?\d+(?:\.\d+)?|true|false|null)\b/g,
    (match, str, colon, num) => str ? `<span class="${colon ? 'k' : 's'}">${str}</span>${colon ?? ''}` : `<span class="n">${num}</span>`);
}

export function JsonPanel({entries}: {entries: WireEntry[]}) {
  // Keep the newest message in view.
  const panel = useRef<HTMLElement>(null);
  useEffect(() => {
    panel.current?.scrollTo({top: panel.current.scrollHeight, behavior: 'smooth'});
  }, [entries]);

  return (
    <aside className="wire" ref={panel}>
      <h2>A2UI messages</h2>
      <p className="wire-hint">Newest at the bottom. This is exactly what travels between the agent and the app.</p>
      {entries.length === 0 && <p className="wire-empty">Nothing yet. Ask Study Helper something.</p>}
      {entries.map((entry, i) => (
        <div className={`wire-entry ${entry.direction === 'browser → agent' ? 'up' : 'down'}`} key={i}>
          <div className="wire-head">
            <span className={`badge badge-${kindOf(entry.message)}`}>{kindOf(entry.message)}</span>
            <span className="wire-dir">{entry.direction}</span>
          </div>
          <pre dangerouslySetInnerHTML={{__html: highlight(JSON.stringify(entry.message, null, 2))}} />
        </div>
      ))}
    </aside>
  );
}
