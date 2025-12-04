import { Construct } from 'constructs';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import { Duration } from 'aws-cdk-lib';
import { createLambdaFunctionInstance } from '../../utils/lambda-helper';
import { APIEndpointHandlerStackProps } from '../../props/APIEndpointHandlerStackProps';

export class MappingManagementHandler {
  public readonly mappingHandler: lambda.Function;

  constructor(scope: Construct, props: APIEndpointHandlerStackProps) {
    this.mappingHandler = createLambdaFunctionInstance(
      scope,
      'NexusMappingHandler',
      'MappingHandler',
      'NexusMappingAPIHandlerLambda',
      '1.0',
      'nexus_mapping_api_handler_lambda.handler.api_endpoint_handler',
      Duration.minutes(15),
      props.vpc,
    );
  }

  public setupMappingAPIResources(
    v1Resource: apigateway.Resource,
    tokenAuthorizer: apigateway.TokenAuthorizer,
  ): { mappingsResource: apigateway.Resource; mappingIdResource: apigateway.Resource } {
    const mappingIntegration = new apigateway.LambdaIntegration(this.mappingHandler);
    const defaultMethodOptions = {
      authorizer: tokenAuthorizer,
      authorizationType: apigateway.AuthorizationType.CUSTOM,
    };

    // POST /api/v1/batchMappings
    const batchMappingsResource = v1Resource.addResource('batchMappings');
    batchMappingsResource.addMethod('POST', mappingIntegration, defaultMethodOptions);

    // /api/v1/mappings
    const mappingsResource = v1Resource.addResource('mappings');

    // GET /api/v1/mappings?status={}&nextToken={}&maxResults={}&frameworkName={}&frameworkVersion={}&controlId={}
    mappingsResource.addMethod('GET', mappingIntegration, {
      ...defaultMethodOptions,
      requestParameters: {
        'method.request.querystring.status': false,
        'method.request.querystring.nextToken': false,
        'method.request.querystring.maxResults': false,
        'method.request.querystring.frameworkName': false,
        'method.request.querystring.frameworkVersion': false,
        'method.request.querystring.controlId': false,
      },
    });

    // /api/v1/mappings/{mappingId}
    const mappingIdResource = mappingsResource.addResource('{mappingId}');

    // GET /api/v1/mappings/{mappingId}
    mappingIdResource.addMethod('GET', mappingIntegration, {
      ...defaultMethodOptions,
      requestParameters: {
        'method.request.path.mappingId': true,
      },
    });

    // PUT /api/v1/mappings/{mappingId}
    mappingIdResource.addMethod('PUT', mappingIntegration, {
      ...defaultMethodOptions,
      requestParameters: {
        'method.request.path.mappingId': true,
      },
    });

    // PUT /api/v1/mappings/{mappingId}/archive
    const mappingArchiveResource = mappingIdResource.addResource('archive');
    mappingArchiveResource.addMethod('PUT', mappingIntegration, {
      ...defaultMethodOptions,
      requestParameters: {
        'method.request.path.mappingId': true,
      },
    });

    return { mappingsResource, mappingIdResource };
  }
}
