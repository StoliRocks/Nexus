from nexus_application_interface.api.ingestion.document import Document
from nexus_application_interface.api.ingestion.ingestion_request import IngestionRequest


def document_encoder(document: IngestionRequest):
    return document.__dict__


# From JSON
def document_decoder(document_dict):
    if "documents" in document_dict:
        return IngestionRequest(
            ingestion_configuration_id=document_dict["ingestionConfigurationId"],
            session_id=document_dict["sessionId"],
            documents=[Document(**doc) for doc in document_dict["documents"]],
        )
    return document_dict
