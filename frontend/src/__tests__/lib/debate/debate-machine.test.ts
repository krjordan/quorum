/**
 * Tests for XState Debate Machine
 */
import { describe, it, expect } from 'vitest'
import { createActor } from 'xstate'
import { debateMachine } from '@/lib/debate/debate-machine'
import type { DebateConfigV2 } from '@/types/debate'

describe('Debate Machine', () => {
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

  describe('Initial State', () => {
    it('should start in CONFIGURING state', () => {
      const actor = createActor(debateMachine)
      actor.start()

      expect(actor.getSnapshot().matches('CONFIGURING')).toBe(true)
    })

    it('should have empty initial context', () => {
      const actor = createActor(debateMachine)
      actor.start()

      const context = actor.getSnapshot().context
      expect(context.debateId).toBeNull()
      expect(context.config).toBeNull()
      expect(context.currentRound).toBe(0)
      expect(context.currentTurn).toBe(0)
    })
  })

  describe('Configuration', () => {
    it('should accept valid config', () => {
      const actor = createActor(debateMachine)
      actor.start()

      actor.send({ type: 'SET_CONFIG', config: mockConfig })

      const context = actor.getSnapshot().context
      expect(context.config).toEqual(mockConfig)
    })

    it('should transition to READY when config is valid', () => {
      const actor = createActor(debateMachine)
      actor.start()

      actor.send({ type: 'SET_CONFIG', config: mockConfig })
      actor.send({ type: 'START_DEBATE' })

      const snapshot = actor.getSnapshot()
      expect(snapshot.matches('READY') || snapshot.matches('RUNNING')).toBe(true)
    })

    it('should reject config with too few participants', () => {
      const actor = createActor(debateMachine)
      actor.start()

      const invalidConfig = {
        ...mockConfig,
        participants: [mockConfig.participants[0]],
      }

      actor.send({ type: 'SET_CONFIG', config: invalidConfig })
      actor.send({ type: 'START_DEBATE' })

      // Should remain in CONFIGURING due to validation
      expect(actor.getSnapshot().matches('CONFIGURING')).toBe(true)
    })

    it('should reject config with invalid rounds', () => {
      const actor = createActor(debateMachine)
      actor.start()

      const invalidConfig = {
        ...mockConfig,
        max_rounds: 0,
      }

      actor.send({ type: 'SET_CONFIG', config: invalidConfig })
      actor.send({ type: 'START_DEBATE' })

      expect(actor.getSnapshot().matches('CONFIGURING')).toBe(true)
    })
  })

  describe('Turn Management', () => {
    it('should advance turns correctly', () => {
      const actor = createActor(debateMachine)
      actor.start()

      actor.send({ type: 'SET_CONFIG', config: mockConfig })
      actor.send({ type: 'START_DEBATE', debateId: 'test-debate-123' })

      const initialContext = actor.getSnapshot().context
      expect(initialContext.currentTurn).toBe(0)

      actor.send({
        type: 'STREAM_COMPLETE',
        response: {
          participant_name: 'Agent 1',
          participant_index: 0,
          model: 'gpt-4o',
          content: 'Test response',
          tokens_used: 100,
          response_time_ms: 500,
        },
      })

      const updatedContext = actor.getSnapshot().context
      expect(updatedContext.currentTurn).toBe(1)
    })

    it('should advance rounds after all participants respond', () => {
      const actor = createActor(debateMachine)
      actor.start()

      actor.send({ type: 'SET_CONFIG', config: mockConfig })
      actor.send({ type: 'START_DEBATE', debateId: 'test-debate-123' })

      // Agent 1 responds
      actor.send({
        type: 'STREAM_COMPLETE',
        response: {
          participant_name: 'Agent 1',
          participant_index: 0,
          model: 'gpt-4o',
          content: 'Response 1',
          tokens_used: 100,
          response_time_ms: 500,
        },
      })

      expect(actor.getSnapshot().context.currentRound).toBe(1)
      expect(actor.getSnapshot().context.currentTurn).toBe(1)

      // Agent 2 responds (completes round)
      actor.send({
        type: 'STREAM_COMPLETE',
        response: {
          participant_name: 'Agent 2',
          participant_index: 1,
          model: 'claude-3-5-sonnet-20241022',
          content: 'Response 2',
          tokens_used: 100,
          response_time_ms: 500,
        },
      })

      const context = actor.getSnapshot().context
      expect(context.currentRound).toBe(2)
      expect(context.currentTurn).toBe(0)
    })
  })

  describe('Pause and Resume', () => {
    it('should transition to PAUSED state', () => {
      const actor = createActor(debateMachine)
      actor.start()

      actor.send({ type: 'SET_CONFIG', config: mockConfig })
      actor.send({ type: 'START_DEBATE', debateId: 'test-debate-123' })
      actor.send({ type: 'PAUSE' })

      expect(actor.getSnapshot().matches('PAUSED')).toBe(true)
    })

    it('should resume from PAUSED state', () => {
      const actor = createActor(debateMachine)
      actor.start()

      actor.send({ type: 'SET_CONFIG', config: mockConfig })
      actor.send({ type: 'START_DEBATE', debateId: 'test-debate-123' })
      actor.send({ type: 'PAUSE' })
      actor.send({ type: 'RESUME' })

      expect(actor.getSnapshot().matches('RUNNING')).toBe(true)
    })
  })

  describe('Stop and Complete', () => {
    it('should transition to COMPLETED when stopped', () => {
      const actor = createActor(debateMachine)
      actor.start()

      actor.send({ type: 'SET_CONFIG', config: mockConfig })
      actor.send({ type: 'START_DEBATE', debateId: 'test-debate-123' })
      actor.send({ type: 'STOP' })

      expect(actor.getSnapshot().matches('COMPLETED')).toBe(true)
    })

    it('should transition to COMPLETED after all rounds', () => {
      const actor = createActor(debateMachine)
      actor.start()

      const shortConfig = {
        ...mockConfig,
        max_rounds: 1,
      }

      actor.send({ type: 'SET_CONFIG', config: shortConfig })
      actor.send({ type: 'START_DEBATE', debateId: 'test-debate-123' })

      // Complete round 1
      actor.send({
        type: 'STREAM_COMPLETE',
        response: {
          participant_name: 'Agent 1',
          participant_index: 0,
          model: 'gpt-4o',
          content: 'Response 1',
          tokens_used: 100,
          response_time_ms: 500,
        },
      })

      actor.send({
        type: 'STREAM_COMPLETE',
        response: {
          participant_name: 'Agent 2',
          participant_index: 1,
          model: 'claude-3-5-sonnet-20241022',
          content: 'Response 2',
          tokens_used: 100,
          response_time_ms: 500,
        },
      })

      // Should complete after max_rounds (1)
      expect(actor.getSnapshot().matches('COMPLETED')).toBe(true)
    })
  })

  describe('Cost Tracking', () => {
    it('should update costs on STREAM_COMPLETE', () => {
      const actor = createActor(debateMachine)
      actor.start()

      actor.send({ type: 'SET_CONFIG', config: mockConfig })
      actor.send({ type: 'START_DEBATE', debateId: 'test-debate-123' })

      actor.send({
        type: 'STREAM_COMPLETE',
        response: {
          participant_name: 'Agent 1',
          participant_index: 0,
          model: 'gpt-4o',
          content: 'Response',
          tokens_used: 100,
          response_time_ms: 500,
        },
      })

      const context = actor.getSnapshot().context
      expect(context.totalCost).toBeGreaterThan(0)
      expect(context.totalTokens['gpt-4o']).toBe(100)
    })
  })

  describe('Error Handling', () => {
    it('should transition to ERROR state on error', () => {
      const actor = createActor(debateMachine)
      actor.start()

      actor.send({ type: 'SET_CONFIG', config: mockConfig })
      actor.send({ type: 'START_DEBATE', debateId: 'test-debate-123' })
      actor.send({ type: 'ERROR', error: 'Test error' })

      expect(actor.getSnapshot().matches('ERROR')).toBe(true)
      expect(actor.getSnapshot().context.error).toBe('Test error')
    })

    it('should allow retry from ERROR state', () => {
      const actor = createActor(debateMachine)
      actor.start()

      actor.send({ type: 'SET_CONFIG', config: mockConfig })
      actor.send({ type: 'START_DEBATE', debateId: 'test-debate-123' })
      actor.send({ type: 'ERROR', error: 'Test error' })
      actor.send({ type: 'RETRY' })

      expect(actor.getSnapshot().matches('CONFIGURING')).toBe(true)
      expect(actor.getSnapshot().context.error).toBeNull()
    })
  })
})
