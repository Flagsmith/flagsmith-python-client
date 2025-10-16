import json

import pytest
from pyfakefs.fake_filesystem import FakeFilesystem

from flagsmith.offline_handlers import LocalFileHandler


def test_local_file_handler(
    fs: FakeFilesystem,
    environment_json: str,
) -> None:
    # Given
    environment_document_file_path = "/some/path/environment.json"
    fs.create_file(environment_document_file_path, contents=environment_json)
    local_file_handler = LocalFileHandler(environment_document_file_path)

    # When
    result = local_file_handler.get_environment()

    # Then
    assert result == json.loads(environment_json)


def test_local_file_handler__invalid_contents__raises_expected(
    fs: FakeFilesystem,
) -> None:
    # Given
    environment_document_file_path = "/some/path/environment.json"
    fs.create_file(environment_document_file_path, contents="{}")

    # When & Then
    with pytest.raises(KeyError):
        LocalFileHandler(environment_document_file_path)
