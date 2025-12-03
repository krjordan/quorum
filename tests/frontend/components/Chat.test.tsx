/**
 * Unit Tests for Chat Component
 *
 * Tests cover:
 * - Message rendering
 * - User input handling
 * - SSE streaming integration
 * - Error states
 * - Loading states
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Chat } from '@components/Chat';
import { ChatProvider } from '@components/ChatProvider';

// Mock the SSE hook
vi.mock('@hooks/useSSE', () => ({
  useSSE: vi.fn(() => ({
    messages: [],
    isConnected: false,
    error: null,
    sendMessage: vi.fn(),
    clearMessages: vi.fn(),
    reconnect: vi.fn()
  }))
}));

// Helper to render with providers
const renderWithProviders = (component: React.ReactElement) => {
  return render(
    <ChatProvider>
      {component}
    </ChatProvider>
  );
};

describe('Chat Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders chat interface', () => {
    renderWithProviders(<Chat />);

    expect(screen.getByRole('textbox')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /send/i })).toBeInTheDocument();
  });

  it('displays initial empty state', () => {
    renderWithProviders(<Chat />);

    expect(screen.getByText(/start a conversation/i)).toBeInTheDocument();
  });

  it('handles user message input', async () => {
    const user = userEvent.setup();
    renderWithProviders(<Chat />);

    const input = screen.getByRole('textbox');
    await user.type(input, 'Hello, AI!');

    expect(input).toHaveValue('Hello, AI!');
  });

  it('sends message on button click', async () => {
    const mockSendMessage = vi.fn();
    const { useSSE } = await import('@hooks/useSSE');
    vi.mocked(useSSE).mockReturnValue({
      messages: [],
      isConnected: true,
      error: null,
      sendMessage: mockSendMessage,
      clearMessages: vi.fn(),
      reconnect: vi.fn()
    });

    const user = userEvent.setup();
    renderWithProviders(<Chat />);

    const input = screen.getByRole('textbox');
    const sendButton = screen.getByRole('button', { name: /send/i });

    await user.type(input, 'Test message');
    await user.click(sendButton);

    expect(mockSendMessage).toHaveBeenCalledWith('Test message');
    expect(input).toHaveValue('');
  });

  it('sends message on Enter key', async () => {
    const mockSendMessage = vi.fn();
    const { useSSE } = await import('@hooks/useSSE');
    vi.mocked(useSSE).mockReturnValue({
      messages: [],
      isConnected: true,
      error: null,
      sendMessage: mockSendMessage,
      clearMessages: vi.fn(),
      reconnect: vi.fn()
    });

    const user = userEvent.setup();
    renderWithProviders(<Chat />);

    const input = screen.getByRole('textbox');
    await user.type(input, 'Test message{Enter}');

    expect(mockSendMessage).toHaveBeenCalledWith('Test message');
  });

  it('does not send empty messages', async () => {
    const mockSendMessage = vi.fn();
    const { useSSE } = await import('@hooks/useSSE');
    vi.mocked(useSSE).mockReturnValue({
      messages: [],
      isConnected: true,
      error: null,
      sendMessage: mockSendMessage,
      clearMessages: vi.fn(),
      reconnect: vi.fn()
    });

    const user = userEvent.setup();
    renderWithProviders(<Chat />);

    const sendButton = screen.getByRole('button', { name: /send/i });
    await user.click(sendButton);

    expect(mockSendMessage).not.toHaveBeenCalled();
  });

  it('displays messages in conversation', () => {
    const { useSSE } = await import('@hooks/useSSE');
    vi.mocked(useSSE).mockReturnValue({
      messages: [
        { role: 'user', content: 'Hello' },
        { role: 'assistant', content: 'Hi there!' }
      ],
      isConnected: true,
      error: null,
      sendMessage: vi.fn(),
      clearMessages: vi.fn(),
      reconnect: vi.fn()
    });

    renderWithProviders(<Chat />);

    expect(screen.getByText('Hello')).toBeInTheDocument();
    expect(screen.getByText('Hi there!')).toBeInTheDocument();
  });

  it('shows streaming indicator during response', () => {
    const { useSSE } = await import('@hooks/useSSE');
    vi.mocked(useSSE).mockReturnValue({
      messages: [
        { role: 'user', content: 'Question' },
        { role: 'assistant', content: 'Streaming...', streaming: true }
      ],
      isConnected: true,
      error: null,
      sendMessage: vi.fn(),
      clearMessages: vi.fn(),
      reconnect: vi.fn()
    });

    renderWithProviders(<Chat />);

    expect(screen.getByTestId('streaming-indicator')).toBeInTheDocument();
  });

  it('displays error state', () => {
    const { useSSE } = await import('@hooks/useSSE');
    vi.mocked(useSSE).mockReturnValue({
      messages: [],
      isConnected: false,
      error: 'Connection failed',
      sendMessage: vi.fn(),
      clearMessages: vi.fn(),
      reconnect: vi.fn()
    });

    renderWithProviders(<Chat />);

    expect(screen.getByText(/connection failed/i)).toBeInTheDocument();
  });

  it('allows retry on error', async () => {
    const mockReconnect = vi.fn();
    const { useSSE } = await import('@hooks/useSSE');
    vi.mocked(useSSE).mockReturnValue({
      messages: [],
      isConnected: false,
      error: 'Connection failed',
      sendMessage: vi.fn(),
      clearMessages: vi.fn(),
      reconnect: mockReconnect
    });

    const user = userEvent.setup();
    renderWithProviders(<Chat />);

    const retryButton = screen.getByRole('button', { name: /retry/i });
    await user.click(retryButton);

    expect(mockReconnect).toHaveBeenCalled();
  });

  it('clears conversation', async () => {
    const mockClearMessages = vi.fn();
    const { useSSE } = await import('@hooks/useSSE');
    vi.mocked(useSSE).mockReturnValue({
      messages: [
        { role: 'user', content: 'Hello' }
      ],
      isConnected: true,
      error: null,
      sendMessage: vi.fn(),
      clearMessages: mockClearMessages,
      reconnect: vi.fn()
    });

    const user = userEvent.setup();
    renderWithProviders(<Chat />);

    const clearButton = screen.getByRole('button', { name: /clear/i });
    await user.click(clearButton);

    expect(mockClearMessages).toHaveBeenCalled();
  });

  it('auto-scrolls to latest message', async () => {
    const { useSSE } = await import('@hooks/useSSE');
    const { rerender } = renderWithProviders(<Chat />);

    // Add messages
    vi.mocked(useSSE).mockReturnValue({
      messages: [
        { role: 'user', content: 'Message 1' },
        { role: 'assistant', content: 'Response 1' }
      ],
      isConnected: true,
      error: null,
      sendMessage: vi.fn(),
      clearMessages: vi.fn(),
      reconnect: vi.fn()
    });

    rerender(
      <ChatProvider>
        <Chat />
      </ChatProvider>
    );

    // Verify scroll behavior
    const chatContainer = screen.getByTestId('chat-messages');
    expect(chatContainer.scrollTop).toBe(chatContainer.scrollHeight);
  });
});
