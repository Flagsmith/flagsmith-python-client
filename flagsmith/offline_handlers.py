import json
from pathlib import Path
from typing import Protocol

from flag_engine.context.types import EvaluationContext

from flagsmith.mappers import map_environment_document_to_context


class OfflineHandler(Protocol):
    def get_evaluation_context(self) -> EvaluationContext: ...


class EvaluationContextLocalFileHandler:
    """
    Handler to load evaluation context from a local JSON file.
    The JSON file should contain the full evaluation context as per Flagsmith Engine's specification.

    JSON schema:
    https://raw.githubusercontent.com/Flagsmith/flagsmith/main/sdk/evaluation-context.json
    """

    def __init__(self, file_path: str) -> None:
        self.evaluation_context: EvaluationContext = json.loads(
            Path(file_path).read_text(),
        )

    def get_evaluation_context(self) -> EvaluationContext:
        return self.evaluation_context


class EnvironmentDocumentLocalFileHandler:
    """
    Handler to load evaluation context from a local JSON file containing the environment document.
    The JSON file should contain the environment document as returned by the Flagsmith API.

    API documentation:
    https://api.flagsmith.com/api/v1/docs/#/api/api_v1_environment-document_list
    """

    def __init__(self, file_path: str) -> None:
        self.evaluation_context: EvaluationContext = (
            map_environment_document_to_context(
                json.loads(
                    Path(file_path).read_text(),
                ),
            )
        )

    def get_evaluation_context(self) -> EvaluationContext:
        return self.evaluation_context


# For backward compatibility, use the old class name for
# the local file handler implementation dependant on the environment document.
LocalFileHandler = EnvironmentDocumentLocalFileHandler
