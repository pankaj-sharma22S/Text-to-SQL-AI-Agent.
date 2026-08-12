import { Sidebar } from "./components/Sidebar";
import { ChatWindow } from "./components/ChatWindow";
import { useChat } from "./hooks/useChat";
import "./styles.css";
export default function App() {
  const chat = useChat();
  return (
    <div className="app">
      <Sidebar
        conversations={chat.conversations}
        active={chat.activeThreadId}
        onNew={chat.newChat}
        onSelect={chat.select}
        onDelete={chat.remove}
      />
      <ChatWindow
        messages={chat.messages}
        sending={chat.sending}
        error={chat.error}
        onSend={chat.send}
      />
      {chat.loading && <div className="loading">Loading…</div>}
    </div>
  );
}
