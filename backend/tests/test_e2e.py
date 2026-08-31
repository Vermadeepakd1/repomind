import os
import time
import unittest
from uuid import uuid4


RUN_E2E = os.getenv("REPO_MIND_RUN_E2E") == "1"
TEST_REPO_URL = os.getenv("REPO_MIND_E2E_REPO_URL")


@unittest.skipUnless(
    RUN_E2E and TEST_REPO_URL,
    "Set REPO_MIND_RUN_E2E=1 and REPO_MIND_E2E_REPO_URL to run the live flow.",
)
class RepositoryFlowE2ETest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        from app.main import app

        cls.client = TestClient(app)
        email = f"e2e-{uuid4()}@example.com"
        response = cls.client.post(
            "/auth/register",
            json={"email": email, "password": "test-password-123"},
        )
        if response.status_code != 200:
            raise RuntimeError(f"Could not create E2E user: {response.text}")
        cls.headers = {"Authorization": f"Bearer {response.json()['token']}"}

    def test_index_and_ask_flow(self):
        index_response = self.client.post(
            "/repositories/index",
            json={"repo_url": TEST_REPO_URL},
            headers=self.headers,
        )
        self.assertEqual(index_response.status_code, 202)
        job_id = index_response.json()["job_id"]

        deadline = time.monotonic() + 600
        while time.monotonic() < deadline:
            status_response = self.client.get(
                f"/repositories/index/{job_id}", headers=self.headers
            )
            self.assertEqual(status_response.status_code, 200)
            job = status_response.json()
            if job["status"] == "failed":
                self.fail(job.get("error") or "Indexing failed")
            if job["status"] == "completed":
                break
            time.sleep(2)
        else:
            self.fail("Indexing did not complete within ten minutes")

        ask_response = self.client.post(
            "/ask",
            json={"repo_url": TEST_REPO_URL, "question": "How does this project start?"},
            headers=self.headers,
        )
        self.assertEqual(ask_response.status_code, 200)
        self.assertTrue(ask_response.json().get("answer"))


if __name__ == "__main__":
    unittest.main()
