from tests import _env  # noqa: F401  (must run before app imports)

import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from app.chunking import chunk_text
from app.conversation import build_retrieval_question
from app.github import validate_github_url
from app.rate_limit import _window_start, check_rate_limit
from app.repository import get_repository_id
from app.repository_store import title_from_question
from app.reranker import rerank_results


class CoreBehaviorTests(unittest.TestCase):
    def test_chunk_line_ranges_are_ordered(self):
        chunks = chunk_text("\n".join(f"line {index}" for index in range(30)), chunk_size=40, overlap=5)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(chunk["start_line"] <= chunk["end_line"] for chunk in chunks))
        self.assertEqual(chunks[0]["start_line"], 1)

    def test_follow_up_retrieval_includes_recent_context(self):
        query = build_retrieval_question(
            "Where is it created?",
            [SimpleNamespace(role="user", content="How does authentication work?")],
        )
        self.assertIn("authentication", query)
        self.assertIn("Where is it created?", query)

    def test_reranker_prefers_matching_file(self):
        result = SimpleNamespace(
            score=0.5,
            payload={"file_path": "src/authController.py", "text": "def login():", "symbols": ["login"]},
        )
        other = SimpleNamespace(
            score=0.51,
            payload={"file_path": "src/database.py", "text": "def connect():", "symbols": ["connect"]},
        )
        self.assertIs(rerank_results("Where is login implemented?", [other, result], 1)[0], result)

    def test_equivalent_urls_share_a_repository_id(self):
        variants = [
            "https://github.com/User/Repo",
            "https://github.com/User/Repo/",
            "https://github.com/user/repo.git",
            "https://www.github.com/User/Repo.git/",
        ]
        ids = {get_repository_id(validate_github_url(url), "user-1") for url in variants}
        self.assertEqual(len(ids), 1)

    def test_chat_title_is_collapsed_and_truncated(self):
        self.assertEqual(title_from_question("  How   does\nauth work? "), "How does auth work?")
        long_title = title_from_question("word " * 40)
        self.assertLessEqual(len(long_title), 60)
        self.assertTrue(long_title.endswith("..."))
        self.assertEqual(title_from_question("   "), "New chat")


class RateLimitTests(unittest.TestCase):
    def test_blocks_after_limit(self):
        with patch("app.repository_store.increment_rate_limit", side_effect=[1, 2]):
            self.assertTrue(check_rate_limit("key", limit=1))
            self.assertFalse(check_rate_limit("key", limit=1))

    def test_fails_open_when_store_is_unavailable(self):
        with patch("app.repository_store.increment_rate_limit", side_effect=RuntimeError("db down")):
            with self.assertLogs("repomind.rate_limit", level="ERROR"):
                self.assertTrue(check_rate_limit("key", limit=1))

    def test_window_start_is_aligned(self):
        now = datetime(2026, 1, 1, 12, 7, 42, tzinfo=timezone.utc)
        self.assertEqual(
            _window_start(900, now),
            datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(
            _window_start(60, now),
            datetime(2026, 1, 1, 12, 7, 0, tzinfo=timezone.utc),
        )


if __name__ == "__main__":
    unittest.main()
