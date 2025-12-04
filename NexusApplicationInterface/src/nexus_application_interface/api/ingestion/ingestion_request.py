import json
from dataclasses import dataclass
from typing import Any, Dict

from nexus_application_interface.api.constants.constants import (
    MAX_DOCUMENT_COUNT,
    MAX_TOTAL_DOCUMENT_SIZE_MB,
)
from nexus_application_interface.api.ingestion.document import Document

"""
The class defines the model for ingestion request payload.
"""


@dataclass
class IngestionRequest:
    ingestion_configuration_id: str
    session_id: str
    documents: list[Document]

    @classmethod
    def from_json(cls, json_str: str) -> "IngestionRequest":
        """
        Creates an IngestionRequest instance from a JSON string
        Args:
            json_str: JSON string containing ingestion request data
        Returns:
            IngestionRequest instance
        """
        try:
            data = json.loads(json_str)

            # Validate session ID
            if "sessionId" not in data:
                raise ValueError("SessionId is missing.")

            # Validate documents
            if "documents" not in data or not data["documents"]:
                raise ValueError("No documents to ingest.")

            # Validate document count
            if len(data["documents"]) > MAX_DOCUMENT_COUNT:
                raise ValueError(
                    f"Number of documents per ingestion request cannot exceed {MAX_DOCUMENT_COUNT}."
                )

            # Create Document instances and validate total size
            documents = [Document.from_dict(doc) for doc in data["documents"]]
            total_size = sum(doc.document_size for doc in documents)

            if total_size > MAX_TOTAL_DOCUMENT_SIZE_MB:
                raise ValueError(
                    f"Total size of documents per ingestion request cannot exceed {MAX_TOTAL_DOCUMENT_SIZE_MB} MB."
                )

            return cls(
                ingestion_configuration_id=data.get("ingestionConfigurationId", "default"),
                session_id=data["sessionId"],
                documents=documents,
            )

        except json.JSONDecodeError:
            raise ValueError("Invalid JSON format")
        except KeyError as e:
            raise ValueError(f"Missing required field: {e}")

    def to_json(self) -> str:
        """
        Converts the IngestionRequest instance to a JSON string
        Returns:
            JSON string representation of the ingestion request
        """
        return json.dumps(
            {
                "ingestionConfigurationId": self.ingestion_configuration_id,
                "sessionId": self.session_id,
                "documents": [doc.to_dict() for doc in self.documents],
            }
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Converts the IngestionRequest instance to a dictionary
        Returns:
            Dictionary representation of the ingestion request
        """
        return {
            "ingestionConfigurationId": self.ingestion_configuration_id,
            "sessionId": self.session_id,
            "documents": [doc.to_dict() for doc in self.documents],
        }

    def __post_init__(self):
        if not self.session_id:
            raise ValueError("SessionId is missing.")
        if not self.documents:
            raise ValueError("No documents to ingest.")
        if len(self.documents) > MAX_DOCUMENT_COUNT:
            raise ValueError(
                f"Number of documents per ingestion request cannot exceed {MAX_DOCUMENT_COUNT}."
            )
        self.__validate_documents_size()

    def __validate_documents_size(self):
        total_document_size = 0
        for document in self.documents:
            total_document_size += document.document_size

        if total_document_size > MAX_TOTAL_DOCUMENT_SIZE_MB:
            raise ValueError(
                f"Total size of documents per ingestion request cannot exceed {MAX_TOTAL_DOCUMENT_SIZE_MB} MB."
            )
