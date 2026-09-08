#!/usr/bin/env python3
"""
Integration script to test and verify the end-to-end voice-based candidate application,
screening session execution, dynamic question generation, turn evaluations, and
evaluation report generation.
"""

import asyncio
import httpx
import json
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("voice_screening_test")

BASE_URL = "http://127.0.0.1:8000"


async def run_voice_screening_simulation():
    async with httpx.AsyncClient(timeout=120.0) as client:
        logger.info("=== Starting AI Voice Interview Agent End-to-End Test ===")

        # 1. Register Recruiter Account
        recruiter_email = f"recruiter_{asyncio.get_event_loop().time()}@implere.com"
        logger.info(f"1. Registering Recruiter ({recruiter_email})...")
        signup_res = await client.post(f"{BASE_URL}/api/v1/auth/signup", json={
            "full_name": "Sarah Recruiter",
            "email": recruiter_email,
            "password": "Password123!",
            "role": "interviewer"
        })
        assert signup_res.status_code == 201, f"Recruiter signup failed: {signup_res.text}"

        token_res = await client.post(f"{BASE_URL}/api/v1/auth/token", data={
            "username": recruiter_email,
            "password": "Password123!"
        })
        assert token_res.status_code == 200, f"Recruiter token failed: {token_res.text}"
        recruiter_token = token_res.json()["access_token"]
        recruiter_headers = {"Authorization": f"Bearer {recruiter_token}"}

        # 2. Post Job Description
        logger.info("2. Creating Job Description (Senior AI & Backend Systems Engineer)...")
        jd_res = await client.post(f"{BASE_URL}/api/v1/jobs", json={
            "title": "Senior AI & Backend Systems Engineer",
            "company_name": "Implere Technologies",
            "status": "Open",
            "work_mode": "Onsite",
            "location": "Bangalore",
            "experience_range": "3 - 5 Years",
            "salary_range": "₹ 18L - 24L / year",
            "match_threshold": 70.0,
            "raw_text": (
                "Role Title: Senior AI & Backend Systems Engineer\n"
                "Company: Implere Technologies\n"
                "We are hiring a Senior AI & Backend Systems Engineer with 3-5 years experience.\n"
                "Required Tech Stack: Python, FastAPI, PostgreSQL, LangGraph, Ollama, Docker.\n"
                "Nice to Have: FAISS, WebSockets, Audio Speech Synthesis.\n"
                "Responsibilities: Design scalable backend microservices, build agentic workflows using LangGraph, "
                "optimize SQL queries in PostgreSQL, and maintain automated CI/CD pipelines."
            )
        }, headers=recruiter_headers)
        assert jd_res.status_code == 201, f"Job creation failed: {jd_res.text}"
        job_id = jd_res.json()["id"]
        logger.info(f"Job Description created with ID: {job_id}")

        # 3. Register Candidate Account
        candidate_email = f"candidate_{asyncio.get_event_loop().time()}@example.com"
        logger.info(f"3. Registering Candidate ({candidate_email})...")
        cand_signup = await client.post(f"{BASE_URL}/api/v1/auth/signup", json={
            "full_name": "Alex Rivers",
            "email": candidate_email,
            "password": "Password123!",
            "role": "candidate"
        })
        assert cand_signup.status_code == 201, f"Candidate signup failed: {cand_signup.text}"

        cand_token_res = await client.post(f"{BASE_URL}/api/v1/auth/token", data={
            "username": candidate_email,
            "password": "Password123!"
        })
        assert cand_token_res.status_code == 200
        candidate_token = cand_token_res.json()["access_token"]
        candidate_headers = {"Authorization": f"Bearer {candidate_token}"}

        # 4. Candidate Submits Resume Application
        logger.info("4. Candidate Uploading Resume Application...")
        resume_content = (
            "ALEX RIVERS\n"
            "Bangalore, India | +91 9876543210 | alex.rivers@example.com | GitHub: github.com/alexrivers\n\n"
            "SUMMARY\n"
            "Senior Backend & AI Engineer with 4.5 years of experience building high-concurrency Python applications, "
            "agentic state machines, and vector search systems.\n\n"
            "TECHNICAL SKILLS\n"
            "Languages & Frameworks: Python, FastAPI, Django, LangGraph, Ollama, PyTest\n"
            "Databases & Storage: PostgreSQL, Redis, FAISS Vector Search\n"
            "DevOps: Docker, Kubernetes, GitHub Actions CI/CD\n\n"
            "PROJECTS & EXPERIENCE\n"
            "1. AI Voice Screening Platform:\n"
            "Designed and implemented an automated voice screening platform using FastAPI, LangGraph agent workflows, "
            "and Local Speech TTS/STT pipelines handling 1,000+ daily candidate interviews.\n"
            "2. Realtime Query Engine:\n"
            "Built a low-latency database query engine using PostgreSQL and Redis caching, achieving sub-20ms P99 latencies.\n"
            "3. FAISS Vector Search Gateway:\n"
            "Integrated similarity search with FAISS and Ollama LLM embeddings for semantic document retrieval."
        ).encode("utf-8")

        files = {"file": ("alex_rivers_resume.txt", resume_content, "text/plain")}
        res_res = await client.post(
            f"{BASE_URL}/api/v1/resumes?job_id={job_id}",
            files=files,
            headers=candidate_headers
        )
        assert res_res.status_code == 201, f"Resume application failed: {res_res.text}"
        resume_id = res_res.json()["id"]
        logger.info(f"Resume application submitted successfully with ID: {resume_id}")

        # 5. Candidate Starts Live Screening Session
        logger.info("5. Starting Live Voice Screening Session (POST /api/v1/interviews/sessions)...")
        session_res = await client.post(f"{BASE_URL}/api/v1/interviews/sessions", json={
            "job_description_id": job_id,
            "resume_id": resume_id
        }, headers=candidate_headers)
        assert session_res.status_code == 201, f"Session creation failed: {session_res.text}"
        session_data = session_res.json()
        logger.info(f"Raw Session Response JSON: {session_data}")
        interview_id = session_data["id"]
        first_question = session_data.get("first_question", session_data.get("questions", [{}])[0].get("question_text", "First Question"))
        questions_plan = session_data.get("questions", [])

        logger.info(f"Session initialized with Interview ID: {interview_id}")
        logger.info(f"First Question Displayed: '{first_question}'")
        logger.info("Dynamically Planned Questions:")
        for idx, q in enumerate(questions_plan):
            logger.info(f"  [{idx + 1}] Topic: {q['topic']} -> '{q['question_text']}'")

        # 6. Candidate Executes 5 Turn Submissions
        candidate_answers = [
            "In my AI Voice Screening Platform project, I architected the backend using FastAPI and LangGraph to manage non-linear interview workflows. I integrated speech-to-text and text-to-speech pipelines using WebSockets and background processing to keep turn latency under 2 seconds.",
            "The main bottleneck in the AI Voice Screening project was managing concurrent audio streams and LLM response delays. I resolved this by introducing asynchronous queue workers in Python and caching intermediate state in Redis.",
            "With 4.5 years of experience, I use FastAPI for high-throughput async endpoints and LangGraph state nodes to enforce strict deterministic guardrails over LLM outputs, ensuring 99.9% uptime in production.",
            "I design PostgreSQL schemas with composite indexes and normalized tables for transactional data, while leveraging FAISS for high-dimensional vector embeddings, optimizing query execution plans using EXPLAIN ANALYZE.",
            "Our CI/CD pipeline runs automated unit tests with PyTest in Docker containers on every pull request. We enforce 90%+ code coverage, run static analysis with Flake8, and perform blue-green deployments on Kubernetes."
        ]

        logger.info("6. Executing Voice Screening Candidate Turns...")
        turn_idx = 0
        is_last = False
        while not is_last and turn_idx < 10:
            answer = candidate_answers[turn_idx % len(candidate_answers)]
            logger.info(f"\n--- Submitting Turn {turn_idx + 1} ---")
            logger.info(f"Candidate Answer: '{answer[:80]}...'")

            turn_res = await client.post(
                f"{BASE_URL}/api/v1/interviews/{interview_id}/turns",
                json={
                    "response_text": answer,
                    "latency_seconds": 2.5
                },
                headers=candidate_headers
            )
            assert turn_res.status_code == 200, f"Turn submission failed: {turn_res.text}"
            turn_data = turn_res.json()
            is_last = turn_data["is_last"]
            next_q = turn_data["next_question"]

            if is_last:
                logger.info("All questions answered! Voice screening session finalized.")
                break
            else:
                logger.info(f"Next Question Prompted: '{next_q}'")
            turn_idx += 1

        # 7. Recruiter Inspects the Evaluation Report
        logger.info("\n7. Fetching Final Recruiter Evaluation Report...")
        report_res = await client.get(
            f"{BASE_URL}/api/v1/reports/{interview_id}",
            headers=recruiter_headers
        )
        assert report_res.status_code == 200, f"Report fetch failed: {report_res.text}"
        report = report_res.json()

        logger.info("==========================================")
        logger.info("      FINAL VOICE EVALUATION REPORT      ")
        logger.info("==========================================")
        logger.info(f"Candidate: Alex Rivers")
        logger.info(f"Overall Score: {report['overall_score']} / 10.0")
        logger.info(f"Recommendation: {report['recommendation'].upper()}")
        logger.info(f"Executive Summary: {report['primary_summary']}")
        logger.info("Detailed Breakdown by Dimension:")
        for topic, detail in report.get("details", {}).items():
            logger.info(f"  • {topic}: Score {detail.get('score')} | Evidence: {detail.get('evidence')}")

        logger.info("\nVoice screening simulation completed with 100% SUCCESS!")

if __name__ == "__main__":
    asyncio.run(run_voice_screening_simulation())
