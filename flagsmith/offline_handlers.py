from abc import ABC, abstractmethod

from flag_engine.environments.models import EnvironmentModel


class BaseOfflineHandler(ABC):
    @abstractmethod
    def get_environment(self) -> EnvironmentModel:
        raise NotImplementedError()


class LocalFileHandler(BaseOfflineHandler):
    def __init__(self, environment_document_path: str):
        with open(environment_document_path) as environment_document:
            self.environment = EnvironmentModel.model_validate_json(
                environment_document.read()
            )

    def get_environment(self) -> EnvironmentModel:
        return self.environment
