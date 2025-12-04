from nexus_application_interface.api.constants.constants import DEFAULT_INGESTION_CONFIGURATION_ID
from nexus_application_interface.api.ingestion.ingestion_request import IngestionRequest


def validate_ingestion_request(payload: IngestionRequest):
    # TODO: Only allow supplied ingestion configuration id if it exists in AppConfig
    if not payload.ingestion_configuration_id:
        payload.ingestion_configuration_id = DEFAULT_INGESTION_CONFIGURATION_ID
