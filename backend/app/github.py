import logging
import shutil
import tarfile
import tempfile
import time
import zlib
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse

import requests


logger = logging.getLogger("repomind.github")

MAX_INDEXABLE_FILES = 2_000
MAX_INDEXABLE_BYTES = 50 * 1024 * 1024
MAX_FILE_BYTES = 500_000
# Compressed archive size. Archives larger than this are abandoned mid-download.
MAX_ARCHIVE_BYTES = 200 * 1024 * 1024
DOWNLOAD_TIMEOUT_SECONDS = 180
# (connect, read-between-bytes) timeouts for the archive request.
REQUEST_TIMEOUT = (10, 30)
# GitHub serves the default branch for the "HEAD" ref.
ARCHIVE_URL = "https://codeload.github.com/{owner}/{name}/tar.gz/HEAD"

IGNORED_DIRS = {
    ".git",
    "node_modules",
    "venv",
    ".venv",
    "__pycache__",
    ".next",
    "dist",
    "build",
    "coverage",
    ".pytest_cache",
    ".mypy_cache",
    ".idea",
    ".vscode",
}

ALLOWED_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".c", ".cpp", ".h", ".hpp",
    ".cs", ".go", ".rs", ".php", ".rb", ".swift", ".kt", ".kts", ".sql",
    ".html", ".css", ".scss", ".sass", ".vue", ".svelte", ".json", ".yaml",
    ".yml", ".toml", ".xml", ".md", ".mdx", ".txt", ".sh", ".bat", ".ps1",
}

SOURCE_LIMIT_MESSAGE = "Repository exceeds the 50 MB source indexing limit."


def _parse_github_url(repo_url: str) -> tuple[str, str]:
    parsed = urlparse(repo_url.strip())
    host = (parsed.hostname or "").lower()
    parts = [part for part in parsed.path.strip("/").split("/") if part]

    if (
        parsed.scheme != "https"
        or host not in {"github.com", "www.github.com"}
        or parsed.username
        or parsed.password
        or parsed.port
        or parsed.query
        or parsed.fragment
        or len(parts) != 2
    ):
        raise ValueError(
            "Enter a public GitHub repository URL such as "
            "https://github.com/user/repository."
        )

    owner, name = parts
    if name.lower().endswith(".git"):
        name = name[:-4]
    if not owner or not name:
        raise ValueError(
            "Enter a public GitHub repository URL such as "
            "https://github.com/user/repository."
        )
    return owner, name


def validate_github_url(repo_url: str) -> str:
    """Validate a public GitHub repository URL and return its canonical form.

    The canonical form is ``https://github.com/<owner>/<repo>`` with no
    ``www.``, trailing slash, or ``.git`` suffix, so equivalent URLs map to
    the same repository.
    """
    owner, name = _parse_github_url(repo_url)
    return f"https://github.com/{owner}/{name}"


def _is_indexable_path(parts: tuple[str, ...]) -> bool:
    return (
        bool(parts)
        and not any(part in IGNORED_DIRS for part in parts)
        and PurePosixPath(parts[-1]).suffix.lower() in ALLOWED_EXTENSIONS
    )


class _BoundedReader:
    """File-like wrapper that enforces a byte budget and a wall-clock deadline."""

    def __init__(self, raw, max_bytes: int, deadline: float):
        self._raw = raw
        self._max_bytes = max_bytes
        self._deadline = deadline
        self._read = 0

    def read(self, size: int = -1) -> bytes:
        if time.monotonic() > self._deadline:
            raise ValueError(
                "Downloading the repository took too long. Try a smaller repository."
            )
        chunk = self._raw.read(size)
        self._read += len(chunk)
        if self._read > self._max_bytes:
            raise ValueError(
                f"Repository is too large to index (download limit is "
                f"{MAX_ARCHIVE_BYTES // (1024 * 1024)} MB)."
            )
        return chunk


def _extract_source_files(archive: tarfile.TarFile, destination: Path) -> int:
    """Write only regular, indexable files from a streamed archive.

    Symlinks, hard links, and special files are never extracted, paths that
    could escape ``destination`` are ignored, and the total bytes written are
    capped, so disk use stays bounded no matter what the repository contains.
    """
    root = destination.resolve()
    written_files = 0
    written_bytes = 0

    for member in archive:
        if not member.isfile():
            continue

        member_path = PurePosixPath(member.name)
        # GitHub archives wrap everything in a single "<repo>-<sha>/" folder.
        parts = member_path.parts[1:]
        if member_path.is_absolute() or ".." in parts or not _is_indexable_path(parts):
            continue
        if member.size > MAX_FILE_BYTES:
            continue

        written_bytes += member.size
        if written_bytes > MAX_INDEXABLE_BYTES:
            raise ValueError(SOURCE_LIMIT_MESSAGE)

        target = root.joinpath(*parts)
        try:
            target.resolve().relative_to(root)
        except ValueError:
            continue

        source = archive.extractfile(member)
        if source is None:
            continue
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            with open(target, "wb") as output:
                shutil.copyfileobj(source, output)
        except OSError:
            # e.g. a file name that is not valid on this filesystem
            continue
        written_files += 1

    return written_files


def download_repository(repo_url: str) -> Path:
    """Download a public GitHub repository's default branch into a temp directory.

    Uses GitHub's tarball endpoint instead of ``git clone``: no git binary is
    needed, no history is downloaded, and only indexable source files are
    written to disk.
    """
    owner, name = _parse_github_url(repo_url)
    url = ARCHIVE_URL.format(owner=owner, name=name)
    temp_dir = Path(tempfile.mkdtemp(prefix="repomind-"))
    deadline = time.monotonic() + DOWNLOAD_TIMEOUT_SECONDS

    try:
        with requests.get(
            url,
            stream=True,
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": "RepoMind"},
        ) as response:
            if response.status_code == 404:
                raise ValueError(
                    "Repository was not found. Make sure it exists and is public."
                )
            response.raise_for_status()

            reader = _BoundedReader(response.raw, MAX_ARCHIVE_BYTES, deadline)
            with tarfile.open(fileobj=reader, mode="r|gz") as archive:
                file_count = _extract_source_files(archive, temp_dir)
    except ValueError:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise
    except requests.RequestException as error:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise ValueError(
            "Unable to download repository from GitHub. Please try again."
        ) from error
    except (tarfile.TarError, zlib.error, EOFError, OSError) as error:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise ValueError(
            "The repository archive could not be read. Please try again."
        ) from error

    logger.info("Extracted %s candidate files from %s/%s", file_count, owner, name)
    return temp_dir


def cleanup_repository(repo_path: Path):
    """Remove the temporary repository directory."""
    if repo_path.exists():
        shutil.rmtree(repo_path, ignore_errors=True)


def _is_inside(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=True).relative_to(root)
        return True
    except (OSError, ValueError):
        return False


def get_code_files(repo_path: Path):
    code_files = []
    total_size = 0
    root = repo_path.resolve()

    for path in repo_path.rglob("*"):
        relative_parts = path.relative_to(repo_path).parts

        # Never follow symlinks: a malicious repository could otherwise link
        # to server files such as /proc/self/environ or the backend .env.
        if path.is_symlink() or not _is_inside(path, root):
            continue

        if not path.is_file() or not _is_indexable_path(relative_parts):
            continue

        try:
            file_size = path.stat().st_size
        except OSError:
            continue

        # Skip very large files
        if file_size > MAX_FILE_BYTES:
            continue

        total_size += file_size
        if total_size > MAX_INDEXABLE_BYTES:
            raise ValueError(SOURCE_LIMIT_MESSAGE)

        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        # Skip empty files
        if not content.strip():
            continue

        code_files.append({
            "path": Path(*relative_parts).as_posix(),
            "content": content,
        })

        if len(code_files) > MAX_INDEXABLE_FILES:
            raise ValueError(
                "Repository exceeds the 2,000 source file indexing limit."
            )

    logger.info("Found %s indexable files", len(code_files))

    return code_files
