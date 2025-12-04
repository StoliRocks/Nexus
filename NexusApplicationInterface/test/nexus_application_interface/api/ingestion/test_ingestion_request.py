import json

import pytest

from nexus_application_interface.api.constants.constants import (
    MAX_DOCUMENT_COUNT,
    MAX_TOTAL_DOCUMENT_SIZE_MB,
)
from nexus_application_interface.api.ingestion.ingestion_request import IngestionRequest


class TestIngestionRequest:
    def test_from_json_with_valid_complete_data(self):
        # Arrange
        with open("test/resources/ingestion_document_request.json", "r") as f:
            test_json = json.load(f)

        # Act
        result = IngestionRequest.from_json(json.dumps(test_json))

        # Assert
        assert result.ingestion_configuration_id == "default"
        assert result.session_id == "sessionId"
        assert len(result.documents) == 2

    def test_from_json_with_missing_session_id_field(self):
        # Arrange
        with open("test/resources/ingestion_document_request.json", "r") as f:
            test_json = json.load(f)
        del test_json["sessionId"]

        # Act
        with pytest.raises(ValueError) as exec_info:
            IngestionRequest.from_json(json.dumps(test_json))

        assert exec_info.value.args[0] == "SessionId is missing."

    def test_from_json_with_missing_documents_field(self):
        # Arrange
        with open("test/resources/ingestion_document_request.json", "r") as f:
            test_json = json.load(f)
        del test_json["documents"]

        # Act
        with pytest.raises(ValueError) as exec_info:
            IngestionRequest.from_json(json.dumps(test_json))

        assert exec_info.value.args[0] == "No documents to ingest."

    def test_from_json_with_more_than_max_document_counts(self):
        # Arrange
        with open("test/resources/ingestion_document_request.json", "r") as f:
            test_json = json.load(f)

        test_json["documents"] = test_json["documents"] * (MAX_DOCUMENT_COUNT + 1)

        # Act
        with pytest.raises(ValueError) as exec_info:
            IngestionRequest.from_json(json.dumps(test_json))

        assert (
            exec_info.value.args[0]
            == f"Number of documents per ingestion request cannot exceed {MAX_DOCUMENT_COUNT}."
        )

    def test_from_json_combined_size_of_documents_exceed_max_limit(self):
        # Arrange
        with open("test/resources/ingestion_document_request.json", "r") as f:
            test_json = json.load(f)

        test_json["documents"] = test_json["documents"] * int(
            MAX_DOCUMENT_COUNT / len(test_json["documents"])
        )

        # Act
        with pytest.raises(ValueError) as exec_info:
            IngestionRequest.from_json(json.dumps(test_json))

        assert (
            exec_info.value.args[0]
            == f"Total size of documents per ingestion request cannot exceed {MAX_TOTAL_DOCUMENT_SIZE_MB} MB."
        )
