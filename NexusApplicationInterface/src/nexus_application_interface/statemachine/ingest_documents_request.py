import json
from dataclasses import dataclass

from nexus_application_interface.api.ingestion.ingestion_response import IngestionResponse
from nexus_application_interface.statemachine.ingest_document import IngestDocument


@dataclass
class IngestDocumentsRequest:
    documents_to_ingest: list[IngestDocument]

    @classmethod
    def from_dict(cls, data: dict) -> "IngestDocumentsRequest":
        return cls([IngestDocument.from_dict(doc) for doc in data.get("documents_to_ingest", [])])

    def to_dict(self):
        return {"documents_to_ingest": [doc.to_dict() for doc in self.documents_to_ingest]}

    def to_json(self):
        return json.dumps(self.to_dict())

    @classmethod
    def from_ingestion_response(
        cls, ingestion_configuration_id: str, response: IngestionResponse
    ) -> "IngestDocumentsRequest":
        ingest_document_status_list = []
        for document_ingestion_status in response.document_ingestion_status:
            ingest_document_status_list.append(
                IngestDocument.from_document_ingestion_status(
                    response.reference_id,
                    ingestion_configuration_id,
                    response.session_id,
                    response.timestamp,
                    document_ingestion_status,
                )
            )

        return cls(ingest_document_status_list)
