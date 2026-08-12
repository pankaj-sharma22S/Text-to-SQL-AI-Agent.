import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  createConversation,
  deleteConversation,
  getHistory,
  listConversations,
  streamChat,
} from "../api/client";
import type { Conversation, Message } from "../types";

export function useChat() {
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);
  const activeThreadRef = useRef<string | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [messagesByThread, setMessagesByThread] = useState<
    Record<string, Message[]>
  >({});
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messages = useMemo(
    () => (activeThreadId ? (messagesByThread[activeThreadId] ?? []) : []),
    [activeThreadId, messagesByThread],
  );

  const select = useCallback(
    async (id: string) => {
      activeThreadRef.current = id;
      setSending(false);
      setActiveThreadId(id);
      sessionStorage.setItem("activeThreadId", id);
      if (!messagesByThread[id]) {
        const history = await getHistory(id);
        setMessagesByThread((old) => ({ ...old, [id]: history }));
      }
    },
    [messagesByThread],
  );
  useEffect(() => {
    (async () => {
      try {
        const stored = sessionStorage.getItem("activeThreadId");
        const { conversations: items } = await listConversations();
        setConversations(items);
        const selected =
          stored && items.some((item) => item.thread_id === stored)
            ? stored
            : items[0]?.thread_id;
        if (selected) await select(selected);
      } catch (e) {
        setError(String(e));
      } finally {
        setLoading(false);
      }
    })();
  }, []);
  const newChat = async () => {
    const { thread_id } = await createConversation();
    const item = {
      thread_id,
      title: "New conversation",
      preview: "",
      updated_at: "",
    };
    setConversations((old) => [item, ...old]);
    setMessagesByThread((old) => ({ ...old, [thread_id]: [] }));
    activeThreadRef.current = thread_id;
    setActiveThreadId(thread_id);
    sessionStorage.setItem("activeThreadId", thread_id);
  };
  const send = async (text: string) => {
    if (!activeThreadId || !text.trim()) return;
    const id = activeThreadId;
    const controller = new AbortController();
    setSending(true);
    setError(null);
    setMessagesByThread((old) => ({
      ...old,
      [id]: [
        ...(old[id] ?? []),
        { role: "user", message: text, created_at: new Date().toISOString() },
        {
          role: "assistant",
          message: "",
          created_at: new Date().toISOString(),
        },
      ],
    }));
    try {
      await streamChat(
        id,
        text,
        (event, data) => {
          if (id !== activeThreadRef.current) return;
          if (event === "answer")
            setMessagesByThread((old) => ({
              ...old,
              [id]: [
                ...(old[id] ?? []).slice(0, -1),
                {
                  role: "assistant",
                  message: data,
                  created_at: new Date().toISOString(),
                },
              ],
            }));
        },
        controller.signal,
      );
    } catch (e) {
      if (id === activeThreadRef.current) setError(String(e));
    } finally {
      if (id === activeThreadRef.current) setSending(false);
    }
  };
  const remove = async (id: string) => {
    await deleteConversation(id);
    setConversations((old) => old.filter((item) => item.thread_id !== id));
    setMessagesByThread((old) => {
      const next = { ...old };
      delete next[id];
      return next;
    });
    if (activeThreadRef.current === id) {
      activeThreadRef.current = null;
      setActiveThreadId(null);
      sessionStorage.removeItem("activeThreadId");
    }
  };
  useEffect(() => {
    if (activeThreadId)
      sessionStorage.setItem("activeThreadId", activeThreadId);
  }, [activeThreadId]);
  return {
    activeThreadId,
    conversations,
    messages,
    loading,
    sending,
    error,
    newChat,
    select,
    send,
    remove,
  };
}
