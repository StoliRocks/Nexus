from enum import Enum


# Supported actor types
class ActorType(Enum):
    USER = "USER"
    SERVICE = "SERVICE"
    UNKNOWN = "UNKNOWN"
