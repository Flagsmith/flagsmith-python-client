from unittest.mock import mock_open, patch

from flag_engine.environments.models import EnvironmentModel
from hamcrest import assert_that, equal_to

from flagsmith.offline_handlers import LocalFileHandler


def test_local_file_handler(environment_json: str) -> None:
    with patch("builtins.open", mock_open(read_data=environment_json)) as mock_file:
        # Given
        environment_document_file_path = "/some/path/environment.json"
        local_file_handler = LocalFileHandler(environment_document_file_path)

        # When
        environment_model = local_file_handler.get_environment()

        # Then
        assert isinstance(environment_model, EnvironmentModel)
        assert_that(
            environment_model.api_key, equal_to("B62qaMZNwfiqT76p38ggrQ")
        )  # hard coded from json file
        mock_file.assert_called_once_with(environment_document_file_path)
