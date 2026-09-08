# Product Specification (SPEC)

# AI Voice Interview Agent

## Vision

Build an AI-powered voice interviewer that screens candidates by
analyzing a Job Description (JD) and a candidate's resume, conducting an
adaptive voice interview, evaluating responses, and generating a
recruiter-ready report.

## Goals

-   Reduce recruiter screening time.
-   Provide standardized candidate evaluations.
-   Adapt questions to the candidate's background.
-   Produce evidence-backed hiring recommendations.

## Primary Users

-   Talent Acquisition (TAG)
-   Hiring Managers
-   Candidates

## Functional Requirements

1.  Recruiter authentication
2.  Upload Job Description
3.  Upload Resume
4.  Resume & JD parsing
5.  Resume-JD matching
6.  AI interview planning
7.  Voice interview
8.  Speech-to-text transcription
9.  Answer evaluation
10. Adaptive follow-up questions
11. Recruiter report generation
12. Interview transcript storage

## Non-Functional Requirements

-   Average response latency \< 3 seconds
-   Modular architecture
-   Local LLM support
-   Audit logging
-   Secure document handling
-   Configurable interview templates

## Acceptance Criteria

-   Interview completes end-to-end.
-   Recruiter receives structured report.
-   All questions, answers, scores, and transcripts are stored.
