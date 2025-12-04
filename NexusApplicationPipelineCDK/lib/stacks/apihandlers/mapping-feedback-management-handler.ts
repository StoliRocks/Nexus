import { Construct } from 'constructs';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import { Duration } from 'aws-cdk-lib';
import { createLambdaFunctionInstance } from '../../utils/lambda-helper';
import { APIEndpointHandlerStackProps } from '../../props/APIEndpointHandlerStackProps';

export class MappingFeedbackManagementHandler {
  public readonly mappingFeedbackHandler: lambda.Function;

  constructor(scope: Construct, props: APIEndpointHandlerStackProps) {
    this.mappingFeedbackHandler = createLambdaFunctionInstance(
      scope,
      'NexusMappingFeedbackHandler',
      'MappingFeedbackHandler',
      'NexusMappingFeedbackAPIHandlerLambda',
      '1.0',
      'nexus_mapping_feedback_api_handler_lambda.handler.api_endpoint_handler',
      Duration.minutes(15),
      props.vpc,
    );
  }

  public setupMappingFeedbackAPIResources(
    mappingIdResource: apigateway.Resource,
    tokenAuthorizer: apigateway.TokenAuthorizer,
  ): void {
    const feedbackIntegration = new apigateway.LambdaIntegration(this.mappingFeedbackHandler);
    const defaultMethodOptions = {
      authorizer: tokenAuthorizer,
      authorizationType: apigateway.AuthorizationType.CUSTOM,
    };

    // /api/v1/mappings/{mappingId}/feedbacks
    const feedbacksResource = mappingIdResource.addResource('feedbacks');

    // POST /api/v1/mappings/{mappingId}/feedbacks
    feedbacksResource.addMethod('POST', feedbackIntegration, {
      ...defaultMethodOptions,
      requestParameters: {
        'method.request.path.mappingId': true,
      },
    });

    // GET /api/v1/mappings/{mappingId}/feedbacks
    feedbacksResource.addMethod('GET', feedbackIntegration, {
      ...defaultMethodOptions,
      requestParameters: {
        'method.request.path.mappingId': true,
      },
    });

    // /api/v1/mappings/{mappingId}/feedbacks/{feedbackId}
    const feedbackIdResource = feedbacksResource.addResource('{feedbackId}');

    // PUT /api/v1/mappings/{mappingId}/feedbacks/{feedbackId}
    feedbackIdResource.addMethod('PUT', feedbackIntegration, {
      ...defaultMethodOptions,
      requestParameters: {
        'method.request.path.mappingId': true,
        'method.request.path.feedbackId': true,
      },
    });
  }
}
