from typing import List, Dict, Any
import logging
from datetime import datetime
from src.db.models import EvaluationReport, InterviewTurn

logger = logging.getLogger(__name__)


class ReportService:
    """
    Service responsible for formatting, exporting, and compiling candidate evaluation reports.
    """

    @staticmethod
    def generate_markdown(
        report: EvaluationReport, 
        candidate_name: str, 
        job_title: str, 
        turns: List[InterviewTurn]
    ) -> str:
        """
        Compiles an EvaluationReport and associated turns history into a highly readable,
        structured Markdown document for recruiters.
        """
        logger.info(f"Generating markdown report for candidate {candidate_name} for role {job_title}")
        
        created_str = (
            report.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")
            if report.created_at
            else datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        )
        
        md_lines = [
            f"# Candidate Evaluation Report",
            f"",
            f"**Candidate Name:** {candidate_name}",
            f"**Applied Position:** {job_title}",
            f"**Evaluation Date:** {created_str}",
            f"",
            f"## 1. Overall Assessment Summary",
            f"",
            f"- **Overall Recommendation:** `{report.recommendation.upper()}`",
            f"- **AI Score Rating:** `{report.overall_score:.1f} / 10.0`",
        ]
        
        # Include human-in-the-loop overrides
        if report.recruiter_override_recommendation:
            md_lines.extend([
                f"- **Recruiter Override Recommendation:** `{report.recruiter_override_recommendation.upper()}`",
                f"- **Reviewer ID:** {report.reviewer_id}",
                f"- **Review Date:** {report.reviewed_at.strftime('%Y-%m-%d %H:%M:%S') if report.reviewed_at else 'N/A'}"
            ])
            
        md_lines.extend([
            f"",
            f"### Primary Executive Summary",
            f"{report.primary_summary}",
            f""
        ])
        
        if report.recruiter_notes:
            md_lines.extend([
                f"### Recruiter Override Notes & Feedback",
                f"{report.recruiter_notes}",
                f""
            ])
            
        md_lines.extend([
            f"## 2. Technical and Core Rubric Scores",
            f""
        ])
        
        # Parse details
        details: Dict[str, Any] = report.details or {}
        for category, cat_data in details.items():
            score = cat_data.get("score", 0.0)
            evidence = cat_data.get("evidence", "No supporting evidence cited.")
            md_lines.extend([
                f"### {category.replace('_', ' ').title()}",
                f"- **Score:** `{score:.1f} / 10.0`",
                f"- **Evidence & Citations:** *{evidence}*",
                f""
            ])
            
        md_lines.extend([
            f"## 3. Question-by-Question Transcript Details",
            f""
        ])
        
        # Sort turns by index to preserve interview timeline
        sorted_turns = sorted(turns, key=lambda t: t.turn_index)
        for turn in sorted_turns:
            score_val = f"{turn.turn_score:.1f}" if turn.turn_score is not None else "N/A"
            evidence_val = turn.score_evidence if turn.score_evidence else "N/A"
            latency_val = f"{turn.latency_seconds:.2f}s" if turn.latency_seconds is not None else "N/A"
            
            md_lines.extend([
                f"### Turn {turn.turn_index + 1}",
                f"- **Interviewer Question Asked:** \"*{turn.question_asked}*\"",
                f"- **Candidate Transcript:** \"{turn.response_transcript or '(No response transcript generated)'}\"",
                f"- **Response Latency:** `{latency_val}`",
                f"- **Turn Assessment Score:** `{score_val} / 10.0`",
                f"- **Score Evidence:** *{evidence_val}*",
                f""
            ])
            
        return "\n".join(md_lines)

    @staticmethod
    def generate_raw_text(
        report: EvaluationReport,
        candidate_name: str,
        job_title: str,
        turns: List[InterviewTurn]
    ) -> str:
        """
        Compiles the report as plain text, suitable for console logs or external API exports.
        """
        markdown_content = ReportService.generate_markdown(
            report=report,
            candidate_name=candidate_name,
            job_title=job_title,
            turns=turns
        )
        # Simply strip markdown headers for plain text format
        return markdown_content.replace("# ", "").replace("## ", "").replace("### ", "").replace("`", "")
