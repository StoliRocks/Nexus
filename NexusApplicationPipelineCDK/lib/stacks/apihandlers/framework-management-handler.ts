import { Construct } from 'constructs';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import { Duration } from 'aws-cdk-lib';
import { createLambdaFunctionInstance } from '../../utils/lambda-helper';
import { APIEndpointHandlerStackProps } from '../../props/APIEndpointHandlerStackProps';

export class FrameworkManagementHandler {
  public readonly frameworkHandler: lambda.Function;

  constructor(scope: Construct, props: APIEndpointHandlerStackProps) {
    this.frameworkHandler = createLambdaFunctionInstance(
      scope,
      'FrameworkAPIHandler',
      'FrameworkAPIHandler',
      'NexusFrameworkAPIHandlerLambda',
      '1.0',
      'nexus_framework_api_handler_lambda.handler.api_endpoint_handler',
      Duration.minutes(15),
      props.vpc,
    );
  }

  public setupFrameworkAPIResources(
    api: apigateway.RestApi,
    tokenAuthorizer: apigateway.TokenAuthorizer,
  ): { frameworkVersionResource: apigateway.Resource; v1Resource: apigateway.Resource } {
    const frameworkIntegration = new apigateway.LambdaIntegration(this.frameworkHandler);
    const defaultMethodOptions = {
      authorizer: tokenAuthorizer,
      authorizationType: apigateway.AuthorizationType.CUSTOM,
    };

    // /api/v1/frameworks
    const apiResource = api.root.addResource('api');
    const v1Resource = apiResource.addResource('v1');
    const frameworksResource = v1Resource.addResource('frameworks');

    // GET /api/v1/frameworks?maxResults=50&nextToken=""
    frameworksResource.addMethod('GET', frameworkIntegration, {
      ...defaultMethodOptions,
      requestParameters: {
        'method.request.querystring.maxResults': false,
        'method.request.querystring.nextToken': false,
      },
    });

    // /api/v1/frameworks/{frameworkName}
    const frameworkNameResource = frameworksResource.addResource('{frameworkName}');

    // GET /api/v1/frameworks/{frameworkName}?maxResults=50&nextToken=""
    frameworkNameResource.addMethod('GET', frameworkIntegration, {
      ...defaultMethodOptions,
      requestParameters: {
        'method.request.path.frameworkName': true,
        'method.request.querystring.maxResults': false,
        'method.request.querystring.nextToken': false,
      },
    });

    // /api/v1/frameworks/{frameworkName}/{frameworkVersion}
    const frameworkVersionResource = frameworkNameResource.addResource('{frameworkVersion}');

    // GET /api/v1/frameworks/{frameworkName}/{frameworkVersion}
    frameworkVersionResource.addMethod('GET', frameworkIntegration, {
      ...defaultMethodOptions,
      requestParameters: {
        'method.request.path.frameworkName': true,
        'method.request.path.frameworkVersion': true,
      },
    });

    // PUT /api/v1/frameworks/{frameworkName}/{frameworkVersion}
    frameworkVersionResource.addMethod('PUT', frameworkIntegration, {
      ...defaultMethodOptions,
      requestParameters: {
        'method.request.path.frameworkName': true,
        'method.request.path.frameworkVersion': true,
      },
    });

    // POST /api/v1/frameworks/{frameworkName}/{frameworkVersion}/archive
    const archiveResource = frameworkVersionResource.addResource('archive');
    archiveResource.addMethod('POST', frameworkIntegration, {
      ...defaultMethodOptions,
      requestParameters: {
        'method.request.path.frameworkName': true,
        'method.request.path.frameworkVersion': true,
      },
    });

    return { frameworkVersionResource, v1Resource };
  }
}
