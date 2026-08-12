import { useState } from "react";
import type { Message } from "../types";
export function ChatWindow({
  messages,
  sending,
  error,
  onSend,
}: {
  messages: Message[];
  sending: boolean;
  error: string | null;
  onSend: (text: string) => void;
}) {
  const [text, setText] = useState("");
  return (
    <main>
      <section className="messages">
        {messages.map((item, i) => (
          <div
            className={`message ${item.role}`}
            key={`${item.created_at}-${i}`}
          >
            <b>{item.role === "user" ? "You" : "Assistant"}</b>
            <p>{item.message || (sending ? "Thinking…" : "")}</p>
          </div>
        ))}
      </section>
      {error && <div className="error">{error}</div>}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          onSend(text);
          setText("");
        }}
      >
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Ask about your data…"
          disabled={sending}
        />
        <button disabled={sending || !text.trim()}>Send</button>
      </form>
    </main>
  );
}
