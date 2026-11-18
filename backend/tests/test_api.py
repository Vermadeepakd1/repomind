from tests import _env  # noqa: F401  (must run before app imports)

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import main
from app.auth import get_current_user
from app.main import GENERIC_INDEX_ERROR, app
from app.schemas import RepositoryRequest


USER = {"user_id": "user-1", "email": "user@example.com"}
REPO_URL = "https://github.com/user/repo"


def _search_result(path="src/app.py"):
    return SimpleNamespace(
        score=0.9,
        payload={
            "file_path": path,
            "chunk_index": 0,
            "start_line": 1,
            "end_line": 3,
            "symbols": [],
            "text": "def main(): pass",
        },
    )


class ApiTestCase(unittest.TestCase):
    """The client is created without a ``with`` block, so the lifespan hook
    (which connects to the database) never runs."""

    def setUp(self):
        self.client = TestClient(app)

    def authenticate(self):
        app.dependency_overrides[get_current_user] = lambda: USER
        self.addCleanup(app.dependency_overrides.clear)


class PublicRouteTests(ApiTestCase):
    def test_health_check_is_available_without_authentication(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_repository_routes_require_authentication(self):
        for method, path in [
            ("get", "/repositories"),
            ("delete", "/repositories/abc"),
            ("delete", "/chats/abc"),
            ("get", "/repositories/index/job-1"),
        ]:
            with self.subTest(path=path):
                response = getattr(self.client, method)(path)
                self.assertEqual(response.status_code, 401)


class AuthRateLimitTests(ApiTestCase):
    def test_login_is_rate_limited_per_ip_and_per_email(self):
        keys = []

        def record(key, limit, window_seconds):
            keys.append(key)
            return True

        with patch("app.main.check_rate_limit", side_effect=record), patch(
            "app.main.get_user_by_email", return_value=None
        ):
            response = self.client.post(
                "/auth/login",
                json={"email": "Victim@Example.com", "password": "wrong-password"},
            )

        self.assertEqual(response.status_code, 401)
        self.assertIn("login:email:victim@example.com", keys)
        self.assertTrue(any(key.startswith("login:ip:") for key in keys))

    def test_login_returns_429_when_limited(self):
        with patch("app.main.check_rate_limit", return_value=False), patch(
            "app.main.get_user_by_email"
        ) as get_user:
            response = self.client.post(
                "/auth/login",
                json={"email": "user@example.com", "password": "password123"},
            )
        self.assertEqual(response.status_code, 429)
        get_user.assert_not_called()

    def test_register_returns_429_when_limited(self):
        with patch("app.main.check_rate_limit", return_value=False), patch(
            "app.main.create_user"
        ) as create_user:
            response = self.client.post(
                "/auth/register",
                json={"email": "new@example.com", "password": "password123"},
            )
        self.assertEqual(response.status_code, 429)
        create_user.assert_not_called()


class RepositoryRouteTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.authenticate()

    def test_repository_list_is_scoped_to_user(self):
        with patch("app.main.get_repositories", return_value=[]) as get_repositories:
            response = self.client.get("/repositories")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"repositories": []})
        get_repositories.assert_called_once_with("user-1")

    def test_invalid_repository_url_is_rejected(self):
        response = self.client.post(
            "/repositories/index",
            json={"repo_url": "https://gitlab.com/example/repository"},
        )
        self.assertEqual(response.status_code, 422)

    def test_index_job_lookup_is_scoped_to_user(self):
        with patch("app.main.get_job", return_value=None) as get_job:
            response = self.client.get("/repositories/index/job-1")
        self.assertEqual(response.status_code, 404)
        get_job.assert_called_once_with("job-1", "user-1")

    def test_delete_repository_removes_records_and_vectors(self):
        with patch("app.main.delete_repository", return_value=True) as delete_records, patch(
            "app.main.delete_repository_chunks"
        ) as delete_chunks:
            response = self.client.delete("/repositories/repo-1")
        self.assertEqual(response.status_code, 204)
        delete_records.assert_called_once_with("repo-1", "user-1")
        delete_chunks.assert_called_once_with("repo-1")

    def test_delete_repository_of_other_user_is_404(self):
        with patch("app.main.delete_repository", return_value=False), patch(
            "app.main.delete_repository_chunks"
        ) as delete_chunks:
            response = self.client.delete("/repositories/repo-1")
        self.assertEqual(response.status_code, 404)
        delete_chunks.assert_not_called()

    def test_delete_chat(self):
        with patch("app.main.delete_chat", return_value=True) as delete_chat:
            self.assertEqual(self.client.delete("/chats/chat-1").status_code, 204)
        delete_chat.assert_called_once_with("chat-1", "user-1")
        with patch("app.main.delete_chat", return_value=False):
            self.assertEqual(self.client.delete("/chats/chat-1").status_code, 404)


class AskTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.authenticate()
        patcher = patch("app.main.check_rate_limit", return_value=True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_unknown_repository_returns_404_without_provider_calls(self):
        with patch("app.main.get_repository", return_value=None), patch(
            "app.main.embed_text"
        ) as embed:
            response = self.client.post("/ask", json={"repo_url": REPO_URL, "question": "How?"})
        self.assertEqual(response.status_code, 404)
        embed.assert_not_called()

    def test_ask_searches_active_index_version_and_saves_exchange(self):
        repository = {"repository_id": "r", "index_version": "v2"}
        with patch("app.main.get_repository", return_value=repository), patch(
            "app.main.get_chat", return_value={"repository_id": None}
        ) as get_chat, patch("app.main.embed_text", return_value=[0.1]), patch(
            "app.main.search_vectors", return_value=[_search_result()]
        ) as search, patch("app.main.ask_gemini", return_value="It starts in main."), patch(
            "app.main.add_chat_exchange"
        ) as save_exchange, patch("app.main.get_repository_id", return_value="r"):
            get_chat.return_value = {"repository_id": "r"}
            response = self.client.post(
                "/ask",
                json={"repo_url": REPO_URL, "question": "How does it start?", "chat_id": "c1"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["answer"], "It starts in main.")
        self.assertEqual(search.call_args.kwargs["index_version"], "v2")
        save_exchange.assert_called_once()
        chat_id, question, answer, sources = save_exchange.call_args.args
        self.assertEqual((chat_id, question, answer), ("c1", "How does it start?", "It starts in main."))
        self.assertEqual(sources[0]["file"], "src/app.py")

    def test_provider_errors_are_not_leaked(self):
        repository = {"repository_id": "r", "index_version": None}
        with patch("app.main.get_repository", return_value=repository), patch(
            "app.main.embed_text", side_effect=RuntimeError("https://internal-host secret")
        ):
            with self.assertLogs("repomind.api", level="ERROR"):
                response = self.client.post("/ask", json={"repo_url": REPO_URL, "question": "How?"})
        self.assertEqual(response.status_code, 500)
        self.assertNotIn("internal-host", response.text)


class IndexJobTests(unittest.TestCase):
    """``_run_index_job`` must never destroy a working index on failure."""

    def setUp(self):
        self.request = RepositoryRequest(repo_url=REPO_URL)
        self.patches = {
            name: patch(f"app.main.{name}").start()
            for name in [
                "update_job",
                "download_repository",
                "get_code_files",
                "index_repository",
                "save_repository_files",
                "save_repository",
                "delete_repository_chunks",
                "cleanup_repository",
            ]
        }
        self.addCleanup(patch.stopall)
        self.patches["get_code_files"].return_value = [{"path": "a.py", "content": "x = 1"}]
        self.patches["index_repository"].return_value = 7

    def _final_job_update(self):
        return self.patches["update_job"].call_args_list[-1].kwargs

    def test_success_activates_new_version_then_removes_stale_chunks(self):
        main._run_index_job("job-9", self.request, "user-1")

        repository_id = self.patches["index_repository"].call_args.args[1]
        self.assertEqual(self.patches["index_repository"].call_args.args[2], "job-9")
        self.assertEqual(self.patches["save_repository"].call_args.kwargs["index_version"], "job-9")
        self.patches["delete_repository_chunks"].assert_called_once_with(
            repository_id, exclude_version="job-9"
        )
        self.assertEqual(self._final_job_update()["status"], "completed")
        self.assertEqual(self._final_job_update()["chunk_count"], 7)
        self.patches["cleanup_repository"].assert_called_once()

    def test_failure_only_removes_the_partial_new_version(self):
        self.patches["index_repository"].side_effect = RuntimeError(
            "Qdrant at https://internal-host rejected the request"
        )

        with self.assertLogs("repomind.api", level="ERROR"):
            main._run_index_job("job-9", self.request, "user-1")

        repository_id = self.patches["index_repository"].call_args.args[1]
        self.patches["delete_repository_chunks"].assert_called_once_with(
            repository_id, index_version="job-9"
        )
        self.patches["save_repository"].assert_not_called()
        final = self._final_job_update()
        self.assertEqual(final["status"], "failed")
        self.assertEqual(final["error"], GENERIC_INDEX_ERROR)
        self.patches["cleanup_repository"].assert_called_once()

    def test_user_facing_errors_are_preserved(self):
        self.patches["download_repository"].side_effect = ValueError("Repository is too large to index.")

        with self.assertLogs("repomind.api", level="ERROR"):
            main._run_index_job("job-9", self.request, "user-1")

        self.assertEqual(self._final_job_update()["error"], "Repository is too large to index.")
        self.patches["cleanup_repository"].assert_not_called()


if __name__ == "__main__":
    unittest.main()
