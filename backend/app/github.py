from git import Repo, GitCommandError
from pathlib import Path
import tempfile
import shutil


def clone_repository(repo_url: str):
    """
    Clone a Git repository into a temporary directory.
    """

    if not repo_url.startswith(
        ("https://github.com/", "https://www.github.com/")
    ):
        raise ValueError(
            "Only public GitHub repository URLs are supported."
        )

    temp_dir = tempfile.mkdtemp()

    try:
        Repo.clone_from(
            repo_url,
            temp_dir
        )

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

    ignored = {
        ".git",
        "node_modules",
        "venv",
        "__pycache__",
        ".next",
        "dist",
        "build",
    }

    for path in repo_path.rglob("*"):

        if not path.is_file():
            continue

        if any(
            part in ignored
            for part in path.parts
        ):
            continue

        try:
            content = path.read_text(
                encoding="utf-8"
            )

            code_files.append({
                "path": str(
                    path.relative_to(repo_path)
                ),
                "content": content,
            })

        except (
            UnicodeDecodeError,
            OSError,
        ):
            continue

    return code_files