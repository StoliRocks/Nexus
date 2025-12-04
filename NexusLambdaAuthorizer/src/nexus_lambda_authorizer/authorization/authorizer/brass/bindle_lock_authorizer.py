import functools

from retrying import retry

from nexus_lambda_authorizer.authorization.authorizer.base_authorizer import BaseAuthorizer
from nexus_lambda_authorizer.authorization.exception.bad_request_exception import (
    BadRequestException,
)
from nexus_lambda_authorizer.authorization.model.auth_context import AuthContext
from nexus_lambda_authorizer.authorization.util.client_retry import is_throttled_or_timed_out
from nexus_lambda_authorizer.gateway.brass_gateway import BrassGateway


class BindleLockAuthorizer(BaseAuthorizer):
    def __init__(self, brass_gateway: BrassGateway):
        self.brass_gateway = brass_gateway

    @retry(
        retry_on_exception=functools.partial(is_throttled_or_timed_out, func_name="is_authorized"),
        stop_max_attempt_number=5,
        wait_exponential_multiplier=1000,
        wait_exponential_max=10000,
    )
    def is_authorized(self, authorization_context: AuthContext):
        if not authorization_context.actorContext:
            raise BadRequestException("actorContext is required for authorization")

        if not authorization_context.resourceContext:
            raise BadRequestException("resourceContext is required for authorization")

        actor_id = authorization_context.actorContext.actorId
        resource_id = authorization_context.resourceContext.resourceId

        if not isinstance(actor_id, str):
            raise BadRequestException("actorId must be a string")

        if not isinstance(resource_id, str):
            raise BadRequestException("resourceId must be a string")

        return self.brass_gateway.can_unlock_bindle(
            actor_id,
            resource_id,
        ).authorized
