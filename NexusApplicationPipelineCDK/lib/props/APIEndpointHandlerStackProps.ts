import { DeploymentEnvironment } from '@amzn/pipelines';
import { Vpc } from 'aws-cdk-lib/aws-ec2';

export interface APIEndpointHandlerStackProps {
  readonly env: DeploymentEnvironment;
  readonly stage: string;
  readonly region: string;
  readonly awsRegion: string;
  readonly isProd: boolean;
  readonly vpc: Vpc;
}
