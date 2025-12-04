import json
from dataclasses import dataclass

from nexus_application_interface.statemachine.ingest_document import IngestDocument


@dataclass
class FailedDocumentsSQSMessage:
    timestamp: str
    failed_documents: list[IngestDocument]
    successful_documents: list[IngestDocument]
    total_processed: int

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "failed_documents": [doc.to_dict() for doc in self.failed_documents],
            "successful_documents": [doc.to_dict() for doc in self.successful_documents],
            "total_processed": self.total_processed,
        }

    def to_json(self):
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict) -> "FailedDocumentsSQSMessage":
        try:
            return cls(
                timestamp=data["timestamp"],
                failed_documents=[
                    IngestDocument.from_dict(doc) for doc in data["failed_documents"]
                ],
                successful_documents=[
                    IngestDocument.from_dict(doc) for doc in data["successful_documents"]
                ],
                total_processed=data["total_processed"],
            )
        except KeyError as e:
            raise KeyError(f"Missing required field: {e}")
        except Exception as e:
            raise ValueError(f"Error creating FailedDocumentsSQSMessage: {str(e)}")
