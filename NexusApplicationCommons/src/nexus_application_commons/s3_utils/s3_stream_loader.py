import logging
from datetime import datetime
from typing import Dict, List

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class S3StreamLoader:
    """Lambda-optimized document loader for S3 text files"""

    def __init__(self):
        self.s3_client = boto3.client("s3")

    def _get_s3_object(self, bucket: str, key: str) -> Dict:
        """Get a file from S3"""
        try:
            response = self.s3_client.get_object(Bucket=bucket, Key=key)
            return response
        except ClientError as e:
            logger.error(f"Error getting S3 object: {str(e)}")
            raise

    def _load_text_content(self, response: Dict, metadata: Dict) -> Dict:
        """Load text content from S3 object"""
        try:
            content = response["Body"].read().decode("utf-8")
            return {"content": content, "metadata": metadata}
        except Exception as e:
            logger.error(f"Error processing text content: {str(e)}")
            raise

    def _list_s3_objects(self, bucket: str, prefix: str) -> List[str]:
        """List objects in S3 bucket with given prefix"""
        try:
            response = self.s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
            return [
                obj["Key"] for obj in response.get("Contents", []) if obj["Key"].endswith(".txt")
            ]
        except ClientError as e:
            logger.error(f"Error listing S3 objects: {str(e)}")
            raise

    def process_s3_files(self, bucket: str, key: str, is_directory: bool = False) -> List[Dict]:
        """Process text file(s) from S3"""
        logger.info(f"Processing s3://{bucket}/{key}")

        if is_directory:
            keys = self._list_s3_objects(bucket, key)
        else:
            keys = [key]

        documents = []

        for file_key in keys:
            try:
                s3_object = self._get_s3_object(bucket, file_key)
                metadata = {
                    "source_type": "s3",
                    "source_bucket": bucket,
                    "source_key": file_key,
                    "last_modified": s3_object["LastModified"].isoformat(),
                    "size": s3_object["ContentLength"],
                    "processed_at": datetime.utcnow().isoformat(),
                }
                document = self._load_text_content(s3_object, metadata)
                documents.append(document)
            except Exception as e:
                logger.error(f"Error processing file {file_key}: {str(e)}")

        return documents
