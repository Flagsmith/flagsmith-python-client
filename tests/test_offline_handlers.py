from pyfakefs.fake_filesystem import FakeFilesystem

from flagsmith.offline_handlers import LocalFileHandler
from flagsmith.types import SDKEvaluationContext


def test_local_file_handler(
    fs: FakeFilesystem,
    evaluation_context: SDKEvaluationContext,
    environment_json: str,
) -> None:
    # Given
    environment_document_file_path = "/some/path/environment.json"
    fs.create_file(environment_document_file_path, contents=environment_json)
    local_file_handler = LocalFileHandler(environment_document_file_path)

    # When
    result = local_file_handler.get_evaluation_context()

    # Then
    assert result == evaluation_context
