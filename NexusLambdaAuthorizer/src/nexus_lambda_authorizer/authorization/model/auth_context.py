from dataclasses import dataclass
from typing import Optional

from nexus_lambda_authorizer.authorization.model.actor_context import ActorContext
from nexus_lambda_authorizer.authorization.model.auth_type import AuthType
from nexus_lambda_authorizer.authorization.model.resource_context import ResourceContext


@dataclass
class AuthContext:
    actorContext: Optional[ActorContext] = None
    resourceContext: Optional[ResourceContext] = None
    authType: Optional[AuthType] = AuthType.UNKNOWN
    persona: Optional[str] = None

    def to_dict(self) -> dict:
        """
        Convert AuthContext instance to a dictionary.

        Returns:
            dict: Dictionary representation of the AuthContext
        """
        return {
            "actorContext": self.actorContext.to_dict() if self.actorContext else None,
            "resourceContext": self.resourceContext.to_dict() if self.resourceContext else None,
            "authType": self.authType.value if self.authType else None,
            "persona": self.persona,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AuthContext":
        """
        Create an AuthContext instance from a dictionary.

        Args:
            data (dict): Dictionary containing AuthContext data

        Returns:
            AuthContext: New instance of AuthContext
        """
        actor_context_data = data.get("actorContext")
        resource_context_data = data.get("resourceContext")

        return cls(
            actorContext=(
                ActorContext.from_dict(actor_context_data)
                if isinstance(actor_context_data, dict)
                else None
            ),
            resourceContext=(
                ResourceContext.from_dict(resource_context_data)
                if isinstance(resource_context_data, dict)
                else None
            ),
            authType=AuthType(data.get("authType")) if data.get("authType") else AuthType.UNKNOWN,
            persona=data.get("persona"),
        )
