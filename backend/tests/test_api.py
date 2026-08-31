import os
import unittest
from unittest.mock import patch


RUN_API_TESTS = os.getenv("REPO_MIND_RUN_API_TESTS") == "1"


@unittest.skipUnless(
    RUN_API_TESTS,
    "Set REPO_MIND_RUN_API_TESTS=1 with a configured test database to run API tests.",
)
class ApiIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        from app.main import app

        cls.client = TestClient(app)

    def test_repository_routes_require_authentication(self):
        response = self.client.get("/repositories")
        self.assertEqual(response.status_code, 401)

    def test_invalid_repository_request_is_rejected(self):
        response = self.client.post(
            "/repositories/index",
            json={"repo_url": "https://gitlab.com/example/repository"},
        )
        self.assertEqual(response.status_code, 422)

    def test_authenticated_repository_list_is_scoped(self):
        from app.main import app
        from app.auth import get_current_user

        app.dependency_overrides[get_current_user] = lambda: {
            "user_id": "integration-test-user",
            "email": "integration@example.com",
        }
        try:
            with patch("app.main.get_repositories", return_value=[]):
                response = self.client.get("/repositories")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {"repositories": []})
        finally:
            app.dependency_overrides.clear()


if __name__ == "__main__":
    unittest.main()
