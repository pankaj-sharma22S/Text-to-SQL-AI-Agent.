import type { Conversation } from "../types";
export function Sidebar({
  conversations,
  active,
  onNew,
  onSelect,
  onDelete,
}: {
  conversations: Conversation[];
  active: string | null;
  onNew: () => void;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
}) {
  return (
    <aside>
      <button onClick={onNew}>＋ New Chat</button>
      <h2>Conversations</h2>
      {conversations.map((item) => (
        <div
          className={`conversation ${item.thread_id === active ? "active" : ""}`}
          key={item.thread_id}
          onClick={() => onSelect(item.thread_id)}
        >
          <span>{item.title}</span>
          <button
            aria-label="Delete conversation"
            onClick={(e) => {
              e.stopPropagation();
              onDelete(item.thread_id);
            }}
          >
            ×
          </button>
        </div>
      ))}
    </aside>
  );
}
