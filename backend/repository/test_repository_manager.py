from backend.repository.manager import RepositoryManager


manager = RepositoryManager("./sample_project")

print("Repository valid:", manager.validate_repository())

files = manager.get_python_files()

print("\nPython files found:")

for file in files:
    print(file)