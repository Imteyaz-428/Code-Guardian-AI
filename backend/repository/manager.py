from pathlib import Path


class RepositoryManager:

    def __init__(self, repository_path: str):
        self.repository_path = Path(repository_path)

    def validate_repository(self) -> bool:
        """
        Check whether the given path exists and is a directory.
        """
        return self.repository_path.exists() and self.repository_path.is_dir()

    def get_python_files(self) -> list[Path]:
        """
        Find all Python files inside the repository.
        """
        if not self.validate_repository():
            raise ValueError(
                f"Invalid repository path: {self.repository_path}"
            )

        return list(self.repository_path.rglob("*.py"))