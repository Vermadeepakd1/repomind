from tests import _env  # noqa: F401  (must run before app imports)

import unittest
from unittest.mock import patch

from qdrant_client import QdrantClient

from app import vector_db


def _chunk(repository_id, index_version, file_path, vector):
    return {
        "repository_id": repository_id,
        "index_version": index_version,
        "file_path": file_path,
        "chunk_index": 0,
        "start_line": 1,
        "end_line": 1,
        "text": file_path,
        "vector": vector,
    }


class IndexVersioningTests(unittest.TestCase):
    """Runs against qdrant-client's in-process engine; no server needed."""

    def setUp(self):
        self.client = QdrantClient(":memory:")
        patcher = patch("app.vector_db.get_client", return_value=self.client)
        patcher.start()
        self.addCleanup(patcher.stop)
        vector_db._collection_ready = False
        self.addCleanup(setattr, vector_db, "_collection_ready", False)

    def _files(self, repository_id, index_version=None):
        results = vector_db.search_vectors(
            [1.0, 0.0], repository_id, limit=10, index_version=index_version
        )
        return sorted(point.payload["file_path"] for point in results)

    def test_versions_coexist_and_search_uses_the_active_one(self):
        vector_db.add_chunks([
            _chunk("repo", "v1", "old.py", [1.0, 0.0]),
            _chunk("repo", "v2", "new.py", [1.0, 0.1]),
            _chunk("other", "v1", "other.py", [1.0, 0.0]),
        ])

        self.assertEqual(self._files("repo", "v1"), ["old.py"])
        self.assertEqual(self._files("repo", "v2"), ["new.py"])

    def test_same_file_in_two_versions_does_not_overwrite(self):
        vector_db.add_chunks([
            _chunk("repo", "v1", "app.py", [1.0, 0.0]),
            _chunk("repo", "v2", "app.py", [1.0, 0.0]),
        ])
        self.assertEqual(self._files("repo", "v1"), ["app.py"])
        self.assertEqual(self._files("repo", "v2"), ["app.py"])

    def test_failed_build_cleanup_keeps_previous_version(self):
        vector_db.add_chunks([
            _chunk("repo", "v1", "old.py", [1.0, 0.0]),
            _chunk("repo", "v2", "partial.py", [1.0, 0.0]),
        ])

        vector_db.delete_repository_chunks("repo", index_version="v2")

        self.assertEqual(self._files("repo"), ["old.py"])

    def test_successful_build_removes_stale_and_legacy_chunks(self):
        vector_db.add_chunks([
            _chunk("repo", None, "legacy.py", [1.0, 0.0]),
            _chunk("repo", "v1", "old.py", [1.0, 0.0]),
            _chunk("repo", "v2", "new.py", [1.0, 0.0]),
            _chunk("other", "v1", "other.py", [1.0, 0.0]),
        ])

        vector_db.delete_repository_chunks("repo", exclude_version="v2")

        self.assertEqual(self._files("repo"), ["new.py"])
        self.assertEqual(self._files("other"), ["other.py"])

    def test_delete_all_and_search_before_collection_exists(self):
        self.assertEqual(self._files("repo"), [])
        vector_db.delete_repository_chunks("repo")  # no collection yet: no error

        vector_db.add_chunks([_chunk("repo", "v1", "a.py", [1.0, 0.0])])
        vector_db.delete_repository_chunks("repo")
        self.assertEqual(self._files("repo"), [])


if __name__ == "__main__":
    unittest.main()
