from nexus_lambda_authorizer.authorization.authorizer.base_authorizer import BaseAuthorizer
from nexus_lambda_authorizer.authorization.exception.unauthorized_exception import (
    UnauthorizedException,
)
from nexus_lambda_authorizer.authorization.model.auth_context import AuthContext
from nexus_lambda_authorizer.authorization.strategy.authorization_strategy import (
    AuthorizationStrategy,
)


class BindleLockAuthorizationStrategy(AuthorizationStrategy):

    def __init__(self, authorizer: BaseAuthorizer):
        self.authorizer = authorizer

    def authorize(self, auth_context: AuthContext):
        if not self.authorizer.is_authorized(auth_context):
            raise UnauthorizedException("Unauthorized")
        pass
