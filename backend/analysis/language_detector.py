import os


class LanguageDetector:

    LANGUAGE_EXTENSIONS = {
        ".py": "python",
        ".java": "java",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".cpp": "cpp",
        ".cc": "cpp",
        ".cxx": "cpp",
        ".h": "cpp",
        ".hpp": "cpp",
        ".c": "c",
        ".go": "go",
        ".rs": "rust",
        ".php": "php",
        ".rb": "ruby"
    }

    def detect_from_file(self, file_path):
        """
        Detect programming language from file extension.

        Returns:
            str: Language name.
            None: If language is not supported.
        """

        extension = os.path.splitext(file_path)[1].lower()

        return self.LANGUAGE_EXTENSIONS.get(extension)

    def is_supported(self, file_path):
        """
        Check whether the file belongs to a supported language.
        """

        return self.detect_from_file(file_path) is not None