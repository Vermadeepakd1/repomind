from app.repository_store import (
    init_database,
    save_repository,
    get_repositories,
)


init_database()


save_repository(
    repository_id="test123",
    repo_url="https://github.com/test/example",
    repo_name="example",
    chunk_count=100,
)


repositories = get_repositories()

print("Repositories:")

for repository in repositories:
    print(repository)