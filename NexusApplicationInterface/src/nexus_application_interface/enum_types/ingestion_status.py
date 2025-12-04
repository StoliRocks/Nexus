from enum import Enum, unique


# Different states that the document ingestion process can be in.
@unique
class IngestionStatus(Enum):
    # Ingesting documents into the system
    INGESTING = "ingesting"
    # Uploading documents to the system
    START_UPLOAD = "start_upload"
    # Upload to S3 completed.
    SUCCESS_UPLOAD = "success_upload"
    # Document failed to upload
    FAILED_UPLOAD = "failed_upload"
    # Started document loader step
    START_DOCUMENT_LOADER = "start_document_loader"
    # Failed document loader step
    FAILED_DOCUMENT_LOADER = "failed_document_loader"
    # Successfully completed document loader step
    SUCCESS_DOCUMENT_LOADER = "success_document_loader"
    # Started the extractor step
    START_DOCUMENT_EXTRACTOR = "start_document_extractor"
    # Failed extractor step
    FAILED_DOCUMENT_EXTRACTOR = "failed_document_extractor"
    # Successfully completed extractor step
    SUCCESS_DOCUMENT_EXTRACTOR = "success_document_extractor"
    # Start csv generator step
    START_CSV_GENERATOR = "start_csv_generator"
    # Failed CSV generator step
    FAILED_CSV_GENERATOR = "failed_csv_generator"
    # Successfully completed CSV generator step
    SUCCESS_CSV_GENERATOR = "success_csv_generator"
    # Start batch load step
    START_BATCH_LOAD = "start_batch_load"
    # Failed batch load step
    FAILED_BATCH_LOAD = "failed_batch_load"
    # Successfully completed batch load step
    SUCCESS_BATCH_LOAD = "success_batch_load"
    # Retrying failed document.
    RETRYING = "retrying"
    # Successfully ingested document
    SUCCESS = "success"
    # Successfully ingested the document
    SUCCESS_INGESTING = "success_ingesting"
    # Failed to ingest the document into GraphDB
    FAILED_INGESTION = "failed_ingestion"
    # Document ingestion operation failed after retries
    FAILED = "failed"
    # Provided document is invalid type or format
    INVALID = "invalid"
    # Document ingestion completed
    COMPLETED = "completed"
