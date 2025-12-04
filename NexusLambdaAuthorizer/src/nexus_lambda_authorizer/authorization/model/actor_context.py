from dataclasses import dataclass
from typing import Optional

from nexus_lambda_authorizer.authorization.model.actor_type import ActorType


@dataclass
class ActorContext:
    actorId: Optional[str] = ""
    actorType: Optional[ActorType] = ActorType.UNKNOWN

    def to_dict(self) -> dict:
        """
        Convert ActorContext instance to dictionary representation.

        Returns:
            dict: Dictionary containing the ActorContext data
        """
        return {
            "actorId": self.actorId if self.actorId else None,
            "actorType": self.actorType.value if self.actorType else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ActorContext":
        """
        Create an ActorContext instance from a dictionary.

        Args:
            data (dict): Dictionary containing ActorContext data

        Returns:
            ActorContext: New instance of ActorContext
        """
        actor_id = data.get("actorId")
        actor_type_value = data.get("actorType")
        actor_type = (
            ActorType(actor_type_value) if actor_type_value is not None else ActorType.UNKNOWN
        )

        return cls(actorId=actor_id, actorType=actor_type)
