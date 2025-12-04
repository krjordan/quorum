/**
 * DebateInputControls Component
 * Bottom input bar with text field and control buttons
 */
'use client';

import { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Send, Pause, Play, Square } from 'lucide-react';
import type { UseSequentialDebateReturn } from '@/hooks/useSequentialDebate';

interface DebateInputControlsProps {
  debate: UseSequentialDebateReturn;
}

export function DebateInputControls({ debate }: DebateInputControlsProps) {
  const { isRunning, isPaused, pauseDebate, resumeDebate, stopDebate } = debate;
  const [userInput, setUserInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [userInput]);

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setUserInput(e.target.value);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSend = () => {
    // Phase 1: UI only, no actual sending
    console.log('User message (not sent):', userInput);
    // Phase 2 will implement actual sending
    setUserInput('');
  };

  return (
    <div className="bg-background border-t">
      <div className="max-w-4xl mx-auto p-4">
        <div className="flex gap-3 items-end">
          {/* Auto-resizing Textarea */}
          <Textarea
            ref={textareaRef}
            value={userInput}
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            placeholder="Type a message... (coming soon)"
            disabled={true} // Phase 1: disabled
            rows={1}
            className="flex-1 resize-none max-h-32 min-h-10"
          />

          {/* Control Buttons */}
          <div className="flex gap-2">
            {/* Pause/Resume Button */}
            <Button
              size="icon"
              variant={isPaused ? 'default' : 'outline'}
              onClick={isPaused ? resumeDebate : pauseDebate}
              disabled={!isRunning && !isPaused}
              title={isPaused ? 'Resume' : 'Pause'}
            >
              {isPaused ? <Play className="h-4 w-4" /> : <Pause className="h-4 w-4" />}
            </Button>

            {/* Stop Button */}
            <Button
              size="icon"
              variant="destructive"
              onClick={stopDebate}
              disabled={!isRunning && !isPaused}
              title="Stop"
            >
              <Square className="h-4 w-4" />
            </Button>

            {/* Send Button */}
            <Button
              size="icon"
              disabled // Phase 1: disabled
              title="Send message (coming soon)"
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Helper Text */}
        <div className="text-xs text-muted-foreground mt-2">
          User participation coming soon • Press Enter to send, Shift+Enter for new line
        </div>
      </div>
    </div>
  );
}
