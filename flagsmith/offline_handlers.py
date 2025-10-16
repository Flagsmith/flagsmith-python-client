import json
from pathlib import Path
from typing import Protocol

from flagsmith.api.types import EnvironmentModel
from flagsmith.mappers import map_environment_document_to_context


class OfflineHandler(Protocol):
    def get_environment(self) -> EnvironmentModel: ...


class LocalFileHandler:
    """
    Handler to load evaluation context from a local JSON file containing the environment document.
    The JSON file should contain the environment document as returned by the Flagsmith API.

    API documentation:
    https://api.flagsmith.com/api/v1/docs/#/api/api_v1_environment-document_list
    """

    def __init__(self, file_path: str) -> None:
        environment_document = json.loads(Path(file_path).read_text())
        # Make sure the document can be used for evaluation
        map_environment_document_to_context(environment_document)
        self.environment_document: EnvironmentModel = environment_document

    def get_environment(self) -> EnvironmentModel:
        return self.environment_document
