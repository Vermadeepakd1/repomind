from tests import _env  # noqa: F401  (must run before app imports)

import io
import os
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import requests

from app import github
from app.github import (
    cleanup_repository,
    download_repository,
    get_code_files,
    validate_github_url,
)


class ValidateGithubUrlTests(unittest.TestCase):
    def test_returns_canonical_url(self):
        for url in [
            " https://github.com/User/Repo/ ",
            "https://www.github.com/User/Repo",
            "https://github.com/User/Repo.git",
        ]:
            self.assertEqual(validate_github_url(url), "https://github.com/User/Repo")

    def test_rejects_non_repository_urls(self):
        for url in [
            "https://gitlab.com/user/repo",
            "https://github.com/user",
            "https://github.com/user/repo/tree/main",
            "http://github.com/user/repo",
            "https://github.com:8443/user/repo",
            "https://github.com/user/repo?x=1",
            "https://token@github.com/user/repo",
            "https://github.com/user/.git",
        ]:
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate_github_url(url)


class GetCodeFilesTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def test_collects_source_files_with_posix_paths(self):
        (self.repo / "src").mkdir()
        (self.repo / "src" / "app.py").write_text("print('hi')\n", encoding="utf-8")
        (self.repo / "node_modules").mkdir()
        (self.repo / "node_modules" / "dep.js").write_text("x = 1\n", encoding="utf-8")
        (self.repo / "image.png").write_bytes(b"\x89PNG")
        (self.repo / "empty.py").write_text("   \n", encoding="utf-8")

        files = get_code_files(self.repo)

        self.assertEqual([file["path"] for file in files], ["src/app.py"])

    def test_skips_symlinks_to_files_outside_the_repository(self):
        secret = self.root / "server.env"
        secret.write_text("JWT_SECRET=leaked\n", encoding="utf-8")
        (self.repo / "main.py").write_text("print('ok')\n", encoding="utf-8")
        try:
            os.symlink(secret, self.repo / "notes.txt")
            os.symlink(self.root, self.repo / "linked_dir", target_is_directory=True)
        except (OSError, NotImplementedError) as error:
            self.skipTest(f"Symlinks are not available here: {error}")

        files = get_code_files(self.repo)

        self.assertEqual([file["path"] for file in files], ["main.py"])
        self.assertFalse(any("leaked" in file["content"] for file in files))


def _archive(entries) -> bytes:
    """Build a GitHub-style tar.gz. ``entries`` maps names to bytes, or to a
    ``(tarfile type, linkname)`` tuple for links."""
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for name, value in entries.items():
            info = tarfile.TarInfo(name)
            if isinstance(value, tuple):
                info.type, info.linkname = value
                archive.addfile(info)
            else:
                info.size = len(value)
                archive.addfile(info, io.BytesIO(value))
    return buffer.getvalue()


def _response(status_code=200, body=b""):
    response = MagicMock(status_code=status_code)
    response.__enter__.return_value = response
    response.raw = io.BytesIO(body)
    if status_code >= 400 and status_code != 404:
        response.raise_for_status.side_effect = requests.HTTPError(str(status_code))
    return response


class DownloadRepositoryTests(unittest.TestCase):
    def _download(self, response, url="https://github.com/user/repo.git"):
        with patch("app.github.requests.get", return_value=response) as get:
            path = download_repository(url)
        self.addCleanup(cleanup_repository, path)
        return path, get

    def _files(self, path):
        return sorted(
            p.relative_to(path).as_posix() for p in path.rglob("*") if p.is_file()
        )

    def test_extracts_only_indexable_regular_files(self):
        body = _archive({
            "repo-abc123/src/app.py": b"print('hi')\n",
            "repo-abc123/README.md": b"# Repo\n",
            "repo-abc123/logo.png": b"\x89PNG",
            "repo-abc123/node_modules/dep.js": b"x = 1\n",
            "repo-abc123/big.py": b"#" * (github.MAX_FILE_BYTES + 1),
            "repo-abc123/link.txt": (tarfile.SYMTYPE, "/proc/self/environ"),
            "repo-abc123/hard.txt": (tarfile.LNKTYPE, "repo-abc123/README.md"),
            "repo-abc123/../../escape.py": b"print('escaped')\n",
        })

        path, get = self._download(_response(body=body))

        self.assertEqual(self._files(path), ["README.md", "src/app.py"])
        self.assertEqual(
            get.call_args.args[0],
            "https://codeload.github.com/user/repo/tar.gz/HEAD",
        )
        self.assertTrue(get.call_args.kwargs["stream"])
        self.assertFalse((path.parent / "escape.py").exists())

    def test_missing_repository_raises_not_found(self):
        with patch("app.github.requests.get", return_value=_response(404)):
            with self.assertRaisesRegex(ValueError, "not found"):
                download_repository("https://github.com/user/repo")

    def test_network_errors_become_value_errors(self):
        with patch(
            "app.github.requests.get",
            side_effect=requests.ConnectionError("offline"),
        ):
            with self.assertRaisesRegex(ValueError, "Unable to download"):
                download_repository("https://github.com/user/repo")
        with patch("app.github.requests.get", return_value=_response(500)):
            with self.assertRaisesRegex(ValueError, "Unable to download"):
                download_repository("https://github.com/user/repo")

    def test_oversized_archive_is_abandoned(self):
        body = _archive({"repo-abc/a.py": os.urandom(4096)})
        with patch.object(github, "MAX_ARCHIVE_BYTES", 1024), patch(
            "app.github.requests.get", return_value=_response(body=body)
        ):
            with self.assertRaisesRegex(ValueError, "too large"):
                download_repository("https://github.com/user/repo")

    def test_extracted_source_is_capped(self):
        body = _archive({
            "repo-abc/a.py": b"a" * 600,
            "repo-abc/b.py": b"b" * 600,
        })
        with patch.object(github, "MAX_INDEXABLE_BYTES", 1000), patch(
            "app.github.requests.get", return_value=_response(body=body)
        ):
            with self.assertRaisesRegex(ValueError, "50 MB"):
                download_repository("https://github.com/user/repo")

    def test_slow_download_times_out(self):
        body = _archive({"repo-abc/a.py": b"print(1)\n"})
        with patch.object(github, "DOWNLOAD_TIMEOUT_SECONDS", -1), patch(
            "app.github.requests.get", return_value=_response(body=body)
        ):
            with self.assertRaisesRegex(ValueError, "took too long"):
                download_repository("https://github.com/user/repo")

    def test_corrupt_archive_is_reported(self):
        with patch(
            "app.github.requests.get",
            return_value=_response(body=b"definitely not gzip"),
        ):
            with self.assertRaisesRegex(ValueError, "could not be read"):
                download_repository("https://github.com/user/repo")

    def test_failed_download_removes_temp_directory(self):
        created = []
        real_mkdtemp = tempfile.mkdtemp

        def tracking_mkdtemp(*args, **kwargs):
            created.append(Path(real_mkdtemp(*args, **kwargs)))
            return str(created[-1])

        with patch("app.github.tempfile.mkdtemp", side_effect=tracking_mkdtemp), patch(
            "app.github.requests.get", return_value=_response(404)
        ):
            with self.assertRaises(ValueError):
                download_repository("https://github.com/user/repo")

        self.assertFalse(created[0].exists())


if __name__ == "__main__":
    unittest.main()
