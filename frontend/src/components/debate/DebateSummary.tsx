/**
 * Debate Summary Component
 * Displays formatted summary with markdown transcript and statistics in a modal
 * Phase 2: No AI judge, just formatted data
 */
'use client';

import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Download, FileText } from 'lucide-react';
import type { UseSequentialDebateReturn } from '@/hooks/useSequentialDebate';

interface DebateSummary {
  debate_id: string;
  topic: string;
  status: string;
  rounds_completed: number;
  total_rounds: number;
  participants: string[];
  participant_stats: Array<{
    name: string;
    model: string;
    total_tokens: number;
    total_cost: number;
    average_response_time_ms: number;
    response_count: number;
  }>;
  total_tokens: Record<string, number>;
  total_cost: number;
  duration_seconds: number;
  markdown_transcript: string;
  created_at: string;
  completed_at: string;
}

interface DebateSummaryProps {
  debate: UseSequentialDebateReturn;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function DebateSummary({ debate, open, onOpenChange }: DebateSummaryProps) {
  const { getSummary, isCompleted, debateId } = debate;
  const [summary, setSummary] = useState<DebateSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [showTranscript, setShowTranscript] = useState(false);

  useEffect(() => {
    if (isCompleted && debateId && !summary) {
      loadSummary();
    }
  }, [isCompleted, debateId]);

  const loadSummary = async () => {
    setLoading(true);
    try {
      const data = await getSummary();
      if (data) {
        setSummary(data);
      }
    } catch (error) {
      console.error('Failed to load summary:', error);
    } finally {
      setLoading(false);
    }
  };

  const downloadTranscript = () => {
    if (!summary) return;

    const blob = new Blob([summary.markdown_transcript], {
      type: 'text/markdown',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `debate_${summary.debate_id}_transcript.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-5xl max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center justify-between">
            <div>
              <span className="text-2xl font-bold">Debate Summary</span>
              {summary && (
                <p className="text-sm text-muted-foreground mt-1 font-normal">
                  {summary.topic}
                </p>
              )}
            </div>
            {summary && (
              <Badge variant={summary.status === 'completed' ? 'default' : 'secondary'}>
                {summary.status}
              </Badge>
            )}
          </DialogTitle>
        </DialogHeader>

        {!isCompleted ? (
          <div className="text-center text-muted-foreground py-8">
            Debate not completed yet
          </div>
        ) : loading ? (
          <div className="text-center text-muted-foreground py-8">
            Generating summary...
          </div>
        ) : !summary ? (
          <div className="text-center py-8">
            <Button onClick={loadSummary}>Load Summary</Button>
          </div>
        ) : (
          <ScrollArea className="flex-1 pr-4">
            <div className="space-y-6">

              {/* Overview Stats */}
              <div className="grid grid-cols-4 gap-4">
                <Card className="p-4">
                  <div className="text-sm text-muted-foreground">Rounds</div>
                  <div className="text-2xl font-bold">
                    {summary.rounds_completed}/{summary.total_rounds}
                  </div>
                </Card>
                <Card className="p-4">
                  <div className="text-sm text-muted-foreground">Participants</div>
                  <div className="text-2xl font-bold">{summary.participants.length}</div>
                </Card>
                <Card className="p-4">
                  <div className="text-sm text-muted-foreground">Total Cost</div>
                  <div className="text-2xl font-bold">${summary.total_cost.toFixed(4)}</div>
                </Card>
                <Card className="p-4">
                  <div className="text-sm text-muted-foreground">Duration</div>
                  <div className="text-2xl font-bold">
                    {Math.floor(summary.duration_seconds)}s
                  </div>
                </Card>
              </div>

              {/* Participant Statistics */}
              <div>
                <h3 className="font-semibold mb-3">Participant Performance</h3>
                <div className="space-y-2">
                  {summary.participant_stats.map((stats) => (
                    <Card key={stats.name} className="p-4">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{stats.name}</span>
                          <Badge variant="outline" className="text-xs">
                            {stats.model}
                          </Badge>
                        </div>
                        <div className="text-sm text-muted-foreground">
                          ${stats.total_cost.toFixed(4)}
                        </div>
                      </div>
                      <div className="grid grid-cols-3 gap-4 text-sm">
                        <div>
                          <div className="text-muted-foreground">Responses</div>
                          <div className="font-medium">{stats.response_count}</div>
                        </div>
                        <div>
                          <div className="text-muted-foreground">Tokens</div>
                          <div className="font-medium">{stats.total_tokens.toLocaleString()}</div>
                        </div>
                        <div>
                          <div className="text-muted-foreground">Avg Time</div>
                          <div className="font-medium">
                            {stats.average_response_time_ms.toFixed(0)}ms
                          </div>
                        </div>
                      </div>
                    </Card>
                  ))}
                </div>
              </div>

              {/* Transcript */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-semibold">Full Transcript</h3>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setShowTranscript(!showTranscript)}
                    >
                      <FileText className="h-4 w-4 mr-2" />
                      {showTranscript ? 'Hide' : 'Show'} Transcript
                    </Button>
                    <Button variant="outline" size="sm" onClick={downloadTranscript}>
                      <Download className="h-4 w-4 mr-2" />
                      Download Markdown
                    </Button>
                  </div>
                </div>

                {showTranscript && (
                  <ScrollArea className="h-[400px] border rounded-md p-4">
                    <pre className="text-sm whitespace-pre-wrap font-sans">
                      {summary.markdown_transcript}
                    </pre>
                  </ScrollArea>
                )}
              </div>
            </div>
          </ScrollArea>
        )}
      </DialogContent>
    </Dialog>
  );
}
