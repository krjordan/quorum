"""
Summary Service - Generate formatted debate summaries without AI judge
Phase 2 implementation: Simple formatted transcripts and statistics.
"""
from app.models.debate_v2 import (
    DebateV2,
    DebateSummary,
    ParticipantStats
)
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class SummaryService:
    """Service for generating debate summaries"""

    def generate_summary(self, debate: DebateV2) -> DebateSummary:
        """
        Generate formatted summary of a debate

        Args:
            debate: Completed or stopped debate

        Returns:
            DebateSummary with markdown transcript and statistics
        """
        logger.info(f"Generating summary for debate {debate.id}")

        # Calculate participant statistics
        participant_stats = self._calculate_participant_stats(debate)

        # Generate markdown transcript
        markdown_transcript = self._generate_markdown_transcript(debate)

        # Calculate duration
        duration_seconds = (debate.updated_at - debate.created_at).total_seconds()

        summary = DebateSummary(
            debate_id=debate.id,
            topic=debate.config.topic,
            status=debate.status,
            rounds_completed=len(debate.rounds),
            total_rounds=debate.config.max_rounds,
            participants=[p.name for p in debate.config.participants],
            participant_stats=participant_stats,
            total_tokens=debate.total_tokens,
            total_cost=debate.total_cost,
            duration_seconds=duration_seconds,
            markdown_transcript=markdown_transcript,
            created_at=debate.created_at,
            completed_at=debate.updated_at
        )

        return summary

    def _calculate_participant_stats(self, debate: DebateV2) -> list[ParticipantStats]:
        """Calculate statistics for each participant"""
        stats_dict = {}

        # Initialize stats for each participant
        for participant in debate.config.participants:
            stats_dict[participant.name] = {
                "name": participant.name,
                "model": participant.model,
                "total_tokens": 0,
                "total_cost": 0.0,
                "response_times": [],
                "response_count": 0
            }

        # Aggregate data from all rounds
        for round_obj in debate.rounds:
            for response in round_obj.responses:
                stats = stats_dict[response.participant_name]
                stats["total_tokens"] += response.tokens_used
                stats["response_times"].append(response.response_time_ms)
                stats["response_count"] += 1

        # Calculate costs per participant (proportional to their token usage)
        total_tokens_all = sum(debate.total_tokens.values())
        if total_tokens_all > 0:
            for name, stats in stats_dict.items():
                participant_ratio = stats["total_tokens"] / total_tokens_all
                stats["total_cost"] = debate.total_cost * participant_ratio

        # Create ParticipantStats objects
        participant_stats = []
        for name, stats in stats_dict.items():
            avg_response_time = (
                sum(stats["response_times"]) / len(stats["response_times"])
                if stats["response_times"]
                else 0.0
            )

            participant_stats.append(ParticipantStats(
                name=stats["name"],
                model=stats["model"],
                total_tokens=stats["total_tokens"],
                total_cost=stats["total_cost"],
                average_response_time_ms=avg_response_time,
                response_count=stats["response_count"]
            ))

        return participant_stats

    def _generate_markdown_transcript(self, debate: DebateV2) -> str:
        """Generate markdown-formatted transcript of the debate"""
        lines = []

        # Header
        lines.append(f"# Debate Transcript\n")
        lines.append(f"**Topic:** {debate.config.topic}\n")
        lines.append(f"**Status:** {debate.status.value}\n")
        lines.append(f"**Rounds Completed:** {len(debate.rounds)} / {debate.config.max_rounds}\n")
        lines.append(f"**Participants:** {', '.join(p.name for p in debate.config.participants)}\n")
        lines.append(f"**Total Cost:** ${debate.total_cost:.4f}\n")
        lines.append(f"**Created:** {debate.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n")
        lines.append(f"**Completed:** {debate.updated_at.strftime('%Y-%m-%d %H:%M:%S')}\n")
        lines.append("\n---\n")

        # Rounds
        for round_obj in debate.rounds:
            lines.append(f"\n## Round {round_obj.round_number}\n")
            lines.append(f"*Cost: ${round_obj.cost_estimate:.4f}*\n")

            # Responses in turn order
            for response in round_obj.responses:
                lines.append(f"\n### {response.participant_name} ({response.model})\n")
                lines.append(f"*Tokens: {response.tokens_used} | Response Time: {response.response_time_ms:.0f}ms*\n")
                lines.append(f"\n{response.content}\n")

            lines.append("\n---\n")

        # Footer with statistics
        lines.append("\n## Statistics\n")

        # Participant breakdown
        lines.append("\n### Participant Performance\n")
        participant_stats = self._calculate_participant_stats(debate)

        for stats in participant_stats:
            lines.append(f"\n**{stats.name}** ({stats.model})")
            lines.append(f"- Responses: {stats.response_count}")
            lines.append(f"- Total Tokens: {stats.total_tokens:,}")
            lines.append(f"- Cost: ${stats.total_cost:.4f}")
            lines.append(f"- Avg Response Time: {stats.average_response_time_ms:.0f}ms\n")

        # Token breakdown
        lines.append("\n### Token Usage by Model\n")
        for model, tokens in debate.total_tokens.items():
            lines.append(f"- **{model}**: {tokens:,} tokens\n")

        # Cost summary
        lines.append(f"\n### Total Cost\n")
        lines.append(f"**${debate.total_cost:.4f}**\n")

        return "".join(lines)

    def export_markdown(self, debate: DebateV2, file_path: str) -> str:
        """
        Export debate summary to markdown file

        Args:
            debate: Debate to export
            file_path: Path to save markdown file

        Returns:
            Path to saved file
        """
        summary = self.generate_summary(debate)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(summary.markdown_transcript)

        logger.info(f"Exported debate {debate.id} to {file_path}")

        return file_path


# Singleton instance
summary_service = SummaryService()
