import json
from dataclasses import dataclass

from nexus_application_interface.statemachine.control.ingest_control import IngestControl


@dataclass
class FailedControlsSQSMessage:
    timestamp: str
    failed_controls: list[IngestControl]
    successful_controls: list[IngestControl]
    total_processed: int

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "failed_controls": [doc.to_dict() for doc in self.failed_controls],
            "successful_controls": [doc.to_dict() for doc in self.successful_controls],
            "total_processed": self.total_processed,
        }

    def to_json(self):
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict) -> "FailedControlsSQSMessage":
        try:
            return cls(
                timestamp=data["timestamp"],
                failed_controls=[IngestControl.from_dict(doc) for doc in data["failed_controls"]],
                successful_controls=[
                    IngestControl.from_dict(doc) for doc in data["successful_controls"]
                ],
                total_processed=data["total_processed"],
            )
        except KeyError as e:
            raise KeyError(f"Missing required field: {e}")
        except Exception as e:
            raise ValueError(f"Error creating FailedControlsSQSMessage: {str(e)}")
