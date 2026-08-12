export type Role = "user" | "assistant";
export type Message = { role: Role; message: string; created_at: string };
export type Conversation = {
  thread_id: string;
  title: string;
  preview: string;
  updated_at: string;
};
