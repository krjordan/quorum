/**
 * Tests for useSequentialDebate hook
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { useSequentialDebate } from '@/hooks/useSequentialDebate'
import type { DebateConfigV2 } from '@/types/debate'

// Mock fetch API
global.fetch = vi.fn()
global.EventSource = vi.fn()

describe('useSequentialDebate', () => {
  const mockConfig: DebateConfigV2 = {
    topic: 'Should AI development be open source?',
    participants: [
      {
        name: 'Agent 1',
        model: 'gpt-4o',
        system_prompt: 'You are an advocate for open source AI.',
        temperature: 0.7,
      },
      {
        name: 'Agent 2',
        model: 'claude-3-5-sonnet-20241022',
        system_prompt: 'You are a proponent of controlled AI development.',
        temperature: 0.7,
      },
    ],
    max_rounds: 2,
    context_window_rounds: 10,
    cost_warning_threshold: 1.0,
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('createDebate', () => {
    it('should create a debate successfully', async () => {
      const mockDebate = {
        id: 'debate-123',
        status: 'initialized',
        current_round: 1,
        current_turn: 0,
        config: mockConfig,
      }

      ;(global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockDebate,
      })

      const { result } = renderHook(() => useSequentialDebate())

      await waitFor(async () => {
        await result.current.createDebate(mockConfig)
      })

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/debates/v2'),
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(mockConfig),
        })
      )
    })

    it('should handle creation errors', async () => {
      ;(global.fetch as any).mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => ({ detail: 'Invalid config' }),
      })

      const { result } = renderHook(() => useSequentialDebate())

      await expect(
        result.current.createDebate(mockConfig)
      ).rejects.toThrow()
    })
  })

  describe('stopDebate', () => {
    it('should stop a debate successfully', async () => {
      const mockDebateId = 'debate-123'
      const mockStoppedDebate = {
        id: mockDebateId,
        status: 'stopped',
        stopped_manually: true,
      }

      ;(global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockStoppedDebate,
      })

      const { result } = renderHook(() => useSequentialDebate())

      await waitFor(async () => {
        await result.current.stopDebate(mockDebateId)
      })

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining(`/api/v1/debates/v2/${mockDebateId}/stop`),
        expect.objectContaining({
          method: 'POST',
        })
      )
    })
  })

  describe('pauseDebate', () => {
    it('should pause a debate successfully', async () => {
      const mockDebateId = 'debate-123'
      const mockPausedDebate = {
        id: mockDebateId,
        status: 'paused',
      }

      ;(global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockPausedDebate,
      })

      const { result } = renderHook(() => useSequentialDebate())

      await waitFor(async () => {
        await result.current.pauseDebate(mockDebateId)
      })

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining(`/api/v1/debates/v2/${mockDebateId}/pause`),
        expect.objectContaining({
          method: 'POST',
        })
      )
    })
  })

  describe('resumeDebate', () => {
    it('should resume a debate successfully', async () => {
      const mockDebateId = 'debate-123'
      const mockResumedDebate = {
        id: mockDebateId,
        status: 'running',
      }

      ;(global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResumedDebate,
      })

      const { result } = renderHook(() => useSequentialDebate())

      await waitFor(async () => {
        await result.current.resumeDebate(mockDebateId)
      })

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining(`/api/v1/debates/v2/${mockDebateId}/resume`),
        expect.objectContaining({
          method: 'POST',
        })
      )
    })
  })

  describe('getSummary', () => {
    it('should fetch debate summary successfully', async () => {
      const mockDebateId = 'debate-123'
      const mockSummary = {
        debate_id: mockDebateId,
        topic: mockConfig.topic,
        rounds_completed: 2,
        total_rounds: 2,
        markdown_transcript: '# Debate Transcript\n...',
      }

      ;(global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockSummary,
      })

      const { result } = renderHook(() => useSequentialDebate())

      let summary
      await waitFor(async () => {
        summary = await result.current.getSummary(mockDebateId)
      })

      expect(summary).toEqual(mockSummary)
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining(
          `/api/v1/debates/v2/${mockDebateId}/summary`
        ),
        expect.objectContaining({
          method: 'GET',
        })
      )
    })
  })

  describe('SSE Integration', () => {
    it('should connect to SSE for next turn', () => {
      const mockDebateId = 'debate-123'
      const mockEventSource = {
        addEventListener: vi.fn(),
        close: vi.fn(),
        onerror: null,
      }

      ;(global.EventSource as any).mockImplementation(
        () => mockEventSource
      )

      const { result } = renderHook(() => useSequentialDebate())

      result.current.requestNextTurn(mockDebateId)

      expect(global.EventSource).toHaveBeenCalledWith(
        expect.stringContaining(
          `/api/v1/debates/v2/${mockDebateId}/next-turn`
        )
      )
    })

    it('should handle SSE errors', () => {
      const mockDebateId = 'debate-123'
      const mockEventSource = {
        addEventListener: vi.fn(),
        close: vi.fn(),
        onerror: null,
      }

      ;(global.EventSource as any).mockImplementation(() => {
        setTimeout(() => {
          if (mockEventSource.onerror) {
            mockEventSource.onerror(new Event('error'))
          }
        }, 100)
        return mockEventSource
      })

      const { result } = renderHook(() => useSequentialDebate())

      result.current.requestNextTurn(mockDebateId)

      // EventSource should be created
      expect(global.EventSource).toHaveBeenCalled()
    })

    it('should close SSE connection on cleanup', () => {
      const mockDebateId = 'debate-123'
      const mockEventSource = {
        addEventListener: vi.fn(),
        close: vi.fn(),
        onerror: null,
      }

      ;(global.EventSource as any).mockImplementation(
        () => mockEventSource
      )

      const { result, unmount } = renderHook(() => useSequentialDebate())

      result.current.requestNextTurn(mockDebateId)
      unmount()

      expect(mockEventSource.close).toHaveBeenCalled()
    })
  })

  describe('Error Handling', () => {
    it('should handle network errors gracefully', async () => {
      ;(global.fetch as any).mockRejectedValueOnce(
        new Error('Network error')
      )

      const { result } = renderHook(() => useSequentialDebate())

      await expect(
        result.current.createDebate(mockConfig)
      ).rejects.toThrow('Network error')
    })

    it('should handle invalid responses', async () => {
      ;(global.fetch as any).mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => ({ detail: 'Internal server error' }),
      })

      const { result } = renderHook(() => useSequentialDebate())

      await expect(
        result.current.createDebate(mockConfig)
      ).rejects.toThrow()
    })
  })
})
