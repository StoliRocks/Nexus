from dataclasses import dataclass
from typing import Optional

from nexus_lambda_authorizer.authorization.model.resource_type import ResourceType


@dataclass
class ResourceContext:
    # Unique resource identifier. example: bindleId
    resourceId: Optional[str] = ""
    # Type of the resource
    resourceType: Optional[ResourceType] = ResourceType.UNKNOWN

    def to_dict(self) -> dict:
        """
        Convert ResourceContext instance to dictionary representation.

        Returns:
            dict: Dictionary containing the ResourceContext data
        """
        return {
            "resourceId": self.resourceId,
            "resourceType": self.resourceType.value if self.resourceType else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ResourceContext":
        """
        Create a ResourceContext instance from a dictionary.

        Args:
            data (dict): Dictionary containing ResourceContext data

        Returns:
            ResourceContext: New instance of ResourceContext
        """
        resource_id = data.get("resourceId")
        resource_type_value = data.get("resourceType")
        resource_type = (
            ResourceType(resource_type_value)
            if resource_type_value is not None
            else ResourceType.UNKNOWN
        )

        return cls(resourceId=resource_id, resourceType=resource_type)
