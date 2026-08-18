from app.github import clone_repository, get_code_files, cleanup_repository


repo_url = "https://github.com/Vermadeepakd1/this-repository-does-not-exist"

repo_path = clone_repository(repo_url)

print("Repository cloned:")
print(repo_path)

files = get_code_files(repo_path)

print("Files found:", len(files))

for file in files[:5]:
    print(file["path"])

cleanup_repository(repo_path)

print("Temporary repository cleaned up.")