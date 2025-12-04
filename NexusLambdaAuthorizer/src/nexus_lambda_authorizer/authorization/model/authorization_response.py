from dataclasses import dataclass
from typing import Optional

from nexus_lambda_authorizer.authorization.model.auth_context import AuthContext


@dataclass
class AuthorizationResponse:
    principalId: Optional[str] = ""
    policyDocument: Optional[dict] = None
    context: Optional[AuthContext] = None

    def to_dict(self) -> dict:
        """
        Convert AuthorizationResponse instance to a dictionary.

        Returns:
            dict: Dictionary representation of the AuthorizationResponse
        """
        return {
            "principalId": self.principalId,
            "policyDocument": self.policyDocument,
            "context": self.context.to_dict() if self.context else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AuthorizationResponse":
        """
        Create an AuthorizationResponse instance from a dictionary.

        Args:
            data (dict): Dictionary containing AuthorizationResponse data

        Returns:
            AuthorizationResponse: New instance of AuthorizationResponse
        """
        return cls(
            principalId=data.get("principalId", ""),
            policyDocument=data.get("policyDocument"),
            context=AuthContext.from_dict(data["context"]) if data.get("context") else None,
        )
