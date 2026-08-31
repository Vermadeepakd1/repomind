from git import Repo, GitCommandError
from pathlib import Path
import tempfile
import shutil
from urllib.parse import urlparse


MAX_INDEXABLE_FILES = 2_000
MAX_INDEXABLE_BYTES = 50 * 1024 * 1024


def validate_github_url(repo_url: str) -> str:
    """Validate the public GitHub repository URL accepted by RepoMind."""
    value = repo_url.strip()
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower()
    parts = [part for part in parsed.path.strip("/").split("/") if part]

    if (
        parsed.scheme != "https"
        or host not in {"github.com", "www.github.com"}
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or len(parts) != 2
    ):
        raise ValueError(
            "Enter a public GitHub repository URL such as "
            "https://github.com/user/repository."
        )

    return value


def clone_repository(repo_url: str):
    """
    Clone a Git repository into a temporary directory.
    """

    repo_url = validate_github_url(repo_url)

    temp_dir = tempfile.mkdtemp()

    try:
        Repo.clone_from(repo_url, temp_dir, depth=1)

        return Path(temp_dir)

    except GitCommandError as error:
        # Remove the temporary directory if cloning fails
        shutil.rmtree(
            temp_dir,
            ignore_errors=True
        )

        raise ValueError(
            "Unable to clone repository. "
            "Make sure the GitHub URL is valid and the repository is public."
        ) from error


def cleanup_repository(repo_path: Path):
    """
    Remove the temporary cloned repository.
    """

    if repo_path.exists():
        shutil.rmtree(
            repo_path,
            ignore_errors=True
        )


def get_code_files(repo_path: Path):
    code_files = []
    total_size = 0

    ignored_dirs = {
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

    allowed_extensions = {
        ".py",
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
        ".java",
        ".c",
        ".cpp",
        ".h",
        ".hpp",
        ".cs",
        ".go",
        ".rs",
        ".php",
        ".rb",
        ".swift",
        ".kt",
        ".kts",
        ".sql",
        ".html",
        ".css",
        ".scss",
        ".sass",
        ".vue",
        ".svelte",
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".xml",
        ".md",
        ".mdx",
        ".txt",
        ".sh",
        ".bat",
        ".ps1",
    }

    max_file_size = 500_000  # 500 KB

    for path in repo_path.rglob("*"):

            if not path.is_file():
                continue

            # Ignore unwanted directories
            if any(
                part in ignored_dirs
                for part in path.relative_to(repo_path).parts
            ):
                continue

            # Only process supported file types
            if path.suffix.lower() not in allowed_extensions:
                continue

            # Skip very large files
            try:
                file_size = path.stat().st_size
                if file_size > max_file_size:
                    continue

                total_size += file_size
                if total_size > MAX_INDEXABLE_BYTES:
                    raise ValueError(
                        "Repository exceeds the 50 MB source indexing limit."
                    )
            except OSError:
                continue

            try:
                content = path.read_text(
                    encoding="utf-8"
                )
            except (
                UnicodeDecodeError,
                OSError,
            ):
                continue

            # Skip empty files
            if not content.strip():
                continue

            code_files.append({
                "path": str(
                    path.relative_to(repo_path)
                ),
                "content": content,
            })

            if len(code_files) > MAX_INDEXABLE_FILES:
                raise ValueError(
                    "Repository exceeds the 2,000 source file indexing limit."
                )

    print(
        f"Found {len(code_files)} indexable files"
    )

    return code_files
