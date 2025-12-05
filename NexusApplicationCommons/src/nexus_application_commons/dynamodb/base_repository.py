"""Base DynamoDB repository with common patterns."""

import logging
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

import boto3
from boto3.dynamodb.conditions import Key
from boto3.dynamodb.types import TypeSerializer
from botocore.exceptions import ClientError
from pydantic import BaseModel

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class BaseRepository(Generic[T]):
    """
    Base repository class for DynamoDB operations.

    Provides common CRUD and query patterns for Pydantic models.

    Usage:
        class ControlRepository(BaseRepository[Control]):
            def __init__(self):
                super().__init__(
                    table_name="framework-controls",
                    model_class=Control,
                    partition_key="frameworkKey",
                    sort_key="controlKey"
                )
    """

    def __init__(
        self,
        table_name: str,
        model_class: Type[T],
        partition_key: str,
        sort_key: Optional[str] = None,
        dynamodb_resource=None,
        dynamodb_client=None,
    ):
        """
        Initialize the repository.

        Args:
            table_name: Name of the DynamoDB table
            model_class: Pydantic model class for serialization/deserialization
            partition_key: Name of the partition key attribute
            sort_key: Name of the sort key attribute (optional)
            dynamodb_resource: Optional boto3 DynamoDB resource
            dynamodb_client: Optional boto3 DynamoDB client (for transactions)
        """
        self.table_name = table_name
        self.model_class = model_class
        self.partition_key = partition_key
        self.sort_key = sort_key

        if dynamodb_resource is None:
            session = boto3.Session()
            self.dynamodb = session.resource("dynamodb")
            self.dynamodb_client = session.client("dynamodb")
        else:
            self.dynamodb = dynamodb_resource
            self.dynamodb_client = dynamodb_client or boto3.client("dynamodb")

        self.table = self.dynamodb.Table(table_name)
        self._serializer = TypeSerializer()
        logger.info(f"Initialized {self.__class__.__name__} with table: {table_name}")

    def get_item(self, pk_value: str, sk_value: Optional[str] = None) -> Optional[T]:
        """
        Get a single item by primary key.

        Args:
            pk_value: Partition key value
            sk_value: Sort key value (required if table has sort key)

        Returns:
            Model instance if found, None otherwise
        """
        try:
            key = {self.partition_key: pk_value}
            if self.sort_key and sk_value:
                key[self.sort_key] = sk_value

            response = self.table.get_item(Key=key)

            if "Item" not in response:
                return None

            return self.model_class.model_validate(response["Item"])

        except ClientError as e:
            logger.error(f"Error getting item from {self.table_name}: {e}")
            raise

    def put_item(self, item: T) -> None:
        """
        Create or update an item.

        Args:
            item: Model instance to save
        """
        try:
            data = item.model_dump(by_alias=True, exclude_none=True)
            self.table.put_item(Item=data)
            logger.debug(f"Saved item to {self.table_name}")

        except ClientError as e:
            logger.error(f"Error saving item to {self.table_name}: {e}")
            raise

    def put_item_idempotent(self, item: T) -> bool:
        """
        Create an item only if it doesn't exist (idempotent create).

        Uses a conditional expression to prevent overwriting existing items.
        This is useful for critical operations where duplicate prevention is required.

        Args:
            item: Model instance to save

        Returns:
            True if item was created, False if item already exists

        Raises:
            ClientError: For errors other than ConditionalCheckFailedException
        """
        try:
            data = item.model_dump(by_alias=True, exclude_none=True)
            self.table.put_item(
                Item=data,
                ConditionExpression=f"attribute_not_exists({self.partition_key})",
            )
            logger.debug(f"Created new item in {self.table_name} (idempotent)")
            return True

        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                logger.debug(f"Item already exists in {self.table_name}, skipping create")
                return False
            logger.error(f"Error saving item to {self.table_name}: {e}")
            raise

    def delete_item(self, pk_value: str, sk_value: Optional[str] = None) -> None:
        """
        Delete an item by primary key.

        Args:
            pk_value: Partition key value
            sk_value: Sort key value (required if table has sort key)
        """
        try:
            key = {self.partition_key: pk_value}
            if self.sort_key and sk_value:
                key[self.sort_key] = sk_value

            self.table.delete_item(Key=key)
            logger.debug(f"Deleted item from {self.table_name}")

        except ClientError as e:
            logger.error(f"Error deleting item from {self.table_name}: {e}")
            raise

    def query(
        self,
        pk_value: str,
        sk_condition: Optional[Any] = None,
        index_name: Optional[str] = None,
        limit: Optional[int] = None,
        scan_forward: bool = True,
        filter_expression: Optional[Any] = None,
    ) -> List[T]:
        """
        Query items by partition key with optional sort key condition.

        Args:
            pk_value: Partition key value
            sk_condition: Optional sort key condition (e.g., Key('sk').begins_with('prefix'))
            index_name: Optional GSI name to query
            limit: Maximum number of items to return
            scan_forward: True for ascending, False for descending order
            filter_expression: Optional filter expression

        Returns:
            List of model instances
        """
        try:
            pk_attr = self.partition_key
            if index_name:
                # For GSI, caller should provide the correct PK attribute
                pass

            key_condition = Key(pk_attr).eq(pk_value)
            if sk_condition:
                key_condition = key_condition & sk_condition

            query_params: Dict[str, Any] = {
                "KeyConditionExpression": key_condition,
                "ScanIndexForward": scan_forward,
            }

            if index_name:
                query_params["IndexName"] = index_name
            if limit:
                query_params["Limit"] = limit
            if filter_expression:
                query_params["FilterExpression"] = filter_expression

            items: List[T] = []
            response = self.table.query(**query_params)
            items.extend([self.model_class.model_validate(item) for item in response["Items"]])

            # Handle pagination
            while "LastEvaluatedKey" in response and (limit is None or len(items) < limit):
                query_params["ExclusiveStartKey"] = response["LastEvaluatedKey"]
                response = self.table.query(**query_params)
                items.extend([self.model_class.model_validate(item) for item in response["Items"]])

            return items

        except ClientError as e:
            logger.error(f"Error querying {self.table_name}: {e}")
            raise

    def query_by_gsi(
        self,
        index_name: str,
        pk_attr: str,
        pk_value: str,
        sk_attr: Optional[str] = None,
        sk_condition: Optional[Any] = None,
        limit: Optional[int] = None,
    ) -> List[T]:
        """
        Query items using a Global Secondary Index.

        Args:
            index_name: Name of the GSI
            pk_attr: Partition key attribute name for the GSI
            pk_value: Partition key value
            sk_attr: Sort key attribute name for the GSI (optional)
            sk_condition: Sort key condition (optional)
            limit: Maximum number of items to return

        Returns:
            List of model instances
        """
        try:
            key_condition = Key(pk_attr).eq(pk_value)
            if sk_condition:
                key_condition = key_condition & sk_condition

            query_params: Dict[str, Any] = {
                "IndexName": index_name,
                "KeyConditionExpression": key_condition,
            }

            if limit:
                query_params["Limit"] = limit

            items: List[T] = []
            response = self.table.query(**query_params)
            items.extend([self.model_class.model_validate(item) for item in response["Items"]])

            while "LastEvaluatedKey" in response and (limit is None or len(items) < limit):
                query_params["ExclusiveStartKey"] = response["LastEvaluatedKey"]
                response = self.table.query(**query_params)
                items.extend([self.model_class.model_validate(item) for item in response["Items"]])

            return items

        except ClientError as e:
            logger.error(f"Error querying GSI {index_name} on {self.table_name}: {e}")
            raise

    def batch_get(self, keys: List[Dict[str, str]]) -> List[T]:
        """
        Batch get multiple items.

        Args:
            keys: List of key dictionaries

        Returns:
            List of model instances
        """
        try:
            items: List[T] = []

            # DynamoDB batch_get_item has a limit of 100 items
            for i in range(0, len(keys), 100):
                batch_keys = keys[i : i + 100]
                response = self.dynamodb.batch_get_item(
                    RequestItems={self.table_name: {"Keys": batch_keys}}
                )

                if self.table_name in response.get("Responses", {}):
                    items.extend(
                        [
                            self.model_class.model_validate(item)
                            for item in response["Responses"][self.table_name]
                        ]
                    )

            return items

        except ClientError as e:
            logger.error(f"Error in batch get from {self.table_name}: {e}")
            raise

    def batch_write(self, items: List[T]) -> None:
        """
        Batch write multiple items.

        Args:
            items: List of model instances to write
        """
        try:
            with self.table.batch_writer() as batch:
                for item in items:
                    data = item.model_dump(by_alias=True, exclude_none=True)
                    batch.put_item(Item=data)

            logger.debug(f"Batch wrote {len(items)} items to {self.table_name}")

        except ClientError as e:
            logger.error(f"Error in batch write to {self.table_name}: {e}")
            raise

    def transact_write(self, operations: List[Dict[str, Any]]) -> None:
        """
        Execute transactional write operations.

        Args:
            operations: List of transaction operations (Put, Update, Delete, ConditionCheck)
        """
        try:
            self.dynamodb_client.transact_write_items(TransactItems=operations)
            logger.debug(f"Executed {len(operations)} transactional operations")

        except ClientError as e:
            logger.error(f"Error in transact write: {e}")
            raise

    def _to_dynamodb_format(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert a Python dictionary to DynamoDB format.

        Args:
            item: Python dictionary

        Returns:
            DynamoDB formatted dictionary
        """
        return {k: self._serializer.serialize(v) for k, v in item.items()}

    def scan(
        self,
        filter_expression: Optional[Any] = None,
        limit: Optional[int] = None,
    ) -> List[T]:
        """
        Scan the table. Use sparingly - prefer queries with indexes.

        Args:
            filter_expression: Optional filter expression
            limit: Maximum number of items to return

        Returns:
            List of model instances
        """
        try:
            scan_params: Dict[str, Any] = {}

            if filter_expression:
                scan_params["FilterExpression"] = filter_expression
            if limit:
                scan_params["Limit"] = limit

            items: List[T] = []
            response = self.table.scan(**scan_params)
            items.extend([self.model_class.model_validate(item) for item in response["Items"]])

            while "LastEvaluatedKey" in response and (limit is None or len(items) < limit):
                scan_params["ExclusiveStartKey"] = response["LastEvaluatedKey"]
                response = self.table.scan(**scan_params)
                items.extend([self.model_class.model_validate(item) for item in response["Items"]])

            return items

        except ClientError as e:
            logger.error(f"Error scanning {self.table_name}: {e}")
            raise
