import os
from collections import OrderedDict

import boto3
from aws_lambda_powertools import Logger

from nexus_lambda_authorizer.authorization.authorizer.brass.bindle_lock_authorizer import (
    BindleLockAuthorizer,
)
from nexus_lambda_authorizer.authorization.exception.bad_request_exception import (
    BadRequestException,
)
from nexus_lambda_authorizer.authorization.exception.unauthorized_exception import (
    UnauthorizedException,
)
from nexus_lambda_authorizer.authorization.model.actor_context import ActorContext
from nexus_lambda_authorizer.authorization.model.actor_type import ActorType
from nexus_lambda_authorizer.authorization.model.auth_context import AuthContext
from nexus_lambda_authorizer.authorization.model.auth_type import AuthType
from nexus_lambda_authorizer.authorization.model.authorization_response import AuthorizationResponse
from nexus_lambda_authorizer.authorization.model.resource_context import ResourceContext
from nexus_lambda_authorizer.authorization.model.resource_type import ResourceType
from nexus_lambda_authorizer.authorization.strategy.bindle_lock_authorization_strategy import (
    BindleLockAuthorizationStrategy,
)
from nexus_lambda_authorizer.gateway.brass_gateway import BrassGateway

logger = Logger(service="nexus_lambda_authorizer")

PERSONAS = OrderedDict()
PERSONAS["SA"] = "nexus_bindle_lock_id_sa"
PERSONAS["QA"] = "nexus_bindle_lock_id_qa"


def lambda_handler(event, context):
    try:
        method_arn = event["methodArn"]
        authorization_context: AuthContext

        # For IAM auth, AWS sends the caller's ARN in requestContext
        if "requestContext" in event and "identity" in event["requestContext"]:
            auth_type = AuthType.IAM
            principal_arn = event["requestContext"]["identity"].get("userArn") or event[
                "requestContext"
            ]["identity"].get("caller")

            if not principal_arn:
                logger.error("No IAM principal ARN found")
                raise UnauthorizedException("Unauthorized - No IAM principal ARN found")

            actor_context = validate_iam_principal(principal_arn)
        else:
            # Handle Midway token
            auth_type = AuthType.MIDWAY
            token = event.get("authorizationToken")
            if not token:
                logger.error("No Midway token provided")
                raise UnauthorizedException("Unauthorized - No Midway token provided")

            actor_context = validate_midway_token(token)

        authorization_context = AuthContext(actor_context, None, auth_type)

        persona = assumed_persona(authorization_context)
        authorization_context.persona = persona

        policy = generate_iam_policy("Allow", method_arn)

        return AuthorizationResponse(actor_context.actorId, policy, authorization_context).to_dict()

    except Exception as e:
        logger.error(f"Authorization failed: {str(e)}")
        return AuthorizationResponse(
            "unauthorized", generate_iam_policy("Deny", method_arn)
        ).to_dict()


def validate_midway_token(token) -> ActorContext:
    """
    Validate Midway token and return principal information
    """
    try:
        midway_client = boto3.client("midway")
        response = midway_client.validate_token(Token=token)

        return ActorContext(response["EmployeeId"], ActorType.USER)
    except Exception as e:
        logger.error(f"Midway validation failed: {str(e)}")
        raise UnauthorizedException("Invalid Midway token") from e


def validate_iam_principal(principal_arn) -> ActorContext:
    """
    Validate and extract information for IAM principal
    """
    if not principal_arn:
        logger.error("No IAM principal ARN found")
        raise BadRequestException("No IAM principal ARN found")

    # Determine if this is a role, user, or assumed role
    arn_parts = principal_arn.split(":")
    if len(arn_parts) < 6:
        raise BadRequestException("Invalid ARN format")

    return ActorContext(principal_arn, ActorType.SERVICE)


def assumed_persona(authorization_context: AuthContext) -> str:
    """
    Check if the principal is an assumed persona
    """
    for persona, bindle_id in PERSONAS.items():
        resource_context = ResourceContext(bindle_id, ResourceType.BINDLE)
        authorization_context.resourceContext = resource_context
        if check_brass_bindle_authorization(authorization_context):
            logger.info(
                f"Authorization Context: {authorization_context} assumed persona: {persona}"
            )
            return persona

    logger.warning(f"Authorization denied for authorization context:{authorization_context}")
    raise UnauthorizedException("Unauthorized - Not authorized to access Nexus")


def check_brass_bindle_authorization(authorization_context: AuthContext):
    """
    Check BRASS authorization for Bindle lock access
    """
    region = os.environ.get("REGION", "iad")
    stage = os.environ.get("STAGE", "beta")
    brass_gateway = BrassGateway(stage, region)
    authorizer = BindleLockAuthorizer(brass_gateway)
    return BindleLockAuthorizationStrategy(authorizer).authorize(authorization_context)


def generate_iam_policy(effect, resource):
    return {
        "Version": "2012-10-17",
        "Statement": [{"Action": "execute-api:Invoke", "Effect": effect, "Resource": resource}],
    }
