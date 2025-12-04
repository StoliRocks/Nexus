from abc import abstractmethod

from nexus_lambda_authorizer.authorization.model.actor_context import ActorContext


class CustomAuthorizer:
    @abstractmethod
    def authorize(self, principal_info: ActorContext):
        pass
