import axios from "axios";
import type { Message } from "@/types/chat";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface ChatCompletionRequest {
  message: string;
  conversationHistory?: Message[];
}

export interface ChatCompletionResponse {
  id: string;
  content: string;
  model: string;
}

export const chatApi = {
  /**
   * Send a chat message and get a non-streaming response
   */
  async sendMessage(request: ChatCompletionRequest): Promise<ChatCompletionResponse> {
    const response = await axios.post<ChatCompletionResponse>(
      `${API_URL}/api/v1/chat/completions`,
      {
        message: request.message,
        stream: false,
      }
    );
    return response.data;
  },

  /**
   * Send a chat message and get a streaming response
   */
  async streamMessage(request: ChatCompletionRequest): Promise<Response> {
    return await fetch(`${API_URL}/api/v1/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message: request.message,
        conversation_history: request.conversationHistory,
        stream: true,
      }),
    });
  },

  /**
   * List available models
   */
  async listModels(): Promise<string[]> {
    const response = await axios.get<string[]>(`${API_URL}/api/v1/models`);
    return response.data;
  },

  /**
   * Health check
   */
  async healthCheck(): Promise<{ status: string }> {
    const response = await axios.get<{ status: string }>(`${API_URL}/health`);
    return response.data;
  },
};
