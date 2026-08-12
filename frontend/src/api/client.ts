import type { Conversation, Message } from "../types";
const base = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${base}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!response.ok)
    throw new Error(
      (await response.json().catch(() => null))?.detail ?? "Request failed",
    );
  return response.json();
}
export const createConversation = () =>
  request<{ thread_id: string }>("/conversations", { method: "POST" });
export const listConversations = () =>
  request<{ conversations: Conversation[] }>("/conversations");
export const getHistory = (id: string) =>
  request<Message[]>(`/conversations/${encodeURIComponent(id)}`);
export const deleteConversation = (id: string) =>
  request(`/conversations/${encodeURIComponent(id)}`, { method: "DELETE" });
export const getProfile = () =>
  request<{ name: string; profession: string; preferences: string[] }>(
    "/profile",
  );
export const putProfile = (profile: {
  name: string;
  profession: string;
  preferences: string[];
}) => request("/profile", { method: "PUT", body: JSON.stringify(profile) });

export async function streamChat(
  threadId: string,
  message: string,
  onEvent: (event: string, data: string) => void,
  signal: AbortSignal,
) {
  const response = await fetch(`${base}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ thread_id: threadId, message }),
    signal,
  });
  if (!response.ok || !response.body)
    throw new Error("Streaming request failed");
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const part = await reader.read();
    if (part.done) break;
    buffer += decoder.decode(part.value, { stream: true });
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() ?? "";
    for (const chunk of chunks) {
      const event = chunk.match(/^event: (.+)$/m)?.[1];
      const data = chunk.match(/^data: (.+)$/m)?.[1];
      if (event && data) onEvent(event, JSON.parse(data));
    }
  }
}
