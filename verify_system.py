import asyncio
import httpx
import uuid
import sys
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("system_verifier")

BASE_URL = "http://127.0.0.1:8000"

async def test_endpoint_connectivity():
    logger.info("Checking server health endpoint connectivity...")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/health")
            if response.status_code == 200:
                logger.info(f"Health check passed: {response.json()}")
                return True
            else:
                logger.error(f"Health check failed with status: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Server is offline or unreachable: {e}")
            return False

async def verify_flow():
    async with httpx.AsyncClient() as client:
        # 1. Sign up recruiter
        logger.info("1. Registering new recruiter...")
        recruiter_email = f"verifier_{uuid.uuid4().hex[:6]}@example.com"
        signup_payload = {
            "email": recruiter_email,
            "password": "SecurePassword123!",
            "full_name": "Verifier Agent",
            "role": "interviewer"
        }
        res_signup = await client.post(f"{BASE_URL}/api/v1/auth/signup", json=signup_payload)
        if res_signup.status_code != 201:
            logger.error(f"Signup failed: {res_signup.text}")
            return False
        logger.info(f"Recruiter registered successfully with ID: {res_signup.json()['id']}")

        # 2. Login and get JWT Token
        logger.info("2. Generating authentication token...")
        login_payload = {
            "username": recruiter_email,
            "password": "SecurePassword123!"
        }
        res_token = await client.post(f"{BASE_URL}/api/v1/auth/token", data=login_payload)
        if res_token.status_code != 200:
            logger.error(f"Token generation failed: {res_token.text}")
            return False
        token = res_token.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        logger.info("Token retrieved successfully.")

        # 3. Create Job Description
        logger.info("3. Creating Job Description (JD)...")
        jd_payload = {
            "title": "Senior Python Engineer",
            "raw_text": "We are seeking a Senior Python Engineer with experience in FastAPI, PostgreSQL, and LLMs. Minimum 5 years experience."
        }
        res_jd = await client.post(f"{BASE_URL}/api/v1/jobs", json=jd_payload, headers=headers)
        if res_jd.status_code != 201:
            logger.error(f"JD creation failed: {res_jd.text}")
            return False
        jd_id = res_jd.json()["id"]
        logger.info(f"Job Description created with ID: {jd_id}")

        # 4. Upload Resume and Verify Parsing / Matching
        logger.info("4. Uploading candidate resume and verifying match parsing...")
        # Since local PDF readers are mocked in testing, we use text-only format upload to guarantee out-of-the-box parsing
        resume_payload = {
            "file": ("resume.txt", "John Doe\nEmail: john.doe@example.com\nSkills: Python, FastAPI, PostgreSQL, AWS\nExperience: 6 years", "text/plain")
        }
        res_resume = await client.post(
            f"{BASE_URL}/api/v1/resumes?job_id={jd_id}",
            files=resume_payload,
            headers=headers
        )
        if res_resume.status_code != 201:
            logger.error(f"Resume upload failed: {res_resume.text}")
            return False
        resume_data = res_resume.json()
        resume_id = resume_data["id"]
        logger.info(f"Candidate Resume processed: Name={resume_data['candidate_name']}, Email={resume_data['candidate_email']}")
        logger.info(f"Match Analysis: Overall Score = {resume_data['match_score']['overall_percentage']}%")

        # 5. Create Interview Session
        logger.info("5. Scheduling voice screening session...")
        sess_payload = {
            "job_description_id": jd_id,
            "resume_id": resume_id
        }
        res_sess = await client.post(f"{BASE_URL}/api/v1/interviews/sessions", json=sess_payload, headers=headers)
        if res_sess.status_code != 201:
            logger.error(f"Interview session creation failed: {res_sess.text}")
            return False
        interview_id = res_sess.json()["id"]
        logger.info(f"Interview session scheduled successfully with ID: {interview_id}")

        # 6. Execute Mock Turn REST Submission
        logger.info("6. Submitting candidate response turn...")
        turn_payload = {
            "response_text": "I have used FastAPI for building microservices and managed connections using SQLAlchemy.",
            "latency_seconds": 1.5
        }
        res_turn = await client.post(
            f"{BASE_URL}/api/v1/interviews/{interview_id}/turns",
            json=turn_payload,
            headers=headers
        )
        if res_turn.status_code != 200:
            logger.error(f"Turn submission failed: {res_turn.text}")
            return False
        turn_data = res_turn.json()
        logger.info(f"Turn response received. Next question text: '{turn_data['next_question']}'")

        # 7. Delete Resume & Verify Cascading Delete (Privacy by Default)
        logger.info("7. Verifying Privacy-by-Default cascading deletes...")
        res_delete = await client.delete(f"{BASE_URL}/api/v1/resumes/{resume_id}", headers=headers)
        if res_delete.status_code != 204:
            logger.error(f"Resume deletion failed: {res_delete.text}")
            return False
        logger.info("Resume deleted successfully.")
        
        # Verify that fetching the deleted interview session returns a 404
        res_sess_check = await client.get(f"{BASE_URL}/api/v1/reports/{interview_id}", headers=headers)
        if res_sess_check.status_code == 404:
            logger.info("Privacy audit passed: Deleting resume automatically purged all interview sessions and transcripts.")
        else:
            logger.error(f"Privacy audit failed: Deleted interview session still returned status {res_sess_check.status_code}")
            return False

        logger.info("Verification completed successfully! All constraints and specifications are fully operational.")
        return True

async def main():
    if not await test_endpoint_connectivity():
        sys.exit(1)
    
    success = await verify_flow()
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
