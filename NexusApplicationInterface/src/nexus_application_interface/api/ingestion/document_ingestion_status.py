import json
from dataclasses import dataclass

from nexus_application_interface.api.ingestion.control import Control
from nexus_application_interface.enum_types.ingestion_status import IngestionStatus


@dataclass
class DocumentIngestionStatus:
    status: IngestionStatus
    message: str
    document: Control

    def __str__(self):
        return f"status: {self.status}, message: {self.message}, document: {self.document}"

    def to_dict(self):
        return {
            "status": self.status.value,
            "message": self.message,
            "document": self.document.to_dict(),
        }

    def to_json(self):
        return json.dumps(self.to_dict())
