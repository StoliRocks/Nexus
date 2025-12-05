import { DeploymentEnvironment } from '@amzn/pipelines';
import { Vpc } from 'aws-cdk-lib/aws-ec2';
import * as sqs from 'aws-cdk-lib/aws-sqs';

export interface APIEndpointHandlerStackProps {
  readonly env: DeploymentEnvironment;
  readonly stage: string;
  readonly region: string;
  readonly awsRegion: string;
  readonly isProd: boolean;
  readonly vpc: Vpc;
  /**
   * Optional SQS queue for async mapping requests.
   * When provided, the async handler will publish to this queue
   * instead of directly starting Step Functions.
   */
  readonly mappingRequestQueue?: sqs.IQueue;
}
