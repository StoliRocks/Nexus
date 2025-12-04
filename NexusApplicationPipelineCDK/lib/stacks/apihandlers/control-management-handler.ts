import { Construct } from 'constructs';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import { Duration } from 'aws-cdk-lib';
import { createLambdaFunctionInstance } from '../../utils/lambda-helper';
import { APIEndpointHandlerStackProps } from '../../props/APIEndpointHandlerStackProps';

export class ControlManagementHandler {
  public readonly controlHandler: lambda.Function;

  constructor(scope: Construct, props: APIEndpointHandlerStackProps) {
    this.controlHandler = createLambdaFunctionInstance(
      scope,
      'NexusControlHandler',
      'ControlHandler',
      'NexusControlAPIHandlerLambda',
      '1.0',
      'nexus_control_api_handler_lambda.handler.api_endpoint_handler',
      Duration.minutes(15),
      props.vpc,
    );
  }

  public setupControlAPIResources(
    frameworkVersionResource: apigateway.Resource,
    tokenAuthorizer: apigateway.TokenAuthorizer,
  ): void {
    const controlIntegration = new apigateway.LambdaIntegration(this.controlHandler);
    const defaultMethodOptions = {
      authorizer: tokenAuthorizer,
      authorizationType: apigateway.AuthorizationType.CUSTOM,
    };

    // POST /api/v1/frameworks/{frameworkName}/{frameworkVersion}/batchControls
    const batchControlsResource = frameworkVersionResource.addResource('batchControls');
    batchControlsResource.addMethod('POST', controlIntegration, {
      ...defaultMethodOptions,
      requestParameters: {
        'method.request.path.frameworkName': true,
        'method.request.path.frameworkVersion': true,
      },
    });

    // /api/v1/frameworks/{frameworkName}/{frameworkVersion}/controls
    const controlsResource = frameworkVersionResource.addResource('controls');

    // GET /api/v1/frameworks/{frameworkName}/{frameworkVersion}/controls?status={}&nextToken={}&maxResults={}
    controlsResource.addMethod('GET', controlIntegration, {
      ...defaultMethodOptions,
      requestParameters: {
        'method.request.path.frameworkName': true,
        'method.request.path.frameworkVersion': true,
        'method.request.querystring.status': false,
        'method.request.querystring.nextToken': false,
        'method.request.querystring.maxResults': false,
      },
    });

    // POST /api/v1/frameworks/{frameworkName}/{frameworkVersion}/controls/batchArchive
    const batchArchiveResource = controlsResource.addResource('batchArchive');
    batchArchiveResource.addMethod('POST', controlIntegration, {
      ...defaultMethodOptions,
      requestParameters: {
        'method.request.path.frameworkName': true,
        'method.request.path.frameworkVersion': true,
      },
    });

    // /api/v1/frameworks/{frameworkName}/{frameworkVersion}/controls/{controlId}
    const controlIdResource = controlsResource.addResource('{controlId}');

    // GET /api/v1/frameworks/{frameworkName}/{frameworkVersion}/controls/{controlId}
    controlIdResource.addMethod('GET', controlIntegration, {
      ...defaultMethodOptions,
      requestParameters: {
        'method.request.path.frameworkName': true,
        'method.request.path.frameworkVersion': true,
        'method.request.path.controlId': true,
      },
    });

    // PUT /api/v1/frameworks/{frameworkName}/{frameworkVersion}/controls/{controlId}
    controlIdResource.addMethod('PUT', controlIntegration, {
      ...defaultMethodOptions,
      requestParameters: {
        'method.request.path.frameworkName': true,
        'method.request.path.frameworkVersion': true,
        'method.request.path.controlId': true,
      },
    });

    // PUT /api/v1/frameworks/{frameworkName}/{frameworkVersion}/controls/{controlId}/archive
    const controlArchiveResource = controlIdResource.addResource('archive');
    controlArchiveResource.addMethod('PUT', controlIntegration, {
      ...defaultMethodOptions,
      requestParameters: {
        'method.request.path.frameworkName': true,
        'method.request.path.frameworkVersion': true,
        'method.request.path.controlId': true,
      },
    });
  }
}
