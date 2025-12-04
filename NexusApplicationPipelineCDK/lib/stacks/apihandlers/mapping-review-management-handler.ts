import { Construct } from 'constructs';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import { Duration } from 'aws-cdk-lib';
import { createLambdaFunctionInstance } from '../../utils/lambda-helper';
import { APIEndpointHandlerStackProps } from '../../props/APIEndpointHandlerStackProps';

export class MappingReviewManagementHandler {
  public readonly mappingReviewHandler: lambda.Function;

  constructor(scope: Construct, props: APIEndpointHandlerStackProps) {
    this.mappingReviewHandler = createLambdaFunctionInstance(
      scope,
      'NexusMappingReviewHandler',
      'MappingReviewHandler',
      'NexusMappingReviewAPIHandlerLambda',
      '1.0',
      'nexus_mapping_review_api_handler_lambda.handler.api_endpoint_handler',
      Duration.minutes(15),
      props.vpc,
    );
  }

  public setupMappingReviewAPIResources(
    mappingIdResource: apigateway.Resource,
    tokenAuthorizer: apigateway.TokenAuthorizer,
  ): void {
    const reviewIntegration = new apigateway.LambdaIntegration(this.mappingReviewHandler);
    const defaultMethodOptions = {
      authorizer: tokenAuthorizer,
      authorizationType: apigateway.AuthorizationType.CUSTOM,
    };

    // /api/v1/mappings/{mappingId}/reviews
    const reviewsResource = mappingIdResource.addResource('reviews');

    // POST /api/v1/mappings/{mappingId}/reviews
    reviewsResource.addMethod('POST', reviewIntegration, {
      ...defaultMethodOptions,
      requestParameters: {
        'method.request.path.mappingId': true,
      },
    });

    // GET /api/v1/mappings/{mappingId}/reviews?nextToken={}&maxResults={}
    reviewsResource.addMethod('GET', reviewIntegration, {
      ...defaultMethodOptions,
      requestParameters: {
        'method.request.path.mappingId': true,
        'method.request.querystring.nextToken': false,
        'method.request.querystring.maxResults': false,
      },
    });

    // /api/v1/mappings/{mappingId}/reviews/{reviewId}
    const reviewIdResource = reviewsResource.addResource('{reviewId}');

    // PUT /api/v1/mappings/{mappingId}/reviews/{reviewId}
    reviewIdResource.addMethod('PUT', reviewIntegration, {
      ...defaultMethodOptions,
      requestParameters: {
        'method.request.path.mappingId': true,
        'method.request.path.reviewId': true,
      },
    });
  }
}
