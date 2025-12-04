import json
from dataclasses import dataclass

from nexus_application_interface.api.ingestion.document_ingestion_status import (
    DocumentIngestionStatus,
)

"""
The class defines the model for ingestion response payload.
"""


@dataclass
class IngestionResponse:
    reference_id: str
    session_id: str
    timestamp: str
    document_ingestion_status: list[DocumentIngestionStatus]

    def __str__(self) -> str:
        return f"IngestionResponse(referenceId={self.reference_id}, sessionId={self.session_id}, timestamp={self.timestamp}, documentIngestionStatus={self.document_ingestion_status})"

    def to_dict(self):
        return {
            "referenceId": self.reference_id,
            "sessionId": self.session_id,
            "timestamp": self.timestamp,
            "documentIngestionStatus": [
                status.to_dict() for status in self.document_ingestion_status
            ],
        }

    def to_json(self):
        return json.dumps(self.to_dict())
