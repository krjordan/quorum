/**
 * Type definitions for conversation quality tracking
 */

export interface HealthScore {
  score: number; // 0-100
  trend?: 'improving' | 'stable' | 'declining';
  lastUpdate?: string;
  recommendation?: string;
}

export type ContradictionSeverity = 'high' | 'medium' | 'low';

export interface Contradiction {
  id: string;
  severity: ContradictionSeverity;
  statement1: {
    participantName: string;
    content: string;
    messageId: string;
  };
  statement2: {
    participantName: string;
    content: string;
    messageId: string;
  };
  similarityScore?: number;
  timestamp: string;
}

export type CitationStatus = 'verified' | 'unverified' | 'pending';

export interface Citation {
  id: string;
  text: string;
  source?: {
    title: string;
    url: string;
    author?: string;
  };
  status: CitationStatus;
  timestamp?: string;
}

export interface LoopDetection {
  detected: boolean;
  patternLength?: number;
  repetitions?: number;
  lastOccurrence?: string;
}

export interface QualityMetrics {
  healthScore: HealthScore;
  contradictions: Contradiction[];
  loopDetection?: LoopDetection;
  totalCitations: number;
  verifiedCitations: number;
}
