import json
from dataclasses import dataclass

from nexus_application_interface.api.ingestion.control import Control
from nexus_application_interface.api.ingestion.document_ingestion_status import (
    DocumentIngestionStatus,
)
from nexus_application_interface.enum_types.ingestion_status import IngestionStatus


@dataclass
class IngestDocument:
    reference_id: str
    ingestion_configuration_id: str
    session_id: str
    document: Control
    ingestion_status: IngestionStatus
    message: str
    timestamp: str
    retry_count: int = 0

    def to_dict(self) -> dict:
        """
        Converts the IngestDocumentStatus instance to a dictionary
        Returns:
            dict: Dictionary representation of the IngestDocumentStatus
        """
        return {
            "reference_id": self.reference_id,
            "ingestion_configuration_id": self.ingestion_configuration_id,
            "session_id": self.session_id,
            "document": self.document.to_dict(),
            "ingestion_status": self.ingestion_status.value,
            "message": self.message,
            "timestamp": self.timestamp,
            "retry_count": self.retry_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "IngestDocument":
        try:
            return cls(
                reference_id=data["reference_id"],
                ingestion_configuration_id=data["ingestion_configuration_id"],
                session_id=data["session_id"],
                document=Control.from_dict(data["document"]),
                ingestion_status=IngestionStatus(data["ingestion_status"]),
                message=data["message"],
                timestamp=data["timestamp"],
                retry_count=data.get("retry_count", 0),
            )
        except KeyError as e:
            raise ValueError(f"Missing required field: {e}")
        except ValueError as e:
            raise ValueError(f"Invalid data format: {e}")

    def to_json(self):
        return json.dumps(self.to_dict())

    """
    Transforms DocumentIngestionStatus to IngestDocumentStatus type
    """

    @classmethod
    def from_document_ingestion_status(
        cls,
        reference_id: str,
        ingestion_configuration_id: str,
        session_id: str,
        timestamp: str,
        document_ingestion_status: DocumentIngestionStatus,
    ) -> "IngestDocument":
        return cls(
            reference_id,
            ingestion_configuration_id,
            session_id,
            document_ingestion_status.document,
            document_ingestion_status.status,
            document_ingestion_status.message,
            timestamp,
            0,
        )
