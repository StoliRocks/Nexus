import pytest

from nexus_application_interface.api.constants.constants import MAX_DOCUMENT_SIZE_MB
from nexus_application_interface.api.ingestion.document import Document
from nexus_application_interface.enum_types.document_types import DocumentType


class TestDocument:

    def test_invalid_document(self):
        with pytest.raises(ValueError, match="Document size must be an integer"):
            Document(
                path="s3://test-bucket/test-file.txt",
                document_type=DocumentType.PDF,
                document_size="not_an_int",
            )

        with pytest.raises(ValueError, match="Document size must be positive"):
            Document(
                path="s3://test-bucket/test-file.txt",
                document_type=DocumentType.PDF,
                document_size=0,
            )

        with pytest.raises(
            ValueError,
            match=f"Document size must be less than or equal to {MAX_DOCUMENT_SIZE_MB} MB",
        ):
            Document(
                path="s3://test-bucket/test-file.txt",
                document_type=DocumentType.PDF,
                document_size=MAX_DOCUMENT_SIZE_MB + 1,
            )

        with pytest.raises(ValueError, match="Document type is required and cannot be empty"):
            Document(path="s3://test-bucket/test-file.txt", document_type="", document_size=100)

        with pytest.raises(ValueError, match="Invalid document type"):
            Document(
                path="s3://test-bucket/test-file.txt",
                document_type="INVALID_TYPE",
                document_size=100,
            )

        with pytest.raises(ValueError, match="Document path is required and cannot be empty"):
            Document(path="", document_type=DocumentType.PDF, document_size=100)

        with pytest.raises(ValueError, match="Document path must be an S3 URI"):
            Document(
                path="/local/path/test-file.txt", document_type=DocumentType.PDF, document_size=100
            )
