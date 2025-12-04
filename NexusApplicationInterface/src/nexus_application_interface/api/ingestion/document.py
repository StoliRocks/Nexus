import json
from dataclasses import dataclass

from nexus_application_interface.api.constants.constants import MAX_DOCUMENT_SIZE_MB
from nexus_application_interface.enum_types.document_types import DocumentType


@dataclass
class Document:
    path: str
    document_type: DocumentType
    document_size: int

    def to_dict(self):
        return {
            "path": self.path,
            "documentType": self.document_type.value,
            "documentSize": self.document_size,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Document":
        """
        Creates a Document instance from a dictionary
        Args:
            data: Dictionary containing document data with keys 'path', 'documentType', and 'documentSize'
        Returns:
            Document instance
        """
        try:
            return cls(
                path=data["path"],
                document_type=DocumentType(data["documentType"]),
                document_size=data["documentSize"],
            )
        except KeyError as e:
            raise ValueError(f"Missing required field: {e}")
        except ValueError as e:
            raise ValueError(f"Invalid data format: {e}")

    def to_json(self):
        return json.dumps(self.to_dict())

    def copy(self) -> "Document":
        """
        Creates a deep copy of the Document instance
        Returns:
            New Document instance with copied values
        """
        return Document(
            path=self.path, document_type=self.document_type, document_size=self.document_size
        )

    @classmethod
    def from_json(cls, json_str: str) -> "Document":
        """
        Creates a Document instance from a JSON string
        Args:
            json_str: JSON string containing document data
        Returns:
            Document instance
        """
        import json

        data = json.loads(json_str)
        return cls(
            path=data["path"],
            document_type=data["documentType"],
            document_size=data["documentSize"],
        )

    def __post_init__(self):
        # Validate document size
        if self.document_size is None:
            raise ValueError("Document size is required and cannot be empty")
        if not isinstance(self.document_size, int):
            raise ValueError("Document size must be an integer")
        if self.document_size <= 0:
            raise ValueError("Document size must be positive")
        if self.document_size > MAX_DOCUMENT_SIZE_MB:
            raise ValueError(
                f"Document size must be less than or equal to {MAX_DOCUMENT_SIZE_MB} MB"
            )

        # Validate document type
        if not self.document_type:
            raise ValueError("Document type is required and cannot be empty")
        if not isinstance(self.document_type, DocumentType):
            try:
                self.document_type = DocumentType(self.document_type)
            except ValueError:
                raise ValueError(f"Invalid document type: {self.document_type}")
        if self.document_type not in DocumentType:
            raise ValueError(
                f"Invalid document type: {self.document_type}. Supported types are {', '.join(doc_type.name for doc_type in DocumentType)}"
            )

        # Validate document path
        if not self.path:
            raise ValueError("Document path is required and cannot be empty")
        if not self.path.startswith("s3://"):
            raise ValueError("Document path must be an S3 URI")
