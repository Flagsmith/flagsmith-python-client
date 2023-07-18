import json
from abc import ABC, abstractmethod

from flag_engine.environments.builders import build_environment_model
from flag_engine.environments.models import EnvironmentModel


class BaseOfflineModeHandler(ABC):
    @abstractmethod
    def get_environment(self) -> EnvironmentModel:
        raise NotImplementedError()


class LocalFileHandler(BaseOfflineModeHandler):
    def __init__(self, environment_document_path: str):
        with open(environment_document_path) as environment_document:
            self.environment = build_environment_model(
                json.loads(environment_document.read())
            )

    def get_environment(self) -> EnvironmentModel:
        return self.environment
