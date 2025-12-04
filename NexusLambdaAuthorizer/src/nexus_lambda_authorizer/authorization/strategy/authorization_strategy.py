from abc import abstractmethod

from nexus_lambda_authorizer.authorization.model.auth_context import AuthContext


class AuthorizationStrategy:
    @abstractmethod
    def authorize(self, auth_context: AuthContext):
        raise NotImplementedError
