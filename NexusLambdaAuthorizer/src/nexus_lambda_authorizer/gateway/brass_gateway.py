from typing import Dict

import boto3
import six
from com.amazon.brass.coral.calls.brassservice import BrassServiceClient
from com.amazon.brass.coral.calls.isauthorizedrequest import IsAuthorizedRequest
from com.amazon.brass.coral.calls.isauthorizedresponse import IsAuthorizedResponse
from com.amazon.brass.coral.types.actorreference import ActorReference
from com.amazon.brass.coral.types.resourcereference import ResourceReference
from coral.coralrpc import new_orchestrator

# https://w.amazon.com/bin/view/BRASS/Onboarding/AWSAuth/#HInternalProdEndpoints
BRASS_ENDPOINTS: Dict[str, Dict[str, str]] = {
    "beta": {
        "us-east-1": "https://awsauth.gamma.brass.a2z.com",
    },
    "gamma": {
        "us-east-1": "https://awsauth.gamma.brass.a2z.com",
    },
    "prod": {
        "us-east-1": "https://awsauth.us-east-1.prod.brass.a2z.com",
        "eu-west-1": "https://awsauth.eu-west-1.prod.brass.a2z.com",
        "us-west-2": "https://awsauth.us-west-2.prod.brass.a2z.com",
    },
}


class BrassGateway:
    def __init__(self, stage: str, region: str):
        self.stage = stage
        self.region = region
        self.brass_client = self.__get_client()

    def __get_client(self) -> BrassServiceClient:
        # Boto Credentials
        credentials = boto3.Session().get_credentials()
        brass_endpoint = BRASS_ENDPOINTS[self.stage]

        # Coral gateway for BotoService
        return BrassServiceClient(
            new_orchestrator(
                endpoint=brass_endpoint[self.region],
                timeout=10,
                aws_region=brass_endpoint[self.region],
                aws_service="BrassService",
                signature_algorithm="v4",
                aws_access_key=six.b(credentials.access_key),
                aws_secret_key=six.b(credentials.secret_key),
                aws_security_token=six.b(credentials.token),
            )
        )

    def can_unlock_bindle(self, principal_id: str, bindle_id: str) -> IsAuthorizedResponse:
        resource = ResourceReference(
            namespace="Bindle",
            resource_type="Lock",
            resource_name=bindle_id,
        )
        actor = ActorReference(actor_type="principal", actor_id=principal_id)
        request = IsAuthorizedRequest(actor=actor, operation="Unlock", resource=resource)
        return self.brass_client.is_authorized(request)
