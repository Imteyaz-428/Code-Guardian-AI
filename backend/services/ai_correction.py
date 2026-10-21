from dataclasses import dataclass
from typing import Protocol


@dataclass
class CorrectionInput:
    file_path: str
    function_name: str
    original_code: str
    finding: str
    severity: str
    explanation: str
    previous_attempt: str | None = None
    failure_feedback: str | None = None


@dataclass
class CorrectionOutput:
    corrected_code: str
    explanation: str
    


class CorrectionProvider(Protocol):
    def generate_correction(
        self,
        request: CorrectionInput,
    ) -> CorrectionOutput:
        ...


class AICorrectionService:
    """
    Coordinates AI-based code correction.

    The provider is injected so that we can integrate an AI service
    later without changing the existing analysis pipeline.
    """

    def __init__(self, provider: CorrectionProvider):
        self.provider = provider

    def correct(
        self,
        request: CorrectionInput,
    ) -> CorrectionOutput:

        if not request.original_code.strip():
            raise ValueError("Original code cannot be empty.")

        if not request.finding.strip():
            raise ValueError("A code finding is required.")

        if not request.function_name.strip():
            raise ValueError("Function name cannot be empty.")

        result = self.provider.generate_correction(request)

        if not result.corrected_code.strip():
            raise ValueError("The correction provider returned empty code.")

        return result