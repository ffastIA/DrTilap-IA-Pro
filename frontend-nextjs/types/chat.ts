// types/chat.ts
export interface ChatMessage {
  id: string;
  text: string;
  sender: 'user' | 'ai';
  isError?: boolean;
}