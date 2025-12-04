import json
from dataclasses import dataclass

from nexus_application_interface.api.ingestion.ingestion_response import IngestionResponse
from nexus_application_interface.statemachine.control.ingest_control import IngestControl


@dataclass
class IngestControlRequest:
    controls_to_ingest: list[IngestControl]

    @classmethod
    def from_dict(cls, data: dict) -> "IngestControlRequest":
        return cls([IngestControl.from_dict(doc) for doc in data.get("controls_to_ingest", [])])

    def to_dict(self):
        return {"controls_to_ingest": [doc.to_dict() for doc in self.controls_to_ingest]}

    def to_json(self):
        return json.dumps(self.to_dict())

    @classmethod
    def from_ingestion_response(
        cls, ingestion_configuration_id: str, response: IngestionResponse
    ) -> "IngestControlRequest":
        ingest_control_status_list = []
        for document_ingestion_status in response.document_ingestion_status:
            ingest_control_status_list.append(
                IngestControl.from_control_ingestion_status(
                    response.reference_id,
                    ingestion_configuration_id,
                    response.session_id,
                    response.timestamp,
                    document_ingestion_status,
                )
            )

        return cls(ingest_control_status_list)
