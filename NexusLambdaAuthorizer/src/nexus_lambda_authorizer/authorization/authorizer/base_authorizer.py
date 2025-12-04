from abc import abstractmethod

from nexus_lambda_authorizer.authorization.model.auth_context import AuthContext


class BaseAuthorizer:

    @abstractmethod
    def is_authorized(self, auth_context: AuthContext) -> bool:
        raise NotImplementedError
