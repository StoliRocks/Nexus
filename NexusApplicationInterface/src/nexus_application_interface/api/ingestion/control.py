import json
from dataclasses import dataclass
from typing import Any, Dict, Optional

from nexus_application_interface.enum_types.document_types import DocumentFrameworkType


@dataclass
class Framework:
    name: str
    version: str
    type: DocumentFrameworkType
    id: Optional[str] = None

    def __post_init__(self):
        # Generate ID by combining name and version in lowercase, separated by hyphen
        self.id = f"{self.name.lower()}"
        if self.version and self.version != "":
            self.id += f"-{self.version.lower()}"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Framework":
        """
        Creates a Framework instance from a dictionary
        Args:
            data: Dictionary containing framework data with keys 'name', 'version', and 'type'
        Returns:
            Framework instance
        """
        try:
            return cls(
                name=data["name"], version=data["version"], type=DocumentFrameworkType(data["type"])
            )
        except KeyError as e:
            raise ValueError(f"Missing required field: {e}")
        except ValueError as e:
            raise ValueError(f"Invalid data format: {e}")

    def to_dict(self):
        return {
            "name": self.name,
            "version": self.version,
            "type": self.type.value,
        }


@dataclass
class Control:
    bucket: str
    control_id: str
    framework: Framework

    def to_dict(self):
        return {
            "bucket": self.bucket,
            "controlId": self.control_id,
            "framework": self.framework.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Control":
        """
        Creates a Document instance from a dictionary
        Args:
            data: Dictionary containing document data with keys 'bucket', 'controlId', 'documentType',
            'documentSize', 'controlType', and 'framework'
        Returns:
            Document instance
        """
        try:
            return cls(
                bucket=data["bucket"],
                control_id=data["controlId"],
                framework=Framework.from_dict(data["framework"]),
            )
        except KeyError as e:
            raise ValueError(f"Missing required field: {e}")
        except ValueError as e:
            raise ValueError(f"Invalid data format: {e}")

    def to_json(self):
        return json.dumps(self.to_dict())

    def copy(self) -> "Control":
        """
        Creates a deep copy of the Document instance
        Returns:
            New Document instance with copied values
        """
        return Control(
            bucket=self.bucket,
            control_id=self.control_id,
            framework=self.framework,
        )

    @classmethod
    def from_json(cls, json_str: str) -> "Control":
        """
        Creates a Document instance from a JSON string
        Args:
            json_str: JSON string containing document data
        Returns:
            Document instance
        """
        import json

        data = json.loads(json_str)
        return cls(
            bucket=data["bucket"],
            control_id=data["controlId"],
            framework=data["framework"],
        )

    @property
    def s3_uri(self) -> str:
        """
        Constructs and returns the S3 URI for the document
        Returns:
            S3 URI string in the format s3://{bucket}/{control_id}
        """
        return f"s3://{self.bucket}/{self.control_id}"

    def _validate_bucket_and_control_id(self):
        """Validate bucket and control_id constraints"""
        if not self.bucket:
            raise ValueError("Bucket name is required and cannot be empty")
        if not self.control_id:
            raise ValueError("Control ID is required and cannot be empty")

    def _validate_framework(self):
        """Validate framework constraints"""
        if not self.framework:
            raise ValueError("Framework is required and cannot be empty")
        if not isinstance(self.framework, Framework):
            raise ValueError("Framework must be an instance of Framework class")

    def __post_init__(self):
        """Validate all document attributes after initialization"""
        self._validate_bucket_and_control_id()
        self._validate_framework()
