import unittest
from types import SimpleNamespace

from app.chunking import chunk_text
from app.conversation import build_retrieval_question
from app.github import validate_github_url
from app.rate_limit import check_rate_limit
from app.reranker import rerank_results


class CoreBehaviorTests(unittest.TestCase):
    def test_public_github_url_validation(self):
        self.assertEqual(
            validate_github_url(" https://github.com/User/Repo/ "),
            "https://github.com/User/Repo/",
        )
        with self.assertRaises(ValueError):
            validate_github_url("https://gitlab.com/user/repo")
        with self.assertRaises(ValueError):
            validate_github_url("https://github.com/user")

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

    def test_rate_limit_blocks_after_limit(self):
        key = "test-core-rate-limit"
        self.assertTrue(check_rate_limit(key, 1))
        self.assertFalse(check_rate_limit(key, 1))


if __name__ == "__main__":
    unittest.main()
