import { Construct } from 'constructs';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import { Duration } from 'aws-cdk-lib';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import { Effect, PolicyStatement } from 'aws-cdk-lib/aws-iam';
import { createLambdaFunctionInstance } from '../../utils/lambda-helper';
import { APIEndpointHandlerStackProps } from '../../props/APIEndpointHandlerStackProps';

/**
 * Props for AsyncMappingHandler that extends the base props with SQS queue.
 */
export interface AsyncMappingHandlerProps extends APIEndpointHandlerStackProps {
  readonly mappingRequestQueue?: sqs.IQueue;
}

/**
 * Handler for async mapping operations.
 *
 * POST /api/v1/mappings - Start a new async mapping workflow
 * GET /api/v1/mappings/{mappingId}/status - Get job status
 *
 * This handler publishes mapping requests to SQS for durable processing.
 * The SQS Trigger Lambda then starts Step Functions workflows.
 */
export class AsyncMappingHandler {
  public readonly asyncHandler: lambda.Function;
  public readonly statusHandler: lambda.Function;

  constructor(scope: Construct, id: string, props: AsyncMappingHandlerProps) {
    // Async API handler - publishes to SQS queue
    this.asyncHandler = createLambdaFunctionInstance(
      scope,
      `NexusAsyncAPIHandler-${props.stage}`,
      'AsyncAPIHandler',
      'NexusAsyncAPIHandlerLambda',
      '1.0',
      'nexus_async_api_handler_lambda.handler.lambda_handler',
      Duration.minutes(1),
      props.vpc,
    );

    // Add environment variables
    this.asyncHandler.addEnvironment('STAGE', props.stage);
    this.asyncHandler.addEnvironment('JOB_TABLE_NAME', 'MappingJobs');
    this.asyncHandler.addEnvironment('FRAMEWORKS_TABLE_NAME', 'Frameworks');
    this.asyncHandler.addEnvironment('CONTROLS_TABLE_NAME', 'FrameworkControls');

    // Set queue URL if provided
    if (props.mappingRequestQueue) {
      this.asyncHandler.addEnvironment(
        'MAPPING_REQUEST_QUEUE_URL',
        props.mappingRequestQueue.queueUrl,
      );
      // Grant permission to send messages to the queue
      props.mappingRequestQueue.grantSendMessages(this.asyncHandler);
    }

    // Grant DynamoDB permissions for job creation and validation queries
    this.asyncHandler.addToRolePolicy(
      new PolicyStatement({
        actions: [
          'dynamodb:PutItem',
          'dynamodb:GetItem',
          'dynamodb:Query',
        ],
        effect: Effect.ALLOW,
        resources: [
          `arn:aws:dynamodb:${props.awsRegion}:*:table/MappingJobs`,
          `arn:aws:dynamodb:${props.awsRegion}:*:table/Frameworks`,
          `arn:aws:dynamodb:${props.awsRegion}:*:table/FrameworkControls`,
          `arn:aws:dynamodb:${props.awsRegion}:*:table/FrameworkControls/index/*`,
        ],
      }),
    );

    // Status API handler - returns job status
    this.statusHandler = createLambdaFunctionInstance(
      scope,
      `NexusStatusAPIHandler-${props.stage}`,
      'StatusAPIHandler',
      'NexusStatusAPIHandlerLambda',
      '1.0',
      'nexus_status_api_handler_lambda.handler.lambda_handler',
      Duration.minutes(1),
      props.vpc,
    );

    // Add environment variables for status handler
    this.statusHandler.addEnvironment('STAGE', props.stage);
    this.statusHandler.addEnvironment('JOB_TABLE_NAME', 'MappingJobs');

    // Grant DynamoDB permissions for job status queries
    this.statusHandler.addToRolePolicy(
      new PolicyStatement({
        actions: ['dynamodb:GetItem', 'dynamodb:Query'],
        effect: Effect.ALLOW,
        resources: [
          `arn:aws:dynamodb:${props.awsRegion}:*:table/MappingJobs`,
          `arn:aws:dynamodb:${props.awsRegion}:*:table/MappingJobs/index/*`,
        ],
      }),
    );
  }

  /**
   * Setup API resources for async mapping operations.
   *
   * @param mappingsResource The /api/v1/mappings resource from MappingManagementHandler
   * @param mappingIdResource The /api/v1/mappings/{mappingId} resource
   * @param tokenAuthorizer The token authorizer for authentication
   */
  public setupAsyncMappingAPIResources(
    mappingsResource: apigateway.Resource,
    mappingIdResource: apigateway.Resource,
    tokenAuthorizer: apigateway.TokenAuthorizer,
  ): void {
    const asyncIntegration = new apigateway.LambdaIntegration(this.asyncHandler);
    const statusIntegration = new apigateway.LambdaIntegration(this.statusHandler);
    const defaultMethodOptions = {
      authorizer: tokenAuthorizer,
      authorizationType: apigateway.AuthorizationType.CUSTOM,
    };

    // POST /api/v1/mappings - Start async mapping workflow
    // Note: This adds POST to the existing mappings resource created by MappingManagementHandler
    mappingsResource.addMethod('POST', asyncIntegration, defaultMethodOptions);

    // GET /api/v1/mappings/{mappingId}/status - Get job status
    const statusResource = mappingIdResource.addResource('status');
    statusResource.addMethod('GET', statusIntegration, {
      ...defaultMethodOptions,
      requestParameters: {
        'method.request.path.mappingId': true,
      },
    });
  }
}
