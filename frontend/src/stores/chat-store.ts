import { create } from "zustand";
import { devtools } from "zustand/middleware";
import { immer } from "zustand/middleware/immer";
import type { Message, ChatState } from "@/types/chat";

export const useChatStore = create<ChatState>()(
  devtools(
    immer((set) => ({
      messages: [],
      isStreaming: false,
      currentStreamingMessageId: null,

      addMessage: (message) => {
        const newMessageId = crypto.randomUUID();
        set((state) => {
          const newMessage: Message = {
            ...message,
            id: newMessageId,
            timestamp: new Date(),
          };
          state.messages.push(newMessage);

          if (message.role === "assistant") {
            state.isStreaming = true;
            state.currentStreamingMessageId = newMessageId;
          }
        });
        return newMessageId;
      },

      updateStreamingMessage: (id, content) =>
        set((state) => {
          const message = state.messages.find((m) => m.id === id);
          if (message) {
            message.content = content;
            message.isStreaming = true;
          }
        }),

      completeStreamingMessage: (id) =>
        set((state) => {
          const message = state.messages.find((m) => m.id === id);
          if (message) {
            message.isStreaming = false;
          }
          state.isStreaming = false;
          state.currentStreamingMessageId = null;
        }),

      clearMessages: () =>
        set((state) => {
          state.messages = [];
          state.isStreaming = false;
          state.currentStreamingMessageId = null;
        }),
    })),
    { name: "ChatStore" }
  )
);
